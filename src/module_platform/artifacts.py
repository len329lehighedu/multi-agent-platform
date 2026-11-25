"""Typed agent artifacts: schema validation and cross-artifact consistency.

Everything here is deterministic code. Agents return JSON artifacts; the
orchestrator validates them without spending model tokens, and downstream agents
receive these artifacts instead of the chat history.
"""

from __future__ import annotations

import json
from pathlib import Path

MAX_PLOTS_PER_TAB = 5
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "number": (int, float)}


class ArtifactSchemas:
    def __init__(self, schemas: dict[str, dict]):
        self._schemas = schemas

    @classmethod
    def load(cls, root: Path) -> "ArtifactSchemas":
        return cls({p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(root).glob("*.json"))})

    def names(self) -> tuple[str, ...]:
        return tuple(self._schemas)

    def validate(self, name: str, data) -> list[str]:
        if name not in self._schemas:
            raise ValueError(f"unknown artifact: {name}")
        errors: list[str] = []
        _check(self._schemas[name], data, name, errors)
        return errors

    def describe(self, name: str) -> str:
        """Compact, token-cheap description of a schema for the prompt."""
        lines: list[str] = []
        _describe(self._schemas[name], 0, lines)
        return "\n".join(lines)


def _matches(kind: str, value) -> bool:
    if kind in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[kind])


def _check(schema: dict, value, path: str, errors: list[str]) -> None:
    expected = schema.get("type")
    if expected:
        allowed = expected if isinstance(expected, list) else [expected]
        ok = any(_matches(kind, value) for kind in allowed)
        if not ok:
            errors.append(f"{path}: expected {'|'.join(allowed)}")
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(value, str) and len(value.strip()) < schema.get("minLength", 0):
        errors.append(f"{path}: too short")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: missing")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                _check(sub, value[key], f"{path}.{key}", errors)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        for index, item in enumerate(value):
            if "items" in schema:
                _check(schema["items"], item, f"{path}[{index}]", errors)


def _describe(schema: dict, depth: int, lines: list[str], key: str = "") -> None:
    pad = "  " * depth
    kind = schema.get("type", "any")
    if isinstance(kind, list):
        kind = "|".join(kind)
    if "enum" in schema:
        kind = "|".join(schema["enum"])
    if kind == "object":
        required = set(schema.get("required", []))
        if key:
            lines.append(f"{pad}{key}: object")
        for name, sub in schema.get("properties", {}).items():
            _describe(sub, depth + (1 if key else 0), lines, name + ("" if name in required else "?"))
    elif kind == "array":
        item = schema.get("items", {})
        if item.get("type") == "object":
            lines.append(f"{pad}{key}: list of")
            _describe(item, depth + 1, lines, "")
        else:
            lines.append(f"{pad}{key}: list of {'|'.join(item['enum']) if 'enum' in item else item.get('type', 'any')}")
    else:
        lines.append(f"{pad}{key}: {kind}")


# -- cross-artifact checks ---------------------------------------------------

def criterion_ids(task_spec: dict) -> list[str]:
    return [item["id"] for item in task_spec.get("acceptance_criteria", [])]


def check_research(task_spec: dict, brief: dict) -> list[str]:
    oracle_ids = [c["id"] for c in task_spec["acceptance_criteria"] if c["verification"] == "scientific_oracle"]
    missing = [i for i in oracle_ids if i not in brief.get("covers", [])]
    return [f"research_brief.covers must include scientific_oracle criteria: {', '.join(missing)}"] if missing else []


def check_design(task_spec: dict, brief: dict, design: dict, existing: set[str] | None = None) -> list[str]:
    """`existing` is the set of module files already built; passing it means this design extends a module."""
    errors: list[str] = []
    mapped = {item["criterion_id"] for item in design["criteria_map"]}
    for cid in criterion_ids(task_spec):
        if cid not in mapped:
            errors.append(f"criteria_map: no implementation mapped for {cid}")
    controls = {c.get("hyperparameter") for tab in design["tabs"] for c in tab["controls"]}
    for param in brief["hyperparameters"]:
        if param["ui_control"] != "none" and param["name"] not in controls:
            errors.append(f"hyperparameter '{param['name']}' has ui_control '{param['ui_control']}' but no control in any tab")
    paths = {f["path"] for f in design["files"]}
    for tab in design["tabs"]:
        if f"tabs/{tab['id']}_tab.py" not in paths | (existing or set()):
            errors.append(f"tab '{tab['id']}' needs file tabs/{tab['id']}_tab.py")
        if len(tab["plots"]) > MAX_PLOTS_PER_TAB:
            errors.append(f"tab '{tab['id']}' has {len(tab['plots'])} plots; maximum is {MAX_PLOTS_PER_TAB}")
    for path in sorted(paths):
        if path.endswith(".html") or path.startswith("templates/") or path == "flask_app.py":
            errors.append(f"files: {path} is not allowed; HTML pages and Flask are disabled, build a Bokeh-only module")
    if existing is None and not any(p.startswith("engine/") for p in paths):
        errors.append("files: science code must live under engine/")
    if existing is None and "main.py" not in paths:
        errors.append("files: the Bokeh entry file must be main.py (the preview runs `bokeh serve` on the module folder)")
    if not any(p.startswith("tests/") for p in paths):
        errors.append("files: tests/ is required")
    return errors


