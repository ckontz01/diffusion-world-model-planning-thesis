#!/usr/bin/env python3
"""Independent, read-only audit of the frozen PushT candidate executions.

This script deliberately does not import the execution or aggregation code.  It
checks the artifacts against the immutable source dataset and recomputes their
stored traces/labels from primitive arrays.  It is intended to catch reset,
row-mapping, trace-axis, and physical-label mistakes that could otherwise be
shared by the producer and aggregator.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import h5py
import numpy as np


EXPECTED_ROOTS = {
    "p2_fixed": ("P2", "fixed", 60),
    "p2_real": ("P2", "real", 120),
    "p3_fixed": ("P3", "fixed", 120),
    "p3_real": ("P3", "real", 240),
}
TRACE_STEPS = 26
LATENT_DIM = 192
POSITION_TOLERANCE = 20.0
ANGLE_TOLERANCE = math.pi / 9.0


def sha256_file(path: Path, chunk_size: int = 16 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def wrapped_angle_error(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    raw = np.abs(a - b)
    return np.minimum(raw, 2.0 * np.pi - raw)


def load_partitions(path: Path) -> dict[int, str]:
    output: dict[int, str] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            output[int(row["episode_id"])] = row["partition"]
    if not output:
        raise RuntimeError("partition manifest is empty")
    return output


def max_abs(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        return float("inf")
    if a.size == 0:
        return 0.0
    return float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64))))


def allclose(a: np.ndarray, b: np.ndarray, *, atol: float = 2e-6) -> bool:
    return a.shape == b.shape and bool(np.allclose(a, b, rtol=2e-6, atol=atol))


class Audit:
    def __init__(self, max_failures: int) -> None:
        self.max_failures = max_failures
        self.checks = Counter()
        self.failures: list[dict[str, Any]] = []
        self.max_errors: dict[str, float] = defaultdict(float)

    def check(self, condition: bool, name: str, path: Path, detail: str = "") -> None:
        self.checks[f"{name}:total"] += 1
        if condition:
            self.checks[f"{name}:passed"] += 1
            return
        self.checks[f"{name}:failed"] += 1
        if len(self.failures) < self.max_failures:
            self.failures.append({"check": name, "path": str(path), "detail": detail})

    def error(self, name: str, value: float) -> None:
        if math.isfinite(value):
            self.max_errors[name] = max(self.max_errors[name], value)
        else:
            self.max_errors[name] = value


def verify_manifest_hash(audit: Audit, manifest: dict[str, Any], h5_path: Path) -> None:
    expected = manifest.get("output_h5_sha256")
    if expected:
        actual = sha256_file(h5_path)
        audit.check(actual == expected, "manifest_output_sha256", h5_path, f"{actual} != {expected}")


def audit_common_latent_trace(
    audit: Audit,
    handle: h5py.File,
    h5_path: Path,
    latent_std: np.ndarray,
) -> dict[str, int]:
    trace = np.asarray(handle["latent_trace"][:], dtype=np.float32)
    target = np.asarray(handle["target_latent"][:], dtype=np.float32)
    state_trace = np.asarray(handle["state_trace"][:], dtype=np.float32)
    audit.check(trace.ndim == 3 and trace.shape[0] == TRACE_STEPS and trace.shape[2] == LATENT_DIM,
                "latent_trace_shape", h5_path, str(trace.shape))
    audit.check(state_trace.ndim == 3 and state_trace.shape[0] == TRACE_STEPS and state_trace.shape[2] == 7,
                "state_trace_shape", h5_path, str(state_trace.shape))
    audit.check(target.shape == trace.shape[1:], "target_latent_shape", h5_path, f"{target.shape} vs {trace.shape}")
    if trace.shape[0] != TRACE_STEPS or target.shape != trace.shape[1:]:
        return {"candidate_count": int(target.shape[0]) if target.ndim else 0, "min_at_t0": 0}

    raw = np.sqrt(np.mean((trace - target[None, :, :]) ** 2, axis=-1, dtype=np.float64))
    stored_raw = np.asarray(handle["raw_latent_rmse_trace"][:], dtype=np.float64)
    error = max_abs(raw, stored_raw)
    audit.error("raw_latent_rmse_trace", error)
    audit.check(allclose(raw, stored_raw), "raw_latent_rmse_recompute", h5_path, f"max_abs={error}")

    raw_min = raw.min(axis=0)
    raw_argmin = raw.argmin(axis=0).astype(np.int64)
    if "minimum_raw_latent_rmse" in handle:
        stored = np.asarray(handle["minimum_raw_latent_rmse"][:], dtype=np.float64)
        error = max_abs(raw_min, stored)
        audit.error("minimum_raw_latent_rmse", error)
        audit.check(allclose(raw_min, stored), "raw_min_recompute", h5_path, f"max_abs={error}")
    if "minimum_raw_latent_step" in handle:
        stored_step = np.asarray(handle["minimum_raw_latent_step"][:], dtype=np.int64)
        audit.check(np.array_equal(raw_argmin, stored_step), "raw_argmin_recompute", h5_path)

    standardized = np.sqrt(
        np.mean(((trace - target[None, :, :]) / latent_std[None, None, :]) ** 2,
                axis=-1, dtype=np.float64)
    )
    if "standardized_latent_rmse_trace" in handle:
        stored = np.asarray(handle["standardized_latent_rmse_trace"][:], dtype=np.float64)
        error = max_abs(standardized, stored)
        audit.error("standardized_latent_rmse_trace", error)
        audit.check(allclose(standardized, stored), "standardized_rmse_recompute", h5_path,
                    f"max_abs={error}")
    standardized_argmin = standardized.argmin(axis=0).astype(np.int64)
    if "minimum_standardized_latent_rmse" in handle:
        stored = np.asarray(handle["minimum_standardized_latent_rmse"][:], dtype=np.float64)
        error = max_abs(standardized.min(axis=0), stored)
        audit.error("minimum_standardized_latent_rmse", error)
        audit.check(allclose(standardized.min(axis=0), stored), "standardized_min_recompute", h5_path,
                    f"max_abs={error}")
    if "minimum_standardized_latent_step" in handle:
        stored_step = np.asarray(handle["minimum_standardized_latent_step"][:], dtype=np.int64)
        # Torch and NumPy may select opposite sides of a float32 near-tie even
        # when the stored minimum value itself reproduces.  Validate that the
        # stored step attains the independently recomputed minimum to numerical
        # precision instead of requiring the same arbitrary tie winner.
        candidate_index = np.arange(standardized.shape[1], dtype=np.int64)
        selected_gap = standardized[stored_step, candidate_index] - standardized.min(axis=0)
        largest_gap = float(np.max(selected_gap))
        audit.error("standardized_argmin_selected_gap", largest_gap)
        audit.check(
            bool(np.all(selected_gap <= 5.0e-7)),
            "standardized_argmin_recompute",
            h5_path,
            f"exact_match={np.array_equal(standardized_argmin, stored_step)}, max_selected_gap={largest_gap}",
        )
    return {"candidate_count": int(target.shape[0]), "min_at_t0": int(np.count_nonzero(standardized_argmin == 0))}


def audit_fixed(
    audit: Audit,
    dataset: dict[str, np.ndarray],
    partitions: dict[int, str],
    h5_path: Path,
    manifest: dict[str, Any],
    expected_partition: str,
    latent_std: np.ndarray,
    source_rows_seen: set[int],
) -> dict[str, int]:
    source_row = int(manifest["source_global_row"])
    goal_row = int(manifest["goal_global_row"])
    source_rows_seen.add(source_row)
    expected_source = np.asarray(dataset["state"][source_row], dtype=np.float32)
    expected_goal = np.asarray(dataset["state"][goal_row], dtype=np.float32)
    episode = int(dataset["episode_idx"][source_row])
    goal_episode = int(dataset["episode_idx"][goal_row])
    audit.check(partitions.get(episode) == expected_partition, "fixed_source_partition", h5_path,
                f"episode={episode}, got={partitions.get(episode)}")
    audit.check(partitions.get(goal_episode) == expected_partition, "fixed_goal_partition", h5_path,
                f"episode={goal_episode}, got={partitions.get(goal_episode)}")
    audit.check(episode == int(manifest["episode_id"]) == goal_episode, "fixed_episode_mapping", h5_path)
    audit.check(int(dataset["step_idx"][goal_row]) - int(dataset["step_idx"][source_row]) == 75,
                "fixed_d75_query_mapping", h5_path)

    with h5py.File(h5_path, "r") as handle:
        source_state = np.asarray(handle["source_state"][:], dtype=np.float32)
        goal_state = np.asarray(handle["goal_state"][:], dtype=np.float32)
        state_t0 = np.asarray(handle["state_trace"][0], dtype=np.float32)
        expected_source_batch = np.broadcast_to(expected_source, source_state.shape)
        expected_goal_batch = np.broadcast_to(expected_goal, goal_state.shape)
        err = max_abs(source_state, expected_source_batch)
        audit.error("fixed_source_state_vs_dataset", err)
        audit.check(np.array_equal(source_state, expected_source_batch), "fixed_source_state_vs_dataset", h5_path,
                    f"max_abs={err}")
        err = max_abs(goal_state, expected_goal_batch)
        audit.error("fixed_goal_state_vs_dataset", err)
        audit.check(np.array_equal(goal_state, expected_goal_batch), "fixed_goal_state_vs_dataset", h5_path,
                    f"max_abs={err}")
        err = max_abs(state_t0, source_state)
        audit.error("fixed_trace_t0_vs_source", err)
        audit.check(np.array_equal(state_t0, source_state), "fixed_trace_t0_vs_source", h5_path,
                    f"max_abs={err}")
        slots = np.asarray(handle["candidate_slot"][:], dtype=np.int64)
        expected_slots = np.arange(int(manifest["candidate_slice"][0]), int(manifest["candidate_slice"][1]))
        audit.check(np.array_equal(slots, expected_slots), "fixed_candidate_slots", h5_path)
        return audit_common_latent_trace(audit, handle, h5_path, latent_std)


def audit_real(
    audit: Audit,
    dataset: dict[str, np.ndarray],
    partitions: dict[int, str],
    h5_path: Path,
    manifest: dict[str, Any],
    expected_partition: str,
    latent_std: np.ndarray,
    source_rows_seen: set[int],
) -> dict[str, int]:
    with h5py.File(h5_path, "r") as handle:
        source_rows = np.asarray(handle["source_global_row"][:], dtype=np.int64)
        target_rows = np.asarray(handle["target_global_row"][:], dtype=np.int64)
        source_rows_seen.update(int(value) for value in source_rows)
        source_episode = np.asarray(handle["source_episode_id"][:], dtype=np.int64)
        target_episode = np.asarray(handle["target_episode_id"][:], dtype=np.int64)
        source_step = np.asarray(handle["source_step"][:], dtype=np.int64)
        target_step = np.asarray(handle["target_step"][:], dtype=np.int64)
        target_state = np.asarray(handle["target_state"][:], dtype=np.float32)
        state_trace = np.asarray(handle["state_trace"][:], dtype=np.float32)

        expected_source = np.asarray(dataset["state"][source_rows], dtype=np.float32)
        expected_target = np.asarray(dataset["state"][target_rows], dtype=np.float32)
        dataset_source_episode = np.asarray(dataset["episode_idx"][source_rows], dtype=np.int64)
        dataset_target_episode = np.asarray(dataset["episode_idx"][target_rows], dtype=np.int64)
        dataset_source_step = np.asarray(dataset["step_idx"][source_rows], dtype=np.int64)
        dataset_target_step = np.asarray(dataset["step_idx"][target_rows], dtype=np.int64)

        err = max_abs(state_trace[0], expected_source)
        audit.error("real_trace_t0_vs_dataset", err)
        audit.check(np.array_equal(state_trace[0], expected_source), "real_trace_t0_vs_dataset", h5_path,
                    f"max_abs={err}")
        err = max_abs(target_state, expected_target)
        audit.error("real_target_state_vs_dataset", err)
        audit.check(np.array_equal(target_state, expected_target), "real_target_state_vs_dataset", h5_path,
                    f"max_abs={err}")
        audit.check(np.array_equal(source_episode, dataset_source_episode), "real_source_episode_mapping", h5_path)
        audit.check(np.array_equal(target_episode, dataset_target_episode), "real_target_episode_mapping", h5_path)
        audit.check(np.array_equal(source_step, dataset_source_step), "real_source_step_mapping", h5_path)
        audit.check(np.array_equal(target_step, dataset_target_step), "real_target_step_mapping", h5_path)
        source_partition_ok = all(partitions.get(int(ep)) == expected_partition for ep in source_episode)
        target_partition_ok = all(partitions.get(int(ep)) == expected_partition for ep in target_episode)
        audit.check(source_partition_ok, "real_source_partition", h5_path)
        audit.check(target_partition_ok, "real_target_partition", h5_path)

        stratum = int(manifest["stratum_index"])
        if stratum == 0:
            audit.check(np.array_equal(source_episode, target_episode), "real_same_trajectory_episode", h5_path)
            audit.check(np.array_equal(target_step - source_step, np.full_like(source_step, 25)),
                        "real_same_trajectory_d25", h5_path)
        elif stratum == 1:
            audit.check(bool(np.all(source_episode != target_episode)), "real_cross_trajectory_episode", h5_path)
        else:
            audit.check(False, "real_stratum_value", h5_path, str(stratum))

        block_position_error = np.linalg.norm(state_trace[:, :, 2:4] - target_state[None, :, 2:4], axis=-1)
        joint_position_error = np.linalg.norm(state_trace[:, :, :4] - target_state[None, :, :4], axis=-1)
        angle_error = wrapped_angle_error(state_trace[:, :, 4], target_state[None, :, 4])
        primary_trace = (block_position_error < POSITION_TOLERANCE) & (angle_error < ANGLE_TOLERANCE)
        released_trace = (joint_position_error < POSITION_TOLERANCE) & (angle_error < ANGLE_TOLERANCE)
        for name, recomputed in (
            ("block_position_error_trace", block_position_error),
            ("agent_block_position_error_trace", joint_position_error),
            ("wrapped_block_angle_error_trace", angle_error),
        ):
            stored = np.asarray(handle[name][:])
            err = max_abs(recomputed, stored)
            audit.error(name, err)
            audit.check(allclose(recomputed, stored), f"{name}_recompute", h5_path, f"max_abs={err}")
        audit.check(np.array_equal(primary_trace, np.asarray(handle["primary_success_trace"][:], dtype=np.bool_)),
                    "primary_success_trace_recompute", h5_path)
        audit.check(np.array_equal(primary_trace.any(axis=0), np.asarray(handle["primary_attained"][:], dtype=np.bool_)),
                    "primary_attained_recompute", h5_path)
        audit.check(np.array_equal(released_trace, np.asarray(handle["agent_included_success_trace"][:], dtype=np.bool_)),
                    "released_success_trace_recompute", h5_path)
        audit.check(np.array_equal(released_trace.any(axis=0), np.asarray(handle["agent_included_attained"][:], dtype=np.bool_)),
                    "released_attained_recompute", h5_path)
        # The released environment success array intentionally excludes t=0.
        audit.check(
            np.array_equal(released_trace[1:].any(axis=0),
                           np.asarray(handle["released_environment_success_steps_1_to_25"][:], dtype=np.bool_)),
            "released_steps_1_to_25_recompute", h5_path,
        )
        latent_summary = audit_common_latent_trace(audit, handle, h5_path, latent_std)
        latent_summary.update(
            {
                "primary_count": int(np.count_nonzero(primary_trace.any(axis=0))),
                "primary_t0_count": int(np.count_nonzero(primary_trace[0])),
                "released_count": int(np.count_nonzero(released_trace.any(axis=0))),
                "released_t0_count": int(np.count_nonzero(released_trace[0])),
            }
        )
        return latent_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--stats-npz", type=Path, required=True)
    for key in EXPECTED_ROOTS:
        parser.add_argument(f"--{key.replace('_', '-')}-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--max-failures", type=int, default=100)
    parser.add_argument("--skip-hashes", action="store_true")
    args = parser.parse_args()

    started = time.time()
    audit = Audit(args.max_failures)
    partitions = load_partitions(args.partition_manifest)
    with np.load(args.stats_npz, allow_pickle=False) as stats:
        latent_std = np.asarray(stats["std"], dtype=np.float32)
    if latent_std.shape != (LATENT_DIM,) or not np.isfinite(latent_std).all() or np.any(latent_std <= 0):
        raise RuntimeError("invalid P1 latent standard deviation")

    roots = {key: getattr(args, f"{key}_root") for key in EXPECTED_ROOTS}
    root_summaries: dict[str, Any] = {}
    source_rows_seen: set[int] = set()
    all_source_rows_by_root: dict[str, set[int]] = {}
    with h5py.File(args.dataset, "r") as dataset_handle:
        dataset = {
            "state": np.asarray(dataset_handle["state"][:], dtype=np.float32),
            "episode_idx": np.asarray(dataset_handle["episode_idx"][:], dtype=np.int64),
            "step_idx": np.asarray(dataset_handle["step_idx"][:], dtype=np.int64),
        }
    for key, (expected_partition, kind, expected_count) in EXPECTED_ROOTS.items():
        root = roots[key]
        files = sorted(root.rglob("executions.h5"))
        audit.check(len(files) == expected_count, "execution_file_count", root,
                    f"got={len(files)}, expected={expected_count}")
        counters = Counter()
        root_rows: set[int] = set()
        coverage: set[tuple[int, int, int]] = set()
        for index, h5_path in enumerate(files, start=1):
            manifest_path = h5_path.with_name("manifest.json")
            audit.check(manifest_path.is_file(), "manifest_exists", h5_path)
            if not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            audit.check(manifest.get("status") == "ok", "manifest_status", manifest_path)
            classification = str(manifest.get("classification", ""))
            audit.check(classification.startswith(expected_partition.lower()), "manifest_partition_classification",
                        manifest_path, classification)
            manifest_partition = manifest.get("partition")
            audit.check(manifest_partition in (None, expected_partition), "manifest_partition_field", manifest_path,
                        str(manifest_partition))
            if not args.skip_hashes:
                verify_manifest_hash(audit, manifest, h5_path)
            if kind == "fixed":
                summary = audit_fixed(audit, dataset, partitions, h5_path, manifest,
                                      expected_partition, latent_std, root_rows)
                coverage.add((-1, int(manifest["pool_index"]), int(manifest["repeat_index"])))
            else:
                summary = audit_real(audit, dataset, partitions, h5_path, manifest,
                                     expected_partition, latent_std, root_rows)
                coverage.add((int(manifest["stratum_index"]), int(manifest["pool_index"]),
                              int(manifest["repeat_index"])))
                for name in ("primary_count", "primary_t0_count", "released_count", "released_t0_count"):
                    counters[name] += summary.get(name, 0)
            counters["candidate_count"] += summary["candidate_count"]
            counters["latent_min_at_t0"] += summary["min_at_t0"]
            if index % 50 == 0:
                print(f"audited {key}: {index}/{len(files)}", flush=True)
        if kind == "fixed":
            pools = expected_count // 5
            expected_coverage = {(-1, pool, repeat) for pool in range(pools) for repeat in range(5)}
        else:
            pools = expected_count // (2 * 5)
            expected_coverage = {(stratum, pool, repeat) for stratum in range(2)
                                 for pool in range(pools) for repeat in range(5)}
        audit.check(coverage == expected_coverage, "execution_pool_repeat_coverage", root,
                    f"missing={len(expected_coverage - coverage)}, extra={len(coverage - expected_coverage)}")
        all_source_rows_by_root[key] = root_rows
        source_rows_seen.update(root_rows)
        root_summaries[key] = {
            "root": str(root),
            "execution_files": len(files),
            "unique_source_rows": len(root_rows),
            **{name: int(value) for name, value in sorted(counters.items())},
        }

    # Development and confirmation source episodes must be disjoint.
    p2_episodes = set()
    p3_episodes = set()
    for key in ("p2_fixed", "p2_real"):
        rows = np.asarray(sorted(all_source_rows_by_root[key]), dtype=np.int64)
        p2_episodes.update(int(value) for value in dataset["episode_idx"][rows])
    for key in ("p3_fixed", "p3_real"):
        rows = np.asarray(sorted(all_source_rows_by_root[key]), dtype=np.int64)
        p3_episodes.update(int(value) for value in dataset["episode_idx"][rows])
    audit.check(p2_episodes.isdisjoint(p3_episodes), "p2_p3_source_episode_disjoint", args.partition_manifest,
                f"overlap={len(p2_episodes & p3_episodes)}")

    failed_checks = int(sum(value for name, value in audit.checks.items() if name.endswith(":failed")))
    result = {
        "status": "ok" if failed_checks == 0 else "failed",
        "classification": "independent_pusht_execution_lineage_audit",
        "read_only": True,
        "inputs": {
            "dataset": str(args.dataset),
            "partition_manifest": str(args.partition_manifest),
            "stats_npz": str(args.stats_npz),
            "roots": {key: str(path) for key, path in roots.items()},
        },
        "checks": dict(sorted(audit.checks.items())),
        "failed_check_count": failed_checks,
        "failures": audit.failures,
        "max_numeric_recompute_error": dict(sorted(audit.max_errors.items())),
        "root_summaries": root_summaries,
        "source_episode_overlap": {
            "p2_episode_count": len(p2_episodes),
            "p3_episode_count": len(p3_episodes),
            "intersection_count": len(p2_episodes & p3_episodes),
        },
        "known_reset_semantics_not_resolved_by_this_audit": {
            "issue": "released PushT _set_state advances physics by dt=0.01 before the helper overwrites world.infos",
            "consequence": "stored t=0 equality proves reported-row synchronization but not exact internal simulator state",
            "required_companion_test": "direct post-_set_state internal observation probe",
        },
        "elapsed_seconds": time.time() - started,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_json.with_name(f".{args.output_json.name}.partial-{os.getpid()}")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.output_json)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
