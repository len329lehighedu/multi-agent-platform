"""Anthropic (Claude) adapter for the vendor-neutral ModelProvider contract.

Models by tier: the agent manifest marks each agent "fast" or "strong".
  fast   -> CLAUDE_MODEL_FAST   (default claude-haiku-5-5)
  strong -> CLAUDE_MODEL_STRONG, else CLAUDE_MODEL (default claude-sonnet-5-5)

Every call is priced from its real usage and added to a persistent ledger. Calls stop with a
clear error once the ledger reaches the total budget (CLAUDE_BUDGET_USD, default 90) or one
project reaches its module budget (CLAUDE_MODULE_BUDGET_USD, default 1.00), so a runaway loop
cannot overspend the agreed API credit.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

from .base import ModelRequest, ModelResponse, ProviderError

# USD per 1M tokens: (input, output, cache read). Cache writes (5 min) cost 1.25x input.
# Haiku has a higher price above 100K prompt tokens.
PRICES = {
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cache": 0.01, "big_in": 0.50, "big_out": 2.50},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache": 0.10},
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cache": 0.20},
}
DEFAULTS = {"fast": "claude-haiku-5-5", "strong": "claude-sonnet-5-5"}
EFFORT = {"fast": "medium", "strong": "medium"}


def price_of(model: str) -> dict:
    # Unknown model: price it like the most expensive one so the budget guard fails safe.
    return PRICES.get(model) or PRICES["claude-opus-5-5"]


def cost_usd(model: str, usage: dict) -> float:
    price = price_of(model)
    fresh = usage.get("input_tokens") or 0
    written = usage.get("cache_creation_input_tokens") or 0
    read = usage.get("cache_read_input_tokens") or 0
    out = usage.get("output_tokens") or 0
    big = fresh + written + read > 100_000 and "big_in" in price
    rate_in = price["big_in"] if big else price["in"]
    rate_out = price["big_out"] if big else price["out"]
    return (fresh * rate_in + written * rate_in * 1.25 + read * price["cache"] + out * rate_out) / 1_000_000


class SpendLedger:
    """Running total of API spend, persisted so a restart does not reset the budget."""

    def __init__(self, path: Path | None, budget: float, module_budget: float | None = None):
        self.path, self.budget, self.module_budget = path, budget, module_budget
        self.by_project: dict[str, float] = {}
        self._lock = Lock()
        self.total = 0.0
        self.calls = 0
        self.by_model: dict[str, float] = {}
        if path and Path(path).exists():
            try:
                saved = json.loads(Path(path).read_text(encoding="utf-8"))
                self.total = float(saved.get("total_usd", 0))
                self.calls = int(saved.get("calls", 0))
                self.by_model = dict(saved.get("by_model", {}))
                self.by_project = dict(saved.get("by_project", {}))
            except (OSError, ValueError):
                pass

    def check(self, project_id: str | None = None) -> None:
        with self._lock:
            if self.total >= self.budget:
                raise ProviderError(f"API budget reached: ${self.total:.2f} spent of ${self.budget:.2f}. Raise CLAUDE_BUDGET_USD to continue.")
            spent = self.by_project.get(project_id, 0.0) if project_id else 0.0
            if self.module_budget is not None and spent >= self.module_budget:
                raise ProviderError(f"Module budget reached: ${spent:.2f} spent of ${self.module_budget:.2f} on this project. Raise CLAUDE_MODULE_BUDGET_USD to continue.")

    def add(self, model: str, amount: float, project_id: str | None = None) -> float:
        with self._lock:
            self.total += amount
            if project_id:
                self.by_project[project_id] = round(self.by_project.get(project_id, 0.0) + amount, 6)
            self.calls += 1
            self.by_model[model] = round(self.by_model.get(model, 0.0) + amount, 6)
            if self.path:
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
                Path(self.path).write_text(json.dumps(self.snapshot_unlocked(), indent=2), encoding="utf-8")
            return self.total

    def snapshot_unlocked(self) -> dict:
        return {"total_usd": round(self.total, 6), "budget_usd": self.budget, "calls": self.calls, "by_model": self.by_model,
                "module_budget_usd": self.module_budget, "by_project": self.by_project}

    def snapshot(self) -> dict:
        with self._lock:
            return self.snapshot_unlocked()


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None, ledger_path: Path | None = None,
                 budget: float | None = None, client=None, debug_dir: Path | None = None, module_budget: float | None = None):
        self._api_key = api_key or os.getenv("CLAUDE_API_KEY")
        self.model = model or os.getenv("CLAUDE_MODEL") or DEFAULTS["strong"]
        self._client = client
        self.debug_dir = Path(debug_dir) if debug_dir else None
        limit = budget if budget is not None else float(os.getenv("CLAUDE_BUDGET_USD", "90"))
        per_module = module_budget if module_budget is not None else float(os.getenv("CLAUDE_MODULE_BUDGET_USD", "1.00"))
        self.ledger = SpendLedger(ledger_path, limit, per_module)

    def _model_for(self, tier: str | None) -> str:
        tier = tier if tier in DEFAULTS else "strong"
        override = os.getenv(f"CLAUDE_MODEL_{tier.upper()}")
        if override:
            return override
        if tier == "fast":
            return DEFAULTS["fast"]
        return self.model if self.model.startswith("claude") else DEFAULTS["strong"]

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ProviderError("CLAUDE_API_KEY is not set")
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def generate(self, request: ModelRequest) -> ModelResponse:
        project_id = request.metadata.get("project_id")
        self.ledger.check(project_id)
        tier = request.metadata.get("tier")
        tier = tier if tier in DEFAULTS else "strong"
        model = self._model_for(tier)
        big = str(request.metadata.get("key", "")).startswith("file_set")
        params = dict(
            model=model,
            max_tokens=32000 if big else 16000,
            system=[{"type": "text", "text": request.system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": m["role"], "content": m["content"]} for m in request.messages],
            output_config={"effort": os.getenv(f"CLAUDE_EFFORT_{tier.upper()}", EFFORT[tier])},
            cache_control={"type": "ephemeral"},
        )
        # Fast-tier models write JSON files directly; hidden thinking only burns the output budget.
        if tier == "fast" and os.getenv("CLAUDE_THINKING_FAST", "off") == "off":
            params["thinking"] = {"type": "disabled"}
        try:
            with self._get_client().messages.stream(**params) as stream:
                message = stream.get_final_message()
        except ProviderError:
            raise
        except Exception as error:  # vendor exceptions never cross this boundary
            raise ProviderError(f"Claude request failed: {str(error)[:200]}") from error
        usage = message.usage
        counts = {
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        }
        spent = cost_usd(model, counts)
        total = self.ledger.add(model, spent, project_id)
        if getattr(message, "stop_reason", None) == "refusal":
            raise ProviderError("Claude declined this request")
        text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text").strip()
        if getattr(message, "stop_reason", None) == "max_tokens":
            self._dump_truncated(request, model, counts, text)
            raise ProviderError("Claude hit the output limit before finishing; shorten the request or split the work")
        if not text:
            raise ProviderError("Claude returned no text")
        structured = None
        if request.metadata.get("json"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                start, end = text.find("{"), text.rfind("}")
                try:
                    parsed = json.loads(text[start:end + 1]) if 0 <= start < end else None
                except json.JSONDecodeError:
                    parsed = None
            structured = parsed if isinstance(parsed, dict) else None
        return ModelResponse(
            text=text,
            structured_output=structured,
            usage={**counts, "cost_usd": round(spent, 6), "total_spent_usd": round(total, 4)},
            provider_metadata={"provider": "claude", "model": model},
        )

    def _dump_truncated(self, request: ModelRequest, model: str, counts: dict, text: str) -> None:
        """Keep the cut-off reply on disk so the cause (loop, huge file, thinking) can be read, not guessed."""
        if not self.debug_dir:
            return
        try:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            name = f"{request.run_id}-{request.agent_id}-{str(request.metadata.get('key', 'call')).replace(':', '_')}-truncated.txt"
            (self.debug_dir / name).write_text(f"model={model}\nusage={json.dumps(counts)}\nchars={len(text)}\n\n{text}", encoding="utf-8")
        except OSError:
            pass
