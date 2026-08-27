#!/usr/bin/env python3
"""Select fresh E18 P2 starts while preserving the E17 failure record."""

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

import gdp_cem_e15_specs as e15
import gdp_cem_e18_specs as spec
from gdp_cem_e15_data import sha256_file


def atomic_json(path: Path, value: Any) -> None:
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
        raise RuntimeError("invalid E18 partition manifest")
    result = {int(row["episode_id"]): row["partition"] for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("duplicate E18 partition episode")
    return result


def read_old_pairs(path: Path) -> set[tuple[int, int]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "start_step", "goal_horizon"}.issubset(
        rows[0]
    ):
        raise RuntimeError("invalid old P2 query manifest")
    return {(int(row["episode_id"]), int(row["start_step"])) for row in rows}


def verify_e17_audit(path: Path) -> dict[str, Any]:
    if not path.is_file() or sha256_file(path) != spec.E17_AUDIT_SHA256:
        raise RuntimeError("E17 audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("decision") != "stop_transition_adapter_preflight_failed"
        or value.get("both_tasks_passed") is not False
        or value.get("planner_evaluation_authorized") is not False
        or value.get("separate_protocol_draft_authorized") is not False
        or value.get("task_results", {}).get("pusht", {}).get("passed") is not True
        or value.get("task_results", {}).get("cube", {}).get("passed") is not False
        or value.get("protocol_sha256") != spec.E17_PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != spec.E17_SOURCE_MANIFEST_SHA256
        or value.get("d5_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E17 failure record differs")
    return value


def select_base_starts(
    lengths: np.ndarray,
    partitions: dict[int, str],
    *,
    task: str,
    excluded: set[tuple[int, int]],
) -> tuple[list[tuple[int, int, str]], int]:
    maximum_horizon = max(spec.HORIZONS)
    eligible = [
        (episode, start)
        for episode, length in enumerate(lengths.tolist())
        if partitions[episode] == "P2"
        for start in range(max(0, int(length) - maximum_horizon))
        if (episode, start) not in excluded
    ]
    ranked: list[tuple[str, int, int]] = []
    for episode, start in eligible:
        digest = hashlib.sha256(
            f"{spec.SELECTION_SALT}\0{task}\0{episode}\0{start}".encode("utf-8")
        ).hexdigest()
        ranked.append((digest, episode, start))
    ranked.sort()
    if len(ranked) < spec.BASE_STARTS:
        raise RuntimeError("E18 P2 has too few fresh H150-compatible starts")
    return (
        [
            (episode, start, digest)
            for digest, episode, start in ranked[: spec.BASE_STARTS]
        ],
        len(eligible),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--old-queries", type=Path, required=True)
    parser.add_argument("--old-provenance", type=Path, required=True)
    parser.add_argument("--e17-audit", type=Path, required=True)
    parser.add_argument("--input-audit", type=Path, required=True)
    parser.add_argument("--input-audit-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.dataset,
        args.partition_manifest,
        args.old_queries,
        args.old_provenance,
        args.e17_audit,
        args.input_audit,
        args.protocol,
        args.source_manifest,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing existing E18 P2 manifest artifacts")
    task_spec = e15.TASK_SPEC[args.task]
    old_provenance = json.loads(args.old_provenance.read_text(encoding="utf-8"))
    if (
        sha256_file(args.dataset) != task_spec["dataset_sha256"]
        or sha256_file(args.partition_manifest)
        != task_spec["partition_manifest_sha256"]
        or sha256_file(args.old_queries) != task_spec["p2_queries_sha256"]
        or sha256_file(args.old_provenance) != task_spec["p2_manifest_sha256"]
        or old_provenance.get("task") != args.task
        or old_provenance.get("partition") != "P2"
        or sha256_file(args.protocol) != spec.PROTOCOL_SHA256
    ):
        raise RuntimeError("E18 P2 manifest input identity differs")
    verify_e17_audit(args.e17_audit)
    if sha256_file(args.input_audit) != args.input_audit_sha256:
        raise RuntimeError("E18 input-audit hash differs")
    input_audit = json.loads(args.input_audit.read_text(encoding="utf-8"))
    if (
        input_audit.get("status") != "passed"
        or input_audit.get("kind") != "gdp_cem_e18_nonmetric_input_audit"
        or input_audit.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or input_audit.get("e17_decision_preserved")
        != "stop_transition_adapter_preflight_failed"
        or input_audit.get("e17_used_as_authorization") is not False
        or input_audit.get("p2_outcomes_read") is not False
        or input_audit.get("d5_read") is not False
    ):
        raise RuntimeError("E18 input-audit content differs")
    partitions = read_partitions(args.partition_manifest)
    excluded = read_old_pairs(args.old_queries)
    if len(excluded) != e15.GATE_C_BASE_STARTS:
        raise RuntimeError("E18 old P2 exclusion cardinality differs")
    with h5py.File(args.dataset, "r") as handle:
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
    if len(offsets) != len(lengths) or set(partitions) != set(range(len(lengths))):
        raise RuntimeError("E18 P2 dataset and partition episodes differ")
    selected, eligible_count = select_base_starts(
        lengths, partitions, task=args.task, excluded=excluded
    )
    if any((episode, start) in excluded for episode, start, _ in selected):
        raise RuntimeError("E18 selected a previously named P2 start")
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
            writer = csv.DictWriter(
                stream, fieldnames=fields, delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            index = 0
            for horizon in spec.HORIZONS:
                for base_index, (episode, start, digest) in enumerate(selected):
                    writer.writerow(
                        {
                            "eval_index": index,
                            "base_index": base_index,
                            "episode_id": episode,
                            "start_step": start,
                            "goal_horizon": horizon,
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
        "kind": "gdp_cem_e18_fresh_shared_start_p2_manifest",
        "analysis_role": "P2_exploratory_continuation_development",
        "task": args.task,
        "selection_salt": spec.SELECTION_SALT,
        "base_start_count": spec.BASE_STARTS,
        "horizons": list(spec.HORIZONS),
        "rows_per_horizon": spec.BASE_STARTS,
        "total_rows": spec.BASE_STARTS * len(spec.HORIZONS),
        "maximum_horizon_compatible_eligible_count_after_exclusion": eligible_count,
        "same_episode_start_pairs_across_horizons": True,
        "partition": "P2",
        "excluded_old_pair_count": len(excluded),
        "excluded_old_queries_sha256": sha256_file(args.old_queries),
        "excluded_old_provenance_sha256": sha256_file(args.old_provenance),
        "dataset_sha256": sha256_file(args.dataset),
        "partition_manifest_sha256": sha256_file(args.partition_manifest),
        "e17_audit_sha256": sha256_file(args.e17_audit),
        "input_audit_sha256": args.input_audit_sha256,
        "e17_decision_preserved": "stop_transition_adapter_preflight_failed",
        "e17_used_as_authorization": False,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "output_tsv_sha256": sha256_file(args.output_tsv),
        "p2_outcomes_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_json, record)


if __name__ == "__main__":
    main()
