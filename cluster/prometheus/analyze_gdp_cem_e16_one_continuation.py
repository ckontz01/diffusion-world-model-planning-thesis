#!/usr/bin/env python3
"""Aggregate the completed E16 one-continuation diagnostic task first."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e16_specs as spec
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


def verify_result(directory: Path, *, task: str, source_sha: str) -> None:
    summary_path = directory / "summary.json"
    metrics_path = directory / "metrics.h5"
    checksum_path = directory / "sha256.txt"
    if not all(path.is_file() for path in (summary_path, metrics_path, checksum_path)):
        raise FileNotFoundError(f"incomplete E16 Stage-B result: {directory}")
    records: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        records[name.lstrip("*")] = digest
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        records != {
            "metrics.h5": sha256_file(metrics_path),
            "summary.json": sha256_file(summary_path),
        }
        or summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e16_one_continuation_diagnostic"
        or summary.get("task") != task
        or int(summary.get("rows", -1))
        != len(spec.DIAGNOSTIC_DELTAS) * spec.DIAGNOSTIC_ROWS_PER_CELL
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_sha
        or summary.get("metrics_h5_sha256") != sha256_file(metrics_path)
        or summary.get("d5_read") is not False
    ):
        raise RuntimeError(f"invalid E16 Stage-B result: {directory}")


def summarize(metrics: dict[str, np.ndarray], rows: np.ndarray) -> dict[str, float]:
    greedy_local = metrics["greedy_first_local_cost"][rows]
    continuation_local = metrics["continuation_first_local_cost"][rows]
    greedy_final = metrics["greedy_branch_final_far_cost"][rows]
    continuation_final = metrics["continuation_selected_final_far_cost"][rows]
    return {
        "queries": float(len(rows)),
        "selection_changed_fraction": float(metrics["selection_changed"][rows].mean()),
        "greedy_first_local_cost": float(greedy_local.mean()),
        "continuation_first_local_cost": float(continuation_local.mean()),
        "continuation_minus_greedy_first_local_cost": float(
            (continuation_local - greedy_local).mean()
        ),
        "continuation_first_local_cost_win_fraction": float(
            (continuation_local < greedy_local).mean()
        ),
        "continuation_selected_immediate_far_rank_mean": float(
            metrics["continuation_selected_immediate_far_rank"][rows].mean()
        ),
        "continuation_selected_immediate_far_rank_median": float(
            np.median(metrics["continuation_selected_immediate_far_rank"][rows])
        ),
        "continuation_selected_immediate_local_rank_mean": float(
            metrics["continuation_selected_immediate_local_rank"][rows].mean()
        ),
        "continuation_selected_immediate_local_rank_median": float(
            np.median(metrics["continuation_selected_immediate_local_rank"][rows])
        ),
        "greedy_branch_final_far_cost": float(greedy_final.mean()),
        "continuation_selected_final_far_cost": float(continuation_final.mean()),
        "continuation_minus_greedy_final_far_cost": float(
            (continuation_final - greedy_final).mean()
        ),
        "continuation_final_far_cost_win_fraction": float(
            (continuation_final < greedy_final).mean()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(args.source_manifest_sha256) != 64:
        raise ValueError("invalid E16 Stage-B source hash")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E16 Stage-B analyzer protocol differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E16 Stage-B analysis")
    table: list[dict[str, Any]] = []
    inputs: dict[str, Any] = {}
    for task in spec.TASKS:
        directory = args.input_root / task
        verify_result(directory, task=task, source_sha=args.source_manifest_sha256)
        inputs[task] = {
            "summary_sha256": sha256_file(directory / "summary.json"),
            "metrics_sha256": sha256_file(directory / "metrics.h5"),
        }
        with h5py.File(directory / "metrics.h5", "r") as handle:
            delta = np.asarray(handle["delta"][:], dtype=np.int64)
            metrics = {
                name: np.asarray(handle[f"metrics/{name}"][:], dtype=np.float64)
                for name in handle["metrics"]
            }
        for delta_value in spec.DIAGNOSTIC_DELTAS:
            rows = np.flatnonzero(delta == delta_value)
            if len(rows) != spec.DIAGNOSTIC_ROWS_PER_CELL:
                raise RuntimeError("E16 Stage-B cell size differs")
            table.append(
                {"task": task, "delta": delta_value, **summarize(metrics, rows)}
            )
        table.append(
            {
                "task": task,
                "delta": "all",
                **summarize(metrics, np.arange(len(delta))),
            }
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    table_path = args.output_dir / "task-first.tsv"
    with table_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(table)
    task_aggregate = {
        row["task"]: row for row in table if row["delta"] == "all"
    }
    audit = {
        "status": "ok",
        "kind": "gdp_cem_e16_one_continuation_stage_b_audit",
        "analysis_role": "outcome_informed_P1_validation_diagnostic",
        "inputs": inputs,
        "task_aggregate": task_aggregate,
        "task_first_rows": len(table),
        "task_first_tsv": str(table_path),
        "task_first_tsv_sha256": sha256_file(table_path),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": args.source_manifest_sha256,
        "stage_c_authorized": True,
        "authorization_basis": (
            "both frozen adapter gates and Stages A/B completed without a "
            "technical or exact-replay failure; no Stage-B performance threshold"
        ),
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    audit_path = args.output_dir / "STAGE-B-AUDIT.json"
    atomic_json(audit_path, audit)
    (args.output_dir / "sha256.txt").write_text(
        f"{sha256_file(audit_path)}  STAGE-B-AUDIT.json\n"
        f"{sha256_file(table_path)}  task-first.tsv\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()

