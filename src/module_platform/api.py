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
from .store import JsonRunStore, RunNotFound
from .workspaces import WorkspaceManager
from .domain import RunStatus
from .providers import OpenAIProvider, ReplayProvider
from .workflow import PlanningWorkflow


def create_app(project_root: Path | None = None, data_root: Path | None = None, providers: dict | None = None, stream_poll: float = 0.25) -> Flask:
    root = Path(project_root or Path(__file__).resolve().parents[2])
    from dotenv import load_dotenv
    load_dotenv(root / ".env")
    data = Path(data_root or os.environ.get("MODULE_FOUNDRY_DATA", root / "var"))
    orchestrator = Orchestrator(
        JsonRunStore(data / "runs"),
        AgentCatalog.load(root / "config" / "agents"),
        WorkspaceManager(data / "workspaces"),
    )
    if providers is None:
        providers = {"replay": ReplayProvider(root / "config" / "replay" / "demo.json", delay=float(os.environ.get("REPLAY_DELAY", "1.2")))}
        if os.environ.get("OPENAI_API_KEY"):
            providers["openai"] = OpenAIProvider()
    default_provider = os.environ.get("MODULE_FOUNDRY_PROVIDER") or ("openai" if "openai" in providers else "replay")
    if default_provider not in providers:
        default_provider = next(iter(providers))
    workflow = PlanningWorkflow(orchestrator, providers, default_provider)
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
        return jsonify(items=orchestrator.agents.public_definitions())

    @app.post("/api/v1/runs")
    def create_run():
        payload = json_object()
        provider = payload.get("provider") or default_provider
        if provider not in providers:
            raise ValueError(f"provider is not available: {provider}")
        run = orchestrator.create_run(str(payload.get("goal", "")), str(payload.get("created_by", "local-user")), provider)
        return jsonify(run.to_dict()), 201

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
        run = workflow.submit(run_id, str(payload.get("content", "")))
        return jsonify(run.to_dict()), 202

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
