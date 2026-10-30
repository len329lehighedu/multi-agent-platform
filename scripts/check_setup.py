#!/usr/bin/env python3
"""Check local configuration and exemplar integrity without invoking a model."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROLES = {
    "stem-learning-planner", "stem-architect", "stem-builder", "stem-qa-reviewer"
}
EXPECTED_SKILLS = {
    "stem-build-module", "stem-module-examples", "stem-lesson-design",
    "stem-scientific-python", "stem-bokeh-interaction", "stem-flask-bokeh",
    "stem-learning-ui", "stem-module-verification",
}


def frontmatter(path):
    """Read only the plain scalar/list subset used by this project's files.

    This is intentionally not a general YAML parser or runtime schema validator.
    """
    match = re.match(r"\A---\n(.*?)\n---\n", path.read_text(), re.S)
    if not match:
        raise ValueError(f"Missing frontmatter: {path}")
    fields = {}
    active_list = None
    for line in match.group(1).splitlines():
        if line.startswith("  - ") and active_list:
            fields[active_list].append(line[4:].strip())
            continue
        item = re.fullmatch(r"([a-z-]+):(?: (.+))?", line)
        if not item:
            raise ValueError(f"Unsupported frontmatter line in {path.name}: {line}")
        key, value = item.groups()
        if key in fields:
            raise ValueError(f"Duplicate field {key} in {path.name}")
        fields[key] = value if value is not None else []
        active_list = key if value is None else None
    return fields


def check(root):
    errors = []
    skills_dir = root / ".agents/skills"
    skills = {p.parent.name: p for p in skills_dir.glob("*/SKILL.md")}
    if set(skills) != EXPECTED_SKILLS:
        errors.append(f"Skill inventory differs: {sorted(set(skills) ^ EXPECTED_SKILLS)}")
    for name, path in skills.items():
        try:
            fields = frontmatter(path)
            if fields.get("name") != name or not fields.get("description"):
                errors.append(f"Invalid skill metadata: {name}")
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                errors.append(f"Invalid skill name: {name}")
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if "://" not in link and not (path.parent / link).is_file():
                    errors.append(f"Missing skill reference: {name}/{link}")
        except ValueError as exc:
            errors.append(str(exc))

    roles = {p.stem: p for p in (root / "agents").glob("*.md")}
    if set(roles) != EXPECTED_ROLES:
        errors.append(f"Role inventory differs: {sorted(set(roles) ^ EXPECTED_ROLES)}")
    for name, path in roles.items():
        try:
            fields = frontmatter(path)
            if fields.get("name") != name or not fields.get("description"):
                errors.append(f"Invalid role metadata: {name}")
            preloads = fields.get("skills")
            if not isinstance(preloads, list) or not preloads:
                errors.append(f"Missing skill preloads: {name}")
            else:
                for skill in preloads:
                    if skill not in skills:
                        errors.append(f"Unknown preloaded skill: {name}/{skill}")
        except ValueError as exc:
            errors.append(str(exc))

    for relative in (
        "AGENTS.md", "README.md", "docs/design-proposal.md", "docs/usage.md",
        "docs/runtime-decision.md", "templates/module-brief.md",
        "templates/handoff.md", "templates/qa-report.md", "evaluations/cases.md",
    ):
        if not (root / relative).is_file():
            errors.append(f"Missing required document: {relative}")

    try:
        manifest = json.loads((root / "templates/run-manifest.json").read_text())
        if manifest.get("schema_version") != 1 or manifest.get("status") != "not-started":
            errors.append("Invalid initial run manifest")
        catalog_path = root / "corpus/catalog.json"
        catalog = json.loads(catalog_path.read_text())
        if catalog.get("schema_version") != 1 or not catalog.get("modules"):
            errors.append("Invalid or empty corpus catalog")
        for module in catalog.get("modules", []):
            source = (catalog_path.parent / module["source_root"]).resolve()
            card = catalog_path.parent / module["case_study"]
            if not card.is_file():
                errors.append(f"Missing case study: {module['id']}")
            if not module.get("files"):
                errors.append(f"No source files registered: {module['id']}")
            for item in module.get("files", []):
                path = source / item["path"]
                if not path.is_file():
                    errors.append(f"Missing exemplar source: {module['id']}/{item['path']}")
                elif hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                    errors.append(f"Exemplar source drift: {module['id']}/{item['path']}")
        sources = json.loads((root / "sources.json").read_text())
        if not sources.get("sources"):
            errors.append("Source manifest is empty")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Manifest/catalog error: {exc}")
    try:
        from sync_runtime import adapter_errors
        errors.extend(adapter_errors(root))
        for path in (root / ".codex/agents").glob("*.toml"):
            data = tomllib.loads(path.read_text())
            if not all(data.get(key) for key in ("name", "description", "developer_instructions")):
                errors.append(f"Invalid Codex role: {path.name}")
            if "model" in data or "model_reasoning_effort" in data:
                errors.append(f"Unexpected Codex model override: {path.name}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Adapter validation error: {exc}")
    return errors, len(roles), len(skills)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-runtime", action="store_true")
    parser.add_argument("--runtime", choices=("codex", "claude"), default="codex")
    args = parser.parse_args()
    errors, roles, skills = check(ROOT)
    runtime = shutil.which(args.runtime)
    if args.require_runtime and not runtime:
        errors.append(f"{args.runtime} is not on PATH; CLI runtime checks are unavailable")
    for error in errors:
        print(f"FAIL: {error}")
    print(f"Configuration: {roles} roles, {skills} skills; {len(errors)} error(s)")
    print(f"Selected CLI ({args.runtime}): {runtime or 'not found on PATH'}")
    print(f"Codex CLI: {'available' if shutil.which('codex') else 'not found on PATH'}")
    print(f"Claude Code: {'available' if shutil.which('claude') else 'not found on PATH (optional)'}")
    print("Scope: static local checks only; no model calls or browser verification")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
