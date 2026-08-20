from __future__ import annotations

import pytest
import torch
from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.models import (
    ConditionalDiffusionVerifier,
    DeterministicForwardVerifier,
    FlowInverseDynamics,
    TemporalReachabilityHead,
    TensorStandardizer,
    count_parameters,
    model_from_config,
    select_capacity_matched_width,
)
from acid_alternative.train_transition_scorer import (
    fixed_derangement_indices,
    validate,
    validation_diagnostic_actions,
    validation_selection_action,
)


class FakeWorldModel(torch.nn.Module):
    def __init__(self, latent_dim: int, action_dim: int) -> None:
        super().__init__()
        self.anchor = torch.nn.Parameter(torch.zeros(()))
        self.latent_dim = latent_dim
        self.transition = torch.nn.Linear(action_dim, latent_dim, bias=False)
        torch.nn.init.constant_(self.transition.weight, 0.1)

    def encode(self, info):
        pixels = info["pixels"]
        flat = pixels.reshape(*pixels.shape[:2], -1)
        if flat.shape[-1] < self.latent_dim:
            flat = torch.nn.functional.pad(flat, (0, self.latent_dim - flat.shape[-1]))
        info["emb"] = flat[..., : self.latent_dim]
        return info

    def rollout(self, info, actions):
        initial = self.encode({"pixels": info["pixels"][:, 0]})["emb"]
        initial = initial[:, None].expand(actions.shape[0], actions.shape[1], -1, -1)
        latent = initial[:, :, -1]
        states = [latent]
        for step in range(actions.shape[2]):
            latent = latent + self.transition(actions[:, :, step])
            states.append(latent)
        info["predicted_emb"] = torch.stack(states, dim=2)
        return info

    def criterion(self, info):
        goal = info["goal_emb"][..., -1, :]
        if goal.ndim == 2:
            goal = goal[:, None]
        return (info["predicted_emb"][:, :, -1] - goal).square().sum(dim=-1)


def _inputs(batch=2, samples=7, horizon=5, latent_dim=8, action_dim=4):
    info = {
        "pixels": torch.randn(batch, samples, 1, 1, 1, latent_dim),
        "goal": torch.randn(batch, samples, 1, 1, 1, latent_dim),
        "action": torch.zeros(batch, samples, 1, action_dim),
    }
    actions = torch.randn(batch, samples, horizon, action_dim)
    return info, actions


def test_validation_checkpoint_selection_matches_control_objective():
    true_action = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    permuted_action = torch.tensor([[3.0, 4.0], [1.0, 2.0]])

    assert (
        validation_selection_action("true", true_action, permuted_action) is true_action
    )
    assert (
        validation_selection_action("shuffled_action", true_action, permuted_action)
        is permuted_action
    )
    torch.testing.assert_close(
        validation_selection_action("action_ablated", true_action, permuted_action),
        torch.zeros_like(true_action),
    )

    with pytest.raises(ValueError, match="differ in shape"):
        validation_selection_action("true", true_action, permuted_action[:, :1])


def test_fixed_validation_derangement_is_reproducible_and_has_no_self_matches():
    first = fixed_derangement_indices(101, seed=13)
    second = fixed_derangement_indices(101, seed=13)
    torch.testing.assert_close(first, second, rtol=0, atol=0)
    assert torch.equal(first.sort().values, torch.arange(101))
    assert torch.all(first != torch.arange(101))
    with pytest.raises(ValueError, match="at least two"):
        fixed_derangement_indices(1, seed=13)


def test_action_ablated_validation_diagnostics_use_deployed_zero_input():
    true_action = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    permuted_action = torch.tensor([[3.0, 4.0], [1.0, 2.0]])

    actual_true, actual_permuted = validation_diagnostic_actions(
        "action_ablated", true_action, permuted_action
    )
    torch.testing.assert_close(actual_true, torch.zeros_like(true_action))
    torch.testing.assert_close(actual_permuted, torch.zeros_like(true_action))

    actual_true, actual_permuted = validation_diagnostic_actions(
        "shuffled_action", true_action, permuted_action
    )
    assert actual_true is true_action
    assert actual_permuted is permuted_action


