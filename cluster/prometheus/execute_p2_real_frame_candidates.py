#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

from execute_fixed_subgoal_candidates import (
    ATTAINMENT_HORIZON,
    CommonRandomNumbersCEMSolver,
    atomic_json,
    repeat_seeds,
    run_world_loop_with_attainment_trace,
    sha256_file,
    solver_equivalence_self_test,
)
from hi_acting_diagnostics import (
    ActingDiagnosticConfig,
    InstrumentedStagePolicy,
    PreparedBatch,
    build_context,
    reset_world_from_batch,
)
from h_le_wm.eval.determinism import configure_process_determinism


CANDIDATE_COUNT = 64
STRATA = ("same_trajectory_delta25", "cross_trajectory")


def safe_h5_rows(dataset: h5py.Dataset, rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.int64)
    order = np.argsort(rows, kind="mergesort")
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    return np.asarray(dataset[rows[order]])[inverse]


def build_varied_batch(
    *,
    ctx: Any,
    dataset_path: Path,
    source_rows: np.ndarray,
    target_rows: np.ndarray,
    environment_seed: int,
    start_latent: torch.Tensor,
    goal_latent: torch.Tensor,
    environment: str,
) -> PreparedBatch:
    source_rows = np.asarray(source_rows, dtype=np.int64)
    target_rows = np.asarray(target_rows, dtype=np.int64)
    if source_rows.shape != target_rows.shape or source_rows.ndim != 1:
        raise RuntimeError("source and target row arrays must be matching 1D arrays")
    count = len(source_rows)
    with h5py.File(dataset_path, "r") as handle:
        if environment == "pusht":
            keys = ("pixels", "action", "proprio", "state", "episode_idx", "step_idx")
            episode_key = "episode_idx"
        else:
            keys = ("pixels", "action", "proprio", "ep_idx", "step_idx")
            episode_key = "ep_idx"
        missing = [key for key in keys if key not in handle]
        if missing:
            raise RuntimeError(f"dataset is missing varied-batch keys: {missing}")
        source_values = {key: safe_h5_rows(handle[key], source_rows) for key in keys}
        target_values = {key: safe_h5_rows(handle[key], target_rows) for key in keys}

    init_step_np = {key: np.asarray(value) for key, value in source_values.items()}
    init_step_np["seed"] = np.asarray(
        [int(environment_seed) for _ in range(count)], dtype=object
    )
    goal_step_np: dict[str, np.ndarray] = {}
    for key, value in target_values.items():
        out_key = "goal" if key == "pixels" else f"goal_{key}"
        goal_step_np[out_key] = np.asarray(value)

    # TwoRoom's offline file stores the agent position as ``proprio``, while
    # live environment infos expose the same vector under both ``proprio`` and
    # ``state``.  Supplying the aliases prevents the random reset's stale
    # ``state`` value from leaking into the inclusive t=0 physical trace after
    # the released _set_state/_set_goal_state callables run.
    if environment == "tworoom":
        init_step_np["state"] = np.asarray(init_step_np["proprio"]).copy()
        goal_step_np["goal_state"] = np.asarray(
            goal_step_np["goal_proprio"]
        ).copy()

    init_plus_goal = copy.deepcopy(init_step_np)
    init_plus_goal.update(copy.deepcopy(goal_step_np))
    shape_prefix = (count, int(ctx.eval_cfg.world.history_size))
    init_step_broadcast = {
        key: np.broadcast_to(value[:, None, ...], shape_prefix + value.shape[1:]).copy()
        for key, value in init_plus_goal.items()
    }
    goal_step_broadcast = {
        key: np.broadcast_to(value[:, None, ...], shape_prefix + value.shape[1:]).copy()
        for key, value in goal_step_np.items()
    }
    return PreparedBatch(
        sampled_indices=source_rows.copy(),
        episodes_idx=np.asarray(init_step_np[episode_key], dtype=np.int64),
        start_steps=np.asarray(init_step_np["step_idx"], dtype=np.int64),
        data=[],
        init_step_np=init_step_np,
        goal_step_np=goal_step_np,
        init_step_broadcast=init_step_broadcast,
        goal_step_broadcast=goal_step_broadcast,
        future_pixels_bthwc=np.empty((count, 0, 224, 224, 3), dtype=np.uint8),
        future_states=None,
        future_latents=torch.empty((count, 0, start_latent.shape[-1])),
        goal_latent=goal_latent,
        start_latent=start_latent,
    )


