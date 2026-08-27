#!/usr/bin/env python3
"""Replay exact E15 VAD banks and emit frozen E16 candidate-rank diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

import gdp_cem_e15_specs as e15
import gdp_cem_e16_specs as spec
from acid_alternative.io_utils import resolve_policy_checkpoint
from evaluate_gdp_cem_e15_offline import load_model, reject_protected_path
from gdp_cem_e15_data import E15ArrayStore, sha256_file
from gdp_cem_e15_models import (
    CosineSchedule,
    VariableVelocityDiffusion,
    action_active_mask,
    bounded_actions_from_standardized_u,
    velocity_ddim_sample,
)
from gdp_cem_latent_rollout import rollout_from_single_latent


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
        value = value.detach().cpu().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def pearson_rows(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.shape != y.shape or x.ndim != 2:
        raise ValueError("invalid E16 correlation arrays")
    x = x - x.mean(axis=1, keepdims=True)
    y = y - y.mean(axis=1, keepdims=True)
    denominator = np.sqrt(np.square(x).sum(axis=1) * np.square(y).sum(axis=1))
    return np.divide(
        (x * y).sum(axis=1),
        denominator,
        out=np.zeros(len(x), dtype=np.float64),
        where=denominator > 0,
    )


def ordinal_rank_rows(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value)
    if value.ndim != 2:
        raise ValueError("invalid E16 rank array")
    order = np.argsort(value, axis=1, kind="stable")
    rank = np.empty_like(order)
    rows = np.arange(len(value))[:, None]
    rank[rows, order] = np.arange(value.shape[1])[None]
    return rank


def candidate_rank_metrics(
    far_cost: np.ndarray,
    local_cost: np.ndarray,
    *,
    top_k: tuple[int, ...] = spec.TOP_K,
) -> dict[str, np.ndarray]:
    far_cost = np.asarray(far_cost, dtype=np.float64)
    local_cost = np.asarray(local_cost, dtype=np.float64)
    if (
        far_cost.shape != local_cost.shape
        or far_cost.ndim != 2
        or not np.isfinite(far_cost).all()
        or not np.isfinite(local_cost).all()
        or any(not 0 < value <= far_cost.shape[1] for value in top_k)
    ):
        raise ValueError("invalid E16 candidate costs")
    far_order = np.argsort(far_cost, axis=1, kind="stable")
    local_oracle = np.argmin(local_cost, axis=1)
    far_rank = ordinal_rank_rows(far_cost)
    result: dict[str, np.ndarray] = {
        "pearson_far_vs_local": pearson_rows(far_cost, local_cost),
        "spearman_far_vs_local": pearson_rows(
            ordinal_rank_rows(far_cost), ordinal_rank_rows(local_cost)
        ),
        "local_oracle_far_rank": far_rank[np.arange(len(far_cost)), local_oracle]
        + 1,
        "local_oracle_cost": local_cost[np.arange(len(local_cost)), local_oracle],
    }
    for count in top_k:
        candidates = far_order[:, :count]
        values = np.take_along_axis(local_cost, candidates, axis=1)
        best = values.min(axis=1)
        result[f"top_{count}_local_cost"] = best
        result[f"top_{count}_local_regret"] = best - result["local_oracle_cost"]
        result[f"top_{count}_contains_local_oracle"] = np.any(
            candidates == local_oracle[:, None], axis=1
        )
    return result


def verify_e15_result(directory: Path, *, task: str) -> tuple[Path, dict[str, Any]]:
    checksum_path = directory / "sha256.txt"
    summary_path = directory / "summary.json"
    metrics_path = directory / "metrics.h5"
    if not all(path.is_file() for path in (checksum_path, summary_path, metrics_path)):
        raise FileNotFoundError("incomplete frozen E15 result directory")
    records: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        records[name.lstrip("*")] = digest
    if records.get("summary.json") != sha256_file(summary_path) or records.get(
        "metrics.h5"
    ) != sha256_file(metrics_path):
        raise RuntimeError("E15 result checksum differs")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("mode") != "full"
        or summary.get("task") != task
        or summary.get("condition") != "vad"
        or int(summary.get("seed", -1)) != spec.DIAGNOSTIC_MODEL_SEED
        or int(summary.get("candidate_count", -1)) != e15.CANDIDATE_COUNT
        or summary.get("protocol_sha256") != spec.E15_PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != spec.E15_OFFLINE_SOURCE_MANIFEST_SHA256
        or summary.get("metrics_h5_sha256") != sha256_file(metrics_path)
    ):
        raise RuntimeError("frozen E15 result identity differs")
    return metrics_path, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--training-dir", type=Path, required=True)
    parser.add_argument("--e15-result-dir", type=Path, required=True)
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
    required = (
        args.training_dir,
        args.e15_result_dir,
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
        raise RuntimeError("E16 diagnostic protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E16 exact-bank output")
    if not torch.cuda.is_available():
        raise RuntimeError("E16 exact-bank diagnostic requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E16 exact-bank GPU model differs")
    task_spec = e15.TASK_SPEC[args.task]
    if (
        args.world_model_policy != task_spec["world_model_policy"]
        or sha256_file(args.world_model_checkpoint)
        != task_spec["world_model_sha256"]
        or resolve_policy_checkpoint(
            args.world_model_policy, args.stablewm_home
        ).resolve()
        != args.world_model_checkpoint.resolve()
    ):
        raise RuntimeError("E16 released world-model identity differs")
    e15_metrics_path, e15_summary = verify_e15_result(
        args.e15_result_dir, task=args.task
    )

    torch.manual_seed(1616)
    np.random.seed(1616)
    torch.cuda.manual_seed_all(1616)
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
        condition="vad",
        seed=spec.DIAGNOSTIC_MODEL_SEED,
        store=store,
        device=device,
    )
    if not isinstance(model, VariableVelocityDiffusion):
        raise RuntimeError("E16 exact-bank model type differs")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    schedule = CosineSchedule.build(e15.DIFFUSION_STEPS)
    generator = torch.Generator(device=device).manual_seed(
        e15.derived_seed(
            f"offline-gpu|task={args.task}|condition=vad|seed={spec.DIAGNOSTIC_MODEL_SEED}"
        )
    )
    evaluation_rows = store.validation_rows
    row_to_position = np.full(len(store.role), -1, dtype=np.int64)
    row_to_position[evaluation_rows] = np.arange(len(evaluation_rows))
    with h5py.File(e15_metrics_path, "r") as handle:
        reference_rows = np.asarray(handle["cache_row"][:], dtype=np.int64)
        reference_far = np.asarray(
            handle["metrics/selected_far_goal_lewm_cost"][:], dtype=np.float64
        )
        reference_local = np.asarray(
            handle["metrics/selected_true_local_lewm_cost"][:], dtype=np.float64
        )
    if not np.array_equal(reference_rows, evaluation_rows):
        raise RuntimeError("E16 exact replay row identity differs")

    metric_names = (
        "pearson_far_vs_local",
        "spearman_far_vs_local",
        "local_oracle_far_rank",
        "local_oracle_cost",
        *(f"top_{count}_local_cost" for count in spec.TOP_K),
        *(f"top_{count}_local_regret" for count in spec.TOP_K),
        *(f"top_{count}_contains_local_oracle" for count in spec.TOP_K),
        "standard_selected_far_cost",
        "standard_selected_local_cost",
        "standard_oracle_action_mse",
        "mixed_selected_far_cost",
        "mixed_selected_local_cost",
        "mixed_oracle_action_mse",
    )
    metrics = {
        name: np.full(len(evaluation_rows), np.nan, dtype=np.float64)
        for name in metric_names
    }
    u_mean = torch.from_numpy(store.u_mean).to(device)
    u_std = torch.from_numpy(store.u_std).to(device)
    planner_mean = torch.from_numpy(store.planner_action_mean).to(device)
    planner_std = torch.from_numpy(store.planner_action_std).to(device)
    latent_mean = torch.from_numpy(store.latent_mean).to(device)
    latent_std = torch.from_numpy(store.latent_std).to(device)
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    for delta_value, tau_value in e15.DELTA_TAU_PAIRS:
        cell_rows = evaluation_rows[
            (store.delta[evaluation_rows] == delta_value)
            & (store.tau[evaluation_rows] == tau_value)
        ]
        for start in range(0, len(cell_rows), e15.OFFLINE_BATCH_SIZE):
            rows = cell_rows[start : start + e15.OFFLINE_BATCH_SIZE]
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
            flat_mask = active.reshape(len(rows), -1)
            noise = torch.randn(
                len(rows),
                e15.CANDIDATE_COUNT,
                flat_mask.shape[1],
                device=device,
                generator=generator,
            ) * flat_mask[:, None]
            standard_flat = velocity_ddim_sample(
                model,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                initial_noise=noise,
                active_mask=flat_mask,
                schedule=schedule,
                evaluations=e15.DIFFUSION_EVALUATIONS,
                guidance_scale=spec.STANDARD_GUIDANCE,
            )
            low_flat = velocity_ddim_sample(
                model,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                initial_noise=noise,
                active_mask=flat_mask,
                schedule=schedule,
                evaluations=e15.DIFFUSION_EVALUATIONS,
                guidance_scale=spec.LOW_GUIDANCE,
            )
            shape = (
                len(rows),
                e15.CANDIDATE_COUNT,
                e15.ACTION_HORIZON,
                store.primitive_action_dim,
            )
            standard_u = standard_flat.reshape(shape)
            low_u = low_flat.reshape(shape)
            mixed_u = torch.cat(
                (
                    standard_u[:, : spec.MIX_STANDARD_COUNT],
                    low_u[:, spec.MIX_STANDARD_COUNT :],
                ),
                dim=1,
            )
            standard_raw, standard_planner, _ = bounded_actions_from_standardized_u(
                standard_u,
                u_mean=u_mean,
                u_std=u_std,
                planner_mean=planner_mean,
                planner_std=planner_std,
                interior_scale=store.interior_scale,
                active_mask=active,
            )
            mixed_raw, mixed_planner, _ = bounded_actions_from_standardized_u(
                mixed_u,
                u_mean=u_mean,
                u_std=u_std,
                planner_mean=planner_mean,
                planner_std=planner_std,
                interior_scale=store.interior_scale,
                active_mask=active,
            )
            current_raw = current * latent_std + latent_mean
            local_raw = local * latent_std + latent_mean
            goal_raw = goal * latent_std + latent_mean

            def rollout(planner: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
                macro = planner[:, :, :tau_value].reshape(
                    len(rows),
                    e15.CANDIDATE_COUNT,
                    tau_value // e15.ACTION_BLOCK,
                    e15.ACTION_BLOCK * store.primitive_action_dim,
                )
                terminal = rollout_from_single_latent(
                    world_model, current=current_raw, macro_actions=macro
                )[:, :, -1]
                return (
                    (terminal - goal_raw[:, None]).square().sum(dim=-1),
                    (terminal - local_raw[:, None]).square().sum(dim=-1),
                )

            standard_far, standard_local = rollout(standard_planner)
            mixed_far, mixed_local = rollout(mixed_planner)
            rank = candidate_rank_metrics(
                standard_far.double().cpu().numpy(),
                standard_local.double().cpu().numpy(),
            )
            for name, value in rank.items():
                metrics[name][positions] = value.astype(np.float64)
            batch_index = torch.arange(len(rows), device=device)
            standard_best = standard_far.argmin(dim=1)
            mixed_best = mixed_far.argmin(dim=1)
            projected = batch.action_raw_projected[:, :tau_value].to(device)
            standard_action_mse = (
                standard_raw[:, :, :tau_value] - projected[:, None]
            ).square().mean(dim=(-1, -2)).min(dim=1).values
            mixed_action_mse = (
                mixed_raw[:, :, :tau_value] - projected[:, None]
            ).square().mean(dim=(-1, -2)).min(dim=1).values
            batch_values = {
                "standard_selected_far_cost": standard_far[
                    batch_index, standard_best
                ],
                "standard_selected_local_cost": standard_local[
                    batch_index, standard_best
                ],
                "standard_oracle_action_mse": standard_action_mse,
                "mixed_selected_far_cost": mixed_far[batch_index, mixed_best],
                "mixed_selected_local_cost": mixed_local[batch_index, mixed_best],
                "mixed_oracle_action_mse": mixed_action_mse,
            }
            for name, value in batch_values.items():
                metrics[name][positions] = value.double().cpu().numpy()

    if any(not np.isfinite(value).all() for value in metrics.values()):
        raise RuntimeError("E16 exact-bank diagnostic contains missing metrics")
    far_error = np.abs(metrics["standard_selected_far_cost"] - reference_far)
    local_error = np.abs(metrics["standard_selected_local_cost"] - reference_local)
    replay_passed = bool(
        float(far_error.max()) <= spec.REPLAY_ABSOLUTE_TOLERANCE
        and float(local_error.max()) <= spec.REPLAY_ABSOLUTE_TOLERANCE
    )
    if not replay_passed:
        raise RuntimeError(
            "E16 exact-bank replay failed: "
            f"far={far_error.max():.9g} local={local_error.max():.9g}"
        )

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
            handle.create_dataset(
                "tau", data=store.tau[evaluation_rows], compression="lzf"
            )
            group = handle.create_group("metrics")
            for name, value in metrics.items():
                group.create_dataset(name, data=value, compression="lzf")
            handle.attrs["task"] = args.task
            handle.attrs["model_seed"] = spec.DIAGNOSTIC_MODEL_SEED
            handle.attrs["protocol_sha256"] = spec.PROTOCOL_SHA256
        os.replace(partial, metrics_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e16_exact_e15_bank_ranking_diagnostic",
        "analysis_role": "outcome_informed_P1_validation_diagnostic",
        "task": args.task,
        "model_seed": spec.DIAGNOSTIC_MODEL_SEED,
        "row_count": len(evaluation_rows),
        "candidate_count": e15.CANDIDATE_COUNT,
        "top_k": list(spec.TOP_K),
        "standard_guidance": spec.STANDARD_GUIDANCE,
        "low_guidance": spec.LOW_GUIDANCE,
        "mixture_counts": [spec.MIX_STANDARD_COUNT, spec.MIX_LOW_COUNT],
        "exact_e15_replay": {
            "passed": replay_passed,
            "absolute_tolerance": spec.REPLAY_ABSOLUTE_TOLERANCE,
            "maximum_far_cost_absolute_error": float(far_error.max()),
            "maximum_local_cost_absolute_error": float(local_error.max()),
            "reference_summary_sha256": sha256_file(
                args.e15_result_dir / "summary.json"
            ),
            "reference_metrics_sha256": sha256_file(e15_metrics_path),
            "reference_source_manifest_sha256": e15_summary[
                "source_manifest_sha256"
            ],
        },
        "model": model_record,
        "lineage": store.lineage,
        "metrics_h5": str(metrics_path),
        "metrics_h5_sha256": sha256_file(metrics_path),
        "evaluation_rows_sha256": array_sha256(evaluation_rows),
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "runtime": {
            "python": platform.python_version(),
            "torch": metadata.version("torch"),
            "numpy": metadata.version("numpy"),
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
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
    (args.output_dir / "sha256.txt").write_text(
        f"{sha256_file(metrics_path)}  metrics.h5\n"
        f"{sha256_file(summary_path)}  summary.json\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
