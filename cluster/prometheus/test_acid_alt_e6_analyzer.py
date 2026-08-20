#!/usr/bin/env python3
"""Deterministic synthetic tests for the E6 frozen gate logic."""

from __future__ import annotations

import numpy as np

import acid_alt_e6_quantile_models as e6
from analyze_acid_alt_e6_d2 import TASKS, analyze


def matrix(primary_value: int, shuffled_value: int, forward_value: int):
    values = {}
    for task in TASKS:
        values[task] = {arm: np.zeros(50, dtype=np.float64) for arm in e6.ARMS}
        values[task]["b0"][:30] = 1
        values[task]["acid_cont"][:31] = 1
        values[task]["forward_gate_tail5_q40"][:forward_value] = 1
        values[task]["rdx_shuffled_gate_tail5_q40"][:shuffled_value] = 1
        values[task][e6.PRIMARY_ARM][:primary_value] = 1
    return values


def main() -> None:
    passing = analyze(matrix(34, 30, 34))
    if not passing["all_pilot_promotion_gates_pass"]:
        raise RuntimeError(f"synthetic passing E6 case failed: {passing['gates']}")
    null = analyze(matrix(34, 34, 34))
    if null["gates"]["2_primary_beats_shuffled_equal_task"]:
        raise RuntimeError("equal shuffled control incorrectly passed")
    inferior = analyze(matrix(30, 28, 34))
    if inferior["gates"]["1_primary_beats_acid_equal_task"]:
        raise RuntimeError("ACID-inferior primary incorrectly passed")
    print("E6 analyzer tests: ok")


if __name__ == "__main__":
    main()
