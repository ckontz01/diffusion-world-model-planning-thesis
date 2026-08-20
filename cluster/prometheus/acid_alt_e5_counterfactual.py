"""Counterfactual successor scores for E5 diffusion development.

The E4 direct denoising energy is dominated by generic action support.  E5
holds the current latent, proposed action, noise, denoiser, and noise level
fixed, and changes only the proposed successor.  This same-model comparison
isolates information attributable to the successor without cross-model
calibration offsets.

All E5-D2 uses are explicitly post-outcome development.  No function in this
module opens or identifies protected C1/I1 material.
"""

from __future__ import annotations

import math
from typing import Any

import torch
from torch import nn

from acid_alt_e4_models import reconstruction_energy, upper_tail_horizon_mean
from acid_alt_e4_scoring import CIDER_EPSILON, NOISE_DRAWS, SCORING_SIGMAS


# Nested prefixes permit one predeclared Monte-Carlo sensitivity analysis.
# Every offset is a nonzero deterministic permutation of a 300-member CEM
# population; no outcome or score is used to choose a counterfactual.
COUNTERFACTUAL_OFFSETS = (
    11,
    29,
    47,
    67,
    83,
    101,
    127,
    149,
    167,
    191,
    211,
    229,
    247,
    263,
    277,
    293,
)
PRIMARY_COUNTERFACTUAL_COUNT = 8
SENSITIVITY_COUNTERFACTUAL_COUNTS = (4, 16)
HORIZON_TAIL_COUNT = 2


def _validate_inputs(
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    noise_bank: torch.Tensor,
    offsets: tuple[int, ...],
) -> tuple[torch.Tensor, torch.Tensor]:
    if trajectory.ndim != 4 or actions.ndim != 4:
        raise ValueError("E5 expects [pool,candidate,horizon,feature] tensors")
    if trajectory.shape[:2] != actions.shape[:2]:
        raise ValueError("trajectory and action population shapes differ")
    if trajectory.shape[2] != actions.shape[2] + 1:
        raise ValueError("trajectory must contain one more state than actions")
    if trajectory.device != actions.device or trajectory.dtype != actions.dtype:
        raise ValueError("trajectory and actions must share device and dtype")
    pool_count, candidate_count, horizon, action_dim = actions.shape
    if pool_count <= 0 or candidate_count <= 1 or horizon < HORIZON_TAIL_COUNT:
        raise ValueError("invalid E5 candidate population dimensions")
    if tuple(noise_bank.shape) != (
        len(SCORING_SIGMAS),
        NOISE_DRAWS,
        horizon,
        action_dim,
    ):
        raise ValueError("E5 noise bank shape differs")
    modulo_offsets = tuple(int(value) % candidate_count for value in offsets)
    if (
        not offsets
        or any(value == 0 for value in modulo_offsets)
        or len(set(modulo_offsets)) != len(modulo_offsets)
    ):
        raise ValueError("counterfactual offsets must be unique and nonzero modulo N")
    return trajectory[..., :-1, :], trajectory[..., 1:, :]


