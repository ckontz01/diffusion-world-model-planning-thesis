#!/usr/bin/env python3
"""Apply the frozen E14 Gate-B rules to complete P1-validation results."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import sha256_file
from evaluate_gdp_cem_e14_offline import (
    CANDIDATE_COUNT,
    TRAINING_SOURCE_MANIFEST_SHA256,
)


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


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != 32 or [int(row["array_id"]) for row in rows] != list(range(32)):
        raise RuntimeError("E14 Gate-B manifest differs")
    if len({(row["task"], row["condition"], row["seed"]) for row in rows}) != 32:
        raise RuntimeError("E14 Gate-B manifest is not bijective")
    return rows


def equal_cell(record: dict[str, Any], metric: str) -> float:
    return float(record["aggregates"]["equal_cell_mean"][metric])


def per_tau(record: dict[str, Any], tau: int, metric: str) -> float:
    return float(record["aggregates"]["per_tau"][str(tau)][metric])


def gate_endpoint(
    records: dict[tuple[str, str, int], dict[str, Any]], endpoint: str
) -> dict[str, Any]:
    true_condition = f"{endpoint}_true"
    gaussian_condition = f"{endpoint}_gaussian"
    shuffled_condition = f"{endpoint}_shuffled_goal"
    unconditional_condition = f"{endpoint}_unconditional"
    relevant = [
        record
        for (task, condition, seed), record in records.items()
        if condition.startswith(f"{endpoint}_")
    ]
    bank_validity = all(
        record["bank_validity"]["all_finite"] is True
        and int(record["bank_validity"]["minimum_unique_candidates"]) >= 285
        and float(record["bank_validity"]["maximum_boundary_fraction"]) <= 0.25
        for record in relevant
    )
    comparisons: dict[str, Any] = {}
    matched_all = True
    direction_all = True
    cvd_all = True
    for seed in spec.MODEL_SEEDS:
        true_action = np.mean(
            [
                equal_cell(records[(task, true_condition, seed)], "oracle_action_mse")
                for task in spec.TASKS
            ]
        )
        gaussian_action = np.mean(
            [
                equal_cell(records[(task, gaussian_condition, seed)], "oracle_action_mse")
                for task in spec.TASKS
            ]
        )
        true_cost = np.mean(
            [
                equal_cell(
                    records[(task, true_condition, seed)],
                    "true_local_terminal_cost",
                )
                for task in spec.TASKS
            ]
        )
        gaussian_cost = np.mean(
            [
                equal_cell(
                    records[(task, gaussian_condition, seed)],
                    "true_local_terminal_cost",
                )
                for task in spec.TASKS
            ]
        )
        matched = true_action < gaussian_action and true_cost < gaussian_cost
        matched_all &= matched
        task_directions: dict[str, Any] = {}
        for task in spec.TASKS:
            winning_tau = []
            for tau in spec.TAU_VALUES:
                if (
                    per_tau(
                        records[(task, true_condition, seed)],
                        tau,
                        "oracle_action_mse",
                    )
                    < per_tau(
                        records[(task, gaussian_condition, seed)],
                        tau,
                        "oracle_action_mse",
                    )
                    and per_tau(
                        records[(task, true_condition, seed)],
                        tau,
                        "true_local_terminal_cost",
                    )
                    < per_tau(
                        records[(task, gaussian_condition, seed)],
                        tau,
                        "true_local_terminal_cost",
                    )
                ):
                    winning_tau.append(tau)
            task_pass = len(winning_tau) >= 2
            direction_all &= task_pass
            task_directions[task] = {
                "winning_tau": winning_tau,
                "pass": task_pass,
            }
        cvd_record: dict[str, Any] | None = None
        if endpoint == "cvd":
            true_local = np.mean(
                [
                    equal_cell(
                        records[(task, true_condition, seed)],
                        "oracle_generated_local_mse",
                    )
                    for task in spec.TASKS
                ]
            )
            gaussian_local = np.mean(
                [
                    equal_cell(
                        records[(task, gaussian_condition, seed)],
                        "oracle_generated_local_mse",
                    )
                    for task in spec.TASKS
                ]
            )
            true_consistency = np.mean(
                [
                    equal_cell(
                        records[(task, true_condition, seed)],
                        "terminal_consistency",
                    )
                    for task in spec.TASKS
                ]
            )
            gaussian_consistency = np.mean(
                [
                    equal_cell(
                        records[(task, gaussian_condition, seed)],
                        "terminal_consistency",
                    )
                    for task in spec.TASKS
                ]
            )
            cvd_pass = (
                true_local < gaussian_local
                and true_consistency < gaussian_consistency
            )
            cvd_all &= cvd_pass
            cvd_record = {
                "true_local_error": true_local,
                "gaussian_local_error": gaussian_local,
                "true_terminal_consistency": true_consistency,
                "gaussian_terminal_consistency": gaussian_consistency,
                "pass": cvd_pass,
            }
        comparisons[str(seed)] = {
            "true_oracle_action_mse": true_action,
            "gaussian_oracle_action_mse": gaussian_action,
            "true_local_terminal_cost": true_cost,
            "gaussian_local_terminal_cost": gaussian_cost,
            "matched_equal_task_pass": matched,
            "per_task_tau_direction": task_directions,
            "cvd_additional": cvd_record,
        }

    control_comparisons: dict[str, Any] = {}
    controls_pass = True
    for control_name, condition in (
        ("shuffled_goal", shuffled_condition),
        ("unconditional", unconditional_condition),
    ):
        true_action = np.mean(
            [
                equal_cell(
                    records[(task, true_condition, spec.DIAGNOSTIC_SEED)],
                    "oracle_action_mse",
                )
                for task in spec.TASKS
            ]
        )
        control_action = np.mean(
            [
                equal_cell(
                    records[(task, condition, spec.DIAGNOSTIC_SEED)],
                    "oracle_action_mse",
                )
                for task in spec.TASKS
            ]
        )
        true_cost = np.mean(
            [
                equal_cell(
                    records[(task, true_condition, spec.DIAGNOSTIC_SEED)],
                    "true_local_terminal_cost",
                )
                for task in spec.TASKS
            ]
        )
        control_cost = np.mean(
            [
                equal_cell(
                    records[(task, condition, spec.DIAGNOSTIC_SEED)],
                    "true_local_terminal_cost",
                )
                for task in spec.TASKS
            ]
        )
        passed = true_action < control_action and true_cost < control_cost
        controls_pass &= passed
        control_comparisons[control_name] = {
            "true_oracle_action_mse": true_action,
            "control_oracle_action_mse": control_action,
            "true_local_terminal_cost": true_cost,
            "control_local_terminal_cost": control_cost,
            "pass": passed,
        }
    gates = {
        "all_banks_finite_unique_and_within_bounds": bank_validity,
        "diffusion_beats_matched_gaussian_each_seed": matched_all,
        "direction_holds_each_task_two_of_three_durations_each_seed": direction_all,
        "true_beats_shuffled_and_unconditional": controls_pass,
        "cvd_beats_gaussian_on_local_error_and_consistency_each_seed": (
            cvd_all if endpoint == "cvd" else True
        ),
    }
    return {
        "endpoint": endpoint,
        "eligible_for_gate_c": all(gates.values()),
        "gates": gates,
        "minimum_unique_candidates": min(
            int(record["bank_validity"]["minimum_unique_candidates"])
            for record in relevant
        ),
        "maximum_boundary_fraction": max(
            float(record["bank_validity"]["maximum_boundary_fraction"])
            for record in relevant
        ),
        "matched_comparisons": comparisons,
        "control_comparisons": control_comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--endpoint-manifest", type=Path, required=True)
    parser.add_argument("--endpoint-manifest-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.evaluation_root,
        args.endpoint_manifest,
        args.protocol,
        args.source_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E14 Gate-B analysis output")
    if sha256_file(args.endpoint_manifest) != args.endpoint_manifest_sha256:
        raise RuntimeError("E14 Gate-B manifest hash differs")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E14 Gate-B protocol hash differs")
    source_hash = sha256_file(args.source_manifest)
    rows = read_manifest(args.endpoint_manifest)
    records: dict[tuple[str, str, int], dict[str, Any]] = {}
    artifacts: dict[str, Any] = {}
    validation_hashes: dict[str, set[str]] = {task: set() for task in spec.TASKS}
    for row in rows:
        task = row["task"]
        condition = row["condition"]
        seed = int(row["seed"])
        summary_path = (
            args.evaluation_root
            / task
            / condition
            / f"seed-{seed}"
            / "summary.json"
        )
        if not summary_path.is_file():
            raise FileNotFoundError(summary_path)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if (
            summary.get("status") != "ok"
            or summary.get("kind")
            != "gdp_cem_e14_full_p1_validation_endpoint_evaluation"
            or summary.get("mode") != "full"
            or summary.get("analysis_role")
            != "P1_validation_only_Gate_B_development"
            or summary.get("task") != task
            or summary.get("condition") != condition
            or int(summary.get("seed", -1)) != seed
            or int(summary.get("row_count", -1)) != spec.VALIDATION_ROWS
            or int(summary.get("candidate_count", -1)) != CANDIDATE_COUNT
            or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
            or summary.get("training_source_manifest_sha256")
            != TRAINING_SOURCE_MANIFEST_SHA256
            or summary.get("source_manifest_sha256") != source_hash
            or summary.get("d3_metric_read") is not False
            or summary.get("d4_metric_read") is not False
            or summary.get("d5_read") is not False
            or summary.get("protected_p3_p4_c1_i1_read") is not False
            or summary.get("claim_allowed") is not False
        ):
            raise RuntimeError(f"E14 Gate-B summary identity differs: {summary_path}")
        metrics_path = Path(summary.get("metrics_h5", ""))
        if not metrics_path.is_file() or sha256_file(metrics_path) != summary.get(
            "metrics_h5_sha256"
        ):
            raise RuntimeError("E14 Gate-B metrics hash differs")
        with h5py.File(metrics_path, "r") as handle:
            if (
                handle.attrs.get("task") != task
                or handle.attrs.get("condition") != condition
                or int(handle.attrs.get("seed", -1)) != seed
                or handle.attrs.get("protocol_sha256") != spec.PROTOCOL_SHA256
                or len(handle["cache_row"]) != spec.VALIDATION_ROWS
                or any(
                    not np.isfinite(np.asarray(dataset[:])).all()
                    for dataset in handle["metrics"].values()
                )
            ):
                raise RuntimeError("E14 Gate-B metrics content differs")
        key = (task, condition, seed)
        records[key] = summary
        validation_hashes[task].add(summary["validation_rows_sha256"])
        artifacts["|".join(map(str, key))] = {
            "summary": str(summary_path),
            "summary_sha256": sha256_file(summary_path),
            "metrics_h5": str(metrics_path),
            "metrics_h5_sha256": summary["metrics_h5_sha256"],
        }
    if any(len(value) != 1 for value in validation_hashes.values()):
        raise RuntimeError("E14 Gate-B validation rows differ across arms")
    endpoint_results = {
        endpoint: gate_endpoint(records, endpoint) for endpoint in ("vad", "cvd")
    }
    eligible = [
        endpoint
        for endpoint, result in endpoint_results.items()
        if result["eligible_for_gate_c"]
    ]
    decision = (
        "authorize_gate_c_p2_development_for_eligible_endpoints"
        if eligible
        else "stop_before_gate_c_no_diffusion_endpoint_passed_gate_b"
    )
    result = {
        "status": "ok",
        "kind": "gdp_cem_e14_gate_b_offline_analysis",
        "analysis_role": "P1_validation_only_Gate_B_development",
        "decision": decision,
        "eligible_endpoints": eligible,
        "endpoint_results": endpoint_results,
        "task_validation_rows_sha256": {
            task: next(iter(value)) for task, value in validation_hashes.items()
        },
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "endpoint_manifest": str(args.endpoint_manifest),
        "endpoint_manifest_sha256": args.endpoint_manifest_sha256,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest_sha256": TRAINING_SOURCE_MANIFEST_SHA256,
        "source_manifest_sha256": source_hash,
        "analyzer_source_sha256": sha256_file(Path(__file__)),
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output_dir / "GATE-B-AUDIT.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
