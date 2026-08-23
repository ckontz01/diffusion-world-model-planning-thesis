#!/usr/bin/env python3
"""Run one frozen E14 P2 Gate-C task/arm/seed/horizon/shard cell."""

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
import stable_worldmodel as swm
import stable_pretraining as spt
import torch
from omegaconf import OmegaConf
from sklearn import preprocessing
from torchvision.transforms import v2 as transforms

import gdp_cem_e14_specs as spec
from gdp_cem_e14_closed_loop import (
    E14Statistics,
    ScheduledE14Planner,
    ScheduledE14Policy,
)
from gdp_cem_e14_data import sha256_file
from gdp_cem_e14_models import (
    SAGEOptionPrior,
    SAGESubgoalGenerator,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    endpoint_output_dim,
)


TRAINING_SOURCE_MANIFEST_SHA256 = (
    "99f92cbe3c735a999866b52103241633ec80a7dffeca5217c07b0ec5590176cd"
)
OFFLINE_SOURCE_MANIFEST_SHA256 = (
    "bc27ec5c93dfae6681c149fd755d93742a0678583787bad7e3fcd43300d59cae"
)
P2_MANIFEST_SOURCE_SHA256 = (
    "33ae351fd3141b5651091a7a4bbe56939808d9af3efe81c79ec4b575ed63f269"
)


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected E14 path is forbidden: {path}")


def atomic_json(path: Path, value: object) -> None:
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


def resolve_policy_checkpoint(policy: str, stablewm_home: Path) -> Path:
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


def verify_training_directory(directory: Path) -> None:
    manifest = directory / "sha256.txt"
    expected_names = {"best.pt", "training.jsonl", "summary.json"}
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    records: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, filename = line.split(maxsplit=1)
        name = Path(filename.lstrip("* ")).name
        if name in records:
            raise RuntimeError("duplicate E14 training checksum entry")
        records[name] = digest
    if set(records) != expected_names:
        raise RuntimeError("E14 training checksum manifest differs")
    for name, digest in records.items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"E14 training artifact hash differs: {path}")


