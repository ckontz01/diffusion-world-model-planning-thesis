from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

import gdp_cem_e14_specs as spec
from gdp_cem_e14_closed_loop import (
    E14Statistics,
    ScheduledE14Planner,
    ScheduledE14Policy,
)
from gdp_cem_e14_models import VariableDiagonalGaussian


class DummyWorldModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.anchor = torch.nn.Parameter(torch.zeros(()))

    def encode(self, info: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        pixels = info["pixels"].float()
        if pixels.ndim != 3 or pixels.shape[-1] != spec.LATENT_DIM:
            raise ValueError("dummy encoder expects precomputed latent-shaped pixels")
        return {**info, "emb": pixels + self.anchor}

    def action_encoder(self, action: torch.Tensor) -> torch.Tensor:
        return action

    def predict(
        self, embedding: torch.Tensor, action_embedding: torch.Tensor
    ) -> torch.Tensor:
        update = torch.zeros_like(embedding[:, -1:])
        width = min(update.shape[-1], action_embedding.shape[-1])
        update[..., :width] = action_embedding[:, -1:, :width]
        return embedding[:, -1:] + update


@dataclass
class DummyActionSpace:
    shape: tuple[int, int]


class DummyEnvironment:
    def __init__(self, n_envs: int, action_dim: int) -> None:
        self.num_envs = n_envs
        self.action_space = DummyActionSpace((n_envs, action_dim))


def statistics(*, state_dim: int = 7, action_dim: int = 2) -> E14Statistics:
    return E14Statistics(
        latent_mean=torch.zeros(spec.LATENT_DIM),
        latent_std=torch.ones(spec.LATENT_DIM),
        state_mean=torch.zeros(state_dim),
        state_std=torch.ones(state_dim),
        action_mean=torch.zeros(action_dim),
        action_std=torch.ones(action_dim),
        action_robust_low=torch.full((action_dim,), -3.0),
        action_robust_high=torch.full((action_dim,), 3.0),
        local_residual_mean=torch.zeros(spec.LATENT_DIM),
        local_residual_std=torch.ones(spec.LATENT_DIM),
    )


def online_info(batch: int, *, state_dim: int = 7) -> dict[str, torch.Tensor]:
    return {
        "pixels": torch.zeros(batch, 1, spec.LATENT_DIM),
        "goal": torch.ones(batch, 1, spec.LATENT_DIM),
        "state": torch.zeros(batch, 1, state_dim),
        "goal_state": torch.ones(batch, 1, state_dim),
    }


def test_base_cem_has_exact_shape_and_population_budget() -> None:
    batch = 2
    model = DummyWorldModel()
    planner = ScheduledE14Planner(
        model,
        arm="base_cem",
        statistics=statistics(),
        state_dim=7,
        primitive_action_dim=2,
        candidate_count=8,
        cem_rounds=3,
        elites=2,
        batch_size=1,
        planner_seed=11,
        proposal_seed=12,
    )
    planner.configure(action_space=DummyActionSpace((batch, 2)), n_envs=batch)
    result = planner.solve(
        online_info(batch),
        raw_state=torch.zeros(batch, 7),
        delta_value=75,
        tau_value=15,
    )
    assert result["actions"].shape == (batch, 3, 10)
    record = planner.diagnostic_history[-1]
    assert record["cem_rounds"] == 3
    assert record["lewm_population_calls"] == batch * 3
    assert record["planner_generator_before_sha256"] != record[
        "planner_generator_after_sha256"
    ]


def test_gaussian_selector_is_one_population_and_duration_masked() -> None:
    batch = 2
    action_dim = 2
    model = DummyWorldModel()
    gaussian = VariableDiagonalGaussian(
        latent_dim=spec.LATENT_DIM,
        state_dim=7,
        output_dim=spec.ACTION_HORIZON * action_dim,
        width=32,
        depth=1,
        time_embedding_dim=16,
    )
    planner = ScheduledE14Planner(
        model,
        arm="vad_gaussian",
        statistics=statistics(),
        state_dim=7,
        primitive_action_dim=action_dim,
        endpoint_model=gaussian,
        candidate_count=16,
        cem_rounds=30,
        elites=4,
        batch_size=1,
        planner_seed=21,
        proposal_seed=22,
    )
    planner.configure(action_space=DummyActionSpace((batch, action_dim)), n_envs=batch)
    result = planner.solve(
        online_info(batch),
        raw_state=torch.zeros(batch, 7),
        delta_value=75,
        tau_value=15,
    )
    assert result["actions"].shape == (batch, 3, 10)
    record = planner.diagnostic_history[-1]
    assert record["cem_rounds"] == 1
    assert record["lewm_population_calls"] == batch
    assert 1 <= record["minimum_unique_candidates"] <= 16
    assert 0.0 <= record["maximum_boundary_fraction"] <= 1.0


class RecordingPlanner:
    primitive_action_dim = 2
    device = torch.device("cpu")

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def configure(self, *, action_space: DummyActionSpace, n_envs: int) -> None:
        assert action_space.shape == (n_envs, self.primitive_action_dim)

    def solve(
        self,
        info_dict: dict[str, torch.Tensor],
        *,
        raw_state: torch.Tensor,
        delta_value: int,
        tau_value: int,
    ) -> dict[str, torch.Tensor]:
        self.calls.append((delta_value, tau_value))
        return {
            "actions": torch.full(
                (len(raw_state), tau_value // spec.ACTION_BLOCK, 10),
                float(len(self.calls)),
            )
        }


def test_pusht_policy_repeats_complete_schedule_for_two_h_budget() -> None:
    batch = 3
    planner = RecordingPlanner()
    policy = ScheduledE14Policy(
        planner,  # type: ignore[arg-type]
        schedule=spec.schedule_for(75),
        environment_budget=150,
        state_key="state",
        process={},
        transform={},
    )
    policy.set_env(DummyEnvironment(batch, 2))
    info = {
        "pixels": np.zeros((batch, 1, spec.LATENT_DIM), dtype=np.float32),
        "goal": np.ones((batch, 1, spec.LATENT_DIM), dtype=np.float32),
        "state": np.zeros((batch, 1, 7), dtype=np.float32),
    }
    actions = [policy.get_action(dict(info)) for _ in range(150)]
    assert all(action.shape == (batch, 2) for action in actions)
    expected_cycle = [(75, 15), (60, 15), (45, 15), (30, 15), (15, 15)]
    assert planner.calls == expected_cycle * 2
    assert np.all(actions[0] == 1.0)
    assert np.all(actions[14] == 1.0)
    assert np.all(actions[15] == 2.0)
    assert np.all(actions[75] == 6.0)


def test_policy_rejects_partial_schedule_budget() -> None:
    planner = RecordingPlanner()
    try:
        ScheduledE14Policy(
            planner,  # type: ignore[arg-type]
            schedule=spec.schedule_for(75),
            environment_budget=100,
            state_key="state",
            process={},
            transform={},
        )
    except ValueError as error:
        assert "whole schedule cycles" in str(error)
    else:
        raise AssertionError("partial E14 schedule budget was accepted")
