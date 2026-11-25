"""Where a project stands, for the pipeline board on the home page.

Everything is derived from the latest run's status, stage and events; nothing is stored twice.
"""

from __future__ import annotations

import re

from .domain import RunRecord, RunStatus

COLUMNS = ("planning", "needs_you", "building", "ready", "failed")
STAGES = ("intake", "planning", "architecture", "building", "qa", "review")
PLANNING_STAGES = {"intake", "planning", "architecture"}


def has_module(run: RunRecord) -> bool:
    """A run produced a module the developer can use (a completed build, or a failed one that kept its files)."""
    return any(e.type == "build.completed" or (e.type == "build.failed" and not e.data.get("rolled_back")) for e in run.events)


BOILERPLATE = re.compile(r"^(build|create|make|add)\s+(a|an)\s+(module|app|tab)\s+(where|that|which|for|to|in which)\s+(learners\s+)?", re.I)


def short_goal(goal: str, limit: int = 110) -> str:
    first = re.split(r"(?<=[.!?])\s", goal.strip(), maxsplit=1)[0]
    first = BOILERPLATE.sub("", first)
    first = first[:1].upper() + first[1:]
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def _title(run: RunRecord) -> str | None:
    for event in reversed(run.events):
        if event.type == "artifact.accepted" and event.data.get("name") == "task_spec":
            return (event.data.get("artifact") or {}).get("title")
    return None


def _waiting_reason(run: RunRecord) -> str | None:
    """Why the run waits for the developer, or None."""
    for event in reversed(run.events):
        if event.type in ("question.answered", "criterion.answered", "plan.approved"):
            return None
        if event.type == "criterion.question":
            d = event.data
            return f"{d.get('criterion_id')}: measured {d.get('measured')}; proposed {d.get('proposed')}"
        if event.type == "question.asked":
            return str(event.data.get("question", ""))[:160]
        if event.type == "plan.ready":
            return "Plan ready for your approval"
    return None


def column_of(run: RunRecord | None) -> tuple[str, str]:
    if run is None:
        return "planning", "No runs yet. Open it and describe the module."
    waiting = _waiting_reason(run)
    if run.status == RunStatus.AWAITING_USER or (run.status == RunStatus.READY_FOR_REVIEW and waiting):
        return "needs_you", waiting or "Waiting for your answer"
    if run.status == RunStatus.ACTIVE:
        if run.stage.value in PLANNING_STAGES:
            return "planning", "Agents are planning"
        return "building", "Agents are building or changing the module"
    if run.status == RunStatus.READY_FOR_REVIEW:
        return "ready", "Module built and checked"
    if run.status == RunStatus.NEEDS_REVIEW:
        return "failed", "Tests failed; the module is kept for changes"
    error = next((e.data.get("error") for e in reversed(run.events) if e.type == "agent.failed"), None)
    return "failed", (str(error)[:160] if error else "The run failed")


def strip(run: RunRecord | None, column: str) -> list[str]:
    """Six cells, intake to review: done, current, waiting, failed or todo."""
    if run is None:
        return ["todo"] * len(STAGES)
    stage = "qa" if run.stage.value == "repair" else run.stage.value
    at = STAGES.index(stage) if stage in STAGES else 0
    here = {"needs_you": "waiting", "failed": "failed", "ready": "done"}.get(column, "current")
    return ["done" if i < at else here if i == at else "todo" for i in range(len(STAGES))]


def project_state(runs: list[RunRecord], files: int, spent: float | None) -> dict:
    runs = sorted(runs, key=lambda r: r.created_at)
    latest = runs[-1] if runs else None
    column, reason = column_of(latest)
    first = runs[0] if runs else None
    specs = {}
    for run in runs:
        for event in run.events:
            if event.type == "artifact.accepted":
                specs[event.data.get("name")] = event.data.get("artifact") or {}
    task = specs.get("task_spec", {})
    method = specs.get("research_brief", {}).get("method") or {}
    return {
        "learning_objective": next(iter(task.get("learning_objectives") or []), ""),
        "method_name": method.get("name"),
        "audience": task.get("learner_audience"),
        "column": column,
        "reason": reason,
        "strip": strip(latest, column),
        "summary": short_goal(first.goal) if first else "",
        "title": _title(first) if first else None,
        "versions": sum(has_module(r) for r in runs),
        "has_module": files > 0 and any(has_module(r) for r in runs),
        "last_activity": max((r.updated_at for r in runs), default=None),
        "spend_usd": round(spent, 4) if spent is not None else None,
    }
