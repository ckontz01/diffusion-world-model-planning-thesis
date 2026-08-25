from __future__ import annotations

import numpy as np
import pytest
import torch
from torch import nn

import gdp_cem_e15_specs as spec
from gdp_cem_e14_closed_loop import E14Statistics
from gdp_cem_e14_models import SAGEOptionPrior, SAGESubgoalGenerator
from gdp_cem_e15_closed_loop import E15Statistics, InstrumentedE14Planner


class DummyWorldModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.anchor = nn.Parameter(torch.zeros(()))


def e14_statistics(action_dim: int = 2, state_dim: int = 7) -> E14Statistics:
    return E14Statistics(
        latent_mean=torch.zeros(spec.LATENT_DIM),
        latent_std=torch.ones(spec.LATENT_DIM),
        state_mean=torch.zeros(state_dim),
        state_std=torch.ones(state_dim),
        action_mean=torch.zeros(action_dim),
        action_std=torch.ones(action_dim),
        action_robust_low=-torch.ones(action_dim),
        action_robust_high=torch.ones(action_dim),
        local_residual_mean=torch.zeros(spec.LATENT_DIM),
        local_residual_std=torch.ones(spec.LATENT_DIM),
    )


def test_e15_online_statistics_reject_invalid_scale() -> None:
    statistics = E15Statistics(
        latent_mean=torch.zeros(spec.LATENT_DIM),
        latent_std=torch.ones(spec.LATENT_DIM),
        state_mean=torch.zeros(7),
        state_std=torch.ones(7),
        u_mean=torch.zeros(2),
        u_std=torch.ones(2),
        planner_action_mean=torch.zeros(2),
        planner_action_std=torch.ones(2),
        interior_scale=float(np.nextafter(np.float32(1.0), np.float32(0.0))),
        target_raw_limit=float(
            np.float32(
                np.nextafter(np.float32(1.0), np.float32(0.0)) ** np.float32(2.0)
            )
        ),
    )
    statistics.validate(state_dim=7, primitive_action_dim=2)
    invalid = E15Statistics(
        **{**statistics.__dict__, "planner_action_std": torch.tensor([1.0, 0.0])}
    )
    with pytest.raises(ValueError, match="range"):
        invalid.validate(state_dim=7, primitive_action_dim=2)


def test_sage_one_stage_is_the_same_stack_with_one_population() -> None:
    subgoal = SAGESubgoalGenerator(
        latent_dim=spec.LATENT_DIM,
        state_dim=7,
        width=16,
        heads=4,
        depth=1,
        feedforward_dim=32,
    )
    option = SAGEOptionPrior(
        latent_dim=spec.LATENT_DIM,
        state_dim=7,
        primitive_action_dim=2,
        width=16,
        heads=4,
        depth=1,
        feedforward_dim=32,
        modes=spec.GMM_MODES,
        action_blocks=5,
        block_size=5,
    )
    planner = InstrumentedE14Planner(
        DummyWorldModel(),
        reported_arm="sage_one_stage",
        one_stage=True,
        statistics=e14_statistics(),
        state_dim=7,
        primitive_action_dim=2,
        sage_subgoal=subgoal,
        sage_option=option,
        candidate_count=spec.CANDIDATE_COUNT,
        cem_rounds=1,
        elites=spec.CEM_ELITES,
        batch_size=1,
    )
    assert planner.arm == "sage_reconstruction"
    assert planner.reported_arm == "sage_one_stage"
    assert planner.cem_rounds == 1
    with pytest.raises(ValueError, match="one-stage"):
        InstrumentedE14Planner(
            DummyWorldModel(),
            reported_arm="sage_one_stage",
            one_stage=True,
            statistics=e14_statistics(),
            state_dim=7,
            primitive_action_dim=2,
            sage_subgoal=subgoal,
            sage_option=option,
            candidate_count=spec.CANDIDATE_COUNT,
            cem_rounds=30,
            elites=spec.CEM_ELITES,
            batch_size=1,
        )
