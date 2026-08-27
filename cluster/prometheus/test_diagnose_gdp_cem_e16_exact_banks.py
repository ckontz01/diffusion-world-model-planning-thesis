from __future__ import annotations

import numpy as np

from diagnose_gdp_cem_e16_exact_banks import (
    candidate_rank_metrics,
    ordinal_rank_rows,
    pearson_rows,
)


def test_ordinal_ranks_and_correlations() -> None:
    x = np.asarray([[3.0, 1.0, 2.0], [1.0, 2.0, 3.0]])
    assert np.array_equal(ordinal_rank_rows(x), [[2, 0, 1], [0, 1, 2]])
    assert np.allclose(pearson_rows(x, x), 1.0)
    assert np.allclose(pearson_rows(x, -x), -1.0)


def test_candidate_rank_metrics() -> None:
    far = np.asarray([[0.0, 1.0, 2.0, 3.0], [3.0, 2.0, 1.0, 0.0]])
    local = np.asarray([[4.0, 3.0, 1.0, 2.0], [4.0, 1.0, 2.0, 3.0]])
    value = candidate_rank_metrics(far, local, top_k=(1, 2, 4))
    assert np.array_equal(value["local_oracle_far_rank"], [3, 3])
    assert np.array_equal(value["top_1_local_cost"], [4.0, 3.0])
    assert np.array_equal(value["top_2_local_cost"], [3.0, 2.0])
    assert np.array_equal(value["top_4_local_cost"], [1.0, 1.0])
    assert np.array_equal(value["top_4_contains_local_oracle"], [True, True])
