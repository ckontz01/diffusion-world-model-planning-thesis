#!/usr/bin/env python3
"""Write the frozen ten-run E19 discrepancy sentinel registry."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import gdp_cem_e19_discrepancy_specs as spec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "array_id",
        "sentinel_id",
        "repeat",
        "e19_array_id",
        "benchmark",
        "method",
        "seed",
        "horizon",
        "e19_result_sha256",
    )
    with args.output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for array_id, sentinel, repeat in spec.runs():
            writer.writerow(
                {
                    "array_id": array_id,
                    "sentinel_id": sentinel.sentinel_id,
                    "repeat": repeat,
                    "e19_array_id": sentinel.e19_array_id,
                    "benchmark": sentinel.benchmark,
                    "method": sentinel.method,
                    "seed": sentinel.seed,
                    "horizon": sentinel.horizon,
                    "e19_result_sha256": sentinel.e19_result_sha256,
                }
            )


if __name__ == "__main__":
    main()
