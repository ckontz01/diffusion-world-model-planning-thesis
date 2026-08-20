#!/usr/bin/env python3
"""Unit tests for E10M confirmation rows and multiseed gates."""

from __future__ import annotations

import numpy as np

import analyze_gdp_cem_e10m_p1 as analysis
import train_gdp_cem_e10m_models as train


def metric(value: float) -> dict[str, float]:
    return {
        "selected_action_mse": value,
        "oracle_action_mse": value,
        "minimum_goal_cost": value,
        "candidate_variance": 0.5,
        "unique_candidates": 300.0,
        "boundary_fraction": 0.01,
        "generation_seconds": 1.0,
        "rollout_seconds": 1.0,
    }


def main() -> None:
    validation = np.arange(60_000, dtype=np.int64)
    first = train.select_confirmation_rows(validation, task="cube")
    second = train.select_confirmation_rows(validation, task="cube")
    if any(not np.array_equal(a, b) for a, b in zip(first[:3], second[:3])):
        raise RuntimeError("E10M confirmation selection is not deterministic")
    checkpoint, final, confirmation, record = first
    if (
        len(checkpoint) != 8_192
        or len(final) != 512
        or len(confirmation) != 1_024
        or len(np.intersect1d(checkpoint, confirmation))
        or len(np.intersect1d(final, confirmation))
        or record["confirmation_rows_sha256"]
        != train.e10v.array_sha256(confirmation)
    ):
        raise RuntimeError("E10M confirmation isolation test failed")

    tasks = {task: {"medians": {}} for task in analysis.TASKS}
    for task in analysis.TASKS:
        for condition in analysis.CONDITIONS:
            tasks[task]["medians"][f"seed6102_{condition}"] = metric(2.0)
        tasks[task]["medians"]["seed6102_vp_true"] = metric(1.0)
    passing = analysis.seed_record(tasks, 6102)
    if not passing["seed_pass"] or not all(passing["gates"].values()):
        raise RuntimeError("E10M passing seed-gate test failed")
    tasks["cube"]["medians"]["seed6102_vp_true"]["selected_action_mse"] = 2.5
    tasks["reacher"]["medians"]["seed6102_vp_true"]["selected_action_mse"] = 2.5
    failing = analysis.seed_record(tasks, 6102)
    if failing["gates"]["5_selected_wins_at_least_two_tasks"]:
        raise RuntimeError("E10M per-task seed-gate test failed")
    print("E10M analyzer and confirmation-row tests passed")


if __name__ == "__main__":
    main()
