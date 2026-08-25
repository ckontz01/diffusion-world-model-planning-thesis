from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import analyze_gdp_cem_e15_gate_c as analysis
import gdp_cem_e15_specs as spec
from gdp_cem_e15_data import sha256_file


def test_nested_rates_and_clustered_bootstrap_keep_replicates_paired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    success = np.zeros(
        (
            len(spec.TASKS),
            spec.GATE_C_BASE_STARTS,
            len(spec.ARMS),
            len(spec.GATE_C_HORIZONS),
            3,
        ),
        dtype=np.float64,
    )
    success[:, :, spec.ARMS.index("vad"), :, :] = 1.0
    rates = analysis.nested_rate_tables(success)
    differences = analysis.paired_differences(success)
    assert rates["equal_task_equal_horizon"]["vad"] == 1.0
    assert rates["equal_task_long_horizons_75_150"]["direct_gmm"] == 0.0
    assert differences["direct_gmm"]["minimum_task_horizon_cell"] == 1.0
    assert differences["direct_gmm"]["positive_horizon_count_by_task"] == {
        "pusht": 3,
        "cube": 3,
    }

    monkeypatch.setattr(analysis, "BOOTSTRAP_RESAMPLES", 20)
    bootstrap = analysis.clustered_bootstrap(success)
    assert bootstrap["unit"] == "task_base_start_cluster"
    assert bootstrap["arms_horizons_replicates_retained_paired"] is True
    assert bootstrap["seeds_resampled_as_independent"] is False
    assert bootstrap[
        "vad_minus_comparator_equal_task_long_horizons_75_150_95ci"
    ]["direct_gmm"] == [1.0, 1.0]
    assert bootstrap["vad_minus_comparator_equal_task_horizon_150_95ci"][
        "sage_reconstruction"
    ] == [1.0, 1.0]


def test_timing_ratio_uses_post_first_long_horizon_stage_calls() -> None:
    records = []
    for task in spec.TASKS:
        for horizon in spec.GATE_C_HORIZONS:
            for arm in spec.ARMS:
                post = 50.0 if arm == "sage_reconstruction" else 5.0
                records.append(
                    {
                        "cell": {"task": task, "horizon": horizon, "arm": arm},
                        "diagnostics": [
                            {
                                "call": 0,
                                "end_to_end_stage_seconds": 500.0,
                                "proposal_and_selection_seconds": 1.0,
                                "lewm_scoring_seconds": 1.0,
                                "encoding_seconds": 1.0,
                            },
                            {
                                "call": 1,
                                "end_to_end_stage_seconds": post,
                                "proposal_and_selection_seconds": 1.0,
                                "lewm_scoring_seconds": 1.0,
                                "encoding_seconds": 1.0,
                            },
                        ],
                    }
                )
    timing = analysis.timing_tables(records)
    assert timing["full_sage_over_vad_post_first_latency_ratio"] == 10.0
    assert (
        timing["task_horizon"]["pusht"]["vad"]["75"]["end_to_end"][
            "post_first_call_median_seconds"
        ]
        == 1.0
    )


def test_gate_decision_accepts_registered_inclusive_noninferiority_bounds() -> None:
    def comparison(
        *,
        overall: float,
        long: float = 0.0,
        h150: float = 0.0,
        minimum: float = 0.0,
        minimum_long: float = 0.0,
    ) -> dict[str, object]:
        return {
            "equal_task_equal_horizon": overall,
            "equal_task_long_horizons_75_150": long,
            "equal_task_horizon_150": h150,
            "minimum_task_horizon_cell": minimum,
            "minimum_long_task_horizon_cell": minimum_long,
            "positive_horizon_count_by_task": {"pusht": 2, "cube": 2},
            "task_horizon": {
                "pusht": {"25": 0.0, "75": 0.0, "150": 0.15},
                "cube": {"25": 0.0, "75": 0.0, "150": 0.0},
            },
        }

    differences = {
        "diagonal_gaussian": comparison(overall=0.01, minimum=-0.05),
        "direct_gmm": comparison(overall=0.01, minimum=-0.05),
        "base_cem": comparison(overall=0.0),
        "sage_reconstruction": comparison(
            overall=0.0, long=-0.03, h150=-0.03, minimum_long=-0.10
        ),
        "sage_one_stage": comparison(overall=0.0),
    }
    decision = analysis.gate_decision(
        differences, {"full_sage_over_vad_post_first_latency_ratio": 5.0}
    )
    assert decision["full_sage_efficiency_noninferiority_route"] is True
    assert decision["authorize_separate_untouched_d5_protocol_draft"] is True
    decision = analysis.gate_decision(
        differences, {"full_sage_over_vad_post_first_latency_ratio": 4.99}
    )
    assert decision["authorize_separate_untouched_d5_protocol_draft"] is False


def authorization_payloads() -> tuple[dict[str, object], dict[str, object]]:
    gate_a = {
        "status": "passed",
        "kind": "gdp_cem_e15_gate_a_implementation_lineage_validation",
        "analysis_role": "P1_train_only_technical_preflight",
        "smoke_artifacts": {str(index): {} for index in range(22)},
        "sage_artifacts": {str(index): {} for index in range(6)},
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest_sha256": analysis.TRAINING_SOURCE_MANIFEST_SHA256,
        "source_manifest_sha256": analysis.OFFLINE_SOURCE_MANIFEST_SHA256,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    gate_b = {
        "status": "ok",
        "kind": "gdp_cem_e15_gate_b_offline_analysis",
        "analysis_role": "P1_validation_only_Gate_B_development",
        "decision": "authorize_fixed_gate_c_p2_long_horizon_development",
        "gate_b_passed": True,
        "gates": {
            "common_bank_integrity": {"pass": True},
            "direct_gmm_structural_validity": {"pass": True},
            "vad_mechanism_and_conditioning": {"pass": True},
        },
        "artifact_count": 22,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest_sha256": analysis.TRAINING_SOURCE_MANIFEST_SHA256,
        "source_manifest_sha256": analysis.OFFLINE_SOURCE_MANIFEST_SHA256,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    return gate_a, gate_b


def write_json(path: Path, value: dict[str, object]) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def test_gate_c_analyzer_revalidates_both_authorizations(tmp_path: Path) -> None:
    gate_a, gate_b = authorization_payloads()
    gate_a_path = tmp_path / "gate-a.json"
    gate_b_path = tmp_path / "gate-b.json"
    gate_a_hash = write_json(gate_a_path, gate_a)
    gate_b_hash = write_json(gate_b_path, gate_b)
    loaded_a, loaded_b = analysis.verify_gate_authorizations(
        gate_a_path,
        gate_b_path,
        gate_a_sha256=gate_a_hash,
        gate_b_sha256=gate_b_hash,
    )
    assert loaded_a == gate_a
    assert loaded_b == gate_b

    gate_b["decision"] = "stop_focused_long_horizon_confirmation_line"
    gate_b_hash = write_json(gate_b_path, gate_b)
    with pytest.raises(RuntimeError, match="Gate-B authorization"):
        analysis.verify_gate_authorizations(
            gate_a_path,
            gate_b_path,
            gate_a_sha256=gate_a_hash,
            gate_b_sha256=gate_b_hash,
        )
