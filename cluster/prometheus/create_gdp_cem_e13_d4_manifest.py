#!/usr/bin/env python3
"""Create E13's identifier-only, one-start-per-episode untouched D4 manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e13_specs as spec


TASKS = spec.TASKS
COUNT = spec.COUNT
SHARD_SIZE = spec.SHARD_SIZE
SHARD_COUNT = spec.SHARD_COUNT
GOAL_OFFSET = 25
PARTITION = "P3"
SELECTION_SEED = spec.SELECTION_SEED
PROTOCOL_SHA256 = spec.PROTOCOL_SHA256
EXPECTED_DATASET_SHA256 = {
    task: str(spec.TASK_SPEC[task]["dataset_sha256"]) for task in TASKS
}
EXPECTED_PARTITION_SHA256 = spec.EXPECTED_PARTITION_SHA256
EXPECTED_EXCLUSION_SHA256 = spec.EXPECTED_EXCLUSION_SHA256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise FileExistsError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def reject_forbidden_input(
    path: Path,
    *,
    permit_protocol_d4: bool = False,
    permit_d3_exclusion: bool = False,
) -> None:
    normalized = str(path).replace("\\", "/").lower()
    tokens = {
        token
        for component in normalized.split("/")
        for token in re.split(r"[^a-z0-9]+", component)
        if token
    }
    forbidden = {"c1", "i1", "p4", "results"}
    if not permit_protocol_d4:
        forbidden.add("d4")
    if not permit_d3_exclusion:
        forbidden.add("d3")
    if tokens.intersection(forbidden):
        raise RuntimeError(f"forbidden manifest-generation input: {path}")


def read_partition(path: Path) -> dict[int, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"episode_id", "episode_length", "partition"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("invalid episode partition manifest")
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        episode = int(row["episode_id"])
        if episode in result:
            raise ValueError(f"duplicate partition episode {episode}")
        result[episode] = row
    return result


def read_identifier_episodes(path: Path) -> set[int]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames is None or "episode_id" not in reader.fieldnames:
            raise ValueError(f"invalid identifier manifest: {path}")
        if "success" in reader.fieldnames:
            raise RuntimeError(f"outcome-bearing exclusion input is forbidden: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty identifier manifest: {path}")
    return {int(row["episode_id"]) for row in rows}


def selection_hash(task: str, episode: int, start: int) -> str:
    payload = (
        f"gdp-e13-d4\0{task}\0{SELECTION_SEED}\0{episode}\0{start}"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument(
        "--exclusion", nargs=2, action="append", metavar=("LABEL", "TSV"), required=True
    )
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    exclusion_paths = {label: Path(path) for label, path in args.exclusion}
    if set(exclusion_paths) != {"r0", "d1", "d2", "d3"} or len(args.exclusion) != 4:
        raise ValueError(
            "E13 requires exactly the R0, D1, D2, and D3 identifier inputs"
        )
    ordinary_inputs = (
        args.dataset,
        args.partition_manifest,
        args.source_manifest,
        *exclusion_paths.values(),
    )
    for path in ordinary_inputs:
        reject_forbidden_input(
            path,
            permit_d3_exclusion=path == exclusion_paths.get("d3"),
        )
        if not path.is_file():
            raise FileNotFoundError(path)
    reject_forbidden_input(args.protocol, permit_protocol_d4=True)
    if not args.protocol.is_file():
        raise FileNotFoundError(args.protocol)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an E13 D4 manifest")
    protocol_sha256 = sha256_file(args.protocol)
    dataset_sha256 = sha256_file(args.dataset)
    partition_sha256 = sha256_file(args.partition_manifest)
    source_manifest_sha256 = sha256_file(args.source_manifest)
    exclusion_sha256 = {
        label: sha256_file(path) for label, path in exclusion_paths.items()
    }
    if protocol_sha256 != PROTOCOL_SHA256:
        raise RuntimeError("E13 protocol hash mismatch")
    if dataset_sha256 != EXPECTED_DATASET_SHA256[args.task]:
        raise RuntimeError("E13 dataset hash mismatch")
    if partition_sha256 != EXPECTED_PARTITION_SHA256[args.task]:
        raise RuntimeError("E13 partition-manifest hash mismatch")
    for label, path in exclusion_paths.items():
        if exclusion_sha256[label] != EXPECTED_EXCLUSION_SHA256[args.task][label]:
            raise RuntimeError(f"E13 {label} identifier-manifest hash mismatch")

    partition = read_partition(args.partition_manifest)
    exclusion_sets = {
        label: read_identifier_episodes(path)
        for label, path in exclusion_paths.items()
    }
    excluded = set().union(*exclusion_sets.values())
    with h5py.File(args.dataset, "r") as handle:
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64).reshape(-1)
    if len(lengths) != len(offsets) or set(partition) != set(range(len(lengths))):
        raise RuntimeError("E13 dataset and partition episode identities differ")
    for episode, length in enumerate(lengths.tolist()):
        if int(partition[episode]["episode_length"]) != int(length):
            raise RuntimeError(f"E13 episode-length mismatch for {episode}")

    ranked: list[tuple[str, int, int]] = []
    eligible_tuple_count = 0
    for episode, length_value in enumerate(lengths.tolist()):
        if partition[episode]["partition"] != PARTITION or episode in excluded:
            continue
        best: tuple[str, int] | None = None
        for start in range(max(0, int(length_value) - GOAL_OFFSET)):
            digest = selection_hash(args.task, episode, start)
            record = (digest, start)
            if best is None or record < best:
                best = record
            eligible_tuple_count += 1
        if best is not None:
            ranked.append((best[0], episode, best[1]))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    if len(ranked) != spec.UNTOUCHED_P3_CAPACITY[args.task]:
        raise RuntimeError(
            f"E13 untouched P3 capacity {len(ranked)} differs from frozen "
            f"{spec.UNTOUCHED_P3_CAPACITY[args.task]}"
        )
    if len(ranked) < COUNT:
        raise RuntimeError(
            f"need {COUNT} untouched valid P3 episodes; found {len(ranked)}"
        )
    selected = ranked[:COUNT]
    selected_episodes = {episode for _, episode, _ in selected}
    selected_pairs = {(episode, start) for _, episode, start in selected}
    if len(selected_episodes) != COUNT or len(selected_pairs) != COUNT:
        raise RuntimeError("E13 selection is not one unique start per unique episode")
    intersections = {
        label: len(selected_episodes.intersection(episodes))
        for label, episodes in exclusion_sets.items()
    }
    if any(intersections.values()):
        raise RuntimeError(f"E13 selected excluded episode identities: {intersections}")

    fieldnames = (
        "eval_index",
        "shard_index",
        "episode_id",
        "start_step",
        "dataset_goal_step",
        "declared_goal_offset",
        "source_global_row",
        "goal_global_row",
        "selection_hash",
    )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    for index, (digest, episode, start) in enumerate(selected):
        writer.writerow(
            {
                "eval_index": index,
                "shard_index": index // SHARD_SIZE,
                "episode_id": episode,
                "start_step": start,
                "dataset_goal_step": start + GOAL_OFFSET - 1,
                "declared_goal_offset": GOAL_OFFSET,
                "source_global_row": int(offsets[episode]) + start,
                "goal_global_row": int(offsets[episode]) + start + GOAL_OFFSET - 1,
                "selection_hash": digest,
            }
        )
    atomic_text(args.output_tsv, buffer.getvalue())

    summary = {
        "status": "ok",
        "kind": "gdp_cem_e13_untouched_d4_manifest",
        "analysis_role": "untouched_D4_confirmation",
        "task": args.task,
        "count": COUNT,
        "unique_episode_count": len(selected_episodes),
        "partition": PARTITION,
        "selection_namespace": "gdp-e13-d4",
        "selection_seed": SELECTION_SEED,
        "selection_rule": (
            "lowest SHA256 start per eligible episode, then lowest 400 "
            "(digest,episode,start) records"
        ),
        "goal_offset": GOAL_OFFSET,
        "shard_size": SHARD_SIZE,
        "shard_count": SHARD_COUNT,
        "eligible_untouched_p3_episodes": len(ranked),
        "eligible_start_tuples": eligible_tuple_count,
        "excluded_episode_union_count": len(excluded),
        "exclusion_counts": {
            label: len(episodes) for label, episodes in exclusion_sets.items()
        },
        "selected_exclusion_intersections": intersections,
        "identifier_inputs_only": True,
        "outcome_columns_read": False,
        "d3_outcomes_read": False,
        "d4_outcomes_read": False,
        "protected_p4_c1_i1_paths_read": False,
        "dataset": str(args.dataset),
        "dataset_sha256": dataset_sha256,
        "dataset_file_identity": {
            "size": args.dataset.stat().st_size,
            "mtime_ns": args.dataset.stat().st_mtime_ns,
            "device": args.dataset.stat().st_dev,
            "inode": args.dataset.stat().st_ino,
            "mode": args.dataset.stat().st_mode,
        },
        "partition_manifest": str(args.partition_manifest),
        "partition_manifest_sha256": partition_sha256,
        "exclusion_manifests": {
            label: {"path": str(path), "sha256": exclusion_sha256[label]}
            for label, path in sorted(exclusion_paths.items())
        },
        "protocol": str(args.protocol),
        "protocol_sha256": protocol_sha256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_manifest_sha256,
        "manifest_tsv": str(args.output_tsv),
        "manifest_tsv_sha256": sha256_file(args.output_tsv),
    }
    atomic_json(args.output_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
