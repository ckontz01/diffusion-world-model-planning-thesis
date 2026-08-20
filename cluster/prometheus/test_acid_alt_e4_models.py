"""Unit tests for the E4 inverse-diffusion model and calibration primitives."""

from __future__ import annotations

import torch

from acid_alt_e4_models import (
    ConditionalActionDenoiser,
    calibrated_transition_violation,
    cider_ratio,
    count_parameters,
    reconstruction_energy,
    upper_tail_horizon_mean,
)
from train_acid_alt_e4_didm import fixed_derangement


def test_model_shapes_backward_and_capacity_scale() -> None:
    model = ConditionalActionDenoiser(192, 10)
    current = torch.randn(11, 192)
    successor = torch.randn(11, 192)
    action = torch.randn(11, 10)
    sigma = torch.tensor([0.25, 0.5, 1.0, 2.0, 4.0, 0.5, 1.0, 2.0, 4.0, 1.0, 0.5])
    prediction = model(
        current,
        successor,
        action + sigma[:, None] * torch.randn_like(action),
        sigma,
        torch.ones(11),
    )
    assert prediction.shape == action.shape
    loss = reconstruction_energy(prediction, action).mean()
    loss.backward()
    assert torch.isfinite(loss)
    assert all(parameter.grad is not None for parameter in model.parameters())
    assert 1_800_000 < count_parameters(model) < 2_100_000


def test_successor_dropped_branch_is_explicit() -> None:
    torch.manual_seed(7)
    model = ConditionalActionDenoiser(8, 3, width=32, depth=2)
    current = torch.randn(5, 8)
    successor = torch.randn(5, 8)
    noisy_action = torch.randn(5, 3)
    sigma = torch.ones(5)
    dropped_a = model(
        current, torch.zeros_like(successor), noisy_action, sigma, torch.zeros(5)
    )
    dropped_b = model(
        current, torch.zeros_like(successor), noisy_action, sigma, torch.zeros(5)
    )
    conditional = model(current, successor, noisy_action, sigma, torch.ones(5))
    assert torch.equal(dropped_a, dropped_b)
    assert not torch.equal(dropped_a, conditional)


def test_cider_direction_and_tail_calibration() -> None:
    conditional = torch.tensor([0.1, 0.5, 2.0])
    current_only = torch.tensor([1.0, 1.0, 1.0])
    ratio = cider_ratio(conditional, current_only)
    assert ratio[0] < ratio[1] < ratio[2]
    violation = calibrated_transition_violation(
        torch.tensor([-1.0, 0.1, 0.5, 20.0]),
        q95=torch.tensor(0.1),
        q99=torch.tensor(0.3),
    )
    assert torch.equal(violation[:2], torch.zeros(2))
    assert torch.isclose(violation[2], torch.tensor(2.0))
    assert torch.isclose(violation[3], torch.tensor(10.0))


def test_upper_tail_horizon_reduction() -> None:
    transition_cost = torch.tensor([[1.0, 9.0, 3.0, 7.0, 2.0]])
    result = upper_tail_horizon_mean(transition_cost, count=2)
    assert torch.equal(result, torch.tensor([8.0]))


def test_fixed_derangement_is_reproducible_and_has_no_fixed_points() -> None:
    first = fixed_derangement(101, seed=42)
    second = fixed_derangement(101, seed=42)
    assert torch.equal(first, second)
    assert torch.equal(first.sort().values, torch.arange(101))
    assert not torch.any(first == torch.arange(101))
