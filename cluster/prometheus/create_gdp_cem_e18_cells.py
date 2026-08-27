#!/usr/bin/env python3
"""Create the frozen 240-cell E18 execution registry."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import gdp_cem_e18_specs as spec


def rows() -> list[dict[str, int | str]]:
    result: list[dict[str, int | str]] = []
    for task in spec.TASKS:
        for arm in spec.ARMS:
            for replicate, learned_seed in enumerate(spec.MODEL_SEEDS, start=1):
                for horizon in spec.HORIZONS:
                    for shard in range(spec.SHARD_COUNT):
                        result.append(
                            {
                                "array_id": len(result),
                                "task": task,
                                "arm": arm,
                                "replicate": replicate,
                                "learned_seed": learned_seed,
                                "horizon": horizon,
                                "shard": shard,
                            }
                        )
    expected = (
        len(spec.TASKS)
        * len(spec.ARMS)
        * len(spec.MODEL_SEEDS)
        * len(spec.HORIZONS)
        * spec.SHARD_COUNT
    )
    if expected != 240 or len(result) != expected:
        raise RuntimeError("E18 execution-registry cardinality differs")
    if [row["array_id"] for row in result] != list(range(expected)):
        raise RuntimeError("E18 execution-registry identifiers differ")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing existing E18 execution registry")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "array_id",
                "task",
                "arm",
                "replicate",
                "learned_seed",
                "horizon",
                "shard",
            ),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows())


if __name__ == "__main__":
    main()
