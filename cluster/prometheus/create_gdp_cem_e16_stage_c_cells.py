#!/usr/bin/env python3
"""Create the frozen 336-cell E16 Stage-C execution registry."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import gdp_cem_e16_specs as spec


def rows() -> list[dict[str, int | str]]:
    result: list[dict[str, int | str]] = []
    for task in spec.TASKS:
        for arm in spec.STAGE_C_ARMS:
            for replicate in (1, 2, 3):
                for horizon in spec.STAGE_C_HORIZONS:
                    for shard in range(spec.STAGE_C_SHARD_COUNT):
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
    if len(result) != 336 or [row["array_id"] for row in result] != list(range(336)):
        raise RuntimeError("E16 Stage-C cell registry differs")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing existing E16 Stage-C cell registry")
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

