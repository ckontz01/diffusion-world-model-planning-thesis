#!/usr/bin/env python3
"""Physically execute every frozen diagnostic candidate in its released task."""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
import time
from collections import defaultdict
from copy import deepcopy
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import hydra
import numpy as np
import stable_worldmodel as swm
import torch
from acid_alternative.extract_flat_latents import encode, preprocess_pixels
from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)
from omegaconf import OmegaConf


def atomic_h5_path(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.partial-", dir=path.parent
    )
    os.close(descriptor)
    partial = Path(name)
    partial.unlink()
    return partial


class ReplayPolicy:
    """Replay one fixed raw primitive-action sequence per vector environment."""

    def __init__(self) -> None:
        self.env: Any = None
        self.actions: np.ndarray | None = None
        self.cursor = 0

    def set_env(self, env: Any) -> None:
        self.env = env

    def set_actions(self, actions: np.ndarray) -> None:
        actions = np.asarray(actions)
        if actions.ndim != 3 or not np.isfinite(actions).all():
            raise ValueError("replay actions must be finite (B,T,A)")
        self.actions = actions.copy()
        self.cursor = 0

    def get_action(self, info_dict: dict[str, Any], **kwargs: Any) -> np.ndarray:
        del info_dict, kwargs
        if self.actions is None or self.cursor >= self.actions.shape[1]:
            raise RuntimeError("replay policy has no remaining action")
        action = self.actions[:, self.cursor]
        self.cursor += 1
        return action


def current_value(info: dict[str, Any], key: str) -> np.ndarray:
    value = np.asarray(info[key])
    # The released World wraps observations with a history axis.
    if value.ndim >= 3:
        return np.asarray(value[:, -1]).copy()
    return value.copy()


def prepare_dataset_reset(
    *,
    world: Any,
    dataset: Any,
    episodes: list[int],
    starts: list[int],
    goal_offset: int,
    callables: list[dict[str, Any]],
) -> dict[str, np.ndarray]:
    """Mirror stable_worldmodel.World.evaluate_from_dataset setup exactly."""

    ep_idx_arr = np.asarray(episodes)
    start_steps = np.asarray(starts)
    data = dataset.load_chunk(ep_idx_arr, start_steps, start_steps + goal_offset)
    columns = dataset.column_names
    init_per_env: dict[str, list[Any]] = defaultdict(list)
    goal_per_env: dict[str, list[Any]] = defaultdict(list)
    for episode in data:
        for column in columns:
            if column.startswith("goal"):
                continue
            if column.startswith("pixels"):
                episode[column] = episode[column].permute(0, 2, 3, 1)
            if not isinstance(episode[column], (torch.Tensor, np.ndarray)):
                continue
            initial = episode[column][0]
            goal = episode[column][-1]
            if not isinstance(initial, (torch.Tensor, np.ndarray)):
                continue
            if torch.is_tensor(initial):
                initial = initial.numpy()
            if torch.is_tensor(goal):
                goal = goal.numpy()
            init_per_env[column].append(initial)
            goal_per_env[column].append(goal)
    init_step = {key: np.stack(value) for key, value in deepcopy(init_per_env).items()}
    goal_step = {
        ("goal" if key == "pixels" else f"goal_{key}"): np.stack(value)
        for key, value in goal_per_env.items()
    }
    seeds = init_step.get("seed")
    prefix = "variation."
    variations = {
        key.removeprefix(prefix): value
        for key, value in init_step.items()
        if key.startswith(prefix)
    }
    options = [{} for _ in episodes]
    if variations:
        for index in range(len(episodes)):
            options[index]["variation"] = list(variations)
            options[index]["variation_values"] = {
                key: value[index] for key, value in variations.items()
            }
    init_step.update(deepcopy(goal_step))
    world.reset(seed=seeds, options=options)
    for index, env in enumerate(world.envs.unwrapped.envs):
        unwrapped = env.unwrapped
        for spec in callables:
            method_name = spec["method"]
            if not hasattr(unwrapped, method_name):
                raise RuntimeError(f"environment lacks required callable {method_name}")
            prepared: dict[str, Any] = {}
            for argument, declaration in spec.get("args", spec).items():
                value = declaration.get("value")
                if declaration.get("in_dataset", True):
                    if value not in init_step:
                        raise RuntimeError(f"dataset lacks callable value {value}")
                    prepared[argument] = deepcopy(init_step[value][index])
                else:
                    prepared[argument] = value
            getattr(unwrapped, method_name)(**prepared)
    shape_prefix = world.infos["pixels"].shape[:2]
    init_broadcast = {
        key: np.broadcast_to(value[:, None, ...], shape_prefix + value.shape[1:])
        for key, value in init_step.items()
    }
    goal_broadcast = {
        key: np.broadcast_to(value[:, None, ...], shape_prefix + value.shape[1:])
        for key, value in goal_step.items()
    }
    world.infos.update(deepcopy(init_broadcast))
    world.infos.update(deepcopy(goal_broadcast))
    return goal_broadcast


