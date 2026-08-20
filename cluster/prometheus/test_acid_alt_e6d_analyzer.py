#!/usr/bin/env python3
"""Synthetic frozen-gate tests for E6D."""

from __future__ import annotations

import numpy as np

from acid_alt_e6d_allgate import ARMS
from analyze_acid_alt_e6d_d2 import ALL_ARMS, TASKS, analyze


def case(true: int, shuffled: int, forward: int, acid: int):
    result = {}
    for task in TASKS:
        result[task] = {arm: np.zeros(50, dtype=np.float64) for arm in ALL_ARMS}
        for arm, count in (("rdx_gate_all_q40", true), ("acid_cont", acid), ("rdx_shuffled_gate_all_q40", shuffled), ("forward_gate_all_q40", forward), ("acid_gate_all_q40", acid - 1)):
            result[task][arm][:count] = 1
    return result


def main() -> None:
    if set(ARMS) != {"rdx_shuffled_gate_all_q40", "forward_gate_all_q40", "acid_gate_all_q40"}:
        raise RuntimeError("E6D arm registry differs")
    passing = analyze(case(40, 37, 38, 42))
    if not passing["all_e6d_gates_pass"]:
        raise RuntimeError(f"passing E6D synthetic case failed: {passing['gates']}")
    shuffled = analyze(case(40, 40, 38, 42))
    if shuffled["gates"]["1_true_beats_shuffled_equal_task"]:
        raise RuntimeError("equal shuffled E6D control passed")
    forward = analyze(case(40, 37, 41, 42))
    if forward["gates"]["2_true_beats_forward_equal_task"]:
        raise RuntimeError("forward-superior E6D case passed")
    print("E6D analyzer tests: ok")


if __name__ == "__main__":
    main()
