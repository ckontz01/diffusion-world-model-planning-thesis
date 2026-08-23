#!/usr/bin/env python3
"""Build the frozen balanced P1 cache for E14 long-horizon development."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e14_specs as spec


ROLE_CODE = {"P1_train": 0, "P1_val": 1}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def episode_bounds(episodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if episodes.ndim != 1 or len(episodes) == 0:
        raise ValueError("episode array must be nonempty and one-dimensional")
    if np.any(episodes[1:] < episodes[:-1]):
        raise ValueError("episode array must be sorted")
    changes = np.flatnonzero(episodes[1:] != episodes[:-1]) + 1
    starts = np.concatenate((np.asarray([0], dtype=np.int64), changes))
    stops = np.concatenate((changes, np.asarray([len(episodes)], dtype=np.int64)))
    if np.any(stops <= starts):
        raise RuntimeError("empty episode group")
    return starts, stops


def sample_pair_starts(
    *,
    episode_starts: np.ndarray,
    episode_stops: np.ndarray,
    episode_roles: np.ndarray,
    role: int,
    delta: int,
    quota: int,
    seed: int,
) -> tuple[np.ndarray, int]:
    """Sample unique start rows uniformly within one role/pair cell."""

    lengths = episode_stops - episode_starts
    eligible = episode_roles == role
    capacities = np.where(eligible, np.maximum(lengths - delta, 0), 0).astype(
        np.int64
    )
    total = int(capacities.sum())
    if total < quota:
        raise RuntimeError(
            f"E14 cell role={role}, delta={delta} has {total} rows, needs {quota}"
        )
    generator = np.random.default_rng(seed)
    ranks = np.sort(generator.choice(total, size=quota, replace=False).astype(np.int64))
    active = np.flatnonzero(capacities)
    cumulative = np.cumsum(capacities[active], dtype=np.int64)
    episode_positions = np.searchsorted(cumulative, ranks, side="right")
    previous = np.where(episode_positions == 0, 0, cumulative[episode_positions - 1])
    offsets = ranks - previous
    starts = episode_starts[active[episode_positions]] + offsets
    if len(np.unique(starts)) != quota:
        raise RuntimeError("E14 within-cell sampling produced duplicate starts")
    return starts.astype(np.int64), total


def read_h5_rows(dataset: h5py.Dataset, rows: np.ndarray) -> np.ndarray:
    """Read arbitrary rows once each, preserving repeats and input order."""

    rows = np.asarray(rows, dtype=np.int64)
    if rows.ndim != 1 or np.any(rows < 0) or np.any(rows >= len(dataset)):
        raise ValueError("invalid HDF5 row selection")
    unique, inverse = np.unique(rows, return_inverse=True)
    return np.asarray(dataset[unique])[inverse]


def load_role_map(path: Path) -> dict[int, int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "episode_length", "p1_role"}.issubset(rows[0]):
        raise RuntimeError("invalid E14 P1 role manifest")
    result: dict[int, int] = {}
    for row in rows:
        episode = int(row["episode_id"])
        role = ROLE_CODE.get(row["p1_role"])
        if role is None or episode in result:
            raise RuntimeError("invalid or duplicate E14 P1 role row")
        result[episode] = role
    return result


def masked_action_statistics(
    actions: np.ndarray, tau: np.ndarray, train: np.ndarray
) -> dict[str, np.ndarray]:
    primitive_dim = actions.shape[-1]
    selected = []
    for duration in spec.TAU_VALUES:
        active = train & (tau == duration)
        if active.any():
            selected.append(actions[active, :duration].reshape(-1, primitive_dim))
    if not selected:
        raise RuntimeError("E14 has no train actions for statistics")
    values = np.concatenate(selected).astype(np.float64, copy=False)
    mean = values.mean(axis=0)
    std = values.std(axis=0)
    low = np.quantile(values, 0.001, axis=0)
    high = np.quantile(values, 0.999, axis=0)
    if (
        not np.isfinite(values).all()
        or not np.isfinite(mean).all()
        or not np.isfinite(std).all()
        or np.any(std < 1.0e-6)
        or np.any(high <= low)
    ):
        raise RuntimeError("invalid E14 action statistics")
    return {
        "mean": mean.astype(np.float32),
        "std": std.astype(np.float32),
        "robust_low": low.astype(np.float32),
        "robust_high": high.astype(np.float32),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--p1-role-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    inputs = (
        args.dataset,
        args.latent_h5,
        args.latent_manifest,
        args.transition_h5,
        args.transition_manifest,
        args.p1_role_manifest,
        args.protocol,
        args.source_manifest,
    )
    for path in inputs:
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an E14 cache artifact")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E14 development protocol hash differs")

    task_spec = spec.TASK_SPEC[args.task]
    latent_sha = sha256_file(args.latent_h5)
    transition_sha = sha256_file(args.transition_h5)
    latent_manifest_sha = sha256_file(args.latent_manifest)
    transition_manifest_sha = sha256_file(args.transition_manifest)
    p1_role_sha = sha256_file(args.p1_role_manifest)
    if (
        latent_sha != task_spec["latent_sha256"]
        or transition_sha != task_spec["transition_sha256"]
        or latent_manifest_sha != task_spec["latent_manifest_sha256"]
        or transition_manifest_sha != task_spec["transition_manifest_sha256"]
        or p1_role_sha != task_spec["p1_role_sha256"]
    ):
        raise RuntimeError("E14 input content hash differs")
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    transition_manifest = json.loads(
        args.transition_manifest.read_text(encoding="utf-8")
    )
    if (
        latent_manifest.get("status") != "ok"
        or latent_manifest.get("kind") != "flat_frozen_encoder_latent_cache"
        or latent_manifest.get("dataset_sha256") != task_spec["dataset_sha256"]
        or latent_manifest.get("output_h5_sha256") != latent_sha
        or transition_manifest.get("status") != "ok"
        or transition_manifest.get("kind") != "flat_one_model_step_transition_cache"
        or transition_manifest.get("dataset_sha256") != task_spec["dataset_sha256"]
        or transition_manifest.get("output_h5_sha256") != transition_sha
        or transition_manifest.get("latent_h5_sha256") != latent_sha
        or int(transition_manifest.get("frameskip", -1)) != spec.ACTION_BLOCK
        or int(transition_manifest.get("primitive_action_dim", -1))
        != task_spec["primitive_action_dim"]
    ):
        raise RuntimeError("E14 input lineage differs")

    started = time.time()
    with h5py.File(args.latent_h5, "r") as handle:
        raw_row = np.asarray(handle["row_index"][:], dtype=np.int64)
        episodes = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        steps = np.asarray(handle["step_idx"][:], dtype=np.int64)
        latents = np.asarray(handle["latent"][:], dtype=np.float32)
    if latents.shape != (len(episodes), spec.LATENT_DIM):
        raise RuntimeError("E14 latent array shape differs")
    episode_starts, episode_stops = episode_bounds(episodes)
    unique_episodes = episodes[episode_starts]
    role_map = load_role_map(args.p1_role_manifest)
    if set(unique_episodes.tolist()) != set(role_map):
        raise RuntimeError("E14 latent episodes differ from P1 role manifest")
    episode_roles = np.asarray([role_map[int(value)] for value in unique_episodes], dtype=np.uint8)
    for start, stop in zip(episode_starts, episode_stops):
        expected = np.arange(int(steps[start]), int(steps[start]) + int(stop - start))
        if not np.array_equal(steps[start:stop], expected):
            raise RuntimeError(f"non-contiguous latent steps in episode {episodes[start]}")

    with h5py.File(args.transition_h5, "r") as handle:
        transition_source = np.asarray(handle["source_index"][:], dtype=np.int64)
        transition_target = np.asarray(handle["target_index"][:], dtype=np.int64)
        transition_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        transition_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        transition_role = np.asarray(handle["role"][:], dtype=np.uint8)
        transition_action = np.asarray(handle["action"][:], dtype=np.float32)
        latent_mean = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        latent_std = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
    primitive_dim = int(task_spec["primitive_action_dim"])
    if (
        transition_action.shape != (len(transition_source), spec.ACTION_BLOCK * primitive_dim)
        or latent_mean.shape != (spec.LATENT_DIM,)
        or latent_std.shape != (spec.LATENT_DIM,)
        or np.any(latent_std < 1.0e-6)
        or not np.isfinite(transition_action).all()
    ):
        raise RuntimeError("invalid E14 transition arrays")
    transition_for_source = np.full(len(latents), -1, dtype=np.int64)
    transition_for_source[transition_source] = np.arange(len(transition_source))
    if (
        np.any(transition_source < 0)
        or np.any(transition_target >= len(latents))
        or np.any(episodes[transition_source] != transition_episode)
        or np.any(steps[transition_source] != transition_step)
        or np.any(steps[transition_target] - steps[transition_source] != spec.ACTION_BLOCK)
        or np.any(transition_role != episode_roles[np.searchsorted(unique_episodes, transition_episode)])
    ):
        raise RuntimeError("E14 transition-to-latent mapping differs")

    selected_parts: dict[str, list[np.ndarray]] = {
        key: []
        for key in ("source_index", "local_index", "goal_index", "role", "delta", "tau")
    }
    availability: dict[str, dict[str, int]] = {"P1_train": {}, "P1_val": {}}
    for role_name, total_rows in (
        ("P1_train", spec.TRAIN_ROWS),
        ("P1_val", spec.VALIDATION_ROWS),
    ):
        role = ROLE_CODE[role_name]
        for (delta, tau), quota in spec.row_quotas(total_rows).items():
            starts, available = sample_pair_starts(
                episode_starts=episode_starts,
                episode_stops=episode_stops,
                episode_roles=episode_roles,
                role=role,
                delta=delta,
                quota=quota,
                seed=spec.derived_seed(
                    f"cache|task={args.task}|role={role_name}|delta={delta}|tau={tau}"
                ),
            )
            selected_parts["source_index"].append(starts)
            selected_parts["local_index"].append(starts + tau)
            selected_parts["goal_index"].append(starts + delta)
            selected_parts["role"].append(np.full(quota, role, dtype=np.uint8))
            selected_parts["delta"].append(np.full(quota, delta, dtype=np.int16))
            selected_parts["tau"].append(np.full(quota, tau, dtype=np.int16))
            availability[role_name][f"delta={delta},tau={tau}"] = available

    selected = {key: np.concatenate(value) for key, value in selected_parts.items()}
    expected_rows = spec.TRAIN_ROWS + spec.VALIDATION_ROWS
    if any(len(value) != expected_rows for value in selected.values()):
        raise RuntimeError("E14 selected array length differs")
    permutation_parts = []
    for role_name, role in ROLE_CODE.items():
        rows = np.flatnonzero(selected["role"] == role)
        generator = np.random.default_rng(
            spec.derived_seed(f"cache-shuffle|task={args.task}|role={role_name}")
        )
        permutation_parts.append(rows[generator.permutation(len(rows))])
    permutation = np.concatenate(permutation_parts)
    selected = {key: value[permutation] for key, value in selected.items()}

    source = selected["source_index"]
    local = selected["local_index"]
    goal = selected["goal_index"]
    tau = selected["tau"].astype(np.int64)
    if (
        np.any(episodes[source] != episodes[local])
        or np.any(episodes[source] != episodes[goal])
        or np.any(steps[local] - steps[source] != tau)
        or np.any(steps[goal] - steps[source] != selected["delta"])
    ):
        raise RuntimeError("E14 selected windows cross episodes")

    actions = np.zeros((expected_rows, spec.ACTION_HORIZON, primitive_dim), dtype=np.float32)
    action_mask = np.arange(spec.ACTION_HORIZON)[None, :] < tau[:, None]
    for offset in range(0, spec.ACTION_HORIZON, spec.ACTION_BLOCK):
        active = tau > offset
        rows = transition_for_source[source[active] + offset]
        if np.any(rows < 0):
            raise RuntimeError("E14 selected option lacks a transition block")
        block = transition_action[rows].reshape(-1, spec.ACTION_BLOCK, primitive_dim)
        actions[active, offset : offset + spec.ACTION_BLOCK] = block
    if np.any(actions[~action_mask] != 0.0):
        raise RuntimeError("E14 padded action tail is nonzero")

    selected_raw_rows = raw_row[source]
    with h5py.File(args.dataset, "r") as handle:
        state_dataset = handle[task_spec["state_key"]]
        if state_dataset.shape[1:] != (task_spec["state_dim"],):
            raise RuntimeError("E14 low-dimensional state shape differs")
        states = read_h5_rows(state_dataset, selected_raw_rows).astype(np.float32)
        raw_episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
        raw_step = read_h5_rows(handle["step_idx"], selected_raw_rows).reshape(-1)
        raw_episode = read_h5_rows(handle[raw_episode_key], selected_raw_rows).reshape(-1)
    if (
        states.shape != (expected_rows, task_spec["state_dim"])
        or not np.isfinite(states).all()
        or not np.array_equal(raw_episode.astype(np.int64), episodes[source])
        or not np.array_equal(raw_step.astype(np.int64), steps[source])
    ):
        raise RuntimeError("E14 raw dataset join differs")

    train = selected["role"] == ROLE_CODE["P1_train"]
    validation = ~train
    if train.sum() != spec.TRAIN_ROWS or validation.sum() != spec.VALIDATION_ROWS:
        raise RuntimeError("E14 role counts differ")
    state_mean = states[train].astype(np.float64).mean(axis=0)
    state_std = states[train].astype(np.float64).std(axis=0)
    if np.any(state_std < 1.0e-8) or not np.isfinite(state_std).all():
        raise RuntimeError("E14 state standardizer is invalid")
    action_stats = masked_action_statistics(actions, tau, train)
    normalized_local = (latents[local] - latent_mean) / latent_std
    normalized_goal = (latents[goal] - latent_mean) / latent_std
    residual = (normalized_local - normalized_goal).astype(np.float64)
    residual_mean = residual[train].mean(axis=0)
    residual_std = residual[train].std(axis=0)
    if np.any(residual_std < 1.0e-6) or not np.isfinite(residual_std).all():
        raise RuntimeError("E14 local-residual standardizer is invalid")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as target:
            scalar_chunk = min(65_536, expected_rows)
            for key in ("source_index", "local_index", "goal_index", "role", "delta", "tau"):
                target.create_dataset(
                    key,
                    data=selected[key],
                    chunks=(scalar_chunk,),
                    compression="lzf",
                )
            target.create_dataset(
                "raw_row_index",
                data=selected_raw_rows,
                chunks=(scalar_chunk,),
                compression="lzf",
            )
            target.create_dataset(
                "episode_idx",
                data=episodes[source],
                chunks=(scalar_chunk,),
                compression="lzf",
            )
            target.create_dataset(
                "step_idx",
                data=steps[source],
                chunks=(scalar_chunk,),
                compression="lzf",
            )
            vector_chunk = min(4096, expected_rows)
            target.create_dataset(
                "state", data=states, chunks=(vector_chunk, states.shape[1]), compression="lzf"
            )
            target.create_dataset(
                "action",
                data=actions,
                chunks=(vector_chunk, spec.ACTION_HORIZON, primitive_dim),
                compression="lzf",
            )
            target.create_dataset(
                "action_mask",
                data=action_mask,
                chunks=(vector_chunk, spec.ACTION_HORIZON),
                compression="lzf",
            )
            stats = target.create_group("stats")
            stats.create_dataset("latent_mean", data=latent_mean)
            stats.create_dataset("latent_std", data=latent_std)
            stats.create_dataset("state_mean", data=state_mean.astype(np.float32))
            stats.create_dataset("state_std", data=state_std.astype(np.float32))
            stats.create_dataset("action_mean", data=action_stats["mean"])
            stats.create_dataset("action_std", data=action_stats["std"])
            stats.create_dataset("action_robust_low", data=action_stats["robust_low"])
            stats.create_dataset("action_robust_high", data=action_stats["robust_high"])
            stats.create_dataset("local_residual_mean", data=residual_mean.astype(np.float32))
            stats.create_dataset("local_residual_std", data=residual_std.astype(np.float32))
            target.attrs["task"] = args.task
            target.attrs["protocol_sha256"] = spec.PROTOCOL_SHA256
            target.attrs["latent_h5_sha256"] = latent_sha
            target.attrs["transition_h5_sha256"] = transition_sha
            target.attrs["p1_role_manifest_sha256"] = p1_role_sha
        os.replace(partial, args.output_h5)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    pair_counts: dict[str, dict[str, int]] = {"P1_train": {}, "P1_val": {}}
    for role_name, role in ROLE_CODE.items():
        for delta, duration in spec.DELTA_TAU_PAIRS:
            count = int(
                np.count_nonzero(
                    (selected["role"] == role)
                    & (selected["delta"] == delta)
                    & (selected["tau"] == duration)
                )
            )
            pair_counts[role_name][f"delta={delta},tau={duration}"] = count

    manifest = {
        "status": "ok",
        "kind": "gdp_cem_e14_balanced_variable_horizon_p1_cache",
        "analysis_role": "P1_only_long_horizon_method_development",
        "task": args.task,
        "rows": expected_rows,
        "train_rows": int(train.sum()),
        "validation_rows": int(validation.sum()),
        "delta_values": list(spec.DELTA_VALUES),
        "tau_values": list(spec.TAU_VALUES),
        "pair_counts": pair_counts,
        "availability_before_sampling": availability,
        "latent_dim": spec.LATENT_DIM,
        "state_key": task_spec["state_key"],
        "state_dim": int(task_spec["state_dim"]),
        "primitive_action_dim": primitive_dim,
        "action_horizon": spec.ACTION_HORIZON,
        "dataset": str(args.dataset),
        "declared_dataset_sha256": task_spec["dataset_sha256"],
        "dataset_hash_verified_by_frozen_upstream_manifests": True,
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": latent_sha,
        "latent_manifest_sha256": latent_manifest_sha,
        "transition_h5": str(args.transition_h5),
        "transition_h5_sha256": transition_sha,
        "transition_manifest_sha256": transition_manifest_sha,
        "p1_role_manifest": str(args.p1_role_manifest),
        "p1_role_manifest_sha256": p1_role_sha,
        "protocol": str(args.protocol),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "output_h5": str(args.output_h5),
        "output_h5_sha256": sha256_file(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

