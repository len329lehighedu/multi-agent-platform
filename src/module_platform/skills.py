"""Skill library: deterministic, token-aware prompt composition.

The orchestrator (not the agent) decides which skills and references an agent
receives. The stable part of the prompt (role + skills + references) comes first
so provider-side prompt caching can reuse it across calls.

Report the size of every agent's prompt with:
    PYTHONPATH=src .venv/bin/python -m module_platform.skills
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agents import AgentCatalog, AgentDefinition


def estimate_tokens(text: str) -> int:
    """Rough token estimate (words x 1.35); good enough to track budgets."""
    return int(len(text.split()) * 1.35)


@dataclass(frozen=True, slots=True)
class Skill:
    id: str
    description: str
    owner: str
    body: str


@dataclass(frozen=True, slots=True)
class ComposedPrompt:
    text: str
    skills: tuple[str, ...]
    references: tuple[str, ...]
    tokens_est: int


def _parse(path: Path) -> Skill:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"{path}: missing frontmatter")
    head, _, body = raw[4:].partition("\n---\n")
    meta = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
    for key in ("name", "description", "owner"):
        if key not in meta:
            raise ValueError(f"{path}: frontmatter needs '{key}'")
    if meta["name"] != path.parent.name:
        raise ValueError(f"{path}: name must match directory '{path.parent.name}'")
    return Skill(meta["name"], meta["description"], meta["owner"], body.strip())


class SkillLibrary:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._skills = {p.parent.name: _parse(p) for p in sorted(self.root.glob("*/SKILL.md"))}

    def get(self, skill_id: str) -> Skill:
        try:
            return self._skills[skill_id]
        except KeyError as error:
            raise ValueError(f"unknown skill: {skill_id}") from error

    def ids(self) -> tuple[str, ...]:
        return tuple(self._skills)

    def validate(self, catalog: AgentCatalog) -> None:
        """Fail fast on manifest entries that point at missing skills or references."""
        for agent_id in catalog.ids():
            agent = catalog.get(agent_id)
            for skill_id in agent.skills:
                skill = self.get(skill_id)
                if skill.owner != agent.id:
                    raise ValueError(f"skill {skill_id} is owned by {skill.owner}, not {agent.id}")
            for ref in agent.references:
                if not (self.root / ref.path).is_file():
                    raise ValueError(f"missing reference: {ref.path}")

    def compose(self, agent: AgentDefinition, tags: tuple[str, ...] = (), only: tuple[str, ...] | None = None) -> ComposedPrompt:
        skill_ids = tuple(s for s in agent.skills if only is None or s in only)
        parts = [agent.prompt.strip()]
        if skill_ids:
            parts.append("# Skills\n\n" + "\n\n".join(self.get(s).body for s in skill_ids))
        refs = tuple(r.path for r in agent.references if only is None and (r.when_tag == "*" or r.when_tag in tags))
        if refs:
            parts.append("# Reference material\n\n" + "\n\n".join((self.root / r).read_text(encoding="utf-8").strip() for r in refs))
        text = "\n\n".join(parts)
        return ComposedPrompt(text, skill_ids, refs, estimate_tokens(text))


def report(config_root: Path) -> str:
    """Per-agent prompt size: skills only, and worst case with every reference."""
    catalog = AgentCatalog.load(config_root / "agents")
    library = SkillLibrary(config_root / "skills")
    library.validate(catalog)
    lines = [f"{'agent':<18}{'tier':<8}{'skills':>7}{'skills tokens':>15}{'max prompt':>12}"]
    for agent_id in catalog.ids():
        agent = catalog.get(agent_id)
        base = library.compose(agent, only=agent.skills)
        worst = library.compose(agent, tags=tuple(r.when_tag for r in agent.references))
        lines.append(f"{agent.id:<18}{agent.tier:<8}{len(base.skills):>7}{base.tokens_est:>15}{worst.tokens_est:>12}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(Path(__file__).resolve().parents[2] / "config"))
