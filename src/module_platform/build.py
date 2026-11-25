"""Build and revision phases that follow an approved plan.

The Builder returns whole files as a schema-validated `file_set`; the orchestrator
writes them into the run's module workspace, runs the module's own tests as a
subprocess (deterministic, no model tokens) and feeds real failure output back for
at most two repair rounds. The Tester then reports evidence per planned test case.
After a successful build the user can request changes; each revision is applied
and re-checked, and rolled back if it cannot be made to pass.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock, Thread

from . import artifacts as checks
from .domain import Message, RunRecord, RunStage, RunStatus
from .providers.base import ModelRequest
from .workspaces import module_files
from .workflow import MANAGER, ArtifactRejected, PlanningWorkflow, _add_usage, condense, parse_agent_reply

MAX_REPAIRS = 2
CHECK_TIMEOUT = 180
OUTPUT_TAIL = 3500

BUILD_FORMAT = """
Build mode: you write real files. Reply with one JSON object and nothing else:
{"message": "at most 80 words: what you wrote or changed. Never claim it works; the orchestrator runs the tests and reports results", "question": null, "handoff_summary": "at most 40 words", "artifact": <file_set described below>}
Every file is complete (never a diff or a fragment). Paths are relative to the module root.
"""
QA_FORMAT = """
Verification mode: you cannot run anything yourself. The orchestrator already ran the module's automated tests; their real output is in your context. Reply with one JSON object and nothing else:
{"message": "at most 80 words", "question": null, "handoff_summary": "at most 40 words", "artifact": <qa_report described below>}
Report one result per test_plan case. Mark a case passed only when the test output supports it; a case the automated tests do not exercise (browser, oracle) is not_run with the reason as evidence. Never invent evidence.
"""


APP_LOAD_CHECK = """
import sys
from bokeh.application import Application
from bokeh.application.handlers.directory import DirectoryHandler
handler = DirectoryHandler(filename=sys.argv[1])
Application(handler).create_document()
if handler.failed:
    print("The module's main.py failed to load as a Bokeh app: " + str(handler.error))
    print((handler.error_detail or "")[-1500:])
    sys.exit(1)
