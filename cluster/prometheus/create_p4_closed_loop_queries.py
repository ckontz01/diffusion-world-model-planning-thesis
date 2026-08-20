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


ROOT_SEED = 20260728
PARTITION = "P4"
QUERY_COUNT = 40
GOAL_OFFSET = 75
LATENT_DIM = 192
HASH_NAMESPACE = "p4_closed_loop"
P4_LATENT_H5_SHA256 = "b8e9ab39497fa64b9f489e36a2dfc1462f8e77f455eaf8d7069750aadd83ffc7"
PARTITION_MANIFEST_SHA256 = "35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0"
CHECKPOINT_SHA256 = "b87805747d40037841877ce7b99b7dda3ebe7a52202c0ba46bf0006ab5d6f008"


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
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


def hash_u64(payload: str) -> int:
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


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
            raise RuntimeError(f"checksum path escapes input directory: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid input: {path}")
        found[str(resolved.relative_to(root))] = digest
    return found


def read_partition_manifest(path: Path) -> dict[int, int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    declared = {
        int(row["episode_id"]): int(row["episode_length"])
        for row in rows
        if row["partition"] == PARTITION
    }
    if len(declared) != 1785:
        raise RuntimeError(f"unexpected P4 episode count: {len(declared)}")
    return declared


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-dir", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite frozen P4 query artifact")
    started = time.time()
    inventory = verify_inventory(args.latent_dir)
    expected_inventory = {"latents.h5", "manifest.json", "provenance.txt"}
    if set(inventory) != expected_inventory:
        raise RuntimeError(f"unexpected P4 latent inventory: {sorted(inventory)}")
    if inventory["latents.h5"] != P4_LATENT_H5_SHA256:
        raise RuntimeError("P4 latent cache differs from the pre-execution lock")
    if sha256_file(args.partition_manifest) != PARTITION_MANIFEST_SHA256:
        raise RuntimeError("episode partition manifest differs from the frozen split")

    latent_manifest_path = args.latent_dir / "manifest.json"
    latent_manifest = json.loads(latent_manifest_path.read_text(encoding="utf-8"))
    if (
        latent_manifest.get("status") != "ok"
        or latent_manifest.get("classification") != "frozen_encoder_latent_cache"
        or latent_manifest.get("partitions") != [PARTITION]
        or latent_manifest.get("output_h5_sha256") != P4_LATENT_H5_SHA256
        or latent_manifest.get("partition_manifest_sha256") != PARTITION_MANIFEST_SHA256
        or latent_manifest.get("checkpoint_sha256") != CHECKPOINT_SHA256
        or int(latent_manifest.get("latent_dim")) != LATENT_DIM
    ):
        raise RuntimeError("P4 latent-cache manifest differs from the frozen inputs")

    declared = read_partition_manifest(args.partition_manifest)
    latent_h5 = args.latent_dir / "latents.h5"
    with h5py.File(latent_h5, "r") as handle:
        if (
            handle.attrs.get("checkpoint_sha256") != CHECKPOINT_SHA256
            or handle.attrs.get("partition_manifest_sha256")
            != PARTITION_MANIFEST_SHA256
        ):
            raise RuntimeError("P4 latent HDF5 lineage changed")
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        cache_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        cache_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        latent = np.asarray(handle["latent"][:], dtype=np.float32)
    if (
        cache_rows.shape != (223465,)
        or cache_episode.shape != cache_rows.shape
        or cache_step.shape != cache_rows.shape
        or latent.shape != (len(cache_rows), LATENT_DIM)
        or np.any(np.diff(cache_rows) <= 0)
        or not np.isfinite(latent).all()
    ):
        raise RuntimeError("unexpected P4 latent-cache geometry")
    if set(int(value) for value in np.unique(cache_episode)) != set(declared):
        raise RuntimeError("P4 cache episode set differs from the partition manifest")

    eligible_episodes = {
        episode_id: length
        for episode_id, length in declared.items()
        if length > GOAL_OFFSET
    }
    if len(eligible_episodes) < QUERY_COUNT:
        raise RuntimeError("not enough D75-eligible P4 episodes")
    ordered_episodes = sorted(
        eligible_episodes,
        key=lambda episode_id: hash_u64(
            f"pusht_expert_train\0{ROOT_SEED}\0{HASH_NAMESPACE}_pool_episode\0{episode_id}"
        ),
    )

    queries: list[dict[str, int]] = []
    z_init = np.empty((QUERY_COUNT, LATENT_DIM), dtype=np.float32)
    z_goal = np.empty_like(z_init)
    for query_id, episode_id in enumerate(ordered_episodes[:QUERY_COUNT]):
        episode_mask = cache_episode == episode_id
        episode_rows = cache_rows[episode_mask]
        episode_steps = cache_step[episode_mask]
        if len(episode_rows) != declared[episode_id]:
            raise RuntimeError(f"episode length mismatch: {episode_id}")
        eligible_rows = episode_rows[
            episode_steps + GOAL_OFFSET < declared[episode_id]
        ]
        offset_hash = hash_u64(
            f"pusht_expert_train\0{ROOT_SEED}\0{HASH_NAMESPACE}_pool_start\0{episode_id}"
        )
        source_row = int(eligible_rows[offset_hash % len(eligible_rows)])
        goal_row = source_row + GOAL_OFFSET
        source_position = int(np.searchsorted(cache_rows, source_row))
        goal_position = int(np.searchsorted(cache_rows, goal_row))
        if (
            source_position >= len(cache_rows)
            or goal_position >= len(cache_rows)
            or cache_rows[source_position] != source_row
            or cache_rows[goal_position] != goal_row
            or cache_episode[source_position] != episode_id
            or cache_episode[goal_position] != episode_id
            or cache_step[goal_position] - cache_step[source_position] != GOAL_OFFSET
        ):
            raise RuntimeError(f"invalid D75 row mapping: episode {episode_id}")
        planner_seed = hash_u64(
            f"pusht_expert_train\0{ROOT_SEED}\0{HASH_NAMESPACE}_cem\0{query_id}\0{episode_id}\0{source_row}"
        ) & ((1 << 63) - 1)
        queries.append(
            {
                "query_id": query_id,
                "episode_id": episode_id,
                "source_global_row": source_row,
                "goal_global_row": goal_row,
                "source_step": int(cache_step[source_position]),
                "goal_step": int(cache_step[goal_position]),
                "planner_seed": planner_seed,
            }
        )
        z_init[query_id] = latent[source_position]
        z_goal[query_id] = latent[goal_position]
    if len({record["episode_id"] for record in queries}) != QUERY_COUNT:
        raise RuntimeError("P4 queries are not episode-distinct")
    if len({record["planner_seed"] for record in queries}) != QUERY_COUNT:
        raise RuntimeError("P4 planner seeds are not unique")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "p4_closed_loop_d75_queries"
            output.attrs["partition"] = PARTITION
            output.attrs["root_seed"] = ROOT_SEED
            output.attrs["hash_namespace"] = HASH_NAMESPACE
            output.attrs["query_count"] = QUERY_COUNT
            output.attrs["goal_offset"] = GOAL_OFFSET
            output.attrs["latent_h5_sha256"] = P4_LATENT_H5_SHA256
            output.attrs["checkpoint_sha256"] = CHECKPOINT_SHA256
            for key in (
                "query_id",
                "episode_id",
                "source_global_row",
                "goal_global_row",
                "source_step",
                "goal_step",
                "planner_seed",
            ):
                output.create_dataset(
                    key, data=np.asarray([record[key] for record in queries], dtype=np.int64)
                )
            output.create_dataset("z_init", data=z_init, compression="gzip")
            output.create_dataset("z_goal", data=z_goal, compression="gzip")
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_p4_query_artifact_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": "p4_closed_loop_d75_queries",
        "partition": PARTITION,
        "reporting_rule": "outcome-blind locked P4 query and seed artifact",
        "root_seed": ROOT_SEED,
        "hash_namespace": HASH_NAMESPACE,
        "query_count": QUERY_COUNT,
        "goal_offset": GOAL_OFFSET,
        "query_selection": {
            "episode_order": "ascending domain-separated SHA-256",
            "within_episode_start": "domain-separated SHA-256 modulo all D75-valid starts",
            "planner_seed": "low 63 bits of a separate domain-separated SHA-256",
            "episode_distinct": True,
        },
        "queries": queries,
        "inputs": {
            "latent_h5": str(latent_h5),
            "latent_h5_sha256": P4_LATENT_H5_SHA256,
            "latent_manifest_sha256": sha256_file(latent_manifest_path),
            "partition_manifest": str(args.partition_manifest),
            "partition_manifest_sha256": PARTITION_MANIFEST_SHA256,
            "checkpoint_sha256": CHECKPOINT_SHA256,
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
