#!/usr/bin/env python3
"""Apply the frozen per-task B0/native-ACID reproduction gate."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.task_registry import TASKS, get_task_spec


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=tuple(TASKS), required=True)
    parser.add_argument("--b0-summary", type=Path, required=True)
    parser.add_argument("--acid-summary", type=Path, action="append", required=True)
    parser.add_argument(
        "--acid-training-summary", type=Path, action="append", required=True
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.acid_summary) != 3 or len(args.acid_training_summary) != 3:
        raise ValueError("R0 gate requires exactly three A1 evaluation/training runs")
    for path in (
        args.b0_summary,
        args.source_manifest,
        *args.acid_summary,
        *args.acid_training_summary,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output.exists():
        raise SystemExit("refusing existing gate output")

    spec = get_task_spec(args.task)
    b0 = read_json(args.b0_summary)
    evaluations = [read_json(path) for path in args.acid_summary]
    trainings = [read_json(path) for path in args.acid_training_summary]
    errors: list[str] = []
    if b0.get("status") != "ok" or b0.get("arm") != "b0":
        errors.append("invalid B0 evaluation")
    if b0.get("episode_count") != 50 or b0.get("planner_seed") != 42:
        errors.append("B0 does not use the frozen 50-start seed-42 R0")
    b0_rate = b0.get("success_rate_fraction")
    if not finite(b0_rate):
        errors.append("B0 rate is non-finite")
        b0_rate = float("nan")
    shared = {
        key: b0.get(key)
        for key in (
            "eval_manifest_sha256",
            "dataset_sha256",
            "world_model_checkpoint_sha256",
        )
    }
    training_by_seed = {run.get("seed"): run for run in trainings}
    if set(training_by_seed) != {6101, 6102, 6103}:
        errors.append("A1 training seeds differ from 6101/6102/6103")
    acid_rates: list[float] = []
    accuracies: list[float] = []
    records: list[dict[str, Any]] = []
    for path, run in zip(args.acid_summary, evaluations):
        seed = run.get("scorer_training_seed")
        training = training_by_seed.get(seed)
        if run.get("status") != "ok" or run.get("arm") != "acid":
            errors.append(f"{path}: invalid A1 evaluation")
        if run.get("episode_count") != 50 or run.get("planner_seed") != 42:
            errors.append(f"{path}: A1 R0 namespace mismatch")
        if any(run.get(key) != value for key, value in shared.items()):
            errors.append(f"{path}: A1 matched input differs from B0")
        rate = run.get("success_rate_fraction")
        if finite(rate):
            acid_rates.append(float(rate))
        else:
            errors.append(f"{path}: non-finite A1 rate")
        accuracy = None
        loss = None
        if training is None:
            errors.append(f"{path}: missing matching A1 training summary")
        else:
            if training.get("status") != "ok" or training.get("model") != "acid":
                errors.append(f"seed {seed}: invalid A1 training summary")
            if training.get("condition") != "true":
                errors.append(f"seed {seed}: A1 condition is not true")
            loss = training.get("best_validation_loss")
            accuracy = (training.get("final_validation") or {}).get(
                "correct_action_pairwise_accuracy"
            )
            if not finite(loss):
                errors.append(f"seed {seed}: non-finite A1 validation loss")
            if finite(accuracy):
                accuracies.append(float(accuracy))
            else:
                errors.append(f"seed {seed}: non-finite A1 action recovery")
        records.append(
            {
                "training_seed": seed,
                "success_rate_fraction": rate,
                "best_validation_loss": loss,
                "correct_action_pairwise_accuracy": accuracy,
                "evaluation_summary": str(path),
                "evaluation_summary_sha256": sha256_file(path),
            }
        )
    b0_reproduction = (
        finite(b0_rate)
        and abs(float(b0_rate) - spec.published_lewm_b0) <= 0.10 + 1.0e-12
    )
    action_recovery = len(accuracies) == 3 and all(value > 0.5 for value in accuracies)
    mean_acid = float(sum(acid_rates) / len(acid_rates)) if acid_rates else float("nan")
    direction = len(acid_rates) == 3 and mean_acid >= float(b0_rate)
    integrity = not errors
    passed = integrity and b0_reproduction and action_recovery and direction
    payload = {
        "status": "pass" if passed else "fail",
        "kind": "task_r0_b0_native_acid_reproduction_gate",
        "task": args.task,
        "frozen_definition": {
            "published_lewm_b0": spec.published_lewm_b0,
            "published_acid": spec.published_acid,
            "b0_absolute_tolerance": 0.10,
            "acid_pairwise_accuracy_exclusive_minimum": 0.5,
            "acid_direction_rule": "mean native-A1 success >= matched B0 success",
            "expected_episodes": 50,
            "planner_seed": 42,
        },
        "b0": {"summary": str(args.b0_summary), "rate": b0_rate},
        "acid": records,
        "mean_acid_rate": mean_acid,
        "mean_acid_minus_b0": mean_acid - float(b0_rate),
        "gates": {
            "integrity": integrity,
            "b0_reproduction": b0_reproduction,
            "acid_correct_action_recovery": action_recovery,
            "acid_reported_gain_direction": direction,
        },
        "errors": errors,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
    }
    atomic_write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(4)


if __name__ == "__main__":
    main()
