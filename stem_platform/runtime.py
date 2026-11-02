"""Serve independently authored lesson packages through Flask and Bokeh."""

import importlib.util
import json
from pathlib import Path
import re
import signal
import sys
import threading

from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.embed import server_document
from bokeh.server.server import Server
from flask import Flask, abort, redirect, render_template, url_for
from tornado.ioloop import IOLoop
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parents[1]


def module_metadata(root, module_id):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", module_id):
        raise ValueError("Module ID must use lowercase letters, digits and hyphens")
    directory = root / "modules" / module_id
    if not (directory / "module.json").is_file():
        raise ValueError(f"Module not found: {module_id}")
    metadata = json.loads((directory / "module.json").read_text())
    for key in ("title", "subtitle"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"{module_id}: {key} must be a nonempty string")
    presentation = metadata.get("presentation", "lesson")
    if presentation not in {"lesson", "dashboard"}:
        raise ValueError(f"{module_id}: presentation must be lesson or dashboard")
    for key in ("objectives", "assumptions"):
        value = metadata.get(key, [])
        if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
            raise ValueError(f"{module_id}: {key} must be a string list")
        if presentation == "lesson" and not value:
            raise ValueError(f"{module_id}: {key} must be a nonempty string list")
    instructions = metadata.get("instructions")
    if not isinstance(instructions, list) or not instructions or not all(
            isinstance(item, str) and item.strip() for item in instructions):
        raise ValueError(f"{module_id}: instructions must be a nonempty string list")
    questions = metadata.get("questions")
    minimum_questions = 3 if presentation == "lesson" else 0
    if not isinstance(questions, list) or len(questions) < minimum_questions:
        raise ValueError(f"{module_id}: supply at least three questions with feedback")
    for item in questions:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip() for k in ("question", "answer")):
            raise ValueError(f"{module_id}: each question needs text and an answer")
    return {**metadata, "id": module_id}


def discover_modules(root=ROOT):
    return [module_metadata(root, p.parent.name) for p in sorted((root / "modules").glob("*/module.json"))]


def load_document_builder(root, module_id):
    module_metadata(root, module_id)
    directory = root / "modules" / module_id
    package_name = "_stem_" + module_id.replace("-", "_")
    package_spec = importlib.util.spec_from_file_location(
        package_name, directory / "__init__.py", submodule_search_locations=[str(directory)])
    if package_spec is None or package_spec.loader is None:
        raise ValueError(f"Cannot load module package: {module_id}")
    package = importlib.util.module_from_spec(package_spec)
    # Give each independently loaded module an isolated package namespace.
    for key in list(sys.modules):
        if key == package_name or key.startswith(package_name + "."):
            del sys.modules[key]
    sys.modules[package_name] = package
    package_spec.loader.exec_module(package)
    ui = __import__(package_name + ".ui", fromlist=["build_document"])
    if not callable(getattr(ui, "build_document", None)):
        raise ValueError(f"{module_id}: ui.py must export build_document(doc)")
    return ui.build_document


def create_app(root=ROOT, bokeh_base="http://127.0.0.1:5006", module_ids=None):
    root = Path(root)
    available = discover_modules(root)
    if module_ids is not None:
        available = [module_metadata(root, name) for name in module_ids]
    by_id = {module["id"]: module for module in available}
    app = Flask(__name__, template_folder=str(root / "web/templates"), static_folder=str(root / "web/static"))

    @app.get("/")
    def index():
        if len(available) == 1 and available[0].get("presentation") == "dashboard":
            return redirect(url_for("lesson", module_id=available[0]["id"]))
        return render_template("index.html", modules=available)

    @app.get("/modules/<module_id>/")
    def lesson(module_id):
        if module_id not in by_id:
            abort(404)
        module = by_id[module_id]
        template = "dashboard.html" if module.get("presentation") == "dashboard" else "lesson.html"
        return render_template(template, module=module,
                               script=server_document(f"{bokeh_base}/lesson/{module_id}"))

    @app.get("/health")
    def health():
        return {"status": "ok", "modules": list(by_id)}

    @app.get("/favicon.ico")
    def favicon():
        return "", 204

    return app


def serve(root=ROOT, port=8080, bokeh_port=5006, module_ids=None):
    """Local development host: one process owns two endpoints and their cleanup."""
    if port == bokeh_port or not all(1024 <= p <= 65535 for p in (port, bokeh_port)):
        raise ValueError("Use different ports between 1024 and 65535")
    root = Path(root)
    selected = module_ids or [m["id"] for m in discover_modules(root)]
    if not selected:
        raise ValueError("No modules found; create one with scripts/create_module.py")
    applications = {
        f"/lesson/{name}": Application(FunctionHandler(load_document_builder(root, name)))
        for name in selected
    }
    app = create_app(root, f"http://127.0.0.1:{bokeh_port}", selected)
    web = make_server("127.0.0.1", port, app, threaded=True)
    loop = IOLoop.current()
    try:
        server = Server(applications, io_loop=loop, address="127.0.0.1", port=bokeh_port,
                        allow_websocket_origin=[f"127.0.0.1:{port}", f"localhost:{port}"])
    except Exception:
        web.server_close()
        raise
    thread = threading.Thread(target=web.serve_forever, name="lesson-web", daemon=True)
    previous = {}
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, lambda *_: loop.add_callback_from_signal(loop.stop))
        server.start()
        thread.start()
        loop.add_callback(lambda: print(f"READY http://127.0.0.1:{port}/ (Bokeh {bokeh_port})", flush=True))
        loop.start()
    finally:
        server.unlisten()
        server.stop(wait=False)
        if thread.is_alive():
            web.shutdown()
            thread.join(timeout=5)
        web.server_close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        print("STOPPED: web and Bokeh endpoints closed", flush=True)
