#!/usr/bin/env python3
"""P1-only datasets shared by E12 PRISM training jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import hdf5plugin  # noqa: F401 - registers the datasets' compression filters
import numpy as np
import torch
from torch.utils.data import Dataset


P1_TRAIN = np.uint8(0)
P1_VALIDATION = np.uint8(1)
IMAGENET_MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)


def load_prism_head_arrays(
    *,
    sequence_h5: Path,
    latent_h5: Path,
    goal_mode: str,
) -> dict[str, np.ndarray | int]:
    """Materialize the exact P1 latent/action inputs for a PriorHead job."""

    if goal_mode not in {"h25", "endframe"}:
        raise ValueError("invalid E12 PRISM head goal mode")
    with h5py.File(latent_h5, "r") as handle:
        latents = np.asarray(handle["latent"][:], dtype=np.float32)
        row_index = np.asarray(handle["row_index"][:], dtype=np.int64)
        episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        step = np.asarray(handle["step_idx"][:], dtype=np.int64)
    with h5py.File(sequence_h5, "r") as handle:
        source_index = np.asarray(handle["source_index"][:], dtype=np.int64)
        h25_goal_index = np.asarray(handle["goal_index"][:], dtype=np.int64)
        sequence_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        sequence_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        role = np.asarray(handle["role"][:], dtype=np.uint8)
        macro_action = np.asarray(handle["action"][:], dtype=np.float32)
        planner_action_mean = np.asarray(
            handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
        ).astype(np.float32)
        planner_action_std = np.asarray(
            handle["stats/planner_primitive_action_std"][:], dtype=np.float64
        ).astype(np.float32)
        goal_offset = int(handle.attrs["goal_offset"])
        macro_horizon = int(handle.attrs["macro_horizon"])
        primitive_steps = int(handle.attrs["primitive_steps_per_macro"])
    if (
        goal_offset != 25
        or macro_horizon != 5
        or primitive_steps != 5
        or latents.ndim != 2
        or latents.shape[1] != 192
        or len(row_index) != len(latents)
        or len(episode) != len(latents)
        or len(step) != len(latents)
        or not (
            len(source_index)
            == len(h25_goal_index)
            == len(sequence_episode)
            == len(sequence_step)
            == len(role)
            == len(macro_action)
        )
        or set(np.unique(role).tolist()) != {int(P1_TRAIN), int(P1_VALIDATION)}
        or np.any(source_index < 0)
        or np.any(h25_goal_index >= len(latents))
        or np.any(episode[source_index] != sequence_episode)
        or np.any(episode[h25_goal_index] != sequence_episode)
        or np.any(step[source_index] != sequence_step)
        or np.any(step[h25_goal_index] - step[source_index] != 25)
        or not np.isfinite(latents).all()
        or not np.isfinite(macro_action).all()
    ):
        raise RuntimeError("invalid E12 PRISM P1 latent/action arrays")

    primitive_action_dim = int(macro_action.shape[-1] // primitive_steps)
    planner_actions = macro_action.reshape(len(macro_action), 25, primitive_action_dim)
    if (
        planner_action_mean.shape != (primitive_action_dim,)
        or planner_action_std.shape != (primitive_action_dim,)
        or np.any(planner_action_std <= 1.0e-8)
    ):
        raise RuntimeError("invalid shared planner action scaler")
    actions = (
        planner_actions * planner_action_std.reshape(1, 1, -1)
        + planner_action_mean.reshape(1, 1, -1)
    ).astype(np.float32)
    train_actions = actions[role == P1_TRAIN].reshape(-1, primitive_action_dim)
    action_mean = train_actions.mean(axis=0, dtype=np.float64).astype(np.float32)
    action_std = train_actions.std(axis=0, dtype=np.float64).astype(np.float32)
    if np.any(action_std <= 1.0e-8):
        raise RuntimeError("degenerate E12 PRISM P1 action scaler")
    normalized_actions = (actions - action_mean) / action_std

    if goal_mode == "h25":
        goal_index = h25_goal_index
    else:
        max_episode = int(episode.max())
        maximum_step = np.full(max_episode + 1, -1, dtype=np.int64)
        np.maximum.at(maximum_step, episode, step)
        final_mask = step == maximum_step[episode]
        endframe_index = np.full(max_episode + 1, -1, dtype=np.int64)
        endframe_index[episode[final_mask]] = np.flatnonzero(final_mask)
        goal_index = endframe_index[sequence_episode]
        if np.any(goal_index < 0) or np.any(episode[goal_index] != sequence_episode):
            raise RuntimeError("failed to map E12 PRISM episode-final goals")

    return {
        "latents": latents,
        "row_index": row_index,
        "episode": episode,
        "step": step,
        "source_index": source_index,
        "goal_index": goal_index,
        "sequence_episode": sequence_episode,
        "sequence_step": sequence_step,
        "role": role,
        "actions": actions,
        "normalized_actions": normalized_actions.astype(np.float32),
        "action_mean": action_mean,
        "action_std": action_std,
        "planner_action_mean": planner_action_mean,
        "planner_action_std": planner_action_std,
        "primitive_action_dim": primitive_action_dim,
    }


class PrismDPP1Dataset(Dataset[dict[str, torch.Tensor]]):
    """Read only P1 rows through the pre-audited sequence/latent lineage.

    The raw Stable-WorldModel HDF5 is opened lazily per worker.  No episode not
    represented by the selected P1 role can be indexed by this object.
    """

    def __init__(
        self,
        *,
        dataset_h5: Path,
        sequence_h5: Path,
        latent_h5: Path,
        role: str,
        action_min: np.ndarray | None = None,
        action_max: np.ndarray | None = None,
    ) -> None:
        super().__init__()
        if role not in {"P1_train", "P1_val"}:
            raise ValueError("invalid E12 PRISM-DP P1 role")
        self.dataset_h5 = str(dataset_h5)
        self.sequence_h5 = str(sequence_h5)
        self.latent_h5 = str(latent_h5)
        self.role_name = role
        self.role_code = P1_TRAIN if role == "P1_train" else P1_VALIDATION
        with h5py.File(latent_h5, "r") as handle:
            row_index = np.asarray(handle["row_index"][:], dtype=np.int64)
            latent_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
            latent_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
        with h5py.File(sequence_h5, "r") as handle:
            source_index = np.asarray(handle["source_index"][:], dtype=np.int64)
            goal_index = np.asarray(handle["goal_index"][:], dtype=np.int64)
            sequence_episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
            sequence_step = np.asarray(handle["step_idx"][:], dtype=np.int64)
            roles = np.asarray(handle["role"][:], dtype=np.uint8)
            macro_action = np.asarray(handle["action"][:], dtype=np.float32)
            planner_action_mean = np.asarray(
                handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
            ).astype(np.float32)
            planner_action_std = np.asarray(
                handle["stats/planner_primitive_action_std"][:], dtype=np.float64
            ).astype(np.float32)
            goal_offset = int(handle.attrs["goal_offset"])
            macro_horizon = int(handle.attrs["macro_horizon"])
            primitive_steps = int(handle.attrs["primitive_steps_per_macro"])
        selected = np.flatnonzero(roles == self.role_code)
        if (
            not len(selected)
            or goal_offset != 25
            or macro_horizon != 5
            or primitive_steps != 5
            or np.any(source_index[selected] < 0)
            or np.any(goal_index[selected] >= len(row_index))
            or np.any(latent_episode[source_index[selected]] != sequence_episode[selected])
            or np.any(latent_episode[goal_index[selected]] != sequence_episode[selected])
            or np.any(latent_step[source_index[selected]] != sequence_step[selected])
            or np.any(
                latent_step[goal_index[selected]] - latent_step[source_index[selected]]
                != 25
            )
        ):
            raise RuntimeError("invalid E12 PRISM-DP P1 sequence lineage")
        self.sequence_rows = selected.astype(np.int64)
        self.source_global_rows = row_index[source_index[selected]].astype(np.int64)
        self.goal_global_rows = row_index[goal_index[selected]].astype(np.int64)
        self.episode_ids = sequence_episode[selected].astype(np.int64)
        self.start_steps = sequence_step[selected].astype(np.int64)
        primitive_action_dim = int(macro_action.shape[-1] // primitive_steps)
        self.action_dim = primitive_action_dim
        self.action_horizon = 25
        planner_actions = macro_action[selected].reshape(
            len(selected), self.action_horizon, self.action_dim
        )
        if (
            planner_action_mean.shape != (self.action_dim,)
            or planner_action_std.shape != (self.action_dim,)
            or np.any(planner_action_std <= 1.0e-8)
        ):
            raise RuntimeError("invalid E12 PRISM-DP planner action scaler")
        self.planner_action_mean = planner_action_mean
        self.planner_action_std = planner_action_std
        self.actions = (
            planner_actions * planner_action_std.reshape(1, 1, -1)
            + planner_action_mean.reshape(1, 1, -1)
        ).astype(np.float32)
        if not np.isfinite(self.actions).all():
            raise RuntimeError("non-finite E12 PRISM-DP actions")

        if role == "P1_train":
            flat = self.actions.reshape(-1, self.action_dim)
            self.action_min = flat.min(axis=0).astype(np.float32)
            self.action_max = flat.max(axis=0).astype(np.float32)
        else:
            if action_min is None or action_max is None:
                raise ValueError("P1_val requires P1_train action bounds")
            self.action_min = np.asarray(action_min, dtype=np.float32)
            self.action_max = np.asarray(action_max, dtype=np.float32)
        if (
            self.action_min.shape != (self.action_dim,)
            or self.action_max.shape != (self.action_dim,)
            or np.any(self.action_max <= self.action_min)
        ):
            raise RuntimeError("invalid E12 PRISM-DP action min/max")
        with h5py.File(dataset_h5, "r") as handle:
            if "pixels" not in handle:
                raise KeyError("pixels missing from E12 PRISM-DP dataset")
            pixel_count = len(handle["pixels"])
        if (
            np.any(self.source_global_rows < 0)
            or np.any(self.goal_global_rows < 0)
            or np.any(self.source_global_rows >= pixel_count)
            or np.any(self.goal_global_rows >= pixel_count)
        ):
            raise RuntimeError("E12 PRISM-DP pixel row outside dataset")
        self._handle: h5py.File | None = None

    def __len__(self) -> int:
        return len(self.sequence_rows)

    def _h5(self) -> h5py.File:
        if self._handle is None:
            self._handle = h5py.File(self.dataset_h5, "r", swmr=True)
        return self._handle

    @staticmethod
    def _prepare_image(value: np.ndarray) -> np.ndarray:
        array = np.asarray(value)
        if array.ndim == 4:
            array = array[-1]
        if array.ndim != 3 or array.shape[-1] != 3:
            raise RuntimeError(f"invalid E12 PRISM-DP RGB shape {array.shape}")
        image = array.astype(np.float32)
        if array.dtype == np.uint8 or float(image.max(initial=0.0)) > 1.5:
            image /= 255.0
        image = np.transpose(image, (2, 0, 1))
        return (image - IMAGENET_MEAN) / IMAGENET_STD

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        handle = self._h5()
        observation = self._prepare_image(
            handle["pixels"][int(self.source_global_rows[index])]
        )
        goal = self._prepare_image(handle["pixels"][int(self.goal_global_rows[index])])
        scale = self.action_max - self.action_min
        action = (
            2.0 * (self.actions[index] - self.action_min) / scale - 1.0
        ).astype(np.float32)
        return {
            "observation": torch.from_numpy(observation.copy()),
            "goal": torch.from_numpy(goal.copy()),
            "action": torch.from_numpy(action.copy()),
            "episode_id": torch.tensor(self.episode_ids[index], dtype=torch.int64),
            "start_step": torch.tensor(self.start_steps[index], dtype=torch.int64),
            "sequence_row": torch.tensor(self.sequence_rows[index], dtype=torch.int64),
        }

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_handle"] = None
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
