#!/usr/bin/env python3
"""Build one-model-step latent/action tuples without crossing episodes."""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path

import h5py
import numpy as np
from sklearn import preprocessing

from acid_alternative.io_utils import atomic_write_json, sha256_file

ROLE_CODE = {"P1_train": 0, "P1_val": 1}


def fit_finite_action_standardizer(
    raw_actions: np.ndarray,
) -> preprocessing.StandardScaler:
    """Fit the exact action processor used by the released evaluator."""

    raw_actions = np.asarray(raw_actions, dtype=np.float32)
    if raw_actions.ndim != 2 or raw_actions.shape[1] == 0:
        raise ValueError("raw actions must be a nonempty two-dimensional array")
    # Deliberately use the released evaluator's NaN filter and sklearn class,
    # rather than an independently reimplemented approximation.
    usable_rows = ~np.isnan(raw_actions).any(axis=1)
    if not usable_rows.any():
        raise RuntimeError("source action column has no non-NaN row")
    usable_actions = raw_actions[usable_rows]
    if not np.isfinite(usable_actions).all():
        raise RuntimeError("source action column contains infinity")
    processor = preprocessing.StandardScaler()
    processor.fit(usable_actions)
    mean = np.asarray(processor.mean_)
    std = np.asarray(processor.scale_)
    if mean.dtype != np.float64 or std.dtype != np.float64:
        raise RuntimeError("unexpected StandardScaler statistics dtype")
    if not np.isfinite(mean).all() or not np.isfinite(std).all():
        raise RuntimeError("source action statistics are non-finite")
    if np.any(std < 1.0e-6):
        raise RuntimeError("source action has a near-zero standard deviation")
    return processor


