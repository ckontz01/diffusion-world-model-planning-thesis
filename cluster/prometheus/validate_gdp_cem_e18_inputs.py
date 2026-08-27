#!/usr/bin/env python3
"""Run the nonmetric frozen-input audit for E18."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import torch

import gdp_cem_e18_specs as spec
from gdp_cem_e15_data import sha256_file
from gdp_cem_e18_inputs import load_e17_adapter, verify_e17_audit
from gdp_cem_e18_runtime import load_e15_proposer


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e15-training-root", type=Path, required=True)
    parser.add_argument("--e17-model-root", type=Path, required=True)
    parser.add_argument("--e17-audit", type=Path, required=True)
    parser.add_argument("--e17-task-first", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.e15_training_root,
        args.e17_model_root,
        args.e17_audit,
        args.e17_task_first,
        args.protocol,
        args.source_manifest,
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E18 input-audit output")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E18 protocol hash differs")
    source_sha = sha256_file(args.source_manifest)
    e17_audit = verify_e17_audit(args.e17_audit, args.e17_task_first)
    device = torch.device("cpu")
    adapters: dict[str, Any] = {}
    for task in spec.TASKS:
        adapter, record = load_e17_adapter(
            args.e17_model_root / task, task=task, device=device
        )
        adapters[task] = record
        del adapter
    proposers: dict[str, Any] = {}
    for task in spec.TASKS:
        for condition in ("vad", "diagonal_gaussian", "direct_gmm"):
            for seed in spec.MODEL_SEEDS:
                model, _, record = load_e15_proposer(
                    args.e15_training_root,
                    task=task,
                    condition=condition,
                    seed=seed,
                    device=device,
                )
                proposers[f"{task}|{condition}|{seed}"] = record
                del model
    if len(proposers) != 18:
        raise RuntimeError("E18 proposer artifact count differs")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit = {
        "status": "passed",
        "kind": "gdp_cem_e18_nonmetric_input_audit",
        "analysis_role": "pre_outcome_lineage_validation_only",
        "e18_exploratory_study": True,
        "e17_decision_preserved": e17_audit["decision"],
        "e17_both_tasks_passed": False,
        "e17_used_as_authorization": False,
        "adapters": adapters,
        "proposers": proposers,
        "adapter_count": len(adapters),
        "proposer_count": len(proposers),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": source_sha,
        "e15_training_source_manifest_sha256": (
            spec.E15_TRAINING_SOURCE_MANIFEST_SHA256
        ),
        "e17_source_manifest_sha256": spec.E17_SOURCE_MANIFEST_SHA256,
        "e17_audit_sha256": spec.E17_AUDIT_SHA256,
        "p2_outcomes_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    audit_path = args.output_dir / "INPUT-AUDIT.json"
    atomic_json(audit_path, audit)
    (args.output_dir / "sha256.txt").write_text(
        f"{sha256_file(audit_path)}  INPUT-AUDIT.json\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
