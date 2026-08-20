#!/usr/bin/env python3
"""Run one frozen E4-D2B arm on the exposed D2 closed-loop starts."""

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
import acid_alt_e4_d2b_models as e4d2b
from acid_alt_e4_controls import load_inverse_control
from acid_alt_e4_scoring import E4_P1_PROTOCOL_SHA256, load_e4_model, sha256_file
from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.io_utils import atomic_write_json, resolve_policy_checkpoint


TASKS = ("pusht", "reacher", "cube")
PLANNER_SEED = 8401
PRIMARY_E4_SEED = 7101
PRIMARY_CORE_SEED = 6101
EVAL_COUNT = 50
D2B_FREEZE_SHA256 = (
    "0b8aba12023ffcd7f4f010a72452ae021e081d80f11dfc7fe21cb13c8dfb4250"
)
D2A_IMPLEMENTATION_FREEZE_SHA256 = (
    "193f5679ec91377c0d2411b9092cc4d2c8308d64f509917244d1b89dcb7354b9"
)
D2A_SOURCE_MANIFEST_SHA256 = (
    "36a6c04fe47e8bfc0bb6e375e5d2d3448879e06146af433d504c523842af70bd"
)


def reject_protected_path(path: Path) -> None:
    lowered = str(path).lower().replace("_", "-")
    if "c1" in lowered or "i1" in lowered:
        raise RuntimeError(f"protected C1/I1 path is forbidden: {path}")


def image_transform(image_size: int):
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=image_size),
        ]
    )


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


def validate_d2a_authorization(
    authorization_path: Path,
    analysis_path: Path,
    *,
    parent_protocol: Path,
    d2a_implementation_freeze: Path,
    d2a_source_manifest: Path,
) -> dict[str, Any]:
    for path in (
        authorization_path,
        analysis_path,
        parent_protocol,
        d2a_implementation_freeze,
        d2a_source_manifest,
    ):
        reject_protected_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(parent_protocol) != E4_P1_PROTOCOL_SHA256:
        raise RuntimeError("E4 parent protocol hash mismatch")
    if sha256_file(d2a_implementation_freeze) != D2A_IMPLEMENTATION_FREEZE_SHA256:
        raise RuntimeError("E4-D2A implementation-freeze hash mismatch")
    if sha256_file(d2a_source_manifest) != D2A_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("E4-D2A source-manifest hash mismatch")

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if (
        analysis.get("status") != "ok"
        or analysis.get("kind") != "acid_alt_e4_d2a_analysis"
        or analysis.get("analysis_role")
        != "post-E3 exposed D2 exploratory development"
        or analysis.get("all_d2a_gates_pass") is not True
        or analysis.get("decision") != "authorize_e4_d2b_closed_loop"
        or not isinstance(analysis.get("gates"), dict)
        or not all(analysis["gates"].values())
        or analysis.get("parent_protocol_sha256") != E4_P1_PROTOCOL_SHA256
        or analysis.get("implementation_freeze_sha256")
        != D2A_IMPLEMENTATION_FREEZE_SHA256
        or analysis.get("source_manifest_sha256") != D2A_SOURCE_MANIFEST_SHA256
        or set(analysis.get("inputs", {})) != set(TASKS)
        or analysis.get("protected_c1_i1_read") is not False
        or analysis.get("confirmation_claim_allowed") is not False
        or analysis.get("alternative_to_acid_claim_allowed") is not False
    ):
        raise RuntimeError("E4-D2A analysis does not authorize D2B")

    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if (
        authorization.get("status") != "authorized"
        or authorization.get("kind") != "acid_alt_e4_d2b_authorization"
        or authorization.get("d2a_summary_sha256") != sha256_file(analysis_path)
        or authorization.get("parent_protocol_sha256") != E4_P1_PROTOCOL_SHA256
        or authorization.get("implementation_freeze_sha256")
        != D2A_IMPLEMENTATION_FREEZE_SHA256
        or authorization.get("source_manifest_sha256")
        != D2A_SOURCE_MANIFEST_SHA256
        or authorization.get("protected_c1_i1_read") is not False
        or authorization.get("confirmation_claim_allowed") is not False
    ):
        raise RuntimeError("E4-D2B authorization record is invalid")
    return {
        "authorization": authorization,
        "analysis": analysis,
        "authorization_sha256": sha256_file(authorization_path),
        "analysis_sha256": sha256_file(analysis_path),
    }


