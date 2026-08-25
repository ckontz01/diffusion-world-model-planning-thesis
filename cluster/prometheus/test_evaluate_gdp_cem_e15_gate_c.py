from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import evaluate_gdp_cem_e15_gate_c as evaluation
import gdp_cem_e15_specs as spec
from gdp_cem_e15_data import sha256_file


def test_read_p2_rows_verifies_shared_starts_and_selects_exact_shard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = tmp_path / "dataset.h5"
    dataset.write_bytes(b"synthetic-e15-p2-dataset")
    queries = tmp_path / "queries.tsv"
    fields = (
        "eval_index",
        "base_index",
        "episode_id",
        "start_step",
        "goal_horizon",
        "dataset_goal_step",
        "source_global_row",
        "goal_global_row",
        "selection_hash",
    )
    with queries.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        index = 0
        for horizon in spec.GATE_C_HORIZONS:
            for base in range(spec.GATE_C_BASE_STARTS):
                writer.writerow(
                    {
                        "eval_index": index,
                        "base_index": base,
                        "episode_id": 100 + base,
                        "start_step": 10 + base,
                        "goal_horizon": horizon,
                        "dataset_goal_step": 10 + base + horizon - 1,
                        "source_global_row": 1000 + base,
                        "goal_global_row": 1000 + base + horizon - 1,
                        "selection_hash": f"selection-{base}",
                    }
                )
                index += 1
    task_spec = {
        **spec.TASK_SPEC["pusht"],
        "dataset_sha256": sha256_file(dataset),
        "p2_queries_sha256": sha256_file(queries),
        "partition_manifest_sha256": "partition-hash",
    }
    provenance = {
        "status": "ok",
        "kind": "gdp_cem_e14_shared_start_p2_gate_c_manifest",
        "analysis_role": "P2_closed_loop_endpoint_selection_development",
        "task": "pusht",
        "partition": "P2",
        "base_start_count": spec.GATE_C_BASE_STARTS,
        "horizons": list(spec.GATE_C_HORIZONS),
        "rows_per_horizon": spec.GATE_C_BASE_STARTS,
        "total_rows": spec.GATE_C_BASE_STARTS * len(spec.GATE_C_HORIZONS),
        "same_episode_start_pairs_across_horizons": True,
        "dataset_sha256": sha256_file(dataset),
        "partition_manifest_sha256": "partition-hash",
        "protocol_sha256": evaluation.E14_PROTOCOL_SHA256,
        "source_manifest_sha256": evaluation.P2_MANIFEST_SOURCE_SHA256,
        "output_tsv_sha256": sha256_file(queries),
        "selection_seed": 2026082301,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    provenance_path = tmp_path / "manifest.json"
    provenance_path.write_text(
        json.dumps(provenance, sort_keys=True) + "\n", encoding="utf-8"
    )
    task_spec["p2_manifest_sha256"] = sha256_file(provenance_path)
    monkeypatch.setitem(spec.TASK_SPEC, "pusht", task_spec)

    selected, loaded = evaluation.read_p2_rows(
        queries,
        provenance_path,
        task="pusht",
        horizon=75,
        shard=2,
        dataset=dataset,
    )
    assert [int(row["base_index"]) for row in selected] == [10, 11, 12, 13, 14]
    assert {int(row["goal_horizon"]) for row in selected} == {75}
    assert loaded == provenance


def test_timing_summary_excludes_only_the_first_synchronized_call() -> None:
    diagnostics = [
        {"value": 50.0},
        {"value": 5.0},
        {"value": 15.0},
    ]
    result = evaluation.timing_summary(diagnostics, "value")
    assert result["all_call_median_seconds_per_context_stage"] == 3.0
    assert result["post_first_call_median_seconds_per_context_stage"] == 2.0


def test_protected_evidence_paths_are_rejected() -> None:
    with pytest.raises(RuntimeError, match="protected"):
        evaluation.reject_protected_path(Path("/tmp/thesis/D5/results.json"))
    evaluation.reject_protected_path(Path("/tmp/thesis/P2/queries.tsv"))