def check_test_plan(task_spec: dict, brief: dict, plan: dict) -> list[str]:
    errors: list[str] = []
    covered = {cid for case in plan["cases"] for cid in case["criterion_ids"]}
    for cid in criterion_ids(task_spec):
        if cid not in covered:
            errors.append(f"no test case covers {cid}")
    if not any(case["edge_case"] for case in plan["cases"]):
        errors.append("cases: at least one edge case is required")
    if not plan["oracle_checks"]:
        errors.append("oracle_checks: at least one independent oracle check is required")
    return errors


def check_plan(task_spec: dict, brief: dict, plan: dict) -> list[str]:
    errors: list[str] = []
    listed = {item["criterion_id"] for item in plan["success_definition"]}
    for cid in criterion_ids(task_spec):
        if cid not in listed:
            errors.append(f"success_definition: missing acceptance criterion {cid}")
    if plan["algorithm"]["name"].strip().lower() != brief["method"]["name"].strip().lower():
        errors.append(f"algorithm.name must equal research_brief.method.name exactly: '{brief['method']['name']}'")
    return errors


def render_plan(task_spec: dict, plan: dict) -> str:
    """Deterministic, user-facing rendering of the project plan (no model tokens)."""
    def bullets(items):
        return "\n".join(f"- {item}" for item in items) if items else "- None"

    success = "\n".join(f"- {s['criterion_id']}: {s['statement']} (measured by: {s['how_measured']})" for s in plan["success_definition"])
    return (
        f"PROJECT PLAN: {task_spec['title']}\n\n{plan['summary']}\n\n"
        f"What the module will do\n{bullets(plan['what_it_does'])}\n\n"
        f"Algorithm: {plan['algorithm']['name']}\n{plan['algorithm']['why']}\n\n"
        f"How success is defined\n{success}\n\n"
        f"What you can do with the MVP\n{bullets(plan['mvp_user_capabilities'])}\n\n"
        f"Out of scope\n{bullets(plan['out_of_scope'])}\n\n"
        f"How it will be built\n{bullets(plan['build_overview'])}\n\n"
        f"How it will be verified\n{bullets(plan['verification_overview'])}\n\n"
        f"Risks and open points\n{bullets(plan['risks'])}\n\n"
        "Nothing has been built or run yet. Approve this plan to start the build."
    )


# -- build phase ------------------------------------------------------------

# HTML is intentionally absent: description pages are disabled, generated modules are Bokeh-only.
ALLOWED_SUFFIXES = {".py", ".css", ".js", ".txt", ".md", ".json", ".sh", ".cfg", ".toml"}
MAX_FILE_CHARS = 200_000
MAX_SET_CHARS = 600_000


def safe_relative_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    return bool(path) and not path.startswith(("/", "~")) and "\\" not in path and all(p not in ("", ".", "..") for p in parts) \
        and not any(p.startswith(".") for p in parts)


def check_file_set(file_set: dict, design: dict | None = None, existing: set[str] | None = None) -> list[str]:
    """Deterministic checks on a file_set. Pass `design` for the first build (every designed file must exist)."""
    errors: list[str] = []
    seen: set[str] = set()
    total = 0
    for item in file_set["files"]:
        path = item["path"]
        if not safe_relative_path(path):
            errors.append(f"{path}: path must be relative, inside the module, with no '..' or hidden folders")
            continue
        if Path(path).suffix not in ALLOWED_SUFFIXES:
            errors.append(f"{path}: file type not allowed (use {', '.join(sorted(ALLOWED_SUFFIXES))})")
        if path in seen:
            errors.append(f"{path}: listed twice")
        seen.add(path)
        total += len(item["content"])
        if len(item["content"]) > MAX_FILE_CHARS:
            errors.append(f"{path}: file too large")
        if not item["content"].strip():
            errors.append(f"{path}: file is empty")
    if total > MAX_SET_CHARS:
        errors.append("file_set is too large")
    for path in file_set.get("delete", []):
        if existing is not None and path not in existing:
            errors.append(f"delete: {path} does not exist")
    if design is not None:
        for entry in design["files"]:
            if entry["path"] not in seen:
                errors.append(f"design file not written: {entry['path']}")
    return errors


def check_qa(test_plan: dict, qa: dict) -> list[str]:
    errors: list[str] = []
    reported = {r["case_id"] for r in qa["results"]}
    for case in test_plan["cases"]:
        if case["id"] not in reported:
            errors.append(f"results: no result for test case {case['id']}")
    failing = [r["case_id"] for r in qa["results"] if r["status"] == "failed"]
    if qa["verdict"] == "ready_for_review" and (failing or any(d["severity"] == "blocker" for d in qa["defects"])):
        errors.append("verdict ready_for_review is not allowed with failed cases or blocker defects")
    return errors


def render_build_summary(task_spec: dict, qa: dict | None, files: list[str], checks: dict, version: str) -> str:
    """User-facing result of a build, written by code from evidence rather than by a model."""
    lines = [f"Build {version}: {len(files)} files written. Automated checks: {'PASSED' if checks['passed'] else 'FAILED'}."]
    if qa:
        label = {"passed": "passed", "failed": "FAILED", "blocked": "blocked", "not_run": "not run"}
        lines.append("")
        lines.append("Evidence per test case:")
        for result in qa["results"]:
            lines.append(f"- {result['case_id']}: {label[result['status']]} — {result['evidence']}")
        for defect in qa["defects"]:
            lines.append(f"- DEFECT [{defect['severity']}] {defect['actual']} (expected: {defect['expected']})")
        lines.append(f"Tester verdict: {qa['verdict'].replace('_', ' ')}.")
    lines += ["", "Tell me what to change (layout, labels, colours, plots, defaults) and the Builder will edit the module and re-run the checks."]
    return "\n".join(lines)
