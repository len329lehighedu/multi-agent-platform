"""Live preview of a project's module.

Generated code never runs inside the platform process: each preview is a `bokeh serve`
subprocess bound to 127.0.0.1 on a free port. The platform only supervises it (start, health
check, log tail, stop). The module's entry file is `main.py` (a Bokeh directory app).
"""

from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from threading import Lock, current_thread, main_thread

LOG_TAIL = 3000
ENTRY = "main.py"


class PreviewManager:
    def __init__(self, python: str | None = None, startup_timeout: float = 25.0, max_running: int = 3):
        self.python = python or sys.executable
        self.startup_timeout = startup_timeout
        self.max_running = max_running
        self._lock = Lock()
        self._items: dict[str, dict] = {}
        self._starting: dict[str, Lock] = {}
        atexit.register(self.stop_all)
        if current_thread() is main_thread():
            self._chain_sigterm()

    def _chain_sigterm(self) -> None:
        """atexit does not run on SIGTERM, which would orphan the module processes: stop them first."""
        previous = signal.getsignal(signal.SIGTERM)

        def handler(signum, frame):
            self.stop_all()
            if callable(previous):
                previous(signum, frame)
            else:
                signal.signal(signal.SIGTERM, signal.SIG_DFL)
                os.kill(os.getpid(), signal.SIGTERM)

        signal.signal(signal.SIGTERM, handler)

    # -- public --------------------------------------------------------------

    def status(self, project_id: str, module_dir: Path) -> dict:
        with self._lock:
            item = self._items.get(project_id)
            if item and item["process"].poll() is None:
                return self._view(item, "running")
            if item:  # exited on its own
                return self._view(item, "failed", "the module process stopped")
        if not (Path(module_dir) / ENTRY).is_file():
            return {"state": "no_entry", "message": f"The module has no {ENTRY} yet.", "url": None, "log": ""}
        return {"state": "stopped", "url": None, "message": "", "log": ""}

    def start(self, project_id: str, module_dir: Path) -> dict:
        """Start (or restart, so changed code is picked up) the preview and wait until it answers.

        Starts of one project are serialized: two overlapping requests must not kill each other's process."""
        with self._lock:
            gate = self._starting.setdefault(project_id, Lock())
        with gate:
            return self._start(project_id, module_dir)

    def _start(self, project_id: str, module_dir: Path) -> dict:
        module_dir = Path(module_dir).resolve()
        if not (module_dir / ENTRY).is_file():
            return {"state": "no_entry", "message": f"The module has no {ENTRY} yet.", "url": None, "log": ""}
        self.stop(project_id)
        with self._lock:
            while len(self._items) >= self.max_running:
                oldest = min(self._items, key=lambda key: self._items[key]["started"])
                self._terminate(self._items.pop(oldest))
            port = self._free_port()
            log_path = module_dir.parent / "preview.log"
            log = open(log_path, "wb")
            origins = [f"127.0.0.1:{port}", f"localhost:{port}"]
            command = [self.python, "-m", "bokeh", "serve", str(module_dir), "--address", "127.0.0.1", "--port", str(port)]
            for origin in origins:
                command += ["--allow-websocket-origin", origin]
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            try:
                process = subprocess.Popen(command, cwd=module_dir, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            except OSError as error:
                log.close()
                return {"state": "failed", "message": f"could not start the module: {error}", "url": None, "log": ""}
            item = {"process": process, "port": port, "log": log_path, "log_file": log, "name": module_dir.name, "started": time.time()}
            self._items[project_id] = item
        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if process.poll() is not None:
                break
            if self._answers(port, module_dir.name):
                return self.status(project_id, module_dir)
            time.sleep(0.25)
        with self._lock:
            if self._items.get(project_id) is item:
                self._items.pop(project_id)
        reason = "the module exited while starting" if process.poll() is not None else "the module did not answer in time"
        self._terminate(item)
        return {"state": "failed", "message": reason, "url": None, "log": self._tail(log_path)}

    def stop(self, project_id: str) -> None:
        with self._lock:
            item = self._items.pop(project_id, None)
        if item:
            self._terminate(item)

    def stop_all(self) -> None:
        with self._lock:
            items, self._items = list(self._items.values()), {}
        for item in items:
            self._terminate(item)

    # -- internals -----------------------------------------------------------

    def _view(self, item: dict, state: str, message: str = "") -> dict:
        url = f"http://127.0.0.1:{item['port']}/{item['name']}" if state == "running" else None
        return {"state": state, "url": url, "message": message, "log": self._tail(item["log"]) if state != "running" else ""}

    @staticmethod
    def _tail(path: Path) -> str:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")[-LOG_TAIL:]
        except OSError:
            return ""

    @staticmethod
    def _free_port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    @staticmethod
    def _answers(port: int, name: str) -> bool:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/{name}", timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    @staticmethod
    def _terminate(item: dict) -> None:
        process = item["process"]
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        try:
            item["log_file"].close()
        except OSError:
            pass
