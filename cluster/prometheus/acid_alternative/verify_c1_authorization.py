#!/usr/bin/env python3
"""Refuse a C1 run unless every immutable input matches its signed-off lock file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from acid_alternative.create_c1_authorization import (
    DEVELOPMENT_EVIDENCE,
    SCORER_VARIANTS,
)
from acid_alternative.io_utils import sha256_file
from acid_alternative.task_registry import TASKS

ARMS = {"b0", "acid", "reachability", "diffusion", "forward"}
SEEDS = {6101, 6102, 6103}
VARIANT_ARM = {
    "acid": "acid",
    "reachability": "reachability",
    "reachability_shuffled": "reachability",
    "diffusion": "diffusion",
    "diffusion_shuffled": "diffusion",
    "diffusion_action_ablated": "diffusion",
    "forward": "forward",
    "forward_shuffled": "forward",
}


def require_hash(record: dict[str, Any], key: str, path: Path) -> None:
    expected = record.get(key)
    actual = sha256_file(path)
    if expected != actual:
        raise RuntimeError(f"{key} mismatch for {path}: {expected!r} != {actual}")


def verify(
    authorization: dict[str, Any],
    *,
    task: str,
    arm: str,
    seed: int,
    source_manifest: Path,
    analysis_manifest: Path,
    orchestration_manifest: Path,
    eval_manifest: Path,
    world_model_checkpoint: Path,
    identification_manifest: Path,
    identification_summary: Path,
    scorer_checkpoint: Path | None,
    scorer_variant: str | None = None,
) -> dict[str, Any]:
    if authorization.get("status") != "authorized":
        raise RuntimeError("confirmation authorization status is not authorized")
    if authorization.get("kind") != "acid_alternative_c1_authorization_v1":
        raise RuntimeError("unexpected confirmation authorization kind")
    if authorization.get("confirmation_outcomes_unseen") is not True:
        raise RuntimeError("authorization does not attest that C1 outcomes are unseen")
    if (
        not str(authorization.get("authorized_by", "")).strip()
        or not str(authorization.get("decision_note", "")).strip()
    ):
        raise RuntimeError("authorization lacks an accountable decision record")
    if set(authorization.get("task_suite", [])) != set(TASKS):
        raise RuntimeError("authorization does not lock the full task suite")
    if set(authorization.get("tasks", {})) != set(TASKS):
        raise RuntimeError("authorization task records are incomplete")
    evidence = authorization.get("development_evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(DEVELOPMENT_EVIDENCE):
        raise RuntimeError("authorization lacks the exact development evidence set")
    for name, (kind, _role_field, _role_value) in DEVELOPMENT_EVIDENCE.items():
        record = evidence[name]
        evidence_path = Path(record.get("path", ""))
        if record.get("kind") != kind or not evidence_path.is_file():
            raise RuntimeError(f"authorization development evidence is invalid: {name}")
        require_hash(record, "sha256", evidence_path)
    state_path = Path(authorization.get("development_submission_state", ""))
    if not state_path.is_file():
        raise RuntimeError("authorization development submission state is missing")
    require_hash(authorization, "development_submission_state_sha256", state_path)
    if arm not in ARMS or seed not in SEEDS or task not in TASKS:
        raise ValueError("invalid task, arm, or scorer seed")
    primary = authorization.get("primary_configuration")
    expected_primary = {
        "lambda_weight": 0.07,
        "goal_offset": 25,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "cem_samples": 300,
        "cem_steps": 30,
        "cem_topk": 30,
    }
    if primary != expected_primary:
        raise RuntimeError("authorization primary configuration differs from protocol")
    require_hash(authorization, "source_manifest_sha256", source_manifest)
    require_hash(authorization, "analysis_manifest_sha256", analysis_manifest)
    require_hash(authorization, "orchestration_manifest_sha256", orchestration_manifest)
    try:
        task_record = authorization["tasks"][task]
    except (KeyError, TypeError) as error:
        raise RuntimeError(f"authorization lacks task {task}") from error
    require_hash(task_record, "eval_manifest_sha256", eval_manifest)
    require_hash(task_record, "world_model_checkpoint_sha256", world_model_checkpoint)
    require_hash(
        task_record, "identification_manifest_sha256", identification_manifest
    )
    require_hash(
        task_record, "identification_summary_sha256", identification_summary
    )
    hashes = task_record.get("scorer_checkpoint_sha256")
    expected_seed_keys = {str(seed) for seed in SEEDS}
    if not isinstance(hashes, dict) or set(hashes) != SCORER_VARIANTS:
        raise RuntimeError("authorization scorer matrix is incomplete")
    if any(
        not isinstance(seed_hashes, dict) or set(seed_hashes) != expected_seed_keys
        for seed_hashes in hashes.values()
    ):
        raise RuntimeError("authorization scorer seed matrix is incomplete")
    if arm == "b0":
        if scorer_checkpoint is not None or scorer_variant is not None:
            raise RuntimeError("B0 must not declare a scorer checkpoint or variant")
    else:
        if scorer_checkpoint is None:
            raise RuntimeError(f"{arm} requires a scorer checkpoint")
        variant = scorer_variant or arm
        if variant not in SCORER_VARIANTS or VARIANT_ARM[variant] != arm:
            raise RuntimeError(f"scorer variant {variant!r} is incompatible with {arm}")
        try:
            expected = hashes[variant][str(seed)]
        except (KeyError, TypeError) as error:
            raise RuntimeError(
                f"authorization lacks {task}/{arm}/seed-{seed} scorer hash"
            ) from error
        actual = sha256_file(scorer_checkpoint)
        if expected != actual:
            raise RuntimeError(
                f"authorized scorer hash differs for {task}/{arm}/seed-{seed}"
            )
    return {
        "status": "pass",
        "task": task,
        "arm": arm,
        "seed": seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--task", choices=tuple(TASKS), required=True)
    parser.add_argument("--arm", choices=tuple(sorted(ARMS)), required=True)
    parser.add_argument("--seed", type=int, choices=tuple(sorted(SEEDS)), required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--analysis-manifest", type=Path, required=True)
    parser.add_argument("--orchestration-manifest", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--identification-manifest", type=Path, required=True)
    parser.add_argument("--identification-summary", type=Path, required=True)
    parser.add_argument("--scorer-checkpoint", type=Path)
    parser.add_argument("--scorer-variant", choices=tuple(sorted(SCORER_VARIANTS)))
    args = parser.parse_args()
    for path in (
        args.authorization,
        args.source_manifest,
        args.analysis_manifest,
        args.orchestration_manifest,
        args.eval_manifest,
        args.world_model_checkpoint,
        args.identification_manifest,
        args.identification_summary,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    payload = json.loads(args.authorization.read_text(encoding="utf-8"))
    result = verify(
        payload,
        task=args.task,
        arm=args.arm,
        seed=args.seed,
        source_manifest=args.source_manifest,
        analysis_manifest=args.analysis_manifest,
        orchestration_manifest=args.orchestration_manifest,
        eval_manifest=args.eval_manifest,
        world_model_checkpoint=args.world_model_checkpoint,
        identification_manifest=args.identification_manifest,
        identification_summary=args.identification_summary,
        scorer_checkpoint=args.scorer_checkpoint,
        scorer_variant=args.scorer_variant,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
