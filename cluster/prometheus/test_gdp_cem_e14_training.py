"""Pure unit tests for E14 data and training utilities."""

from __future__ import annotations

import numpy as np
import torch

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import deterministic_group_derangement
from train_gdp_cem_e14_endpoint import learning_rate, masked_mean
from train_gdp_cem_e14_sage import subgoal_loss


def test_group_derangement_is_deterministic_cell_preserving_and_fixed_point_free() -> None:
    cells = [
        (role, delta, tau)
        for role in (0, 1)
        for delta, tau in spec.DELTA_TAU_PAIRS
        for _ in range(3)
    ]
    role = np.asarray([value[0] for value in cells], dtype=np.uint8)
    delta = np.asarray([value[1] for value in cells], dtype=np.int64)
    tau = np.asarray([value[2] for value in cells], dtype=np.int64)
    first = deterministic_group_derangement(role, delta, tau, task="pusht")
    second = deterministic_group_derangement(role, delta, tau, task="pusht")
    assert np.array_equal(first, second)
    assert np.all(first != np.arange(len(first)))
    assert np.array_equal(role[first], role)
    assert np.array_equal(delta[first], delta)
    assert np.array_equal(tau[first], tau)
    assert len(np.unique(first)) == len(first)


def test_masked_mean_normalizes_each_row_by_its_active_dimensions() -> None:
    value = torch.tensor([[1.0, 3.0, 100.0], [2.0, 4.0, 6.0]])
    mask = torch.tensor([[True, True, False], [True, True, True]])
    observed = masked_mean(value, mask)
    expected = torch.tensor(((1.0 + 3.0) / 2.0 + (2.0 + 4.0 + 6.0) / 3.0) / 2.0)
    assert torch.equal(observed, expected)


def test_learning_rate_matches_frozen_warmup_and_cosine_endpoints() -> None:
    assert learning_rate(1) == spec.LEARNING_RATE / spec.WARMUP_STEPS
    assert learning_rate(spec.WARMUP_STEPS) == spec.LEARNING_RATE
    assert abs(learning_rate(spec.TRAIN_STEPS)) < 1.0e-15


def test_sage_subgoal_loss_matches_independent_terms() -> None:
    prediction = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
    target = torch.tensor([[1.0, 0.0], [1.0, 0.0]])
    total, smooth, cosine = subgoal_loss(prediction, target)
    expected_smooth = torch.nn.functional.smooth_l1_loss(prediction, target)
    expected_cosine = (
        1.0 - torch.nn.functional.cosine_similarity(prediction, target)
    ).mean()
    assert torch.equal(smooth, expected_smooth)
    assert torch.equal(cosine, expected_cosine)
    assert torch.equal(total, expected_smooth + expected_cosine)

