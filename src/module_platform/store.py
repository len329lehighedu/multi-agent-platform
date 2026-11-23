"""Atomic local persistence behind a replaceable run-store boundary."""

from __future__ import annotations

import json
from pathlib import Path
import re
from threading import RLock

from .domain import Project, RunRecord, utc_now


RUN_ID = re.compile(r"^[0-9a-f]{32}$")


class RunNotFound(KeyError):
    pass


class JsonRunStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, run_id: str) -> Path:
        if not RUN_ID.fullmatch(run_id):
            raise RunNotFound(run_id)
        return self.root / f"{run_id}.json"

    def create(self, run: RunRecord) -> RunRecord:
        path = self._path(run.id)
        with self._lock:
            if path.exists():
                raise ValueError(f"run already exists: {run.id}")
            self._write(path, run)
        return run

    def save(self, run: RunRecord) -> RunRecord:
        path = self._path(run.id)
        with self._lock:
            if not path.exists():
                raise RunNotFound(run.id)
            self._write(path, run)
        return run

    def get(self, run_id: str) -> RunRecord:
        path = self._path(run_id)
        with self._lock:
            if not path.exists():
                raise RunNotFound(run_id)
            return RunRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, run_id: str) -> None:
        path = self._path(run_id)
        with self._lock:
            if not path.exists():
                raise RunNotFound(run_id)
            path.unlink()

    def list(self) -> list[RunRecord]:
        with self._lock:
            runs = [RunRecord.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in self.root.glob("*.json")]
        return sorted(runs, key=lambda item: item.created_at, reverse=True)

    @staticmethod
    def _write(path: Path, run: RunRecord) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)


class ProjectNotFound(KeyError):
    pass


class JsonProjectStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, project_id: str) -> Path:
        if not RUN_ID.fullmatch(project_id):
            raise ProjectNotFound(project_id)
        return self.root / f"{project_id}.json"

    def create(self, name: str, created_by: str = "local-user") -> Project:
        name = " ".join(name.split())
        if not name:
            raise ValueError("project name is required")
        if len(name) > 80:
            raise ValueError("project name must be at most 80 characters")
        with self._lock:
            if any(existing.name.lower() == name.lower() for existing in self.list()):
                raise ValueError(f"a project named '{name}' already exists")
            project = Project.create(name, created_by.strip() or "local-user")
            self._write(project)
        return project

    def get(self, project_id: str) -> Project:
        path = self._path(project_id)
        with self._lock:
            if not path.exists():
                raise ProjectNotFound(project_id)
            return Project(**json.loads(path.read_text(encoding="utf-8")))

    def delete(self, project_id: str) -> None:
        path = self._path(project_id)
        with self._lock:
            if not path.exists():
                raise ProjectNotFound(project_id)
            path.unlink()

    def touch(self, project_id: str) -> None:
        with self._lock:
            project = self.get(project_id)
            project.updated_at = utc_now()
            self._write(project)

    def list(self) -> list[Project]:
        with self._lock:
            items = [Project(**json.loads(path.read_text(encoding="utf-8"))) for path in self.root.glob("*.json")]
        return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def _write(self, project: Project) -> None:
        path = self._path(project.id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(project.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)
