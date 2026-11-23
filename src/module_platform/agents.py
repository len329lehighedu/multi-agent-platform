"""Versioned agent catalog loaded from repository configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    id: str
    display_name: str
    prompt_path: Path
    skills: tuple[str, ...]

    @property
    def prompt(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8")


class AgentCatalog:
    def __init__(self, definitions: dict[str, AgentDefinition]):
        self._definitions = definitions

    @classmethod
    def load(cls, config_root: Path) -> "AgentCatalog":
        config_root = Path(config_root)
        manifest = json.loads((config_root / "manifest.json").read_text(encoding="utf-8"))
        definitions = {}
        for item in manifest["agents"]:
            definition = AgentDefinition(
                id=item["id"], display_name=item["display_name"],
                prompt_path=config_root / item["prompt"], skills=tuple(item.get("skills", [])),
            )
            if definition.id in definitions:
                raise ValueError(f"duplicate agent id: {definition.id}")
            if not definition.prompt_path.is_file():
                raise ValueError(f"missing prompt: {definition.prompt_path}")
            definitions[definition.id] = definition
        return cls(definitions)

    def get(self, agent_id: str) -> AgentDefinition:
        try:
            return self._definitions[agent_id]
        except KeyError as error:
            raise ValueError(f"unknown agent: {agent_id}") from error

    def ids(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def public_definitions(self) -> list[dict]:
        return [
            {
                "id": definition.id,
                "display_name": definition.display_name,
                "skills": list(definition.skills),
            }
            for definition in self._definitions.values()
        ]
