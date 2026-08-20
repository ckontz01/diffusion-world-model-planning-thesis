#!/usr/bin/env python3
"""Run one frozen arm in the post-v3 exploratory E3 D2 closed loop."""

from __future__ import annotations

import argparse
import csv
import importlib.util
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
from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.io_utils import atomic_write_json, resolve_policy_checkpoint


TASKS = ("pusht", "reacher", "cube")
ARMS = (
    "b0",
    "acid",
    "forward",
    "rdx",
    "ae",
    "ae_shuffled",
)
PLANNER_SEEDS = (8301, 8302, 8303)
EVAL_COUNT = 50
E3_PROTOCOL_SHA256 = (
    "c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0"
)
V3_SOURCE_MANIFEST_SHA256 = (
    "2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea"
)
STAGE_A_SUMMARY_SHA256 = (
    "0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37"
)
STAGE_A_MANIFEST_SHA256 = (
    "3558b8612787035cfa92c17d8a36f46f379bb2812f67aa0a73438d8cab974053"
)
D2_HASHES = {
    "pusht": {
        "manifest": "85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89",
        "provenance": "fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede",
    },
    "reacher": {
        "manifest": "a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61",
        "provenance": "f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11",
    },
    "cube": {
        "manifest": "bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388",
        "provenance": "fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b",
    },
}
EXPECTED_STAGE_A_GATES = {
    "1_rdx_positive_all_tasks_and_pooled": True,
    "2_rdx_beats_shuffled": True,
    "3_rdx_noninferior_forward_and_acid": False,
    "4_ae_beats_shuffled_without_negative_task": True,
    "5_ae_selection_noninferior_acid": True,
}


def image_transform(image_size: int):
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=image_size),
        ]
    )


