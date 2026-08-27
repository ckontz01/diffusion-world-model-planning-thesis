from __future__ import annotations

import gdp_cem_e18_specs as spec
from create_gdp_cem_e18_cells import rows


def test_arm_and_budget_registry() -> None:
    assert spec.first_candidate_count("vad_greedy_300") == 300
    assert spec.first_candidate_count("vad_greedy_576") == 576
    assert spec.first_candidate_count("vad_continuation") == 64
    assert spec.family_for_arm("vad_continuation") == "vad"
    assert spec.family_for_arm("diagonal_gaussian_continuation") == (
        "diagonal_gaussian"
    )
    assert spec.family_for_arm("direct_gmm_continuation") == "direct_gmm"
    assert spec.FIRST_CANDIDATES * (1 + spec.CONTINUATIONS_PER_FIRST) == 576


def test_execution_registry_is_exact() -> None:
    values = rows()
    assert len(values) == 240
    assert [row["array_id"] for row in values] == list(range(240))
    assert {row["task"] for row in values} == set(spec.TASKS)
    assert {row["arm"] for row in values} == set(spec.ARMS)
    assert {row["learned_seed"] for row in values} == set(spec.MODEL_SEEDS)
    assert {row["horizon"] for row in values} == set(spec.HORIZONS)
    assert {row["shard"] for row in values} == set(range(spec.SHARD_COUNT))
