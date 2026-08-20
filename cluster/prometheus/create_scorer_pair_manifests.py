#!/usr/bin/env python3

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from pathlib import Path


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise SystemExit(f"empty manifest: {path}")
    return rows


def write_m12_plan(
    path: Path,
    split_rows: list[dict[str, str]],
    offsets: dict[int, int],
    delta: int,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "episode_id",
                "p1_role",
                "global_offset",
                "episode_length",
                "delta",
                "pair_count",
                "source_start_row",
                "source_end_exclusive",
                "target_start_row",
                "target_end_exclusive",
            ),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in sorted(split_rows, key=lambda item: int(item["episode_id"])):
            episode_id = int(row["episode_id"])
            length = int(row["episode_length"])
            role = row["p1_role"]
            pair_count = max(length - delta, 0)
            offset = offsets[episode_id]
            writer.writerow(
                {
                    "episode_id": episode_id,
                    "p1_role": role,
                    "global_offset": offset,
                    "episode_length": length,
                    "delta": delta,
                    "pair_count": pair_count,
                    "source_start_row": offset,
                    "source_end_exclusive": offset + pair_count,
                    "target_start_row": offset + delta,
                    "target_end_exclusive": offset + delta + pair_count,
                }
            )
            counts[role] += pair_count
    return dict(sorted(counts.items()))


def uniform_ordinal(
    dataset_name: str,
    seed: int,
    role: str,
    delta: int,
    draw_index: int,
    candidate_count: int,
    used: set[int],
) -> tuple[int, str, int]:
    if len(used) >= candidate_count:
        raise RuntimeError("requested more unique pairs than the eligible population")
    modulus = 1 << 256
    rejection_limit = modulus - (modulus % candidate_count)
    attempt = 0
    while True:
        payload = (
            f"{dataset_name}\0{seed}\0m3_balanced\0{role}\0{delta}\0"
            f"{draw_index}\0{attempt}"
        ).encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        value = int.from_bytes(digest, "big")
        attempt += 1
        if value >= rejection_limit:
            continue
        ordinal = value % candidate_count
        if ordinal in used:
            continue
        used.add(ordinal)
        return ordinal, digest.hex(), attempt - 1


