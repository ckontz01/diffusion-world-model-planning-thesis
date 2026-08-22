#!/usr/bin/env python3
"""Run one frozen E13 task/seed/arm/shard on untouched D4 starts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import hydra
import h5py
import numpy as np
import stable_worldmodel as swm
import torch
from omegaconf import OmegaConf
from sklearn import preprocessing

import acid_alt_d2_models as d2
import create_gdp_cem_e13_d4_manifest as d4_manifest
import evaluate_gdp_cem_e7p_selection as e7
import evaluate_gdp_cem_e8d_closed_loop as e8d
import evaluate_gdp_cem_e10m_p1 as e10m
import evaluate_gdp_cem_e10v_p1 as e10v
import gdp_cem_e13_specs as spec
from acid_alternative.io_utils import resolve_policy_checkpoint
from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    GoalConditionedProposalSampler,
    ProposalCEMSolver,
    VelocityActionDiffusion,
)
from gdp_cem_e12_prism_models import (
    PrismDPBestOfNSampler,
    PrismDPModel,
)


class CountingGoalCost(torch.nn.Module):
    """Count calls while delegating exactly to the released Le-WM cost."""

    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model
        self.call_count = 0

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        self.call_count += 1
        return self.model.get_cost(info_dict, action_candidates)


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"p4", "c1", "i1"}):
        raise RuntimeError(f"protected P4/C1/I1 path is forbidden: {path}")


def validate_e10m(path: Path) -> dict[str, Any]:
    reject_protected_path(path)
    if d2.sha256_file(path) != spec.E10M_AGGREGATE_SHA256:
        raise RuntimeError("E11 E10M prerequisite hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e10m_p1_multiseed_aggregate"
        or value.get("analysis_role")
        != "fixed_configuration_multiseed_P1_replication"
        or value.get("decision")
        != "authorize_writing_separately_frozen_untouched_data_protocol"
        or value.get("e10m_replication_pass") is not True
        or value.get("claim_allowed") is not False
        or value.get("d2_read") is not False
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
        or value.get("source_manifest_sha256")
        != spec.E10M_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E11 E10M prerequisite decision differs")
    return value


def read_d4_manifest(
    path: Path,
    provenance_path: Path,
    *,
    task: str,
    shard: int,
    dataset: Path,
    source_manifest: Path,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    for item in (path, provenance_path):
        reject_protected_path(item)
        if not item.is_file():
            raise FileNotFoundError(item)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {
        "eval_index",
        "shard_index",
        "episode_id",
        "start_step",
        "dataset_goal_step",
        "declared_goal_offset",
        "source_global_row",
        "goal_global_row",
        "selection_hash",
    }
    if len(rows) != spec.COUNT or not rows or not required.issubset(rows[0]):
        raise RuntimeError("invalid E13 D4 manifest rows")
    if [int(row["eval_index"]) for row in rows] != list(range(spec.COUNT)):
        raise RuntimeError("E13 D4 evaluation indices differ")
    if any(
        int(row["shard_index"]) != int(row["eval_index"]) // spec.SHARD_SIZE
        or int(row["declared_goal_offset"]) != 25
        or int(row["dataset_goal_step"]) != int(row["start_step"]) + 24
        or row["selection_hash"]
        != d4_manifest.selection_hash(
            task, int(row["episode_id"]), int(row["start_step"])
        )
        for row in rows
    ):
        raise RuntimeError("E13 D4 row configuration differs")
    episodes = [int(row["episode_id"]) for row in rows]
    starts = [(int(row["episode_id"]), int(row["start_step"])) for row in rows]
    if len(set(episodes)) != spec.COUNT or len(set(starts)) != spec.COUNT:
        raise RuntimeError("E13 D4 rows are not one-start-per-episode unique")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    expected_exclusions = d4_manifest.EXPECTED_EXCLUSION_SHA256[task]
    observed_exclusions = {
        label: value.get("sha256")
        for label, value in provenance.get("exclusion_manifests", {}).items()
    }
    current_stat = dataset.stat()
    current_identity = {
        "size": current_stat.st_size,
        "mtime_ns": current_stat.st_mtime_ns,
        "device": current_stat.st_dev,
        "inode": current_stat.st_ino,
        "mode": current_stat.st_mode,
    }
    if (
        provenance.get("status") != "ok"
        or provenance.get("kind") != "gdp_cem_e13_untouched_d4_manifest"
        or provenance.get("analysis_role") != "untouched_D4_confirmation"
        or provenance.get("task") != task
        or provenance.get("count") != spec.COUNT
        or provenance.get("unique_episode_count") != spec.COUNT
        or provenance.get("partition") != "P3"
        or provenance.get("selection_seed") != spec.SELECTION_SEED
        or provenance.get("selection_namespace") != spec.SELECTION_NAMESPACE
        or provenance.get("selection_rule")
        != "lowest SHA256 start per eligible episode, then lowest 400 (digest,episode,start) records"
        or provenance.get("eligible_untouched_p3_episodes")
        != spec.UNTOUCHED_P3_CAPACITY[task]
        or provenance.get("goal_offset") != 25
        or provenance.get("shard_size") != spec.SHARD_SIZE
        or provenance.get("shard_count") != spec.SHARD_COUNT
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256")
        != d2.sha256_file(source_manifest)
        or provenance.get("dataset_sha256") != spec.TASK_SPEC[task]["dataset_sha256"]
        or provenance.get("dataset_file_identity") != current_identity
        or current_stat.st_mode & 0o222
        or provenance.get("partition_manifest_sha256")
        != d4_manifest.EXPECTED_PARTITION_SHA256[task]
        or observed_exclusions != expected_exclusions
        or provenance.get("manifest_tsv_sha256") != d2.sha256_file(path)
        or provenance.get("selected_exclusion_intersections")
        != {"d1": 0, "d2": 0, "d3": 0, "r0": 0}
        or provenance.get("identifier_inputs_only") is not True
        or provenance.get("outcome_columns_read") is not False
        or provenance.get("d3_outcomes_read") is not False
        or provenance.get("d4_outcomes_read") is not False
        or provenance.get("protected_p4_c1_i1_paths_read") is not False
        or not dataset.is_file()
    ):
        raise RuntimeError("E13 D4 manifest provenance differs")
    with h5py.File(dataset, "r") as handle:
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64).reshape(-1)
    if any(
        int(row["episode_id"]) not in range(len(lengths))
        or not 0 <= int(row["start_step"]) < int(lengths[int(row["episode_id"])]) - 25
        or int(row["source_global_row"])
        != int(offsets[int(row["episode_id"])]) + int(row["start_step"])
        or int(row["goal_global_row"])
        != int(offsets[int(row["episode_id"])]) + int(row["start_step"]) + 24
        for row in rows
    ):
        raise RuntimeError("E13 D4 start/global-row lineage differs")
    start = shard * spec.SHARD_SIZE
    selected = rows[start : start + spec.SHARD_SIZE]
    if len(selected) != spec.SHARD_SIZE or any(
        int(row["shard_index"]) != shard for row in selected
    ):
        raise RuntimeError("E13 D4 shard extraction differs")
    return selected, provenance


def p1_smoke_selection_hash(task: str, episode: int, start: int) -> str:
    return hashlib.sha256(
        f"gdp-e13-p1-smoke|{task}|{episode}|{start}".encode("utf-8")
    ).hexdigest()


def read_p1_smoke_manifest(
    path: Path,
    provenance_path: Path,
    *,
    task: str,
    dataset: Path,
    source_manifest: Path,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    for item in (path, provenance_path):
        reject_protected_path(item)
        if not item.is_file():
            raise FileNotFoundError(item)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    current_stat = dataset.stat()
    identity = {
        "size": current_stat.st_size,
        "mtime_ns": current_stat.st_mtime_ns,
        "device": current_stat.st_dev,
        "inode": current_stat.st_ino,
        "mode": current_stat.st_mode,
    }
    if (
        len(rows) != 4
        or [int(row["eval_index"]) for row in rows] != list(range(4))
        or len({int(row["episode_id"]) for row in rows}) != 4
        or any(
            int(row["shard_index"]) != 0
            or int(row["dataset_goal_step"]) != int(row["start_step"]) + 24
            or row["selection_hash"]
            != p1_smoke_selection_hash(
                task, int(row["episode_id"]), int(row["start_step"])
            )
            for row in rows
        )
        or provenance.get("status") != "ok"
        or provenance.get("kind") != "gdp_cem_e13_p1_smoke_manifest"
        or provenance.get("analysis_role")
        != "non_confirmatory_P1_integration_only"
        or provenance.get("task") != task
        or provenance.get("count") != 4
        or provenance.get("partition") != "P1"
        or provenance.get("selection_namespace") != "gdp-e13-p1-smoke"
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256")
        != d2.sha256_file(source_manifest)
        or provenance.get("dataset_sha256") != spec.TASK_SPEC[task]["dataset_sha256"]
        or provenance.get("dataset_file_identity") != identity
        or provenance.get("manifest_tsv_sha256") != d2.sha256_file(path)
        or provenance.get("d3_outcomes_read") is not False
        or provenance.get("d4_read") is not False
        or provenance.get("protected_p4_c1_i1_read") is not False
        or current_stat.st_mode & 0o222
    ):
        raise RuntimeError("E13 P1 smoke manifest provenance differs")
    with h5py.File(dataset, "r") as handle:
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64).reshape(-1)
    if any(
        int(row["episode_id"]) not in range(len(lengths))
        or not 0 <= int(row["start_step"]) < int(lengths[int(row["episode_id"])]) - 25
        or int(row["source_global_row"])
        != int(offsets[int(row["episode_id"])]) + int(row["start_step"])
        or int(row["goal_global_row"])
        != int(offsets[int(row["episode_id"])]) + int(row["start_step"]) + 24
        for row in rows
    ):
        raise RuntimeError("E13 P1 smoke start/global-row lineage differs")
    return rows, provenance


def load_proposal(
    summary_path: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    device: torch.device,
) -> tuple[torch.nn.Module, dict[str, Any], dict[str, Any]]:
    reject_protected_path(summary_path)
    index = spec.seed_index(seed)
    expected_summary, expected_checkpoint = spec.PROPOSAL_ARTIFACT_SHA256[task][
        condition
    ][index]
    if d2.sha256_file(summary_path) != expected_summary:
        raise RuntimeError("E11 proposal summary hash differs")
    if seed == 6101 and condition in {"vp_true", "vp_shuffled_goal"}:
        model, payload, record = e10v.load_vp_checkpoint(
            summary_path,
            task=task,
            condition=condition,
            source_manifest_sha256=spec.E10V_SOURCE_MANIFEST_SHA256,
            device=device,
        )
    elif seed == 6101 and condition == "gaussian_true":
        model, payload, record = e7.load_checkpoint(
            summary_path,
            task=task,
            condition="gaussian_true",
            device=device,
        )
    else:
        model, payload, record = e10m.load_new_checkpoint(
            summary_path,
            task=task,
            condition=condition,
            seed=seed,
            source_manifest_sha256=spec.E10M_SOURCE_MANIFEST_SHA256,
            device=device,
        )
    if record.get("checkpoint_sha256") != expected_checkpoint:
        raise RuntimeError("E11 proposal checkpoint hash differs")
    expected_class = (
        ConditionalDiagonalGaussian
        if condition == "gaussian_true"
        else VelocityActionDiffusion
    )
    if not isinstance(model, expected_class):
        raise RuntimeError("E11 proposal checkpoint class differs")
    return model, payload, record


def load_e12_stage_b_audit(
    path: Path, *, training_source_manifest: Path
) -> dict[str, Any]:
    reject_protected_path(path)
    reject_protected_path(training_source_manifest)
    if not path.is_file() or not training_source_manifest.is_file():
        raise FileNotFoundError(path if not path.is_file() else training_source_manifest)
    audit_sha256 = d2.sha256_file(path)
    if audit_sha256 != spec.E12_STAGE_B_AUDIT_SHA256:
        raise RuntimeError("E13 E12 Stage-B audit hash differs")
    if (
        d2.sha256_file(training_source_manifest)
        != spec.E12_TRAINING_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E13 E12 training-source manifest hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    expected_failures = {
        ("reacher", seed, method)
        for seed in spec.SEEDS
        for method in ("prism_head_h25", "prism_head_endframe")
    }
    observed_failures = {
        (entry.get("task"), entry.get("seed"), entry.get("method"))
        for entry in value.get("failed_artifacts", [])
    }
    if (
        value.get("status") != "blocked"
        or value.get("kind") != "gdp_cem_e12_stage_b_validity_audit"
        or value.get("analysis_role") != "P1_only_stage_gate_audit"
        or value.get("protocol_sha256") != spec.E12_PROTOCOL_SHA256
        or value.get("training_source_manifest_sha256")
        != spec.E12_TRAINING_SOURCE_MANIFEST_SHA256
        or value.get("expected_artifact_count") != 27
        or value.get("audited_artifact_count") != 27
        or value.get("invalid_artifact_count") != 6
        or observed_failures != expected_failures
        or value.get("stage_b_passed") is not False
        or value.get("d3_outcomes_read") is not False
        or value.get("d4_outcomes_read") is not False
        or value.get("protected_p4_c1_i1_read") is not False
        or set(value.get("entries", {})) != set(spec.TASKS)
    ):
        raise RuntimeError("invalid E13 external E12 Stage-B audit")
    for task in spec.TASKS:
        task_entries = value["entries"][task]
        if set(task_entries) != {str(seed) for seed in spec.SEEDS}:
            raise RuntimeError("incomplete E13 external audit seed grid")
        for seed in spec.SEEDS:
            if set(task_entries[str(seed)]) != {
                "prism_head_h25",
                "prism_head_endframe",
                "prism_dp",
            }:
                raise RuntimeError("incomplete E13 external audit method grid")
    value["audit_sha256"] = audit_sha256
    return value


def prism_dp_artifact_entry(
    audit: dict[str, Any], *, task: str, seed: int
) -> dict[str, Any]:
    entry = audit["entries"][task][str(seed)]["prism_dp"]
    summary_path = Path(entry["summary"])
    checkpoint_path = Path(entry["checkpoint"])
    for path in (summary_path, checkpoint_path):
        reject_protected_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    if (
        (entry.get("summary_sha256"), entry.get("checkpoint_sha256"))
        != spec.PRISM_DP_ARTIFACT_SHA256[task][seed]
        or d2.sha256_file(summary_path) != entry.get("summary_sha256")
        or d2.sha256_file(checkpoint_path) != entry.get("checkpoint_sha256")
    ):
        raise RuntimeError("E13 pinned PRISM-DP artifact hash differs")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e12_prism_dp_reconstruction_training"
        or summary.get("task") != task
        or summary.get("seed") != seed
        or summary.get("checkpoint_sha256") != entry.get("checkpoint_sha256")
        or summary.get("protocol_sha256") != spec.E12_PROTOCOL_SHA256
        or summary.get("validity", {}).get("passed") is not True
        or summary.get("reconstruction_not_official") is not True
        or summary.get("d3_read") is not False
        or summary.get("d4_read") is not False
        or summary.get("protected_p4_c1_i1_read") is not False
    ):
        raise RuntimeError("invalid E13 pinned PRISM-DP artifact summary")
    return {
        **entry,
        "summary_payload": summary,
        "summary_path": summary_path,
        "checkpoint_path": checkpoint_path,
    }


def load_prism_dp(
    entry: dict[str, Any],
    *,
    task: str,
    seed: int,
    device: torch.device,
) -> tuple[PrismDPModel, dict[str, Any], dict[str, Any]]:
    payload = torch.load(entry["checkpoint_path"], map_location="cpu", weights_only=False)
    config = payload.get("model_config", {})
    if (
        payload.get("kind") != "gdp_cem_e12_prism_dp_reconstruction_checkpoint"
        or payload.get("reconstruction_not_official") is not True
        or payload.get("task") != task
        or payload.get("seed") != seed
        or payload.get("protocol_sha256") != spec.E12_PROTOCOL_SHA256
        or payload.get("validity", {}).get("passed") is not True
        or int(config.get("action_horizon", -1)) != 25
        or tuple(config.get("channels", ())) != (64, 128, 256, 512)
        or int(config.get("residual_blocks_per_level", -1)) != 3
        or int(config.get("middle_blocks", -1)) != 1
    ):
        raise RuntimeError("invalid E13 PRISM-DP reconstruction checkpoint")
    model = PrismDPModel(
        action_dim=int(config["action_dim"]),
        action_horizon=int(config["action_horizon"]),
        feature_dim=int(config["feature_dim"]),
        condition_dim=int(config["condition_dim"]),
        time_embedding_dim=int(config["time_embedding_dim"]),
        channels=tuple(int(value) for value in config["channels"]),
        residual_blocks_per_level=int(config["residual_blocks_per_level"]),
        middle_blocks=int(config["middle_blocks"]),
    ).to(device)
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    model.eval().requires_grad_(False)
    if model.num_params != int(payload["parameter_count"]):
        raise RuntimeError("E13 PRISM-DP reconstruction parameter count differs")
    record = {
        "method": "prism_dp_reconstruction",
        "reconstruction_not_official": True,
        "summary": str(entry["summary_path"]),
        "summary_sha256": entry["summary_sha256"],
        "checkpoint": str(entry["checkpoint_path"]),
        "checkpoint_sha256": entry["checkpoint_sha256"],
        "parameter_count": model.num_params,
    }
    return model, payload, record


def summarize_proposal_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "call_count": 0,
            "candidate_counts": [],
            "boundary_fraction_max": None,
            "robust_clip_fraction_max": None,
            "mean_coordinate_std_min": None,
            "all_finite": False,
            "generator_state_before_chain_sha256": None,
            "generator_state_after_chain_sha256": None,
            "generator_state_before_sha256_values": [],
            "generator_state_after_sha256_values": [],
        }
    finite = all(
        math.isfinite(float(record["boundary_fraction"]))
        and math.isfinite(
            float(record.get("robust_clip_fraction", record["boundary_fraction"]))
        )
        and math.isfinite(float(record["mean_coordinate_std"]))
        for record in records
    )
    robust_clip = [
        float(record.get("robust_clip_fraction", record["boundary_fraction"]))
        for record in records
    ]
    before_chain = "\n".join(
        record["generator_state_before_sha256"] for record in records
    ).encode("utf-8")
    after_chain = "\n".join(
        record["generator_state_after_sha256"] for record in records
    ).encode("utf-8")
    return {
        "call_count": len(records),
        "candidate_counts": sorted({int(record["candidate_count"]) for record in records}),
        "boundary_fraction_mean": float(
            np.mean([record["boundary_fraction"] for record in records])
        ),
        "boundary_fraction_max": float(
            np.max([record["boundary_fraction"] for record in records])
        ),
        "robust_clip_fraction_mean": float(np.mean(robust_clip)),
        "robust_clip_fraction_max": float(np.max(robust_clip)),
        "mean_coordinate_std_mean": float(
            np.mean([record["mean_coordinate_std"] for record in records])
        ),
        "mean_coordinate_std_min": float(
            np.min([record["mean_coordinate_std"] for record in records])
        ),
        "all_finite": finite,
        "generator_state_before_chain_sha256": hashlib.sha256(before_chain).hexdigest(),
        "generator_state_after_chain_sha256": hashlib.sha256(after_chain).hexdigest(),
        "generator_state_before_sha256_values": [
            record["generator_state_before_sha256"] for record in records
        ],
        "generator_state_after_sha256_values": [
            record["generator_state_after_sha256"] for record in records
        ],
    }


@torch.inference_mode()
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("p1_smoke", "d4"), required=True)
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--arm", choices=spec.ARMS, required=True)
    parser.add_argument("--model-seed", type=int, choices=spec.SEEDS, required=True)
    parser.add_argument("--shard", type=int, choices=range(spec.SHARD_COUNT), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--e12-stage-b-audit", type=Path, required=True)
    parser.add_argument("--e12-training-source-manifest", type=Path, required=True)
    parser.add_argument("--e10m-aggregate", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--eval-provenance", type=Path, required=True)
    parser.add_argument("--proposal-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "p1_smoke" and args.shard != 0:
        raise ValueError("E13 P1 smoke uses only shard zero")

    required = (
        args.protocol,
        args.source_manifest,
        args.e12_stage_b_audit,
        args.e12_training_source_manifest,
        args.e10m_aggregate,
        args.code_root,
        args.stablewm_home,
        args.dataset,
        args.world_model_checkpoint,
        args.eval_manifest,
        args.eval_provenance,
        args.proposal_summary,
    )
    for path in required:
        reject_protected_path(path)
        if not path.exists():
            raise FileNotFoundError(path)
    reject_protected_path(args.output_dir)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E13 output")
    snapshot_root = Path(__file__).resolve().parent
    if (
        args.protocol.resolve()
        != (snapshot_root / "ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md").resolve()
        or args.source_manifest.resolve()
        != (snapshot_root / "SOURCE-MANIFEST.sha256").resolve()
        or d2.sha256_file(args.protocol) != spec.PROTOCOL_SHA256
    ):
        raise RuntimeError("E13 protocol/source files are not from this snapshot")
    validate_e10m(args.e10m_aggregate)
    e12_audit = load_e12_stage_b_audit(
        args.e12_stage_b_audit,
        training_source_manifest=args.e12_training_source_manifest,
    )
    runtime_spec = spec.TASK_SPEC[args.task]
    if (
        args.dataset_name != runtime_spec["dataset_name"]
        or args.world_model_policy != runtime_spec["world_model_policy"]
    ):
        raise RuntimeError("E13 task runtime identity differs")
    if args.mode == "d4":
        rows, manifest_provenance = read_d4_manifest(
            args.eval_manifest,
            args.eval_provenance,
            task=args.task,
            shard=args.shard,
            dataset=args.dataset,
            source_manifest=args.source_manifest,
        )
    else:
        rows, manifest_provenance = read_p1_smoke_manifest(
            args.eval_manifest,
            args.eval_provenance,
            task=args.task,
            dataset=args.dataset,
            source_manifest=args.source_manifest,
        )
    evaluation_count = len(rows)

    seed_position = spec.seed_index(args.model_seed)
    planner_seed = spec.derived_seed(
        "planner",
        args.task,
        spec.PLANNER_BASE_SEEDS[seed_position],
        args.shard,
    )
    velocity_seed = spec.derived_seed(
        "velocity",
        args.task,
        spec.VELOCITY_BASE_SEEDS[seed_position],
        args.shard,
    )
    gaussian_seed = spec.derived_seed(
        "gaussian",
        args.task,
        spec.GAUSSIAN_BASE_SEEDS[seed_position],
        args.shard,
    )
    prism_dp_seed = spec.derived_seed(
        "prism_dp",
        args.task,
        spec.PRISM_DP_BASE_SEEDS[seed_position],
        args.shard,
    )
    torch.manual_seed(planner_seed)
    np.random.seed(planner_seed % (2**32))
    torch.cuda.manual_seed_all(planner_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E13 closed-loop evaluation requires CUDA")
    device = torch.device("cuda")
    if (
        torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME
        or platform.node() != spec.EXPECTED_HOSTNAME
    ):
        raise RuntimeError("E13 ran on an unexpected GPU or host")

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.task)
    cfg.world.num_envs = evaluation_count
    cfg.world.max_episode_steps = 100
    cfg.eval.num_eval = evaluation_count
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
        raise RuntimeError("E13 dataset name resolves to a different file")
    transform = {
        "pixels": e8d.image_transform(int(cfg.eval.img_size)),
        "goal": e8d.image_transform(int(cfg.eval.img_size)),
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
    world_model_checkpoint_sha256 = d2.sha256_file(args.world_model_checkpoint)
    if (
        resolved_checkpoint != args.world_model_checkpoint.resolve()
        or world_model_checkpoint_sha256 != runtime_spec["world_model_sha256"]
        or args.world_model_checkpoint.stat().st_mode & 0o222
    ):
        raise RuntimeError("E13 world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    proposal_record = None
    proposal_sampler = None
    counting_cost = CountingGoalCost(world_model).to(device)
    cost_model: Any = counting_cost

    active_parameter_count = 0
    second_image_encoder = False
    condition = None
    kind = None
    guidance = None
    proposal_seed: int | None = None
    if args.arm in spec.E11_SELECTOR_ARMS:
        condition = (
            "gaussian_true"
            if args.arm == "latent_gaussian_select_k300"
            else "vp_true"
        )
        kind = "gaussian" if condition == "gaussian_true" else "velocity"
        guidance = 1.0 if kind == "gaussian" else 1.5
        proposal_seed = gaussian_seed if kind == "gaussian" else velocity_seed
        proposal_model, proposal_payload, proposal_record = load_proposal(
            args.proposal_summary,
            task=args.task,
            condition=condition,
            seed=args.model_seed,
            device=device,
        )
        proposal_sampler = GoalConditionedProposalSampler(
            world_model,
            proposal_model,
            kind=kind,
            latent_mean=proposal_payload["latent_mean"],
            latent_std=proposal_payload["latent_std"],
            action_mean=proposal_payload["action_mean"],
            action_std=proposal_payload["action_std"],
            robust_low=proposal_payload["robust_low"],
            robust_high=proposal_payload["robust_high"],
            inference_steps=5 if kind == "velocity" else 10,
            schedule_steps=100,
            guidance_scale=guidance,
        )
        active_parameter_count = sum(
            parameter.numel() for parameter in proposal_model.parameters()
        )
    elif args.arm in spec.PRISM_DP_ARMS:
        # The frozen E11 velocity summary supplies the common P1 robust action
        # bounds and planner-coordinate lineage; its model is not evaluated.
        support_model, support_payload, support_record = load_proposal(
            args.proposal_summary,
            task=args.task,
            condition="vp_true",
            seed=args.model_seed,
            device=device,
        )
        del support_model
        entry = prism_dp_artifact_entry(
            e12_audit,
            task=args.task,
            seed=args.model_seed,
        )
        dp_model, dp_payload, dp_record = load_prism_dp(
            entry,
            task=args.task,
            seed=args.model_seed,
            device=device,
        )
        processor = process["action"]
        planner_mean = np.asarray(processor.mean_, dtype=np.float32)
        planner_std = np.asarray(processor.scale_, dtype=np.float32)
        robust_low_raw = (
            np.asarray(support_payload["robust_low"], dtype=np.float32) * planner_std
            + planner_mean
        )
        robust_high_raw = (
            np.asarray(support_payload["robust_high"], dtype=np.float32) * planner_std
            + planner_mean
        )
        proposal_sampler = PrismDPBestOfNSampler(
            dp_model,
            action_min=dp_payload["action_min"],
            action_max=dp_payload["action_max"],
            planner_action_mean=planner_mean,
            planner_action_std=planner_std,
            robust_low=robust_low_raw,
            robust_high=robust_high_raw,
            inference_steps=10,
            diffusion_steps=100,
        )
        condition = "h25_pixels"
        kind = "prism_dp_reconstruction"
        guidance = None
        proposal_seed = prism_dp_seed
        proposal_record = {
            **dp_record,
            "support_e11_velocity_artifact": support_record,
        }
        active_parameter_count = dp_model.num_params
        second_image_encoder = True
    else:
        raise RuntimeError("E13 arm was not assigned a proposal sampler")

    plan_config = swm.PlanConfig(horizon=5, receding_horizon=5, action_block=5)
    candidate_count = spec.CANDIDATE_COUNT[args.arm]
    iterations_per_decision = spec.ITERATIONS[args.arm]
    topk = min(30, candidate_count)
    assert proposal_sampler is not None and proposal_seed is not None
    solver: Any = ProposalCEMSolver(
        cost_model,
        proposal_sampler=proposal_sampler,
        proposal_fraction=1.0,
        refresh_mode="first",
        batch_size=1,
        num_samples=candidate_count,
        var_scale=1.0,
        n_steps=1,
        topk=topk,
        device=device,
        seed=planner_seed,
        proposal_seed=int(proposal_seed),
        return_mode="best",
        preserve_mean_candidate=False,
    )
    integration = "pure_one_pool_selector"
    policy = swm.policy.WorldModelPolicy(
        solver=solver,
        config=plan_config,
        process=process,
        transform=transform,
    )
    world.set_policy(policy)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    resolved_config = {
        "mode": args.mode,
        "task": args.task,
        "arm": args.arm,
        "model_seed": args.model_seed,
        "shard": args.shard,
        "planner_seed": planner_seed,
        "velocity_proposal_seed": velocity_seed,
        "gaussian_proposal_seed": gaussian_seed,
        "prism_dp_proposal_seed": prism_dp_seed,
        "active_proposal_seed": proposal_seed,
        "proposal_condition": condition,
        "proposal_kind": kind,
        "guidance_scale": guidance,
        "reverse_evaluations": (
            5 if kind == "velocity" else (10 if kind == "prism_dp_reconstruction" else None)
        ),
        "integration": integration,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "candidate_count": candidate_count,
        "optimizer_steps": iterations_per_decision,
        "topk": topk,
        "iterations_per_planning_decision": iterations_per_decision,
        "candidate_evaluations_per_planning_decision": (
            candidate_count * iterations_per_decision
        ),
        "active_learned_parameter_count": active_parameter_count,
        "world_model_parameter_count": sum(
            parameter.numel() for parameter in world_model.parameters()
        ),
        "total_inference_parameter_count": active_parameter_count
        + sum(parameter.numel() for parameter in world_model.parameters()),
        "requires_second_image_encoder": second_image_encoder,
        "world": OmegaConf.to_container(cfg.world, resolve=True),
        "callables": OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
    }
    d4_manifest.atomic_json(args.output_dir / "resolved-config.json", resolved_config)

    torch.cuda.reset_peak_memory_stats(device)
    started = time.time()
    metrics = world.evaluate_from_dataset(
        dataset=dataset,
        episodes_idx=[int(row["episode_id"]) for row in rows],
        start_steps=[int(row["start_step"]) for row in rows],
        goal_offset_steps=25,
        eval_budget=50,
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        save_video=False,
        video_path=args.output_dir / "videos-disabled",
    )
    torch.cuda.synchronize()
    elapsed = time.time() - started
    successes = np.asarray(metrics["episode_successes"], dtype=bool)
    if successes.shape != (evaluation_count,):
        raise RuntimeError("E13 evaluator returned an unexpected episode count")

    episode_path = args.output_dir / "episodes.tsv"
    with episode_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "eval_index",
                "shard_index",
                "episode_id",
                "start_step",
                "task",
                "model_seed",
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
                    "shard_index": args.shard,
                    "episode_id": row["episode_id"],
                    "start_step": row["start_step"],
                    "task": args.task,
                    "model_seed": args.model_seed,
                    "planner_seed": planner_seed,
                    "arm": args.arm,
                    "success": int(success),
                }
            )

    solver_records = getattr(solver, "diagnostic_history", [])
    proposal_records = proposal_sampler.diagnostic_history
    for filename, records in (
        ("solver-diagnostics.jsonl", solver_records),
        ("proposal-diagnostics.jsonl", proposal_records),
    ):
        with (args.output_dir / filename).open("x", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(e8d.jsonable(record), sort_keys=True) + "\n")
    cost_calls = int(counting_cost.call_count)
    if cost_calls <= 0:
        raise RuntimeError("E13 recorded no Le-WM cost calls")
    proposal_seconds = float(
        sum(float(record.get("proposal_seconds", 0.0)) for record in solver_records)
    )
    proposal_diagnostics = summarize_proposal_diagnostics(proposal_records)
    if cost_calls % iterations_per_decision:
        raise RuntimeError("E13 cost-call count is not a whole planning budget")
    planning_decisions = cost_calls // iterations_per_decision
    if (
        proposal_diagnostics["candidate_counts"] != [candidate_count]
        or proposal_diagnostics["mean_coordinate_std_min"] is None
        or proposal_diagnostics["mean_coordinate_std_min"] <= 0.0
        or proposal_diagnostics["all_finite"] is not True
        or len(solver_records) != cost_calls
        or proposal_diagnostics["call_count"] != planning_decisions
    ):
        raise RuntimeError("E13 proposal diagnostics fail finite-diversity integrity")

    summary = {
        "status": "ok",
        "kind": (
            "gdp_cem_e13_untouched_d4_closed_loop_shard"
            if args.mode == "d4"
            else "gdp_cem_e13_p1_integration_smoke_shard"
        ),
        "analysis_role": (
            "untouched_D4_confirmation"
            if args.mode == "d4"
            else "non_confirmatory_P1_integration_only"
        ),
        "mode": args.mode,
        "task": args.task,
        "arm": args.arm,
        "model_seed": args.model_seed,
        "shard": args.shard,
        "eval_index_start": int(rows[0]["eval_index"]),
        "eval_index_stop": int(rows[-1]["eval_index"]) + 1,
        "success_count": int(successes.sum()),
        "episode_count": evaluation_count,
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "proposal_seconds": proposal_seconds,
        "lewm_cost_calls": cost_calls,
        "planning_decisions": planning_decisions,
        "iterations_per_planning_decision": iterations_per_decision,
        "candidate_evaluations_per_planning_decision": (
            iterations_per_decision * candidate_count
        ),
        "candidate_evaluations": cost_calls * candidate_count,
        "active_learned_parameter_count": active_parameter_count,
        "world_model_parameter_count": resolved_config["world_model_parameter_count"],
        "total_inference_parameter_count": resolved_config[
            "total_inference_parameter_count"
        ],
        "requires_second_image_encoder": second_image_encoder,
        "metrics": e8d.jsonable(metrics),
        "proposal_diagnostics": proposal_diagnostics,
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "e12_stage_b_audit": str(args.e12_stage_b_audit),
        "e12_stage_b_audit_sha256": e12_audit["audit_sha256"],
        "e12_training_source_manifest": str(args.e12_training_source_manifest),
        "e12_training_source_manifest_sha256": (
            spec.E12_TRAINING_SOURCE_MANIFEST_SHA256
        ),
        "e10m_aggregate": str(args.e10m_aggregate),
        "e10m_aggregate_sha256": d2.sha256_file(args.e10m_aggregate),
        "eval_manifest": str(args.eval_manifest),
        "eval_manifest_sha256": d2.sha256_file(args.eval_manifest),
        "eval_provenance": str(args.eval_provenance),
        "eval_provenance_sha256": d2.sha256_file(args.eval_provenance),
        "manifest_dataset_sha256": manifest_provenance["dataset_sha256"],
        "dataset_file_identity": manifest_provenance["dataset_file_identity"],
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": world_model_checkpoint_sha256,
        "proposal": proposal_record,
        "resolved_config": resolved_config,
        "episodes_tsv": str(episode_path),
        "episodes_tsv_sha256": d2.sha256_file(episode_path),
        "d3_identifiers_read": args.mode == "d4",
        "d3_outcomes_read": False,
        "d4_read": args.mode == "d4",
        "d4_outcomes_read_before_full_launch": False,
        "protected_p4_c1_i1_read": False,
        "claim_allowed_per_shard": False,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
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
    }
    d4_manifest.atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
