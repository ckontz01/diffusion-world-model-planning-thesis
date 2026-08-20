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
MACRO_DIM = 32


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


def verify_output(directory: Path, expected_classification: str) -> tuple[dict[str, Any], str]:
    inventory = directory / "checksums.sha256"
    if not inventory.is_file():
        raise RuntimeError(f"missing checksum inventory: {directory}")
    expected_names = {"aggregate.h5", "manifest.json", "provenance.txt"}
    found: dict[str, str] = {}
    for raw in inventory.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, raw_path = raw.split(maxsplit=1)
        path = Path(raw_path.lstrip("* "))
        if not path.is_absolute():
            path = directory / path
        if path.resolve().parent != directory.resolve():
            raise RuntimeError(f"checksum path escapes aggregate directory: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid aggregate file: {path}")
        found[path.name] = digest
    if set(found) != expected_names:
        raise RuntimeError(f"unexpected aggregate inventory: {sorted(found)}")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "ok" or manifest.get(
        "classification"
    ) != expected_classification:
        raise RuntimeError(f"unexpected aggregate classification: {directory}")
    if manifest["output_h5_sha256"] != found["aggregate.h5"]:
        raise RuntimeError(f"aggregate HDF5 hash differs from manifest: {directory}")
    return manifest, found["aggregate.h5"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-aggregate-dir", type=Path, required=True)
    parser.add_argument("--real-aggregate-dir", type=Path, required=True)
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
    prefix = "tworoom_" if environment == "tworoom" else ""
    pool_count = 12 if partition == "P2" else 24
    fixed_classification = f"{prefix}{partition_key}_stratum3_candidate_attainment_aggregate"
    candidate_classification = f"{prefix}{partition_key}_stratum3_b0_candidate_pools"
    output_classification = f"{prefix}{partition_key}_stratum3_labeled_candidate_audit"
    output_partition = "P2-development-only" if partition == "P2" else "P3-locked"

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit(f"refusing to overwrite labeled {partition} stratum-3 audit")
    started = time.time()

    fixed_manifest, fixed_h5_sha = verify_output(
        args.fixed_aggregate_dir, fixed_classification
    )
    real_manifest, real_h5_sha = verify_output(
        args.real_aggregate_dir, f"{prefix}p2_real_frame_attainment_and_tolerance"
    )
    if fixed_manifest.get("environment", "pusht") != environment or real_manifest.get(
        "environment", "pusht"
    ) != environment:
        raise RuntimeError("aggregate environment differs from requested environment")
    if fixed_manifest.get("labels_assigned") is not False:
        raise RuntimeError("fixed-subgoal aggregate was labeled before tolerance selection")
    if fixed_manifest["inputs"]["stats_npz_sha256"] != real_manifest["inputs"][
        "stats_npz_sha256"
    ]:
        raise RuntimeError("real-frame and imagined candidates use different P1 statistics")

    selection = real_manifest["latent_tolerance_selection"]
    delta = float(selection["selected_delta"])
    delta_index = int(selection["selected_index"])
    grid = np.asarray(selection["grid"], dtype=np.float64)
    if grid.shape != (10,) or delta_index < 0 or delta_index >= len(grid):
        raise RuntimeError("invalid selected tolerance record")
    if delta != float(grid[delta_index]):
        raise RuntimeError("selected tolerance index/value mismatch")
    if selection["objective"] != (
        "maximum Cohen's kappa against primary physical labels over both P2 real-frame strata"
    ) or selection["tie_break"] != "smaller delta":
        raise RuntimeError("tolerance selection rule differs from the frozen protocol")
    if environment == "pusht" and (delta_index != 8 or not np.isclose(
        delta, 0.7168711644368866, rtol=0.0, atol=1.0e-15
    )):
        raise RuntimeError("selected tolerance differs from the P3 lock")

    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
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
    if fixed_manifest["inputs"]["candidate_h5_sha256"] != candidate_sha:
        raise RuntimeError("fixed aggregate uses a different candidate pool")

    with h5py.File(args.candidate_h5, "r") as candidates:
        if (
            candidates.attrs.get("classification") != candidate_classification
            or candidates.attrs.get("partition") != partition
            or candidates.attrs.get("environment", "pusht") != environment
        ):
            raise RuntimeError("candidate HDF5 classification or partition changed")
        pool_id = np.asarray(candidates["pool_id"][:], dtype=np.int64)
        episode_id = np.asarray(candidates["episode_id"][:], dtype=np.int64)
        source_row = np.asarray(candidates["source_global_row"][:], dtype=np.int64)
        goal_row = np.asarray(candidates["goal_global_row"][:], dtype=np.int64)
        source_step = np.asarray(candidates["source_step"][:], dtype=np.int64)
        goal_step = np.asarray(candidates["goal_step"][:], dtype=np.int64)
        planner_seed = np.asarray(candidates["planner_seed"][:], dtype=np.int64)
        source_latent = np.asarray(candidates["z_init"][:], dtype=np.float32)
        goal_latent = np.asarray(candidates["z_goal"][:], dtype=np.float32)
        selected_final_index = np.asarray(
            candidates["selected_final_index"][:], dtype=np.int64
        )
        selected_macro = np.asarray(candidates["selected_first_macro"][:], dtype=np.float32)
        selected_subgoal = np.asarray(
            candidates["selected_z_subgoal"][:], dtype=np.float32
        )
        selected_nominal_cost = np.asarray(
            candidates["selected_nominal_cost"][:], dtype=np.float32
        )
    if not np.array_equal(pool_id, np.arange(pool_count)):
        raise RuntimeError("candidate pools are incomplete or unordered")
    if source_latent.shape != (pool_count, LATENT_DIM):
        raise RuntimeError("unexpected source-latent shape")
    if selected_macro.shape != (pool_count, CANDIDATE_COUNT, MACRO_DIM):
        raise RuntimeError("unexpected selected-macro shape")
    if selected_subgoal.shape != (pool_count, CANDIDATE_COUNT, LATENT_DIM):
        raise RuntimeError("unexpected selected-subgoal shape")

    fixed_path = args.fixed_aggregate_dir / "aggregate.h5"
    with h5py.File(fixed_path, "r") as fixed:
        if fixed.attrs["classification"] != fixed_classification:
            raise RuntimeError("fixed aggregate HDF5 classification mismatch")
        if fixed.attrs.get("environment", "pusht") != environment:
            raise RuntimeError("fixed aggregate HDF5 environment mismatch")
        if fixed.attrs.get("partition", partition) != partition:
            raise RuntimeError("fixed aggregate HDF5 partition mismatch")
        if bool(fixed.attrs["labels_assigned"]):
            raise RuntimeError("fixed aggregate HDF5 was labeled early")
        if not np.array_equal(fixed["pool_id"][:], pool_id):
            raise RuntimeError("fixed aggregate pool IDs changed")
        if not np.array_equal(fixed["selected_final_index"][:], selected_final_index):
            raise RuntimeError("fixed aggregate candidate indices changed")
        if not np.array_equal(fixed["target_latent"][:], selected_subgoal):
            raise RuntimeError("fixed aggregate subgoals changed")
        repeat_seed = np.asarray(fixed["repeat_seed"][:], dtype=np.uint32)
        minimum_raw_rmse = np.asarray(
            fixed["minimum_raw_latent_rmse"][:], dtype=np.float32
        )
        minimum_raw_step = np.asarray(
            fixed["minimum_raw_latent_step"][:], dtype=np.int64
        )
        final_raw_rmse = np.asarray(fixed["final_raw_latent_rmse"][:], dtype=np.float32)
        minimum_standardized_rmse = np.asarray(
            fixed["minimum_standardized_latent_rmse"][:], dtype=np.float32
        )
        minimum_standardized_step = np.asarray(
            fixed["minimum_standardized_latent_step"][:], dtype=np.int64
        )
        environment_goal_success = np.asarray(
            fixed["environment_goal_success"][:], dtype=np.bool_
        )
        source_state = np.asarray(fixed["source_state"][:], dtype=np.float32)
        goal_state = np.asarray(fixed["goal_state"][:], dtype=np.float32)

    repeated_shape = (pool_count, REPEAT_COUNT, CANDIDATE_COUNT)
    if minimum_standardized_rmse.shape != repeated_shape:
        raise RuntimeError("unexpected imagined-candidate execution shape")
    if tuple(int(value) for value in repeat_seed) != REPEAT_SEEDS:
        raise RuntimeError("fixed aggregate repeat seeds changed")
    if not np.isfinite(minimum_standardized_rmse).all() or np.any(
        minimum_standardized_rmse < 0.0
    ):
        raise RuntimeError("invalid standardized latent distances")

    attained_per_run = minimum_standardized_rmse <= delta
    attainment_count = attained_per_run.sum(axis=1, dtype=np.int64)
    attainment_rate = attainment_count.astype(np.float32) / REPEAT_COUNT
    label_2_of_5 = attainment_count >= 2
    label_3_of_5 = attainment_count >= 3
    label_4_of_5 = attainment_count >= 4

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = output_classification
            output.attrs["environment"] = environment
            output.attrs["partition"] = output_partition
            output.attrs["selected_delta"] = delta
            output.attrs["primary_label_rule"] = "attained in at least 3 of 5 runs"
            output.create_dataset("pool_id", data=pool_id)
            output.create_dataset("episode_id", data=episode_id)
            output.create_dataset("source_global_row", data=source_row)
            output.create_dataset("goal_global_row", data=goal_row)
            output.create_dataset("source_step", data=source_step)
            output.create_dataset("goal_step", data=goal_step)
            output.create_dataset("planner_seed", data=planner_seed)
            output.create_dataset("repeat_seed", data=repeat_seed)
            output.create_dataset("source_latent", data=source_latent, compression="gzip")
            output.create_dataset("goal_latent", data=goal_latent, compression="gzip")
            output.create_dataset("selected_final_index", data=selected_final_index)
            output.create_dataset("selected_first_macro", data=selected_macro, compression="gzip")
            output.create_dataset("selected_subgoal", data=selected_subgoal, compression="gzip")
            output.create_dataset("selected_nominal_cost", data=selected_nominal_cost)
            output.create_dataset("source_state", data=source_state)
            output.create_dataset("goal_state", data=goal_state)
            output.create_dataset("minimum_raw_latent_rmse", data=minimum_raw_rmse)
            output.create_dataset("minimum_raw_latent_step", data=minimum_raw_step)
            output.create_dataset("final_raw_latent_rmse", data=final_raw_rmse)
            output.create_dataset(
                "minimum_standardized_latent_rmse", data=minimum_standardized_rmse
            )
            output.create_dataset(
                "minimum_standardized_latent_step", data=minimum_standardized_step
            )
            output.create_dataset("environment_goal_success", data=environment_goal_success)
            output.create_dataset("attained_per_run", data=attained_per_run)
            output.create_dataset("attainment_count", data=attainment_count)
            output.create_dataset("attainment_rate", data=attainment_rate)
            output.create_dataset("label_at_least_2_of_5", data=label_2_of_5)
            output.create_dataset("primary_label_at_least_3_of_5", data=label_3_of_5)
            output.create_dataset("label_at_least_4_of_5", data=label_4_of_5)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_labeled_stratum3_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": output_classification,
        "environment": environment,
        "partition": output_partition,
        "reporting_rule": (
            "P2 values select frozen settings and are not final thesis results"
            if partition == "P2"
            else "P3 is locked confirmation; values may not change any setting"
        ),
        "coverage": {
            "pools": pool_count,
            "candidates_per_pool": CANDIDATE_COUNT,
            "candidates": pool_count * CANDIDATE_COUNT,
            "repeats_per_candidate": REPEAT_COUNT,
            "candidate_executions": pool_count * CANDIDATE_COUNT * REPEAT_COUNT,
            "repeat_seeds": list(REPEAT_SEEDS),
        },
        "tolerance": {
            "selected_delta": delta,
            "selected_grid_index": delta_index,
            "source_rule": selection["objective"],
            "tie_break": selection["tie_break"],
            "real_frame_selected_combined_primary": selection[
                "selected_combined_primary"
            ],
        },
        "label": {
            "per_run": "minimum P1-standardized latent RMSE over t=0..25 <= selected delta",
            "primary": "attained in at least 3 of 5 runs",
            "primary_prevalence": float(label_3_of_5.mean()),
            "sensitivity_2_of_5_prevalence": float(label_2_of_5.mean()),
            "sensitivity_4_of_5_prevalence": float(label_4_of_5.mean()),
            "attainment_count_histogram": {
                str(count): int(np.sum(attainment_count == count))
                for count in range(REPEAT_COUNT + 1)
            },
            "per_pool_primary_prevalence": [
                float(label_3_of_5[pool].mean()) for pool in range(pool_count)
            ],
        },
        "inputs": {
            "fixed_aggregate_dir": str(args.fixed_aggregate_dir),
            "fixed_aggregate_h5_sha256": fixed_h5_sha,
            "fixed_aggregate_manifest_sha256": sha256_file(
                args.fixed_aggregate_dir / "manifest.json"
            ),
            "real_aggregate_dir": str(args.real_aggregate_dir),
            "real_aggregate_h5_sha256": real_h5_sha,
            "real_aggregate_manifest_sha256": sha256_file(
                args.real_aggregate_dir / "manifest.json"
            ),
            "candidate_h5": str(args.candidate_h5),
            "candidate_h5_sha256": candidate_sha,
            "candidate_manifest_sha256": sha256_file(args.candidate_manifest),
            "stats_npz_sha256": fixed_manifest["inputs"]["stats_npz_sha256"],
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
