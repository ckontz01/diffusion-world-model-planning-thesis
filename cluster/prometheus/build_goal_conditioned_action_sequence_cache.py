#!/usr/bin/env python3
"""Build exact 25-step P1 action-sequence examples for GDP-CEM.

The vetted transition cache contains every five-primitive-step transition.  A
GDP-CEM example joins transitions starting at t, t+5, ..., t+20, producing the
current latent index, the t+25 goal latent index, and five planner macro actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np


ROLE_CODE = {"P1_train": 0, "P1_val": 1}
MACRO_HORIZON = 5
PRIMITIVE_STEPS_PER_MACRO = 5
GOAL_OFFSET = MACRO_HORIZON * PRIMITIVE_STEPS_PER_MACRO
PROTOCOL_SHA256 = "50690a07e2a2a949b0d0a9c5e43a8c4eb53b483780021ea20142031264de3299"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
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
    if episodes.ndim != 1 or not len(episodes):
        raise ValueError("transition episode array must be nonempty and one-dimensional")
    changes = np.flatnonzero(episodes[1:] != episodes[:-1]) + 1
    starts = np.concatenate((np.asarray([0], dtype=np.int64), changes))
    stops = np.concatenate((changes, np.asarray([len(episodes)], dtype=np.int64)))
    if np.any(stops <= starts):
        raise RuntimeError("empty transition episode group")
    return starts, stops


def assemble_sequences(
    *,
    source_index: np.ndarray,
    target_index: np.ndarray,
    episode: np.ndarray,
    step: np.ndarray,
    role: np.ndarray,
    action: np.ndarray,
) -> dict[str, np.ndarray]:
    """Join non-overlapping five-step blocks without crossing episodes."""

    count = len(source_index)
    if not (
        count
        == len(target_index)
        == len(episode)
        == len(step)
        == len(role)
        == len(action)
    ):
        raise ValueError("transition arrays have inconsistent lengths")
    if action.ndim != 2 or action.shape[1] % PRIMITIVE_STEPS_PER_MACRO:
        raise ValueError("transition action blocks have an invalid shape")
    starts, stops = episode_bounds(episode)
    group_lengths = stops - starts
    valid_counts = np.maximum(group_lengths - (GOAL_OFFSET - PRIMITIVE_STEPS_PER_MACRO), 0)
    total = int(valid_counts.sum())
    if total <= 0:
        raise RuntimeError("no complete 25-step sequences")

    output = {
        "source_index": np.empty(total, dtype=np.int64),
        "goal_index": np.empty(total, dtype=np.int64),
        "episode_idx": np.empty(total, dtype=np.int64),
        "step_idx": np.empty(total, dtype=np.int64),
        "role": np.empty(total, dtype=np.uint8),
        "action": np.empty(
            (total, MACRO_HORIZON, action.shape[1]), dtype=np.float32
        ),
    }
    cursor = 0
    for group_start, group_stop, valid_count in zip(starts, stops, valid_counts):
        valid_count = int(valid_count)
        if valid_count == 0:
            continue
        group_start = int(group_start)
        group_stop = int(group_stop)
        group_slice = slice(group_start, group_stop)
        expected_steps = np.arange(
            int(step[group_start]), int(step[group_start]) + group_stop - group_start
        )
        if not np.array_equal(step[group_slice], expected_steps):
            raise RuntimeError(f"episode {episode[group_start]} transition steps are not contiguous")
        if np.any(role[group_slice] != role[group_start]):
            raise RuntimeError(f"episode {episode[group_start]} spans P1 roles")
        destination = slice(cursor, cursor + valid_count)
        first_rows = slice(group_start, group_start + valid_count)
        last_rows = slice(
            group_start + GOAL_OFFSET - PRIMITIVE_STEPS_PER_MACRO,
            group_start + GOAL_OFFSET - PRIMITIVE_STEPS_PER_MACRO + valid_count,
        )
        output["source_index"][destination] = source_index[first_rows]
        output["goal_index"][destination] = target_index[last_rows]
        output["episode_idx"][destination] = episode[first_rows]
        output["step_idx"][destination] = step[first_rows]
        output["role"][destination] = role[first_rows]
        for macro in range(MACRO_HORIZON):
            block_start = group_start + macro * PRIMITIVE_STEPS_PER_MACRO
            block_rows = slice(block_start, block_start + valid_count)
            output["action"][destination, macro] = action[block_rows]
        cursor += valid_count
    if cursor != total:
        raise RuntimeError("sequence-cache fill count differs")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.latent_h5,
        args.latent_manifest,
        args.transition_h5,
        args.transition_manifest,
        args.protocol,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite GDP-CEM sequence cache")
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("GDP-CEM sequence-cache protocol hash differs")
    started = time.time()

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    transition_manifest = json.loads(
        args.transition_manifest.read_text(encoding="utf-8")
    )
    latent_sha = sha256_file(args.latent_h5)
    transition_sha = sha256_file(args.transition_h5)
    if (
        latent_manifest.get("status") != "ok"
        or latent_manifest.get("output_h5_sha256") != latent_sha
        or transition_manifest.get("status") != "ok"
        or transition_manifest.get("kind") != "flat_one_model_step_transition_cache"
        or transition_manifest.get("output_h5_sha256") != transition_sha
        or transition_manifest.get("latent_h5_sha256") != latent_sha
        or int(transition_manifest.get("frameskip", -1))
        != PRIMITIVE_STEPS_PER_MACRO
    ):
        raise RuntimeError("GDP-CEM input lineage differs")

    with h5py.File(args.latent_h5, "r") as handle:
        latent_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_episodes = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        latent_steps = np.asarray(handle["step_idx"][:], dtype=np.int64)
        latent_shape = tuple(handle["latent"].shape)
    with h5py.File(args.transition_h5, "r") as handle:
        source_index = np.asarray(handle["source_index"][:], dtype=np.int64)
        target_index = np.asarray(handle["target_index"][:], dtype=np.int64)
        episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        role = np.asarray(handle["role"][:], dtype=np.uint8)
        action = np.asarray(handle["action"][:], dtype=np.float32)
        latent_mean = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        latent_std = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        primitive_mean = np.asarray(
            handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
        )
        primitive_std = np.asarray(
            handle["stats/planner_primitive_action_std"][:], dtype=np.float64
        )

    if (
        latent_shape[0] != len(latent_rows)
        or np.any(source_index < 0)
        or np.any(target_index >= len(latent_rows))
        or set(np.unique(role).tolist()) != set(ROLE_CODE.values())
    ):
        raise RuntimeError("GDP-CEM input arrays are invalid")
    sequences = assemble_sequences(
        source_index=source_index,
        target_index=target_index,
        episode=episode,
        step=step,
        role=role,
        action=action,
    )
    source = sequences["source_index"]
    goal = sequences["goal_index"]
    if (
        np.any(latent_episodes[source] != sequences["episode_idx"])
        or np.any(latent_episodes[goal] != sequences["episode_idx"])
        or np.any(latent_steps[source] != sequences["step_idx"])
        or np.any(latent_steps[goal] - latent_steps[source] != GOAL_OFFSET)
    ):
        raise RuntimeError("GDP-CEM sequence joins cross an episode or miss t+25")
    if not np.isfinite(sequences["action"]).all():
        raise RuntimeError("GDP-CEM action sequences are non-finite")

    train = sequences["role"] == ROLE_CODE["P1_train"]
    validation = sequences["role"] == ROLE_CODE["P1_val"]
    if not train.any() or not validation.any():
        raise RuntimeError("GDP-CEM cache requires both P1 roles")
    primitive_dim = int(action.shape[1] // PRIMITIVE_STEPS_PER_MACRO)
    train_actions = sequences["action"][train].reshape(-1, primitive_dim)
    robust_low = np.quantile(train_actions, 0.001, axis=0).astype(np.float32)
    robust_high = np.quantile(train_actions, 0.999, axis=0).astype(np.float32)

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as target:
            chunk = min(65_536, len(source))
            for key in ("source_index", "goal_index", "episode_idx", "step_idx", "role"):
                target.create_dataset(
                    key,
                    data=sequences[key],
                    chunks=(chunk,),
                    compression="lzf",
                )
            action_chunk = min(4096, len(source))
            target.create_dataset(
                "action",
                data=sequences["action"],
                chunks=(action_chunk, MACRO_HORIZON, action.shape[1]),
                compression="lzf",
            )
            stats = target.create_group("stats")
            stats.create_dataset("latent_mean", data=latent_mean)
            stats.create_dataset("latent_std", data=latent_std)
            stats.create_dataset("planner_primitive_action_mean", data=primitive_mean)
            stats.create_dataset("planner_primitive_action_std", data=primitive_std)
            stats.create_dataset("p1_train_action_robust_low", data=robust_low)
            stats.create_dataset("p1_train_action_robust_high", data=robust_high)
            target.attrs["goal_offset"] = GOAL_OFFSET
            target.attrs["macro_horizon"] = MACRO_HORIZON
            target.attrs["primitive_steps_per_macro"] = PRIMITIVE_STEPS_PER_MACRO
            target.attrs["latent_h5_sha256"] = latent_sha
            target.attrs["transition_h5_sha256"] = transition_sha
        os.replace(partial, args.output_h5)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    manifest = {
        "status": "ok",
        "kind": "gdp_cem_p1_goal_conditioned_action_sequence_cache",
        "analysis_role": "P1_only_method_development",
        "goal_offset": GOAL_OFFSET,
        "macro_horizon": MACRO_HORIZON,
        "primitive_steps_per_macro": PRIMITIVE_STEPS_PER_MACRO,
        "sequences": len(source),
        "train_sequences": int(train.sum()),
        "validation_sequences": int(validation.sum()),
        "latent_dim": int(latent_shape[1]),
        "primitive_action_dim": primitive_dim,
        "macro_action_dim": int(action.shape[1]),
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": latent_sha,
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "transition_h5": str(args.transition_h5),
        "transition_h5_sha256": transition_sha,
        "transition_manifest_sha256": sha256_file(args.transition_manifest),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "protocol": str(args.protocol),
        "protocol_sha256": PROTOCOL_SHA256,
        "output_h5": str(args.output_h5),
        "output_h5_sha256": sha256_file(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "protected_c1_i1_read": False,
        "d2_read": False,
        "d3_read": False,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
