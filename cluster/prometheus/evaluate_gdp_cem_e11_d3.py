#!/usr/bin/env python3
"""Run one frozen E11 task/seed/arm/shard on untouched D3 starts."""

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
import create_gdp_cem_e11_d3_manifest as d3_manifest
import evaluate_gdp_cem_e7p_selection as e7
import evaluate_gdp_cem_e8d_closed_loop as e8d
import evaluate_gdp_cem_e10m_p1 as e10m
import evaluate_gdp_cem_e10v_p1 as e10v
import gdp_cem_e11_specs as spec
from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.io_utils import resolve_policy_checkpoint
from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    GoalConditionedProposalSampler,
    ProposalCEMSolver,
    VelocityActionDiffusion,
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
    if tokens.intersection({"c1", "i1"}):
        raise RuntimeError(f"protected C1/I1 path is forbidden: {path}")


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


def read_d3_manifest(
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
        raise RuntimeError("invalid E11 D3 manifest rows")
    if [int(row["eval_index"]) for row in rows] != list(range(spec.COUNT)):
        raise RuntimeError("E11 D3 evaluation indices differ")
    if any(
        int(row["shard_index"]) != int(row["eval_index"]) // spec.SHARD_SIZE
        or int(row["declared_goal_offset"]) != 25
        or int(row["dataset_goal_step"]) != int(row["start_step"]) + 24
        or row["selection_hash"]
        != d3_manifest.selection_hash(
            task, int(row["episode_id"]), int(row["start_step"])
        )
        for row in rows
    ):
        raise RuntimeError("E11 D3 row configuration differs")
    episodes = [int(row["episode_id"]) for row in rows]
    starts = [(int(row["episode_id"]), int(row["start_step"])) for row in rows]
    if len(set(episodes)) != spec.COUNT or len(set(starts)) != spec.COUNT:
        raise RuntimeError("E11 D3 rows are not one-start-per-episode unique")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    expected_exclusions = d3_manifest.EXPECTED_EXCLUSION_SHA256[task]
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
        or provenance.get("kind") != "gdp_cem_e11_untouched_d3_manifest"
        or provenance.get("analysis_role") != "untouched_D3_confirmation"
        or provenance.get("task") != task
        or provenance.get("count") != spec.COUNT
        or provenance.get("unique_episode_count") != spec.COUNT
        or provenance.get("partition") != "P3"
        or provenance.get("selection_seed") != 2026081709
        or provenance.get("selection_namespace") != "gdp-e11-d3"
        or provenance.get("selection_rule")
        != "lowest SHA256 start per eligible episode, then lowest 400 (digest,episode,start) records"
        or provenance.get("eligible_untouched_p3_episodes")
        != spec.UNTOUCHED_CAPACITY[task]
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
        != d3_manifest.EXPECTED_PARTITION_SHA256[task]
        or observed_exclusions != expected_exclusions
        or provenance.get("manifest_tsv_sha256") != d2.sha256_file(path)
        or provenance.get("selected_exclusion_intersections")
        != {"d1": 0, "d2": 0, "r0": 0}
        or provenance.get("identifier_inputs_only") is not True
        or provenance.get("outcome_columns_read") is not False
        or provenance.get("d3_outcomes_read") is not False
        or provenance.get("protected_c1_i1_paths_read") is not False
        or not dataset.is_file()
    ):
        raise RuntimeError("E11 D3 manifest provenance differs")
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
        raise RuntimeError("E11 D3 start/global-row lineage differs")
    start = shard * spec.SHARD_SIZE
    selected = rows[start : start + spec.SHARD_SIZE]
    if len(selected) != spec.SHARD_SIZE or any(
        int(row["shard_index"]) != shard for row in selected
    ):
        raise RuntimeError("E11 D3 shard extraction differs")
    return selected, provenance


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


