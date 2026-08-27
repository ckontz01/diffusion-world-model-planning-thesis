from __future__ import annotations

import pytest
import torch

from gdp_cem_e16_models import LatentStateAdapter, continuation_score


def test_adapter_shape_and_gradient() -> None:
    model = LatentStateAdapter(latent_dim=192, state_dim=7, width=32)
    latent = torch.randn(5, 192, requires_grad=True)
    value = model(latent)
    assert value.shape == (5, 7)
    value.square().mean().backward()
    assert latent.grad is not None
    assert torch.isfinite(latent.grad).all()


def test_adapter_rejects_wrong_shape() -> None:
    model = LatentStateAdapter(latent_dim=192, state_dim=7, width=32)
    with pytest.raises(ValueError):
        model(torch.randn(2, 191))


def test_continuation_score_is_mean_of_best_two() -> None:
    costs = torch.tensor(
        [[[9.0, 1.0, 5.0, 3.0], [2.0, 4.0, 8.0, 6.0]]]
    )
    assert torch.equal(continuation_score(costs, best_count=2), torch.tensor([[2.0, 3.0]]))


def test_continuation_score_rejects_nonfinite() -> None:
    with pytest.raises(RuntimeError):
        continuation_score(torch.tensor([[[1.0, float("nan")]]]), best_count=1)
