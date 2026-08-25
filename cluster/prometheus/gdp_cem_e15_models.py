"""E15 learned proposal models and the common smooth bounded-action decoder."""

from __future__ import annotations

import math
from typing import Any

import torch
from torch import nn

import gdp_cem_e15_specs as spec
from gdp_cem_e14_models import (
    CosineSchedule,
    FiLMResidualBlock,
    VariableConditionEncoder,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    sample_trajectory_gmm,
    trajectory_gmm_nll,
    velocity_ddim_sample,
    velocity_target,
)


class DirectTrajectoryGMM(nn.Module):
    """Direct far-goal trajectory-level eight-mode GMM in standardized u-space."""

    def __init__(
        self,
        *,
        latent_dim: int,
        state_dim: int,
        primitive_action_dim: int,
        horizon: int = 25,
        modes: int = 8,
        width: int = 512,
        depth: int = 4,
    ) -> None:
        super().__init__()
        if min(
            latent_dim,
            state_dim,
            primitive_action_dim,
            horizon,
            modes,
            width,
            depth,
        ) <= 0:
            raise ValueError("invalid E15 GMM dimension")
        self.latent_dim = int(latent_dim)
        self.state_dim = int(state_dim)
        self.primitive_action_dim = int(primitive_action_dim)
        self.horizon = int(horizon)
        self.modes = int(modes)
        self.width = int(width)
        self.depth = int(depth)
        self.output_dim = self.horizon * self.primitive_action_dim
        self.condition = VariableConditionEncoder(
            latent_dim=self.latent_dim,
            state_dim=self.state_dim,
            width=self.width,
        )
        self.query = nn.Parameter(torch.zeros(self.width))
        nn.init.normal_(self.query, std=0.02)
        self.blocks = nn.ModuleList(
            [FiLMResidualBlock(self.width) for _ in range(self.depth)]
        )
        self.norm = nn.LayerNorm(self.width)
        self.mean_head = nn.Linear(self.width, self.modes * self.output_dim)
        self.log_std_head = nn.Linear(self.width, self.modes * self.output_dim)
        self.logit_head = nn.Linear(self.width, self.modes)

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        condition = self.condition(current, goal, state, delta, tau)
        hidden = self.query[None].expand(current.shape[0], -1) + condition
        for block in self.blocks:
            hidden = block(hidden, condition)
        hidden = self.norm(hidden)
        shape = (
            current.shape[0],
            self.modes,
            self.horizon,
            self.primitive_action_dim,
        )
        means = self.mean_head(hidden).reshape(shape)
        log_stds = self.log_std_head(hidden).reshape(shape).clamp(
            spec.LOG_STD_MIN, spec.LOG_STD_MAX
        )
        logits = self.logit_head(hidden)
        return logits, means, log_stds


