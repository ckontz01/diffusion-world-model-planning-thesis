#!/usr/bin/env python3
"""Create the frozen shared-start P2 manifest for E14 Gate C."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import h5py
import numpy as np

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import sha256_file


SELECTION_SEED = 2026082301
BASE_STARTS = 20
HORIZONS = (25, 75, 150)


def atomic_json(path: Path, value: object) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def read_partitions(path: Path) -> dict[int, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "partition"}.issubset(rows[0]):
        raise RuntimeError("invalid E14 P2 partition manifest")
    result = {int(row["episode_id"]): row["partition"] for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("duplicate E14 P2 partition episode")
    return result


def select_base_starts(
    lengths: np.ndarray, partitions: dict[int, str], *, task: str
) -> tuple[list[tuple[int, int, str]], int]:
    maximum_horizon = max(HORIZONS)
    eligible = [
        (episode, start)
        for episode, length in enumerate(lengths.tolist())
        if partitions[episode] == "P2"
        for start in range(max(0, int(length) - maximum_horizon))
    ]
    ranked = []
    for episode, start in eligible:
        digest = hashlib.sha256(
            f"gdp-cem-e14-p2\0{task}\0{SELECTION_SEED}\0{episode}\0{start}".encode()
        ).hexdigest()
        ranked.append((digest, episode, start))
    ranked.sort()
    if len(ranked) < BASE_STARTS:
        raise RuntimeError("E14 P2 has too few H150-compatible starts")
    selected = [
        (episode, start, digest)
        for digest, episode, start in ranked[:BASE_STARTS]
    ]
    return selected, len(eligible)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.dataset,
        args.partition_manifest,
        args.protocol,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite E14 P2 manifest artifacts")
    task_spec = spec.TASK_SPEC[args.task]
    if (
        sha256_file(args.dataset) != task_spec["dataset_sha256"]
        or sha256_file(args.partition_manifest)
        != task_spec["partition_manifest_sha256"]
        or sha256_file(args.protocol) != spec.PROTOCOL_SHA256
    ):
        raise RuntimeError("E14 P2 manifest input hash differs")
    partitions = read_partitions(args.partition_manifest)
    with h5py.File(args.dataset, "r") as handle:
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
    if len(offsets) != len(lengths) or set(partitions) != set(range(len(lengths))):
        raise RuntimeError("E14 P2 dataset and partition episodes differ")
    selected, eligible_count = select_base_starts(
        lengths, partitions, task=args.task
    )
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_tsv.with_name(
        f".{args.output_tsv.name}.partial-{os.getpid()}"
    )
    try:
        with partial.open("x", newline="", encoding="utf-8") as stream:
            fields = (
                "eval_index",
                "base_index",
                "episode_id",
                "start_step",
                "goal_horizon",
                "dataset_goal_step",
                "source_global_row",
                "goal_global_row",
                "selection_hash",
            )
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            index = 0
            for horizon in HORIZONS:
                for base_index, (episode, start, digest) in enumerate(selected):
                    writer.writerow(
                        {
                            "eval_index": index,
                            "base_index": base_index,
                            "episode_id": episode,
                            "start_step": start,
                            "goal_horizon": horizon,
                            # StableWorldModel load_chunk uses an exclusive end.
                            "dataset_goal_step": start + horizon - 1,
                            "source_global_row": int(offsets[episode]) + start,
                            "goal_global_row": int(offsets[episode]) + start + horizon - 1,
                            "selection_hash": digest,
                        }
                    )
                    index += 1
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, args.output_tsv)
    finally:
        partial.unlink(missing_ok=True)
    record = {
        "status": "ok",
        "kind": "gdp_cem_e14_shared_start_p2_gate_c_manifest",
        "analysis_role": "P2_closed_loop_endpoint_selection_development",
        "task": args.task,
        "selection_seed": SELECTION_SEED,
        "base_start_count": BASE_STARTS,
        "horizons": list(HORIZONS),
        "rows_per_horizon": BASE_STARTS,
        "total_rows": BASE_STARTS * len(HORIZONS),
        "maximum_horizon_compatible_eligible_count": eligible_count,
        "same_episode_start_pairs_across_horizons": True,
        "partition": "P2",
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "partition_manifest": str(args.partition_manifest),
        "partition_manifest_sha256": sha256_file(args.partition_manifest),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "output_tsv": str(args.output_tsv),
        "output_tsv_sha256": sha256_file(args.output_tsv),
        "stable_worldmodel_goal_step_note": (
            "load_chunk end is exclusive; declared H selects dataset step start+H-1"
        ),
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_json, record)
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
