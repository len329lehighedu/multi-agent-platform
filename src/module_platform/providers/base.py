"""Vendor-neutral model-provider contract."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ModelRequest:
    run_id: str
    agent_id: str
    system_prompt: str
    messages: tuple[dict, ...]
    tools: tuple[dict, ...] = ()
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    structured_output: dict | None = None
    tool_calls: tuple[dict, ...] = ()
    usage: dict = field(default_factory=dict)
    provider_metadata: dict = field(default_factory=dict)


class ModelProvider(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse: ...


class ProviderNotConfigured(RuntimeError):
    pass


class ProviderError(RuntimeError):
    """A provider call failed; the message is safe to show to the user."""


class DisabledProvider:
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise ProviderNotConfigured("No model provider is configured for this foundation build")
