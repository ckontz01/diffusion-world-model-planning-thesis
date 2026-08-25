from __future__ import annotations

import numpy as np
import torch

import gdp_cem_e15_specs as spec
from gdp_cem_e15_data import E15Batch, deterministic_group_derangement


def test_group_derangement_stays_in_cell_and_changes_episode(monkeypatch) -> None:
    monkeypatch.setattr(spec, "DELTA_TAU_PAIRS", ((15, 15),))
    role = np.asarray([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.uint8)
    delta = np.full(8, 15, dtype=np.int64)
    tau = np.full(8, 15, dtype=np.int64)
    episode = np.asarray([1, 1, 2, 2, 3, 3, 4, 4], dtype=np.int64)
    result = deterministic_group_derangement(
        role, delta, tau, episode, task="pusht"
    )
    assert np.array_equal(role[result], role)
    assert np.array_equal(delta[result], delta)
    assert np.array_equal(tau[result], tau)
    assert np.all(episode[result] != episode)


def test_flat_target_masks_inactive_dimensions() -> None:
    action = torch.arange(12, dtype=torch.float32).reshape(2, 3, 2)
    mask = torch.tensor([[True, True, False], [True, False, False]])
    action[~mask] = 0
    batch = E15Batch(
        current=torch.zeros(2, 4),
        goal=torch.zeros(2, 4),
        local=torch.zeros(2, 4),
        state=torch.zeros(2, 2),
        delta=torch.tensor([3, 3]),
        tau=torch.tensor([2, 1]),
        action_u=action,
        action_mask=mask,
        action_raw_projected=torch.zeros_like(action),
        action_raw_original=torch.zeros_like(action),
    )
    target, flat_mask = batch.flat_target()
    assert target.shape == (2, 6)
    assert flat_mask.shape == (2, 6)
    assert torch.all(target[~flat_mask] == 0)
