from __future__ import annotations

import torch
from torch import nn

from acid_alt_e4_scoring import NOISE_DRAWS, SCORING_SIGMAS
from acid_alt_e5_counterfactual import (
    COUNTERFACTUAL_OFFSETS,
    counterfactual_successor_costs,
    network_pairs_per_sequence,
)


class DeltaOracle(nn.Module):
    def forward(
        self,
        current: torch.Tensor,
        successor: torch.Tensor,
        noisy_action: torch.Tensor,
        sigma: torch.Tensor,
        successor_present: torch.Tensor,
    ) -> torch.Tensor:
        del noisy_action, sigma, successor_present
        return successor[..., :1] - current[..., :1]


class ConditionBlindOracle(nn.Module):
    def forward(
        self,
        current: torch.Tensor,
        successor: torch.Tensor,
        noisy_action: torch.Tensor,
        sigma: torch.Tensor,
        successor_present: torch.Tensor,
    ) -> torch.Tensor:
        del current, successor, sigma, successor_present
        return noisy_action


def fixture() -> tuple[torch.Tensor, torch.Tensor, dict[str, object], torch.Tensor]:
    pools, candidates, horizon = 2, 300, 2
    action = torch.arange(candidates, dtype=torch.float32).reshape(1, candidates, 1, 1)
    action = action.expand(pools, candidates, horizon, 1) / 100.0
    current = torch.zeros(pools, candidates, horizon, 2)
    current[:, :, 1] = action[:, :, 0]
    successor = current.clone()
    successor[..., :1] += action
    trajectory = torch.cat((current[:, :, :1], successor), dim=2)
    # Reconstruct a valid Markov chain while retaining candidate-specific deltas.
    trajectory[:, :, 1] = successor[:, :, 0]
    trajectory[:, :, 2] = trajectory[:, :, 1]
    trajectory[:, :, 2, :1] += action[:, :, 1]
    payload = {
        "latent_mean": [0.0, 0.0],
        "latent_std": [1.0, 1.0],
        "acid_action_mean": [0.0],
        "acid_action_std": [1.0],
    }
    noise = torch.zeros(len(SCORING_SIGMAS), NOISE_DRAWS, horizon, 1)
    return trajectory, action, payload, noise


def test_matching_successor_beats_counterfactuals() -> None:
    trajectory, action, payload, noise = fixture()
    result = counterfactual_successor_costs(
        DeltaOracle(),
        trajectory=trajectory,
        actions=action,
        payload=payload,
        noise_bank=noise,
        batch_size=113,
    )
    assert result["dide_replay"].shape == (2, 300)
    assert torch.all(result["dide_replay"] == 0)
    assert torch.all(result["csda_log_tail_k8"] < 0)
    assert torch.all(result["csda_pairwise_tail_k8"] == 0)


def test_condition_blind_null_is_exactly_indifferent() -> None:
    trajectory, action, payload, noise = fixture()
    result = counterfactual_successor_costs(
        ConditionBlindOracle(),
        trajectory=trajectory,
        actions=action,
        payload=payload,
        noise_bank=noise,
        batch_size=257,
    )
    assert torch.allclose(result["csda_log_tail_k8"], torch.zeros(2, 300))
    assert torch.all(result["csda_pairwise_tail_k8"] == 0.5)


def test_offset_and_call_count_contract() -> None:
    assert len(COUNTERFACTUAL_OFFSETS) == 16
    assert len(set(COUNTERFACTUAL_OFFSETS)) == 16
    assert 0 not in COUNTERFACTUAL_OFFSETS
    assert network_pairs_per_sequence(8) == 720
