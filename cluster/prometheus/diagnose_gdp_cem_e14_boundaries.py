#!/usr/bin/env python3
"""Post-E14 diagnosis of frozen VAD action-boundary behavior.

This script is deliberately descriptive.  It regenerates the already-frozen
E14 VAD proposal banks on P1-validation, verifies the stored E14 boundary
fractions, and measures raw, clipped, selected, and expert-cache behavior.
It never reads a confirmation partition and cannot select or authorize E15.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

import gdp_cem_e14_specs as spec
from acid_alternative.io_utils import resolve_policy_checkpoint
from evaluate_gdp_cem_e14_offline import (
    CANDIDATE_COUNT,
    TRAINING_SOURCE_MANIFEST_SHA256,
    generate_candidates,
    load_model,
)
from gdp_cem_e14_data import E14ArrayStore, sha256_file
from gdp_cem_e14_models import CosineSchedule
from gdp_cem_latent_rollout import rollout_from_single_latent


DEFAULT_BATCH_SIZE = 8
EXPECTED_GPU_NAME = "NVIDIA RTX 6000 Ada Generation"
NEAR_MARGINS = (1.0e-6, 1.0e-4, 1.0e-3, 1.0e-2, 5.0e-2)
RAW_ENVIRONMENT_TOLERANCE = float(4.0 * np.finfo(np.float32).eps)
ENVIRONMENT_LEGAL_LOW = {
    "pusht": np.full(2, -1.0, dtype=np.float32),
    "cube": np.full(5, -1.0, dtype=np.float32),
}
ENVIRONMENT_LEGAL_HIGH = {
    "pusht": np.full(2, 1.0, dtype=np.float32),
    "cube": np.full(5, 1.0, dtype=np.float32),
}


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected path is forbidden: {path}")


def atomic_json(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def array_sha256(value: np.ndarray | torch.Tensor) -> str:
    if torch.is_tensor(value):
        value = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def per_row_fraction(value: torch.Tensor) -> torch.Tensor:
    if value.ndim not in (3, 4):
        raise ValueError("boundary mask must be selected actions or a proposal bank")
    return value.float().mean(dim=tuple(range(1, value.ndim)))


def outside(value: torch.Tensor, low: torch.Tensor, high: torch.Tensor) -> torch.Tensor:
    return torch.logical_or(value < low, value > high)


def exact_boundary(
    value: torch.Tensor, low: torch.Tensor, high: torch.Tensor
) -> torch.Tensor:
    return torch.logical_or(value == low, value == high)


def near_boundary(
    value: torch.Tensor,
    low: torch.Tensor,
    high: torch.Tensor,
    margin: float,
) -> torch.Tensor:
    if not 0.0 <= margin < 0.5:
        raise ValueError("invalid relative boundary margin")
    span = high - low
    distance = torch.minimum(value - low, high - value) / span
    return torch.logical_and(
        torch.logical_and(value >= low, value <= high), distance <= margin
    )


def aggregate_rows(
    *, delta: np.ndarray, tau: np.ndarray, metrics: dict[str, np.ndarray]
) -> dict[str, Any]:
    cells: dict[str, dict[str, float]] = {}
    for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
        active = (delta == delta_value) & (tau == tau_value)
        if not active.any():
            raise RuntimeError("empty E14 diagnostic condition cell")
        cells[f"delta={delta_value},tau={tau_value}"] = {
            key: float(np.mean(value[active], dtype=np.float64))
            for key, value in metrics.items()
        }
    per_tau: dict[str, dict[str, float]] = {}
    for tau_value in spec.TAU_VALUES:
        matching = [
            cell
            for key, cell in cells.items()
            if key.endswith(f"tau={tau_value}")
        ]
        per_tau[str(tau_value)] = {
            key: float(np.mean([cell[key] for cell in matching])) for key in metrics
        }
    per_delta: dict[str, dict[str, float]] = {}
    for delta_value in spec.DELTA_VALUES:
        matching = [
            cell
            for key, cell in cells.items()
            if key.startswith(f"delta={delta_value},")
        ]
        per_delta[str(delta_value)] = {
            key: float(np.mean([cell[key] for cell in matching])) for key in metrics
        }
    return {
        "equal_cell_mean": {
            key: float(np.mean([cell[key] for cell in cells.values()]))
            for key in metrics
        },
        "per_tau": per_tau,
        "per_delta": per_delta,
        "cells": cells,
    }


class AxisAccumulator:
    """Weighted action-element rates by option time and action dimension."""

    def __init__(self, horizon: int, action_dim: int) -> None:
        self.numerator = np.zeros((horizon, action_dim), dtype=np.float64)
        self.denominator = np.zeros((horizon, action_dim), dtype=np.float64)

    def add(self, value: torch.Tensor) -> None:
        if value.ndim == 4:
            numerator = value.double().sum(dim=(0, 1)).cpu().numpy()
            denominator = np.full_like(numerator, value.shape[0] * value.shape[1])
        elif value.ndim == 3:
            numerator = value.double().sum(dim=0).cpu().numpy()
            denominator = np.full_like(numerator, value.shape[0])
        else:
            raise ValueError("axis accumulator input shape differs")
        self.numerator[: value.shape[-2]] += numerator
        self.denominator[: value.shape[-2]] += denominator

    def result(self) -> dict[str, Any]:
        if np.any((self.denominator == 0) & (self.numerator != 0)):
            raise RuntimeError("invalid boundary accumulator")
        matrix = np.divide(
            self.numerator,
            self.denominator,
            out=np.full_like(self.numerator, np.nan),
            where=self.denominator > 0,
        )
        per_time = np.divide(
            self.numerator.sum(axis=1),
            self.denominator.sum(axis=1),
            out=np.full(self.numerator.shape[0], np.nan, dtype=np.float64),
            where=self.denominator.sum(axis=1) > 0,
        )
        per_dimension = np.divide(
            self.numerator.sum(axis=0),
            self.denominator.sum(axis=0),
            out=np.full(self.numerator.shape[1], np.nan, dtype=np.float64),
            where=self.denominator.sum(axis=0) > 0,
        )
        return {
            "per_time_and_dimension": matrix.tolist(),
            "per_time": per_time.tolist(),
            "per_dimension": per_dimension.tolist(),
            "active_element_count": int(self.denominator.sum()),
        }


def expert_cache_summary(
    store: E14ArrayStore,
    rows: np.ndarray,
    *,
    legal_low: np.ndarray,
    legal_high: np.ndarray,
    tolerant_legal_low: np.ndarray,
    tolerant_legal_high: np.ndarray,
) -> dict[str, Any]:
    action = store.action[rows] * store.action_std[None, None] + store.action_mean[
        None, None
    ]
    mask = store.action_mask[rows]
    robust_low = store.action_robust_low
    robust_high = store.action_robust_high
    result: dict[str, Any] = {
        "row_count": int(len(rows)),
        "active_action_count": int(mask.sum()),
        "dimensions": [],
    }
    for dimension in range(store.primitive_action_dim):
        values = action[:, :, dimension][mask]
        if not np.isfinite(values).all():
            raise RuntimeError("expert cache contains non-finite actions")
        result["dimensions"].append(
            {
                "dimension": dimension,
                "minimum": float(values.min()),
                "q0001": float(np.quantile(values, 0.0001)),
                "q001": float(np.quantile(values, 0.001)),
                "q01": float(np.quantile(values, 0.01)),
                "q05": float(np.quantile(values, 0.05)),
                "median": float(np.quantile(values, 0.5)),
                "q95": float(np.quantile(values, 0.95)),
                "q99": float(np.quantile(values, 0.99)),
                "q999": float(np.quantile(values, 0.999)),
                "q9999": float(np.quantile(values, 0.9999)),
                "maximum": float(values.max()),
                "robust_low": float(robust_low[dimension]),
                "robust_high": float(robust_high[dimension]),
                "legal_low": float(legal_low[dimension]),
                "legal_high": float(legal_high[dimension]),
                "tolerant_legal_low": float(tolerant_legal_low[dimension]),
                "tolerant_legal_high": float(tolerant_legal_high[dimension]),
                "outside_robust_fraction": float(
                    np.mean(
                        (values < robust_low[dimension])
                        | (values > robust_high[dimension])
                    )
                ),
                "outside_legal_strict_fraction": float(
                    np.mean(
                        (values < legal_low[dimension])
                        | (values > legal_high[dimension])
                    )
                ),
                "outside_legal_tolerant_fraction": float(
                    np.mean(
                        (values < tolerant_legal_low[dimension])
                        | (values > tolerant_legal_high[dimension])
                    )
                ),
            }
        )
    return result


def transform_environment_bounds(
    environment_low: np.ndarray,
    environment_high: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Map raw environment bounds into standardized planner coordinates."""

    expected = environment_low.shape
    if (
        environment_high.shape != expected
        or mean.shape != expected
        or std.shape != expected
        or np.any(std < 1.0e-8)
        or not np.isfinite(environment_low).all()
        or not np.isfinite(environment_high).all()
        or not np.isfinite(mean).all()
        or not np.isfinite(std).all()
    ):
        raise RuntimeError("released planner action scaler differs")
    # sklearn's released StandardScaler preserves the float32 input dtype and
    # performs subtraction and division as two in-place float32 operations.
    # A single float64 formula followed by one cast can differ by one ULP at
    # exactly saturated Cube actions, so reproduce the released operation
    # sequence rather than using the algebraically equivalent shortcut.
    transformed = np.stack((environment_low, environment_high), axis=0).astype(
        np.float32, copy=True
    )
    transformed -= mean.astype(np.float32)
    transformed /= std.astype(np.float32)
    low, high = transformed
    if np.any(high <= low):
        raise RuntimeError("planner-coordinate legal bounds are invalid")
    return low, high


