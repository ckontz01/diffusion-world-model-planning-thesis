#!/usr/bin/env python3

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


STRATA = ("same_trajectory_delta25", "cross_trajectory")


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def hash_u64(payload: str) -> int:
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise RuntimeError(f"empty partition manifest: {path}")
    return rows


def safe_h5_rows(dataset: h5py.Dataset, rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.int64)
    order = np.argsort(rows, kind="mergesort")
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    return np.asarray(dataset[rows[order]])[inverse]


def map_global_rows(cache_rows: np.ndarray, requested: np.ndarray) -> np.ndarray:
    positions = np.searchsorted(cache_rows, requested)
    if np.any(positions >= len(cache_rows)):
        raise RuntimeError("requested row lies outside the partition latent cache")
    if not np.array_equal(cache_rows[positions], requested):
        raise RuntimeError("requested row is absent from the partition latent cache")
    return positions.astype(np.int64, copy=False)


def angular_error(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    difference = np.abs(first - second) % (2.0 * np.pi)
    return np.minimum(difference, 2.0 * np.pi - difference)


def source_assignments(
    episode_ids: list[int],
    episodes: dict[int, dict[str, int]],
    count: int,
    delta: int,
) -> list[tuple[int, int]]:
    """Assign adjacent, unique within-episode source occurrences deterministically."""
    if len(episode_ids) > count:
        episode_ids = episode_ids[:count]
    assignments: list[tuple[int, int]] = []
    base_repeats, extra = divmod(count, len(episode_ids))
    for index, episode_id in enumerate(episode_ids):
        repeat_count = base_repeats + (1 if index < extra else 0)
        valid_source_count = episodes[episode_id]["episode_length"] - delta
        if repeat_count > valid_source_count:
            raise RuntimeError(
                f"episode {episode_id} has {valid_source_count} unique D{delta} "
                f"source rows but needs {repeat_count}"
            )
        assignments.extend((episode_id, occurrence) for occurrence in range(repeat_count))
    if len(assignments) != count:
        raise RuntimeError("source assignment count mismatch")
    return assignments


def unique_hashed_step(payload: str, count: int, used: set[int]) -> int:
    if len(used) >= count:
        raise RuntimeError("no unused step remains in an episode")
    step = hash_u64(payload) % count
    while step in used:
        step = (step + 1) % count
    used.add(step)
    return step


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--partition", choices=("P2", "P3"), default="P2")
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--pools-per-stratum", type=int, default=12)
    parser.add_argument("--candidates-per-pool", type=int, default=64)
    parser.add_argument("--delta", type=int, default=25)
    args = parser.parse_args()

    partition = args.partition
    partition_key = partition.lower()
    environment = args.environment
    dataset_namespace = "pusht_expert_train" if environment == "pusht" else "tworoom"
    classification = (
        f"{partition_key}_real_frame_candidate_pools"
        if environment == "pusht"
        else f"tworoom_{partition_key}_real_frame_candidate_pools"
    )
    expected_pools = 12 if partition == "P2" else 24

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit(f"refusing to overwrite {partition} real-frame candidate pools")
    if (
        args.pools_per_stratum,
        args.candidates_per_pool,
        args.delta,
    ) != (expected_pools, 64, 25):
        raise SystemExit(
            f"{partition} real-frame pool sizes and Delta are frozen at "
            f"{expected_pools}/64/25"
        )
    started = time.time()

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok" or latent_manifest.get("partitions") != [
        partition
    ]:
        raise RuntimeError(f"latent input is not a completed {partition} cache")
    partition_sha = sha256_file(args.partition_manifest)
    if partition_sha != latent_manifest["partition_manifest_sha256"]:
        raise RuntimeError(f"{partition} latent cache and partition manifest differ")
    if sha256_file(args.latent_h5) != latent_manifest["output_h5_sha256"]:
        raise RuntimeError(f"{partition} latent HDF5 does not match its manifest")

    partition_rows = read_tsv(args.partition_manifest)
    ordered_partition_rows = sorted(
        partition_rows, key=lambda row: int(row["episode_id"])
    )
    episode_offsets: dict[int, int] = {}
    running_offset = 0
    for expected_episode_id, row in enumerate(ordered_partition_rows):
        episode_id = int(row["episode_id"])
        if episode_id != expected_episode_id:
            raise RuntimeError("episode IDs are not contiguous from zero")
        episode_offsets[episode_id] = running_offset
        running_offset += int(row["episode_length"])
    episodes = {
        int(row["episode_id"]): {
            "episode_id": int(row["episode_id"]),
            "global_offset": episode_offsets[int(row["episode_id"])],
            "episode_length": int(row["episode_length"]),
        }
        for row in partition_rows
        if row["partition"] == partition and int(row["episode_length"]) > args.delta
    }
    per_stratum = args.pools_per_stratum * args.candidates_per_pool
    ordered_episode_ids = sorted(
        episodes,
        key=lambda episode_id: hash_u64(
            f"{dataset_namespace}\0{args.seed}\0{partition_key}_real_source_episode\0{episode_id}"
        ),
    )
    if partition == "P2":
        if len(episodes) >= 2 * per_stratum:
            stratum_unique_episode_ids = (
                ordered_episode_ids[:per_stratum],
                ordered_episode_ids[per_stratum : 2 * per_stratum],
            )
        elif environment == "tworoom":
            if len(episodes) != 1042:
                raise RuntimeError(
                    "the frozen TwoRoom P2 capacity adapter requires exactly "
                    f"1,042 D25-eligible episodes; found {len(episodes)}"
                )
            stratum_unique_episode_ids = (
                ordered_episode_ids[0::2],
                ordered_episode_ids[1::2],
            )
            if tuple(map(len, stratum_unique_episode_ids)) != (521, 521):
                raise RuntimeError("TwoRoom P2 disjoint episode split changed")
        else:
            raise RuntimeError(
                f"need {2 * per_stratum} D25-eligible P2 episodes, "
                f"found {len(episodes)}"
            )
    else:
        stratum_unique_episode_ids = (
            ordered_episode_ids[0::2],
            ordered_episode_ids[1::2],
        )
        if not all(stratum_unique_episode_ids):
            raise RuntimeError("P3 cannot be split into two nonempty episode sets")
    if set(stratum_unique_episode_ids[0]) & set(stratum_unique_episode_ids[1]):
        raise RuntimeError("real-frame strata reuse source episodes")

    stratum_assignments = tuple(
        source_assignments(episode_ids, episodes, per_stratum, args.delta)
        for episode_ids in stratum_unique_episode_ids
    )
    stratum_episode_ids = tuple(
        [episode_id for episode_id, _ in assignments]
        for assignments in stratum_assignments
    )

    source_episode = np.empty((2, per_stratum), dtype=np.int64)
    target_episode = np.empty_like(source_episode)
    source_step = np.empty_like(source_episode)
    target_step = np.empty_like(source_episode)
    source_row = np.empty_like(source_episode)
    target_row = np.empty_like(source_episode)

    for stratum_index, assignments in enumerate(stratum_assignments):
        episode_ids = stratum_episode_ids[stratum_index]
        source_episode[stratum_index] = episode_ids
        used_source_steps: dict[int, set[int]] = {}
        for item_index, (episode_id, occurrence) in enumerate(assignments):
            episode = episodes[episode_id]
            valid_source_count = episode["episode_length"] - args.delta
            payload = (
                f"{dataset_namespace}\0{args.seed}\0{partition_key}_real_source_step\0"
                f"{STRATA[stratum_index]}\0{episode_id}"
            )
            if len(stratum_unique_episode_ids[stratum_index]) < per_stratum:
                payload += f"\0{occurrence}"
            step = unique_hashed_step(
                payload,
                valid_source_count,
                used_source_steps.setdefault(episode_id, set()),
            )
            source_step[stratum_index, item_index] = step
            source_row[stratum_index, item_index] = episode["global_offset"] + step

        if stratum_index == 0:
            target_episode[stratum_index] = source_episode[stratum_index]
            target_step[stratum_index] = source_step[stratum_index] + args.delta
            target_row[stratum_index] = source_row[stratum_index] + args.delta
        else:
            target_order = sorted(
                stratum_unique_episode_ids[stratum_index],
                key=lambda episode_id: hash_u64(
                    f"{dataset_namespace}\0{args.seed}\0{partition_key}_real_cross_target_order\0"
                    f"{episode_id}"
                ),
            )
            mapping = {
                episode_id: target_order[(index + 1) % len(target_order)]
                for index, episode_id in enumerate(target_order)
            }
            if any(mapping[episode_id] == episode_id for episode_id in episode_ids):
                raise RuntimeError("cross-trajectory target mapping is not a derangement")
            used_target_steps: dict[int, set[int]] = {}
            for item_index, (episode_id, occurrence) in enumerate(assignments):
                target_id = mapping[episode_id]
                target = episodes[target_id]
                payload = (
                    f"{dataset_namespace}\0{args.seed}\0{partition_key}_real_cross_target_step\0"
                    f"{episode_id}\0{target_id}"
                )
                if len(stratum_unique_episode_ids[stratum_index]) < per_stratum:
                    payload += f"\0{occurrence}"
                step = unique_hashed_step(
                    payload,
                    target["episode_length"],
                    used_target_steps.setdefault(target_id, set()),
                )
                target_episode[stratum_index, item_index] = target_id
                target_step[stratum_index, item_index] = step
                target_row[stratum_index, item_index] = target["global_offset"] + step

    if np.any(source_episode[1] == target_episode[1]):
        raise RuntimeError("cross-trajectory stratum contains a same-episode pair")
    if not np.all(target_row[0] - source_row[0] == args.delta):
        raise RuntimeError("same-trajectory stratum has an incorrect separation")
    if any(len(ids) < per_stratum for ids in stratum_unique_episode_ids):
        for stratum_index in range(2):
            episode_pools: dict[int, set[int]] = {}
            for flat_index, episode_id in enumerate(source_episode[stratum_index]):
                episode_pools.setdefault(int(episode_id), set()).add(
                    flat_index // args.candidates_per_pool
                )
            if any(len(pools) != 1 for pools in episode_pools.values()):
                raise RuntimeError("repeated source episodes cross pool boundaries")

    flat_source = source_row.reshape(-1)
    flat_target = target_row.reshape(-1)
    with h5py.File(args.latent_h5, "r") as latent_handle:
        cache_rows = np.asarray(latent_handle["row_index"][:], dtype=np.int64)
        source_cache = map_global_rows(cache_rows, flat_source)
        target_cache = map_global_rows(cache_rows, flat_target)
        source_latent = safe_h5_rows(latent_handle["latent"], source_cache).astype(
            np.float32, copy=False
        ).reshape(2, per_stratum, -1)
        target_latent = safe_h5_rows(latent_handle["latent"], target_cache).astype(
            np.float32, copy=False
        ).reshape(2, per_stratum, -1)
    if source_latent.shape[-1] != 192 or target_latent.shape != source_latent.shape:
        raise RuntimeError(f"unexpected {partition} latent shape")

    with h5py.File(args.dataset, "r") as dataset:
        if int(dataset["pixels"].shape[0]) != running_offset:
            raise RuntimeError("episode lengths do not sum to the dataset row count")
        episode_key = "episode_idx" if "episode_idx" in dataset else "ep_idx"
        if environment == "pusht":
            state_key = "state"
        else:
            state_key = "pos_agent"
            if "proprio" not in dataset:
                raise RuntimeError("TwoRoom dataset is missing proprio")
        if state_key not in dataset:
            raise RuntimeError(f"dataset is missing physical state key {state_key}")
        source_state = safe_h5_rows(dataset[state_key], flat_source).astype(
            np.float32, copy=False
        ).reshape(2, per_stratum, -1)
        target_state = safe_h5_rows(dataset[state_key], flat_target).astype(
            np.float32, copy=False
        ).reshape(2, per_stratum, -1)
        if environment == "tworoom":
            source_proprio = safe_h5_rows(dataset["proprio"], flat_source).astype(
                np.float32, copy=False
            ).reshape(2, per_stratum, -1)
            target_proprio = safe_h5_rows(dataset["proprio"], flat_target).astype(
                np.float32, copy=False
            ).reshape(2, per_stratum, -1)
            if not np.array_equal(source_state, source_proprio) or not np.array_equal(
                target_state, target_proprio
            ):
                raise RuntimeError("TwoRoom pos_agent and proprio disagree")
        source_episode_check = safe_h5_rows(dataset[episode_key], flat_source).reshape(
            2, per_stratum
        )
        target_episode_check = safe_h5_rows(dataset[episode_key], flat_target).reshape(
            2, per_stratum
        )
        source_step_check = safe_h5_rows(dataset["step_idx"], flat_source).reshape(
            2, per_stratum
        )
        target_step_check = safe_h5_rows(dataset["step_idx"], flat_target).reshape(
            2, per_stratum
        )
    if not np.array_equal(source_episode, source_episode_check) or not np.array_equal(
        target_episode, target_episode_check
    ):
        raise RuntimeError("dataset episode metadata differs from the partition manifest")
    if not np.array_equal(source_step, source_step_check) or not np.array_equal(
        target_step, target_step_check
    ):
        raise RuntimeError("dataset step metadata differs from sampled rows")

    if environment == "pusht":
        initial_block_position_error = np.linalg.norm(
            source_state[:, :, 2:4] - target_state[:, :, 2:4], axis=-1
        ).astype(np.float32)
        initial_agent_block_position_error = np.linalg.norm(
            source_state[:, :, :4] - target_state[:, :, :4], axis=-1
        ).astype(np.float32)
        initial_angle_error = angular_error(
            source_state[:, :, 4], target_state[:, :, 4]
        ).astype(np.float32)
        initial_primary_success = (initial_block_position_error < 20.0) & (
            initial_angle_error < np.pi / 9.0
        )
        initial_agent_included_success = (initial_agent_block_position_error < 20.0) & (
            initial_angle_error < np.pi / 9.0
        )
    else:
        initial_agent_position_error = np.linalg.norm(
            source_state - target_state, axis=-1
        ).astype(np.float32)
        initial_primary_success = initial_agent_position_error < 16.0

    reshape = (2, args.pools_per_stratum, args.candidates_per_pool)
    arrays: dict[str, np.ndarray] = {
        "source_episode_id": source_episode.reshape(reshape),
        "target_episode_id": target_episode.reshape(reshape),
        "source_step": source_step.reshape(reshape),
        "target_step": target_step.reshape(reshape),
        "source_global_row": source_row.reshape(reshape),
        "target_global_row": target_row.reshape(reshape),
        "source_latent": source_latent.reshape(*reshape, 192),
        "target_latent": target_latent.reshape(*reshape, 192),
        "source_state": source_state.reshape(*reshape, source_state.shape[-1]),
        "target_state": target_state.reshape(*reshape, target_state.shape[-1]),
        "initial_primary_success": initial_primary_success.reshape(reshape),
    }
    if environment == "pusht":
        arrays.update(
            {
                "initial_block_position_error": initial_block_position_error.reshape(reshape),
                "initial_agent_block_position_error": initial_agent_block_position_error.reshape(reshape),
                "initial_angle_error": initial_angle_error.reshape(reshape),
                "initial_agent_included_success": initial_agent_included_success.reshape(reshape),
            }
        )
    else:
        arrays["initial_agent_position_error"] = initial_agent_position_error.reshape(reshape)

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = classification
            output.attrs["environment"] = environment
            output.attrs["dataset_namespace"] = dataset_namespace
            output.attrs["partition"] = partition
            output.attrs["seed"] = args.seed
            output.attrs["delta_primitive_steps"] = args.delta
            output.attrs["pools_per_stratum"] = args.pools_per_stratum
            output.attrs["candidates_per_pool"] = args.candidates_per_pool
            output.create_dataset("stratum_name", data=np.asarray(STRATA, dtype="S32"))
            output.create_dataset(
                "pool_id",
                data=np.broadcast_to(
                    np.arange(args.pools_per_stratum, dtype=np.int64)[None, :],
                    (2, args.pools_per_stratum),
                ),
            )
            output.create_dataset(
                "candidate_slot",
                data=np.broadcast_to(
                    np.arange(args.candidates_per_pool, dtype=np.int64)[None, None, :],
                    reshape,
                ),
            )
            for key, value in arrays.items():
                compression = "gzip" if value.ndim == 4 else None
                output.create_dataset(key, data=value, compression=compression)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_real_frame_pool_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": classification,
        "environment": environment,
        "dataset_namespace": dataset_namespace,
        "partition": partition,
        "seed": args.seed,
        "strata": list(STRATA),
        "pools_per_stratum": args.pools_per_stratum,
        "candidates_per_pool": args.candidates_per_pool,
        "candidates_per_stratum": per_stratum,
        "delta_primitive_steps": args.delta,
        "sampling": {
            "source_episode_rule": (
                "domain-separated SHA-256 order; one source per episode; source sets disjoint across strata"
                if partition == "P2" and environment == "pusht"
                else "domain-separated SHA-256 order; alternating disjoint stratum split; all 521 episodes per stratum; first 247 have two adjacent unique source rows and remaining 274 have one"
                if partition == "P2" and environment == "tworoom"
                else "domain-separated SHA-256 order; alternating disjoint stratum split; repeated rows stay adjacent and unique within episode"
            ),
            "source_step_rule": "domain-separated SHA-256 modulo the within-episode D25-valid source count",
            "same_trajectory_target_rule": "source row plus exactly 25 primitive steps",
            "cross_trajectory_target_rule": "domain-separated SHA-256 episode order with a one-position cyclic derangement; hashed target step",
            "source_episode_ids_sha256": [
                sha256_array(source_episode[index]) for index in range(2)
            ],
            "target_episode_ids_sha256": [
                sha256_array(target_episode[index]) for index in range(2)
            ],
            "source_rows_sha256": [sha256_array(source_row[index]) for index in range(2)],
            "target_rows_sha256": [sha256_array(target_row[index]) for index in range(2)],
            "unique_source_episode_counts": [
                len(set(source_episode[index].tolist())) for index in range(2)
            ],
            "maximum_source_rows_per_episode": [
                max(
                    np.unique(source_episode[index], return_counts=True)[1]
                ).item()
                for index in range(2)
            ],
        },
        "initial_state_diagnostics_not_labels": (
            {
                STRATA[index]: {
                    "primary_block_position_and_angle_success_rate": float(initial_primary_success[index].mean()),
                    "agent_included_benchmark_success_rate": float(initial_agent_included_success[index].mean()),
                    "block_position_error_median": float(np.median(initial_block_position_error[index])),
                    "angle_error_median": float(np.median(initial_angle_error[index])),
                }
                for index in range(2)
            }
            if environment == "pusht"
            else {
                STRATA[index]: {
                    "primary_agent_position_success_rate": float(initial_primary_success[index].mean()),
                    "agent_position_error_median": float(np.median(initial_agent_position_error[index])),
                }
                for index in range(2)
            }
        ),
        "physical_criterion": (
            {
                "primary": "block position L2 < 20 pixels and wrapped block angle error < pi/9",
                "sensitivity": "released stable_worldmodel 0.0.6 eval_state: joint agent+block position L2 < 20 and wrapped block angle error < pi/9",
            }
            if environment == "pusht"
            else {
                "primary": "minimum agent-position L2 over the execution trace < 16 pixels",
                "source": "stable_worldmodel 0.0.6 TwoRoom termination condition",
            }
        ),
        "inputs": {
            "partition_manifest": str(args.partition_manifest),
            "partition_manifest_sha256": partition_sha,
            "latent_h5": str(args.latent_h5),
            "latent_h5_sha256": latent_manifest["output_h5_sha256"],
            "latent_manifest_sha256": sha256_file(args.latent_manifest),
            "dataset": str(args.dataset),
            "dataset_bytes": args.dataset.stat().st_size,
            "episode_dataset": episode_key,
            "physical_state_dataset": state_key,
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
