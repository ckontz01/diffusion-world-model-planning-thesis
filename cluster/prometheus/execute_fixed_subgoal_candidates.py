#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata as metadata
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch
from gymnasium.spaces import Box

from hi_acting_diagnostics import (
    ActingDiagnosticConfig,
    InstrumentedStagePolicy,
    PreparedBatch,
    build_context,
    reset_world_from_batch,
)
from h_le_wm.eval.determinism import configure_process_determinism


ATTAINMENT_HORIZON = 25
REPEAT_COUNT = 5
REPEAT_SEED_ROOT = 20260728


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def hash_u64(payload: str) -> int:
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def repeat_seeds() -> list[int]:
    return [
        hash_u64(
            f"pusht_expert_train\0{REPEAT_SEED_ROOT}\0fixed_subgoal_attainment_repeat\0{index}"
        )
        & ((1 << 32) - 1)
        for index in range(REPEAT_COUNT)
    ]


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


class CommonRandomNumbersCEMSolver:
    """Vectorized equivalent of independent same-seed official CEM solves.

    Every environment receives the same standardized Gaussian sample at each
    CEM iteration. This is equivalent to running one released CEMSolver per
    candidate with the same seed, while batching model inference on the GPU.
    """

    def __init__(
        self,
        *,
        model: Any,
        num_samples: int,
        var_scale: float,
        n_steps: int,
        topk: int,
        device: str | torch.device,
        seed: int,
        cost_env_chunk_size: int = 16,
    ) -> None:
        self.model = model
        self.num_samples = int(num_samples)
        self.var_scale = float(var_scale)
        self.n_steps = int(n_steps)
        self.topk = int(topk)
        self.device = torch.device(device)
        self.seed = int(seed)
        self.cost_env_chunk_size = int(cost_env_chunk_size)
        if self.cost_env_chunk_size <= 0:
            raise ValueError("cost_env_chunk_size must be positive")
        self.torch_gen = torch.Generator(device=self.device).manual_seed(self.seed)

    def configure(self, *, action_space: Any, n_envs: int, config: Any) -> None:
        self._action_space = action_space
        self._n_envs = int(n_envs)
        self._config = config
        self._action_dim = int(np.prod(action_space.shape[1:]))
        if self.topk <= 0 or self.topk > self.num_samples:
            raise ValueError("invalid CEM top-k")

    @property
    def n_envs(self) -> int:
        return self._n_envs

    @property
    def action_dim(self) -> int:
        return self._action_dim * int(self._config.action_block)

    @property
    def horizon(self) -> int:
        return int(self._config.horizon)

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.solve(*args, **kwargs)

    def _cost_in_environment_chunks(
        self,
        expanded_infos: dict[str, Any],
        candidates: torch.Tensor,
    ) -> torch.Tensor:
        """Evaluate independent environments in bounded batches.

        The LeWM attention kernel cannot accept the effective 64 x 1200
        population in one launch on the cluster GPU. Slicing only the
        environment axis leaves each candidate's CEM population and the
        common random numbers unchanged.
        """

        chunks: list[torch.Tensor] = []
        for start in range(0, self.n_envs, self.cost_env_chunk_size):
            stop = min(start + self.cost_env_chunk_size, self.n_envs)
            chunk_infos: dict[str, Any] = {}
            for key, value in expanded_infos.items():
                if (
                    (torch.is_tensor(value) or isinstance(value, np.ndarray))
                    and value.ndim > 0
                    and value.shape[0] == self.n_envs
                ):
                    chunk_infos[key] = value[start:stop]
                else:
                    chunk_infos[key] = value
            chunk_cost = self.model.get_cost(chunk_infos, candidates[start:stop])
            expected = (stop - start, self.num_samples)
            if chunk_cost.shape != expected:
                raise RuntimeError(
                    f"unexpected low-level cost chunk shape: {tuple(chunk_cost.shape)}; "
                    f"expected {expected}"
                )
            chunks.append(chunk_cost)
        return torch.cat(chunks, dim=0)

    def init_action_distrib(
        self, actions: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        std = self.var_scale * torch.ones(
            [self.n_envs, self.horizon, self.action_dim]
        )
        mean = (
            torch.zeros([self.n_envs, 0, self.action_dim])
            if actions is None
            else actions
        )
        remaining = self.horizon - mean.shape[1]
        if remaining > 0:
            extension = torch.zeros([self.n_envs, remaining, self.action_dim])
            mean = torch.cat([mean, extension], dim=1).to(mean.device)
        return mean, std

    @torch.inference_mode()
    def solve(
        self, info_dict: dict[str, Any], init_action: torch.Tensor | None = None
    ) -> dict[str, Any]:
        mean, std = self.init_action_distrib(init_action)
        mean = mean.to(self.device)
        std = std.to(self.device)
        expanded_infos: dict[str, Any] = {}
        for key, value in info_dict.items():
            if torch.is_tensor(value):
                value = value.to(self.device)
                expanded_infos[key] = value.unsqueeze(1).expand(
                    self.n_envs, self.num_samples, *value.shape[1:]
                )
            elif isinstance(value, np.ndarray):
                expanded_infos[key] = np.repeat(value[:, None, ...], self.num_samples, axis=1)
            else:
                expanded_infos[key] = value

        final_cost: torch.Tensor | None = None
        for _ in range(self.n_steps):
            common_epsilon = torch.randn(
                1,
                self.num_samples,
                self.horizon,
                self.action_dim,
                generator=self.torch_gen,
                device=self.device,
            )
            candidates = common_epsilon.expand(self.n_envs, -1, -1, -1)
            candidates = candidates * std.unsqueeze(1) + mean.unsqueeze(1)
            candidates[:, 0] = mean
            costs = self._cost_in_environment_chunks(expanded_infos, candidates)
            if costs.shape != (self.n_envs, self.num_samples):
                raise RuntimeError(f"unexpected low-level cost shape: {tuple(costs.shape)}")
            top_values, top_indices = torch.topk(
                costs, k=self.topk, dim=1, largest=False
            )
            batch_indices = torch.arange(self.n_envs, device=self.device).unsqueeze(1)
            batch_indices = batch_indices.expand(-1, self.topk)
            elites = candidates[batch_indices, top_indices]
            mean = elites.mean(dim=1)
            std = elites.std(dim=1)
            final_cost = top_values.mean(dim=1)

        if final_cost is None:
            raise RuntimeError("CEM performed no iterations")
        return {
            "actions": mean.detach().cpu(),
            "costs": final_cost.detach().cpu().tolist(),
            "mean": [mean.detach().cpu()],
            "var": [std.detach().cpu()],
        }


class QuadraticToyCost:
    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], candidates: torch.Tensor
    ) -> torch.Tensor:
        target = info_dict["target"]
        return (candidates - target).pow(2).sum(dim=(-1, -2))


