#!/usr/bin/env python3
"""Build the frozen, data-only E15 bounded-action P1 development cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e15_data_specs as spec


ROLE_NAME = {0: "E15_train", 1: "E15_val"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected path is forbidden: {path}")


def atomic_json(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def raw_to_planner_float32(
    raw: np.ndarray, mean: np.ndarray, scale: np.ndarray
) -> np.ndarray:
    """Reproduce released StandardScaler.transform float32 semantics."""

    value = np.asarray(raw, dtype=np.float32).copy()
    mean32 = np.asarray(mean, dtype=np.float32)
    scale32 = np.asarray(scale, dtype=np.float32)
    if value.shape[-1:] != mean32.shape or scale32.shape != mean32.shape:
        raise ValueError("planner-transform shape differs")
    if np.any(scale32 <= 0) or not np.isfinite(value).all():
        raise ValueError("planner-transform input differs")
    value -= mean32
    value /= scale32
    return value


def planner_to_raw_float32(
    planner: np.ndarray, mean: np.ndarray, scale: np.ndarray
) -> np.ndarray:
    """Reproduce released StandardScaler.inverse_transform float32 semantics."""

    value = np.asarray(planner, dtype=np.float32).copy()
    mean32 = np.asarray(mean, dtype=np.float32)
    scale32 = np.asarray(scale, dtype=np.float32)
    if value.shape[-1:] != mean32.shape or scale32.shape != mean32.shape:
        raise ValueError("planner-inverse shape differs")
    if np.any(scale32 <= 0) or not np.isfinite(value).all():
        raise ValueError("planner-inverse input differs")
    value *= scale32
    value += mean32
    return value


def bounded_action_targets(
    raw: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.float32, np.float32]:
    """Project expert actions to a finite inverse of s*tanh(u)."""

    value = np.asarray(raw, dtype=np.float32)
    if not np.isfinite(value).all():
        raise ValueError("non-finite raw E15 action")
    interior_scale = np.nextafter(
        np.float32(1.0), np.float32(0.0), dtype=np.float32
    )
    target_limit = np.float32(
        np.float64(interior_scale) * np.float64(interior_scale)
    )
    projected = np.clip(value, -target_limit, target_limit).astype(
        np.float32, copy=False
    )
    ratio = (projected.astype(np.float64) / float(interior_scale)).clip(
        -float(interior_scale), float(interior_scale)
    )
    unconstrained = np.arctanh(ratio).astype(np.float32)
    if (
        not np.isfinite(unconstrained).all()
        or np.any(np.abs(projected) > target_limit)
        or not (0.0 < target_limit < interior_scale < 1.0)
    ):
        raise RuntimeError("invalid E15 bounded target")
    return projected, unconstrained, interior_scale, target_limit


def select_rows(
    *,
    task: str,
    old_role: np.ndarray,
    episode: np.ndarray,
    delta: np.ndarray,
    tau: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Apply the frozen episode split and balanced per-cell quotas."""

    arrays = tuple(np.asarray(value) for value in (old_role, episode, delta, tau))
    if task not in spec.TASKS or any(value.ndim != 1 for value in arrays):
        raise ValueError("invalid E15 selection arrays")
    if len({len(value) for value in arrays}) != 1:
        raise ValueError("E15 selection length differs")
    old_role, episode, delta, tau = arrays
    eligible = old_role == 0
    unique_episodes = np.unique(episode[eligible])
    assignment = {
        int(value): int(spec.episode_is_validation(task, int(value)))
        for value in unique_episodes
    }
    episode_role = np.asarray([assignment[int(value)] for value in episode], dtype=np.uint8)
    selected_parts: list[np.ndarray] = []
    selected_role_parts: list[np.ndarray] = []
    availability: dict[str, dict[str, int]] = {
        "E15_train": {},
        "E15_val": {},
    }
    for role in (0, 1):
        quota = (
            spec.TRAIN_ROWS_PER_CELL if role == 0 else spec.VALIDATION_ROWS_PER_CELL
        )
        role_name = ROLE_NAME[role]
        for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
            available = np.flatnonzero(
                eligible
                & (episode_role == role)
                & (delta == delta_value)
                & (tau == tau_value)
            ).astype(np.int64)
            availability[role_name][f"delta={delta_value},tau={tau_value}"] = int(
                len(available)
            )
            if len(available) < quota:
                raise RuntimeError(
                    f"E15 {task} {role_name} delta={delta_value},tau={tau_value} "
                    f"has {len(available)} rows and needs {quota}"
                )
            generator = np.random.default_rng(
                spec.derived_seed(
                    f"cache|task={task}|role={role_name}"
                    f"|delta={delta_value}|tau={tau_value}"
                )
            )
            chosen = np.sort(
                generator.choice(available, size=quota, replace=False).astype(np.int64)
            )
            selected_parts.append(chosen)
            selected_role_parts.append(np.full(quota, role, dtype=np.uint8))
    selected = np.concatenate(selected_parts)
    new_role = np.concatenate(selected_role_parts)
    shuffled_rows: list[np.ndarray] = []
    shuffled_roles: list[np.ndarray] = []
    for role in (0, 1):
        positions = np.flatnonzero(new_role == role)
        generator = np.random.default_rng(
            spec.derived_seed(f"cache-shuffle|task={task}|role={ROLE_NAME[role]}")
        )
        permutation = positions[generator.permutation(len(positions))]
        shuffled_rows.append(selected[permutation])
        shuffled_roles.append(new_role[permutation])
    selected = np.concatenate(shuffled_rows)
    new_role = np.concatenate(shuffled_roles)
    train_episodes = set(episode[selected[new_role == 0]].astype(int).tolist())
    validation_episodes = set(episode[selected[new_role == 1]].astype(int).tolist())
    if (
        len(selected) != spec.TRAIN_ROWS + spec.VALIDATION_ROWS
        or len(np.unique(selected)) != len(selected)
        or train_episodes.intersection(validation_episodes)
        or np.any(old_role[selected] != 0)
    ):
        raise RuntimeError("E15 balanced selection integrity failed")
    return selected, new_role, {
        "old_p1_train_episode_count": int(len(unique_episodes)),
        "e15_train_episode_count": int(len(train_episodes)),
        "e15_validation_episode_count": int(len(validation_episodes)),
        "episode_overlap_count": 0,
        "availability_before_sampling": availability,
    }


