#!/usr/bin/env python3
"""Build frozen TRM pair/label caches from disjoint P1 episode roles."""

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

ROLE_CODE = {"P1_train": 0, "P1_val": 1}


def load_roles(path: Path) -> dict[str, list[int]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "p1_role"}.issubset(rows[0]):
        raise ValueError("invalid P1 role manifest")
    result = {name: [] for name in ROLE_CODE}
    seen: set[int] = set()
    for row in rows:
        episode = int(row["episode_id"])
        role = row["p1_role"]
        if role not in result:
            raise ValueError(f"unexpected P1 role {role}")
        if episode in seen:
            raise ValueError(f"duplicate episode {episode}")
        seen.add(episode)
        result[role].append(episode)
    if any(not episodes for episodes in result.values()):
        raise ValueError("both P1 roles require episodes")
    return result


def sample_unique_pairs(
    episodes: list[int],
    offsets: np.ndarray,
    lengths: np.ndarray,
    *,
    count: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sample episode-uniform, separation-uniform unique same-episode pairs."""

    eligible = np.asarray([episode for episode in episodes if lengths[episode] >= 2])
    if len(eligible) == 0:
        raise RuntimeError("role has no episode with at least two rows")
    possible = int(sum(int(lengths[e]) * (int(lengths[e]) - 1) // 2 for e in eligible))
    if count > possible:
        raise ValueError(f"requested {count} unique pairs but only {possible} exist")

    selected: set[tuple[int, int, int]] = set()
    episode_out = np.empty(count, dtype=np.int64)
    first_row = np.empty(count, dtype=np.int64)
    second_row = np.empty(count, dtype=np.int64)
    delta_out = np.empty(count, dtype=np.int32)
    swapped = np.empty(count, dtype=np.bool_)
    index = 0
    while index < count:
        episode = int(eligible[int(rng.integers(0, len(eligible)))])
        length = int(lengths[episode])
        delta = int(rng.integers(1, length))
        start = int(rng.integers(0, length - delta))
        key = (episode, start, delta)
        if key in selected:
            continue
        selected.add(key)
        source = int(offsets[episode]) + start
        target = source + delta
        swap = bool(rng.integers(0, 2))
        episode_out[index] = episode
        first_row[index] = target if swap else source
        second_row[index] = source if swap else target
        delta_out[index] = delta
        swapped[index] = swap
        index += 1
    return episode_out, first_row, second_row, delta_out, swapped


def map_global_rows(cache_rows: np.ndarray, requested: np.ndarray) -> np.ndarray:
    positions = np.searchsorted(cache_rows, requested)
    if np.any(positions >= len(cache_rows)):
        raise RuntimeError("requested row lies outside the latent cache")
    if not np.array_equal(cache_rows[positions], requested):
        raise RuntimeError("requested row is absent from the latent cache")
    return positions.astype(np.int64, copy=False)


def wrapped_angle_difference(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    difference = first - second
    return np.arctan2(np.sin(difference), np.cos(difference))


def pusht_task_state_distance(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """Euclidean norm over agent XY, object XY, and wrapped object angle."""

    if first.shape != second.shape or first.ndim != 2 or first.shape[1] < 5:
        raise ValueError("PushT state arrays must have at least five columns")
    position = first[:, :4] - second[:, :4]
    angle = wrapped_angle_difference(first[:, 4], second[:, 4])
    return np.sqrt(np.square(position).sum(axis=1) + np.square(angle)).astype(
        np.float32
    )


def read_selected_states(
    state_dataset: h5py.Dataset, first_rows: np.ndarray, second_rows: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    combined = np.concatenate((first_rows, second_rows))
    unique, inverse = np.unique(combined, return_inverse=True)
    values = np.asarray(state_dataset[unique], dtype=np.float32)
    if not np.isfinite(values).all():
        raise RuntimeError("selected task states contain non-finite values")
    split = len(first_rows)
    return values[inverse[:split]], values[inverse[split:]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--p1-role-manifest", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument(
        "--target", choices=("pusht_task_state", "temporal"), required=True
    )
    parser.add_argument("--train-pairs", type=int, default=100_000)
    parser.add_argument("--validation-pairs", type=int, default=10_000)
    parser.add_argument("--seed", type=int, required=True)
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
    if min(args.train_pairs, args.validation_pairs) <= 0:
        raise ValueError("pair counts must be positive")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing output")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok":
        raise RuntimeError("latent manifest is not complete")
    latent_hash = sha256_file(args.latent_h5)
    if latent_hash != latent_manifest.get("output_h5_sha256"):
        raise RuntimeError("latent cache hash mismatch")
    roles = load_roles(args.p1_role_manifest)
    started = time.time()

    with h5py.File(args.dataset, "r", rdcc_nbytes=256 * 1024 * 1024) as dataset:
        offsets = np.asarray(dataset["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(dataset["ep_len"][:], dtype=np.int64)
        if max(max(items) for items in roles.values()) >= len(lengths):
            raise RuntimeError("role manifest refers to an unknown episode")
        train = sample_unique_pairs(
            roles["P1_train"],
            offsets,
            lengths,
            count=args.train_pairs,
            rng=np.random.Generator(np.random.PCG64(args.seed ^ 0x54524D01)),
        )
        validation = sample_unique_pairs(
            roles["P1_val"],
            offsets,
            lengths,
            count=args.validation_pairs,
            rng=np.random.Generator(np.random.PCG64(args.seed ^ 0x54524D02)),
        )
        episode = np.concatenate((train[0], validation[0]))
        first_row = np.concatenate((train[1], validation[1]))
        second_row = np.concatenate((train[2], validation[2]))
        delta = np.concatenate((train[3], validation[3]))
        swapped = np.concatenate((train[4], validation[4]))
        if args.target == "pusht_task_state":
            if "state" not in dataset:
                raise RuntimeError("PushT task-state target requires dataset/state")
            first_state, second_state = read_selected_states(
                dataset["state"], first_row, second_row
            )
            label = pusht_task_state_distance(first_state, second_state)
            label_formula = (
                "sqrt(sum((agent_xy_i-agent_xy_j)^2) + "
                "sum((object_xy_i-object_xy_j)^2) + "
                "wrap(object_angle_i-object_angle_j)^2)"
            )
            target_scale = 224.0
            target_scale_rule = "fixed published PushT image-coordinate scale"
        else:
            label = delta.astype(np.float32)
            label_formula = "absolute within-episode primitive-step separation"
            target_scale = float(
                max(int(lengths[episode]) - 1 for episode in roles["P1_train"])
            )
            target_scale_rule = (
                "maximum available within-episode separation in P1_train"
            )

    with h5py.File(args.latent_h5, "r") as latent_handle:
        cache_rows = np.asarray(latent_handle["row_index"][:], dtype=np.int64)
        latent_dim = int(latent_handle["latent"].shape[1])
    if not np.all(cache_rows[1:] > cache_rows[:-1]):
        raise RuntimeError("latent row index is not strictly increasing")
    first_index = map_global_rows(cache_rows, first_row)
    second_index = map_global_rows(cache_rows, second_row)
    role = np.concatenate(
        (
            np.full(args.train_pairs, ROLE_CODE["P1_train"], dtype=np.uint8),
            np.full(args.validation_pairs, ROLE_CODE["P1_val"], dtype=np.uint8),
        )
    )
    if not np.isfinite(label).all() or np.any(label < 0):
        raise RuntimeError("invalid reachability labels")
    if set(episode[: args.train_pairs]) & set(episode[args.train_pairs :]):
        raise RuntimeError("train and validation pair episodes overlap")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as output:
            arrays = {
                "episode_idx": episode,
                "first_row": first_row,
                "second_row": second_row,
                "first_index": first_index,
                "second_index": second_index,
                "delta": delta,
                "swapped": swapped,
                "role": role,
                "label": label,
            }
            for name, values in arrays.items():
                output.create_dataset(
                    name,
                    data=values,
                    chunks=(min(65_536, len(values)),),
                    compression="lzf",
                )
            output.attrs["target"] = args.target
            output.attrs["target_formula"] = label_formula
            output.attrs["target_scale"] = target_scale
            output.attrs["target_scale_rule"] = target_scale_rule
            output.attrs["seed"] = args.seed
            output.attrs["latent_h5_sha256"] = latent_hash
            output.attrs["dataset_sha256"] = sha256_file(args.dataset)
            output.attrs["p1_role_manifest_sha256"] = sha256_file(args.p1_role_manifest)
        os.replace(partial, args.output_h5)
    except BaseException:
        if partial.exists():
            partial.unlink()
        raise

    manifest = {
        "status": "ok",
        "kind": "trm_reachability_pair_cache",
        "target": args.target,
        "target_formula": label_formula,
        "target_scale": target_scale,
        "target_scale_rule": target_scale_rule,
        "sampling": (
            "unique pairs; episode uniform, then delta uniform over [1,L-1], "
            "then valid start uniform; input order Bernoulli(0.5)"
        ),
        "seed": args.seed,
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": latent_hash,
        "latent_manifest": str(args.latent_manifest),
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "p1_role_manifest": str(args.p1_role_manifest),
        "p1_role_manifest_sha256": sha256_file(args.p1_role_manifest),
        "source_manifest": str(args.source_manifest) if args.source_manifest else None,
        "source_manifest_sha256": (
            sha256_file(args.source_manifest) if args.source_manifest else None
        ),
        "latent_dim": latent_dim,
        "train_pairs": args.train_pairs,
        "validation_pairs": args.validation_pairs,
        "train_episodes": len(set(episode[: args.train_pairs].tolist())),
        "validation_episodes": len(set(episode[args.train_pairs :].tolist())),
        "swapped": int(swapped.sum()),
        "label": {
            "minimum": float(label.min()),
            "maximum": float(label.max()),
            "mean": float(label.mean()),
            "standard_deviation": float(label.std()),
            "scale_for_training": target_scale,
            "scale_rule": target_scale_rule,
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
