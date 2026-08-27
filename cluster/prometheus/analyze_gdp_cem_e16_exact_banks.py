#!/usr/bin/env python3
"""Aggregate completed E16 exact-bank diagnostics task first."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e15_specs as e15
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


def verify_result(directory: Path, *, task: str, source_sha: str) -> dict[str, Any]:
    summary_path = directory / "summary.json"
    metrics_path = directory / "metrics.h5"
    checksum_path = directory / "sha256.txt"
    if not all(path.is_file() for path in (summary_path, metrics_path, checksum_path)):
        raise FileNotFoundError(f"incomplete E16 exact-bank result: {directory}")
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
        or summary.get("kind")
        != "gdp_cem_e16_exact_e15_bank_ranking_diagnostic"
        or summary.get("task") != task
        or int(summary.get("row_count", -1)) != e15.VALIDATION_ROWS
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_sha
        or summary.get("metrics_h5_sha256") != sha256_file(metrics_path)
        or summary.get("exact_e15_replay", {}).get("passed") is not True
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"invalid E16 exact-bank result: {directory}")
    return summary


def summarize_cell(metrics: dict[str, np.ndarray], rows: np.ndarray) -> dict[str, float]:
    value: dict[str, float] = {
        "queries": float(len(rows)),
        "pearson_mean": float(metrics["pearson_far_vs_local"][rows].mean()),
        "pearson_median": float(np.median(metrics["pearson_far_vs_local"][rows])),
        "spearman_mean": float(metrics["spearman_far_vs_local"][rows].mean()),
        "spearman_median": float(np.median(metrics["spearman_far_vs_local"][rows])),
        "local_oracle_far_rank_mean": float(
            metrics["local_oracle_far_rank"][rows].mean()
        ),
        "local_oracle_far_rank_median": float(
            np.median(metrics["local_oracle_far_rank"][rows])
        ),
        "local_oracle_far_rank_q90": float(
            np.quantile(metrics["local_oracle_far_rank"][rows], 0.90)
        ),
        "standard_selected_local_cost": float(
            metrics["standard_selected_local_cost"][rows].mean()
        ),
        "mixed_selected_local_cost": float(
            metrics["mixed_selected_local_cost"][rows].mean()
        ),
        "standard_selected_far_cost": float(
            metrics["standard_selected_far_cost"][rows].mean()
        ),
        "mixed_selected_far_cost": float(
            metrics["mixed_selected_far_cost"][rows].mean()
        ),
        "standard_oracle_action_mse": float(
            metrics["standard_oracle_action_mse"][rows].mean()
        ),
        "mixed_oracle_action_mse": float(
            metrics["mixed_oracle_action_mse"][rows].mean()
        ),
    }
    value["mixed_minus_standard_selected_local_cost"] = (
        value["mixed_selected_local_cost"] - value["standard_selected_local_cost"]
    )
    value["mixed_minus_standard_oracle_action_mse"] = (
        value["mixed_oracle_action_mse"] - value["standard_oracle_action_mse"]
    )
    for count in spec.TOP_K:
        value[f"top_{count}_oracle_recall"] = float(
            metrics[f"top_{count}_contains_local_oracle"][rows].mean()
        )
        value[f"top_{count}_local_cost"] = float(
            metrics[f"top_{count}_local_cost"][rows].mean()
        )
        value[f"top_{count}_local_regret"] = float(
            metrics[f"top_{count}_local_regret"][rows].mean()
        )
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(args.source_manifest_sha256) != 64:
        raise ValueError("invalid E16 source-manifest hash")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E16 analyzer protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E16 Stage-A analysis output")

    table: list[dict[str, Any]] = []
    inputs: dict[str, Any] = {}
    for task in spec.TASKS:
        directory = args.input_root / task / "vad" / f"seed-{spec.DIAGNOSTIC_MODEL_SEED}"
        summary = verify_result(
            directory, task=task, source_sha=args.source_manifest_sha256
        )
        inputs[task] = {
            "directory": str(directory),
            "summary_sha256": sha256_file(directory / "summary.json"),
            "metrics_sha256": sha256_file(directory / "metrics.h5"),
            "reference_replay": summary["exact_e15_replay"],
        }
        with h5py.File(directory / "metrics.h5", "r") as handle:
            delta = np.asarray(handle["delta"][:], dtype=np.int64)
            tau = np.asarray(handle["tau"][:], dtype=np.int64)
            metrics = {
                name: np.asarray(handle[f"metrics/{name}"][:], dtype=np.float64)
                for name in handle["metrics"]
            }
        for delta_value, tau_value in e15.DELTA_TAU_PAIRS:
            rows = np.flatnonzero((delta == delta_value) & (tau == tau_value))
            if len(rows) != e15.VALIDATION_ROWS_PER_CELL:
                raise RuntimeError("E16 Stage-A cell size differs")
            table.append(
                {
                    "task": task,
                    "delta": delta_value,
                    "tau": tau_value,
                    **summarize_cell(metrics, rows),
                }
            )
        all_rows = np.arange(len(delta))
        table.append(
            {
                "task": task,
                "delta": "all",
                "tau": "all",
                **summarize_cell(metrics, all_rows),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    table_path = args.output_dir / "task-first.tsv"
    fields = list(table[0])
    with table_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(table)
    task_aggregate = {
        row["task"]: row for row in table if row["delta"] == "all"
    }
    audit = {
        "status": "ok",
        "kind": "gdp_cem_e16_exact_bank_stage_a_audit",
        "analysis_role": "outcome_informed_P1_validation_diagnostic",
        "exact_e15_replay_all_tasks_passed": all(
            value["reference_replay"]["passed"] for value in inputs.values()
        ),
        "inputs": inputs,
        "task_aggregate": task_aggregate,
        "task_first_rows": len(table),
        "task_first_tsv": str(table_path),
        "task_first_tsv_sha256": sha256_file(table_path),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": args.source_manifest_sha256,
        "stage_b_authorized": True,
        "stage_c_requires_adapter_gate_and_stage_b_technical_success": True,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    audit_path = args.output_dir / "STAGE-A-AUDIT.json"
    atomic_json(audit_path, audit)
    (args.output_dir / "sha256.txt").write_text(
        f"{sha256_file(audit_path)}  STAGE-A-AUDIT.json\n"
        f"{sha256_file(table_path)}  task-first.tsv\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
