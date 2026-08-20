#!/usr/bin/env python3
"""Create E11's identifier-only, one-start-per-episode untouched D3 manifest."""

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


TASKS = ("pusht", "reacher", "cube")
COUNT = 400
SHARD_SIZE = 50
SHARD_COUNT = 8
GOAL_OFFSET = 25
PARTITION = "P3"
SELECTION_SEED = 2026081709
PROTOCOL_SHA256 = "9b4bde9e2f69a7b92abaaf33f9db3016b8f61e82bedbe662a71a054cf3832ce0"
EXPECTED_DATASET_SHA256 = {
    "pusht": "b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb",
    "reacher": "85a7dddfa1801302abcb175a80a23bb69c78291dd977ce40d69aedcb9123da06",
    "cube": "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625",
}
EXPECTED_PARTITION_SHA256 = {
    "pusht": "35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0",
    "reacher": "d0628d371224bcccc4b65db20d91212aafdc91a5bbb2b707be10354470910fcd",
    "cube": "2bb7dbe8faedcf58dc00669def093efeb9b70198fe8602a9f650b09c5adfcf8d",
}
EXPECTED_EXCLUSION_SHA256 = {
    "pusht": {
        "r0": "232c71ec2c69c2f130d2506cc8b720448975728f6eb3ad763f648e74df13cd79",
        "d1": "948a5e0dc1f79551845a9ef039908729d3d0c4c4bee5deb8445fe465f694814e",
        "d2": "85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89",
    },
    "reacher": {
        "r0": "7a72a2a3e1ea89b5ec8bb0a39807673621c2ae92e0c581b34276e0bc11f9279e",
        "d1": "0b6e89cbe785ec88b0a3ff8e2ff77375ba9518695ab54f9bc2d3256013084a56",
        "d2": "a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61",
    },
    "cube": {
        "r0": "7a72a2a3e1ea89b5ec8bb0a39807673621c2ae92e0c581b34276e0bc11f9279e",
        "d1": "9e5c3d336c44226dbd293c2f2c77427ef86941202d15874d509e884691cffcf4",
        "d2": "bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388",
    },
}


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


def reject_forbidden_input(path: Path, *, permit_protocol_d3: bool = False) -> None:
    normalized = str(path).replace("\\", "/").lower()
    tokens = {
        token
        for component in normalized.split("/")
        for token in re.split(r"[^a-z0-9]+", component)
        if token
    }
    forbidden = {"c1", "i1", "results"}
    if not permit_protocol_d3:
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
        f"gdp-e11-d3\0{task}\0{SELECTION_SEED}\0{episode}\0{start}"
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
    if set(exclusion_paths) != {"r0", "d1", "d2"} or len(args.exclusion) != 3:
        raise ValueError("E11 requires exactly the R0, D1, and D2 identifier inputs")
    ordinary_inputs = (
        args.dataset,
        args.partition_manifest,
        args.source_manifest,
        *exclusion_paths.values(),
    )
    for path in ordinary_inputs:
        reject_forbidden_input(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    reject_forbidden_input(args.protocol, permit_protocol_d3=True)
    if not args.protocol.is_file():
        raise FileNotFoundError(args.protocol)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an E11 D3 manifest")
    protocol_sha256 = sha256_file(args.protocol)
    dataset_sha256 = sha256_file(args.dataset)
    partition_sha256 = sha256_file(args.partition_manifest)
    source_manifest_sha256 = sha256_file(args.source_manifest)
    exclusion_sha256 = {
        label: sha256_file(path) for label, path in exclusion_paths.items()
    }
    if protocol_sha256 != PROTOCOL_SHA256:
        raise RuntimeError("E11 protocol hash mismatch")
    if dataset_sha256 != EXPECTED_DATASET_SHA256[args.task]:
        raise RuntimeError("E11 dataset hash mismatch")
    if partition_sha256 != EXPECTED_PARTITION_SHA256[args.task]:
        raise RuntimeError("E11 partition-manifest hash mismatch")
    for label, path in exclusion_paths.items():
        if exclusion_sha256[label] != EXPECTED_EXCLUSION_SHA256[args.task][label]:
            raise RuntimeError(f"E11 {label} identifier-manifest hash mismatch")

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
        raise RuntimeError("E11 dataset and partition episode identities differ")
    for episode, length in enumerate(lengths.tolist()):
        if int(partition[episode]["episode_length"]) != int(length):
            raise RuntimeError(f"E11 episode-length mismatch for {episode}")

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
    if len(ranked) < COUNT:
        raise RuntimeError(
            f"need {COUNT} untouched valid P3 episodes; found {len(ranked)}"
        )
    selected = ranked[:COUNT]
    selected_episodes = {episode for _, episode, _ in selected}
    selected_pairs = {(episode, start) for _, episode, start in selected}
    if len(selected_episodes) != COUNT or len(selected_pairs) != COUNT:
        raise RuntimeError("E11 selection is not one unique start per unique episode")
    intersections = {
        label: len(selected_episodes.intersection(episodes))
        for label, episodes in exclusion_sets.items()
    }
    if any(intersections.values()):
        raise RuntimeError(f"E11 selected excluded episode identities: {intersections}")

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
        "kind": "gdp_cem_e11_untouched_d3_manifest",
        "analysis_role": "untouched_D3_confirmation",
        "task": args.task,
        "count": COUNT,
        "unique_episode_count": len(selected_episodes),
        "partition": PARTITION,
        "selection_namespace": "gdp-e11-d3",
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
        "protected_c1_i1_paths_read": False,
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
