#!/usr/bin/env python3
"""Measure single-environment end-to-end episode latency on one allocated GPU."""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import hydra
import numpy as np
import stable_worldmodel as swm
import torch
from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.evaluate_matched import (
    image_transform,
    load_scorer,
    read_eval_manifest,
)
from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)
from omegaconf import OmegaConf
from sklearn import preprocessing

from acid_alternative_diagnostics.benchmark_latency import latency_summary
from acid_alternative_diagnostics.score_candidate_pools import parse_scorer_spec


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument(
        "--eval-config-name", choices=("pusht", "reacher", "cube"), required=True
    )
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--planner-seed", type=int, default=7101)
    parser.add_argument("--lambda-weight", type=float, default=0.07)
    parser.add_argument("--goal-offset", type=int, default=25)
    parser.add_argument("--eval-budget", type=int, default=50)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--receding-horizon", type=int, default=5)
    parser.add_argument("--action-block", type=int, default=5)
    parser.add_argument("--cem-samples", type=int, default=300)
    parser.add_argument("--cem-steps", type=int, default=30)
    parser.add_argument("--cem-topk", type=int, default=30)
    parser.add_argument("--diffusion-sigma", type=float, action="append")
    parser.add_argument(
        "--scorer", type=parse_scorer_spec, action="append", required=True
    )
    parser.add_argument("--warmup-episodes", type=int, default=1)
    parser.add_argument("--measured-episodes", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.code_root,
        args.dataset,
        args.world_model_checkpoint,
        args.source_manifest,
        args.eval_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    for _, _, checkpoint in args.scorer:
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if args.warmup_episodes < 0 or args.measured_episodes <= 0:
        raise ValueError("invalid episode repetition counts")
    if args.cem_topk > args.cem_samples:
        raise ValueError("CEM top-k exceeds population")
    labels = [label for label, _, _ in args.scorer]
    if len(labels) != len(set(labels)) or "b0" in labels:
        raise ValueError("scorer labels must be unique and cannot be b0")
    rows = read_eval_manifest(args.eval_manifest, args.goal_offset)
    required_rows = args.warmup_episodes + args.measured_episodes
    if len(rows) < required_rows:
        raise RuntimeError(
            f"latency manifest has {len(rows)} starts, requires {required_rows}"
        )
    latency_rows = rows[:required_rows]

    torch.manual_seed(0)
    np.random.seed(0)
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("episode latency benchmark requires CUDA")
    device = torch.device("cuda")

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.eval_config_name)
    cfg.world.num_envs = 1
    cfg.world.max_episode_steps = 2 * args.eval_budget
    cfg.eval.num_eval = 1
    cfg.eval.goal_offset_steps = args.goal_offset
    cfg.eval.eval_budget = args.eval_budget
    cfg.eval.dataset_name = args.dataset_name
    cfg.plan_config.horizon = args.horizon
    cfg.plan_config.receding_horizon = args.receding_horizon
    cfg.plan_config.action_block = args.action_block

    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        args.dataset_name,
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("dataset name resolves to different bytes")
    transform = {
        "pixels": image_transform(int(cfg.eval.img_size)),
        "goal": image_transform(int(cfg.eval.img_size)),
    }
    process = {}
    for column in cfg.dataset.keys_to_cache:
        if column == "pixels":
            continue
        processor = preprocessing.StandardScaler()
        values = dataset.get_col_data(column)
        values = values[~np.isnan(values).any(axis=1)]
        processor.fit(values)
        process[column] = processor
        if column != "action":
            process[f"goal_{column}"] = processor

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

    sigmas = tuple(args.diffusion_sigma or (0.10, 0.25, 0.50))
    declarations: list[tuple[str, str, Path | None]] = [("b0", "b0", None)]
    declarations.extend(args.scorer)
    results: dict[str, Any] = {}
    callables = OmegaConf.to_container(cfg.eval.get("callables"), resolve=True)
    benchmark_started = time.time()
    try:
        for label, arm, checkpoint in declarations:
            scorer = None
            payload = None
            action_standardization = None
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
                action_processor = process.get("action")
                if action_processor is None:
                    raise RuntimeError("evaluation has no action standardizer")
                expected_mean = np.asarray(
                    payload["planner_primitive_action_mean"], dtype=np.float64
                )
                expected_std = np.asarray(
                    payload["planner_primitive_action_std"], dtype=np.float64
                )
                action_standardization = validate_planner_action_standardizer(
                    dataset.get_col_data("action"),
                    action_processor.mean_,
                    action_processor.scale_,
                    expected_mean,
                    expected_std,
                )
            wrapper = SharedRolloutCostModel(
                world_model,
                arm=arm,
                scorer=scorer,
                lambda_weight=args.lambda_weight,
                horizon=args.horizon,
                diffusion_sigmas=sigmas,
                record_diagnostics=False,
                **kwargs,
            ).to(device)
            torch.cuda.reset_peak_memory_stats(device)
            durations_ms: list[float] = []
            successes: list[bool] = []
            episode_records: list[dict[str, Any]] = []
            for row_index, row in enumerate(latency_rows):
                # Re-create policy and solver so action buffers and warm starts
                # cannot leak between timed episodes. Each arm receives the
                # same solver seed and the same ordered start identities.
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
                policy = swm.policy.WorldModelPolicy(
                    solver=solver,
                    config=swm.PlanConfig(
                        horizon=args.horizon,
                        receding_horizon=args.receding_horizon,
                        action_block=args.action_block,
                    ),
                    process=process,
                    transform=transform,
                )
                world.set_policy(policy)
                torch.cuda.synchronize()
                started = time.perf_counter()
                metrics = world.evaluate_from_dataset(
                    dataset=dataset,
                    episodes_idx=[int(row["episode_id"])],
                    start_steps=[int(row["start_step"])],
                    goal_offset_steps=args.goal_offset,
                    eval_budget=args.eval_budget,
                    callables=callables,
                    save_video=False,
                )
                torch.cuda.synchronize()
                duration_ms = (time.perf_counter() - started) * 1000.0
                success = bool(np.asarray(metrics["episode_successes"])[0])
                measured = row_index >= args.warmup_episodes
                if measured:
                    durations_ms.append(duration_ms)
                    successes.append(success)
                episode_records.append(
                    {
                        "phase": "measured" if measured else "warmup",
                        "eval_index": int(row["eval_index"]),
                        "episode_id": int(row["episode_id"]),
                        "start_step": int(row["start_step"]),
                        "duration_ms": duration_ms,
                        "success_sanity_only": success,
                    }
                )
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
                "planner_action_standardization": action_standardization,
                "end_to_end_episode_wall_clock": latency_summary(durations_ms),
                "episode_records": episode_records,
                "measured_successes_sanity_only": successes,
                "peak_cuda_memory_allocated_bytes": int(
                    torch.cuda.max_memory_allocated(device)
                ),
                "peak_cuda_memory_reserved_bytes": int(
                    torch.cuda.max_memory_reserved(device)
                ),
            }
            world.policy = None
            policy = None
            solver = None
            wrapper = None
            scorer = None
            gc.collect()
            torch.cuda.empty_cache()
    finally:
        world.close()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "ok",
        "kind": "matched_single_environment_episode_latency_benchmark",
        "outcome_role": (
            "latency only; recorded successes are execution sanity checks and "
            "are excluded from efficacy analyses"
        ),
        "timing_scope": (
            "dataset reset, preprocessing, all released CEM replans, environment "
            "steps, and synchronization for one environment"
        ),
        "configuration": {
            "warmup_episodes": args.warmup_episodes,
            "measured_episodes": args.measured_episodes,
            "planner_seed_reinitialized_per_episode": args.planner_seed,
            "goal_offset": args.goal_offset,
            "eval_budget": args.eval_budget,
            "horizon": args.horizon,
            "receding_horizon": args.receding_horizon,
            "action_block": args.action_block,
            "cem_samples": args.cem_samples,
            "cem_steps": args.cem_steps,
            "cem_topk": args.cem_topk,
            "lambda_weight": args.lambda_weight,
            "diffusion_sigmas": list(sigmas),
        },
        "results": results,
        "eval_manifest": str(args.eval_manifest),
        "eval_manifest_sha256": sha256_file(args.eval_manifest),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "elapsed_seconds": time.time() - benchmark_started,
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