def test_validation_reports_dimensionwise_residuals_consistent_with_scalar_cost():
    torch.manual_seed(5)
    latent_dim, action_dim = 4, 2
    validation_pairs = torch.arange(4)
    source_index = torch.arange(4)
    target_index = torch.arange(4, 8)
    latents = torch.randn(8, latent_dim)
    actions = torch.randn(4, action_dim)
    common = {
        "validation_pairs": validation_pairs,
        "source_index": source_index,
        "target_index": target_index,
        "latents": latents,
        "actions": actions,
        "latent_mean": torch.zeros(latent_dim),
        "latent_std": torch.ones(latent_dim),
        "acid_action_mean": torch.zeros(action_dim),
        "acid_action_std": torch.ones(action_dim),
        "device": torch.device("cpu"),
        "batch_size": 3,
        "seed": 11,
    }
    models = {
        "acid": FlowInverseDynamics(
            latent_dim, action_dim, width=12, depth=1, heads=3, mlp_ratio=2
        ),
        "diffusion": ConditionalDiffusionVerifier(
            latent_dim,
            action_dim,
            width=24,
            depth=1,
            noise_embedding_dim=8,
        ),
        "forward": DeterministicForwardVerifier(
            latent_dim, action_dim, width=24, depth=1
        ),
    }
    for model_name, model in models.items():
        result = validate(model_name, model, **common)
        correct_dimensions = result["correct_cost_per_dimension"]
        permuted_dimensions = result["permuted_cost_per_dimension"]
        expected_dimensions = action_dim if model_name == "acid" else latent_dim
        assert len(correct_dimensions) == expected_dimensions
        assert len(permuted_dimensions) == expected_dimensions
        reduction = (
            sum if model_name == "acid" else lambda values: sum(values) / len(values)
        )
        assert result["correct_action_cost"] == pytest.approx(
            reduction(correct_dimensions), rel=1.0e-6, abs=1.0e-7
        )
        assert result["permuted_action_cost"] == pytest.approx(
            reduction(permuted_dimensions), rel=1.0e-6, abs=1.0e-7
        )


def test_flow_shapes_mask_and_euler_sign():
    torch.manual_seed(1)
    model = FlowInverseDynamics(8, 4)
    assert model.attention_mask[0, 2].isneginf()
    assert model.attention_mask[1, 2].isneginf()
    assert model.attention_mask[2, :].eq(0).all()
    current = torch.randn(3, 8)
    nxt = torch.randn(3, 8)
    noise = torch.randn(3, 4)
    output = model.one_step_action(current, nxt, noise)
    direct = noise - model(current, nxt, noise, torch.ones(3))
    torch.testing.assert_close(output, direct)
    assert output.shape == noise.shape


def test_all_cost_arms_are_finite_and_shaped():
    torch.manual_seed(2)
    latent_dim, action_dim, horizon = 8, 4, 5
    info, actions = _inputs(
        latent_dim=latent_dim, action_dim=action_dim, horizon=horizon
    )
    stats_z = torch.zeros(latent_dim), torch.ones(latent_dim)
    stats_a = torch.zeros(action_dim), torch.ones(action_dim)
    scorers = {
        "b0": None,
        "acid": FlowInverseDynamics(latent_dim, action_dim),
        "diffusion": ConditionalDiffusionVerifier(latent_dim, action_dim, width=64),
        "forward": DeterministicForwardVerifier(latent_dim, action_dim, width=72),
        "reachability": TemporalReachabilityHead(latent_dim),
    }
    for arm, scorer in scorers.items():
        world = FakeWorldModel(latent_dim, action_dim)
        kwargs = {}
        if arm in ("diffusion", "forward"):
            kwargs.update(latent_mean=stats_z[0], latent_std=stats_z[1])
        if arm == "acid":
            kwargs.update(action_mean=stats_a[0], action_std=stats_a[1])
        wrapper = SharedRolloutCostModel(
            world,
            arm=arm,
            scorer=scorer,
            horizon=horizon,
            noise_seed=17,
            **kwargs,
        )
        cost = wrapper.get_cost(dict(info), actions)
        assert cost.shape == actions.shape[:2]
        assert torch.isfinite(cost).all()


