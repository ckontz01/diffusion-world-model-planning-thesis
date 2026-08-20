"""Models and score primitives for the E4 conditional inverse-diffusion study.

E4 deliberately lives outside the frozen v1-v3 packages.  It predicts a clean
standardized action block from a noisy action and a latent endpoint pair.  A
successor-dropped branch estimates the current-state-only action model used in
the CIDER evidence ratio.
"""

from __future__ import annotations

import math

import torch
from torch import nn


def sinusoidal_embedding(value: torch.Tensor, dimension: int) -> torch.Tensor:
    """Embed scalar log-noise values with deterministic sinusoidal features."""

    if dimension <= 0 or dimension % 2:
        raise ValueError("embedding dimension must be positive and even")
    half = dimension // 2
    frequency = torch.exp(
        -math.log(10_000.0)
        * torch.arange(half, device=value.device, dtype=value.dtype)
        / max(half - 1, 1)
    )
    phase = value[..., None] * frequency
    return torch.cat((torch.sin(phase), torch.cos(phase)), dim=-1)


class ResidualMLPBlock(nn.Module):
    """Pre-normalized residual MLP block."""

    def __init__(self, width: int, expansion: int = 2) -> None:
        super().__init__()
        if min(width, expansion) <= 0:
            raise ValueError("block dimensions must be positive")
        self.norm = nn.LayerNorm(width)
        self.network = nn.Sequential(
            nn.Linear(width, width * expansion),
            nn.SiLU(),
            nn.Linear(width * expansion, width),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return value + self.network(self.norm(value))


class ConditionalActionDenoiser(nn.Module):
    """Predict a clean action from its noisy version and latent endpoints."""

    def __init__(
        self,
        latent_dim: int,
        action_dim: int,
        *,
        width: int = 384,
        depth: int = 3,
        noise_embedding_dim: int = 64,
    ) -> None:
        super().__init__()
        if min(latent_dim, action_dim, width, depth, noise_embedding_dim) <= 0:
            raise ValueError("model dimensions must be positive")
        if noise_embedding_dim % 2:
            raise ValueError("noise embedding dimension must be even")
        self.latent_dim = int(latent_dim)
        self.action_dim = int(action_dim)
        self.width = int(width)
        self.depth = int(depth)
        self.noise_embedding_dim = int(noise_embedding_dim)
        input_dim = (
            2 * self.latent_dim
            + self.action_dim
            + self.noise_embedding_dim
            + 1
        )
        self.input_projection = nn.Linear(input_dim, self.width)
        self.blocks = nn.ModuleList(
            [ResidualMLPBlock(self.width, expansion=2) for _ in range(self.depth)]
        )
        self.output_norm = nn.LayerNorm(self.width)
        self.output = nn.Linear(self.width, self.action_dim)

    def forward(
        self,
        current: torch.Tensor,
        successor: torch.Tensor,
        noisy_action: torch.Tensor,
        sigma: torch.Tensor,
        successor_present: torch.Tensor,
    ) -> torch.Tensor:
        if current.shape != successor.shape:
            raise ValueError("current and successor shapes differ")
        if current.shape[-1] != self.latent_dim:
            raise ValueError("invalid latent width")
        if noisy_action.shape[:-1] != current.shape[:-1]:
            raise ValueError("action and latent leading shapes differ")
        if noisy_action.shape[-1] != self.action_dim:
            raise ValueError("invalid action width")

        leading = current.shape[:-1]
        sigma_flat = (
            torch.as_tensor(sigma, device=current.device, dtype=current.dtype)
            .expand(leading)
            .reshape(-1)
        )
        present_flat = (
            torch.as_tensor(
                successor_present, device=current.device, dtype=current.dtype
            )
            .expand(leading)
            .reshape(-1, 1)
        )
        noise_embedding = sinusoidal_embedding(
            torch.log(sigma_flat.clamp_min(1.0e-8)), self.noise_embedding_dim
        )
        inputs = torch.cat(
            (
                current.reshape(-1, self.latent_dim),
                successor.reshape(-1, self.latent_dim),
                noisy_action.reshape(-1, self.action_dim),
                noise_embedding,
                present_flat,
            ),
            dim=-1,
        )
        hidden = self.input_projection(inputs)
        for block in self.blocks:
            hidden = block(hidden)
        prediction = self.output(self.output_norm(hidden))
        return prediction.reshape(*leading, self.action_dim)


def count_parameters(model: nn.Module) -> int:
    """Count trainable scalar parameters."""

    return sum(parameter.numel() for parameter in model.parameters())


def reconstruction_energy(
    prediction: torch.Tensor, clean_action: torch.Tensor
) -> torch.Tensor:
    """Per-example standardized-action x0 reconstruction energy."""

    if prediction.shape != clean_action.shape:
        raise ValueError("prediction and clean action shapes differ")
    return (prediction - clean_action).square().mean(dim=-1)


def cider_ratio(
    conditional_energy: torch.Tensor,
    current_only_energy: torch.Tensor,
    *,
    epsilon: float = 1.0e-6,
) -> torch.Tensor:
    """Conditional inverse-denoising evidence ratio; lower is better."""

    if conditional_energy.shape != current_only_energy.shape:
        raise ValueError("energy shapes differ")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    return torch.log(conditional_energy + epsilon) - torch.log(
        current_only_energy + epsilon
    )


def calibrated_transition_violation(
    cider: torch.Tensor,
    q95: torch.Tensor,
    q99: torch.Tensor,
    *,
    minimum_scale: float = 0.10,
    maximum_violation: float = 10.0,
) -> torch.Tensor:
    """Apply the frozen one-sided P1 tail calibration to CIDER values."""

    if minimum_scale <= 0 or maximum_violation <= 0:
        raise ValueError("calibration constants must be positive")
    scale = (q99 - q95).clamp_min(minimum_scale)
    return ((cider - q95) / scale).clamp(min=0.0, max=maximum_violation)


def upper_tail_horizon_mean(
    transition_cost: torch.Tensor, *, count: int = 2
) -> torch.Tensor:
    """Mean the largest fixed number of transition costs per candidate."""

    if transition_cost.ndim < 1:
        raise ValueError("transition cost needs a horizon dimension")
    if count <= 0 or count > transition_cost.shape[-1]:
        raise ValueError("invalid upper-tail count")
    return transition_cost.topk(count, dim=-1, largest=True, sorted=False).values.mean(
        dim=-1
    )


__all__ = [
    "ConditionalActionDenoiser",
    "calibrated_transition_violation",
    "cider_ratio",
    "count_parameters",
    "reconstruction_energy",
    "sinusoidal_embedding",
    "upper_tail_horizon_mean",
]
