import numpy as np
import pytest
from sklearn import preprocessing

from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)


def stats(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scaler = preprocessing.StandardScaler().fit(values)
    return scaler.mean_, scaler.scale_


def test_exact_source_dtype_statistics_pass():
    values = np.asarray([[0.1, -0.2], [0.4, 0.8], [np.nan, np.nan]])
    mean, scale = stats(values[:2])
    report = validate_planner_action_standardizer(
        values, mean, scale, mean.copy(), scale.copy()
    )
    assert report["mode"] == "exact_source_dtype"
    assert report["maximum_absolute_difference"] == {"mean": 0.0, "scale": 0.0}


def test_exact_legacy_float32_refit_passes_and_is_reported():
    values = np.asarray(
        [[0.123456789123, -0.987654321987], [0.333333333333, 0.777777777777]],
        dtype=np.float64,
    )
    actual_mean, actual_scale = stats(values)
    expected_mean, expected_scale = stats(values.astype(np.float32))
    assert not np.array_equal(actual_mean, expected_mean)
    report = validate_planner_action_standardizer(
        values, actual_mean, actual_scale, expected_mean, expected_scale
    )
    assert report["mode"] == "exact_legacy_float32_refit"
    assert report["exact_legacy_float32_refit_match"] == {
        "mean": True,
        "scale": True,
    }


def test_unrelated_close_statistics_do_not_pass_as_legacy_float32():
    values = np.asarray([[0.1, -0.2], [0.4, 0.8]], dtype=np.float64)
    actual_mean, actual_scale = stats(values)
    with pytest.raises(RuntimeError, match="mean differs"):
        validate_planner_action_standardizer(
            values,
            actual_mean,
            actual_scale,
            actual_mean + 1.0e-12,
            actual_scale,
        )


def test_large_float32_cast_discrepancy_is_rejected():
    values = np.asarray(
        [[1.0e9 + 1.0, 1.0e9 + 3.0], [1.0e9 + 5.0, 1.0e9 + 7.0]],
        dtype=np.float64,
    )
    actual_mean, actual_scale = stats(values)
    expected_mean, expected_scale = stats(values.astype(np.float32))
    with pytest.raises(RuntimeError, match="rounding envelope"):
        validate_planner_action_standardizer(
            values, actual_mean, actual_scale, expected_mean, expected_scale
        )
