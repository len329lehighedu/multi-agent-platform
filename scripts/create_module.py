#!/usr/bin/env python3
"""Create a runnable starter lesson without overwriting an existing module."""

import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def create(module_id, title, root=ROOT):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", module_id):
        raise ValueError("Use a lowercase module ID with letters, digits and hyphens")
    if not title.strip():
        raise ValueError("Title cannot be empty")
    destination = root / "modules" / module_id
    if destination.exists():
        raise FileExistsError(f"Module already exists: {module_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "templates/module-scaffold", destination)
    path = destination / "module.json"
    metadata = json.loads(path.read_text())
    metadata["title"] = title
    path.write_text(json.dumps(metadata, indent=2) + "\n")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module_id")
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    try:
        result = create(args.module_id, args.title)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"Created {result}; run python3 scripts/serve.py --module {args.module_id}")
