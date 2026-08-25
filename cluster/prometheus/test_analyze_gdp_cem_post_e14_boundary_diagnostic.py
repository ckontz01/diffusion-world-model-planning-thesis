"""Unit tests for post-E14 boundary aggregation."""

from __future__ import annotations

import numpy as np

import gdp_cem_e14_specs as spec
from analyze_gdp_cem_post_e14_boundary_diagnostic import (
    KEY_METRICS,
    distribution,
    read_sha256_records,
    summarize_cells,
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
