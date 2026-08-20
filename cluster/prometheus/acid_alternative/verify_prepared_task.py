#!/usr/bin/env python3
"""Verify frozen task partitions/evaluation starts without rewriting them."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from acid_alternative.create_episode_partitions import assignment
from acid_alternative.create_p1_split import role
from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.task_registry import TASKS, get_task_spec


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        result = list(csv.DictReader(stream, delimiter="\t"))
    if not result:
        raise RuntimeError(f"empty manifest: {path}")
    return result


def payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("status") != "ok":
        raise RuntimeError(f"invalid summary: {path}")
    return value


def optional_exact(record: dict[str, Any], key: str, expected: Any) -> bool:
    """Accept a missing legacy metadata key, but never a conflicting value."""
    return key not in record or record[key] == expected


def verify(args: argparse.Namespace) -> dict[str, Any]:
    spec = get_task_spec(args.task)
    for path in (args.dataset, args.partition_dir, args.eval_dir):
        if not path.exists():
            raise FileNotFoundError(path)
    dataset_hash = sha256_file(args.dataset)
    with h5py.File(args.dataset, "r") as handle:
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
        episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
        row_episodes = np.asarray(handle[episode_key][:], dtype=np.int64)
        row_steps = np.asarray(handle["step_idx"][:], dtype=np.int64)
    master_path = args.partition_dir / "episodes-seed-20260728.tsv"
    master_json_path = args.partition_dir / "episodes-seed-20260728-summary.json"
    p1_path = args.partition_dir / "p1-train-val-seed-20260728.tsv"
    p1_json_path = args.partition_dir / "p1-train-val-seed-20260728-summary.json"
    master = rows(master_path)
    master_json = payload(master_json_path)
    if (
        not optional_exact(master_json, "kind", "episode_partition")
        or not optional_exact(master_json, "dataset_sha256", dataset_hash)
        or master_json.get("dataset_name") != spec.dataset_name
        or master_json.get("seed") != 20260728
        or master_json.get("manifest_sha256") != sha256_file(master_path)
    ):
        raise RuntimeError("master partition summary differs from frozen task")
    if len(master) != len(lengths):
        raise RuntimeError("master partition does not cover every episode")
    partitions: dict[int, str] = {}
    for expected_episode, item in enumerate(master):
        episode = int(item["episode_id"])
        length = int(item["episode_length"])
        partition = item["partition"]
        if episode != expected_episode or length != int(lengths[episode]):
            raise RuntimeError("master episode identity or length mismatch")
        expected_partition, digest = assignment(spec.dataset_name, 20260728, episode)
        if item["sha256"] != digest:
            raise RuntimeError(f"episode {episode}: partition hash mismatch")
        if partition == "P0":
            if item.get("reason") != "observed_prepartition_baseline_or_smoke":
                raise RuntimeError(f"episode {episode}: invalid P0 reason")
        elif partition != expected_partition:
            raise RuntimeError(f"episode {episode}: seeded partition mismatch")
        partitions[episode] = partition
    if dict(sorted(Counter(partitions.values()).items())) != master_json.get(
        "episode_counts"
    ):
        raise RuntimeError("master partition counts differ from its summary")

    p1 = rows(p1_path)
    p1_json = payload(p1_json_path)
    if (
        not optional_exact(
            p1_json, "kind", "p1_episode_train_validation_split"
        )
        or p1_json.get("dataset_name") != spec.dataset_name
        or p1_json.get("seed") != 20260728
        or p1_json.get("source_partition_manifest_sha256") != sha256_file(master_path)
        or p1_json.get("manifest_sha256") != sha256_file(p1_path)
    ):
        raise RuntimeError("P1 split summary differs from frozen task")
    expected_p1 = {
        episode for episode, partition in partitions.items() if partition == "P1"
    }
    actual_p1: set[int] = set()
    for item in p1:
        episode = int(item["episode_id"])
        assigned, digest = role(spec.dataset_name, 20260728, episode)
        if (
            episode in actual_p1
            or int(item["episode_length"]) != int(lengths[episode])
            or item["p1_role"] != assigned
            or item["sha256"] != digest
        ):
            raise RuntimeError(f"episode {episode}: invalid P1 role record")
        actual_p1.add(episode)
    if actual_p1 != expected_p1:
        raise RuntimeError("P1 role manifest does not equal master P1 episodes")

    eval_json_path = args.eval_dir / "summary.json"
    eval_json = payload(eval_json_path)
    if (
        eval_json.get("kind") != "flat_matched_evaluation_manifests"
        or eval_json.get("task") != args.task
        or eval_json.get("dataset_sha256") != dataset_hash
        or eval_json.get("partition_manifest_sha256") != sha256_file(master_path)
        or eval_json.get("goal_offset") != 25
    ):
        raise RuntimeError("evaluation summary differs from frozen task")
    namespace_files = {
        "R0": ("r0-official-seed42.tsv", 50, 42, None),
        "D1": ("d1-fresh-development.tsv", 24, 2026081201, "P2"),
        "C1": ("c1-locked-confirmation.tsv", 50, 2026081202, "P4"),
    }
    seen: set[tuple[int, int]] = set()
    namespace_records: dict[str, Any] = {}
    for namespace, (
        filename,
        count,
        seed,
        required_partition,
    ) in namespace_files.items():
        path = args.eval_dir / filename
        selected = rows(path)
        record = eval_json.get("namespaces", {}).get(namespace, {})
        if (
            len(selected) != count
            or record.get("count") != count
            or record.get("seed") != seed
            or record.get("sha256") != sha256_file(path)
        ):
            raise RuntimeError(f"{namespace}: count, seed, or hash mismatch")
        if (
            required_partition is not None
            and record.get("partition") != required_partition
        ):
            raise RuntimeError(f"{namespace}: partition summary mismatch")
        pairs = []
        for expected_index, item in enumerate(selected):
            episode, start = int(item["episode_id"]), int(item["start_step"])
            pair = (episode, start)
            if pair in seen or int(item["eval_index"]) != expected_index:
                raise RuntimeError(f"{namespace}: duplicate pair or eval index")
            if (
                episode not in partitions
                or start < 0
                or start >= int(lengths[episode]) - 25
            ):
                raise RuntimeError(f"{namespace}: invalid episode/start pair")
            if (
                required_partition is not None
                and partitions[episode] != required_partition
            ):
                raise RuntimeError(f"{namespace}: pair is in the wrong partition")
            if (
                int(item["dataset_goal_step"]) != start + 24
                or int(item["declared_goal_offset"]) != 25
                or int(item["source_global_row"]) != int(offsets[episode]) + start
                or int(item["goal_global_row"]) != int(offsets[episode]) + start + 24
            ):
                raise RuntimeError(f"{namespace}: row-coordinate mismatch")
            if namespace == "R0":
                global_row = int(item["source_global_row"])
                digest = hashlib.sha256(
                    f"official-lewm\0{seed}\0{global_row}".encode()
                ).hexdigest()
            else:
                digest = hashlib.sha256(
                    f"{args.task}\0{seed}\0{episode}\0{start}".encode()
                ).hexdigest()
            if item["selection_hash"] != digest:
                raise RuntimeError(f"{namespace}: selection hash mismatch")
            seen.add(pair)
            pairs.append(pair)
        namespace_records[namespace] = {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "count": len(pairs),
        }

    i1_path = args.eval_dir / "i1-confirmation-identification-episodes.tsv"
    i1_json_path = args.eval_dir / "i1-confirmation-identification-summary.json"
    i1 = rows(i1_path)
    i1_record = payload(i1_json_path)
    expected_eval_hashes = [
        sha256_file(args.eval_dir / filename)
        for filename in (
            "r0-official-seed42.tsv",
            "d1-fresh-development.tsv",
            "c1-locked-confirmation.tsv",
        )
    ]
    if (
        len(i1) != 200
        or i1_record.get("kind")
        != "acid_alternative_i1_identification_episode_manifest"
        or i1_record.get("task") != args.task
        or i1_record.get("count") != 200
        or i1_record.get("seed") != 2026081314
        or i1_record.get("source_partition") != spec.i1_source_partition
        or i1_record.get("frameskip") != 5
        or i1_record.get("dataset_sha256") != dataset_hash
        or i1_record.get("partition_manifest_sha256") != sha256_file(master_path)
        or i1_record.get("manifest_sha256") != sha256_file(i1_path)
        or i1_record.get("confirmation_identification_outcomes_computed") is not False
        or [
            record.get("sha256")
            for record in i1_record.get("evaluation_manifests", [])
        ]
        != expected_eval_hashes
    ):
        raise RuntimeError("I1: count, seed, partition, or hash mismatch")
    i1_episodes: set[int] = set()
    i1_hashes: list[str] = []
    evaluation_episodes = {episode for episode, _start in seen}
    for item in i1:
        episode = int(item["episode_id"])
        digest = hashlib.sha256(
            f"{args.task}\0{2026081314}\0I1\0{episode}".encode()
        ).hexdigest()
        if (
            episode in i1_episodes
            or episode in evaluation_episodes
            or partitions.get(episode) != spec.i1_source_partition
            or int(item["episode_length"]) != int(lengths[episode])
            or int(lengths[episode]) <= 5
            or item["partition"] != "I1"
            or item["selection_hash"] != digest
        ):
            raise RuntimeError(f"I1: invalid episode record {episode}")
        i1_episodes.add(episode)
        i1_hashes.append(digest)
    if i1_hashes != sorted(i1_hashes):
        raise RuntimeError("I1: episodes are not in frozen hash order")
    namespace_records["I1"] = {
        "path": str(i1_path.resolve()),
        "sha256": sha256_file(i1_path),
        "count": len(i1),
        "episode_disjoint_from_r0_d1_c1": True,
        "summary_sha256": sha256_file(i1_json_path),
    }

    max_start = lengths - 26
    valid_rows = np.nonzero(row_steps <= max_start[row_episodes])[0]
    generator = np.random.default_rng(42)
    positions = generator.choice(len(valid_rows) - 1, size=50, replace=False)
    official = sorted(
        (int(row_episodes[row]), int(row_steps[row]))
        for row in np.sort(valid_rows[positions])
    )
    actual_r0 = sorted(
        (int(item["episode_id"]), int(item["start_step"]))
        for item in rows(args.eval_dir / "r0-official-seed42.tsv")
    )
    if actual_r0 != official:
        raise RuntimeError("R0 does not match the released seed-42 selection rule")
    return {
        "status": "pass",
        "kind": "acid_alternative_prepared_task_verification_v1",
        "task": args.task,
        "dataset": str(args.dataset.resolve()),
        "dataset_sha256": dataset_hash,
        "partition_manifest_sha256": sha256_file(master_path),
        "p1_manifest_sha256": sha256_file(p1_path),
        "evaluation_summary_sha256": sha256_file(eval_json_path),
        "namespaces": namespace_records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=tuple(TASKS), required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-dir", type=Path, required=True)
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite verification output: {args.output}")
    result = verify(args)
    atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
