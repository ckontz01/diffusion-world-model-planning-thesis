#!/usr/bin/env python3
"""Freeze an episode-disjoint 90/10 train/validation split within P1."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path

from acid_alternative.io_utils import atomic_write_json, sha256_file


def role(dataset_name: str, seed: int, episode: int) -> tuple[str, str]:
    payload = f"{dataset_name}\0{seed}\0p1_train_val\0{episode}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    uniform = int(digest[:16], 16) / float(1 << 64)
    return ("P1_train" if uniform < 0.9 else "P1_val"), digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if not args.partition_manifest.is_file():
        raise FileNotFoundError(args.partition_manifest)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing P1 split")
    with args.partition_manifest.open(newline="", encoding="utf-8") as stream:
        master = list(csv.DictReader(stream, delimiter="\t"))
    p1 = [row for row in master if row["partition"] == "P1"]
    if not p1:
        raise ValueError("partition manifest contains no P1 episodes")
    rows: list[dict[str, str | int]] = []
    for source in p1:
        episode = int(source["episode_id"])
        assigned, digest = role(args.dataset_name, args.seed, episode)
        rows.append(
            {
                "episode_id": episode,
                "episode_length": int(source["episode_length"]),
                "p1_role": assigned,
                "sha256": digest,
            }
        )
    if {str(row["p1_role"]) for row in rows} != {"P1_train", "P1_val"}:
        raise RuntimeError("P1 split did not produce both roles")
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(str(row["p1_role"]) for row in rows)
    frames: Counter[str] = Counter()
    for row in rows:
        frames[str(row["p1_role"])] += int(row["episode_length"])
    atomic_write_json(
        args.output_json,
        {
            "status": "ok",
            "kind": "p1_episode_train_validation_split",
            "dataset_name": args.dataset_name,
            "seed": args.seed,
            "hash_rule": (
                "SHA256(dataset_name + NUL + seed + NUL + "
                "p1_train_val + NUL + episode_id)"
            ),
            "thresholds": {"P1_train": [0.0, 0.9], "P1_val": [0.9, 1.0]},
            "source_partition_manifest": str(args.partition_manifest.resolve()),
            "source_partition_manifest_sha256": sha256_file(args.partition_manifest),
            "episode_counts": dict(sorted(counts.items())),
            "frame_counts": dict(sorted(frames.items())),
            "manifest_tsv": str(args.output_tsv.resolve()),
            "manifest_sha256": sha256_file(args.output_tsv),
        },
    )


if __name__ == "__main__":
    main()
