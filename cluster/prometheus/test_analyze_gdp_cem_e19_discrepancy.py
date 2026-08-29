from __future__ import annotations

from analyze_gdp_cem_e19_discrepancy import cube_cache_gate


def cache_event(*, key=(0, 0, 150, 25), value="abc", hit=False):
    text_key = str(tuple(key))
    return {
        "kind": "cube_local_goal_cache",
        "stage_keys": [list(key)],
        "cache_hit": [hit],
        "values_before": ({text_key: value} if hit else {}),
        "values_after": {text_key: value},
        "returned_by_stage_key": [value],
    }


def test_cube_cache_gate_accepts_stable_miss_then_hit() -> None:
    traces = [
        {"events": [cache_event(hit=False), cache_event(hit=True)]},
        {"events": [cache_event(hit=False), cache_event(hit=True)]},
    ]
    audit = cube_cache_gate(traces)
    assert audit["passed"] is True
    assert audit["scoped_unique_stage_key_count"] == 2


def test_cube_cache_gate_rejects_return_drift() -> None:
    event = cache_event()
    event["returned_by_stage_key"] = ["different"]
    audit = cube_cache_gate([{"events": [event]}])
    assert audit["passed"] is False
    assert audit["return_mismatches"] == ["sunknown/runknown/t0:(0, 0, 150, 25)"]


def test_cube_cache_gate_scopes_same_key_to_each_run() -> None:
    traces = [
        {
            "sentinel": {"sentinel_id": 3},
            "repeat": 0,
            "events": [cache_event(value="first")],
        },
        {
            "sentinel": {"sentinel_id": 4},
            "repeat": 0,
            "events": [cache_event(value="second")],
        },
    ]
    audit = cube_cache_gate(traces)
    assert audit["passed"] is True
    assert audit["scoped_unique_stage_key_count"] == 2


def test_cube_cache_gate_rejects_expanded_stage_key_drift() -> None:
    first = cache_event(key=(0, 4, 150, 25), value="first")
    second = cache_event(key=(0, 4, 125, 25), value="second")
    audit = cube_cache_gate([{"events": [first, second]}])
    assert audit["passed"] is False
    assert audit["checks"]["expanded_unexpanded_stage_keys_exact"] is False
