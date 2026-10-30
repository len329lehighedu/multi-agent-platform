#!/usr/bin/env python3
"""Run setup, shared runtime and every installed module's automated tests."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
directories = [ROOT / "tests"] + sorted((ROOT / "modules").glob("*/tests"))
for directory in directories:
    print(f"Testing {directory.relative_to(ROOT)}", flush=True)
    result = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(directory), "-v"], cwd=ROOT)
    if result.returncode:
        sys.exit(result.returncode)
print("All automated non-browser suites passed.")
