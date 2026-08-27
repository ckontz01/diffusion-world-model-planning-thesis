from __future__ import annotations

import numpy as np

import gdp_cem_e18_specs as spec
from analyze_gdp_cem_e18 import (
    clustered_bootstrap,
    gate_decision,
    paired_differences,
    rate_tables,
)


def synthetic_success() -> np.ndarray:
    value = np.zeros(
        (
            len(spec.TASKS),
            spec.BASE_STARTS,
            len(spec.ARMS),
            len(spec.HORIZONS),
            len(spec.MODEL_SEEDS),
        ),
        dtype=np.float64,
    )
    value[:, :, spec.ARMS.index("vad_continuation")] = 1.0
    return value


def test_task_first_rates_and_frozen_gates() -> None:
    success = synthetic_success()
    rates = rate_tables(success)
    assert rates["equal_task_equal_horizon"]["vad_continuation"] == 1.0
    differences = paired_differences(success)
    decision = gate_decision(differences)
    assert decision["continuation_mechanism_passed"]
    assert decision["diffusion_specificity_passed"]
    assert decision["joint_exploratory_signal_passed"]


def test_cluster_bootstrap_uses_start_clusters(monkeypatch) -> None:
    monkeypatch.setattr(spec, "BOOTSTRAP_RESAMPLES", 100)
    result = clustered_bootstrap(synthetic_success())
    assert result["unit"] == "task_base_start_cluster"
    assert result["arms_horizons_replicates_retained_paired"] is True
    assert result["seeds_resampled_as_independent"] is False
    assert result["vad_continuation_minus_comparator_equal_95ci"][
        "vad_greedy_576"
    ] == [1.0, 1.0]
