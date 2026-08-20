#!/usr/bin/env python3
"""Aggregate the preregistered PushT R0 B0/native-ACID reproduction gate."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"expected a JSON object: {path}")
    return value


def read_episodes(path: Path) -> dict[tuple[int, int, int], int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"eval_index", "episode_id", "start_step", "success"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"invalid episode table: {path}")
    result: dict[tuple[int, int, int], int] = {}
    for row in rows:
        key = (int(row["eval_index"]), int(row["episode_id"]), int(row["start_step"]))
        success = int(row["success"])
        if success not in (0, 1):
            raise ValueError(f"non-binary success in {path}")
        if key in result:
            raise ValueError(f"duplicate evaluation key in {path}: {key}")
        result[key] = success
    return result


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b0-summary", type=Path, required=True)
    parser.add_argument("--acid-summary", type=Path, action="append", required=True)
    parser.add_argument(
        "--acid-training-summary", type=Path, action="append", required=True
    )
    parser.add_argument("--minimum-b0-rate", type=float, default=0.86)
    parser.add_argument("--expected-episodes", type=int, default=50)
    parser.add_argument("--expected-planner-seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if len(args.acid_summary) != 3 or len(args.acid_training_summary) != 3:
        raise ValueError(
            "R0 gate requires exactly three ACID runs and training summaries"
        )
    if args.output.exists():
        raise SystemExit(f"refusing existing output: {args.output}")

    b0 = read_json(args.b0_summary)
    acid_runs = [read_json(path) for path in args.acid_summary]
    training_runs = [read_json(path) for path in args.acid_training_summary]
    errors: list[str] = []

    if b0.get("status") != "ok" or b0.get("arm") != "b0":
        errors.append("B0 summary is not a successful B0 evaluation")
    if b0.get("episode_count") != args.expected_episodes:
        errors.append("B0 episode count differs from the frozen R0 count")
    if b0.get("planner_seed") != args.expected_planner_seed:
        errors.append("B0 planner seed differs from the frozen R0 seed")
    b0_rate = b0.get("success_rate_fraction")
    if not finite_number(b0_rate):
        errors.append("B0 success rate is non-finite or missing")
        b0_rate = float("nan")

    b0_episodes_path = Path(str(b0.get("episode_tsv", "")))
    if not b0_episodes_path.is_file():
        errors.append("B0 episode table is missing")
        b0_episodes: dict[tuple[int, int, int], int] = {}
    else:
        b0_episodes = read_episodes(b0_episodes_path)

    expected_shared = {
        "eval_manifest_sha256": b0.get("eval_manifest_sha256"),
        "dataset_sha256": b0.get("dataset_sha256"),
        "world_model_checkpoint_sha256": b0.get("world_model_checkpoint_sha256"),
    }
    training_by_seed = {run.get("seed"): run for run in training_runs}
    if len(training_by_seed) != 3 or None in training_by_seed:
        errors.append("ACID training summaries do not contain three distinct seeds")

    acid_records: list[dict[str, Any]] = []
    acid_rates: list[float] = []
    pairwise_accuracies: list[float] = []
    for path, run in zip(args.acid_summary, acid_runs):
        seed = run.get("scorer_training_seed")
        training = training_by_seed.get(seed)
        record: dict[str, Any] = {
            "evaluation_summary": str(path),
            "training_seed": seed,
            "success_rate_fraction": run.get("success_rate_fraction"),
        }
        if run.get("status") != "ok" or run.get("arm") != "acid":
            errors.append(f"{path}: not a successful native-ACID evaluation")
        if run.get("episode_count") != args.expected_episodes:
            errors.append(f"{path}: episode count differs from R0")
        if run.get("planner_seed") != args.expected_planner_seed:
            errors.append(f"{path}: planner seed differs from B0")
        for key, expected in expected_shared.items():
            if run.get(key) != expected:
                errors.append(f"{path}: {key} differs from B0")
        rate = run.get("success_rate_fraction")
        if not finite_number(rate):
            errors.append(f"{path}: success rate is non-finite or missing")
        else:
            acid_rates.append(float(rate))

        episodes_path = Path(str(run.get("episode_tsv", "")))
        if not episodes_path.is_file():
            errors.append(f"{path}: episode table is missing")
        else:
            episodes = read_episodes(episodes_path)
            if episodes.keys() != b0_episodes.keys():
                errors.append(f"{path}: episode identities differ from B0")
            else:
                deltas = [episodes[key] - b0_episodes[key] for key in b0_episodes]
                record.update(
                    paired_wins=sum(delta == 1 for delta in deltas),
                    paired_losses=sum(delta == -1 for delta in deltas),
                    paired_ties=sum(delta == 0 for delta in deltas),
                    paired_success_difference=sum(deltas) / len(deltas),
                )

        if training is None:
            errors.append(f"{path}: no matching training summary for seed {seed}")
        else:
            if training.get("status") != "ok" or training.get("model") != "acid":
                errors.append(f"seed {seed}: invalid ACID training summary")
            if training.get("condition") != "true":
                errors.append(f"seed {seed}: ACID checkpoint is not true-condition")
            loss = training.get("best_validation_loss")
            accuracy = (training.get("final_validation") or {}).get(
                "correct_action_pairwise_accuracy"
            )
            record.update(
                best_validation_loss=loss,
                correct_action_pairwise_accuracy=accuracy,
                training_summary=str(
                    args.acid_training_summary[training_runs.index(training)]
                ),
            )
            if not finite_number(loss):
                errors.append(f"seed {seed}: validation loss is non-finite")
            if not finite_number(accuracy):
                errors.append(f"seed {seed}: pairwise accuracy is non-finite")
            else:
                pairwise_accuracies.append(float(accuracy))
        acid_records.append(record)

    b0_gate = finite_number(b0_rate) and float(b0_rate) >= args.minimum_b0_rate
    action_gate = len(pairwise_accuracies) == 3 and all(
        accuracy > 0.5 for accuracy in pairwise_accuracies
    )
    mean_acid_rate = sum(acid_rates) / len(acid_rates) if acid_rates else float("nan")
    direction_gate = len(acid_rates) == 3 and mean_acid_rate >= float(b0_rate)
    integrity_gate = not errors
    passed = integrity_gate and b0_gate and action_gate and direction_gate

    payload = {
        "status": "pass" if passed else "fail",
        "kind": "pusht_r0_b0_native_acid_reproduction_gate",
        "frozen_gate_definition": {
            "minimum_b0_rate": args.minimum_b0_rate,
            "minimum_acid_pairwise_accuracy_exclusive": 0.5,
            "acid_direction_rule": "mean native-ACID success >= matched B0 success",
            "expected_episodes": args.expected_episodes,
            "expected_planner_seed": args.expected_planner_seed,
        },
        "b0": {
            "summary": str(args.b0_summary),
            "success_rate_fraction": b0_rate,
        },
        "acid": acid_records,
        "mean_acid_success_rate_fraction": mean_acid_rate,
        "mean_acid_minus_b0": mean_acid_rate - float(b0_rate),
        "gates": {
            "integrity": integrity_gate,
            "b0_reproduction": b0_gate,
            "acid_correct_action_recovery": action_gate,
            "acid_reported_gain_direction": direction_gate,
        },
        "errors": errors,
    }
    atomic_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(4)


if __name__ == "__main__":
    main()
