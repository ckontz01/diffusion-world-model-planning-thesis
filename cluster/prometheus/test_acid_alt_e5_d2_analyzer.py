from __future__ import annotations

import numpy as np

import analyze_acid_alt_e5_d2_counterfactual as analysis


def test_pool_unit_rank_is_scale_invariant() -> None:
    base = np.tile(np.arange(analysis.CANDIDATE_COUNT), (analysis.POOL_COUNT, 1))
    assert np.array_equal(
        analysis.pool_unit_rank(base),
        analysis.pool_unit_rank(13.0 * base - 7.0),
    )


def test_collapsed_score_reproduces_b0_selection() -> None:
    goal = np.linspace(1.0, -1.0, analysis.CANDIDATE_COUNT)
    score = np.ones(analysis.CANDIDATE_COUNT)
    assert analysis.select_candidate(goal, score) == int(np.argmin(goal))


def test_fixed_composites_are_exact(tmp_path) -> None:
    generator = np.random.default_rng(7)
    shape = (analysis.POOL_COUNT, analysis.CANDIDATE_COUNT)
    baseline = {
        "goal": generator.normal(size=shape),
        "standardized_rmse": generator.random(size=shape),
        "success": generator.integers(0, 2, size=shape),
    }
    for key in analysis.BASELINE_KEYS.values():
        baseline[key] = generator.normal(size=shape)
    e5 = {
        key: generator.normal(size=shape) for key in analysis.E5_KEYS.values()
    }
    baseline_path = tmp_path / "baseline.npz"
    e5_path = tmp_path / "e5.npz"
    np.savez(baseline_path, **baseline)
    np.savez(e5_path, **e5)
    loaded = analysis.load_task("pusht", baseline_path, e5_path)
    scores = loaded["scores"]
    expected_anchor = 0.5 * (
        analysis.pool_unit_rank(scores["dide"])
        + analysis.pool_unit_rank(scores["csda"])
    )
    expected_hybrid = 0.5 * (
        analysis.pool_unit_rank(scores["forward"])
        + analysis.pool_unit_rank(scores["csda"])
    )
    assert np.array_equal(scores["dide_csda_anchor"], expected_anchor)
    assert np.array_equal(scores["forward_csda"], expected_hybrid)
