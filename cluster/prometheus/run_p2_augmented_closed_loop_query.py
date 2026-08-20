#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

from execute_fixed_subgoal_candidates import (
    build_fixed_batch,
    run_world_loop_with_attainment_trace,
)
from feasibility_augmented_high_cost import (
    FeasibilityAugmentedHighCost,
    load_frozen_calibrated_ensemble,
)
from hi_acting_diagnostics import (
    ActingDiagnosticConfig,
    InstrumentedHierarchicalPolicy,
    build_context,
    build_solvers_and_configs,
    reset_world_from_batch,
)
from h_le_wm.eval.determinism import configure_process_determinism
from h_le_wm.planning.policies import calibrate_latent_prior
from score_and_select_p2_true_scorers import LATENT_DIM, MACRO_DIM, verify_inventory


POOL_COUNT = 12
P4_QUERY_COUNT = 40
GOAL_OFFSET = 75
EVAL_BUDGET = 150
HIGH_HORIZON = 2
HIGH_RECEDING_HORIZON = 1
HIGH_ACTION_BLOCK = 1
HIGH_REPLAN_INTERVAL = 5
HIGH_NUM_SAMPLES = 1200
HIGH_ITERATIONS = 60
HIGH_TOPK = 10
LOW_HORIZON = 2
LOW_RECEDING_HORIZON = 1
LOW_ACTION_BLOCK = 5
LOW_NUM_SAMPLES = 1200
LOW_ITERATIONS = 30
LOW_TOPK = 150
WEIGHTS = (0.25, 0.5, 1.0, 2.0, 4.0)
P4_LOCKED_WEIGHTS = {"M1": 2.0, "M2": 1.0, "M3": 0.25}
P4_QUERY_H5_SHA256 = "098559f55bf1e1b6cde440349e7bbe1debfd3d5441d9bf1b1e673f031c1758cd"

ENVIRONMENT_SPECS = {
    "pusht": {
        "dataset_name": "pusht_expert_train",
        "goal_offset": 75,
        "eval_budget": 150,
        "high_horizon": 2,
        "high_receding_horizon": 1,
        "high_action_block": 1,
        "high_replan_interval": 5,
        "high_num_samples": 1200,
        "high_iterations": 60,
        "high_topk": 10,
        "low_horizon": 2,
        "low_receding_horizon": 1,
        "low_action_block": 5,
        "low_num_samples": 1200,
        "low_iterations": 30,
        "low_topk": 150,
    },
    "tworoom": {
        "dataset_name": "tworoom",
        "goal_offset": 25,
        "eval_budget": 50,
        "high_horizon": 2,
        "high_receding_horizon": 1,
        "high_action_block": 1,
        "high_replan_interval": 5,
        "high_num_samples": 300,
        "high_iterations": 20,
        "high_topk": 10,
        "low_horizon": 5,
        "low_receding_horizon": 1,
        "low_action_block": 5,
        "low_num_samples": 300,
        "low_iterations": 30,
        "low_topk": 10,
    },
}


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def stack_latents(values: list[torch.Tensor]) -> np.ndarray:
    if not values:
        return np.empty((0, LATENT_DIM), dtype=np.float32)
    stacked = torch.stack([value.detach().cpu() for value in values], dim=0)
    if stacked.ndim != 3 or stacked.shape[1:] != (1, LATENT_DIM):
        raise RuntimeError(f"unexpected recorded latent shape: {tuple(stacked.shape)}")
    return stacked[:, 0, :].numpy().astype(np.float32, copy=False)


def current_info_array(info_dict: dict[str, Any], key: str) -> np.ndarray:
    value = np.asarray(info_dict[key])
    if value.ndim >= 3:
        value = value[:, -1]
    if value.shape[0] != 1:
        raise RuntimeError(f"unexpected final {key} shape: {value.shape}")
    return np.asarray(value[0], dtype=np.float32)


