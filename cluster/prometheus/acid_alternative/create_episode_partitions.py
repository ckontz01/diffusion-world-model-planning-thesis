#!/usr/bin/env python3
"""Freeze deterministic episode-level P1/P2/P3/P4 partitions."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

import h5py
import numpy as np

from acid_alternative.io_utils import atomic_write_json, sha256_file


def read_exclusions(paths: list[Path]) -> tuple[set[int], dict[int, list[str]]]:
    excluded: set[int] = set()
    sources: dict[int, list[str]] = defaultdict(list)
    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(path)
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        if not rows or "episode_id" not in rows[0]:
            raise ValueError(f"invalid exclusion manifest: {path}")
        for row in rows:
            episode = int(row["episode_id"])
            excluded.add(episode)
            sources[episode].append(str(path))
    return excluded, sources


def assignment(dataset_name: str, seed: int, episode: int) -> tuple[str, str]:
    digest = hashlib.sha256(f"{dataset_name}\0{seed}\0{episode}".encode()).hexdigest()
    uniform = int(digest[:16], 16) / float(1 << 64)
    if uniform < 0.7:
        partition = "P1"
    elif uniform < 0.8:
        partition = "P2"
    elif uniform < 0.9:
        partition = "P3"
    else:
        partition = "P4"
    return partition, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--exclude-manifest", type=Path, action="append", default=[])
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if not args.dataset.is_file():
        raise FileNotFoundError(args.dataset)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing partition")

    excluded, sources = read_exclusions(args.exclude_manifest)
    with h5py.File(args.dataset, "r") as handle:
        if "ep_len" in handle:
            lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
            episodes = np.arange(len(lengths), dtype=np.int64)
        else:
            episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
            raw = np.asarray(handle[episode_key][:], dtype=np.int64).reshape(-1)
            episodes, lengths = np.unique(raw, return_counts=True)
    unknown = sorted(excluded - set(episodes.tolist()))
    if unknown:
        raise ValueError(f"excluded episodes absent from dataset: {unknown}")

    rows: list[dict[str, str | int]] = []
    for episode_value, length_value in zip(episodes, lengths):
        episode, length = int(episode_value), int(length_value)
        partition, digest = assignment(args.dataset_name, args.seed, episode)
        reason = "seeded_sha256_assignment"
        if episode in excluded:
            partition, reason = "P0", "observed_prepartition_baseline_or_smoke"
        rows.append(
            {
                "episode_id": episode,
                "episode_length": length,
                "partition": partition,
                "sha256": digest,
                "reason": reason,
                "exclusion_sources": "|".join(sorted(sources.get(episode, []))),
            }
        )
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    episode_counts = Counter(str(row["partition"]) for row in rows)
    frame_counts: Counter[str] = Counter()
    for row in rows:
        frame_counts[str(row["partition"])] += int(row["episode_length"])
    atomic_write_json(
        args.output_json,
        {
            "status": "ok",
            "kind": "episode_partition",
            "dataset": str(args.dataset.resolve()),
            "dataset_sha256": sha256_file(args.dataset),
            "dataset_name": args.dataset_name,
            "seed": args.seed,
            "hash_rule": "SHA256(dataset_name + NUL + seed + NUL + episode_id)",
            "thresholds": {
                "P1": [0.0, 0.7],
                "P2": [0.7, 0.8],
                "P3": [0.8, 0.9],
                "P4": [0.9, 1.0],
            },
            "p0_rule": "union of supplied pre-partition observed episode manifests",
            "source_exclusion_manifests": [str(path) for path in args.exclude_manifest],
            "total_episodes": len(rows),
            "total_frames": int(sum(int(row["episode_length"]) for row in rows)),
            "episode_counts": dict(sorted(episode_counts.items())),
            "frame_counts": dict(sorted(frame_counts.items())),
            "manifest_tsv": str(args.output_tsv.resolve()),
            "manifest_sha256": sha256_file(args.output_tsv),
        },
    )


if __name__ == "__main__":
    main()
