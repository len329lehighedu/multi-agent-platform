"""Orchestrator-driven planning workflow.

The Project Manager orchestrates; specialists never talk to each other. Each step
hands a task to one agent, which returns a schema-validated artifact. Deterministic
checks (schema, cross-artifact consistency) run in code; a failure triggers one
targeted repair request, and a second failure ends the run. Downstream agents
receive artifacts, not chat history.

A specialist may ask the user one question; that pauses the run in a persisted
`awaiting_user` state and the answer resumes the same step. This workflow produces
a plan only: no agent writes code or runs tools yet.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from pathlib import Path
from threading import Lock, Thread

from . import artifacts as checks
from .artifacts import ArtifactSchemas
from .domain import Message, RunRecord, RunStage, RunStatus
from .environment import environment_note
from .orchestrator import Orchestrator
from .providers.base import ModelProvider, ModelRequest
from .skills import SkillLibrary
from .workspaces import module_files

MANAGER = "project_manager"

REPLY_FORMAT = """
Plan-only mode: do not write code, use tools, or claim anything was built, tested or run.
Reply with one JSON object and nothing else:
{"message": "plain text for the user, at most 120 words", "question": "one question or null", "handoff_summary": "at most 60 words for the next agent", "artifact": <object described below, or null>}
"""


@dataclass(frozen=True, slots=True)
class Step:
    agent_id: str
    stage: RunStage
    task: str
    artifact: str | None = None
    needs: tuple[str, ...] = ()
    may_ask: bool = False
    only_skills: tuple[str, ...] | None = None
    digest: bool = False  # receive condensed design_spec / test_plan instead of the full artifacts
    ask_about: str = ""  # what this step may ask the user about (one question at most)


STEPS = (
    Step(MANAGER, RunStage.PLANNING, "Turn the user's request into a task_spec for an interactive data-science module (train, test, predict).", artifact="task_spec", may_ask=True,
         ask_about="the request is ambiguous about the goal or scope (what the module is for, who uses it); leave scientific and technical choices to the specialists"),
    Step("researcher", RunStage.ARCHITECTURE, "Decide the model, inputs, hyperparameters, algorithm, packages and the independent scientific oracle.", artifact="research_brief", needs=("task_spec",), may_ask=True,
         ask_about="the depth of the science changes the module: how advanced the method should be, which advanced hyperparameters learners should control, or a number in the task spec that the method cannot reach for this data"),
    Step("builder", RunStage.BUILDING, "Design the Bokeh-only system (no Flask, no HTML pages): files, train/test/predict separation, performance, plots, controls. Design only.", artifact="design_spec", needs=("task_spec", "research_brief"), may_ask=True,
         ask_about="a code or system design choice the user must make: how tabs share state, what runs on a button versus live on a slider, or a performance trade-off (speed against accuracy)"),
    Step("tester", RunStage.QA, "Create the test plan: cases per layer, edge cases, and oracle checks. Nothing has been run yet.", artifact="test_plan", needs=("task_spec", "research_brief", "design_spec")),
    Step(MANAGER, RunStage.REVIEW, "Synthesize the specialists' accepted artifacts into the project_plan the user will approve before any build: what the module does, the algorithm, how success is defined, and what the user can do with the MVP.",
         artifact="project_plan", needs=("task_spec", "research_brief", "design_spec", "test_plan"), only_skills=("plan-synthesis", "stage-gating-and-handoff"), digest=True),
)


class ArtifactRejected(RuntimeError):
    pass


def condense(name: str, artifact: dict) -> dict:
    """Compact view of the large artifacts for the final synthesis (fewer input tokens)."""
    if name == "design_spec":
        return {
            "files": [f"{f['path']} ({f['role']})" for f in artifact["files"]],
            "tabs": [{"id": t["id"], "title": t["title"], "controls": [c["id"] for c in t["controls"]],
                      "plots": [p["question_answered"] for p in t["plots"]]} for t in artifact["tabs"]],
            "performance": artifact["performance"]["strategy"],
        }
    if name == "test_plan":
        return {
            "cases": [f"{c['id']} [{c['layer']}{', edge' if c['edge_case'] else ''}] covers {','.join(c['criterion_ids'])}" for c in artifact["cases"]],
            "oracle_checks": [f"{o['id']}: {o['description']} (tolerance {o['tolerance']})" for o in artifact["oracle_checks"]],
            "not_runnable": artifact["not_runnable"],
        }
    return artifact


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
        return {"message": response.text.strip(), "question": None, "summary": response.text.strip()[:300], "artifact": None}
    question = data.get("question")
    return {
        "message": str(data["message"]).strip(),
        "question": str(question).strip() if question else None,
        "summary": str(data.get("handoff_summary") or data["message"]).strip()[:400],
        "artifact": data.get("artifact"),
    }


def _add_usage(total: dict, usage: dict) -> None:
    for key, value in usage.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total[key] = total.get(key, 0) + value
        else:
            total[key] = value


class PlanningWorkflow:
    def __init__(self, orchestrator: Orchestrator, providers: dict[str, ModelProvider], default_provider: str,
                 skills: SkillLibrary, schemas: ArtifactSchemas):
        self.orchestrator = orchestrator
        self.providers = providers
        self.default_provider = default_provider
        self.skills = skills
        self.schemas = schemas
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
                raise ValueError("the plan is ready: approve it to start the build, or start a new run" if any(e.type == "plan.ready" for e in run.events) else "this run has finished; start a new run")
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

    def claim(self, run_id: str) -> None:
        with self._lock:
            if run_id in self._active:
                raise ValueError("this run is already working")
            self._active.add(run_id)

    def release(self, run_id: str) -> None:
        with self._lock:
            self._active.discard(run_id)

    def artifacts(self, run: RunRecord) -> dict[str, dict]:
        return {e.data["name"]: e.data["artifact"] for e in run.events if e.type == "artifact.accepted"}

    # -- execution ---------------------------------------------------------

    def _execute(self, run_id: str, start: int) -> None:
        agent_id = MANAGER
        try:
            for index in range(start, len(STEPS)):
                agent_id = STEPS[index].agent_id
                if self._run_step(run_id, index, STEPS[index]):
                    return
            run = self.orchestrator.store.get(run_id)
            run.status = RunStatus.READY_FOR_REVIEW
            run.append_event("workflow.completed", {"outcome": "plan_ready", "built": False, "artifacts": sorted(self.artifacts(run))})
            self.orchestrator.store.save(run)
        except Exception as error:
            run = self.orchestrator.store.get(run_id)
            run.status = RunStatus.FAILED
            run.append_event("agent.failed", {"agent_id": agent_id, "error": str(error)[:400]})
            self.orchestrator.store.save(run)
        finally:
            with self._lock:
                self._active.discard(run_id)

    def _run_step(self, run_id: str, index: int, step: Step) -> bool:
        """Run one step. Returns True when the run paused to ask the user."""
        store = self.orchestrator.store
        run = store.get(run_id)
        resumed = any(e.type == "question.answered" and e.data.get("step") == index for e in run.events)
        delegated = step.agent_id != MANAGER
        known = self.artifacts(run)
        tags = tuple(known.get("task_spec", {}).get("tags", ()))
        agent = self.orchestrator.agents.get(step.agent_id)
        composed = self.skills.compose(agent, tags, step.only_skills)

        if run.stage != step.stage:
            run.transition(step.stage, f"{step.agent_id} assigned")
        if delegated and not resumed:
            run.append_event("handoff.requested", {"from": MANAGER, "to": step.agent_id, "task": step.task})
        run.append_event("agent.started", {
            "agent_id": step.agent_id, "step": index, "skills": list(composed.skills),
            "references": list(composed.references), "prompt_tokens_est": composed.tokens_est,
        })
        store.save(run)

        system_prompt = f"{composed.text}\n\n{REPLY_FORMAT}"
        if step.artifact:
            system_prompt += f"\nThe `artifact` is a {step.artifact} with these fields (`?` = optional):\n{self.schemas.describe(step.artifact)}\n"
        existing = {f["path"] for f in module_files(Path(run.module_path))} if run.kind == "feature" and run.module_path else None
        prefix = environment_note() if agent.id in ("researcher", "builder") else ""
        messages = [{"role": "user", "content": prefix + self._feature_note(run, existing) + self._context(run, step, resumed, known)}]
        usage: dict = {}
        started = time.monotonic()
        attempts = 0
        while True:
            attempts += 1
            request = ModelRequest(run_id, agent.id, system_prompt, tuple(messages), metadata={"json": True, "tier": agent.tier, "key": step.artifact, "project_id": run.project_id})
            response = self.providers[self._provider_id(run)].generate(request)
            _add_usage(usage, response.usage)
            reply = parse_agent_reply(response)
            question = reply["question"] if step.may_ask and not resumed else None
            if question or not step.artifact:
                break
            errors = self._validate(step, reply["artifact"], known, existing)
            if not errors:
                break
            self._emit(run_id, "artifact.rejected", {"agent_id": agent.id, "name": step.artifact, "attempt": attempts, "errors": errors[:8]})
            if attempts >= 2:
                raise ArtifactRejected(f"{step.artifact} rejected after repair: {'; '.join(errors[:3])}")
            messages += [
                {"role": "assistant", "content": response.text},
                {"role": "user", "content": "The artifact failed these checks. Return the full corrected JSON object.\n- " + "\n- ".join(errors[:8])},
            ]
        latency_ms = int((time.monotonic() - started) * 1000)

        text = reply["message"] + (f"\n\n{question}" if question else "")
        if step.artifact == "project_plan":
            text += "\n\n" + checks.render_plan(known["task_spec"], reply["artifact"])
        run = store.get(run_id)
        run.append_message(Message.create("agent", text, agent_id=agent.id))
        run.append_event("agent.completed", {"agent_id": agent.id, "step": index, "artifact": step.artifact, "latency_ms": latency_ms, "usage": usage, "attempts": attempts})
        if question:
            run.append_event("question.asked", {"agent_id": agent.id, "step": index, "question": question})
            run.status = RunStatus.AWAITING_USER
            run.append_event("workflow.paused", {"step": index, "agent_id": agent.id})
            store.save(run)
            return True
        if step.artifact:
            path = Path(run.workspace_path) / "artifacts" / f"{step.artifact}.json"
            path.write_text(json.dumps(reply["artifact"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            run.append_event("artifact.accepted", {"agent_id": agent.id, "name": step.artifact, "step": index,
                                                   "path": f"artifacts/{step.artifact}.json", "summary": reply["summary"], "artifact": reply["artifact"]})
        if step.artifact == "project_plan":
            run.append_event("plan.ready", {"plan": reply["artifact"], "built": False})
        if delegated:
            run.append_event("handoff.returned", {"from": agent.id, "to": MANAGER, "summary": reply["summary"]})
        store.save(run)
        return False

    # -- helpers -----------------------------------------------------------

    def _emit(self, run_id: str, event_type: str, data: dict) -> None:
        run = self.orchestrator.store.get(run_id)
        run.append_event(event_type, data)
        self.orchestrator.store.save(run)

    def _validate(self, step: Step, artifact, known: dict[str, dict], existing: set[str] | None = None) -> list[str]:
        if not isinstance(artifact, dict):
            return [f"artifact: a {step.artifact} object is required"]
        errors = self.schemas.validate(step.artifact, artifact)
        if errors:
            return errors
        task, brief = known.get("task_spec"), known.get("research_brief")
        if step.artifact == "research_brief":
            return checks.check_research(task, artifact)
        if step.artifact == "design_spec":
            return checks.check_design(task, brief, artifact, existing)
        if step.artifact == "test_plan":
            return checks.check_test_plan(task, brief, artifact)
        if step.artifact == "project_plan":
            return checks.check_plan(task, brief, artifact)
        return []

    def _feature_note(self, run: RunRecord, existing: set[str] | None) -> str:
        """Tells every planning agent that this run extends a working module instead of starting one."""
        if existing is None:
            return ""
        earlier = [r.goal for r in self.orchestrator.store.list()
                   if r.project_id == run.project_id and r.id != run.id and any(e.type == "build.completed" for e in r.events)]
        listing = "\n".join(f"- {path}" for path in sorted(existing)[:80])
        history = "\n".join(f"- {goal[:160]}" for goal in reversed(earlier)) or "- (the first build)"
        return ("This run adds a NEW FEATURE to an existing, working module. Scope, research and design only the addition: reuse "
                "the existing code and its conventions, do not redesign or rebuild what exists, and list in the design only files "
                f"you add or change.\nExisting module files:\n{listing}\nWhat was built before:\n{history}\n\n")

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
    def _context(run: RunRecord, step: Step, resumed: bool, known: dict[str, dict]) -> str:
        users = [m.content for m in run.messages if m.role == "user"]
        parts = [f"Goal: {run.goal}", "User messages:\n" + "\n".join(f"- {text}" for text in users)]
        for name in step.needs:
            artifact = condense(name, known[name]) if step.digest else known[name]
            parts.append(f"{name} (accepted):\n{json.dumps(artifact, separators=(',', ':'))}")
        parts.append(f"Your task: {step.task}")
        if step.may_ask:
            parts.append("The user has answered your question; do not ask another. Set question to null and return the artifact." if resumed
                         else f"Ask the user exactly one question (and set artifact to null) only if {step.ask_about or 'one decision would materially change the data source, required output or an acceptance criterion'}. Give the reason and your recommended answer in the question. Otherwise set question to null and return the artifact.")
        else:
            parts.append("Set question to null.")
        parts.append("Reply with the JSON object described in your instructions.")
        return "\n\n".join(parts)