def validate_candidate_input(
    candidate_dir: Path,
    checkpoint_file: Path,
    environment: str,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    inventory = verify_inventory(candidate_dir)
    expected = {"candidate-pools.h5", "manifest.json", "provenance.txt"}
    if set(inventory) != expected:
        raise RuntimeError(f"unexpected candidate-pool inventory: {sorted(inventory)}")
    manifest = json.loads((candidate_dir / "manifest.json").read_text(encoding="utf-8"))
    prefix = "tworoom_" if environment == "tworoom" else ""
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification")
        != f"{prefix}p2_stratum3_b0_candidate_pools"
        or manifest.get("environment", "pusht") != environment
    ):
        raise RuntimeError("input is not the frozen P2 stratum-3 candidate artifact")
    if manifest.get("partition") != "P2" or int(manifest["seed"]) != 20260728:
        raise RuntimeError("candidate artifact partition or root seed changed")
    planner = manifest["planner"]
    if (
        int(planner["goal_offset_primitive_steps"]),
        int(planner["high_horizon"]),
        int(planner["high_action_block"]),
        int(planner["num_samples"]),
        int(planner["n_steps"]),
        int(planner["topk"]),
    ) != (
        int(spec["goal_offset"]),
        int(spec["high_horizon"]),
        int(spec["high_action_block"]),
        int(spec["high_num_samples"]),
        int(spec["high_iterations"]),
        int(spec["high_topk"]),
    ):
        raise RuntimeError("candidate artifact does not use the frozen high planner")
    if int(manifest["shapes"]["pools"]) != POOL_COUNT:
        raise RuntimeError("P2 closed-loop selection requires exactly 12 queries")
    h5_path = candidate_dir / "candidate-pools.h5"
    if inventory["candidate-pools.h5"] != manifest["output_h5_sha256"]:
        raise RuntimeError("candidate HDF5 differs from its manifest")
    if sha256_file(checkpoint_file) != manifest["inputs"]["checkpoint_sha256"]:
        raise RuntimeError("world-model checkpoint differs from candidate capture")
    return manifest, h5_path


