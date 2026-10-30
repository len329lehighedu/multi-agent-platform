#!/usr/bin/env python3
"""Relocate a registered source checkout only after verifying every recorded hash."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module_id")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    source = args.path.expanduser().resolve()
    catalog_path = ROOT / "corpus/catalog.json"
    data = json.loads(catalog_path.read_text())
    matches = [item for item in data["modules"] if item["id"] == args.module_id]
    if len(matches) != 1:
        parser.error("Module ID is not uniquely registered")
    module = matches[0]
    for item in module["files"]:
        path = source / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            parser.error(f"Source differs from reviewed snapshot: {item['path']}; review changes before refreshing hashes")
    module["source_root"] = str(source)
    catalog_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Updated {args.module_id} source location; all reviewed hashes match.")
