#!/usr/bin/env python3
"""Run one frozen E18 task/arm/replicate/horizon/shard cell."""

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
import gdp_cem_e18_specs as spec
from gdp_cem_e15_data import sha256_file
from gdp_cem_e18_closed_loop import E18Planner
from gdp_cem_e18_inputs import load_e17_adapter
from gdp_cem_e18_runtime import E18ScheduledPolicy, load_e15_proposer


def resolve_policy_checkpoint(policy: str, stablewm_home: Path) -> Path:
    """Resolve a Stable-Worldmodel policy checkpoint within the E18 snapshot."""

    run_path = Path(policy)
    if not run_path.exists():
        run_path = stablewm_home / policy
    if run_path.is_dir():
        candidates = sorted(
            run_path.glob("*_object.ckpt"),
            key=lambda path: path.stat().st_ctime,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(f"no object checkpoint in {run_path}")
        return candidates[0].resolve()
    candidate = Path(f"{run_path}_object.ckpt")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate.resolve()


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected E18 path is forbidden: {path}")


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


def read_input_audit(
    path: Path, expected_sha256: str, source_manifest_sha256: str
) -> dict[str, Any]:
    reject_protected_path(path)
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise RuntimeError("E18 input-audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "passed"
        or value.get("kind") != "gdp_cem_e18_nonmetric_input_audit"
        or value.get("analysis_role") != "pre_outcome_lineage_validation_only"
        or value.get("e18_exploratory_study") is not True
        or value.get("e17_decision_preserved")
        != "stop_transition_adapter_preflight_failed"
        or value.get("e17_both_tasks_passed") is not False
        or value.get("e17_used_as_authorization") is not False
        or int(value.get("adapter_count", -1)) != 2
        or int(value.get("proposer_count", -1)) != 18
        or value.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != source_manifest_sha256
        or value.get("e17_audit_sha256") != spec.E17_AUDIT_SHA256
        or value.get("p2_outcomes_read") is not False
        or value.get("d5_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E18 input-audit content differs")
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
    input_audit_sha256: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    for path in (queries, provenance_path, dataset):
        reject_protected_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    task_spec = spec.TASK_SPEC[task]
    if (
        provenance.get("status") != "ok"
        or provenance.get("kind")
        != "gdp_cem_e18_fresh_shared_start_p2_manifest"
        or provenance.get("analysis_role")
        != "P2_exploratory_continuation_development"
        or provenance.get("task") != task
        or provenance.get("partition") != "P2"
        or int(provenance.get("base_start_count", -1)) != spec.BASE_STARTS
        or provenance.get("horizons") != list(spec.HORIZONS)
        or int(provenance.get("rows_per_horizon", -1)) != spec.BASE_STARTS
        or int(provenance.get("total_rows", -1))
        != spec.BASE_STARTS * len(spec.HORIZONS)
        or provenance.get("same_episode_start_pairs_across_horizons") is not True
        or provenance.get("selection_salt") != spec.SELECTION_SALT
        or int(provenance.get("excluded_old_pair_count", -1))
        != e15.GATE_C_BASE_STARTS
        or provenance.get("excluded_old_queries_sha256")
        != task_spec["p2_queries_sha256"]
        or provenance.get("excluded_old_provenance_sha256")
        != task_spec["p2_manifest_sha256"]
        or provenance.get("dataset_sha256") != task_spec["dataset_sha256"]
        or provenance.get("partition_manifest_sha256")
        != task_spec["partition_manifest_sha256"]
        or provenance.get("e17_audit_sha256") != spec.E17_AUDIT_SHA256
        or provenance.get("input_audit_sha256") != input_audit_sha256
        or provenance.get("e17_decision_preserved")
        != "stop_transition_adapter_preflight_failed"
        or provenance.get("e17_used_as_authorization") is not False
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256") != source_manifest_sha256
        or provenance.get("output_tsv_sha256") != sha256_file(queries)
        or provenance.get("p2_outcomes_read") is not False
        or provenance.get("d5_read") is not False
        or provenance.get("claim_allowed") is not False
        or sha256_file(dataset) != task_spec["dataset_sha256"]
    ):
        raise RuntimeError("E18 P2 provenance differs")
    with queries.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != spec.BASE_STARTS * len(spec.HORIZONS):
        raise RuntimeError("E18 P2 query row count differs")
    pair_sets: list[list[tuple[int, int]]] = []
    for value in spec.HORIZONS:
        group = sorted(
            [row for row in rows if int(row["goal_horizon"]) == value],
            key=lambda row: int(row["base_index"]),
        )
        if (
            len(group) != spec.BASE_STARTS
            or [int(row["base_index"]) for row in group]
            != list(range(spec.BASE_STARTS))
            or any(
                int(row["dataset_goal_step"])
                != int(row["start_step"]) + value - 1
                for row in group
            )
        ):
            raise RuntimeError("E18 P2 horizon group differs")
        pair_sets.append(
            [(int(row["episode_id"]), int(row["start_step"])) for row in group]
        )
    if any(value != pair_sets[0] for value in pair_sets[1:]):
        raise RuntimeError("E18 P2 starts differ across horizons")
    selected = sorted(
        [row for row in rows if int(row["goal_horizon"]) == horizon],
        key=lambda row: int(row["base_index"]),
    )
    start = shard * spec.SHARD_SIZE
    selected = selected[start : start + spec.SHARD_SIZE]
    if len(selected) != spec.SHARD_SIZE:
        raise RuntimeError("E18 P2 shard cardinality differs")
    return selected, provenance


def timing_summary(
    diagnostics: list[dict[str, Any]], field: str
) -> dict[str, float | None]:
    values = np.asarray(
        [float(record.get(field, 0.0)) / spec.SHARD_SIZE for record in diagnostics],
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


def validate_diagnostics(arm: str, records: list[dict[str, Any]]) -> int:
    total_rollouts = 0
    for index, record in enumerate(records):
        if (
            int(record.get("call", -1)) != index
            or record.get("arm") != arm
            or int(record.get("tau", -1)) != spec.TAU
            or int(record.get("first_candidate_count", -1))
            != spec.first_candidate_count(arm)
            or int(record.get("minimum_first_unique_candidates", -1))
            < spec.MINIMUM_FIRST_UNIQUE[arm]
            or float(record.get("strict_legal_oob_fraction", -1.0)) != 0.0
            or float(record.get("exact_legal_boundary_fraction", -1.0)) != 0.0
            or record.get("component_timing_method")
            != "cuda_events_resolved_after_outer_stage_synchronize"
        ):
            raise RuntimeError("E18 planner validity differs")
        delta = int(record["delta"])
        continuation = spec.is_continuation_arm(arm) and delta >= 2 * spec.TAU
        expected_continuations = spec.CONTINUATIONS_PER_FIRST if continuation else 0
        expected_best = spec.CONTINUATION_BEST_COUNT if continuation else 0
        expected_per_context = (
            spec.GREEDY_COMPUTE_MATCHED_CANDIDATES
            if continuation or arm == "vad_greedy_576"
            else spec.GREEDY_CANDIDATES
            if arm == "vad_greedy_300"
            else spec.FIRST_CANDIDATES
        )
        if (
            int(record.get("continuations_per_first", -1))
            != expected_continuations
            or int(record.get("continuation_best_count", -1)) != expected_best
            or int(record.get("lewm_rollout_trajectories", -1))
            != spec.SHARD_SIZE * expected_per_context
        ):
            raise RuntimeError("E18 rollout budget differs")
        second_unique = record.get("minimum_second_unique_candidates_per_first")
        state_max = record.get("predicted_state_absolute_max")
        state_q99 = record.get("predicted_state_absolute_q99")
        if continuation:
            if (
                int(second_unique) < spec.MINIMUM_SECOND_UNIQUE
                or not np.isfinite(float(state_max))
                or not np.isfinite(float(state_q99))
            ):
                raise RuntimeError("E18 continuation validity differs")
        elif second_unique is not None or state_max is not None or state_q99 is not None:
            raise RuntimeError("E18 non-continuation diagnostics differ")
        for field in (
            "end_to_end_stage_seconds",
            "proposal_and_selection_seconds",
            "adapter_seconds",
            "lewm_scoring_seconds",
            "encoding_seconds",
        ):
            value = float(record.get(field, np.nan))
            if not np.isfinite(value) or value < 0.0:
                raise RuntimeError("E18 timing differs")
        total_rollouts += int(record["lewm_rollout_trajectories"])
    return total_rollouts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--arm", choices=spec.ARMS, required=True)
    parser.add_argument("--replicate", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--horizon", type=int, choices=spec.HORIZONS, required=True)
    parser.add_argument("--shard", type=int, choices=range(spec.SHARD_COUNT), required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--e15-training-root", type=Path, required=True)
    parser.add_argument("--e17-model-root", type=Path, required=True)
    parser.add_argument("--input-audit", type=Path, required=True)
    parser.add_argument("--input-audit-sha256", required=True)
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
        args.e17_model_root,
        args.input_audit,
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
        raise RuntimeError("E18 protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E18 output")
    if not torch.cuda.is_available():
        raise RuntimeError("E18 requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E18 GPU model differs")
    source_manifest_sha = sha256_file(args.source_manifest)
    input_audit = read_input_audit(
        args.input_audit, args.input_audit_sha256, source_manifest_sha
    )
    task_spec = spec.TASK_SPEC[args.task]
    if (
        args.dataset_name != task_spec["dataset_name"]
        or args.world_model_policy != task_spec["world_model_policy"]
        or sha256_file(args.dataset) != task_spec["dataset_sha256"]
        or sha256_file(args.world_model_checkpoint)
        != task_spec["world_model_sha256"]
        or resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
        != args.world_model_checkpoint.resolve()
    ):
        raise RuntimeError("E18 released-stack identity differs")
    rows, p2_provenance = read_p2_rows(
        args.p2_queries,
        args.p2_provenance,
        task=args.task,
        horizon=args.horizon,
        shard=args.shard,
        dataset=args.dataset,
        source_manifest_sha256=source_manifest_sha,
        input_audit_sha256=args.input_audit_sha256,
    )
    learned_seed = 7200 + args.replicate
    if learned_seed != spec.MODEL_SEEDS[args.replicate - 1]:
        raise RuntimeError("E18 learned seed differs")
    planner_seed = spec.derived_seed(
        f"planner|task={args.task}|h={args.horizon}"
        f"|replicate={args.replicate}|shard={args.shard}"
    )
    proposal_seed = spec.derived_seed(
        f"proposal|task={args.task}|h={args.horizon}"
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
    cfg.world.num_envs = spec.SHARD_SIZE
    cfg.world.max_episode_steps = 2 * eval_budget
    cfg.eval.num_eval = spec.SHARD_SIZE
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
        raise RuntimeError("E18 dataset name resolves differently")
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

    family = spec.family_for_arm(args.arm)
    proposer, statistics, proposer_record = load_e15_proposer(
        args.e15_training_root,
        task=args.task,
        condition=family,
        seed=learned_seed,
        device=device,
    )
    adapter = None
    adapter_record = None
    active_parameters = int(proposer_record["parameter_count"])
    if spec.is_continuation_arm(args.arm):
        adapter, adapter_record = load_e17_adapter(
            args.e17_model_root / args.task, task=args.task, device=device
        )
        active_parameters += int(adapter_record["parameter_count"])
    model_records = {
        "e15_proposer": proposer_record,
        "e17_transition_state_adapter": adapter_record,
        "e17_failure_preserved": True,
        "e17_used_as_authorization": False,
    }
    planner = E18Planner(
        world_model,
        arm=args.arm,
        statistics=statistics,
        state_dim=int(task_spec["state_dim"]),
        primitive_action_dim=int(task_spec["primitive_action_dim"]),
        proposer=proposer,
        state_adapter=adapter,
        batch_size=1,
        proposal_seed=proposal_seed,
    )
    schedule = spec.schedule_for(args.horizon)
    policy = E18ScheduledPolicy(
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
    if successes.shape != (spec.SHARD_SIZE,):
        raise RuntimeError("E18 episode count differs")
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
            "planner_seed",
            "proposal_seed",
            "arm",
            "shard",
            "success",
        )
        writer = csv.DictWriter(
            stream, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
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
        raise RuntimeError("E18 planning-stage count differs")
    rollout_trajectories = validate_diagnostics(args.arm, planner.diagnostic_history)
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
        "kind": "gdp_cem_e18_p2_exploratory_closed_loop_shard",
        "analysis_role": "P2_exploratory_continuation_development",
        "task": args.task,
        "arm": args.arm,
        "replicate": args.replicate,
        "learned_seed": learned_seed,
        "horizon": args.horizon,
        "shard": args.shard,
        "episode_count": spec.SHARD_SIZE,
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
        "input_audit_sha256": args.input_audit_sha256,
        "e17_decision_preserved": input_audit["e17_decision_preserved"],
        "e17_used_as_authorization": False,
        "protocol_sha256": spec.PROTOCOL_SHA256,
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
