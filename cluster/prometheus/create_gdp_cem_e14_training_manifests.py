#!/usr/bin/env python3
"""Create identifier-only frozen E14 endpoint and SAGE training manifests."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import gdp_cem_e14_specs as spec
from train_gdp_cem_e14_endpoint import CONDITIONS


def atomic_tsv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-output", type=Path, required=True)
    parser.add_argument("--sage-output", type=Path, required=True)
    args = parser.parse_args()
    endpoint_rows: list[dict[str, object]] = []
    for task in spec.TASKS:
        for condition in CONDITIONS:
            family = condition.split("_", maxsplit=1)[1]
            seeds = (
                (spec.DIAGNOSTIC_SEED,)
                if family in ("shuffled_goal", "unconditional")
                else spec.MODEL_SEEDS
            )
            for seed in seeds:
                endpoint_rows.append(
                    {
                        "array_id": len(endpoint_rows),
                        "task": task,
                        "condition": condition,
                        "seed": seed,
                    }
                )
    sage_rows = [
        {
            "array_id": index,
            "task": task,
            "seed": seed,
        }
        for index, (task, seed) in enumerate(
            (task, seed) for task in spec.TASKS for seed in spec.MODEL_SEEDS
        )
    ]
    if len(endpoint_rows) != 32 or len(sage_rows) != 6:
        raise RuntimeError("E14 training manifest cardinality differs")
    atomic_tsv(
        args.endpoint_output,
        ("array_id", "task", "condition", "seed"),
        endpoint_rows,
    )
    atomic_tsv(args.sage_output, ("array_id", "task", "seed"), sage_rows)


if __name__ == "__main__":
    main()

