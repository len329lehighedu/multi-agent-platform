"""Thin Flask adapter over the orchestration domain."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from collections.abc import Mapping

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from .agents import AgentCatalog
from .orchestrator import Orchestrator
from .store import JsonProjectStore, JsonRunStore, ProjectNotFound, RunNotFound
from .workspaces import WorkspaceManager, module_files as list_module_files
from .domain import RunStatus
from .providers import AnthropicProvider, OpenAIProvider, ReplayProvider
from .workflow import PlanningWorkflow
from .skills import SkillLibrary
from . import artifacts as checks
from .artifacts import ArtifactSchemas
from .build import ModuleBuilder
from .preview import PreviewManager
from . import reports
from . import board


def create_app(project_root: Path | None = None, data_root: Path | None = None, providers: dict | None = None, stream_poll: float = 0.25, previews: PreviewManager | None = None) -> Flask:
    root = Path(project_root or Path(__file__).resolve().parents[2])
    from dotenv import load_dotenv
    load_dotenv(root / ".env")
    data = Path(data_root or os.environ.get("MODULE_FOUNDRY_DATA", root / "var"))
    orchestrator = Orchestrator(
        JsonRunStore(data / "runs"),
        AgentCatalog.load(root / "config" / "agents"),
        WorkspaceManager(data / "workspaces"),
        JsonProjectStore(data / "projects"),
    )
    if providers is None:
        providers = {"replay": ReplayProvider(root / "config" / "replay" / "demo.json", delay=float(os.environ.get("REPLAY_DELAY", "1.2")))}
        if os.environ.get("OPENAI_API_KEY"):
            providers["openai"] = OpenAIProvider()
        if os.environ.get("CLAUDE_API_KEY"):
            providers["claude"] = AnthropicProvider(ledger_path=data / "spend.json", debug_dir=data / "debug")
    # A paid provider is used only when MODULE_FOUNDRY_PROVIDER names it; the default is the free replay.
    default_provider = os.environ.get("MODULE_FOUNDRY_PROVIDER") or "replay"
    if default_provider not in providers:
        default_provider = next(iter(providers))
    skills = SkillLibrary(root / "config" / "skills")
    skills.validate(orchestrator.agents)
    schemas = ArtifactSchemas.load(root / "config" / "schemas")
    workflow = PlanningWorkflow(orchestrator, providers, default_provider, skills, schemas)
    builder = ModuleBuilder(workflow)
    previews = previews or PreviewManager()
    app = Flask(__name__, template_folder=str(root / "apps" / "web" / "templates"), static_folder=str(root / "apps" / "web" / "static"))

    @app.get("/")
    def home():
        return render_template("index.html")

    def error(code: str, message: str, status: int):
        return jsonify(error={"code": code, "message": message}), status

    def json_object() -> Mapping:
        payload = request.get_json(silent=True)
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    @app.errorhandler(RunNotFound)
    def missing(_exception):
        return error("run_not_found", "run was not found", 404)

    @app.errorhandler(ProjectNotFound)
    def missing_project(_exception):
        return error("project_not_found", "project was not found", 404)

    @app.errorhandler(ValueError)
    def invalid(exception):
        return error("invalid_request", str(exception), 400)

    @app.get("/api/v1/health")
    def health():
        return jsonify(status="ok", service="module-foundry")

    @app.get("/api/v1/config")
    def config():
        return jsonify(providers=[{"id": name} for name in providers], default_provider=default_provider)

    @app.get("/api/v1/agents")
    def agents():
        provider = providers.get(default_provider)
        describe = getattr(provider, "describe", None)
        return jsonify(items=[{**item, **(describe(item["tier"]) if describe else {})} for item in orchestrator.agents.public_definitions()])

    @app.post("/api/v1/runs")
    def create_run():
        payload = json_object()
        provider = payload.get("provider") or default_provider
        if provider not in providers:
            raise ValueError(f"provider is not available: {provider}")
        run = orchestrator.create_run(str(payload.get("goal", "")), str(payload.get("created_by", "local-user")), provider,
                                      payload.get("project_id") or None)
        return jsonify(run.to_dict()), 201

    def run_summary(run):
        return {"id": run.id, "goal": run.goal, "kind": run.kind, "status": run.status.value, "stage": run.stage.value,
                "created_at": run.created_at, "updated_at": run.updated_at,
                "built": board.has_module(run)}

    def project_spend(project_id: str):
        ledger = getattr(providers.get("claude"), "ledger", None)
        return ledger.snapshot()["by_project"].get(project_id, 0.0) if ledger else None

    def project_summary(project):
        runs = [r for r in orchestrator.store.list() if r.project_id == project.id]
        files = len(list_module_files(orchestrator.workspaces.project_module(project.id)))
        state = board.project_state(runs, files, project_spend(project.id))
        return {**project.to_dict(), **state, "runs": [run_summary(r) for r in runs], "run_count": len(runs), "files": files}

    @app.get("/api/v1/runs/<run_id>/report")
    def run_report(run_id: str):
        return jsonify(reports.run_report(orchestrator.store.get(run_id)))

    @app.get("/api/v1/reports")
    def usage_report():
        runs = orchestrator.store.list()
        project_id = request.args.get("project_id")
        if project_id:
            runs = [r for r in runs if r.project_id == project_id]
        return jsonify(reports.aggregate(runs, include_replayed=request.args.get("include_replayed") == "1"))

    @app.get("/api/v1/spend")
    def spend():
        ledger = getattr(providers.get("claude"), "ledger", None)
        return jsonify(spend=ledger.snapshot() if ledger else None)

    @app.get("/api/v1/projects")
    def list_projects():
        return jsonify(items=[project_summary(p) for p in orchestrator.projects.list()])

    @app.post("/api/v1/projects")
    def create_project():
        payload = json_object()
        project = orchestrator.projects.create(str(payload.get("name", "")), str(payload.get("created_by", "local-user")))
        return jsonify(project_summary(project)), 201

    @app.get("/api/v1/projects/<project_id>")
    def get_project(project_id: str):
        return jsonify(project_summary(orchestrator.projects.get(project_id)))

    @app.get("/api/v1/projects/<project_id>/preview")
    def preview_status(project_id: str):
        orchestrator.projects.get(project_id)
        return jsonify(previews.status(project_id, orchestrator.workspaces.project_module(project_id)))

    @app.post("/api/v1/projects/<project_id>/preview")
    def preview_start(project_id: str):
        orchestrator.projects.get(project_id)
        return jsonify(previews.start(project_id, orchestrator.workspaces.project_module(project_id)))

    @app.delete("/api/v1/projects/<project_id>/preview")
    def preview_stop(project_id: str):
        orchestrator.projects.get(project_id)
        previews.stop(project_id)
        return jsonify(stopped=True)

    @app.delete("/api/v1/projects/<project_id>")
    def delete_project(project_id: str):
        previews.stop(project_id)
        return jsonify(deleted=True, runs_removed=orchestrator.delete_project(project_id))

    @app.get("/api/v1/runs")
    def list_runs():
        return jsonify(items=[run.to_dict() for run in orchestrator.store.list()])

    @app.get("/api/v1/runs/<run_id>")
    def get_run(run_id: str):
        return jsonify(orchestrator.store.get(run_id).to_dict())

    @app.post("/api/v1/runs/<run_id>/messages")
    def add_message(run_id: str):
        payload = json_object()
        run = orchestrator.receive_message(run_id, str(payload.get("content", "")), payload.get("target_agent"))
        return jsonify(run.to_dict()), 201

    @app.post("/api/v1/runs/<run_id>/chat")
    def chat(run_id: str):
        payload = json_object()
        content = str(payload.get("content", ""))
        current = orchestrator.store.get(run_id)
        if builder.pending_criterion(current):
            raise ValueError("answer the criterion question first: accept, keep or stop")
        run = builder.revise(run_id, content) if builder.has_build(current) else workflow.submit(run_id, content)
        return jsonify(run.to_dict()), 202

    @app.post("/api/v1/runs/<run_id>/approve")
    def approve(run_id: str):
        return jsonify(builder.approve(run_id).to_dict()), 202

    @app.post("/api/v1/runs/<run_id>/criterion")
    def answer_criterion(run_id: str):
        payload = json_object()
        return jsonify(builder.answer_criterion(run_id, str(payload.get("decision", "")), str(payload.get("note", ""))[:500]).to_dict()), 202

    @app.post("/api/v1/runs/<run_id>/retry")
    def retry(run_id: str):
        return jsonify(builder.retry(run_id).to_dict()), 202

    @app.get("/api/v1/runs/<run_id>/files")
    def module_files(run_id: str):
        return jsonify(items=builder.list_files(orchestrator.store.get(run_id)))

    @app.get("/api/v1/runs/<run_id>/files/<path:file_path>")
    def module_file(run_id: str, file_path: str):
        run = orchestrator.store.get(run_id)
        if not checks.safe_relative_path(file_path):
            raise ValueError("invalid file path")
        target = builder.module_dir(run) / file_path
        if not target.is_file():
            return error("file_not_found", "file was not found", 404)
        return Response(target.read_text(encoding="utf-8", errors="replace"), mimetype="text/plain")

    @app.put("/api/v1/runs/<run_id>/files/<path:file_path>")
    def save_module_file(run_id: str, file_path: str):
        payload = json_object()
        return jsonify(builder.save_file(run_id, file_path, payload.get("content"), str(payload.get("by", "local-user"))))

    @app.post("/api/v1/runs/<run_id>/revert-edit")
    def revert_module_edit(run_id: str):
        return jsonify(builder.revert_edit(run_id, str(json_object().get("commit", ""))))

    @app.get("/api/v1/runs/<run_id>/events")
    def events(run_id: str):
        try:
            after = int(request.args.get("after", 0))
        except ValueError as exception:
            raise ValueError("after must be an integer") from exception
        if after < 0:
            raise ValueError("after must be non-negative")
        run = orchestrator.store.get(run_id)
        return jsonify(items=[event.__dict__ if hasattr(event, "__dict__") else {
            "sequence": event.sequence, "type": event.type, "created_at": event.created_at, "data": event.data
        } for event in run.events if event.sequence > after])

    @app.get("/api/v1/runs/<run_id>/artifacts")
    def run_artifacts(run_id: str):
        return jsonify(workflow.artifacts(orchestrator.store.get(run_id)))

    @app.get("/api/v1/runs/<run_id>/events/stream")
    def event_stream(run_id: str):
        orchestrator.store.get(run_id)
        try:
            cursor = max(int(request.args.get("after", 0)), int(request.headers.get("Last-Event-ID", 0)))
        except ValueError as exception:
            raise ValueError("after must be an integer") from exception

        def generate():
            nonlocal cursor
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline:
                run = orchestrator.store.get(run_id)
                fresh = [event for event in run.events if event.sequence > cursor]
                for event in fresh:
                    cursor = event.sequence
                    yield f"id: {event.sequence}\nevent: run_event\ndata: {json.dumps(asdict(event))}\n\n"
                if run.status != RunStatus.ACTIVE and not fresh:
                    yield "event: end\ndata: {}\n\n"
                    return
                time.sleep(stream_poll)

        return Response(stream_with_context(generate()), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/v1/runs/<run_id>/transitions")
    def transition(run_id: str):
        payload = json_object()
        run = orchestrator.transition(run_id, str(payload.get("stage", "")), str(payload.get("reason", "")))
        return jsonify(run.to_dict())

    return app


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    create_app().run(host="127.0.0.1", port=port, debug=False)
