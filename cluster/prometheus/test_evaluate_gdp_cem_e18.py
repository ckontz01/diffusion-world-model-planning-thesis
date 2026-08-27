from __future__ import annotations

import pytest

import gdp_cem_e18_specs as spec
from evaluate_gdp_cem_e18 import validate_diagnostics


def record(*, arm: str, delta: int) -> dict[str, object]:
    continuation = spec.is_continuation_arm(arm) and delta >= 30
    per_context = (
        576
        if continuation or arm == "vad_greedy_576"
        else 300
        if arm == "vad_greedy_300"
        else 64
    )
    return {
        "call": 0,
        "arm": arm,
        "delta": delta,
        "tau": 15,
        "first_candidate_count": spec.first_candidate_count(arm),
        "continuations_per_first": 8 if continuation else 0,
        "continuation_best_count": 2 if continuation else 0,
        "lewm_rollout_trajectories": spec.SHARD_SIZE * per_context,
        "minimum_first_unique_candidates": spec.MINIMUM_FIRST_UNIQUE[arm],
        "minimum_second_unique_candidates_per_first": 7 if continuation else None,
        "predicted_state_absolute_max": 3.0 if continuation else None,
        "predicted_state_absolute_q99": 2.0 if continuation else None,
        "strict_legal_oob_fraction": 0.0,
        "exact_legal_boundary_fraction": 0.0,
        "component_timing_method": "cuda_events_resolved_after_outer_stage_synchronize",
        "end_to_end_stage_seconds": 1.0,
        "proposal_and_selection_seconds": 0.2,
        "adapter_seconds": 0.1 if continuation else 0.0,
        "lewm_scoring_seconds": 0.6,
        "encoding_seconds": 0.1,
    }


def test_continuation_and_terminal_budgets() -> None:
    assert validate_diagnostics("vad_continuation", [record(arm="vad_continuation", delta=75)]) == 3 * 576
    assert validate_diagnostics("vad_continuation", [record(arm="vad_continuation", delta=15)]) == 3 * 64
    assert validate_diagnostics("vad_greedy_576", [record(arm="vad_greedy_576", delta=75)]) == 3 * 576


def test_invalid_uniqueness_is_rejected() -> None:
    value = record(arm="direct_gmm_continuation", delta=75)
    value["minimum_second_unique_candidates_per_first"] = 6
    with pytest.raises(RuntimeError):
        validate_diagnostics("direct_gmm_continuation", [value])