"""


class ModuleBuilder:
    def __init__(self, workflow: PlanningWorkflow):
        self.w = workflow
        self.store = workflow.orchestrator.store
        self._guard = Lock()
        self._writing: set[str] = set()

    # -- public entry points ----------------------------------------------

    def approve(self, run_id: str) -> RunRecord:
        self.w.claim(run_id)
        claimed = False
        try:
            run = self.store.get(run_id)
            types = [e.type for e in run.events]
            if "plan.ready" not in types:
                raise ValueError("there is no plan to approve yet")
            if "plan.approved" in types:
                raise ValueError("the plan is already approved")
            if run.status != RunStatus.READY_FOR_REVIEW:
                raise ValueError("the plan can only be approved when the run is waiting for review")
            if run.kind == "module" and self.list_files(run):
                raise ValueError("this project already has a module: start a new feature instead")
            self._claim_project(run)
            claimed = True
            run.append_event("plan.approved", {"by": run.created_by})
            run.status = RunStatus.ACTIVE
            self.store.save(run)
            Thread(target=self._guarded, args=(run_id, self._build, None), daemon=True).start()
        except Exception:
            self.w.release(run_id)
            if claimed:
                self._release_project(run.project_id)
            raise
        return run

    def can_retry(self, run: RunRecord) -> bool:
        """A build that stopped while the Builder was writing (a provider error) can be run again from the approved plan."""
        types = [e.type for e in run.events]
        return (run.status == RunStatus.FAILED and "plan.approved" in types and run.stage == RunStage.BUILDING
                and "build.completed" not in types and "build.failed" not in types)

    def retry(self, run_id: str) -> RunRecord:
        self.w.claim(run_id)
        claimed = False
        try:
            run = self.store.get(run_id)
            if not self.can_retry(run):
                raise ValueError("only a build that stopped while the Builder was writing can be retried")
            self._claim_project(run)
            claimed = True
            run.append_event("build.retried", {"by": run.created_by})
            run.status = RunStatus.ACTIVE
            self.store.save(run)
            Thread(target=self._guarded, args=(run_id, self._build, None), daemon=True).start()
        except Exception:
            self.w.release(run_id)
            if claimed:
                self._release_project(run.project_id)
            raise
        return run

    def revise(self, run_id: str, content: str) -> RunRecord:
        content = content.strip()
        if not content:
            raise ValueError("content is required")
        self.w.claim(run_id)
        claimed = False
        try:
            run = self.store.get(run_id)
            if not self.has_build(run):
                raise ValueError("there is no built module to change yet")
            self._claim_project(run)
            claimed = True
            number = sum(e.type == "revision.requested" for e in run.events) + 1
            run.append_message(Message.create("user", content, target_agent="builder"))
            run.append_event("revision.requested", {"number": number, "request": content})
            run.status = RunStatus.ACTIVE
            self.store.save(run)
            Thread(target=self._guarded, args=(run_id, self._revise, (number, content)), daemon=True).start()
        except Exception:
            self.w.release(run_id)
            if claimed:
                self._release_project(run.project_id)
            raise
        return run

    def has_build(self, run: RunRecord) -> bool:
        return any(e.type == "build.completed" or (e.type == "build.failed" and not e.data.get("rolled_back")) for e in run.events)

    def module_dir(self, run: RunRecord) -> Path:
        return Path(run.module_path) if run.module_path else Path(run.workspace_path) / "module"

    def list_files(self, run: RunRecord) -> list[dict]:
        return module_files(self.module_dir(run))

    def _claim_project(self, run: RunRecord) -> None:
        """Runs of one project share one module, so only one may write to it at a time."""
        if not run.project_id:
            return
        with self._guard:
            if run.project_id in self._writing:
                raise ValueError("another run in this project is working on the module; wait for it to finish")
            self._writing.add(run.project_id)

    def _release_project(self, project_id: str | None) -> None:
        with self._guard:
            self._writing.discard(project_id)

    def _version(self, run: RunRecord) -> str:
        built = sum(1 for other in self.store.list()
                    if other.id != run.id and other.project_id == run.project_id and any(e.type == "build.completed" for e in other.events))
        return f"v{built + 1}"

    # -- orchestration -----------------------------------------------------

    def _guarded(self, run_id: str, target, args) -> None:
        agent_id = "builder"
        try:
            target(run_id, *(args if args is not None else ()))
        except Exception as error:
            run = self.store.get(run_id)
            run.status = RunStatus.FAILED
            run.append_event("agent.failed", {"agent_id": agent_id, "error": str(error)[:400]})
            self.store.save(run)
        finally:
            self._release_project(self.store.get(run_id).project_id)
            self.w.release(run_id)

    def _build(self, run_id: str) -> None:
        run = self.store.get(run_id)
        feature = run.kind == "feature"
        label = "feature" if feature else "build"
        module = self.module_dir(run)
        backup = self._backup(run) if feature else None
        try:
            self._build_files(run_id, run, feature, label, module, backup)
        except Exception:
            if backup:
                self._restore(run, backup, "failed feature")
            raise

    def _build_files(self, run_id: str, run: RunRecord, feature: bool, label: str, module: Path, backup: Path | None) -> None:
        known = self.w.artifacts(run)
        self._stage(run_id, RunStage.BUILDING, "plan approved")
        self._handoff(run_id, "builder", "Write the files from the approved design, then the orchestrator will run the tests." if not feature
                      else "Add the approved feature to the existing module, then the orchestrator will run all tests.")
        context = self._design_context(run, known)
        if feature:
            existing = {f["path"] for f in self.list_files(run)}
            context += "\n\nExisting module files (extend them; every existing test must keep passing):\n" + self._context_files(module, existing, known["design_spec"])
            context += "\n\nYour task: write every file listed in design_spec.files (new files, and the complete new content of files you change), integrated with the existing code. Include tests for the new feature. Do not rewrite unrelated files. Reply with the JSON object described in your instructions."
        else:
            context += "\n\nYour task: write every file listed in design_spec.files, complete and consistent with the design and the engine_api. Include the tests named in design_spec so the module's own test suite can run. Reply with the JSON object described in your instructions."
        file_set = self._call_builder(run_id, label, context, known, initial=True)
        self._apply(run_id, module, file_set, label)
        checks_result, file_set = self._check_and_repair(run_id, module, known, file_set, label)
        if not checks_result["passed"]:
            if backup:
                self._restore(run, backup, "failed feature")
            self._finish_failed(run_id, "The feature could not be made to pass the tests after repair attempts, so the module was restored to its previous version. Describe the feature more specifically or start a new feature." if feature
                                else "The module could not be made to pass its own tests after repair attempts. The files are kept in the workspace; ask the Builder to fix a specific problem, or start a new run.",
                                rolled_back=feature)
            return
        files = [f["path"] for f in self.list_files(self.store.get(run_id))]
        qa = self._verify(run_id, known, checks_result, files)
        run = self.store.get(run_id)
        version = self._version(run)
        text = checks.render_build_summary(known["task_spec"], qa, files, checks_result, version)
        run.append_message(Message.create("agent", text, agent_id=MANAGER))
        if run.stage != RunStage.REVIEW:
            run.transition(RunStage.REVIEW, "build verified")
        run.status = RunStatus.READY_FOR_REVIEW
        run.append_event("build.completed", {"version": version, "files": files, "checks_passed": True, "kind": run.kind,
                                              "verdict": qa["verdict"] if qa else None, "module_path": str(module)})
        self.store.save(run)

    def _backup(self, run: RunRecord) -> Path:
        backup = Path(run.workspace_path) / ".backup"
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(self.module_dir(run), backup, ignore=shutil.ignore_patterns("__pycache__", ".git"))
        return backup

    def _restore(self, run: RunRecord, backup: Path, why: str) -> None:
        """Put the module back exactly as it was, keeping its git history."""
        module = self.module_dir(run)
        for child in module.iterdir():
            if child.name == ".git":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        shutil.copytree(backup, module, dirs_exist_ok=True)
        self._commit(module, f"restore: {why}")

    def _revise(self, run_id: str, number: int, request: str) -> None:
        run = self.store.get(run_id)
        known = self.w.artifacts(run)
        module = self.module_dir(run)
        backup = self._backup(run)
        if run.stage == RunStage.REPAIR:  # runs saved before failed builds were parked in review
            self._stage(run_id, RunStage.QA, "settling before the change")
        if self.store.get(run_id).stage == RunStage.QA:
            self._stage(run_id, RunStage.REVIEW, "settling before the change")
        self._stage(run_id, RunStage.BUILDING, f"revision {number}")
        self._handoff(run_id, "builder", f"Revision {number}: {request[:160]}")
        existing = {f["path"] for f in self.list_files(run)}
        context = (self._design_context(run, known, condensed=True) + "\n\nCurrent module files:\n" + self._files_block(module, existing)
                   + f"\n\nChange request from the user:\n{request}\n\nYour task: apply exactly this change with the smallest edit. Return only the files you change or add (complete content) and list removed files in `delete`. Do not alter behaviour the user did not mention; keep the existing tests passing and update a test only if the behaviour it checks was requested to change. Reply with the JSON object described in your instructions.")
        try:
            file_set = self._call_builder(run_id, f"revision {number}", context, known, initial=False, existing=existing, kind="revision")
            self._apply(run_id, module, file_set, f"revision {number}")
            result, file_set = self._check_and_repair(run_id, module, known, file_set, f"revision {number}")
            ok = result["passed"]
        except ArtifactRejected as error:
            ok, file_set, result = False, None, {"output": str(error)}
        run = self.store.get(run_id)
        if not ok:
            self._restore(run, backup, f"revision {number} failed")
            run.append_message(Message.create("agent", f"Revision {number} could not be applied safely, so the module was restored to its previous version. Reason: {str(result.get('output', ''))[-400:].strip()}\nTry describing the change more specifically.", agent_id=MANAGER))
            run.append_event("revision.failed", {"number": number, "rolled_back": True})
        else:
            files = [f["path"] for f in file_set["files"]]
            run.append_message(Message.create("agent", f"Revision {number} applied to {len(files)} file(s): {', '.join(files)}. Automated checks: PASSED. Anything else to change?", agent_id=MANAGER))
            run.append_event("revision.completed", {"number": number, "files": files, "checks_passed": True})
        if run.stage == RunStage.REPAIR:
            run.transition(RunStage.QA, f"revision {number} checks finished")
        if run.stage != RunStage.REVIEW:
            run.transition(RunStage.REVIEW, f"revision {number} finished")
        run.status = RunStatus.READY_FOR_REVIEW
        self.store.save(run)

    # -- steps -------------------------------------------------------------

    def _call_builder(self, run_id: str, label: str, context: str, known: dict, initial: bool, existing: set[str] | None = None,
                      messages: list | None = None, kind: str = "build") -> dict:
        run = self.store.get(run_id)
        agent = self.w.orchestrator.agents.get("builder")
        composed = self.w.skills.compose(agent, tuple(known.get("task_spec", {}).get("tags", ())))
        system = f"{composed.text}\n\n{BUILD_FORMAT}\nThe `artifact` is a file_set with these fields (`?` = optional):\n{self.w.schemas.describe('file_set')}\n"
        design = known["design_spec"] if initial else None
        self._emit(run_id, "agent.started", {"agent_id": "builder", "step": label, "skills": list(composed.skills),
                                             "references": list(composed.references), "prompt_tokens_est": composed.tokens_est})
        msgs = list(messages or [{"role": "user", "content": context}])
        usage: dict = {}
        started = time.monotonic()
        for attempt in (1, 2):
            response = self.w.providers[self.w._provider_id(run)].generate(
                ModelRequest(run_id, "builder", system, tuple(msgs), metadata={"json": True, "tier": agent.tier, "key": f"file_set:{kind}", "project_id": run.project_id}))
            _add_usage(usage, response.usage)
            reply = parse_agent_reply(response)
            errors = self._validate_file_set(reply["artifact"], design, existing)
            if not errors:
                break
            self._emit(run_id, "artifact.rejected", {"agent_id": "builder", "name": "file_set", "attempt": attempt, "errors": errors[:8]})
            if attempt == 2:
                raise ArtifactRejected(f"file_set rejected after repair: {'; '.join(errors[:3])}")
            msgs += [{"role": "assistant", "content": response.text},
                     {"role": "user", "content": "The file_set failed these checks. Return the full corrected JSON object.\n- " + "\n- ".join(errors[:8])}]
        run = self.store.get(run_id)
        run.append_message(Message.create("agent", reply["message"], agent_id="builder"))
        run.append_event("agent.completed", {"agent_id": "builder", "step": label, "latency_ms": int((time.monotonic() - started) * 1000),
                                             "usage": usage, "attempts": attempt})
        run.append_event("handoff.returned", {"from": "builder", "to": MANAGER, "summary": reply["summary"]})
        self.store.save(run)
        return reply["artifact"]

    def _validate_file_set(self, artifact, design, existing) -> list[str]:
        if not isinstance(artifact, dict):
            return ["artifact: a file_set object is required"]
        errors = self.w.schemas.validate("file_set", artifact)
        return errors or checks.check_file_set(artifact, design, existing)

    def _apply(self, run_id: str, module: Path, file_set: dict, label: str) -> None:
        for item in file_set["files"]:
            target = module / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item["content"], encoding="utf-8")
        for path in file_set.get("delete", []):
            (module / path).unlink(missing_ok=True)
        commit = self._commit(module, label)
        self._emit(run_id, "build.files_written", {"label": label, "files": [f["path"] for f in file_set["files"]],
                                                    "deleted": file_set.get("delete", []), "commit": commit, "notes": file_set["notes"]})

    def _check_and_repair(self, run_id: str, module: Path, known: dict, file_set: dict, label: str) -> tuple[dict, dict]:
        self._stage(run_id, RunStage.QA, f"{label}: running tests")
        result = self._run_checks(module)
        for round_number in range(0, MAX_REPAIRS + 1):
            self._emit(run_id, "build.checks", {"label": label, "round": round_number, **result})
            if result["passed"] or round_number == MAX_REPAIRS:
                break
            self._stage(run_id, RunStage.REPAIR, f"{label}: repair round {round_number + 1}")
            existing = {f["path"] for f in self.list_files(self.store.get(run_id))}
            context = (self._design_context(self.store.get(run_id), known, condensed=True)
                       + f"\n\nThe module's automated checks failed. Real output (tail):\n{result['output']}\n\nRelevant files:\n"
                       + self._files_block(module, existing, only_in=result["output"])
                       + "\n\nYour task: fix the cause of the failure with the smallest edit; return only the files you change (complete content). If a test is wrong because it contradicts the design, fix the test, not the engine. Reply with the JSON object described in your instructions.")
            fix = self._call_builder(run_id, f"{label} repair {round_number + 1}", context, known, initial=False, existing=existing, kind="repair")
            self._apply(run_id, module, fix, f"{label} repair {round_number + 1}")
            self._stage(run_id, RunStage.QA, f"{label}: re-running tests")
            result = self._run_checks(module)
            file_set = {"files": file_set["files"] + fix["files"], "notes": fix["notes"]}
        return result, file_set

    def _verify(self, run_id: str, known: dict, result: dict, files: list[str]) -> dict:
        run = self.store.get(run_id)
        self._handoff(run_id, "tester", "Report evidence per test case from the real test output.")
        agent = self.w.orchestrator.agents.get("tester")
        composed = self.w.skills.compose(agent, tuple(known.get("task_spec", {}).get("tags", ())))
        system = f"{composed.text}\n\n{QA_FORMAT}\nThe `artifact` is a qa_report with these fields (`?` = optional):\n{self.w.schemas.describe('qa_report')}\n"
        context = "\n\n".join([
            f"Goal: {run.goal}",
            "task_spec acceptance criteria:\n" + json.dumps(known["task_spec"].get("acceptance_criteria", known["task_spec"]), separators=(",", ":")),
            "test_plan (accepted):\n" + json.dumps(known["test_plan"], separators=(",", ":")),
            "Module files: " + ", ".join(files),
            f"Automated test run: command `{result['command']}` -> {'passed' if result['passed'] else 'failed'}\n{result['output']}",
            "Reply with the JSON object described in your instructions.",
        ])
        self._emit(run_id, "agent.started", {"agent_id": "tester", "step": "verify", "skills": list(composed.skills),
                                             "references": list(composed.references), "prompt_tokens_est": composed.tokens_est})
        msgs = [{"role": "user", "content": context}]
        usage: dict = {}
        started = time.monotonic()
        for attempt in (1, 2):
            response = self.w.providers[self.w._provider_id(run)].generate(
                ModelRequest(run_id, "tester", system, tuple(msgs), metadata={"json": True, "tier": agent.tier, "key": "qa_report", "project_id": run.project_id}))
            _add_usage(usage, response.usage)
            reply = parse_agent_reply(response)
            artifact = reply["artifact"]
            errors = ["artifact: a qa_report object is required"] if not isinstance(artifact, dict) else (
                self.w.schemas.validate("qa_report", artifact) or checks.check_qa(known["test_plan"], artifact))
            if not errors:
                break
            self._emit(run_id, "artifact.rejected", {"agent_id": "tester", "name": "qa_report", "attempt": attempt, "errors": errors[:8]})
            if attempt == 2:
                raise ArtifactRejected(f"qa_report rejected after repair: {'; '.join(errors[:3])}")
            msgs += [{"role": "assistant", "content": response.text},
                     {"role": "user", "content": "The qa_report failed these checks. Return the full corrected JSON object.\n- " + "\n- ".join(errors[:8])}]
        run = self.store.get(run_id)
        run.append_message(Message.create("agent", reply["message"], agent_id="tester"))
        run.append_event("agent.completed", {"agent_id": "tester", "step": "verify", "latency_ms": int((time.monotonic() - started) * 1000),
                                             "usage": usage, "attempts": attempt})
        path = Path(run.workspace_path) / "artifacts" / "qa_report.json"
        path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        run.append_event("artifact.accepted", {"agent_id": "tester", "name": "qa_report", "step": "verify", "path": "artifacts/qa_report.json",
                                               "summary": reply["summary"], "artifact": artifact})
        run.append_event("handoff.returned", {"from": "tester", "to": MANAGER, "summary": reply["summary"]})
        self.store.save(run)
        return artifact

    # -- helpers -----------------------------------------------------------

    def _finish_failed(self, run_id: str, text: str, rolled_back: bool = False) -> None:
        run = self.store.get(run_id)
        run.append_message(Message.create("agent", text, agent_id=MANAGER))
        if not rolled_back:
            # The kept module is now in the developer's hands: park the run in review so a change request can start from there.
            if run.stage == RunStage.REPAIR:
                run.transition(RunStage.QA, "build stopped after repair attempts")
            if run.stage == RunStage.QA:
                run.transition(RunStage.REVIEW, "build failed its tests; module kept for changes")
        run.status = RunStatus.NEEDS_REVIEW
        run.append_event("build.failed", {"reason": text, "rolled_back": rolled_back})
        self.store.save(run)

    def _stage(self, run_id: str, stage: RunStage, reason: str) -> None:
        run = self.store.get(run_id)
        if run.stage != stage:
            run.transition(stage, reason)
            self.store.save(run)

    def _handoff(self, run_id: str, to: str, task: str) -> None:
        self._emit(run_id, "handoff.requested", {"from": MANAGER, "to": to, "task": task})

    def _emit(self, run_id: str, event_type: str, data: dict) -> None:
        self.w._emit(run_id, event_type, data)

    @staticmethod
    def _design_context(run: RunRecord, known: dict, condensed: bool = False) -> str:
        parts = [f"Goal: {run.goal}", "task_spec (accepted):\n" + json.dumps(known["task_spec"], separators=(",", ":"))]
        if condensed:
            parts.append("design_spec (condensed):\n" + json.dumps(condense("design_spec", known["design_spec"]), separators=(",", ":")))
        else:
            parts.append("research_brief (accepted):\n" + json.dumps(known["research_brief"], separators=(",", ":")))
            parts.append("design_spec (accepted):\n" + json.dumps(known["design_spec"], separators=(",", ":")))
        return "\n\n".join(parts)

    @classmethod
    def _context_files(cls, module: Path, existing: set[str], design: dict, limit: int = 120_000) -> str:
        """All existing files, or only the ones the design touches plus tests when the module is large."""
        size = sum((module / p).stat().st_size for p in existing if (module / p).is_file())
        if size <= limit:
            return cls._files_block(module, existing)
        touched = {f["path"] for f in design["files"]}
        chosen = {p for p in existing if p in touched or p.startswith("tests/") or p.startswith("engine/")}
        listing = "\n".join(f"- {p}" for p in sorted(existing - chosen))
        return cls._files_block(module, chosen) + f"\n(Other files not shown, available on request:\n{listing})"

    @staticmethod
    def _files_block(module: Path, paths: set[str], only_in: str | None = None) -> str:
        chosen = sorted(p for p in paths if only_in is None or p in only_in or Path(p).name in only_in) or sorted(paths)
        blocks = []
        for path in chosen:
            file = module / path
            if file.is_file():
                blocks.append(f"--- {path}\n{file.read_text(encoding='utf-8', errors='replace')}")
        return "\n".join(blocks)

    @staticmethod
    def _run_checks(module: Path) -> dict:
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "tests"]
        shown = "python -m unittest discover -s tests"
        started = time.monotonic()
        if not (module / "tests").is_dir():
            return {"passed": False, "command": shown, "output": "tests/ directory is missing", "duration_ms": 0}
        env = {**os.environ, "PYTHONPATH": str(module), "PYTHONDONTWRITEBYTECODE": "1"}
        try:
            done = subprocess.run(command, cwd=module, env=env, capture_output=True, text=True, timeout=CHECK_TIMEOUT)
            output, passed = (done.stdout + done.stderr), done.returncode == 0
            if passed and (module / "main.py").is_file():
                # Unit tests cannot see Bokeh's own checks (callback signatures, bad properties): load the app the way `bokeh serve` does.
                loaded = subprocess.run([sys.executable, "-c", APP_LOAD_CHECK, str(module)], cwd=module, env=env, capture_output=True, text=True, timeout=CHECK_TIMEOUT)
                if loaded.returncode != 0:
                    output, passed = (output + "\n" + loaded.stdout + loaded.stderr), False
                    shown += " + load main.py as a Bokeh app"
        except subprocess.TimeoutExpired:
            output, passed = f"tests timed out after {CHECK_TIMEOUT}s", False
        return {"passed": passed, "command": shown, "output": output.strip()[-OUTPUT_TAIL:], "duration_ms": int((time.monotonic() - started) * 1000)}

    @staticmethod
    def _commit(module: Path, label: str) -> str | None:
        """Snapshot for history; a missing git binary only means no history."""
        git = ["git", "-c", "user.name=Module Foundry", "-c", "user.email=foundry@localhost"]
        try:
            if not (module / ".git").exists():
                subprocess.run(["git", "init", "-q"], cwd=module, check=True, capture_output=True, timeout=30)
            subprocess.run(["git", "add", "-A"], cwd=module, check=True, capture_output=True, timeout=30)
            subprocess.run([*git, "commit", "-q", "-m", label, "--allow-empty"], cwd=module, check=True, capture_output=True, timeout=30)
            return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=module, check=True, capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
