#!/usr/bin/env python3
"""Run the local lesson gallery and Bokeh applications with one command."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--bokeh-port", type=int, default=5006)
    parser.add_argument("--module", action="append", dest="modules", help="Serve only this module (repeatable)")
    args = parser.parse_args()
    try:
        from stem_platform.runtime import serve
        serve(ROOT, args.port, args.bokeh_port, args.modules)
    except (ImportError, OSError, ValueError) as exc:
        print(f"Cannot start lessons: {exc}", file=sys.stderr)
        print("Check requirements.lock.txt, module files, and available ports.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
