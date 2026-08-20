#!/usr/bin/env python3
"""Shape, determinism, and Gaussian-control tests for GDP-CEM."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    CosineDiffusionSchedule,
    GaussianAnchoredRefinementSampler,
    GoalConditionedProposalSampler,
    JointActionDiffusion,
    ProposalCEMSolver,
    VelocityActionDiffusion,
    classifier_free_velocity_prediction,
    ddim_refine_epsilon,
    ddim_sample,
    gaussian_sample,
    velocity_ddim_sample,
)


class EncodeWorld(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.marker = torch.nn.Parameter(torch.zeros(()))

    def encode(self, info):
        return {"emb": info["pixels"]}


class OracleEpsilon(torch.nn.Module):
    def __init__(self, schedule: CosineDiffusionSchedule) -> None:
        super().__init__()
        self.action_horizon = 25
        self.primitive_action_dim = 2
        self.register_buffer("alpha_bar", schedule.alpha_bar.clone())

    def forward(self, current, goal, noisy_action, timestep):
        del goal
        clean = current.reshape(-1, self.action_horizon, self.primitive_action_dim)
        alpha = self.alpha_bar[timestep].view(-1, 1, 1)
        return (noisy_action - alpha.sqrt() * clean) / (1.0 - alpha).sqrt()


class OracleVelocity(torch.nn.Module):
    def __init__(self, schedule: CosineDiffusionSchedule) -> None:
        super().__init__()
        self.latent_dim = 50
        self.action_horizon = 25
        self.primitive_action_dim = 2
        self.register_buffer("alpha_bar", schedule.alpha_bar.clone())

    def forward(
        self, current, goal, noisy_action, timestep, conditioned=True
    ):
        del goal, conditioned
        clean = current.reshape(-1, self.action_horizon, self.primitive_action_dim)
        alpha = self.alpha_bar[timestep].view(-1, 1, 1)
        noise = (noisy_action - alpha.sqrt() * clean) / (1.0 - alpha).sqrt()
        return alpha.sqrt() * noise - (1.0 - alpha).sqrt() * clean


class CFGMarker(torch.nn.Module):
    def forward(
        self, current, goal, noisy_action, timestep, conditioned=True
    ):
        del current, goal, timestep
        value = 1.0 if conditioned is True else 0.0
        return torch.full_like(noisy_action, value)


class QuadraticCost:
    def get_cost(self, info, candidates):
        target = info["target"][..., None, None]
        return (candidates - target).square().sum(dim=(-1, -2))


class FixedSampler:
    def __init__(self) -> None:
        self.counts = []

    def prepare(self, info):
        return info["target"]

    def sample(self, context, *, count, generator):
        del generator
        self.counts.append(count)
        return context[:, None, None, None].expand(-1, count, 5, 10).clone()


@dataclass
class Config:
    horizon: int = 5
    action_block: int = 5


class Space:
    shape = (2, 2)


def reference(seed: int, steps: int = 4):
    generator = torch.Generator().manual_seed(seed)
    mean = torch.zeros(2, 5, 10)
    var = torch.ones_like(mean)
    target = torch.tensor((0.2, -0.3))
    final = None
    for _ in range(steps):
        candidates = torch.randn(2, 17, 5, 10, generator=generator)
        candidates = candidates * var[:, None] + mean[:, None]
        candidates[:, 0] = mean
        costs = (candidates - target[:, None, None, None]).square().sum((-1, -2))
        values, indices = torch.topk(costs, k=5, dim=1, largest=False)
        batch = torch.arange(2).unsqueeze(1).expand(-1, 5)
        elite = candidates[batch, indices]
        mean = elite.mean(1)
        var = elite.std(1)
        final = values.mean(1).tolist()
    return mean, var, final


def main() -> None:
    torch.manual_seed(17)
    torch.set_num_threads(1)
    diffusion = JointActionDiffusion(
        latent_dim=8,
        primitive_action_dim=2,
        action_horizon=25,
        width=32,
        depth=2,
        time_embedding_dim=16,
    )
    current = torch.randn(3, 8)
    goal = torch.randn(3, 8)
    noisy = torch.randn(3, 25, 2)
    timestep = torch.tensor((1, 20, 99))
    prediction = diffusion(current, goal, noisy, timestep)
    if prediction.shape != noisy.shape or not torch.isfinite(prediction).all():
        raise RuntimeError("GDP-CEM diffusion forward test failed")
    velocity_model = VelocityActionDiffusion(
        latent_dim=8,
        primitive_action_dim=2,
        action_horizon=25,
        width=32,
        depth=2,
        time_embedding_dim=16,
    )
    velocity_prediction = velocity_model(current, goal, noisy, timestep)
    velocity_unconditional = velocity_model(
        current, goal, noisy, timestep, conditioned=False
    )
    mixed_mask = torch.tensor((True, False, True))
    velocity_mixed = velocity_model(
        current, goal, noisy, timestep, conditioned=mixed_mask
    )
    if (
        velocity_prediction.shape != noisy.shape
        or not torch.isfinite(velocity_prediction).all()
        or not torch.equal(velocity_mixed[1], velocity_unconditional[1])
        or not torch.equal(velocity_mixed[[0, 2]], velocity_prediction[[0, 2]])
    ):
        raise RuntimeError("GDP-CEM velocity model condition-mask test failed")
    marker = CFGMarker()
    marker_arguments = {
        "current": current,
        "goal": goal,
        "noisy_action": noisy,
        "timestep": timestep,
    }
    marker_zero = classifier_free_velocity_prediction(
        marker, guidance_scale=0.0, **marker_arguments
    )
    marker_one = classifier_free_velocity_prediction(
        marker, guidance_scale=1.0, **marker_arguments
    )
    marker_two = classifier_free_velocity_prediction(
        marker, guidance_scale=2.0, **marker_arguments
    )
    if (
        not torch.equal(marker_zero, torch.zeros_like(noisy))
        or not torch.equal(marker_one, torch.ones_like(noisy))
        or not torch.equal(marker_two, 2.0 * torch.ones_like(noisy))
    ):
        raise RuntimeError("GDP-CEM classifier-free guidance algebra test failed")
    schedule = CosineDiffusionSchedule.build(100)
    first = ddim_sample(
        diffusion,
        current=current,
        goal=goal,
        count=4,
        inference_steps=5,
        schedule=schedule,
        generator=torch.Generator().manual_seed(91),
    )
    second = ddim_sample(
        diffusion,
        current=current,
        goal=goal,
        count=4,
        inference_steps=5,
        schedule=schedule,
        generator=torch.Generator().manual_seed(91),
    )
    if not torch.equal(first, second):
        raise RuntimeError("GDP-CEM DDIM sampling is not deterministic")

    oracle_velocity = OracleVelocity(schedule)
    velocity_clean = torch.randn(2, 25, 2).clamp(-2.0, 2.0)
    velocity_arguments = {
        "current": velocity_clean.flatten(1),
        "goal": torch.zeros(2, 50),
        "count": 3,
        "inference_steps": 5,
        "schedule": schedule,
        "guidance_scale": 2.0,
        "clip_low": -3.0 * torch.ones(2),
        "clip_high": 3.0 * torch.ones(2),
    }
    velocity_first = velocity_ddim_sample(
        oracle_velocity,
        generator=torch.Generator().manual_seed(901),
        **velocity_arguments,
    )
    velocity_second = velocity_ddim_sample(
        oracle_velocity,
        generator=torch.Generator().manual_seed(901),
        **velocity_arguments,
    )
    velocity_expected = velocity_clean[:, None].expand_as(velocity_first)
    if (
        not torch.equal(velocity_first, velocity_second)
        or not torch.allclose(
            velocity_first, velocity_expected, rtol=1.0e-4, atol=1.0e-4
        )
    ):
        raise RuntimeError("GDP-CEM velocity-DDIM oracle reconstruction failed")

    oracle_schedule = CosineDiffusionSchedule.build(100)
    oracle = OracleEpsilon(oracle_schedule)
    oracle_clean = torch.randn(2, 25, 2).clamp(-2.0, 2.0)
    oracle_bank = oracle_clean[:, None].expand(2, 3, 25, 2).clone()
    refined = ddim_refine_epsilon(
        oracle,
        current=oracle_clean.flatten(1),
        goal=torch.zeros(2, 50),
        clean=oracle_bank,
        restart_timestep=20,
        inference_steps=5,
        schedule=oracle_schedule,
        generator=torch.Generator().manual_seed(911),
        clip_low=-3.0 * torch.ones(2),
        clip_high=3.0 * torch.ones(2),
    )
    if not torch.allclose(refined, oracle_bank, rtol=1.0e-5, atol=1.0e-5):
        raise RuntimeError("GDP-CEM DDIM refinement failed oracle reconstruction")
    one_step_refined = ddim_refine_epsilon(
        oracle,
        current=oracle_clean.flatten(1),
        goal=torch.zeros(2, 50),
        clean=oracle_bank,
        restart_timestep=20,
        inference_steps=1,
        schedule=oracle_schedule,
        generator=torch.Generator().manual_seed(912),
        clip_low=-3.0 * torch.ones(2),
        clip_high=3.0 * torch.ones(2),
    )
    if not torch.allclose(one_step_refined, oracle_bank, rtol=1.0e-5, atol=1.0e-5):
        raise RuntimeError("GDP-CEM one-step refinement failed oracle reconstruction")

    gaussian = ConditionalDiagonalGaussian(
        latent_dim=8,
        primitive_action_dim=2,
        action_horizon=25,
        width=32,
        depth=2,
        time_embedding_dim=16,
    )
    sample = gaussian_sample(
        gaussian,
        current=current,
        goal=goal,
        count=4,
        generator=torch.Generator().manual_seed(92),
    )
    if sample.shape != (3, 4, 25, 2) or not torch.isfinite(sample).all():
        raise RuntimeError("GDP-CEM Gaussian sampling test failed")

    sampler = GoalConditionedProposalSampler(
        EncodeWorld(),
        diffusion,
        kind="diffusion",
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
        action_mean=torch.zeros(2),
        action_std=torch.ones(2),
        robust_low=-3.0 * torch.ones(2),
        robust_high=3.0 * torch.ones(2),
        inference_steps=5,
    )
    planner_sample = sampler.sample(
        (current, goal),
        count=4,
        generator=torch.Generator().manual_seed(93),
    )
    if (
        sampler.latent_mean.device != next(diffusion.parameters()).device
        or planner_sample.shape != (3, 4, 5, 10)
        or not torch.isfinite(planner_sample).all()
    ):
        raise RuntimeError("GDP-CEM proposal sampler device/shape test failed")

    velocity_sampler = GoalConditionedProposalSampler(
        EncodeWorld(),
        velocity_model,
        kind="velocity",
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
        action_mean=torch.zeros(2),
        action_std=torch.ones(2),
        robust_low=-3.0 * torch.ones(2),
        robust_high=3.0 * torch.ones(2),
        inference_steps=5,
        guidance_scale=1.5,
    )
    velocity_planner_first = velocity_sampler.sample(
        (current, goal),
        count=4,
        generator=torch.Generator().manual_seed(9301),
    )
    velocity_planner_second = velocity_sampler.sample(
        (current, goal),
        count=4,
        generator=torch.Generator().manual_seed(9301),
    )
    velocity_diagnostic = velocity_sampler.diagnostic_history[-1]
    if (
        not torch.equal(velocity_planner_first, velocity_planner_second)
        or velocity_planner_first.shape != (3, 4, 5, 10)
        or velocity_diagnostic["kind"] != "velocity"
        or velocity_diagnostic["candidate_count"] != 4
        or velocity_diagnostic["guidance_scale"] != 1.5
        or velocity_diagnostic["mean_coordinate_std"] <= 0.0
        or velocity_diagnostic["boundary_fraction"] >= 1.0
    ):
        raise RuntimeError("GDP-CEM velocity proposal sampler test failed")

    matched_diffusion = JointActionDiffusion(
        latent_dim=8,
        primitive_action_dim=2,
        action_horizon=25,
        width=32,
        depth=2,
        time_embedding_dim=16,
    )
    matched_diffusion.load_state_dict(diffusion.state_dict(), strict=True)
    gadr_arguments = {
        "latent_mean": torch.zeros(8),
        "latent_std": torch.ones(8),
        "action_mean": torch.zeros(2),
        "action_std": torch.ones(2),
        "robust_low": -3.0 * torch.ones(2),
        "robust_high": 3.0 * torch.ones(2),
        "restart_timestep": 40,
        "inference_steps": 1,
        "refined_fraction": 0.5,
    }
    true_gadr = GaussianAnchoredRefinementSampler(
        EncodeWorld(), gaussian, diffusion, condition="true", **gadr_arguments
    )
    shuffled_gadr = GaussianAnchoredRefinementSampler(
        EncodeWorld(),
        gaussian,
        matched_diffusion,
        condition="shuffled",
        **gadr_arguments,
    )
    gaussian_gadr = GaussianAnchoredRefinementSampler(
        EncodeWorld(), gaussian, None, condition="gaussian", **gadr_arguments
    )
    true_generator = torch.Generator().manual_seed(941)
    shuffled_generator = torch.Generator().manual_seed(941)
    gaussian_generator = torch.Generator().manual_seed(941)
    true_bank = true_gadr.sample(
        (current, goal), count=10, generator=true_generator
    )
    shuffled_bank = shuffled_gadr.sample(
        (current, goal), count=10, generator=shuffled_generator
    )
    gaussian_bank = gaussian_gadr.sample(
        (current, goal), count=10, generator=gaussian_generator
    )
    if not torch.equal(true_bank, shuffled_bank):
        raise RuntimeError("matched GADR models did not share exact candidates")
    expected_mean = gaussian(current, goal)[0].clamp(-3.0, 3.0).reshape(3, 5, 10)
    if (
        true_bank.shape != (3, 10, 5, 10)
        or not torch.equal(true_bank[:, 0], expected_mean)
        or not torch.equal(gaussian_bank[:, 0], expected_mean)
        or true_gadr.diagnostic_history[0]["refined_count"] != 5
        or gaussian_gadr.diagnostic_history[0]["refined_count"] != 0
        or gaussian_gadr.diagnostic_history[0]["matched_refinement_slots"] != 5
        or true_bank.abs().max() > 3.0
        or gaussian_bank.abs().max() > 3.0
    ):
        raise RuntimeError("GADR bank slot/count/bound test failed")
    if not torch.equal(
        torch.randn(11, generator=true_generator),
        torch.randn(11, generator=gaussian_generator),
    ):
        raise RuntimeError("GADR Gaussian control did not consume matched RNG")

    tiny_current = torch.randn(16, 8)
    tiny_goal = torch.randn(16, 8)
    tiny_clean = torch.randn(16, 25, 2)
    tiny_noise = torch.randn_like(tiny_clean)
    tiny_timestep = torch.full((16,), 40, dtype=torch.long)
    alpha = CosineDiffusionSchedule.build(100).alpha_bar[40]
    tiny_noisy = alpha.sqrt() * tiny_clean + (1.0 - alpha).sqrt() * tiny_noise
    diffusion_optimizer = torch.optim.Adam(diffusion.parameters(), lr=3.0e-3)
    diffusion_initial = None
    for index in range(120):
        diffusion_optimizer.zero_grad(set_to_none=True)
        tiny_prediction = diffusion(
            tiny_current, tiny_goal, tiny_noisy, tiny_timestep
        )
        tiny_loss = (tiny_prediction - tiny_noise).square().mean()
        if diffusion_initial is None:
            diffusion_initial = float(tiny_loss.detach())
        tiny_loss.backward()
        diffusion_optimizer.step()
    if float(tiny_loss.detach()) >= 0.7 * float(diffusion_initial):
        raise RuntimeError("GDP-CEM diffusion failed fixed-tiny-batch overfit")

    velocity_optimizer = torch.optim.Adam(velocity_model.parameters(), lr=3.0e-3)
    velocity_initial = None
    velocity_alpha = oracle_schedule.alpha_bar[40]
    velocity_target = (
        velocity_alpha.sqrt() * tiny_noise
        - (1.0 - velocity_alpha).sqrt() * tiny_clean
    )
    for _ in range(120):
        velocity_optimizer.zero_grad(set_to_none=True)
        velocity_output = velocity_model(
            tiny_current, tiny_goal, tiny_noisy, tiny_timestep, conditioned=True
        )
        velocity_loss = (velocity_output - velocity_target).square().mean()
        if velocity_initial is None:
            velocity_initial = float(velocity_loss.detach())
        velocity_loss.backward()
        velocity_optimizer.step()
    if float(velocity_loss.detach()) >= 0.7 * float(velocity_initial):
        raise RuntimeError("GDP-CEM velocity model failed fixed-tiny-batch overfit")

    gaussian_optimizer = torch.optim.Adam(gaussian.parameters(), lr=3.0e-3)
    gaussian_initial = None
    for index in range(120):
        gaussian_optimizer.zero_grad(set_to_none=True)
        tiny_mean, tiny_log_std = gaussian(tiny_current, tiny_goal)
        tiny_standardized = (tiny_clean - tiny_mean) / tiny_log_std.exp()
        tiny_gaussian_loss = (
            0.5 * tiny_standardized.square() + tiny_log_std
        ).mean()
        if gaussian_initial is None:
            gaussian_initial = float(tiny_gaussian_loss.detach())
        tiny_gaussian_loss.backward()
        gaussian_optimizer.step()
    if float(tiny_gaussian_loss.detach()) >= float(gaussian_initial) - 0.1:
        raise RuntimeError("GDP-CEM Gaussian failed fixed-tiny-batch overfit")

    seed = 731
    solver = ProposalCEMSolver(
        QuadraticCost(),
        proposal_sampler=None,
        proposal_fraction=0.0,
        refresh_mode="none",
        batch_size=2,
        num_samples=17,
        n_steps=4,
        topk=5,
        seed=seed,
    )
    solver.configure(action_space=Space(), n_envs=2, config=Config())
    result = solver.solve({"target": torch.tensor((0.2, -0.3))})
    expected_mean, expected_var, expected_cost = reference(seed)
    if (
        not torch.equal(result["actions"], expected_mean)
        or not torch.equal(result["var"][0], expected_var)
        or result["costs"] != expected_cost
    ):
        raise RuntimeError("GDP-CEM Gaussian control does not reproduce released CEM")

    fixed_selector = FixedSampler()
    selector = ProposalCEMSolver(
        QuadraticCost(),
        proposal_sampler=fixed_selector,
        proposal_fraction=1.0,
        refresh_mode="first",
        batch_size=2,
        num_samples=17,
        n_steps=1,
        topk=5,
        seed=812,
        proposal_seed=813,
        return_mode="best",
        preserve_mean_candidate=False,
    )
    selector.configure(action_space=Space(), n_envs=2, config=Config())
    target = torch.tensor((0.2, -0.3))
    selected = selector.solve({"target": target})["actions"]
    expected = target[:, None, None].expand(2, 5, 10)
    untouched_cem_rng = torch.randn(7, generator=selector.torch_gen)
    fresh_cem_rng = torch.randn(7, generator=torch.Generator().manual_seed(812))
    if (
        not torch.equal(selected, expected)
        or fixed_selector.counts != [17]
        or not torch.equal(untouched_cem_rng, fresh_cem_rng)
    ):
        raise RuntimeError("GDP-Select did not return the best actual proposal")

    fixed_refresh = FixedSampler()
    refresh = ProposalCEMSolver(
        QuadraticCost(),
        proposal_sampler=fixed_refresh,
        proposal_fraction=0.5,
        refresh_mode="all",
        batch_size=2,
        num_samples=17,
        n_steps=3,
        topk=5,
        seed=814,
        proposal_seed=815,
    )
    refresh.configure(action_space=Space(), n_envs=2, config=Config())
    refresh.solve({"target": target})
    if (
        fixed_refresh.counts != [8, 8, 8]
        or [item["proposal_count"] for item in refresh.diagnostic_history]
        != [8, 8, 8]
        or not all(item["proposal_active"] for item in refresh.diagnostic_history)
    ):
        raise RuntimeError("GDP-CEM refresh count/timing test failed")
    print("GDP-CEM model and solver tests: ok")


if __name__ == "__main__":
    main()
