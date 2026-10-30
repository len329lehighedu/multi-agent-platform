#!/usr/bin/env python3
"""Evaluate matched human-effort measurements without inventing missing baselines."""

import argparse
import csv
import json
import math
from pathlib import Path
import statistics


def evaluate(path):
    pairs = {}
    with Path(path).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        pair_id, mode = row["pair_id"].strip(), row["mode"].strip()
        if not pair_id or mode not in ("baseline", "multi-agent"):
            raise ValueError("Each row needs pair_id and baseline/multi-agent mode")
        if mode in pairs.setdefault(pair_id, {}):
            raise ValueError(f"Duplicate measurement: {pair_id}/{mode}")
        human, wall = float(row["human_minutes"]), float(row["wall_seconds"])
        if not all(math.isfinite(x) and x >= 0 for x in (human, wall)):
            raise ValueError("Time measurements must be finite and nonnegative")
        if mode == "baseline" and human == 0:
            raise ValueError("Baseline human effort must be positive")
        if row["quality_pass"] not in ("true", "false"):
            raise ValueError("quality_pass must be true or false")
        cost = None if not row.get("cost_usd", "").strip() else float(row["cost_usd"])
        if cost is not None and (not math.isfinite(cost) or cost < 0):
            raise ValueError("Cost must be nonnegative or left unavailable")
        pairs[pair_id][mode] = {"human_minutes": human, "wall_seconds": wall,
                                "quality_pass": row["quality_pass"] == "true", "cost_usd": cost}
    complete = {key: value for key, value in pairs.items() if set(value) == {"baseline", "multi-agent"}}
    report = {"matched_pairs": len(complete), "measurements": pairs,
              "target_reduction_percent": 30, "minimum_pairs": 3,
              "status": "insufficient-data", "target_met": None,
              "limitations": ["Human effort must be measured on equivalent tasks with the same acceptance criteria.",
                              "Setup and maintenance effort must be reported separately; this CSV measures task effort.",
                              "Three pairs remain a small exploratory study, not a general productivity guarantee."]}
    if len(complete) < 3 or len(complete) != len(pairs):
        return report
    if not all(item[mode]["quality_pass"] for item in complete.values() for mode in ("baseline", "multi-agent")):
        report.update(status="quality-failed", target_met=False)
        return report
    baseline = statistics.median(item["baseline"]["human_minutes"] for item in complete.values())
    multi = statistics.median(item["multi-agent"]["human_minutes"] for item in complete.values())
    reduction = 100 * (1 - multi / baseline)
    report.update(status="measured", baseline_median_minutes=baseline,
                  multi_agent_median_minutes=multi, reduction_percent=reduction, target_met=reduction >= 30)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.csv)
    except (OSError, KeyError, ValueError) as exc:
        parser.error(str(exc))
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text)