def load_module(path: Path, expected_hash: str, name: str) -> Any:
    if not path.is_file() or d2.sha256_file(path) != expected_hash:
        raise RuntimeError(f"{name} source hash mismatch: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject_protected_path(path: Path) -> None:
    lowered = str(path).lower().replace("_", "-")
    if "c1" in lowered or "i1" in lowered:
        raise RuntimeError(f"protected C1/I1 path is forbidden: {path}")


def read_d2_manifest(
    path: Path,
    provenance_path: Path,
    *,
    task: str,
    dataset: Path,
    source_manifest: Path,
) -> list[dict[str, str]]:
    reject_protected_path(path)
    reject_protected_path(provenance_path)
    if task not in D2_HASHES:
        raise ValueError(f"unexpected E3 task: {task}")
    if (
        d2.sha256_file(path) != D2_HASHES[task]["manifest"]
        or d2.sha256_file(provenance_path) != D2_HASHES[task]["provenance"]
    ):
        raise RuntimeError(f"frozen D2 input hash mismatch for {task}")
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {
        "eval_index",
        "episode_id",
        "start_step",
        "declared_goal_offset",
    }
    if len(rows) != EVAL_COUNT or not required.issubset(rows[0]):
        raise ValueError("invalid D2 evaluation manifest")
    if [int(row["eval_index"]) for row in rows] != list(range(EVAL_COUNT)):
        raise ValueError("D2 evaluation indices are not contiguous")
    if any(int(row["declared_goal_offset"]) != 25 for row in rows):
        raise ValueError("D2 manifest configuration differs from frozen protocol")
    episodes = [int(row["episode_id"]) for row in rows]
    starts = [(int(row["episode_id"]), int(row["start_step"])) for row in rows]
    if len(set(episodes)) != EVAL_COUNT or len(set(starts)) != EVAL_COUNT:
        raise ValueError("D2 requires one unique start per unique episode")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (
        provenance.get("status") != "ok"
        or provenance.get("kind") != "acid_alternative_v3_fresh_d2_manifest"
        or provenance.get("analysis_role") != "D2"
        or provenance.get("task") != task
        or provenance.get("partition") != "P3"
        or provenance.get("selection_seed") != 2026081603
        or provenance.get("goal_offset") != 25
        or provenance.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or provenance.get("dataset_sha256") != d2.sha256_file(dataset)
        or provenance.get("manifest_tsv_sha256") != d2.sha256_file(path)
        or provenance.get("protected_c1_i1_paths_read") is not False
        or provenance.get("count") != EVAL_COUNT
        or provenance.get("unique_episode_count") != EVAL_COUNT
    ):
        raise RuntimeError("D2 manifest provenance is invalid")
    return rows


def validate_e3_authorization(
    path: Path, *, protocol: Path, source_manifest: Path
) -> dict[str, Any]:
    reject_protected_path(path)
    authorization = json.loads(path.read_text(encoding="utf-8"))
    if (
        authorization.get("status")
        != "authorized_for_exploratory_development_only"
        or authorization.get("kind")
        != "acid_alt_e3_d2_exploratory_authorization"
        or authorization.get("analysis_role")
        != "post_v3_exploratory_d2_closed_loop_development"
        or authorization.get("protocol_sha256") != E3_PROTOCOL_SHA256
        or d2.sha256_file(protocol) != E3_PROTOCOL_SHA256
        or authorization.get("source_manifest_sha256")
        != d2.sha256_file(source_manifest)
        or authorization.get("v3_protocol_sha256") != d2.PROTOCOL_SHA256
        or authorization.get("v3_source_manifest_sha256")
        != V3_SOURCE_MANIFEST_SHA256
        or authorization.get("v3_upstream_source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or authorization.get("v3_stage_b_authorized") is not False
        or authorization.get("confirmation_claim_allowed") is not False
        or authorization.get("alternative_to_acid_claim_allowed") is not False
        or authorization.get("arms") != list(ARMS)
        or authorization.get("scorer_seeds") != list(d2.SEEDS)
        or authorization.get("planner_seeds") != list(PLANNER_SEEDS)
        or authorization.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E3 exploratory authorization is invalid")

    stage_a = Path(authorization["stage_a_summary"])
    stage_a_manifest = Path(authorization["stage_a_manifest"])
    reject_protected_path(stage_a)
    reject_protected_path(stage_a_manifest)
    if (
        not stage_a.is_file()
        or not stage_a_manifest.is_file()
        or d2.sha256_file(stage_a) != STAGE_A_SUMMARY_SHA256
        or authorization.get("stage_a_summary_sha256")
        != STAGE_A_SUMMARY_SHA256
        or d2.sha256_file(stage_a_manifest) != STAGE_A_MANIFEST_SHA256
        or authorization.get("stage_a_manifest_sha256")
        != STAGE_A_MANIFEST_SHA256
    ):
        raise RuntimeError("frozen failed Stage-A evidence hash mismatch")
    stage_a_payload = json.loads(stage_a.read_text(encoding="utf-8"))
    stage_a_manifest_payload = json.loads(
        stage_a_manifest.read_text(encoding="utf-8")
    )
    if (
        stage_a_payload.get("status") != "ok"
        or stage_a_payload.get("kind") != "acid_alt_v3_d2_stage_a_analysis"
        or stage_a_payload.get("all_stage_a_gates_pass") is not False
        or stage_a_payload.get("decision") != "stop_before_stage_b"
        or stage_a_payload.get("gates") != EXPECTED_STAGE_A_GATES
        or stage_a_payload.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or stage_a_payload.get("source_manifest_sha256")
        != V3_SOURCE_MANIFEST_SHA256
        or stage_a_payload.get("upstream_source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or stage_a_payload.get("protected_c1_i1_read") is not False
        or stage_a_manifest_payload.get("stage_b_authorized") is not False
        or stage_a_manifest_payload.get("summary_sha256")
        != STAGE_A_SUMMARY_SHA256
        or stage_a_manifest_payload.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E3 requires the exact failed v3 Stage-A result")
    return authorization

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
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--scorer-seed", type=int, required=True)
    parser.add_argument("--planner-seed", type=int, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--exploratory-authorization", type=Path, required=True)
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

    if args.scorer_seed not in d2.SEEDS:
        raise ValueError(f"scorer seed must be one of {d2.SEEDS}")
    if args.planner_seed not in PLANNER_SEEDS:
        raise ValueError(f"planner seed must be one of {PLANNER_SEEDS}")
    if args.planner_seed - args.scorer_seed != 2200:
        raise ValueError("scorer/planner seeds must be paired by protocol")
    if args.arm == "b0":
        if args.scorer_checkpoint is not None or args.scorer_summary is not None:
            raise ValueError("B0 must not receive a scorer artifact")
    elif args.arm in {"acid", "forward"}:
        if args.scorer_checkpoint is None or args.scorer_summary is not None:
            raise ValueError("core arms require only --scorer-checkpoint")
    elif args.scorer_summary is None or args.scorer_checkpoint is not None:
        raise ValueError("residual arms require only --scorer-summary")

    required = (
        args.protocol,
        args.source_manifest,
        args.exploratory_authorization,
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
    if d2.sha256_file(args.protocol) != E3_PROTOCOL_SHA256:
        raise RuntimeError("E3 protocol hash mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E3 evaluation output")
    authorization = validate_e3_authorization(
        args.exploratory_authorization,
        protocol=args.protocol,
        source_manifest=args.source_manifest,
    )
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
        raise RuntimeError("D2 closed-loop evaluation requires CUDA")
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
        raise RuntimeError(
            f"dataset-name resolved to {dataset.h5_path}, not {args.dataset}"
        )
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
    if args.arm in {"acid", "forward"}:
        assert args.scorer_checkpoint is not None
        scorer, payload, scorer_record = d2.load_core_scorer(
            args.scorer_checkpoint,
            arm=args.arm,
            expected_seed=args.scorer_seed,
            device=device,
        )
    elif args.arm in {"rdx", "ae", "ae_shuffled"}:
        assert args.scorer_summary is not None
        trainer = load_module(
            args.trainer_source,
            d2.V2_TRAINER_SHA256,
            "frozen_residual_diffusion_trainer",
        )
        expected_condition = "shuffled_action" if args.arm == "ae_shuffled" else "true"
        scorer, payload, scorer_record = d2.load_residual_model(
            args.scorer_summary,
            expected_condition=expected_condition,
            trainer_module=trainer,
            device=device,
        )
        if int(payload["seed"]) != args.scorer_seed:
            raise RuntimeError("residual scorer seed differs from declared seed")

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

    cost_model = d2.D2CostModel(
        world_model,
        arm=args.arm,
        task=args.task,
        planner_seed=args.planner_seed,
        scorer=scorer,
        payload=payload,
        horizon=5,
        record_diagnostics=True,
    ).to(device)
    plan_config = swm.PlanConfig(horizon=5, receding_horizon=5, action_block=5)
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
        "scorer_seed": args.scorer_seed,
        "planner_seed": args.planner_seed,
        "lambda_weight": cost_model.lambda_weight,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "cem_samples": 300,
        "cem_steps": 30,
        "cem_topk": 30,
        "residual_sigmas": list(d2.SIGMAS),
        "residual_noise_draws": d2.NOISE_DRAWS,
        "acid_noise_stream": (
            "SHA-256(task, scorer seed, planner seed, cost-call index)"
            if args.arm == "acid"
            else None
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
        raise RuntimeError("closed-loop evaluator returned an unexpected episode count")

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
                    "scorer_seed": args.scorer_seed,
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
        "kind": "acid_alt_e3_d2_exploratory_closed_loop_evaluation",
        "analysis_role": "post_v3_exploratory_d2_closed_loop_development",
        "task": args.task,
        "arm": args.arm,
        "scorer_seed": args.scorer_seed,
        "planner_seed": args.planner_seed,
        "metrics": jsonable(metrics),
        "success_count": int(successes.sum()),
        "episode_count": EVAL_COUNT,
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "upstream_source_manifest_sha256": V3_SOURCE_MANIFEST_SHA256,
        "v3_upstream_source_manifest_sha256": (
            d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        ),
        "exploratory_authorization": str(args.exploratory_authorization),
        "exploratory_authorization_sha256": d2.sha256_file(
            args.exploratory_authorization
        ),
        "stage_a_summary_sha256": authorization["stage_a_summary_sha256"],
        "stage_a_manifest_sha256": authorization["stage_a_manifest_sha256"],
        "v3_stage_b_authorized": False,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
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
        "cem_cost_calls": len(cost_model.diagnostic_history),
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


