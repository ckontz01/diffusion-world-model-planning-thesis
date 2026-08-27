from __future__ import annotations

import numpy as np

import gdp_cem_e16_specs as spec
from create_gdp_cem_e16_p2_manifest import select_base_starts
from create_gdp_cem_e16_stage_c_cells import rows


def test_cell_registry_is_task_first_and_complete() -> None:
    value = rows()
    assert len(value) == 336
    assert [row["array_id"] for row in value] == list(range(336))
    assert set(row["arm"] for row in value) == set(spec.STAGE_C_ARMS)


def test_p2_selector_excludes_old_pairs() -> None:
    lengths = np.asarray([200, 200], dtype=np.int64)
    partitions = {0: "P2", 1: "P2"}
    excluded = {(0, 0), (1, 0)}
    selected, eligible = select_base_starts(
        lengths, partitions, task="pusht", excluded=excluded
    )
    assert eligible == 98
    assert len(selected) == spec.STAGE_C_BASE_STARTS
    assert all((episode, start) not in excluded for episode, start, _ in selected)
