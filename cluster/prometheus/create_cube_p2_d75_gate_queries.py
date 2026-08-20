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
DATASET_NAME = "cube_single_expert"
PARTITION = "P2"
QUERY_COUNT = 12
GOAL_OFFSET = 75
HASH_NAMESPACE = "cube_p2_d75_environment_gate"
DATASET_BYTES = 101_942_558_720
DATASET_SHA256 = "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625"
PARTITION_MANIFEST_SHA256 = "39b59b7162d8cf932b5cab82a7f1a4b9f2e80be3fb5401b94d8e14335d91e2c3"


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


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


def read_p2_episodes(path: Path) -> dict[int, int]:
    if sha256_file(path) != PARTITION_MANIFEST_SHA256:
        raise RuntimeError("Cube partition manifest differs from A-039")
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    selected = {
        int(row["episode_id"]): int(row["episode_length"])
        for row in rows
        if row["partition"] == PARTITION
    }
    if len(selected) != 957 or any(length != 201 for length in selected.values()):
        raise RuntimeError("unexpected Cube P2 episode geometry")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite frozen Cube P2 gate queries")
    if args.dataset.stat().st_size != DATASET_BYTES:
        raise RuntimeError("Cube dataset byte size differs from the staged artifact")
    started = time.time()
    p2_episodes = read_p2_episodes(args.partition_manifest)
    eligible = {
        episode_id: length
        for episode_id, length in p2_episodes.items()
        if length > GOAL_OFFSET
    }
    ordered = sorted(
        eligible,
        key=lambda episode_id: hash_u64(
            f"{DATASET_NAME}\0{ROOT_SEED}\0{HASH_NAMESPACE}_episode\0{episode_id}"
        ),
    )
    chosen = ordered[:QUERY_COUNT]
    if len(chosen) != QUERY_COUNT:
        raise RuntimeError("insufficient D75-eligible Cube P2 episodes")

    queries: list[dict[str, int]] = []
    with h5py.File(args.dataset, "r") as handle:
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
        if offsets.shape != (10_000,) or lengths.shape != (10_000,):
            raise RuntimeError("Cube offset/length geometry changed")
        for query_id, episode_id in enumerate(chosen):
            length = int(lengths[episode_id])
            if length != eligible[episode_id]:
                raise RuntimeError("Cube HDF5/partition episode length mismatch")
            valid_start_count = length - GOAL_OFFSET
            start_hash = hash_u64(
                f"{DATASET_NAME}\0{ROOT_SEED}\0{HASH_NAMESPACE}_start\0{episode_id}"
            )
            source_step = int(start_hash % valid_start_count)
            goal_step = source_step + GOAL_OFFSET
            source_row = int(offsets[episode_id]) + source_step
            goal_row = source_row + GOAL_OFFSET
            if (
                int(handle["ep_idx"][source_row]) != episode_id
                or int(handle["ep_idx"][goal_row]) != episode_id
                or int(handle["step_idx"][source_row]) != source_step
                or int(handle["step_idx"][goal_row]) != goal_step
            ):
                raise RuntimeError("invalid Cube source/goal row mapping")
            planner_seed = hash_u64(
                f"{DATASET_NAME}\0{ROOT_SEED}\0{HASH_NAMESPACE}_cem\0{query_id}\0{episode_id}\0{source_row}"
            ) & ((1 << 63) - 1)
            queries.append(
                {
                    "query_id": query_id,
                    "episode_id": episode_id,
                    "source_global_row": source_row,
                    "goal_global_row": goal_row,
                    "source_step": source_step,
                    "goal_step": goal_step,
                    "planner_seed": planner_seed,
                }
            )
    if len({record["episode_id"] for record in queries}) != QUERY_COUNT:
        raise RuntimeError("Cube gate queries are not episode-distinct")
    if len({record["planner_seed"] for record in queries}) != QUERY_COUNT:
        raise RuntimeError("Cube gate planner seeds are not unique")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "cube_p2_d75_environment_gate_queries"
            output.attrs["partition"] = PARTITION
            output.attrs["root_seed"] = ROOT_SEED
            output.attrs["hash_namespace"] = HASH_NAMESPACE
            output.attrs["query_count"] = QUERY_COUNT
            output.attrs["goal_offset"] = GOAL_OFFSET
            output.attrs["dataset_sha256"] = DATASET_SHA256
            output.attrs["partition_manifest_sha256"] = PARTITION_MANIFEST_SHA256
            for key in queries[0]:
                output.create_dataset(
                    key,
                    data=np.asarray([record[key] for record in queries], dtype=np.int64),
                )
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_cube_gate_queries_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": "cube_p2_d75_environment_gate_queries",
        "partition": PARTITION,
        "reporting_rule": "outcome-blind Cube/TwoRoom substitution-gate queries",
        "root_seed": ROOT_SEED,
        "hash_namespace": HASH_NAMESPACE,
        "query_count": QUERY_COUNT,
        "goal_offset": GOAL_OFFSET,
        "queries": queries,
        "selection": {
            "episode_order": "ascending domain-separated SHA-256",
            "start": "domain-separated SHA-256 modulo all D75-valid starts",
            "planner_seed": "low 63 bits of a separate domain-separated SHA-256",
            "episode_distinct": True,
        },
        "inputs": {
            "dataset": str(args.dataset),
            "dataset_bytes": DATASET_BYTES,
            "dataset_sha256": DATASET_SHA256,
            "partition_manifest": str(args.partition_manifest),
            "partition_manifest_sha256": PARTITION_MANIFEST_SHA256,
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