def execute_batch(
    *,
    world: Any,
    policy: ReplayPolicy,
    dataset: Any,
    episodes: list[int],
    starts: list[int],
    goal_offset: int,
    callables: list[dict[str, Any]],
    raw_actions: np.ndarray,
) -> dict[str, np.ndarray]:
    goal_step = prepare_dataset_reset(
        world=world,
        dataset=dataset,
        episodes=episodes,
        starts=starts,
        goal_offset=goal_offset,
        callables=callables,
    )
    policy.set_actions(raw_actions)
    successes = np.zeros(len(episodes), dtype=bool)
    states = [current_value(world.infos, "state")] if "state" in world.infos else None
    pixels = [current_value(world.infos, "pixels")]
    for _ in range(raw_actions.shape[1]):
        world.infos.update(deepcopy(goal_step))
        world.step()
        successes = np.logical_or(successes, np.asarray(world.terminateds, dtype=bool))
        world.envs.unwrapped._autoreset_envs = np.zeros((world.num_envs,))
        if states is not None:
            states.append(current_value(world.infos, "state"))
        pixels.append(current_value(world.infos, "pixels"))
    if policy.cursor != raw_actions.shape[1]:
        raise RuntimeError("replay policy did not consume the complete plan")
    result = {
        "success": successes,
        "pixel_trace": np.stack(pixels),
    }
    if states is not None:
        result["state_trace"] = np.stack(states)
    if "goal_state" in world.infos:
        result["goal_state"] = current_value(world.infos, "goal_state")
    return result


def task_distance(state: np.ndarray, goal: np.ndarray) -> np.ndarray:
    position = np.square(state[..., :4] - goal[..., :4]).sum(axis=-1)
    angle = np.abs(state[..., 4] - goal[..., 4]) % (2.0 * np.pi)
    angle = np.minimum(angle, 2.0 * np.pi - angle)
    return np.sqrt(position + np.square(angle)).astype(np.float32)


