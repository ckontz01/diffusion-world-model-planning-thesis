from __future__ import annotations

import torch

import gdp_cem_e15_specs as spec
from train_gdp_cem_e15_proposer import learning_rate, masked_mean


def test_learning_rate_has_frozen_warmup_and_cosine_end() -> None:
    assert learning_rate(1) == spec.LEARNING_RATE / spec.WARMUP_STEPS
    assert learning_rate(spec.WARMUP_STEPS) == spec.LEARNING_RATE
    assert abs(learning_rate(spec.TRAIN_STEPS)) < 1.0e-15


def test_masked_mean_is_row_balanced() -> None:
    value = torch.tensor([[1.0, 3.0, 100.0], [2.0, 100.0, 100.0]])
    mask = torch.tensor([[True, True, False], [True, False, False]])
    # Row means are 2 and 2; inactive large values cannot contribute.
    assert torch.equal(masked_mean(value, mask), torch.tensor(2.0))
