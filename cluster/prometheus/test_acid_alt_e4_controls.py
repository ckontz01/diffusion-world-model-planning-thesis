"""Tests for the capacity-matched non-diffusion E4 controls."""

from __future__ import annotations

import torch

from acid_alt_e4_controls import (
    ConditionalGaussianInverse,
    DeterministicInverseRegressor,
    deterministic_inverse_costs,
    diagonal_gaussian_nll,
    gaussian_inverse_costs,
)


def test_control_models_have_expected_shapes_and_capacity() -> None:
    deterministic = DeterministicInverseRegressor(192, 10)
    gaussian = ConditionalGaussianInverse(192, 10)
    current = torch.randn(13, 192)
    successor = torch.randn(13, 192)
    deterministic_prediction = deterministic(current, successor)
    mean, log_scale = gaussian(current, successor, torch.ones(13))
    assert deterministic_prediction.shape == (13, 10)
    assert mean.shape == log_scale.shape == (13, 10)
    for model in (deterministic, gaussian):
        parameter_count = sum(parameter.numel() for parameter in model.parameters())
        assert 1_700_000 < parameter_count < 2_100_000


def test_gaussian_nll_rewards_matching_mean_and_backpropagates() -> None:
    model = ConditionalGaussianInverse(8, 4, width=32, depth=2)
    current = torch.randn(7, 8)
    successor = torch.randn(7, 8)
    target = torch.randn(7, 4)
    mean, log_scale = model(current, successor, torch.ones(7))
    loss = diagonal_gaussian_nll(mean, log_scale, target).mean()
    exact = diagonal_gaussian_nll(target, torch.zeros_like(target), target).mean()
    assert exact < diagonal_gaussian_nll(
        target + 2.0, torch.zeros_like(target), target
    ).mean()
    loss.backward()
    assert torch.isfinite(loss)
    assert all(parameter.grad is not None for parameter in model.parameters())


def test_control_candidate_costs_are_batch_invariant() -> None:
    torch.manual_seed(17)
    trajectory = torch.randn(2, 3, 6, 8)
    actions = torch.randn(2, 3, 5, 4)
    statistics = {
        "latent_mean": torch.zeros(8),
        "latent_std": torch.ones(8),
        "action_mean": torch.zeros(4),
        "action_std": torch.ones(4),
    }
    deterministic = DeterministicInverseRegressor(8, 4, width=32, depth=2).eval()
    full_deterministic = deterministic_inverse_costs(
        deterministic,
        trajectory=trajectory,
        actions=actions,
        **statistics,
        batch_size=10_000,
    )
    batched_deterministic = deterministic_inverse_costs(
        deterministic,
        trajectory=trajectory,
        actions=actions,
        **statistics,
        batch_size=7,
    )
    assert full_deterministic.shape == (2, 3)
    assert torch.allclose(
        full_deterministic, batched_deterministic, rtol=1.0e-6, atol=1.0e-6
    )

    gaussian = ConditionalGaussianInverse(8, 4, width=32, depth=2).eval()
    calibration = {"ratio_q50": -0.2, "ratio_q95": 0.0, "ratio_q99": 0.2}
    full_gaussian = gaussian_inverse_costs(
        gaussian,
        trajectory=trajectory,
        actions=actions,
        calibration=calibration,
        **statistics,
        batch_size=10_000,
    )
    batched_gaussian = gaussian_inverse_costs(
        gaussian,
        trajectory=trajectory,
        actions=actions,
        calibration=calibration,
        **statistics,
        batch_size=7,
    )
    assert full_gaussian["gaussian_tail"].shape == (2, 3)
    assert full_gaussian["transition_gaussian_ratio"].shape == (2, 3, 5)
    for name in full_gaussian:
        assert torch.allclose(
            full_gaussian[name], batched_gaussian[name], rtol=1.0e-5, atol=2.0e-6
        )
