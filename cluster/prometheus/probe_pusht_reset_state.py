#!/usr/bin/env python3
"""Measure the released PushT reset helper's hidden post-_set_state offset.

The thesis execution helper writes the requested dataset row into ``world.infos``
after calling the environment setter.  PushT's released setter itself advances
Pymunk by one 0.01 s step, so this probe reads the simulator directly and
quantifies any discrepancy that the info overwrite can hide.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

import gymnasium as gym
import h5py
import numpy as np
import stable_worldmodel  # noqa: F401 - registers swm/PushT-v1


POSITION_TOLERANCE = 20.0
ANGLE_TOLERANCE = math.pi / 9.0
DT = 0.01


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def wrapped_angle_error(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    raw = np.abs(a - b)
    return np.minimum(raw, 2.0 * np.pi - raw)


def summarize(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {"count": 0}
    return {
        "count": int(array.size),
        "min": float(array.min()),
        "median": float(np.median(array)),
        "mean": float(array.mean()),
        "p95": float(np.quantile(array, 0.95)),
        "p99": float(np.quantile(array, 0.99)),
        "max": float(array.max()),
    }


def collect_execution_files(roots: list[Path]) -> list[Path]:
    output: list[Path] = []
    for root in roots:
        output.extend(sorted(root.rglob("executions.h5")))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--execution-root", type=Path, action="append", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    started = time.time()
    files = collect_execution_files(args.execution_root)
    if not files:
        raise RuntimeError("no execution HDF5 files found")
    with h5py.File(args.dataset, "r") as dataset:
        states = np.asarray(dataset["state"][:], dtype=np.float64)

    # A cache key reproduces the exact state and environment seed used by an
    # execution.  Fixed-pool rows come from the manifest; real-frame rows are
    # stored per candidate in the HDF5 file.
    requested: set[tuple[int, int]] = set()
    real_records: list[tuple[Path, int, np.ndarray, np.ndarray]] = []
    classifications = Counter()
    for path in files:
        manifest = json.loads(path.with_name("manifest.json").read_text(encoding="utf-8"))
        seed = int(manifest["environment_seed"])
        classification = str(manifest["classification"])
        classifications[classification] += 1
        with h5py.File(path, "r") as handle:
            if "source_global_row" in handle:
                source_rows = np.asarray(handle["source_global_row"][:], dtype=np.int64)
                target_states = np.asarray(handle["target_state"][:], dtype=np.float64)
                real_records.append((path, seed, source_rows, target_states))
                requested.update((seed, int(row)) for row in source_rows)
            else:
                requested.add((seed, int(manifest["source_global_row"])))

    env = gym.make("swm/PushT-v1", render_mode="rgb_array")
    actual_by_key: dict[tuple[int, int], np.ndarray] = {}
    vector_l2: list[float] = []
    agent_position_l2: list[float] = []
    block_position_l2: list[float] = []
    angle_abs: list[float] = []
    velocity_l2: list[float] = []
    ballistic_residual_l2: list[float] = []
    exact_count = 0
    threshold_counts = Counter()
    try:
        for index, (seed, row) in enumerate(sorted(requested), start=1):
            desired = states[row]
            env.reset(seed=seed)
            unwrapped = env.unwrapped
            unwrapped._set_state(desired.copy())
            actual = np.asarray(unwrapped._get_obs(), dtype=np.float64)
            actual_by_key[(seed, row)] = actual
            difference = actual - desired
            total = float(np.linalg.norm(difference))
            agent = float(np.linalg.norm(difference[:2]))
            block = float(np.linalg.norm(difference[2:4]))
            angle = float(wrapped_angle_error(actual[4:5], desired[4:5])[0])
            velocity = float(np.linalg.norm(difference[5:7]))
            ballistic = desired.copy()
            ballistic[:2] += desired[5:7] * DT
            ballistic[4] %= 2.0 * np.pi
            ballistic_residual = float(np.linalg.norm(actual - ballistic))
            vector_l2.append(total)
            agent_position_l2.append(agent)
            block_position_l2.append(block)
            angle_abs.append(angle)
            velocity_l2.append(velocity)
            ballistic_residual_l2.append(ballistic_residual)
            if np.array_equal(actual.astype(np.float32), desired.astype(np.float32)):
                exact_count += 1
            for threshold in (1e-6, 0.01, 0.1, 1.0, 5.0, 20.0):
                if total > threshold:
                    threshold_counts[str(threshold)] += 1
            if index % 100 == 0:
                print(f"probed {index}/{len(requested)} reset states", flush=True)
    finally:
        env.close()

    primary_flips = 0
    released_flips = 0
    primary_desired_positive = 0
    primary_actual_positive = 0
    released_desired_positive = 0
    released_actual_positive = 0
    real_candidate_executions = 0
    for _path, seed, source_rows, target_states in real_records:
        actual_source = np.stack([actual_by_key[(seed, int(row))] for row in source_rows], axis=0)
        desired_source = states[source_rows]
        desired_block = np.linalg.norm(desired_source[:, 2:4] - target_states[:, 2:4], axis=-1)
        actual_block = np.linalg.norm(actual_source[:, 2:4] - target_states[:, 2:4], axis=-1)
        desired_joint = np.linalg.norm(desired_source[:, :4] - target_states[:, :4], axis=-1)
        actual_joint = np.linalg.norm(actual_source[:, :4] - target_states[:, :4], axis=-1)
        desired_angle = wrapped_angle_error(desired_source[:, 4], target_states[:, 4])
        actual_angle = wrapped_angle_error(actual_source[:, 4], target_states[:, 4])
        desired_primary = (desired_block < POSITION_TOLERANCE) & (desired_angle < ANGLE_TOLERANCE)
        actual_primary = (actual_block < POSITION_TOLERANCE) & (actual_angle < ANGLE_TOLERANCE)
        desired_released = (desired_joint < POSITION_TOLERANCE) & (desired_angle < ANGLE_TOLERANCE)
        actual_released = (actual_joint < POSITION_TOLERANCE) & (actual_angle < ANGLE_TOLERANCE)
        primary_flips += int(np.count_nonzero(desired_primary != actual_primary))
        released_flips += int(np.count_nonzero(desired_released != actual_released))
        primary_desired_positive += int(np.count_nonzero(desired_primary))
        primary_actual_positive += int(np.count_nonzero(actual_primary))
        released_desired_positive += int(np.count_nonzero(desired_released))
        released_actual_positive += int(np.count_nonzero(actual_released))
        real_candidate_executions += int(len(source_rows))

    result: dict[str, Any] = {
        "status": "ok",
        "classification": "pusht_released_set_state_internal_offset_probe",
        "method": {
            "sequence": "env.reset(seed=recorded_environment_seed); env.unwrapped._set_state(dataset_state); env.unwrapped._get_obs()",
            "released_setter_physics_step_seconds": DT,
            "comparison": "direct simulator observation versus requested dataset state before any policy action",
        },
        "inputs": {
            "dataset": str(args.dataset),
            "execution_roots": [str(path) for path in args.execution_root],
            "execution_file_count": len(files),
            "classifications": dict(sorted(classifications.items())),
        },
        "coverage": {
            "unique_environment_seed_source_row_pairs": len(requested),
            "exact_after_float32_count": exact_count,
            "offset_threshold_exceedance_count": dict(sorted(threshold_counts.items(), key=lambda item: float(item[0]))),
        },
        "offsets": {
            "full_state_l2": summarize(vector_l2),
            "agent_position_l2_pixels": summarize(agent_position_l2),
            "block_position_l2_pixels": summarize(block_position_l2),
            "wrapped_angle_abs_radians": summarize(angle_abs),
            "agent_velocity_l2": summarize(velocity_l2),
            "residual_from_expected_velocity_times_dt_shift_l2": summarize(ballistic_residual_l2),
        },
        "effect_on_inclusive_t0_real_frame_classification": {
            "candidate_execution_count_including_repeats": real_candidate_executions,
            "primary_block_only_label_flips": primary_flips,
            "primary_desired_positive": primary_desired_positive,
            "primary_actual_positive": primary_actual_positive,
            "released_joint_label_flips": released_flips,
            "released_desired_positive": released_desired_positive,
            "released_actual_positive": released_actual_positive,
        },
        "interpretation_boundary": (
            "This probe measures only the pre-action reset discrepancy. It does not rerun planning, "
            "and therefore cannot by itself establish whether later attainment labels would change."
        ),
        "runtime": {
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "elapsed_seconds": time.time() - started,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_json.with_name(f".{args.output_json.name}.partial-{os.getpid()}")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.output_json)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
