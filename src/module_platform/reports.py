"""Where the tokens and the failures go, computed from run events (the events are the log).

`run_report` summarizes one run; `aggregate` sums many and lists recurring problems with a hint of
which skill could prevent them. Hints are suggestions for a human: a rule added to a skill is sent
with every call, so only problems that recur earn one.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from .domain import RunRecord

# Failure kinds read from real test output; the first matching pattern wins.
FAILURE_KINDS = (
    ("bokeh_load", re.compile(r"failed to load as a Bokeh app")),
    ("timeout", re.compile(r"timed out after")),
    ("missing_package", re.compile(r"ModuleNotFoundError|No module named")),
    ("syntax", re.compile(r"SyntaxError|IndentationError")),
    ("import_error", re.compile(r"ImportError|cannot import name")),
    ("assertion", re.compile(r"AssertionError")),
    ("exception", re.compile(r"Traceback \(most recent call last\)")),
)

# Normalized rejection messages -> a short kind.
REJECTION_KINDS = (
    ("uncovered_criterion", re.compile(r"no test case covers")),
    ("enum_value", re.compile(r"must be one of")),
    ("wrong_type", re.compile(r"expected (string|number|boolean|object|array|integer)")),
    ("empty_list", re.compile(r"needs at least \d+ item")),
    ("empty_file", re.compile(r"file is empty")),
    ("missing_design_file", re.compile(r"design file not written")),
    ("not_allowed", re.compile(r"not allowed")),
    ("missing_field", re.compile(r"is required|missing")),
)

HINTS = {
    "rejection:uncovered_criterion": "test-design: every acceptance criterion needs at least one case",
    "rejection:enum_value": "the agent's skill: list the allowed values of the field it got wrong",
    "rejection:wrong_type": "the agent's skill: show the expected type of the field it got wrong",
    "rejection:empty_list": "the agent's skill: the field needs at least one item",
    "rejection:empty_file": "code-conventions: never write an empty file",
    "failure:bokeh_load": "bokeh-ui-design: add the Bokeh API rule from the failing output",
    "failure:missing_package": "package-selection / code-conventions: import only installed packages",
    "failure:assertion": "scientific-oracle / test-design: reachable thresholds with margin (or the criterion question)",
    "failure:timeout": "performance-optimization: keep tests fast (smaller sizes in tests)",
    "failure:syntax": "code-conventions: a syntax error usually means a truncated or rushed file",
}


def _model_from_price(usage: dict) -> str:
    """Older events lack the model name; the price table identifies it from tokens and cost."""
    from .providers.anthropic_provider import PRICES, cost_usd

    cost = usage.get("cost_usd")
    if not cost:
        return "not recorded"
    best = min(PRICES, key=lambda model: abs(cost_usd(model, usage) - cost))
    return best if abs(cost_usd(best, usage) - cost) <= max(1e-6, cost * 0.02) else "not recorded"


def classify_failure(output: str) -> str:
    for kind, pattern in FAILURE_KINDS:
        if pattern.search(output or ""):
            return kind
    return "other"


def classify_rejection(message: str) -> str:
    for kind, pattern in REJECTION_KINDS:
        if pattern.search(message or ""):
            return kind
    return "other"


def failing_tests(output: str) -> tuple[list[str], list[str]]:
    """unittest output -> (test names that FAILed an assertion, test names that ERRORed)."""
    failed = re.findall(r"^FAIL: (\w+)", output or "", re.M)
    errored = re.findall(r"^ERROR: (\w+)", output or "", re.M)
    return failed, errored


def run_report(run: RunRecord) -> dict:
    steps: dict[str, dict] = {}
    agents: dict[str, dict] = {}
    models: dict[str, dict] = {}
    rejections: Counter = Counter()
    failures: Counter = Counter()
    repairs = revisions = 0
    replayed = priced = False
    artifact_by_step = {e.data.get("step"): e.data.get("name") for e in run.events if e.type == "artifact.accepted" and isinstance(e.data.get("step"), int)}
    for event in run.events:
        data = event.data
        if event.type == "agent.completed":
            usage = data.get("usage") or {}
            replayed = replayed or bool(usage.get("replayed"))
            priced = priced or "cost_usd" in usage
            step = data.get("artifact") or artifact_by_step.get(data.get("step")) or str(data.get("step"))
            key = f"{data.get('agent_id')}:{step}"
            row = steps.setdefault(key, {"agent": data.get("agent_id"), "step": step, "calls": 0, "input_tokens": 0,
                                         "output_tokens": 0, "cache_read_tokens": 0, "cost_usd": 0.0, "seconds": 0.0, "attempts": 0})
            row["calls"] += 1
            row["attempts"] += data.get("attempts", 1) or 1
            row["input_tokens"] += (usage.get("input_tokens") or 0) + (usage.get("cache_creation_input_tokens") or 0)
            row["output_tokens"] += usage.get("output_tokens") or 0
            row["cache_read_tokens"] += usage.get("cache_read_input_tokens") or 0
            row["cost_usd"] += usage.get("cost_usd") or 0.0
            row["seconds"] += (data.get("latency_ms") or 0) / 1000
            model = usage.get("model") or ("replay" if usage.get("replayed") else _model_from_price(usage))
            for table, name in ((agents, data.get("agent_id")), (models, model)):
                total = table.setdefault(name, {"calls": 0, "output_tokens": 0, "cost_usd": 0.0, "models": set()})
                total["calls"] += 1
                total["output_tokens"] += usage.get("output_tokens") or 0
                total["cost_usd"] += usage.get("cost_usd") or 0.0
                total["models"].add(model)
        elif event.type == "artifact.rejected":
            for message in data.get("errors", [])[:8]:
                rejections[(data.get("agent_id"), classify_rejection(message))] += 1
        elif event.type == "build.checks" and not data.get("passed"):
            failures[classify_failure(data.get("output", ""))] += 1
            repairs += 1 if data.get("round") else 0
        elif event.type == "revision.requested":
            revisions += 1
    rows = sorted(steps.values(), key=lambda r: -r["cost_usd"])
    for row in rows:
        row["cost_usd"] = round(row["cost_usd"], 6)
        row["seconds"] = round(row["seconds"], 1)
    by_agent: dict[str, float] = defaultdict(float)
    for row in rows:
        by_agent[row["agent"]] += row["cost_usd"]
    outcome = next((e.type for e in reversed(run.events) if e.type in ("build.completed", "build.failed", "plan.ready", "agent.failed")), "in progress")
    return {
        "run_id": run.id, "project_id": run.project_id, "kind": run.kind, "goal": run.goal[:160], "outcome": outcome,
        "replayed": replayed, "priced": priced, "cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
        "output_tokens": sum(r["output_tokens"] for r in rows), "calls": sum(r["calls"] for r in rows),
        "by_agent": {k: round(v, 6) for k, v in sorted(by_agent.items(), key=lambda kv: -kv[1])},
        "steps": rows, "repair_rounds": repairs, "revisions": revisions,
        "agents": _totals(agents, "agent"), "models": _totals(models, "model"),
        "rejections": [{"agent": a, "kind": k, "count": n} for (a, k), n in rejections.most_common()],
        "test_failures": [{"kind": k, "count": n} for k, n in failures.most_common()],
    }


def _totals(table: dict[str, dict], key: str) -> list[dict]:
    rows = [{key: name, "calls": t["calls"], "output_tokens": t["output_tokens"], "cost_usd": round(t["cost_usd"], 6),
             **({"models": sorted(t["models"])} if key == "agent" else {})} for name, t in table.items()]
    return sorted(rows, key=lambda r: -r["cost_usd"])


def aggregate(runs: list[RunRecord], include_replayed: bool = False) -> dict:
    reports = [run_report(run) for run in runs]
    if not include_replayed:  # replayed and unpriced (legacy) runs say nothing about real cost
        reports = [r for r in reports if r["priced"] and not r["replayed"]]
    by_agent: dict[str, float] = defaultdict(float)
    by_model: dict[str, dict] = {}
    by_step: dict[str, dict] = {}
    rejections: Counter = Counter()
    failures: Counter = Counter()
    for report in reports:
        for agent, cost in report["by_agent"].items():
            by_agent[agent] += cost
        for row in report["models"]:
            total = by_model.setdefault(row["model"], {"model": row["model"], "calls": 0, "output_tokens": 0, "cost_usd": 0.0})
            total["calls"] += row["calls"]
            total["output_tokens"] += row["output_tokens"]
            total["cost_usd"] += row["cost_usd"]
        for row in report["steps"]:
            step = re.sub(r"\d+", "#", row["step"])  # "revision 3 repair 1" -> "revision # repair #"
            key = f"{row['agent']}:{step}"
            total = by_step.setdefault(key, {"agent": row["agent"], "step": step, "calls": 0, "output_tokens": 0, "cost_usd": 0.0})
            total["calls"] += row["calls"]
            total["output_tokens"] += row["output_tokens"]
            total["cost_usd"] += row["cost_usd"]
        for item in report["rejections"]:
            rejections[(item["agent"], item["kind"])] += item["count"]
        for item in report["test_failures"]:
            failures[item["kind"]] += item["count"]
    cost = sum(r["cost_usd"] for r in reports)
    recurring = [{"source": f"rejection:{kind}", "agent": agent, "count": n, "hint": HINTS.get(f"rejection:{kind}", "")}
                 for (agent, kind), n in rejections.most_common() if n >= 2]
    recurring += [{"source": f"failure:{kind}", "agent": "builder", "count": n, "hint": HINTS.get(f"failure:{kind}", "")}
                  for kind, n in failures.most_common() if n >= 2]
    built = [r for r in reports if r["outcome"] == "build.completed"]
    return {
        "runs": len(reports), "cost_usd": round(cost, 6),
        "avg_cost_per_built_run": round(sum(r["cost_usd"] for r in built) / len(built), 6) if built else None,
        "by_agent": [{"agent": a, "cost_usd": round(c, 6), "share": round(c / cost, 3) if cost else 0.0}
                     for a, c in sorted(by_agent.items(), key=lambda kv: -kv[1])],
        "by_model": [dict(row, cost_usd=round(row["cost_usd"], 6)) for row in sorted(by_model.values(), key=lambda r: -r["cost_usd"])],
        "by_step": [dict(row, cost_usd=round(row["cost_usd"], 6)) for row in sorted(by_step.values(), key=lambda r: -r["cost_usd"])],
        "rejections": [{"agent": a, "kind": k, "count": n} for (a, k), n in rejections.most_common()],
        "test_failures": [{"kind": k, "count": n} for k, n in failures.most_common()],
        "recurring": recurring,
    }


def markdown(summary: dict) -> str:
    lines = ["# Agent usage report", "", f"Runs: {summary['runs']} · total ${summary['cost_usd']:.4f}"
             + (f" · average per built run ${summary['avg_cost_per_built_run']:.4f}" if summary["avg_cost_per_built_run"] else ""), "",
             "## Cost by agent", "", "| Agent | Cost | Share |", "|---|---|---|"]
    lines += [f"| {r['agent']} | ${r['cost_usd']:.4f} | {r['share']:.0%} |" for r in summary["by_agent"]]
    lines += ["", "## Most expensive steps", "", "| Step | Calls | Output tokens | Cost |", "|---|---|---|---|"]
    lines += [f"| {r['agent']}: {r['step']} | {r['calls']} | {r['output_tokens']} | ${r['cost_usd']:.4f} |" for r in summary["by_step"][:12]]
    lines += ["", "## Recurring problems (2 or more)", ""]
    lines += [f"- {r['source']} ({r['agent']}, {r['count']}x): {r['hint']}" for r in summary["recurring"]] or ["- none"]
    lines += ["", "## All rejections", ""]
    lines += [f"- {r['agent']} {r['kind']}: {r['count']}" for r in summary["rejections"]] or ["- none"]
    lines += ["", "## Test failures by kind", ""]
    lines += [f"- {r['kind']}: {r['count']}" for r in summary["test_failures"]] or ["- none"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import os
    from pathlib import Path

    from .store import JsonRunStore

    root = Path(__file__).resolve().parents[2]
    data = Path(os.environ.get("MODULE_FOUNDRY_DATA", root / "var"))
    text = markdown(aggregate(JsonRunStore(data / "runs").list()))
    out = data / "reports" / "usage.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved to {out}")
