#!/usr/bin/env python3
"""Write the exact 180-cell official SAGE reproduction registry."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import gdp_cem_e19_specs as spec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    with args.output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["array_id", "benchmark", "method", "seed", "horizon"])
        for row in spec.cells():
            writer.writerow(
                [row.array_id, row.benchmark, row.method, row.seed, row.horizon]
            )


if __name__ == "__main__":
    main()
