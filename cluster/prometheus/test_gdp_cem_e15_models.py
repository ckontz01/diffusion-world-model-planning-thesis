from __future__ import annotations

import math

import numpy as np
import torch

import gdp_cem_e15_specs as spec
from gdp_cem_e15_models import (
    DirectTrajectoryGMM,
    action_active_mask,
    bounded_actions_from_standardized_u,
    direct_gmm_loss,
    sample_direct_gmm_with_modes,
    trajectory_gmm_posterior,
)


def test_direct_gmm_shapes_and_independent_loss() -> None:
    torch.manual_seed(4)
    model = DirectTrajectoryGMM(
        latent_dim=4,
        state_dim=3,
        primitive_action_dim=2,
        horizon=3,
        modes=2,
        width=16,
        depth=2,
    )
    current = torch.randn(5, 4)
    goal = torch.randn(5, 4)
    state = torch.randn(5, 3)
    delta = torch.tensor([3, 3, 3, 3, 3])
    tau = torch.tensor([1, 2, 3, 2, 1])
    logits, means, log_stds = model(current, goal, state, delta, tau)
    target = torch.randn(5, 3, 2)
    mask = torch.arange(3)[None] < tau[:, None]
    total, normalized, balance = direct_gmm_loss(
        logits, means, log_stds, target, mask
    )
    terms = []
    for row in range(5):
        component = []
        active = int(tau[row])
        for mode in range(2):
            value = 0.0
            for time in range(active):
                for dim in range(2):
                    std = log_stds[row, mode, time, dim].exp()
                    z = (target[row, time, dim] - means[row, mode, time, dim]) / std
                    value += float(0.5 * z.square() + std.log() + 0.5 * math.log(2 * math.pi))
            component.append(float(torch.log_softmax(logits[row], -1)[mode]) - value)
        terms.append(-float(torch.logsumexp(torch.tensor(component), 0)) / (active * 2))
    expected_nll = torch.tensor(terms).mean()
    pbar = torch.softmax(logits, -1).mean(0)
    expected_balance = (pbar * (pbar.log() + math.log(2))).sum()
    assert torch.allclose(normalized, expected_nll, atol=1e-5)
    assert torch.allclose(balance, expected_balance, atol=1e-6)
    assert torch.allclose(total, normalized + spec.GMM_BALANCE_WEIGHT * balance)
    posterior = trajectory_gmm_posterior(logits, means, log_stds, target, mask)
    assert posterior.shape == (5, 2)
    assert torch.allclose(posterior.sum(-1), torch.ones(5), atol=1e-6)


def test_common_bounded_decoder_is_strictly_legal_and_matches_numpy() -> None:
    standardized = torch.tensor(
        [[[[20.0, -20.0], [0.25, -0.5], [0.0, 0.0]]]], dtype=torch.float32
    )
    active = torch.tensor([[[True, True], [True, True], [False, False]]])
    u_mean = torch.tensor([0.2, -0.1])
    u_std = torch.tensor([1.5, 0.7])
    planner_mean = torch.tensor([0.3, -0.4])
    planner_std = torch.tensor([0.5, 2.0])
    scale = float(np.nextafter(np.float32(1), np.float32(0)))
    raw, planner, jacobian = bounded_actions_from_standardized_u(
        standardized,
        u_mean=u_mean,
        u_std=u_std,
        planner_mean=planner_mean,
        planner_std=planner_std,
        interior_scale=scale,
        active_mask=active,
    )
    u_np = standardized.numpy() * u_std.numpy() + u_mean.numpy()
    smooth_np = np.float32(scale) * np.tanh(u_np).astype(np.float32)
    smooth_np[:, :, 2] = 0
    # libtorch and NumPy tanh may differ by one float32 unit. The smooth map
    # must agree within that fixed envelope; the subsequent planner transform
    # must reproduce the two in-place float32 operations bit exactly.
    assert np.allclose(
        raw.numpy(), smooth_np, rtol=0.0, atol=np.finfo(np.float32).eps
    )
    planner_np = raw.numpy().copy()
    planner_np -= planner_mean.numpy().astype(np.float32)
    planner_np /= planner_std.numpy().astype(np.float32)
    planner_np[:, :, 2] = 0
    assert np.array_equal(planner.numpy(), planner_np)
    assert torch.all(torch.abs(raw[active[:, None].expand_as(raw)]) < 1)
    assert torch.all(jacobian >= 0)


def test_action_mask_expands_duration() -> None:
    mask = action_active_mask(
        torch.tensor([1, 3]), primitive_action_dim=2, horizon=3
    )
    assert mask.shape == (2, 3, 2)
    assert mask[0].sum() == 2
    assert mask[1].sum() == 6


def test_direct_gmm_draw_uses_one_mode_for_whole_trajectory() -> None:
    logits = torch.tensor([[20.0, -20.0], [-20.0, 20.0]])
    means = torch.zeros(2, 2, 3, 1)
    means[:, 1] = 10.0
    log_stds = torch.full_like(means, -20.0)
    mask = torch.tensor([[True, True, False], [True, True, True]])
    first_generator = torch.Generator(device="cpu").manual_seed(99)
    second_generator = torch.Generator(device="cpu").manual_seed(99)
    sample, mode = sample_direct_gmm_with_modes(
        logits,
        means,
        log_stds,
        count=5,
        active_mask=mask,
        generator=first_generator,
    )
    repeated, repeated_mode = sample_direct_gmm_with_modes(
        logits,
        means,
        log_stds,
        count=5,
        active_mask=mask,
        generator=second_generator,
    )
    assert torch.equal(mode, repeated_mode)
    assert torch.equal(sample, repeated)
    assert torch.all(mode[0] == 0)
    assert torch.all(mode[1] == 1)
    assert torch.all(sample[0, :, :2].abs() < 1.0e-6)
    assert torch.all((sample[1, :, :3] - 10.0).abs() < 1.0e-6)
    assert torch.all(sample[0, :, 2] == 0)