def write_m3_samples(
    path: Path,
    split_rows: list[dict[str, str]],
    offsets: dict[int, int],
    dataset_name: str,
    seed: int,
    min_delta: int,
    max_delta: int,
    counts_per_delta: dict[str, int],
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    role_rows = {
        role: sorted(
            (row for row in split_rows if row["p1_role"] == role),
            key=lambda item: int(item["episode_id"]),
        )
        for role in counts_per_delta
    }
    realized: Counter[str] = Counter()
    population_sizes: dict[str, dict[str, int]] = {
        role: {} for role in counts_per_delta
    }

    with path.open("xb") as raw_stream:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw_stream, mtime=0
        ) as compressed:
            with io.TextIOWrapper(
                compressed, encoding="utf-8", newline=""
            ) as text_stream:
                writer = csv.DictWriter(
                    text_stream,
                    fieldnames=(
                        "p1_role",
                        "delta",
                        "draw_index",
                        "episode_id",
                        "start_step",
                        "target_step",
                        "source_row",
                        "target_row",
                        "candidate_ordinal",
                        "selection_sha256",
                        "collision_attempt",
                    ),
                    delimiter="\t",
                    lineterminator="\n",
                )
                writer.writeheader()
                for role in sorted(counts_per_delta):
                    sample_count = counts_per_delta[role]
                    for delta in range(min_delta, max_delta + 1):
                        eligible = [
                            row
                            for row in role_rows[role]
                            if int(row["episode_length"]) > delta
                        ]
                        episode_counts = [
                            int(row["episode_length"]) - delta for row in eligible
                        ]
                        cumulative: list[int] = []
                        running = 0
                        for count in episode_counts:
                            running += count
                            cumulative.append(running)
                        population_sizes[role][str(delta)] = running
                        if running < sample_count:
                            raise RuntimeError(
                                f"{role} delta={delta} has only {running} eligible pairs"
                            )

                        used: set[int] = set()
                        for draw_index in range(sample_count):
                            ordinal, digest, collision_attempt = uniform_ordinal(
                                dataset_name=dataset_name,
                                seed=seed,
                                role=role,
                                delta=delta,
                                draw_index=draw_index,
                                candidate_count=running,
                                used=used,
                            )
                            episode_position = bisect.bisect_right(cumulative, ordinal)
                            prior = (
                                cumulative[episode_position - 1]
                                if episode_position > 0
                                else 0
                            )
                            start_step = ordinal - prior
                            episode_id = int(eligible[episode_position]["episode_id"])
                            source_row = offsets[episode_id] + start_step
                            writer.writerow(
                                {
                                    "p1_role": role,
                                    "delta": delta,
                                    "draw_index": draw_index,
                                    "episode_id": episode_id,
                                    "start_step": start_step,
                                    "target_step": start_step + delta,
                                    "source_row": source_row,
                                    "target_row": source_row + delta,
                                    "candidate_ordinal": ordinal,
                                    "selection_sha256": digest,
                                    "collision_attempt": collision_attempt,
                                }
                            )
                            realized[role] += 1
    return dict(sorted(realized.items())), population_sizes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("master_partition_manifest", type=Path)
    parser.add_argument("p1_split_manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-name", default="pusht_expert_train")
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--m12-delta", type=int, default=25)
    parser.add_argument("--m3-min-delta", type=int, default=1)
    parser.add_argument("--m3-max-delta", type=int, default=40)
    parser.add_argument("--m3-train-per-delta", type=int, default=2500)
    parser.add_argument("--m3-val-per-delta", type=int, default=250)
    args = parser.parse_args()

    master_rows = read_tsv(args.master_partition_manifest)
    split_rows = read_tsv(args.p1_split_manifest)
    required_master = {"episode_id", "episode_length", "partition"}
    required_split = {"episode_id", "episode_length", "p1_role"}
    if not required_master.issubset(master_rows[0]):
        raise SystemExit("master partition manifest has an invalid schema")
    if not required_split.issubset(split_rows[0]):
        raise SystemExit("P1 split manifest has an invalid schema")

    master_by_id = {int(row["episode_id"]): row for row in master_rows}
    expected_ids = list(range(len(master_rows)))
    if sorted(master_by_id) != expected_ids:
        raise SystemExit("episode IDs must be unique and contiguous from zero")
    offsets: dict[int, int] = {}
    running_offset = 0
    for episode_id in expected_ids:
        length = int(master_by_id[episode_id]["episode_length"])
        if length <= 0:
            raise SystemExit(f"episode {episode_id} has non-positive length")
        offsets[episode_id] = running_offset
        running_offset += length

    p1_ids = {
        episode_id
        for episode_id, row in master_by_id.items()
        if row["partition"] == "P1"
    }
    split_ids = {int(row["episode_id"]) for row in split_rows}
    if split_ids != p1_ids or len(split_ids) != len(split_rows):
        raise SystemExit("P1 split episodes do not exactly match master P1 episodes")
    for row in split_rows:
        episode_id = int(row["episode_id"])
        if int(row["episode_length"]) != int(
            master_by_id[episode_id]["episode_length"]
        ):
            raise SystemExit(f"episode length mismatch for episode {episode_id}")
        if row["p1_role"] not in {"P1_train", "P1_val"}:
            raise SystemExit(f"invalid P1 role for episode {episode_id}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    m12_path = args.output_dir / f"m1-m2-all-delta{args.m12_delta}-episodes.tsv"
    m3_path = args.output_dir / (
        f"m3-balanced-delta{args.m3_min_delta}-{args.m3_max_delta}.tsv.gz"
    )
    summary_path = args.output_dir / "scorer-pair-manifests-summary.json"
    for path in (m12_path, m3_path, summary_path):
        if path.exists():
            raise SystemExit(f"refusing to overwrite frozen output: {path}")

    m12_counts = write_m12_plan(
        path=m12_path,
        split_rows=split_rows,
        offsets=offsets,
        delta=args.m12_delta,
    )
    m3_counts, population_sizes = write_m3_samples(
        path=m3_path,
        split_rows=split_rows,
        offsets=offsets,
        dataset_name=args.dataset_name,
        seed=args.seed,
        min_delta=args.m3_min_delta,
        max_delta=args.m3_max_delta,
        counts_per_delta={
            "P1_train": args.m3_train_per_delta,
            "P1_val": args.m3_val_per_delta,
        },
    )

    result = {
        "status": "ok",
        "dataset_name": args.dataset_name,
        "seed": args.seed,
        "total_dataset_rows": running_offset,
        "source_master_manifest": str(args.master_partition_manifest.resolve()),
        "source_master_manifest_sha256": sha256_file(
            args.master_partition_manifest
        ),
        "source_p1_split_manifest": str(args.p1_split_manifest.resolve()),
        "source_p1_split_manifest_sha256": sha256_file(args.p1_split_manifest),
        "m1_m2": {
            "rule": "all valid within-episode pairs at exactly delta",
            "delta": args.m12_delta,
            "pair_counts": m12_counts,
            "manifest": str(m12_path.resolve()),
            "manifest_sha256": sha256_file(m12_path),
        },
        "m3": {
            "rule": (
                "balanced by integer delta; within each role and delta, uniform "
                "without replacement over valid within-episode pairs using "
                "domain-separated SHA-256 rejection sampling"
            ),
            "hash_domain": (
                "dataset_name\\0seed\\0m3_balanced\\0p1_role\\0delta\\0"
                "draw_index\\0collision_attempt"
            ),
            "delta_range_inclusive": [args.m3_min_delta, args.m3_max_delta],
            "requested_per_delta": {
                "P1_train": args.m3_train_per_delta,
                "P1_val": args.m3_val_per_delta,
            },
            "sample_counts": m3_counts,
            "eligible_population_sizes_by_delta": population_sizes,
            "manifest": str(m3_path.resolve()),
            "manifest_sha256": sha256_file(m3_path),
        },
    }
    summary_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
