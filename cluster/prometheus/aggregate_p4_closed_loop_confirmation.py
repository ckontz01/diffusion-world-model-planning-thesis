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


QUERY_COUNT = 40
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260728
QUERY_H5_SHA256 = "098559f55bf1e1b6cde440349e7bbe1debfd3d5441d9bf1b1e673f031c1758cd"
LOCKED_WEIGHTS = {"M1": 2.0, "M2": 1.0, "M3": 0.25}
LEARNED_METHODS = ("M1", "M2", "M3")
SCORER_TRAINING_SEEDS = [20260728, 20260729, 20260730]


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


def verify_inventory(directory: Path) -> dict[str, str]:
    inventory_path = directory / "checksums.sha256"
    if not inventory_path.is_file():
        raise RuntimeError(f"missing checksum inventory: {directory}")
    root = directory.resolve()
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
            raise RuntimeError(f"checksum path escapes result directory: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid result: {path}")
        found[str(resolved.relative_to(root))] = digest
    return found


def verify_three_file_artifact(
    directory: Path, *, filename: str, classification: str
) -> tuple[dict[str, Any], Path, dict[str, str]]:
    inventory = verify_inventory(directory)
    expected = {filename, "manifest.json", "provenance.txt"}
    if set(inventory) != expected:
        raise RuntimeError(f"unexpected artifact inventory: {directory}")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification") != classification
        or manifest.get("output_h5_sha256") != inventory[filename]
    ):
        raise RuntimeError(f"invalid artifact: {directory}")
    return manifest, directory / filename, inventory


def exact_paired_sign_pvalue(reference: np.ndarray, comparison: np.ndarray) -> dict[str, Any]:
    reference = np.asarray(reference, dtype=np.bool_)
    comparison = np.asarray(comparison, dtype=np.bool_)
    gains = int(np.sum(comparison & ~reference))
    losses = int(np.sum(reference & ~comparison))
    discordant = gains + losses
    if discordant == 0:
        pvalue = 1.0
    else:
        tail = sum(
            math.comb(discordant, value)
            for value in range(min(gains, losses) + 1)
        ) / (2**discordant)
        pvalue = min(1.0, 2.0 * tail)
    return {
        "comparison_only_successes": gains,
        "B0_only_successes": losses,
        "discordant_pairs": discordant,
        "two_sided_exact_pvalue": float(pvalue),
        "test": "two-sided exact paired sign test over discordant query outcomes",
    }


def percentile_interval(values: np.ndarray) -> list[float]:
    low, high = np.quantile(values, (0.025, 0.975), method="linear")
    return [float(low), float(high)]


