#!/usr/bin/env python3
"""Validate E15 implementation lineage after all train-only smoke cells finish."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

import gdp_cem_e15_specs as spec
from analyze_gdp_cem_e15_offline import expected_cells, verify_checksum_file
from evaluate_gdp_cem_e15_offline import TRAINING_SOURCE_MANIFEST_SHA256
from gdp_cem_e14_models import SAGEOptionPrior, SAGESubgoalGenerator
from gdp_cem_e15_data import sha256_file


E14_PROTOCOL_SHA256 = "9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6"
E14_TRAINING_SOURCE_MANIFEST_SHA256 = (
    "99f92cbe3c735a999866b52103241633ec80a7dffeca5217c07b0ec5590176cd"
)


def atomic_json(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def verify_sage_component(
    directory: Path,
    *,
    task: str,
    component: str,
    seed: int,
    expected_subgoal_sha256: str | None,
) -> dict[str, Any]:
    summary_path = directory / "summary.json"
    checkpoint_path = directory / "best.pt"
    if not summary_path.is_file() or not checkpoint_path.is_file():
        raise FileNotFoundError(directory)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    checkpoint_hash = sha256_file(checkpoint_path)
    config = summary.get("model_config")
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != f"gdp_cem_e14_sage_{component}_training"
        or summary.get("analysis_role")
        != "P1_only_published_equation_SAGE_reconstruction"
        or summary.get("task") != task
        or summary.get("component") != component
        or int(summary.get("seed", -1)) != seed
        or summary.get("checkpoint_sha256") != checkpoint_hash
        or summary.get("subgoal_checkpoint_sha256") != expected_subgoal_sha256
        or summary.get("protocol_sha256") != E14_PROTOCOL_SHA256
        or summary.get("source_manifest_sha256")
        != E14_TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("official_implementation") is not False
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
        or not isinstance(config, dict)
    ):
        raise RuntimeError("E15 unchanged E14 SAGE summary identity differs")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if (
        payload.get("kind") != f"gdp_cem_e14_sage_{component}_checkpoint"
        or payload.get("task") != task
        or int(payload.get("seed", -1)) != seed
        or payload.get("model_config") != config
        or payload.get("subgoal_checkpoint_sha256") != expected_subgoal_sha256
        or not isinstance(payload.get("state_dict"), dict)
    ):
        raise RuntimeError("E15 unchanged E14 SAGE checkpoint identity differs")
    model: torch.nn.Module = (
        SAGESubgoalGenerator(**config)
        if component == "subgoal"
        else SAGEOptionPrior(**config)
    )
    model.load_state_dict(payload["state_dict"], strict=True)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != int(summary.get("parameter_count", -1)):
        raise RuntimeError("E15 unchanged E14 SAGE parameter count differs")
    del model, payload
    return {
        "directory": str(directory),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint_sha256": checkpoint_hash,
        "parameter_count": parameter_count,
        "loaded_strictly_on_cpu": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-root", type=Path, required=True)
    parser.add_argument("--sage-normalized-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--static-preflight", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.smoke_root,
        args.sage_normalized_root,
        args.protocol,
        args.source_manifest,
        args.static_preflight,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E15 Gate-A output")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E15 Gate-A protocol hash differs")
    source_hash = sha256_file(args.source_manifest)
    static = json.loads(args.static_preflight.read_text(encoding="utf-8"))
    if (
        static.get("status") != "passed"
        or static.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or static.get("d5_read") is not False
    ):
        raise RuntimeError("E15 Gate-A static preflight differs")

    smoke: dict[str, Any] = {}
    for task, condition, seed in expected_cells():
        directory = args.smoke_root / task / condition / f"seed-{seed}"
        verify_checksum_file(directory)
        summary_path = directory / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if (
            summary.get("status") != "ok"
            or summary.get("kind") != "gdp_cem_e15_offline_proposer_evaluation"
            or summary.get("analysis_role") != "P1_train_only_technical_smoke"
            or summary.get("mode") != "smoke"
            or summary.get("task") != task
            or summary.get("condition") != condition
            or int(summary.get("seed", -1)) != seed
            or int(summary.get("row_count", -1)) != len(spec.DELTA_TAU_PAIRS)
            or int(summary.get("candidate_count", -1)) != spec.CANDIDATE_COUNT
            or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
            or summary.get("source_manifest_sha256") != source_hash
            or summary.get("training_source_manifest_sha256")
            != TRAINING_SOURCE_MANIFEST_SHA256
            or summary.get("p2_read") is not False
            or summary.get("d3_metric_read") is not False
            or summary.get("d4_metric_read") is not False
            or summary.get("d5_read") is not False
            or summary.get("protected_p3_p4_c1_i1_read") is not False
            or summary.get("claim_allowed") is not False
        ):
            raise RuntimeError("E15 Gate-A smoke identity differs")
        metrics_path = directory / "metrics.h5"
        with h5py.File(metrics_path, "r") as handle:
            delta = np.asarray(handle["delta"][:], dtype=np.int64)
            tau = np.asarray(handle["tau"][:], dtype=np.int64)
            metrics_finite = all(
                np.isfinite(np.asarray(dataset[:])).all()
                for dataset in handle["metrics"].values()
            )
            gmm_finite = "gmm" not in handle or all(
                np.isfinite(np.asarray(dataset[:])).all()
                for dataset in handle["gmm"].values()
            )
        if (
            not metrics_finite
            or not gmm_finite
            or sorted(zip(delta.tolist(), tau.tolist()))
            != sorted(spec.DELTA_TAU_PAIRS)
        ):
            raise RuntimeError("E15 Gate-A smoke content differs")
        smoke["|".join(map(str, (task, condition, seed)))] = {
            "summary_sha256": sha256_file(summary_path),
            "metrics_h5_sha256": sha256_file(metrics_path),
            "all_45_shapes_and_rollouts_succeeded": True,
        }

    normalization_path = args.sage_normalized_root / "NORMALIZATION.json"
    if sha256_file(normalization_path) != spec.SAGE_NORMALIZATION_AUDIT_SHA256:
        raise RuntimeError("E15 SAGE normalization audit hash differs")
    normalization = json.loads(normalization_path.read_text(encoding="utf-8"))
    if (
        normalization.get("status") != "ok"
        or int(normalization.get("logical_link_count", -1)) != 44
        or normalization.get("model_bytes_modified") is not False
        or normalization.get("performance_metric_read") is not False
        or normalization.get("claim_allowed") is not False
    ):
        raise RuntimeError("E15 SAGE normalization audit content differs")
    sage: dict[str, Any] = {}
    for task in spec.TASKS:
        for seed in (6101, 6102, 6103):
            subgoal = verify_sage_component(
                args.sage_normalized_root / "sage" / "subgoal" / task / f"seed-{seed}",
                task=task,
                component="subgoal",
                seed=seed,
                expected_subgoal_sha256=None,
            )
            option = verify_sage_component(
                args.sage_normalized_root / "sage" / "option" / task / f"seed-{seed}",
                task=task,
                component="option",
                seed=seed,
                expected_subgoal_sha256=subgoal["checkpoint_sha256"],
            )
            sage[f"{task}|{seed}"] = {"subgoal": subgoal, "option": option}

    result = {
        "status": "passed",
        "kind": "gdp_cem_e15_gate_a_implementation_lineage_validation",
        "analysis_role": "P1_train_only_technical_preflight",
        "checks": [
            "static_formula_and_mask_tests",
            "22_checksum_valid_final_training_artifacts_loaded_by_smoke",
            "22_train_only_45_cell_300_candidate_lewm_rollout_smokes",
            "strictly_legal_common_bounded_decoder",
            "direct_gmm_one_component_per_trajectory",
            "unchanged_e14_sage_normalization_audit",
            "12_sage_subgoal_option_checkpoints_strictly_loaded_on_cpu",
        ],
        "smoke_artifacts": smoke,
        "sage_artifacts": sage,
        "sage_normalization_audit_sha256": spec.SAGE_NORMALIZATION_AUDIT_SHA256,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest_sha256": TRAINING_SOURCE_MANIFEST_SHA256,
        "source_manifest_sha256": source_hash,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "GATE-A-AUDIT.json"
    atomic_json(output, result)
    (args.output_dir / "sha256.txt").write_text(
        f"{sha256_file(output)}  GATE-A-AUDIT.json\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
