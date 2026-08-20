#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata as metadata
import json
import math
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import h5py
import numpy as np
import torch
from omegaconf import OmegaConf

from hi_acting_diagnostics import (
    ActingDiagnosticConfig,
    InstrumentedHierarchicalPolicy,
    PreparedBatch,
    apply_goal_info,
    build_context,
    build_solvers_and_configs,
    encode_pixels_sequence,
    reset_world_from_batch,
)
from hi_diagnostics import img_transform
from h_le_wm.eval.determinism import configure_process_determinism
from h_le_wm.planning.policies import (
    EmpiricalMacroActionSolver,
    build_empirical_macro_action_bank,
    calibrate_latent_prior,
)


QUERY_COUNT = 12
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
EXPECTED_MACRO_DIM = 32
EXPECTED_RAW_ACTION_DIM = 5
EXPECTED_GROUP = 5
QUERY_H5_SHA256 = "5c6036906bd94f74c2041952d26e0ad67784d0c9966d8519880465db8a6ee5ce"
DATASET_SHA256 = "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625"
DATASET_BYTES = 101_942_558_720
CHECKPOINT_SHA256 = "50aaae8539904e86a835939f8d85af56ca83549ef181d0f6bca7e444437fe4c4"
EVAL_CONFIG_SHA256 = "664bd25376ce94bd952af2d7b1afc193ab9623d32e9e5d2c28895a1eaf75c571"


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
    digest.update(array.tobytes())
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


def verify_inventory(directory: Path) -> dict[str, str]:
    inventory_path = directory / "checksums.sha256"
    if not inventory_path.is_file():
        raise RuntimeError(f"missing checksum inventory: {directory}")
    root = directory.resolve()
    found: dict[str, str] = {}
    for raw in inventory_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, raw_path = raw.split(maxsplit=1)
        path = Path(raw_path.lstrip("* "))
        if not path.is_absolute():
            path = directory / path
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise RuntimeError(f"checksum path escapes query directory: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid query input: {path}")
        found[str(resolved.relative_to(root))] = digest
    return found


def validate_query_artifact(directory: Path) -> tuple[dict[str, Any], Path, dict[str, str]]:
    inventory = verify_inventory(directory)
    if set(inventory) != {"queries.h5", "manifest.json", "provenance.txt"}:
        raise RuntimeError("unexpected Cube gate-query inventory")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification") != "cube_p2_d75_environment_gate_queries"
        or manifest.get("partition") != "P2"
        or int(manifest.get("query_count")) != QUERY_COUNT
        or int(manifest.get("goal_offset")) != GOAL_OFFSET
        or manifest.get("output_h5_sha256") != QUERY_H5_SHA256
        or inventory["queries.h5"] != QUERY_H5_SHA256
        or manifest.get("inputs", {}).get("dataset_sha256") != DATASET_SHA256
    ):
        raise RuntimeError("Cube gate-query artifact differs from A-040")
    return manifest, directory / "queries.h5", inventory


def stack_latents(values: list[torch.Tensor], latent_dim: int) -> np.ndarray:
    if not values:
        return np.empty((0, latent_dim), dtype=np.float32)
    stacked = torch.stack([value.detach().cpu() for value in values], dim=0)
    if stacked.ndim != 3 or stacked.shape[1:] != (1, latent_dim):
        raise RuntimeError(f"unexpected recorded latent shape: {tuple(stacked.shape)}")
    return stacked[:, 0, :].numpy().astype(np.float32, copy=False)


def run_cube_world_loop(
    ctx: Any,
    batch: PreparedBatch,
    policy: InstrumentedHierarchicalPolicy,
    *,
    max_steps: int,
) -> dict[str, Any]:
    """Run the released loop while restoring Cube's fixed goal for diagnostics.

    The shared helper supplies goal fields before ``world.step`` so planning can
    consume them. OGBCube replaces ``world.infos`` during that step, unlike
    PushT, so the post-step diagnostic must receive the same fixed goal fields
    again. This second update cannot affect the action or environment transition.
    """
    world = ctx.world
    world.set_policy(policy)
    episode_successes = np.zeros(world.num_envs, dtype=bool)
    goal_reinjection_count = 0
    for _ in range(int(max_steps)):
        apply_goal_info(world, batch)
        world.step()
        episode_successes = np.logical_or(episode_successes, world.terminateds)
        world.envs.unwrapped._autoreset_envs = np.zeros((world.num_envs,))
        apply_goal_info(world, batch)
        goal_reinjection_count += 1
        policy.after_env_step(world.infos)
    return {
        "episode_successes": episode_successes,
        "success_rate": float(episode_successes.mean() * 100.0),
        "post_step_goal_reinjection_count": goal_reinjection_count,
    }


