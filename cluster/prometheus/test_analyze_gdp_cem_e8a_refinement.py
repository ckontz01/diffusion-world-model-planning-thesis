#!/usr/bin/env python3
"""Focused tests for the frozen E8A cross-task gate and tie-break."""

from __future__ import annotations

import copy

from analyze_gdp_cem_e8a_refinement import (
    FRACTIONS,
    RESTARTS,
    REVERSE_STEPS,
    TASKS,
    choose_configuration,
    configuration_record,
    label,
)


def fixture() -> dict:
    metrics = {}
    base = {
        "selected_action_mse": 1.0,
        "oracle_action_mse": 0.5,
        "minimum_goal_cost": 2.0,
        "candidate_variance": 1.0,
        "unique_candidates": 300.0,
        "boundary_fraction": 0.01,
        "refinement_displacement_mse": 0.0,
        "generation_seconds": 0.01,
        "rollout_seconds": 0.02,
    }
    metrics["gaussian_base"] = base
    for restart in RESTARTS:
        for steps in REVERSE_STEPS:
            for fraction in FRACTIONS:
                true = copy.deepcopy(base)
                true.update(
                    selected_action_mse=0.8,
                    oracle_action_mse=0.49,
                    minimum_goal_cost=1.8,
                    refinement_displacement_mse=0.1,
                )
                shuffled = copy.deepcopy(base)
                shuffled.update(
                    selected_action_mse=0.9,
                    oracle_action_mse=0.51,
                    minimum_goal_cost=1.9,
                    refinement_displacement_mse=0.1,
                )
                metrics[label("true", restart, steps, fraction)] = true
                metrics[label("shuffled", restart, steps, fraction)] = shuffled
    return {task: {"per_task_medians": copy.deepcopy(metrics)} for task in TASKS}


def main() -> None:
    tasks = fixture()
    passing = configuration_record(
        tasks, restart=10, reverse_steps=5, fraction=0.25
    )
    assert passing["eligible"]
    assert passing["selected_task_wins"] == 3
    assert passing["goal_task_wins"] == 3

    failed = fixture()
    failed["cube"]["per_task_medians"][label("true", 10, 5, 0.25)][
        "oracle_action_mse"
    ] = 0.8
    record = configuration_record(
        failed, restart=10, reverse_steps=5, fraction=0.25
    )
    assert not record["eligible"]
    assert not record["gates"]["true_oracle_within_2pct_gaussian_equal_task"]

    records = []
    for restart, steps, fraction, selected, goal in (
        (20, 5, 0.50, 0.7, 1.7),
        (10, 10, 0.25, 0.7, 1.7),
        (10, 5, 1.00, 0.7, 1.7),
        (10, 1, 0.50, 0.7, 1.7),
        (10, 1, 0.25, 0.7, 1.7),
    ):
        item = copy.deepcopy(passing)
        item["restart_timestep"] = restart
        item["reverse_evaluations"] = steps
        item["refined_fraction"] = fraction
        item["equal_task_metrics"]["selected_action_mse"]["true"] = selected
        item["equal_task_metrics"]["minimum_goal_cost"]["true"] = goal
        records.append(item)
    selected = choose_configuration(records)
    assert selected is not None
    assert (
        selected["restart_timestep"],
        selected["reverse_evaluations"],
        selected["refined_fraction"],
    ) == (10, 1, 0.25)
    assert choose_configuration([{**passing, "eligible": False}]) is None
    print("E8A analyzer tests passed")


if __name__ == "__main__":
    main()
