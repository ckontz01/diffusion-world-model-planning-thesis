from __future__ import annotations

import gdp_cem_e19_discrepancy_specs as spec
from gdp_cem_e19_d2_validity import trace_gate
from trace_gdp_cem_e19_discrepancy import canonical_sha256


def make_trace(sentinel: spec.Sentinel, *, include_history: bool) -> dict:
    events = [
        {"kind": "solver_input", "plan_index": 0},
        {"kind": "final_goal_latents", "plan_index": 0},
        {"kind": "local_goal", "plan_index": 0},
    ]
    if include_history:
        events.append({"kind": "history_latents", "plan_index": 0})
    for round_index in range(spec.PLANNER["cem_rounds"]):
        row = {
            "kind": "cem_fit",
            "plan_index": 0,
            "round_index": round_index,
            "elite_indices": "elite",
            "mean": "mean",
            "effective_std": "std",
        }
        if round_index == 0:
            row["candidates"] = "candidates"
            row["costs"] = "costs"
        events.append(row)
    return {
        "kind": "gdp_cem_e19_discrepancy_trace",
        "sentinel": {"sentinel_id": sentinel.sentinel_id},
        "repeat": 0,
        "planner": spec.PLANNER,
        "events": events,
        "event_stream_sha256": canonical_sha256(events),
        "observational_only": True,
        "official_sage_source_modified": False,
        "checkpoint_modified": False,
        "planner_parameter_modified": False,
        "protected_metric_artifact_read": False,
        "e18_vs_sage_comparison_run": False,
        "d5_read": False,
    }


def test_valid_history_free_base_cem_trace_passes() -> None:
    gate = trace_gate(make_trace(spec.SENTINELS[0], include_history=False), spec.SENTINELS[0], 0)
    assert gate["passed"] is True
    assert gate["checks"]["history_semantics_valid"] is True


def test_base_cem_trace_rejects_unexpected_history_event() -> None:
    gate = trace_gate(make_trace(spec.SENTINELS[0], include_history=True), spec.SENTINELS[0], 0)
    assert gate["passed"] is False
    assert gate["checks"]["history_semantics_valid"] is False


def test_history_free_sage_trace_fails() -> None:
    gate = trace_gate(make_trace(spec.SENTINELS[4], include_history=False), spec.SENTINELS[4], 0)
    assert gate["passed"] is False
    assert gate["checks"]["history_semantics_valid"] is False


def test_sage_trace_with_history_event_passes() -> None:
    gate = trace_gate(make_trace(spec.SENTINELS[4], include_history=True), spec.SENTINELS[4], 0)
    assert gate["passed"] is True
    assert gate["checks"]["history_semantics_valid"] is True
