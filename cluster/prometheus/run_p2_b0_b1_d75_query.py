#!/usr/bin/env python3

from __future__ import annotations

import argparse
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
import torch
from omegaconf import OmegaConf

from execute_fixed_subgoal_candidates import build_fixed_batch
from hi_acting_diagnostics import (
    ActingDiagnosticConfig,
    InstrumentedHierarchicalPolicy,
    build_context,
    build_solvers_and_configs,
    reset_world_from_batch,
    run_world_loop,
)
from h_le_wm.eval.determinism import configure_process_determinism
from h_le_wm.planning.policies import (
    EmpiricalMacroActionSolver,
    build_empirical_macro_action_bank,
    calibrate_latent_prior,
)
from run_p2_augmented_closed_loop_query import (
    EVAL_BUDGET,
    GOAL_OFFSET,
    HIGH_ACTION_BLOCK,
    HIGH_HORIZON,
    HIGH_ITERATIONS,
    HIGH_NUM_SAMPLES,
    HIGH_RECEDING_HORIZON,
    HIGH_REPLAN_INTERVAL,
    HIGH_TOPK,
    LATENT_DIM,
    MACRO_DIM,
    LOW_ACTION_BLOCK,
    LOW_HORIZON,
    LOW_ITERATIONS,
    LOW_NUM_SAMPLES,
    LOW_RECEDING_HORIZON,
    LOW_TOPK,
    P4_QUERY_COUNT,
    POOL_COUNT,
    atomic_json,
    current_info_array,
    sha256_file,
    stack_latents,
    validate_candidate_input,
    validate_p4_query_input,
)


class CountingHighCost:
    def __init__(self, base_model: torch.nn.Module) -> None:
        self.base_model = base_model
        self.call_count = 0
        self.candidate_evaluations = 0

    @torch.inference_mode()
    def get_cost(self, info_dict: dict[str, Any], action_candidates: torch.Tensor) -> torch.Tensor:
        is_high = torch.is_tensor(info_dict.get("z_init")) and torch.is_tensor(
            info_dict.get("z_goal")
        )
        if not is_high:
            raise RuntimeError("high-level counter received a non-high planner call")
        if action_candidates.ndim != 4:
            raise RuntimeError("unexpected high-level candidate shape")
        self.call_count += 1
        self.candidate_evaluations += int(action_candidates.shape[0] * action_candidates.shape[1])
        return self.base_model.get_cost(info_dict, action_candidates)


