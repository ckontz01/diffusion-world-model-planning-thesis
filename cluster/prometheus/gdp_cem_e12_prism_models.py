#!/usr/bin/env python3
"""Frozen E12 PRISM comparators and the disclosed PRISM-DP reconstruction.

The Gaussian head, beta-NLL, and Product-of-Gaussians equations reproduce the
public PRISM implementation pinned in the E12 protocol.  The diffusion-policy
model is necessarily a reconstruction: PRISM's public repository documents
the architecture and recipe but omits model.py, scheduler.py, and checkpoints.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import torch
from stable_worldmodel.solver import MPPISolver
from torch import nn
from torch.nn import functional as F


PRISM_UPSTREAM_COMMIT = "baa0eb95efb812196b68796c258b1f0cf10b7625"
PRISM_PRIOR_HEAD_SHA256 = (
    "6a60613ea2acd10b9185d415868a9006acf27f1211df3b3e4758c2458921617c"
)
PRISM_MPPI_SHA256 = (
    "4e6d2430f4bf64c5d901c5bf4db986e8bf4436618591b983543b5e8f63cd62e6"
)
PRISM_DP_DOC_SHA256 = (
    "59677186511b4dde1c45f1048f79b89aa8ca85f635a9108da84ce5dd8bc87578"
)


class PrismPriorHead(nn.Module):
    """Public PRISM MLP: ``(z_t, z_g) -> (mu, sigma)`` over 25 actions."""

    def __init__(
        self,
        z_dim: int,
        horizon: int,
        action_block: int,
        raw_action_dim: int,
        hidden: int = 512,
        sigma_floor: float = 0.05,
    ) -> None:
        super().__init__()
        if min(z_dim, horizon, action_block, raw_action_dim, hidden) <= 0:
            raise ValueError("invalid PRISM PriorHead dimensions")
        if not math.isfinite(sigma_floor) or sigma_floor <= 0.0:
            raise ValueError("invalid PRISM sigma floor")
        self.z_dim = int(z_dim)
        self.horizon = int(horizon)
        self.action_block = int(action_block)
        self.raw_action_dim = int(raw_action_dim)
        self.hidden = int(hidden)
        self.sigma_floor = float(sigma_floor)
        self.action_sequence_dim = (
            self.horizon * self.action_block * self.raw_action_dim
        )
        self.mlp = nn.Sequential(
            nn.Linear(2 * self.z_dim, self.hidden),
            nn.GELU(),
            nn.Linear(self.hidden, self.hidden),
            nn.GELU(),
            nn.Linear(self.hidden, 2 * self.action_sequence_dim),
        )

    def forward(
        self, current: torch.Tensor, goal: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if current.shape != goal.shape or current.shape[-1] != self.z_dim:
            raise ValueError("invalid PRISM PriorHead condition shape")
        output = self.mlp(torch.cat((current, goal), dim=-1))
        mean_flat, raw_sigma_flat = output.chunk(2, dim=-1)
        sigma_flat = F.softplus(raw_sigma_flat) + self.sigma_floor
        shape = (
            current.shape[0],
            self.horizon,
            self.action_block,
            self.raw_action_dim,
        )
        return mean_flat.reshape(shape), sigma_flat.reshape(shape)


def prism_beta_nll_loss(
    mean: torch.Tensor,
    sigma: torch.Tensor,
    target: torch.Tensor,
    *,
    beta: float = 0.5,
) -> torch.Tensor:
    """PRISM's beta-NLL, dropping the additive Gaussian constant."""

    if mean.shape != sigma.shape or mean.shape != target.shape:
        raise ValueError("PRISM beta-NLL tensors differ in shape")
    if not 0.0 <= beta <= 1.0 or torch.any(sigma <= 0.0):
        raise ValueError("invalid PRISM beta-NLL inputs")
    variance = sigma.square()
    nll = 0.5 * (target - mean).square() / variance + sigma.log()
    weight = sigma.detach().pow(2.0 * beta)
    return (weight * nll).mean()


