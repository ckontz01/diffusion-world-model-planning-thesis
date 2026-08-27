"""E16 shared latent-to-state adapter and continuation-score primitives."""

from __future__ import annotations

import torch
from torch import nn

import gdp_cem_e16_specs as spec


class LatentStateAdapter(nn.Module):
    """Decode an E15-standardized Le-WM CLS latent to standardized state."""

    def __init__(
        self,
        *,
        latent_dim: int,
        state_dim: int,
        width: int = spec.ADAPTER_WIDTH,
    ) -> None:
        super().__init__()
        if min(latent_dim, state_dim, width) <= 0:
            raise ValueError("invalid E16 adapter dimension")
        self.latent_dim = int(latent_dim)
        self.state_dim = int(state_dim)
        self.width = int(width)
        self.network = nn.Sequential(
            nn.LayerNorm(self.latent_dim),
            nn.Linear(self.latent_dim, self.width),
            nn.SiLU(),
            nn.Linear(self.width, self.width),
            nn.SiLU(),
            nn.Linear(self.width, self.state_dim),
        )

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        if latent.ndim != 2 or latent.shape[1] != self.latent_dim:
            raise ValueError("E16 adapter input shape differs")
        value = self.network(latent)
        if value.shape != (len(latent), self.state_dim):
            raise RuntimeError("E16 adapter output shape differs")
        return value


def continuation_score(
    final_cost: torch.Tensor,
    *,
    best_count: int = spec.CONTINUATION_BEST_COUNT,
) -> torch.Tensor:
    """Mean the fixed lower tail of continuation costs for every first branch."""

    if final_cost.ndim != 3 or not 0 < best_count <= final_cost.shape[-1]:
        raise ValueError("invalid E16 continuation-cost shape")
    if not torch.isfinite(final_cost).all():
        raise RuntimeError("non-finite E16 continuation cost")
    return torch.topk(
        final_cost, k=best_count, dim=-1, largest=False, sorted=False
    ).values.mean(dim=-1)


__all__ = ["LatentStateAdapter", "continuation_score"]

