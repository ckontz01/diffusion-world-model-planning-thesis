"""Tests for frozen E14 P2 shared-start selection."""

from __future__ import annotations

import numpy as np

from create_gdp_cem_e14_p2_manifest import BASE_STARTS, select_base_starts


def test_p2_selection_is_deterministic_unique_and_h150_compatible() -> None:
    lengths = np.asarray([200, 180, 149, 170], dtype=np.int64)
    partitions = {0: "P2", 1: "P2", 2: "P2", 3: "P1"}
    first, eligible = select_base_starts(lengths, partitions, task="pusht")
    second, second_eligible = select_base_starts(
        lengths, partitions, task="pusht"
    )
    assert first == second
    assert eligible == second_eligible == (200 - 150) + (180 - 150)
    assert len(first) == BASE_STARTS
    assert len({(episode, start) for episode, start, _ in first}) == BASE_STARTS
    assert all(start + 150 <= lengths[episode] for episode, start, _ in first)
