"""Local per-run and per-project workspace adapter."""

import shutil
from pathlib import Path


def module_files(root: Path) -> list[dict]:
    """Source files of a module, without hidden folders and caches."""
    root = Path(root)
    if not root.is_dir():
        return []
    return [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size}
            for p in sorted(root.rglob("*"))
            if p.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(root).parts)]


class WorkspaceManager:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, run_id: str, with_module: bool = True) -> Path:
        workspace = self.root / run_id
        if workspace.exists():
            raise ValueError(f"workspace already exists: {run_id}")
        for child in ("module", "artifacts", "logs") if with_module else ("artifacts", "logs"):
            (workspace / child).mkdir(parents=True, exist_ok=False)
        return workspace.resolve()

    def project_module(self, project_id: str) -> Path:
        """The one module directory shared by every run of a project."""
        path = self.root / "projects" / project_id / "module"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    def delete_run(self, run_id: str) -> None:
        shutil.rmtree(self.root / run_id, ignore_errors=True)

    def delete_project(self, project_id: str) -> None:
        shutil.rmtree(self.root / "projects" / project_id, ignore_errors=True)
