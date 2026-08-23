"""Unit tests for the frozen E14 model and sampler interfaces."""

from __future__ import annotations

import math

import torch

from gdp_cem_e14_models import (
    CosineSchedule,
    SAGEOptionPrior,
    SAGESubgoalGenerator,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    endpoint_active_mask,
    endpoint_output_dim,
    sample_trajectory_gmm,
    trajectory_gmm_nll,
    velocity_ddim_sample,
    velocity_target,
)


def _condition(batch: int = 3) -> tuple[torch.Tensor, ...]:
    generator = torch.Generator().manual_seed(1401)
    return (
        torch.randn(batch, 8, generator=generator),
        torch.randn(batch, 8, generator=generator),
        torch.randn(batch, 3, generator=generator),
        torch.tensor([25, 75, 150][:batch], dtype=torch.long),
        torch.tensor([15, 20, 25][:batch], dtype=torch.long),
    )


def test_endpoint_shapes_masks_and_network_outputs() -> None:
    current, goal, state, delta, tau = _condition()
    for endpoint in ("vad", "cvd"):
        output_dim = endpoint_output_dim(
            endpoint, latent_dim=8, primitive_action_dim=2
        )
        mask = endpoint_active_mask(
            endpoint,
            tau,
            latent_dim=8,
            primitive_action_dim=2,
        )
        assert mask.shape == (3, output_dim)
        assert mask.dtype == torch.bool
        action_offset = 0 if endpoint == "vad" else 8
        assert mask[0, action_offset:].sum().item() == 15 * 2
        assert mask[1, action_offset:].sum().item() == 20 * 2
        assert mask[2, action_offset:].sum().item() == 25 * 2
        if endpoint == "cvd":
            assert mask[:, :8].all()

        diffusion = VariableVelocityDiffusion(
            latent_dim=8,
            state_dim=3,
            output_dim=output_dim,
            width=32,
            depth=2,
            time_embedding_dim=16,
        )
        noisy = torch.randn(3, output_dim)
        timestep = torch.tensor([0, 50, 99], dtype=torch.long)
        conditioned = diffusion(
            current, goal, state, delta, tau, noisy, timestep, conditioned=True
        )
        mixed = diffusion(
            current,
            goal,
            state,
            delta,
            tau,
            noisy,
            timestep,
            conditioned=torch.tensor([True, False, True]),
        )
        unconditional = diffusion(
            current, goal, state, delta, tau, noisy, timestep, conditioned=False
        )
        assert conditioned.shape == noisy.shape
        assert mixed.shape == noisy.shape
        assert torch.equal(mixed[0], conditioned[0])
        assert torch.equal(mixed[1], unconditional[1])
        assert torch.equal(mixed[2], conditioned[2])

        gaussian = VariableDiagonalGaussian(
            latent_dim=8,
            state_dim=3,
            output_dim=output_dim,
            width=32,
            depth=2,
            time_embedding_dim=16,
        )
        mean, log_std = gaussian(current, goal, state, delta, tau)
        assert mean.shape == noisy.shape
        assert log_std.shape == noisy.shape
        assert torch.isfinite(mean).all() and torch.isfinite(log_std).all()


def test_velocity_target_and_sampler_are_finite_deterministic_and_masked() -> None:
    current, goal, state, delta, tau = _condition()
    output_dim = endpoint_output_dim("vad", latent_dim=8, primitive_action_dim=2)
    mask = endpoint_active_mask(
        "vad", tau, latent_dim=8, primitive_action_dim=2
    )
    model = VariableVelocityDiffusion(
        latent_dim=8,
        state_dim=3,
        output_dim=output_dim,
        width=32,
        depth=2,
        time_embedding_dim=16,
    ).eval()
    initial_noise = torch.randn(3, 4, output_dim, generator=torch.Generator().manual_seed(1402))
    arguments = dict(
        current=current,
        goal=goal,
        state=state,
        delta=delta,
        tau=tau,
        initial_noise=initial_noise,
        active_mask=mask,
        schedule=CosineSchedule.build(100),
        evaluations=5,
        guidance_scale=1.5,
    )
    first = velocity_ddim_sample(model, **arguments)
    second = velocity_ddim_sample(model, **arguments)
    assert torch.equal(first, second)
    assert torch.isfinite(first).all()
    inactive = (~mask)[:, None].expand_as(first)
    assert torch.equal(first[inactive], torch.zeros_like(first[inactive]))

    clean = torch.randn(3, output_dim)
    noise = torch.randn_like(clean)
    alpha = torch.tensor([[0.2], [0.5], [0.8]])
    target = velocity_target(clean, noise, alpha)
    assert torch.allclose(
        target, alpha.sqrt() * noise - (1.0 - alpha).sqrt() * clean
    )


def test_sage_shapes_gmm_likelihood_and_sampling() -> None:
    current, goal, state, delta, tau = _condition()
    subgoal = SAGESubgoalGenerator(
        latent_dim=8,
        state_dim=3,
        width=32,
        depth=2,
        heads=4,
        feedforward_dim=64,
    )
    local = subgoal(current, goal, state, delta, tau)
    assert local.shape == current.shape
    assert torch.isfinite(local).all()

    option = SAGEOptionPrior(
        latent_dim=8,
        state_dim=3,
        primitive_action_dim=2,
        width=32,
        depth=2,
        heads=4,
        feedforward_dim=64,
        modes=3,
    )
    logits, means, log_stds = option(current, goal, local, state, delta, tau)
    assert logits.shape == (3, 3)
    assert means.shape == (3, 3, 25, 2)
    assert log_stds.shape == means.shape

    active = torch.arange(25)[None] < tau[:, None]
    target = torch.randn(3, 25, 2)
    nll = trajectory_gmm_nll(logits, means, log_stds, target, active)
    assert nll.shape == (3,)
    assert torch.isfinite(nll).all()

    one_logits = torch.zeros(1, 1)
    one_means = torch.zeros(1, 1, 2, 1)
    one_log_stds = torch.zeros_like(one_means)
    one_target = torch.tensor([[[2.0], [7.0]]])
    one_mask = torch.tensor([[True, False]])
    manual = 0.5 * 2.0**2 + 0.5 * math.log(2.0 * math.pi)
    observed = trajectory_gmm_nll(
        one_logits, one_means, one_log_stds, one_target, one_mask
    )
    assert torch.allclose(observed, torch.tensor([manual]))

    first = sample_trajectory_gmm(
        logits,
        means,
        log_stds,
        count=5,
        active_mask=active,
        generator=torch.Generator().manual_seed(1403),
    )
    second = sample_trajectory_gmm(
        logits,
        means,
        log_stds,
        count=5,
        active_mask=active,
        generator=torch.Generator().manual_seed(1403),
    )
    assert first.shape == (3, 5, 25, 2)
    assert torch.equal(first, second)
    inactive = (~active)[:, None, :, None].expand_as(first)
    assert torch.equal(first[inactive], torch.zeros_like(first[inactive]))


def test_disclosed_sage_parameter_counts_are_in_target_range() -> None:
    subgoal = SAGESubgoalGenerator(latent_dim=192, state_dim=7)
    option = SAGEOptionPrior(
        latent_dim=192, state_dim=7, primitive_action_dim=2
    )
    subgoal_parameters = sum(parameter.numel() for parameter in subgoal.parameters())
    option_parameters = sum(parameter.numel() for parameter in option.parameters())
    assert 20_000_000 <= subgoal_parameters <= 22_000_000
    assert 12_000_000 <= option_parameters <= 15_000_000

