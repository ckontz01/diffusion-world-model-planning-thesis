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


QUERY_COUNT = 12
ARMS = ("B0", "B1")
QUERY_H5_SHA256 = "5c6036906bd94f74c2041952d26e0ad67784d0c9966d8519880465db8a6ee5ce"
DATASET_SHA256 = "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625"
CHECKPOINT_SHA256 = "50aaae8539904e86a835939f8d85af56ca83549ef181d0f6bca7e444437fe4c4"
EVAL_CONFIG_SHA256 = "664bd25376ce94bd952af2d7b1afc193ab9623d32e9e5d2c28895a1eaf75c571"


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
    digest.update(array.tobytes())
    return digest.hexdigest()


def verify_inventory(directory: Path) -> dict[str, str]:
    root = directory.resolve()
    inventory_path = directory / "checksums.sha256"
    if not inventory_path.is_file():
        raise RuntimeError(f"missing checksum inventory: {directory}")
    found: dict[str, str] = {}
    for raw in inventory_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, raw_path = raw.split(maxsplit=1)
        path = Path(raw_path.lstrip("* "))
        if not path.is_absolute():
            path = directory / path
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise RuntimeError(f"checksum path escapes artifact: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"checksum-invalid file: {path}")
        found[str(resolved.relative_to(root))] = digest
    return found


def atomic_json(path: Path, value: dict[str, Any]) -> None:
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
    parser.add_argument("--query-dir", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite Cube environment decision")
    if args.input_root.name != f"b0-b1-d75-job-{args.array_job_id}":
        raise RuntimeError("Cube input root does not match declared array job")
    started = time.time()

    query_inventory = verify_inventory(args.query_dir)
    if set(query_inventory) != {"queries.h5", "manifest.json", "provenance.txt"}:
        raise RuntimeError("unexpected Cube query artifact inventory")
    query_manifest = json.loads(
        (args.query_dir / "manifest.json").read_text(encoding="utf-8")
    )
    if (
        query_manifest.get("classification")
        != "cube_p2_d75_environment_gate_queries"
        or query_inventory["queries.h5"] != QUERY_H5_SHA256
        or query_manifest.get("output_h5_sha256") != QUERY_H5_SHA256
    ):
        raise RuntimeError("Cube query artifact changed")
    with h5py.File(args.query_dir / "queries.h5", "r") as handle:
        expected_queries = [
            {
                key: int(handle[key][index])
                for key in (
                    "query_id",
                    "episode_id",
                    "source_global_row",
                    "goal_global_row",
                    "source_step",
                    "goal_step",
                    "planner_seed",
                )
            }
            for index in range(QUERY_COUNT)
        ]

    success = np.empty((len(ARMS), QUERY_COUNT), dtype=np.bool_)
    execution_seconds = np.empty((len(ARMS), QUERY_COUNT), dtype=np.float64)
    peak_allocated = np.empty((len(ARMS), QUERY_COUNT), dtype=np.int64)
    peak_reserved = np.empty_like(peak_allocated)
    task_records: list[dict[str, Any]] = []
    for arm_index, arm in enumerate(ARMS):
        for query_index in range(QUERY_COUNT):
            directory = args.input_root / f"arm-{arm}" / f"query-{query_index:02d}"
            inventory = verify_inventory(directory)
            if set(inventory) != {"result.h5", "manifest.json", "provenance.txt"}:
                raise RuntimeError(f"unexpected Cube task inventory: {directory}")
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            if (
                manifest.get("status") != "ok"
                or manifest.get("classification")
                != "cube_p2_d75_environment_substitution_gate"
                or manifest.get("partition") != "P2-development-only"
                or manifest.get("arm") != arm
                or manifest.get("query") != expected_queries[query_index]
                or manifest.get("output_h5_sha256") != inventory["result.h5"]
            ):
                raise RuntimeError(f"invalid Cube task: {directory}")
            planner = manifest["planner"]
            if (
                int(planner["eval_budget_primitive_steps"]),
                int(planner["goal_offset_primitive_steps"]),
                int(planner["high"]["num_samples"]),
                int(planner["high"]["iterations"]),
                int(planner["high"]["topk"]),
                int(planner["low"]["num_samples"]),
                int(planner["low"]["iterations"]),
                int(planner["low"]["topk"]),
            ) != (150, 75, 1200, 60, 10, 1200, 30, 150):
                raise RuntimeError(f"Cube task planner budget changed: {directory}")
            expected_solver = (
                "stable_worldmodel.CEMSolver"
                if arm == "B0"
                else "released EmpiricalMacroActionSolver"
            )
            expected_empirical = (
                None
                if arm == "B0"
                else {
                    "num_sequences": 4096,
                    "chunk_len": 5,
                    "raw_macro_len": 25,
                    "residual_scale": 0.1,
                    "min_residual_std": 0.001,
                    "return_top_candidates": 8,
                    "encode_batch_size": 4096,
                    "stage_sampling": "sequence",
                }
            )
            if (
                planner["high"]["solver"] != expected_solver
                or planner["empirical_macro_configuration"] != expected_empirical
            ):
                raise RuntimeError(f"Cube task proposal mechanism changed: {directory}")
            accounting = manifest["planner_accounting"]
            if (
                int(accounting["high_plan_count"]),
                int(accounting["low_block_count"]),
                int(accounting["step_count"]),
                int(accounting["high_cost_calls"]),
                int(accounting["high_candidate_evaluations"]),
                int(accounting["post_step_goal_reinjection_count"]),
            ) != (30, 30, 150, 1800, 2_160_000, 150):
                raise RuntimeError(f"Cube task cost accounting changed: {directory}")
            adapter = manifest["cube_goal_diagnostic_adapter"]
            if (
                adapter["operation"]
                != "restore the immutable goal fields after world.step and before diagnostics"
                or adapter["planner_or_environment_effect"] is not False
            ):
                raise RuntimeError(f"Cube goal adapter changed: {directory}")
            if (
                manifest["inputs"]["query_h5_sha256"] != QUERY_H5_SHA256
                or manifest["inputs"]["query_manifest_sha256"]
                != query_inventory["manifest.json"]
                or manifest["inputs"]["dataset_sha256"] != DATASET_SHA256
                or manifest["inputs"]["checkpoint_sha256"] != CHECKPOINT_SHA256
                or manifest["inputs"]["eval_config_sha256"] != EVAL_CONFIG_SHA256
                or int(manifest["state_latent_dim"]) != 192
            ):
                raise RuntimeError(f"Cube task lineage/geometry changed: {directory}")
            with h5py.File(directory / "result.h5", "r") as handle:
                if (
                    handle.attrs["classification"]
                    != "cube_p2_d75_environment_substitution_gate"
                    or handle.attrs["partition"] != "P2-development-only"
                    or str(handle.attrs["arm"]) != arm
                    or int(handle.attrs["query_index"]) != query_index
                    or bool(handle.attrs["episode_success"])
                    != bool(manifest["episode_success"])
                    or handle["high_plan_current_latent"].shape != (30, 192)
                    or handle["high_plan_goal_latent"].shape != (30, 192)
                    or handle["high_plan_subgoal_latent"].shape != (30, 192)
                    or handle["low_block_actual_latent"].shape != (30, 192)
                    or handle["low_block_subgoal_latent"].shape != (30, 192)
                    or handle["step_current_latent"].shape != (150, 192)
                    or handle["step_subgoal_latent"].shape != (150, 192)
                ):
                    raise RuntimeError(f"Cube task HDF5/manifest mismatch: {directory}")
                if arm == "B0":
                    if "empirical_bank_actions" in handle or manifest["empirical_bank"] is not None:
                        raise RuntimeError(f"Cube B0 unexpectedly has an empirical bank: {directory}")
                else:
                    bank = np.asarray(handle["empirical_bank_actions"])
                    bank_manifest = manifest["empirical_bank"]
                    if (
                        bank.shape != (4096, 2, 32)
                        or bank_manifest["shape"] != [4096, 2, 32]
                        or bank_manifest["sha256"] != sha256_array(bank)
                    ):
                        raise RuntimeError(f"Cube B1 empirical bank changed: {directory}")
            success[arm_index, query_index] = bool(manifest["episode_success"])
            execution_seconds[arm_index, query_index] = float(
                manifest["runtime"]["execution_seconds"]
            )
            peak_allocated[arm_index, query_index] = int(
                manifest["runtime"]["peak_gpu_allocated_bytes"]
            )
            peak_reserved[arm_index, query_index] = int(
                manifest["runtime"]["peak_gpu_reserved_bytes"]
            )
            task_records.append(
                {
                    "arm": arm,
                    "query_index": query_index,
                    "episode_success": bool(manifest["episode_success"]),
                    "manifest_sha256": inventory["manifest.json"],
                    "result_h5_sha256": inventory["result.h5"],
                }
            )

    success_count = success.sum(axis=1, dtype=np.int64)
    success_rate = 100.0 * success_count.astype(np.float64) / QUERY_COUNT
    improvement = float(success_rate[1] - success_rate[0])
    triggers = {
        "Cube_B0_above_85_percent": bool(success_rate[0] > 85.0),
        "Cube_B0_below_5_percent": bool(success_rate[0] < 5.0),
        "Cube_B1_minus_B0_below_5_percentage_points": bool(improvement < 5.0),
    }
    replace_cube = any(triggers.values())
    selected_environment = "TwoRoom" if replace_cube else "Cube"

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "cube_p2_d75_environment_substitution_decision"
            output.attrs["partition"] = "P2-development-only"
            output.attrs["selected_second_environment"] = selected_environment
            output.create_dataset("arm", data=np.asarray(ARMS, dtype="S2"))
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
            print(f"partial_cube_decision_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": "cube_p2_d75_environment_substitution_decision",
        "partition": "P2-development-only",
        "reporting_rule": "environment selection only; rates are not final estimates",
        "query_count_per_arm": QUERY_COUNT,
        "success": {
            arm: {
                "count_of_12": int(success_count[index]),
                "rate_percent": float(success_rate[index]),
            }
            for index, arm in enumerate(ARMS)
        },
        "B1_minus_B0_percentage_points": improvement,
        "triggers": triggers,
        "replace_Cube": replace_cube,
        "selected_second_environment": selected_environment,
        "tasks": task_records,
        "inputs": {
            "input_root": str(args.input_root),
            "array_job_id": args.array_job_id,
            "query_h5_sha256": query_inventory["queries.h5"],
            "query_manifest_sha256": query_inventory["manifest.json"],
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
