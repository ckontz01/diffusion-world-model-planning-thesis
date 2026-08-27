from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from gdp_cem_e17_models import TransitionStateAdapter
from gdp_cem_e18_closed_loop import E18Planner, continuation_score


def test_continuation_score_is_best_two_mean() -> None:
    value = torch.tensor([[[9.0, 3.0, 5.0, 1.0, 7.0, 8.0, 6.0, 4.0]]])
    assert continuation_score(value).item() == pytest.approx(2.0)
    with pytest.raises(ValueError):
        continuation_score(value[..., :7])


def test_action_conditioned_adapter_bridge_shapes() -> None:
    planner = object.__new__(E18Planner)
    planner.state_dim = 7
    planner.primitive_action_dim = 2
    planner.statistics = SimpleNamespace(
        latent_mean=torch.zeros(192), latent_std=torch.ones(192)
    )
    planner.state_adapter = TransitionStateAdapter(state_dim=7, action_dim=2)
    batch, count = 2, 3
    current = torch.randn(batch, 192)
    terminal = torch.randn(batch, count, 192)
    state = torch.randn(batch, 7)
    action = torch.zeros(batch, count, 25, 2)
    action[:, :, :15] = torch.randn(batch, count, 15, 2).tanh()
    tau = torch.full((batch,), 15, dtype=torch.long)
    predicted, normalized = planner._predict_intermediate_state(
        current=current,
        terminal_raw=terminal,
        state=state,
        first_raw=action,
        tau=tau,
    )
    assert predicted.shape == (batch * count, 7)
    assert normalized.shape == (batch * count, 192)
    assert torch.isfinite(predicted).all()


def test_adapter_bridge_rejects_nonzero_inactive_actions() -> None:
    planner = object.__new__(E18Planner)
    planner.state_dim = 7
    planner.primitive_action_dim = 2
    planner.statistics = SimpleNamespace(
        latent_mean=torch.zeros(192), latent_std=torch.ones(192)
    )
    planner.state_adapter = TransitionStateAdapter(state_dim=7, action_dim=2)
    action = torch.zeros(1, 1, 25, 2)
    action[:, :, 20] = 0.5
    with pytest.raises(ValueError):
        planner._predict_intermediate_state(
            current=torch.zeros(1, 192),
            terminal_raw=torch.zeros(1, 1, 192),
            state=torch.zeros(1, 7),
            first_raw=action,
            tau=torch.tensor([15]),
        )
