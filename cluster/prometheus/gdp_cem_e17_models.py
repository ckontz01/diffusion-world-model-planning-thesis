"""Frozen E17 action-conditioned transition-state adapter."""

from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F

import gdp_cem_e17_specs as spec


class ResidualBlock(nn.Module):
    def __init__(self, width: int) -> None:
        super().__init__()
        if width <= 0:
            raise ValueError("invalid E17 residual width")
        self.network = nn.Sequential(
            nn.LayerNorm(width),
            nn.Linear(width, width),
            nn.SiLU(),
            nn.Linear(width, width),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        if value.ndim != 2:
            raise ValueError("invalid E17 residual input")
        return (value + self.network(value)) / math.sqrt(2.0)


class TransitionStateAdapter(nn.Module):
    """Predict standardized next state from one bounded proposed chunk."""

    def __init__(
        self,
        *,
        state_dim: int,
        action_dim: int,
        latent_dim: int = spec.LATENT_DIM,
        width: int = spec.MODEL_WIDTH,
        residual_blocks: int = spec.MODEL_RESIDUAL_BLOCKS,
    ) -> None:
        super().__init__()
        if (
            min(state_dim, action_dim, latent_dim, width, residual_blocks) <= 0
            or latent_dim != spec.LATENT_DIM
        ):
            raise ValueError("invalid E17 adapter dimensions")
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)
        self.latent_dim = int(latent_dim)
        self.width = int(width)
        self.residual_blocks = int(residual_blocks)
        self.input_dim = spec.input_dim(
            state_dim=self.state_dim, action_dim=self.action_dim
        )
        self.input = nn.Sequential(
            nn.LayerNorm(self.input_dim),
            nn.Linear(self.input_dim, self.width),
            nn.SiLU(),
        )
        self.blocks = nn.ModuleList(
            ResidualBlock(self.width) for _ in range(self.residual_blocks)
        )
        self.output = nn.Sequential(
            nn.LayerNorm(self.width),
            nn.Linear(self.width, self.state_dim),
        )

    def _tau_one_hot(self, tau: torch.Tensor) -> torch.Tensor:
        if tau.ndim != 1:
            raise ValueError("invalid E17 tau shape")
        index = torch.full_like(tau, -1, dtype=torch.long)
        for position, value in enumerate(spec.TAU_VALUES):
            index = torch.where(tau == value, position, index)
        if torch.any(index < 0):
            raise ValueError("unsupported E17 tau")
        return F.one_hot(index, num_classes=len(spec.TAU_VALUES)).to(
            dtype=torch.float32
        )

    def features(
        self,
        *,
        current_latent: torch.Tensor,
        terminal_latent: torch.Tensor,
        current_state: torch.Tensor,
        action_raw: torch.Tensor,
        action_mask: torch.Tensor,
        tau: torch.Tensor,
    ) -> torch.Tensor:
        batch = len(current_latent)
        if (
            current_latent.shape != (batch, self.latent_dim)
            or terminal_latent.shape != current_latent.shape
            or current_state.shape != (batch, self.state_dim)
            or action_raw.shape
            != (batch, spec.ACTION_HORIZON, self.action_dim)
            or action_mask.shape != (batch, spec.ACTION_HORIZON)
            or tau.shape != (batch,)
        ):
            raise ValueError("E17 adapter input shape differs")
        if action_mask.dtype != torch.bool:
            raise ValueError("E17 action mask must be boolean")
        if torch.any(action_raw[~action_mask] != 0):
            raise ValueError("E17 inactive action must be zero")
        value = torch.cat(
            (
                current_latent,
                terminal_latent,
                terminal_latent - current_latent,
                current_state,
                action_raw.flatten(start_dim=1),
                action_mask.to(dtype=torch.float32),
                self._tau_one_hot(tau).to(device=tau.device),
            ),
            dim=1,
        )
        if value.shape != (batch, self.input_dim):
            raise RuntimeError("E17 concatenated feature shape differs")
        return value

    def forward(
        self,
        *,
        current_latent: torch.Tensor,
        terminal_latent: torch.Tensor,
        current_state: torch.Tensor,
        action_raw: torch.Tensor,
        action_mask: torch.Tensor,
        tau: torch.Tensor,
    ) -> torch.Tensor:
        value = self.input(
            self.features(
                current_latent=current_latent,
                terminal_latent=terminal_latent,
                current_state=current_state,
                action_raw=action_raw,
                action_mask=action_mask,
                tau=tau,
            )
        )
        for block in self.blocks:
            value = block(value)
        result = current_state + self.output(value)
        if result.shape != current_state.shape:
            raise RuntimeError("E17 adapter output shape differs")
        return result


__all__ = ["ResidualBlock", "TransitionStateAdapter"]
