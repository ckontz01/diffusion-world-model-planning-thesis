from __future__ import annotations

import hashlib

import numpy as np
from sklearn import preprocessing

import gdp_cem_e15_data_specs as spec
from build_gdp_cem_e15_bounded_cache import (
    bounded_action_targets,
    planner_to_raw_float32,
    raw_to_planner_float32,
    select_rows,
)


def test_episode_split_matches_independent_formula() -> None:
    for task in spec.TASKS:
        for episode in (0, 1, 17, 999_999):
            payload = f"gdp-cem-e15-split\0{task}\0{episode}".encode("utf-8")
            expected = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % 4 == 0
            assert spec.episode_is_validation(task, episode) is expected


def test_float32_planner_transforms_match_sklearn() -> None:
    raw = np.asarray(
        [[-1.0, 0.25], [np.nextafter(np.float32(1), np.float32(2)), -0.75]],
        dtype=np.float32,
    )
    fit = np.asarray(
        [[-1.0, -2.0], [-0.5, 0.0], [0.5, 1.0], [1.0, 3.0]],
        dtype=np.float32,
    )
    scaler = preprocessing.StandardScaler().fit(fit)
    transformed = raw_to_planner_float32(raw, scaler.mean_, scaler.scale_)
    assert transformed.dtype == np.float32
    assert np.array_equal(transformed, scaler.transform(raw))
    recovered = planner_to_raw_float32(transformed, scaler.mean_, scaler.scale_)
    assert recovered.dtype == np.float32
    assert np.array_equal(recovered, scaler.inverse_transform(transformed))


def test_bounded_targets_are_finite_and_smoothly_reconstruct() -> None:
    raw = np.asarray([[-2.0, -1.0, 0.0, 1.0, 2.0]], dtype=np.float32)
    projected, unconstrained, scale, limit = bounded_action_targets(raw)
    reconstructed = float(scale) * np.tanh(unconstrained.astype(np.float64))
    assert np.isfinite(unconstrained).all()
    assert 0.0 < limit < scale < 1.0
    assert np.all(np.abs(projected) <= limit)
    assert np.allclose(reconstructed, projected, atol=2 * np.finfo(np.float32).eps)
    assert projected[0, 2] == 0.0


def test_balanced_selection_is_episode_disjoint_and_deterministic(monkeypatch) -> None:
    monkeypatch.setattr(spec, "DELTA_TAU_PAIRS", ((15, 15), (20, 15)))
    monkeypatch.setattr(spec, "TRAIN_ROWS_PER_CELL", 4)
    monkeypatch.setattr(spec, "VALIDATION_ROWS_PER_CELL", 3)
    monkeypatch.setattr(spec, "TRAIN_ROWS", 8)
    monkeypatch.setattr(spec, "VALIDATION_ROWS", 6)
    episodes = np.arange(200, dtype=np.int64)
    role = np.zeros(200, dtype=np.uint8)
    # Upstream E14 validation rows are present in the source cache but are
    # forbidden from the new split. Their episode IDs need not occur in the
    # eligible-role lookup.
    role[-20:] = 1
    delta = np.where(np.arange(200) % 2 == 0, 15, 20).astype(np.int64)
    tau = np.full(200, 15, dtype=np.int64)
    first = select_rows(
        task="pusht", old_role=role, episode=episodes, delta=delta, tau=tau
    )
    second = select_rows(
        task="pusht", old_role=role, episode=episodes, delta=delta, tau=tau
    )
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])
    train_episode = set(episodes[first[0][first[1] == 0]].tolist())
    validation_episode = set(episodes[first[0][first[1] == 1]].tolist())
    assert not train_episode.intersection(validation_episode)
    assert len(first[0]) == 14
    assert np.all(role[first[0]] == 0)
