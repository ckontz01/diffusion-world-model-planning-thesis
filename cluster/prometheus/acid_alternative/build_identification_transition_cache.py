#!/usr/bin/env python3
"""Build I1 latent/action transitions using frozen P1 training statistics."""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path

import h5py
import numpy as np

from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.task_registry import TASKS


def read_episode_manifest(path: Path) -> list[int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "partition"}.issubset(rows[0]):
        raise RuntimeError("invalid I1 episode manifest")
    episodes = [int(row["episode_id"]) for row in rows]
    if (
        len(episodes) != len(set(episodes))
        or any(row["partition"] != "I1" for row in rows)
    ):
        raise RuntimeError("I1 episode manifest has duplicates or wrong roles")
    return episodes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=tuple(TASKS), required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--identification-manifest", type=Path, required=True)
    parser.add_argument("--training-transition-h5", type=Path, required=True)
    parser.add_argument("--training-transition-manifest", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--frameskip", type=int, default=5)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.dataset,
        args.latent_h5,
        args.latent_manifest,
        args.identification_manifest,
        args.training_transition_h5,
        args.training_transition_manifest,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.frameskip <= 0:
        raise ValueError("frameskip must be positive")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite I1 transition output")

    source_hash = sha256_file(args.source_manifest)
    dataset_hash = sha256_file(args.dataset)
    latent_hash = sha256_file(args.latent_h5)
    training_hash = sha256_file(args.training_transition_h5)
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    training_manifest = json.loads(
        args.training_transition_manifest.read_text(encoding="utf-8")
    )
    if (
        latent_manifest.get("status") != "ok"
        or latent_manifest.get("kind") != "flat_frozen_encoder_latent_cache"
        or latent_manifest.get("output_h5_sha256") != latent_hash
        or latent_manifest.get("dataset_sha256") != dataset_hash
        or latent_manifest.get("source_manifest_sha256") != source_hash
        or latent_manifest.get("partition_manifest_sha256")
        != sha256_file(args.identification_manifest)
        or latent_manifest.get("partitions") != ["I1"]
    ):
        raise RuntimeError("I1 latent cache provenance mismatch")
    if (
        training_manifest.get("status") != "ok"
        or training_manifest.get("kind") != "flat_one_model_step_transition_cache"
        or training_manifest.get("output_h5_sha256") != training_hash
        or training_manifest.get("dataset_sha256") != dataset_hash
        or training_manifest.get("source_manifest_sha256") != source_hash
        or training_manifest.get("frameskip") != args.frameskip
    ):
        raise RuntimeError("training transition cache provenance mismatch")

    episodes = read_episode_manifest(args.identification_manifest)
    started = time.time()
    with h5py.File(args.dataset, "r", rdcc_nbytes=512 * 1024 * 1024) as source:
        offsets = np.asarray(source["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(source["ep_len"][:], dtype=np.int64)
        raw_actions = np.asarray(source["action"][:], dtype=np.float32)
    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        cache_episodes = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        cache_steps = np.asarray(handle["step_idx"][:], dtype=np.int64)
        latents = np.asarray(handle["latent"][:], dtype=np.float32)
    with h5py.File(args.training_transition_h5, "r") as handle:
        planner_mean = np.asarray(
            handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
        )
        planner_std = np.asarray(
            handle["stats/planner_primitive_action_std"][:], dtype=np.float64
        )
        latent_mean = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        latent_std = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        acid_action_mean = np.asarray(
            handle["stats/acid_action_mean"][:], dtype=np.float32
        )
        acid_action_std = np.asarray(
            handle["stats/acid_action_std"][:], dtype=np.float32
        )
    if (
        len(offsets) != len(lengths)
        or raw_actions.ndim != 2
        or len(raw_actions) != int(np.sum(lengths))
        or any(episode < 0 or episode >= len(lengths) for episode in episodes)
    ):
        raise RuntimeError("I1 episode manifest or source dataset is inconsistent")
    if (
        not np.all(cache_rows[1:] > cache_rows[:-1])
        or len(cache_rows) != len(latents)
        or len(cache_rows) != len(cache_episodes)
        or len(cache_rows) != len(cache_steps)
        or not np.isfinite(latents).all()
    ):
        raise RuntimeError("I1 latent cache row identities are invalid")
    expected_action_dim = raw_actions.shape[1] * args.frameskip
    if (
        training_manifest.get("latent_dim") != latents.shape[1]
        or training_manifest.get("action_block_dim") != expected_action_dim
        or planner_mean.shape != (raw_actions.shape[1],)
        or planner_std.shape != (raw_actions.shape[1],)
        or latent_mean.shape != (latents.shape[1],)
        or latent_std.shape != (latents.shape[1],)
        or acid_action_mean.shape != (expected_action_dim,)
        or acid_action_std.shape != (expected_action_dim,)
        or not np.isfinite(planner_mean).all()
        or not np.isfinite(planner_std).all()
        or not np.isfinite(latent_mean).all()
        or not np.isfinite(latent_std).all()
        or not np.isfinite(acid_action_mean).all()
        or not np.isfinite(acid_action_std).all()
        or np.any(planner_std < 1.0e-6)
        or np.any(latent_std < 1.0e-6)
        or np.any(acid_action_std < 1.0e-6)
    ):
        raise RuntimeError("frozen P1 training statistics are inconsistent")
    normalized_actions = raw_actions.copy()
    normalized_actions -= planner_mean
    normalized_actions /= planner_std
    # Released datasets use NaN as an episode-terminal action sentinel.  It is
    # allowed globally but must never enter a valid five-step transition below.
    if normalized_actions.dtype != np.float32 or np.isinf(normalized_actions).any():
        raise RuntimeError("I1 action normalization is invalid")

    source_indices = []
    target_indices = []
    blocks = []
    pair_episodes = []
    pair_steps = []
    for episode in episodes:
        count = int(lengths[episode]) - args.frameskip
        if count <= 0:
            raise RuntimeError(f"I1 episode {episode} is too short")
        first_rows = int(offsets[episode]) + np.arange(count, dtype=np.int64)
        second_rows = first_rows + args.frameskip
        first_cache = np.searchsorted(cache_rows, first_rows)
        second_cache = np.searchsorted(cache_rows, second_rows)
        if (
            np.any(first_cache >= len(cache_rows))
            or np.any(second_cache >= len(cache_rows))
            or not np.array_equal(cache_rows[first_cache], first_rows)
            or not np.array_equal(cache_rows[second_cache], second_rows)
        ):
            raise RuntimeError(f"I1 episode {episode} is incomplete in latent cache")
        action = np.stack(
            [
                normalized_actions[row : row + args.frameskip].reshape(-1)
                for row in first_rows
            ]
        ).astype(np.float32, copy=False)
        if not np.isfinite(action).all():
            raise RuntimeError(
                f"I1 episode {episode} contains a non-finite action inside a valid transition"
            )
        source_indices.append(first_cache.astype(np.int64))
        target_indices.append(second_cache.astype(np.int64))
        blocks.append(action)
        pair_episodes.append(np.full(count, episode, dtype=np.int64))
        pair_steps.append(cache_steps[first_cache].astype(np.int64, copy=False))
    source_index = np.concatenate(source_indices)
    target_index = np.concatenate(target_indices)
    actions = np.concatenate(blocks)
    episode_idx = np.concatenate(pair_episodes)
    step_idx = np.concatenate(pair_steps)
    if (
        np.any(cache_episodes[source_index] != episode_idx)
        or np.any(cache_episodes[target_index] != episode_idx)
        or np.any(cache_steps[target_index] - cache_steps[source_index] != args.frameskip)
    ):
        raise RuntimeError("I1 transition crosses an episode or has the wrong gap")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as output:
            chunk = min(65_536, len(source_index))
            for name, value in (
                ("source_index", source_index),
                ("target_index", target_index),
                ("episode_idx", episode_idx),
                ("step_idx", step_idx),
            ):
                output.create_dataset(
                    name, data=value, chunks=(chunk,), compression="lzf"
                )
            output.create_dataset(
                "action",
                data=actions,
                chunks=(min(8192, len(actions)), actions.shape[1]),
                compression="lzf",
            )
            stats = output.create_group("stats")
            stats.create_dataset("latent_mean", data=latent_mean)
            stats.create_dataset("latent_std", data=latent_std)
            stats.create_dataset("acid_action_mean", data=acid_action_mean)
            stats.create_dataset("acid_action_std", data=acid_action_std)
            stats.create_dataset("planner_primitive_action_mean", data=planner_mean)
            stats.create_dataset("planner_primitive_action_std", data=planner_std)
            output.attrs["frameskip"] = args.frameskip
            output.attrs["task"] = args.task
            output.attrs["dataset_sha256"] = dataset_hash
            output.attrs["latent_h5_sha256"] = latent_hash
            output.attrs["source_manifest_sha256"] = source_hash
            output.attrs["training_transition_h5_sha256"] = training_hash
            output.attrs["identification_manifest_sha256"] = sha256_file(
                args.identification_manifest
            )
        os.replace(partial, args.output_h5)
    finally:
        partial.unlink(missing_ok=True)
    result = {
        "status": "ok",
        "kind": "acid_alternative_i1_transition_cache",
        "task": args.task,
        "data_role": "I1",
        "episodes": len(episodes),
        "pairs": len(source_index),
        "frameskip": args.frameskip,
        "latent_dim": int(latents.shape[1]),
        "action_block_dim": int(actions.shape[1]),
        "dataset_sha256": dataset_hash,
        "latent_h5_sha256": latent_hash,
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "identification_manifest_sha256": sha256_file(
            args.identification_manifest
        ),
        "training_transition_h5_sha256": training_hash,
        "training_transition_manifest_sha256": sha256_file(
            args.training_transition_manifest
        ),
        "source_manifest_sha256": source_hash,
        "confirmation_identification_outcomes_computed": False,
        "output_h5": str(args.output_h5),
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_write_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
