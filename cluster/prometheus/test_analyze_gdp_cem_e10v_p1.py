#!/usr/bin/env python3
"""Unit tests for E10V row isolation and frozen advancement gates."""

from __future__ import annotations

import numpy as np

import analyze_gdp_cem_e10v_p1 as analysis
import evaluate_gdp_cem_e10v_p1 as e10
import train_gdp_cem_vp_proposal as train


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
    validation_rows = np.arange(40_000, dtype=np.int64)
    first_checkpoint, first_final, first_record = train.select_fresh_rows(
        validation_rows, task="pusht"
    )
    second_checkpoint, second_final, second_record = train.select_fresh_rows(
        validation_rows, task="pusht"
    )
    if (
        not np.array_equal(first_checkpoint, second_checkpoint)
        or not np.array_equal(first_final, second_final)
        or first_record != second_record
        or len(np.intersect1d(first_checkpoint, first_final))
        or len(first_checkpoint) != train.VALIDATION_COUNT
        or len(first_final) != e10.CONTEXT_COUNT
    ):
        raise RuntimeError("E10V fresh-row isolation test failed")

    labels = analysis.expected_labels()
    tasks = {
        task: {"medians": {label: metric(3.0) for label in labels}}
        for task in analysis.TASKS
    }
    target_true = "vp_true_k10_g020"
    target_shuffled = "vp_shuffled_goal_k10_g020"
    target_unconditional = "vp_true_k10_g000"
    for task in analysis.TASKS:
        tasks[task]["medians"][target_true] = metric(1.0)
        tasks[task]["medians"][target_shuffled] = metric(2.0)
        tasks[task]["medians"][target_unconditional] = metric(2.5)
        tasks[task]["medians"]["gaussian_true"] = metric(2.2)
        tasks[task]["medians"]["epsilon_true_k10"] = metric(2.4)
    record = analysis.configuration_record(tasks, steps=10, scale=2.0)
    if not record["eligible"] or not all(record["gates"].values()):
        raise RuntimeError("E10V passing-gate test failed")
    tasks["cube"]["medians"][target_true]["selected_action_mse"] = 2.3
    tasks["reacher"]["medians"][target_true]["selected_action_mse"] = 2.3
    record = analysis.configuration_record(tasks, steps=10, scale=2.0)
    if record["gates"]["4_selected_wins_at_least_two_tasks"]:
        raise RuntimeError("E10V per-task gate boundary test failed")
    print("E10V analyzer and row-isolation tests passed")


if __name__ == "__main__":
    main()
