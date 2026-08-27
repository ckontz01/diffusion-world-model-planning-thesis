"""Self-contained runtime helpers for the frozen E18 planner study."""

from __future__ import annotations

import json
import os
import re
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import stable_worldmodel as swm
import torch

import gdp_cem_e15_specs as e15
import gdp_cem_e18_specs as spec
from gdp_cem_e15_data import sha256_file
from gdp_cem_e15_models import instantiate_model, model_config


CudaInterval = tuple[torch.cuda.Event, torch.cuda.Event]


def cuda_interval(function: Any) -> tuple[Any, CudaInterval]:
    """Record a CUDA component without an inner synchronization barrier."""

    started = torch.cuda.Event(enable_timing=True)
    finished = torch.cuda.Event(enable_timing=True)
    started.record()
    result = function()
    finished.record()
    return result, (started, finished)


def cuda_interval_seconds(intervals: list[CudaInterval]) -> float:
    """Resolve CUDA intervals after the enclosing planner synchronization."""

    return sum(float(started.elapsed_time(finished)) for started, finished in intervals) / 1_000.0


@dataclass(frozen=True)
class E15Statistics:
    """Pinned E15 normalization payload used by the unchanged proposers."""

    latent_mean: torch.Tensor
    latent_std: torch.Tensor
    state_mean: torch.Tensor
    state_std: torch.Tensor
    u_mean: torch.Tensor
    u_std: torch.Tensor
    planner_action_mean: torch.Tensor
    planner_action_std: torch.Tensor
    interior_scale: float
    target_raw_limit: float

    def to(self, device: torch.device) -> "E15Statistics":
        return E15Statistics(
            latent_mean=self.latent_mean.to(device=device, dtype=torch.float32),
            latent_std=self.latent_std.to(device=device, dtype=torch.float32),
            state_mean=self.state_mean.to(device=device, dtype=torch.float32),
            state_std=self.state_std.to(device=device, dtype=torch.float32),
            u_mean=self.u_mean.to(device=device, dtype=torch.float32),
            u_std=self.u_std.to(device=device, dtype=torch.float32),
            planner_action_mean=self.planner_action_mean.to(
                device=device, dtype=torch.float32
            ),
            planner_action_std=self.planner_action_std.to(
                device=device, dtype=torch.float32
            ),
            interior_scale=float(self.interior_scale),
            target_raw_limit=float(self.target_raw_limit),
        )

    def validate(self, *, state_dim: int, primitive_action_dim: int) -> None:
        expected = {
            "latent_mean": (e15.LATENT_DIM,),
            "latent_std": (e15.LATENT_DIM,),
            "state_mean": (state_dim,),
            "state_std": (state_dim,),
            "u_mean": (primitive_action_dim,),
            "u_std": (primitive_action_dim,),
            "planner_action_mean": (primitive_action_dim,),
            "planner_action_std": (primitive_action_dim,),
        }
        if any(
            getattr(self, name).shape != shape
            or not torch.isfinite(getattr(self, name)).all()
            for name, shape in expected.items()
        ):
            raise ValueError("invalid E18 inherited statistic shape")
        if (
            torch.any(self.latent_std <= 1.0e-6)
            or torch.any(self.state_std <= 1.0e-8)
            or torch.any(self.u_std <= 1.0e-6)
            or torch.any(self.planner_action_std <= 1.0e-8)
            or not 0.0 < self.target_raw_limit < self.interior_scale < 1.0
        ):
            raise ValueError("invalid E18 inherited statistic range")


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected E18 path is forbidden: {path}")


