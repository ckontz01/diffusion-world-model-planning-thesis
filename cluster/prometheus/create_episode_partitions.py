#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import h5py
import numpy as np


def read_excluded_episode_ids(paths: list[Path]) -> tuple[set[int], dict[int, list[str]]]:
    excluded: set[int] = set()
    sources: dict[int, list[str]] = defaultdict(list)
    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"missing or empty exclusion manifest: {path}")
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        if not rows or "episode_id" not in rows[0]:
            raise SystemExit(f"invalid exclusion manifest: {path}")
        for row in rows:
            episode_id = int(row["episode_id"])
            excluded.add(episode_id)
            sources[episode_id].append(str(path))
    return excluded, sources


def assignment(dataset_name: str, seed: int, episode_id: int) -> tuple[str, str]:
    payload = f"{dataset_name}\0{seed}\0{episode_id}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
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
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--dataset-name", default="pusht_expert_train")
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--exclude-manifest", type=Path, action="append", default=[])
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    excluded, exclusion_sources = read_excluded_episode_ids(args.exclude_manifest)
    with h5py.File(args.dataset, "r") as handle:
        if "ep_len" in handle:
            lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
            episode_ids = np.arange(lengths.size, dtype=np.int64)
        else:
            episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
            raw_ids = np.asarray(handle[episode_key][:], dtype=np.int64).reshape(-1)
            episode_ids, lengths = np.unique(raw_ids, return_counts=True)

    unknown_exclusions = sorted(excluded.difference(int(value) for value in episode_ids))
    if unknown_exclusions:
        raise SystemExit(f"excluded episode IDs not present in dataset: {unknown_exclusions}")

    rows = []
    for episode_id_np, length_np in zip(episode_ids, lengths):
        episode_id = int(episode_id_np)
        length = int(length_np)
        assigned, digest = assignment(args.dataset_name, args.seed, episode_id)
        if episode_id in excluded:
            partition = "P0"
            reason = "observed_prepartition_baseline_or_smoke"
        else:
            partition = assigned
            reason = "seeded_sha256_assignment"
        rows.append(
            {
                "episode_id": episode_id,
                "episode_length": length,
                "partition": partition,
                "sha256": digest,
                "reason": reason,
                "exclusion_sources": "|".join(sorted(exclusion_sources.get(episode_id, []))),
            }
        )

    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "episode_id",
                "episode_length",
                "partition",
                "sha256",
                "reason",
                "exclusion_sources",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    manifest_sha256 = hashlib.sha256(args.output_tsv.read_bytes()).hexdigest()
    episode_counts = Counter(row["partition"] for row in rows)
    frame_counts = Counter()
    for row in rows:
        frame_counts[row["partition"]] += row["episode_length"]
    result = {
        "status": "ok",
        "dataset": str(args.dataset.resolve()),
        "dataset_name": args.dataset_name,
        "seed": args.seed,
        "hash_rule": 'SHA256(dataset_name + "\\0" + seed + "\\0" + episode_id)',
        "thresholds": {"P1": [0.0, 0.7], "P2": [0.7, 0.8], "P3": [0.8, 0.9], "P4": [0.9, 1.0]},
        "p0_rule": "union of supplied pre-partition observed episode manifests",
        "source_exclusion_manifests": [str(path) for path in args.exclude_manifest],
        "total_episodes": len(rows),
        "total_frames": int(sum(row["episode_length"] for row in rows)),
        "episode_counts": dict(sorted(episode_counts.items())),
        "frame_counts": dict(sorted(frame_counts.items())),
        "manifest_tsv": str(args.output_tsv),
        "manifest_sha256": manifest_sha256,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

