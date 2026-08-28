from __future__ import annotations

import gdp_cem_e19_specs as spec


def test_exact_cell_registry() -> None:
    rows = spec.cells()
    assert len(rows) == 180
    assert [row.array_id for row in rows] == list(range(180))
    assert {
        (row.benchmark, row.method, row.seed, row.horizon) for row in rows
    } == {
        (task, method, seed, horizon)
        for task in spec.BENCHMARKS
        for method in spec.METHODS
        for seed in spec.SEEDS
        for horizon in spec.HORIZONS
    }


def test_checkpoint_selection_matches_official_methods() -> None:
    assert spec.checkpoint_paths("pusht", "base_cem") == (
        None,
        "pusht_action_prior.pt",
    )
    assert spec.checkpoint_paths("cube", "far_goal_prior_cem") == (
        None,
        "cube_far_action_prior.pt",
    )
    assert spec.checkpoint_paths("pusht", "sage") == (
        "pusht_generator.pt",
        "pusht_action_prior.pt",
    )


def test_frozen_counts_and_hashes() -> None:
    assert spec.EXPECTED_TOTAL_EPISODES == (
        spec.EXPECTED_CELLS * spec.EXPECTED_EPISODES_PER_CELL
    )
    assert len(spec.CHECKPOINTS) == 6
    for entry in spec.CHECKPOINTS.values():
        assert len(entry["sha256"]) == 64
        int(entry["sha256"], 16)
        assert entry["bytes"] > 0