def read_gate_b(path: Path, expected_sha256: str) -> dict[str, Any]:
    reject_protected_path(path)
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise RuntimeError("E14 Gate-B audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    eligible = value.get("eligible_endpoints")
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e14_gate_b_offline_analysis"
        or value.get("analysis_role") != "P1_validation_only_Gate_B_development"
        or value.get("decision")
        != "authorize_gate_c_p2_development_for_eligible_endpoints"
        or not isinstance(eligible, list)
        or not eligible
        or any(endpoint not in ("vad", "cvd") for endpoint in eligible)
        or value.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or value.get("training_source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or value.get("source_manifest_sha256") != OFFLINE_SOURCE_MANIFEST_SHA256
        or int(value.get("artifact_count", -1)) != 32
        or value.get("d3_metric_read") is not False
        or value.get("d4_metric_read") is not False
        or value.get("d5_read") is not False
        or value.get("protected_p3_p4_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E14 Gate-B authorization differs")
    for endpoint in eligible:
        result = value.get("endpoint_results", {}).get(endpoint, {})
        if result.get("eligible_for_gate_c") is not True or not all(
            result.get("gates", {}).values()
        ):
            raise RuntimeError("E14 Gate-B eligible endpoint has a failed gate")
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
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    task_spec = spec.TASK_SPEC[task]
    if (
        provenance.get("status") != "ok"
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
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256")
        != P2_MANIFEST_SOURCE_SHA256
        or provenance.get("output_tsv_sha256") != sha256_file(queries)
        or provenance.get("d3_metric_read") is not False
        or provenance.get("d4_metric_read") is not False
        or provenance.get("d5_read") is not False
        or provenance.get("protected_p3_p4_c1_i1_read") is not False
        or provenance.get("claim_allowed") is not False
        or sha256_file(dataset) != task_spec["dataset_sha256"]
    ):
        raise RuntimeError("E14 P2 manifest provenance differs")
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
        raise RuntimeError("E14 P2 query rows differ")
    pair_sets: list[list[tuple[int, int]]] = []
    for value in spec.GATE_C_HORIZONS:
        group = [row for row in rows if int(row["goal_horizon"]) == value]
        group.sort(key=lambda row: int(row["base_index"]))
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
            raise RuntimeError("E14 P2 horizon group differs")
        pair_sets.append(
            [(int(row["episode_id"]), int(row["start_step"])) for row in group]
        )
    if any(pairs != pair_sets[0] for pairs in pair_sets[1:]):
        raise RuntimeError("E14 P2 starts differ across horizons")
    selected = [row for row in rows if int(row["goal_horizon"]) == horizon]
    selected.sort(key=lambda row: int(row["base_index"]))
    start = shard * spec.GATE_C_SHARD_SIZE
    selected = selected[start : start + spec.GATE_C_SHARD_SIZE]
    if len(selected) != spec.GATE_C_SHARD_SIZE:
        raise RuntimeError("E14 P2 shard cardinality differs")
    return selected, provenance


def endpoint_config(task: str, endpoint: str) -> dict[str, int]:
    task_spec = spec.TASK_SPEC[task]
    return {
        "latent_dim": spec.LATENT_DIM,
        "state_dim": int(task_spec["state_dim"]),
        "output_dim": endpoint_output_dim(
            endpoint,
            latent_dim=spec.LATENT_DIM,
            primitive_action_dim=int(task_spec["primitive_action_dim"]),
        ),
        "width": spec.MODEL_WIDTH,
        "depth": spec.MODEL_DEPTH,
        "time_embedding_dim": spec.TIME_EMBEDDING_DIM,
    }


def expected_training_lineage(task: str) -> dict[str, str]:
    task_spec = spec.TASK_SPEC[task]
    return {
        "latent_h5_sha256": str(task_spec["latent_sha256"]),
        "latent_manifest_sha256": str(task_spec["latent_manifest_sha256"]),
        "cache_h5_sha256": str(task_spec["e14_cache_sha256"]),
        "cache_manifest_sha256": str(task_spec["e14_cache_manifest_sha256"]),
    }


def statistics_from_payload(
    payload: dict[str, Any], *, task: str
) -> E14Statistics:
    names = (
        "latent_mean",
        "latent_std",
        "state_mean",
        "state_std",
        "action_mean",
        "action_std",
        "action_robust_low",
        "action_robust_high",
        "local_residual_mean",
        "local_residual_std",
    )
    if any(not torch.is_tensor(payload.get(name)) for name in names):
        raise RuntimeError("E14 checkpoint statistics differ")
    result = E14Statistics(**{name: payload[name].float() for name in names})
    task_spec = spec.TASK_SPEC[task]
    result.validate(
        state_dim=int(task_spec["state_dim"]),
        primitive_action_dim=int(task_spec["primitive_action_dim"]),
    )
    return result


def load_endpoint_artifact(
    training_root: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    device: torch.device,
    instantiate: bool,
) -> tuple[
    VariableVelocityDiffusion | VariableDiagonalGaussian | None,
    E14Statistics,
    dict[str, Any],
]:
    endpoint, family = condition.split("_", maxsplit=1)
    if endpoint not in ("vad", "cvd") or family not in ("true", "gaussian"):
        raise ValueError("invalid E14 Gate-C endpoint condition")
    directory = training_root / "endpoint" / task / condition / f"seed-{seed}"
    reject_protected_path(directory)
    verify_training_directory(directory)
    summary_path = directory / "summary.json"
    checkpoint = directory / "best.pt"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config = endpoint_config(task, endpoint)
    model_kind = "diagonal_gaussian" if family == "gaussian" else "velocity_diffusion"
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e14_p1_endpoint_training"
        or summary.get("analysis_role")
        != "P1_only_long_horizon_method_development"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or summary.get("endpoint") != endpoint
        or summary.get("family") != family
        or int(summary.get("seed", -1)) != seed
        or summary.get("model_kind") != model_kind
        or summary.get("model_config") != config
        or summary.get("lineage") != expected_training_lineage(task)
        or summary.get("checkpoint_sha256") != sha256_file(checkpoint)
        or Path(summary.get("checkpoint", "")).resolve() != checkpoint.resolve()
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E14 endpoint training summary differs")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if (
        payload.get("kind") != "gdp_cem_e14_p1_endpoint_checkpoint"
        or payload.get("task") != task
        or payload.get("condition") != condition
        or payload.get("endpoint") != endpoint
        or payload.get("family") != family
        or int(payload.get("seed", -1)) != seed
        or payload.get("model_kind") != model_kind
        or payload.get("model_config") != config
        or payload.get("lineage") != expected_training_lineage(task)
        or payload.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or payload.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E14 endpoint checkpoint identity differs")
    statistics = statistics_from_payload(payload, task=task)
    model: VariableVelocityDiffusion | VariableDiagonalGaussian | None = None
    if instantiate:
        model = (
            VariableDiagonalGaussian(**config)
            if family == "gaussian"
            else VariableVelocityDiffusion(**config)
        )
        model.load_state_dict(payload["ema_state_dict"], strict=True)
        model = model.to(device).eval().requires_grad_(False)
        if sum(parameter.numel() for parameter in model.parameters()) != int(
            summary["parameter_count"]
        ):
            raise RuntimeError("E14 endpoint parameter count differs")
    record = {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "condition": condition,
        "seed": seed,
        "best_step": summary["best_step"],
        "parameter_count": summary["parameter_count"],
    }
    return model, statistics, record


def sage_expected_config(task: str, component: str) -> dict[str, int]:
    task_spec = spec.TASK_SPEC[task]
    common = {
        "latent_dim": spec.LATENT_DIM,
        "state_dim": int(task_spec["state_dim"]),
        "width": 512,
        "heads": 8,
    }
    if component == "subgoal":
        return {**common, "depth": 4, "feedforward_dim": 2816}
    if component == "option":
        return {
            **common,
            "primitive_action_dim": int(task_spec["primitive_action_dim"]),
            "depth": 3,
            "feedforward_dim": 2048,
            "modes": 8,
            "action_blocks": 5,
            "block_size": 5,
        }
    raise ValueError("invalid E14 SAGE component")


def load_sage_component(
    training_root: Path,
    *,
    task: str,
    component: str,
    seed: int,
    device: torch.device,
    expected_subgoal_sha256: str | None = None,
) -> tuple[SAGESubgoalGenerator | SAGEOptionPrior, dict[str, Any]]:
    directory = training_root / "sage" / component / task / f"seed-{seed}"
    reject_protected_path(directory)
    verify_training_directory(directory)
    summary_path = directory / "summary.json"
    checkpoint = directory / "best.pt"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config = sage_expected_config(task, component)
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != f"gdp_cem_e14_sage_{component}_training"
        or summary.get("analysis_role")
        != "P1_only_published_equation_SAGE_reconstruction"
        or summary.get("official_implementation") is not False
        or summary.get("task") != task
        or summary.get("component") != component
        or int(summary.get("seed", -1)) != seed
        or summary.get("model_config") != config
        or summary.get("lineage") != expected_training_lineage(task)
        or summary.get("checkpoint_sha256") != sha256_file(checkpoint)
        or Path(summary.get("checkpoint", "")).resolve() != checkpoint.resolve()
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("subgoal_checkpoint_sha256")
        != expected_subgoal_sha256
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E14 SAGE training summary differs")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if (
        payload.get("kind") != f"gdp_cem_e14_sage_{component}_checkpoint"
        or payload.get("task") != task
        or payload.get("component") != component
        or int(payload.get("seed", -1)) != seed
        or payload.get("model_config") != config
        or payload.get("lineage") != expected_training_lineage(task)
        or payload.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or payload.get("source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or payload.get("subgoal_checkpoint_sha256")
        != expected_subgoal_sha256
    ):
        raise RuntimeError("E14 SAGE checkpoint identity differs")
    model: SAGESubgoalGenerator | SAGEOptionPrior = (
        SAGESubgoalGenerator(**config)
        if component == "subgoal"
        else SAGEOptionPrior(**config)
    )
    model.load_state_dict(payload["state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    if sum(parameter.numel() for parameter in model.parameters()) != int(
        summary["parameter_count"]
    ):
        raise RuntimeError("E14 SAGE parameter count differs")
    return model, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "component": component,
        "seed": seed,
        "best_epoch": summary["best_epoch"],
        "parameter_count": summary["parameter_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument(
        "--arm",
        choices=(
            "base_cem",
            "sage_reconstruction",
            "vad_true",
            "vad_gaussian",
            "cvd_true",
            "cvd_gaussian",
        ),
        required=True,
    )
    parser.add_argument("--model-seed", type=int, choices=spec.MODEL_SEEDS, required=True)
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
    parser.add_argument("--training-root", type=Path, required=True)
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
        args.training_root,
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
        raise RuntimeError("E14 Gate-C protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E14 Gate-C output")
    if not torch.cuda.is_available():
        raise RuntimeError("E14 Gate-C evaluation requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E14 Gate-C GPU model differs")

    gate_b = read_gate_b(args.gate_b_audit, args.gate_b_audit_sha256)
    endpoint = args.arm.split("_", maxsplit=1)[0]
    if endpoint in ("vad", "cvd") and endpoint not in gate_b["eligible_endpoints"]:
        raise RuntimeError("E14 Gate-C arm was not authorized by Gate B")

    task_spec = spec.TASK_SPEC[args.task]
    if (
        args.dataset_name != task_spec["dataset_name"]
        or args.world_model_policy != task_spec["world_model_policy"]
        or sha256_file(args.dataset) != task_spec["dataset_sha256"]
        or sha256_file(args.world_model_checkpoint)
        != task_spec["world_model_sha256"]
    ):
        raise RuntimeError("E14 Gate-C released-stack identity differs")
    resolved_checkpoint = resolve_policy_checkpoint(
        args.world_model_policy, args.stablewm_home
    )
    if resolved_checkpoint != args.world_model_checkpoint.resolve():
        raise RuntimeError("E14 Gate-C world-model policy resolves differently")
    rows, p2_provenance = read_p2_rows(
        args.p2_queries,
        args.p2_provenance,
        task=args.task,
        horizon=args.horizon,
        shard=args.shard,
        dataset=args.dataset,
    )

    planner_seed = spec.derived_seed(
        f"gate-c|planner|task={args.task}|h={args.horizon}"
        f"|seed={args.model_seed}|shard={args.shard}"
    )
    proposal_label = endpoint if endpoint in ("vad", "cvd") else args.arm
    proposal_seed = spec.derived_seed(
        f"gate-c|proposal|task={args.task}|h={args.horizon}"
        f"|seed={args.model_seed}|shard={args.shard}|family={proposal_label}"
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
    # Keep TimeLimit safely outside the measured loop, as in the released
    # StableWorldModel evaluation harness; evaluate_from_dataset still executes
    # exactly eval_budget actions.
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
        raise RuntimeError("E14 Gate-C dataset name resolves differently")
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

    endpoint_model: VariableVelocityDiffusion | VariableDiagonalGaussian | None = None
    sage_subgoal: SAGESubgoalGenerator | None = None
    sage_option: SAGEOptionPrior | None = None
    model_records: dict[str, Any] = {}
    if endpoint in ("vad", "cvd"):
        endpoint_model, statistics, record = load_endpoint_artifact(
            args.training_root,
            task=args.task,
            condition=args.arm,
            seed=args.model_seed,
            device=device,
            instantiate=True,
        )
        model_records["endpoint"] = record
    else:
        _, statistics, record = load_endpoint_artifact(
            args.training_root,
            task=args.task,
            condition="vad_true",
            seed=args.model_seed,
            device=device,
            instantiate=False,
        )
        model_records["statistics_source"] = record
        if args.arm == "sage_reconstruction":
            loaded_subgoal, subgoal_record = load_sage_component(
                args.training_root,
                task=args.task,
                component="subgoal",
                seed=args.model_seed,
                device=device,
            )
            assert isinstance(loaded_subgoal, SAGESubgoalGenerator)
            sage_subgoal = loaded_subgoal
            loaded_option, option_record = load_sage_component(
                args.training_root,
                task=args.task,
                component="option",
                seed=args.model_seed,
                device=device,
                expected_subgoal_sha256=subgoal_record["checkpoint_sha256"],
            )
            assert isinstance(loaded_option, SAGEOptionPrior)
            sage_option = loaded_option
            model_records["sage_subgoal"] = subgoal_record
            model_records["sage_option"] = option_record

    planner = ScheduledE14Planner(
        world_model,
        arm=args.arm,
        statistics=statistics,
        state_dim=int(task_spec["state_dim"]),
        primitive_action_dim=int(task_spec["primitive_action_dim"]),
        endpoint_model=endpoint_model,
        sage_subgoal=sage_subgoal,
        sage_option=sage_option,
        candidate_count=spec.CANDIDATE_COUNT,
        cem_rounds=spec.CEM_ROUNDS,
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
        raise RuntimeError("E14 Gate-C evaluator episode count differs")

    episodes_path = args.output_dir / "episodes.tsv"
    with episodes_path.open("x", newline="", encoding="utf-8") as stream:
        fields = (
            "eval_index",
            "base_index",
            "episode_id",
            "start_step",
            "task",
            "horizon",
            "model_seed",
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
                    "model_seed": args.model_seed,
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
        raise RuntimeError("E14 Gate-C planning-stage count differs")
    rounds = spec.CEM_ROUNDS if args.arm in ("base_cem", "sage_reconstruction") else 1
    expected_population_calls = (
        spec.GATE_C_SHARD_SIZE * expected_stages * rounds
    )
    population_calls = sum(
        int(record["lewm_population_calls"])
        for record in planner.diagnostic_history
    )
    if population_calls != expected_population_calls:
        raise RuntimeError("E14 Gate-C Le-WM population budget differs")
    per_context_stage_seconds = [
        float(record["planner_seconds"]) / spec.GATE_C_SHARD_SIZE
        for record in planner.diagnostic_history
    ]

    summary = {
        "status": "ok",
        "kind": "gdp_cem_e14_p2_gate_c_closed_loop_shard",
        "analysis_role": "P2_closed_loop_endpoint_selection_development",
        "task": args.task,
        "arm": args.arm,
        "model_seed": args.model_seed,
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
        "elapsed_seconds": elapsed,
        "median_planner_seconds_per_context_stage": float(
            np.median(per_context_stage_seconds)
        ),
        "mean_planner_seconds_per_context_stage": float(
            np.mean(per_context_stage_seconds)
        ),
        "metrics": jsonable(metrics),
        "model_artifacts": model_records,
        "planner_seed": planner_seed,
        "proposal_seed": proposal_seed,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(
            args.world_model_checkpoint
        ),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "p2_queries": str(args.p2_queries),
        "p2_queries_sha256": sha256_file(args.p2_queries),
        "p2_provenance": str(args.p2_provenance),
        "p2_provenance_sha256": sha256_file(args.p2_provenance),
        "p2_selection_seed": p2_provenance["selection_seed"],
        "gate_b_audit": str(args.gate_b_audit),
        "gate_b_audit_sha256": args.gate_b_audit_sha256,
        "gate_b_eligible_endpoints": gate_b["eligible_endpoints"],
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "implementation_decisions": str(args.implementation_decisions),
        "implementation_decisions_sha256": sha256_file(
            args.implementation_decisions
        ),
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
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