def read_sha256_records(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for raw_line in path.read_bytes().split(b"\n"):
        if not raw_line:
            continue
        digest_bytes, separator, filename_bytes = raw_line.partition(b" ")
        filename_bytes = filename_bytes.lstrip(b" *")
        if (
            not separator
            or len(digest_bytes) != 64
            or any(value not in b"0123456789abcdef" for value in digest_bytes.lower())
            or not filename_bytes
        ):
            raise RuntimeError(f"invalid E18 checksum record: {path}")
        name = Path(os.fsdecode(filename_bytes)).name
        if not name or name in records:
            raise RuntimeError(f"duplicate E18 checksum record: {path}")
        records[name] = digest_bytes.decode("ascii").lower()
    if not records:
        raise RuntimeError(f"empty E18 checksum manifest: {path}")
    return records


def verify_training_directory(directory: Path) -> None:
    records = read_sha256_records(directory / "sha256.txt")
    if set(records) != {"final.pt", "training.jsonl", "summary.json"}:
        raise RuntimeError("E18 inherited training checksum names differ")
    for name, digest in records.items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError("E18 inherited training checksum differs")


def e15_statistics(payload: dict[str, Any], *, task: str) -> E15Statistics:
    values = payload.get("statistics", {})
    tensor_names = (
        "latent_mean",
        "latent_std",
        "state_mean",
        "state_std",
        "u_mean",
        "u_std",
        "planner_action_mean",
        "planner_action_std",
    )
    if set(values) != {*tensor_names, "interior_scale", "target_raw_limit"} or any(
        not torch.is_tensor(values.get(name)) for name in tensor_names
    ):
        raise RuntimeError("E18 inherited checkpoint statistics differ")
    result = E15Statistics(
        **{name: values[name].float() for name in tensor_names},
        interior_scale=float(values["interior_scale"]),
        target_raw_limit=float(values["target_raw_limit"]),
    )
    task_spec = e15.TASK_SPEC[task]
    result.validate(
        state_dim=int(task_spec["state_dim"]),
        primitive_action_dim=int(task_spec["primitive_action_dim"]),
    )
    return result


def load_e15_proposer(
    training_root: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    device: torch.device,
) -> tuple[torch.nn.Module, E15Statistics, dict[str, Any]]:
    """Load one unchanged E15 final-EMA proposer with full lineage checks."""

    directory = training_root / task / condition / f"seed-{seed}"
    reject_protected_path(directory)
    verify_training_directory(directory)
    summary_path = directory / "summary.json"
    checkpoint_path = directory / "final.pt"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config = model_config(task, condition)
    expected_lineage = {
        "latent_h5_sha256": e15.TASK_SPEC[task]["latent_sha256"],
        "latent_manifest_sha256": e15.TASK_SPEC[task]["latent_manifest_sha256"],
        "cache_h5_sha256": e15.TASK_SPEC[task]["e15_cache_sha256"],
        "cache_manifest_sha256": e15.TASK_SPEC[task]["e15_cache_manifest_sha256"],
    }
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e15_p1_final_proposer_training"
        or summary.get("analysis_role")
        != "P1_train_only_long_horizon_method_development"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or int(summary.get("seed", -1)) != seed
        or summary.get("model_config") != config
        or summary.get("lineage") != expected_lineage
        or summary.get("checkpoint_selection")
        != "fixed_final_ema_step_30000_no_validation_access"
        or summary.get("checkpoint_sha256") != sha256_file(checkpoint_path)
        or int(summary.get("validation_payload_rows_read", -1)) != 0
        or summary.get("protocol_sha256") != e15.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != spec.E15_TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E18 inherited proposer training summary differs")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if (
        payload.get("kind") != "gdp_cem_e15_p1_final_proposer_checkpoint"
        or payload.get("task") != task
        or payload.get("condition") != condition
        or int(payload.get("seed", -1)) != seed
        or payload.get("model_config") != config
        or payload.get("lineage") != expected_lineage
        or int(payload.get("final_step", -1)) != e15.TRAIN_STEPS
        or int(payload.get("validation_payload_rows_read", -1)) != 0
        or payload.get("protocol_sha256") != e15.PROTOCOL_SHA256
        or payload.get("source_manifest_sha256")
        != spec.E15_TRAINING_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E18 inherited proposer checkpoint identity differs")
    statistics = e15_statistics(payload, task=task)
    model = instantiate_model(task, condition)
    model.load_state_dict(payload["ema_state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != int(summary.get("parameter_count", -1)):
        raise RuntimeError("E18 inherited proposer parameter count differs")
    return model, statistics, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "condition": condition,
        "seed": seed,
        "parameter_count": parameter_count,
    }


class E18ScheduledPolicy(swm.policy.BasePolicy):
    """Execute the frozen 15-action schedule for the E18 planner."""

    def __init__(
        self,
        planner: Any,
        *,
        schedule: tuple[int, ...],
        environment_budget: int,
        state_key: str,
        process: dict[str, Any],
        transform: dict[str, Any],
    ) -> None:
        super().__init__()
        if sum(schedule) <= 0 or environment_budget % sum(schedule):
            raise ValueError("E18 environment budget is not whole schedule cycles")
        self.type = "world_model"
        self.planner = planner
        self.base_schedule = tuple(schedule)
        self.environment_budget = int(environment_budget)
        self.state_key = state_key
        self.process = process
        self.transform = transform
        cycles = environment_budget // sum(schedule)
        self.stages: list[tuple[int, int]] = []
        for _ in range(cycles):
            elapsed = 0
            for tau in schedule:
                self.stages.append((sum(schedule) - elapsed, tau))
                elapsed += tau

    def set_env(self, env: Any) -> None:
        self.env = env
        self.planner.configure(action_space=env.action_space, n_envs=env.num_envs)
        self._action_buffer: deque[torch.Tensor] = deque(
            maxlen=max(self.base_schedule)
        )
        self._stage_index = 0

    def get_action(self, info_dict: dict[str, Any], **kwargs: Any) -> np.ndarray:
        if len(self._action_buffer) == 0:
            if self._stage_index >= len(self.stages):
                raise RuntimeError("E18 duration schedule exhausted before budget")
            if self.state_key not in info_dict:
                raise KeyError(f"E18 state key absent: {self.state_key}")
            raw_state = np.asarray(info_dict[self.state_key])
            if raw_state.ndim == 3:
                raw_state = raw_state[:, -1]
            if raw_state.ndim != 2:
                raise RuntimeError("E18 online raw-state shape differs")
            prepared = self._prepare_info(deepcopy(info_dict))
            for key, value in prepared.items():
                if torch.is_tensor(value):
                    prepared[key] = value.to(self.planner.device)
            delta, tau = self.stages[self._stage_index]
            result = self.planner.solve(
                prepared,
                raw_state=torch.from_numpy(raw_state).float(),
                delta_value=delta,
                tau_value=tau,
            )
            macro = result["actions"]
            plan = macro.reshape(
                self.env.num_envs, tau, self.planner.primitive_action_dim
            )
            self._action_buffer.extend(plan.transpose(0, 1))
            self._stage_index += 1
        action = self._action_buffer.popleft().reshape(*self.env.action_space.shape)
        result = action.numpy()
        if "action" in self.process:
            result = self.process["action"].inverse_transform(result)
        return result
