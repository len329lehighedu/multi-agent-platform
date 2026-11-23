"""Explicit orchestration state; model/tool execution will attach here."""

from .agents import AgentCatalog
from .domain import Message, RunRecord, RunStage
from .store import JsonRunStore
from .workspaces import WorkspaceManager


class Orchestrator:
    def __init__(self, store: JsonRunStore, agents: AgentCatalog, workspaces: WorkspaceManager):
        self.store = store
        self.agents = agents
        self.workspaces = workspaces

    def create_run(self, goal: str, created_by: str = "local-user", provider: str | None = None) -> RunRecord:
        goal = goal.strip()
        if not goal:
            raise ValueError("goal is required")
        run = RunRecord.create(goal, created_by.strip() or "local-user")
        run.workspace_path = str(self.workspaces.create(run.id))
        run.append_event("run.created", {"goal": goal, "created_by": run.created_by, "provider": provider})
        return self.store.create(run)

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