def test_b0_matches_native_fake_goal_cost():
    latent_dim, action_dim = 8, 4
    info, actions = _inputs(latent_dim=latent_dim, action_dim=action_dim)
    world = FakeWorldModel(latent_dim, action_dim)
    wrapper = SharedRolloutCostModel(world, arm="b0", horizon=5)
    actual = wrapper.get_cost(dict(info), actions)

    native_info = dict(info)
    goal = {
        key: value[:, 0] for key, value in native_info.items() if torch.is_tensor(value)
    }
    goal["pixels"] = goal["goal"]
    goal.pop("action")
    goal = world.encode(goal)
    native_info["goal_emb"] = goal["emb"]
    native_info = world.rollout(native_info, actions)
    expected = world.criterion(native_info)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)


def test_standardizer_round_trip_and_adaptive_cost_formula():
    mean = torch.tensor([2.0, -3.0, 5.0])
    std = torch.tensor([0.5, 2.0, 4.0])
    standardizer = TensorStandardizer(mean, std)
    values = torch.randn(11, 3)
    torch.testing.assert_close(
        standardizer.inverse(standardizer(values)), values, rtol=1.0e-6, atol=1.0e-6
    )

    torch.manual_seed(19)
    latent_dim, action_dim, horizon = 8, 4, 5
    info, actions = _inputs(
        latent_dim=latent_dim, action_dim=action_dim, horizon=horizon
    )
    wrapper = SharedRolloutCostModel(
        FakeWorldModel(latent_dim, action_dim),
        arm="forward",
        scorer=DeterministicForwardVerifier(latent_dim, action_dim, width=72),
        latent_mean=torch.zeros(latent_dim),
        latent_std=torch.ones(latent_dim),
        lambda_weight=0.07,
        horizon=horizon,
    )
    actual = wrapper.get_cost(dict(info), actions)
    goal, trajectory, candidate_actions, _ = wrapper._rollout_once(dict(info), actions)
    verifier = wrapper._forward_cost(trajectory, candidate_actions)
    expected_weight = (
        0.07
        * goal.std(dim=1, unbiased=True)
        / verifier.std(dim=1, unbiased=True).clamp_min(1.0e-8)
    )
    expected = goal + expected_weight[:, None] * verifier
    torch.testing.assert_close(actual, expected)


def test_zero_verifier_weight_leaves_cem_actions_bitwise_identical():
    torch.manual_seed(23)
    latent_dim, action_dim, horizon = 8, 4, 5
    world = FakeWorldModel(latent_dim, action_dim)
    info, _ = _inputs(
        batch=1,
        samples=20,
        horizon=horizon,
        latent_dim=latent_dim,
        action_dim=action_dim,
    )
    b0 = SharedRolloutCostModel(world, arm="b0", horizon=horizon)
    zero = SharedRolloutCostModel(
        world,
        arm="diffusion",
        scorer=ConditionalDiffusionVerifier(latent_dim, action_dim, width=32, depth=1),
        latent_mean=torch.zeros(latent_dim),
        latent_std=torch.ones(latent_dim),
        lambda_weight=0.0,
        horizon=horizon,
        noise_seed=17,
    )

    def solve(wrapper: SharedRolloutCostModel) -> torch.Tensor:
        generator = torch.Generator().manual_seed(29)
        mean = torch.zeros(1, horizon, action_dim)
        spread = torch.ones_like(mean)
        for _ in range(4):
            candidates = (
                torch.randn(
                    1,
                    20,
                    horizon,
                    action_dim,
                    generator=generator,
                )
                * spread[:, None]
                + mean[:, None]
            )
            candidates[:, 0] = mean
            costs = wrapper.get_cost(dict(info), candidates)
            elite_indices = torch.topk(costs, k=4, dim=1, largest=False).indices
            elites = candidates[torch.arange(1)[:, None], elite_indices]
            mean = elites.mean(dim=1)
            spread = elites.std(dim=1)
        return mean

    torch.testing.assert_close(solve(b0), solve(zero), rtol=0, atol=0)


