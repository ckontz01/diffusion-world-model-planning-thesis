#!/usr/bin/env python3
"""CPU unit tests for the frozen E12 PRISM implementation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest
import torch

from gdp_cem_e12_prism_data import PrismDPP1Dataset, load_prism_head_arrays
from gdp_cem_e12_prism_models import (
    CosineDDIMSchedule,
    PrismDPModel,
    PrismFixedStdMPPISolver,
    PrismPriorHead,
    prism_beta_nll_loss,
    prism_pog_fusion,
)


def test_prior_head_and_beta_nll_match_public_equations() -> None:
    torch.manual_seed(19)
    head = PrismPriorHead(192, 5, 5, 2)
    current = torch.randn(3, 192)
    goal = torch.randn(3, 192)
    mean, sigma = head(current, goal)
    assert mean.shape == sigma.shape == (3, 5, 5, 2)
    assert bool(torch.all(sigma > 0.05))
    target = torch.randn_like(mean)
    observed = prism_beta_nll_loss(mean, sigma, target, beta=0.5)
    reference = (
        sigma.detach()
        * (0.5 * (target - mean).square() / sigma.square() + sigma.log())
    ).mean()
    torch.testing.assert_close(observed, reference, rtol=0.0, atol=0.0)


def test_pog_matches_precision_addition() -> None:
    mean = torch.tensor([[[0.0, 1.0]]])
    std = torch.tensor([[[1.0, 2.0]]])
    prior_mean = torch.tensor([[[2.0, -1.0]]])
    prior_std = torch.tensor([[[0.5, 1.0]]])
    fused_mean, fused_std = prism_pog_fusion(mean, std, prior_mean, prior_std)
    base_precision = 1.0 / (std.square() + 1.0e-8)
    prior_precision = 1.0 / (prior_std.square() + 1.0e-8)
    expected_mean = (
        base_precision * mean + prior_precision * prior_mean
    ) / (base_precision + prior_precision)
    expected_std = (1.0 / (base_precision + prior_precision)).sqrt().clamp(0.05)
    torch.testing.assert_close(fused_mean, expected_mean)
    torch.testing.assert_close(fused_std, expected_std)


def test_prism_mppi_hook_matches_installed_stable_worldmodel_api() -> None:
    solver = PrismFixedStdMPPISolver(
        model=object(),
        batch_size=1,
        num_samples=8,
        var_scale=1.0,
        n_steps=2,
        topk=4,
        temperature=0.5,
        device="cpu",
        seed=123,
        prior_conditioner=None,
    )
    # Mirror the three fields populated by MPPISolver.configure without needing
    # a live Gym environment in this isolated integration test.
    solver._n_envs = 2
    solver._config = SimpleNamespace(horizon=5, action_block=5)
    solver._action_dim = 2
    base_mean, base_std = solver.init_action_distrib()
    assert base_mean.shape == base_std.shape == (2, 5, 10)
    prior_mean = torch.full_like(base_mean, 0.25)
    prior_std = torch.full_like(base_std, 0.5)
    solver._active_prior = (prior_mean, prior_std)
    fused_mean, fused_std = solver.init_action_distrib()
    expected_mean, expected_std = prism_pog_fusion(
        base_mean, base_std, prior_mean, prior_std
    )
    torch.testing.assert_close(fused_mean, expected_mean)
    torch.testing.assert_close(fused_std, expected_std)


@pytest.mark.parametrize(
    ("action_dim", "parameter_count"),
    ((2, 19_302_466), (3, 19_302_787), (4, 19_303_108), (5, 19_303_429)),
)
def test_prism_dp_reconstruction_parameter_count(
    action_dim: int, parameter_count: int
) -> None:
    model = PrismDPModel(action_dim)
    assert model.num_params == parameter_count
    value = torch.randn(2, 25, action_dim)
    timestep = torch.tensor([0, 99])
    condition = torch.randn(2, 256)
    with torch.inference_mode():
        output = model.forward_with_condition(value, timestep, condition)
    assert output.shape == value.shape
    assert bool(torch.isfinite(output).all())


class _ZeroDenoiser:
    action_horizon = 25
    action_dim = 2

    @staticmethod
    def forward_with_condition(
        value: torch.Tensor, timestep: torch.Tensor, condition: torch.Tensor
    ) -> torch.Tensor:
        del timestep, condition
        return torch.zeros_like(value)


def test_cosine_ddim_is_deterministic_and_uses_frozen_timestep_grid() -> None:
    schedule = CosineDDIMSchedule.build(100)
    assert schedule.inference_timesteps(10) == [90, 80, 70, 60, 50, 40, 30, 20, 10, 0]
    condition = torch.zeros(3, 256)
    first = schedule.sample(
        _ZeroDenoiser(),
        condition,
        generator=torch.Generator().manual_seed(82),
        inference_steps=10,
    )
    second = schedule.sample(
        _ZeroDenoiser(),
        condition,
        generator=torch.Generator().manual_seed(82),
        inference_steps=10,
    )
    torch.testing.assert_close(first, second, rtol=0.0, atol=0.0)
    assert first.shape == (3, 25, 2)
    assert bool(torch.all(first >= -1.0) and torch.all(first <= 1.0))


def _write_synthetic_p1_inputs(root: Path) -> tuple[Path, Path, Path]:
    dataset = root / "dataset.h5"
    latent = root / "latents.h5"
    sequence = root / "sequences.h5"
    rows = 52
    episode = np.repeat(np.arange(2, dtype=np.int64), 26)
    step = np.tile(np.arange(26, dtype=np.int64), 2)
    with h5py.File(dataset, "w") as handle:
        pixels = np.arange(rows * 4 * 4 * 3, dtype=np.uint8).reshape(rows, 4, 4, 3)
        handle.create_dataset("pixels", data=pixels)
    with h5py.File(latent, "w") as handle:
        handle.create_dataset("row_index", data=np.arange(rows, dtype=np.int64))
        handle.create_dataset("episode_idx", data=episode)
        handle.create_dataset("step_idx", data=step)
        handle.create_dataset(
            "latent", data=np.arange(rows * 192, dtype=np.float32).reshape(rows, 192)
        )
    action = np.arange(2 * 5 * 10, dtype=np.float32).reshape(2, 5, 10) / 100.0
    with h5py.File(sequence, "w") as handle:
        handle.create_dataset("source_index", data=np.asarray([0, 26], dtype=np.int64))
        handle.create_dataset("goal_index", data=np.asarray([25, 51], dtype=np.int64))
        handle.create_dataset("episode_idx", data=np.asarray([0, 1], dtype=np.int64))
        handle.create_dataset("step_idx", data=np.asarray([0, 0], dtype=np.int64))
        handle.create_dataset("role", data=np.asarray([0, 1], dtype=np.uint8))
        handle.create_dataset("action", data=action)
        stats = handle.create_group("stats")
        stats.create_dataset(
            "planner_primitive_action_mean", data=np.zeros(2, dtype=np.float64)
        )
        stats.create_dataset(
            "planner_primitive_action_std", data=np.ones(2, dtype=np.float64)
        )
        handle.attrs["goal_offset"] = 25
        handle.attrs["macro_horizon"] = 5
        handle.attrs["primitive_steps_per_macro"] = 5
    return dataset, latent, sequence


def test_p1_data_lineage_and_action_roundtrip(tmp_path: Path) -> None:
    dataset, latent, sequence = _write_synthetic_p1_inputs(tmp_path)
    arrays_h25 = load_prism_head_arrays(
        sequence_h5=sequence, latent_h5=latent, goal_mode="h25"
    )
    arrays_end = load_prism_head_arrays(
        sequence_h5=sequence, latent_h5=latent, goal_mode="endframe"
    )
    np.testing.assert_array_equal(arrays_h25["goal_index"], [25, 51])
    np.testing.assert_array_equal(arrays_end["goal_index"], [25, 51])
    train = PrismDPP1Dataset(
        dataset_h5=dataset,
        sequence_h5=sequence,
        latent_h5=latent,
        role="P1_train",
    )
    validation = PrismDPP1Dataset(
        dataset_h5=dataset,
        sequence_h5=sequence,
        latent_h5=latent,
        role="P1_val",
        action_min=train.action_min,
        action_max=train.action_max,
    )
    assert len(train) == len(validation) == 1
    assert set(train.episode_ids.tolist()).isdisjoint(validation.episode_ids.tolist())
    item = train[0]
    assert item["observation"].shape == item["goal"].shape == (3, 4, 4)
    assert item["action"].shape == (25, 2)
    raw = (item["action"].numpy() + 1.0) * 0.5 * (
        train.action_max - train.action_min
    ) + train.action_min
    np.testing.assert_allclose(raw, train.actions[0], atol=1.0e-6)


def test_optional_byte_pinned_public_prior_head_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run true source parity when PRISM_REFERENCE_ROOT is supplied by preflight."""

    import os

    reference_root = os.environ.get("PRISM_REFERENCE_ROOT")
    if not reference_root:
        pytest.skip("PRISM_REFERENCE_ROOT not configured")
    path = Path(reference_root) / "prior_head.py"
    if not path.is_file():
        pytest.fail(f"missing pinned public PRISM prior_head.py: {path}")
    spec = importlib.util.spec_from_file_location("e12_public_prism_prior_head", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    public = module.PriorHead(z_dim=192, H=5, A_block=5, A_raw=2)
    local = PrismPriorHead(192, 5, 5, 2)
    local.load_state_dict(public.state_dict())
    torch.manual_seed(92)
    current = torch.randn(7, 192)
    goal = torch.randn(7, 192)
    public_mean, public_sigma = public(current, goal)
    local_mean, local_sigma = local(current, goal)
    torch.testing.assert_close(local_mean, public_mean, rtol=0.0, atol=0.0)
    torch.testing.assert_close(local_sigma, public_sigma, rtol=0.0, atol=0.0)
    target = torch.randn_like(local_mean)
    torch.testing.assert_close(
        prism_beta_nll_loss(local_mean, local_sigma, target),
        module.beta_nll_loss(public_mean, public_sigma, target),
        rtol=0.0,
        atol=0.0,
    )