def load_roles(path: Path) -> dict[int, int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "p1_role"}.issubset(rows[0]):
        raise ValueError("invalid P1 role manifest")
    roles: dict[int, int] = {}
    for row in rows:
        role_name = row["p1_role"]
        if role_name not in ROLE_CODE:
            raise ValueError(f"unexpected P1 role {role_name}")
        episode = int(row["episode_id"])
        if episode in roles:
            raise ValueError(f"duplicate episode {episode}")
        roles[episode] = ROLE_CODE[role_name]
    return roles


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--p1-role-manifest", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--frameskip", type=int, default=5)
    parser.add_argument("--episode-limit", type=int)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.dataset,
        args.latent_h5,
        args.latent_manifest,
        args.p1_role_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.source_manifest is not None and not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    if args.frameskip <= 0 or (
        args.episode_limit is not None and args.episode_limit <= 0
    ):
        raise ValueError("frameskip and episode limit must be positive")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing output")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok":
        raise RuntimeError("latent manifest is not complete")
    if sha256_file(args.latent_h5) != latent_manifest.get("output_h5_sha256"):
        raise RuntimeError("latent HDF5 hash differs from its manifest")
    roles = load_roles(args.p1_role_manifest)
    episode_ids = sorted(roles)
    if args.episode_limit is not None:
        episode_ids = episode_ids[: args.episode_limit]
    started = time.time()

    with h5py.File(args.dataset, "r", rdcc_nbytes=512 * 1024 * 1024) as source:
        offsets = np.asarray(source["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(source["ep_len"][:], dtype=np.int64)
        raw_actions = np.asarray(source["action"][:], dtype=np.float32)
    action_processor = fit_finite_action_standardizer(raw_actions)
    primitive_mean = np.asarray(action_processor.mean_, dtype=np.float64)
    primitive_std = np.asarray(action_processor.scale_, dtype=np.float64)
    normalized_actions = action_processor.transform(raw_actions)
    if normalized_actions.dtype != np.float32:
        raise RuntimeError("StandardScaler did not preserve float32 action dtype")

    with h5py.File(args.latent_h5, "r") as latent_handle:
        cache_rows = np.asarray(latent_handle["row_index"][:], dtype=np.int64)
        cache_episodes = np.asarray(latent_handle["episode_idx"][:], dtype=np.int64)
        cache_steps = np.asarray(latent_handle["step_idx"][:], dtype=np.int64)
        latents = np.asarray(latent_handle["latent"][:], dtype=np.float32)
    if not np.all(cache_rows[1:] > cache_rows[:-1]):
        raise RuntimeError("latent cache row indices are not strictly increasing")
    if len(cache_rows) != len(latents):
        raise RuntimeError("latent cache arrays have inconsistent lengths")

    source_indices: list[np.ndarray] = []
    target_indices: list[np.ndarray] = []
    block_actions: list[np.ndarray] = []
    role_codes: list[np.ndarray] = []
    pair_episodes: list[np.ndarray] = []
    pair_steps: list[np.ndarray] = []
    for episode in episode_ids:
        length = int(lengths[episode])
        count = length - args.frameskip
        if count <= 0:
            continue
        global_start = int(offsets[episode])
        current_rows = global_start + np.arange(count, dtype=np.int64)
        next_rows = current_rows + args.frameskip
        current_cache = np.searchsorted(cache_rows, current_rows)
        next_cache = np.searchsorted(cache_rows, next_rows)
        if (
            np.any(current_cache >= len(cache_rows))
            or np.any(next_cache >= len(cache_rows))
            or not np.array_equal(cache_rows[current_cache], current_rows)
            or not np.array_equal(cache_rows[next_cache], next_rows)
        ):
            raise RuntimeError(f"episode {episode} is incomplete in the latent cache")
        actions = np.stack(
            [
                normalized_actions[row : row + args.frameskip].reshape(-1)
                for row in current_rows
            ],
            axis=0,
        ).astype(np.float32, copy=False)
        if not np.isfinite(actions).all():
            raise RuntimeError(
                f"episode {episode} contains a non-finite action inside a valid transition"
            )
        source_indices.append(current_cache.astype(np.int64))
        target_indices.append(next_cache.astype(np.int64))
        block_actions.append(actions)
        role_codes.append(np.full(count, roles[episode], dtype=np.uint8))
        pair_episodes.append(np.full(count, episode, dtype=np.int64))
        pair_steps.append(cache_steps[current_cache].astype(np.int64, copy=False))

    source_index = np.concatenate(source_indices)
    target_index = np.concatenate(target_indices)
    actions = np.concatenate(block_actions)
    role = np.concatenate(role_codes)
    pair_episode = np.concatenate(pair_episodes)
    pair_step = np.concatenate(pair_steps)
    if not (
        len(source_index)
        == len(target_index)
        == len(actions)
        == len(role)
        == len(pair_episode)
        == len(pair_step)
    ):
        raise RuntimeError("transition arrays have inconsistent lengths")
    if np.any(cache_episodes[source_index] != pair_episode):
        raise RuntimeError("source transitions cross episode boundaries")
    if np.any(cache_episodes[target_index] != pair_episode):
        raise RuntimeError("target transitions cross episode boundaries")
    if np.any(cache_steps[target_index] - cache_steps[source_index] != args.frameskip):
        raise RuntimeError("transition gap does not equal frameskip")

    train = role == ROLE_CODE["P1_train"]
    validation = role == ROLE_CODE["P1_val"]
    if not train.any() or not validation.any():
        raise RuntimeError("both train and validation transitions are required")
    train_latent_indices = np.unique(
        np.concatenate((source_index[train], target_index[train]))
    )
    training_latents = latents[train_latent_indices].astype(np.float64)
    latent_mean = training_latents.mean(axis=0).astype(np.float32)
    latent_std = training_latents.std(axis=0).astype(np.float32)
    scorer_action_mean = (
        actions[train].mean(axis=0, dtype=np.float64).astype(np.float32)
    )
    scorer_action_std = actions[train].std(axis=0, dtype=np.float64).astype(np.float32)
    if np.any(latent_std < 1.0e-6) or np.any(scorer_action_std < 1.0e-6):
        raise RuntimeError("training standardization contains a near-zero dimension")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as target:
            chunk = min(65_536, len(source_index))
            target.create_dataset(
                "source_index", data=source_index, chunks=(chunk,), compression="lzf"
            )
            target.create_dataset(
                "target_index", data=target_index, chunks=(chunk,), compression="lzf"
            )
            target.create_dataset(
                "episode_idx", data=pair_episode, chunks=(chunk,), compression="lzf"
            )
            target.create_dataset(
                "step_idx", data=pair_step, chunks=(chunk,), compression="lzf"
            )
            target.create_dataset("role", data=role, chunks=(chunk,), compression="lzf")
            target.create_dataset(
                "action",
                data=actions,
                chunks=(min(8192, len(actions)), actions.shape[1]),
                compression="lzf",
            )
            stats = target.create_group("stats")
            stats.create_dataset("latent_mean", data=latent_mean)
            stats.create_dataset("latent_std", data=latent_std)
            stats.create_dataset("planner_primitive_action_mean", data=primitive_mean)
            stats.create_dataset("planner_primitive_action_std", data=primitive_std)
            stats.create_dataset("acid_action_mean", data=scorer_action_mean)
            stats.create_dataset("acid_action_std", data=scorer_action_std)
            target.attrs["frameskip"] = args.frameskip
            target.attrs["latent_h5_sha256"] = sha256_file(args.latent_h5)
            target.attrs["dataset_sha256"] = sha256_file(args.dataset)
            target.attrs["p1_role_manifest_sha256"] = sha256_file(args.p1_role_manifest)
        os.replace(partial, args.output_h5)
    except BaseException:
        if partial.exists():
            partial.unlink()
        raise

    manifest = {
        "status": "ok",
        "kind": "flat_one_model_step_transition_cache",
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "p1_role_manifest": str(args.p1_role_manifest),
        "p1_role_manifest_sha256": sha256_file(args.p1_role_manifest),
        "source_manifest": str(args.source_manifest) if args.source_manifest else None,
        "source_manifest_sha256": (
            sha256_file(args.source_manifest) if args.source_manifest else None
        ),
        "frameskip": args.frameskip,
        "episodes": len(episode_ids),
        "episode_limit": args.episode_limit,
        "pairs": len(source_index),
        "train_pairs": int(train.sum()),
        "validation_pairs": int(validation.sum()),
        "latent_dim": int(latents.shape[1]),
        "primitive_action_dim": int(raw_actions.shape[1]),
        "action_block_dim": int(actions.shape[1]),
        "standardization": {
            "planner_action": "released StandardScaler fitted to source HDF5 action rows without NaNs",
            "latent": "population statistics over unique P1_train latent rows used by transitions",
            "acid_action": "population statistics over P1_train planner-coordinate action blocks",
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_write_json(args.output_json, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