def query_identity(manifest: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    query = manifest["query"]
    return (
        int(query["pool_index"]),
        int(query["episode_id"]),
        int(query["source_global_row"]),
        int(query["goal_global_row"]),
        int(query["source_step"]),
        int(query["planner_seed_63bit"]),
    )


def verify_common_task(
    directory: Path,
    *,
    expected_classification: str,
    expected_identity: tuple[int, int, int, int, int, int],
    expected_query_manifest_sha256: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    inventory = verify_inventory(directory)
    if set(inventory) != {"result.h5", "manifest.json", "provenance.txt"}:
        raise RuntimeError(f"unexpected P4 task inventory: {directory}")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification") != expected_classification
        or manifest.get("partition") != "P4-locked"
        or manifest.get("output_h5_sha256") != inventory["result.h5"]
    ):
        raise RuntimeError(f"invalid P4 task: {directory}")
    if query_identity(manifest) != expected_identity:
        raise RuntimeError(f"P4 query identity mismatch: {directory}")
    if int(manifest["query"]["goal_step"]) - int(manifest["query"]["source_step"]) != 75:
        raise RuntimeError(f"P4 task is not D75: {directory}")
    planner = manifest["planner"]
    if (
        int(planner["eval_budget_primitive_steps"]),
        int(planner["high"]["num_samples"]),
        int(planner["high"]["iterations"]),
        int(planner["high"]["topk"]),
        int(planner["low"]["num_samples"]),
        int(planner["low"]["iterations"]),
        int(planner["low"]["topk"]),
    ) != (150, 1200, 60, 10, 1200, 30, 150):
        raise RuntimeError(f"P4 planner budget changed: {directory}")
    if int(manifest["diagnostics"]["step_count"]) != 150:
        raise RuntimeError(f"P4 task did not complete 150 steps: {directory}")
    if (
        manifest["inputs"]["candidate_h5_sha256"] != QUERY_H5_SHA256
        or manifest["inputs"]["candidate_manifest_sha256"]
        != expected_query_manifest_sha256
    ):
        raise RuntimeError(f"P4 task uses a different query artifact: {directory}")
    with h5py.File(directory / "result.h5", "r") as handle:
        if (
            handle.attrs.get("classification") != expected_classification
            or handle.attrs.get("partition") != "P4-locked"
            or int(handle.attrs["pool_index"]) != expected_identity[0]
            or int(handle.attrs["planner_seed"]) != expected_identity[-1]
            or bool(handle.attrs["episode_success"])
            != bool(manifest["episode_success"])
            or handle["step_current_latent"].shape != (150, 192)
        ):
            raise RuntimeError(f"P4 task HDF5/manifest mismatch: {directory}")
    return manifest, inventory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-dir", type=Path, required=True)
    parser.add_argument("--promotion-dir", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--m1-root", type=Path)
    parser.add_argument("--m2-root", type=Path)
    parser.add_argument("--m3-root", type=Path)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite P4 closed-loop aggregate")
    started = time.time()

    query_manifest, query_h5, query_inventory = verify_three_file_artifact(
        args.query_dir,
        filename="queries.h5",
        classification="p4_closed_loop_d75_queries",
    )
    if (
        query_inventory["queries.h5"] != QUERY_H5_SHA256
        or query_manifest.get("partition") != "P4"
        or int(query_manifest.get("query_count")) != QUERY_COUNT
    ):
        raise RuntimeError("P4 query artifact differs from the frozen input")
    with h5py.File(query_h5, "r") as queries:
        query_id = np.asarray(queries["query_id"][:], dtype=np.int64)
        episode_id = np.asarray(queries["episode_id"][:], dtype=np.int64)
        source_row = np.asarray(queries["source_global_row"][:], dtype=np.int64)
        goal_row = np.asarray(queries["goal_global_row"][:], dtype=np.int64)
        source_step = np.asarray(queries["source_step"][:], dtype=np.int64)
        planner_seed = np.asarray(queries["planner_seed"][:], dtype=np.int64)
    if not np.array_equal(query_id, np.arange(QUERY_COUNT)):
        raise RuntimeError("P4 query IDs are not canonical")
    expected_identities = [
        (
            index,
            int(episode_id[index]),
            int(source_row[index]),
            int(goal_row[index]),
            int(source_step[index]),
            int(planner_seed[index]),
        )
        for index in range(QUERY_COUNT)
    ]

    promotion_manifest, promotion_h5, promotion_inventory = verify_three_file_artifact(
        args.promotion_dir,
        filename="audit.h5",
        classification="p3_locked_scorer_audit_and_promotion",
    )
    if promotion_manifest.get("partition") != "P3-locked":
        raise RuntimeError("promotion artifact is not marked locked")
    promoted = promotion_manifest.get("promoted_arms")
    if (
        not isinstance(promoted, list)
        or len(set(promoted)) != len(promoted)
        or any(method not in LEARNED_METHODS for method in promoted)
    ):
        raise RuntimeError("invalid P3 promoted-arm list")
    promoted = [method for method in LEARNED_METHODS if method in promoted]
    promotion_records = promotion_manifest.get("promotion")
    if not isinstance(promotion_records, dict):
        raise RuntimeError("P3 audit has no promotion records")
    for method in LEARNED_METHODS:
        record = promotion_records.get(method)
        if not isinstance(record, dict) or record.get("promoted") is not (
            method in promoted
        ):
            raise RuntimeError(f"P3 promotion list/record mismatch for {method}")

    promotion_inputs = promotion_manifest.get("inputs")
    selected_configuration = promotion_manifest.get("selected_configuration")
    training_seeds = promotion_manifest.get("coverage", {}).get("training_seeds")
    if (
        not isinstance(promotion_inputs, dict)
        or not isinstance(selected_configuration, dict)
        or training_seeds != SCORER_TRAINING_SEEDS
    ):
        raise RuntimeError("P3 scorer lineage/configuration record is incomplete")
    for required in (
        "p2_true_score_h5_sha256",
        "p2_calibration_h5_sha256",
        "stats_npz_sha256",
        "noise_npy_sha256",
    ):
        if not isinstance(promotion_inputs.get(required), str):
            raise RuntimeError(f"P3 scorer lineage is missing {required}")
    expected_checkpoint_hashes: dict[str, dict[int, str]] = {
        method: {} for method in LEARNED_METHODS
    }
    for record in promotion_manifest.get("checkpoints", []):
        method = record.get("method")
        if method in LEARNED_METHODS and record.get("condition") == "true":
            seed = int(record["seed"])
            if seed in expected_checkpoint_hashes[method]:
                raise RuntimeError(f"duplicate P3 true checkpoint for {method}/{seed}")
            expected_checkpoint_hashes[method][seed] = record["checkpoint_sha256"]
    for method in LEARNED_METHODS:
        if set(expected_checkpoint_hashes[method]) != set(training_seeds):
            raise RuntimeError(f"P3 true-checkpoint lineage is incomplete for {method}")

    learned_roots = {"M1": args.m1_root, "M2": args.m2_root, "M3": args.m3_root}
    for method, root in learned_roots.items():
        if method in promoted and root is None:
            raise RuntimeError(f"missing P4 result root for promoted {method}")
        if method not in promoted and root is not None:
            raise RuntimeError(f"P4 result root supplied for unpromoted {method}")

    arms = ["B0", "B1", *promoted]
    success = np.empty((len(arms), QUERY_COUNT), dtype=np.bool_)
    execution_seconds = np.empty((len(arms), QUERY_COUNT), dtype=np.float64)
    scorer_seconds = np.full((len(arms), QUERY_COUNT), np.nan, dtype=np.float64)
    peak_allocated = np.empty((len(arms), QUERY_COUNT), dtype=np.int64)
    peak_reserved = np.empty_like(peak_allocated)
    task_manifest_sha = np.empty((len(arms), QUERY_COUNT), dtype="S64")
    task_h5_sha = np.empty_like(task_manifest_sha)
    task_records: list[dict[str, Any]] = []

    for arm_index, arm in enumerate(arms):
        for index in range(QUERY_COUNT):
            if arm in ("B0", "B1"):
                directory = args.baseline_root / f"arm-{arm}" / f"query-{index:02d}"
                classification = "p4_b0_b1_d75_confirmation"
            else:
                root = learned_roots[arm]
                assert root is not None
                directory = root / f"query-{index:02d}"
                classification = "p4_augmented_closed_loop_confirmation"
            manifest, inventory = verify_common_task(
                directory,
                expected_classification=classification,
                expected_identity=expected_identities[index],
                expected_query_manifest_sha256=query_inventory["manifest.json"],
            )
            if arm in ("B0", "B1"):
                if manifest.get("arm") != arm:
                    raise RuntimeError(f"baseline arm mismatch: {directory}")
                planner = manifest["planner"]
                if (
                    int(planner["high_cost_calls"]),
                    int(planner["high_candidate_evaluations"]),
                ) != (1800, 2_160_000):
                    raise RuntimeError(f"baseline cost accounting changed: {directory}")
            else:
                if manifest.get("method") != arm or not math.isclose(
                    float(manifest.get("weight")),
                    LOCKED_WEIGHTS[arm],
                    rel_tol=0.0,
                    abs_tol=0.0,
                ):
                    raise RuntimeError(f"learned arm/weight mismatch: {directory}")
                if manifest["cost"]["nominal_equivalence"] != {
                    "max_abs": 0.0,
                    "shape": [1, 4],
                    "status": "ok",
                }:
                    raise RuntimeError(f"nominal-cost equivalence failed: {directory}")
                timing = manifest["cost"]["timing"]
                if (
                    int(timing["cost_calls"]),
                    int(timing["completed_high_solves"]),
                    int(timing["candidate_evaluations"]),
                ) != (1800, 30, 2_160_000):
                    raise RuntimeError(f"scorer cost accounting changed: {directory}")
                if (
                    manifest["inputs"].get("p3_promotion_h5_sha256")
                    != promotion_inventory["audit.h5"]
                ):
                    raise RuntimeError(f"learned arm uses another promotion audit: {directory}")
                artifacts = manifest["cost"]["scorer_artifacts"]
                expected_width = (
                    selected_configuration["M1_width"]
                    if arm == "M1"
                    else selected_configuration["M2_width"]
                    if arm == "M2"
                    else None
                )
                expected_sigma = (
                    selected_configuration["M2_sigma"] if arm == "M2" else None
                )
                if (
                    artifacts.get("method") != arm
                    or artifacts.get("seeds") != training_seeds
                    or artifacts.get("width") != expected_width
                    or artifacts.get("sigma") != expected_sigma
                    or artifacts.get("true_selection_h5_sha256")
                    != promotion_inputs["p2_true_score_h5_sha256"]
                    or artifacts.get("calibration_h5_sha256")
                    != promotion_inputs["p2_calibration_h5_sha256"]
                    or artifacts.get("statistics_sha256")
                    != promotion_inputs["stats_npz_sha256"]
                ):
                    raise RuntimeError(f"learned scorer lineage/config changed: {directory}")
                observed_checkpoints = artifacts.get("checkpoints")
                if not isinstance(observed_checkpoints, list) or {
                    int(record["seed"]): record["checkpoint_sha256"]
                    for record in observed_checkpoints
                } != expected_checkpoint_hashes[arm]:
                    raise RuntimeError(f"learned checkpoint lineage changed: {directory}")
                noise = artifacts.get("noise")
                if arm == "M2":
                    if not isinstance(noise, dict) or noise.get("npy_sha256") != (
                        promotion_inputs["noise_npy_sha256"]
                    ):
                        raise RuntimeError(f"M2 noise lineage changed: {directory}")
                elif noise is not None:
                    raise RuntimeError(f"non-M2 arm unexpectedly uses a noise bank: {directory}")
                scorer_seconds[arm_index, index] = float(timing["scorer_ms"]) / 1000.0

            success[arm_index, index] = bool(manifest["episode_success"])
            execution_seconds[arm_index, index] = float(
                manifest["runtime"]["execution_seconds"]
            )
            peak_allocated[arm_index, index] = int(
                manifest["runtime"]["peak_gpu_allocated_bytes"]
            )
            peak_reserved[arm_index, index] = int(
                manifest["runtime"]["peak_gpu_reserved_bytes"]
            )
            task_manifest_sha[arm_index, index] = inventory["manifest.json"].encode()
            task_h5_sha[arm_index, index] = inventory["result.h5"].encode()
            task_records.append(
                {
                    "arm": arm,
                    "query_index": index,
                    "directory": str(directory),
                    "episode_success": bool(success[arm_index, index]),
                    "execution_seconds": float(execution_seconds[arm_index, index]),
                    "scorer_seconds": (
                        None
                        if not np.isfinite(scorer_seconds[arm_index, index])
                        else float(scorer_seconds[arm_index, index])
                    ),
                    "manifest_sha256": inventory["manifest.json"],
                    "result_h5_sha256": inventory["result.h5"],
                }
            )

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    resampled_query = rng.integers(
        0, QUERY_COUNT, size=(BOOTSTRAP_REPLICATES, QUERY_COUNT), dtype=np.uint8
    )
    success_rate_bootstrap = 100.0 * success[:, resampled_query].mean(axis=2)
    success_count = success.sum(axis=1, dtype=np.int64)
    success_rate = 100.0 * success_count.astype(np.float64) / QUERY_COUNT
    arm_records: dict[str, Any] = {}
    difference_bootstrap: dict[str, np.ndarray] = {}
    for arm_index, arm in enumerate(arms):
        record: dict[str, Any] = {
            "success_count_of_40": int(success_count[arm_index]),
            "success_rate_percent": float(success_rate[arm_index]),
            "success_rate_bootstrap_95_percentile_interval": percentile_interval(
                success_rate_bootstrap[arm_index]
            ),
            "mean_execution_seconds": float(execution_seconds[arm_index].mean()),
            "max_peak_gpu_allocated_bytes": int(peak_allocated[arm_index].max()),
            "max_peak_gpu_reserved_bytes": int(peak_reserved[arm_index].max()),
        }
        if arm not in ("B0", "B1"):
            record["weight"] = LOCKED_WEIGHTS[arm]
            record["mean_total_scorer_seconds"] = float(
                scorer_seconds[arm_index].mean()
            )
        if arm != "B0":
            difference = success_rate_bootstrap[arm_index] - success_rate_bootstrap[0]
            difference_bootstrap[arm] = difference
            record["versus_B0"] = {
                "paired_success_difference_percentage_points": float(
                    success_rate[arm_index] - success_rate[0]
                ),
                "paired_bootstrap_95_percentile_interval": percentile_interval(
                    difference
                ),
                **exact_paired_sign_pvalue(success[0], success[arm_index]),
            }
        arm_records[arm] = record

    if "M2" in promoted:
        primary_endpoint: dict[str, Any] = {
            "status": "evaluated",
            "contrast": "M2 minus B0 PushT D75 success over 40 paired P4 queries",
            **arm_records["M2"]["versus_B0"],
        }
    else:
        primary_endpoint = {
            "status": "not evaluated because M2 failed the locked P3 promotion gate",
            "contrast": "M2 minus B0 PushT D75 success",
        }
    secondary_raw_pvalues = {
        arm: arm_records[arm]["versus_B0"]["two_sided_exact_pvalue"]
        for arm in arms
        if arm not in ("B0", "M2")
    }

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "p4_closed_loop_confirmation_aggregate"
            output.attrs["partition"] = "P4-locked"
            output.attrs["bootstrap_seed"] = BOOTSTRAP_SEED
            output.attrs["bootstrap_replicates"] = BOOTSTRAP_REPLICATES
            output.create_dataset("arm", data=np.asarray(arms, dtype="S2"))
            output.create_dataset("query_id", data=query_id)
            output.create_dataset("episode_id", data=episode_id)
            output.create_dataset("source_global_row", data=source_row)
            output.create_dataset("goal_global_row", data=goal_row)
            output.create_dataset("planner_seed", data=planner_seed)
            output.create_dataset("episode_success", data=success)
            output.create_dataset("success_count", data=success_count)
            output.create_dataset("success_rate_percent", data=success_rate)
            output.create_dataset("execution_seconds", data=execution_seconds)
            output.create_dataset("scorer_seconds", data=scorer_seconds)
            output.create_dataset("peak_gpu_allocated_bytes", data=peak_allocated)
            output.create_dataset("peak_gpu_reserved_bytes", data=peak_reserved)
            output.create_dataset("task_manifest_sha256", data=task_manifest_sha)
            output.create_dataset("task_result_h5_sha256", data=task_h5_sha)
            output.create_dataset("bootstrap/resampled_query_index", data=resampled_query)
            output.create_dataset(
                "bootstrap/success_rate_percent", data=success_rate_bootstrap
            )
            for arm, values in difference_bootstrap.items():
                output.create_dataset(
                    f"bootstrap/difference_vs_B0/{arm}", data=values
                )
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_p4_aggregate_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": "p4_closed_loop_confirmation_aggregate",
        "partition": "P4-locked",
        "reporting_rule": "locked confirmation; no setting may be revised from these outcomes",
        "coverage": {
            "queries": QUERY_COUNT,
            "arms": arms,
            "promoted_learned_arms": promoted,
            "matched_query_identity_across_arms": True,
        },
        "arms": arm_records,
        "primary_endpoint": primary_endpoint,
        "secondary_family": {
            "available_PushT_core_raw_pvalues": secondary_raw_pvalues,
            "final_Holm_status": "deferred until every executable predeclared secondary-family contrast, including the second environment, is available",
            "raw_test": "two-sided exact paired sign test",
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "unit": "complete P4 query/evaluation seed",
            "paired": True,
            "interval": "2.5th and 97.5th percentiles using NumPy linear quantiles",
        },
        "inputs": {
            "query_h5_sha256": query_inventory["queries.h5"],
            "query_manifest_sha256": query_inventory["manifest.json"],
            "promotion_h5_sha256": promotion_inventory["audit.h5"],
            "promotion_manifest_sha256": promotion_inventory["manifest.json"],
            "baseline_root": str(args.baseline_root),
            "learned_roots": {
                method: str(root) if root is not None else None
                for method, root in learned_roots.items()
            },
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
