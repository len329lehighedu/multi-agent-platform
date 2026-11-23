"""Orchestrator-driven planning workflow.

The orchestrator, not the agents, decides the order of work. Each step hands a
task to one specialist, which returns control with a summary. A specialist may
ask the user one question; that pauses the run in a persisted `awaiting_user`
state and a later answer resumes the same step. Every decision is a run event.

This workflow produces a plan only: no agent writes code or runs tools yet.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from threading import Lock, Thread

from .domain import Message, RunRecord, RunStage, RunStatus
from .orchestrator import Orchestrator
from .providers.base import ModelProvider, ModelRequest

PLAN_ONLY_RULES = """
Plan-only mode: do not write code, use tools, or claim anything was built, tested or run.
Reply with one JSON object and nothing else:
{"message": "plain text for the user, at most 120 words", "question": "one question or null", "handoff_summary": "at most 60 words for the next agent"}
"""


@dataclass(frozen=True, slots=True)
class Step:
    agent_id: str
    stage: RunStage
    task: str
    may_ask: bool = False


STEPS = (
    Step("learning_planner", RunStage.PLANNING, "Draft a learner brief for an interactive data-science module in which the learner can fit a model, test it on held-out data, and predict. Cover audience, one objective, and the core interaction.", may_ask=True),
    Step("scientific_architect", RunStage.ARCHITECTURE, "Propose the scientific method, the data contract, the train/test approach, and how the science will be verified."),
    Step("builder", RunStage.BUILDING, "Outline the build plan: files, responsibilities, and order of work. Plan only."),
    Step("qa_reviewer", RunStage.QA, "List the independent checks you will run on the finished module. Mark all as not yet run."),
    Step("orchestrator", RunStage.REVIEW, "Summarize the specialists' work for the user. State clearly that this is a plan and nothing has been built."),
)


def parse_agent_reply(response) -> dict:
    data = response.structured_output
    if data is None:
        text = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(text)
            data = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            data = None
    if not data or not str(data.get("message", "")).strip():
        return {"message": response.text.strip(), "question": None, "summary": response.text.strip()[:300]}
    question = data.get("question")
    return {
        "message": str(data["message"]).strip(),
        "question": str(question).strip() if question else None,
        "summary": str(data.get("handoff_summary") or data["message"]).strip()[:400],
    }


class PlanningWorkflow:
    def __init__(self, orchestrator: Orchestrator, providers: dict[str, ModelProvider], default_provider: str):
        self.orchestrator = orchestrator
        self.providers = providers
        self.default_provider = default_provider
        self._lock = Lock()
        self._active: set[str] = set()

    # -- entry point -------------------------------------------------------

    def submit(self, run_id: str, content: str) -> RunRecord:
        """Start the workflow with the first message, or answer a pending question."""
        if not content.strip():
            raise ValueError("content is required")
        with self._lock:
            if run_id in self._active:
                raise ValueError("this run is already working")
            run = self.orchestrator.store.get(run_id)
            paused = self._pending_pause(run)
            if paused is not None:
                start = paused["step"]
            elif not any(e.type == "workflow.started" for e in run.events):
                start = 0
            else:
                raise ValueError("this run has finished; start a new run")
            provider_id = self._provider_id(run)
            if provider_id not in self.providers:
                raise ValueError(f"provider is not available: {provider_id}")
            self._active.add(run_id)
        try:
            run = self.orchestrator.receive_message(run_id, content)
            if paused is not None:
                run.append_event("question.answered", {"agent_id": STEPS[start].agent_id, "step": start})
            else:
                run.append_event("workflow.started", {"steps": [s.agent_id for s in STEPS], "provider": provider_id})
            run.status = RunStatus.ACTIVE
            self.orchestrator.store.save(run)
            Thread(target=self._execute, args=(run_id, start), daemon=True).start()
        except Exception:
            with self._lock:
                self._active.discard(run_id)
            raise
        return run

    # -- execution ---------------------------------------------------------

    def _execute(self, run_id: str, start: int) -> None:
        agent_id = "orchestrator"
        try:
            for index in range(start, len(STEPS)):
                agent_id = STEPS[index].agent_id
                if self._run_step(run_id, index, STEPS[index]):
                    return
            run = self.orchestrator.store.get(run_id)
            run.status = RunStatus.READY_FOR_REVIEW
            run.append_event("workflow.completed", {"outcome": "plan_ready", "built": False})
            self.orchestrator.store.save(run)
        except Exception as error:
            run = self.orchestrator.store.get(run_id)
            run.status = RunStatus.FAILED
            run.append_event("agent.failed", {"agent_id": agent_id, "error": str(error)[:300]})
            self.orchestrator.store.save(run)
        finally:
            with self._lock:
                self._active.discard(run_id)

    def _run_step(self, run_id: str, index: int, step: Step) -> bool:
        """Run one step. Returns True when the run paused to ask the user."""
        store = self.orchestrator.store
        run = store.get(run_id)
        resumed = any(e.type == "question.answered" and e.data.get("step") == index for e in run.events)
        delegated = step.agent_id != "orchestrator"
        if run.stage != step.stage:
            run.transition(step.stage, f"{step.agent_id} assigned")
        if delegated and not resumed:
            run.append_event("handoff.requested", {"from": "orchestrator", "to": step.agent_id, "task": step.task})
        run.append_event("agent.started", {"agent_id": step.agent_id, "step": index})
        store.save(run)

        agent = self.orchestrator.agents.get(step.agent_id)
        request = ModelRequest(
            run_id=run_id,
            agent_id=agent.id,
            system_prompt=f"{agent.prompt}\n{PLAN_ONLY_RULES}",
            messages=({"role": "user", "content": self._context(run, step, resumed)},),
            metadata={"json": True},
        )
        started = time.monotonic()
        response = self.providers[self._provider_id(run)].generate(request)
        latency_ms = int((time.monotonic() - started) * 1000)
        reply = parse_agent_reply(response)

        question = reply["question"] if step.may_ask and not resumed else None
        text = reply["message"] + (f"\n\n{question}" if question else "")
        run = store.get(run_id)
        run.append_message(Message.create("agent", text, agent_id=agent.id))
        run.append_event("agent.completed", {"agent_id": agent.id, "step": index, "latency_ms": latency_ms, "usage": response.usage})
        if question:
            run.append_event("question.asked", {"agent_id": agent.id, "step": index, "question": question})
            run.status = RunStatus.AWAITING_USER
            run.append_event("workflow.paused", {"step": index, "agent_id": agent.id})
            store.save(run)
            return True
        if delegated:
            run.append_event("handoff.returned", {"from": agent.id, "to": "orchestrator", "summary": reply["summary"]})
        store.save(run)
        return False

    # -- helpers -----------------------------------------------------------

    def _provider_id(self, run: RunRecord) -> str:
        created = next((e for e in run.events if e.type == "run.created"), None)
        return (created.data.get("provider") if created else None) or self.default_provider

    @staticmethod
    def _pending_pause(run: RunRecord) -> dict | None:
        if run.status != RunStatus.AWAITING_USER:
            return None
        paused = [e for e in run.events if e.type == "workflow.paused"]
        return paused[-1].data if paused else None

    @staticmethod
    def _context(run: RunRecord, step: Step, resumed: bool) -> str:
        users = [m.content for m in run.messages if m.role == "user"]
        summaries = [e.data for e in run.events if e.type == "handoff.returned"]
        parts = [f"Goal: {run.goal}", "User messages:\n" + "\n".join(f"- {text}" for text in users)]
        if summaries:
            parts.append("Earlier specialist summaries:\n" + "\n".join(f"- {s['from']}: {s['summary']}" for s in summaries))
        parts.append(f"Your task: {step.task}")
        if step.may_ask:
            parts.append("The user has answered your question; do not ask another. Set question to null." if resumed
                         else "If one decision would materially change the learner experience, ask exactly one question; otherwise set question to null.")
        else:
            parts.append("Set question to null.")
        parts.append("Reply with the JSON object described in your instructions.")
        return "\n\n".join(parts)