def validate_p4_query_input(
    query_dir: Path, checkpoint_file: Path
) -> tuple[dict[str, Any], Path]:
    inventory = verify_inventory(query_dir)
    expected = {"queries.h5", "manifest.json", "provenance.txt"}
    if set(inventory) != expected:
        raise RuntimeError(f"unexpected P4 query inventory: {sorted(inventory)}")
    manifest = json.loads((query_dir / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification") != "p4_closed_loop_d75_queries"
        or manifest.get("partition") != "P4"
        or int(manifest.get("root_seed")) != 20260728
        or int(manifest.get("query_count")) != P4_QUERY_COUNT
        or int(manifest.get("goal_offset")) != GOAL_OFFSET
        or manifest.get("hash_namespace") != "p4_closed_loop"
    ):
        raise RuntimeError("input is not the frozen P4 D75 query artifact")
    h5_path = query_dir / "queries.h5"
    if (
        inventory["queries.h5"] != P4_QUERY_H5_SHA256
        or manifest.get("output_h5_sha256") != P4_QUERY_H5_SHA256
    ):
        raise RuntimeError("P4 query HDF5 differs from the frozen artifact")
    if sha256_file(checkpoint_file) != manifest["inputs"]["checkpoint_sha256"]:
        raise RuntimeError("world-model checkpoint differs from P4 query generation")
    return manifest, h5_path


def validate_p3_promotion(promotion_dir: Path, method: str) -> dict[str, Any]:
    inventory = verify_inventory(promotion_dir)
    expected = {"audit.h5", "manifest.json", "provenance.txt"}
    if set(inventory) != expected:
        raise RuntimeError(f"unexpected P3 promotion inventory: {sorted(inventory)}")
    manifest = json.loads((promotion_dir / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification") != "p3_locked_scorer_audit_and_promotion"
        or manifest.get("partition") != "P3-locked"
        or manifest.get("output_h5_sha256") != inventory["audit.h5"]
    ):
        raise RuntimeError("input is not the locked P3 promotion audit")
    promoted = manifest.get("promoted_arms")
    if not isinstance(promoted, list) or method not in promoted:
        raise RuntimeError(f"P4 execution forbidden because {method} was not promoted")
    decision = manifest.get("promotion", {}).get(method, {})
    if decision.get("promoted") is not True:
        raise RuntimeError(f"P3 promotion record is inconsistent for {method}")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--partition", choices=("P2", "P4"), default="P2")
    parser.add_argument("--promotion-dir", type=Path)
    parser.add_argument("--true-selection-dir", type=Path, required=True)
    parser.add_argument("--calibration-dir", type=Path, required=True)
    parser.add_argument("--m1-root", type=Path, required=True)
    parser.add_argument("--m2-root", type=Path, required=True)
    parser.add_argument("--m3-root", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--eval-config", type=Path, required=True)
    parser.add_argument("--method", choices=("M1", "M2", "M3"), required=True)
    parser.add_argument("--weight", type=float, choices=WEIGHTS, required=True)
    parser.add_argument("--pool-index", type=int, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--m2-batch-size", type=int, default=2048)
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    partition = args.partition
    environment = args.environment
    if partition == "P4" and environment != "pusht":
        raise SystemExit("the current P4 lock is PushT-only")
    spec = ENVIRONMENT_SPECS[environment]
    GOAL_OFFSET = int(spec["goal_offset"])
    EVAL_BUDGET = int(spec["eval_budget"])
    HIGH_HORIZON = int(spec["high_horizon"])
    HIGH_RECEDING_HORIZON = int(spec["high_receding_horizon"])
    HIGH_ACTION_BLOCK = int(spec["high_action_block"])
    HIGH_REPLAN_INTERVAL = int(spec["high_replan_interval"])
    HIGH_NUM_SAMPLES = int(spec["high_num_samples"])
    HIGH_ITERATIONS = int(spec["high_iterations"])
    HIGH_TOPK = int(spec["high_topk"])
    LOW_HORIZON = int(spec["low_horizon"])
    LOW_RECEDING_HORIZON = int(spec["low_receding_horizon"])
    LOW_ACTION_BLOCK = int(spec["low_action_block"])
    LOW_NUM_SAMPLES = int(spec["low_num_samples"])
    LOW_ITERATIONS = int(spec["low_iterations"])
    LOW_TOPK = int(spec["low_topk"])
    prefix = "tworoom_" if environment == "tworoom" else ""
    query_count = POOL_COUNT if partition == "P2" else P4_QUERY_COUNT
    output_classification = (
        f"{prefix}p2_augmented_closed_loop_weight_development"
        if partition == "P2"
        else "p4_augmented_closed_loop_confirmation"
    )
    output_partition = "P2-development-only" if partition == "P2" else "P4-locked"
    reporting_rule = (
        "used only to select a frozen arm-specific weight; not a final result"
        if partition == "P2"
        else "locked confirmation; no setting may be revised from this outcome"
    )
    if args.pool_index < 0 or args.pool_index >= query_count:
        raise SystemExit(f"{partition} query index is outside [0, {query_count})")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit(f"refusing to overwrite {partition} closed-loop output")
    if not torch.cuda.is_available():
        raise RuntimeError(f"{partition} augmented closed-loop execution requires CUDA")
    if metadata.version("stable-worldmodel") != "0.0.6":
        raise RuntimeError("closed-loop runner requires stable-worldmodel==0.0.6")
    if args.m2_batch_size != 2048:
        raise SystemExit("online M2 batch size is frozen to the calibration batch size 2048")

    promotion_manifest: dict[str, Any] | None = None
    if partition == "P4":
        if args.promotion_dir is None:
            raise SystemExit("P4 execution requires the locked P3 promotion directory")
        if args.weight != P4_LOCKED_WEIGHTS[args.method]:
            raise SystemExit(
                f"P4 {args.method} requires frozen weight {P4_LOCKED_WEIGHTS[args.method]}"
            )
        promotion_manifest = validate_p3_promotion(args.promotion_dir, args.method)
    elif args.promotion_dir is not None:
        raise SystemExit("P2 development must not read a P3 promotion artifact")

    started = time.time()
    if partition == "P2":
        candidate_manifest, candidate_h5 = validate_candidate_input(
            args.candidate_dir, args.checkpoint_file, environment, spec
        )
        input_h5_classification = f"{prefix}p2_stratum3_b0_candidate_pools"
        query_id_dataset = "pool_id"
        manifest_queries = candidate_manifest["query_selection"]["queries"]
    else:
        candidate_manifest, candidate_h5 = validate_p4_query_input(
            args.candidate_dir, args.checkpoint_file
        )
        input_h5_classification = "p4_closed_loop_d75_queries"
        query_id_dataset = "query_id"
        manifest_queries = candidate_manifest["queries"]
    with h5py.File(candidate_h5, "r") as handle:
        if handle.attrs["classification"] != input_h5_classification:
            raise RuntimeError(f"{partition} query HDF5 classification mismatch")
        pool_id = int(handle[query_id_dataset][args.pool_index])
        if pool_id != args.pool_index:
            raise RuntimeError("query IDs are not canonical")
        episode_id = int(handle["episode_id"][args.pool_index])
        source_row = int(handle["source_global_row"][args.pool_index])
        goal_row = int(handle["goal_global_row"][args.pool_index])
        source_step = int(handle["source_step"][args.pool_index])
        goal_step = int(handle["goal_step"][args.pool_index])
        planner_seed = int(handle["planner_seed"][args.pool_index])
        start_np = np.asarray(handle["z_init"][args.pool_index], dtype=np.float32)
        goal_np = np.asarray(handle["z_goal"][args.pool_index], dtype=np.float32)
    if goal_row - source_row != GOAL_OFFSET or goal_step - source_step != GOAL_OFFSET:
        raise RuntimeError("selected query has the wrong frozen goal offset")
    query_record = manifest_queries[args.pool_index]
    query_record_id = "pool_id" if partition == "P2" else "query_id"
    for key, actual in {
        query_record_id: pool_id,
        "episode_id": episode_id,
        "source_global_row": source_row,
        "goal_global_row": goal_row,
        "source_step": source_step,
        "goal_step": goal_step,
        "planner_seed": planner_seed,
    }.items():
        if int(query_record[key]) != actual:
            raise RuntimeError(f"candidate HDF5/manifest query mismatch for {key}")

    process_seed = planner_seed & ((1 << 32) - 1)
    determinism = configure_process_determinism(seed=process_seed, mode="strict")
    cfg = ActingDiagnosticConfig(
        policy=args.policy,
        experiment_kind=(
            f"{prefix}p2_augmented_closed_loop_weight_development"
            if partition == "P2"
            else "p4_augmented_closed_loop_confirmation"
        ),
        dataset_name=str(spec["dataset_name"]),
        eval_config=str(args.eval_config),
        cache_dir=str(args.stablewm_home),
        img_size=224,
        num_eval=1,
        goal_offset_steps=GOAL_OFFSET,
        eval_budget=EVAL_BUDGET,
        high_horizon=HIGH_HORIZON,
        low_horizon=LOW_HORIZON,
        low_receding_horizon=LOW_RECEDING_HORIZON,
        high_num_samples=HIGH_NUM_SAMPLES,
        high_iters=HIGH_ITERATIONS,
        high_topk=HIGH_TOPK,
        low_num_samples=LOW_NUM_SAMPLES,
        low_iters=LOW_ITERATIONS,
        low_topk=LOW_TOPK,
        frame_skip=LOW_ACTION_BLOCK,
        seed=planner_seed,
        device="cuda",
        num_reference_samples=4096,
    )
    ctx = build_context(cfg)
    device = ctx.device
    # The released diagnostics call this field ``latent_dim``, but it is
    # populated by _infer_latent_action_dim and therefore denotes the macro
    # action width, not the flattened 192-dimensional state latent.
    if int(ctx.latent_dim) != MACRO_DIM:
        raise RuntimeError(f"unexpected frozen macro-action dimension: {ctx.latent_dim}")
    if start_np.shape != (LATENT_DIM,) or goal_np.shape != (LATENT_DIM,):
        raise RuntimeError("candidate artifact state-latent shape changed")
    start_latent = torch.from_numpy(start_np[None]).to(device)
    goal_latent = torch.from_numpy(goal_np[None]).to(device)
    batch = build_fixed_batch(
        ctx=ctx,
        dataset_path=args.dataset,
        source_row=source_row,
        goal_row=goal_row,
        count=1,
        environment_seed=planner_seed,
        start_latent=start_latent,
        goal_latent=goal_latent,
        environment=environment,
    )

    eval_cfg, high_cfg, low_cfg, high_solver, low_solver = build_solvers_and_configs(ctx)
    if (
        int(high_cfg.horizon),
        int(high_cfg.receding_horizon),
        int(high_cfg.action_block),
        int(low_cfg.horizon),
        int(low_cfg.receding_horizon),
        int(low_cfg.action_block),
    ) != (
        HIGH_HORIZON,
        HIGH_RECEDING_HORIZON,
        HIGH_ACTION_BLOCK,
        LOW_HORIZON,
        LOW_RECEDING_HORIZON,
        LOW_ACTION_BLOCK,
    ):
        raise RuntimeError("released planner configuration differs from the frozen environment row")
    if not bool(getattr(high_cfg, "warm_start", True)) or not bool(
        getattr(low_cfg, "warm_start", True)
    ):
        raise RuntimeError("frozen closed-loop comparison requires released warm starts")
    if int(eval_cfg.planning.high.replan_interval) != HIGH_REPLAN_INTERVAL:
        raise RuntimeError("released high-level replan interval is not five steps")
    for solver, expected in (
        (high_solver, (HIGH_NUM_SAMPLES, HIGH_ITERATIONS, HIGH_TOPK)),
        (low_solver, (LOW_NUM_SAMPLES, LOW_ITERATIONS, LOW_TOPK)),
    ):
        if (int(solver.num_samples), int(solver.n_steps), int(solver.topk)) != expected:
            raise RuntimeError("CEM solver budget mismatch")
        if not hasattr(solver, "torch_gen") or int(solver.torch_gen.initial_seed()) != planner_seed:
            raise RuntimeError("CEM solver did not retain the recorded 63-bit query seed")

    scorer = load_frozen_calibrated_ensemble(
        method=args.method,
        true_selection_dir=args.true_selection_dir,
        calibration_dir=args.calibration_dir,
        m1_root=args.m1_root,
        m2_root=args.m2_root,
        m3_root=args.m3_root,
        noise_npy=args.noise_npy,
        noise_manifest=args.noise_manifest,
        device=device,
        m2_batch_size=args.m2_batch_size,
        environment=environment,
    )
    augmented_model = FeasibilityAugmentedHighCost(
        base_model=ctx.model,
        scorer=scorer,
        weight=args.weight,
        cem_iterations=HIGH_ITERATIONS,
        topk=HIGH_TOPK,
        environment=environment,
    )
    equivalence_candidates = torch.linspace(
        -0.75,
        0.75,
        steps=4 * HIGH_HORIZON * MACRO_DIM,
        device=device,
        dtype=start_latent.dtype,
    ).reshape(1, 4, HIGH_HORIZON, MACRO_DIM)
    nominal_equivalence = augmented_model.assert_nominal_equivalence(
        {"planner_level": "high", "z_init": start_latent, "z_goal": goal_latent},
        equivalence_candidates,
    )
    high_solver.model = augmented_model

    high_bounds = None
    if bool(eval_cfg.planning.high.latent_prior.get("enabled", True)):
        high_bounds = calibrate_latent_prior(
            model=ctx.model,
            dataset=ctx.dataset,
            cfg=eval_cfg.planning.high.latent_prior,
            process=ctx.process,
            seed=planner_seed,
        )
    policy = InstrumentedHierarchicalPolicy(
        ctx=ctx,
        high_solver=high_solver,
        low_solver=low_solver,
        high_config=high_cfg,
        low_config=low_cfg,
        macro_replan_interval=HIGH_REPLAN_INTERVAL,
        high_latent_bounds=high_bounds,
    )
    reset_world_from_batch(ctx, batch)
    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)
    execution_started = time.time()
    loop = run_world_loop_with_attainment_trace(
        ctx, batch, policy, max_steps=EVAL_BUDGET
    )
    torch.cuda.synchronize(device)
    execution_seconds = time.time() - execution_started
    peak_allocated = int(torch.cuda.max_memory_allocated(device))
    peak_reserved = int(torch.cuda.max_memory_reserved(device))

    expected_high_solves = math.ceil(EVAL_BUDGET / HIGH_REPLAN_INTERVAL)
    expected_cost_calls = expected_high_solves * HIGH_ITERATIONS
    if len(policy.high_plan_events) != expected_high_solves:
        raise RuntimeError(
            f"expected {expected_high_solves} high plans, observed {len(policy.high_plan_events)}"
        )
    if augmented_model.call_count != expected_cost_calls:
        raise RuntimeError(
            f"expected {expected_cost_calls} augmented costs, observed {augmented_model.call_count}"
        )
    if len(augmented_model.final_iteration_summaries) != expected_high_solves:
        raise RuntimeError("missing augmented-cost final-iteration summaries")
    timing = augmented_model.timing_summary()
    expected_candidate_evaluations = expected_cost_calls * HIGH_NUM_SAMPLES
    if timing["candidate_evaluations"] != expected_candidate_evaluations:
        raise RuntimeError("augmented scorer candidate-evaluation count mismatch")

    high_current = stack_latents(policy.high_plan_current_latents)
    high_goal = stack_latents(policy.high_plan_goal_latents)
    high_subgoal = stack_latents(policy.high_plan_subgoal_latents)
    low_actual = stack_latents(policy.low_block_actual_latents)
    low_subgoal = stack_latents(policy.low_block_subgoal_latents)
    step_current = stack_latents(policy.step_current_latents)
    step_subgoal = stack_latents(policy.step_subgoal_latents)
    if step_current.shape != (EVAL_BUDGET, LATENT_DIM):
        raise RuntimeError(f"unexpected step-latent trace: {step_current.shape}")
    episode_success = bool(np.asarray(loop["episode_successes"], dtype=np.bool_)[0])
    if environment == "tworoom":
        final_state = np.asarray(loop["state_trace"][-1, 0], dtype=np.float32)
        goal_state = np.asarray(batch.goal_step_np["goal_proprio"][0], dtype=np.float32)
    else:
        final_state = current_info_array(ctx.world.infos, "state")
        goal_state = current_info_array(ctx.world.infos, "goal_state")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = output_classification
            output.attrs["environment"] = environment
            output.attrs["partition"] = output_partition
            output.attrs["method"] = args.method
            output.attrs["weight"] = args.weight
            output.attrs["pool_index"] = args.pool_index
            output.attrs["episode_success"] = episode_success
            output.attrs["planner_seed"] = planner_seed
            output.create_dataset("start_latent", data=start_np)
            output.create_dataset("goal_latent", data=goal_np)
            output.create_dataset("high_plan_current_latent", data=high_current, compression="gzip")
            output.create_dataset("high_plan_goal_latent", data=high_goal, compression="gzip")
            output.create_dataset("high_plan_subgoal_latent", data=high_subgoal, compression="gzip")
            output.create_dataset("high_plan_step", data=np.asarray(policy.high_plan_steps, dtype=np.int64))
            output.create_dataset("low_block_actual_latent", data=low_actual, compression="gzip")
            output.create_dataset("low_block_subgoal_latent", data=low_subgoal, compression="gzip")
            output.create_dataset(
                "low_block_high_plan_id",
                data=np.asarray(policy.low_block_high_plan_ids, dtype=np.int64),
            )
            output.create_dataset(
                "low_block_end_step", data=np.asarray(policy.low_block_end_steps, dtype=np.int64)
            )
            output.create_dataset("step_current_latent", data=step_current, compression="gzip")
            output.create_dataset("step_subgoal_latent", data=step_subgoal, compression="gzip")
            output.create_dataset(
                "step_high_plan_id", data=np.asarray(policy.step_high_plan_ids, dtype=np.int64)
            )
            output.create_dataset("final_state", data=final_state)
            output.create_dataset("goal_state", data=goal_state)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_closed_loop_retained={partial_h5}", file=sys.stderr)
        raise

    result = {
        "status": "ok",
        "classification": output_classification,
        "environment": environment,
        "partition": output_partition,
        "reporting_rule": reporting_rule,
        "method": args.method,
        "weight": args.weight,
        "query": {
            "pool_index": args.pool_index,
            "episode_id": episode_id,
            "source_global_row": source_row,
            "goal_global_row": goal_row,
            "source_step": source_step,
            "goal_step": goal_step,
            "planner_seed_63bit": planner_seed,
            "process_seed_low32": process_seed,
        },
        "episode_success": episode_success,
        "success_rate_percent": float(loop["success_rate"]),
        "planner": {
            "eval_budget_primitive_steps": EVAL_BUDGET,
            "goal_offset_primitive_steps": GOAL_OFFSET,
            "high": {
                "horizon": HIGH_HORIZON,
                "receding_horizon": HIGH_RECEDING_HORIZON,
                "action_block": HIGH_ACTION_BLOCK,
                "replan_interval": HIGH_REPLAN_INTERVAL,
                "num_samples": HIGH_NUM_SAMPLES,
                "iterations": HIGH_ITERATIONS,
                "topk": HIGH_TOPK,
            },
            "low": {
                "horizon": LOW_HORIZON,
                "receding_horizon": LOW_RECEDING_HORIZON,
                "action_block": LOW_ACTION_BLOCK,
                "num_samples": LOW_NUM_SAMPLES,
                "iterations": LOW_ITERATIONS,
                "topk": LOW_TOPK,
            },
            "released_latent_prior_enabled": high_bounds is not None,
        },
        "cost": {
            "formula": "released squared-L2 final-goal cost + weight * mean three-seed Platt failure probability",
            "scored_transition": "current latent, first predicted subgoal, first proposed macro action",
            "nominal_equivalence": nominal_equivalence,
            "scorer_artifacts": scorer.artifact_record,
            "final_iteration_summaries": augmented_model.final_iteration_summaries,
            "timing": timing,
        },
        "diagnostics": {
            "high_plan_events": policy.high_plan_events,
            "low_block_events": policy.low_block_events,
            "step_events": policy.step_events,
            "high_plan_count": len(policy.high_plan_events),
            "low_block_count": len(policy.low_block_events),
            "step_count": len(policy.step_events),
            "final_state": final_state.tolist(),
            "goal_state": goal_state.tolist(),
        },
        "matching": {
            "shared_across_methods_and_weights": [
                "source frame",
                "goal frame",
                "environment seed",
                "high CEM seed and initial random draws",
                "low CEM seed and initial random draws",
                "planner budgets and warm-start rules",
            ],
            "adaptive_candidates_may_diverge_after_score_dependent_elite_selection": True,
        },
        "inputs": {
            "candidate_dir": str(args.candidate_dir),
            "candidate_h5_sha256": candidate_manifest["output_h5_sha256"],
            "candidate_manifest_sha256": sha256_file(args.candidate_dir / "manifest.json"),
            "dataset": str(args.dataset),
            "checkpoint_file": str(args.checkpoint_file),
            "checkpoint_sha256": candidate_manifest["inputs"]["checkpoint_sha256"],
            "eval_config": str(args.eval_config),
            "eval_config_sha256": sha256_file(args.eval_config),
        },
        "determinism": determinism,
        "runtime": {
            "python": sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "gpu": torch.cuda.get_device_name(device),
            "execution_seconds": execution_seconds,
            "peak_gpu_allocated_bytes": peak_allocated,
            "peak_gpu_reserved_bytes": peak_reserved,
            "elapsed_seconds": time.time() - started,
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
    }
    if promotion_manifest is not None:
        assert args.promotion_dir is not None
        result["inputs"]["p3_promotion_dir"] = str(args.promotion_dir)
        result["inputs"]["p3_promotion_h5_sha256"] = promotion_manifest[
            "output_h5_sha256"
        ]
        result["inputs"]["p3_promotion_manifest_sha256"] = sha256_file(
            args.promotion_dir / "manifest.json"
        )
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
