#!/usr/bin/env python3
"""Evaluate one frozen E15 proposer on training-smoke or full validation rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

import gdp_cem_e15_specs as spec
from acid_alternative.io_utils import resolve_policy_checkpoint
from gdp_cem_e15_data import E15ArrayStore, sha256_file
from gdp_cem_e15_models import (
    CosineSchedule,
    DirectTrajectoryGMM,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    action_active_mask,
    bounded_actions_from_standardized_u,
    flat_action_active_mask,
    instantiate_model,
    model_config,
    sample_direct_gmm_with_modes,
    trajectory_gmm_posterior,
    velocity_ddim_sample,
)
from gdp_cem_latent_rollout import rollout_from_single_latent


TRAINING_SOURCE_MANIFEST_SHA256 = (
    "ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c"
)


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E15 protected path is forbidden: {path}")


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


def atomic_text(path: Path, value: str) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def array_sha256(value: np.ndarray | torch.Tensor) -> str:
    if torch.is_tensor(value):
        value = value.detach().cpu().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def scientific_label(value: float) -> str:
    """Return the stable metric suffix used by the frozen E15 registry."""

    return f"{value:.0e}".replace("e-0", "e-").replace("e+0", "e+")


def read_sha256_records(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        if name in records or len(digest) != 64:
            raise RuntimeError("invalid E15 checksum manifest")
        records[name] = digest
    return records


def verify_training_directory(directory: Path) -> None:
    manifest = directory / "sha256.txt"
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    records = read_sha256_records(manifest)
    if set(records) != {"final.pt", "training.jsonl", "summary.json"}:
        raise RuntimeError("E15 training checksum names differ")
    for name, digest in records.items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"E15 training checksum differs: {path}")


def tensor_matches(value: Any, expected: np.ndarray | float) -> bool:
    if isinstance(expected, float):
        return isinstance(value, (float, int)) and float(value) == expected
    return torch.is_tensor(value) and np.array_equal(
        value.detach().cpu().numpy(), expected
    )


def load_model(
    directory: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    store: E15ArrayStore,
    device: torch.device,
) -> tuple[torch.nn.Module, dict[str, Any]]:
    verify_training_directory(directory)
    summary_path = directory / "summary.json"
    checkpoint_path = directory / "final.pt"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config = model_config(task, condition)
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e15_p1_final_proposer_training"
        or summary.get("analysis_role")
        != "P1_train_only_long_horizon_method_development"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or int(summary.get("seed", -1)) != seed
        or summary.get("model_config") != config
        or summary.get("checkpoint_selection")
        != "fixed_final_ema_step_30000_no_validation_access"
        or int(summary.get("training_rows", -1)) != spec.TRAIN_ROWS
        or int(summary.get("validation_payload_rows_read", -1)) != 0
        or summary.get("lineage") != store.lineage
        or summary.get("checkpoint_sha256") != sha256_file(checkpoint_path)
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("p2_read") is not False
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E15 training summary identity differs")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    statistics = payload.get("statistics", {})
    expected_statistics: dict[str, np.ndarray | float] = {
        "latent_mean": store.latent_mean,
        "latent_std": store.latent_std,
        "state_mean": store.state_mean,
        "state_std": store.state_std,
        "u_mean": store.u_mean,
        "u_std": store.u_std,
        "planner_action_mean": store.planner_action_mean,
        "planner_action_std": store.planner_action_std,
        "interior_scale": store.interior_scale,
        "target_raw_limit": store.target_raw_limit,
    }
    if (
        payload.get("kind") != "gdp_cem_e15_p1_final_proposer_checkpoint"
        or payload.get("task") != task
        or payload.get("condition") != condition
        or int(payload.get("seed", -1)) != seed
        or payload.get("model_config") != config
        or int(payload.get("final_step", -1)) != spec.TRAIN_STEPS
        or payload.get("lineage") != store.lineage
        or int(payload.get("validation_payload_rows_read", -1)) != 0
        or payload.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or payload.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or set(statistics) != set(expected_statistics)
        or any(
            not tensor_matches(statistics[name], value)
            for name, value in expected_statistics.items()
        )
    ):
        raise RuntimeError("E15 checkpoint identity/statistics differ")
    model = instantiate_model(task, condition)
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    if sum(parameter.numel() for parameter in model.parameters()) != int(
        summary["parameter_count"]
    ):
        raise RuntimeError("E15 proposer parameter count differs")
    return model, {
        "directory": str(directory),
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "parameter_count": summary["parameter_count"],
        "training_elapsed_seconds": summary["elapsed_seconds"],
        "training_peak_cuda_memory_allocated_bytes": summary[
            "peak_cuda_memory_allocated_bytes"
        ],
    }


@torch.inference_mode()
def generate_standardized_u(
    model: torch.nn.Module,
    *,
    condition: str,
    current: torch.Tensor,
    goal: torch.Tensor,
    state: torch.Tensor,
    delta: torch.Tensor,
    tau: torch.Tensor,
    schedule: CosineSchedule,
    gpu_generator: torch.Generator,
    cpu_generator: torch.Generator,
    primitive_action_dim: int,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    batch = len(current)
    active_3d = action_active_mask(
        tau, primitive_action_dim=primitive_action_dim
    )
    active_flat = active_3d.reshape(batch, -1)
    extras: dict[str, torch.Tensor] = {}
    if condition in ("vad", "vad_shuffled", "vad_unconditional"):
        assert isinstance(model, VariableVelocityDiffusion)
        noise = torch.randn(
            batch,
            spec.CANDIDATE_COUNT,
            active_flat.shape[1],
            device=current.device,
            generator=gpu_generator,
        ) * active_flat[:, None]
        flat = velocity_ddim_sample(
            model,
            current=current,
            goal=goal,
            state=state,
            delta=delta,
            tau=tau,
            initial_noise=noise,
            active_mask=active_flat,
            schedule=schedule,
            evaluations=spec.DIFFUSION_EVALUATIONS,
            guidance_scale=(
                0.0 if condition == "vad_unconditional" else spec.GUIDANCE_SCALE
            ),
        )
        value = flat.reshape(
            batch,
            spec.CANDIDATE_COUNT,
            spec.ACTION_HORIZON,
            primitive_action_dim,
        )
    elif condition == "diagonal_gaussian":
        assert isinstance(model, VariableDiagonalGaussian)
        mean, log_std = model(current, goal, state, delta, tau)
        noise = torch.randn(
            batch,
            spec.CANDIDATE_COUNT,
            mean.shape[1],
            device=current.device,
            generator=gpu_generator,
        )
        flat = (mean[:, None] + log_std.exp()[:, None] * noise) * active_flat[:, None]
        value = flat.reshape(
            batch,
            spec.CANDIDATE_COUNT,
            spec.ACTION_HORIZON,
            primitive_action_dim,
        )
    elif condition == "direct_gmm":
        assert isinstance(model, DirectTrajectoryGMM)
        logits, means, log_stds = model(current, goal, state, delta, tau)
        value, modes = sample_direct_gmm_with_modes(
            logits,
            means,
            log_stds,
            count=spec.CANDIDATE_COUNT,
            active_mask=active_3d[:, :, 0],
            generator=cpu_generator,
        )
        extras = {
            "prior_probability": torch.softmax(logits.float(), dim=-1),
            "sampled_modes": modes,
            "gmm_logits": logits.float(),
            "gmm_means": means.float(),
            "gmm_log_stds": log_stds.float(),
        }
    else:
        raise ValueError("unknown E15 offline condition")
    return value, extras


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--condition", choices=spec.TRAINING_CONDITIONS, required=True)
    parser.add_argument("--seed", type=int, choices=spec.MODEL_SEEDS, required=True)
    parser.add_argument("--training-dir", type=Path, required=True)
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
    args = parser.parse_args()
    if args.condition in ("vad_shuffled", "vad_unconditional") and args.seed != spec.NULL_SEED:
        raise RuntimeError("E15 offline null seed differs")
    required = (
        args.training_dir,
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.world_model_checkpoint,
        args.stablewm_home,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E15 offline protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E15 offline output")
    if not torch.cuda.is_available():
        raise RuntimeError("E15 offline evaluation requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E15 offline GPU model differs")
    task_spec = spec.TASK_SPEC[args.task]
    if (
        args.world_model_policy != task_spec["world_model_policy"]
        or sha256_file(args.world_model_checkpoint)
        != task_spec["world_model_sha256"]
        or resolve_policy_checkpoint(
            args.world_model_policy, args.stablewm_home
        ).resolve()
        != args.world_model_checkpoint.resolve()
    ):
        raise RuntimeError("E15 released world-model identity differs")

    torch.manual_seed(1516)
    np.random.seed(1516)
    torch.cuda.manual_seed_all(1516)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    store = E15ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    model, model_record = load_model(
        args.training_dir,
        task=args.task,
        condition=args.condition,
        seed=args.seed,
        store=store,
        device=device,
    )
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    schedule = CosineSchedule.build(spec.DIFFUSION_STEPS)
    gpu_generator = torch.Generator(device=device).manual_seed(
        spec.derived_seed(
            f"offline-gpu|task={args.task}|condition={args.condition}|seed={args.seed}"
        )
    )
    cpu_generator = torch.Generator(device="cpu").manual_seed(
        spec.derived_seed(
            f"offline-cpu|task={args.task}|condition={args.condition}|seed={args.seed}"
        )
    )
    evaluation_rows = store.validation_rows
    analysis_role = "P1_validation_only_Gate_B_development"
    if args.mode == "smoke":
        evaluation_rows = np.asarray(
            [
                store.train_rows[
                    (store.delta[store.train_rows] == delta_value)
                    & (store.tau[store.train_rows] == tau_value)
                ][0]
                for delta_value, tau_value in spec.DELTA_TAU_PAIRS
            ],
            dtype=np.int64,
        )
        analysis_role = "P1_train_only_technical_smoke"
    row_to_position = np.full(len(store.role), -1, dtype=np.int64)
    row_to_position[evaluation_rows] = np.arange(len(evaluation_rows))
    metric_names = [
        "oracle_projected_action_mse",
        "oracle_original_action_mse",
        "selected_true_local_lewm_cost",
        "selected_far_goal_lewm_cost",
        "candidate_variance",
        "post_squash_coordinate_std_mean",
        "mean_pairwise_raw_action_rmse",
        "minimum_unique_candidates",
        "strict_legal_oob_fraction",
        "exact_legal_boundary_fraction",
        "expert_target_projection_fraction",
        "pre_squash_abs_u_mean",
        "pre_squash_abs_u_q95",
        "pre_squash_abs_u_q99",
        "pre_squash_abs_u_max",
        "proposal_seconds_per_row",
        "lewm_seconds_per_row",
        "total_seconds_per_row",
    ]
    for margin in spec.NEAR_BOUNDARY_MARGINS:
        suffix = scientific_label(margin)
        metric_names.extend(
            (f"near_{suffix}_fraction", f"expert_near_{suffix}_fraction")
        )
    for threshold in spec.JACOBIAN_THRESHOLDS:
        suffix = scientific_label(threshold)
        metric_names.extend(
            (
                f"jacobian_below_{suffix}_fraction",
                f"expert_jacobian_below_{suffix}_fraction",
            )
        )
    metrics = {
        name: np.full(len(evaluation_rows), np.nan, dtype=np.float64)
        for name in metric_names
    }
    gmm_arrays: dict[str, np.ndarray] = {}
    if args.condition == "direct_gmm":
        for name in ("prior_probability", "posterior_probability", "sampled_mode_fraction"):
            gmm_arrays[name] = np.full(
                (len(evaluation_rows), spec.GMM_MODES), np.nan, dtype=np.float64
            )
        gmm_arrays["normalized_prior_entropy"] = np.full(
            len(evaluation_rows), np.nan, dtype=np.float64
        )
        gmm_arrays["effective_prior_modes"] = np.full(
            len(evaluation_rows), np.nan, dtype=np.float64
        )

    u_mean = torch.from_numpy(store.u_mean).to(device)
    u_std = torch.from_numpy(store.u_std).to(device)
    planner_mean = torch.from_numpy(store.planner_action_mean).to(device)
    planner_std = torch.from_numpy(store.planner_action_std).to(device)
    latent_mean = torch.from_numpy(store.latent_mean).to(device)
    latent_std = torch.from_numpy(store.latent_std).to(device)
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
        cell_rows = evaluation_rows[
            (store.delta[evaluation_rows] == delta_value)
            & (store.tau[evaluation_rows] == tau_value)
        ]
        for start in range(0, len(cell_rows), spec.OFFLINE_BATCH_SIZE):
            rows = cell_rows[start : start + spec.OFFLINE_BATCH_SIZE]
            positions = row_to_position[rows]
            batch = store.batch(rows)
            current = batch.current.to(device)
            goal = batch.goal.to(device)
            local = batch.local.to(device)
            state = batch.state.to(device)
            delta = batch.delta.to(device)
            tau = batch.tau.to(device)
            active = action_active_mask(
                tau, primitive_action_dim=store.primitive_action_dim
            )
            torch.cuda.synchronize()
            proposal_started = time.perf_counter()
            standardized_u, extras = generate_standardized_u(
                model,
                condition=args.condition,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                schedule=schedule,
                gpu_generator=gpu_generator,
                cpu_generator=cpu_generator,
                primitive_action_dim=store.primitive_action_dim,
            )
            if args.condition == "direct_gmm":
                extras["posterior_probability"] = trajectory_gmm_posterior(
                    extras.pop("gmm_logits"),
                    extras.pop("gmm_means"),
                    extras.pop("gmm_log_stds"),
                    batch.action_u.to(device),
                    batch.action_mask.to(device),
                )
            raw, planner, jacobian = bounded_actions_from_standardized_u(
                standardized_u,
                u_mean=u_mean,
                u_std=u_std,
                planner_mean=planner_mean,
                planner_std=planner_std,
                interior_scale=store.interior_scale,
                active_mask=active,
            )
            torch.cuda.synchronize()
            proposal_seconds = time.perf_counter() - proposal_started

            raw_active = raw[:, :, :tau_value]
            planner_active = planner[:, :, :tau_value]
            physical_u_active = (
                standardized_u[:, :, :tau_value]
                * u_std.reshape(1, 1, 1, -1)
                + u_mean.reshape(1, 1, 1, -1)
            )
            macro = planner_active.reshape(
                len(rows),
                spec.CANDIDATE_COUNT,
                tau_value // spec.ACTION_BLOCK,
                spec.ACTION_BLOCK * store.primitive_action_dim,
            )
            current_raw = current * latent_std + latent_mean
            local_raw = local * latent_std + latent_mean
            goal_raw = goal * latent_std + latent_mean
            torch.cuda.synchronize()
            lewm_started = time.perf_counter()
            terminal = rollout_from_single_latent(
                world_model, current=current_raw, macro_actions=macro
            )[:, :, -1]
            far_cost = (terminal - goal_raw[:, None]).square().sum(dim=-1)
            selected_index = far_cost.argmin(dim=1)
            batch_index = torch.arange(len(rows), device=device)
            selected_terminal = terminal[batch_index, selected_index]
            local_cost = (selected_terminal - local_raw).square().sum(dim=-1)
            torch.cuda.synchronize()
            lewm_seconds = time.perf_counter() - lewm_started

            projected = batch.action_raw_projected[:, :tau_value].to(device)
            original = batch.action_raw_original[:, :tau_value].to(device)
            projected_error = (raw_active - projected[:, None]).square().mean(
                dim=(-1, -2)
            )
            original_error = (raw_active - original[:, None]).square().mean(
                dim=(-1, -2)
            )
            rounded = torch.round(raw_active * 1.0e4).to(torch.int64).cpu().numpy()
            unique = np.asarray(
                [
                    np.unique(row.reshape(spec.CANDIDATE_COUNT, -1), axis=0).shape[0]
                    for row in rounded
                ],
                dtype=np.float64,
            )
            strict_oob = torch.abs(raw_active) > 1.0
            exact = torch.abs(raw_active) == 1.0
            generated_jacobian = jacobian[:, :, :tau_value]
            expert_u = (
                batch.action_u[:, :tau_value].to(device) * u_std + u_mean
            )
            expert_jacobian = 1.0 - torch.tanh(expert_u).square()
            coordinate_variance = raw_active.var(dim=1, unbiased=True)
            absolute_u = physical_u_active.abs().reshape(len(rows), -1)
            values = {
                "oracle_projected_action_mse": projected_error.min(dim=1).values,
                "oracle_original_action_mse": original_error.min(dim=1).values,
                "selected_true_local_lewm_cost": local_cost,
                "selected_far_goal_lewm_cost": far_cost.min(dim=1).values,
                "candidate_variance": coordinate_variance.mean(dim=(-1, -2)),
                "post_squash_coordinate_std_mean": coordinate_variance.sqrt().mean(
                    dim=(-1, -2)
                ),
                "mean_pairwise_raw_action_rmse": (
                    2.0 * coordinate_variance.mean(dim=(-1, -2))
                ).sqrt(),
                "strict_legal_oob_fraction": strict_oob.float().mean(
                    dim=(1, 2, 3)
                ),
                "exact_legal_boundary_fraction": exact.float().mean(
                    dim=(1, 2, 3)
                ),
                "expert_target_projection_fraction": (
                    projected != original
                ).float().mean(dim=(1, 2)),
                "pre_squash_abs_u_mean": absolute_u.mean(dim=1),
                "pre_squash_abs_u_q95": torch.quantile(
                    absolute_u, 0.95, dim=1
                ),
                "pre_squash_abs_u_q99": torch.quantile(
                    absolute_u, 0.99, dim=1
                ),
                "pre_squash_abs_u_max": absolute_u.max(dim=1).values,
            }
            for margin in spec.NEAR_BOUNDARY_MARGINS:
                suffix = scientific_label(margin)
                values[f"near_{suffix}_fraction"] = (
                    ((1.0 - torch.abs(raw_active)) / 2.0) <= margin
                ).float().mean(dim=(1, 2, 3))
                values[f"expert_near_{suffix}_fraction"] = (
                    ((1.0 - torch.abs(projected)) / 2.0) <= margin
                ).float().mean(dim=(1, 2))
            for threshold in spec.JACOBIAN_THRESHOLDS:
                suffix = scientific_label(threshold)
                values[f"jacobian_below_{suffix}_fraction"] = (
                    generated_jacobian < threshold
                ).float().mean(dim=(1, 2, 3))
                values[f"expert_jacobian_below_{suffix}_fraction"] = (
                    expert_jacobian < threshold
                ).float().mean(dim=(1, 2))
            for name, value in values.items():
                metrics[name][positions] = value.double().cpu().numpy()
            metrics["minimum_unique_candidates"][positions] = unique
            metrics["proposal_seconds_per_row"][positions] = proposal_seconds / len(rows)
            metrics["lewm_seconds_per_row"][positions] = lewm_seconds / len(rows)
            metrics["total_seconds_per_row"][positions] = (
                proposal_seconds + lewm_seconds
            ) / len(rows)
            if args.condition == "direct_gmm":
                prior = extras["prior_probability"].double().cpu().numpy()
                posterior = extras["posterior_probability"].double().cpu().numpy()
                modes = extras["sampled_modes"].numpy()
                sampled = np.stack(
                    [
                        np.bincount(row, minlength=spec.GMM_MODES)
                        / spec.CANDIDATE_COUNT
                        for row in modes
                    ]
                )
                entropy = -np.sum(prior * np.log(np.maximum(prior, 1.0e-300)), axis=1)
                gmm_arrays["prior_probability"][positions] = prior
                gmm_arrays["posterior_probability"][positions] = posterior
                gmm_arrays["sampled_mode_fraction"][positions] = sampled
                gmm_arrays["normalized_prior_entropy"][positions] = entropy / math.log(
                    spec.GMM_MODES
                )
                gmm_arrays["effective_prior_modes"][positions] = np.exp(entropy)

    if any(not np.isfinite(value).all() for value in metrics.values()) or any(
        not np.isfinite(value).all() for value in gmm_arrays.values()
    ):
        raise RuntimeError("E15 offline evaluation contains missing metrics")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "metrics.h5"
    partial = metrics_path.with_name(f".{metrics_path.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as handle:
            handle.create_dataset("cache_row", data=evaluation_rows, compression="lzf")
            handle.create_dataset(
                "episode_idx", data=store.episode[evaluation_rows], compression="lzf"
            )
            handle.create_dataset(
                "delta", data=store.delta[evaluation_rows], compression="lzf"
            )
            handle.create_dataset("tau", data=store.tau[evaluation_rows], compression="lzf")
            group = handle.create_group("metrics")
            for name, value in metrics.items():
                group.create_dataset(name, data=value, compression="lzf")
            if gmm_arrays:
                gmm = handle.create_group("gmm")
                for name, value in gmm_arrays.items():
                    gmm.create_dataset(name, data=value, compression="lzf")
            handle.attrs["mode"] = args.mode
            handle.attrs["task"] = args.task
            handle.attrs["condition"] = args.condition
            handle.attrs["seed"] = args.seed
            handle.attrs["protocol_sha256"] = spec.PROTOCOL_SHA256
        os.replace(partial, metrics_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e15_offline_proposer_evaluation",
        "analysis_role": analysis_role,
        "mode": args.mode,
        "task": args.task,
        "condition": args.condition,
        "seed": args.seed,
        "row_count": len(evaluation_rows),
        "candidate_count": spec.CANDIDATE_COUNT,
        "batch_size": spec.OFFLINE_BATCH_SIZE,
        "model": model_record,
        "lineage": store.lineage,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "metrics_h5": str(metrics_path),
        "metrics_h5_sha256": sha256_file(metrics_path),
        "evaluation_rows_sha256": array_sha256(evaluation_rows),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "training_source_manifest_sha256": TRAINING_SOURCE_MANIFEST_SHA256,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "h5py": metadata.version("h5py"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
        },
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, summary)
    atomic_text(
        args.output_dir / "sha256.txt",
        f"{sha256_file(metrics_path)}  metrics.h5\n"
        f"{sha256_file(summary_path)}  summary.json\n",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
