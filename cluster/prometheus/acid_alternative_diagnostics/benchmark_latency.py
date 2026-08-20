#!/usr/bin/env python3
"""CUDA-event latency benchmark for matched B0 and learned planner arms."""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import time
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
import stable_worldmodel as swm
import torch
from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.evaluate_matched import load_scorer
from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)
from gymnasium.spaces import Box

from acid_alternative_diagnostics.score_candidate_pools import (
    expand_pool_tensor,
    parse_scorer_spec,
    score_raw,
)


def latency_summary(milliseconds: list[float]) -> dict[str, Any]:
    values = np.asarray(milliseconds, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.isfinite(values).all():
        raise ValueError("latencies must be a nonempty finite vector")
    if np.any(values < 0):
        raise ValueError("latencies must be nonnegative")
    q25, median, q75, p95 = np.quantile(values, (0.25, 0.50, 0.75, 0.95))
    return {
        "calls": int(values.size),
        "median_ms": float(median),
        "q25_ms": float(q25),
        "q75_ms": float(q75),
        "iqr_ms": float(q75 - q25),
        "p95_ms": float(p95),
        "minimum_ms": float(values.min()),
        "maximum_ms": float(values.max()),
    }


def measure_cuda(
    function: Callable[[], Any], *, warmup: int, repetitions: int
) -> tuple[dict[str, Any], Any]:
    if warmup < 0 or repetitions <= 0:
        raise ValueError("invalid timing repetition counts")
    result = None
    for _ in range(warmup):
        result = function()
    torch.cuda.synchronize()
    measurements: list[float] = []
    for _ in range(repetitions):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        result = function()
        end.record()
        end.synchronize()
        measurements.append(float(start.elapsed_time(end)))
    return latency_summary(measurements), result


def single_pool_info(
    info_tensors: dict[str, torch.Tensor], pool: int, device: torch.device
) -> dict[str, torch.Tensor]:
    return {
        key: value[pool].unsqueeze(0).to(device) for key, value in info_tensors.items()
    }


def expanded_pool_info(
    info_tensors: dict[str, torch.Tensor],
    pool: int,
    count: int,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    return {
        key: expand_pool_tensor(value[pool], count, device)
        for key, value in info_tensors.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-artifact", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--lambda-weight", type=float, default=0.07)
    parser.add_argument("--diffusion-sigma", type=float, action="append")
    parser.add_argument(
        "--scorer", type=parse_scorer_spec, action="append", required=True
    )
    parser.add_argument("--pool-index", type=int, default=0)
    parser.add_argument("--warmup-calls", type=int, default=20)
    parser.add_argument("--measured-calls", type=int, default=100)
    parser.add_argument("--full-solve-warmups", type=int, default=1)
    parser.add_argument("--full-solve-repetitions", type=int, default=10)
    parser.add_argument("--cem-samples", type=int, default=300)
    parser.add_argument("--cem-steps", type=int, default=30)
    parser.add_argument("--cem-topk", type=int, default=30)
    parser.add_argument("--planner-seed", type=int, default=7101)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.candidate_artifact,
        args.candidate_manifest,
        args.world_model_checkpoint,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    for _, _, checkpoint in args.scorer:
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if args.cem_topk > args.cem_samples:
        raise ValueError("CEM top-k exceeds population")
    labels = [label for label, _, _ in args.scorer]
    if len(labels) != len(set(labels)):
        raise ValueError("scorer labels must be unique")

    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    if candidate_manifest.get("status") != "ok" or sha256_file(
        args.candidate_artifact
    ) != candidate_manifest.get("artifact_sha256"):
        raise RuntimeError("candidate artifact does not match its manifest")
    capture = torch.load(
        args.candidate_artifact, map_location="cpu", weights_only=False
    )
    if capture.get("kind") != "flat_b0_final_cem_candidate_pools":
        raise RuntimeError("unexpected candidate artifact kind")
    candidates = torch.as_tensor(capture["candidates"]).float()
    info_tensors = capture["info_tensors"]
    if candidates.ndim != 4:
        raise RuntimeError("invalid candidate tensor")
    pool_count, captured_samples, horizon, flat_action_dim = candidates.shape
    if not 0 <= args.pool_index < pool_count:
        raise ValueError("pool index is outside captured artifact")
    if captured_samples != args.cem_samples:
        raise RuntimeError("captured population differs from requested CEM samples")

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("latency benchmark requires CUDA")
    device = torch.device("cuda")
    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("resolved world-model checkpoint differs from declaration")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    )
    world_model = world_model.to(device).eval()
    world_model.requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    pool_candidates = candidates[args.pool_index].unsqueeze(0).to(device)
    expanded_info = expanded_pool_info(
        info_tensors, args.pool_index, args.cem_samples, device
    )
    solver_info = single_pool_info(info_tensors, args.pool_index, device)
    sigmas = tuple(args.diffusion_sigma or (0.10, 0.25, 0.50))
    declarations: list[tuple[str, str, Path | None]] = [("b0", "b0", None)]
    declarations.extend(args.scorer)
    results: dict[str, Any] = {}
    started = time.time()

    for label, arm, checkpoint in declarations:
        scorer = None
        payload = None
        kwargs: dict[str, Any] = {}
        if checkpoint is not None:
            scorer, payload = load_scorer(checkpoint, arm, device)
            kwargs.update(
                noise_seed=int(payload["seed"]),
                use_action_condition=payload.get("condition") != "action_ablated",
            )
            if arm in ("diffusion", "forward"):
                kwargs.update(
                    latent_mean=payload["latent_mean"],
                    latent_std=payload["latent_std"],
                )
            if arm == "acid":
                kwargs.update(
                    action_mean=payload["acid_action_mean"],
                    action_std=payload["acid_action_std"],
                )
        wrapper = SharedRolloutCostModel(
            world_model,
            arm=arm,
            scorer=scorer,
            lambda_weight=args.lambda_weight,
            horizon=horizon,
            diffusion_sigmas=sigmas,
            record_diagnostics=False,
            **kwargs,
        ).to(device)
        torch.cuda.reset_peak_memory_stats(device)

        rollout_latency, rollout_result = measure_cuda(
            lambda wrapper=wrapper: wrapper._rollout_once(
                expanded_info, pool_candidates
            ),
            warmup=args.warmup_calls,
            repetitions=args.measured_calls,
        )
        _goal_cost, trajectory, actions, goal_embedding = rollout_result
        if arm == "b0":
            verifier_latency = latency_summary([0.0] * args.measured_calls)
        else:
            verifier_latency, _ = measure_cuda(
                lambda wrapper=wrapper, arm=arm, trajectory=trajectory, actions=actions, goal_embedding=goal_embedding: (
                    score_raw(wrapper, arm, trajectory, actions, goal_embedding)
                ),
                warmup=args.warmup_calls,
                repetitions=args.measured_calls,
            )
        total_latency, total_cost = measure_cuda(
            lambda wrapper=wrapper: wrapper.get_cost(expanded_info, pool_candidates),
            warmup=args.warmup_calls,
            repetitions=args.measured_calls,
        )
        if not torch.isfinite(total_cost).all():
            raise RuntimeError(f"{label}: non-finite cost during timing")

        action_block = int(capture["configuration"]["action_block"])
        receding_horizon = int(capture["configuration"]["receding_horizon"])
        primitive_action_dim, remainder = divmod(flat_action_dim, action_block)
        if remainder:
            raise RuntimeError("flat action dimension is incompatible with horizon")
        action_space = Box(
            low=-np.inf,
            high=np.inf,
            shape=(1, primitive_action_dim),
            dtype=np.float32,
        )
        plan_config = swm.PlanConfig(
            horizon=horizon,
            receding_horizon=receding_horizon,
            action_block=action_block,
        )
        solver = swm.solver.CEMSolver(
            model=wrapper,
            batch_size=1,
            num_samples=args.cem_samples,
            var_scale=1.0,
            n_steps=args.cem_steps,
            topk=args.cem_topk,
            device=device,
            seed=args.planner_seed,
        )
        solver.configure(action_space=action_space, n_envs=1, config=plan_config)
        solve_latency, solve_output = measure_cuda(
            lambda solver=solver: solver.solve(solver_info),
            warmup=args.full_solve_warmups,
            repetitions=args.full_solve_repetitions,
        )
        if torch.as_tensor(solve_output["actions"]).shape != (
            1,
            horizon,
            flat_action_dim,
        ):
            raise RuntimeError(f"{label}: released CEM returned unexpected actions")
        results[label] = {
            "arm": arm,
            "condition": payload.get("condition") if payload else None,
            "training_seed": int(payload["seed"]) if payload else None,
            "checkpoint": str(checkpoint) if checkpoint else None,
            "checkpoint_sha256": sha256_file(checkpoint) if checkpoint else None,
            "scorer_parameter_count": (
                sum(parameter.numel() for parameter in scorer.parameters())
                if scorer is not None
                else 0
            ),
            "world_model_rollout": rollout_latency,
            "verifier_only": verifier_latency,
            "total_cost_call": total_latency,
            "full_released_cem_solve": solve_latency,
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
            "peak_cuda_memory_reserved_bytes": int(
                torch.cuda.max_memory_reserved(device)
            ),
        }
        solver = None
        wrapper = None
        scorer = None
        rollout_result = None
        total_cost = None
        solve_output = None
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "ok",
        "kind": "matched_cuda_event_latency_benchmark",
        "timing_scope": (
            "single captured task D1 start; identical candidate/info tensors; "
            "arms measured sequentially on one allocated GPU"
        ),
        "configuration": {
            "pool_index": args.pool_index,
            "warmup_calls": args.warmup_calls,
            "measured_calls": args.measured_calls,
            "full_solve_warmups": args.full_solve_warmups,
            "full_solve_repetitions": args.full_solve_repetitions,
            "cem_samples": args.cem_samples,
            "cem_steps": args.cem_steps,
            "cem_topk": args.cem_topk,
            "horizon": horizon,
            "receding_horizon": receding_horizon,
            "action_block": action_block,
            "flat_action_dim": flat_action_dim,
            "lambda_weight": args.lambda_weight,
            "diffusion_sigmas": list(sigmas),
        },
        "results": results,
        "end_to_end_episode_latency": (
            "reported from matched closed-loop summary elapsed_seconds / episode_count"
        ),
        "candidate_artifact": str(args.candidate_artifact),
        "candidate_artifact_sha256": sha256_file(args.candidate_artifact),
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        },
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
