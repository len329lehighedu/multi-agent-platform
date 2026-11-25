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
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock, Thread

from . import artifacts as checks
from . import reports
from .domain import Message, RunRecord, RunStage, RunStatus
from .environment import environment_note
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
PROPOSAL_FORMAT = """
Criterion check: tests tied to an acceptance criterion still fail after a repair. Decide honestly, from the real output, whether the
code is wrong (verdict "code_bug") or the code is right and the threshold cannot be reached for this data and method (verdict
"threshold"). Choose "threshold" only with a scientific reason, never to make a test pass. Reply with one JSON object and nothing else:
{"message": "at most 60 words", "question": null, "handoff_summary": "at most 30 words", "artifact": <criterion proposal described below>}
`measured` must be the value exactly as it appears in the test output. `current` is the threshold now; `proposed` a reachable one with margin.
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

    # -- manual edits ------------------------------------------------------

    def save_file(self, run_id: str, path: str, content: str, author: str = "developer") -> dict:
        """A developer's edit: same path/suffix/size rules as the Builder, snapshotted, then checked like a build."""
        if not isinstance(content, str):
            raise ValueError("content must be text")
        if not checks.safe_relative_path(path):
            raise ValueError("invalid file path")
        if Path(path).suffix not in checks.ALLOWED_SUFFIXES:
            raise ValueError(f"file type not allowed (use {', '.join(sorted(checks.ALLOWED_SUFFIXES))})")
        if len(content) > checks.MAX_FILE_CHARS:
            raise ValueError("file too large")
        run = self.store.get(run_id)
        module = self.module_dir(run)
        if not module.is_dir():
            raise ValueError("this run has no module yet")
        self._claim_project(run)  # one writer per project: refuses while an agent is writing
        try:
            target = module / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            commit = self._commit(module, f"manual edit: {path}")
            result = self._run_checks(module)
            run = self.store.get(run_id)
            run.append_event("file.edited", {"path": path, "by": author, "commit": commit, "checks_passed": result["passed"]})
            self.store.save(run)
            return {"saved": True, "path": path, "commit": commit, "checks": result}
        finally:
            self._release_project(run.project_id)

    def revert_edit(self, run_id: str, commit: str) -> dict:
        """Undo the last manual edit (only when it is still the newest snapshot, so nothing else is lost)."""
        run = self.store.get(run_id)
        module = self.module_dir(run)
        self._claim_project(run)
        try:
            git = ["git", "-c", "user.name=Module Foundry", "-c", "user.email=foundry@localhost"]
            head = subprocess.run(["git", "log", "-1", "--format=%h %s"], cwd=module, capture_output=True, text=True, timeout=30).stdout.strip()
            short, _, subject = head.partition(" ")
            if not subject.startswith("manual edit:") or not (commit and (short.startswith(commit) or commit.startswith(short))):
                raise ValueError("only the latest manual edit can be reverted")
            done = subprocess.run([*git, "revert", "--no-edit", "HEAD"], cwd=module, capture_output=True, text=True, timeout=30)
            if done.returncode != 0:
                raise ValueError("could not revert the edit")
            result = self._run_checks(module)
            run = self.store.get(run_id)
            run.append_event("file.edit_reverted", {"commit": commit, "checks_passed": result["passed"]})
            self.store.save(run)
            return {"reverted": True, "checks": result}
        finally:
            self._release_project(run.project_id)

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
        checks_result, file_set = self._check_and_repair(run_id, module, known, file_set, label, allow_question=True)
        if checks_result.get("question"):
            self._ask_criterion(run_id, checks_result["question"], label)
            return
        self._finish_build(run_id, module, known, checks_result, feature, backup)

    def _finish_build(self, run_id: str, module: Path, known: dict, checks_result: dict, feature: bool, backup: Path | None) -> None:
        if not checks_result["passed"]:
            if backup:
                self._restore(self.store.get(run_id), backup, "failed feature")
            self._finish_failed(run_id, "The feature could not be made to pass the tests after repair attempts, so the module was restored to its previous version. Describe the feature more specifically or start a new feature." if feature
                                else "The module could not be made to pass its own tests after repair attempts. The files are kept in the workspace; ask the Builder to fix a specific problem, or start a new run.",
                                rolled_back=feature)
            return
        files = [f["path"] for f in self.list_files(self.store.get(run_id))]
        qa = self._verify(run_id, known, checks_result, files)
        run = self.store.get(run_id)
        version = self._version(run)
        text = checks.render_build_summary(known["task_spec"], qa, files, checks_result, version)
        amended = self._amendments(run)
        if amended:
            text += "\n\nCriteria you changed during this build:\n" + "\n".join(f"- {a['criterion_id']}: {a['current']} -> {a['proposed']} (measured {a['measured']})" for a in amended)
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

    def _check_and_repair(self, run_id: str, module: Path, known: dict, file_set: dict, label: str,
                          allow_question: bool = False) -> tuple[dict, dict]:
        self._stage(run_id, RunStage.QA, f"{label}: running tests")
        result = self._run_checks(module)
        asked = False
        for round_number in range(0, MAX_REPAIRS + 1):
            self._emit(run_id, "build.checks", {"label": label, "round": round_number, **result})
            if result["passed"]:
                break
            # After at least one honest repair, a failure that is only a criterion threshold goes to the human.
            if allow_question and not asked and round_number >= 1 and not self._asked_before(run_id):
                asked = True
                proposal = self._criterion_proposal(run_id, module, known, result)
                if proposal:
                    return {**result, "question": proposal}, file_set
            if round_number == MAX_REPAIRS:
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

    # -- criterion questions ------------------------------------------------

    @staticmethod
    def criterion_failures(output: str, task_spec: dict) -> list[str]:
        """Criterion IDs behind the failing tests, or [] when any failure is a crash or an unnamed test."""
        failed, errored = reports.failing_tests(output)
        if errored or not failed or "failed to load as a Bokeh app" in output:
            return []
        ids = checks.criterion_ids(task_spec)
        found: set[str] = set()
        for name in failed:
            matched = [cid for cid in ids if re.search(rf"(^|_){re.escape(cid.lower())}(_|$)", name.lower())]
            if not matched:
                return []
            found.update(matched)
        return sorted(found)

    def _asked_before(self, run_id: str) -> bool:
        return any(e.type == "criterion.question" for e in self.store.get(run_id).events)

    def _criterion_proposal(self, run_id: str, module: Path, known: dict, result: dict) -> dict | None:
        ids = self.criterion_failures(result["output"], known["task_spec"])
        if not ids:
            return None
        run = self.store.get(run_id)
        statements = {c["id"]: c["statement"] for c in known["task_spec"].get("acceptance_criteria", [])}
        agent = self.w.orchestrator.agents.get("builder")
        composed = self.w.skills.compose(agent, tuple(known.get("task_spec", {}).get("tags", ())))
        system = f"{composed.text}\n\n{PROPOSAL_FORMAT}\nThe `artifact` has these fields (`?` = optional):\n{self.w.schemas.describe('criterion_proposal')}\n"
        existing = {f["path"] for f in self.list_files(run)}
        context = "\n\n".join([
            "Failing acceptance criteria:\n" + "\n".join(f"- {cid}: {statements.get(cid, '')}" for cid in ids),
            f"Real test output (tail):\n{result['output']}",
            "Relevant files:\n" + self._files_block(module, existing, only_in=result["output"]),
            "Reply with the JSON object described in your instructions.",
        ])
        self._emit(run_id, "agent.started", {"agent_id": "builder", "step": "criterion check", "skills": list(composed.skills),
                                             "references": list(composed.references), "prompt_tokens_est": composed.tokens_est})
        started = time.monotonic()
        try:
            response = self.w.providers[self.w._provider_id(run)].generate(ModelRequest(
                run_id, "builder", system, ({"role": "user", "content": context},),
                metadata={"json": True, "tier": agent.tier, "key": "criterion_proposal", "project_id": run.project_id}))
            reply = parse_agent_reply(response)
        except Exception as error:  # a failed proposal only means: keep repairing as before
            self._emit(run_id, "criterion.checked", {"verdict": "unavailable", "error": str(error)[:200]})
            return None
        self._emit(run_id, "agent.completed", {"agent_id": "builder", "step": "criterion check", "usage": response.usage,
                                               "latency_ms": int((time.monotonic() - started) * 1000), "attempts": 1})
        proposal = reply.get("artifact")
        errors = ["artifact: an object is required"] if not isinstance(proposal, dict) else self.w.schemas.validate("criterion_proposal", proposal)
        if not errors:
            errors = checks.check_criterion_proposal(proposal, ids, result["output"])
        verdict = proposal.get("verdict") if isinstance(proposal, dict) else None
        self._emit(run_id, "criterion.checked", {"verdict": verdict, "errors": errors[:4], "criteria": ids})
        if errors or verdict != "threshold":
            return None
        return {**proposal, "statement": statements.get(proposal["criterion_id"], "")}

    def _ask_criterion(self, run_id: str, proposal: dict, label: str) -> None:
        run = self.store.get(run_id)
        text = (f"The tests for {proposal['criterion_id']} still fail after a repair, and the Builder thinks the threshold, not the code, is the problem.\n\n"
                f"Criterion: {proposal['statement']}\nMeasured: {proposal['measured']}\n"
                f"Current threshold: {proposal.get('current') or '(see the criterion)'}\nProposed: {proposal.get('proposed') or '(no proposal)'}\n"
                f"Why: {proposal['reason']}\n\nAccept the new threshold, keep it and let the Builder try again, or stop the build.")
        run.append_message(Message.create("agent", text, agent_id=MANAGER))
        run.append_event("criterion.question", {**{k: proposal.get(k) for k in ("criterion_id", "statement", "measured", "current", "proposed", "reason")}, "label": label})
        run.status = RunStatus.AWAITING_USER
        self.store.save(run)

    def pending_criterion(self, run: RunRecord) -> dict | None:
        if run.status != RunStatus.AWAITING_USER:
            return None
        for event in reversed(run.events):
            if event.type == "criterion.answered":
                return None
            if event.type == "criterion.question":
                return event.data
        return None

    def answer_criterion(self, run_id: str, decision: str, note: str = "") -> RunRecord:
        if decision not in ("accept", "keep", "stop"):
            raise ValueError("decision must be accept, keep or stop")
        self.w.claim(run_id)
        claimed = False
        try:
            run = self.store.get(run_id)
            question = self.pending_criterion(run)
            if not question:
                raise ValueError("there is no criterion question waiting for an answer")
            self._claim_project(run)
            claimed = True
            words = {"accept": f"Accept {question['criterion_id']}: {question.get('proposed')}", "keep": f"Keep {question['criterion_id']} as it is and fix the code",
                     "stop": "Stop the build"}[decision]
            run.append_message(Message.create("user", words + (f". {note}" if note else ""), target_agent="builder"))
            run.append_event("criterion.answered", {"decision": decision, "criterion_id": question["criterion_id"], "by": run.created_by})
            run.status = RunStatus.ACTIVE
            self.store.save(run)
            Thread(target=self._guarded, args=(run_id, self._resume_after_criterion, (decision, question)), daemon=True).start()
        except Exception:
            self.w.release(run_id)
            if claimed:
                self._release_project(run.project_id)
            raise
        return run

    def _resume_after_criterion(self, run_id: str, decision: str, question: dict) -> None:
        run = self.store.get(run_id)
        known = self.w.artifacts(run)
        module = self.module_dir(run)
        feature = run.kind == "feature"
        backup = Path(run.workspace_path) / ".backup"
        backup = backup if feature and backup.exists() else None
        label = question.get("label") or ("feature" if feature else "build")
        if decision == "stop":
            self._finish_build(run_id, module, known, {"passed": False}, feature, backup)
            return
        if decision == "accept":
            existing = {f["path"] for f in self.list_files(run)}
            context = (f"The user approved a changed acceptance threshold for {question['criterion_id']} ({question['statement']}).\n"
                       f"Measured: {question['measured']}. Change the threshold from {question.get('current')} to {question.get('proposed')}.\n\n"
                       "Test files:\n" + self._files_block(module, {p for p in existing if p.startswith("tests/")}, only_in=question["criterion_id"].lower())
                       + "\n\nYour task: edit only the assertion(s) for this criterion so they check the approved threshold. Change nothing else. Return only the files you change (complete content). Reply with the JSON object described in your instructions.")
            fix = self._call_builder(run_id, f"{label}: amend {question['criterion_id']}", context, known, initial=False, existing=existing, kind="amend")
            self._apply(run_id, module, fix, f"{label}: amend {question['criterion_id']}")
            self._emit(run_id, "criterion.amended", {k: question.get(k) for k in ("criterion_id", "measured", "current", "proposed")})
        else:
            self._emit(run_id, "criterion.kept", {"criterion_id": question["criterion_id"]})
        result, _ = self._check_and_repair(run_id, module, known, {"files": [], "notes": ""}, label, allow_question=False)
        self._finish_build(run_id, module, known, result, feature, backup)

    @staticmethod
    def _amendments(run: RunRecord) -> list[dict]:
        return [e.data for e in run.events if e.type == "criterion.amended"]

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
            *(["Thresholds the user approved during this build (judge against these):\n" + "\n".join(f"- {a['criterion_id']}: {a['current']} -> {a['proposed']}" for a in self._amendments(run))] if self._amendments(run) else []),
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
        counts = {}
        for result in artifact["results"]:
            counts[result["status"]] = counts.get(result["status"], 0) + 1
        run.append_event("handoff.returned", {"from": "tester", "to": MANAGER,
                                              "summary": f"Verdict: {artifact['verdict'].replace('_', ' ')} ({', '.join(f'{n} {s.replace(chr(95), chr(32))}' for s, n in sorted(counts.items()))})."})
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
        parts = [environment_note().strip(), f"Goal: {run.goal}", "task_spec (accepted):\n" + json.dumps(known["task_spec"], separators=(",", ":"))]
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
