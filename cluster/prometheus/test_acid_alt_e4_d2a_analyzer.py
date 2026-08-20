"""Unit tests for E4-D2A analysis invariants."""

from __future__ import annotations

import numpy as np

from analyze_acid_alt_e4_d2a import (
    CANDIDATE_COUNT,
    POOL_COUNT,
    safe_spearman,
    select_candidate,
    selection_vectors,
)


def test_constant_score_has_zero_rank_and_b0_selection() -> None:
    rmse = np.linspace(0.0, 1.0, CANDIDATE_COUNT)
    score = np.zeros(CANDIDATE_COUNT)
    correlation, collapsed = safe_spearman(score, rmse)
    assert collapsed is True
    assert correlation == 0.0
    goal = np.linspace(1.0, 0.0, CANDIDATE_COUNT)
    assert select_candidate(goal, score, 0.07) == int(np.argmin(goal))


def test_spearman_direction_is_cost_consistent() -> None:
    rmse = np.linspace(0.0, 1.0, CANDIDATE_COUNT)
    positive, collapsed = safe_spearman(rmse.copy(), rmse)
    negative, _ = safe_spearman(-rmse, rmse)
    assert collapsed is False
    assert np.isclose(positive, 1.0)
    assert np.isclose(negative, -1.0)


def test_shuffled_deployment_is_exactly_b0() -> None:
    generator = np.random.default_rng(31)
    goal = generator.normal(size=(POOL_COUNT, CANDIDATE_COUNT))
    rmse = generator.uniform(size=(POOL_COUNT, CANDIDATE_COUNT))
    success = generator.integers(0, 2, size=(POOL_COUNT, CANDIDATE_COUNT))
    task = {
        "arrays": {
            "goal": goal,
            "standardized_rmse": rmse,
            "success": success,
        },
        "methods": {"e4_cider_tail": generator.normal(size=goal.shape)},
    }
    b0 = selection_vectors(task, "b0", weight=0.07)
    shuffled = selection_vectors(task, "e4_shuffled_deployment", weight=0.07)
    for name in ("rmse", "success", "oracle_regret", "index"):
        assert np.array_equal(b0[name], shuffled[name])
