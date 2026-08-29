from __future__ import annotations

import hashlib
import os
from pathlib import Path

import gdp_cem_e19_discrepancy_specs as spec
import gdp_cem_e19_specs as e19_spec
import pytest


def test_five_unique_prespecified_sentinels_cover_every_method() -> None:
    assert len(spec.SENTINELS) == 5
    assert len({row.sentinel_id for row in spec.SENTINELS}) == 5
    assert len({row.e19_array_id for row in spec.SENTINELS}) == 5
    assert {row.method for row in spec.SENTINELS} == {
        "base_cem",
        "far_goal_prior_cem",
        "lewm_generator",
        "generator_prior_top",
        "sage",
    }
    assert {row.benchmark for row in spec.SENTINELS} == {"pusht", "cube"}
    assert {row.seed for row in spec.SENTINELS} == {32}


def test_two_repeats_produce_exact_ten_run_registry() -> None:
    runs = spec.runs()
    assert len(runs) == 10
    assert [row[0] for row in runs] == list(range(10))
    for sentinel in spec.SENTINELS:
        assert [repeat for _, row, repeat in runs if row == sentinel] == [0, 1]


def test_planner_is_exact_e19_planner() -> None:
    assert spec.PLANNER == {
        "candidates": 300,
        "cem_rounds": 30,
        "elites": 30,
        "action_block": 5,
        "history_length": 3,
        "frameskip": 5,
        "precision": "bf16",
        "warm_start": False,
    }


def test_sentinel_array_ids_match_the_frozen_e19_grid() -> None:
    cells = e19_spec.cells()
    for sentinel in spec.SENTINELS:
        cell = cells[sentinel.e19_array_id]
        assert (
            cell.benchmark,
            cell.method,
            cell.seed,
            cell.horizon,
        ) == (
            sentinel.benchmark,
            sentinel.method,
            sentinel.seed,
            sentinel.horizon,
        )
        assert len(sentinel.e19_result_sha256) == 64


def test_five_frozen_e19_result_hashes_on_cluster() -> None:
    run_root_text = os.environ.get("E19_DIAGNOSTIC_E19_RUN_ROOT")
    if run_root_text is None:
        pytest.skip("cluster E19 run root not supplied")
    run_root = Path(run_root_text)
    for sentinel in spec.SENTINELS:
        path = (
            run_root
            / "evaluation"
            / sentinel.benchmark
            / sentinel.method
            / f"seed{sentinel.seed}"
            / f"h{sentinel.horizon}"
            / "results.json"
        )
        assert hashlib.sha256(path.read_bytes()).hexdigest() == (
            sentinel.e19_result_sha256
        )
