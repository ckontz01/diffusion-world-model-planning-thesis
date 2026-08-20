#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from score_and_select_p2_true_scorers import verify_inventory


METHODS = ("M1", "M2", "M3")
WEIGHTS = (0.25, 0.5, 1.0, 2.0, 4.0)
POOL_COUNT = 12


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def task_id(method_index: int, weight_index: int, pool_index: int) -> int:
    return method_index * len(WEIGHTS) * POOL_COUNT + weight_index * POOL_COUNT + pool_index


def task_directory(
    root: Path, method: str, weight: float, pool_index: int, array_task_id: int
) -> Path:
    return (
        root
        / f"method-{method}"
        / f"weight-{weight}"
        / f"pool-{pool_index:02d}-task-{array_task_id}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--array-job-id", type=int, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    args = parser.parse_args()
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite P2 closed-loop grid aggregate")
    if args.input_root.name != f"augmented-grid-job-{args.array_job_id}":
        raise RuntimeError("input root does not match the declared array job")
    environment = args.environment
    prefix = "tworoom_" if environment == "tworoom" else ""
    task_classification = f"{prefix}p2_augmented_closed_loop_weight_development"
    output_classification = f"{prefix}p2_augmented_closed_loop_weight_selection"
    if environment == "pusht":
        goal_offset = 75
        planner_budget = (150, 1200, 60, 10, 1200, 30, 150)
        cost_accounting = (1800, 30, 2_160_000)
    else:
        goal_offset = 25
        planner_budget = (50, 300, 20, 10, 300, 30, 10)
        cost_accounting = (200, 10, 60_000)
    eval_budget = planner_budget[0]
    started = time.time()

    success = np.empty((len(METHODS), len(WEIGHTS), POOL_COUNT), dtype=np.bool_)
    execution_seconds = np.empty_like(success, dtype=np.float64)
    scorer_seconds = np.empty_like(success, dtype=np.float64)
    peak_allocated = np.empty_like(success, dtype=np.int64)
    peak_reserved = np.empty_like(success, dtype=np.int64)
    episode_id = np.empty(POOL_COUNT, dtype=np.int64)
    source_row = np.empty(POOL_COUNT, dtype=np.int64)
    goal_row = np.empty(POOL_COUNT, dtype=np.int64)
    planner_seed = np.empty(POOL_COUNT, dtype=np.int64)
    expected_query: dict[int, tuple[int, int, int, int]] = {}
    task_records: list[dict[str, Any]] = []
    candidate_h5_sha: str | None = None
    candidate_manifest_sha: str | None = None
    calibration_h5_sha: str | None = None
    true_selection_h5_sha: str | None = None

    for method_index, method in enumerate(METHODS):
        for weight_index, weight in enumerate(WEIGHTS):
            for pool_index in range(POOL_COUNT):
                array_task_id = task_id(method_index, weight_index, pool_index)
                directory = task_directory(
                    args.input_root, method, weight, pool_index, array_task_id
                )
                inventory = verify_inventory(directory)
                expected_inventory = {"result.h5", "manifest.json", "provenance.txt"}
                if set(inventory) != expected_inventory:
                    raise RuntimeError(
                        f"unexpected task inventory for {array_task_id}: {sorted(inventory)}"
                    )
                manifest = json.loads(
                    (directory / "manifest.json").read_text(encoding="utf-8")
                )
                if manifest.get("status") != "ok" or manifest.get(
                    "classification"
                ) != task_classification:
                    raise RuntimeError(f"invalid grid task {array_task_id}")
                if (
                    manifest.get("partition") != "P2-development-only"
                    or manifest.get("environment", "pusht") != environment
                ):
                    raise RuntimeError("closed-loop task is not marked P2-only")
                if manifest["method"] != method or not math.isclose(
                    float(manifest["weight"]), weight, rel_tol=0.0, abs_tol=0.0
                ):
                    raise RuntimeError(f"method/weight mapping mismatch in task {array_task_id}")
                query = manifest["query"]
                if int(query["pool_index"]) != pool_index:
                    raise RuntimeError(f"pool mapping mismatch in task {array_task_id}")
                identity = (
                    int(query["episode_id"]),
                    int(query["source_global_row"]),
                    int(query["goal_global_row"]),
                    int(query["planner_seed_63bit"]),
                )
                if pool_index in expected_query and expected_query[pool_index] != identity:
                    raise RuntimeError(f"query matching failed for pool {pool_index}")
                expected_query.setdefault(pool_index, identity)
                episode_id[pool_index], source_row[pool_index], goal_row[pool_index], planner_seed[
                    pool_index
                ] = identity
                if int(query["goal_step"]) - int(query["source_step"]) != goal_offset:
                    raise RuntimeError("grid task has the wrong frozen goal offset")
                planner = manifest["planner"]
                if (
                    int(planner["eval_budget_primitive_steps"]),
                    int(planner["high"]["num_samples"]),
                    int(planner["high"]["iterations"]),
                    int(planner["high"]["topk"]),
                    int(planner["low"]["num_samples"]),
                    int(planner["low"]["iterations"]),
                    int(planner["low"]["topk"]),
                ) != planner_budget:
                    raise RuntimeError("grid task planner budget changed")
                if manifest["cost"]["nominal_equivalence"] != {
                    "max_abs": 0.0,
                    "shape": [1, 4],
                    "status": "ok",
                }:
                    raise RuntimeError("nominal-cost equivalence gate did not pass exactly")
                timing = manifest["cost"]["timing"]
                if (
                    int(timing["cost_calls"]) != cost_accounting[0]
                    or int(timing["completed_high_solves"]) != cost_accounting[1]
                    or int(timing["candidate_evaluations"]) != cost_accounting[2]
                ):
                    raise RuntimeError("grid task augmented-cost accounting changed")
                if int(manifest["diagnostics"]["step_count"]) != eval_budget:
                    raise RuntimeError("grid task did not complete its frozen step budget")
                if inventory["result.h5"] != manifest["output_h5_sha256"]:
                    raise RuntimeError("task HDF5 differs from its manifest")
                with h5py.File(directory / "result.h5", "r") as handle:
                    if handle.attrs["classification"] != (
                        task_classification
                    ):
                        raise RuntimeError("task HDF5 classification mismatch")
                    if str(handle.attrs["method"]) != method or float(
                        handle.attrs["weight"]
                    ) != weight:
                        raise RuntimeError("task HDF5 method/weight mismatch")
                    if bool(handle.attrs["episode_success"]) != bool(
                        manifest["episode_success"]
                    ):
                        raise RuntimeError("task HDF5/JSON success mismatch")
                    if handle.attrs.get("environment", "pusht") != environment:
                        raise RuntimeError("task HDF5 environment mismatch")
                    if handle["step_current_latent"].shape != (eval_budget, 192):
                        raise RuntimeError("task step-latent trace shape mismatch")

                current_candidate_h5 = manifest["inputs"]["candidate_h5_sha256"]
                current_candidate_manifest = manifest["inputs"][
                    "candidate_manifest_sha256"
                ]
                artifacts = manifest["cost"]["scorer_artifacts"]
                current_calibration = artifacts["calibration_h5_sha256"]
                current_true = artifacts["true_selection_h5_sha256"]
                candidate_h5_sha = candidate_h5_sha or current_candidate_h5
                candidate_manifest_sha = candidate_manifest_sha or current_candidate_manifest
                calibration_h5_sha = calibration_h5_sha or current_calibration
                true_selection_h5_sha = true_selection_h5_sha or current_true
                if (
                    current_candidate_h5 != candidate_h5_sha
                    or current_candidate_manifest != candidate_manifest_sha
                    or current_calibration != calibration_h5_sha
                    or current_true != true_selection_h5_sha
                ):
                    raise RuntimeError("grid tasks do not share frozen candidate/scorer artifacts")

                success[method_index, weight_index, pool_index] = bool(
                    manifest["episode_success"]
                )
                execution_seconds[method_index, weight_index, pool_index] = float(
                    manifest["runtime"]["execution_seconds"]
                )
                scorer_seconds[method_index, weight_index, pool_index] = float(
                    timing["scorer_ms"]
                ) / 1000.0
                peak_allocated[method_index, weight_index, pool_index] = int(
                    manifest["runtime"]["peak_gpu_allocated_bytes"]
                )
                peak_reserved[method_index, weight_index, pool_index] = int(
                    manifest["runtime"]["peak_gpu_reserved_bytes"]
                )
                task_records.append(
                    {
                        "array_task_id": array_task_id,
                        "method": method,
                        "weight": weight,
                        "pool_index": pool_index,
                        "episode_success": bool(manifest["episode_success"]),
                        "result_h5_sha256": manifest["output_h5_sha256"],
                        "manifest_sha256": inventory["manifest.json"],
                    }
                )

    success_count = success.sum(axis=2, dtype=np.int64)
    selected_index = np.empty(len(METHODS), dtype=np.int64)
    selected_weight = np.empty(len(METHODS), dtype=np.float64)
    selections: dict[str, Any] = {}
    for method_index, method in enumerate(METHODS):
        maximum = int(success_count[method_index].max())
        tied = np.flatnonzero(success_count[method_index] == maximum)
        chosen = int(tied[0])
        selected_index[method_index] = chosen
        selected_weight[method_index] = WEIGHTS[chosen]
        selections[method] = {
            "selected_weight": WEIGHTS[chosen],
            "selected_weight_index": chosen,
            "selected_success_count_of_12": maximum,
            "weight_records": [
                {
                    "weight": weight,
                    "success_count_of_12": int(success_count[method_index, index]),
                }
                for index, weight in enumerate(WEIGHTS)
            ],
        }

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = output_classification
            output.attrs["environment"] = environment
            output.attrs["partition"] = "P2-development-only"
            output.attrs["array_job_id"] = args.array_job_id
            output.create_dataset(
                "method", data=np.asarray(METHODS, dtype=h5py.string_dtype("utf-8"))
            )
            output.create_dataset("weight", data=np.asarray(WEIGHTS, dtype=np.float64))
            output.create_dataset("pool_index", data=np.arange(POOL_COUNT, dtype=np.int64))
            output.create_dataset("episode_id", data=episode_id)
            output.create_dataset("source_global_row", data=source_row)
            output.create_dataset("goal_global_row", data=goal_row)
            output.create_dataset("planner_seed", data=planner_seed)
            output.create_dataset("episode_success", data=success)
            output.create_dataset("success_count", data=success_count)
            output.create_dataset("selected_weight_index", data=selected_index)
            output.create_dataset("selected_weight", data=selected_weight)
            output.create_dataset("execution_seconds", data=execution_seconds)
            output.create_dataset("scorer_seconds", data=scorer_seconds)
            output.create_dataset("peak_gpu_allocated_bytes", data=peak_allocated)
            output.create_dataset("peak_gpu_reserved_bytes", data=peak_reserved)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_grid_aggregate_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": output_classification,
        "environment": environment,
        "partition": "P2-development-only",
        "reporting_rule": "selection artifact only; P2 counts are not final thesis results",
        "selection_rule": {
            "objective": f"largest released benchmark success count over the 12 shared D{goal_offset} queries",
            "tie_break": "smaller weight only",
            "weight_grid": list(WEIGHTS),
        },
        "query_count_per_weight": POOL_COUNT,
        "task_count": len(task_records),
        "selections": selections,
        "task_records": task_records,
        "matching_audit": {
            "query_identity_shared_across_all_methods_and_weights": True,
            "candidate_h5_sha256": candidate_h5_sha,
            "candidate_manifest_sha256": candidate_manifest_sha,
            "true_selection_h5_sha256": true_selection_h5_sha,
            "calibration_h5_sha256": calibration_h5_sha,
        },
        "runtime_summary": {
            method: {
                "mean_execution_seconds": float(execution_seconds[index].mean()),
                "mean_scorer_seconds": float(scorer_seconds[index].mean()),
                "maximum_peak_gpu_allocated_bytes": int(peak_allocated[index].max()),
                "maximum_peak_gpu_reserved_bytes": int(peak_reserved[index].max()),
            }
            for index, method in enumerate(METHODS)
        },
        "input_root": str(args.input_root),
        "array_job_id": args.array_job_id,
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
