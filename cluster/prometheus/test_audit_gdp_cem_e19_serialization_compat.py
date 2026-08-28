from __future__ import annotations

from types import SimpleNamespace

import torch

import audit_gdp_cem_e19_serialization_compat as audit


def test_legacy_pickle_names_resolve_to_pinned_official_classes():
    from jepa import JEPA
    from module import ARPredictor
    from stable_worldmodel.wm.lewm.lewm import LeWM
    from stable_worldmodel.wm.lewm.module import Predictor

    assert JEPA is LeWM
    assert ARPredictor is Predictor


def test_state_digest_handles_scalar_tensor():
    first = audit.state_digest({"scalar": torch.tensor(7)})
    second = audit.state_digest({"scalar": torch.tensor(7)})
    different = audit.state_digest({"scalar": torch.tensor(8)})
    assert first == second
    assert first != different


def test_rollout_history_matches_official_legacy_fallback():
    historical = SimpleNamespace(predictor=SimpleNamespace())
    current = SimpleNamespace(predictor=SimpleNamespace(num_frames=5))
    assert audit.rollout_history(historical) == 3
    assert audit.rollout_history(current) == 5


def test_dimensions_fall_back_to_serialized_tensors():
    historical = SimpleNamespace(
        predictor=SimpleNamespace(pos_embedding=torch.zeros(1, 3, 384)),
        action_encoder=SimpleNamespace(
            patch_embed=SimpleNamespace(in_channels=10)
        ),
    )
    current = SimpleNamespace(
        predictor=SimpleNamespace(input_dim=512),
        action_encoder=SimpleNamespace(input_dim=12),
    )
    assert audit.predictor_embedding_dim(historical) == 384
    assert audit.action_input_dim(historical) == 10
    assert audit.predictor_embedding_dim(current) == 512
    assert audit.action_input_dim(current) == 12
