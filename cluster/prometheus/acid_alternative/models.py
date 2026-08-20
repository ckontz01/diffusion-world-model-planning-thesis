"""Neural scorers for the native flat-world-model comparison.

The ACID implementation follows the architecture and flow-matching equations
published in arXiv:2607.02403.  Choices absent from that paper are deliberately
small, explicit in the checkpoint metadata, and described as reconstruction
choices rather than author-reported ACID settings.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import torch
from torch import nn
from torch.nn import functional as F


def count_parameters(module: nn.Module) -> int:
    """Return the number of trainable scalar parameters."""

    return sum(
        parameter.numel()
        for parameter in module.parameters()
        if parameter.requires_grad
    )


def sinusoidal_embedding(
    value: torch.Tensor, dimension: int, max_period: float = 10_000.0
) -> torch.Tensor:
    """Embed a scalar using the standard transformer sinusoidal basis."""

    if dimension <= 0:
        raise ValueError("dimension must be positive")
    value = value.reshape(-1).float()
    half = dimension // 2
    if half == 0:
        return value[:, None].to(dtype=value.dtype)
    frequencies = torch.exp(
        -math.log(max_period)
        * torch.arange(half, device=value.device, dtype=torch.float32)
        / max(half - 1, 1)
    )
    angles = value[:, None] * frequencies[None]
    embedding = torch.cat((torch.cos(angles), torch.sin(angles)), dim=-1)
    if dimension % 2:
        embedding = F.pad(embedding, (0, 1))
    return embedding


class TensorStandardizer(nn.Module):
    """Frozen per-dimension affine standardizer stored in a state dict."""

    def __init__(
        self,
        mean: torch.Tensor,
        std: torch.Tensor,
        *,
        minimum_std: float = 1.0e-6,
    ) -> None:
        super().__init__()
        mean = torch.as_tensor(mean, dtype=torch.float32).flatten()
        std = torch.as_tensor(std, dtype=torch.float32).flatten()
        if mean.shape != std.shape or mean.numel() == 0:
            raise ValueError("mean and std must be nonempty vectors of equal shape")
        if not torch.isfinite(mean).all() or not torch.isfinite(std).all():
            raise ValueError("standardizer statistics must be finite")
        if torch.any(std < minimum_std):
            raise ValueError("standardizer contains a near-zero standard deviation")
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return (value - self.mean) / self.std

    def inverse(self, value: torch.Tensor) -> torch.Tensor:
        return value * self.std + self.mean


class FlowInverseDynamics(nn.Module):
    """Published ACID-style prefix/suffix flow-matching inverse model."""

    def __init__(
        self,
        latent_dim: int,
        action_dim: int,
        *,
        width: int = 192,
        depth: int = 4,
        heads: int = 3,
        mlp_ratio: int = 4,
    ) -> None:
        super().__init__()
        if width % heads:
            raise ValueError("width must be divisible by heads")
        if min(latent_dim, action_dim, width, depth, heads, mlp_ratio) <= 0:
            raise ValueError("model dimensions must be positive")
        self.latent_dim = int(latent_dim)
        self.action_dim = int(action_dim)
        self.width = int(width)
        self.depth = int(depth)
        self.heads = int(heads)

        self.latent_projection = nn.Linear(self.latent_dim, self.width)
        self.action_projection = nn.Linear(self.action_dim, self.width)
        self.token_position = nn.Parameter(torch.zeros(1, 3, self.width))
        nn.init.normal_(self.token_position, std=0.02)
        self.layers = nn.ModuleList(
            [
                nn.TransformerEncoderLayer(
                    d_model=self.width,
                    nhead=self.heads,
                    dim_feedforward=self.width * mlp_ratio,
                    dropout=0.0,
                    activation="gelu",
                    batch_first=True,
                    norm_first=True,
                )
                for _ in range(self.depth)
            ]
        )
        self.output_norm = nn.LayerNorm(self.width)
        self.velocity_head = nn.Linear(self.width, self.action_dim)
        attention_mask = torch.zeros(3, 3, dtype=torch.float32)
        attention_mask[:2, 2] = float("-inf")
        self.register_buffer("attention_mask", attention_mask, persistent=True)

    def forward(
        self,
        current_latent: torch.Tensor,
        next_latent: torch.Tensor,
        noisy_action: torch.Tensor,
        tau: torch.Tensor,
    ) -> torch.Tensor:
        if current_latent.shape != next_latent.shape:
            raise ValueError("current and next latent shapes differ")
        if current_latent.shape[-1] != self.latent_dim:
            raise ValueError("unexpected latent dimension")
        if noisy_action.shape[:-1] != current_latent.shape[:-1]:
            raise ValueError("action and latent leading shapes differ")
        if noisy_action.shape[-1] != self.action_dim:
            raise ValueError("unexpected action dimension")
        leading_shape = current_latent.shape[:-1]
        flat_current = current_latent.reshape(-1, self.latent_dim)
        flat_next = next_latent.reshape(-1, self.latent_dim)
        flat_action = noisy_action.reshape(-1, self.action_dim)
        flat_tau = (
            torch.as_tensor(tau, device=flat_action.device)
            .expand(leading_shape)
            .reshape(-1)
        )

        state_tokens = torch.stack(
            (self.latent_projection(flat_current), self.latent_projection(flat_next)),
            dim=1,
        )
        suffix = self.action_projection(flat_action)
        suffix = suffix + sinusoidal_embedding(flat_tau, self.width).to(
            dtype=suffix.dtype
        )
        tokens = torch.cat((state_tokens, suffix[:, None]), dim=1)
        tokens = tokens + self.token_position.to(dtype=tokens.dtype)
        mask = self.attention_mask.to(device=tokens.device, dtype=tokens.dtype)
        for layer in self.layers:
            tokens = layer(tokens, src_mask=mask)
        velocity = self.velocity_head(self.output_norm(tokens[:, -1]))
        return velocity.reshape(*leading_shape, self.action_dim)

    def flow_loss(
        self,
        current_latent: torch.Tensor,
        next_latent: torch.Tensor,
        action: torch.Tensor,
        *,
        tau: torch.Tensor | None = None,
        noise: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Return the scalar straight-path flow-matching objective."""

        if noise is None:
            noise = torch.randn_like(action)
        if tau is None:
            distribution = torch.distributions.Beta(
                torch.tensor(1.5, device=action.device),
                torch.tensor(1.0, device=action.device),
            )
            tau = distribution.sample(action.shape[:-1]).to(dtype=action.dtype)
        tau_action = tau.unsqueeze(-1)
        noisy_action = tau_action * noise + (1.0 - tau_action) * action
        target_velocity = noise - action
        prediction = self(current_latent, next_latent, noisy_action, tau)
        return F.mse_loss(prediction, target_velocity)

    def one_step_action(
        self,
        current_latent: torch.Tensor,
        next_latent: torch.Tensor,
        noise: torch.Tensor,
    ) -> torch.Tensor:
        """Integrate once from flow time one to zero using explicit Euler."""

        tau = torch.ones(noise.shape[:-1], device=noise.device, dtype=noise.dtype)
        velocity = self(current_latent, next_latent, noise, tau)
        return noise - velocity