def summarize_proposal_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "call_count": 0,
            "candidate_counts": [],
            "boundary_fraction_max": None,
            "mean_coordinate_std_min": None,
            "all_finite": False,
            "generator_state_before_chain_sha256": None,
            "generator_state_after_chain_sha256": None,
            "generator_state_before_sha256_values": [],
            "generator_state_after_sha256_values": [],
        }
    finite = all(
        math.isfinite(float(record["boundary_fraction"]))
        and math.isfinite(float(record["mean_coordinate_std"]))
        for record in records
    )
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
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--arm", choices=spec.ARMS, required=True)
    parser.add_argument("--model-seed", type=int, choices=spec.SEEDS, required=True)
    parser.add_argument("--shard", type=int, choices=range(spec.SHARD_COUNT), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--e10m-aggregate", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--eval-provenance", type=Path, required=True)
    parser.add_argument("--scorer-checkpoint", type=Path)
    parser.add_argument("--proposal-summary", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    required = (
        args.protocol,
        args.source_manifest,
        args.e10m_aggregate,
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
    reject_protected_path(args.output_dir)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E11 output")
    if args.arm in spec.CORE_ARMS:
        if args.scorer_checkpoint is None or args.proposal_summary is not None:
            raise ValueError("E11 core scorer arm arguments differ")
    elif args.arm in spec.PROPOSAL_ARMS:
        if args.proposal_summary is None or args.scorer_checkpoint is not None:
            raise ValueError("E11 proposal arm arguments differ")
    elif args.scorer_checkpoint is not None or args.proposal_summary is not None:
        raise ValueError("E11 B0 received a learned artifact")
    for path in (args.scorer_checkpoint, args.proposal_summary):
        if path is not None:
            reject_protected_path(path)
            if not path.is_file():
                raise FileNotFoundError(path)

    snapshot_root = Path(__file__).resolve().parent
    if (
        args.protocol.resolve()
        != (snapshot_root / "ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md").resolve()
        or args.source_manifest.resolve()
        != (snapshot_root / "SOURCE-MANIFEST.sha256").resolve()
        or d2.sha256_file(args.protocol) != spec.PROTOCOL_SHA256
    ):
        raise RuntimeError("E11 protocol/source files are not from this snapshot")
    validate_e10m(args.e10m_aggregate)
    runtime_spec = spec.TASK_SPEC[args.task]
    if (
        args.dataset_name != runtime_spec["dataset_name"]
        or args.world_model_policy != runtime_spec["world_model_policy"]
    ):
        raise RuntimeError("E11 task runtime identity differs")
    rows, manifest_provenance = read_d3_manifest(
        args.eval_manifest,
        args.eval_provenance,
        task=args.task,
        shard=args.shard,
        dataset=args.dataset,
        source_manifest=args.source_manifest,
    )

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
    torch.manual_seed(planner_seed)
    np.random.seed(planner_seed % (2**32))
    torch.cuda.manual_seed_all(planner_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E11 closed-loop evaluation requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E11 ran on an unexpected GPU model")

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.task)
    cfg.world.num_envs = spec.SHARD_SIZE
    cfg.world.max_episode_steps = 100
    cfg.eval.num_eval = spec.SHARD_SIZE
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
        raise RuntimeError("E11 dataset name resolves to a different file")
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
        raise RuntimeError("E11 world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    scorer_record = None
    proposal_record = None
    proposal_sampler = None
    action_standardization = None
    counting_cost: CountingGoalCost | None = None
    cost_model: Any
    if args.arm in spec.CORE_ARMS:
        assert args.scorer_checkpoint is not None
        expected_core_hash = spec.CORE_CHECKPOINT_SHA256[args.task][args.arm][
            seed_position
        ]
        if d2.sha256_file(args.scorer_checkpoint) != expected_core_hash:
            raise RuntimeError("E11 core scorer checkpoint hash differs")
        scorer, payload, scorer_record = d2.load_core_scorer(
            args.scorer_checkpoint,
            arm=args.arm,
            expected_seed=args.model_seed,
            device=device,
        )
        processor = process.get("action")
        if processor is None:
            raise RuntimeError("E11 has no action standardizer")
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
            planner_seed=planner_seed,
            scorer=scorer,
            payload=payload,
            horizon=5,
            record_diagnostics=True,
        ).to(device)
    else:
        counting_cost = CountingGoalCost(world_model).to(device)
        cost_model = counting_cost

    if args.arm in spec.PROPOSAL_ARMS:
        assert args.proposal_summary is not None
        if args.arm == "gaussian_select":
            condition, kind, guidance, proposal_seed = (
                "gaussian_true",
                "gaussian",
                1.0,
                gaussian_seed,
            )
        elif args.arm == "vp_shuffled_select":
            condition, kind, guidance, proposal_seed = (
                "vp_shuffled_goal",
                "velocity",
                spec.GUIDANCE_SCALE,
                velocity_seed,
            )
        elif args.arm == "vp_unconditional_select":
            condition, kind, guidance, proposal_seed = (
                "vp_true",
                "velocity",
                0.0,
                velocity_seed,
            )
        else:
            condition, kind, guidance, proposal_seed = (
                "vp_true",
                "velocity",
                spec.GUIDANCE_SCALE,
                velocity_seed,
            )
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
            inference_steps=(
                spec.REVERSE_EVALUATIONS if kind == "velocity" else 10
            ),
            schedule_steps=100,
            guidance_scale=guidance,
        )
    else:
        proposal_seed = None
        condition = None
        kind = None
        guidance = None

    plan_config = swm.PlanConfig(horizon=5, receding_horizon=5, action_block=5)
    if args.arm in spec.PROPOSAL_ARMS:
        solver: Any = ProposalCEMSolver(
            cost_model,
            proposal_sampler=proposal_sampler,
            proposal_fraction=1.0,
            refresh_mode="first",
            batch_size=1,
            num_samples=spec.CANDIDATE_COUNT,
            var_scale=1.0,
            n_steps=1,
            topk=30,
            device=device,
            seed=planner_seed,
            proposal_seed=int(proposal_seed),
            return_mode="best",
            preserve_mean_candidate=False,
        )
        integration = "pure_one_pool_selector"
    else:
        solver = swm.solver.CEMSolver(
            model=cost_model,
            batch_size=1,
            num_samples=spec.CANDIDATE_COUNT,
            var_scale=1.0,
            n_steps=30,
            topk=30,
            device=device,
            seed=planner_seed,
        )
        integration = "released_cem"
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
        "model_seed": args.model_seed,
        "shard": args.shard,
        "planner_seed": planner_seed,
        "velocity_proposal_seed": velocity_seed,
        "gaussian_proposal_seed": gaussian_seed,
        "active_proposal_seed": proposal_seed,
        "proposal_condition": condition,
        "proposal_kind": kind,
        "guidance_scale": guidance,
        "reverse_evaluations": (
            spec.REVERSE_EVALUATIONS if kind == "velocity" else None
        ),
        "integration": integration,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "cem_samples": spec.CANDIDATE_COUNT,
        "cem_steps": 1 if args.arm in spec.PROPOSAL_ARMS else 30,
        "cem_topk": 30,
        "iterations_per_planning_decision": (
            1 if args.arm in spec.PROPOSAL_ARMS else 30
        ),
        "candidate_evaluations_per_planning_decision": (
            spec.CANDIDATE_COUNT
            * (1 if args.arm in spec.PROPOSAL_ARMS else 30)
        ),
        "lambda_weight": getattr(cost_model, "lambda_weight", None),
        "action_standardization": action_standardization,
        "world": OmegaConf.to_container(cfg.world, resolve=True),
        "callables": OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
    }
    d3_manifest.atomic_json(args.output_dir / "resolved-config.json", resolved_config)

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
    if successes.shape != (spec.SHARD_SIZE,):
        raise RuntimeError("E11 evaluator returned an unexpected episode count")

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

    cost_records = getattr(cost_model, "diagnostic_history", [])
    solver_records = getattr(solver, "diagnostic_history", [])
    proposal_records = (
        proposal_sampler.diagnostic_history if proposal_sampler is not None else []
    )
    for filename, records in (
        ("cost-diagnostics.jsonl", cost_records),
        ("solver-diagnostics.jsonl", solver_records),
        ("proposal-diagnostics.jsonl", proposal_records),
    ):
        with (args.output_dir / filename).open("x", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(e8d.jsonable(record), sort_keys=True) + "\n")
    cost_calls = int(
        getattr(cost_model, "call_count", 0)
        if counting_cost is None
        else counting_cost.call_count
    )
    if cost_calls <= 0:
        raise RuntimeError("E11 recorded no Le-WM cost calls")
    proposal_seconds = float(
        sum(float(record.get("proposal_seconds", 0.0)) for record in solver_records)
    )
    proposal_diagnostics = summarize_proposal_diagnostics(proposal_records)
    iterations_per_decision = 1 if args.arm in spec.PROPOSAL_ARMS else 30
    if cost_calls % iterations_per_decision:
        raise RuntimeError("E11 cost-call count is not a whole planning budget")
    planning_decisions = cost_calls // iterations_per_decision
    if args.arm in spec.PROPOSAL_ARMS and (
        proposal_diagnostics["candidate_counts"] != [spec.CANDIDATE_COUNT]
        or proposal_diagnostics["mean_coordinate_std_min"] is None
        or proposal_diagnostics["mean_coordinate_std_min"] <= 0.0
        or proposal_diagnostics["all_finite"] is not True
        or len(solver_records) != cost_calls
        or proposal_diagnostics["call_count"] != planning_decisions
    ):
        raise RuntimeError("E11 proposal diagnostics fail finite-diversity integrity")

    summary = {
        "status": "ok",
        "kind": "gdp_cem_e11_untouched_d3_closed_loop_shard",
        "analysis_role": "untouched_D3_confirmation",
        "task": args.task,
        "arm": args.arm,
        "model_seed": args.model_seed,
        "shard": args.shard,
        "eval_index_start": args.shard * spec.SHARD_SIZE,
        "eval_index_stop": (args.shard + 1) * spec.SHARD_SIZE,
        "success_count": int(successes.sum()),
        "episode_count": spec.SHARD_SIZE,
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "proposal_seconds": proposal_seconds,
        "lewm_cost_calls": cost_calls,
        "planning_decisions": planning_decisions,
        "iterations_per_planning_decision": iterations_per_decision,
        "candidate_evaluations_per_planning_decision": (
            iterations_per_decision * spec.CANDIDATE_COUNT
        ),
        "candidate_evaluations": cost_calls * spec.CANDIDATE_COUNT,
        "metrics": e8d.jsonable(metrics),
        "proposal_diagnostics": proposal_diagnostics,
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
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
        "scorer": scorer_record,
        "proposal": proposal_record,
        "resolved_config": resolved_config,
        "episodes_tsv": str(episode_path),
        "episodes_tsv_sha256": d2.sha256_file(episode_path),
        "d3_read": True,
        "d3_outcomes_read_before_full_launch": False,
        "protected_c1_i1_read": False,
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
    d3_manifest.atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
