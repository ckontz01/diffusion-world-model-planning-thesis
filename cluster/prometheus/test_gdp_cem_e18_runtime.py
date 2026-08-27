from __future__ import annotations

import hashlib

import torch

import gdp_cem_e15_specs as e15
from gdp_cem_e18_runtime import (
    E15Statistics,
    E18ScheduledPolicy,
    read_sha256_records,
)


def test_inherited_statistics_validate() -> None:
    task = e15.TASK_SPEC["pusht"]
    state_dim = int(task["state_dim"])
    action_dim = int(task["primitive_action_dim"])
    statistics = E15Statistics(
        latent_mean=torch.zeros(e15.LATENT_DIM),
        latent_std=torch.ones(e15.LATENT_DIM),
        state_mean=torch.zeros(state_dim),
        state_std=torch.ones(state_dim),
        u_mean=torch.zeros(action_dim),
        u_std=torch.ones(action_dim),
        planner_action_mean=torch.zeros(action_dim),
        planner_action_std=torch.ones(action_dim),
        interior_scale=0.99,
        target_raw_limit=0.95,
    )
    statistics.validate(state_dim=state_dim, primitive_action_dim=action_dim)


def test_checksum_reader_and_schedule(tmp_path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"e18")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest = tmp_path / "sha256.txt"
    manifest.write_text(f"{digest}  payload.bin\n", encoding="utf-8")
    assert read_sha256_records(manifest) == {"payload.bin": digest}

    policy = E18ScheduledPolicy(
        object(),
        schedule=(15, 15),
        environment_budget=60,
        state_key="state",
        process={},
        transform={},
    )
    assert policy.stages == [(30, 15), (15, 15), (30, 15), (15, 15)]
