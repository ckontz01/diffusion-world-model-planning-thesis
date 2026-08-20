#!/usr/bin/env python3
"""Freeze episode-disjoint I1 episodes from each task's locked source partition."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np

from acid_alternative.create_eval_manifests import (
    find_legacy_pairs,
    read_partitions,
)
from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.task_registry import get_task_spec


def evaluation_episodes(paths: list[Path]) -> set[int]:
    result: set[int] = set()
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        if not rows or "episode_id" not in rows[0]:
            raise RuntimeError(f"invalid evaluation manifest: {path}")
        result.update(int(row["episode_id"]) for row in rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument(
        "--evaluation-manifest", type=Path, action="append", required=True
    )
    parser.add_argument("--legacy-root", type=Path, action="append", default=[])
    parser.add_argument("--legacy-exclude-path-token", action="append", default=[])
    parser.add_argument("--seed", type=int, default=2026081314)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--partition", default="P4")
    parser.add_argument("--frameskip", type=int, default=5)
    parser.add_argument(
        "--maximum-legacy-h5-bytes", type=int, default=128 * 1024 * 1024
    )
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    spec = get_task_spec(args.task)
    if args.partition != spec.i1_source_partition:
        raise ValueError(
            f"{args.task}: I1 must use frozen source partition "
            f"{spec.i1_source_partition}, got {args.partition}"
        )
    for path in (args.dataset, args.partition_manifest):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite I1 manifests")
    if min(args.count, args.frameskip, args.maximum_legacy_h5_bytes) <= 0:
        raise ValueError("I1 count, frameskip, and scan size must be positive")

    partitions = read_partitions(args.partition_manifest)
    with h5py.File(args.dataset, "r") as handle:
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
    if set(partitions) != set(range(len(lengths))):
        raise RuntimeError("partition and dataset episode sets differ")
    legacy_pairs, legacy_sources = find_legacy_pairs(
        args.legacy_root,
        args.maximum_legacy_h5_bytes,
        excluded_path_tokens=args.legacy_exclude_path_token,
    )
    legacy_episodes = {episode for episode, _step in legacy_pairs}
    evaluated_episodes = evaluation_episodes(args.evaluation_manifest)
    excluded = legacy_episodes | evaluated_episodes
    ranked: list[tuple[str, int]] = []
    for episode, length in enumerate(lengths.tolist()):
        if (
            partitions[episode] == args.partition
            and length > args.frameskip
            and episode not in excluded
        ):
            digest = hashlib.sha256(
                f"{args.task}\0{args.seed}\0I1\0{episode}".encode()
            ).hexdigest()
            ranked.append((digest, episode))
    ranked.sort()
    if len(ranked) < args.count:
        raise RuntimeError(
            f"need {args.count} eligible I1 episodes, found {len(ranked)}"
        )
    selected = ranked[: args.count]
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "episode_id",
                "episode_length",
                "partition",
                "selection_hash",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for digest, episode in selected:
            writer.writerow(
                {
                    "episode_id": episode,
                    "episode_length": int(lengths[episode]),
                    "partition": "I1",
                    "selection_hash": digest,
                }
            )
    summary = {
        "status": "ok",
        "kind": "acid_alternative_i1_identification_episode_manifest",
        "task": args.task,
        "seed": args.seed,
        "count": len(selected),
        "source_partition": args.partition,
        "frameskip": args.frameskip,
        "selection_rule": "ascending SHA256(task + NUL + seed + NUL + I1 + NUL + episode)",
        "dataset": str(args.dataset.resolve()),
        "dataset_sha256": sha256_file(args.dataset),
        "partition_manifest": str(args.partition_manifest.resolve()),
        "partition_manifest_sha256": sha256_file(args.partition_manifest),
        "evaluation_manifests": [
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
            }
            for path in args.evaluation_manifest
        ],
        "legacy_unique_pairs_recovered": len(legacy_pairs),
        "legacy_unique_episodes_excluded": len(legacy_episodes),
        "evaluation_episodes_excluded": len(evaluated_episodes),
        "eligible_episode_count": len(ranked),
        "legacy_sources": legacy_sources,
        "legacy_excluded_path_tokens": args.legacy_exclude_path_token,
        "maximum_legacy_h5_bytes": args.maximum_legacy_h5_bytes,
        "confirmation_identification_outcomes_computed": False,
        "manifest_tsv": str(args.output_tsv.resolve()),
        "manifest_sha256": sha256_file(args.output_tsv),
    }
    atomic_write_json(args.output_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
