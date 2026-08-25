"""Checksum-pinned E15 bounded-action array store and deterministic batches."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import h5py
import numpy as np
import torch

import gdp_cem_e15_specs as spec


GoalMode = Literal["true", "shuffled"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_group_derangement(
    role: np.ndarray,
    delta: np.ndarray,
    tau: np.ndarray,
    episode: np.ndarray,
    *,
    task: str,
) -> np.ndarray:
    """Map each row to another episode in the same role/delta/tau cell."""

    arrays = tuple(np.asarray(value) for value in (role, delta, tau, episode))
    if any(value.ndim != 1 for value in arrays) or len({len(v) for v in arrays}) != 1:
        raise ValueError("invalid E15 derangement arrays")
    role, delta, tau, episode = arrays
    result = np.full(len(role), -1, dtype=np.int64)
    for role_value in np.unique(role):
        for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
            rows = np.flatnonzero(
                (role == role_value)
                & (delta == delta_value)
                & (tau == tau_value)
            ).astype(np.int64)
            if len(rows) < 2 or len(np.unique(episode[rows])) < 2:
                raise RuntimeError("E15 shuffled-goal cell cannot be deranged")
            generator = np.random.default_rng(
                spec.derived_seed(
                    f"goal-derangement|task={task}|role={int(role_value)}"
                    f"|delta={delta_value}|tau={tau_value}"
                )
            )
            episode_values = np.unique(episode[rows])
            episode_values = episode_values[generator.permutation(len(episode_values))]
            blocks = [
                rows[episode[rows] == episode_value]
                for episode_value in episode_values
            ]
            order = np.concatenate(blocks)
            maximum_block = max(len(block) for block in blocks)
            if maximum_block * 2 > len(order):
                raise RuntimeError("E15 goal derangement has a majority episode")
            target = np.roll(order, maximum_block)
            if np.any(episode[order] == episode[target]):
                raise RuntimeError("E15 block-rotation derangement failed")
            result[order] = target
    if (
        np.any(result < 0)
        or not np.array_equal(role[result], role)
        or not np.array_equal(delta[result], delta)
        or not np.array_equal(tau[result], tau)
        or np.any(episode[result] == episode)
    ):
        raise RuntimeError("E15 grouped derangement integrity failed")
    return result


@dataclass(frozen=True)
class E15Batch:
    current: torch.Tensor
    goal: torch.Tensor
    local: torch.Tensor
    state: torch.Tensor
    delta: torch.Tensor
    tau: torch.Tensor
    action_u: torch.Tensor
    action_mask: torch.Tensor
    action_raw_projected: torch.Tensor
    action_raw_original: torch.Tensor

    def flat_target(self) -> tuple[torch.Tensor, torch.Tensor]:
        batch, horizon, action_dim = self.action_u.shape
        mask = self.action_mask[:, :, None].expand(batch, horizon, action_dim)
        target = self.action_u.reshape(batch, horizon * action_dim)
        flat_mask = mask.reshape(batch, horizon * action_dim)
        if torch.any(target[~flat_mask] != 0):
            raise RuntimeError("E15 inactive action target is nonzero")
        return target, flat_mask


class E15ArrayStore:
    """Materialize only immutable E15 P1 cache rows."""

    def __init__(
        self,
        *,
        task: str,
        latent_h5: Path,
        latent_manifest: Path,
        cache_h5: Path,
        cache_manifest: Path,
    ) -> None:
        if task not in spec.TASKS:
            raise ValueError(f"unknown E15 task: {task}")
        for path in (latent_h5, latent_manifest, cache_h5, cache_manifest):
            if not path.is_file():
                raise FileNotFoundError(path)
        task_spec = spec.TASK_SPEC[task]
        hashes = {
            "latent_h5_sha256": sha256_file(latent_h5),
            "latent_manifest_sha256": sha256_file(latent_manifest),
            "cache_h5_sha256": sha256_file(cache_h5),
            "cache_manifest_sha256": sha256_file(cache_manifest),
        }
        expected = {
            "latent_h5_sha256": task_spec["latent_sha256"],
            "latent_manifest_sha256": task_spec["latent_manifest_sha256"],
            "cache_h5_sha256": task_spec["e15_cache_sha256"],
            "cache_manifest_sha256": task_spec["e15_cache_manifest_sha256"],
        }
        if hashes != expected:
            raise RuntimeError("E15 array-store input hash differs")
        latent_record = json.loads(latent_manifest.read_text(encoding="utf-8"))
        cache_record = json.loads(cache_manifest.read_text(encoding="utf-8"))
        if (
            latent_record.get("status") != "ok"
            or latent_record.get("output_h5_sha256") != hashes["latent_h5_sha256"]
            or cache_record.get("status") != "ok"
            or cache_record.get("kind")
            != "gdp_cem_e15_episode_disjoint_bounded_action_p1_cache"
            or cache_record.get("analysis_role")
            != "P1_structural_data_preflight_only"
            or cache_record.get("task") != task
            or cache_record.get("output_h5_sha256") != hashes["cache_h5_sha256"]
            or cache_record.get("train_rows") != spec.TRAIN_ROWS
            or cache_record.get("validation_rows") != spec.VALIDATION_ROWS
            or cache_record.get("model_training_performed") is not False
            or cache_record.get("p2_read") is not False
            or cache_record.get("d3_metric_read") is not False
            or cache_record.get("d4_metric_read") is not False
            or cache_record.get("d5_read") is not False
            or cache_record.get("protected_p3_p4_c1_i1_read") is not False
            or cache_record.get("claim_allowed") is not False
            or cache_record.get("input_hashes", {}).get("source_manifest_sha256")
            != spec.DATA_PREFLIGHT_SOURCE_MANIFEST_SHA256
        ):
            raise RuntimeError("E15 cache manifest lineage differs")

        with h5py.File(latent_h5, "r") as handle:
            latent = np.asarray(handle["latent"][:], dtype=np.float32)
        with h5py.File(cache_h5, "r") as handle:
            source = np.asarray(handle["source_index"][:], dtype=np.int64)
            local = np.asarray(handle["local_index"][:], dtype=np.int64)
            goal = np.asarray(handle["goal_index"][:], dtype=np.int64)
            self.episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
            self.role = np.asarray(handle["role"][:], dtype=np.uint8)
            self.delta = np.asarray(handle["delta"][:], dtype=np.int64)
            self.tau = np.asarray(handle["tau"][:], dtype=np.int64)
            state = np.asarray(handle["state"][:], dtype=np.float32)
            self.action_u = np.asarray(
                handle["action_u_standardized"][:], dtype=np.float32
            )
            self.action_mask = np.asarray(handle["action_mask"][:], dtype=np.bool_)
            self.action_raw_projected = np.asarray(
                handle["action_raw_projected"][:], dtype=np.float32
            )
            self.action_raw_original = np.asarray(
                handle["action_raw_original"][:], dtype=np.float32
            )
            self.latent_mean = np.asarray(
                handle["stats/latent_mean"][:], dtype=np.float32
            )
            self.latent_std = np.asarray(
                handle["stats/latent_std"][:], dtype=np.float32
            )
            self.state_mean = np.asarray(
                handle["stats/state_mean"][:], dtype=np.float32
            )
            self.state_std = np.asarray(
                handle["stats/state_std"][:], dtype=np.float32
            )
            self.u_mean = np.asarray(handle["stats/u_mean"][:], dtype=np.float32)
            self.u_std = np.asarray(handle["stats/u_std"][:], dtype=np.float32)
            self.planner_action_mean = np.asarray(
                handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
            ).astype(np.float32)
            self.planner_action_std = np.asarray(
                handle["stats/planner_primitive_action_std"][:], dtype=np.float64
            ).astype(np.float32)
            self.interior_scale = float(handle["stats"].attrs["interior_scale"])
            self.target_raw_limit = float(handle["stats"].attrs["target_raw_limit"])
            attr_expected = {
                "task": task,
                "preflight_spec_sha256": cache_record["input_hashes"][
                    "preflight_spec_sha256"
                ],
                "e14_cache_h5_sha256": cache_record["input_hashes"][
                    "e14_cache_h5_sha256"
                ],
                "latent_h5_sha256": hashes["latent_h5_sha256"],
                "transition_h5_sha256": task_spec["transition_sha256"],
            }
            for name, value in attr_expected.items():
                if handle.attrs.get(name) != value:
                    raise RuntimeError(f"E15 cache attribute differs: {name}")

        rows = spec.TRAIN_ROWS + spec.VALIDATION_ROWS
        state_dim = int(task_spec["state_dim"])
        action_dim = int(task_spec["primitive_action_dim"])
        if (
            latent.ndim != 2
            or latent.shape[1] != spec.LATENT_DIM
            or any(
                len(value) != rows
                for value in (
                    source,
                    local,
                    goal,
                    self.episode,
                    self.role,
                    self.delta,
                    self.tau,
                    state,
                    self.action_u,
                    self.action_mask,
                    self.action_raw_projected,
                    self.action_raw_original,
                )
            )
            or state.shape != (rows, state_dim)
            or self.action_u.shape != (rows, spec.ACTION_HORIZON, action_dim)
            or self.action_mask.shape != (rows, spec.ACTION_HORIZON)
            or self.action_raw_projected.shape != self.action_u.shape
            or self.action_raw_original.shape != self.action_u.shape
            or np.any(source < 0)
            or np.any(local < 0)
            or np.any(goal < 0)
            or np.any(source >= len(latent))
            or np.any(local >= len(latent))
            or np.any(goal >= len(latent))
        ):
            raise RuntimeError("E15 cache array shape differs")
        self.task = task
        self.state_dim = state_dim
        self.primitive_action_dim = action_dim

        def normalized_latent(indices: np.ndarray) -> np.ndarray:
            return np.ascontiguousarray(
                (latent[indices] - self.latent_mean) / self.latent_std,
                dtype=np.float32,
            )

        self.current = normalized_latent(source)
        self.local = normalized_latent(local)
        self.goal = normalized_latent(goal)
        del latent
        self.state = np.ascontiguousarray(
            (state - self.state_mean) / self.state_std, dtype=np.float32
        )
        self.train_rows = np.flatnonzero(self.role == 0).astype(np.int64)
        self.validation_rows = np.flatnonzero(self.role == 1).astype(np.int64)
        if (
            len(self.train_rows) != spec.TRAIN_ROWS
            or len(self.validation_rows) != spec.VALIDATION_ROWS
            or set(np.unique(self.role).tolist()) != {0, 1}
            or set(self.episode[self.train_rows]).intersection(
                set(self.episode[self.validation_rows])
            )
            or not np.array_equal(
                self.action_mask,
                np.arange(spec.ACTION_HORIZON)[None] < self.tau[:, None],
            )
            or np.any(self.action_u[~self.action_mask] != 0)
            or np.any(self.action_raw_projected[~self.action_mask] != 0)
            or not all(
                np.isfinite(value).all()
                for value in (
                    self.current,
                    self.local,
                    self.goal,
                    self.state,
                    self.action_u,
                    self.action_raw_projected,
                    self.action_raw_original,
                )
            )
            or np.any(self.latent_std <= 1.0e-6)
            or np.any(self.state_std <= 1.0e-8)
            or np.any(self.u_std <= 1.0e-6)
            or np.any(self.planner_action_std <= 1.0e-8)
            or not (0.0 < self.target_raw_limit < self.interior_scale < 1.0)
        ):
            raise RuntimeError("E15 normalized cache integrity failed")
        self.shuffled_goal_rows = deterministic_group_derangement(
            self.role,
            self.delta,
            self.tau,
            self.episode,
            task=task,
        )
        self.lineage = hashes
        self.expert_geometry = cache_record["expert_geometry"]

    def batch(self, rows: np.ndarray, *, goal_mode: GoalMode = "true") -> E15Batch:
        rows = np.asarray(rows, dtype=np.int64)
        if rows.ndim != 1 or np.any(rows < 0) or np.any(rows >= len(self.role)):
            raise ValueError("invalid E15 batch rows")
        if goal_mode == "true":
            goal_rows = rows
        elif goal_mode == "shuffled":
            goal_rows = self.shuffled_goal_rows[rows]
        else:
            raise ValueError(f"unknown E15 goal mode: {goal_mode}")
        return E15Batch(
            current=torch.from_numpy(self.current[rows]),
            goal=torch.from_numpy(self.goal[goal_rows]),
            local=torch.from_numpy(self.local[rows]),
            state=torch.from_numpy(self.state[rows]),
            delta=torch.from_numpy(self.delta[rows]),
            tau=torch.from_numpy(self.tau[rows]),
            action_u=torch.from_numpy(self.action_u[rows]),
            action_mask=torch.from_numpy(self.action_mask[rows]),
            action_raw_projected=torch.from_numpy(self.action_raw_projected[rows]),
            action_raw_original=torch.from_numpy(self.action_raw_original[rows]),
        )


class E15TrainingStore:
    """Load role-0 model inputs only; validation payload arrays stay unopened."""

    def __init__(
        self,
        *,
        task: str,
        latent_h5: Path,
        latent_manifest: Path,
        cache_h5: Path,
        cache_manifest: Path,
    ) -> None:
        if task not in spec.TASKS:
            raise ValueError(f"unknown E15 training task: {task}")
        task_spec = spec.TASK_SPEC[task]
        hashes = {
            "latent_h5_sha256": sha256_file(latent_h5),
            "latent_manifest_sha256": sha256_file(latent_manifest),
            "cache_h5_sha256": sha256_file(cache_h5),
            "cache_manifest_sha256": sha256_file(cache_manifest),
        }
        if hashes != {
            "latent_h5_sha256": task_spec["latent_sha256"],
            "latent_manifest_sha256": task_spec["latent_manifest_sha256"],
            "cache_h5_sha256": task_spec["e15_cache_sha256"],
            "cache_manifest_sha256": task_spec["e15_cache_manifest_sha256"],
        }:
            raise RuntimeError("E15 training-store input hash differs")
        cache_record = json.loads(cache_manifest.read_text(encoding="utf-8"))
        latent_record = json.loads(latent_manifest.read_text(encoding="utf-8"))
        if (
            cache_record.get("status") != "ok"
            or cache_record.get("task") != task
            or cache_record.get("train_rows") != spec.TRAIN_ROWS
            or cache_record.get("validation_rows") != spec.VALIDATION_ROWS
            or cache_record.get("output_h5_sha256") != hashes["cache_h5_sha256"]
            or cache_record.get("d5_read") is not False
            or latent_record.get("status") != "ok"
            or latent_record.get("output_h5_sha256") != hashes["latent_h5_sha256"]
        ):
            raise RuntimeError("E15 training-store manifest differs")

        train_slice = slice(0, spec.TRAIN_ROWS)
        validation_slice = slice(spec.TRAIN_ROWS, spec.TRAIN_ROWS + spec.VALIDATION_ROWS)
        with h5py.File(cache_h5, "r") as handle:
            # Role codes are non-performance metadata and are the only full
            # dataset read. Every model input below is sliced to role 0.
            role = np.asarray(handle["role"][:], dtype=np.uint8)
            if (
                not np.all(role[train_slice] == 0)
                or not np.all(role[validation_slice] == 1)
            ):
                raise RuntimeError("E15 cache role ordering differs")
            source = np.asarray(handle["source_index"][train_slice], dtype=np.int64)
            local = np.asarray(handle["local_index"][train_slice], dtype=np.int64)
            goal = np.asarray(handle["goal_index"][train_slice], dtype=np.int64)
            self.episode = np.asarray(
                handle["episode_idx"][train_slice], dtype=np.int64
            )
            self.delta = np.asarray(handle["delta"][train_slice], dtype=np.int64)
            self.tau = np.asarray(handle["tau"][train_slice], dtype=np.int64)
            state = np.asarray(handle["state"][train_slice], dtype=np.float32)
            self.action_u = np.asarray(
                handle["action_u_standardized"][train_slice], dtype=np.float32
            )
            self.action_mask = np.asarray(
                handle["action_mask"][train_slice], dtype=np.bool_
            )
            self.action_raw_projected = np.asarray(
                handle["action_raw_projected"][train_slice], dtype=np.float32
            )
            self.action_raw_original = np.asarray(
                handle["action_raw_original"][train_slice], dtype=np.float32
            )
            self.latent_mean = np.asarray(
                handle["stats/latent_mean"][:], dtype=np.float32
            )
            self.latent_std = np.asarray(
                handle["stats/latent_std"][:], dtype=np.float32
            )
            self.state_mean = np.asarray(
                handle["stats/state_mean"][:], dtype=np.float32
            )
            self.state_std = np.asarray(
                handle["stats/state_std"][:], dtype=np.float32
            )
            self.u_mean = np.asarray(handle["stats/u_mean"][:], dtype=np.float32)
            self.u_std = np.asarray(handle["stats/u_std"][:], dtype=np.float32)
            self.planner_action_mean = np.asarray(
                handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
            ).astype(np.float32)
            self.planner_action_std = np.asarray(
                handle["stats/planner_primitive_action_std"][:], dtype=np.float64
            ).astype(np.float32)
            self.interior_scale = float(handle["stats"].attrs["interior_scale"])
            self.target_raw_limit = float(handle["stats"].attrs["target_raw_limit"])
        unique, inverse = np.unique(
            np.concatenate((source, local, goal)), return_inverse=True
        )
        with h5py.File(latent_h5, "r") as handle:
            selected_latent = np.asarray(handle["latent"][unique], dtype=np.float32)
        normalized = np.ascontiguousarray(
            (selected_latent - self.latent_mean) / self.latent_std,
            dtype=np.float32,
        )
        first = inverse[: spec.TRAIN_ROWS]
        second = inverse[spec.TRAIN_ROWS : 2 * spec.TRAIN_ROWS]
        third = inverse[2 * spec.TRAIN_ROWS :]
        self.current = np.ascontiguousarray(normalized[first])
        self.local = np.ascontiguousarray(normalized[second])
        self.goal = np.ascontiguousarray(normalized[third])
        self.state = np.ascontiguousarray(
            (state - self.state_mean) / self.state_std, dtype=np.float32
        )
        self.role = np.zeros(spec.TRAIN_ROWS, dtype=np.uint8)
        self.train_rows = np.arange(spec.TRAIN_ROWS, dtype=np.int64)
        self.validation_payload_rows_read = 0
        self.task = task
        self.state_dim = int(task_spec["state_dim"])
        self.primitive_action_dim = int(task_spec["primitive_action_dim"])
        if (
            self.action_u.shape
            != (spec.TRAIN_ROWS, spec.ACTION_HORIZON, self.primitive_action_dim)
            or self.action_mask.shape != (spec.TRAIN_ROWS, spec.ACTION_HORIZON)
            or not np.array_equal(
                self.action_mask,
                np.arange(spec.ACTION_HORIZON)[None] < self.tau[:, None],
            )
            or np.any(self.action_u[~self.action_mask] != 0)
            or not all(
                np.isfinite(value).all()
                for value in (
                    self.current,
                    self.local,
                    self.goal,
                    self.state,
                    self.action_u,
                    self.action_raw_projected,
                    self.action_raw_original,
                )
            )
        ):
            raise RuntimeError("E15 train-only payload integrity failed")
        self.shuffled_goal_rows = deterministic_group_derangement(
            self.role,
            self.delta,
            self.tau,
            self.episode,
            task=task,
        )
        self.lineage = hashes

    def batch(self, rows: np.ndarray, *, goal_mode: GoalMode = "true") -> E15Batch:
        rows = np.asarray(rows, dtype=np.int64)
        if rows.ndim != 1 or np.any(rows < 0) or np.any(rows >= spec.TRAIN_ROWS):
            raise ValueError("invalid E15 training batch rows")
        if goal_mode == "true":
            goal_rows = rows
        elif goal_mode == "shuffled":
            goal_rows = self.shuffled_goal_rows[rows]
        else:
            raise ValueError(f"unknown E15 training goal mode: {goal_mode}")
        return E15Batch(
            current=torch.from_numpy(self.current[rows]),
            goal=torch.from_numpy(self.goal[goal_rows]),
            local=torch.from_numpy(self.local[rows]),
            state=torch.from_numpy(self.state[rows]),
            delta=torch.from_numpy(self.delta[rows]),
            tau=torch.from_numpy(self.tau[rows]),
            action_u=torch.from_numpy(self.action_u[rows]),
            action_mask=torch.from_numpy(self.action_mask[rows]),
            action_raw_projected=torch.from_numpy(self.action_raw_projected[rows]),
            action_raw_original=torch.from_numpy(self.action_raw_original[rows]),
        )


__all__ = [
    "E15ArrayStore",
    "E15Batch",
    "E15TrainingStore",
    "deterministic_group_derangement",
    "sha256_file",
]
