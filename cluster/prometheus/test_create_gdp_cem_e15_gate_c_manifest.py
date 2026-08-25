from __future__ import annotations

import gdp_cem_e15_specs as spec
from create_gdp_cem_e15_gate_c_manifest import rows


def test_gate_c_registry_is_complete_bijective_and_task_first() -> None:
    value = rows()
    assert len(value) == 432
    assert len(
        {
            (
                row["task"],
                row["arm"],
                row["replicate"],
                row["horizon"],
                row["shard"],
            )
            for row in value
        }
    ) == 432
    assert [row["array_id"] for row in value] == list(range(432))
    assert {row["task"] for row in value[:216]} == {spec.TASKS[0]}
    assert {row["task"] for row in value[216:]} == {spec.TASKS[1]}
    assert {row["learned_seed"] for row in value} == set(spec.MODEL_SEEDS)
    assert {row["sage_seed"] for row in value} == {6101, 6102, 6103}
