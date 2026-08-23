#!/usr/bin/env python3
"""Evaluate one frozen E14 endpoint model on all 40k P1-validation rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
from gdp_cem_e14_data import E14ArrayStore, sha256_file
from gdp_cem_e14_models import (
    CosineSchedule,
    Endpoint,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    endpoint_output_dim,
    velocity_ddim_sample,
    velocity_target,
)
from gdp_cem_latent_rollout import rollout_from_single_latent
from train_gdp_cem_e14_endpoint import CONDITIONS


TRAINING_SOURCE_MANIFEST_SHA256 = (
    "99f92cbe3c735a999866b52103241633ec80a7dffeca5217c07b0ec5590176cd"
)
CANDIDATE_COUNT = 300
DEFAULT_BATCH_SIZE = 8


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E14 protected path is forbidden: {path}")


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


def load_model(
    summary_path: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    store: E14ArrayStore,
    device: torch.device,
) -> tuple[torch.nn.Module, dict[str, Any], dict[str, Any]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    endpoint, family = condition.split("_", maxsplit=1)
    gaussian = family == "gaussian"
    output_dim = endpoint_output_dim(
        endpoint,
        latent_dim=store.latent_dim,
        primitive_action_dim=store.primitive_action_dim,
    )
    config = {
        "latent_dim": store.latent_dim,
        "state_dim": store.state_dim,
        "output_dim": output_dim,
        "width": spec.MODEL_WIDTH,
        "depth": spec.MODEL_DEPTH,
        "time_embedding_dim": spec.TIME_EMBEDDING_DIM,
    }
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e14_p1_endpoint_training"
        or summary.get("analysis_role")
        != "P1_only_long_horizon_method_development"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or summary.get("endpoint") != endpoint
        or summary.get("family") != family
        or int(summary.get("seed", -1)) != seed
        or summary.get("model_kind")
        != ("diagonal_gaussian" if gaussian else "velocity_diffusion")
        or summary.get("model_config") != config
        or summary.get("lineage") != store.lineage
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E14 endpoint training summary differs")
    checkpoint = Path(summary.get("checkpoint", ""))
    reject_protected_path(checkpoint)
    if not checkpoint.is_file() or sha256_file(checkpoint) != summary.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError("E14 endpoint checkpoint hash differs")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if (
        payload.get("kind") != "gdp_cem_e14_p1_endpoint_checkpoint"
        or payload.get("task") != task
        or payload.get("condition") != condition
        or payload.get("endpoint") != endpoint
        or payload.get("family") != family
        or int(payload.get("seed", -1)) != seed
        or payload.get("model_config") != config
        or payload.get("lineage") != store.lineage
        or payload.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or payload.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E14 endpoint checkpoint identity differs")
    model: torch.nn.Module = (
        VariableDiagonalGaussian(**config)
        if gaussian
        else VariableVelocityDiffusion(**config)
    )
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    if sum(parameter.numel() for parameter in model.parameters()) != int(
        summary["parameter_count"]
    ):
        raise RuntimeError("E14 endpoint parameter count differs")
    return model, payload, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "best_step": summary["best_step"],
        "best_validation": summary["best_validation"],
        "parameter_count": summary["parameter_count"],
    }


def per_row_masked_mean(value: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    weight = mask.to(value.dtype)
    return (value * weight).sum(dim=-1) / weight.sum(dim=-1)


@torch.inference_mode()
def family_objective(
    model: torch.nn.Module,
    *,
    family: str,
    current: torch.Tensor,
    goal: torch.Tensor,
    state: torch.Tensor,
    delta: torch.Tensor,
    tau: torch.Tensor,
    clean: torch.Tensor,
    mask: torch.Tensor,
    schedule: CosineSchedule,
    generator: torch.Generator,
) -> torch.Tensor:
    if family == "gaussian":
        assert isinstance(model, VariableDiagonalGaussian)
        mean, log_std = model(current, goal, state, delta, tau)
        standardized = (clean - mean) / log_std.exp()
        element = 0.5 * standardized.square() + log_std + 0.5 * math.log(
            2.0 * math.pi
        )
        return per_row_masked_mean(element, mask)
    assert isinstance(model, VariableVelocityDiffusion)
    timestep = torch.randint(
        0,
        spec.DIFFUSION_STEPS,
        (len(current),),
        device=current.device,
        generator=generator,
    )
    noise = torch.randn(
        clean.shape,
        device=clean.device,
        dtype=clean.dtype,
        generator=generator,
    )
    alpha = schedule.alpha_bar.to(clean.device)[timestep, None]
    noisy = (alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise) * mask
    target = velocity_target(clean, noise, alpha) * mask
    prediction = model(
        current,
        goal,
        state,
        delta,
        tau,
        noisy,
        timestep,
        conditioned=family != "unconditional",
    )
    return per_row_masked_mean((prediction - target).square(), mask)


@torch.inference_mode()
def generate_candidates(
    model: torch.nn.Module,
    *,
    endpoint: Endpoint,
    family: str,
    current: torch.Tensor,
    goal: torch.Tensor,
    state: torch.Tensor,
    delta: torch.Tensor,
    tau: torch.Tensor,
    active_mask: torch.Tensor,
    schedule: CosineSchedule,
    generator: torch.Generator,
) -> torch.Tensor:
    shape = (len(current), CANDIDATE_COUNT, active_mask.shape[1])
    noise = torch.randn(
        shape,
        device=current.device,
        dtype=current.dtype,
        generator=generator,
    ) * active_mask[:, None]
    if family == "gaussian":
        assert isinstance(model, VariableDiagonalGaussian)
        mean, log_std = model(current, goal, state, delta, tau)
        result = mean[:, None] + log_std.exp()[:, None] * noise
        result = result * active_mask[:, None]
    else:
        assert isinstance(model, VariableVelocityDiffusion)
        result = velocity_ddim_sample(
            model,
            current=current,
            goal=goal,
            state=state,
            delta=delta,
            tau=tau,
            initial_noise=noise,
            active_mask=active_mask,
            schedule=schedule,
            evaluations=spec.DIFFUSION_EVALUATIONS,
            guidance_scale=(
                0.0 if family == "unconditional" else spec.GUIDANCE_SCALE
            ),
        )
    if result.shape != shape or not torch.isfinite(result).all():
        raise RuntimeError("E14 offline candidate bank differs")
    return result


def aggregate_metrics(
    *,
    delta: np.ndarray,
    tau: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> dict[str, Any]:
    cells: dict[str, dict[str, float]] = {}
    for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
        active = (delta == delta_value) & (tau == tau_value)
        if not active.any():
            raise RuntimeError("E14 offline aggregate cell is empty")
        cells[f"delta={delta_value},tau={tau_value}"] = {
            key: float(np.mean(value[active], dtype=np.float64))
            for key, value in metrics.items()
        }
    per_tau: dict[str, dict[str, float]] = {}
    for tau_value in spec.TAU_VALUES:
        matching = [
            value
            for key, value in cells.items()
            if key.endswith(f"tau={tau_value}")
        ]
        per_tau[str(tau_value)] = {
            metric: float(np.mean([cell[metric] for cell in matching]))
            for metric in metrics
        }
    equal_cell = {
        metric: float(np.mean([cell[metric] for cell in cells.values()]))
        for metric in metrics
    }
    return {"cells": cells, "per_tau": per_tau, "equal_cell_mean": equal_cell}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--seed", type=int, choices=spec.MODEL_SEEDS, required=True)
    parser.add_argument("--training-summary", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    args = parser.parse_args()
    endpoint, family = args.condition.split("_", maxsplit=1)
    if family in ("shuffled_goal", "unconditional") and args.seed != spec.DIAGNOSTIC_SEED:
        raise RuntimeError("E14 diagnostics are frozen to seed 6101")
    if args.batch_size <= 0:
        raise ValueError("E14 offline batch size must be positive")
    required = (
        args.training_summary,
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.world_model_checkpoint,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E14 offline protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E14 offline output")
    if not torch.cuda.is_available():
        raise RuntimeError("E14 offline evaluation requires CUDA")

    torch.manual_seed(1416)
    torch.cuda.manual_seed_all(1416)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    store = E14ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    model, payload, model_record = load_model(
        args.training_summary,
        task=args.task,
        condition=args.condition,
        seed=args.seed,
        store=store,
        device=device,
    )
    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("E14 world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    schedule = CosineSchedule.build(spec.DIFFUSION_STEPS)
    output_dim = endpoint_output_dim(
        endpoint,
        latent_dim=store.latent_dim,
        primitive_action_dim=store.primitive_action_dim,
    )
    action_offset = 0 if endpoint == "vad" else store.latent_dim
    normalized_low = torch.from_numpy(
        (store.action_robust_low - store.action_mean) / store.action_std
    ).to(device)
    normalized_high = torch.from_numpy(
        (store.action_robust_high - store.action_mean) / store.action_std
    ).to(device)
    action_mean = torch.from_numpy(store.action_mean).to(device)
    action_std = torch.from_numpy(store.action_std).to(device)
    latent_mean = torch.from_numpy(store.latent_mean).to(device)
    latent_std = torch.from_numpy(store.latent_std).to(device)
    residual_mean = torch.from_numpy(store.local_residual_mean).to(device)
    residual_std = torch.from_numpy(store.local_residual_std).to(device)

    metric_names = [
        "family_objective",
        "oracle_action_mse",
        "selected_action_mse",
        "true_local_terminal_cost",
        "far_goal_terminal_cost",
        "selection_cost",
        "candidate_variance",
        "unique_candidates",
        "boundary_fraction",
        "generation_seconds_per_context",
        "rollout_seconds_per_context",
    ]
    if endpoint == "cvd":
        metric_names.extend(
            (
                "oracle_generated_local_mse",
                "selected_generated_local_mse",
                "mean_generated_local_mse",
                "terminal_consistency",
            )
        )
    if args.mode == "full":
        evaluation_rows = store.validation_rows
    else:
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
    values = {
        name: np.full(len(evaluation_rows), np.nan, dtype=np.float64)
        for name in metric_names
    }
    row_to_position = np.full(len(store.role), -1, dtype=np.int64)
    row_to_position[evaluation_rows] = np.arange(len(evaluation_rows))
    candidate_generator = torch.Generator(device=device).manual_seed(
        spec.derived_seed(
            f"offline-candidates|task={args.task}|endpoint={endpoint}|seed={args.seed}"
        )
    )
    objective_generator = torch.Generator(device=device).manual_seed(
        spec.derived_seed(
            f"offline-objective|task={args.task}|endpoint={endpoint}|seed={args.seed}"
        )
    )
    started = time.time()
    warmed = False
    torch.cuda.reset_peak_memory_stats(device)
    for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
        cell_rows = evaluation_rows[
            (store.delta[evaluation_rows] == delta_value)
            & (store.tau[evaluation_rows] == tau_value)
        ]
        for start in range(0, len(cell_rows), args.batch_size):
            rows = cell_rows[start : start + args.batch_size]
            positions = row_to_position[rows]
            batch = store.batch(rows)
            clean, active_mask = batch.endpoint_target(endpoint)
            current = batch.current.to(device)
            goal = batch.goal.to(device)
            local = batch.local.to(device)
            state = batch.state.to(device)
            delta = batch.delta.to(device)
            tau = batch.tau.to(device)
            clean = clean.to(device)
            active_mask = active_mask.to(device)
            values["family_objective"][positions] = family_objective(
                model,
                family=family,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                clean=clean,
                mask=active_mask,
                schedule=schedule,
                generator=objective_generator,
            ).double().cpu().numpy()

            if not warmed:
                warm_generator = torch.Generator(device=device).manual_seed(
                    spec.derived_seed(
                        f"offline-warmup|task={args.task}|endpoint={endpoint}|seed={args.seed}"
                    )
                )
                warm = generate_candidates(
                    model,
                    endpoint=endpoint,
                    family=family,
                    current=current,
                    goal=goal,
                    state=state,
                    delta=delta,
                    tau=tau,
                    active_mask=active_mask,
                    schedule=schedule,
                    generator=warm_generator,
                )
                warm_action = warm[:, :, action_offset:].reshape(
                    len(rows),
                    CANDIDATE_COUNT,
                    spec.ACTION_HORIZON,
                    store.primitive_action_dim,
                )[:, :, :tau_value]
                warm_action = torch.maximum(
                    torch.minimum(warm_action, normalized_high), normalized_low
                )
                warm_primitive = warm_action * action_std + action_mean
                warm_macro = warm_primitive.reshape(
                    len(rows),
                    CANDIDATE_COUNT,
                    tau_value // spec.ACTION_BLOCK,
                    spec.ACTION_BLOCK * store.primitive_action_dim,
                )
                _ = rollout_from_single_latent(
                    world_model,
                    current=current * latent_std + latent_mean,
                    macro_actions=warm_macro,
                )
                torch.cuda.synchronize()
                del warm, warm_action, warm_primitive, warm_macro
                warmed = True

            torch.cuda.synchronize()
            generation_started = time.perf_counter()
            candidates = generate_candidates(
                model,
                endpoint=endpoint,
                family=family,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                active_mask=active_mask,
                schedule=schedule,
                generator=candidate_generator,
            )
            normalized_action = candidates[:, :, action_offset:].reshape(
                len(rows),
                CANDIDATE_COUNT,
                spec.ACTION_HORIZON,
                store.primitive_action_dim,
            )[:, :, :tau_value]
            normalized_action = torch.maximum(
                torch.minimum(normalized_action, normalized_high), normalized_low
            )
            torch.cuda.synchronize()
            generation_seconds = time.perf_counter() - generation_started
            primitive_action = normalized_action * action_std + action_mean
            macro_action = primitive_action.reshape(
                len(rows),
                CANDIDATE_COUNT,
                tau_value // spec.ACTION_BLOCK,
                spec.ACTION_BLOCK * store.primitive_action_dim,
            )
            current_raw = current * latent_std + latent_mean
            goal_raw = goal * latent_std + latent_mean
            local_raw = local * latent_std + latent_mean
            torch.cuda.synchronize()
            rollout_started = time.perf_counter()
            trajectory = rollout_from_single_latent(
                world_model, current=current_raw, macro_actions=macro_action
            )
            terminal = trajectory[:, :, -1]
            if endpoint == "vad":
                selection_bank = (terminal - goal_raw[:, None]).square().sum(dim=-1)
                generated_local = None
            else:
                residual = (
                    candidates[:, :, : store.latent_dim] * residual_std
                    + residual_mean
                )
                generated_local_normalized = goal[:, None] + residual
                generated_local = (
                    generated_local_normalized * latent_std + latent_mean
                )
                selection_bank = (terminal - generated_local).square().sum(dim=-1)
            selected_index = selection_bank.argmin(dim=1)
            batch_index = torch.arange(len(rows), device=device)
            selected_terminal = terminal[batch_index, selected_index]
            selected_action = primitive_action[batch_index, selected_index]
            true_local_cost = (selected_terminal - local_raw).square().sum(dim=-1)
            far_goal_cost = (selected_terminal - goal_raw).square().sum(dim=-1)
            reference_action = (
                batch.action[:, :tau_value].to(device) * action_std + action_mean
            )
            action_error = (primitive_action - reference_action[:, None]).square().mean(
                dim=(-1, -2)
            )
            candidate_variance = primitive_action.var(dim=1, unbiased=True).mean(
                dim=(-1, -2)
            )
            boundary = torch.logical_or(
                normalized_action == normalized_low,
                normalized_action == normalized_high,
            ).float().mean(dim=(-1, -2, -3))
            torch.cuda.synchronize()
            rollout_seconds = time.perf_counter() - rollout_started

            rounded = torch.round(normalized_action * 1.0e4).to(torch.int64).cpu().numpy()
            unique = np.asarray(
                [
                    np.unique(row.reshape(CANDIDATE_COUNT, -1), axis=0).shape[0]
                    for row in rounded
                ],
                dtype=np.float64,
            )
            values["oracle_action_mse"][positions] = action_error.min(dim=1).values.double().cpu().numpy()
            values["selected_action_mse"][positions] = (
                (selected_action - reference_action).square().mean(dim=(-1, -2)).double().cpu().numpy()
            )
            values["true_local_terminal_cost"][positions] = true_local_cost.double().cpu().numpy()
            values["far_goal_terminal_cost"][positions] = far_goal_cost.double().cpu().numpy()
            values["selection_cost"][positions] = selection_bank[batch_index, selected_index].double().cpu().numpy()
            values["candidate_variance"][positions] = candidate_variance.double().cpu().numpy()
            values["unique_candidates"][positions] = unique
            values["boundary_fraction"][positions] = boundary.double().cpu().numpy()
            values["generation_seconds_per_context"][positions] = generation_seconds / len(rows)
            values["rollout_seconds_per_context"][positions] = rollout_seconds / len(rows)
            if endpoint == "cvd":
                assert generated_local is not None
                local_error = (
                    (generated_local - local_raw[:, None]) / latent_std
                ).square().mean(dim=-1)
                values["oracle_generated_local_mse"][positions] = local_error.min(dim=1).values.double().cpu().numpy()
                values["selected_generated_local_mse"][positions] = local_error[batch_index, selected_index].double().cpu().numpy()
                values["mean_generated_local_mse"][positions] = local_error.mean(dim=1).double().cpu().numpy()
                values["terminal_consistency"][positions] = selection_bank[batch_index, selected_index].double().cpu().numpy()

    if any(not np.isfinite(value).all() for value in values.values()):
        raise RuntimeError("E14 offline metrics contain missing or non-finite values")
    aggregates = aggregate_metrics(
        delta=store.delta[evaluation_rows],
        tau=store.tau[evaluation_rows],
        metrics=values,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "metrics.h5"
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
            handle.attrs["condition"] = args.condition
            handle.attrs["seed"] = args.seed
            handle.attrs["protocol_sha256"] = spec.PROTOCOL_SHA256
        os.replace(partial, detail_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    summary = {
        "status": "ok",
        "kind": f"gdp_cem_e14_{args.mode}_p1_validation_endpoint_evaluation",
        "analysis_role": (
            "P1_validation_only_Gate_B_development"
            if args.mode == "full"
            else "P1_validation_structural_smoke_only"
        ),
        "mode": args.mode,
        "task": args.task,
        "condition": args.condition,
        "endpoint": endpoint,
        "family": family,
        "seed": args.seed,
        "row_count": len(evaluation_rows),
        "validation_rows_sha256": array_sha256(evaluation_rows),
        "candidate_count": CANDIDATE_COUNT,
        "reverse_evaluations": None if family == "gaussian" else spec.DIFFUSION_EVALUATIONS,
        "guidance_scale": None if family == "gaussian" else (0.0 if family == "unconditional" else spec.GUIDANCE_SCALE),
        "batch_size": args.batch_size,
        "aggregates": aggregates,
        "bank_validity": {
            "all_finite": True,
            "minimum_unique_candidates": int(values["unique_candidates"].min()),
            "maximum_boundary_fraction": float(values["boundary_fraction"].max()),
        },
        "model": model_record,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "metrics_h5": str(detail_path),
        "metrics_h5_sha256": sha256_file(detail_path),
        "lineage": store.lineage,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest_sha256": TRAINING_SOURCE_MANIFEST_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "evaluator_source_sha256": sha256_file(Path(__file__)),
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
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
        "smoke_metrics_may_select_or_modify_method": False,
    }
    atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