def sha256_array(value: np.ndarray) -> str:
    import hashlib

    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
    digest.update(array.tobytes())
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--partition", choices=("P2", "P4"), default="P2")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--eval-config", type=Path, required=True)
    parser.add_argument("--arm", choices=("B0", "B1"), required=True)
    parser.add_argument("--pool-index", type=int, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    partition = args.partition
    query_count = POOL_COUNT if partition == "P2" else P4_QUERY_COUNT
    output_classification = (
        "p2_b0_b1_d75_difficulty_development"
        if partition == "P2"
        else "p4_b0_b1_d75_confirmation"
    )
    output_partition = "P2-development-only" if partition == "P2" else "P4-locked"
    reporting_rule = (
        "environment-difficulty/substitution decision only; not a final baseline estimate"
        if partition == "P2"
        else "locked baseline confirmation; no setting may be revised from this outcome"
    )
    if args.pool_index < 0 or args.pool_index >= query_count:
        raise SystemExit(f"{partition} query index is outside [0, {query_count})")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit(f"refusing to overwrite {partition} B0/B1 D75 query output")
    if not torch.cuda.is_available():
        raise RuntimeError(f"{partition} D75 baseline execution requires CUDA")
    if metadata.version("stable-worldmodel") != "0.0.6":
        raise RuntimeError("baseline runner requires stable-worldmodel==0.0.6")
    started = time.time()

    if partition == "P2":
        candidate_manifest, candidate_h5 = validate_candidate_input(
            args.candidate_dir, args.checkpoint_file
        )
        query_id_dataset = "pool_id"
        manifest_queries = candidate_manifest["query_selection"]["queries"]
    else:
        candidate_manifest, candidate_h5 = validate_p4_query_input(
            args.candidate_dir, args.checkpoint_file
        )
        query_id_dataset = "query_id"
        manifest_queries = candidate_manifest["queries"]
    with h5py.File(candidate_h5, "r") as handle:
        pool_id = int(handle[query_id_dataset][args.pool_index])
        episode_id = int(handle["episode_id"][args.pool_index])
        source_row = int(handle["source_global_row"][args.pool_index])
        goal_row = int(handle["goal_global_row"][args.pool_index])
        source_step = int(handle["source_step"][args.pool_index])
        goal_step = int(handle["goal_step"][args.pool_index])
        planner_seed = int(handle["planner_seed"][args.pool_index])
        start_np = np.asarray(handle["z_init"][args.pool_index], dtype=np.float32)
        goal_np = np.asarray(handle["z_goal"][args.pool_index], dtype=np.float32)
    if pool_id != args.pool_index or goal_row - source_row != GOAL_OFFSET:
        raise RuntimeError("invalid frozen D75 query mapping")
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
            "p2_b0_b1_d75_difficulty_development"
            if partition == "P2"
            else "p4_b0_b1_d75_confirmation"
        ),
        dataset_name="pusht_expert_train",
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
    if int(ctx.latent_dim) != MACRO_DIM:
        raise RuntimeError("frozen Hi-LeWM macro-action dimension changed")
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
    )

    eval_cfg, high_cfg, low_cfg, high_solver, low_solver = build_solvers_and_configs(ctx)
    if (
        int(high_cfg.horizon),
        int(high_cfg.receding_horizon),
        int(high_cfg.action_block),
        int(low_cfg.horizon),
        int(low_cfg.receding_horizon),
        int(low_cfg.action_block),
        int(eval_cfg.planning.high.replan_interval),
    ) != (
        HIGH_HORIZON,
        HIGH_RECEDING_HORIZON,
        HIGH_ACTION_BLOCK,
        LOW_HORIZON,
        LOW_RECEDING_HORIZON,
        LOW_ACTION_BLOCK,
        HIGH_REPLAN_INTERVAL,
    ):
        raise RuntimeError("released D75 planner configuration changed")
    if (int(low_solver.num_samples), int(low_solver.n_steps), int(low_solver.topk)) != (
        LOW_NUM_SAMPLES,
        LOW_ITERATIONS,
        LOW_TOPK,
    ) or not hasattr(low_solver, "torch_gen") or int(
        low_solver.torch_gen.initial_seed()
    ) != planner_seed:
        raise RuntimeError("low-level D75 solver configuration changed")

    counted_model = CountingHighCost(ctx.model)
    empirical_bank: dict[str, np.ndarray] | None = None
    if args.arm == "B0":
        if (int(high_solver.num_samples), int(high_solver.n_steps), int(high_solver.topk)) != (
            HIGH_NUM_SAMPLES,
            HIGH_ITERATIONS,
            HIGH_TOPK,
        ) or not hasattr(high_solver, "torch_gen") or int(
            high_solver.torch_gen.initial_seed()
        ) != planner_seed:
            raise RuntimeError("B0 high-level D75 solver configuration changed")
        high_solver.model = counted_model
    else:
        empirical_cfg = OmegaConf.create(
            {
                "enabled": True,
                "num_sequences": 4096,
                "chunk_len": 5,
                "residual_scale": 0.1,
                "min_residual_std": 0.001,
                "return_top_candidates": 8,
                "encode_batch_size": 4096,
                "stage_sampling": "sequence",
                "seed": planner_seed,
            }
        )
        empirical_bank = build_empirical_macro_action_bank(
            model=ctx.model,
            dataset=ctx.dataset,
            cfg=empirical_cfg,
            high_horizon=HIGH_HORIZON,
            high_action_block=HIGH_ACTION_BLOCK,
            process=ctx.process,
            seed=planner_seed,
        )
        if empirical_bank["actions"].shape != (4096, HIGH_HORIZON, MACRO_DIM):
            raise RuntimeError("released B1 empirical bank shape changed")
        high_solver = EmpiricalMacroActionSolver(
            model=counted_model,
            macro_bank=empirical_bank["actions"],
            batch_size=1,
            num_samples=HIGH_NUM_SAMPLES,
            var_scale=1.0,
            n_steps=HIGH_ITERATIONS,
            topk=HIGH_TOPK,
            device=device,
            seed=planner_seed,
            residual_scale=0.1,
            min_residual_std=0.001,
            return_top_candidates=8,
            stage_sampling="sequence",
        )
        if int(high_solver.torch_gen.initial_seed()) != planner_seed:
            raise RuntimeError("B1 solver did not retain the recorded 63-bit query seed")

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
    loop = run_world_loop(ctx, batch, policy, max_steps=EVAL_BUDGET)
    torch.cuda.synchronize(device)
    execution_seconds = time.time() - execution_started
    peak_allocated = int(torch.cuda.max_memory_allocated(device))
    peak_reserved = int(torch.cuda.max_memory_reserved(device))

    expected_high_solves = math.ceil(EVAL_BUDGET / HIGH_REPLAN_INTERVAL)
    expected_cost_calls = expected_high_solves * HIGH_ITERATIONS
    if len(policy.high_plan_events) != expected_high_solves:
        raise RuntimeError("baseline run emitted an unexpected number of high plans")
    if counted_model.call_count != expected_cost_calls:
        raise RuntimeError("baseline run emitted an unexpected number of high costs")
    if counted_model.candidate_evaluations != expected_cost_calls * HIGH_NUM_SAMPLES:
        raise RuntimeError("baseline high candidate-evaluation count mismatch")

    high_current = stack_latents(policy.high_plan_current_latents)
    high_goal = stack_latents(policy.high_plan_goal_latents)
    high_subgoal = stack_latents(policy.high_plan_subgoal_latents)
    low_actual = stack_latents(policy.low_block_actual_latents)
    low_subgoal = stack_latents(policy.low_block_subgoal_latents)
    step_current = stack_latents(policy.step_current_latents)
    step_subgoal = stack_latents(policy.step_subgoal_latents)
    if step_current.shape != (EVAL_BUDGET, LATENT_DIM):
        raise RuntimeError("baseline step trace is incomplete")
    episode_success = bool(np.asarray(loop["episode_successes"], dtype=np.bool_)[0])
    final_state = current_info_array(ctx.world.infos, "state")
    goal_state = current_info_array(ctx.world.infos, "goal_state")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = output_classification
            output.attrs["partition"] = output_partition
            output.attrs["arm"] = args.arm
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
            output.create_dataset("step_current_latent", data=step_current, compression="gzip")
            output.create_dataset("step_subgoal_latent", data=step_subgoal, compression="gzip")
            output.create_dataset("final_state", data=final_state)
            output.create_dataset("goal_state", data=goal_state)
            if high_bounds is not None:
                output.create_dataset("high_latent_bound_low", data=high_bounds["low"])
                output.create_dataset("high_latent_bound_high", data=high_bounds["high"])
            if empirical_bank is not None:
                output.create_dataset(
                    "empirical_macro_action_bank",
                    data=empirical_bank["actions"],
                    compression="gzip",
                )
                output.create_dataset("empirical_macro_start_row", data=empirical_bank["row_indices"])
                output.create_dataset(
                    "empirical_macro_goal_row", data=empirical_bank["goal_row_indices"]
                )
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_baseline_query_retained={partial_h5}", file=sys.stderr)
        raise

    bank_record = None
    if empirical_bank is not None:
        bank_record = {
            "actions_shape": list(empirical_bank["actions"].shape),
            "actions_sha256": sha256_array(empirical_bank["actions"]),
            "row_indices_sha256": sha256_array(empirical_bank["row_indices"]),
            "goal_row_indices_sha256": sha256_array(empirical_bank["goal_row_indices"]),
            "num_sequences": int(empirical_bank["num_sequences"]),
            "chunk_len": int(empirical_bank["chunk_len"]),
            "raw_macro_len": int(empirical_bank["raw_macro_len"]),
            "encode_batch_size": int(empirical_bank["encode_batch_size"]),
            "residual_scale": 0.1,
            "min_residual_std": 0.001,
            "return_top_candidates": 8,
            "stage_sampling": "sequence",
        }
    result = {
        "status": "ok",
        "classification": output_classification,
        "partition": output_partition,
        "reporting_rule": reporting_rule,
        "arm": args.arm,
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
                "solver": "stable_worldmodel.CEMSolver"
                if args.arm == "B0"
                else "released EmpiricalMacroActionSolver",
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
            "high_cost_calls": counted_model.call_count,
            "high_candidate_evaluations": counted_model.candidate_evaluations,
            "released_latent_prior_enabled": high_bounds is not None,
            "empirical_macro_bank": bank_record,
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
        "known_limitation": (
            "released B1 GPU path has documented same-seed non-bitwise behavior; no selective rerun"
            if args.arm == "B1"
            else None
        ),
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
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
