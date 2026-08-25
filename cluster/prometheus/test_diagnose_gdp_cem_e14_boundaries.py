"""Unit tests for the post-E14 boundary diagnostic helpers."""

from __future__ import annotations

import numpy as np
import torch

import gdp_cem_e14_specs as spec
from diagnose_gdp_cem_e14_boundaries import (
    AxisAccumulator,
    aggregate_rows,
    exact_boundary,
    near_boundary,
    outside,
    per_row_fraction,
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
