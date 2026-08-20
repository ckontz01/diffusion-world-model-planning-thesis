"""Tests for E4 candidate scoring and ACID flow-energy controls."""

from __future__ import annotations

import torch
from torch import nn

from acid_alt_e4_models import ConditionalActionDenoiser
from acid_alt_e4_scoring import (
    SCORING_SIGMAS,
    acid_flow_training_energy,
    acid_multisample_costs,
    build_acid_sample_noise_bank,
    build_action_noise_bank,
    inverse_diffusion_costs,
)


def calibration() -> dict:
    return {
        "quantiles": {
            str(sigma): {"cider_q50": -0.2, "cider_q95": 0.0, "cider_q99": 0.2}
            for sigma in SCORING_SIGMAS
        }
    }


def test_noise_bank_is_reproducible_and_keyed() -> None:
    first = build_action_noise_bank(task="pusht", scorer_seed=7101, horizon=5, action_dim=4)
    second = build_action_noise_bank(task="pusht", scorer_seed=7101, horizon=5, action_dim=4)
    other = build_action_noise_bank(task="cube", scorer_seed=7101, horizon=5, action_dim=4)
    assert torch.equal(first, second)
    assert not torch.equal(first, other)


def test_inverse_diffusion_cost_shapes_and_batch_invariance() -> None:
    torch.manual_seed(3)
    model = ConditionalActionDenoiser(8, 4, width=32, depth=2).eval()
    trajectory = torch.randn(2, 3, 6, 8)
    actions = torch.randn(2, 3, 5, 4)
    payload = {
        "latent_mean": torch.zeros(8),
        "latent_std": torch.ones(8),
        "acid_action_mean": torch.zeros(4),
        "acid_action_std": torch.ones(4),
    }
    noise = build_action_noise_bank(
        task="pusht", scorer_seed=7101, horizon=5, action_dim=4
    )
    full = inverse_diffusion_costs(
        model,
        trajectory=trajectory,
        actions=actions,
        payload=payload,
        calibration=calibration(),
        noise_bank=noise,
        batch_size=10_000,
    )
    batched = inverse_diffusion_costs(
        model,
        trajectory=trajectory,
        actions=actions,
        payload=payload,
        calibration=calibration(),
        noise_bank=noise,
        batch_size=7,
    )
    assert full["cider_tail"].shape == (2, 3)
    assert full["transition_cider"].shape == (4, 2, 3, 5)
    assert full["transition_violation"].shape == (2, 3, 5)
    for name in full:
        assert torch.allclose(full[name], batched[name], rtol=1.0e-6, atol=1.0e-6)


class FlowProbe(nn.Module):
    def forward(
        self,
        current: torch.Tensor,
        successor: torch.Tensor,
        noisy_action: torch.Tensor,
        tau: torch.Tensor,
    ) -> torch.Tensor:
        del successor
        return noisy_action + tau[:, None] * current[:, : noisy_action.shape[-1]]


def test_acid_flow_energy_batch_invariance() -> None:
    torch.manual_seed(5)
    trajectory = torch.randn(2, 3, 6, 8)
    actions = torch.randn(2, 3, 5, 4)
    noise = build_action_noise_bank(
        task="reacher", scorer_seed=7101, horizon=5, action_dim=4
    )
    model = FlowProbe()
    full = acid_flow_training_energy(
        model,
        trajectory=trajectory,
        actions=actions,
        action_mean=torch.zeros(4),
        action_std=torch.ones(4),
        noise_bank=noise,
        batch_size=10_000,
    )
    batched = acid_flow_training_energy(
        model,
        trajectory=trajectory,
        actions=actions,
        action_mean=torch.zeros(4),
        action_std=torch.ones(4),
        noise_bank=noise,
        batch_size=7,
    )
    assert full.shape == (2, 3)
    assert torch.allclose(full, batched, rtol=1.0e-6, atol=1.0e-6)


class SampleProbe(nn.Module):
    def one_step_action(
        self,
        current: torch.Tensor,
        successor: torch.Tensor,
        noise: torch.Tensor,
    ) -> torch.Tensor:
        return noise + 0.1 * (successor - current)[:, : noise.shape[-1]]


def test_acid_multisample_shapes_replay_and_batch_invariance() -> None:
    torch.manual_seed(23)
    trajectory = torch.randn(2, 3, 6, 8)
    actions = torch.randn(2, 3, 5, 4)
    first_noise = build_acid_sample_noise_bank(
        task="cube", scorer_seed=6101, horizon=5, action_dim=4
    )
    second_noise = build_acid_sample_noise_bank(
        task="cube", scorer_seed=6101, horizon=5, action_dim=4
    )
    assert torch.equal(first_noise, second_noise)
    model = SampleProbe()
    full = acid_multisample_costs(
        model,
        trajectory=trajectory,
        actions=actions,
        action_mean=torch.zeros(4),
        action_std=torch.ones(4),
        noise_bank=first_noise,
        batch_size=10_000,
    )
    batched = acid_multisample_costs(
        model,
        trajectory=trajectory,
        actions=actions,
        action_mean=torch.zeros(4),
        action_std=torch.ones(4),
        noise_bank=first_noise,
        batch_size=7,
    )
    assert full["acid_sample_mean"].shape == (2, 3)
    assert full["transition_acid_sample_min"].shape == (2, 3, 5)
    assert torch.all(
        full["transition_acid_sample_min"]
        <= full["transition_acid_sample_mean"]
    )
    for name in full:
        assert torch.allclose(full[name], batched[name], rtol=1.0e-6, atol=1.0e-6)
