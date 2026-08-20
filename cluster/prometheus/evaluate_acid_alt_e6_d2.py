#!/usr/bin/env python3
"""Run one frozen E6 arm on the already exposed D2 starts."""

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

import acid_alt_d2_models as d2
import acid_alt_e6_quantile_models as e6
import evaluate_acid_alt_e3_d2 as e3
from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.io_utils import atomic_write_json, resolve_policy_checkpoint


TASKS = ("pusht", "reacher", "cube")
SCORER_SEED = 6101
PLANNER_SEED = 8301
EVAL_COUNT = 50
PROTOCOL_SHA256 = "2a7facb513f6fcda8a6d923e736d30820aa59e14735bf621b960756d13e9b196"
E3_SUMMARY_SHA256 = "2a4134b49f770cd3f339d73233183d5bd2013b562aee751abc0e8a744959fdbb"
E5_SUMMARY_SHA256 = "0c956e95e258eeb440bad12e71de3528b317c49c06f50519e5bc110e3c5da553"


def image_transform(image_size: int):
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=image_size),
        ]
    )


def reject_protected_path(path: Path) -> None:
    e3.reject_protected_path(path)


def validate_authorization(
    path: Path, *, protocol: Path, source_manifest: Path
) -> dict[str, Any]:
    reject_protected_path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "authorized_for_exposed_d2_development_only"
        or value.get("kind") != "acid_alt_e6_d2_authorization"
        or value.get("analysis_role")
        != "post_e3_e5_exposed_d2_planner_integration_development"
        or value.get("protocol_sha256") != PROTOCOL_SHA256
        or d2.sha256_file(protocol) != PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != d2.sha256_file(source_manifest)
        or value.get("arms") != list(e6.ARMS)
        or value.get("primary_arm") != e6.PRIMARY_ARM
        or value.get("scorer_seed") != SCORER_SEED
        or value.get("planner_seed") != PLANNER_SEED
        or value.get("e3_summary_sha256") != E3_SUMMARY_SHA256
        or value.get("e5_summary_sha256") != E5_SUMMARY_SHA256
        or value.get("confirmation_claim_allowed") is not False
        or value.get("alternative_to_acid_claim_allowed") is not False
        or value.get("d3_selection_allowed_before_analysis") is not False
        or value.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E6 exposed-D2 authorization is invalid")
    for key, expected in (
        ("e3_summary", E3_SUMMARY_SHA256),
        ("e5_summary", E5_SUMMARY_SHA256),
    ):
        evidence = Path(value[key])
        reject_protected_path(evidence)
        if not evidence.is_file() or d2.sha256_file(evidence) != expected:
            raise RuntimeError(f"E6 prior-result evidence mismatch: {key}")
    return value


