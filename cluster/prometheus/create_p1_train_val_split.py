#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def role(dataset_name: str, seed: int, episode_id: int) -> tuple[str, str]:
    payload = f"{dataset_name}\0{seed}\0p1_train_val\0{episode_id}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    uniform = int(digest[:16], 16) / float(1 << 64)
    return ("P1_train" if uniform < 0.9 else "P1_val"), digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition_manifest", type=Path)
    parser.add_argument("--dataset-name", default="pusht_expert_train")
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing P1 split")
    with args.partition_manifest.open(newline="", encoding="utf-8") as stream:
        master_rows = list(csv.DictReader(stream, delimiter="\t"))
    p1_rows = [row for row in master_rows if row["partition"] == "P1"]
    if not p1_rows:
        raise SystemExit("master partition manifest contains no P1 episodes")

    rows = []
    for source in p1_rows:
        episode_id = int(source["episode_id"])
        assigned, digest = role(args.dataset_name, args.seed, episode_id)
        rows.append(
            {
                "episode_id": episode_id,
                "episode_length": int(source["episode_length"]),
                "p1_role": assigned,
                "sha256": digest,
            }
        )

    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("episode_id", "episode_length", "p1_role", "sha256"),
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(row["p1_role"] for row in rows)
    frames = Counter()
    for row in rows:
        frames[row["p1_role"]] += row["episode_length"]
    result = {
        "status": "ok",
        "dataset_name": args.dataset_name,
        "seed": args.seed,
        "hash_rule": 'SHA256(dataset_name + "\\0" + seed + "\\0p1_train_val\\0" + episode_id)',
        "thresholds": {"P1_train": [0.0, 0.9], "P1_val": [0.9, 1.0]},
        "source_partition_manifest": str(args.partition_manifest.resolve()),
        "source_partition_manifest_sha256": hashlib.sha256(
            args.partition_manifest.read_bytes()
        ).hexdigest(),
        "episode_counts": dict(sorted(counts.items())),
        "frame_counts": dict(sorted(frames.items())),
        "manifest_tsv": str(args.output_tsv.resolve()),
        "manifest_sha256": hashlib.sha256(args.output_tsv.read_bytes()).hexdigest(),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
