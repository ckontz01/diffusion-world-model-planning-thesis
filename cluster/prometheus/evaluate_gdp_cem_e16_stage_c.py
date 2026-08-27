#!/usr/bin/env python3
"""Run one frozen E16 P2 task/arm/replicate/horizon/shard cell."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
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

import gdp_cem_e15_specs as e15
import gdp_cem_e16_specs as spec
from diagnose_gdp_cem_e16_one_continuation import verify_adapter
from evaluate_gdp_cem_e14_gate_c import (
    load_endpoint_artifact,
    load_sage_component,
    resolve_policy_checkpoint,
)
from evaluate_gdp_cem_e15_gate_c import load_e15_proposer
from gdp_cem_e15_closed_loop import InstrumentedE14Planner, ScheduledE14Policy
from gdp_cem_e15_data import sha256_file
from gdp_cem_e16_closed_loop import (
    E16DirectPlanner,
    family_for_arm,
    is_continuation_arm,
)


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected E16 path is forbidden: {path}")


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


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if torch.is_tensor(value):
        return value.detach().cpu().tolist()
    if isinstance(value, Path):
        return str(value)
    return value


def image_transform(image_size: int) -> Any:
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=image_size),
        ]
    )


def read_stage_b(path: Path, expected_sha256: str) -> dict[str, Any]:
    reject_protected_path(path)
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise RuntimeError("E16 Stage-B audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e16_one_continuation_stage_b_audit"
        or value.get("stage_c_authorized") is not True
        or value.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or value.get("source_manifest_sha256")
        != spec.STAGE_B_SOURCE_MANIFEST_SHA256
        or value.get("p2_read") is not False
        or value.get("d5_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E16 Stage-B authorization differs")
    return value


def read_p2_rows(
    queries: Path,
    provenance_path: Path,
    *,
    task: str,
    horizon: int,
    shard: int,
    dataset: Path,
    source_manifest_sha256: str,
    stage_b_audit_sha256: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    for path in (queries, provenance_path, dataset):
        reject_protected_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    task_spec = e15.TASK_SPEC[task]
    if (
        provenance.get("status") != "ok"
        or provenance.get("kind") != "gdp_cem_e16_fresh_shared_start_p2_manifest"
        or provenance.get("analysis_role") != "P2_continuation_method_development"
        or provenance.get("task") != task
        or provenance.get("partition") != "P2"
        or int(provenance.get("base_start_count", -1)) != spec.STAGE_C_BASE_STARTS
        or provenance.get("horizons") != list(spec.STAGE_C_HORIZONS)
        or int(provenance.get("rows_per_horizon", -1)) != spec.STAGE_C_BASE_STARTS
        or int(provenance.get("total_rows", -1))
        != spec.STAGE_C_BASE_STARTS * len(spec.STAGE_C_HORIZONS)
        or provenance.get("same_episode_start_pairs_across_horizons") is not True
        or provenance.get("selection_salt") != spec.STAGE_C_SELECTION_SALT
        or int(provenance.get("excluded_old_pair_count", -1))
        != e15.GATE_C_BASE_STARTS
        or provenance.get("excluded_old_queries_sha256")
        != task_spec["p2_queries_sha256"]
        or provenance.get("excluded_old_provenance_sha256")
        != task_spec["p2_manifest_sha256"]
        or provenance.get("dataset_sha256") != task_spec["dataset_sha256"]
        or provenance.get("partition_manifest_sha256")
        != task_spec["partition_manifest_sha256"]
        or provenance.get("stage_b_audit_sha256") != stage_b_audit_sha256
        or provenance.get("stage_b_source_manifest_sha256")
        != spec.STAGE_B_SOURCE_MANIFEST_SHA256
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256") != source_manifest_sha256
        or provenance.get("output_tsv_sha256") != sha256_file(queries)
        or provenance.get("d5_read") is not False
        or provenance.get("claim_allowed") is not False
        or sha256_file(dataset) != task_spec["dataset_sha256"]
    ):
        raise RuntimeError("E16 P2 provenance differs")
    with queries.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != spec.STAGE_C_BASE_STARTS * len(spec.STAGE_C_HORIZONS):
        raise RuntimeError("E16 P2 query row count differs")
    pair_sets = []
    for value in spec.STAGE_C_HORIZONS:
        group = sorted(
            [row for row in rows if int(row["goal_horizon"]) == value],
            key=lambda row: int(row["base_index"]),
        )
        if (
            len(group) != spec.STAGE_C_BASE_STARTS
            or [int(row["base_index"]) for row in group]
            != list(range(spec.STAGE_C_BASE_STARTS))
            or any(
                int(row["dataset_goal_step"])
                != int(row["start_step"]) + value - 1
                for row in group
            )
        ):
            raise RuntimeError("E16 P2 horizon group differs")
        pair_sets.append(
            [(int(row["episode_id"]), int(row["start_step"])) for row in group]
        )
    if any(value != pair_sets[0] for value in pair_sets[1:]):
        raise RuntimeError("E16 P2 starts differ across horizons")
    selected = sorted(
        [row for row in rows if int(row["goal_horizon"]) == horizon],
        key=lambda row: int(row["base_index"]),
    )
    start = shard * spec.STAGE_C_SHARD_SIZE
    selected = selected[start : start + spec.STAGE_C_SHARD_SIZE]
    if len(selected) != spec.STAGE_C_SHARD_SIZE:
        raise RuntimeError("E16 P2 shard cardinality differs")
    return selected, provenance


def timing_summary(
    diagnostics: list[dict[str, Any]], field: str
) -> dict[str, float | None]:
    values = np.asarray(
        [float(record.get(field, 0.0)) / spec.STAGE_C_SHARD_SIZE for record in diagnostics],
        dtype=np.float64,
    )
    post = values[1:]
    return {
        "all_call_median_seconds_per_context_stage": float(np.median(values)),
        "all_call_mean_seconds_per_context_stage": float(np.mean(values)),
        "post_first_call_median_seconds_per_context_stage": (
            float(np.median(post)) if len(post) else None
        ),
        "post_first_call_mean_seconds_per_context_stage": (
            float(np.mean(post)) if len(post) else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--arm", choices=spec.STAGE_C_ARMS, required=True)
    parser.add_argument("--replicate", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--horizon", type=int, choices=spec.STAGE_C_HORIZONS, required=True)
    parser.add_argument(
        "--shard", type=int, choices=range(spec.STAGE_C_SHARD_COUNT), required=True
    )
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--e15-training-root", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--sage-normalized-root", type=Path, required=True)
    parser.add_argument("--stage-b-audit", type=Path, required=True)
    parser.add_argument("--stage-b-audit-sha256", required=True)
    parser.add_argument("--p2-queries", type=Path, required=True)
    parser.add_argument("--p2-provenance", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.code_root,
        args.stablewm_home,
        args.dataset,
        args.world_model_checkpoint,
        args.e15_training_root,
        args.adapter_root,
        args.sage_normalized_root,
        args.stage_b_audit,
        args.p2_queries,
        args.p2_provenance,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E16 Stage-C protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E16 Stage-C output")
    if not torch.cuda.is_available():
        raise RuntimeError("E16 Stage-C requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E16 Stage-C GPU model differs")
    stage_b = read_stage_b(args.stage_b_audit, args.stage_b_audit_sha256)
    source_manifest_sha = sha256_file(args.source_manifest)
    task_spec = e15.TASK_SPEC[args.task]
    if (
        args.dataset_name != task_spec["dataset_name"]
        or args.world_model_policy != task_spec["world_model_policy"]
        or sha256_file(args.dataset) != task_spec["dataset_sha256"]
        or sha256_file(args.world_model_checkpoint) != task_spec["world_model_sha256"]
        or resolve_policy_checkpoint(
            args.world_model_policy, args.stablewm_home
        )
        != args.world_model_checkpoint.resolve()
    ):
        raise RuntimeError("E16 Stage-C released-stack identity differs")
    rows, p2_provenance = read_p2_rows(
        args.p2_queries,
        args.p2_provenance,
        task=args.task,
        horizon=args.horizon,
        shard=args.shard,
        dataset=args.dataset,
        source_manifest_sha256=source_manifest_sha,
        stage_b_audit_sha256=args.stage_b_audit_sha256,
    )
    learned_seed = 7200 + args.replicate
    sage_seed = 6100 + args.replicate
    planner_seed = spec.derived_seed(
        f"stage-c|planner|task={args.task}|h={args.horizon}"
        f"|replicate={args.replicate}|shard={args.shard}"
    )
    proposal_seed = spec.derived_seed(
        f"stage-c|proposal|task={args.task}|h={args.horizon}"
        f"|replicate={args.replicate}|shard={args.shard}"
    )
    torch.manual_seed(planner_seed)
    np.random.seed(planner_seed % (2**32))
    torch.cuda.manual_seed_all(planner_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.task)
    eval_budget = args.horizon * (2 if args.task == "pusht" else 1)
    cfg.world.num_envs = spec.STAGE_C_SHARD_SIZE
    cfg.world.max_episode_steps = 2 * eval_budget
    cfg.eval.num_eval = spec.STAGE_C_SHARD_SIZE
    cfg.eval.goal_offset_steps = args.horizon
    cfg.eval.eval_budget = eval_budget
    cfg.eval.dataset_name = args.dataset_name
    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        args.dataset_name,
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("E16 Stage-C dataset name resolves differently")
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
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    model_records: dict[str, Any] = {}
    active_parameters = 0
    if args.arm in ("base_cem", "sage_reconstruction"):
        _, e14_statistics, statistics_record = load_endpoint_artifact(
            args.sage_normalized_root,
            task=args.task,
            condition="vad_true",
            seed=sage_seed,
            device=device,
            instantiate=False,
        )
        model_records["e14_statistics_source"] = statistics_record
        sage_subgoal = None
        sage_option = None
        if args.arm == "sage_reconstruction":
            sage_subgoal, subgoal_record = load_sage_component(
                args.sage_normalized_root,
                task=args.task,
                component="subgoal",
                seed=sage_seed,
                device=device,
            )
            sage_option, option_record = load_sage_component(
                args.sage_normalized_root,
                task=args.task,
                component="option",
                seed=sage_seed,
                device=device,
                expected_subgoal_sha256=subgoal_record["checkpoint_sha256"],
            )
            model_records["sage_subgoal"] = subgoal_record
            model_records["sage_option"] = option_record
            active_parameters = int(subgoal_record["parameter_count"]) + int(
                option_record["parameter_count"]
            )
        planner: Any = InstrumentedE14Planner(
            world_model,
            reported_arm=args.arm,
            one_stage=False,
            statistics=e14_statistics,
            state_dim=int(task_spec["state_dim"]),
            primitive_action_dim=int(task_spec["primitive_action_dim"]),
            sage_subgoal=sage_subgoal,
            sage_option=sage_option,
            candidate_count=e15.CANDIDATE_COUNT,
            cem_rounds=e15.CEM_ROUNDS,
            elites=e15.CEM_ELITES,
            batch_size=1,
            planner_seed=planner_seed,
            proposal_seed=proposal_seed,
        )
    else:
        family = family_for_arm(args.arm)  # type: ignore[arg-type]
        proposer, statistics, proposer_record = load_e15_proposer(
            args.e15_training_root,
            task=args.task,
            condition=family,
            seed=learned_seed,
            device=device,
        )
        adapter, adapter_summary = verify_adapter(
            args.adapter_root / args.task, task=args.task
        )
        model_records["e15_proposer"] = proposer_record
        model_records["e16_state_adapter"] = {
            "summary": str(args.adapter_root / args.task / "summary.json"),
            "summary_sha256": sha256_file(
                args.adapter_root / args.task / "summary.json"
            ),
            "checkpoint_sha256": adapter_summary["checkpoint_sha256"],
            "parameter_count": adapter_summary["parameter_count"],
        }
        active_parameters = int(proposer_record["parameter_count"]) + int(
            adapter_summary["parameter_count"]
        )
        planner = E16DirectPlanner(
            world_model,
            arm=args.arm,  # type: ignore[arg-type]
            statistics=statistics,
            state_dim=int(task_spec["state_dim"]),
            primitive_action_dim=int(task_spec["primitive_action_dim"]),
            proposer=proposer,
            state_adapter=adapter,
            batch_size=1,
            proposal_seed=proposal_seed,
        )
    schedule = e15.schedule_for(args.horizon)
    policy = ScheduledE14Policy(
        planner,
        schedule=schedule,
        environment_budget=eval_budget,
        state_key=str(task_spec["state_key"]),
        process=process,
        transform=transform,
    )
    world.set_policy(policy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.time()
    metrics = world.evaluate_from_dataset(
        dataset=dataset,
        episodes_idx=[int(row["episode_id"]) for row in rows],
        start_steps=[int(row["start_step"]) for row in rows],
        goal_offset_steps=args.horizon,
        eval_budget=eval_budget,
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        save_video=False,
        video_path=args.output_dir / "videos-disabled",
    )
    torch.cuda.synchronize()
    elapsed = time.time() - started
    successes = np.asarray(metrics["episode_successes"], dtype=bool)
    if successes.shape != (spec.STAGE_C_SHARD_SIZE,):
        raise RuntimeError("E16 Stage-C episode count differs")
    episodes_path = args.output_dir / "episodes.tsv"
    with episodes_path.open("x", newline="", encoding="utf-8") as stream:
        fields = (
            "eval_index",
            "base_index",
            "episode_id",
            "start_step",
            "task",
            "horizon",
            "replicate",
            "learned_seed",
            "sage_seed",
            "planner_seed",
            "proposal_seed",
            "arm",
            "shard",
            "success",
        )
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row, success in zip(rows, successes.tolist()):
            writer.writerow(
                {
                    "eval_index": row["eval_index"],
                    "base_index": row["base_index"],
                    "episode_id": row["episode_id"],
                    "start_step": row["start_step"],
                    "task": args.task,
                    "horizon": args.horizon,
                    "replicate": args.replicate,
                    "learned_seed": learned_seed,
                    "sage_seed": sage_seed,
                    "planner_seed": planner_seed,
                    "proposal_seed": proposal_seed,
                    "arm": args.arm,
                    "shard": args.shard,
                    "success": int(success),
                }
            )
    diagnostics_path = args.output_dir / "planner-diagnostics.jsonl"
    with diagnostics_path.open("x", encoding="utf-8") as stream:
        for record in planner.diagnostic_history:
            stream.write(json.dumps(jsonable(record), sort_keys=True) + "\n")
    cycles = eval_budget // args.horizon
    expected_stages = len(schedule) * cycles
    if len(planner.diagnostic_history) != expected_stages:
        raise RuntimeError("E16 Stage-C planning-stage count differs")
    if args.arm in ("base_cem", "sage_reconstruction"):
        population_calls = sum(
            int(record["lewm_population_calls"])
            for record in planner.diagnostic_history
        )
        expected = spec.STAGE_C_SHARD_SIZE * expected_stages * e15.CEM_ROUNDS
        if population_calls != expected:
            raise RuntimeError("E16 comparator population-call budget differs")
        rollout_trajectories = population_calls * e15.CANDIDATE_COUNT
    else:
        rollout_trajectories = sum(
            int(record["lewm_rollout_trajectories"])
            for record in planner.diagnostic_history
        )
        for record in planner.diagnostic_history:
            delta_value = int(record["delta"])
            if is_continuation_arm(args.arm):  # type: ignore[arg-type]
                per_context = (
                    spec.GREEDY_COMPUTE_MATCHED_CANDIDATES
                    if delta_value >= 2 * spec.TAU
                    else spec.CONTINUATION_FIRST_CANDIDATES
                )
            elif args.arm == "vad_greedy_300":
                per_context = spec.GREEDY_CANDIDATES
            else:
                per_context = spec.GREEDY_COMPUTE_MATCHED_CANDIDATES
            if int(record["lewm_rollout_trajectories"]) != (
                spec.STAGE_C_SHARD_SIZE * per_context
            ):
                raise RuntimeError("E16 direct rollout budget differs")
    timing = {
        name: timing_summary(planner.diagnostic_history, field)
        for name, field in (
            ("end_to_end", "end_to_end_stage_seconds"),
            ("proposal_and_selection", "proposal_and_selection_seconds"),
            ("adapter", "adapter_seconds"),
            ("lewm_scoring", "lewm_scoring_seconds"),
            ("encoding", "encoding_seconds"),
        )
    }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e16_p2_stage_c_closed_loop_shard",
        "analysis_role": "P2_continuation_method_development",
        "task": args.task,
        "arm": args.arm,
        "replicate": args.replicate,
        "learned_seed": learned_seed,
        "sage_seed": sage_seed,
        "horizon": args.horizon,
        "shard": args.shard,
        "episode_count": spec.STAGE_C_SHARD_SIZE,
        "success_count": int(successes.sum()),
        "success_rate_fraction": float(successes.mean()),
        "schedule": list(schedule),
        "schedule_cycles": cycles,
        "environment_budget": eval_budget,
        "planning_stage_count": expected_stages,
        "lewm_rollout_trajectories": rollout_trajectories,
        "active_learned_parameters": active_parameters,
        "timing": timing,
        "elapsed_seconds": elapsed,
        "metrics": jsonable(metrics),
        "model_artifacts": model_records,
        "planner_seed": planner_seed,
        "proposal_seed": proposal_seed,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "dataset_sha256": sha256_file(args.dataset),
        "p2_queries_sha256": sha256_file(args.p2_queries),
        "p2_provenance_sha256": sha256_file(args.p2_provenance),
        "p2_selection_salt": p2_provenance["selection_salt"],
        "stage_b_audit_sha256": args.stage_b_audit_sha256,
        "stage_b_source_manifest_sha256": stage_b["source_manifest_sha256"],
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest_sha256": source_manifest_sha,
        "episodes_tsv_sha256": sha256_file(episodes_path),
        "planner_diagnostics_sha256": sha256_file(diagnostics_path),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
        },
        "p2_read": True,
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
        f"{sha256_file(episodes_path)}  episodes.tsv\n"
        f"{sha256_file(diagnostics_path)}  planner-diagnostics.jsonl\n"
        f"{sha256_file(summary_path)}  summary.json\n",
    )


if __name__ == "__main__":
    main()
