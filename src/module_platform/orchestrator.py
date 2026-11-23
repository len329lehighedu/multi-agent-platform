"""Explicit orchestration state; model/tool execution will attach here."""

from .agents import AgentCatalog
from .domain import Message, RunRecord, RunStage, RunStatus
from .store import JsonRunStore
from .store import JsonProjectStore
from .workspaces import WorkspaceManager, module_files


class Orchestrator:
    def __init__(self, store: JsonRunStore, agents: AgentCatalog, workspaces: WorkspaceManager, projects: JsonProjectStore | None = None):
        self.store = store
        self.projects = projects
        self.agents = agents
        self.workspaces = workspaces

    def create_run(self, goal: str, created_by: str = "local-user", provider: str | None = None, project_id: str | None = None) -> RunRecord:
        goal = goal.strip()
        if not goal:
            raise ValueError("goal is required")
        run = RunRecord.create(goal, created_by.strip() or "local-user")
        if project_id:
            if self.projects is None:
                raise ValueError("projects are not enabled")
            self.projects.get(project_id)
            module = self.workspaces.project_module(project_id)
            run.project_id, run.module_path = project_id, str(module)
            run.kind = "feature" if module_files(module) else "module"
            run.workspace_path = str(self.workspaces.create(run.id, with_module=False))
            self.projects.touch(project_id)
        else:
            run.workspace_path = str(self.workspaces.create(run.id))
        run.append_event("run.created", {"goal": goal, "created_by": run.created_by, "provider": provider,
                                         "project_id": project_id, "kind": run.kind})
        return self.store.create(run)

    def delete_project(self, project_id: str) -> int:
        """Permanently remove a project, its module files and all its runs. Returns the number of runs removed."""
        if self.projects is None:
            raise ValueError("projects are not enabled")
        self.projects.get(project_id)
        runs = [run for run in self.store.list() if run.project_id == project_id]
        if any(run.status == RunStatus.ACTIVE for run in runs):
            raise ValueError("a run in this project is still working; wait for it to finish before deleting")
        for run in runs:
            self.workspaces.delete_run(run.id)
            self.store.delete(run.id)
        self.workspaces.delete_project(project_id)
        self.projects.delete(project_id)
        return len(runs)

    def receive_message(self, run_id: str, content: str, target_agent: str | None = None) -> RunRecord:
        content = content.strip()
        if not content:
            raise ValueError("content is required")
        if target_agent is not None:
            self.agents.get(target_agent)
        run = self.store.get(run_id)
        run.append_message(Message.create("user", content, target_agent=target_agent))
        run.append_event("message.accepted", {"target_agent": target_agent})
        return self.store.save(run)

    def transition(self, run_id: str, stage: str, reason: str) -> RunRecord:
        reason = reason.strip()
        if not reason:
            raise ValueError("reason is required")
        run = self.store.get(run_id)
        run.transition(RunStage(stage), reason)
        return self.store.save(run)
