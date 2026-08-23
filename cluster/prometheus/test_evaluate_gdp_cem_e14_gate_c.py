from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import torch

import gdp_cem_e14_specs as spec
from evaluate_gdp_cem_e14_gate_c import (
    P2_MANIFEST_SOURCE_SHA256,
    atomic_json,
    read_gate_b,
    read_p2_rows,
    sage_expected_config,
    statistics_from_payload,
    verify_training_directory,
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate_b_requires_predeclared_successful_endpoint(tmp_path: Path) -> None:
    audit = tmp_path / "GATE-B-AUDIT.json"
    payload = {
        "status": "ok",
        "kind": "gdp_cem_e14_gate_b_offline_analysis",
        "analysis_role": "P1_validation_only_Gate_B_development",
        "decision": "authorize_gate_c_p2_development_for_eligible_endpoints",
        "eligible_endpoints": ["vad"],
        "endpoint_results": {
            "vad": {
                "eligible_for_gate_c": True,
                "gates": {"a": True, "b": True},
            }
        },
        "artifact_count": 32,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest_sha256": (
            "99f92cbe3c735a999866b52103241633ec80a7dffeca5217c07b0ec5590176cd"
        ),
        "source_manifest_sha256": (
            "bc27ec5c93dfae6681c149fd755d93742a0678583787bad7e3fcd43300d59cae"
        ),
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(audit, payload)
    assert read_gate_b(audit, file_hash(audit))["eligible_endpoints"] == ["vad"]
    payload["endpoint_results"]["vad"]["gates"]["b"] = False
    audit.unlink()
    atomic_json(audit, payload)
    try:
        read_gate_b(audit, file_hash(audit))
    except RuntimeError as error:
        assert "failed gate" in str(error)
    else:
        raise AssertionError("failed Gate-B endpoint was authorized")


def test_p2_reader_preserves_shared_starts_and_shards(
    tmp_path: Path, monkeypatch
) -> None:
    dataset = tmp_path / "dataset.h5"
    dataset.write_bytes(b"identifier-only test dataset")
    dataset_sha = file_hash(dataset)
    monkeypatch.setitem(spec.TASK_SPEC["pusht"], "dataset_sha256", dataset_sha)
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
    with queries.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        index = 0
        for horizon in spec.GATE_C_HORIZONS:
            for base in range(spec.GATE_C_BASE_STARTS):
                writer.writerow(
                    {
                        "eval_index": index,
                        "base_index": base,
                        "episode_id": base + 100,
                        "start_step": base,
                        "goal_horizon": horizon,
                        "dataset_goal_step": base + horizon - 1,
                        "source_global_row": base,
                        "goal_global_row": base + horizon - 1,
                        "selection_hash": f"hash-{base}",
                    }
                )
                index += 1
    provenance = tmp_path / "manifest.json"
    atomic_json(
        provenance,
        {
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
            "dataset_sha256": dataset_sha,
            "partition_manifest_sha256": spec.TASK_SPEC["pusht"][
                "partition_manifest_sha256"
            ],
            "protocol_sha256": spec.PROTOCOL_SHA256,
            "source_manifest_sha256": P2_MANIFEST_SOURCE_SHA256,
            "output_tsv_sha256": file_hash(queries),
            "selection_seed": 2026082301,
            "d3_metric_read": False,
            "d4_metric_read": False,
            "d5_read": False,
            "protected_p3_p4_c1_i1_read": False,
            "claim_allowed": False,
        },
    )
    rows, _ = read_p2_rows(
        queries,
        provenance,
        task="pusht",
        horizon=75,
        shard=2,
        dataset=dataset,
    )
    assert [int(row["base_index"]) for row in rows] == [10, 11, 12, 13, 14]
    assert all(int(row["goal_horizon"]) == 75 for row in rows)


def test_statistics_and_sage_configs_are_exact() -> None:
    payload = {
        "latent_mean": torch.zeros(spec.LATENT_DIM),
        "latent_std": torch.ones(spec.LATENT_DIM),
        "state_mean": torch.zeros(7),
        "state_std": torch.ones(7),
        "action_mean": torch.zeros(2),
        "action_std": torch.ones(2),
        "action_robust_low": torch.full((2,), -2.0),
        "action_robust_high": torch.full((2,), 2.0),
        "local_residual_mean": torch.zeros(spec.LATENT_DIM),
        "local_residual_std": torch.ones(spec.LATENT_DIM),
    }
    statistics_from_payload(payload, task="pusht")
    assert sage_expected_config("pusht", "subgoal")["feedforward_dim"] == 2816
    assert sage_expected_config("cube", "option")["primitive_action_dim"] == 5


def test_training_checksum_manifest_rejects_mutation(tmp_path: Path) -> None:
    for name in ("best.pt", "training.jsonl", "summary.json"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "sha256.txt").write_text(
        "".join(
            f"{file_hash(tmp_path / name)}  /frozen/{name}\n"
            for name in ("best.pt", "training.jsonl", "summary.json")
        ),
        encoding="utf-8",
    )
    verify_training_directory(tmp_path)
    (tmp_path / "best.pt").write_text("mutated", encoding="utf-8")
    try:
        verify_training_directory(tmp_path)
    except RuntimeError as error:
        assert "hash differs" in str(error)
    else:
        raise AssertionError("mutated E14 training artifact passed")
