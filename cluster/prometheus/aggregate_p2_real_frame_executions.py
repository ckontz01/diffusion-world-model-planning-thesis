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


STRATA = ("same_trajectory_delta25", "cross_trajectory")
STRATUM_COUNT = len(STRATA)
REPEAT_SEEDS = (1070413377, 951166590, 4200525716, 38670800, 2537523285)
REPEAT_COUNT = len(REPEAT_SEEDS)
CANDIDATE_COUNT = 64
TRACE_STEPS = 26
LATENT_DIM = 192
DELTA_GRID = np.logspace(np.log10(0.05), np.log10(1.0), 10)


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
        path = Path(raw_path.lstrip("* "))
        if not path.is_absolute():
            path = directory / path
        if path.resolve().parent != directory.resolve():
            raise RuntimeError(f"checksum path escapes execution directory: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid file: {path}")
        found[path.name] = digest
    expected = {"executions.h5", "manifest.json", "provenance.txt"}
    if set(found) != expected:
        raise RuntimeError(f"unexpected checksum inventory in {directory}: {sorted(found)}")
    return found


def first_true_step(trace: np.ndarray) -> np.ndarray:
    any_true = trace.any(axis=0)
    result = np.argmax(trace, axis=0).astype(np.int64)
    result[~any_true] = -1
    return result


def wrapped_angle_error(value: np.ndarray, target: np.ndarray) -> np.ndarray:
    difference = np.abs(value - target) % (2.0 * np.pi)
    return np.minimum(difference, 2.0 * np.pi - difference)