def load_arm_artifact(
    *,
    arm: str,
    task: str,
    artifact: Path | None,
    device: torch.device,
) -> tuple[torch.nn.Module | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    family = e4d2b.expected_artifact_family(arm)
    if family == "none":
        if artifact is not None:
            raise ValueError("B0 cannot receive --scorer-artifact")
        return None, None, None, None
    if artifact is None:
        raise ValueError(f"{arm} requires --scorer-artifact")
    reject_protected_path(artifact)
    if family in {"acid", "forward", "reachability"}:
        scorer, payload, record = d2.load_core_scorer(
            artifact,
            arm=family,
            expected_seed=PRIMARY_CORE_SEED,
            device=device,
        )
        return scorer, payload, None, record
    if family in {"e4_true", "e4_shuffled"}:
        condition = "true_successor" if family == "e4_true" else "shuffled_successor"
        scorer, payload, calibration, record = load_e4_model(
            artifact,
            task=task,
            expected_condition=condition,
            device=device,
        )
        return scorer, payload, calibration, record
    if family in {"deterministic", "gaussian"}:
        scorer, payload, calibration, record = load_inverse_control(
            artifact,
            task=task,
            model_kind=family,
            expected_seed=PRIMARY_E4_SEED,
            source_manifest_sha256=D2A_SOURCE_MANIFEST_SHA256,
            device=device,
        )
        return scorer, payload, calibration, record
    raise RuntimeError(f"unsupported artifact family: {family}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--arm", choices=e4d2b.ARMS, required=True)
    parser.add_argument("--planner-seed", type=int, required=True)
    parser.add_argument("--parent-protocol", type=Path, required=True)
    parser.add_argument("--d2b-freeze", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--d2a-implementation-freeze", type=Path, required=True)
    parser.add_argument("--d2a-source-manifest", type=Path, required=True)
    parser.add_argument("--d2a-analysis", type=Path, required=True)
    parser.add_argument("--d2a-authorization", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--eval-provenance", type=Path, required=True)
    parser.add_argument("--scorer-artifact", type=Path)
    parser.add_argument("--save-video", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.planner_seed != PLANNER_SEED:
        raise ValueError(f"planner seed must be {PLANNER_SEED}")
    required = (
        args.parent_protocol,
        args.d2b_freeze,
        args.source_manifest,
        args.d2a_implementation_freeze,
        args.d2a_source_manifest,
        args.d2a_analysis,
        args.d2a_authorization,
        args.code_root,
        args.stablewm_home,
        args.dataset,
        args.world_model_checkpoint,
        args.eval_manifest,
        args.eval_provenance,
    )
    for path in required:
        reject_protected_path(path)
        if not path.exists():
            raise FileNotFoundError(path)
    if sha256_file(args.d2b_freeze) != D2B_FREEZE_SHA256:
        raise RuntimeError("E4-D2B implementation-freeze hash mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E4-D2B evaluation output")
    authorization = validate_d2a_authorization(
        args.d2a_authorization,
        args.d2a_analysis,
        parent_protocol=args.parent_protocol,
        d2a_implementation_freeze=args.d2a_implementation_freeze,
        d2a_source_manifest=args.d2a_source_manifest,
    )

    # Reuse the already frozen D2 manifest validator without changing its data
    # lineage.  The validator independently checks the task-specific hashes.
    from evaluate_acid_alt_e3_d2 import read_d2_manifest

    rows = read_d2_manifest(
        args.eval_manifest,
        args.eval_provenance,
        task=args.task,
        dataset=args.dataset,
        source_manifest=args.source_manifest,
    )

    torch.manual_seed(args.planner_seed)
    np.random.seed(args.planner_seed)
    torch.cuda.manual_seed_all(args.planner_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E4-D2B closed-loop evaluation requires CUDA")
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
    cfg.plan_config.horizon = e4d2b.HORIZON
    cfg.plan_config.receding_horizon = e4d2b.HORIZON
    cfg.plan_config.action_block = e4d2b.HORIZON

    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        args.dataset_name,
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError(f"dataset-name resolved to {dataset.h5_path}, not {args.dataset}")
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

    scorer, payload, calibration, scorer_record = load_arm_artifact(
        arm=args.arm,
        task=args.task,
        artifact=args.scorer_artifact,
        device=device,
    )
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

    cost_model = e4d2b.E4D2BCostModel(
        world_model,
        arm=args.arm,
        task=args.task,
        planner_seed=args.planner_seed,
        scorer=scorer,
        payload=payload,
        calibration=calibration,
        horizon=e4d2b.HORIZON,
        record_diagnostics=True,
    ).to(device)
    plan_config = swm.PlanConfig(
        horizon=e4d2b.HORIZON,
        receding_horizon=e4d2b.HORIZON,
        action_block=e4d2b.HORIZON,
    )
    solver = swm.solver.CEMSolver(
        model=cost_model,
        batch_size=1,
        num_samples=300,
        var_scale=1.0,
        n_steps=30,
        topk=30,
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
        "task": args.task,
        "arm": args.arm,
        "artifact_family": e4d2b.expected_artifact_family(args.arm),
        "model_seed": None if scorer_record is None else scorer_record.get("seed"),
        "planner_seed": args.planner_seed,
        "lambda_weight": cost_model.lambda_weight,
        "spread_epsilon": e4d2b.SPREAD_EPSILON,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": e4d2b.HORIZON,
        "receding_horizon": e4d2b.HORIZON,
        "action_block": e4d2b.HORIZON,
        "cem_samples": 300,
        "cem_steps": 30,
        "cem_topk": 30,
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
        raise RuntimeError("closed-loop evaluator returned an unexpected episode count")

    episode_path = args.output_dir / "episodes.tsv"
    with episode_path.open("x", newline="", encoding="utf-8") as stream:
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
    with diagnostics_path.open("x", encoding="utf-8") as stream:
        for record in cost_model.diagnostic_history:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    summary = {
        "status": "ok",
        "kind": "acid_alt_e4_d2b_closed_loop_evaluation",
        "analysis_role": "post-E3 exposed D2 exploratory closed-loop development",
        "task": args.task,
        "arm": args.arm,
        "planner_seed": args.planner_seed,
        "model_seed": None if scorer_record is None else scorer_record.get("seed"),
        "metrics": jsonable(metrics),
        "success_count": int(successes.sum()),
        "episode_count": EVAL_COUNT,
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "parent_protocol": str(args.parent_protocol),
        "parent_protocol_sha256": sha256_file(args.parent_protocol),
        "d2b_freeze": str(args.d2b_freeze),
        "d2b_freeze_sha256": sha256_file(args.d2b_freeze),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "d2a_analysis": str(args.d2a_analysis),
        "d2a_analysis_sha256": authorization["analysis_sha256"],
        "d2a_authorization": str(args.d2a_authorization),
        "d2a_authorization_sha256": authorization["authorization_sha256"],
        "d2a_source_manifest_sha256": D2A_SOURCE_MANIFEST_SHA256,
        "eval_manifest": str(args.eval_manifest),
        "eval_manifest_sha256": sha256_file(args.eval_manifest),
        "eval_provenance": str(args.eval_provenance),
        "eval_provenance_sha256": sha256_file(args.eval_provenance),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "resolved_world_model_checkpoint": str(resolved_checkpoint),
        "scorer": scorer_record,
        "resolved_config": resolved_config,
        "episodes_tsv": str(episode_path),
        "episodes_tsv_sha256": sha256_file(episode_path),
        "cem_diagnostics": str(diagnostics_path),
        "cem_diagnostics_sha256": sha256_file(diagnostics_path),
        "cem_cost_calls": len(cost_model.diagnostic_history),
        "shuffled_reliability": 0 if args.arm == "cider_shuffled" else None,
        "protected_c1_i1_read": False,
        "confirmation_claim_allowed": False,
        "publication_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
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