def _standardize(
    current: torch.Tensor,
    successor: torch.Tensor,
    actions: torch.Tensor,
    payload: dict[str, Any],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    latent_dim = current.shape[-1]
    action_dim = actions.shape[-1]
    latent_mean = torch.as_tensor(
        payload["latent_mean"], device=current.device, dtype=current.dtype
    )
    latent_std = torch.as_tensor(
        payload["latent_std"], device=current.device, dtype=current.dtype
    )
    action_mean = torch.as_tensor(
        payload["acid_action_mean"], device=actions.device, dtype=actions.dtype
    )
    action_std = torch.as_tensor(
        payload["acid_action_std"], device=actions.device, dtype=actions.dtype
    )
    if (
        latent_mean.shape != (latent_dim,)
        or latent_std.shape != (latent_dim,)
        or action_mean.shape != (action_dim,)
        or action_std.shape != (action_dim,)
        or torch.any(latent_std <= 1.0e-6)
        or torch.any(action_std <= 1.0e-6)
    ):
        raise RuntimeError("E5 standardization payload is invalid")
    return (
        (current - latent_mean) / latent_std,
        (successor - latent_mean) / latent_std,
        (actions - action_mean) / action_std,
    )


def _model_energy(
    model: nn.Module,
    *,
    current: torch.Tensor,
    successor: torch.Tensor,
    noisy_action: torch.Tensor,
    sigma_value: float,
    clean_action: torch.Tensor,
    batch_size: int,
) -> torch.Tensor:
    count = current.shape[0]
    chunks: list[torch.Tensor] = []
    for start in range(0, count, batch_size):
        stop = min(start + batch_size, count)
        size = stop - start
        sigma = torch.full(
            (size,),
            sigma_value,
            device=current.device,
            dtype=current.dtype,
        )
        chunks.append(
            reconstruction_energy(
                model(
                    current[start:stop],
                    successor[start:stop],
                    noisy_action[start:stop],
                    sigma,
                    torch.ones(size, device=current.device, dtype=current.dtype),
                ),
                clean_action[start:stop],
            ).float()
        )
    return torch.cat(chunks)


def _candidate_reductions(
    log_ratio: torch.Tensor,
    pairwise_error: torch.Tensor,
    *,
    counterfactual_count: int,
) -> dict[str, torch.Tensor]:
    # Input layout: [noise_level,counterfactual,pool,candidate,horizon].
    selected_log = log_ratio[:, :counterfactual_count]
    selected_pairwise = pairwise_error[:, :counterfactual_count]
    transition_log = selected_log.mean(dim=(0, 1))
    transition_pairwise = selected_pairwise.mean(dim=(0, 1))
    transition_softplus = torch.nn.functional.softplus(selected_log).mean(dim=(0, 1))
    return {
        "log_tail": upper_tail_horizon_mean(
            transition_log, count=HORIZON_TAIL_COUNT
        ),
        "log_mean": transition_log.mean(dim=-1),
        "pairwise_tail": upper_tail_horizon_mean(
            transition_pairwise, count=HORIZON_TAIL_COUNT
        ),
        "softplus_tail": upper_tail_horizon_mean(
            transition_softplus, count=HORIZON_TAIL_COUNT
        ),
        "transition_log": transition_log,
        "transition_pairwise": transition_pairwise,
    }


@torch.inference_mode()
def counterfactual_successor_costs(
    model: nn.Module,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    payload: dict[str, Any],
    noise_bank: torch.Tensor,
    offsets: tuple[int, ...] = COUNTERFACTUAL_OFFSETS,
    batch_size: int = 8192,
) -> dict[str, torch.Tensor]:
    """Score a candidate against deterministic in-pool successor counterfactuals.

    Lower scores indicate that the proposed action is denoised more accurately
    with its matching successor than with alternative successors.  Matching
    and counterfactual calls share the exact noisy action and network.
    """

    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    current, successor = _validate_inputs(trajectory, actions, noise_bank, offsets)
    current, successor, clean_action = _standardize(
        current, successor, actions, payload
    )
    pool_count, candidate_count, horizon, latent_dim = current.shape
    action_dim = clean_action.shape[-1]
    flat_count = pool_count * candidate_count * horizon
    current_flat = current.reshape(flat_count, latent_dim)
    successor_flat = successor.reshape(flat_count, latent_dim)
    action_flat = clean_action.reshape(flat_count, action_dim)
    wrong_successors = tuple(
        torch.roll(successor, shifts=-(offset % candidate_count), dims=1).reshape(
            flat_count, latent_dim
        )
        for offset in offsets
    )

    matching_levels: list[torch.Tensor] = []
    log_ratio_levels: list[torch.Tensor] = []
    pairwise_levels: list[torch.Tensor] = []
    for level, sigma_value in enumerate(SCORING_SIGMAS):
        matching_sum = torch.zeros(flat_count, device=trajectory.device)
        wrong_sum = torch.zeros(
            len(offsets), flat_count, device=trajectory.device
        )
        for draw in range(NOISE_DRAWS):
            step_noise = noise_bank[level, draw].to(
                device=trajectory.device, dtype=actions.dtype
            )
            expanded_noise = step_noise.expand(
                pool_count, candidate_count, horizon, action_dim
            ).reshape(flat_count, action_dim)
            noisy_action = action_flat + float(sigma_value) * expanded_noise
            matching_sum += _model_energy(
                model,
                current=current_flat,
                successor=successor_flat,
                noisy_action=noisy_action,
                sigma_value=float(sigma_value),
                clean_action=action_flat,
                batch_size=batch_size,
            )
            for negative, wrong_successor in enumerate(wrong_successors):
                wrong_sum[negative] += _model_energy(
                    model,
                    current=current_flat,
                    successor=wrong_successor,
                    noisy_action=noisy_action,
                    sigma_value=float(sigma_value),
                    clean_action=action_flat,
                    batch_size=batch_size,
                )
        matching = matching_sum / NOISE_DRAWS
        wrong = wrong_sum / NOISE_DRAWS
        matching_expanded = matching.unsqueeze(0)
        log_ratio = torch.log(matching_expanded + CIDER_EPSILON) - torch.log(
            wrong + CIDER_EPSILON
        )
        pairwise_error = (matching_expanded > wrong).float()
        pairwise_error += 0.5 * (matching_expanded == wrong).float()
        matching_levels.append(
            matching.reshape(pool_count, candidate_count, horizon)
        )
        log_ratio_levels.append(
            log_ratio.reshape(
                len(offsets), pool_count, candidate_count, horizon
            )
        )
        pairwise_levels.append(
            pairwise_error.reshape(
                len(offsets), pool_count, candidate_count, horizon
            )
        )

    matching_stack = torch.stack(matching_levels)
    log_ratio_stack = torch.stack(log_ratio_levels)
    pairwise_stack = torch.stack(pairwise_levels)
    requested_counts = (
        *SENSITIVITY_COUNTERFACTUAL_COUNTS[:1],
        PRIMARY_COUNTERFACTUAL_COUNT,
        *SENSITIVITY_COUNTERFACTUAL_COUNTS[1:],
    )
    if max(requested_counts) > len(offsets):
        raise ValueError("not enough counterfactual offsets for frozen reductions")
    result: dict[str, torch.Tensor] = {
        "dide_replay": matching_stack.mean(dim=(0, -1)),
        "matching_transition_energy": matching_stack.mean(dim=0),
    }
    for count in requested_counts:
        reductions = _candidate_reductions(
            log_ratio_stack, pairwise_stack, counterfactual_count=count
        )
        result[f"csda_log_tail_k{count}"] = reductions["log_tail"]
        if count == PRIMARY_COUNTERFACTUAL_COUNT:
            result["csda_log_mean_k8"] = reductions["log_mean"]
            result["csda_pairwise_tail_k8"] = reductions["pairwise_tail"]
            result["csda_softplus_tail_k8"] = reductions["softplus_tail"]
            result["transition_csda_log_k8"] = reductions["transition_log"]
            result["transition_csda_pairwise_k8"] = reductions[
                "transition_pairwise"
            ]
    if not all(torch.isfinite(value).all() for value in result.values()):
        raise RuntimeError("E5 counterfactual scorer returned non-finite values")
    return result


def network_pairs_per_sequence(counterfactual_count: int) -> int:
    """Count model calls represented by one candidate sequence score."""

    if counterfactual_count <= 0:
        raise ValueError("counterfactual count must be positive")
    return (
        5
        * len(SCORING_SIGMAS)
        * NOISE_DRAWS
        * (1 + counterfactual_count)
    )


__all__ = [
    "COUNTERFACTUAL_OFFSETS",
    "HORIZON_TAIL_COUNT",
    "PRIMARY_COUNTERFACTUAL_COUNT",
    "SENSITIVITY_COUNTERFACTUAL_COUNTS",
    "counterfactual_successor_costs",
    "network_pairs_per_sequence",
]