def wrapped_angle_error(value: np.ndarray, target: np.ndarray) -> np.ndarray:
    difference = np.abs(value - target) % (2.0 * np.pi)
    return np.minimum(difference, 2.0 * np.pi - difference)


def first_true_step(value: np.ndarray) -> np.ndarray:
    any_true = value.any(axis=0)
    result = np.argmax(value, axis=0).astype(np.int64)
    result[~any_true] = -1
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-h5", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--eval-config", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--stats-npz", type=Path, required=True)
    parser.add_argument("--stats-manifest", type=Path, required=True)
    parser.add_argument("--stratum-index", type=int, required=True)
    parser.add_argument("--pool-index", type=int, required=True)
    parser.add_argument("--repeat-index", type=int, required=True)
    parser.add_argument("--candidate-start", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=64)
    parser.add_argument("--low-num-samples", type=int, default=1200)
    parser.add_argument("--low-iters", type=int, default=30)
    parser.add_argument("--low-topk", type=int, default=150)
    parser.add_argument("--cost-env-chunk-size", type=int, default=16)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--partition", choices=("P2", "P3"), default="P2")
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--resource-smoke", action="store_true")
    args = parser.parse_args()

    partition = args.partition
    partition_key = partition.lower()
    environment = args.environment
    dataset_name = "pusht_expert_train" if environment == "pusht" else "tworoom"
    pool_count = 12 if partition == "P2" else 24
    candidate_classification = (
        f"{partition_key}_real_frame_candidate_pools"
        if environment == "pusht"
        else f"tworoom_{partition_key}_real_frame_candidate_pools"
    )
    execution_classification = (
        f"{partition_key}_real_frame_candidate_execution"
        if environment == "pusht"
        else f"tworoom_{partition_key}_real_frame_candidate_execution"
    )
    expected_checkpoint_sha256 = (
        "b87805747d40037841877ce7b99b7dda3ebe7a52202c0ba46bf0006ab5d6f008"
        if environment == "pusht"
        else "5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"
    )
    expected_high_budget = (1200, 60, 10) if environment == "pusht" else (300, 20, 10)
    expected_low_budget = (1200, 30, 150) if environment == "pusht" else (300, 30, 10)
    low_horizon = 2 if environment == "pusht" else 5

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite real-frame execution output")
    if not 0 <= args.stratum_index < len(STRATA) or not 0 <= args.pool_index < pool_count:
        raise SystemExit("invalid real-frame stratum or pool index")
    if not 0 <= args.repeat_index < len(repeat_seeds()):
        raise SystemExit("invalid repeat index")
    if args.cost_env_chunk_size <= 0:
        raise SystemExit("cost environment chunk size must be positive")
    if args.smoke and args.resource_smoke:
        raise SystemExit("choose only one smoke mode")
    if args.smoke:
        if (
            args.candidate_count,
            args.low_num_samples,
            args.low_iters,
            args.low_topk,
        ) != (2, 64, 2, 8):
            raise SystemExit("real-frame smoke must use 2 candidates and CEM 64/2/8")
    elif args.resource_smoke:
        if args.candidate_count not in (8, 64) or (
            args.low_num_samples,
            args.low_iters,
            args.low_topk,
            args.cost_env_chunk_size,
        ) != (*expected_low_budget, 16):
            raise SystemExit(
                "real-frame resource smoke must use 8 or 64 candidates and "
                f"the frozen {environment} low CEM {expected_low_budget}/16"
            )
    elif (
        args.candidate_count,
        args.low_num_samples,
        args.low_iters,
        args.low_topk,
        args.cost_env_chunk_size,
    ) != (64, *expected_low_budget, 16):
        raise SystemExit(
            "full real-frame execution must use frozen "
            f"64/{expected_low_budget[0]}/{expected_low_budget[1]}/"
            f"{expected_low_budget[2]}/16 for {environment}"
        )

    started = time.time()
    seeds = repeat_seeds()
    planner_seed = seeds[args.repeat_index]
    determinism = configure_process_determinism(seed=planner_seed, mode="strict")
    solver_self_test = solver_equivalence_self_test()

    candidate_manifest = json.loads(
        args.candidate_manifest.read_text(encoding="utf-8")
    )
    if candidate_manifest.get("status") != "ok" or candidate_manifest.get(
        "classification"
    ) != candidate_classification or candidate_manifest.get("partition") != partition or candidate_manifest.get(
        "environment", "pusht"
    ) != environment:
        raise RuntimeError(
            f"input is not the frozen {partition} real-frame candidate pool"
        )
    if (
        int(candidate_manifest.get("pools_per_stratum", -1)) != pool_count
        or int(candidate_manifest.get("candidates_per_pool", -1)) != CANDIDATE_COUNT
    ):
        raise RuntimeError("real-frame candidate coverage changed")
    candidate_sha = sha256_file(args.candidate_h5)
    if candidate_sha != candidate_manifest["output_h5_sha256"]:
        raise RuntimeError("real-frame candidate HDF5 does not match its manifest")
    if sha256_file(args.checkpoint_file) != expected_checkpoint_sha256:
        raise RuntimeError("unexpected Hi-LeWM checkpoint")

    end = args.candidate_start + args.candidate_count
    if args.candidate_start < 0 or end > CANDIDATE_COUNT:
        raise RuntimeError("candidate slice lies outside the real-frame pool")
    key = (args.stratum_index, args.pool_index, slice(args.candidate_start, end))
    with h5py.File(args.candidate_h5, "r") as candidates:
        if (
            candidates.attrs.get("classification") != candidate_classification
            or candidates.attrs.get("partition") != partition
            or candidates.attrs.get("environment", "pusht") != environment
        ):
            raise RuntimeError("candidate HDF5 classification or partition changed")
        source_rows = np.asarray(candidates["source_global_row"][key], dtype=np.int64)
        target_rows = np.asarray(candidates["target_global_row"][key], dtype=np.int64)
        source_episode = np.asarray(candidates["source_episode_id"][key], dtype=np.int64)
        target_episode = np.asarray(candidates["target_episode_id"][key], dtype=np.int64)
        source_step = np.asarray(candidates["source_step"][key], dtype=np.int64)
        target_step = np.asarray(candidates["target_step"][key], dtype=np.int64)
        source_latent_np = np.asarray(candidates["source_latent"][key], dtype=np.float32)
        target_latent_np = np.asarray(candidates["target_latent"][key], dtype=np.float32)
        expected_source_state = np.asarray(candidates["source_state"][key], dtype=np.float32)
        target_state = np.asarray(candidates["target_state"][key], dtype=np.float32)
    count = args.candidate_count
    if source_latent_np.shape != (count, 192) or target_latent_np.shape != (count, 192):
        raise RuntimeError("unexpected real-frame latent slice shape")
    if args.stratum_index == 0:
        if not np.array_equal(source_episode, target_episode) or not np.all(
            target_step - source_step == 25
        ):
            raise RuntimeError("same-trajectory execution slice violates its stratum")
    elif np.any(source_episode == target_episode):
        raise RuntimeError("cross-trajectory execution slice contains same-episode pairs")

    cfg = ActingDiagnosticConfig(
        policy=args.policy,
        experiment_kind=f"{partition_key}_real_frame_candidate_attainment",
        dataset_name=dataset_name,
        eval_config=str(args.eval_config),
        cache_dir=str(args.stablewm_home),
        img_size=224,
        num_eval=count,
        goal_offset_steps=25,
        eval_budget=ATTAINMENT_HORIZON,
        high_horizon=2,
        low_horizon=low_horizon,
        low_receding_horizon=1,
        high_num_samples=expected_high_budget[0],
        high_iters=expected_high_budget[1],
        high_topk=expected_high_budget[2],
        low_num_samples=args.low_num_samples,
        low_iters=args.low_iters,
        low_topk=args.low_topk,
        frame_skip=5,
        seed=planner_seed,
        device="cuda",
        num_reference_samples=4096,
    )
    ctx = build_context(cfg)
    device = ctx.device
    targets = torch.from_numpy(target_latent_np).to(device)
    starts = torch.from_numpy(source_latent_np).to(device)
    batch = build_varied_batch(
        ctx=ctx,
        dataset_path=args.dataset,
        source_rows=source_rows,
        target_rows=target_rows,
        environment_seed=planner_seed,
        start_latent=starts,
        goal_latent=targets,
        environment=environment,
    )
    physical_key = "state" if environment == "pusht" else "proprio"
    if not np.array_equal(np.asarray(batch.init_step_np[physical_key], dtype=np.float32), expected_source_state):
        raise RuntimeError("dataset source states differ from frozen real-frame pool")
    if not np.array_equal(np.asarray(batch.goal_step_np[f"goal_{physical_key}"], dtype=np.float32), target_state):
        raise RuntimeError("dataset target states differ from frozen real-frame pool")

    high_cfg = swm.policy.PlanConfig(horizon=2, receding_horizon=1, action_block=1)
    low_cfg = swm.policy.PlanConfig(horizon=low_horizon, receding_horizon=1, action_block=5)
    high_solver = swm.solver.CEMSolver(
        model=ctx.model,
        batch_size=1,
        num_samples=1,
        var_scale=1.0,
        n_steps=1,
        topk=1,
        device=device,
        seed=planner_seed,
    )
    low_solver = CommonRandomNumbersCEMSolver(
        model=ctx.model,
        num_samples=args.low_num_samples,
        var_scale=1.0,
        n_steps=args.low_iters,
        topk=args.low_topk,
        device=device,
        seed=planner_seed,
        cost_env_chunk_size=args.cost_env_chunk_size,
    )
    policy = InstrumentedStagePolicy(
        ctx=ctx,
        high_solver=high_solver,
        low_solver=low_solver,
        high_config=high_cfg,
        low_config=low_cfg,
        stage_duration_steps=ATTAINMENT_HORIZON,
        clear_low_buffer_on_stage_change=True,
        macro_replan_interval=5,
        high_latent_bounds=None,
    )
    policy.set_oracle_stage_targets(targets.unsqueeze(1), [ATTAINMENT_HORIZON])
    reset_world_from_batch(ctx, batch)
    torch.cuda.reset_peak_memory_stats(device)
    execution_started = time.time()
    loop = run_world_loop_with_attainment_trace(
        ctx, batch, policy, max_steps=ATTAINMENT_HORIZON
    )
    execution_seconds = time.time() - execution_started
    peak_gpu_allocated_bytes = int(torch.cuda.max_memory_allocated(device))
    peak_gpu_reserved_bytes = int(torch.cuda.max_memory_reserved(device))

    latent_trace = loop["latent_trace"]
    state_trace = np.asarray(loop["state_trace"], dtype=np.float32)
    if latent_trace.shape != (26, count, 192) or state_trace.shape != (
        26,
        count,
        target_state.shape[1],
    ):
        raise RuntimeError("unexpected real-frame attainment trace shape")
    difference = latent_trace - targets.unsqueeze(0)
    raw_rmse_trace = difference.pow(2).mean(dim=-1).sqrt()

    stats_manifest = json.loads(args.stats_manifest.read_text(encoding="utf-8"))
    if sha256_file(args.stats_npz) != stats_manifest["output_npz_sha256"]:
        raise RuntimeError("P1 statistics do not match their manifest")
    with np.load(args.stats_npz) as stats:
        std_np = np.asarray(stats["std"], dtype=np.float32)
    if std_np.shape != (192,) or np.any(std_np < 1.0e-6):
        raise RuntimeError("invalid P1 latent standard deviations")
    std = torch.from_numpy(std_np).to(device)
    standardized_rmse_trace = (difference / std).pow(2).mean(dim=-1).sqrt()
    minimum_raw_rmse, minimum_raw_step = raw_rmse_trace.min(dim=0)
    minimum_standardized_rmse, minimum_standardized_step = (
        standardized_rmse_trace.min(dim=0)
    )

    if environment == "pusht":
        block_position_error = np.linalg.norm(
            state_trace[:, :, 2:4] - target_state[None, :, 2:4], axis=-1
        ).astype(np.float32)
        agent_block_position_error = np.linalg.norm(
            state_trace[:, :, :4] - target_state[None, :, :4], axis=-1
        ).astype(np.float32)
        angle_error = wrapped_angle_error(
            state_trace[:, :, 4], target_state[None, :, 4]
        ).astype(np.float32)
        primary_success_trace = (block_position_error < 20.0) & (
            angle_error < np.pi / 9.0
        )
        agent_included_success_trace = (agent_block_position_error < 20.0) & (
            angle_error < np.pi / 9.0
        )
        agent_included_attained = agent_included_success_trace.any(axis=0)
        agent_included_first_step = first_true_step(agent_included_success_trace)
    else:
        agent_position_error = np.linalg.norm(
            state_trace - target_state[None, :, :], axis=-1
        ).astype(np.float32)
        primary_success_trace = agent_position_error < 16.0
    primary_attained = primary_success_trace.any(axis=0)
    primary_first_step = first_true_step(primary_success_trace)
    environment_success = np.asarray(loop["episode_successes"], dtype=np.bool_)
    expected_environment_success = (
        agent_included_success_trace[1:].any(axis=0)
        if environment == "pusht"
        else primary_success_trace[1:].any(axis=0)
    )
    if not np.array_equal(environment_success, expected_environment_success):
        raise RuntimeError("recorded states disagree with released environment success")

    classification = (
        f"{'tworoom_' if environment == 'tworoom' else ''}{partition_key}_real_frame_implementation_smoke"
        if args.smoke
        else f"{'tworoom_' if environment == 'tworoom' else ''}{partition_key}_real_frame_resource_smoke"
        if args.resource_smoke
        else execution_classification
    )
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    candidate_slots = np.arange(args.candidate_start, end, dtype=np.int64)
    latent_trace_np = latent_trace.detach().cpu().numpy().astype(np.float32, copy=False)
    raw_rmse_trace_np = raw_rmse_trace.detach().cpu().numpy().astype(np.float32, copy=False)
    standardized_rmse_trace_np = (
        standardized_rmse_trace.detach().cpu().numpy().astype(np.float32, copy=False)
    )
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = classification
            output.attrs["environment"] = environment
            output.attrs["dataset_name"] = dataset_name
            output.attrs["stratum_index"] = args.stratum_index
            output.attrs["stratum_name"] = STRATA[args.stratum_index]
            output.attrs["pool_index"] = args.pool_index
            output.attrs["repeat_index"] = args.repeat_index
            output.attrs["planner_seed"] = planner_seed
            for name, value in (
                ("candidate_slot", candidate_slots),
                ("source_global_row", source_rows),
                ("target_global_row", target_rows),
                ("source_episode_id", source_episode),
                ("target_episode_id", target_episode),
                ("source_step", source_step),
                ("target_step", target_step),
                ("target_latent", target_latent_np),
                ("target_state", target_state),
                ("state_trace", state_trace),
                ("latent_trace", latent_trace_np),
                ("raw_latent_rmse_trace", raw_rmse_trace_np),
                ("standardized_latent_rmse_trace", standardized_rmse_trace_np),
                ("minimum_raw_latent_rmse", minimum_raw_rmse.detach().cpu().numpy()),
                ("minimum_raw_latent_step", minimum_raw_step.detach().cpu().numpy()),
                (
                    "minimum_standardized_latent_rmse",
                    minimum_standardized_rmse.detach().cpu().numpy(),
                ),
                (
                    "minimum_standardized_latent_step",
                    minimum_standardized_step.detach().cpu().numpy(),
                ),
                ("primary_success_trace", primary_success_trace),
                ("primary_attained", primary_attained),
                ("primary_first_attainment_step", primary_first_step),
                ("released_environment_success_steps_1_to_25", environment_success),
            ):
                compression = "gzip" if np.asarray(value).ndim >= 3 else None
                output.create_dataset(name, data=value, compression=compression)
            if environment == "pusht":
                for name, value in (
                    ("block_position_error_trace", block_position_error),
                    ("agent_block_position_error_trace", agent_block_position_error),
                    ("wrapped_block_angle_error_trace", angle_error),
                    ("agent_included_success_trace", agent_included_success_trace),
                    ("agent_included_attained", agent_included_attained),
                    ("agent_included_first_attainment_step", agent_included_first_step),
                ):
                    output.create_dataset(name, data=value, compression="gzip" if np.asarray(value).ndim >= 3 else None)
            else:
                output.create_dataset("agent_position_error_trace", data=agent_position_error)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_real_frame_execution_retained={partial_h5}", file=sys.stderr)
        raise

    result = {
        "status": "ok",
        "classification": classification,
        "environment": environment,
        "dataset_name": dataset_name,
        "partition": partition,
        "stratum_index": args.stratum_index,
        "stratum_name": STRATA[args.stratum_index],
        "pool_index": args.pool_index,
        "repeat_index": args.repeat_index,
        "repeat_seeds": seeds,
        "planner_seed": planner_seed,
        "environment_seed": planner_seed,
        "candidate_slice": [args.candidate_start, end],
        "candidate_count": count,
        "attainment_trace": {
            "steps_inclusive": [0, 25],
            "record_count": 26,
            "initial_state_sync": loop["initial_state_sync"],
            "physical_primary": (
                "any block position L2 < 20 and wrapped block angle < pi/9"
                if environment == "pusht"
                else "minimum agent-position L2 over steps 0..25 < 16 pixels"
            ),
            "physical_sensitivity": (
                "any joint agent+block position L2 < 20 and wrapped block angle < pi/9"
                if environment == "pusht"
                else None
            ),
            "latent_diagnostic": "minimum P1-standardized latent RMSE over steps 0..25",
        },
        "low_planner": {
            "implementation": "batched equivalent of independent same-seed stable_worldmodel CEM solves",
            "common_random_numbers_across_candidates": True,
            "cost_environment_chunk_size": args.cost_env_chunk_size,
            "horizon_tokens": low_horizon,
            "receding_horizon_tokens": 1,
            "action_block_primitive_steps": 5,
            "num_samples": args.low_num_samples,
            "n_steps": args.low_iters,
            "topk": args.low_topk,
            "var_scale": 1.0,
        },
        "solver_equivalence_self_test": solver_self_test,
        "metrics": {
            "primary_attainment_rate": float(primary_attained.mean()),
            "agent_included_attainment_rate": (
                float(agent_included_attained.mean()) if environment == "pusht" else None
            ),
            "released_environment_success_rate_steps_1_to_25": float(
                environment_success.mean()
            ),
            "minimum_standardized_latent_rmse_mean": float(
                minimum_standardized_rmse.mean().item()
            ),
        },
        "inputs": {
            "candidate_h5": str(args.candidate_h5),
            "candidate_h5_sha256": candidate_sha,
            "candidate_manifest_sha256": sha256_file(args.candidate_manifest),
            "dataset": str(args.dataset),
            "checkpoint_file": str(args.checkpoint_file),
            "checkpoint_sha256": sha256_file(args.checkpoint_file),
            "statistics": {
                "stats_npz": str(args.stats_npz),
                "stats_npz_sha256": stats_manifest["output_npz_sha256"],
                "stats_manifest_sha256": sha256_file(args.stats_manifest),
            },
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
            "peak_gpu_allocated_bytes": peak_gpu_allocated_bytes,
            "peak_gpu_reserved_bytes": peak_gpu_reserved_bytes,
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
