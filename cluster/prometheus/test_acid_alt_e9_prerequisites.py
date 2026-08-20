#!/usr/bin/env python3
"""Validate the exact E9 protocol and disclosed failed v3 Stage-A result."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluate_acid_alt_d2 import validate_e9_prerequisites


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--stage-a", type=Path, required=True)
    args = parser.parse_args()
    value = validate_e9_prerequisites(args.protocol, args.stage_a)
    assert value["all_stage_a_gates_pass"] is False
    assert value["decision"] == "stop_before_stage_b"
    print("E9 prerequisite tests passed")


if __name__ == "__main__":
    main()
