#!/usr/bin/env python3
"""Audit whether the P2 M2 penalty could actually alter CEM candidate order."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np


WEIGHTS = (0.25, 0.5, 1.0, 2.0, 4.0)
WEIGHT_DIR = {0.25: "0.25", 0.5: "0.5", 1.0: "1.0", 2.0: "2.0", 4.0: "4.0"}
SEEDS = (20260728, 20260729, 20260730)
COMPARE_DATASETS = (
    "high_plan_subgoal_latent",
    "step_current_latent",
    "step_subgoal_latent",
    "final_state",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def analyze_environment(
    name: str,
    calibration_dir: Path,
    grid_root: Path,
    selection_dir: Path,
) -> dict[str, Any]:
    calibration_manifest_path = calibration_dir / "manifest.json"
    calibration_h5_path = calibration_dir / "audit-and-calibrators.h5"
    selection_manifest_path = selection_dir / "manifest.json"
    selection_h5_path = selection_dir / "selection.h5"
    calibration_manifest = json.loads(calibration_manifest_path.read_text(encoding="utf-8"))
    selection_manifest = json.loads(selection_manifest_path.read_text(encoding="utf-8"))
    if sha256_file(calibration_h5_path) != calibration_manifest["output_h5_sha256"]:
        raise RuntimeError(f"{name} calibration HDF5 hash mismatch")
    if sha256_file(selection_h5_path) != selection_manifest["output_h5_sha256"]:
        raise RuntimeError(f"{name} selection HDF5 hash mismatch")

    m2_calibration = calibration_manifest["calibration"]["methods"]["M2"]
    slopes = np.asarray(
        [record["platt"]["raw_score_slope"] for record in m2_calibration["seeds"]],
        dtype=np.float64,
    )
    intercepts = np.asarray(
        [record["platt"]["raw_score_intercept"] for record in m2_calibration["seeds"]],
        dtype=np.float64,
    )
    with h5py.File(calibration_h5_path, "r") as handle:
        method_index = int(handle["calibrators/M2"].attrs["method_index"])
        h5_slopes = np.asarray(
            [
                handle[f"calibrators/M2/seed-{seed}"].attrs["platt_raw_score_slope"]
                for seed in SEEDS
            ],
            dtype=np.float64,
        )
        h5_intercepts = np.asarray(
            [
                handle[f"calibrators/M2/seed-{seed}"].attrs["platt_raw_score_intercept"]
                for seed in SEEDS
            ],
            dtype=np.float64,
        )
        calibration_probability = np.asarray(
            handle["platt_failure_probability"][method_index], dtype=np.float64
        )
    if not np.array_equal(slopes, h5_slopes) or not np.array_equal(intercepts, h5_intercepts):
        raise RuntimeError(f"{name} calibration manifest/HDF5 disagreement")

    task_records = {
        (float(record["weight"]), int(record["pool_index"])): record
        for record in selection_manifest["task_records"]
        if record["method"] == "M2"
    }
    if set(task_records) != {(weight, pool) for weight in WEIGHTS for pool in range(12)}:
        raise RuntimeError(f"{name} incomplete M2 grid records")

    task_arrays: dict[tuple[float, int], dict[str, np.ndarray]] = {}
    spans: list[float] = []
    successes: dict[float, list[int]] = {weight: [] for weight in WEIGHTS}
    task_hashes: list[dict[str, Any]] = []
    for weight in WEIGHTS:
        for pool in range(12):
            record = task_records[(weight, pool)]
            task_id = int(record["array_task_id"])
            directory = (
                grid_root
                / "method-M2"
                / f"weight-{WEIGHT_DIR[weight]}"
                / f"pool-{pool:02d}-task-{task_id}"
            )
            manifest_path = directory / "manifest.json"
            h5_path = directory / "result.h5"
            if sha256_file(manifest_path) != record["manifest_sha256"]:
                raise RuntimeError(f"{name} task manifest hash mismatch: {weight}/{pool}")
            if sha256_file(h5_path) != record["result_h5_sha256"]:
                raise RuntimeError(f"{name} task HDF5 hash mismatch: {weight}/{pool}")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                manifest["status"] != "ok"
                or manifest["method"] != "M2"
                or float(manifest["weight"]) != weight
                or int(manifest["query"]["pool_index"]) != pool
            ):
                raise RuntimeError(f"{name} task identity mismatch: {weight}/{pool}")
            if bool(manifest["episode_success"]):
                successes[weight].append(pool)
            for summary in manifest["cost"]["final_iteration_summaries"]:
                spans.append(
                    float(summary["failure_probability_max"])
                    - float(summary["failure_probability_min"])
                )
            with h5py.File(h5_path, "r") as handle:
                task_arrays[(weight, pool)] = {
                    dataset: np.asarray(handle[dataset][:]) for dataset in COMPARE_DATASETS
                }
            task_hashes.append(
                {
                    "weight": weight,
                    "pool": pool,
                    "manifest_sha256": record["manifest_sha256"],
                    "result_h5_sha256": record["result_h5_sha256"],
                }
            )

    comparisons: dict[str, dict[str, Any]] = {}
    for dataset in COMPARE_DATASETS:
        exact_count = 0
        comparison_count = 0
        max_abs = 0.0
        shape_mismatch_count = 0
        for pool in range(12):
            reference = task_arrays[(WEIGHTS[0], pool)][dataset]
            for weight in WEIGHTS[1:]:
                current = task_arrays[(weight, pool)][dataset]
                comparison_count += 1
                if current.shape != reference.shape:
                    shape_mismatch_count += 1
                    continue
                if np.array_equal(current, reference):
                    exact_count += 1
                if current.size:
                    max_abs = max(max_abs, float(np.max(np.abs(current - reference))))
        comparisons[dataset] = {
            "comparison_count": comparison_count,
            "exact_count": exact_count,
            "shape_mismatch_count": shape_mismatch_count,
            "maximum_absolute_difference": max_abs,
        }

    span_array = np.asarray(spans, dtype=np.float64)
    success_vectors = [tuple(successes[weight]) for weight in WEIGHTS]
    constant_calibrator = bool(np.all(slopes == 0.0))
    outcomes_identical = len(set(success_vectors)) == 1
    interpretations = {
        "constant_platt_calibrator": constant_calibrator,
        "candidate_constant_penalty_by_construction": constant_calibrator,
        "recorded_final_populations_constant": bool(np.all(span_array <= 1.0e-7)),
        "weight_outcomes_identical": outcomes_identical,
        "m2_weight_grid_is_non_interventional": bool(constant_calibrator and outcomes_identical),
    }
    return {
        "inputs": {
            "calibration_manifest_sha256": sha256_file(calibration_manifest_path),
            "calibration_h5_sha256": sha256_file(calibration_h5_path),
            "selection_manifest_sha256": sha256_file(selection_manifest_path),
            "selection_h5_sha256": sha256_file(selection_h5_path),
            "grid_root": str(grid_root),
        },
        "platt": {
            "raw_score_slopes": slopes.tolist(),
            "raw_score_intercepts": intercepts.tolist(),
            "calibration_probability_min": float(calibration_probability.min()),
            "calibration_probability_max": float(calibration_probability.max()),
            "calibration_probability_unique_count": int(np.unique(calibration_probability).size),
        },
        "online_recorded_final_population_probability_span": {
            "count": int(span_array.size),
            "minimum": float(span_array.min()),
            "median": float(np.median(span_array)),
            "p95": float(np.quantile(span_array, 0.95)),
            "maximum": float(span_array.max()),
            "count_at_most_1e_7": int(np.count_nonzero(span_array <= 1.0e-7)),
        },
        "successful_pool_indices_by_weight": {str(weight): successes[weight] for weight in WEIGHTS},
        "cross_weight_trace_comparisons_against_weight_0_25": comparisons,
        "interpretations_under_prefrozen_rules": interpretations,
        "task_hash_records": task_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for environment in ("pusht", "tworoom"):
        parser.add_argument(f"--{environment}-calibration-dir", type=Path, required=True)
        parser.add_argument(f"--{environment}-grid-root", type=Path, required=True)
        parser.add_argument(f"--{environment}-selection-dir", type=Path, required=True)
    parser.add_argument("--online-implementation", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        raise SystemExit("refusing to overwrite M2 intervention audit")
    started = time.time()
    result = {
        "status": "ok",
        "classification": "m2_p2_calibration_and_intervention_audit",
        "partition_scope": "P2-development-only",
        "reporting_boundary": "exploratory; no P3/P4 artifact was read or changed",
        "spec": str(args.spec),
        "spec_sha256": sha256_file(args.spec),
        "online_implementation": str(args.online_implementation),
        "online_implementation_sha256": sha256_file(args.online_implementation),
        "environments": {
            "pusht": analyze_environment(
                "pusht", args.pusht_calibration_dir, args.pusht_grid_root, args.pusht_selection_dir
            ),
            "tworoom": analyze_environment(
                "tworoom",
                args.tworoom_calibration_dir,
                args.tworoom_grid_root,
                args.tworoom_selection_dir,
            ),
        },
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

