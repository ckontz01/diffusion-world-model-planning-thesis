from __future__ import annotations

import numpy as np

import gdp_cem_e17_specs as spec
from train_gdp_cem_e17_transition_state_adapter import learning_rate, metric_summary


def test_metric_summary_perfect_prediction() -> None:
    target = np.asarray([[0.0, 1.0], [2.0, 3.0], [4.0, 5.0]], dtype=np.float32)
    result = metric_summary(target.copy(), target)
    assert result["standardized_rmse"] == 0.0
    assert result["maximum_coordinate_standardized_rmse"] == 0.0
    assert result["median_coordinate_r2"] == 1.0


def test_learning_rate_has_frozen_endpoints() -> None:
    assert learning_rate(1) == spec.LEARNING_RATE / spec.WARMUP_STEPS
    assert learning_rate(spec.WARMUP_STEPS) == spec.LEARNING_RATE
    assert abs(learning_rate(spec.TRAIN_STEPS)) < 1.0e-15
