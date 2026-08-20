#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing or empty episode manifest: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--first-label", default="first")
    parser.add_argument("--second-label", default="second")
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    first = load(args.first)
    second = load(args.second)
    if len(first) != len(second):
        raise SystemExit(f"manifest row-count mismatch: {len(first)} vs {len(second)}")

    key_fields = ("eval_index", "episode_id", "start_step")
    first_keys = [tuple(row[field] for field in key_fields) for row in first]
    second_keys = [tuple(row[field] for field in key_fields) for row in second]
    if first_keys != second_keys:
        raise SystemExit("episode identity/order mismatch")

    transitions = Counter((left["status"], right["status"]) for left, right in zip(first, second))
    changes = [
        {
            "eval_index": int(left["eval_index"]),
            "episode_id": int(left["episode_id"]),
            "start_step": int(left["start_step"]),
            args.first_label: left["status"],
            args.second_label: right["status"],
        }
        for left, right in zip(first, second)
        if left["status"] != right["status"]
    ]
    first_passes = sum(row["status"] in {"PASS", "SUCCESS"} for row in first)
    second_passes = sum(row["status"] in {"PASS", "SUCCESS"} for row in second)

    result = {
        "status": "ok",
        "classification": "repeated_evaluation_determinism_diagnostic",
        "matched_episode_rows": len(first),
        "outcomes_exact": not changes,
        "changed_outcomes": changes,
        "transition_counts": {
            f"{left} -> {right}": count
            for (left, right), count in sorted(transitions.items())
        },
        args.first_label: {
            "passes": first_passes,
            "success_rate_percent": 100.0 * first_passes / len(first),
        },
        args.second_label: {
            "passes": second_passes,
            "success_rate_percent": 100.0 * second_passes / len(second),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
