import numpy as np
from acid_alternative_diagnostics.analyze_candidate_audit import (
    cluster_bootstrap_mean,
    rankdata,
    spearman,
)


def test_rankdata_uses_average_tie_ranks():
    assert np.array_equal(rankdata(np.array([3.0, 1.0, 1.0])), [3.0, 1.5, 1.5])


def test_spearman_has_expected_direction():
    assert np.isclose(spearman(np.arange(5), np.arange(5)), 1.0)
    assert np.isclose(spearman(np.arange(5), np.arange(4, -1, -1)), -1.0)


def test_cluster_bootstrap_is_reproducible_and_preserves_point_estimate():
    values = np.arange(12, dtype=np.float64).reshape(3, 4)
    first = cluster_bootstrap_mean(values, seed=7, repetitions=100)
    second = cluster_bootstrap_mean(values, seed=7, repetitions=100)
    assert first == second
    assert first["estimate"] == values.mean()
