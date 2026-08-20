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


REPEAT_SEEDS = (1070413377, 951166590, 4200525716, 38670800, 2537523285)
REPEAT_COUNT = len(REPEAT_SEEDS)
CANDIDATE_COUNT = 64
LATENT_DIM = 192


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


def verify_checksum_inventory(directory: Path) -> dict[str, str]:
    inventory = directory / "checksums.sha256"
    if not inventory.is_file():
        raise RuntimeError(f"missing checksum inventory: {inventory}")
    found: dict[str, str] = {}
    for raw in inventory.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, raw_path = raw.split(maxsplit=1)
        raw_path = raw_path.lstrip("* ")
        path = Path(raw_path)
        if not path.is_absolute():
            path = directory / path
        if path.resolve().parent != directory.resolve():
            raise RuntimeError(f"checksum path escapes execution directory: {path}")
        if not path.is_file():
            raise RuntimeError(f"checksum target is missing: {path}")
        actual = sha256_file(path)
        if actual != digest:
            raise RuntimeError(f"checksum mismatch for {path}")
        found[path.name] = digest
    expected = {"executions.h5", "manifest.json", "provenance.txt"}
    if set(found) != expected:
        raise RuntimeError(
            f"unexpected checksum inventory in {directory}: {sorted(found)}"
        )
    return found