def test_transition_scorers_overfit_a_fixed_tiny_batch():
    torch.manual_seed(31)
    latent_dim, action_dim = 4, 2
    current = torch.randn(1, latent_dim)
    nxt = torch.randn(1, latent_dim)
    action = torch.randn(1, action_dim)
    action_noise = torch.randn_like(action)
    latent_noise = torch.randn_like(nxt)
    tau = torch.full((1,), 0.6)
    sigma = torch.full((1,), 0.25)
    models_and_losses = [
        (
            FlowInverseDynamics(
                latent_dim,
                action_dim,
                width=12,
                depth=1,
                heads=3,
                mlp_ratio=2,
            ),
            lambda model: model.flow_loss(
                current, nxt, action, tau=tau, noise=action_noise
            ),
        ),
        (
            ConditionalDiffusionVerifier(
                latent_dim,
                action_dim,
                width=24,
                depth=1,
                noise_embedding_dim=8,
            ),
            lambda model: model.denoising_loss(
                current, action, nxt, sigma=sigma, noise=latent_noise
            ),
        ),
        (
            DeterministicForwardVerifier(latent_dim, action_dim, width=24, depth=1),
            lambda model: (model(current, action) - nxt).square().mean(),
        ),
    ]
    for model, loss_function in models_and_losses:
        optimizer = torch.optim.AdamW(model.parameters(), lr=1.0e-2, weight_decay=0)
        initial = float(loss_function(model).detach())
        for _ in range(200):
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model)
            loss.backward()
            optimizer.step()
        final = float(loss_function(model).detach())
        assert final < initial * 0.05, (type(model).__name__, initial, final)


def test_acid_uses_native_latents_and_denormalizes_inferred_action():
    latent_dim, action_dim, horizon = 8, 2, 5
    scorer = FlowInverseDynamics(latent_dim, action_dim)
    captured: dict[str, torch.Tensor] = {}

    def fixed_one_step(
        current: torch.Tensor, nxt: torch.Tensor, noise: torch.Tensor
    ) -> torch.Tensor:
        captured["current"] = current.detach().clone()
        captured["next"] = nxt.detach().clone()
        return torch.zeros_like(noise)

    scorer.one_step_action = fixed_one_step  # type: ignore[method-assign]
    action_mean = torch.tensor([10.0, -4.0])
    action_std = torch.tensor([2.0, 0.5])
    wrapper = SharedRolloutCostModel(
        FakeWorldModel(latent_dim, action_dim),
        arm="acid",
        scorer=scorer,
        action_mean=action_mean,
        action_std=action_std,
        horizon=horizon,
    )
    trajectory = torch.randn(1, 3, horizon + 1, latent_dim) * 7.0 + 11.0
    actions = torch.randn(1, 3, horizon, action_dim)
    actual = wrapper._acid_cost(trajectory, actions)
    expected = (actions - action_mean).square().sum(dim=-1).mean(dim=-1)

    torch.testing.assert_close(actual, expected)
    torch.testing.assert_close(captured["current"], trajectory[:, :, :-1])
    torch.testing.assert_close(captured["next"], trajectory[:, :, 1:])


