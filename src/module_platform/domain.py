"""Framework-independent run, message, and event types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStage(StrEnum):
    INTAKE = "intake"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    BUILDING = "building"
    QA = "qa"
    REPAIR = "repair"
    REVIEW = "review"


class RunStatus(StrEnum):
    ACTIVE = "active"
    AWAITING_USER = "awaiting_user"
    READY_FOR_REVIEW = "ready_for_review"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_STAGE_TRANSITIONS: dict[RunStage, set[RunStage]] = {
    RunStage.INTAKE: {RunStage.PLANNING},
    RunStage.PLANNING: {RunStage.ARCHITECTURE, RunStage.INTAKE},
    RunStage.ARCHITECTURE: {RunStage.BUILDING, RunStage.PLANNING},
    RunStage.BUILDING: {RunStage.QA, RunStage.ARCHITECTURE},
    RunStage.QA: {RunStage.REPAIR, RunStage.REVIEW},
    RunStage.REPAIR: {RunStage.QA, RunStage.ARCHITECTURE},
    RunStage.REVIEW: {RunStage.REPAIR, RunStage.BUILDING},
}


@dataclass(slots=True)
class Message:
    id: str
    role: str
    content: str
    created_at: str
    agent_id: str | None = None
    target_agent: str | None = None

    @classmethod
    def create(cls, role: str, content: str, **routing: str | None) -> "Message":
        return cls(uuid4().hex, role, content, utc_now(), **routing)


@dataclass(slots=True)
class RunEvent:
    sequence: int
    type: str
    created_at: str
    data: dict = field(default_factory=dict)


@dataclass(slots=True)
class Project:
    """A named container for one module. Its runs (the first build, then each feature) share one module workspace."""
    id: str
    name: str
    created_by: str
    created_at: str
    updated_at: str

    @classmethod
    def create(cls, name: str, created_by: str = "local-user") -> "Project":
        now = utc_now()
        return cls(uuid4().hex, name, created_by, now, now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RunRecord:
    id: str
    goal: str
    created_by: str
    created_at: str
    updated_at: str
    stage: RunStage = RunStage.INTAKE
    status: RunStatus = RunStatus.ACTIVE
    messages: list[Message] = field(default_factory=list)
    events: list[RunEvent] = field(default_factory=list)
    workspace_path: str | None = None
    revision: int = 0
    project_id: str | None = None
    kind: str = "module"  # "module" builds the first version of a project's module, "feature" extends it
    module_path: str | None = None

    @classmethod
    def create(cls, goal: str, created_by: str = "local-user") -> "RunRecord":
        now = utc_now()
        return cls(uuid4().hex, goal, created_by, now, now)

    def append_event(self, event_type: str, data: dict | None = None) -> RunEvent:
        event = RunEvent(len(self.events) + 1, event_type, utc_now(), data or {})
        self.events.append(event)
        self.touch()
        return event

    def append_message(self, message: Message) -> None:
        self.messages.append(message)
        self.append_event("message.created", {"message_id": message.id, "role": message.role, "agent_id": message.agent_id})

    def transition(self, stage: RunStage, reason: str) -> None:
        if stage == self.stage:
            raise ValueError(f"run is already in {stage.value}")
        if stage not in ALLOWED_STAGE_TRANSITIONS[self.stage]:
            raise ValueError(f"cannot transition from {self.stage.value} to {stage.value}")
        previous = self.stage
        self.stage = stage
        self.status = RunStatus.ACTIVE
        self.append_event("run.stage_changed", {"from": previous.value, "to": stage.value, "reason": reason})

    def touch(self) -> None:
        self.updated_at = utc_now()
        self.revision += 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunRecord":
        value = dict(data)
        value["stage"] = RunStage(value["stage"])
        value["status"] = RunStatus(value["status"])
        value["messages"] = [Message(**item) for item in value.get("messages", [])]
        value["events"] = [RunEvent(**item) for item in value.get("events", [])]
        return cls(**value)