def confusion_and_kappa(reference: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    reference = np.asarray(reference, dtype=np.bool_).reshape(-1)
    predicted = np.asarray(predicted, dtype=np.bool_).reshape(-1)
    if reference.shape != predicted.shape or reference.size == 0:
        raise RuntimeError("invalid arrays for Cohen's kappa")
    tp = int(np.sum(reference & predicted))
    tn = int(np.sum(~reference & ~predicted))
    fp = int(np.sum(~reference & predicted))
    fn = int(np.sum(reference & ~predicted))
    count = int(reference.size)
    observed = (tp + tn) / count
    reference_positive = (tp + fn) / count
    predicted_positive = (tp + fp) / count
    expected = (
        reference_positive * predicted_positive
        + (1.0 - reference_positive) * (1.0 - predicted_positive)
    )
    denominator = 1.0 - expected
    kappa = float("nan") if denominator <= 0.0 else (observed - expected) / denominator
    return {
        "count": count,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "reference_prevalence": reference_positive,
        "predicted_prevalence": predicted_positive,
        "observed_agreement": observed,
        "expected_agreement": expected,
        "cohen_kappa": kappa,
    }


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
    parser.add_argument("--frozen-tolerance-h5", type=Path)
    parser.add_argument("--frozen-tolerance-manifest", type=Path)
    args = parser.parse_args()

    partition = args.partition
    partition_key = partition.lower()
    environment = args.environment
    prefix_name = "tworoom_" if environment == "tworoom" else ""
    state_dim = 2 if environment == "tworoom" else 7
    pool_count = 12 if partition == "P2" else 24
    candidate_classification = f"{prefix_name}{partition_key}_real_frame_candidate_pools"
    execution_classification = f"{prefix_name}{partition_key}_real_frame_candidate_execution"
    output_classification = (
        f"{prefix_name}p2_real_frame_attainment_and_tolerance"
        if partition == "P2"
        else f"{prefix_name}p3_real_frame_attainment_and_frozen_tolerance_agreement"
    )
    output_partition = "P2-development-only" if partition == "P2" else "P3-locked"
    expected_low = (
        (1200, 30, 150, 2, 1, 5, 16)
        if environment == "pusht"
        else (300, 30, 10, 5, 1, 5, 16)
    )

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit(f"refusing to overwrite {partition} real-frame aggregate")
    if partition == "P3" and (
        args.frozen_tolerance_h5 is None or args.frozen_tolerance_manifest is None
    ):
        raise SystemExit("P3 aggregation requires the frozen P2 tolerance artifacts")
    started = time.time()

    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    if candidate_manifest.get("status") != "ok" or candidate_manifest.get(
        "classification"
    ) != candidate_classification or candidate_manifest.get("partition") != partition or candidate_manifest.get(
        "environment", "pusht"
    ) != environment:
        raise RuntimeError(
            f"input is not the frozen {partition} real-frame candidate pool"
        )
    if (
        int(candidate_manifest.get("pools_per_stratum", -1)) != pool_count
        or int(candidate_manifest.get("candidates_per_pool", -1)) != CANDIDATE_COUNT
    ):
        raise RuntimeError("real-frame candidate coverage changed")
    if tuple(candidate_manifest.get("strata", [])) != STRATA:
        raise RuntimeError("real-frame candidate stratum names changed")
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
        candidate_slot = np.asarray(candidates["candidate_slot"][:], dtype=np.int64)
        pool_id = np.asarray(candidates["pool_id"][:], dtype=np.int64)
        source_rows = np.asarray(candidates["source_global_row"][:], dtype=np.int64)
        target_rows = np.asarray(candidates["target_global_row"][:], dtype=np.int64)
        source_episode = np.asarray(candidates["source_episode_id"][:], dtype=np.int64)
        target_episode = np.asarray(candidates["target_episode_id"][:], dtype=np.int64)
        source_step = np.asarray(candidates["source_step"][:], dtype=np.int64)
        target_step = np.asarray(candidates["target_step"][:], dtype=np.int64)
        source_latent = np.asarray(candidates["source_latent"][:], dtype=np.float32)
        target_latent = np.asarray(candidates["target_latent"][:], dtype=np.float32)
        source_state = np.asarray(candidates["source_state"][:], dtype=np.float32)
        target_state = np.asarray(candidates["target_state"][:], dtype=np.float32)
        initial_primary = np.asarray(candidates["initial_primary_success"][:], dtype=np.bool_)
        initial_agent = (
            np.asarray(candidates["initial_agent_included_success"][:], dtype=np.bool_)
            if environment == "pusht"
            else initial_primary.copy()
        )

    candidate_shape = (STRATUM_COUNT, pool_count, CANDIDATE_COUNT)
    if candidate_slot.shape != candidate_shape or not np.array_equal(
        candidate_slot, np.broadcast_to(np.arange(CANDIDATE_COUNT), candidate_shape)
    ):
        raise RuntimeError("candidate slots are incomplete or unordered")
    if pool_id.shape != (STRATUM_COUNT, pool_count) or not np.array_equal(
        pool_id, np.broadcast_to(np.arange(pool_count), pool_id.shape)
    ):
        raise RuntimeError("pool IDs are incomplete or unordered")
    if source_latent.shape != candidate_shape + (LATENT_DIM,) or target_latent.shape != (
        candidate_shape + (LATENT_DIM,)
    ):
        raise RuntimeError("unexpected candidate latent shape")
    if source_state.shape != candidate_shape + (state_dim,) or target_state.shape != (
        candidate_shape + (state_dim,)
    ):
        raise RuntimeError("unexpected candidate state shape")
    if not np.array_equal(source_episode[0], target_episode[0]) or not np.all(
        target_step[0] - source_step[0] == 25
    ):
        raise RuntimeError("same-trajectory candidate stratum changed")
    if np.any(source_episode[1] == target_episode[1]):
        raise RuntimeError("cross-trajectory stratum contains same-episode pairs")

    prefix = (STRATUM_COUNT, pool_count, REPEAT_COUNT)
    per_candidate = prefix + (CANDIDATE_COUNT,)
    per_trace = prefix + (TRACE_STEPS, CANDIDATE_COUNT)
    state_trace = np.empty(per_trace + (state_dim,), dtype=np.float32)
    raw_rmse_trace = np.empty(per_trace, dtype=np.float32)
    standardized_rmse_trace = np.empty(per_trace, dtype=np.float32)
    minimum_raw_rmse = np.empty(per_candidate, dtype=np.float32)
    minimum_raw_step = np.empty(per_candidate, dtype=np.int64)
    minimum_standardized_rmse = np.empty(per_candidate, dtype=np.float32)
    minimum_standardized_step = np.empty(per_candidate, dtype=np.int64)
    block_position_error = np.empty(per_trace, dtype=np.float32)
    agent_block_position_error = np.empty(per_trace, dtype=np.float32)
    angle_error = np.empty(per_trace, dtype=np.float32)
    primary_success_trace = np.empty(per_trace, dtype=np.bool_)
    agent_success_trace = np.empty(per_trace, dtype=np.bool_)
    primary_attained = np.empty(per_candidate, dtype=np.bool_)
    agent_attained = np.empty(per_candidate, dtype=np.bool_)
    environment_success = np.empty(per_candidate, dtype=np.bool_)
    execution_manifest_sha = np.empty(prefix, dtype="S64")
    execution_h5_sha = np.empty(prefix, dtype="S64")
    task_records: list[dict[str, Any]] = []
    stats_sha: str | None = None

    for stratum in range(STRATUM_COUNT):
        for pool in range(pool_count):
            for repeat, expected_seed in enumerate(REPEAT_SEEDS):
                directory = (
                    args.execution_root
                    / f"stratum-{stratum}"
                    / f"pool-{pool:02d}-repeat-{repeat}"
                )
                inventory = verify_checksum_inventory(directory)
                manifest_path = directory / "manifest.json"
                execution_path = directory / "executions.h5"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest_partition = manifest.get("partition")
                if (
                    manifest.get("status") != "ok"
                    or manifest.get("classification") != execution_classification
                    or manifest.get("environment", "pusht") != environment
                    or (
                        partition == "P2"
                        and manifest_partition not in (None, "P2")
                    )
                    or (partition == "P3" and manifest_partition != "P3")
                ):
                    raise RuntimeError(f"invalid execution classification: {directory}")
                identity = (
                    manifest["stratum_index"],
                    manifest["stratum_name"],
                    manifest["pool_index"],
                    manifest["repeat_index"],
                )
                if identity != (stratum, STRATA[stratum], pool, repeat):
                    raise RuntimeError(f"stratum/pool/repeat mismatch: {directory}")
                if manifest["planner_seed"] != expected_seed or manifest[
                    "environment_seed"
                ] != expected_seed:
                    raise RuntimeError(f"repeat seed mismatch: {directory}")
                if tuple(manifest["repeat_seeds"]) != REPEAT_SEEDS:
                    raise RuntimeError(f"frozen repeat-seed list mismatch: {directory}")
                if manifest["candidate_slice"] != [0, CANDIDATE_COUNT] or manifest[
                    "candidate_count"
                ] != CANDIDATE_COUNT:
                    raise RuntimeError(f"candidate coverage mismatch: {directory}")
                trace_spec = manifest.get("attainment_trace", {})
                if (
                    trace_spec.get("steps_inclusive") != [0, 25]
                    or trace_spec.get("record_count") != TRACE_STEPS
                    or trace_spec.get("latent_diagnostic")
                    != "minimum P1-standardized latent RMSE over steps 0..25"
                ):
                    raise RuntimeError(f"attainment trace protocol mismatch: {directory}")
                low = manifest["low_planner"]
                low_tuple = (
                    low["num_samples"],
                    low["n_steps"],
                    low["topk"],
                    low["horizon_tokens"],
                    low["receding_horizon_tokens"],
                    low["action_block_primitive_steps"],
                    low["cost_environment_chunk_size"],
                )
                if low_tuple != expected_low:
                    raise RuntimeError(f"low-level planner mismatch: {directory}")
                if not low["common_random_numbers_across_candidates"]:
                    raise RuntimeError(f"common-random-number flag is false: {directory}")
                solver_test = manifest["solver_equivalence_self_test"]
                if solver_test["status"] != "ok" or abs(solver_test["max_abs"]) > 1.0e-7:
                    raise RuntimeError(f"solver equivalence test failed: {directory}")
                if manifest["inputs"]["candidate_h5_sha256"] != candidate_sha:
                    raise RuntimeError(f"candidate input hash mismatch: {directory}")
                task_stats_sha = manifest["inputs"]["statistics"]["stats_npz_sha256"]
                if stats_sha is None:
                    stats_sha = task_stats_sha
                elif stats_sha != task_stats_sha:
                    raise RuntimeError("P1 statistics hash changes across tasks")
                if sha256_file(execution_path) != manifest["output_h5_sha256"]:
                    raise RuntimeError(f"execution HDF5 differs from manifest: {directory}")

                with h5py.File(execution_path, "r") as execution:
                    if execution.attrs["classification"] != execution_classification:
                        raise RuntimeError(f"HDF5 classification mismatch: {directory}")
                    if execution.attrs.get("environment", "pusht") != environment:
                        raise RuntimeError(f"HDF5 environment mismatch: {directory}")
                    h5_identity = (
                        int(execution.attrs["stratum_index"]),
                        str(execution.attrs["stratum_name"]),
                        int(execution.attrs["pool_index"]),
                        int(execution.attrs["repeat_index"]),
                        int(execution.attrs["planner_seed"]),
                    )
                    if h5_identity != (
                        stratum,
                        STRATA[stratum],
                        pool,
                        repeat,
                        expected_seed,
                    ):
                        raise RuntimeError(f"HDF5 task identity mismatch: {directory}")
                    if not np.array_equal(
                        execution["candidate_slot"][:], np.arange(CANDIDATE_COUNT)
                    ):
                        raise RuntimeError(f"candidate slots changed: {directory}")
                    expected_values = {
                        "source_global_row": source_rows[stratum, pool],
                        "target_global_row": target_rows[stratum, pool],
                        "source_episode_id": source_episode[stratum, pool],
                        "target_episode_id": target_episode[stratum, pool],
                        "source_step": source_step[stratum, pool],
                        "target_step": target_step[stratum, pool],
                        "target_latent": target_latent[stratum, pool],
                        "target_state": target_state[stratum, pool],
                    }
                    for name, expected in expected_values.items():
                        if not np.array_equal(execution[name][:], expected):
                            raise RuntimeError(f"{name} changed: {directory}")

                    index = (stratum, pool, repeat)
                    state_trace[index] = np.asarray(execution["state_trace"][:], dtype=np.float32)
                    raw_rmse_trace[index] = np.asarray(
                        execution["raw_latent_rmse_trace"][:], dtype=np.float32
                    )
                    standardized_rmse_trace[index] = np.asarray(
                        execution["standardized_latent_rmse_trace"][:], dtype=np.float32
                    )
                    minimum_raw_rmse[index] = np.asarray(
                        execution["minimum_raw_latent_rmse"][:], dtype=np.float32
                    )
                    minimum_raw_step[index] = np.asarray(
                        execution["minimum_raw_latent_step"][:], dtype=np.int64
                    )
                    minimum_standardized_rmse[index] = np.asarray(
                        execution["minimum_standardized_latent_rmse"][:], dtype=np.float32
                    )
                    minimum_standardized_step[index] = np.asarray(
                        execution["minimum_standardized_latent_step"][:], dtype=np.int64
                    )
                    if environment == "pusht":
                        block_position_error[index] = np.asarray(
                            execution["block_position_error_trace"][:], dtype=np.float32
                        )
                        agent_block_position_error[index] = np.asarray(
                            execution["agent_block_position_error_trace"][:], dtype=np.float32
                        )
                        angle_error[index] = np.asarray(
                            execution["wrapped_block_angle_error_trace"][:], dtype=np.float32
                        )
                    else:
                        block_position_error[index] = np.asarray(
                            execution["agent_position_error_trace"][:], dtype=np.float32
                        )
                        agent_block_position_error[index] = block_position_error[index]
                        angle_error[index].fill(0.0)
                    primary_success_trace[index] = np.asarray(
                        execution["primary_success_trace"][:], dtype=np.bool_
                    )
                    agent_success_trace[index] = (
                        np.asarray(execution["agent_included_success_trace"][:], dtype=np.bool_)
                        if environment == "pusht"
                        else primary_success_trace[index]
                    )
                    primary_attained[index] = np.asarray(
                        execution["primary_attained"][:], dtype=np.bool_
                    )
                    agent_attained[index] = (
                        np.asarray(execution["agent_included_attained"][:], dtype=np.bool_)
                        if environment == "pusht"
                        else primary_attained[index]
                    )
                    environment_success[index] = np.asarray(
                        execution["released_environment_success_steps_1_to_25"][:],
                        dtype=np.bool_,
                    )

                    if not np.array_equal(
                        state_trace[index][0], source_state[stratum, pool]
                    ):
                        raise RuntimeError(f"state trace does not start at source: {directory}")
                    if not np.array_equal(
                        minimum_raw_rmse[index], raw_rmse_trace[index].min(axis=0)
                    ) or not np.array_equal(
                        minimum_raw_step[index], raw_rmse_trace[index].argmin(axis=0)
                    ):
                        raise RuntimeError(f"raw latent minimum mismatch: {directory}")
                    if not np.array_equal(
                        minimum_standardized_rmse[index],
                        standardized_rmse_trace[index].min(axis=0),
                    ) or not np.array_equal(
                        minimum_standardized_step[index],
                        standardized_rmse_trace[index].argmin(axis=0),
                    ):
                        raise RuntimeError(f"standardized latent minimum mismatch: {directory}")
                    if not np.array_equal(
                        primary_attained[index], primary_success_trace[index].any(axis=0)
                    ) or not np.array_equal(
                        agent_attained[index], agent_success_trace[index].any(axis=0)
                    ):
                        raise RuntimeError(f"physical any-step label mismatch: {directory}")
                    expected_success_trace = (
                        agent_success_trace[index]
                        if environment == "pusht"
                        else primary_success_trace[index]
                    )
                    if not np.array_equal(
                        environment_success[index], expected_success_trace[1:].any(axis=0)
                    ):
                        raise RuntimeError(f"released success mismatch: {directory}")
                    if not np.array_equal(
                        execution["primary_first_attainment_step"][:],
                        first_true_step(primary_success_trace[index]),
                    ) or (
                        environment == "pusht"
                        and not np.array_equal(
                            execution["agent_included_first_attainment_step"][:],
                            first_true_step(agent_success_trace[index]),
                        )
                    ):
                        raise RuntimeError(f"first-attainment step mismatch: {directory}")

                execution_manifest_sha[index] = sha256_file(manifest_path).encode()
                execution_h5_sha[index] = inventory["executions.h5"].encode()
                task_records.append(
                    {
                        "stratum_index": stratum,
                        "pool_index": pool,
                        "repeat_index": repeat,
                        "seed": expected_seed,
                        "directory": str(directory),
                        "manifest_sha256": execution_manifest_sha[index].decode(),
                        "execution_h5_sha256": execution_h5_sha[index].decode(),
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

    if not all(
        np.isfinite(value).all()
        for value in (
            state_trace,
            raw_rmse_trace,
            standardized_rmse_trace,
            block_position_error,
            agent_block_position_error,
            angle_error,
        )
    ):
        raise RuntimeError("non-finite real-frame aggregate output")
    target_for_trace = target_state[:, :, None, None, :, :]
    if environment == "pusht":
        recomputed_block = np.linalg.norm(
            state_trace[..., 2:4] - target_for_trace[..., 2:4], axis=-1
        )
        recomputed_agent = np.linalg.norm(
            state_trace[..., :4] - target_for_trace[..., :4], axis=-1
        )
        recomputed_angle = wrapped_angle_error(
            state_trace[..., 4], target_for_trace[..., 4]
        )
        if not np.allclose(block_position_error, recomputed_block, rtol=1e-6, atol=1e-6):
            raise RuntimeError("block-position error trace does not reproduce states")
        if not np.allclose(
            agent_block_position_error, recomputed_agent, rtol=1e-6, atol=1e-6
        ):
            raise RuntimeError("agent+block error trace does not reproduce states")
        if not np.allclose(angle_error, recomputed_angle, rtol=1e-6, atol=1e-6):
            raise RuntimeError("angle error trace does not reproduce states")
        if not np.array_equal(
            primary_success_trace,
            (block_position_error < 20.0) & (angle_error < np.pi / 9.0),
        ) or not np.array_equal(
            agent_success_trace,
            (agent_block_position_error < 20.0) & (angle_error < np.pi / 9.0),
        ):
            raise RuntimeError("PushT physical criteria do not reproduce continuous errors")
    else:
        recomputed_agent_position = np.linalg.norm(
            state_trace - target_for_trace, axis=-1
        )
        if not np.allclose(
            block_position_error, recomputed_agent_position, rtol=1e-6, atol=1e-6
        ):
            raise RuntimeError("TwoRoom agent-position error trace does not reproduce states")
        if not np.array_equal(primary_success_trace, block_position_error < 16.0):
            raise RuntimeError("TwoRoom physical criterion does not reproduce distances")
    if not np.array_equal(
        primary_success_trace[:, :, :, 0],
        np.broadcast_to(initial_primary[:, :, None], primary_success_trace[:, :, :, 0].shape),
    ):
        raise RuntimeError("primary t=0 status differs from frozen candidate diagnostic")
    if environment == "pusht" and not np.array_equal(
        agent_success_trace[:, :, :, 0],
        np.broadcast_to(initial_agent[:, :, None], agent_success_trace[:, :, :, 0].shape),
    ):
        raise RuntimeError("agent-included t=0 status differs from frozen candidate diagnostic")

    primary_count = primary_attained.sum(axis=2, dtype=np.int64)
    agent_count = agent_attained.sum(axis=2, dtype=np.int64)
    primary_label = primary_count >= 3
    agent_label = agent_count >= 3
    primary_rate = primary_count.astype(np.float32) / REPEAT_COUNT
    agent_rate = agent_count.astype(np.float32) / REPEAT_COUNT
    latent_attained_grid = minimum_standardized_rmse[None, ...] <= DELTA_GRID[
        :, None, None, None, None
    ]
    latent_count_grid = latent_attained_grid.sum(axis=3, dtype=np.int64)
    latent_label_grid = latent_count_grid >= 3
    latent_rate_grid = latent_count_grid.astype(np.float32) / REPEAT_COUNT

    grid_records: list[dict[str, Any]] = []
    combined_primary_kappa = np.empty(len(DELTA_GRID), dtype=np.float64)
    combined_agent_kappa = np.empty(len(DELTA_GRID), dtype=np.float64)
    per_stratum_primary_kappa = np.empty((len(DELTA_GRID), STRATUM_COUNT), dtype=np.float64)
    per_stratum_agent_kappa = np.empty_like(per_stratum_primary_kappa)
    for delta_index, delta in enumerate(DELTA_GRID):
        predicted = latent_label_grid[delta_index]
        primary_combined = confusion_and_kappa(primary_label, predicted)
        agent_combined = confusion_and_kappa(agent_label, predicted)
        combined_primary_kappa[delta_index] = primary_combined["cohen_kappa"]
        combined_agent_kappa[delta_index] = agent_combined["cohen_kappa"]
        strata_records: list[dict[str, Any]] = []
        for stratum in range(STRATUM_COUNT):
            primary_stratum = confusion_and_kappa(
                primary_label[stratum], predicted[stratum]
            )
            agent_stratum = confusion_and_kappa(agent_label[stratum], predicted[stratum])
            per_stratum_primary_kappa[delta_index, stratum] = primary_stratum[
                "cohen_kappa"
            ]
            per_stratum_agent_kappa[delta_index, stratum] = agent_stratum["cohen_kappa"]
            stratum_record = {
                "stratum_index": stratum,
                "stratum_name": STRATA[stratum],
                "primary": primary_stratum,
            }
            if environment == "pusht":
                stratum_record["agent_included_sensitivity"] = agent_stratum
            strata_records.append(stratum_record)
        grid_record = {
            "delta_index": delta_index,
            "delta": float(delta),
            "combined_primary": primary_combined,
            "per_stratum": strata_records,
        }
        if environment == "pusht":
            grid_record["combined_agent_included_sensitivity"] = agent_combined
        grid_records.append(grid_record)

    frozen_tolerance_inputs: dict[str, Any] | None = None
    if partition == "P2":
        finite = np.isfinite(combined_primary_kappa)
        if not finite.any():
            raise RuntimeError("Cohen's kappa is undefined for every tolerance")
        maximum = float(np.max(combined_primary_kappa[finite]))
        tied = np.flatnonzero(
            finite & np.isclose(combined_primary_kappa, maximum, rtol=0.0, atol=1e-15)
        )
        selected_index = int(tied[0])
        selected_delta = float(DELTA_GRID[selected_index])
    else:
        assert args.frozen_tolerance_h5 is not None
        assert args.frozen_tolerance_manifest is not None
        frozen_manifest = json.loads(
            args.frozen_tolerance_manifest.read_text(encoding="utf-8")
        )
        if (
            frozen_manifest.get("status") != "ok"
            or frozen_manifest.get("classification")
            != "p2_real_frame_attainment_and_tolerance"
            or frozen_manifest.get("partition") != "P2-development-only"
        ):
            raise RuntimeError("invalid frozen P2 tolerance manifest")
        if sha256_file(args.frozen_tolerance_h5) != frozen_manifest["output_h5_sha256"]:
            raise RuntimeError("frozen P2 tolerance HDF5 differs from its manifest")
        frozen_selection = frozen_manifest["latent_tolerance_selection"]
        selected_index = int(frozen_selection["selected_index"])
        selected_delta = float(frozen_selection["selected_delta"])
        if selected_index != 8 or not np.isclose(
            selected_delta, 0.7168711644368866, rtol=0.0, atol=1.0e-15
        ):
            raise RuntimeError("frozen P2 tolerance differs from the P3 lock")
        if not np.isclose(
            DELTA_GRID[selected_index], selected_delta, rtol=0.0, atol=1.0e-15
        ):
            raise RuntimeError("frozen P2 tolerance is absent from the declared grid")
        with h5py.File(args.frozen_tolerance_h5, "r") as frozen_h5:
            if (
                frozen_h5.attrs.get("classification")
                != "p2_real_frame_attainment_and_tolerance"
                or int(frozen_h5.attrs.get("selected_delta_index", -1))
                != selected_index
                or not np.isclose(
                    float(frozen_h5.attrs.get("selected_delta", np.nan)),
                    selected_delta,
                    rtol=0.0,
                    atol=1.0e-15,
                )
            ):
                raise RuntimeError("frozen P2 tolerance HDF5 metadata changed")
        frozen_tolerance_inputs = {
            "h5": str(args.frozen_tolerance_h5),
            "h5_sha256": frozen_manifest["output_h5_sha256"],
            "manifest": str(args.frozen_tolerance_manifest),
            "manifest_sha256": sha256_file(args.frozen_tolerance_manifest),
        }
    selected_latent_count = latent_count_grid[selected_index]
    selected_latent_rate = latent_rate_grid[selected_index]
    selected_latent_label = latent_label_grid[selected_index]

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = output_classification
            output.attrs["environment"] = environment
            output.attrs["partition"] = output_partition
            output.attrs["selected_delta"] = selected_delta
            output.attrs["selected_delta_index"] = selected_index
            output.create_dataset("candidate_slot", data=candidate_slot)
            output.create_dataset("pool_id", data=pool_id)
            output.create_dataset("source_global_row", data=source_rows)
            output.create_dataset("target_global_row", data=target_rows)
            output.create_dataset("source_episode_id", data=source_episode)
            output.create_dataset("target_episode_id", data=target_episode)
            output.create_dataset("source_step", data=source_step)
            output.create_dataset("target_step", data=target_step)
            output.create_dataset("source_latent", data=source_latent, compression="gzip")
            output.create_dataset("target_latent", data=target_latent, compression="gzip")
            output.create_dataset("source_state", data=source_state)
            output.create_dataset("target_state", data=target_state)
            output.create_dataset("repeat_seed", data=np.asarray(REPEAT_SEEDS, dtype=np.uint32))
            output.create_dataset("state_trace", data=state_trace, compression="gzip")
            output.create_dataset("raw_latent_rmse_trace", data=raw_rmse_trace)
            output.create_dataset(
                "standardized_latent_rmse_trace", data=standardized_rmse_trace
            )
            output.create_dataset("minimum_raw_latent_rmse", data=minimum_raw_rmse)
            output.create_dataset("minimum_raw_latent_step", data=minimum_raw_step)
            output.create_dataset(
                "minimum_standardized_latent_rmse", data=minimum_standardized_rmse
            )
            output.create_dataset(
                "minimum_standardized_latent_step", data=minimum_standardized_step
            )
            output.create_dataset("primary_success_trace", data=primary_success_trace)
            output.create_dataset("primary_attained_per_run", data=primary_attained)
            output.create_dataset("released_environment_success_per_run", data=environment_success)
            output.create_dataset("primary_attainment_count", data=primary_count)
            output.create_dataset("primary_attainment_rate", data=primary_rate)
            output.create_dataset("primary_label_at_least_3_of_5", data=primary_label)
            if environment == "pusht":
                output.create_dataset("block_position_error_trace", data=block_position_error)
                output.create_dataset("agent_block_position_error_trace", data=agent_block_position_error)
                output.create_dataset("wrapped_block_angle_error_trace", data=angle_error)
                output.create_dataset("agent_included_success_trace", data=agent_success_trace)
                output.create_dataset("agent_included_attained_per_run", data=agent_attained)
                output.create_dataset("agent_included_attainment_count", data=agent_count)
                output.create_dataset("agent_included_attainment_rate", data=agent_rate)
                output.create_dataset("agent_included_label_at_least_3_of_5", data=agent_label)
            else:
                output.create_dataset("agent_position_error_trace", data=block_position_error)
            output.create_dataset("delta_grid", data=DELTA_GRID)
            output.create_dataset("latent_attainment_count_grid", data=latent_count_grid)
            output.create_dataset("latent_attainment_rate_grid", data=latent_rate_grid)
            output.create_dataset("latent_label_grid_at_least_3_of_5", data=latent_label_grid)
            output.create_dataset("selected_latent_attainment_count", data=selected_latent_count)
            output.create_dataset("selected_latent_attainment_rate", data=selected_latent_rate)
            output.create_dataset("selected_latent_label_at_least_3_of_5", data=selected_latent_label)
            output.create_dataset("combined_primary_cohen_kappa_grid", data=combined_primary_kappa)
            output.create_dataset(
                "per_stratum_primary_cohen_kappa_grid", data=per_stratum_primary_kappa
            )
            if environment == "pusht":
                output.create_dataset("combined_agent_cohen_kappa_grid", data=combined_agent_kappa)
                output.create_dataset("per_stratum_agent_cohen_kappa_grid", data=per_stratum_agent_kappa)
            output.create_dataset("execution_manifest_sha256", data=execution_manifest_sha)
            output.create_dataset("execution_h5_sha256", data=execution_h5_sha)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_real_frame_aggregate_retained={partial_h5}")
        raise

    per_stratum_summary = []
    for stratum in range(STRATUM_COUNT):
        summary = {
            "stratum_index": stratum,
            "stratum_name": STRATA[stratum],
            "candidate_count": pool_count * CANDIDATE_COUNT,
            "primary_physical_prevalence": float(primary_label[stratum].mean()),
            "selected_latent_prevalence": float(selected_latent_label[stratum].mean()),
            "selected_primary_agreement": grid_records[selected_index]["per_stratum"][stratum]["primary"],
            "minimum_standardized_latent_rmse": quantiles(minimum_standardized_rmse[stratum]),
        }
        if environment == "pusht":
            summary["agent_included_physical_prevalence"] = float(agent_label[stratum].mean())
            summary["selected_agent_included_agreement"] = grid_records[selected_index]["per_stratum"][stratum]["agent_included_sensitivity"]
        per_stratum_summary.append(summary)

    tolerance_record = {
        "distance": "minimum P1-standardized latent RMSE over t=0..25",
        "per_run_comparison": "distance <= delta",
        "candidate_label": "latent criterion met in at least 3 of 5 executions",
        "grid": [float(value) for value in DELTA_GRID],
        "objective": (
            "maximum Cohen's kappa against primary physical labels over both P2 real-frame strata"
            if partition == "P2"
            else "evaluate the P2-frozen tolerance without reselection"
        ),
        "tie_break": "smaller delta" if partition == "P2" else "not applicable",
        "source": "selected on this environment's P2" if partition == "P2" else "frozen from this environment's P2 artifact",
        "selected_index": selected_index,
        "selected_delta": selected_delta,
        "selected_combined_primary": grid_records[selected_index]["combined_primary"],
        "grid_records": grid_records,
    }
    if environment == "pusht":
        tolerance_record["selected_combined_agent_included_sensitivity"] = grid_records[selected_index]["combined_agent_included_sensitivity"]
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
            "strata": list(STRATA),
            "pools_per_stratum": pool_count,
            "candidates_per_pool": CANDIDATE_COUNT,
            "repeats_per_candidate": REPEAT_COUNT,
            "repeat_seeds": list(REPEAT_SEEDS),
            "real_frame_candidates": STRATUM_COUNT * pool_count * CANDIDATE_COUNT,
            "candidate_executions": (
                STRATUM_COUNT * pool_count * CANDIDATE_COUNT * REPEAT_COUNT
            ),
        },
        "physical_labels": {
            "aggregation": "attained in at least 3 of 5 repeated executions",
            "primary": (
                "any t=0..25 with block position L2 < 20 pixels and wrapped block angle < pi/9"
                if environment == "pusht"
                else "minimum agent-position L2 over t=0..25 < 16 pixels"
            ),
            "sensitivity": (
                "any t=0..25 with joint agent+block position L2 < 20 and wrapped block angle < pi/9"
                if environment == "pusht"
                else None
            ),
        },
        (
            "latent_tolerance_selection"
            if partition == "P2"
            else "latent_tolerance_evaluation"
        ): tolerance_record,
        "per_stratum": per_stratum_summary,
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
            "stats_npz_sha256": stats_sha,
            "frozen_p2_tolerance": frozen_tolerance_inputs,
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
