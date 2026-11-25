"""Deterministic provider that replays recorded agent responses.

Used for offline demos and tests. Each agent's recorded responses are consumed
in order per run; the last one repeats if a run asks for more.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
import time

from .base import ModelRequest, ModelResponse, ProviderError


class ReplayProvider:
    def __init__(self, fixture: Path, delay: float = 0.0):
        self.responses: dict[str, list[dict]] = json.loads(Path(fixture).read_text(encoding="utf-8"))
        self.delay = delay
        self._counts: dict[tuple, int] = {}
        self._lock = Lock()

    def describe(self, tier: str | None) -> dict:
        return {"model": "replay", "model_label": "Replay", "effort": None}

    def generate(self, request: ModelRequest) -> ModelResponse:
        recorded = self.responses.get(request.agent_id)
        if not recorded:
            raise ProviderError(f"no recorded response for agent {request.agent_id}")
        kind = request.metadata.get("key")
        if kind and any("for" in item for item in recorded):
            recorded = [item for item in recorded if item.get("for") == kind]
            if not recorded:
                raise ProviderError(f"no recorded response for {request.agent_id} / {kind}")
        with self._lock:
            key = (request.run_id, request.agent_id, kind if any("for" in item for item in self.responses[request.agent_id]) else None)
            index = self._counts.get(key, 0)
            self._counts[key] = index + 1
        entry = {k: v for k, v in recorded[min(index, len(recorded) - 1)].items() if k != "for"}
        if self.delay:
            time.sleep(self.delay)
        return ModelResponse(
            text=json.dumps(entry),
            structured_output=dict(entry),
            usage={"replayed": True},
            provider_metadata={"provider": "replay"},
        )
