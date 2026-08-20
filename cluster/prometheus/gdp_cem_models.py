"""Goal-conditioned joint action diffusion and proposal-aware CEM.

This module is deliberately independent of stable-worldmodel internals.  The
solver implements the released structural protocol while preserving its full
Gaussian RNG stream before overwriting a predeclared candidate subset.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import torch
from torch import nn


ProposalKind = Literal["diffusion", "velocity", "gaussian"]
RefreshMode = Literal["none", "first", "all"]
ReturnMode = Literal["mean", "best"]
GADRCondition = Literal["gaussian", "true", "shuffled"]


def sinusoidal_embedding(timestep: torch.Tensor, dimension: int) -> torch.Tensor:
    if timestep.ndim != 1 or dimension < 4:
        raise ValueError("invalid diffusion timestep embedding input")
    half = dimension // 2
    scale = math.log(10_000.0) / max(half - 1, 1)
    frequency = torch.exp(
        -scale * torch.arange(half, device=timestep.device, dtype=torch.float32)
    )
    phase = timestep.float()[:, None] * frequency[None]
    value = torch.cat((phase.sin(), phase.cos()), dim=-1)
    if value.shape[1] < dimension:
        value = torch.nn.functional.pad(value, (0, dimension - value.shape[1]))
    return value


class FiLMResidualBlock(nn.Module):
    def __init__(self, width: int, condition_width: int) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.film = nn.Linear(condition_width, width * 2)
        self.input = nn.Linear(width, width * 2)
        self.output = nn.Linear(width * 2, width)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, value: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        scale, shift = self.film(condition).chunk(2, dim=-1)
        hidden = self.norm(value) * (1.0 + scale) + shift
        hidden = self.output(torch.nn.functional.silu(self.input(hidden)))
        return value + hidden


class JointActionBackbone(nn.Module):
    def __init__(
        self,
        *,
        latent_dim: int,
        primitive_action_dim: int,
        action_horizon: int = 25,
        width: int = 512,
        depth: int = 4,
        time_embedding_dim: int = 128,
    ) -> None:
        super().__init__()
        if min(latent_dim, primitive_action_dim, action_horizon, width, depth) <= 0:
            raise ValueError("invalid GDP-CEM backbone dimension")
        self.latent_dim = int(latent_dim)
        self.primitive_action_dim = int(primitive_action_dim)
        self.action_horizon = int(action_horizon)
        self.sequence_dim = self.action_horizon * self.primitive_action_dim
        self.width = int(width)
        self.depth = int(depth)
        self.time_embedding_dim = int(time_embedding_dim)
        self.action_input = nn.Linear(self.sequence_dim, self.width)
        self.condition = nn.Sequential(
            nn.Linear(3 * self.latent_dim, self.width),
            nn.SiLU(),
            nn.Linear(self.width, self.width),
        )
        self.time = nn.Sequential(
            nn.Linear(self.time_embedding_dim, self.width),
            nn.SiLU(),
            nn.Linear(self.width, self.width),
        )
        self.blocks = nn.ModuleList(
            [FiLMResidualBlock(self.width, self.width) for _ in range(self.depth)]
        )
        self.output_norm = nn.LayerNorm(self.width)

    def forward_features(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        noisy_action: torch.Tensor,
        timestep: torch.Tensor,
    ) -> torch.Tensor:
        if (
            current.ndim != 2
            or goal.shape != current.shape
            or current.shape[1] != self.latent_dim
            or noisy_action.shape
            != (current.shape[0], self.action_horizon, self.primitive_action_dim)
            or timestep.shape != (current.shape[0],)
        ):
            raise ValueError("GDP-CEM backbone input shape differs")
        condition = self.condition(torch.cat((current, goal, goal - current), dim=-1))
        condition = condition + self.time(
            sinusoidal_embedding(timestep, self.time_embedding_dim)
        )
        hidden = self.action_input(noisy_action.flatten(1)) + condition
        for block in self.blocks:
            hidden = block(hidden, condition)
        return self.output_norm(hidden)


class JointActionDiffusion(nn.Module):
    def __init__(self, **config: int) -> None:
        super().__init__()
        self.backbone = JointActionBackbone(**config)
        self.head = nn.Linear(self.backbone.width, self.backbone.sequence_dim)

    @property
    def latent_dim(self) -> int:
        return self.backbone.latent_dim

    @property
    def primitive_action_dim(self) -> int:
        return self.backbone.primitive_action_dim

    @property
    def action_horizon(self) -> int:
        return self.backbone.action_horizon

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        noisy_action: torch.Tensor,
        timestep: torch.Tensor,
    ) -> torch.Tensor:
        features = self.backbone.forward_features(current, goal, noisy_action, timestep)
        return self.head(features).reshape_as(noisy_action)


class VelocityActionDiffusion(nn.Module):
    """Goal-conditioned velocity model with an explicit classifier-free null."""

    def __init__(self, **config: int) -> None:
        super().__init__()
        self.backbone = JointActionBackbone(**config)
        self.head = nn.Linear(self.backbone.width, self.backbone.sequence_dim)
        self.null_goal = nn.Parameter(torch.zeros(self.backbone.latent_dim))

    @property
    def latent_dim(self) -> int:
        return self.backbone.latent_dim

    @property
    def primitive_action_dim(self) -> int:
        return self.backbone.primitive_action_dim

    @property
    def action_horizon(self) -> int:
        return self.backbone.action_horizon

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        noisy_action: torch.Tensor,
        timestep: torch.Tensor,
        conditioned: bool | torch.Tensor = True,
    ) -> torch.Tensor:
        if isinstance(conditioned, bool):
            mask = torch.full(
                (current.shape[0],),
                conditioned,
                device=current.device,
                dtype=torch.bool,
            )
        elif torch.is_tensor(conditioned) and conditioned.shape == (
            current.shape[0],
        ):
            mask = conditioned.to(device=current.device, dtype=torch.bool)
        else:
            raise ValueError("velocity-diffusion condition mask differs")
        null = self.null_goal.to(dtype=goal.dtype)[None].expand_as(goal)
        effective_goal = torch.where(mask[:, None], goal, null)
        features = self.backbone.forward_features(
            current, effective_goal, noisy_action, timestep
        )
        return self.head(features).reshape_as(noisy_action)


class ConditionalDiagonalGaussian(nn.Module):
    def __init__(self, **config: int) -> None:
        super().__init__()
        self.backbone = JointActionBackbone(**config)
        self.query = nn.Parameter(
            torch.zeros(
                1,
                self.backbone.action_horizon,
                self.backbone.primitive_action_dim,
            )
        )
        self.head = nn.Linear(self.backbone.width, self.backbone.sequence_dim * 2)

    @property
    def latent_dim(self) -> int:
        return self.backbone.latent_dim

    @property
    def primitive_action_dim(self) -> int:
        return self.backbone.primitive_action_dim

    @property
    def action_horizon(self) -> int:
        return self.backbone.action_horizon

    def forward(
        self, current: torch.Tensor, goal: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch = current.shape[0]
        query = self.query.expand(batch, -1, -1)
        timestep = torch.zeros(batch, device=current.device, dtype=torch.long)
        features = self.backbone.forward_features(current, goal, query, timestep)
        mean, log_std = self.head(features).chunk(2, dim=-1)
        shape = (batch, self.action_horizon, self.primitive_action_dim)
        return mean.reshape(shape), log_std.reshape(shape).clamp(-5.0, 2.0)


@dataclass(frozen=True)
class CosineDiffusionSchedule:
    alpha_bar: torch.Tensor

    @classmethod
    def build(cls, steps: int = 100, offset: float = 0.008) -> "CosineDiffusionSchedule":
        if steps <= 1 or offset < 0:
            raise ValueError("invalid cosine schedule")
        point = torch.linspace(0, steps, steps + 1, dtype=torch.float64)
        cumulative = torch.cos(
            ((point / steps + offset) / (1.0 + offset)) * math.pi / 2.0
        ).square()
        cumulative = cumulative / cumulative[0]
        beta = (1.0 - cumulative[1:] / cumulative[:-1]).clamp(1.0e-5, 0.999)
        alpha_bar = torch.cumprod(1.0 - beta, dim=0).float()
        return cls(alpha_bar=alpha_bar)

    @property
    def steps(self) -> int:
        return int(self.alpha_bar.numel())


@torch.inference_mode()
def ddim_sample(
    model: JointActionDiffusion,
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    count: int,
    inference_steps: int,
    schedule: CosineDiffusionSchedule,
    generator: torch.Generator,
) -> torch.Tensor:
    if count <= 0 or not 1 <= inference_steps <= schedule.steps:
        raise ValueError("invalid GDP-CEM DDIM sample configuration")
    batch = current.shape[0]
    current = current[:, None].expand(batch, count, -1).reshape(batch * count, -1)
    goal = goal[:, None].expand(batch, count, -1).reshape(batch * count, -1)
    shape = (
        batch * count,
        model.action_horizon,
        model.primitive_action_dim,
    )
    value = torch.randn(
        shape,
        generator=generator,
        device=current.device,
        dtype=current.dtype,
    )
    time_grid = torch.linspace(
        schedule.steps - 1, 0, inference_steps, device=current.device
    ).round().long()
    alpha_bar = schedule.alpha_bar.to(device=current.device, dtype=current.dtype)
    for index, timestep_value in enumerate(time_grid.tolist()):
        timestep = torch.full(
            (batch * count,), timestep_value, device=current.device, dtype=torch.long
        )
        predicted_noise = model(current, goal, value, timestep)
        alpha = alpha_bar[timestep_value]
        clean = (value - (1.0 - alpha).sqrt() * predicted_noise) / alpha.sqrt()
        if index + 1 == len(time_grid):
            value = clean
        else:
            next_alpha = alpha_bar[int(time_grid[index + 1])]
            value = next_alpha.sqrt() * clean + (1.0 - next_alpha).sqrt() * predicted_noise
    if not torch.isfinite(value).all():
        raise RuntimeError("GDP-CEM DDIM sample is non-finite")
    return value.reshape(batch, count, model.action_horizon, model.primitive_action_dim)


@torch.inference_mode()
def classifier_free_velocity_prediction(
    model: VelocityActionDiffusion,
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    noisy_action: torch.Tensor,
    timestep: torch.Tensor,
    guidance_scale: float,
) -> torch.Tensor:
    """Combine conditional and null-goal velocity predictions exactly once."""

    if not math.isfinite(guidance_scale) or guidance_scale < 0.0:
        raise ValueError("invalid classifier-free velocity guidance scale")
    if guidance_scale == 0.0:
        return model(current, goal, noisy_action, timestep, conditioned=False)
    if guidance_scale == 1.0:
        return model(current, goal, noisy_action, timestep, conditioned=True)
    unconditional = model(
        current, goal, noisy_action, timestep, conditioned=False
    )
    conditional = model(current, goal, noisy_action, timestep, conditioned=True)
    return unconditional + guidance_scale * (conditional - unconditional)


@torch.inference_mode()
def velocity_ddim_sample(
    model: VelocityActionDiffusion,
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    count: int,
    inference_steps: int,
    schedule: CosineDiffusionSchedule,
    generator: torch.Generator,
    guidance_scale: float,
    clip_low: torch.Tensor,
    clip_high: torch.Tensor,
) -> torch.Tensor:
    """Stable deterministic pure-noise DDIM sampling from velocity predictions."""

    if (
        current.ndim != 2
        or goal.shape != current.shape
        or current.shape[1] != model.latent_dim
        or count <= 0
        or not 2 <= inference_steps <= schedule.steps
        or not math.isfinite(guidance_scale)
        or guidance_scale < 0.0
    ):
        raise ValueError("invalid velocity-DDIM sampling configuration")
    time_grid = torch.linspace(
        schedule.steps - 1,
        0,
        inference_steps,
        device=current.device,
    ).round().long()
    if (
        time_grid[0] != schedule.steps - 1
        or time_grid[-1] != 0
        or torch.unique_consecutive(time_grid).numel() != inference_steps
        or not torch.all(time_grid[:-1] > time_grid[1:])
    ):
        raise ValueError("velocity-DDIM time grid contains duplicates")
    batch = current.shape[0]
    value = torch.randn(
        (batch * count, model.action_horizon, model.primitive_action_dim),
        generator=generator,
        device=current.device,
        dtype=current.dtype,
    )
    expanded_current = current[:, None].expand(batch, count, -1).reshape(
        batch * count, -1
    )
    expanded_goal = goal[:, None].expand(batch, count, -1).reshape(
        batch * count, -1
    )
    low = torch.as_tensor(
        clip_low, device=value.device, dtype=value.dtype
    ).reshape(1, 1, model.primitive_action_dim)
    high = torch.as_tensor(
        clip_high, device=value.device, dtype=value.dtype
    ).reshape(1, 1, model.primitive_action_dim)
    if (
        torch.any(high <= low)
        or not torch.isfinite(low).all()
        or not torch.isfinite(high).all()
    ):
        raise ValueError("invalid velocity-DDIM robust bounds")
    alpha_bar = schedule.alpha_bar.to(device=value.device, dtype=value.dtype)
    for index, timestep_value in enumerate(time_grid.tolist()):
        timestep = torch.full(
            (batch * count,), timestep_value, device=value.device, dtype=torch.long
        )
        velocity = classifier_free_velocity_prediction(
            model,
            current=expanded_current,
            goal=expanded_goal,
            noisy_action=value,
            timestep=timestep,
            guidance_scale=guidance_scale,
        )
        alpha = alpha_bar[timestep_value]
        clean = alpha.sqrt() * value - (1.0 - alpha).sqrt() * velocity
        clean = torch.maximum(torch.minimum(clean, high), low)
        if index + 1 == len(time_grid):
            value = clean
        else:
            noise = (value - alpha.sqrt() * clean) / (1.0 - alpha).sqrt().clamp_min(
                1.0e-8
            )
            next_alpha = alpha_bar[int(time_grid[index + 1])]
            value = next_alpha.sqrt() * clean + (1.0 - next_alpha).sqrt() * noise
    if not torch.isfinite(value).all():
        raise RuntimeError("velocity-DDIM sample is non-finite")
    return value.reshape(
        batch, count, model.action_horizon, model.primitive_action_dim
    )


@torch.inference_mode()
def ddim_refine_epsilon(
    model: JointActionDiffusion,
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    clean: torch.Tensor,
    restart_timestep: int,
    inference_steps: int,
    schedule: CosineDiffusionSchedule,
    generator: torch.Generator,
    clip_low: torch.Tensor,
    clip_high: torch.Tensor,
) -> torch.Tensor:
    """Moderate-noise deterministic DDIM projection of an existing action bank."""

    if (
        clean.ndim != 4
        or current.ndim != 2
        or goal.shape != current.shape
        or clean.shape[0] != current.shape[0]
        or clean.shape[2:] != (model.action_horizon, model.primitive_action_dim)
        or not 0 <= restart_timestep < schedule.steps
        or not 1 <= inference_steps <= restart_timestep + 1
    ):
        raise ValueError("invalid GDP-CEM DDIM refinement configuration")
    time_grid = (
        torch.tensor((restart_timestep,), device=current.device, dtype=torch.long)
        if inference_steps == 1
        else torch.linspace(
            restart_timestep, 0, inference_steps, device=current.device
        ).round().long()
    )
    if (
        time_grid[0] != restart_timestep
        or (inference_steps > 1 and time_grid[-1] != 0)
        or torch.unique_consecutive(time_grid).numel() != inference_steps
        or not torch.all(time_grid[:-1] > time_grid[1:])
    ):
        raise ValueError("GDP-CEM DDIM refinement time grid contains duplicates")
    batch, count = clean.shape[:2]
    expanded_current = current[:, None].expand(batch, count, -1).reshape(
        batch * count, -1
    )
    expanded_goal = goal[:, None].expand(batch, count, -1).reshape(
        batch * count, -1
    )
    clean_flat = clean.reshape(
        batch * count, model.action_horizon, model.primitive_action_dim
    )
    low = torch.as_tensor(
        clip_low, device=clean.device, dtype=clean.dtype
    ).reshape(1, 1, model.primitive_action_dim)
    high = torch.as_tensor(
        clip_high, device=clean.device, dtype=clean.dtype
    ).reshape(1, 1, model.primitive_action_dim)
    if (
        torch.any(high <= low)
        or not torch.isfinite(clean_flat).all()
        or not torch.isfinite(low).all()
        or not torch.isfinite(high).all()
    ):
        raise ValueError("invalid GDP-CEM DDIM refinement bank or bounds")
    alpha_bar = schedule.alpha_bar.to(device=clean.device, dtype=clean.dtype)
    initial_alpha = alpha_bar[restart_timestep]
    noise = torch.randn(
        clean_flat.shape,
        generator=generator,
        device=clean.device,
        dtype=clean.dtype,
    )
    value = initial_alpha.sqrt() * clean_flat + (1.0 - initial_alpha).sqrt() * noise
    for index, timestep_value in enumerate(time_grid.tolist()):
        timestep = torch.full(
            (batch * count,), timestep_value, device=clean.device, dtype=torch.long
        )
        predicted_noise = model(
            expanded_current, expanded_goal, value, timestep
        )
        alpha = alpha_bar[timestep_value]
        clean_estimate = (
            value - (1.0 - alpha).sqrt() * predicted_noise
        ) / alpha.sqrt()
        clean_estimate = torch.maximum(torch.minimum(clean_estimate, high), low)
        if index + 1 == len(time_grid):
            value = clean_estimate
        else:
            next_alpha = alpha_bar[int(time_grid[index + 1])]
            value = (
                next_alpha.sqrt() * clean_estimate
                + (1.0 - next_alpha).sqrt() * predicted_noise
            )
    if not torch.isfinite(value).all():
        raise RuntimeError("GDP-CEM DDIM refinement is non-finite")
    return value.reshape_as(clean)


@torch.inference_mode()
def gaussian_sample(
    model: ConditionalDiagonalGaussian,
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    count: int,
    generator: torch.Generator,
) -> torch.Tensor:
    if count <= 0:
        raise ValueError("invalid GDP-CEM Gaussian sample count")
    mean, log_std = model(current, goal)
    noise = torch.randn(
        (current.shape[0], count, model.action_horizon, model.primitive_action_dim),
        generator=generator,
        device=current.device,
        dtype=current.dtype,
    )
    value = mean[:, None] + log_std.exp()[:, None] * noise
    if not torch.isfinite(value).all():
        raise RuntimeError("GDP-CEM conditional-Gaussian sample is non-finite")
    return value


class GoalConditionedProposalSampler(nn.Module):
    """Encode one planner condition and generate planner-coordinate proposals."""

    def __init__(
        self,
        world_model: nn.Module,
        proposal_model: (
            JointActionDiffusion
            | VelocityActionDiffusion
            | ConditionalDiagonalGaussian
        ),
        *,
        kind: ProposalKind,
        latent_mean: torch.Tensor,
        latent_std: torch.Tensor,
        action_mean: torch.Tensor,
        action_std: torch.Tensor,
        robust_low: torch.Tensor,
        robust_high: torch.Tensor,
        inference_steps: int = 10,
        schedule_steps: int = 100,
        guidance_scale: float = 1.0,
    ) -> None:
        super().__init__()
        if kind == "diffusion" and not isinstance(proposal_model, JointActionDiffusion):
            raise TypeError("diffusion sampler requires JointActionDiffusion")
        if kind == "velocity" and not isinstance(
            proposal_model, VelocityActionDiffusion
        ):
            raise TypeError("velocity sampler requires VelocityActionDiffusion")
        if kind == "gaussian" and not isinstance(
            proposal_model, ConditionalDiagonalGaussian
        ):
            raise TypeError("Gaussian sampler requires ConditionalDiagonalGaussian")
        if not math.isfinite(guidance_scale) or guidance_scale < 0.0:
            raise ValueError("invalid proposal guidance scale")
        self.world_model = world_model
        self.proposal_model = proposal_model
        self.kind = kind
        self.inference_steps = int(inference_steps)
        self.guidance_scale = float(guidance_scale)
        self.schedule = CosineDiffusionSchedule.build(schedule_steps)
        self.diagnostic_history: list[dict[str, Any]] = []
        world_device = next(self.world_model.parameters()).device
        proposal_device = next(self.proposal_model.parameters()).device
        if world_device != proposal_device:
            raise ValueError("GDP-CEM world and proposal models must share a device")
        for name, value in (
            ("latent_mean", latent_mean),
            ("latent_std", latent_std),
            ("action_mean", action_mean),
            ("action_std", action_std),
            ("robust_low", robust_low),
            ("robust_high", robust_high),
        ):
            self.register_buffer(
                name,
                torch.as_tensor(value, device=world_device, dtype=torch.float32),
                persistent=True,
            )
        if (
            self.latent_mean.shape != (proposal_model.latent_dim,)
            or self.latent_std.shape != self.latent_mean.shape
            or self.action_mean.shape != (proposal_model.primitive_action_dim,)
            or self.action_std.shape != self.action_mean.shape
            or self.robust_low.shape != self.action_mean.shape
            or self.robust_high.shape != self.action_mean.shape
            or torch.any(self.latent_std <= 1.0e-6)
            or torch.any(self.action_std <= 1.0e-6)
            or torch.any(self.robust_high <= self.robust_low)
        ):
            raise ValueError("invalid GDP-CEM proposal statistics")

    @torch.inference_mode()
    def prepare(self, info_dict: dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor]:
        device = next(self.world_model.parameters()).device
        work = {
            key: value.to(device) if torch.is_tensor(value) else value
            for key, value in info_dict.items()
        }
        current = {key: value for key, value in work.items() if torch.is_tensor(value)}
        current.pop("action", None)
        goal = {key: value for key, value in work.items() if torch.is_tensor(value)}
        if "goal" not in goal:
            raise KeyError("goal not in GDP-CEM proposal info")
        goal["pixels"] = goal["goal"]
        for key in list(goal):
            if key.startswith("goal_"):
                goal[key.removeprefix("goal_")] = goal.pop(key)
        goal.pop("action", None)
        current_embedding = self.world_model.encode(current)["emb"][:, -1]
        goal_embedding = self.world_model.encode(goal)["emb"][:, -1]
        current_embedding = (current_embedding - self.latent_mean) / self.latent_std
        goal_embedding = (goal_embedding - self.latent_mean) / self.latent_std
        if (
            current_embedding.shape != goal_embedding.shape
            or current_embedding.shape[-1] != self.proposal_model.latent_dim
            or not torch.isfinite(current_embedding).all()
            or not torch.isfinite(goal_embedding).all()
        ):
            raise RuntimeError("GDP-CEM encoded condition is invalid")
        return current_embedding, goal_embedding

    @torch.inference_mode()
    def sample(
        self,
        context: tuple[torch.Tensor, torch.Tensor],
        *,
        count: int,
        generator: torch.Generator,
    ) -> torch.Tensor:
        current, goal = context
        generator_state_before = hashlib.sha256(
            generator.get_state().cpu().numpy().tobytes()
        ).hexdigest()
        if self.kind == "diffusion":
            assert isinstance(self.proposal_model, JointActionDiffusion)
            normalized = ddim_sample(
                self.proposal_model,
                current=current,
                goal=goal,
                count=count,
                inference_steps=self.inference_steps,
                schedule=self.schedule,
                generator=generator,
            )
        elif self.kind == "velocity":
            assert isinstance(self.proposal_model, VelocityActionDiffusion)
            normalized_low = (self.robust_low - self.action_mean) / self.action_std
            normalized_high = (self.robust_high - self.action_mean) / self.action_std
            normalized = velocity_ddim_sample(
                self.proposal_model,
                current=current,
                goal=goal,
                count=count,
                inference_steps=self.inference_steps,
                schedule=self.schedule,
                generator=generator,
                guidance_scale=self.guidance_scale,
                clip_low=normalized_low,
                clip_high=normalized_high,
            )
        else:
            assert isinstance(self.proposal_model, ConditionalDiagonalGaussian)
            normalized = gaussian_sample(
                self.proposal_model,
                current=current,
                goal=goal,
                count=count,
                generator=generator,
            )
        normalized_low = ((self.robust_low - self.action_mean) / self.action_std).reshape(
            1, 1, 1, -1
        )
        normalized_high = (
            (self.robust_high - self.action_mean) / self.action_std
        ).reshape(1, 1, 1, -1)
        clipped = torch.maximum(
            torch.minimum(normalized, normalized_high), normalized_low
        )
        boundary = torch.logical_or(
            clipped == normalized_low, clipped == normalized_high
        ).float().mean()
        diversity = clipped.flatten(2).std(dim=1).mean()
        self.diagnostic_history.append(
            {
                "call": len(self.diagnostic_history),
                "kind": self.kind,
                "candidate_count": int(count),
                "guidance_scale": self.guidance_scale,
                "boundary_fraction": float(boundary.cpu()),
                "mean_coordinate_std": float(diversity.cpu()),
                "generator_state_before_sha256": generator_state_before,
                "generator_state_after_sha256": hashlib.sha256(
                    generator.get_state().cpu().numpy().tobytes()
                ).hexdigest(),
            }
        )
        planner = clipped * self.action_std + self.action_mean
        planner = torch.maximum(
            torch.minimum(planner, self.robust_high), self.robust_low
        )
        batch = planner.shape[0]
        planner = planner.reshape(
            batch,
            count,
            5,
            5 * self.proposal_model.primitive_action_dim,
        )
        if not torch.isfinite(planner).all():
            raise RuntimeError("GDP-CEM planner proposal is non-finite")
        return planner


class GaussianAnchoredRefinementSampler(GoalConditionedProposalSampler):
    """Sample a Gaussian action bank and refine a fixed fraction by diffusion."""

    def __init__(
        self,
        world_model: nn.Module,
        gaussian_model: ConditionalDiagonalGaussian,
        refinement_model: JointActionDiffusion | None,
        *,
        condition: GADRCondition,
        latent_mean: torch.Tensor,
        latent_std: torch.Tensor,
        action_mean: torch.Tensor,
        action_std: torch.Tensor,
        robust_low: torch.Tensor,
        robust_high: torch.Tensor,
        restart_timestep: int = 40,
        inference_steps: int = 1,
        refined_fraction: float = 0.5,
        schedule_steps: int = 100,
    ) -> None:
        super().__init__(
            world_model,
            gaussian_model,
            kind="gaussian",
            latent_mean=latent_mean,
            latent_std=latent_std,
            action_mean=action_mean,
            action_std=action_std,
            robust_low=robust_low,
            robust_high=robust_high,
            inference_steps=inference_steps,
            schedule_steps=schedule_steps,
        )
        if (
            condition not in ("gaussian", "true", "shuffled")
            or (condition == "gaussian") != (refinement_model is None)
            or not 0.0 <= refined_fraction <= 1.0
            or not 0 <= restart_timestep < schedule_steps
            or not 1 <= inference_steps <= restart_timestep + 1
        ):
            raise ValueError("invalid GADR sampler configuration")
        if refinement_model is not None:
            if (
                refinement_model.latent_dim != gaussian_model.latent_dim
                or refinement_model.primitive_action_dim
                != gaussian_model.primitive_action_dim
                or refinement_model.action_horizon != gaussian_model.action_horizon
                or next(refinement_model.parameters()).device
                != next(gaussian_model.parameters()).device
            ):
                raise ValueError("GADR Gaussian/refinement model mismatch")
        self.refinement_model = refinement_model
        self.condition = condition
        self.restart_timestep = int(restart_timestep)
        self.refined_fraction = float(refined_fraction)
        self.diagnostic_history: list[dict[str, Any]] = []

    @staticmethod
    def refined_count(count: int, fraction: float) -> int:
        if count <= 0 or not 0.0 <= fraction <= 1.0:
            raise ValueError("invalid GADR candidate count or fraction")
        return int(math.floor((count - 1) * fraction + 0.5))

    @torch.inference_mode()
    def sample(
        self,
        context: tuple[torch.Tensor, torch.Tensor],
        *,
        count: int,
        generator: torch.Generator,
    ) -> torch.Tensor:
        current, goal = context
        gaussian = self.proposal_model
        assert isinstance(gaussian, ConditionalDiagonalGaussian)
        mean, log_std = gaussian(current, goal)
        base_noise = torch.randn(
            (
                current.shape[0],
                count,
                gaussian.action_horizon,
                gaussian.primitive_action_dim,
            ),
            generator=generator,
            device=current.device,
            dtype=current.dtype,
        )
        base = mean[:, None] + log_std.exp()[:, None] * base_noise
        base[:, 0] = mean
        normalized_low = ((self.robust_low - self.action_mean) / self.action_std).reshape(
            1, 1, 1, -1
        )
        normalized_high = (
            (self.robust_high - self.action_mean) / self.action_std
        ).reshape(1, 1, 1, -1)
        base = torch.maximum(torch.minimum(base, normalized_high), normalized_low)
        replace_count = self.refined_count(count, self.refined_fraction)
        if self.refinement_model is None:
            # Consume the exact forward-noise draw used by true/shuffled GADR so
            # later Gaussian bases remain matched across otherwise identical runs.
            torch.randn(
                base.shape,
                generator=generator,
                device=base.device,
                dtype=base.dtype,
            )
            mixed = base
            displacement = 0.0
            effective_count = 0
        else:
            refined = ddim_refine_epsilon(
                self.refinement_model,
                current=current,
                goal=goal,
                clean=base,
                restart_timestep=self.restart_timestep,
                inference_steps=self.inference_steps,
                schedule=self.schedule,
                generator=generator,
                clip_low=normalized_low.flatten(),
                clip_high=normalized_high.flatten(),
            )
            mixed = base.clone()
            mixed[:, 1 : 1 + replace_count] = refined[:, 1 : 1 + replace_count]
            displacement = float((mixed - base).square().mean().cpu())
            effective_count = replace_count
        boundary = torch.logical_or(
            mixed == normalized_low, mixed == normalized_high
        ).float().mean()
        self.diagnostic_history.append(
            {
                "call": len(self.diagnostic_history),
                "condition": self.condition,
                "candidate_count": int(count),
                "refined_count": int(effective_count),
                "matched_refinement_slots": int(replace_count),
                "boundary_fraction": float(boundary.cpu()),
                "refinement_displacement_mse": displacement,
            }
        )
        planner = mixed * self.action_std + self.action_mean
        planner = torch.maximum(
            torch.minimum(planner, self.robust_high), self.robust_low
        )
        planner = planner.reshape(
            current.shape[0],
            count,
            5,
            5 * gaussian.primitive_action_dim,
        )
        if not torch.isfinite(planner).all():
            raise RuntimeError("GADR planner proposal is non-finite")
        return planner


class ProposalCEMSolver:
    """Released CEM with a deterministic, matched candidate overwrite slot."""

    def __init__(
        self,
        model: Any,
        *,
        proposal_sampler: GoalConditionedProposalSampler | None,
        proposal_fraction: float,
        refresh_mode: RefreshMode,
        batch_size: int = 1,
        num_samples: int = 300,
        var_scale: float = 1.0,
        n_steps: int = 30,
        topk: int = 30,
        device: str | torch.device = "cpu",
        seed: int = 1234,
        proposal_seed: int = 5678,
        return_mode: ReturnMode = "mean",
        preserve_mean_candidate: bool = True,
    ) -> None:
        if (
            not 0.0 <= proposal_fraction <= 1.0
            or refresh_mode not in ("none", "first", "all")
            or (refresh_mode == "none") != (proposal_fraction == 0.0)
            or (proposal_fraction > 0.0) != (proposal_sampler is not None)
            or return_mode not in ("mean", "best")
        ):
            raise ValueError("invalid GDP-CEM proposal integration")
        self.model = model
        self.proposal_sampler = proposal_sampler
        self.proposal_fraction = float(proposal_fraction)
        self.refresh_mode = refresh_mode
        self.return_mode = return_mode
        self.preserve_mean_candidate = bool(preserve_mean_candidate)
        self.batch_size = int(batch_size)
        self.var_scale = float(var_scale)
        self.num_samples = int(num_samples)
        self.n_steps = int(n_steps)
        self.topk = int(topk)
        self.device = torch.device(device)
        self.torch_gen = torch.Generator(device=self.device).manual_seed(int(seed))
        self.proposal_gen = torch.Generator(device=self.device).manual_seed(
            int(proposal_seed)
        )
        self.diagnostic_history: list[dict[str, Any]] = []

    def configure(self, *, action_space: Any, n_envs: int, config: Any) -> None:
        self._action_space = action_space
        self._n_envs = int(n_envs)
        self._config = config
        self._action_dim = int(np.prod(action_space.shape[1:]))
        self._configured = True

    @property
    def n_envs(self) -> int:
        return self._n_envs

    @property
    def action_dim(self) -> int:
        return self._action_dim * self._config.action_block

    @property
    def horizon(self) -> int:
        return self._config.horizon

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.solve(*args, **kwargs)

    def init_action_distrib(
        self, actions: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        var = self.var_scale * torch.ones([self.n_envs, self.horizon, self.action_dim])
        mean = (
            torch.zeros([self.n_envs, 0, self.action_dim])
            if actions is None
            else actions
        )
        remaining = self.horizon - mean.shape[1]
        if remaining > 0:
            device = mean.device
            new_mean = torch.zeros([self.n_envs, remaining, self.action_dim])
            mean = torch.cat([mean, new_mean], dim=1).to(device)
        return mean, var

    @torch.inference_mode()
    def solve(
        self, info_dict: dict[str, Any], init_action: torch.Tensor | None = None
    ) -> dict[str, Any]:
        started = time.time()
        outputs: dict[str, Any] = {"costs": [], "mean": [], "var": []}
        mean, var = self.init_action_distrib(init_action)
        mean = mean.to(self.device)
        var = var.to(self.device)
        proposal_slots = self.num_samples - int(self.preserve_mean_candidate)
        proposal_count = int(round(proposal_slots * self.proposal_fraction))
        for start_idx in range(0, self.n_envs, self.batch_size):
            end_idx = min(start_idx + self.batch_size, self.n_envs)
            current_bs = end_idx - start_idx
            batch_mean = mean[start_idx:end_idx]
            batch_var = var[start_idx:end_idx]
            batch_info = {
                key: value[start_idx:end_idx]
                if torch.is_tensor(value) or isinstance(value, np.ndarray)
                else value
                for key, value in info_dict.items()
            }
            expanded_infos: dict[str, Any] = {}
            for key, value in batch_info.items():
                if torch.is_tensor(value):
                    expanded_infos[key] = value.unsqueeze(1).expand(
                        current_bs, self.num_samples, *value.shape[1:]
                    )
                elif isinstance(value, np.ndarray):
                    expanded_infos[key] = np.repeat(
                        value[:, None, ...], self.num_samples, axis=1
                    )
                else:
                    expanded_infos[key] = value
            context = (
                self.proposal_sampler.prepare(batch_info)
                if self.proposal_sampler is not None
                else None
            )
            final_batch_cost = None
            final_topk_candidates = None
            for step in range(self.n_steps):
                active = self.refresh_mode == "all" or (
                    self.refresh_mode == "first" and step == 0
                )
                full_proposal_bank = (
                    active
                    and not self.preserve_mean_candidate
                    and proposal_count == self.num_samples
                )
                if full_proposal_bank:
                    # Selector mode replaces the complete bank.  Do not draw an
                    # unused CEM Gaussian tensor: this keeps both the runtime and
                    # the claimed one-pool sampling semantics exact.
                    candidates = torch.empty(
                        current_bs,
                        self.num_samples,
                        self.horizon,
                        self.action_dim,
                        device=self.device,
                    )
                else:
                    candidates = torch.randn(
                        current_bs,
                        self.num_samples,
                        self.horizon,
                        self.action_dim,
                        generator=self.torch_gen,
                        device=self.device,
                    )
                    candidates = (
                        candidates * batch_var.unsqueeze(1) + batch_mean.unsqueeze(1)
                    )
                    if self.preserve_mean_candidate:
                        candidates[:, 0] = batch_mean
                proposal_seconds = 0.0
                if active:
                    assert self.proposal_sampler is not None and context is not None
                    proposal_started = time.perf_counter()
                    proposed = self.proposal_sampler.sample(
                        context, count=proposal_count, generator=self.proposal_gen
                    )
                    proposal_seconds = time.perf_counter() - proposal_started
                    expected = (
                        current_bs,
                        proposal_count,
                        self.horizon,
                        self.action_dim,
                    )
                    if proposed.shape != expected:
                        raise RuntimeError(
                            f"GDP-CEM proposal shape {tuple(proposed.shape)} != {expected}"
                        )
                    proposal_start = int(self.preserve_mean_candidate)
                    candidates[
                        :, proposal_start : proposal_start + proposal_count
                    ] = proposed
                costs = self.model.get_cost(expanded_infos.copy(), candidates)
                if costs.shape != (current_bs, self.num_samples):
                    raise RuntimeError("GDP-CEM cost shape differs")
                topk_vals, topk_inds = torch.topk(
                    costs, k=self.topk, dim=1, largest=False
                )
                batch_indices = torch.arange(
                    current_bs, device=self.device
                ).unsqueeze(1).expand(-1, self.topk)
                topk_candidates = candidates[batch_indices, topk_inds]
                batch_mean = topk_candidates.mean(dim=1)
                batch_var = topk_candidates.std(dim=1)
                final_batch_cost = topk_vals.mean(dim=1).cpu().tolist()
                final_topk_candidates = topk_candidates
                self.diagnostic_history.append(
                    {
                        "batch_start": start_idx,
                        "iteration": step + 1,
                        "proposal_active": active,
                        "proposal_count": proposal_count if active else 0,
                        "proposal_seconds": proposal_seconds,
                    }
                )
            assert final_topk_candidates is not None
            selected = (
                batch_mean
                if self.return_mode == "mean"
                else final_topk_candidates[:, 0]
            )
            mean[start_idx:end_idx] = selected
            var[start_idx:end_idx] = batch_var
            assert final_batch_cost is not None
            outputs["costs"].extend(final_batch_cost)
        outputs["actions"] = mean.detach().cpu()
        outputs["mean"] = [mean.detach().cpu()]
        outputs["var"] = [var.detach().cpu()]
        outputs["solver_seconds"] = time.time() - started
        return outputs


def model_config_from_payload(payload: dict[str, Any]) -> dict[str, int]:
    config = payload.get("model_config", {})
    required = (
        "latent_dim",
        "primitive_action_dim",
        "action_horizon",
        "width",
        "depth",
        "time_embedding_dim",
    )
    if any(key not in config for key in required):
        raise RuntimeError("GDP-CEM checkpoint model configuration is incomplete")
    return {key: int(config[key]) for key in required}


def load_proposal_model(
    payload: dict[str, Any], *, device: torch.device
) -> JointActionDiffusion | VelocityActionDiffusion | ConditionalDiagonalGaussian:
    kind = payload.get("proposal_kind")
    config = model_config_from_payload(payload)
    if kind == "diffusion":
        model: JointActionDiffusion | VelocityActionDiffusion | ConditionalDiagonalGaussian = (
            JointActionDiffusion(**config)
        )
    elif kind == "velocity_diffusion":
        model = VelocityActionDiffusion(**config)
    elif kind == "gaussian":
        model = ConditionalDiagonalGaussian(**config)
    else:
        raise RuntimeError("unknown GDP-CEM checkpoint proposal kind")
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    return model.to(device).eval().requires_grad_(False)


__all__ = [
    "ConditionalDiagonalGaussian",
    "classifier_free_velocity_prediction",
    "CosineDiffusionSchedule",
    "GaussianAnchoredRefinementSampler",
    "GoalConditionedProposalSampler",
    "JointActionDiffusion",
    "VelocityActionDiffusion",
    "ProposalCEMSolver",
    "ddim_sample",
    "ddim_refine_epsilon",
    "velocity_ddim_sample",
    "gaussian_sample",
    "load_proposal_model",
]