def prism_pog_fusion(
    mean: torch.Tensor,
    std: torch.Tensor,
    prior_mean: torch.Tensor,
    prior_std: torch.Tensor,
    *,
    sigma_floor: float = 0.05,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Public PRISM precision-addition Product-of-Gaussians equation."""

    if not (
        mean.shape == std.shape == prior_mean.shape == prior_std.shape
        and torch.all(std > 0.0)
        and torch.all(prior_std > 0.0)
    ):
        raise ValueError("invalid PRISM PoG tensors")
    epsilon = 1.0e-8
    base_precision = 1.0 / (std.square() + epsilon)
    prior_precision = 1.0 / (prior_std.square() + epsilon)
    precision = base_precision + prior_precision
    fused_mean = (
        base_precision * mean + prior_precision * prior_mean
    ) / precision
    fused_std = (1.0 / precision).sqrt().clamp(min=float(sigma_floor))
    return fused_mean, fused_std


class PrismHeadConditioner:
    """Compute a PRISM prior from the same frozen encoder used by Le-WM.

    The head is trained in a P1-only action-standardization space.  The solver
    consumes Stable-WorldModel planner coordinates, so both mean and standard
    deviation are converted through raw action units before PoG fusion.
    """

    def __init__(
        self,
        world_model: nn.Module,
        head: PrismPriorHead,
        *,
        p1_action_mean: torch.Tensor,
        p1_action_std: torch.Tensor,
        planner_action_mean: torch.Tensor,
        planner_action_std: torch.Tensor,
    ) -> None:
        self.world_model = world_model
        self.head = head
        self.device = next(head.parameters()).device
        self.p1_action_mean = torch.as_tensor(
            p1_action_mean, device=self.device, dtype=torch.float32
        )
        self.p1_action_std = torch.as_tensor(
            p1_action_std, device=self.device, dtype=torch.float32
        )
        self.planner_action_mean = torch.as_tensor(
            planner_action_mean, device=self.device, dtype=torch.float32
        )
        self.planner_action_std = torch.as_tensor(
            planner_action_std, device=self.device, dtype=torch.float32
        )
        expected = (head.raw_action_dim,)
        if (
            self.p1_action_mean.shape != expected
            or self.p1_action_std.shape != expected
            or self.planner_action_mean.shape != expected
            or self.planner_action_std.shape != expected
            or torch.any(self.p1_action_std <= 1.0e-8)
            or torch.any(self.planner_action_std <= 1.0e-8)
        ):
            raise ValueError("invalid PRISM action-standardization statistics")
        self.diagnostic_history: list[dict[str, Any]] = []

    @staticmethod
    def _condition_views(
        info: dict[str, Any], device: torch.device
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        work = {
            key: value.to(device) if torch.is_tensor(value) else value
            for key, value in info.items()
        }
        current = {
            key: value for key, value in work.items() if torch.is_tensor(value)
        }
        current.pop("action", None)
        goal = {
            key: value for key, value in work.items() if torch.is_tensor(value)
        }
        if "goal" not in goal:
            raise KeyError("goal missing from PRISM planner information")
        goal["pixels"] = goal["goal"]
        for key in list(goal):
            if key.startswith("goal_"):
                goal[key.removeprefix("goal_")] = goal.pop(key)
        goal.pop("action", None)
        return current, goal

    @torch.inference_mode()
    def __call__(
        self, info: dict[str, Any]
    ) -> tuple[torch.Tensor, torch.Tensor]:
        started = time.perf_counter()
        current_info, goal_info = self._condition_views(info, self.device)
        current = self.world_model.encode(current_info)["emb"][:, -1]
        goal = self.world_model.encode(goal_info)["emb"][:, -1]
        if current.shape != goal.shape or current.shape[-1] != self.head.z_dim:
            raise RuntimeError("PRISM encoder/head latent mismatch")
        normalized_mean, normalized_sigma = self.head(current, goal)
        raw_mean = (
            normalized_mean * self.p1_action_std.reshape(1, 1, 1, -1)
            + self.p1_action_mean.reshape(1, 1, 1, -1)
        )
        raw_sigma = normalized_sigma * self.p1_action_std.reshape(1, 1, 1, -1)
        planner_mean = (
            raw_mean - self.planner_action_mean.reshape(1, 1, 1, -1)
        ) / self.planner_action_std.reshape(1, 1, 1, -1)
        planner_sigma = raw_sigma / self.planner_action_std.reshape(1, 1, 1, -1)
        planner_mean = planner_mean.flatten(2)
        planner_sigma = planner_sigma.flatten(2)
        if (
            not torch.isfinite(planner_mean).all()
            or not torch.isfinite(planner_sigma).all()
            or torch.any(planner_sigma <= 0.0)
        ):
            raise RuntimeError("non-finite PRISM prior")
        self.diagnostic_history.append(
            {
                "call": len(self.diagnostic_history),
                "condition_seconds": time.perf_counter() - started,
                "sigma_mean": float(planner_sigma.mean().cpu()),
                "sigma_min": float(planner_sigma.min().cpu()),
                "sigma_max": float(planner_sigma.max().cpu()),
                "mean_abs": float(planner_mean.abs().mean().cpu()),
            }
        )
        return planner_mean, planner_sigma


class PrismFixedStdMPPISolver(MPPISolver):
    """Current-Stable-WorldModel-compatible PRISM PoG-MPPI.

    Upstream MPPI already keeps its tensor named ``var`` fixed across all
    iterations; it is used as a standard deviation.  This class only computes
    a fresh learned prior for the exact replanning subset and replaces the
    initial distribution through public PRISM PoG fusion.
    """

    def __init__(
        self,
        *args: Any,
        prior_conditioner: PrismHeadConditioner | None,
        sigma_floor: float = 0.05,
        prior_sigma_scale: float = 1.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if sigma_floor <= 0.0 or prior_sigma_scale <= 0.0:
            raise ValueError("invalid PRISM-MPPI scale")
        self.prior_conditioner = prior_conditioner
        self.sigma_floor = float(sigma_floor)
        self.prior_sigma_scale = float(prior_sigma_scale)
        self._active_prior: tuple[torch.Tensor, torch.Tensor] | None = None
        self.diagnostic_history: list[dict[str, Any]] = []

    def init_action_distrib(
        self, actions: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        # Stable-WorldModel 0.0.6 stores ``n_envs`` on the configured solver;
        # its public MPPI hook therefore accepts only the optional warm start.
        mean, std = super().init_action_distrib(actions)
        if self._active_prior is None:
            return mean, std
        prior_mean, prior_std = self._active_prior
        prior_mean = prior_mean.to(mean.device, dtype=mean.dtype)
        prior_std = prior_std.to(std.device, dtype=std.dtype) * self.prior_sigma_scale
        if prior_mean.shape != mean.shape or prior_std.shape != std.shape:
            raise RuntimeError(
                f"PRISM prior shape {(tuple(prior_mean.shape), tuple(prior_std.shape))} "
                f"differs from planner shape {tuple(mean.shape)}"
            )
        return prism_pog_fusion(
            mean,
            std,
            prior_mean,
            prior_std,
            sigma_floor=self.sigma_floor,
        )

    @torch.inference_mode()
    def solve(
        self, info_dict: dict[str, Any], init_action: torch.Tensor | None = None
    ) -> dict[str, Any]:
        started = time.perf_counter()
        if self.prior_conditioner is None:
            self._active_prior = None
        else:
            self._active_prior = self.prior_conditioner(info_dict)
        output = super().solve(info_dict, init_action=init_action)
        elapsed = time.perf_counter() - started
        self.diagnostic_history.append(
            {
                "call": len(self.diagnostic_history),
                "prior_active": self._active_prior is not None,
                "candidate_count": int(self.num_samples),
                "iterations": int(self.n_steps),
                "temperature": float(self.temperature),
                "topk": int(self.topk) if self.topk is not None else None,
                "solver_seconds": elapsed,
            }
        )
        self._active_prior = None
        output["solver_seconds"] = elapsed
        return output


def diffusion_time_embedding(
    timestep: torch.Tensor, dimension: int
) -> torch.Tensor:
    """Deterministic sinusoidal diffusion-step embedding."""

    if timestep.ndim != 1 or dimension < 4:
        raise ValueError("invalid diffusion timestep embedding input")
    half = dimension // 2
    frequencies = torch.exp(
        -math.log(10_000.0)
        * torch.arange(half, device=timestep.device, dtype=torch.float32)
        / max(half - 1, 1)
    )
    angles = timestep.float()[:, None] * frequencies[None]
    embedding = torch.cat((angles.sin(), angles.cos()), dim=-1)
    if embedding.shape[-1] < dimension:
        embedding = F.pad(embedding, (0, dimension - embedding.shape[-1]))
    return embedding


class Conv1dMishBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        groups = min(8, out_channels)
        while out_channels % groups:
            groups -= 1
        self.block = nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.GroupNorm(groups, out_channels),
            nn.Mish(),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.block(value)


class ConditionalResidual1D(nn.Module):
    """Two-convolution FiLM residual block used by the reconstructed U-Net."""

    def __init__(self, in_channels: int, out_channels: int, cond_dim: int) -> None:
        super().__init__()
        self.first = Conv1dMishBlock(in_channels, out_channels)
        self.second = Conv1dMishBlock(out_channels, out_channels)
        self.film = nn.Sequential(nn.Mish(), nn.Linear(cond_dim, 2 * out_channels))
        self.residual = (
            nn.Identity()
            if in_channels == out_channels
            else nn.Conv1d(in_channels, out_channels, kernel_size=1)
        )

    def forward(self, value: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        hidden = self.first(value)
        scale, bias = self.film(condition).chunk(2, dim=-1)
        hidden = hidden * (1.0 + scale[:, :, None]) + bias[:, :, None]
        hidden = self.second(hidden)
        return hidden + self.residual(value)


class VisionResidual2D(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        groups = min(8, channels)
        while channels % groups:
            groups -= 1
        self.body = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(groups, channels),
            nn.Mish(),
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(groups, channels),
        )
        self.activation = nn.Mish()

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.activation(value + self.body(value))


class SmallVisionEncoder(nn.Module):
    """Shared PRISM-DP CNN mapping ImageNet-normalized 224px RGB to 256D."""

    def __init__(self, feature_dim: int = 256) -> None:
        super().__init__()
        stages: list[nn.Module] = [
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.GroupNorm(8, 64),
            nn.Mish(),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False),
            nn.GroupNorm(8, 128),
            nn.Mish(),
            nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1, bias=False),
            nn.GroupNorm(8, 256),
            nn.Mish(),
            VisionResidual2D(256),
            nn.Conv2d(256, 256, kernel_size=3, stride=2, padding=1, bias=False),
            nn.GroupNorm(8, 256),
            nn.Mish(),
            VisionResidual2D(256),
            nn.AdaptiveAvgPool2d(1),
        ]
        self.network = nn.Sequential(*stages)
        self.output = nn.Linear(256, feature_dim)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        if image.ndim != 4 or image.shape[1] != 3:
            raise ValueError("PRISM-DP image must be BCHW RGB")
        return self.output(self.network(image).flatten(1))


class PrismDPModel(nn.Module):
    """Disclosed reconstruction of PRISM's missing 19.3M diffusion policy."""

    def __init__(
        self,
        action_dim: int,
        *,
        action_horizon: int = 25,
        feature_dim: int = 256,
        condition_dim: int = 256,
        time_embedding_dim: int = 256,
        channels: Sequence[int] = (64, 128, 256, 512),
        residual_blocks_per_level: int = 3,
        middle_blocks: int = 1,
    ) -> None:
        super().__init__()
        if (
            action_dim <= 0
            or action_horizon <= 0
            or len(channels) != 4
            or residual_blocks_per_level < 2
            or middle_blocks < 1
        ):
            raise ValueError("invalid PRISM-DP model configuration")
        self.action_dim = int(action_dim)
        self.action_horizon = int(action_horizon)
        self.feature_dim = int(feature_dim)
        self.condition_dim = int(condition_dim)
        self.time_embedding_dim = int(time_embedding_dim)
        self.channels = tuple(int(value) for value in channels)
        self.residual_blocks_per_level = int(residual_blocks_per_level)
        self.middle_blocks = int(middle_blocks)

        self.vision_encoder = SmallVisionEncoder(feature_dim=self.feature_dim)
        self.condition_encoder = nn.Sequential(
            nn.Linear(2 * self.feature_dim, 512),
            nn.Mish(),
            nn.Linear(512, self.condition_dim),
        )
        self.time_encoder = nn.Sequential(
            nn.Linear(self.time_embedding_dim, self.time_embedding_dim),
            nn.Mish(),
            nn.Linear(self.time_embedding_dim, self.time_embedding_dim),
        )
        global_condition_dim = self.condition_dim + self.time_embedding_dim

        self.down_levels = nn.ModuleList()
        previous = self.action_dim
        for level, width in enumerate(self.channels):
            blocks = nn.ModuleList()
            for block_index in range(self.residual_blocks_per_level):
                blocks.append(
                    ConditionalResidual1D(
                        previous if block_index == 0 else width,
                        width,
                        global_condition_dim,
                    )
                )
            downsample = (
                nn.Conv1d(width, width, kernel_size=4, stride=2, padding=1)
                if level < len(self.channels) - 1
                else nn.Identity()
            )
            self.down_levels.append(nn.ModuleDict({"blocks": blocks, "down": downsample}))
            previous = width

        self.middle = nn.ModuleList(
            [
                ConditionalResidual1D(
                    self.channels[-1], self.channels[-1], global_condition_dim
                )
                for _ in range(self.middle_blocks)
            ]
        )

        self.up_levels = nn.ModuleList()
        current = self.channels[-1]
        reversed_skips = tuple(reversed(self.channels[:-1]))
        for level_index, skip_width in enumerate(reversed_skips):
            blocks = nn.ModuleList()
            for block_index in range(self.residual_blocks_per_level):
                blocks.append(
                    ConditionalResidual1D(
                        current + skip_width if block_index == 0 else skip_width,
                        skip_width,
                        global_condition_dim,
                    )
                )
            upsample = (
                nn.ConvTranspose1d(
                    skip_width, skip_width, kernel_size=4, stride=2, padding=1
                )
                if level_index < len(reversed_skips) - 1
                else nn.Identity()
            )
            self.up_levels.append(
                nn.ModuleDict({"blocks": blocks, "up": upsample})
            )
            current = skip_width
        self.output = nn.Sequential(
            Conv1dMishBlock(self.channels[0], self.channels[0]),
            nn.Conv1d(self.channels[0], self.action_dim, kernel_size=1),
        )

    @property
    def num_params(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def encode_observation(
        self, observation: torch.Tensor, goal: torch.Tensor
    ) -> torch.Tensor:
        if observation.shape != goal.shape:
            raise ValueError("PRISM-DP observation and goal image shapes differ")
        current_feature = self.vision_encoder(observation)
        goal_feature = self.vision_encoder(goal)
        return self.condition_encoder(torch.cat((current_feature, goal_feature), dim=-1))

    def forward_with_condition(
        self,
        noisy_action: torch.Tensor,
        timestep: torch.Tensor,
        condition: torch.Tensor,
    ) -> torch.Tensor:
        if (
            noisy_action.ndim != 3
            or noisy_action.shape[1:] != (self.action_horizon, self.action_dim)
            or timestep.shape != (noisy_action.shape[0],)
            or condition.shape != (noisy_action.shape[0], self.condition_dim)
        ):
            raise ValueError("invalid PRISM-DP denoiser input")
        time_condition = self.time_encoder(
            diffusion_time_embedding(timestep, self.time_embedding_dim)
        )
        global_condition = torch.cat((condition, time_condition), dim=-1)
        value = noisy_action.transpose(1, 2)
        original_length = value.shape[-1]
        multiple = 2 ** (len(self.channels) - 1)
        padded_length = int(math.ceil(original_length / multiple) * multiple)
        if padded_length != original_length:
            value = F.pad(value, (0, padded_length - original_length))

        skips: list[torch.Tensor] = []
        for level_index, level in enumerate(self.down_levels):
            for block in level["blocks"]:
                value = block(value, global_condition)
            if level_index < len(self.down_levels) - 1:
                skips.append(value)
                value = level["down"](value)
        for block in self.middle:
            value = block(value, global_condition)
        for level in self.up_levels:
            skip = skips.pop()
            if value.shape[-1] != skip.shape[-1]:
                value = F.interpolate(value, size=skip.shape[-1], mode="nearest")
            value = torch.cat((value, skip), dim=1)
            for block in level["blocks"]:
                value = block(value, global_condition)
            value = level["up"](value)
        if value.shape[-1] != padded_length:
            value = F.interpolate(value, size=padded_length, mode="nearest")
        return self.output(value)[..., :original_length].transpose(1, 2)

    def forward(
        self,
        noisy_action: torch.Tensor,
        timestep: torch.Tensor,
        observation: torch.Tensor,
        goal: torch.Tensor,
    ) -> torch.Tensor:
        condition = self.encode_observation(observation, goal)
        return self.forward_with_condition(noisy_action, timestep, condition)


@dataclass(frozen=True)
class CosineDDIMSchedule:
    """100-step squared-cosine DDPM forward process and deterministic DDIM."""

    betas: torch.Tensor
    alpha_bar: torch.Tensor

    @classmethod
    def build(
        cls, num_train_timesteps: int = 100, *, max_beta: float = 0.999
    ) -> "CosineDDIMSchedule":
        if num_train_timesteps <= 1:
            raise ValueError("invalid PRISM-DP diffusion-step count")

        def alpha_bar_function(value: float) -> float:
            return math.cos((value + 0.008) / 1.008 * math.pi / 2.0) ** 2

        betas = []
        for step in range(num_train_timesteps):
            first = alpha_bar_function(step / num_train_timesteps)
            second = alpha_bar_function((step + 1) / num_train_timesteps)
            betas.append(min(1.0 - second / first, max_beta))
        beta_tensor = torch.tensor(betas, dtype=torch.float32)
        return cls(
            betas=beta_tensor,
            alpha_bar=torch.cumprod(1.0 - beta_tensor, dim=0),
        )

    @property
    def num_train_timesteps(self) -> int:
        return int(self.betas.numel())

    def add_noise(
        self,
        clean: torch.Tensor,
        noise: torch.Tensor,
        timestep: torch.Tensor,
    ) -> torch.Tensor:
        if clean.shape != noise.shape or timestep.shape != (clean.shape[0],):
            raise ValueError("invalid PRISM-DP forward-noise input")
        alpha = self.alpha_bar.to(clean.device)[timestep].reshape(-1, 1, 1)
        return alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise

    def inference_timesteps(self, count: int) -> list[int]:
        if count <= 0 or count > self.num_train_timesteps:
            raise ValueError("invalid PRISM-DP DDIM evaluation count")
        ratio = self.num_train_timesteps // count
        if ratio <= 0:
            raise ValueError("invalid PRISM-DP DDIM timestep ratio")
        return (torch.arange(count, dtype=torch.int64) * ratio).flip(0).tolist()

    @torch.inference_mode()
    def sample(
        self,
        model: PrismDPModel,
        condition: torch.Tensor,
        *,
        generator: torch.Generator,
        inference_steps: int = 10,
    ) -> torch.Tensor:
        value = torch.randn(
            condition.shape[0],
            model.action_horizon,
            model.action_dim,
            generator=generator,
            device=condition.device,
            dtype=condition.dtype,
        )
        alpha_bar = self.alpha_bar.to(condition.device, dtype=condition.dtype)
        timesteps = self.inference_timesteps(inference_steps)
        for index, timestep_value in enumerate(timesteps):
            timestep = torch.full(
                (condition.shape[0],),
                timestep_value,
                device=condition.device,
                dtype=torch.long,
            )
            epsilon = model.forward_with_condition(value, timestep, condition)
            alpha_now = alpha_bar[timestep_value]
            previous_value = timesteps[index + 1] if index + 1 < len(timesteps) else -1
            alpha_previous = (
                alpha_bar[previous_value]
                if previous_value >= 0
                else torch.ones((), device=condition.device, dtype=condition.dtype)
            )
            predicted_clean = (
                value - (1.0 - alpha_now).sqrt() * epsilon
            ) / alpha_now.sqrt()
            predicted_clean = predicted_clean.clamp(-1.0, 1.0)
            direction = (1.0 - alpha_previous).sqrt() * epsilon
            value = alpha_previous.sqrt() * predicted_clean + direction
        if not torch.isfinite(value).all():
            raise RuntimeError("non-finite PRISM-DP DDIM sample")
        return value.clamp(-1.0, 1.0)


class PrismDPBestOfNSampler(nn.Module):
    """Put PRISM-DP candidates into E11's one-world-model-pass selector slot."""

    def __init__(
        self,
        model: PrismDPModel,
        *,
        action_min: torch.Tensor,
        action_max: torch.Tensor,
        planner_action_mean: torch.Tensor,
        planner_action_std: torch.Tensor,
        robust_low: torch.Tensor,
        robust_high: torch.Tensor,
        inference_steps: int = 10,
        diffusion_steps: int = 100,
    ) -> None:
        super().__init__()
        self.model = model
        self.inference_steps = int(inference_steps)
        self.schedule = CosineDDIMSchedule.build(diffusion_steps)
        device = next(model.parameters()).device
        for name, value in (
            ("action_min", action_min),
            ("action_max", action_max),
            ("planner_action_mean", planner_action_mean),
            ("planner_action_std", planner_action_std),
            ("robust_low", robust_low),
            ("robust_high", robust_high),
        ):
            self.register_buffer(
                name,
                torch.as_tensor(value, device=device, dtype=torch.float32),
                persistent=True,
            )
        expected = (model.action_dim,)
        if (
            any(
                getattr(self, name).shape != expected
                for name in (
                    "action_min",
                    "action_max",
                    "planner_action_mean",
                    "planner_action_std",
                    "robust_low",
                    "robust_high",
                )
            )
            or torch.any(self.action_max <= self.action_min)
            or torch.any(self.planner_action_std <= 1.0e-8)
            or torch.any(self.robust_high <= self.robust_low)
        ):
            raise ValueError("invalid PRISM-DP action statistics")
        self.diagnostic_history: list[dict[str, Any]] = []

    @torch.inference_mode()
    def prepare(self, info: dict[str, Any]) -> torch.Tensor:
        device = next(self.model.parameters()).device
        pixels = info["pixels"].to(device)
        goal = info["goal"].to(device)
        if pixels.ndim == 5:
            pixels = pixels[:, -1]
        if goal.ndim == 5:
            goal = goal[:, -1]
        return self.model.encode_observation(pixels, goal)

    @torch.inference_mode()
    def sample(
        self,
        context: torch.Tensor,
        *,
        count: int,
        generator: torch.Generator,
    ) -> torch.Tensor:
        if count <= 0:
            raise ValueError("invalid PRISM-DP candidate count")
        before = hashlib.sha256(
            generator.get_state().cpu().numpy().tobytes()
        ).hexdigest()
        started = time.perf_counter()
        repeated = context.repeat_interleave(count, dim=0)
        normalized = self.schedule.sample(
            self.model,
            repeated,
            generator=generator,
            inference_steps=self.inference_steps,
        ).reshape(
            context.shape[0],
            count,
            self.model.action_horizon,
            self.model.action_dim,
        )
        raw = (
            (normalized + 1.0)
            * 0.5
            * (self.action_max - self.action_min).reshape(1, 1, 1, -1)
            + self.action_min.reshape(1, 1, 1, -1)
        )
        unclipped_raw = raw
        raw = torch.maximum(
            torch.minimum(raw, self.robust_high.reshape(1, 1, 1, -1)),
            self.robust_low.reshape(1, 1, 1, -1),
        )
        planner = (
            raw - self.planner_action_mean.reshape(1, 1, 1, -1)
        ) / self.planner_action_std.reshape(1, 1, 1, -1)
        boundary = torch.logical_or(
            normalized <= -0.999999, normalized >= 0.999999
        ).float().mean()
        robust_clipped = (raw != unclipped_raw).float().mean()
        diversity = planner.flatten(2).std(dim=1).mean()
        self.diagnostic_history.append(
            {
                "call": len(self.diagnostic_history),
                "kind": "prism_dp_reconstruction",
                "candidate_count": int(count),
                "inference_steps": self.inference_steps,
                "boundary_fraction": float(boundary.cpu()),
                "robust_clip_fraction": float(robust_clipped.cpu()),
                "mean_coordinate_std": float(diversity.cpu()),
                "proposal_seconds": time.perf_counter() - started,
                "generator_state_before_sha256": before,
                "generator_state_after_sha256": hashlib.sha256(
                    generator.get_state().cpu().numpy().tobytes()
                ).hexdigest(),
            }
        )
        planner = planner.reshape(
            context.shape[0],
            count,
            5,
            5 * self.model.action_dim,
        )
        if not torch.isfinite(planner).all():
            raise RuntimeError("non-finite PRISM-DP planner candidate")
        return planner


def cpu_state_dict(module: nn.Module) -> dict[str, torch.Tensor]:
    return {name: value.detach().cpu() for name, value in module.state_dict().items()}


@torch.no_grad()
def update_ema(ema: nn.Module, model: nn.Module, decay: float = 0.999) -> None:
    ema_parameters = dict(ema.named_parameters())
    for name, parameter in model.named_parameters():
        ema_parameters[name].mul_(decay).add_(parameter, alpha=1.0 - decay)
    ema_buffers = dict(ema.named_buffers())
    for name, buffer in model.named_buffers():
        ema_buffers[name].copy_(buffer)
