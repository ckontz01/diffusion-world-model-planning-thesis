#!/usr/bin/env python3
"""Run a paired flat Le-WM/PLDM arm on a frozen start/goal manifest."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import hydra
import numpy as np
import stable_pretraining as spt
import stable_worldmodel as swm
import torch
from omegaconf import OmegaConf
from sklearn import preprocessing
from torchvision.transforms import v2 as transforms

from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)
from acid_alternative.models import model_from_config


def image_transform(image_size: int):
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=image_size),
        ]
    )


def read_eval_manifest(path: Path, goal_offset: int) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"eval_index", "episode_id", "start_step", "declared_goal_offset"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("invalid evaluation manifest")
    if [int(row["eval_index"]) for row in rows] != list(range(len(rows))):
        raise ValueError("evaluation indices are not contiguous")
    if any(int(row["declared_goal_offset"]) != goal_offset for row in rows):
        raise ValueError("manifest goal offset differs from evaluation configuration")
    pairs = [(int(row["episode_id"]), int(row["start_step"])) for row in rows]
    if len(pairs) != len(set(pairs)):
        raise ValueError("evaluation manifest contains duplicate starts")
    return rows


def load_scorer(path: Path, arm: str, device: torch.device):
    payload = torch.load(path, map_location="cpu", weights_only=False)
    expected_name = {
        "acid": "acid",
        "diffusion": "diffusion",
        "forward": "forward",
        "reachability": "reachability",
    }[arm]
    if payload.get("model_name") != expected_name:
        raise RuntimeError(
            f"checkpoint model {payload.get('model_name')} does not match arm {arm}"
        )
    model = model_from_config(payload["model_config"])
    model.load_state_dict(payload["state_dict"], strict=True)
    model = model.to(device).eval()
    model.requires_grad_(False)
    return model, payload


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if torch.is_tensor(value):
        return value.detach().cpu().tolist()
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--arm",
        choices=("b0", "acid", "diffusion", "forward", "reachability"),
        required=True,
    )
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
    parser.add_argument("--confirmation-authorization", type=Path)
    parser.add_argument("--scorer-checkpoint", type=Path)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--planner-seed", type=int, required=True)
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
    parser.add_argument("--save-video", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    required_paths = [
        args.code_root,
        args.dataset,
        args.world_model_checkpoint,
        args.source_manifest,
        args.eval_manifest,
    ]
    if args.confirmation_authorization is not None:
        required_paths.append(args.confirmation_authorization)
    if args.arm != "b0":
        if args.scorer_checkpoint is None:
            raise ValueError("learned arms require a scorer checkpoint")
        required_paths.append(args.scorer_checkpoint)
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(path)
    if args.arm == "b0" and args.scorer_checkpoint is not None:
        raise ValueError("B0 must not receive a scorer checkpoint")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing a nonempty output directory")
    if args.cem_topk > args.cem_samples:
        raise ValueError("CEM top-k exceeds population")
    if args.horizon * args.action_block > args.eval_budget:
        raise ValueError("planning horizon exceeds evaluation budget")
    rows = read_eval_manifest(args.eval_manifest, args.goal_offset)
    torch.manual_seed(args.planner_seed)
    np.random.seed(args.planner_seed)
    torch.cuda.manual_seed_all(args.planner_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("matched evaluation requires CUDA")

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.eval_config_name)
    cfg.world.num_envs = len(rows)
    cfg.world.max_episode_steps = 2 * args.eval_budget
    cfg.eval.num_eval = len(rows)
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
        raise RuntimeError(
            f"dataset-name resolved to {dataset.h5_path}, not declared {args.dataset}"
        )
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

    resolved_checkpoint = resolve_policy_checkpoint(
        args.world_model_policy, args.stablewm_home
    )
    if resolved_checkpoint != args.world_model_checkpoint.resolve():
        raise RuntimeError(
            f"policy resolves to {resolved_checkpoint}, not declared "
            f"{args.world_model_checkpoint.resolve()}"
        )
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    )
    world_model = world_model.to(device).eval()
    world_model.requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    scorer = None
    scorer_payload = None
    action_standardization_check = None
    wrapper_kwargs: dict[str, Any] = {}
    if args.arm != "b0":
        assert args.scorer_checkpoint is not None
        scorer, scorer_payload = load_scorer(args.scorer_checkpoint, args.arm, device)
        wrapper_kwargs.update(
            noise_seed=int(scorer_payload["seed"]),
            use_action_condition=scorer_payload.get("condition") != "action_ablated",
        )
        if args.arm in ("diffusion", "forward"):
            wrapper_kwargs.update(
                latent_mean=scorer_payload["latent_mean"],
                latent_std=scorer_payload["latent_std"],
            )
        if args.arm == "acid":
            wrapper_kwargs.update(
                action_mean=scorer_payload["acid_action_mean"],
                action_std=scorer_payload["acid_action_std"],
            )
        action_processor = process.get("action")
        if action_processor is None:
            raise RuntimeError("evaluation has no action standardizer")
        expected_mean = np.asarray(
            scorer_payload["planner_primitive_action_mean"], dtype=np.float64
        )
        expected_std = np.asarray(
            scorer_payload["planner_primitive_action_std"], dtype=np.float64
        )
        action_standardization_check = validate_planner_action_standardizer(
            dataset.get_col_data("action"),
            action_processor.mean_,
            action_processor.scale_,
            expected_mean,
            expected_std,
        )
    sigmas = tuple(args.diffusion_sigma or (0.10, 0.25, 0.50))
    cost_model = SharedRolloutCostModel(
        world_model,
        arm=args.arm,
        scorer=scorer,
        lambda_weight=args.lambda_weight,
        horizon=args.horizon,
        diffusion_sigmas=sigmas,
        record_diagnostics=True,
        **wrapper_kwargs,
    ).to(device)
    plan_config = swm.PlanConfig(
        horizon=args.horizon,
        receding_horizon=args.receding_horizon,
        action_block=args.action_block,
    )
    solver = swm.solver.CEMSolver(
        model=cost_model,
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
        config=plan_config,
        process=process,
        transform=transform,
    )
    world.set_policy(policy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    resolved_config = {
        "arm": args.arm,
        "planner_seed": args.planner_seed,
        "lambda_weight": args.lambda_weight,
        "goal_offset": args.goal_offset,
        "eval_budget": args.eval_budget,
        "horizon": args.horizon,
        "receding_horizon": args.receding_horizon,
        "action_block": args.action_block,
        "cem_samples": args.cem_samples,
        "cem_steps": args.cem_steps,
        "cem_topk": args.cem_topk,
        "diffusion_sigmas": list(sigmas),
        "scorer_condition": scorer_payload.get("condition") if scorer_payload else None,
        "planner_action_standardization": action_standardization_check,
        "world": OmegaConf.to_container(cfg.world, resolve=True),
        "callables": OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
    }
    atomic_write_json(args.output_dir / "resolved-config.json", resolved_config)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.time()
    metrics = world.evaluate_from_dataset(
        dataset=dataset,
        episodes_idx=[int(row["episode_id"]) for row in rows],
        start_steps=[int(row["start_step"]) for row in rows],
        goal_offset_steps=args.goal_offset,
        eval_budget=args.eval_budget,
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        save_video=args.save_video,
        video_path=args.output_dir / "videos",
    )
    torch.cuda.synchronize()
    elapsed = time.time() - started
    peak_allocated_bytes = int(torch.cuda.max_memory_allocated(device))
    peak_reserved_bytes = int(torch.cuda.max_memory_reserved(device))
    successes = np.asarray(metrics["episode_successes"], dtype=bool)
    episode_path = args.output_dir / "episodes.tsv"
    with episode_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "eval_index",
                "episode_id",
                "start_step",
                "planner_seed",
                "arm",
                "success",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for row, success in zip(rows, successes.tolist()):
            writer.writerow(
                {
                    "eval_index": row["eval_index"],
                    "episode_id": row["episode_id"],
                    "start_step": row["start_step"],
                    "planner_seed": args.planner_seed,
                    "arm": args.arm,
                    "success": int(success),
                }
            )
    diagnostics_path = args.output_dir / "cem-diagnostics.jsonl"
    with diagnostics_path.open("w", encoding="utf-8") as stream:
        for record in cost_model.diagnostic_history:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    summary = {
        "status": "ok",
        "kind": "matched_flat_closed_loop_evaluation",
        "arm": args.arm,
        "metrics": jsonable(metrics),
        "success_count": int(successes.sum()),
        "episode_count": len(successes),
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "eval_manifest": str(args.eval_manifest),
        "eval_manifest_sha256": sha256_file(args.eval_manifest),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "resolved_world_model_checkpoint": str(resolved_checkpoint),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "confirmation_authorization": (
            str(args.confirmation_authorization)
            if args.confirmation_authorization
            else None
        ),
        "confirmation_authorization_sha256": (
            sha256_file(args.confirmation_authorization)
            if args.confirmation_authorization
            else None
        ),
        "scorer_checkpoint": str(args.scorer_checkpoint)
        if args.scorer_checkpoint
        else None,
        "scorer_checkpoint_sha256": (
            sha256_file(args.scorer_checkpoint) if args.scorer_checkpoint else None
        ),
        "scorer_training_seed": scorer_payload.get("seed") if scorer_payload else None,
        "planner_action_standardization": action_standardization_check,
        "planner_seed": args.planner_seed,
        "resolved_config": resolved_config,
        "episode_tsv": str(episode_path),
        "episode_tsv_sha256": sha256_file(episode_path),
        "cem_diagnostics": str(diagnostics_path),
        "cem_diagnostics_sha256": sha256_file(diagnostics_path),
        "cem_cost_calls": len(cost_model.diagnostic_history),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": peak_allocated_bytes,
            "peak_cuda_memory_reserved_bytes": peak_reserved_bytes,
        },
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
