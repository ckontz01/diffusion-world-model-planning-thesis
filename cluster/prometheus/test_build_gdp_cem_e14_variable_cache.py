from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

import build_gdp_cem_e14_variable_cache as cache
import gdp_cem_e14_specs as spec


def test_frozen_pair_and_schedule_specification() -> None:
    assert len(spec.DELTA_TAU_PAIRS) == 45
    assert spec.DELTA_TAU_PAIRS[:3] == ((15, 15), (20, 15), (20, 20))
    assert spec.DELTA_TAU_PAIRS[-3:] == ((150, 15), (150, 20), (150, 25))
    assert max(spec.row_quotas(spec.TRAIN_ROWS).values()) - min(
        spec.row_quotas(spec.TRAIN_ROWS).values()
    ) == 1
    assert max(spec.row_quotas(spec.VALIDATION_ROWS).values()) - min(
        spec.row_quotas(spec.VALIDATION_ROWS).values()
    ) == 1
    for horizon in spec.SCHEDULES:
        assert sum(spec.schedule_for(horizon)) == horizon


def test_episode_bounds_and_role_restricted_sampling() -> None:
    episodes = np.asarray([1] * 20 + [2] * 30 + [3] * 40, dtype=np.int64)
    starts, stops = cache.episode_bounds(episodes)
    assert starts.tolist() == [0, 20, 50]
    assert stops.tolist() == [20, 50, 90]
    roles = np.asarray([0, 1, 0], dtype=np.uint8)
    first, available = cache.sample_pair_starts(
        episode_starts=starts,
        episode_stops=stops,
        episode_roles=roles,
        role=0,
        delta=15,
        quota=20,
        seed=123,
    )
    second, repeated_available = cache.sample_pair_starts(
        episode_starts=starts,
        episode_stops=stops,
        episode_roles=roles,
        role=0,
        delta=15,
        quota=20,
        seed=123,
    )
    assert available == repeated_available == (20 - 15) + (40 - 15)
    assert np.array_equal(first, second)
    assert len(np.unique(first)) == 20
    assert np.all((first < 5) | ((first >= 50) & (first < 75)))


def test_arbitrary_hdf5_rows_preserve_duplicates_and_order(tmp_path: Path) -> None:
    path = tmp_path / "rows.h5"
    values = np.arange(40, dtype=np.int64).reshape(20, 2)
    with h5py.File(path, "w") as handle:
        handle.create_dataset("value", data=values)
    with h5py.File(path, "r") as handle:
        observed = cache.read_h5_rows(
            handle["value"], np.asarray([9, 2, 9, 0, 17], dtype=np.int64)
        )
    assert np.array_equal(observed, values[[9, 2, 9, 0, 17]])


def test_masked_action_statistics_ignore_zero_padding() -> None:
    actions = np.zeros((2, 25, 2), dtype=np.float32)
    actions[0, :15] = np.asarray([1.0, 2.0])
    actions[1, :25] = np.asarray([3.0, 6.0])
    tau = np.asarray([15, 25], dtype=np.int64)
    stats = cache.masked_action_statistics(
        actions, tau, np.asarray([True, True], dtype=bool)
    )
    expected = np.concatenate((actions[0, :15], actions[1, :25]))
    assert np.allclose(stats["mean"], expected.mean(axis=0))
    assert np.allclose(stats["std"], expected.std(axis=0))
    assert np.all(stats["robust_high"] > stats["robust_low"])