def _quantiles(value: np.ndarray) -> dict[str, float]:
    if value.size == 0 or not np.isfinite(value).all():
        raise RuntimeError("invalid E15 diagnostic vector")
    return {
        "q50": float(np.quantile(value, 0.50)),
        "q90": float(np.quantile(value, 0.90)),
        "q95": float(np.quantile(value, 0.95)),
        "q99": float(np.quantile(value, 0.99)),
        "maximum": float(np.max(value)),
    }


def expert_geometry(
    *,
    raw: np.ndarray,
    projected: np.ndarray,
    unconstrained: np.ndarray,
    mask: np.ndarray,
    role: np.ndarray,
    tau: np.ndarray,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    displacement = np.abs(raw.astype(np.float64) - projected.astype(np.float64))
    normalized_jacobian = 1.0 - np.tanh(unconstrained.astype(np.float64)) ** 2
    for role_value, role_name in ROLE_NAME.items():
        result[role_name] = {}
        for tau_value in spec.TAU_VALUES:
            row_mask = (role == role_value) & (tau == tau_value)
            if not row_mask.any():
                raise RuntimeError("empty E15 expert-geometry role/tau cell")
            result[role_name][str(tau_value)] = []
            for dimension in range(raw.shape[-1]):
                active = row_mask[:, None] & mask
                original = raw[:, :, dimension][active]
                bounded = projected[:, :, dimension][active]
                u_value = unconstrained[:, :, dimension][active]
                shift = displacement[:, :, dimension][active]
                jacobian = normalized_jacobian[:, :, dimension][active]
                record: dict[str, Any] = {
                    "dimension": dimension,
                    "active_elements": int(len(original)),
                    "original_legal_oob_fraction": float(
                        np.mean((original < -1.0) | (original > 1.0))
                    ),
                    "original_exact_limit_fraction": float(
                        np.mean((original == -1.0) | (original == 1.0))
                    ),
                    "projection_fraction": float(np.mean(original != bounded)),
                    "projection_displacement": _quantiles(shift),
                    "absolute_u": _quantiles(np.abs(u_value.astype(np.float64))),
                }
                for margin in spec.NEAR_BOUNDARY_MARGINS:
                    record[f"original_near_{margin:.0e}_fraction"] = float(
                        np.mean(((1.0 - np.abs(original)) / 2.0) <= margin)
                    )
                    record[f"projected_near_{margin:.0e}_fraction"] = float(
                        np.mean(((1.0 - np.abs(bounded)) / 2.0) <= margin)
                    )
                for threshold in spec.JACOBIAN_THRESHOLDS:
                    record[f"jacobian_below_{threshold:.0e}_fraction"] = float(
                        np.mean(jacobian < threshold)
                    )
                result[role_name][str(tau_value)].append(record)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--e14-cache-h5", type=Path, required=True)
    parser.add_argument("--e14-cache-manifest", type=Path, required=True)
    parser.add_argument("--preflight-spec", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    required = (
        args.dataset,
        args.latent_h5,
        args.latent_manifest,
        args.transition_h5,
        args.e14_cache_h5,
        args.e14_cache_manifest,
        args.preflight_spec,
        args.source_manifest,
    )
    for path in (*required, args.output_h5, args.output_json):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an E15 data-preflight output")
    if sha256_file(args.preflight_spec) != spec.PREFLIGHT_SPEC_SHA256:
        raise RuntimeError("E15 data-preflight specification hash differs")

    task_spec = spec.TASK_SPEC[args.task]
    input_hashes = {
        "dataset_sha256": sha256_file(args.dataset),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "transition_h5_sha256": sha256_file(args.transition_h5),
        "e14_cache_h5_sha256": sha256_file(args.e14_cache_h5),
        "e14_cache_manifest_sha256": sha256_file(args.e14_cache_manifest),
        "preflight_spec_sha256": sha256_file(args.preflight_spec),
        "source_manifest_sha256": sha256_file(args.source_manifest),
    }
    expected_hashes = {
        "dataset_sha256": task_spec["dataset_sha256"],
        "latent_h5_sha256": task_spec["latent_sha256"],
        "latent_manifest_sha256": task_spec["latent_manifest_sha256"],
        "transition_h5_sha256": task_spec["transition_sha256"],
        "e14_cache_h5_sha256": task_spec["e14_cache_sha256"],
        "e14_cache_manifest_sha256": task_spec["e14_cache_manifest_sha256"],
    }
    for key, expected in expected_hashes.items():
        if input_hashes[key] != expected:
            raise RuntimeError(f"E15 pinned input hash differs: {key}")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    e14_manifest = json.loads(args.e14_cache_manifest.read_text(encoding="utf-8"))
    if (
        latent_manifest.get("status") != "ok"
        or latent_manifest.get("output_h5_sha256") != input_hashes["latent_h5_sha256"]
        or e14_manifest.get("status") != "ok"
        or e14_manifest.get("kind")
        != "gdp_cem_e14_balanced_variable_horizon_p1_cache"
        or e14_manifest.get("task") != args.task
        or e14_manifest.get("output_h5_sha256")
        != input_hashes["e14_cache_h5_sha256"]
        or e14_manifest.get("d3_metric_read") is not False
        or e14_manifest.get("d4_metric_read") is not False
        or e14_manifest.get("d5_read") is not False
        or e14_manifest.get("protected_p3_p4_c1_i1_read") is not False
    ):
        raise RuntimeError("E15 upstream manifest lineage differs")

    started = time.time()
    with h5py.File(args.e14_cache_h5, "r") as handle:
        cache = {
            key: np.asarray(handle[key][:])
            for key in (
                "source_index",
                "local_index",
                "goal_index",
                "raw_row_index",
                "episode_idx",
                "step_idx",
                "role",
                "delta",
                "tau",
                "state",
                "action",
                "action_mask",
            )
        }
    row_count = len(cache["role"])
    if (
        row_count != 440_000
        or any(len(value) != row_count for value in cache.values())
        or cache["action"].shape
        != (row_count, spec.ACTION_HORIZON, task_spec["primitive_action_dim"])
        or cache["action_mask"].shape != (row_count, spec.ACTION_HORIZON)
    ):
        raise RuntimeError("E15 upstream E14 cache shape differs")

    selected, new_role, split_record = select_rows(
        task=args.task,
        old_role=cache["role"],
        episode=cache["episode_idx"],
        delta=cache["delta"],
        tau=cache["tau"],
    )
    selected_cache = {key: value[selected] for key, value in cache.items()}
    del cache
    expected_mask = (
        np.arange(spec.ACTION_HORIZON)[None, :] < selected_cache["tau"][:, None]
    )
    if not np.array_equal(selected_cache["action_mask"], expected_mask):
        raise RuntimeError("E15 action duration mask differs")

    with h5py.File(args.latent_h5, "r") as handle:
        latent_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        latent_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        latent_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent = np.asarray(handle["latent"][:], dtype=np.float32)
    source = selected_cache["source_index"].astype(np.int64)
    local = selected_cache["local_index"].astype(np.int64)
    goal = selected_cache["goal_index"].astype(np.int64)
    if (
        np.any(source < 0)
        or np.any(goal >= len(latent))
        or np.any(latent_episode[source] != selected_cache["episode_idx"])
        or np.any(latent_episode[local] != selected_cache["episode_idx"])
        or np.any(latent_episode[goal] != selected_cache["episode_idx"])
        or np.any(latent_step[source] != selected_cache["step_idx"])
        or np.any(latent_step[local] - latent_step[source] != selected_cache["tau"])
        or np.any(latent_step[goal] - latent_step[source] != selected_cache["delta"])
        or np.any(latent_rows[source] != selected_cache["raw_row_index"])
    ):
        raise RuntimeError("E15 selected latent lineage differs")

    with h5py.File(args.transition_h5, "r") as handle:
        planner_mean = np.asarray(
            handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
        )
        planner_scale = np.asarray(
            handle["stats/planner_primitive_action_std"][:], dtype=np.float64
        )
    primitive_dim = int(task_spec["primitive_action_dim"])
    if (
        planner_mean.shape != (primitive_dim,)
        or planner_scale.shape != (primitive_dim,)
        or np.any(planner_scale <= 1.0e-8)
    ):
        raise RuntimeError("E15 planner scaler differs")

    with h5py.File(args.dataset, "r") as handle:
        raw_source = np.asarray(handle["action"][:], dtype=np.float32)
        raw_episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
        raw_episode = np.asarray(handle[raw_episode_key][:], dtype=np.int64)
        raw_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
    action_indices = selected_cache["raw_row_index"][:, None] + np.arange(
        spec.ACTION_HORIZON, dtype=np.int64
    )[None]
    if (
        np.any(action_indices < 0)
        or np.any(action_indices >= len(raw_source))
        or np.any(
            raw_episode[action_indices][expected_mask]
            != np.repeat(selected_cache["episode_idx"][:, None], spec.ACTION_HORIZON, axis=1)[
                expected_mask
            ]
        )
        or np.any(
            raw_step[action_indices][expected_mask]
            != (
                selected_cache["step_idx"][:, None]
                + np.arange(spec.ACTION_HORIZON, dtype=np.int64)[None]
            )[expected_mask]
        )
    ):
        raise RuntimeError("E15 raw action join crosses an episode")
    raw_action = raw_source[action_indices]
    raw_action[~expected_mask] = 0.0
    del raw_source, raw_episode, raw_step, action_indices

    reconstructed_planner = raw_to_planner_float32(
        raw_action, planner_mean, planner_scale
    )
    active3 = np.broadcast_to(expected_mask[:, :, None], raw_action.shape)
    cached_planner = selected_cache["action"].astype(np.float32)
    planner_bit_mismatch = np.not_equal(reconstructed_planner, cached_planner) & active3
    inverse_raw = planner_to_raw_float32(cached_planner, planner_mean, planner_scale)
    inverse_raw_error = np.abs(inverse_raw.astype(np.float64) - raw_action.astype(np.float64))
    maximum_inverse_raw_error = float(inverse_raw_error[active3].max(initial=0.0))
    if planner_bit_mismatch.any() or maximum_inverse_raw_error > spec.RAW_ROUNDING_TOLERANCE:
        raise RuntimeError("E15 released action StandardScaler reproduction differs")

    projected, unconstrained, interior_scale, target_limit = bounded_action_targets(
        raw_action
    )
    projected[~expected_mask] = 0.0
    unconstrained[~expected_mask] = 0.0
    train = new_role == 0
    validation = new_role == 1
    train_unique_latent = np.unique(
        np.concatenate((source[train], local[train], goal[train]))
    )
    training_latent = latent[train_unique_latent].astype(np.float64)
    latent_mean = training_latent.mean(axis=0).astype(np.float32)
    latent_std = training_latent.std(axis=0).astype(np.float32)
    state_mean = selected_cache["state"][train].mean(axis=0, dtype=np.float64).astype(
        np.float32
    )
    state_std = selected_cache["state"][train].std(axis=0, dtype=np.float64).astype(
        np.float32
    )
    u_mean = np.empty(primitive_dim, dtype=np.float32)
    u_std = np.empty(primitive_dim, dtype=np.float32)
    for dimension in range(primitive_dim):
        value = unconstrained[:, :, dimension][train[:, None] & expected_mask]
        u_mean[dimension] = value.mean(dtype=np.float64)
        u_std[dimension] = value.std(dtype=np.float64)
    if (
        np.any(latent_std < 1.0e-6)
        or np.any(state_std < 1.0e-8)
        or np.any(u_std < 1.0e-6)
        or not all(
            np.isfinite(value).all()
            for value in (latent_mean, latent_std, state_mean, state_std, u_mean, u_std)
        )
    ):
        raise RuntimeError("E15 train-only standardizer is invalid")
    standardized_u = (
        (unconstrained - u_mean[None, None]) / u_std[None, None]
    ).astype(np.float32)
    standardized_u[~expected_mask] = 0.0
    if not np.isfinite(standardized_u).all() or np.any(standardized_u[~expected_mask] != 0):
        raise RuntimeError("E15 standardized bounded target differs")

    pair_counts: dict[str, dict[str, int]] = {name: {} for name in ROLE_NAME.values()}
    for role_value, role_name in ROLE_NAME.items():
        for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
            pair_counts[role_name][f"delta={delta_value},tau={tau_value}"] = int(
                np.count_nonzero(
                    (new_role == role_value)
                    & (selected_cache["delta"] == delta_value)
                    & (selected_cache["tau"] == tau_value)
                )
            )
    if (
        any(value != spec.TRAIN_ROWS_PER_CELL for value in pair_counts["E15_train"].values())
        or any(
            value != spec.VALIDATION_ROWS_PER_CELL
            for value in pair_counts["E15_val"].values()
        )
    ):
        raise RuntimeError("E15 selected pair counts differ")

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "x") as target:
            scalar_chunk = min(65_536, len(selected))
            for key, value in (
                ("e14_cache_row", selected),
                ("source_index", source),
                ("local_index", local),
                ("goal_index", goal),
                ("raw_row_index", selected_cache["raw_row_index"]),
                ("episode_idx", selected_cache["episode_idx"]),
                ("step_idx", selected_cache["step_idx"]),
                ("role", new_role),
                ("delta", selected_cache["delta"]),
                ("tau", selected_cache["tau"]),
            ):
                target.create_dataset(
                    key, data=value, chunks=(scalar_chunk,), compression="lzf"
                )
            vector_chunk = min(4096, len(selected))
            target.create_dataset(
                "state",
                data=selected_cache["state"].astype(np.float32),
                chunks=(vector_chunk, task_spec["state_dim"]),
                compression="lzf",
            )
            for key, value in (
                ("action_raw_original", raw_action),
                ("action_raw_projected", projected),
                ("action_u", unconstrained),
                ("action_u_standardized", standardized_u),
                ("action_planner_original", cached_planner),
            ):
                target.create_dataset(
                    key,
                    data=value.astype(np.float32),
                    chunks=(vector_chunk, spec.ACTION_HORIZON, primitive_dim),
                    compression="lzf",
                )
            target.create_dataset(
                "action_mask",
                data=expected_mask,
                chunks=(vector_chunk, spec.ACTION_HORIZON),
                compression="lzf",
            )
            stats = target.create_group("stats")
            for key, value in (
                ("latent_mean", latent_mean),
                ("latent_std", latent_std),
                ("state_mean", state_mean),
                ("state_std", state_std),
                ("u_mean", u_mean),
                ("u_std", u_std),
                ("planner_primitive_action_mean", planner_mean),
                ("planner_primitive_action_std", planner_scale),
            ):
                stats.create_dataset(key, data=value)
            stats.attrs["interior_scale"] = float(interior_scale)
            stats.attrs["target_raw_limit"] = float(target_limit)
            target.attrs["task"] = args.task
            target.attrs["preflight_spec_sha256"] = spec.PREFLIGHT_SPEC_SHA256
            target.attrs["e14_cache_h5_sha256"] = input_hashes["e14_cache_h5_sha256"]
            target.attrs["latent_h5_sha256"] = input_hashes["latent_h5_sha256"]
            target.attrs["transition_h5_sha256"] = input_hashes[
                "transition_h5_sha256"
            ]
        os.replace(partial, args.output_h5)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    output_sha = sha256_file(args.output_h5)
    manifest = {
        "status": "ok",
        "kind": "gdp_cem_e15_episode_disjoint_bounded_action_p1_cache",
        "analysis_role": "P1_structural_data_preflight_only",
        "task": args.task,
        "rows": int(len(selected)),
        "train_rows": int(train.sum()),
        "validation_rows": int(validation.sum()),
        "pair_counts": pair_counts,
        "split": split_record,
        "split_salt": spec.SPLIT_SALT,
        "split_digest_interpretation": "first_8_bytes_unsigned_big_endian_mod_4_eq_0_is_validation",
        "interior_scale": float(interior_scale),
        "target_raw_limit": float(target_limit),
        "planner_transform_bit_mismatch_count": int(planner_bit_mismatch.sum()),
        "maximum_inverse_raw_roundtrip_error": maximum_inverse_raw_error,
        "raw_rounding_tolerance": spec.RAW_ROUNDING_TOLERANCE,
        "expert_geometry": expert_geometry(
            raw=raw_action,
            projected=projected,
            unconstrained=unconstrained,
            mask=expected_mask,
            role=new_role,
            tau=selected_cache["tau"],
        ),
        "standardizers": {
            "latent_mean": latent_mean.tolist(),
            "latent_std": latent_std.tolist(),
            "state_mean": state_mean.tolist(),
            "state_std": state_std.tolist(),
            "u_mean": u_mean.tolist(),
            "u_std": u_std.tolist(),
            "planner_primitive_action_mean": planner_mean.tolist(),
            "planner_primitive_action_std": planner_scale.tolist(),
            "train_unique_latent_count": int(len(train_unique_latent)),
        },
        "inputs": {key: str(value) for key, value in vars(args).items() if isinstance(value, Path)},
        "input_hashes": input_hashes,
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": output_sha,
        "elapsed_seconds": time.time() - started,
        "model_training_performed": False,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_json, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
