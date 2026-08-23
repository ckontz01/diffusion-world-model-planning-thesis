"""Validated in-memory data interface for frozen E14 development artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import h5py
import numpy as np
import torch

import gdp_cem_e14_specs as spec
from gdp_cem_e14_models import Endpoint, endpoint_active_mask


GoalMode = Literal["true", "shuffled"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_group_derangement(
    role: np.ndarray,
    delta: np.ndarray,
    tau: np.ndarray,
    *,
    task: str,
) -> np.ndarray:
    """Map every row to a different row in the same role/delta/tau cell."""

    if not (role.ndim == delta.ndim == tau.ndim == 1) or not (
        len(role) == len(delta) == len(tau)
    ):
        raise ValueError("invalid E14 derangement arrays")
    result = np.full(len(role), -1, dtype=np.int64)
    for role_value in np.unique(role):
        for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
            cell = np.flatnonzero(
                (role == role_value)
                & (delta == delta_value)
                & (tau == tau_value)
            )
            if len(cell) < 2:
                raise RuntimeError("E14 shuffled-goal cell has fewer than two rows")
            generator = np.random.default_rng(
                spec.derived_seed(
                    "goal-derangement"
                    f"|task={task}|role={int(role_value)}"
                    f"|delta={delta_value}|tau={tau_value}"
                )
            )
            ordered = cell[generator.permutation(len(cell))]
            result[ordered] = np.roll(ordered, 1)
    if np.any(result < 0) or np.any(result == np.arange(len(result))):
        raise RuntimeError("E14 shuffled-goal derangement is incomplete")
    if (
        not np.array_equal(role[result], role)
        or not np.array_equal(delta[result], delta)
        or not np.array_equal(tau[result], tau)
    ):
        raise RuntimeError("E14 shuffled-goal derangement crossed a condition cell")
    return result


@dataclass(frozen=True)
class E14Batch:
    current: torch.Tensor
    goal: torch.Tensor
    local: torch.Tensor
    state: torch.Tensor
    delta: torch.Tensor
    tau: torch.Tensor
    action: torch.Tensor
    action_mask: torch.Tensor
    local_residual: torch.Tensor

    def endpoint_target(self, endpoint: Endpoint) -> tuple[torch.Tensor, torch.Tensor]:
        flattened_action = self.action.flatten(1)
        if endpoint == "vad":
            clean = flattened_action
        elif endpoint == "cvd":
            clean = torch.cat((self.local_residual, flattened_action), dim=-1)
        else:
            raise ValueError(f"unknown E14 endpoint: {endpoint}")
        mask = endpoint_active_mask(
            endpoint,
            self.tau,
            latent_dim=self.current.shape[1],
            primitive_action_dim=self.action.shape[2],
            horizon=self.action.shape[1],
        )
        if clean.shape != mask.shape:
            raise RuntimeError("E14 endpoint target and mask shapes differ")
        return clean, mask


class E14ArrayStore:
    """Materialize only frozen P1 cache rows and serve deterministic batches."""

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
            raise ValueError(f"unknown E14 task: {task}")
        for path in (latent_h5, latent_manifest, cache_h5, cache_manifest):
            if not path.is_file():
                raise FileNotFoundError(path)
        task_spec = spec.TASK_SPEC[task]
        latent_sha = sha256_file(latent_h5)
        latent_manifest_sha = sha256_file(latent_manifest)
        cache_sha = sha256_file(cache_h5)
        cache_manifest_sha = sha256_file(cache_manifest)
        if (
            latent_sha != task_spec["latent_sha256"]
            or latent_manifest_sha != task_spec["latent_manifest_sha256"]
            or cache_sha != task_spec["e14_cache_sha256"]
            or cache_manifest_sha != task_spec["e14_cache_manifest_sha256"]
        ):
            raise RuntimeError("E14 array-store input content hash differs")
        latent_record = json.loads(latent_manifest.read_text(encoding="utf-8"))
        cache_record = json.loads(cache_manifest.read_text(encoding="utf-8"))
        if (
            latent_record.get("status") != "ok"
            or latent_record.get("output_h5_sha256") != latent_sha
            or cache_record.get("status") != "ok"
            or cache_record.get("kind")
            != "gdp_cem_e14_balanced_variable_horizon_p1_cache"
            or cache_record.get("task") != task
            or cache_record.get("output_h5_sha256") != cache_sha
            or cache_record.get("latent_h5_sha256") != latent_sha
            or cache_record.get("protocol_sha256") != spec.PROTOCOL_SHA256
            or cache_record.get("source_manifest_sha256")
            != "6083437487a8d3c2bdec99ac7702f10f680b0e7a15de66c88526be249b6a54f2"
            or cache_record.get("d3_metric_read") is not False
            or cache_record.get("d4_metric_read") is not False
            or cache_record.get("d5_read") is not False
            or cache_record.get("protected_p3_p4_c1_i1_read") is not False
        ):
            raise RuntimeError("E14 array-store lineage differs")

        with h5py.File(latent_h5, "r") as handle:
            latent = np.asarray(handle["latent"][:], dtype=np.float32)
        with h5py.File(cache_h5, "r") as handle:
            source = np.asarray(handle["source_index"][:], dtype=np.int64)
            local = np.asarray(handle["local_index"][:], dtype=np.int64)
            goal = np.asarray(handle["goal_index"][:], dtype=np.int64)
            self.role = np.asarray(handle["role"][:], dtype=np.uint8)
            self.delta = np.asarray(handle["delta"][:], dtype=np.int64)
            self.tau = np.asarray(handle["tau"][:], dtype=np.int64)
            state = np.asarray(handle["state"][:], dtype=np.float32)
            action = np.asarray(handle["action"][:], dtype=np.float32)
            action_mask = np.asarray(handle["action_mask"][:], dtype=np.bool_)
            latent_mean = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
            latent_std = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
            state_mean = np.asarray(handle["stats/state_mean"][:], dtype=np.float32)
            state_std = np.asarray(handle["stats/state_std"][:], dtype=np.float32)
            action_mean = np.asarray(handle["stats/action_mean"][:], dtype=np.float32)
            action_std = np.asarray(handle["stats/action_std"][:], dtype=np.float32)
            self.action_robust_low = np.asarray(
                handle["stats/action_robust_low"][:], dtype=np.float32
            )
            self.action_robust_high = np.asarray(
                handle["stats/action_robust_high"][:], dtype=np.float32
            )
            residual_mean = np.asarray(
                handle["stats/local_residual_mean"][:], dtype=np.float32
            )
            residual_std = np.asarray(
                handle["stats/local_residual_std"][:], dtype=np.float32
            )

        row_count = spec.TRAIN_ROWS + spec.VALIDATION_ROWS
        expected_action_shape = (
            row_count,
            spec.ACTION_HORIZON,
            int(task_spec["primitive_action_dim"]),
        )
        if (
            latent.ndim != 2
            or latent.shape[1] != spec.LATENT_DIM
            or any(len(value) != row_count for value in (source, local, goal, self.role, self.delta, self.tau, state))
            or action.shape != expected_action_shape
            or action_mask.shape != expected_action_shape[:2]
            or state.shape[1] != int(task_spec["state_dim"])
            or np.any(source < 0)
            or np.any(source >= len(latent))
            or np.any(local < 0)
            or np.any(local >= len(latent))
            or np.any(goal < 0)
            or np.any(goal >= len(latent))
        ):
            raise RuntimeError("E14 array-store shape differs")
        self.task = task
        self.latent_dim = spec.LATENT_DIM
        self.state_dim = int(task_spec["state_dim"])
        self.primitive_action_dim = int(task_spec["primitive_action_dim"])
        self.latent_mean = latent_mean
        self.latent_std = latent_std
        self.state_mean = state_mean
        self.state_std = state_std
        self.action_mean = action_mean
        self.action_std = action_std
        self.local_residual_mean = residual_mean
        self.local_residual_std = residual_std

        def latent_rows(rows: np.ndarray) -> np.ndarray:
            return np.ascontiguousarray(
                (latent[rows] - latent_mean) / latent_std, dtype=np.float32
            )

        self.current = latent_rows(source)
        self.local = latent_rows(local)
        self.goal = latent_rows(goal)
        del latent
        self.state = np.ascontiguousarray(
            (state - state_mean) / state_std, dtype=np.float32
        )
        self.action = np.ascontiguousarray(
            (action - action_mean[None, None]) / action_std[None, None],
            dtype=np.float32,
        )
        self.action[~action_mask] = 0.0
        self.action_mask = np.ascontiguousarray(action_mask)
        residual = self.local - self.goal
        self.local_residual = np.ascontiguousarray(
            (residual - residual_mean) / residual_std, dtype=np.float32
        )
        self.train_rows = np.flatnonzero(self.role == 0).astype(np.int64)
        self.validation_rows = np.flatnonzero(self.role == 1).astype(np.int64)
        if (
            len(self.train_rows) != spec.TRAIN_ROWS
            or len(self.validation_rows) != spec.VALIDATION_ROWS
            or not np.array_equal(
                self.action_mask,
                np.arange(spec.ACTION_HORIZON)[None] < self.tau[:, None],
            )
            or not all(
                np.isfinite(value).all()
                for value in (
                    self.current,
                    self.local,
                    self.goal,
                    self.state,
                    self.action,
                    self.local_residual,
                )
            )
        ):
            raise RuntimeError("E14 array-store normalized data differs")
        self.shuffled_goal_rows = deterministic_group_derangement(
            self.role, self.delta, self.tau, task=task
        )
        self.lineage = {
            "latent_h5_sha256": latent_sha,
            "latent_manifest_sha256": latent_manifest_sha,
            "cache_h5_sha256": cache_sha,
            "cache_manifest_sha256": cache_manifest_sha,
        }

    def batch(self, rows: np.ndarray, *, goal_mode: GoalMode = "true") -> E14Batch:
        rows = np.asarray(rows, dtype=np.int64)
        if rows.ndim != 1 or np.any(rows < 0) or np.any(rows >= len(self.role)):
            raise ValueError("invalid E14 batch rows")
        if goal_mode == "true":
            goal_rows = rows
        elif goal_mode == "shuffled":
            goal_rows = self.shuffled_goal_rows[rows]
        else:
            raise ValueError(f"unknown E14 goal mode: {goal_mode}")
        return E14Batch(
            current=torch.from_numpy(self.current[rows]),
            goal=torch.from_numpy(self.goal[goal_rows]),
            local=torch.from_numpy(self.local[rows]),
            state=torch.from_numpy(self.state[rows]),
            delta=torch.from_numpy(self.delta[rows]),
            tau=torch.from_numpy(self.tau[rows]),
            action=torch.from_numpy(self.action[rows]),
            action_mask=torch.from_numpy(self.action_mask[rows]),
            local_residual=torch.from_numpy(self.local_residual[rows]),
        )

    def checkpoint_validation_rows(self, *, seed: int) -> np.ndarray:
        generator = np.random.default_rng(
            spec.derived_seed(f"checkpoint-validation|task={self.task}|seed={seed}")
        )
        rows = generator.choice(
            self.validation_rows,
            size=spec.CHECKPOINT_VALIDATION_ROWS,
            replace=False,
        )
        return np.sort(rows.astype(np.int64))
