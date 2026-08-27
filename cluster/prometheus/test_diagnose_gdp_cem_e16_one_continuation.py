from __future__ import annotations

import numpy as np
import torch

from diagnose_gdp_cem_e16_one_continuation import (
    deterministic_second_noise,
    ordinal_rank,
)


def test_second_noise_is_keyed_and_reproducible() -> None:
    rows = np.asarray([100, 200], dtype=np.int64)
    first = deterministic_second_noise(
        task="pusht", cache_rows=rows, candidates=3, dimensions=5
    )
    second = deterministic_second_noise(
        task="pusht", cache_rows=rows, candidates=3, dimensions=5
    )
    changed = deterministic_second_noise(
        task="cube", cache_rows=rows, candidates=3, dimensions=5
    )
    assert torch.equal(first, second)
    assert not torch.equal(first, changed)
    assert first.shape == (2, 3, 5)


def test_ordinal_rank() -> None:
    value = torch.tensor([[3.0, 1.0, 2.0], [2.0, 3.0, 1.0]])
    assert torch.equal(ordinal_rank(value), torch.tensor([[2, 0, 1], [1, 2, 0]]))