@torch.inference_mode()
def validate_cube_goal_adapter_without_step(
    ctx: Any,
    batch: PreparedBatch,
    policy: InstrumentedHierarchicalPolicy,
) -> dict[str, Any]:
    """Exercise the post-step schema adapter without an environment transition."""
    probe = SimpleNamespace(
        infos={"pixels": np.array(ctx.world.infos["pixels"], copy=True)}
    )
    apply_goal_info(probe, batch)
    prepared = policy._prepare_info(
        {
            "pixels": np.array(probe.infos["pixels"], copy=True),
            "goal": np.array(probe.infos["goal"], copy=True),
        }
    )
    current = policy._encode_pixels_last(prepared["pixels"].to(policy._device()))
    goal = policy._encode_pixels_last(prepared["goal"].to(policy._device()))
    if current.shape != batch.start_latent.shape or goal.shape != batch.goal_latent.shape:
        raise RuntimeError("Cube goal-adapter no-step probe changed latent geometry")
    return {
        "environment_steps": 0,
        "current_shape": list(current.shape),
        "goal_shape": list(goal.shape),
        "finite": bool(torch.isfinite(current).all() and torch.isfinite(goal).all()),
    }


def build_cube_fixed_batch(
    *,
    ctx: Any,
    dataset_path: Path,
    episode_id: int,
    source_row: int,
    goal_row: int,
    source_step: int,
    goal_step: int,
    environment_seed: int,
) -> PreparedBatch:
    with h5py.File(dataset_path, "r") as handle:
        if (
            int(handle["ep_idx"][source_row]) != episode_id
            or int(handle["ep_idx"][goal_row]) != episode_id
            or int(handle["step_idx"][source_row]) != source_step
            or int(handle["step_idx"][goal_row]) != goal_step
        ):
            raise RuntimeError("Cube query does not map to the declared dataset rows")

    data = ctx.dataset.load_chunk(
        np.asarray([episode_id], dtype=np.int64),
        np.asarray([source_step], dtype=np.int64),
        np.asarray([goal_step], dtype=np.int64),
    )
    if len(data) != 1:
        raise RuntimeError("Cube fixed-query load did not return one episode chunk")
    episode = data[0]
    init_step_np: dict[str, np.ndarray] = {}
    goal_step_np: dict[str, np.ndarray] = {}
    source_pixel = None
    goal_pixel = None
    for column in ctx.dataset.column_names:
        if column.startswith("goal") or column not in episode:
            continue
        value = episode[column]
        if column.startswith("pixels") and isinstance(value, torch.Tensor):
            value = value.permute(0, 2, 3, 1)
        if not isinstance(value, (torch.Tensor, np.ndarray)):
            continue
        source_value = value[0]
        goal_value = value[-1]
        if isinstance(source_value, torch.Tensor):
            source_value = source_value.numpy()
        if isinstance(goal_value, torch.Tensor):
            goal_value = goal_value.numpy()
        source_np = np.asarray(source_value)
        goal_np = np.asarray(goal_value)
        init_step_np[column] = source_np[None, ...]
        goal_key = "goal" if column == "pixels" else f"goal_{column}"
        goal_step_np[goal_key] = goal_np[None, ...]
        if column == "pixels":
            source_pixel = source_np
            goal_pixel = goal_np
    if source_pixel is None or goal_pixel is None:
        raise RuntimeError("Cube fixed query has no source/goal pixels")
    init_step_np["seed"] = np.asarray([int(environment_seed)], dtype=object)

    pixel_pair = np.stack((source_pixel, goal_pixel), axis=0)[None, ...]
    future_latents = encode_pixels_sequence(
        ctx.model,
        pixel_pair,
        img_transform(ctx.cfg.img_size),
        ctx.device,
    )
    if future_latents.ndim != 3 or future_latents.shape[:2] != (1, 2):
        raise RuntimeError("Cube source/goal encoder geometry changed")
    start_latent = future_latents[:, 0]
    goal_latent = future_latents[:, 1]
    if not torch.isfinite(start_latent).all() or not torch.isfinite(goal_latent).all():
        raise RuntimeError("Cube source/goal latent is non-finite")

    init_plus_goal = copy.deepcopy(init_step_np)
    init_plus_goal.update(copy.deepcopy(goal_step_np))
    shape_prefix = (1, int(ctx.eval_cfg.world.history_size))
    init_step_broadcast = {
        key: np.broadcast_to(value[:, None, ...], shape_prefix + value.shape[1:]).copy()
        for key, value in init_plus_goal.items()
    }
    goal_step_broadcast = {
        key: np.broadcast_to(value[:, None, ...], shape_prefix + value.shape[1:]).copy()
        for key, value in goal_step_np.items()
    }
    return PreparedBatch(
        sampled_indices=np.asarray([source_row], dtype=np.int64),
        episodes_idx=np.asarray([episode_id], dtype=np.int64),
        start_steps=np.asarray([source_step], dtype=np.int64),
        data=data,
        init_step_np=init_step_np,
        goal_step_np=goal_step_np,
        init_step_broadcast=init_step_broadcast,
        goal_step_broadcast=goal_step_broadcast,
        future_pixels_bthwc=pixel_pair,
        future_states=None,
        future_latents=future_latents,
        goal_latent=goal_latent,
        start_latent=start_latent,
    )


