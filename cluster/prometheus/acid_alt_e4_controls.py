"""Capacity-matched non-diffusion controls for E4 development."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch
from torch import nn

from acid_alt_e4_models import ResidualMLPBlock


E4_P1_PROTOCOL_SHA256 = (
    "eec19adf1558a7366bbc13bd5077c5c26ac4dd73fd5c03b5be2651fe288dfc12"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DeterministicInverseRegressor(nn.Module):
    """Predict the standardized action block from two standardized latents."""

    def __init__(
        self,
        latent_dim: int,
        action_dim: int,
        *,
        width: int = 384,
        depth: int = 3,
    ) -> None:
        super().__init__()
        if min(latent_dim, action_dim, width, depth) <= 0:
            raise ValueError("model dimensions must be positive")
        self.latent_dim = int(latent_dim)
        self.action_dim = int(action_dim)
        self.width = int(width)
        self.depth = int(depth)
        self.input_projection = nn.Linear(2 * self.latent_dim, self.width)
        self.blocks = nn.ModuleList(
            [ResidualMLPBlock(self.width, expansion=2) for _ in range(self.depth)]
        )
        self.output_norm = nn.LayerNorm(self.width)
        self.output = nn.Linear(self.width, self.action_dim)

    def forward(self, current: torch.Tensor, successor: torch.Tensor) -> torch.Tensor:
        if current.shape != successor.shape or current.shape[-1] != self.latent_dim:
            raise ValueError("invalid latent endpoint shapes")
        leading = current.shape[:-1]
        inputs = torch.cat(
            (
                current.reshape(-1, self.latent_dim),
                successor.reshape(-1, self.latent_dim),
            ),
            dim=-1,
        )
        hidden = self.input_projection(inputs)
        for block in self.blocks:
            hidden = block(hidden)
        return self.output(self.output_norm(hidden)).reshape(*leading, self.action_dim)


class ConditionalGaussianInverse(nn.Module):
    """Diagonal-Gaussian inverse density with an explicit successor mask.

    This is the capacity-matched non-diffusion density-ratio control for E4.
    The current-only branch keeps the current latent and masks only the
    successor, matching the information boundary used by CIDER.
    """

    def __init__(
        self,
        latent_dim: int,
        action_dim: int,
        *,
        width: int = 384,
        depth: int = 3,
        minimum_log_scale: float = -5.0,
        maximum_log_scale: float = 2.0,
    ) -> None:
        super().__init__()
        if min(latent_dim, action_dim, width, depth) <= 0:
            raise ValueError("model dimensions must be positive")
        if minimum_log_scale >= maximum_log_scale:
            raise ValueError("invalid Gaussian log-scale bounds")
        self.latent_dim = int(latent_dim)
        self.action_dim = int(action_dim)
        self.width = int(width)
        self.depth = int(depth)
        self.minimum_log_scale = float(minimum_log_scale)
        self.maximum_log_scale = float(maximum_log_scale)
        self.input_projection = nn.Linear(2 * self.latent_dim + 1, self.width)
        self.blocks = nn.ModuleList(
            [ResidualMLPBlock(self.width, expansion=2) for _ in range(self.depth)]
        )
        self.output_norm = nn.LayerNorm(self.width)
        self.output = nn.Linear(self.width, 2 * self.action_dim)

    def forward(
        self,
        current: torch.Tensor,
        successor: torch.Tensor,
        successor_present: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if current.shape != successor.shape or current.shape[-1] != self.latent_dim:
            raise ValueError("invalid latent endpoint shapes")
        leading = current.shape[:-1]
        present = torch.as_tensor(
            successor_present, device=current.device, dtype=current.dtype
        ).expand(leading)
        inputs = torch.cat(
            (
                current.reshape(-1, self.latent_dim),
                successor.reshape(-1, self.latent_dim),
                present.reshape(-1, 1),
            ),
            dim=-1,
        )
        hidden = self.input_projection(inputs)
        for block in self.blocks:
            hidden = block(hidden)
        output = self.output(self.output_norm(hidden)).reshape(
            *leading, 2 * self.action_dim
        )
        mean, raw_log_scale = output.chunk(2, dim=-1)
        log_scale = raw_log_scale.clamp(
            min=self.minimum_log_scale, max=self.maximum_log_scale
        )
        return mean, log_scale


def diagonal_gaussian_nll(
    mean: torch.Tensor, log_scale: torch.Tensor, target: torch.Tensor
) -> torch.Tensor:
    """Gaussian NLL without the candidate-invariant log(2*pi) constant."""

    if mean.shape != log_scale.shape or mean.shape != target.shape:
        raise ValueError("Gaussian tensors have different shapes")
    standardized_error = (target - mean) * torch.exp(-log_scale)
    return (0.5 * standardized_error.square() + log_scale).mean(dim=-1)


@torch.inference_mode()
def deterministic_inverse_costs(
    model: DeterministicInverseRegressor,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    batch_size: int = 8192,
) -> torch.Tensor:
    """Return mean per-transition action reconstruction cost per candidate."""

    if trajectory.shape[:-2] != actions.shape[:-2]:
        raise ValueError("trajectory/action leading shapes differ")
    if trajectory.shape[-2] != actions.shape[-2] + 1:
        raise ValueError("trajectory state/action horizon differs")
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    current = trajectory[..., :-1, :]
    successor = trajectory[..., 1:, :]
    latent_mean = torch.as_tensor(
        latent_mean, device=trajectory.device, dtype=trajectory.dtype
    )
    latent_std = torch.as_tensor(
        latent_std, device=trajectory.device, dtype=trajectory.dtype
    )
    action_mean = torch.as_tensor(
        action_mean, device=actions.device, dtype=actions.dtype
    )
    action_std = torch.as_tensor(
        action_std, device=actions.device, dtype=actions.dtype
    )
    if torch.any(latent_std <= 1.0e-6) or torch.any(action_std <= 1.0e-6):
        raise RuntimeError("deterministic inverse standardizer is degenerate")
    current = (current - latent_mean) / latent_std
    successor = (successor - latent_mean) / latent_std
    standardized_action = (actions - action_mean) / action_std
    leading = current.shape[:-1]
    flat_count = current.numel() // current.shape[-1]
    current_flat = current.reshape(flat_count, current.shape[-1])
    successor_flat = successor.reshape(flat_count, successor.shape[-1])
    action_flat = standardized_action.reshape(flat_count, actions.shape[-1])
    chunks: list[torch.Tensor] = []
    for start in range(0, flat_count, batch_size):
        stop = min(start + batch_size, flat_count)
        prediction = model(current_flat[start:stop], successor_flat[start:stop])
        chunks.append(
            (prediction - action_flat[start:stop]).square().mean(dim=-1).float()
        )
    transition_cost = torch.cat(chunks).reshape(*leading)
    result = transition_cost.mean(dim=-1)
    if not torch.isfinite(result).all():
        raise RuntimeError("deterministic inverse cost is non-finite")
    return result


@torch.inference_mode()
def gaussian_inverse_costs(
    model: ConditionalGaussianInverse,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    calibration: dict[str, float],
    batch_size: int = 8192,
) -> dict[str, torch.Tensor]:
    """Return direct NLL, raw density ratio, and calibrated tail costs."""

    if trajectory.shape[:-2] != actions.shape[:-2]:
        raise ValueError("trajectory/action leading shapes differ")
    if trajectory.shape[-2] != actions.shape[-2] + 1:
        raise ValueError("trajectory state/action horizon differs")
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    current = trajectory[..., :-1, :]
    successor = trajectory[..., 1:, :]
    latent_mean = torch.as_tensor(
        latent_mean, device=trajectory.device, dtype=trajectory.dtype
    )
    latent_std = torch.as_tensor(
        latent_std, device=trajectory.device, dtype=trajectory.dtype
    )
    action_mean = torch.as_tensor(
        action_mean, device=actions.device, dtype=actions.dtype
    )
    action_std = torch.as_tensor(
        action_std, device=actions.device, dtype=actions.dtype
    )
    if torch.any(latent_std <= 1.0e-6) or torch.any(action_std <= 1.0e-6):
        raise RuntimeError("Gaussian inverse standardizer is degenerate")
    current = (current - latent_mean) / latent_std
    successor = (successor - latent_mean) / latent_std
    standardized_action = (actions - action_mean) / action_std
    leading = current.shape[:-1]
    flat_count = current.numel() // current.shape[-1]
    current_flat = current.reshape(flat_count, current.shape[-1])
    successor_flat = successor.reshape(flat_count, successor.shape[-1])
    action_flat = standardized_action.reshape(flat_count, actions.shape[-1])
    conditional_chunks: list[torch.Tensor] = []
    current_only_chunks: list[torch.Tensor] = []
    for start in range(0, flat_count, batch_size):
        stop = min(start + batch_size, flat_count)
        count = stop - start
        conditional_mean, conditional_log_scale = model(
            current_flat[start:stop],
            successor_flat[start:stop],
            torch.ones(count, device=trajectory.device),
        )
        current_mean, current_log_scale = model(
            current_flat[start:stop],
            torch.zeros_like(successor_flat[start:stop]),
            torch.zeros(count, device=trajectory.device),
        )
        conditional_chunks.append(
            diagonal_gaussian_nll(
                conditional_mean, conditional_log_scale, action_flat[start:stop]
            ).float()
        )
        current_only_chunks.append(
            diagonal_gaussian_nll(
                current_mean, current_log_scale, action_flat[start:stop]
            ).float()
        )
    conditional = torch.cat(conditional_chunks).reshape(*leading)
    current_only = torch.cat(current_only_chunks).reshape(*leading)
    ratio = conditional - current_only
    q95 = torch.as_tensor(
        calibration["ratio_q95"], device=ratio.device, dtype=ratio.dtype
    )
    q99 = torch.as_tensor(
        calibration["ratio_q99"], device=ratio.device, dtype=ratio.dtype
    )
    scale = torch.clamp(q99 - q95, min=0.10)
    violation = torch.relu((ratio - q95) / scale).clamp(max=10.0)
    count = min(2, violation.shape[-1])
    result = {
        "gaussian_nll": conditional.mean(dim=-1),
        "gaussian_ratio": ratio.mean(dim=-1),
        "gaussian_tail": torch.topk(violation, k=count, dim=-1).values.mean(dim=-1),
        "transition_gaussian_ratio": ratio,
        "transition_gaussian_violation": violation,
    }
    if not all(torch.isfinite(value).all() for value in result.values()):
        raise RuntimeError("Gaussian inverse scorer returned non-finite values")
    return result


def load_inverse_control(
    summary_path: Path,
    *,
    task: str,
    model_kind: str,
    expected_seed: int,
    source_manifest_sha256: str,
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], dict[str, float] | None, dict[str, Any]]:
    """Load a frozen inverse control with complete identity checks."""

    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required = {
        "status": "ok",
        "kind": "e4_capacity_matched_inverse_control_training",
        "task": task,
        "condition": "true_successor",
        "model": model_kind,
        "seed": expected_seed,
        "protocol_sha256": E4_P1_PROTOCOL_SHA256,
        "source_manifest_sha256": source_manifest_sha256,
        "protected_c1_i1_read": False,
        "confirmation_data_read": False,
    }
    for key, expected in required.items():
        if summary.get(key) != expected:
            raise RuntimeError(
                f"{model_kind} control {key}={summary.get(key)!r}, "
                f"expected {expected!r}"
            )
    if summary.get("best_selection_validation") != summary.get(
        "replayed_selection_validation"
    ):
        raise RuntimeError(f"{model_kind} control checkpoint replay mismatch")
    checkpoint = Path(summary["checkpoint"])
    if not checkpoint.is_file() or sha256_file(checkpoint) != summary.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError(f"{model_kind} control checkpoint hash mismatch")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    config = payload.get("model_config", {})
    if (
        payload.get("task") != task
        or payload.get("condition") != "true_successor"
        or payload.get("seed") != expected_seed
        or payload.get("source_manifest_sha256") != source_manifest_sha256
        or payload.get("protocol_sha256") != E4_P1_PROTOCOL_SHA256
    ):
        raise RuntimeError(f"{model_kind} checkpoint identity mismatch")
    if model_kind == "deterministic":
        expected_name = "e4_deterministic_inverse_control"
        model: nn.Module = DeterministicInverseRegressor(
            int(config["latent_dim"]),
            int(config["action_dim"]),
            width=int(config["width"]),
            depth=int(config["depth"]),
        )
        calibration = None
    elif model_kind == "gaussian":
        expected_name = "e4_gaussian_inverse_control"
        model = ConditionalGaussianInverse(
            int(config["latent_dim"]),
            int(config["action_dim"]),
            width=int(config["width"]),
            depth=int(config["depth"]),
            minimum_log_scale=float(config["minimum_log_scale"]),
            maximum_log_scale=float(config["maximum_log_scale"]),
        )
        calibration_path = Path(summary["calibration"])
        if not calibration_path.is_file() or sha256_file(
            calibration_path
        ) != summary.get("calibration_sha256"):
            raise RuntimeError("Gaussian control calibration hash mismatch")
        calibration_record = json.loads(calibration_path.read_text(encoding="utf-8"))
        if (
            calibration_record.get("status") != "ok"
            or calibration_record.get("role")
            != "P1_validation_Gaussian_inverse_ratio_calibration"
            or calibration_record.get("task") != task
            or calibration_record.get("seed") != expected_seed
            or calibration_record.get("protected_c1_i1_read") is not False
        ):
            raise RuntimeError("Gaussian control calibration identity mismatch")
        calibration = {
            key: float(calibration_record[key])
            for key in ("ratio_q50", "ratio_q95", "ratio_q99")
        }
    else:
        raise ValueError(model_kind)
    if payload.get("model_name") != expected_name or config.get("name") != expected_name:
        raise RuntimeError(f"{model_kind} checkpoint model name mismatch")
    model.load_state_dict(payload["state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != int(summary["parameter_count"]):
        raise RuntimeError(f"{model_kind} parameter count mismatch")
    return model, payload, calibration, {
        "arm": f"{model_kind}_inverse",
        "seed": expected_seed,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "parameter_count": parameter_count,
        "model_config": config,
    }


__all__ = [
    "ConditionalGaussianInverse",
    "DeterministicInverseRegressor",
    "deterministic_inverse_costs",
    "diagonal_gaussian_nll",
    "gaussian_inverse_costs",
    "load_inverse_control",
]