def jsonable(value: Any) -> Any:
    return e3.jsonable(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--arm", choices=e6.ARMS, required=True)
    parser.add_argument("--scorer-seed", type=int, required=True)
    parser.add_argument("--planner-seed", type=int, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--trainer-source", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--eval-provenance", type=Path, required=True)
    parser.add_argument("--scorer-checkpoint", type=Path)
    parser.add_argument("--scorer-summary", type=Path)
    parser.add_argument("--save-video", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.scorer_seed != SCORER_SEED or args.planner_seed != PLANNER_SEED:
        raise ValueError("E6 pilot requires the frozen 6101/8301 seed pair")
    spec = e6.arm_spec(args.arm)
    score_arm = str(spec["score_arm"])
    if score_arm == "b0":
        if args.scorer_checkpoint is not None or args.scorer_summary is not None:
            raise ValueError("B0 must not receive a scorer")
    elif score_arm in {"acid", "forward"}:
        if args.scorer_checkpoint is None or args.scorer_summary is not None:
            raise ValueError("core E6 arms require exactly one checkpoint")
    elif score_arm == "rdx":
        if args.scorer_summary is None or args.scorer_checkpoint is not None:
            raise ValueError("RDX E6 arms require exactly one training summary")
    else:
        raise RuntimeError(f"unsupported E6 score family: {score_arm}")

    required = (
        args.protocol,
        args.source_manifest,
        args.authorization,
        args.trainer_source,
        args.code_root,
        args.stablewm_home,
        args.dataset,
        args.world_model_checkpoint,
        args.eval_manifest,
        args.eval_provenance,
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
        reject_protected_path(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E6 evaluation output")
    authorization = validate_authorization(
        args.authorization, protocol=args.protocol, source_manifest=args.source_manifest
    )
    rows = e3.read_d2_manifest(
        args.eval_manifest,
        args.eval_provenance,
        task=args.task,
        dataset=args.dataset,
        source_manifest=args.source_manifest,
    )

    torch.manual_seed(PLANNER_SEED)
    np.random.seed(PLANNER_SEED)
    torch.cuda.manual_seed_all(PLANNER_SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E6 closed-loop evaluation requires CUDA")
    device = torch.device("cuda")

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.task)
    cfg.world.num_envs = EVAL_COUNT
    cfg.world.max_episode_steps = 100
    cfg.eval.num_eval = EVAL_COUNT
    cfg.eval.goal_offset_steps = 25
    cfg.eval.eval_budget = 50
    cfg.eval.dataset_name = args.dataset_name
    cfg.plan_config.horizon = 5
    cfg.plan_config.receding_horizon = 5
    cfg.plan_config.action_block = 5

    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        args.dataset_name,
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("dataset name resolved to a different file")
    transform = {
        "pixels": image_transform(int(cfg.eval.img_size)),
        "goal": image_transform(int(cfg.eval.img_size)),
    }
    process: dict[str, Any] = {}
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
        raise RuntimeError("world-model policy resolves to a different checkpoint")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    scorer = None
    payload = None
    scorer_record: dict[str, Any] | None = None
    if score_arm in {"acid", "forward"}:
        assert args.scorer_checkpoint is not None
        scorer, payload, scorer_record = d2.load_core_scorer(
            args.scorer_checkpoint,
            arm=score_arm,
            expected_seed=SCORER_SEED,
            device=device,
        )
    elif score_arm == "rdx":
        assert args.scorer_summary is not None
        trainer = e3.load_module(
            args.trainer_source,
            d2.V2_TRAINER_SHA256,
            "frozen_e6_residual_diffusion_trainer",
        )
        expected_condition = "shuffled_action" if spec.get("shuffled") else "true"
        scorer, payload, scorer_record = d2.load_residual_model(
            args.scorer_summary,
            expected_condition=expected_condition,
            trainer_module=trainer,
            device=device,
        )
        if int(payload["seed"]) != SCORER_SEED:
            raise RuntimeError("E6 residual scorer seed differs")

    action_standardization = None
    if payload is not None:
        processor = process.get("action")
        if processor is None:
            raise RuntimeError("evaluation has no action standardizer")
        action_standardization = validate_planner_action_standardizer(
            dataset.get_col_data("action"),
            processor.mean_,
            processor.scale_,
            np.asarray(payload["planner_primitive_action_mean"], dtype=np.float64),
            np.asarray(payload["planner_primitive_action_std"], dtype=np.float64),
        )

    cost_model = e6.E6CostModel(
        world_model,
        arm=args.arm,
        task=args.task,
        planner_seed=PLANNER_SEED,
        scorer=scorer,
        payload=payload,
        horizon=5,
        record_diagnostics=True,
    ).to(device)
    solver = swm.solver.CEMSolver(
        model=cost_model,
        batch_size=1,
        num_samples=e6.CEM_SAMPLES,
        var_scale=1.0,
        n_steps=e6.CEM_STEPS,
        topk=e6.CEM_TOPK,
        device=device,
        seed=PLANNER_SEED,
    )
    policy = swm.policy.WorldModelPolicy(
        solver=solver,
        config=swm.PlanConfig(horizon=5, receding_horizon=5, action_block=5),
        process=process,
        transform=transform,
    )
    world.set_policy(policy)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    resolved_config = {
        "task": args.task,
        "arm": args.arm,
        "arm_spec": spec,
        "scorer_seed": SCORER_SEED,
        "planner_seed": PLANNER_SEED,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "cem_samples": e6.CEM_SAMPLES,
        "cem_steps": e6.CEM_STEPS,
        "cem_topk": e6.CEM_TOPK,
        "residual_sigmas": list(d2.SIGMAS),
        "residual_noise_draws": d2.NOISE_DRAWS,
        "continuous_lambda_weight": (
            cost_model.lambda_weight if spec["integration"] == "continuous" else None
        ),
        "action_standardization": action_standardization,
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
        goal_offset_steps=25,
        eval_budget=50,
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        save_video=args.save_video,
        video_path=args.output_dir / "videos",
    )
    torch.cuda.synchronize()
    elapsed = time.time() - started
    successes = np.asarray(metrics["episode_successes"], dtype=bool)
    if successes.shape != (EVAL_COUNT,):
        raise RuntimeError("E6 returned an unexpected episode count")
    if cost_model.call_count <= 0 or cost_model.call_count % e6.CEM_STEPS != 0:
        raise RuntimeError("E6 cost-call count is not a whole number of CEM solves")
    if len(cost_model.diagnostic_history) != cost_model.call_count:
        raise RuntimeError("E6 diagnostic count differs from cost-call count")

    episode_path = args.output_dir / "episodes.tsv"
    with episode_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "eval_index",
                "episode_id",
                "start_step",
                "scorer_seed",
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
                    "scorer_seed": SCORER_SEED,
                    "planner_seed": PLANNER_SEED,
                    "arm": args.arm,
                    "success": int(success),
                }
            )
    diagnostics_path = args.output_dir / "cem-diagnostics.jsonl"
    with diagnostics_path.open("x", encoding="utf-8") as stream:
        for record in cost_model.diagnostic_history:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    summary = {
        "status": "ok",
        "kind": "acid_alt_e6_d2_quantile_closed_loop_evaluation",
        "analysis_role": "post_e3_e5_exposed_d2_planner_integration_development",
        "task": args.task,
        "arm": args.arm,
        "arm_spec": spec,
        "scorer_seed": SCORER_SEED,
        "planner_seed": PLANNER_SEED,
        "metrics": jsonable(metrics),
        "success_count": int(successes.sum()),
        "episode_count": EVAL_COUNT,
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "authorization": str(args.authorization),
        "authorization_sha256": d2.sha256_file(args.authorization),
        "e3_summary_sha256": authorization["e3_summary_sha256"],
        "e5_summary_sha256": authorization["e5_summary_sha256"],
        "eval_manifest": str(args.eval_manifest),
        "eval_manifest_sha256": d2.sha256_file(args.eval_manifest),
        "eval_provenance": str(args.eval_provenance),
        "eval_provenance_sha256": d2.sha256_file(args.eval_provenance),
        "dataset": str(args.dataset),
        "dataset_sha256": d2.sha256_file(args.dataset),
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": d2.sha256_file(args.world_model_checkpoint),
        "resolved_world_model_checkpoint": str(resolved_checkpoint),
        "scorer": scorer_record,
        "resolved_config": resolved_config,
        "episodes_tsv": str(episode_path),
        "episodes_tsv_sha256": d2.sha256_file(episode_path),
        "cem_diagnostics": str(diagnostics_path),
        "cem_diagnostics_sha256": d2.sha256_file(diagnostics_path),
        "cem_cost_calls": cost_model.call_count,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "d3_selected": False,
        "protected_c1_i1_read": False,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
            "peak_cuda_memory_reserved_bytes": int(
                torch.cuda.max_memory_reserved(device)
            ),
        },
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