def solver_equivalence_self_test() -> dict[str, Any]:
    device = torch.device("cpu")
    config = SimpleNamespace(horizon=2, action_block=1)
    targets = torch.tensor(
        [
            [[0.2, -0.3], [0.5, 0.1]],
            [[-0.4, 0.7], [0.0, -0.2]],
        ],
        dtype=torch.float32,
    )
    action_space_two = Box(
        low=-np.ones((2, 2), dtype=np.float32),
        high=np.ones((2, 2), dtype=np.float32),
        dtype=np.float32,
    )
    batched = CommonRandomNumbersCEMSolver(
        model=QuadraticToyCost(),
        num_samples=16,
        var_scale=1.0,
        n_steps=3,
        topk=4,
        device=device,
        seed=123,
        cost_env_chunk_size=1,
    )
    batched.configure(action_space=action_space_two, n_envs=2, config=config)
    batched_output = batched({"target": targets})["actions"]

    separate = []
    action_space_one = Box(
        low=-np.ones((1, 2), dtype=np.float32),
        high=np.ones((1, 2), dtype=np.float32),
        dtype=np.float32,
    )
    for index in range(2):
        solver = swm.solver.CEMSolver(
            model=QuadraticToyCost(),
            batch_size=1,
            num_samples=16,
            var_scale=1.0,
            n_steps=3,
            topk=4,
            device=device,
            seed=123,
        )
        solver.configure(action_space=action_space_one, n_envs=1, config=config)
        separate.append(solver({"target": targets[index : index + 1]})["actions"][0])
    separate_output = torch.stack(separate)
    max_abs = float((batched_output - separate_output).abs().max().item())
    if max_abs > 1.0e-7:
        raise RuntimeError(
            f"common-random batched CEM differs from separate official solves: {max_abs}"
        )
    return {"status": "ok", "max_abs": max_abs, "device": str(device)}


