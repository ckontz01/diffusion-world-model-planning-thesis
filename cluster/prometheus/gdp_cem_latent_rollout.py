"""Exact cached-latent rollout helpers for P1 GDP-CEM selection."""

from __future__ import annotations

from typing import Any

import torch


@torch.inference_mode()
def rollout_from_single_latent(
    world_model: Any,
    *,
    current: torch.Tensor,
    macro_actions: torch.Tensor,
    predictor_history: int = 3,
) -> torch.Tensor:
    """Reproduce Le-WM's history-one planner rollout without re-encoding pixels.

    Args:
        current: `(B, D)` frozen encoder latents.
        macro_actions: `(B, N, H, A)` planner-coordinate macro actions.

    Returns:
        `(B, N, H + 1, D)` current-plus-predicted latent trajectory.
    """

    if current.ndim != 2 or macro_actions.ndim != 4:
        raise ValueError("GDP-CEM latent rollout input rank differs")
    batch, candidates, horizon, _ = macro_actions.shape
    if current.shape[0] != batch or horizon <= 0 or predictor_history <= 0:
        raise ValueError("GDP-CEM latent rollout input shape differs")
    latent_dim = current.shape[1]
    embedding = (
        current[:, None, None, :]
        .expand(batch, candidates, 1, latent_dim)
        .reshape(batch * candidates, 1, latent_dim)
        .clone()
    )
    action_sequence = macro_actions.reshape(
        batch * candidates, horizon, macro_actions.shape[-1]
    )
    active_actions = action_sequence[:, :1]
    for step in range(horizon):
        action_embedding = world_model.action_encoder(active_actions)
        prediction = world_model.predict(
            embedding[:, -predictor_history:],
            action_embedding[:, -predictor_history:],
        )[:, -1:]
        embedding = torch.cat((embedding, prediction), dim=1)
        if step + 1 < horizon:
            active_actions = torch.cat(
                (active_actions, action_sequence[:, step + 1 : step + 2]), dim=1
            )
    result = embedding.reshape(batch, candidates, horizon + 1, latent_dim)
    if not torch.isfinite(result).all():
        raise RuntimeError("GDP-CEM cached-latent rollout is non-finite")
    return result


def terminal_goal_cost(
    trajectory: torch.Tensor, goal: torch.Tensor
) -> torch.Tensor:
    if trajectory.ndim != 4 or goal.shape != (
        trajectory.shape[0],
        trajectory.shape[-1],
    ):
        raise ValueError("GDP-CEM terminal goal-cost shape differs")
    cost = (trajectory[:, :, -1] - goal[:, None]).square().sum(dim=-1)
    if not torch.isfinite(cost).all():
        raise RuntimeError("GDP-CEM terminal goal cost is non-finite")
    return cost


def selected_candidate_metrics(
    *,
    goal_cost: torch.Tensor,
    candidates: torch.Tensor,
    reference: torch.Tensor,
) -> dict[str, torch.Tensor]:
    if (
        goal_cost.shape != candidates.shape[:2]
        or reference.shape != (candidates.shape[0], *candidates.shape[2:])
    ):
        raise ValueError("GDP-CEM candidate metric shape differs")
    batch = torch.arange(len(candidates), device=candidates.device)
    selected_index = goal_cost.argmin(dim=1)
    selected = candidates[batch, selected_index]
    action_error = (candidates - reference[:, None]).square().mean(dim=(-1, -2))
    rounded = torch.round(candidates * 1.0e4).to(torch.int64)
    unique = []
    for row in rounded:
        unique.append(torch.unique(row.flatten(1), dim=0).shape[0])
    return {
        "minimum_goal_cost": goal_cost[batch, selected_index],
        "selected_action_mse": (selected - reference).square().mean(dim=(-1, -2)),
        "oracle_action_mse": action_error.min(dim=1).values,
        "candidate_variance": candidates.var(dim=1, unbiased=True).mean(dim=(-1, -2)),
        "unique_candidates": torch.as_tensor(unique, device=candidates.device),
        "selected_index": selected_index,
    }


__all__ = [
    "rollout_from_single_latent",
    "selected_candidate_metrics",
    "terminal_goal_cost",
]