def success_from_trace(state: np.ndarray, goal: np.ndarray) -> np.ndarray:
    position = np.linalg.norm(state[..., :4] - goal[..., :4], axis=-1)
    angle = np.abs(state[..., 4] - goal[..., 4]) % (2.0 * np.pi)
    angle = np.minimum(angle, 2.0 * np.pi - angle)
    return (position < 20.0) & (angle < np.pi / 9.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-artifact", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument(
        "--eval-config-name", choices=("pusht", "reacher", "cube"), required=True
    )
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--goal-offset", type=int, default=25)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.candidate_artifact,
        args.candidate_manifest,
        args.code_root,
        args.dataset,
        args.world_model_checkpoint,
        args.source_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    if manifest.get("status") != "ok" or sha256_file(
        args.candidate_artifact
    ) != manifest.get("artifact_sha256"):
        raise RuntimeError("candidate artifact does not match its manifest")
    if manifest.get("analysis_role") not in {"D1", "D2", "C1"}:
        raise RuntimeError("candidate manifest lacks a valid analysis role")
    if manifest.get("source_manifest_sha256") != sha256_file(args.source_manifest):
        raise RuntimeError("candidate/source manifest mismatch")
    if manifest.get("dataset_sha256") != sha256_file(args.dataset):
        raise RuntimeError("candidate/dataset mismatch")
    if manifest.get("world_model_checkpoint_sha256") != sha256_file(
        args.world_model_checkpoint
    ):
        raise RuntimeError("candidate/world-model checkpoint mismatch")
    capture = torch.load(
        args.candidate_artifact, map_location="cpu", weights_only=False
    )
    candidates = capture["candidates"].float()
    rows = capture["rows"]
    if candidates.ndim != 4 or len(rows) != candidates.shape[0]:
        raise RuntimeError("invalid candidate artifact")
    pool_count, candidate_count, horizon, macro_action_dim = candidates.shape
    primitive_dim = len(capture["planner_primitive_action_mean"])
    if macro_action_dim % primitive_dim != 0:
        raise RuntimeError("macro action dimension is not a primitive-action multiple")
    action_block = macro_action_dim // primitive_dim
    primitive_steps = horizon * action_block
    normalized = candidates.reshape(
        pool_count, candidate_count, primitive_steps, primitive_dim
    ).numpy()
    # sklearn StandardScaler.inverse_transform performs these operations
    # in-place and therefore preserves the float32 input dtype.
    raw_actions = normalized.copy()
    raw_actions *= np.asarray(capture["planner_primitive_action_std"], dtype=np.float64)
    raw_actions += np.asarray(
        capture["planner_primitive_action_mean"], dtype=np.float64
    )
    if raw_actions.dtype != np.float32 or not np.isfinite(raw_actions).all():
        raise RuntimeError("invalid inverse-transformed primitive actions")

    torch.manual_seed(0)
    np.random.seed(0)
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("candidate execution requires CUDA for latent encoding")
    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.eval_config_name)
    cfg.world.num_envs = pool_count
    cfg.world.max_episode_steps = 2 * primitive_steps
    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        args.dataset_name,
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("dataset name resolves to different bytes")
    policy = ReplayPolicy()
    world.set_policy(policy)
    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("resolved world-model checkpoint differs from declaration")
    encoder = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    )
    encoder = encoder.to(device).eval()
    encoder.requires_grad_(False)
    if hasattr(encoder, "interpolate_pos_encoding"):
        encoder.interpolate_pos_encoding = True
    episodes = [int(row["episode_id"]) for row in rows]
    starts = [int(row["start_step"]) for row in rows]
    callables = OmegaConf.to_container(cfg.eval.get("callables"), resolve=True)

    state_trace: np.ndarray | None = None
    executed_latent: np.ndarray | None = None
    environment_success = np.empty((pool_count, candidate_count), dtype=bool)
    target_state: np.ndarray | None = None
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    macro_indices = np.arange(0, primitive_steps + 1, action_block)
    for candidate_index in range(candidate_count):
        result = execute_batch(
            world=world,
            policy=policy,
            dataset=dataset,
            episodes=episodes,
            starts=starts,
            goal_offset=args.goal_offset,
            callables=callables,
            raw_actions=raw_actions[:, candidate_index],
        )
        if "state_trace" in result:
            trace = np.asarray(result["state_trace"], dtype=np.float32).transpose(
                1, 0, 2
            )
            expected_prefix = (pool_count, primitive_steps + 1)
            if trace.shape[:2] != expected_prefix or trace.ndim != 3:
                raise RuntimeError(f"unexpected state trace shape: {trace.shape}")
            if state_trace is None:
                state_trace = np.empty(
                    (pool_count, candidate_count, *trace.shape[1:]), dtype=np.float32
                )
            if trace.shape != state_trace.shape[:1] + state_trace.shape[2:]:
                raise RuntimeError("state trace shape changed across candidates")
            state_trace[:, candidate_index] = trace
        if "goal_state" in result:
            goals = np.asarray(result["goal_state"], dtype=np.float32)
            if target_state is None:
                target_state = goals
            elif not np.array_equal(target_state, goals):
                raise RuntimeError("goal state changed across candidate resets")
        environment_success[:, candidate_index] = np.asarray(result["success"])
        macro_pixels = np.asarray(result["pixel_trace"])[macro_indices]
        flat_pixels = macro_pixels.reshape(
            (horizon + 1) * pool_count, *macro_pixels.shape[2:]
        )
        latent = encode(encoder, preprocess_pixels(flat_pixels, device))
        latent_np = latent.detach().cpu().numpy().reshape(horizon + 1, pool_count, -1)
        latent_np = latent_np.transpose(1, 0, 2).astype(np.float32, copy=False)
        if latent_np.shape[:2] != (pool_count, horizon + 1) or latent_np.ndim != 3:
            raise RuntimeError(f"unexpected executed latent shape: {latent_np.shape}")
        if executed_latent is None:
            executed_latent = np.empty(
                (pool_count, candidate_count, *latent_np.shape[1:]), dtype=np.float32
            )
        if latent_np.shape != executed_latent.shape[:1] + executed_latent.shape[2:]:
            raise RuntimeError("executed latent shape changed across candidates")
        executed_latent[:, candidate_index] = latent_np
        if (candidate_index + 1) % 10 == 0 or candidate_index + 1 == candidate_count:
            print(
                f"executed_candidates_per_pool={candidate_index + 1}/{candidate_count}",
                flush=True,
            )
    if executed_latent is None:
        raise RuntimeError("no candidate was executed")
    torch.cuda.synchronize()

    distance_trace: np.ndarray | None = None
    final_distance: np.ndarray | None = None
    minimum_distance: np.ndarray | None = None
    minimum_distance_step: np.ndarray | None = None
    if args.eval_config_name == "pusht":
        if state_trace is None or target_state is None:
            raise RuntimeError("PushT execution lacks state/goal-state diagnostics")
        target = target_state[:, None, None, :]
        distance_trace = task_distance(state_trace, target)
        recomputed_success = success_from_trace(state_trace[:, :, 1:], target)
        if not np.array_equal(environment_success, recomputed_success.any(axis=2)):
            raise RuntimeError("PushT state traces disagree with environment success")
        final_distance = distance_trace[:, :, -1]
        minimum_distance = distance_trace.min(axis=2)
        minimum_distance_step = distance_trace.argmin(axis=2).astype(np.int16)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_h5 = args.output_dir / "candidate-executions.h5"
    partial = atomic_h5_path(output_h5)
    try:
        with h5py.File(partial, "x") as output:
            output.attrs["kind"] = "flat_same_candidate_physical_executions"
            output.attrs["candidate_artifact_sha256"] = sha256_file(
                args.candidate_artifact
            )
            output.attrs["dataset_sha256"] = sha256_file(args.dataset)
            output.attrs["world_model_checkpoint_sha256"] = sha256_file(
                args.world_model_checkpoint
            )
            output.create_dataset(
                "executed_latent", data=executed_latent, compression="lzf"
            )
            output.create_dataset("environment_success", data=environment_success)
            if state_trace is not None:
                output.create_dataset(
                    "state_trace", data=state_trace, compression="lzf"
                )
            if target_state is not None:
                output.create_dataset("target_state", data=target_state)
            if distance_trace is not None:
                output.create_dataset(
                    "task_distance_trace", data=distance_trace, compression="lzf"
                )
                output.create_dataset("final_task_distance", data=final_distance)
                output.create_dataset("minimum_task_distance", data=minimum_distance)
                output.create_dataset(
                    "minimum_task_distance_step", data=minimum_distance_step
                )
            output.create_dataset("raw_actions", data=raw_actions, compression="lzf")
            output.flush()
        os.replace(partial, output_h5)
    finally:
        partial.unlink(missing_ok=True)
    result_manifest = {
        "status": "ok",
        "kind": "flat_same_candidate_physical_executions",
        "analysis_role": manifest.get("analysis_role"),
        "confirmation_authorization_sha256": manifest.get(
            "confirmation_authorization_sha256"
        ),
        "eval_config_name": args.eval_config_name,
        "pool_count": pool_count,
        "candidates_per_pool": candidate_count,
        "primitive_steps_per_candidate": primitive_steps,
        "total_candidate_executions": pool_count * candidate_count,
        "latent_dimension": int(executed_latent.shape[-1]),
        "task_state_diagnostics_available": distance_trace is not None,
        "candidate_artifact": str(args.candidate_artifact),
        "candidate_artifact_sha256": sha256_file(args.candidate_artifact),
        "candidate_manifest": str(args.candidate_manifest),
        "candidate_manifest_sha256": sha256_file(args.candidate_manifest),
        "eval_manifest_sha256": manifest.get("eval_manifest_sha256"),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "output_h5": str(output_h5),
        "output_h5_sha256": sha256_file(output_h5),
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
            "peak_cuda_memory_reserved_bytes": int(
                torch.cuda.max_memory_reserved(device)
            ),
        },
    }
    atomic_write_json(args.output_dir / "manifest.json", result_manifest)
    print(json.dumps(result_manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
