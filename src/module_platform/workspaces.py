"""Local per-run workspace adapter."""

from pathlib import Path


class WorkspaceManager:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, run_id: str) -> Path:
        workspace = self.root / run_id
        if workspace.exists():
            raise ValueError(f"workspace already exists: {run_id}")
        for child in ("module", "artifacts", "logs"):
            (workspace / child).mkdir(parents=True, exist_ok=False)
        return workspace.resolve()
