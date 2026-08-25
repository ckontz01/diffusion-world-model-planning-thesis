#!/usr/bin/env python3
"""Run one frozen E15 P2 task/arm/replicate/horizon/shard cell."""

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

import gdp_cem_e15_specs as spec
from evaluate_gdp_cem_e14_gate_c import (
    load_endpoint_artifact,
    load_sage_component,
    resolve_policy_checkpoint,
)
from gdp_cem_e15_closed_loop import (
    E15OnePassPlanner,
    E15Statistics,
    InstrumentedE14Planner,
    ScheduledE14Policy,
)
from gdp_cem_e14_data import read_sha256_records
from gdp_cem_e15_data import sha256_file
from gdp_cem_e15_models import instantiate_model, model_config


TRAINING_SOURCE_MANIFEST_SHA256 = (
    "ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c"
)
GATE_A_SOURCE_MANIFEST_SHA256 = (
    "d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e"
)
GATE_B_ANALYZER_SOURCE_MANIFEST_SHA256 = (
    "e0fb137d34750b0c1d7e8c239d5a7b3d9c84b2c50c81d870f12aa04ff6ccc039"
)
GATE_B_EVALUATION_SOURCE_MANIFEST_SHA256 = GATE_A_SOURCE_MANIFEST_SHA256
P2_MANIFEST_SOURCE_SHA256 = (
    "33ae351fd3141b5651091a7a4bbe56939808d9af3efe81c79ec4b575ed63f269"
)
E14_PROTOCOL_SHA256 = "9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6"


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected E15 path is forbidden: {path}")


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


