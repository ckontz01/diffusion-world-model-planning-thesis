"""Synthetic tests for the frozen E14 Gate-B decision logic."""

from __future__ import annotations

import copy

import gdp_cem_e14_specs as spec
from analyze_gdp_cem_e14_offline import gate_endpoint
from train_gdp_cem_e14_endpoint import CONDITIONS


def _record(value: float, *, cvd: bool) -> dict:
    metrics = {
        "oracle_action_mse": value,
        "true_local_terminal_cost": value,
    }
    if cvd:
        metrics.update(
            {
                "oracle_generated_local_mse": value,
                "terminal_consistency": value,
            }
        )
    return {
        "bank_validity": {
            "all_finite": True,
            "minimum_unique_candidates": 300,
            "maximum_boundary_fraction": 0.02,
        },
        "aggregates": {
            "equal_cell_mean": dict(metrics),
            "per_tau": {
                str(tau): dict(metrics) for tau in spec.TAU_VALUES
            },
        },
    }


def _passing_records() -> dict[tuple[str, str, int], dict]:
    records = {}
    for task in spec.TASKS:
        for condition in CONDITIONS:
            endpoint, family = condition.split("_", maxsplit=1)
            seeds = (
                (spec.DIAGNOSTIC_SEED,)
                if family in ("shuffled_goal", "unconditional")
                else spec.MODEL_SEEDS
            )
            value = 1.0 if family == "true" else 2.0 if family == "gaussian" else 3.0
            for seed in seeds:
                records[(task, condition, seed)] = _record(
                    value, cvd=endpoint == "cvd"
                )
    return records


def test_both_endpoints_pass_when_every_frozen_comparison_passes() -> None:
    records = _passing_records()
    for endpoint in ("vad", "cvd"):
        result = gate_endpoint(records, endpoint)
        assert result["eligible_for_gate_c"] is True
        assert all(result["gates"].values())


def test_one_bad_bank_blocks_only_its_endpoint() -> None:
    records = _passing_records()
    broken = copy.deepcopy(records)
    broken[("pusht", "vad_true", 6102)]["bank_validity"][
        "minimum_unique_candidates"
    ] = 284
    assert gate_endpoint(broken, "vad")["eligible_for_gate_c"] is False
    assert gate_endpoint(broken, "cvd")["eligible_for_gate_c"] is True


def test_task_duration_rule_is_enforced_for_every_seed() -> None:
    records = _passing_records()
    for tau in (15, 20):
        records[("cube", "vad_true", 6103)]["aggregates"]["per_tau"][str(tau)][
            "oracle_action_mse"
        ] = 4.0
    result = gate_endpoint(records, "vad")
    assert result["eligible_for_gate_c"] is False
    assert (
        result["gates"][
            "direction_holds_each_task_two_of_three_durations_each_seed"
        ]
        is False
    )

