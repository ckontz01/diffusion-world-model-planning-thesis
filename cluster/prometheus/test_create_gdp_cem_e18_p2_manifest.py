from __future__ import annotations

import numpy as np

import gdp_cem_e18_specs as spec
from create_gdp_cem_e18_p2_manifest import select_base_starts


def test_start_selection_is_fresh_deterministic_and_h150_compatible() -> None:
    lengths = np.asarray([220, 205, 149, 180], dtype=np.int64)
    partitions = {0: "P2", 1: "P2", 2: "P2", 3: "P1"}
    excluded = {(0, 0), (1, 0)}
    first, eligible = select_base_starts(
        lengths, partitions, task="pusht", excluded=excluded
    )
    second, second_eligible = select_base_starts(
        lengths, partitions, task="pusht", excluded=excluded
    )
    assert first == second
    assert eligible == second_eligible
    assert len(first) == spec.BASE_STARTS
    assert all((episode, start) not in excluded for episode, start, _ in first)
    assert all(lengths[episode] - start > max(spec.HORIZONS) for episode, start, _ in first)