def direct_gmm_loss(
    logits: torch.Tensor,
    means: torch.Tensor,
    log_stds: torch.Tensor,
    target: torch.Tensor,
    active_mask: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Dimension-normalized mixture NLL plus frozen global load balancing."""

    nll = trajectory_gmm_nll(logits, means, log_stds, target, active_mask)
    active_dimensions = (
        active_mask.sum(dim=1).to(means.dtype) * means.shape[-1]
    ).clamp_min(1.0)
    normalized_nll = (nll / active_dimensions).mean()
    mean_probability = torch.softmax(logits, dim=-1).mean(dim=0)
    balance = (
        mean_probability
        * (mean_probability.clamp_min(1.0e-12).log() + math.log(logits.shape[-1]))
    ).sum()
    total = normalized_nll + spec.GMM_BALANCE_WEIGHT * balance
    return total, normalized_nll, balance


def trajectory_gmm_posterior(
    logits: torch.Tensor,
    means: torch.Tensor,
    log_stds: torch.Tensor,
    target: torch.Tensor,
    active_mask: torch.Tensor,
) -> torch.Tensor:
    """Posterior component responsibilities under the trajectory mixture."""

    batch, modes, horizon, action_dim = means.shape
    if (
        logits.shape != (batch, modes)
        or log_stds.shape != means.shape
        or target.shape != (batch, horizon, action_dim)
        or active_mask.shape != (batch, horizon)
    ):
        raise ValueError("E15 GMM posterior shape differs")
    mask = active_mask[:, None, :, None].to(means.dtype)
    standardized = (target[:, None] - means) / log_stds.exp()
    element = (
        0.5 * standardized.square()
        + log_stds
        + 0.5 * math.log(2.0 * math.pi)
    )
    component = torch.log_softmax(logits, dim=-1) - (element * mask).sum(
        dim=(-1, -2)
    )
    return torch.softmax(component, dim=-1)


def action_active_mask(
    tau: torch.Tensor,
    *,
    primitive_action_dim: int,
    horizon: int = spec.ACTION_HORIZON,
) -> torch.Tensor:
    if tau.ndim != 1:
        raise ValueError("E15 duration tensor shape differs")
    return (
        torch.arange(horizon, device=tau.device)[None, :] < tau[:, None]
    )[:, :, None].expand(-1, -1, primitive_action_dim)


def flat_action_active_mask(
    tau: torch.Tensor,
    *,
    primitive_action_dim: int,
    horizon: int = spec.ACTION_HORIZON,
) -> torch.Tensor:
    return action_active_mask(
        tau, primitive_action_dim=primitive_action_dim, horizon=horizon
    ).reshape(len(tau), horizon * primitive_action_dim)


def bounded_actions_from_standardized_u(
    standardized_u: torch.Tensor,
    *,
    u_mean: torch.Tensor,
    u_std: torch.Tensor,
    planner_mean: torch.Tensor,
    planner_std: torch.Tensor,
    interior_scale: float,
    active_mask: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Decode standardized u to raw/planner actions with no action hard clip."""

    if standardized_u.ndim not in (3, 4):
        raise ValueError("E15 bounded decoder expects selected actions or a bank")
    action_dim = standardized_u.shape[-1]
    expected_stat = (action_dim,)
    if (
        any(value.shape != expected_stat for value in (u_mean, u_std, planner_mean, planner_std))
        or torch.any(u_std <= 0)
        or torch.any(planner_std <= 0)
        or not 0.0 < interior_scale < 1.0
        or active_mask.shape
        != (standardized_u.shape[0], standardized_u.shape[-2], action_dim)
    ):
        raise ValueError("E15 bounded decoder statistics/mask differ")
    expand = (1,) * (standardized_u.ndim - 1) + (action_dim,)
    u = standardized_u * u_std.reshape(expand) + u_mean.reshape(expand)
    raw = float(interior_scale) * torch.tanh(u)
    planner = raw.clone()
    planner.sub_(planner_mean.reshape(expand))
    planner.div_(planner_std.reshape(expand))
    expanded_mask = active_mask
    if standardized_u.ndim == 4:
        expanded_mask = active_mask[:, None]
    raw = raw * expanded_mask.to(raw.dtype)
    planner = planner * expanded_mask.to(planner.dtype)
    normalized_jacobian = (1.0 - torch.tanh(u).square()) * expanded_mask.to(u.dtype)
    if (
        not torch.isfinite(raw).all()
        or not torch.isfinite(planner).all()
        or not torch.isfinite(normalized_jacobian).all()
        or torch.any(torch.abs(raw[expanded_mask.expand_as(raw)]) >= 1.0)
    ):
        raise RuntimeError("E15 bounded action decoder produced an invalid action")
    return raw, planner, normalized_jacobian


def model_config(task: str, family: str) -> dict[str, Any]:
    if task not in spec.TASKS or family not in {
        "vad",
        "vad_shuffled",
        "vad_unconditional",
        "diagonal_gaussian",
        "direct_gmm",
    }:
        raise ValueError("invalid E15 model configuration key")
    task_spec = spec.TASK_SPEC[task]
    common = {
        "latent_dim": spec.LATENT_DIM,
        "state_dim": int(task_spec["state_dim"]),
        "width": spec.MODEL_WIDTH,
        "depth": spec.MODEL_DEPTH,
    }
    if family == "direct_gmm":
        return {
            **common,
            "primitive_action_dim": int(task_spec["primitive_action_dim"]),
            "horizon": spec.ACTION_HORIZON,
            "modes": spec.GMM_MODES,
        }
    return {
        **common,
        "output_dim": spec.ACTION_HORIZON
        * int(task_spec["primitive_action_dim"]),
        "time_embedding_dim": spec.TIME_EMBEDDING_DIM,
    }


def instantiate_model(task: str, family: str) -> nn.Module:
    config = model_config(task, family)
    if family == "direct_gmm":
        return DirectTrajectoryGMM(**config)
    if family == "diagonal_gaussian":
        return VariableDiagonalGaussian(**config)
    return VariableVelocityDiffusion(**config)


__all__ = [
    "CosineSchedule",
    "DirectTrajectoryGMM",
    "VariableDiagonalGaussian",
    "VariableVelocityDiffusion",
    "action_active_mask",
    "bounded_actions_from_standardized_u",
    "direct_gmm_loss",
    "flat_action_active_mask",
    "instantiate_model",
    "model_config",
    "sample_trajectory_gmm",
    "trajectory_gmm_posterior",
    "velocity_ddim_sample",
    "velocity_target",
]
