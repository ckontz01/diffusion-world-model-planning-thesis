#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("master_partition_manifest", type=Path)
    parser.add_argument("p1_split_manifest", type=Path)
    parser.add_argument("m12_manifest", type=Path)
    parser.add_argument("m3_manifest", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--m12-delta", type=int, default=25)
    parser.add_argument("--m3-min-delta", type=int, default=1)
    parser.add_argument("--m3-max-delta", type=int, default=40)
    parser.add_argument("--m3-train-per-delta", type=int, default=2500)
    parser.add_argument("--m3-val-per-delta", type=int, default=250)
    args = parser.parse_args()

    master_rows = read_tsv(args.master_partition_manifest)
    split_rows = read_tsv(args.p1_split_manifest)
    m12_rows = read_tsv(args.m12_manifest)
    summary = json.loads(args.summary.read_text(encoding="utf-8"))

    master_by_id = {int(row["episode_id"]): row for row in master_rows}
    split_by_id = {int(row["episode_id"]): row for row in split_rows}
    if len(master_by_id) != len(master_rows) or len(split_by_id) != len(split_rows):
        raise SystemExit("duplicate episode IDs in a source manifest")

    offsets: dict[int, int] = {}
    running = 0
    for episode_id in range(len(master_rows)):
        row = master_by_id[episode_id]
        offsets[episode_id] = running
        running += int(row["episode_length"])

    if len(m12_rows) != len(split_rows):
        raise SystemExit("M1/M2 plan does not have exactly one row per P1 episode")
    m12_counts: Counter[str] = Counter()
    seen_m12: set[int] = set()
    for row in m12_rows:
        episode_id = int(row["episode_id"])
        if episode_id in seen_m12:
            raise SystemExit(f"duplicate M1/M2 episode: {episode_id}")
        seen_m12.add(episode_id)
        source = split_by_id.get(episode_id)
        if source is None:
            raise SystemExit(f"non-P1 episode in M1/M2 plan: {episode_id}")
        role = source["p1_role"]
        length = int(source["episode_length"])
        offset = offsets[episode_id]
        pair_count = max(length - args.m12_delta, 0)
        expected = {
            "p1_role": role,
            "global_offset": offset,
            "episode_length": length,
            "delta": args.m12_delta,
            "pair_count": pair_count,
            "source_start_row": offset,
            "source_end_exclusive": offset + pair_count,
            "target_start_row": offset + args.m12_delta,
            "target_end_exclusive": offset + args.m12_delta + pair_count,
        }
        for field, value in expected.items():
            observed = row[field] if field == "p1_role" else int(row[field])
            if observed != value:
                raise SystemExit(
                    f"M1/M2 mismatch episode={episode_id} field={field}: "
                    f"observed={observed} expected={value}"
                )
        m12_counts[role] += pair_count

    expected_per_delta = {
        "P1_train": args.m3_train_per_delta,
        "P1_val": args.m3_val_per_delta,
    }
    m3_counts: Counter[tuple[str, int]] = Counter()
    seen_m3: set[tuple[str, int, int, int]] = set()
    rows_read = 0
    with gzip.open(args.m3_manifest, "rt", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        for row in reader:
            rows_read += 1
            role = row["p1_role"]
            delta = int(row["delta"])
            draw_index = int(row["draw_index"])
            episode_id = int(row["episode_id"])
            start_step = int(row["start_step"])
            target_step = int(row["target_step"])
            source_row = int(row["source_row"])
            target_row = int(row["target_row"])
            source = split_by_id.get(episode_id)
            if source is None or source["p1_role"] != role:
                raise SystemExit(
                    f"M3 role/episode mismatch at data row {rows_read}"
                )
            if role not in expected_per_delta:
                raise SystemExit(f"invalid M3 role at data row {rows_read}: {role}")
            if not args.m3_min_delta <= delta <= args.m3_max_delta:
                raise SystemExit(f"invalid M3 delta at data row {rows_read}: {delta}")
            length = int(source["episode_length"])
            if not 0 <= start_step < target_step < length:
                raise SystemExit(f"invalid M3 steps at data row {rows_read}")
            if target_step - start_step != delta:
                raise SystemExit(f"M3 delta mismatch at data row {rows_read}")
            if source_row != offsets[episode_id] + start_step:
                raise SystemExit(f"M3 source-row mismatch at data row {rows_read}")
            if target_row != source_row + delta:
                raise SystemExit(f"M3 target-row mismatch at data row {rows_read}")
            key = (role, delta, episode_id, start_step)
            if key in seen_m3:
                raise SystemExit(f"duplicate M3 pair at data row {rows_read}: {key}")
            seen_m3.add(key)
            m3_counts[(role, delta)] += 1
            if draw_index < 0 or draw_index >= expected_per_delta[role]:
                raise SystemExit(f"invalid M3 draw index at data row {rows_read}")

    for role, expected_count in expected_per_delta.items():
        for delta in range(args.m3_min_delta, args.m3_max_delta + 1):
            observed = m3_counts[(role, delta)]
            if observed != expected_count:
                raise SystemExit(
                    f"M3 count mismatch role={role} delta={delta}: "
                    f"observed={observed} expected={expected_count}"
                )

    hashes = {
        "master": sha256_file(args.master_partition_manifest),
        "p1_split": sha256_file(args.p1_split_manifest),
        "m12": sha256_file(args.m12_manifest),
        "m3": sha256_file(args.m3_manifest),
    }
    expected_hashes = {
        "master": summary["source_master_manifest_sha256"],
        "p1_split": summary["source_p1_split_manifest_sha256"],
        "m12": summary["m1_m2"]["manifest_sha256"],
        "m3": summary["m3"]["manifest_sha256"],
    }
    if hashes != expected_hashes:
        raise SystemExit(
            f"summary hash mismatch: observed={hashes} expected={expected_hashes}"
        )

    result = {
        "status": "ok",
        "total_dataset_rows": running,
        "m1_m2_episode_rows": len(m12_rows),
        "m1_m2_pair_counts": dict(sorted(m12_counts.items())),
        "m3_rows": rows_read,
        "m3_unique_pairs": len(seen_m3),
        "m3_counts_per_role": {
            role: sum(
                m3_counts[(role, delta)]
                for delta in range(args.m3_min_delta, args.m3_max_delta + 1)
            )
            for role in sorted(expected_per_delta)
        },
        "sha256": hashes,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
