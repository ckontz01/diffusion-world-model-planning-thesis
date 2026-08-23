"""Unit tests for E14 full-validation aggregation and objectives."""

from __future__ import annotations

import numpy as np
import torch

import gdp_cem_e14_specs as spec
from evaluate_gdp_cem_e14_offline import aggregate_metrics, family_objective
from gdp_cem_e14_models import CosineSchedule, VariableDiagonalGaussian


def test_equal_cell_and_equal_delta_aggregation() -> None:
    delta = np.asarray(
        [value for value, _ in spec.DELTA_TAU_PAIRS for _ in range(2)],
        dtype=np.int64,
    )
    tau = np.asarray(
        [value for _, value in spec.DELTA_TAU_PAIRS for _ in range(2)],
        dtype=np.int64,
    )
    metric = np.arange(len(delta), dtype=np.float64)
    result = aggregate_metrics(
        delta=delta,
        tau=tau,
        metrics={"metric": metric},
    )
    cell_means = [
        metric[(delta == delta_value) & (tau == tau_value)].mean()
        for delta_value, tau_value in spec.DELTA_TAU_PAIRS
    ]
    assert result["equal_cell_mean"]["metric"] == float(np.mean(cell_means))
    for tau_value in spec.TAU_VALUES:
        expected = np.mean(
            [
                value
                for value, (_, cell_tau) in zip(cell_means, spec.DELTA_TAU_PAIRS)
                if cell_tau == tau_value
            ]
        )
        assert result["per_tau"][str(tau_value)]["metric"] == float(expected)


def test_gaussian_family_objective_matches_manual_masked_nll() -> None:
    model = VariableDiagonalGaussian(
        latent_dim=8,
        state_dim=3,
        output_dim=6,
        width=32,
        depth=2,
        time_embedding_dim=16,
    ).eval()
    current = torch.randn(2, 8)
    goal = torch.randn(2, 8)
    state = torch.randn(2, 3)
    delta = torch.tensor([25, 75])
    tau = torch.tensor([15, 20])
    clean = torch.randn(2, 6)
    mask = torch.tensor(
        [[True, True, False, False, False, False], [True] * 6]
    )
    observed = family_objective(
        model,
        family="gaussian",
        current=current,
        goal=goal,
        state=state,
        delta=delta,
        tau=tau,
        clean=clean,
        mask=mask,
        schedule=CosineSchedule.build(100),
        generator=torch.Generator().manual_seed(17),
    )
    mean, log_std = model(current, goal, state, delta, tau)
    element = (
        0.5 * ((clean - mean) / log_std.exp()).square()
        + log_std
        + 0.5 * np.log(2.0 * np.pi)
    )
    expected = (element * mask).sum(dim=-1) / mask.sum(dim=-1)
    assert torch.allclose(observed, expected)

