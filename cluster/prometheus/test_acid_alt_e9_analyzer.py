#!/usr/bin/env python3
"""Focused tests for the frozen E9 conjunctive gate."""

from __future__ import annotations

import copy

from analyze_acid_alt_e9_ae_closed_loop import TASKS, gate_results


def contrast(estimate: float, lower_one: float, lower_two: float) -> dict:
    return {
        "equal_task": {
            "estimate": estimate,
            "lower_95_one_sided": lower_one,
            "lower_95_two_sided": lower_two,
        },
        "per_task": {
            task: {
                "estimate": estimate,
                "lower_95_one_sided": lower_one,
                "lower_95_two_sided": lower_two,
            }
            for task in TASKS
        },
    }


def main() -> None:
    passing = {
        "ae_minus_acid": contrast(0.03, -0.01, -0.02),
        "ae_minus_ae_shuffled": contrast(0.04, 0.02, 0.01),
        "ae_minus_b0": contrast(0.01, -0.02, -0.03),
        "ae_minus_forward": contrast(0.00, -0.02, -0.03),
    }
    assert all(gate_results(passing).values())

    failed = copy.deepcopy(passing)
    failed["ae_minus_ae_shuffled"]["per_task"]["cube"]["estimate"] = -0.001
    gates = gate_results(failed)
    assert not gates["3_ae_beats_shuffled_equal_and_positive_each_task"]
    assert not all(gates.values())

    failed = copy.deepcopy(passing)
    failed["ae_minus_acid"]["per_task"]["pusht"]["estimate"] = -0.01
    failed["ae_minus_acid"]["per_task"]["cube"]["estimate"] = -0.01
    gates = gate_results(failed)
    assert not gates["6_ae_above_acid_on_at_least_two_tasks"]
    print("E9 analyzer tests passed")


if __name__ == "__main__":
    main()
