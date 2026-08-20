"""Auditable score functions for E4 inverse-diffusion development stages."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import torch
from torch import nn

from acid_alt_e4_models import (
    ConditionalActionDenoiser,
    calibrated_transition_violation,
    cider_ratio,
    reconstruction_energy,
    upper_tail_horizon_mean,
)


E4_P1_PROTOCOL_SHA256 = (
    "eec19adf1558a7366bbc13bd5077c5c26ac4dd73fd5c03b5be2651fe288dfc12"
)
SCORING_SIGMAS = (0.5, 1.0, 2.0, 4.0)
NOISE_DRAWS = 4
CIDER_EPSILON = 1.0e-6
CALIBRATION_MINIMUM_SCALE = 0.10
CALIBRATION_MAXIMUM_VIOLATION = 10.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def derived_seed(label: str) -> int:
    value = int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "little")
    return value % (2**63 - 1)


def build_action_noise_bank(
    *, task: str, scorer_seed: int, horizon: int, action_dim: int
) -> torch.Tensor:
    """Build common random numbers keyed independently by level and draw."""

    levels: list[torch.Tensor] = []
    for sigma in SCORING_SIGMAS:
        draws: list[torch.Tensor] = []
        for draw in range(NOISE_DRAWS):
            seed = derived_seed(
                f"acid-alt-e4-action-noise|task={task}|seed={scorer_seed}|"
                f"sigma={sigma:.8f}|draw={draw}"
            )
            generator = torch.Generator(device="cpu").manual_seed(seed)
            draws.append(torch.randn(horizon, action_dim, generator=generator))
        levels.append(torch.stack(draws))
    return torch.stack(levels)


def build_acid_sample_noise_bank(
    *,
    task: str,
    scorer_seed: int,
    horizon: int,
    action_dim: int,
    draws: int = 16,
) -> torch.Tensor:
    if min(horizon, action_dim, draws) <= 0:
        raise ValueError("ACID sample-bank dimensions must be positive")
    values: list[torch.Tensor] = []
    for draw in range(draws):
        seed = derived_seed(
            f"acid-alt-e4-acid-multisample|task={task}|seed={scorer_seed}|draw={draw}"
        )
        generator = torch.Generator(device="cpu").manual_seed(seed)
        values.append(torch.randn(horizon, action_dim, generator=generator))
    return torch.stack(values)


def load_e4_model(
    summary_path: Path,
    *,
    task: str,
    expected_condition: str,
    device: torch.device,
) -> tuple[ConditionalActionDenoiser, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load and fully provenance-check one E4-P1 model and calibration."""

    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected = {
        "status": "ok",
        "kind": "e4_conditional_inverse_diffusion_p1_training",
        "task": task,
        "condition": expected_condition,
        "seed": 7101,
        "protocol_sha256": E4_P1_PROTOCOL_SHA256,
        "protected_c1_i1_read": False,
        "confirmation_data_read": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise RuntimeError(
                f"E4 model identity mismatch for {key}: "
                f"{summary.get(key)!r} != {value!r}"
            )
    checkpoint = Path(summary["checkpoint"])
    calibration_path = Path(summary["calibration"])
    if (
        not checkpoint.is_file()
        or sha256_file(checkpoint) != summary.get("checkpoint_sha256")
    ):
        raise RuntimeError("E4 checkpoint hash mismatch")
    if (
        not calibration_path.is_file()
        or sha256_file(calibration_path) != summary.get("calibration_sha256")
    ):
        raise RuntimeError("E4 calibration hash mismatch")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    config = payload.get("model_config", {})
    if (
        payload.get("model_name") != "e4_conditional_action_denoiser"
        or payload.get("task") != task
        or payload.get("condition") != expected_condition
        or payload.get("seed") != 7101
        or payload.get("protocol_sha256") != E4_P1_PROTOCOL_SHA256
        or config.get("name") != "e4_conditional_action_denoiser"
    ):
        raise RuntimeError("E4 checkpoint payload identity mismatch")
    model = ConditionalActionDenoiser(
        latent_dim=int(config["latent_dim"]),
        action_dim=int(config["action_dim"]),
        width=int(config["width"]),
        depth=int(config["depth"]),
        noise_embedding_dim=int(config["noise_embedding_dim"]),
    )
    model.load_state_dict(payload["state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    if sum(parameter.numel() for parameter in model.parameters()) != int(
        summary["parameter_count"]
    ):
        raise RuntimeError("E4 checkpoint parameter count mismatch")
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    if (
        calibration.get("status") != "ok"
        or calibration.get("role") != "P1_validation_CIDER_calibration"
        or calibration.get("task") != task
        or calibration.get("condition") != expected_condition
        or calibration.get("seed") != 7101
        or calibration.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E4 calibration identity mismatch")
    return model, payload, calibration, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "calibration": str(calibration_path),
        "calibration_sha256": summary["calibration_sha256"],
        "task": task,
        "condition": expected_condition,
        "seed": 7101,
        "parameter_count": summary["parameter_count"],
    }


def _validate_trajectory_actions(
    trajectory: torch.Tensor, actions: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    if trajectory.ndim < 3 or actions.ndim != trajectory.ndim:
        raise ValueError("trajectory/action rank differs")
    if trajectory.shape[:-2] != actions.shape[:-2]:
        raise ValueError("trajectory/action leading shapes differ")
    if trajectory.shape[-2] != actions.shape[-2] + 1:
        raise ValueError("trajectory must contain one more state than actions")
    return trajectory[..., :-1, :], trajectory[..., 1:, :]


@torch.inference_mode()
def inverse_diffusion_costs(
    model: ConditionalActionDenoiser,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    payload: dict[str, Any],
    calibration: dict[str, Any],
    noise_bank: torch.Tensor,
    batch_size: int = 8192,
) -> dict[str, torch.Tensor]:
    """Compute DIDE, raw CIDER, and calibrated tail CIDER candidate costs."""

    current, successor = _validate_trajectory_actions(trajectory, actions)
    if current.shape[:-1] != actions.shape[:-1]:
        raise ValueError("transition/action horizon shapes differ")
    horizon = actions.shape[-2]
    latent_dim = trajectory.shape[-1]
    action_dim = actions.shape[-1]
    expected_noise_shape = (
        len(SCORING_SIGMAS),
        NOISE_DRAWS,
        horizon,
        action_dim,
    )
    if tuple(noise_bank.shape) != expected_noise_shape:
        raise ValueError(
            f"noise bank {tuple(noise_bank.shape)} != {expected_noise_shape}"
        )
    if batch_size <= 0:
        raise ValueError("batch size must be positive")

    latent_mean = torch.as_tensor(
        payload["latent_mean"], device=trajectory.device, dtype=trajectory.dtype
    )
    latent_std = torch.as_tensor(
        payload["latent_std"], device=trajectory.device, dtype=trajectory.dtype
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
        raise RuntimeError("E4 scorer standardization is invalid")
    current = (current - latent_mean) / latent_std
    successor = (successor - latent_mean) / latent_std
    clean_action = (actions - action_mean) / action_std
    leading = current.shape[:-1]
    flat_count = math.prod(leading)
    current_flat = current.reshape(flat_count, latent_dim)
    successor_flat = successor.reshape(flat_count, latent_dim)
    action_flat = clean_action.reshape(flat_count, action_dim)

    conditional_levels: list[torch.Tensor] = []
    current_only_levels: list[torch.Tensor] = []
    cider_levels: list[torch.Tensor] = []
    violation_levels: list[torch.Tensor] = []
    for level, sigma_value in enumerate(SCORING_SIGMAS):
        conditional_sum = torch.zeros(flat_count, device=trajectory.device)
        current_only_sum = torch.zeros_like(conditional_sum)
        for draw in range(NOISE_DRAWS):
            step_noise = noise_bank[level, draw].to(
                device=trajectory.device, dtype=actions.dtype
            )
            expanded_noise = step_noise.expand(*leading[:-1], horizon, action_dim)
            noise_flat = expanded_noise.reshape(flat_count, action_dim)
            conditional_chunks: list[torch.Tensor] = []
            current_only_chunks: list[torch.Tensor] = []
            for start in range(0, flat_count, batch_size):
                stop = min(start + batch_size, flat_count)
                count = stop - start
                sigma = torch.full(
                    (count,),
                    sigma_value,
                    device=trajectory.device,
                    dtype=actions.dtype,
                )
                noisy_action = (
                    action_flat[start:stop] + sigma[:, None] * noise_flat[start:stop]
                )
                conditional_chunks.append(
                    reconstruction_energy(
                        model(
                            current_flat[start:stop],
                            successor_flat[start:stop],
                            noisy_action,
                            sigma,
                            torch.ones(count, device=trajectory.device),
                        ),
                        action_flat[start:stop],
                    ).float()
                )
                current_only_chunks.append(
                    reconstruction_energy(
                        model(
                            current_flat[start:stop],
                            torch.zeros_like(successor_flat[start:stop]),
                            noisy_action,
                            sigma,
                            torch.zeros(count, device=trajectory.device),
                        ),
                        action_flat[start:stop],
                    ).float()
                )
            conditional_sum += torch.cat(conditional_chunks)
            current_only_sum += torch.cat(current_only_chunks)
        conditional = (conditional_sum / NOISE_DRAWS).reshape(*leading)
        current_only = (current_only_sum / NOISE_DRAWS).reshape(*leading)
        cider = cider_ratio(
            conditional, current_only, epsilon=CIDER_EPSILON
        ).float()
        quantiles = calibration["quantiles"][str(sigma_value)]
        q95 = torch.as_tensor(
            quantiles["cider_q95"], device=trajectory.device, dtype=cider.dtype
        )
        q99 = torch.as_tensor(
            quantiles["cider_q99"], device=trajectory.device, dtype=cider.dtype
        )
        violation = calibrated_transition_violation(
            cider,
            q95,
            q99,
            minimum_scale=CALIBRATION_MINIMUM_SCALE,
            maximum_violation=CALIBRATION_MAXIMUM_VIOLATION,
        )
        conditional_levels.append(conditional)
        current_only_levels.append(current_only)
        cider_levels.append(cider)
        violation_levels.append(violation)

    conditional_stack = torch.stack(conditional_levels)
    current_only_stack = torch.stack(current_only_levels)
    cider_stack = torch.stack(cider_levels)
    violation_stack = torch.stack(violation_levels)
    transition_violation = violation_stack.mean(dim=0)
    result = {
        "dide": conditional_stack.mean(dim=(0, -1)),
        "current_only_energy": current_only_stack.mean(dim=(0, -1)),
        "cider": cider_stack.mean(dim=(0, -1)),
        "cider_tail": upper_tail_horizon_mean(transition_violation, count=2),
        "cider_mean_violation": transition_violation.mean(dim=-1),
        "transition_cider": cider_stack,
        "transition_violation": transition_violation,
    }
    if not all(torch.isfinite(value).all() for value in result.values()):
        raise RuntimeError("E4 inverse-diffusion scorer returned non-finite values")
    return result


@torch.inference_mode()
def acid_flow_training_energy(
    model: nn.Module,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    noise_bank: torch.Tensor,
    batch_size: int = 8192,
) -> torch.Tensor:
    """Evaluate ACID's flow-matching training residual on proposed actions."""

    current, successor = _validate_trajectory_actions(trajectory, actions)
    horizon = actions.shape[-2]
    action_dim = actions.shape[-1]
    if tuple(noise_bank.shape) != (
        len(SCORING_SIGMAS),
        NOISE_DRAWS,
        horizon,
        action_dim,
    ):
        raise ValueError("ACID flow-energy noise bank shape differs")
    mean = torch.as_tensor(action_mean, device=actions.device, dtype=actions.dtype)
    std = torch.as_tensor(action_std, device=actions.device, dtype=actions.dtype)
    if mean.shape != (action_dim,) or std.shape != (action_dim,) or torch.any(std <= 1.0e-6):
        raise RuntimeError("ACID action standardizer is invalid")
    standardized_action = (actions - mean) / std
    leading = current.shape[:-1]
    latent_dim = current.shape[-1]
    flat_count = math.prod(leading)
    current_flat = current.reshape(flat_count, latent_dim)
    successor_flat = successor.reshape(flat_count, latent_dim)
    action_flat = standardized_action.reshape(flat_count, action_dim)
    accumulated = torch.zeros(leading[:-1], device=actions.device, dtype=torch.float64)
    for level, sigma_value in enumerate(SCORING_SIGMAS):
        tau_value = sigma_value / (1.0 + sigma_value)
        for draw in range(NOISE_DRAWS):
            step_noise = noise_bank[level, draw].to(
                device=actions.device, dtype=actions.dtype
            )
            expanded_noise = step_noise.expand(*leading[:-1], horizon, action_dim)
            noise_flat = expanded_noise.reshape(flat_count, action_dim)
            chunks: list[torch.Tensor] = []
            for start in range(0, flat_count, batch_size):
                stop = min(start + batch_size, flat_count)
                count = stop - start
                tau = torch.full(
                    (count,), tau_value, device=actions.device, dtype=actions.dtype
                )
                action = action_flat[start:stop]
                noise = noise_flat[start:stop]
                noisy_action = tau[:, None] * noise + (1.0 - tau[:, None]) * action
                target_velocity = noise - action
                prediction = model(
                    current_flat[start:stop],
                    successor_flat[start:stop],
                    noisy_action,
                    tau,
                )
                chunks.append(
                    (prediction - target_velocity).square().mean(dim=-1).float()
                )
            transition = torch.cat(chunks).reshape(*leading)
            accumulated += transition.mean(dim=-1).double()
    result = (accumulated / (len(SCORING_SIGMAS) * NOISE_DRAWS)).float()
    if not torch.isfinite(result).all():
        raise RuntimeError("ACID flow-training energy is non-finite")
    return result


@torch.inference_mode()
def acid_multisample_costs(
    model: nn.Module,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    noise_bank: torch.Tensor,
    batch_size: int = 8192,
) -> dict[str, torch.Tensor]:
    """Strong ACID controls using mean and nearest of several inverse samples."""

    current, successor = _validate_trajectory_actions(trajectory, actions)
    horizon = actions.shape[-2]
    action_dim = actions.shape[-1]
    if noise_bank.ndim != 3 or tuple(noise_bank.shape[1:]) != (
        horizon,
        action_dim,
    ):
        raise ValueError("ACID multisample noise bank shape differs")
    if len(noise_bank) < 2 or batch_size <= 0:
        raise ValueError("ACID multisample control needs at least two draws")
    mean = torch.as_tensor(action_mean, device=actions.device, dtype=actions.dtype)
    std = torch.as_tensor(action_std, device=actions.device, dtype=actions.dtype)
    if mean.shape != (action_dim,) or std.shape != (action_dim,) or torch.any(std <= 1.0e-6):
        raise RuntimeError("ACID action standardizer is invalid")
    leading = current.shape[:-1]
    flat_count = math.prod(leading)
    current_flat = current.reshape(flat_count, current.shape[-1])
    successor_flat = successor.reshape(flat_count, successor.shape[-1])
    action_flat = actions.reshape(flat_count, action_dim)
    draw_costs: list[torch.Tensor] = []
    for draw in range(len(noise_bank)):
        step_noise = noise_bank[draw].to(device=actions.device, dtype=actions.dtype)
        expanded_noise = step_noise.expand(*leading[:-1], horizon, action_dim)
        noise_flat = expanded_noise.reshape(flat_count, action_dim)
        chunks: list[torch.Tensor] = []
        for start in range(0, flat_count, batch_size):
            stop = min(start + batch_size, flat_count)
            inferred_standardized = model.one_step_action(
                current_flat[start:stop],
                successor_flat[start:stop],
                noise_flat[start:stop],
            )
            inferred = inferred_standardized * std + mean
            chunks.append(
                (action_flat[start:stop] - inferred).square().sum(dim=-1).float()
            )
        draw_costs.append(torch.cat(chunks).reshape(*leading))
    stack = torch.stack(draw_costs)
    result = {
        "acid_sample_mean": stack.mean(dim=(0, -1)),
        "acid_sample_min": stack.min(dim=0).values.mean(dim=-1),
        "transition_acid_sample_mean": stack.mean(dim=0),
        "transition_acid_sample_min": stack.min(dim=0).values,
    }
    if not all(torch.isfinite(value).all() for value in result.values()):
        raise RuntimeError("ACID multisample scorer returned non-finite values")
    return result


__all__ = [
    "CALIBRATION_MAXIMUM_VIOLATION",
    "CALIBRATION_MINIMUM_SCALE",
    "CIDER_EPSILON",
    "E4_P1_PROTOCOL_SHA256",
    "NOISE_DRAWS",
    "SCORING_SIGMAS",
    "acid_flow_training_energy",
    "acid_multisample_costs",
    "build_action_noise_bank",
    "build_acid_sample_noise_bank",
    "derived_seed",
    "inverse_diffusion_costs",
    "load_e4_model",
    "sha256_file",
]
