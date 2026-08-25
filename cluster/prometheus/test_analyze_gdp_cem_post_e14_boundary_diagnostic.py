"""Unit tests for post-E14 boundary aggregation."""

from __future__ import annotations

import numpy as np
import pytest

import gdp_cem_e14_specs as spec
from analyze_gdp_cem_post_e14_boundary_diagnostic import (
    KEY_METRICS,
    LEGAL_SOURCE_SHA256,
    RAW_ENVIRONMENT_TOLERANCE,
    distribution,
    read_sha256_records,
    summarize_cells,
    validate_bounds,
)


def test_distribution_reports_frozen_quantiles() -> None:
    value = np.arange(spec.VALIDATION_ROWS, dtype=np.float64)
    result = distribution(value)
    assert result["minimum"] == 0.0
    assert result["maximum"] == float(spec.VALIDATION_ROWS - 1)
    assert result["median"] == float(np.quantile(value, 0.5))


def test_checksum_reader_accepts_gnu_records(tmp_path) -> None:
    path = tmp_path / "sha256.txt"
    path.write_text(f"{'a' * 64}  summary.json\n{'b' * 64} *row-metrics.h5\n")
    assert read_sha256_records(path) == {
        "summary.json": "a" * 64,
        "row-metrics.h5": "b" * 64,
    }


def test_summarize_cells_weights_tasks_and_seeds_equally() -> None:
    cells = {
        task: {
            str(seed): {
                "equal_cell_mean": {
                    metric: float(task_index * 10 + seed_index)
                    for metric in KEY_METRICS
                }
            }
            for seed_index, seed in enumerate(spec.MODEL_SEEDS)
        }
        for task_index, task in enumerate(spec.TASKS)
    }
    result = summarize_cells(cells)
    for metric in KEY_METRICS:
        assert result["task_seed_mean"]["pusht"][metric] == 1.0
        assert result["task_seed_mean"]["cube"][metric] == 11.0
        assert result["equal_task_seed_mean"][metric] == 6.0


def test_validate_bounds_rejects_one_ulp_shortcut() -> None:
    task = "cube"
    dimension = int(spec.TASK_SPEC[task]["primitive_action_dim"])
    low = np.full(dimension, -1.0, dtype=np.float32)
    high = np.full(dimension, 1.0, dtype=np.float32)
    mean = np.asarray([0.01, -0.003, 0.0026, 0.0004, 0.159], dtype=np.float64)
    std = np.asarray([0.289, 0.394, 0.643, 0.393, 0.250], dtype=np.float64)

    def transform_pair(low_value: np.ndarray, high_value: np.ndarray):
        result = np.stack((low_value, high_value), axis=0).astype(
            np.float32, copy=True
        )
        result -= mean.astype(np.float32)
        result /= std.astype(np.float32)
        return result[0], result[1]

    strict_low, strict_high = transform_pair(low, high)
    tolerant_low, tolerant_high = transform_pair(
        low - RAW_ENVIRONMENT_TOLERANCE,
        high + RAW_ENVIRONMENT_TOLERANCE,
    )

    bounds = {
        "environment_legal_low": low.tolist(),
        "environment_legal_high": high.tolist(),
        "planner_primitive_action_mean": mean.tolist(),
        "planner_primitive_action_std": std.tolist(),
        "planner_coordinate_legal_low": strict_low.tolist(),
        "planner_coordinate_legal_high": strict_high.tolist(),
        "raw_environment_tolerance": RAW_ENVIRONMENT_TOLERANCE,
        "planner_coordinate_tolerant_legal_low": tolerant_low.tolist(),
        "planner_coordinate_tolerant_legal_high": tolerant_high.tolist(),
        "transition_h5_sha256": spec.TASK_SPEC[task]["transition_sha256"],
        "legal_bound_source_sha256": LEGAL_SOURCE_SHA256[task],
        "legal_bound_interpretation": (
            "deployed_environment_action_space_mapped_through_the_exact_"
            "released_float32_planner_StandardScaler_with_strict_and_"
            "four_epsilon_tolerant_diagnostics"
        ),
    }
    assert validate_bounds(bounds, task=task) is bounds
    corrupted = dict(bounds)
    bad = np.asarray(corrupted["planner_coordinate_legal_high"], dtype=np.float32)
    bad[2] = np.nextafter(bad[2], np.float32(0.0))
    corrupted["planner_coordinate_legal_high"] = bad.tolist()
    with pytest.raises(RuntimeError, match="legal bounds differ"):
        validate_bounds(corrupted, task=task)