def planner_coordinate_legal_bounds(
    transition_h5: Path,
    *,
    task: str,
    environment_low: np.ndarray,
    environment_high: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Transform true environment bounds through the released action scaler."""

    if sha256_file(transition_h5) != spec.TASK_SPEC[task]["transition_sha256"]:
        raise RuntimeError("E14 transition cache hash differs")
    with h5py.File(transition_h5, "r") as handle:
        mean = np.asarray(
            handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
        )
        std = np.asarray(
            handle["stats/planner_primitive_action_std"][:], dtype=np.float64
        )
    low, high = transform_environment_bounds(
        environment_low, environment_high, mean, std
    )
    return low, high, mean, std


def validate_original_e14(
    summary_path: Path,
    *,
    task: str,
    seed: int,
    validation_rows: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics_path = Path(summary.get("metrics_h5", ""))
    reject_protected_path(metrics_path)
    if (
        summary.get("status") != "ok"
        or summary.get("kind")
        != "gdp_cem_e14_full_p1_validation_endpoint_evaluation"
        or summary.get("analysis_role") != "P1_validation_only_Gate_B_development"
        or summary.get("task") != task
        or summary.get("condition") != "vad_true"
        or summary.get("endpoint") != "vad"
        or summary.get("family") != "true"
        or int(summary.get("seed", -1)) != seed
        or int(summary.get("row_count", -1)) != len(validation_rows)
        or int(summary.get("candidate_count", -1)) != CANDIDATE_COUNT
        or int(summary.get("batch_size", -1)) != DEFAULT_BATCH_SIZE
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("training_source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
        or not metrics_path.is_file()
        or sha256_file(metrics_path) != summary.get("metrics_h5_sha256")
    ):
        raise RuntimeError("original E14 VAD evaluation identity differs")
    with h5py.File(metrics_path, "r") as handle:
        original_rows = np.asarray(handle["cache_row"][:], dtype=np.int64)
        original_boundary = np.asarray(
            handle["metrics/boundary_fraction"][:], dtype=np.float64
        )
    if not np.array_equal(original_rows, validation_rows):
        raise RuntimeError("original E14 validation row order differs")
    return original_boundary, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "metrics_h5": str(metrics_path),
        "metrics_h5_sha256": summary["metrics_h5_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--seed", type=int, choices=spec.MODEL_SEEDS, required=True)
    parser.add_argument("--training-summary", type=Path, required=True)
    parser.add_argument("--original-summary", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--legal-bound-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    args = parser.parse_args()

    required = (
        args.training_summary,
        args.original_summary,
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.transition_h5,
        args.world_model_checkpoint,
        args.protocol,
        args.source_manifest,
        args.legal_bound_source,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E14 protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E14 boundary-diagnostic output")
    if not torch.cuda.is_available():
        raise RuntimeError("E14 boundary diagnosis requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != EXPECTED_GPU_NAME:
        raise RuntimeError("E14 boundary diagnosis GPU model differs")

    torch.manual_seed(1416)
    torch.cuda.manual_seed_all(1416)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    store = E14ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    environment_legal_low = ENVIRONMENT_LEGAL_LOW[args.task]
    environment_legal_high = ENVIRONMENT_LEGAL_HIGH[args.task]
    if len(environment_legal_low) != store.primitive_action_dim:
        raise RuntimeError("legal action-bound dimension differs")
    legal_low_np, legal_high_np, planner_action_mean, planner_action_std = (
        planner_coordinate_legal_bounds(
            args.transition_h5,
            task=args.task,
            environment_low=environment_legal_low,
            environment_high=environment_legal_high,
        )
    )
    tolerant_legal_low_np, tolerant_legal_high_np = transform_environment_bounds(
        environment_legal_low - RAW_ENVIRONMENT_TOLERANCE,
        environment_legal_high + RAW_ENVIRONMENT_TOLERANCE,
        planner_action_mean,
        planner_action_std,
    )
    model, _, model_record = load_model(
        args.training_summary,
        task=args.task,
        condition="vad_true",
        seed=args.seed,
        store=store,
        device=device,
    )
    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    original_boundary, original_record = validate_original_e14(
        args.original_summary,
        task=args.task,
        seed=args.seed,
        validation_rows=store.validation_rows,
    )
    evaluation_rows = store.validation_rows
    if args.mode == "smoke":
        evaluation_rows = np.asarray(
            [
                store.validation_rows[
                    (store.delta[store.validation_rows] == delta_value)
                    & (store.tau[store.validation_rows] == tau_value)
                ][0]
                for delta_value, tau_value in spec.DELTA_TAU_PAIRS
            ],
            dtype=np.int64,
        )
    row_to_position = np.full(len(store.role), -1, dtype=np.int64)
    row_to_position[evaluation_rows] = np.arange(len(evaluation_rows))
    metric_names = [
        "bank_raw_robust_oob_fraction",
        "bank_raw_legal_oob_fraction",
        "bank_raw_legal_strict_oob_fraction",
        "bank_exact_robust_after_clip_fraction",
        "selected_raw_robust_oob_fraction",
        "selected_raw_legal_oob_fraction",
        "selected_raw_legal_strict_oob_fraction",
        "selected_exact_robust_after_clip_fraction",
        "raw_clip_displacement_fraction_of_robust_span",
        "selected_raw_clip_displacement_fraction_of_robust_span",
        "raw_candidate_variance",
        "clipped_candidate_variance",
        "raw_unique_candidates",
        "clipped_unique_candidates",
    ]
    for margin in NEAR_MARGINS:
        label = f"{margin:.0e}"
        metric_names.extend(
            (
                f"bank_near_robust_{label}_fraction",
                f"bank_near_legal_{label}_fraction",
                f"selected_near_robust_{label}_fraction",
                f"selected_near_legal_{label}_fraction",
            )
        )
    values = {
        name: np.full(len(evaluation_rows), np.nan, dtype=np.float64)
        for name in metric_names
    }
    axis = {
        name: AxisAccumulator(spec.ACTION_HORIZON, store.primitive_action_dim)
        for name in (
            "bank_raw_robust_oob",
            "bank_raw_legal_oob",
            "bank_raw_legal_strict_oob",
            "bank_exact_robust_after_clip",
            "selected_raw_robust_oob",
            "selected_raw_legal_oob",
            "selected_raw_legal_strict_oob",
            "selected_exact_robust_after_clip",
        )
    }

    schedule = CosineSchedule.build(spec.DIFFUSION_STEPS)
    candidate_generator = torch.Generator(device=device).manual_seed(
        spec.derived_seed(
            f"offline-candidates|task={args.task}|endpoint=vad|seed={args.seed}"
        )
    )
    normalized_low = torch.from_numpy(
        (store.action_robust_low - store.action_mean) / store.action_std
    ).to(device)
    normalized_high = torch.from_numpy(
        (store.action_robust_high - store.action_mean) / store.action_std
    ).to(device)
    robust_low = torch.from_numpy(store.action_robust_low).to(device)
    robust_high = torch.from_numpy(store.action_robust_high).to(device)
    legal_low = torch.from_numpy(legal_low_np).to(device)
    legal_high = torch.from_numpy(legal_high_np).to(device)
    tolerant_legal_low = torch.from_numpy(tolerant_legal_low_np).to(device)
    tolerant_legal_high = torch.from_numpy(tolerant_legal_high_np).to(device)
    action_mean = torch.from_numpy(store.action_mean).to(device)
    action_std = torch.from_numpy(store.action_std).to(device)
    latent_mean = torch.from_numpy(store.latent_mean).to(device)
    latent_std = torch.from_numpy(store.latent_std).to(device)
    robust_span = robust_high - robust_low
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)

    for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
        cell_rows = evaluation_rows[
            (store.delta[evaluation_rows] == delta_value)
            & (store.tau[evaluation_rows] == tau_value)
        ]
        for start in range(0, len(cell_rows), DEFAULT_BATCH_SIZE):
            rows = cell_rows[start : start + DEFAULT_BATCH_SIZE]
            positions = row_to_position[rows]
            batch = store.batch(rows)
            _, active_mask = batch.endpoint_target("vad")
            current = batch.current.to(device)
            goal = batch.goal.to(device)
            state = batch.state.to(device)
            delta = batch.delta.to(device)
            tau = batch.tau.to(device)
            active_mask = active_mask.to(device)
            candidates = generate_candidates(
                model,
                endpoint="vad",
                family="true",
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                active_mask=active_mask,
                schedule=schedule,
                generator=candidate_generator,
            )
            raw_normalized = candidates.reshape(
                len(rows),
                CANDIDATE_COUNT,
                spec.ACTION_HORIZON,
                store.primitive_action_dim,
            )[:, :, :tau_value]
            clipped_normalized = torch.maximum(
                torch.minimum(raw_normalized, normalized_high), normalized_low
            )
            raw_action = raw_normalized * action_std + action_mean
            clipped_action = clipped_normalized * action_std + action_mean
            macro = clipped_action.reshape(
                len(rows),
                CANDIDATE_COUNT,
                tau_value // spec.ACTION_BLOCK,
                spec.ACTION_BLOCK * store.primitive_action_dim,
            )
            current_raw = current * latent_std + latent_mean
            goal_raw = goal * latent_std + latent_mean
            terminal = rollout_from_single_latent(
                world_model, current=current_raw, macro_actions=macro
            )[:, :, -1]
            selection_cost = (terminal - goal_raw[:, None]).square().sum(dim=-1)
            selected_index = selection_cost.argmin(dim=1)
            batch_index = torch.arange(len(rows), device=device)
            selected_raw = raw_action[batch_index, selected_index]
            selected_clipped = clipped_action[batch_index, selected_index]

            bank_raw_robust = outside(raw_action, robust_low, robust_high)
            bank_raw_legal = outside(
                raw_action, tolerant_legal_low, tolerant_legal_high
            )
            bank_raw_legal_strict = outside(raw_action, legal_low, legal_high)
            bank_exact_robust = exact_boundary(
                clipped_action, robust_low, robust_high
            )
            selected_raw_robust = outside(selected_raw, robust_low, robust_high)
            selected_raw_legal = outside(
                selected_raw, tolerant_legal_low, tolerant_legal_high
            )
            selected_raw_legal_strict = outside(
                selected_raw, legal_low, legal_high
            )
            selected_exact_robust = exact_boundary(
                selected_clipped, robust_low, robust_high
            )
            masks = {
                "bank_raw_robust_oob": bank_raw_robust,
                "bank_raw_legal_oob": bank_raw_legal,
                "bank_raw_legal_strict_oob": bank_raw_legal_strict,
                "bank_exact_robust_after_clip": bank_exact_robust,
                "selected_raw_robust_oob": selected_raw_robust,
                "selected_raw_legal_oob": selected_raw_legal,
                "selected_raw_legal_strict_oob": selected_raw_legal_strict,
                "selected_exact_robust_after_clip": selected_exact_robust,
            }
            for name, mask in masks.items():
                axis[name].add(mask)
            values["bank_raw_robust_oob_fraction"][positions] = (
                per_row_fraction(bank_raw_robust).double().cpu().numpy()
            )
            values["bank_raw_legal_oob_fraction"][positions] = (
                per_row_fraction(bank_raw_legal).double().cpu().numpy()
            )
            values["bank_raw_legal_strict_oob_fraction"][positions] = (
                per_row_fraction(bank_raw_legal_strict).double().cpu().numpy()
            )
            values["bank_exact_robust_after_clip_fraction"][positions] = (
                per_row_fraction(bank_exact_robust).double().cpu().numpy()
            )
            values["selected_raw_robust_oob_fraction"][positions] = (
                per_row_fraction(selected_raw_robust).double().cpu().numpy()
            )
            values["selected_raw_legal_oob_fraction"][positions] = (
                per_row_fraction(selected_raw_legal).double().cpu().numpy()
            )
            values["selected_raw_legal_strict_oob_fraction"][positions] = (
                per_row_fraction(selected_raw_legal_strict).double().cpu().numpy()
            )
            values["selected_exact_robust_after_clip_fraction"][positions] = (
                per_row_fraction(selected_exact_robust).double().cpu().numpy()
            )
            displacement = (raw_action - clipped_action).abs() / robust_span
            selected_displacement = (
                selected_raw - selected_clipped
            ).abs() / robust_span
            values["raw_clip_displacement_fraction_of_robust_span"][positions] = (
                displacement.mean(dim=(1, 2, 3)).double().cpu().numpy()
            )
            values[
                "selected_raw_clip_displacement_fraction_of_robust_span"
            ][positions] = selected_displacement.mean(dim=(1, 2)).double().cpu().numpy()
            values["raw_candidate_variance"][positions] = (
                raw_action.var(dim=1, unbiased=True)
                .mean(dim=(1, 2))
                .double()
                .cpu()
                .numpy()
            )
            values["clipped_candidate_variance"][positions] = (
                clipped_action.var(dim=1, unbiased=True)
                .mean(dim=(1, 2))
                .double()
                .cpu()
                .numpy()
            )
            for margin in NEAR_MARGINS:
                label = f"{margin:.0e}"
                values[f"bank_near_robust_{label}_fraction"][positions] = (
                    per_row_fraction(
                        near_boundary(clipped_action, robust_low, robust_high, margin)
                    )
                    .double()
                    .cpu()
                    .numpy()
                )
                values[f"bank_near_legal_{label}_fraction"][positions] = (
                    per_row_fraction(
                        near_boundary(clipped_action, legal_low, legal_high, margin)
                    )
                    .double()
                    .cpu()
                    .numpy()
                )
                values[f"selected_near_robust_{label}_fraction"][positions] = (
                    per_row_fraction(
                        near_boundary(
                            selected_clipped, robust_low, robust_high, margin
                        )
                    )
                    .double()
                    .cpu()
                    .numpy()
                )
                values[f"selected_near_legal_{label}_fraction"][positions] = (
                    per_row_fraction(
                        near_boundary(selected_clipped, legal_low, legal_high, margin)
                    )
                    .double()
                    .cpu()
                    .numpy()
                )
            raw_rounded = torch.round(raw_normalized * 1.0e4).to(torch.int64).cpu().numpy()
            clipped_rounded = (
                torch.round(clipped_normalized * 1.0e4).to(torch.int64).cpu().numpy()
            )
            values["raw_unique_candidates"][positions] = np.asarray(
                [
                    np.unique(row.reshape(CANDIDATE_COUNT, -1), axis=0).shape[0]
                    for row in raw_rounded
                ],
                dtype=np.float64,
            )
            values["clipped_unique_candidates"][positions] = np.asarray(
                [
                    np.unique(row.reshape(CANDIDATE_COUNT, -1), axis=0).shape[0]
                    for row in clipped_rounded
                ],
                dtype=np.float64,
            )

    if any(not np.isfinite(value).all() for value in values.values()):
        raise RuntimeError("E14 boundary diagnostic contains missing metrics")
    original_positions = np.searchsorted(store.validation_rows, evaluation_rows)
    original_selected = original_boundary[original_positions]
    reproduced = values["bank_exact_robust_after_clip_fraction"]
    reproduction_error = np.abs(reproduced - original_selected)
    reproduction_mask = (
        np.ones(len(reproduced), dtype=np.bool_)
        if args.mode == "full"
        else np.arange(len(reproduced)) == 0
    )
    # The original full evaluator consumed every row in a cell before advancing
    # its single RNG stream.  A one-row-per-cell smoke run therefore shares the
    # exact bank only for the first condition.  Full mode must reproduce all
    # 40,000 rows.
    if not np.allclose(
        reproduced[reproduction_mask],
        original_selected[reproduction_mask],
        rtol=0.0,
        atol=1.0e-7,
    ):
        raise RuntimeError("E14 boundary statistic was not exactly reproduced")

    aggregates = aggregate_rows(
        delta=store.delta[evaluation_rows],
        tau=store.tau[evaluation_rows],
        metrics=values,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "row-metrics.h5"
    partial = detail_path.with_name(f".{detail_path.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as handle:
            handle.create_dataset("cache_row", data=evaluation_rows, compression="lzf")
            handle.create_dataset(
                "delta", data=store.delta[evaluation_rows], compression="lzf"
            )
            handle.create_dataset(
                "tau", data=store.tau[evaluation_rows], compression="lzf"
            )
            group = handle.create_group("metrics")
            for name, value in values.items():
                group.create_dataset(name, data=value, compression="lzf")
            handle.attrs["task"] = args.task
            handle.attrs["seed"] = args.seed
            handle.attrs["mode"] = args.mode
            handle.attrs["protocol_sha256"] = spec.PROTOCOL_SHA256
        os.replace(partial, detail_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    summary = {
        "status": "ok",
        "kind": "gdp_cem_post_e14_frozen_vad_boundary_diagnostic",
        "analysis_role": "P1_development_artifact_diagnosis_only",
        "task": args.task,
        "seed": args.seed,
        "mode": args.mode,
        "row_count": int(len(evaluation_rows)),
        "validation_rows_sha256": array_sha256(evaluation_rows),
        "candidate_count": CANDIDATE_COUNT,
        "batch_size": DEFAULT_BATCH_SIZE,
        "near_margins_fraction_of_span": list(NEAR_MARGINS),
        "bounds": {
            "robust_low": store.action_robust_low.tolist(),
            "robust_high": store.action_robust_high.tolist(),
            "environment_legal_low": environment_legal_low.tolist(),
            "environment_legal_high": environment_legal_high.tolist(),
            "planner_primitive_action_mean": planner_action_mean.tolist(),
            "planner_primitive_action_std": planner_action_std.tolist(),
            "planner_coordinate_legal_low": legal_low_np.tolist(),
            "planner_coordinate_legal_high": legal_high_np.tolist(),
            "raw_environment_tolerance": RAW_ENVIRONMENT_TOLERANCE,
            "planner_coordinate_tolerant_legal_low": (
                tolerant_legal_low_np.tolist()
            ),
            "planner_coordinate_tolerant_legal_high": (
                tolerant_legal_high_np.tolist()
            ),
            "transition_h5": str(args.transition_h5),
            "transition_h5_sha256": sha256_file(args.transition_h5),
            "legal_bound_source": str(args.legal_bound_source),
            "legal_bound_source_sha256": sha256_file(args.legal_bound_source),
            "legal_bound_interpretation": (
                "deployed_environment_action_space_mapped_through_the_exact_"
                "released_float32_planner_StandardScaler_with_strict_and_"
                "four_epsilon_tolerant_diagnostics"
            ),
        },
        "expert_training_cache": expert_cache_summary(
            store,
            store.train_rows,
            legal_low=legal_low_np,
            legal_high=legal_high_np,
            tolerant_legal_low=tolerant_legal_low_np,
            tolerant_legal_high=tolerant_legal_high_np,
        ),
        "expert_validation_cache": expert_cache_summary(
            store,
            store.validation_rows,
            legal_low=legal_low_np,
            legal_high=legal_high_np,
            tolerant_legal_low=tolerant_legal_low_np,
            tolerant_legal_high=tolerant_legal_high_np,
        ),
        "aggregates": aggregates,
        "axis_diagnostics": {name: accumulator.result() for name, accumulator in axis.items()},
        "reproduction": {
            "original_e14_boundary_metric_reproduced": True,
            "coverage": "all_rows" if args.mode == "full" else "first_condition_only",
            "compared_row_count": int(reproduction_mask.sum()),
            "maximum_absolute_error": float(reproduction_error[reproduction_mask].max()),
            "mean_absolute_error": float(reproduction_error[reproduction_mask].mean()),
            **original_record,
        },
        "model": model_record,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "row_metrics_h5": str(detail_path),
        "row_metrics_h5_sha256": sha256_file(detail_path),
        "lineage": store.lineage,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "diagnostic_source_sha256": sha256_file(Path(__file__)),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "peak_cuda_memory_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
        },
        "descriptive_only": True,
        "may_modify_e14_result": False,
        "may_select_or_authorize_e15": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
