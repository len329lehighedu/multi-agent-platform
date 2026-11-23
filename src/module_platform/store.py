"""Atomic local persistence behind a replaceable run-store boundary."""

from __future__ import annotations

import json
from pathlib import Path
import re
from threading import RLock

from .domain import RunRecord


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

    def list(self) -> list[RunRecord]:
        with self._lock:
            runs = [RunRecord.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in self.root.glob("*.json")]
        return sorted(runs, key=lambda item: item.created_at, reverse=True)

    @staticmethod
    def _write(path: Path, run: RunRecord) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)