def test_reachability_uses_native_terminal_and_goal_latents():
    latent_dim, action_dim, horizon = 8, 2, 5
    scorer = TemporalReachabilityHead(latent_dim)
    captured: dict[str, torch.Tensor] = {}

    def fixed_forward(first: torch.Tensor, second: torch.Tensor) -> torch.Tensor:
        captured["first"] = first.detach().clone()
        captured["second"] = second.detach().clone()
        return torch.zeros(first.shape[:-1], device=first.device, dtype=first.dtype)

    scorer.forward = fixed_forward  # type: ignore[method-assign]
    wrapper = SharedRolloutCostModel(
        FakeWorldModel(latent_dim, action_dim),
        arm="reachability",
        scorer=scorer,
        horizon=horizon,
    )
    trajectory = torch.randn(1, 3, horizon + 1, latent_dim) * 9.0 + 13.0
    goal_embedding = torch.randn(1, 1, latent_dim) * 4.0 - 7.0
    actual = wrapper._reachability_cost(trajectory, goal_embedding)

    torch.testing.assert_close(actual, torch.zeros(1, 3))
    torch.testing.assert_close(captured["first"], trajectory[:, :, -1])
    torch.testing.assert_close(
        captured["second"], goal_embedding[:, None, -1, :].expand_as(captured["first"])
    )


def test_noise_banks_are_reproducible():
    world_a = FakeWorldModel(8, 4)
    world_b = FakeWorldModel(8, 4)
    scorer_a = ConditionalDiffusionVerifier(8, 4, width=64)
    scorer_b = ConditionalDiffusionVerifier(8, 4, width=64)
    wrapper_a = SharedRolloutCostModel(
        world_a,
        arm="diffusion",
        scorer=scorer_a,
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
        noise_seed=99,
    )
    wrapper_b = SharedRolloutCostModel(
        world_b,
        arm="diffusion",
        scorer=scorer_b,
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
        noise_seed=99,
    )
    torch.testing.assert_close(wrapper_a.diffusion_noise, wrapper_b.diffusion_noise)


def test_action_ablated_diffusion_cost_ignores_action_tensor():
    torch.manual_seed(3)
    latent_dim, action_dim, horizon = 8, 4, 5
    wrapper = SharedRolloutCostModel(
        FakeWorldModel(latent_dim, action_dim),
        arm="diffusion",
        scorer=ConditionalDiffusionVerifier(latent_dim, action_dim, width=64),
        latent_mean=torch.zeros(latent_dim),
        latent_std=torch.ones(latent_dim),
        horizon=horizon,
        noise_seed=31,
        use_action_condition=False,
    )
    trajectory = torch.randn(2, 7, horizon + 1, latent_dim)
    first = wrapper._diffusion_cost(trajectory, torch.randn(2, 7, horizon, action_dim))
    second = wrapper._diffusion_cost(
        trajectory, torch.randn(2, 7, horizon, action_dim) * 100
    )
    torch.testing.assert_close(first, second, rtol=0, atol=0)


def test_capacity_width_search_is_mechanical():
    diffusion = ConditionalDiffusionVerifier(192, 10, width=384)
    width, parameter_count, relative = select_capacity_matched_width(
        diffusion,
        lambda candidate_width: DeterministicForwardVerifier(
            192, 10, width=candidate_width
        ),
        minimum=128,
        maximum=640,
        step=8,
    )
    assert 128 <= width <= 640
    assert parameter_count == count_parameters(
        DeterministicForwardVerifier(192, 10, width=width)
    )
    assert relative < 0.02


def test_checkpoint_factories_reconstruct_exact_shapes():
    configs = [
        {
            "name": "acid",
            "latent_dim": 8,
            "action_dim": 4,
            "width": 192,
            "depth": 4,
            "heads": 3,
            "mlp_ratio": 4,
        },
        {
            "name": "diffusion",
            "latent_dim": 8,
            "action_dim": 4,
            "width": 64,
            "depth": 3,
            "noise_embedding_dim": 16,
        },
        {
            "name": "forward",
            "latent_dim": 8,
            "action_dim": 4,
            "width": 72,
            "depth": 3,
        },
        {"name": "reachability", "latent_dim": 8, "hidden_width": 32},
    ]
    for config in configs:
        original = model_from_config(config)
        reconstructed = model_from_config(config)
        reconstructed.load_state_dict(original.state_dict(), strict=True)
        assert count_parameters(reconstructed) == count_parameters(original)