def repeat_rows(value: np.ndarray, count: int) -> np.ndarray:
    return np.repeat(np.asarray(value)[None, ...], count, axis=0)


def build_fixed_batch(
    *,
    ctx: Any,
    dataset_path: Path,
    source_row: int,
    goal_row: int,
    count: int,
    environment_seed: int,
    start_latent: torch.Tensor,
    goal_latent: torch.Tensor,
    environment: str,
) -> PreparedBatch:
    with h5py.File(dataset_path, "r") as handle:
        if environment == "pusht":
            keys = ("pixels", "action", "proprio", "state", "episode_idx", "step_idx")
            episode_key = "episode_idx"
        else:
            keys = ("pixels", "action", "proprio", "ep_idx", "step_idx")
            episode_key = "ep_idx"
        missing = [key for key in keys if key not in handle]
        if missing:
            raise RuntimeError(f"dataset is missing fixed-batch keys: {missing}")
        source_values = {key: np.asarray(handle[key][source_row]) for key in keys}
        goal_values = {key: np.asarray(handle[key][goal_row]) for key in keys}

    init_step_np = {
        key: repeat_rows(value, count) for key, value in source_values.items()
    }
    # SyncWorld indexes this container and Gymnasium requires the resulting
    # scalar to be a built-in Python int rather than numpy.int64.
    init_step_np["seed"] = np.asarray(
        [int(environment_seed) for _ in range(count)], dtype=object
    )
    goal_step_np: dict[str, np.ndarray] = {}
    for key, value in goal_values.items():
        out_key = "goal" if key == "pixels" else f"goal_{key}"
        goal_step_np[out_key] = repeat_rows(value, count)

    # stable-worldmodel 0.0.6 TwoRoom exposes the physical position as both
    # ``proprio`` and ``state`` in environment infos, while its dataset stores
    # only ``proprio``.  The released reset helper invokes _set_state correctly
    # but then retains the random reset's stale ``state`` info at t=0 unless the
    # dataset-backed alias is supplied here.  Keep both aliases synchronized so
    # the inclusive t=0 attainment trace describes the state actually set.
    if environment == "tworoom":
        init_step_np["state"] = np.asarray(init_step_np["proprio"]).copy()
        goal_step_np["goal_state"] = np.asarray(
            goal_step_np["goal_proprio"]
        ).copy()

    init_plus_goal = copy.deepcopy(init_step_np)
    init_plus_goal.update(copy.deepcopy(goal_step_np))
    shape_prefix = (count, int(ctx.eval_cfg.world.history_size))
    init_step_broadcast = {
        key: np.broadcast_to(
            value[:, None, ...], shape_prefix + value.shape[1:]
        ).copy()
        for key, value in init_plus_goal.items()
    }
    goal_step_broadcast = {
        key: np.broadcast_to(
            value[:, None, ...], shape_prefix + value.shape[1:]
        ).copy()
        for key, value in goal_step_np.items()
    }
    return PreparedBatch(
        sampled_indices=np.full(count, source_row, dtype=np.int64),
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


def current_state_from_infos(infos: dict[str, Any]) -> np.ndarray:
    state = np.asarray(infos["state"])
    if state.ndim >= 3:
        state = state[:, -1]
    return state.astype(np.float32, copy=False)


@torch.inference_mode()
def run_world_loop_with_attainment_trace(
    ctx: Any,
    batch: PreparedBatch,
    policy: InstrumentedStagePolicy,
    *,
    max_steps: int,
) -> dict[str, Any]:
    """Run the fixed-subgoal controller and retain states/latents at t=0..H."""

    world = ctx.world
    world.set_policy(policy)
    episode_successes = np.zeros(world.num_envs, dtype=bool)
    initial_state = current_state_from_infos(world.infos).copy()
    physical_key = "state" if "state" in batch.init_step_np else "proprio"
    expected_initial_state = np.asarray(
        batch.init_step_np[physical_key], dtype=np.float32
    )
    if initial_state.shape != expected_initial_state.shape or not np.array_equal(
        initial_state, expected_initial_state
    ):
        raise RuntimeError(
            "world info does not exactly match the dataset-backed state at t=0"
        )
    state_trace = [initial_state]
    latent_trace = [policy._encode_current_latent(world.infos).detach().clone()]
    for _ in range(int(max_steps)):
        world.infos.update(copy.deepcopy(batch.goal_step_broadcast))
        world.step()
        # Some environments (including stable_worldmodel 0.0.6 TwoRoom)
        # replace rather than extend the info dictionary on step. Restore the
        # immutable goal metadata before the diagnostic policy processes the
        # transition; this is the same goal already supplied to the step.
        world.infos.update(copy.deepcopy(batch.goal_step_broadcast))
        episode_successes = np.logical_or(episode_successes, world.terminateds)
        world.envs.unwrapped._autoreset_envs = np.zeros((world.num_envs,))
        if hasattr(policy, "after_env_step"):
            policy.after_env_step(world.infos)
        state_trace.append(current_state_from_infos(world.infos).copy())
        latent_trace.append(policy._encode_current_latent(world.infos).detach().clone())
    return {
        "episode_successes": episode_successes,
        "success_rate": float(episode_successes.mean() * 100.0),
        "initial_state_sync": {
            "status": "ok",
            "physical_key": physical_key,
            "exact": True,
            "max_abs": 0.0,
        },
        "state_trace": np.stack(state_trace, axis=0).astype(np.float32, copy=False),
        "latent_trace": torch.stack(latent_trace, dim=0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-h5", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--eval-config", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--pool-index", type=int, required=True)
    parser.add_argument("--repeat-index", type=int, required=True)
    parser.add_argument("--candidate-start", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=64)
    parser.add_argument("--low-num-samples", type=int, default=1200)
    parser.add_argument("--low-iters", type=int, default=30)
    parser.add_argument("--low-topk", type=int, default=150)
    parser.add_argument("--cost-env-chunk-size", type=int, default=16)
    parser.add_argument("--stats-npz", type=Path)
    parser.add_argument("--stats-manifest", type=Path)
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
    expected_pool_count = 12 if partition == "P2" else 24
    candidate_classification = (
        f"{partition_key}_stratum3_b0_candidate_pools"
        if environment == "pusht"
        else f"tworoom_{partition_key}_stratum3_b0_candidate_pools"
    )
    execution_classification = (
        f"{partition_key}_candidate_attainment_execution"
        if environment == "pusht"
        else f"tworoom_{partition_key}_candidate_attainment_execution"
    )
    expected_goal_offset = 75 if environment == "pusht" else 25
    expected_high_budget = (1200, 60, 10) if environment == "pusht" else (300, 20, 10)
    expected_low_budget = (1200, 30, 150) if environment == "pusht" else (300, 30, 10)
    low_horizon = 2 if environment == "pusht" else 5

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite candidate-execution output")
    if args.cost_env_chunk_size <= 0:
        raise SystemExit("cost environment chunk size must be positive")
    if args.pool_index < 0 or not 0 <= args.repeat_index < REPEAT_COUNT:
        raise SystemExit("invalid pool or repeat index")
    if args.smoke and args.resource_smoke:
        raise SystemExit("choose only one smoke mode")
    if args.smoke:
        if (
            args.candidate_count,
            args.low_num_samples,
            args.low_iters,
            args.low_topk,
        ) != (2, 64, 2, 8):
            raise SystemExit("smoke execution must use 2 candidates and low CEM 64/2/8")
    elif args.resource_smoke:
        if args.candidate_count not in (8, 64) or (
            args.low_num_samples,
            args.low_iters,
            args.low_topk,
        ) != expected_low_budget:
            raise SystemExit(
                "resource smoke must use 8 or 64 candidates and the published "
                f"{environment} low CEM {expected_low_budget}"
            )
    else:
        if (args.low_num_samples, args.low_iters, args.low_topk) != expected_low_budget:
            raise SystemExit(
                f"full execution must use the published {environment} low CEM budget "
                f"{expected_low_budget}"
            )
        if args.stats_npz is None or args.stats_manifest is None:
            raise SystemExit("full execution requires frozen P1 latent statistics")

    started = time.time()
    seeds = repeat_seeds()
    planner_seed = seeds[args.repeat_index]
    determinism = configure_process_determinism(seed=planner_seed, mode="strict")
    solver_self_test = solver_equivalence_self_test()

    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    if candidate_manifest.get("status") != "ok" or candidate_manifest.get(
        "classification"
    ) != candidate_classification or candidate_manifest.get("partition") != partition or candidate_manifest.get(
        "environment", "pusht"
    ) != environment:
        raise RuntimeError(
            f"input is not the frozen {partition} stratum-3 candidate pool"
        )
    if sha256_file(args.candidate_h5) != candidate_manifest["output_h5_sha256"]:
        raise RuntimeError("candidate-pool HDF5 does not match its manifest")
    if sha256_file(args.checkpoint_file) != candidate_manifest["inputs"][
        "checkpoint_sha256"
    ]:
        raise RuntimeError("checkpoint does not match candidate capture")

    with h5py.File(args.candidate_h5, "r") as handle:
        if (
            handle.attrs.get("classification") != candidate_classification
            or handle.attrs.get("partition") != partition
            or handle.attrs.get("environment", "pusht") != environment
        ):
            raise RuntimeError("candidate HDF5 classification or partition changed")
        pool_count = int(handle["pool_id"].shape[0])
        candidate_total = int(handle["selected_final_index"].shape[1])
        if pool_count != expected_pool_count or candidate_total != 64:
            raise RuntimeError("candidate pool coverage changed")
        if args.pool_index >= pool_count:
            raise RuntimeError("pool index outside candidate artifact")
        end = args.candidate_start + args.candidate_count
        if args.candidate_start < 0 or end > candidate_total:
            raise RuntimeError("candidate slice outside selected pool")
        source_row = int(handle["source_global_row"][args.pool_index])
        goal_row = int(handle["goal_global_row"][args.pool_index])
        episode_id = int(handle["episode_id"][args.pool_index])
        candidate_slots = np.arange(args.candidate_start, end, dtype=np.int64)
        selected_final_index = np.asarray(
            handle["selected_final_index"][args.pool_index, args.candidate_start:end],
            dtype=np.int64,
        )
        targets_np = np.asarray(
            handle["selected_z_subgoal"][args.pool_index, args.candidate_start:end],
            dtype=np.float32,
        )
        start_one = np.asarray(handle["z_init"][args.pool_index], dtype=np.float32)
        goal_one = np.asarray(handle["z_goal"][args.pool_index], dtype=np.float32)

    count = args.candidate_count
    cfg = ActingDiagnosticConfig(
        policy=args.policy,
        experiment_kind=f"{partition_key}_fixed_subgoal_candidate_attainment",
        dataset_name=dataset_name,
        eval_config=str(args.eval_config),
        cache_dir=str(args.stablewm_home),
        img_size=224,
        num_eval=count,
        goal_offset_steps=expected_goal_offset,
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
    targets = torch.from_numpy(targets_np).to(device)
    start_latent = torch.from_numpy(np.repeat(start_one[None], count, axis=0)).to(device)
    goal_latent = torch.from_numpy(np.repeat(goal_one[None], count, axis=0)).to(device)

    batch = build_fixed_batch(
        ctx=ctx,
        dataset_path=args.dataset,
        source_row=source_row,
        goal_row=goal_row,
        count=count,
        environment_seed=planner_seed,
        start_latent=start_latent,
        goal_latent=goal_latent,
        environment=environment,
    )
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
    policy.set_oracle_stage_targets(
        targets.unsqueeze(1), [ATTAINMENT_HORIZON]
    )
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
    if latent_trace.shape != (ATTAINMENT_HORIZON + 1, count, targets.shape[-1]):
        raise RuntimeError(f"unexpected attainment latent trace shape: {tuple(latent_trace.shape)}")
    final_latent = latent_trace[-1]
    difference_trace = latent_trace - targets.unsqueeze(0)
    raw_mse_trace = difference_trace.pow(2).mean(dim=-1)
    raw_rmse_trace = raw_mse_trace.sqrt()
    minimum_raw_rmse, minimum_raw_step = raw_rmse_trace.min(dim=0)
    final_raw_mse = raw_mse_trace[-1]
    final_raw_rmse = raw_rmse_trace[-1]

    standardized_rmse_trace_np: np.ndarray | None = None
    minimum_standardized_rmse_np: np.ndarray | None = None
    minimum_standardized_step_np: np.ndarray | None = None
    stats_info: dict[str, Any] | None = None
    if args.stats_npz is not None or args.stats_manifest is not None:
        if args.stats_npz is None or args.stats_manifest is None:
            raise RuntimeError("both statistics files must be provided together")
        stats_manifest = json.loads(args.stats_manifest.read_text(encoding="utf-8"))
        if sha256_file(args.stats_npz) != stats_manifest["output_npz_sha256"]:
            raise RuntimeError("P1 latent statistics do not match their manifest")
        with np.load(args.stats_npz) as stats:
            std_np = np.asarray(stats["std"], dtype=np.float32)
        if std_np.shape != (targets.shape[-1],) or np.any(std_np < 1.0e-6):
            raise RuntimeError("invalid P1 latent standard deviations")
        std = torch.from_numpy(std_np).to(device)
        standardized_rmse_trace = (
            (difference_trace / std).pow(2).mean(dim=-1).sqrt()
        )
        minimum_standardized_rmse, minimum_standardized_step = (
            standardized_rmse_trace.min(dim=0)
        )
        standardized_rmse_trace_np = (
            standardized_rmse_trace.detach().cpu().numpy().astype(np.float32, copy=False)
        )
        minimum_standardized_rmse_np = (
            minimum_standardized_rmse.detach().cpu().numpy().astype(np.float32, copy=False)
        )
        minimum_standardized_step_np = (
            minimum_standardized_step.detach().cpu().numpy().astype(np.int64, copy=False)
        )
        stats_info = {
            "stats_npz": str(args.stats_npz),
            "stats_npz_sha256": stats_manifest["output_npz_sha256"],
            "stats_manifest_sha256": sha256_file(args.stats_manifest),
        }

    final_state = current_state_from_infos(ctx.world.infos)
    physical_key = "state" if environment == "pusht" else "proprio"
    source_state = np.asarray(batch.init_step_np[physical_key], dtype=np.float32)
    goal_state = np.asarray(batch.goal_step_np[f"goal_{physical_key}"], dtype=np.float32)
    final_latent_np = final_latent.detach().cpu().numpy().astype(np.float32, copy=False)
    latent_trace_np = latent_trace.detach().cpu().numpy().astype(np.float32, copy=False)
    raw_mse_trace_np = raw_mse_trace.detach().cpu().numpy().astype(np.float32, copy=False)
    raw_rmse_trace_np = raw_rmse_trace.detach().cpu().numpy().astype(np.float32, copy=False)
    minimum_raw_rmse_np = minimum_raw_rmse.detach().cpu().numpy().astype(np.float32, copy=False)
    minimum_raw_step_np = minimum_raw_step.detach().cpu().numpy().astype(np.int64, copy=False)
    final_raw_mse_np = final_raw_mse.detach().cpu().numpy().astype(np.float32, copy=False)
    final_raw_rmse_np = final_raw_rmse.detach().cpu().numpy().astype(np.float32, copy=False)

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    classification = (
        f"{'tworoom_' if environment == 'tworoom' else ''}{partition_key}_stratum3_implementation_smoke"
        if args.smoke
        else f"{'tworoom_' if environment == 'tworoom' else ''}{partition_key}_stratum3_resource_smoke"
        if args.resource_smoke
        else execution_classification
    )
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = classification
            output.attrs["environment"] = environment
            output.attrs["dataset_name"] = dataset_name
            output.attrs["pool_index"] = args.pool_index
            output.attrs["repeat_index"] = args.repeat_index
            output.attrs["planner_seed"] = planner_seed
            output.create_dataset("candidate_slot", data=candidate_slots)
            output.create_dataset("selected_final_index", data=selected_final_index)
            output.create_dataset("target_latent", data=targets_np, compression="gzip")
            output.create_dataset("final_latent", data=final_latent_np, compression="gzip")
            output.create_dataset("state_trace", data=loop["state_trace"], compression="gzip")
            output.create_dataset("latent_trace", data=latent_trace_np, compression="gzip")
            output.create_dataset("raw_latent_mse_trace", data=raw_mse_trace_np)
            output.create_dataset("raw_latent_rmse_trace", data=raw_rmse_trace_np)
            output.create_dataset("minimum_raw_latent_rmse", data=minimum_raw_rmse_np)
            output.create_dataset("minimum_raw_latent_step", data=minimum_raw_step_np)
            output.create_dataset("final_raw_latent_mse", data=final_raw_mse_np)
            output.create_dataset("final_raw_latent_rmse", data=final_raw_rmse_np)
            if standardized_rmse_trace_np is not None:
                output.create_dataset(
                    "standardized_latent_rmse_trace", data=standardized_rmse_trace_np
                )
                output.create_dataset(
                    "minimum_standardized_latent_rmse",
                    data=minimum_standardized_rmse_np,
                )
                output.create_dataset(
                    "minimum_standardized_latent_step",
                    data=minimum_standardized_step_np,
                )
            output.create_dataset("source_state", data=source_state)
            output.create_dataset("goal_state", data=goal_state)
            output.create_dataset("final_state", data=final_state)
            output.create_dataset(
                "environment_goal_success",
                data=np.asarray(loop["episode_successes"], dtype=np.bool_),
            )
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_execution_retained={partial_h5}", file=sys.stderr)
        raise

    result = {
        "status": "ok",
        "classification": classification,
        "environment": environment,
        "dataset_name": dataset_name,
        "partition": partition,
        "pool_index": args.pool_index,
        "repeat_index": args.repeat_index,
        "repeat_seeds": seeds,
        "planner_seed": planner_seed,
        "environment_seed": planner_seed,
        "episode_id": episode_id,
        "source_global_row": source_row,
        "goal_global_row": goal_row,
        "candidate_slice": [args.candidate_start, args.candidate_start + count],
        "candidate_count": count,
        "attainment_horizon_primitive_steps": ATTAINMENT_HORIZON,
        "attainment_trace": {
            "steps_inclusive": [0, ATTAINMENT_HORIZON],
            "record_count": ATTAINMENT_HORIZON + 1,
            "primary_distance_statistic": "minimum standardized latent RMSE over steps 0..25",
            "labels_assigned": False,
            "initial_state_sync": loop["initial_state_sync"],
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
            "minimum_raw_latent_rmse_min": float(minimum_raw_rmse_np.min()),
            "minimum_raw_latent_rmse_mean": float(minimum_raw_rmse_np.mean()),
            "minimum_raw_latent_rmse_max": float(minimum_raw_rmse_np.max()),
            "final_raw_latent_rmse_mean": float(final_raw_rmse_np.mean()),
            "minimum_standardized_latent_rmse_min": None
            if minimum_standardized_rmse_np is None
            else float(minimum_standardized_rmse_np.min()),
            "minimum_standardized_latent_rmse_mean": None
            if minimum_standardized_rmse_np is None
            else float(minimum_standardized_rmse_np.mean()),
            "minimum_standardized_latent_rmse_max": None
            if minimum_standardized_rmse_np is None
            else float(minimum_standardized_rmse_np.max()),
            "environment_goal_success_rate": loop["success_rate"],
        },
        "inputs": {
            "candidate_h5": str(args.candidate_h5),
            "candidate_h5_sha256": candidate_manifest["output_h5_sha256"],
            "candidate_manifest_sha256": sha256_file(args.candidate_manifest),
            "dataset": str(args.dataset),
            "checkpoint_file": str(args.checkpoint_file),
            "checkpoint_sha256": candidate_manifest["inputs"]["checkpoint_sha256"],
            "statistics": stats_info,
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