def read_gate_a(path: Path, expected_sha256: str) -> dict[str, Any]:
    reject_protected_path(path)
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise RuntimeError("E15 Gate-A audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "passed"
        or value.get("kind")
        != "gdp_cem_e15_gate_a_implementation_lineage_validation"
        or value.get("analysis_role") != "P1_train_only_technical_preflight"
        or len(value.get("smoke_artifacts", {})) != 22
        or len(value.get("sage_artifacts", {})) != 6
        or value.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or value.get("training_source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or value.get("source_manifest_sha256") != GATE_A_SOURCE_MANIFEST_SHA256
        or value.get("d5_read") is not False
        or value.get("protected_p3_p4_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E15 Gate-A authorization differs")
    return value


def read_gate_b(path: Path, expected_sha256: str) -> dict[str, Any]:
    reject_protected_path(path)
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise RuntimeError("E15 Gate-B audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    gates = value.get("gates", {})
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e15_gate_b_offline_analysis"
        or value.get("analysis_role") != "P1_validation_only_Gate_B_development"
        or value.get("decision")
        != "authorize_fixed_gate_c_p2_long_horizon_development"
        or value.get("gate_b_passed") is not True
        or set(gates)
        != {
            "common_bank_integrity",
            "direct_gmm_structural_validity",
            "vad_mechanism_and_conditioning",
        }
        or any(item.get("pass") is not True for item in gates.values())
        or int(value.get("artifact_count", -1)) != 22
        or value.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or value.get("training_source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or value.get("source_manifest_sha256")
        != GATE_B_ANALYZER_SOURCE_MANIFEST_SHA256
        or value.get("evaluation_source_manifest_sha256")
        != GATE_B_EVALUATION_SOURCE_MANIFEST_SHA256
        or len(gates["common_bank_integrity"].get("banks", {})) != 22
        or value.get("d5_read") is not False
        or value.get("protected_p3_p4_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E15 Gate-B authorization differs")
    return value


def read_p2_rows(
    queries: Path,
    provenance_path: Path,
    *,
    task: str,
    horizon: int,
    shard: int,
    dataset: Path,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    for path in (queries, provenance_path, dataset):
        reject_protected_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    task_spec = spec.TASK_SPEC[task]
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (
        sha256_file(queries) != task_spec["p2_queries_sha256"]
        or sha256_file(provenance_path) != task_spec["p2_manifest_sha256"]
        or provenance.get("status") != "ok"
        or provenance.get("kind")
        != "gdp_cem_e14_shared_start_p2_gate_c_manifest"
        or provenance.get("analysis_role")
        != "P2_closed_loop_endpoint_selection_development"
        or provenance.get("task") != task
        or provenance.get("partition") != "P2"
        or int(provenance.get("base_start_count", -1))
        != spec.GATE_C_BASE_STARTS
        or provenance.get("horizons") != list(spec.GATE_C_HORIZONS)
        or int(provenance.get("rows_per_horizon", -1))
        != spec.GATE_C_BASE_STARTS
        or int(provenance.get("total_rows", -1))
        != spec.GATE_C_BASE_STARTS * len(spec.GATE_C_HORIZONS)
        or provenance.get("same_episode_start_pairs_across_horizons") is not True
        or provenance.get("dataset_sha256") != task_spec["dataset_sha256"]
        or provenance.get("partition_manifest_sha256")
        != task_spec["partition_manifest_sha256"]
        or provenance.get("protocol_sha256") != E14_PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256") != P2_MANIFEST_SOURCE_SHA256
        or provenance.get("output_tsv_sha256") != sha256_file(queries)
        or provenance.get("d5_read") is not False
        or provenance.get("protected_p3_p4_c1_i1_read") is not False
        or provenance.get("claim_allowed") is not False
        or sha256_file(dataset) != task_spec["dataset_sha256"]
    ):
        raise RuntimeError("E15 frozen P2 manifest provenance differs")
    with queries.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    expected_fields = {
        "eval_index",
        "base_index",
        "episode_id",
        "start_step",
        "goal_horizon",
        "dataset_goal_step",
        "source_global_row",
        "goal_global_row",
        "selection_hash",
    }
    if len(rows) != spec.GATE_C_BASE_STARTS * len(spec.GATE_C_HORIZONS) or (
        not rows or set(rows[0]) != expected_fields
    ):
        raise RuntimeError("E15 P2 query rows differ")
    pair_sets = []
    for value in spec.GATE_C_HORIZONS:
        group = sorted(
            [row for row in rows if int(row["goal_horizon"]) == value],
            key=lambda row: int(row["base_index"]),
        )
        if (
            len(group) != spec.GATE_C_BASE_STARTS
            or [int(row["base_index"]) for row in group]
            != list(range(spec.GATE_C_BASE_STARTS))
            or any(
                int(row["dataset_goal_step"])
                != int(row["start_step"]) + value - 1
                for row in group
            )
        ):
            raise RuntimeError("E15 P2 horizon group differs")
        pair_sets.append(
            [(int(row["episode_id"]), int(row["start_step"])) for row in group]
        )
    if any(value != pair_sets[0] for value in pair_sets[1:]):
        raise RuntimeError("E15 P2 starts differ across horizons")
    selected = sorted(
        [row for row in rows if int(row["goal_horizon"]) == horizon],
        key=lambda row: int(row["base_index"]),
    )
    start = shard * spec.GATE_C_SHARD_SIZE
    selected = selected[start : start + spec.GATE_C_SHARD_SIZE]
    if len(selected) != spec.GATE_C_SHARD_SIZE:
        raise RuntimeError("E15 P2 shard cardinality differs")
    return selected, provenance


def verify_training_directory(directory: Path) -> None:
    records = read_sha256_records(directory / "sha256.txt")
    if set(records) != {"final.pt", "training.jsonl", "summary.json"}:
        raise RuntimeError("E15 training checksum names differ")
    for name, digest in records.items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError("E15 training checksum differs")


def e15_statistics(payload: dict[str, Any], *, task: str) -> E15Statistics:
    values = payload.get("statistics", {})
    tensor_names = (
        "latent_mean",
        "latent_std",
        "state_mean",
        "state_std",
        "u_mean",
        "u_std",
        "planner_action_mean",
        "planner_action_std",
    )
    if set(values) != {*tensor_names, "interior_scale", "target_raw_limit"} or any(
        not torch.is_tensor(values.get(name)) for name in tensor_names
    ):
        raise RuntimeError("E15 online checkpoint statistics differ")
    result = E15Statistics(
        **{name: values[name].float() for name in tensor_names},
        interior_scale=float(values["interior_scale"]),
        target_raw_limit=float(values["target_raw_limit"]),
    )
    task_spec = spec.TASK_SPEC[task]
    result.validate(
        state_dim=int(task_spec["state_dim"]),
        primitive_action_dim=int(task_spec["primitive_action_dim"]),
    )
    return result


def load_e15_proposer(
    training_root: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    device: torch.device,
) -> tuple[torch.nn.Module, E15Statistics, dict[str, Any]]:
    directory = training_root / task / condition / f"seed-{seed}"
    reject_protected_path(directory)
    verify_training_directory(directory)
    summary_path = directory / "summary.json"
    checkpoint_path = directory / "final.pt"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config = model_config(task, condition)
    expected_lineage = {
        "latent_h5_sha256": spec.TASK_SPEC[task]["latent_sha256"],
        "latent_manifest_sha256": spec.TASK_SPEC[task]["latent_manifest_sha256"],
        "cache_h5_sha256": spec.TASK_SPEC[task]["e15_cache_sha256"],
        "cache_manifest_sha256": spec.TASK_SPEC[task]["e15_cache_manifest_sha256"],
    }
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e15_p1_final_proposer_training"
        or summary.get("analysis_role")
        != "P1_train_only_long_horizon_method_development"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or int(summary.get("seed", -1)) != seed
        or summary.get("model_config") != config
        or summary.get("lineage") != expected_lineage
        or summary.get("checkpoint_selection")
        != "fixed_final_ema_step_30000_no_validation_access"
        or summary.get("checkpoint_sha256") != sha256_file(checkpoint_path)
        or int(summary.get("validation_payload_rows_read", -1)) != 0
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E15 proposer training summary differs")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if (
        payload.get("kind") != "gdp_cem_e15_p1_final_proposer_checkpoint"
        or payload.get("task") != task
        or payload.get("condition") != condition
        or int(payload.get("seed", -1)) != seed
        or payload.get("model_config") != config
        or payload.get("lineage") != expected_lineage
        or int(payload.get("final_step", -1)) != spec.TRAIN_STEPS
        or int(payload.get("validation_payload_rows_read", -1)) != 0
        or payload.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or payload.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E15 proposer checkpoint identity differs")
    statistics = e15_statistics(payload, task=task)
    model = instantiate_model(task, condition)
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != int(summary.get("parameter_count", -1)):
        raise RuntimeError("E15 proposer parameter count differs")
    return model, statistics, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "condition": condition,
        "seed": seed,
        "parameter_count": parameter_count,
    }


def timing_summary(
    diagnostics: list[dict[str, Any]], field: str
) -> dict[str, float | None]:
    values = np.asarray(
        [float(record[field]) / spec.GATE_C_SHARD_SIZE for record in diagnostics],
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
    parser.add_argument("--arm", choices=spec.ARMS, required=True)
    parser.add_argument("--replicate", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--horizon", type=int, choices=spec.GATE_C_HORIZONS, required=True)
    parser.add_argument(
        "--shard", type=int, choices=range(spec.GATE_C_SHARD_COUNT), required=True
    )
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--e15-training-root", type=Path, required=True)
    parser.add_argument("--sage-normalized-root", type=Path, required=True)
    parser.add_argument("--gate-a-audit", type=Path, required=True)
    parser.add_argument("--gate-a-audit-sha256", required=True)
    parser.add_argument("--gate-b-audit", type=Path, required=True)
    parser.add_argument("--gate-b-audit-sha256", required=True)
    parser.add_argument("--p2-queries", type=Path, required=True)
    parser.add_argument("--p2-provenance", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--implementation-decisions", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.code_root,
        args.stablewm_home,
        args.dataset,
        args.world_model_checkpoint,
        args.e15_training_root,
        args.sage_normalized_root,
        args.gate_a_audit,
        args.gate_b_audit,
        args.p2_queries,
        args.p2_provenance,
        args.protocol,
        args.implementation_decisions,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E15 Gate-C protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E15 Gate-C output")
    if not torch.cuda.is_available():
        raise RuntimeError("E15 Gate-C requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E15 Gate-C GPU model differs")
    gate_a = read_gate_a(args.gate_a_audit, args.gate_a_audit_sha256)
    gate_b = read_gate_b(args.gate_b_audit, args.gate_b_audit_sha256)
    task_spec = spec.TASK_SPEC[args.task]
    if (
        args.dataset_name != task_spec["dataset_name"]
        or args.world_model_policy != task_spec["world_model_policy"]
        or sha256_file(args.dataset) != task_spec["dataset_sha256"]
        or sha256_file(args.world_model_checkpoint)
        != task_spec["world_model_sha256"]
        or resolve_policy_checkpoint(
            args.world_model_policy, args.stablewm_home
        )
        != args.world_model_checkpoint.resolve()
    ):
        raise RuntimeError("E15 Gate-C released-stack identity differs")
    rows, p2_provenance = read_p2_rows(
        args.p2_queries,
        args.p2_provenance,
        task=args.task,
        horizon=args.horizon,
        shard=args.shard,
        dataset=args.dataset,
    )
    learned_seed = 7200 + args.replicate
    sage_seed = 6100 + args.replicate
    planner_seed = spec.derived_seed(
        f"gate-c|planner|task={args.task}|h={args.horizon}"
        f"|replicate={args.replicate}|shard={args.shard}"
    )
    proposal_seed = spec.derived_seed(
        f"gate-c|proposal|task={args.task}|h={args.horizon}"
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
    cfg.world.num_envs = spec.GATE_C_SHARD_SIZE
    cfg.world.max_episode_steps = 2 * eval_budget
    cfg.eval.num_eval = spec.GATE_C_SHARD_SIZE
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
        raise RuntimeError("E15 Gate-C dataset name resolves differently")
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
    proposal_components = 0
    if args.arm in ("vad", "direct_gmm", "diagonal_gaussian"):
        proposer, statistics, record = load_e15_proposer(
            args.e15_training_root,
            task=args.task,
            condition=args.arm,
            seed=learned_seed,
            device=device,
        )
        model_records["e15_proposer"] = record
        active_parameters = int(record["parameter_count"])
        proposal_components = 1
        planner: Any = E15OnePassPlanner(
            world_model,
            arm=args.arm,
            statistics=statistics,
            state_dim=int(task_spec["state_dim"]),
            primitive_action_dim=int(task_spec["primitive_action_dim"]),
            proposer=proposer,
            candidate_count=spec.CANDIDATE_COUNT,
            batch_size=1,
            proposal_seed=proposal_seed,
        )
    else:
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
        if args.arm in ("sage_reconstruction", "sage_one_stage"):
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
            proposal_components = 2
        rounds = 30 if args.arm in ("base_cem", "sage_reconstruction") else 1
        planner = InstrumentedE14Planner(
            world_model,
            reported_arm=args.arm,
            one_stage=args.arm == "sage_one_stage",
            statistics=e14_statistics,
            state_dim=int(task_spec["state_dim"]),
            primitive_action_dim=int(task_spec["primitive_action_dim"]),
            sage_subgoal=sage_subgoal,
            sage_option=sage_option,
            candidate_count=spec.CANDIDATE_COUNT,
            cem_rounds=rounds,
            elites=spec.CEM_ELITES,
            batch_size=1,
            planner_seed=planner_seed,
            proposal_seed=proposal_seed,
        )
    schedule = spec.schedule_for(args.horizon)
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
    if successes.shape != (spec.GATE_C_SHARD_SIZE,):
        raise RuntimeError("E15 Gate-C evaluator episode count differs")
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
        raise RuntimeError("E15 Gate-C planning-stage count differs")
    rounds = 30 if args.arm in ("base_cem", "sage_reconstruction") else 1
    expected_population_calls = (
        spec.GATE_C_SHARD_SIZE * expected_stages * rounds
    )
    population_calls = sum(
        int(record["lewm_population_calls"])
        for record in planner.diagnostic_history
    )
    if population_calls != expected_population_calls:
        raise RuntimeError("E15 Gate-C Le-WM population budget differs")
    timing = {
        "end_to_end": timing_summary(
            planner.diagnostic_history, "end_to_end_stage_seconds"
        ),
        "proposal_and_selection": timing_summary(
            planner.diagnostic_history, "proposal_and_selection_seconds"
        ),
        "lewm_scoring": timing_summary(
            planner.diagnostic_history, "lewm_scoring_seconds"
        ),
        "encoding": timing_summary(planner.diagnostic_history, "encoding_seconds"),
    }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e15_p2_gate_c_closed_loop_shard",
        "analysis_role": "P2_long_horizon_method_selection_development",
        "task": args.task,
        "arm": args.arm,
        "replicate": args.replicate,
        "learned_seed": learned_seed,
        "sage_seed": sage_seed,
        "horizon": args.horizon,
        "shard": args.shard,
        "episode_count": spec.GATE_C_SHARD_SIZE,
        "success_count": int(successes.sum()),
        "success_rate_fraction": float(successes.mean()),
        "schedule": list(schedule),
        "schedule_cycles": cycles,
        "environment_budget": eval_budget,
        "candidate_count": spec.CANDIDATE_COUNT,
        "cem_rounds_per_stage": rounds,
        "cem_elites": spec.CEM_ELITES,
        "planning_stage_count": expected_stages,
        "lewm_population_calls": population_calls,
        "candidate_evaluations": population_calls * spec.CANDIDATE_COUNT,
        "active_learned_parameters": active_parameters,
        "learned_proposal_component_count": proposal_components,
        "timing": timing,
        "elapsed_seconds": elapsed,
        "metrics": jsonable(metrics),
        "model_artifacts": model_records,
        "planner_seed": planner_seed,
        "proposal_seed": proposal_seed,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "p2_queries": str(args.p2_queries),
        "p2_queries_sha256": sha256_file(args.p2_queries),
        "p2_provenance": str(args.p2_provenance),
        "p2_provenance_sha256": sha256_file(args.p2_provenance),
        "p2_selection_seed": p2_provenance["selection_seed"],
        "gate_a_audit": str(args.gate_a_audit),
        "gate_a_audit_sha256": args.gate_a_audit_sha256,
        "gate_b_audit": str(args.gate_b_audit),
        "gate_b_audit_sha256": args.gate_b_audit_sha256,
        "gate_b_decision": gate_b["decision"],
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "implementation_decisions": str(args.implementation_decisions),
        "implementation_decisions_sha256": sha256_file(args.implementation_decisions),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "episodes_tsv": str(episodes_path),
        "episodes_tsv_sha256": sha256_file(episodes_path),
        "planner_diagnostics": str(diagnostics_path),
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
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
