#!/usr/bin/env python3
"""Create the isolated one-start-per-P3-episode D2 evaluation manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np


EXPECTED_PROTOCOL_SHA256 = (
    "c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb"
)
SELECTION_SEED = 2026081603
COUNT = 50
GOAL_OFFSET = 25
PARTITION = "P3"


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
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def protected_name(path: Path) -> bool:
    normalized = str(path).replace("\\", "/").lower()
    components = [part for part in normalized.split("/") if part]
    return any(
        part == token or part.startswith(f"{token}-") or part.endswith(f"-{token}")
        for token in ("c1", "i1")
        for part in components
    )


def read_partition(path: Path) -> dict[int, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "episode_length", "partition"}.issubset(
        rows[0]
    ):
        raise ValueError("invalid episode partition manifest")
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        episode = int(row["episode_id"])
        if episode in result:
            raise ValueError(f"duplicate partition episode {episode}")
        result[episode] = row
    return result


def read_r0_episodes(path: Path) -> set[int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or "episode_id" not in rows[0]:
        raise ValueError("invalid R0 manifest")
    return {int(row["episode_id"]) for row in rows}


def selection_hash(task: str, episode: int, start: int) -> str:
    payload = f"{task}\0{SELECTION_SEED}\0{episode}\0{start}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "reacher", "cube"), required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--r0-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    inputs = (
        args.dataset,
        args.partition_manifest,
        args.r0_manifest,
        args.protocol,
        args.source_manifest,
    )
    for path in inputs:
        if protected_name(path):
            raise RuntimeError(f"protected C1/I1 path is forbidden: {path}")
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("D2 protocol hash mismatch")
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite a D2 manifest")

    partition = read_partition(args.partition_manifest)
    r0_episodes = read_r0_episodes(args.r0_manifest)
    with h5py.File(args.dataset, "r") as handle:
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64).reshape(-1)
    if len(lengths) != len(offsets) or set(partition) != set(range(len(lengths))):
        raise RuntimeError("dataset and partition episode identities differ")
    for episode, length in enumerate(lengths.tolist()):
        if int(partition[episode]["episode_length"]) != int(length):
            raise RuntimeError(f"episode-length mismatch for {episode}")

    ranked: list[tuple[str, int, int]] = []
    eligible_episodes = 0
    eligible_tuples = 0
    for episode, length_value in enumerate(lengths.tolist()):
        if partition[episode]["partition"] != PARTITION or episode in r0_episodes:
            continue
        # Mirror the prior evaluator manifest: range(length - goal_offset),
        # whose final valid start has a dataset goal at start+goal_offset-1.
        valid_starts = range(max(0, int(length_value) - GOAL_OFFSET))
        best: tuple[str, int] | None = None
        count = 0
        for start in valid_starts:
            digest = selection_hash(args.task, episode, start)
            record = (digest, start)
            if best is None or record < best:
                best = record
            count += 1
        if best is None:
            continue
        eligible_episodes += 1
        eligible_tuples += count
        ranked.append((best[0], episode, best[1]))
    ranked.sort()
    if len(ranked) < COUNT:
        raise RuntimeError(
            f"need {COUNT} eligible P3 episodes after R0 exclusion; found {len(ranked)}"
        )
    selected = ranked[:COUNT]
    episodes = [episode for _, episode, _ in selected]
    pairs = [(episode, start) for _, episode, start in selected]
    if len(set(episodes)) != COUNT or len(set(pairs)) != COUNT:
        raise RuntimeError("D2 selection is not one-start-per-episode unique")
    if any(partition[episode]["partition"] != PARTITION for episode in episodes):
        raise RuntimeError("D2 selected a non-P3 episode")
    if set(episodes) & r0_episodes:
        raise RuntimeError("D2 overlaps an R0 episode")

    fieldnames = (
        "eval_index",
        "episode_id",
        "start_step",
        "dataset_goal_step",
        "declared_goal_offset",
        "source_global_row",
        "goal_global_row",
        "selection_hash",
    )
    lines: list[str] = []
    # csv module handles tabs and newlines correctly; StringIO keeps the final
    # write atomic.
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    for index, (digest, episode, start) in enumerate(selected):
        writer.writerow(
            {
                "eval_index": index,
                "episode_id": episode,
                "start_step": start,
                "dataset_goal_step": start + GOAL_OFFSET - 1,
                "declared_goal_offset": GOAL_OFFSET,
                "source_global_row": int(offsets[episode]) + start,
                "goal_global_row": int(offsets[episode]) + start + GOAL_OFFSET - 1,
                "selection_hash": digest,
            }
        )
    lines.append(buffer.getvalue())
    atomic_text(args.output_tsv, "".join(lines))

    summary = {
        "status": "ok",
        "kind": "acid_alternative_v3_fresh_d2_manifest",
        "analysis_role": "D2",
        "task": args.task,
        "count": COUNT,
        "unique_episode_count": len(set(episodes)),
        "partition": PARTITION,
        "selection_seed": SELECTION_SEED,
        "selection_rule": (
            "one lowest-hash valid start per eligible episode, then lowest 50 "
            "episode records by SHA256(task+NUL+seed+NUL+episode+NUL+start)"
        ),
        "goal_offset": GOAL_OFFSET,
        "eligible_p3_episodes_after_r0_episode_exclusion": eligible_episodes,
        "eligible_start_tuples": eligible_tuples,
        "r0_episode_count": len(r0_episodes),
        "episode_level_isolation": {
            "P1_training": "P3 differs from P1",
            "D1": "P3 differs from P2",
            "C1_I1": "P3 differs from P4; protected manifests were not inputs",
            "R0": "all R0 episodes excluded",
        },
        "protected_c1_i1_paths_read": False,
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "partition_manifest": str(args.partition_manifest),
        "partition_manifest_sha256": sha256_file(args.partition_manifest),
        "r0_manifest": str(args.r0_manifest),
        "r0_manifest_sha256": sha256_file(args.r0_manifest),
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "manifest_tsv": str(args.output_tsv),
        "manifest_tsv_sha256": sha256_file(args.output_tsv),
    }
    atomic_json(args.output_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