class CountingHighCost:
    def __init__(self, base_model: torch.nn.Module) -> None:
        self.base_model = base_model
        self.call_count = 0
        self.candidate_evaluations = 0

    @torch.inference_mode()
    def get_cost(self, info_dict: dict[str, Any], action_candidates: torch.Tensor) -> torch.Tensor:
        if not torch.is_tensor(info_dict.get("z_init")) or not torch.is_tensor(
            info_dict.get("z_goal")
        ):
            raise RuntimeError("high-level counter received a non-high planner call")
        if action_candidates.ndim != 4:
            raise RuntimeError("unexpected Cube high-level candidate shape")
        self.call_count += 1
        self.candidate_evaluations += int(action_candidates.shape[0] * action_candidates.shape[1])
        return self.base_model.get_cost(info_dict, action_candidates)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-dir", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--eval-config", type=Path, required=True)
    parser.add_argument("--arm", choices=("B0", "B1"), required=True)
    parser.add_argument("--query-index", type=int, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--smoke-no-step", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.query_index < 0 or args.query_index >= QUERY_COUNT:
        raise SystemExit("Cube query index is outside [0, 12)")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite Cube D75 result")
    if not torch.cuda.is_available():
        raise RuntimeError("Cube D75 runner requires CUDA")
    if metadata.version("stable-worldmodel") != "0.0.6":
        raise RuntimeError("Cube D75 runner requires stable-worldmodel==0.0.6")
    started = time.time()
    query_manifest, query_h5, query_inventory = validate_query_artifact(args.query_dir)
    if not args.dataset.is_file() or args.dataset.stat().st_size != DATASET_BYTES:
        raise RuntimeError("Cube dataset path/size differs from the frozen artifact")
    if sha256_file(args.checkpoint_file) != CHECKPOINT_SHA256:
        raise RuntimeError("Cube hierarchical checkpoint differs from the frozen artifact")
    if sha256_file(args.eval_config) != EVAL_CONFIG_SHA256:
        raise RuntimeError("Cube D75 evaluation configuration differs from the frozen artifact")

    with h5py.File(query_h5, "r") as handle:
        query = {
            key: int(handle[key][args.query_index])
            for key in (
                "query_id",
                "episode_id",
                "source_global_row",
                "goal_global_row",
                "source_step",
                "goal_step",
                "planner_seed",
            )
        }
    if query["query_id"] != args.query_index or (
        query["goal_step"] - query["source_step"]
    ) != GOAL_OFFSET:
        raise RuntimeError("invalid Cube D75 query identity")
    if query_manifest["queries"][args.query_index] != query:
        raise RuntimeError("Cube query HDF5/manifest mismatch")

    process_seed = query["planner_seed"] & ((1 << 32) - 1)
    determinism = configure_process_determinism(seed=process_seed, mode="strict")
    cfg = ActingDiagnosticConfig(
        policy=args.policy,
        experiment_kind=(
            "cube_p2_d75_implementation_smoke"
            if args.smoke_no_step
            else "cube_p2_d75_environment_substitution_gate"
        ),
        dataset_name="cube_single_expert",
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
        seed=query["planner_seed"],
        device="cuda",
        num_reference_samples=4096,
    )
    ctx = build_context(cfg)
    if (
        int(ctx.latent_dim) != EXPECTED_MACRO_DIM
        or int(ctx.raw_action_dim) != EXPECTED_RAW_ACTION_DIM
        or int(ctx.group) != EXPECTED_GROUP
    ):
        raise RuntimeError("Cube model action/macro geometry changed")
    batch = build_cube_fixed_batch(
        ctx=ctx,
        dataset_path=args.dataset,
        episode_id=query["episode_id"],
        source_row=query["source_global_row"],
        goal_row=query["goal_global_row"],
        source_step=query["source_step"],
        goal_step=query["goal_step"],
        environment_seed=query["planner_seed"],
    )
    state_latent_dim = int(batch.start_latent.shape[-1])
    if state_latent_dim <= 0 or batch.goal_latent.shape != batch.start_latent.shape:
        raise RuntimeError("Cube state-latent geometry changed")

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
        raise RuntimeError("released Cube D75 planner configuration changed")
    if (
        int(low_solver.num_samples),
        int(low_solver.n_steps),
        int(low_solver.topk),
    ) != (LOW_NUM_SAMPLES, LOW_ITERATIONS, LOW_TOPK):
        raise RuntimeError("Cube low-level CEM budget changed")
    for solver in (high_solver, low_solver):
        if not hasattr(solver, "torch_gen") or int(solver.torch_gen.initial_seed()) != (
            query["planner_seed"]
        ):
            raise RuntimeError("Cube CEM solver did not retain the frozen query seed")

    counted_model = CountingHighCost(ctx.model)
    empirical_bank: dict[str, np.ndarray] | None = None
    if args.arm == "B0":
        if (
            int(high_solver.num_samples),
            int(high_solver.n_steps),
            int(high_solver.topk),
        ) != (HIGH_NUM_SAMPLES, HIGH_ITERATIONS, HIGH_TOPK):
            raise RuntimeError("Cube B0 high-level CEM budget changed")
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
                "seed": query["planner_seed"],
            }
        )
        empirical_bank = build_empirical_macro_action_bank(
            model=ctx.model,
            dataset=ctx.dataset,
            cfg=empirical_cfg,
            high_horizon=HIGH_HORIZON,
            high_action_block=HIGH_ACTION_BLOCK,
            process=ctx.process,
            seed=query["planner_seed"],
        )
        if empirical_bank["actions"].shape != (
            4096,
            HIGH_HORIZON,
            EXPECTED_MACRO_DIM,
        ):
            raise RuntimeError("Cube empirical-macro bank geometry changed")
        high_solver = EmpiricalMacroActionSolver(
            model=counted_model,
            macro_bank=empirical_bank["actions"],
            batch_size=1,
            num_samples=HIGH_NUM_SAMPLES,
            var_scale=1.0,
            n_steps=HIGH_ITERATIONS,
            topk=HIGH_TOPK,
            device=ctx.device,
            seed=query["planner_seed"],
            residual_scale=0.1,
            min_residual_std=0.001,
            return_top_candidates=8,
            stage_sampling="sequence",
        )
        if int(high_solver.torch_gen.initial_seed()) != query["planner_seed"]:
            raise RuntimeError("Cube B1 solver did not retain the frozen query seed")

    high_bounds = None
    if bool(eval_cfg.planning.high.latent_prior.get("enabled", True)):
        high_bounds = calibrate_latent_prior(
            model=ctx.model,
            dataset=ctx.dataset,
            cfg=eval_cfg.planning.high.latent_prior,
            process=ctx.process,
            seed=query["planner_seed"],
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

    common = {
        "query": query,
        "arm": args.arm,
        "state_latent_dim": state_latent_dim,
        "model_geometry": {
            "macro_dim": int(ctx.latent_dim),
            "raw_action_dim": int(ctx.raw_action_dim),
            "macro_input_dim": int(ctx.macro_input_dim),
            "group": int(ctx.group),
        },
        "planner": {
            "eval_budget_primitive_steps": EVAL_BUDGET,
            "goal_offset_primitive_steps": GOAL_OFFSET,
            "high": {
                "solver": (
                    "stable_worldmodel.CEMSolver"
                    if args.arm == "B0"
                    else "released EmpiricalMacroActionSolver"
                ),
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
            "empirical_macro_configuration": (
                None
                if args.arm == "B0"
                else {
                    "num_sequences": 4096,
                    "chunk_len": 5,
                    "raw_macro_len": 25,
                    "residual_scale": 0.1,
                    "min_residual_std": 0.001,
                    "return_top_candidates": 8,
                    "encode_batch_size": 4096,
                    "stage_sampling": "sequence",
                }
            ),
        },
        "inputs": {
            "query_h5_sha256": query_inventory["queries.h5"],
            "query_manifest_sha256": query_inventory["manifest.json"],
            "dataset": str(args.dataset),
            "dataset_sha256": DATASET_SHA256,
            "checkpoint_file": str(args.checkpoint_file),
            "checkpoint_sha256": CHECKPOINT_SHA256,
            "eval_config": str(args.eval_config),
            "eval_config_sha256": sha256_file(args.eval_config),
        },
        "determinism": determinism,
        "cube_goal_diagnostic_adapter": {
            "operation": "restore the immutable goal fields after world.step and before diagnostics",
            "planner_or_environment_effect": False,
        },
    }

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    if args.smoke_no_step:
        goal_adapter_probe = validate_cube_goal_adapter_without_step(ctx, batch, policy)
        if not goal_adapter_probe["finite"]:
            raise RuntimeError("Cube goal-adapter no-step probe produced non-finite latents")
        partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "cube_p2_d75_implementation_smoke_no_step"
            output.attrs["arm"] = args.arm
            output.attrs["query_index"] = args.query_index
            output.create_dataset(
                "start_latent", data=batch.start_latent.detach().cpu().numpy()[0]
            )
            output.create_dataset(
                "goal_latent", data=batch.goal_latent.detach().cpu().numpy()[0]
            )
            if empirical_bank is not None:
                output.create_dataset("empirical_bank_actions", data=empirical_bank["actions"])
            output.flush()
        os.replace(partial_h5, args.output_h5)
        result = {
            "status": "ok",
            "classification": "cube_p2_d75_implementation_smoke_no_step",
            "reporting_rule": "implementation-only; no planner step or outcome was executed",
            **common,
            "goal_adapter_no_step_probe": goal_adapter_probe,
            "empirical_bank": (
                None
                if empirical_bank is None
                else {
                    "shape": list(empirical_bank["actions"].shape),
                    "sha256": sha256_array(empirical_bank["actions"]),
                }
            ),
            "output_h5": str(args.output_h5),
            "output_h5_sha256": sha256_file(args.output_h5),
            "elapsed_seconds": time.time() - started,
        }
        atomic_json(args.output_json, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    torch.cuda.synchronize(ctx.device)
    torch.cuda.reset_peak_memory_stats(ctx.device)
    execution_started = time.time()
    loop = run_cube_world_loop(ctx, batch, policy, max_steps=EVAL_BUDGET)
    torch.cuda.synchronize(ctx.device)
    execution_seconds = time.time() - execution_started
    peak_allocated = int(torch.cuda.max_memory_allocated(ctx.device))
    peak_reserved = int(torch.cuda.max_memory_reserved(ctx.device))

    expected_high_solves = math.ceil(EVAL_BUDGET / HIGH_REPLAN_INTERVAL)
    expected_cost_calls = expected_high_solves * HIGH_ITERATIONS
    if (
        len(policy.high_plan_events) != expected_high_solves
        or counted_model.call_count != expected_cost_calls
        or counted_model.candidate_evaluations
        != expected_cost_calls * HIGH_NUM_SAMPLES
        or len(policy.step_events) != EVAL_BUDGET
        or int(loop["post_step_goal_reinjection_count"]) != EVAL_BUDGET
    ):
        raise RuntimeError("Cube closed-loop cost/step accounting changed")
    episode_success = bool(np.asarray(loop["episode_successes"], dtype=np.bool_)[0])
    high_current = stack_latents(policy.high_plan_current_latents, state_latent_dim)
    high_goal = stack_latents(policy.high_plan_goal_latents, state_latent_dim)
    high_subgoal = stack_latents(policy.high_plan_subgoal_latents, state_latent_dim)
    low_actual = stack_latents(policy.low_block_actual_latents, state_latent_dim)
    low_subgoal = stack_latents(policy.low_block_subgoal_latents, state_latent_dim)
    step_current = stack_latents(policy.step_current_latents, state_latent_dim)
    step_subgoal = stack_latents(policy.step_subgoal_latents, state_latent_dim)
    expected_high_shape = (expected_high_solves, state_latent_dim)
    expected_low_shape = (EVAL_BUDGET // LOW_ACTION_BLOCK, state_latent_dim)
    if (
        high_current.shape != expected_high_shape
        or high_goal.shape != expected_high_shape
        or high_subgoal.shape != expected_high_shape
        or low_actual.shape != expected_low_shape
        or low_subgoal.shape != expected_low_shape
        or step_current.shape != (EVAL_BUDGET, state_latent_dim)
        or step_subgoal.shape != (EVAL_BUDGET, state_latent_dim)
    ):
        raise RuntimeError("Cube planner latent trace is incomplete")

    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "cube_p2_d75_environment_substitution_gate"
            output.attrs["partition"] = "P2-development-only"
            output.attrs["arm"] = args.arm
            output.attrs["query_index"] = args.query_index
            output.attrs["episode_success"] = episode_success
            output.attrs["planner_seed"] = query["planner_seed"]
            output.create_dataset("start_latent", data=batch.start_latent.detach().cpu().numpy()[0])
            output.create_dataset("goal_latent", data=batch.goal_latent.detach().cpu().numpy()[0])
            output.create_dataset("high_plan_current_latent", data=high_current)
            output.create_dataset("high_plan_goal_latent", data=high_goal)
            output.create_dataset("high_plan_subgoal_latent", data=high_subgoal)
            output.create_dataset("low_block_actual_latent", data=low_actual)
            output.create_dataset("low_block_subgoal_latent", data=low_subgoal)
            output.create_dataset("step_current_latent", data=step_current)
            output.create_dataset("step_subgoal_latent", data=step_subgoal)
            if empirical_bank is not None:
                output.create_dataset("empirical_bank_actions", data=empirical_bank["actions"])
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_cube_d75_result_retained={partial_h5}", file=sys.stderr)
        raise

    result = {
        "status": "ok",
        "classification": "cube_p2_d75_environment_substitution_gate",
        "partition": "P2-development-only",
        "reporting_rule": "Cube/TwoRoom substitution decision only; not a final estimate",
        **common,
        "episode_success": episode_success,
        "success_rate_percent": float(loop["success_rate"]),
        "planner_accounting": {
            "high_plan_count": len(policy.high_plan_events),
            "low_block_count": len(policy.low_block_events),
            "step_count": len(policy.step_events),
            "high_cost_calls": counted_model.call_count,
            "high_candidate_evaluations": counted_model.candidate_evaluations,
            "post_step_goal_reinjection_count": int(
                loop["post_step_goal_reinjection_count"]
            ),
        },
        "empirical_bank": (
            None
            if empirical_bank is None
            else {
                "shape": list(empirical_bank["actions"].shape),
                "sha256": sha256_array(empirical_bank["actions"]),
            }
        ),
        "runtime": {
            "python": sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(ctx.device),
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
