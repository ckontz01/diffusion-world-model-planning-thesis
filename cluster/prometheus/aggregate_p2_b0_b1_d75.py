#!/usr/bin/env python3

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

from score_and_select_p2_true_scorers import verify_inventory


ARMS = ("B0", "B1")
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--array-job-id", type=int, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite P2 B0/B1 aggregate")
    if args.input_root.name != f"b0-b1-d75-grid-job-{args.array_job_id}":
        raise RuntimeError("input root does not match declared B0/B1 array job")
    started = time.time()

    success = np.empty((len(ARMS), POOL_COUNT), dtype=np.bool_)
    execution_seconds = np.empty_like(success, dtype=np.float64)
    peak_allocated = np.empty_like(success, dtype=np.int64)
    peak_reserved = np.empty_like(success, dtype=np.int64)
    episode_id = np.empty(POOL_COUNT, dtype=np.int64)
    source_row = np.empty(POOL_COUNT, dtype=np.int64)
    goal_row = np.empty(POOL_COUNT, dtype=np.int64)
    planner_seed = np.empty(POOL_COUNT, dtype=np.int64)
    expected_query: dict[int, tuple[int, int, int, int]] = {}
    candidate_h5_sha: str | None = None
    candidate_manifest_sha: str | None = None
    records: list[dict[str, Any]] = []

    for arm_index, arm in enumerate(ARMS):
        for pool_index in range(POOL_COUNT):
            array_task_id = arm_index * POOL_COUNT + pool_index
            directory = (
                args.input_root
                / f"arm-{arm}"
                / f"pool-{pool_index:02d}-task-{array_task_id}"
            )
            inventory = verify_inventory(directory)
            if set(inventory) != {"result.h5", "manifest.json", "provenance.txt"}:
                raise RuntimeError(f"unexpected inventory for baseline task {array_task_id}")
            manifest = json.loads(
                (directory / "manifest.json").read_text(encoding="utf-8")
            )
            if manifest.get("status") != "ok" or manifest.get(
                "classification"
            ) != "p2_b0_b1_d75_difficulty_development":
                raise RuntimeError(f"invalid baseline task {array_task_id}")
            if manifest.get("partition") != "P2-development-only" or manifest["arm"] != arm:
                raise RuntimeError(f"baseline arm/partition mismatch in task {array_task_id}")
            query = manifest["query"]
            if int(query["pool_index"]) != pool_index:
                raise RuntimeError("baseline pool mapping mismatch")
            identity = (
                int(query["episode_id"]),
                int(query["source_global_row"]),
                int(query["goal_global_row"]),
                int(query["planner_seed_63bit"]),
            )
            if pool_index in expected_query and expected_query[pool_index] != identity:
                raise RuntimeError(f"B0/B1 query mismatch for pool {pool_index}")
            expected_query.setdefault(pool_index, identity)
            episode_id[pool_index], source_row[pool_index], goal_row[pool_index], planner_seed[
                pool_index
            ] = identity
            if int(query["goal_step"]) - int(query["source_step"]) != 75:
                raise RuntimeError("baseline task is not a D75 query")
            planner = manifest["planner"]
            if (
                int(planner["eval_budget_primitive_steps"]),
                int(planner["high"]["num_samples"]),
                int(planner["high"]["iterations"]),
                int(planner["high"]["topk"]),
                int(planner["low"]["num_samples"]),
                int(planner["low"]["iterations"]),
                int(planner["low"]["topk"]),
                int(planner["high_cost_calls"]),
                int(planner["high_candidate_evaluations"]),
            ) != (150, 1200, 60, 10, 1200, 30, 150, 1800, 2_160_000):
                raise RuntimeError("baseline D75 budget/accounting mismatch")
            if arm == "B0":
                if planner["high"]["solver"] != "stable_worldmodel.CEMSolver" or planner[
                    "empirical_macro_bank"
                ] is not None:
                    raise RuntimeError("B0 unexpectedly uses an empirical proposal")
            else:
                bank = planner["empirical_macro_bank"]
                if planner["high"]["solver"] != "released EmpiricalMacroActionSolver":
                    raise RuntimeError("B1 does not use the released empirical solver")
                if (
                    bank["actions_shape"],
                    int(bank["num_sequences"]),
                    int(bank["chunk_len"]),
                    int(bank["raw_macro_len"]),
                    float(bank["residual_scale"]),
                    float(bank["min_residual_std"]),
                    int(bank["return_top_candidates"]),
                    bank["stage_sampling"],
                ) != ([4096, 2, 32], 4096, 5, 25, 0.1, 0.001, 8, "sequence"):
                    raise RuntimeError("B1 empirical-bank configuration mismatch")
                if not manifest.get("known_limitation"):
                    raise RuntimeError("B1 nondeterminism limitation was not recorded")
            if int(manifest["diagnostics"]["step_count"]) != 150:
                raise RuntimeError("baseline step trace is incomplete")
            if inventory["result.h5"] != manifest["output_h5_sha256"]:
                raise RuntimeError("baseline task HDF5 differs from its manifest")
            with h5py.File(directory / "result.h5", "r") as handle:
                if handle.attrs["classification"] != "p2_b0_b1_d75_difficulty_development":
                    raise RuntimeError("baseline HDF5 classification mismatch")
                if str(handle.attrs["arm"]) != arm or int(handle.attrs["pool_index"]) != pool_index:
                    raise RuntimeError("baseline HDF5 arm/pool mismatch")
                if bool(handle.attrs["episode_success"]) != bool(manifest["episode_success"]):
                    raise RuntimeError("baseline HDF5/JSON success mismatch")
                if handle["step_current_latent"].shape != (150, 192):
                    raise RuntimeError("baseline latent trace shape mismatch")
                if arm == "B1" and handle["empirical_macro_action_bank"].shape != (
                    4096,
                    2,
                    32,
                ):
                    raise RuntimeError("saved B1 empirical bank shape mismatch")

            current_candidate_h5 = manifest["inputs"]["candidate_h5_sha256"]
            current_candidate_manifest = manifest["inputs"]["candidate_manifest_sha256"]
            candidate_h5_sha = candidate_h5_sha or current_candidate_h5
            candidate_manifest_sha = candidate_manifest_sha or current_candidate_manifest
            if (
                current_candidate_h5 != candidate_h5_sha
                or current_candidate_manifest != candidate_manifest_sha
            ):
                raise RuntimeError("baseline tasks do not share the frozen query artifact")
            success[arm_index, pool_index] = bool(manifest["episode_success"])
            execution_seconds[arm_index, pool_index] = float(
                manifest["runtime"]["execution_seconds"]
            )
            peak_allocated[arm_index, pool_index] = int(
                manifest["runtime"]["peak_gpu_allocated_bytes"]
            )
            peak_reserved[arm_index, pool_index] = int(
                manifest["runtime"]["peak_gpu_reserved_bytes"]
            )
            records.append(
                {
                    "array_task_id": array_task_id,
                    "arm": arm,
                    "pool_index": pool_index,
                    "episode_success": bool(manifest["episode_success"]),
                    "result_h5_sha256": manifest["output_h5_sha256"],
                    "manifest_sha256": inventory["manifest.json"],
                }
            )

    success_count = success.sum(axis=1, dtype=np.int64)
    success_rate = 100.0 * success_count.astype(np.float64) / POOL_COUNT
    gain = float(success_rate[1] - success_rate[0])
    triggers = {
        "B0_above_85_percent": bool(success_rate[0] > 85.0),
        "B0_below_5_percent": bool(success_rate[0] < 5.0),
        "B1_gain_below_5_percentage_points": bool(gain < 5.0),
    }
    replace_cube = any(triggers.values())
    selected_second_environment = "TwoRoom" if replace_cube else "Cube"

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "p2_b0_b1_d75_difficulty_decision"
            output.attrs["partition"] = "P2-development-only"
            output.attrs["array_job_id"] = args.array_job_id
            output.attrs["selected_second_environment"] = selected_second_environment
            output.create_dataset(
                "arm", data=np.asarray(ARMS, dtype=h5py.string_dtype("utf-8"))
            )
            output.create_dataset("pool_index", data=np.arange(POOL_COUNT, dtype=np.int64))
            output.create_dataset("episode_id", data=episode_id)
            output.create_dataset("source_global_row", data=source_row)
            output.create_dataset("goal_global_row", data=goal_row)
            output.create_dataset("planner_seed", data=planner_seed)
            output.create_dataset("episode_success", data=success)
            output.create_dataset("success_count", data=success_count)
            output.create_dataset("success_rate_percent", data=success_rate)
            output.create_dataset("execution_seconds", data=execution_seconds)
            output.create_dataset("peak_gpu_allocated_bytes", data=peak_allocated)
            output.create_dataset("peak_gpu_reserved_bytes", data=peak_reserved)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_baseline_aggregate_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": "p2_b0_b1_d75_difficulty_decision",
        "partition": "P2-development-only",
        "reporting_rule": "environment choice only; these rates are not final baseline estimates",
        "query_count_per_arm": POOL_COUNT,
        "B0": {
            "success_count_of_12": int(success_count[0]),
            "success_rate_percent": float(success_rate[0]),
        },
        "B1": {
            "success_count_of_12": int(success_count[1]),
            "success_rate_percent": float(success_rate[1]),
            "gain_over_B0_percentage_points": gain,
        },
        "environment_substitution_rule": {
            "replace_Cube_if": [
                "B0 success > 85%",
                "B0 success < 5%",
                "B1 - B0 success < 5 percentage points",
            ],
            "triggers": triggers,
            "replace_cube": replace_cube,
            "selected_second_environment": selected_second_environment,
        },
        "matching_audit": {
            "query_identity_shared_between_B0_and_B1": True,
            "candidate_h5_sha256": candidate_h5_sha,
            "candidate_manifest_sha256": candidate_manifest_sha,
        },
        "known_limitation": "B1 same-seed GPU execution is not guaranteed bitwise; no task was selectively rerun",
        "task_records": records,
        "runtime_summary": {
            arm: {
                "mean_execution_seconds": float(execution_seconds[index].mean()),
                "maximum_peak_gpu_allocated_bytes": int(peak_allocated[index].max()),
                "maximum_peak_gpu_reserved_bytes": int(peak_reserved[index].max()),
            }
            for index, arm in enumerate(ARMS)
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