def quantiles(value: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(value)),
        "p05": float(np.quantile(value, 0.05)),
        "median": float(np.median(value)),
        "mean": float(np.mean(value)),
        "p95": float(np.quantile(value, 0.95)),
        "max": float(np.max(value)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--candidate-h5", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--partition", choices=("P2", "P3"), default="P2")
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    args = parser.parse_args()

    partition = args.partition
    partition_key = partition.lower()
    environment = args.environment
    pool_count = 12 if partition == "P2" else 24
    prefix = "tworoom_" if environment == "tworoom" else ""
    candidate_classification = f"{prefix}{partition_key}_stratum3_b0_candidate_pools"
    execution_classification = f"{prefix}{partition_key}_candidate_attainment_execution"
    output_classification = f"{prefix}{partition_key}_stratum3_candidate_attainment_aggregate"
    expected_low = (1200, 30, 150, 2, 1, 5, 16) if environment == "pusht" else (300, 30, 10, 5, 1, 5, 16)

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit(f"refusing to overwrite {partition} execution aggregate")
    started = time.time()

    candidate_manifest = json.loads(
        args.candidate_manifest.read_text(encoding="utf-8")
    )
    if candidate_manifest.get("status") != "ok" or candidate_manifest.get(
        "classification"
    ) != candidate_classification or candidate_manifest.get("partition") != partition or candidate_manifest.get(
        "environment", "pusht"
    ) != environment:
        raise RuntimeError(
            f"input is not the frozen {partition} stratum-3 candidate pool"
        )
    candidate_sha = sha256_file(args.candidate_h5)
    if candidate_sha != candidate_manifest["output_h5_sha256"]:
        raise RuntimeError("candidate HDF5 does not match its manifest")

    with h5py.File(args.candidate_h5, "r") as candidates:
        if (
            candidates.attrs.get("classification") != candidate_classification
            or candidates.attrs.get("partition") != partition
            or candidates.attrs.get("environment", "pusht") != environment
        ):
            raise RuntimeError("candidate HDF5 classification or partition changed")
        pool_id = np.asarray(candidates["pool_id"][:], dtype=np.int64)
        episode_id = np.asarray(candidates["episode_id"][:], dtype=np.int64)
        source_global_row = np.asarray(
            candidates["source_global_row"][:], dtype=np.int64
        )
        goal_global_row = np.asarray(candidates["goal_global_row"][:], dtype=np.int64)
        selected_final_index = np.asarray(
            candidates["selected_final_index"][:], dtype=np.int64
        )
        target_latent = np.asarray(
            candidates["selected_z_subgoal"][:], dtype=np.float32
        )
    if pool_id.shape != (pool_count,) or not np.array_equal(
        pool_id, np.arange(pool_count)
    ):
        raise RuntimeError("candidate pool IDs are incomplete or unordered")
    if target_latent.shape != (pool_count, CANDIDATE_COUNT, LATENT_DIM):
        raise RuntimeError(f"unexpected candidate target shape: {target_latent.shape}")
    if selected_final_index.shape != (pool_count, CANDIDATE_COUNT):
        raise RuntimeError("unexpected selected-final-index shape")

    trace_steps = 26
    latent_trace = np.empty(
        (pool_count, REPEAT_COUNT, trace_steps, CANDIDATE_COUNT, LATENT_DIM),
        dtype=np.float32,
    )
    final_latent = np.empty(
        (pool_count, REPEAT_COUNT, CANDIDATE_COUNT, LATENT_DIM), dtype=np.float32
    )
    minimum_raw_rmse = np.empty(
        (pool_count, REPEAT_COUNT, CANDIDATE_COUNT), dtype=np.float32
    )
    minimum_raw_step = np.empty_like(minimum_raw_rmse, dtype=np.int64)
    final_raw_mse = np.empty_like(minimum_raw_rmse)
    final_raw_rmse = np.empty_like(minimum_raw_rmse)
    minimum_standardized_rmse = np.empty_like(minimum_raw_rmse)
    minimum_standardized_step = np.empty_like(minimum_raw_step)
    environment_goal_success = np.empty(
        (pool_count, REPEAT_COUNT, CANDIDATE_COUNT), dtype=np.bool_
    )
    source_state: np.ndarray | None = None
    goal_state: np.ndarray | None = None
    final_state: np.ndarray | None = None
    state_trace: np.ndarray | None = None
    execution_manifest_sha = np.empty((pool_count, REPEAT_COUNT), dtype="S64")
    execution_h5_sha = np.empty((pool_count, REPEAT_COUNT), dtype="S64")
    task_records: list[dict[str, Any]] = []
    stats_npz_sha256: str | None = None

    for pool in range(pool_count):
        for repeat, expected_seed in enumerate(REPEAT_SEEDS):
            directory = args.execution_root / f"pool-{pool:02d}-repeat-{repeat}"
            inventory = verify_checksum_inventory(directory)
            manifest_path = directory / "manifest.json"
            execution_path = directory / "executions.h5"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_partition = manifest.get("partition")
            if (
                manifest.get("status") != "ok"
                or manifest.get("classification") != execution_classification
                or manifest.get("environment", "pusht") != environment
                or (partition == "P2" and manifest_partition not in (None, "P2"))
                or (partition == "P3" and manifest_partition != "P3")
            ):
                raise RuntimeError(f"invalid execution classification: {directory}")
            if (manifest["pool_index"], manifest["repeat_index"]) != (pool, repeat):
                raise RuntimeError(f"pool/repeat mismatch: {directory}")
            if manifest["planner_seed"] != expected_seed or manifest[
                "environment_seed"
            ] != expected_seed:
                raise RuntimeError(f"repeat seed mismatch: {directory}")
            if tuple(manifest["repeat_seeds"]) != REPEAT_SEEDS:
                raise RuntimeError(f"frozen seed list mismatch: {directory}")
            if manifest["candidate_slice"] != [0, CANDIDATE_COUNT] or manifest[
                "candidate_count"
            ] != CANDIDATE_COUNT:
                raise RuntimeError(f"candidate coverage mismatch: {directory}")
            trace_spec = manifest.get("attainment_trace", {})
            if (
                trace_spec.get("steps_inclusive") != [0, 25]
                or trace_spec.get("record_count") != trace_steps
                or trace_spec.get("primary_distance_statistic")
                != "minimum standardized latent RMSE over steps 0..25"
                or trace_spec.get("labels_assigned") is not False
            ):
                raise RuntimeError(f"attainment trace protocol mismatch: {directory}")
            low = manifest["low_planner"]
            if (
                low["num_samples"],
                low["n_steps"],
                low["topk"],
                low["horizon_tokens"],
                low["receding_horizon_tokens"],
                low["action_block_primitive_steps"],
                low["cost_environment_chunk_size"],
            ) != expected_low:
                raise RuntimeError(f"low-level planner mismatch: {directory}")
            if not low["common_random_numbers_across_candidates"]:
                raise RuntimeError(f"common-random-number flag is false: {directory}")
            if manifest["solver_equivalence_self_test"]["status"] != "ok" or abs(
                manifest["solver_equivalence_self_test"]["max_abs"]
            ) > 1.0e-7:
                raise RuntimeError(f"solver equivalence test failed: {directory}")
            if manifest["inputs"]["candidate_h5_sha256"] != candidate_sha:
                raise RuntimeError(f"candidate input hash mismatch: {directory}")
            task_stats_sha = manifest["inputs"]["statistics"]["stats_npz_sha256"]
            if stats_npz_sha256 is None:
                stats_npz_sha256 = task_stats_sha
            elif task_stats_sha != stats_npz_sha256:
                raise RuntimeError("P1 statistics hash changes across execution tasks")
            if sha256_file(execution_path) != manifest["output_h5_sha256"]:
                raise RuntimeError(f"execution HDF5 differs from manifest: {directory}")

            with h5py.File(execution_path, "r") as execution:
                if execution.attrs["classification"] != execution_classification:
                    raise RuntimeError(f"execution HDF5 classification mismatch: {directory}")
                if execution.attrs.get("environment", "pusht") != environment:
                    raise RuntimeError(f"execution HDF5 environment mismatch: {directory}")
                if int(execution.attrs["pool_index"]) != pool or int(
                    execution.attrs["repeat_index"]
                ) != repeat:
                    raise RuntimeError(f"execution HDF5 indices mismatch: {directory}")
                if int(execution.attrs["planner_seed"]) != expected_seed:
                    raise RuntimeError(f"execution HDF5 seed mismatch: {directory}")
                slots = np.asarray(execution["candidate_slot"][:], dtype=np.int64)
                selected = np.asarray(
                    execution["selected_final_index"][:], dtype=np.int64
                )
                targets = np.asarray(execution["target_latent"][:], dtype=np.float32)
                if not np.array_equal(slots, np.arange(CANDIDATE_COUNT)):
                    raise RuntimeError(f"candidate slots are incomplete: {directory}")
                if not np.array_equal(selected, selected_final_index[pool]):
                    raise RuntimeError(f"selected candidate indices changed: {directory}")
                if not np.array_equal(targets, target_latent[pool]):
                    raise RuntimeError(f"target latents changed: {directory}")

                latent_trace[pool, repeat] = np.asarray(
                    execution["latent_trace"][:], dtype=np.float32
                )
                final_latent[pool, repeat] = np.asarray(
                    execution["final_latent"][:], dtype=np.float32
                )
                minimum_raw_rmse[pool, repeat] = np.asarray(
                    execution["minimum_raw_latent_rmse"][:], dtype=np.float32
                )
                minimum_raw_step[pool, repeat] = np.asarray(
                    execution["minimum_raw_latent_step"][:], dtype=np.int64
                )
                final_raw_mse[pool, repeat] = np.asarray(
                    execution["final_raw_latent_mse"][:], dtype=np.float32
                )
                final_raw_rmse[pool, repeat] = np.asarray(
                    execution["final_raw_latent_rmse"][:], dtype=np.float32
                )
                minimum_standardized_rmse[pool, repeat] = np.asarray(
                    execution["minimum_standardized_latent_rmse"][:],
                    dtype=np.float32,
                )
                minimum_standardized_step[pool, repeat] = np.asarray(
                    execution["minimum_standardized_latent_step"][:],
                    dtype=np.int64,
                )
                environment_goal_success[pool, repeat] = np.asarray(
                    execution["environment_goal_success"][:], dtype=np.bool_
                )
                source_task = np.asarray(execution["source_state"][:], dtype=np.float32)
                goal_task = np.asarray(execution["goal_state"][:], dtype=np.float32)
                state_trace_task = np.asarray(
                    execution["state_trace"][:], dtype=np.float32
                )
                final_task = np.asarray(execution["final_state"][:], dtype=np.float32)
                if source_state is None:
                    state_dim = int(source_task.shape[1])
                    source_state = np.empty(
                        (pool_count, CANDIDATE_COUNT, state_dim), dtype=np.float32
                    )
                    goal_state = np.empty_like(source_state)
                    final_state = np.empty(
                        (pool_count, REPEAT_COUNT, CANDIDATE_COUNT, state_dim),
                        dtype=np.float32,
                    )
                    state_trace = np.empty(
                        (
                            pool_count,
                            REPEAT_COUNT,
                            trace_steps,
                            CANDIDATE_COUNT,
                            state_dim,
                        ),
                        dtype=np.float32,
                    )
                assert goal_state is not None and final_state is not None
                if repeat == 0:
                    source_state[pool] = source_task
                    goal_state[pool] = goal_task
                elif not np.array_equal(source_task, source_state[pool]) or not np.array_equal(
                    goal_task, goal_state[pool]
                ):
                    raise RuntimeError(f"source or goal state changed across repeats: pool {pool}")
                final_state[pool, repeat] = final_task
                state_trace[pool, repeat] = state_trace_task
                if not np.array_equal(state_trace_task[0], source_task):
                    raise RuntimeError(f"state trace does not start at source: {directory}")
                if not np.array_equal(state_trace_task[-1], final_task):
                    raise RuntimeError(f"state trace does not end at final state: {directory}")
                if not np.array_equal(latent_trace[pool, repeat, -1], final_latent[pool, repeat]):
                    raise RuntimeError(f"latent trace does not end at final latent: {directory}")

            execution_manifest_sha[pool, repeat] = sha256_file(manifest_path).encode()
            execution_h5_sha[pool, repeat] = inventory["executions.h5"].encode()
            task_records.append(
                {
                    "pool_index": pool,
                    "repeat_index": repeat,
                    "seed": expected_seed,
                    "directory": str(directory),
                    "manifest_sha256": execution_manifest_sha[pool, repeat].decode(),
                    "execution_h5_sha256": execution_h5_sha[pool, repeat].decode(),
                    "execution_seconds": manifest["runtime"]["execution_seconds"],
                    "elapsed_seconds": manifest["elapsed_seconds"],
                    "peak_gpu_allocated_bytes": manifest["runtime"][
                        "peak_gpu_allocated_bytes"
                    ],
                    "peak_gpu_reserved_bytes": manifest["runtime"][
                        "peak_gpu_reserved_bytes"
                    ],
                }
            )

    assert (
        source_state is not None
        and goal_state is not None
        and final_state is not None
        and state_trace is not None
    )
    if not np.isfinite(final_latent).all() or not np.isfinite(final_state).all():
        raise RuntimeError("non-finite aggregate execution output")
    if not np.allclose(
        np.square(final_raw_rmse), final_raw_mse, rtol=2.0e-6, atol=2.0e-7
    ):
        raise RuntimeError("raw MSE and RMSE are inconsistent")
    if np.any(minimum_raw_step < 0) or np.any(minimum_raw_step >= trace_steps):
        raise RuntimeError("minimum raw-distance step is outside the trace")
    if np.any(minimum_standardized_step < 0) or np.any(
        minimum_standardized_step >= trace_steps
    ):
        raise RuntimeError("minimum standardized-distance step is outside the trace")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = output_classification
            output.attrs["environment"] = environment
            # Preserve the frozen P2 HDF5 byte layout for compatibility.  P2
            # predates the explicit partition attribute; P3 records it.
            if partition == "P3":
                output.attrs["partition"] = partition
            output.attrs["labels_assigned"] = False
            output.create_dataset("pool_id", data=pool_id)
            output.create_dataset("episode_id", data=episode_id)
            output.create_dataset("source_global_row", data=source_global_row)
            output.create_dataset("goal_global_row", data=goal_global_row)
            output.create_dataset("repeat_seed", data=np.asarray(REPEAT_SEEDS, dtype=np.uint32))
            output.create_dataset("selected_final_index", data=selected_final_index)
            output.create_dataset("target_latent", data=target_latent, compression="gzip")
            output.create_dataset("source_state", data=source_state)
            output.create_dataset("goal_state", data=goal_state)
            output.create_dataset("state_trace", data=state_trace, compression="gzip")
            output.create_dataset("final_state", data=final_state, compression="gzip")
            output.create_dataset("latent_trace", data=latent_trace, compression="gzip")
            output.create_dataset("final_latent", data=final_latent, compression="gzip")
            output.create_dataset("minimum_raw_latent_rmse", data=minimum_raw_rmse)
            output.create_dataset("minimum_raw_latent_step", data=minimum_raw_step)
            output.create_dataset("final_raw_latent_mse", data=final_raw_mse)
            output.create_dataset("final_raw_latent_rmse", data=final_raw_rmse)
            output.create_dataset(
                "minimum_standardized_latent_rmse",
                data=minimum_standardized_rmse,
            )
            output.create_dataset(
                "minimum_standardized_latent_step",
                data=minimum_standardized_step,
            )
            output.create_dataset("environment_goal_success", data=environment_goal_success)
            output.create_dataset("execution_manifest_sha256", data=execution_manifest_sha)
            output.create_dataset("execution_h5_sha256", data=execution_h5_sha)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_execution_aggregate_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": output_classification,
        "environment": environment,
        "partition": partition,
        "labels_assigned": False,
        "label_blocker": (
            "P2 physical-versus-latent tolerance selection on real-frame strata 1 and 2"
            if partition == "P2"
            else "application of the immutable P2-selected tolerance"
        ),
        "coverage": {
            "pools": pool_count,
            "repeats_per_candidate": REPEAT_COUNT,
            "candidates_per_pool": CANDIDATE_COUNT,
            "candidate_executions": pool_count * REPEAT_COUNT * CANDIDATE_COUNT,
            "repeat_seeds": list(REPEAT_SEEDS),
        },
        "metrics_without_labels": {
            "minimum_raw_latent_rmse": quantiles(minimum_raw_rmse),
            "final_raw_latent_rmse": quantiles(final_raw_rmse),
            "minimum_standardized_latent_rmse": quantiles(
                minimum_standardized_rmse
            ),
            "environment_goal_success_rate": float(environment_goal_success.mean()),
        },
        "resources": {
            "summed_execution_seconds": float(
                sum(record["execution_seconds"] for record in task_records)
            ),
            "summed_elapsed_seconds": float(
                sum(record["elapsed_seconds"] for record in task_records)
            ),
            "max_peak_gpu_allocated_bytes": int(
                max(record["peak_gpu_allocated_bytes"] for record in task_records)
            ),
            "max_peak_gpu_reserved_bytes": int(
                max(record["peak_gpu_reserved_bytes"] for record in task_records)
            ),
        },
        "inputs": {
            "execution_root": str(args.execution_root),
            "candidate_h5": str(args.candidate_h5),
            "candidate_h5_sha256": candidate_sha,
            "candidate_manifest_sha256": sha256_file(args.candidate_manifest),
            "stats_npz_sha256": stats_npz_sha256,
        },
        "tasks": task_records,
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
