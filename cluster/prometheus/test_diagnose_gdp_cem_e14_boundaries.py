"""Unit tests for the post-E14 boundary diagnostic helpers."""

from __future__ import annotations

import numpy as np
import torch
from sklearn.preprocessing import StandardScaler

import gdp_cem_e14_specs as spec
from diagnose_gdp_cem_e14_boundaries import (
    AxisAccumulator,
    aggregate_rows,
    exact_boundary,
    near_boundary,
    outside,
    per_row_fraction,
    transform_environment_bounds,
)


def test_boundary_masks_distinguish_oob_exact_and_near() -> None:
    value = torch.tensor([[[[-1.2], [-1.0], [-0.98], [0.0], [1.0], [1.2]]]])
    low = torch.tensor([-1.0])
    high = torch.tensor([1.0])
    assert np.isclose(per_row_fraction(outside(value, low, high)).item(), 2 / 6)
    assert np.isclose(
        per_row_fraction(exact_boundary(value, low, high)).item(), 2 / 6
    )
    assert np.isclose(
        per_row_fraction(near_boundary(value, low, high, 0.011)).item(), 3 / 6
    )


def test_axis_accumulator_weights_candidate_elements() -> None:
    accumulator = AxisAccumulator(3, 2)
    accumulator.add(
        torch.tensor(
            [
                [
                    [[True, False], [False, True]],
                    [[True, True], [False, False]],
                ]
            ]
        )
    )
    result = accumulator.result()
    assert result["per_time_and_dimension"][0] == [1.0, 0.5]
    assert result["per_time_and_dimension"][1] == [0.0, 0.5]
    assert np.isnan(result["per_time_and_dimension"][2][0])


def test_aggregate_rows_keeps_equal_condition_cells() -> None:
    delta = np.asarray([pair[0] for pair in spec.DELTA_TAU_PAIRS])
    tau = np.asarray([pair[1] for pair in spec.DELTA_TAU_PAIRS])
    metric = np.arange(len(delta), dtype=np.float64)
    result = aggregate_rows(delta=delta, tau=tau, metrics={"x": metric})
    assert result["equal_cell_mean"]["x"] == float(metric.mean())
    for delta_value in spec.DELTA_VALUES:
        active = delta == delta_value
        assert result["per_delta"][str(delta_value)]["x"] == float(
            metric[active].mean()
        )


def test_environment_bounds_are_mapped_to_planner_coordinates() -> None:
    low, high = transform_environment_bounds(
        np.asarray([-1.0, -1.0], dtype=np.float32),
        np.asarray([1.0, 1.0], dtype=np.float32),
        np.asarray([0.25, -0.5], dtype=np.float64),
        np.asarray([0.5, 0.25], dtype=np.float64),
    )
    np.testing.assert_allclose(low, [-2.5, -2.0], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(high, [1.5, 6.0], rtol=0.0, atol=0.0)


def test_environment_transform_preserves_released_float32_rounding() -> None:
    environment_low = np.asarray([-1.0], dtype=np.float32)
    environment_high = np.asarray([1.0], dtype=np.float32)
    mean = np.asarray([0.0026465825646189004], dtype=np.float64)
    std = np.asarray([0.6431365217957304], dtype=np.float64)
    low, high = transform_environment_bounds(
        environment_low, environment_high, mean, std
    )
    scaler = StandardScaler()
    scaler.mean_ = mean.copy()
    scaler.scale_ = std.copy()
    scaler.var_ = np.square(std)
    scaler.n_features_in_ = 1
    scaler.n_samples_seen_ = 1
    expected = scaler.transform(
        np.stack((environment_low, environment_high), axis=0)
    )[:, 0]
    assert expected.dtype == np.float32
    assert low[0] == expected[0]
    assert high[0] == expected[1]
    shortcut = np.float32(
        (np.float64(1.0) - np.float64(0.0026465825646189004))
        / np.float64(0.6431365217957304)
    )
    assert shortcut != high[0]
