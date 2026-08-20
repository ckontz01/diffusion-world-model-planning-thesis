#!/usr/bin/env python3
"""Create the immutable C1 input lock only after the development phase is frozen."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.task_registry import TASKS, get_task_spec

SCORER_VARIANTS = {
    "acid",
    "reachability",
    "reachability_shuffled",
    "diffusion",
    "diffusion_shuffled",
    "diffusion_action_ablated",
    "forward",
    "forward_shuffled",
}
SEEDS = {6101, 6102, 6103}
DEVELOPMENT_EVIDENCE = {
    "closed_loop": ("matched_five_arm_closed_loop_analysis", "role", "development"),
    "validation": (
        "heldout_correct_action_identification_analysis",
        "analysis_role",
        "D1",
    ),
    "mechanism": (
        "three_task_same_candidate_mechanism_analysis",
        "analysis_role",
        "D1",
    ),
    "sensitivity": (
        "three_task_cem_weight_sigma_sensitivity_analysis",
        "analysis_role",
        "D1",
    ),
}


def parse_task_input(value: str) -> tuple[str, Path, Path, Path, Path]:
    parts = value.split("=", 4)
    if len(parts) != 5 or parts[0] not in TASKS:
        raise argparse.ArgumentTypeError(
            "task input must be "
            "TASK=EVAL_MANIFEST=WORLD_CKPT=I1_MANIFEST=I1_SUMMARY"
        )
    return parts[0], Path(parts[1]), Path(parts[2]), Path(parts[3]), Path(parts[4])


def parse_scorer(value: str) -> tuple[str, str, int, Path]:
    parts = value.split("=", 3)
    if len(parts) != 4 or parts[0] not in TASKS or parts[1] not in SCORER_VARIANTS:
        raise argparse.ArgumentTypeError("scorer must be TASK=VARIANT=SEED=CHECKPOINT")
    try:
        seed = int(parts[2])
    except ValueError as error:
        raise argparse.ArgumentTypeError("scorer seed must be an integer") from error
    if seed not in SEEDS:
        raise argparse.ArgumentTypeError(f"unexpected scorer seed: {seed}")
    return parts[0], parts[1], seed, Path(parts[3])


def parse_evidence(value: str) -> tuple[str, Path]:
    parts = value.split("=", 1)
    if len(parts) != 2 or parts[0] not in DEVELOPMENT_EVIDENCE:
        raise argparse.ArgumentTypeError(
            "development evidence must be NAME=SUMMARY_JSON"
        )
    return parts[0], Path(parts[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--analysis-manifest", type=Path, required=True)
    parser.add_argument("--orchestration-manifest", type=Path, required=True)
    parser.add_argument(
        "--task-input", type=parse_task_input, action="append", required=True
    )
    parser.add_argument("--scorer", type=parse_scorer, action="append", required=True)
    parser.add_argument(
        "--development-evidence",
        type=parse_evidence,
        action="append",
        required=True,
    )
    parser.add_argument("--development-submission-state", type=Path, required=True)
    parser.add_argument("--decision-note", required=True)
    parser.add_argument("--authorized-by", required=True)
    parser.add_argument("--attest-c1-outcomes-unseen", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.attest_c1_outcomes_unseen:
        raise SystemExit(
            "refusing authorization without the unseen-outcomes attestation"
        )
    if not args.authorized_by.strip():
        raise ValueError("authorized-by must not be blank")
    if not args.decision_note.strip():
        raise ValueError("decision-note must not be blank")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite authorization: {args.output}")
    for path in (
        args.source_manifest,
        args.analysis_manifest,
        args.orchestration_manifest,
        args.development_submission_state,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hash = sha256_file(args.source_manifest)
    evidence_paths = dict(args.development_evidence)
    if len(evidence_paths) != len(args.development_evidence) or set(
        evidence_paths
    ) != set(DEVELOPMENT_EVIDENCE):
        raise RuntimeError("authorization requires the exact development evidence set")
    evidence: dict[str, Any] = {}
    for name, (kind, role_field, role_value) in DEVELOPMENT_EVIDENCE.items():
        path = evidence_paths[name]
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("status") != "ok"
            or payload.get("kind") != kind
            or payload.get(role_field) != role_value
            or set(payload.get("tasks", [])) != set(TASKS)
            or payload.get("source_manifest_sha256") != source_hash
        ):
            raise RuntimeError(f"invalid development evidence: {name}")
        if name == "validation" and (
            payload.get("confirmatory") is not False
            or payload.get("data_role") != "P1_val"
        ):
            raise RuntimeError("development validation evidence is not P1_val-only")
        evidence[name] = {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "kind": kind,
        }
    task_inputs: dict[str, tuple[Path, Path, Path, Path]] = {}
    for (
        task,
        eval_manifest,
        world_checkpoint,
        identification_manifest,
        identification_summary,
    ) in args.task_input:
        if task in task_inputs:
            raise RuntimeError(f"duplicate task input: {task}")
        if (
            not eval_manifest.is_file()
            or not world_checkpoint.is_file()
            or not identification_manifest.is_file()
            or not identification_summary.is_file()
        ):
            raise FileNotFoundError(f"missing task input for {task}")
        summary = json.loads(identification_summary.read_text(encoding="utf-8"))
        evaluation_hashes = {
            record.get("sha256")
            for record in summary.get("evaluation_manifests", [])
            if isinstance(record, dict)
        }
        if (
            summary.get("status") != "ok"
            or summary.get("kind")
            != "acid_alternative_i1_identification_episode_manifest"
            or summary.get("task") != task
            or summary.get("seed") != 2026081314
            or summary.get("count") != 200
            or summary.get("source_partition")
            != get_task_spec(task).i1_source_partition
            or summary.get("frameskip") != 5
            or summary.get("manifest_sha256")
            != sha256_file(identification_manifest)
            or summary.get("confirmation_identification_outcomes_computed") is not False
            or sha256_file(eval_manifest) not in evaluation_hashes
            or not isinstance(summary.get("legacy_sources"), list)
        ):
            raise RuntimeError(f"invalid frozen I1 identification summary for {task}")
        task_inputs[task] = (
            eval_manifest,
            world_checkpoint,
            identification_manifest,
            identification_summary,
        )
    if set(task_inputs) != set(TASKS):
        raise RuntimeError("authorization requires exactly PushT, Reacher, and Cube")
    scorers: dict[tuple[str, str, int], Path] = {}
    for task, arm, seed, path in args.scorer:
        key = (task, arm, seed)
        if key in scorers:
            raise RuntimeError(f"duplicate scorer declaration: {key}")
        if not path.is_file():
            raise FileNotFoundError(path)
        scorers[key] = path
    expected = {
        (task, variant, seed)
        for task in TASKS
        for variant in SCORER_VARIANTS
        for seed in SEEDS
    }
    if set(scorers) != expected:
        raise RuntimeError(
            f"incomplete scorer matrix; missing={sorted(expected - set(scorers))}, "
            f"extra={sorted(set(scorers) - expected)}"
        )
    tasks: dict[str, Any] = {}
    for task in TASKS:
        (
            eval_manifest,
            world_checkpoint,
            identification_manifest,
            identification_summary,
        ) = task_inputs[task]
        tasks[task] = {
            "eval_manifest": str(eval_manifest.resolve()),
            "eval_manifest_sha256": sha256_file(eval_manifest),
            "world_model_checkpoint": str(world_checkpoint.resolve()),
            "world_model_checkpoint_sha256": sha256_file(world_checkpoint),
            "identification_manifest": str(identification_manifest.resolve()),
            "identification_manifest_sha256": sha256_file(
                identification_manifest
            ),
            "identification_summary": str(identification_summary.resolve()),
            "identification_summary_sha256": sha256_file(
                identification_summary
            ),
            "scorer_checkpoint_sha256": {
                variant: {
                    str(seed): sha256_file(scorers[(task, variant, seed)])
                    for seed in sorted(SEEDS)
                }
                for variant in sorted(SCORER_VARIANTS)
            },
            "scorer_checkpoints": {
                variant: {
                    str(seed): str(scorers[(task, variant, seed)].resolve())
                    for seed in sorted(SEEDS)
                }
                for variant in sorted(SCORER_VARIANTS)
            },
        }
    result = {
        "status": "authorized",
        "kind": "acid_alternative_c1_authorization_v1",
        "authorized_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorized_by": args.authorized_by.strip(),
        "decision_note": args.decision_note.strip(),
        "confirmation_outcomes_unseen": True,
        "task_suite": sorted(TASKS),
        "source_manifest": str(args.source_manifest.resolve()),
        "source_manifest_sha256": source_hash,
        "analysis_manifest": str(args.analysis_manifest.resolve()),
        "analysis_manifest_sha256": sha256_file(args.analysis_manifest),
        "orchestration_manifest": str(args.orchestration_manifest.resolve()),
        "orchestration_manifest_sha256": sha256_file(args.orchestration_manifest),
        "development_submission_state": str(
            args.development_submission_state.resolve()
        ),
        "development_submission_state_sha256": sha256_file(
            args.development_submission_state
        ),
        "development_evidence": evidence,
        "primary_configuration": {
            "lambda_weight": 0.07,
            "goal_offset": 25,
            "horizon": 5,
            "receding_horizon": 5,
            "action_block": 5,
            "cem_samples": 300,
            "cem_steps": 30,
            "cem_topk": 30,
        },
        "tasks": tasks,
    }
    atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