class ResidualMLPBlock(nn.Module):
    def __init__(self, width: int, expansion: int = 2) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.network = nn.Sequential(
            nn.Linear(width, width * expansion),
            nn.SiLU(),
            nn.Linear(width * expansion, width),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return value + self.network(self.norm(value))


class ConditionalDiffusionVerifier(nn.Module):
    """Action-conditioned latent transition denoiser."""

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
        self.latent_dim = int(latent_dim)
        self.action_dim = int(action_dim)
        self.width = int(width)
        self.depth = int(depth)
        self.noise_embedding_dim = int(noise_embedding_dim)
        input_dim = 2 * self.latent_dim + self.action_dim + self.noise_embedding_dim
        self.input_projection = nn.Linear(input_dim, self.width)
        self.blocks = nn.ModuleList(
            [ResidualMLPBlock(self.width) for _ in range(self.depth)]
        )
        self.output_norm = nn.LayerNorm(self.width)
        self.output = nn.Linear(self.width, self.latent_dim)

    def forward(
        self,
        current_latent: torch.Tensor,
        action: torch.Tensor,
        noisy_next_latent: torch.Tensor,
        sigma: torch.Tensor,
    ) -> torch.Tensor:
        if current_latent.shape != noisy_next_latent.shape:
            raise ValueError("current and next latent shapes differ")
        if current_latent.shape[-1] != self.latent_dim:
            raise ValueError("unexpected latent dimension")
        if (
            action.shape[:-1] != current_latent.shape[:-1]
            or action.shape[-1] != self.action_dim
        ):
            raise ValueError("unexpected action shape")
        leading_shape = current_latent.shape[:-1]
        flat_sigma = (
            torch.as_tensor(sigma, device=current_latent.device)
            .expand(leading_shape)
            .reshape(-1)
        )
        log_sigma = torch.log(flat_sigma.clamp_min(1.0e-8))
        sigma_embedding = sinusoidal_embedding(log_sigma, self.noise_embedding_dim)
        inputs = torch.cat(
            (
                current_latent.reshape(-1, self.latent_dim),
                action.reshape(-1, self.action_dim),
                noisy_next_latent.reshape(-1, self.latent_dim),
                sigma_embedding.to(dtype=current_latent.dtype),
            ),
            dim=-1,
        )
        hidden = self.input_projection(inputs)
        for block in self.blocks:
            hidden = block(hidden)
        prediction = self.output(self.output_norm(hidden))
        return prediction.reshape(*leading_shape, self.latent_dim)

    def denoising_loss(
        self,
        current_latent: torch.Tensor,
        action: torch.Tensor,
        next_latent: torch.Tensor,
        *,
        sigma: torch.Tensor,
        noise: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if noise is None:
            noise = torch.randn_like(next_latent)
        noisy_next = next_latent + sigma.unsqueeze(-1) * noise
        prediction = self(current_latent, action, noisy_next, sigma)
        return F.mse_loss(prediction, noise)


class DeterministicForwardVerifier(nn.Module):
    """Capacity-matched deterministic conditional forward model."""

    def __init__(
        self,
        latent_dim: int,
        action_dim: int,
        *,
        width: int = 416,
        depth: int = 3,
    ) -> None:
        super().__init__()
        if min(latent_dim, action_dim, width, depth) <= 0:
            raise ValueError("model dimensions must be positive")
        self.latent_dim = int(latent_dim)
        self.action_dim = int(action_dim)
        self.width = int(width)
        self.depth = int(depth)
        self.input_projection = nn.Linear(self.latent_dim + self.action_dim, self.width)
        self.blocks = nn.ModuleList(
            [ResidualMLPBlock(self.width) for _ in range(self.depth)]
        )
        self.output_norm = nn.LayerNorm(self.width)
        self.output = nn.Linear(self.width, self.latent_dim)

    def forward(
        self, current_latent: torch.Tensor, action: torch.Tensor
    ) -> torch.Tensor:
        if current_latent.shape[-1] != self.latent_dim:
            raise ValueError("unexpected latent dimension")
        if (
            action.shape[:-1] != current_latent.shape[:-1]
            or action.shape[-1] != self.action_dim
        ):
            raise ValueError("unexpected action shape")
        leading_shape = current_latent.shape[:-1]
        inputs = torch.cat(
            (
                current_latent.reshape(-1, self.latent_dim),
                action.reshape(-1, self.action_dim),
            ),
            dim=-1,
        )
        hidden = self.input_projection(inputs)
        for block in self.blocks:
            hidden = block(hidden)
        prediction = self.output(self.output_norm(hidden))
        return prediction.reshape(*leading_shape, self.latent_dim)


class TemporalReachabilityHead(nn.Module):
    """Published TRM pairwise head."""

    def __init__(self, latent_dim: int, *, hidden_width: int = 256) -> None:
        super().__init__()
        self.latent_dim = int(latent_dim)
        self.hidden_width = int(hidden_width)
        self.network = nn.Sequential(
            nn.Linear(4 * self.latent_dim, self.hidden_width),
            nn.SiLU(),
            nn.Linear(self.hidden_width, self.hidden_width),
            nn.SiLU(),
            nn.Linear(self.hidden_width, 1),
            nn.Softplus(),
        )

    def forward(self, first: torch.Tensor, second: torch.Tensor) -> torch.Tensor:
        if first.shape != second.shape or first.shape[-1] != self.latent_dim:
            raise ValueError("unexpected latent-pair shape")
        difference = first - second
        features = torch.cat((first, second, difference, difference.abs()), dim=-1)
        return self.network(features).squeeze(-1)


def select_capacity_matched_width(
    reference: nn.Module,
    factory: Callable[[int], nn.Module],
    *,
    minimum: int = 64,
    maximum: int = 1024,
    step: int = 8,
) -> tuple[int, int, float]:
    """Mechanically choose the closest parameter count over a frozen width grid."""

    if minimum <= 0 or maximum < minimum or step <= 0:
        raise ValueError("invalid width search bounds")
    target = count_parameters(reference)
    best: tuple[int, int, float] | None = None
    for width in range(minimum, maximum + 1, step):
        candidate_count = count_parameters(factory(width))
        relative_difference = abs(candidate_count - target) / target
        record = (width, candidate_count, relative_difference)
        if best is None or (record[2], record[0]) < (best[2], best[0]):
            best = record
    if best is None:
        raise RuntimeError("width grid was empty")
    return best


def model_from_config(config: dict) -> nn.Module:
    """Instantiate a scorer from the explicit config stored in its checkpoint."""

    name = config.get("name")
    if name == "reachability":
        return TemporalReachabilityHead(
            latent_dim=int(config["latent_dim"]),
            hidden_width=int(config.get("hidden_width", 256)),
        )
    common = {
        "latent_dim": int(config["latent_dim"]),
        "action_dim": int(config["action_dim"]),
    }
    if name == "acid":
        return FlowInverseDynamics(
            **common,
            width=int(config["width"]),
            depth=int(config["depth"]),
            heads=int(config["heads"]),
            mlp_ratio=int(config["mlp_ratio"]),
        )
    if name == "diffusion":
        return ConditionalDiffusionVerifier(
            **common,
            width=int(config["width"]),
            depth=int(config["depth"]),
            noise_embedding_dim=int(config["noise_embedding_dim"]),
        )
    if name == "forward":
        return DeterministicForwardVerifier(
            **common,
            width=int(config["width"]),
            depth=int(config["depth"]),
        )
    raise ValueError(f"unsupported model config name: {name!r}")
