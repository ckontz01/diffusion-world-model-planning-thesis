from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch

import gdp_cem_e17_specs as spec
from gdp_cem_e17_models import TransitionStateAdapter


def test_protocol_hash_is_frozen() -> None:
    path = Path(__file__).with_name(
        "ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md"
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == spec.PROTOCOL_SHA256


def batch(*, rows: int = 4, state_dim: int = 7, action_dim: int = 2):
    tau = torch.tensor([15, 20, 25, 15][:rows], dtype=torch.long)
    mask = torch.arange(spec.ACTION_HORIZON)[None] < tau[:, None]
    action = torch.randn(rows, spec.ACTION_HORIZON, action_dim)
    action[~mask] = 0
    return {
        "current_latent": torch.randn(rows, spec.LATENT_DIM),
        "terminal_latent": torch.randn(rows, spec.LATENT_DIM),
        "current_state": torch.randn(rows, state_dim),
        "action_raw": action,
        "action_mask": mask,
        "tau": tau,
    }


def test_transition_adapter_shape_and_frozen_input_dimension() -> None:
    model = TransitionStateAdapter(state_dim=7, action_dim=2)
    value = batch()
    result = model(**value)
    assert result.shape == (4, 7)
    assert model.input_dim == spec.input_dim(state_dim=7, action_dim=2)


def test_zeroed_adapter_is_copy_current() -> None:
    model = TransitionStateAdapter(state_dim=7, action_dim=2)
    for parameter in model.parameters():
        torch.nn.init.zeros_(parameter)
    value = batch()
    assert torch.equal(model(**value), value["current_state"])


def test_transition_adapter_rejects_unknown_tau() -> None:
    model = TransitionStateAdapter(state_dim=7, action_dim=2)
    value = batch()
    value["tau"][0] = 10
    with pytest.raises(ValueError, match="unsupported E17 tau"):
        model(**value)


def test_transition_adapter_rejects_nonzero_inactive_action() -> None:
    model = TransitionStateAdapter(state_dim=7, action_dim=2)
    value = batch()
    value["action_raw"][0, 20, 0] = 1.0
    with pytest.raises(ValueError, match="inactive action"):
        model(**value)
