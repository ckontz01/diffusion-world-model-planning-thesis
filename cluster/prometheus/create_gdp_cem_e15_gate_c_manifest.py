#!/usr/bin/env python3
"""Create the identifier-only 432-cell E15 Gate-C execution manifest."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import gdp_cem_e15_specs as spec


def rows() -> list[dict[str, int | str]]:
    result: list[dict[str, int | str]] = []
    for task in spec.TASKS:
        for arm in spec.ARMS:
            for replicate in (1, 2, 3):
                for horizon in spec.GATE_C_HORIZONS:
                    for shard in range(spec.GATE_C_SHARD_COUNT):
                        result.append(
                            {
                                "array_id": len(result),
                                "task": task,
                                "arm": arm,
                                "replicate": replicate,
                                "learned_seed": 7200 + replicate,
                                "sage_seed": 6100 + replicate,
                                "horizon": horizon,
                                "shard": shard,
                            }
                        )
    if len(result) != 432 or [row["array_id"] for row in result] != list(range(432)):
        raise RuntimeError("E15 Gate-C cell registry differs")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing existing E15 Gate-C cell manifest")
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
                "sage_seed",
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
