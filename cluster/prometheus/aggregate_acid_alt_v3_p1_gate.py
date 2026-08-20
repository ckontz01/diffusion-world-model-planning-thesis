#!/usr/bin/env python3
"""Aggregate the frozen three-seed P1 mechanism gate before D2 is touched."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import acid_alt_d2_models as d2


TASKS = ("pusht", "reacher", "cube")
CONDITIONS = ("true", "shuffled_action")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument(
        "--entry",
        nargs=4,
        action="append",
        metavar=("TASK", "CONDITION", "SEED", "SUMMARY"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.protocol, args.source_manifest):
        if not path.is_file():
            raise FileNotFoundError(path)
    if d2.sha256_file(args.protocol) != d2.PROTOCOL_SHA256:
        raise RuntimeError("D2 protocol hash mismatch")
    if args.output.exists():
        raise SystemExit("refusing to overwrite P1 gate")

    entries: dict[tuple[str, str, int], tuple[Path, dict[str, Any]]] = {}
    for task, condition, seed_text, path_text in args.entry:
        seed = int(seed_text)
        path = Path(path_text)
        key = (task, condition, seed)
        if task not in TASKS or condition not in CONDITIONS or seed not in d2.SEEDS:
            raise ValueError(f"invalid P1 gate identity: {key}")
        if key in entries:
            raise ValueError(f"duplicate P1 gate identity: {key}")
        summary = d2.load_training_summary(path)
        expected_kind = (
            "residual_diffusion_x0_pilot_training"
            if seed == 6101
            else "residual_diffusion_x0_multiseed_d2_training"
        )
        expected_protocol = d2.V2_PROTOCOL_SHA256 if seed == 6101 else d2.PROTOCOL_SHA256
        checkpoint = Path(summary.get("checkpoint", ""))
        validation = Path(summary.get("validation_examples", ""))
        if (
            summary.get("kind") != expected_kind
            or summary.get("condition") != condition
            or int(summary.get("seed", -1)) != seed
            or summary.get("protocol_sha256") != expected_protocol
            or summary.get("confirmation_data_read") is not False
            or not checkpoint.is_file()
            or d2.sha256_file(checkpoint) != summary.get("checkpoint_sha256")
            or not validation.is_file()
            or d2.sha256_file(validation) != summary.get("validation_examples_sha256")
        ):
            raise RuntimeError(f"invalid P1 training artifact: {path}")
        entries[key] = (path, summary)
    expected = {
        (task, condition, seed)
        for task in TASKS
        for condition in CONDITIONS
        for seed in d2.SEEDS
    }
    if set(entries) != expected:
        raise RuntimeError("P1 gate does not contain the exact 18 training artifacts")

    records: list[dict[str, Any]] = []
    all_pass = True
    for task in TASKS:
        for seed in d2.SEEDS:
            true_path, true = entries[(task, "true", seed)]
            shuffled_path, shuffled = entries[(task, "shuffled_action", seed)]
            if (
                true.get("transition_h5_sha256") != shuffled.get("transition_h5_sha256")
                or true.get("latent_h5_sha256") != shuffled.get("latent_h5_sha256")
            ):
                raise RuntimeError(f"{task}/seed-{seed}: true/shuffled training lineage differs")
            true_validation = true["final_validation"]
            shuffled_validation = shuffled["final_validation"]
            accuracy = float(true_validation["diagnostic_true_action_pairwise_accuracy"])
            shuffled_accuracy = float(
                shuffled_validation["diagnostic_true_action_pairwise_accuracy"]
            )
            margin = float(true_validation["diagnostic_wrong_minus_true_margin"])
            sigma4 = float(
                true_validation["by_sigma"]["4.0"]["true_action_pairwise_accuracy"]
            )
            checks = {
                "accuracy_at_least_0_70": accuracy >= 0.70,
                "sigma4_accuracy_at_least_0_75": sigma4 >= 0.75,
                "positive_wrong_minus_true_margin": margin > 0.0,
                "accuracy_advantage_at_least_0_10": accuracy - shuffled_accuracy >= 0.10,
            }
            passed = all(checks.values())
            all_pass = all_pass and passed
            records.append(
                {
                    "task": task,
                    "seed": seed,
                    "true_accuracy": accuracy,
                    "shuffled_accuracy": shuffled_accuracy,
                    "accuracy_advantage": accuracy - shuffled_accuracy,
                    "sigma4_accuracy": sigma4,
                    "wrong_minus_true_margin": margin,
                    "checks": checks,
                    "pass": passed,
                    "true_summary": str(true_path),
                    "true_summary_sha256": d2.sha256_file(true_path),
                    "shuffled_summary": str(shuffled_path),
                    "shuffled_summary_sha256": d2.sha256_file(shuffled_path),
                    "transition_h5_sha256": true["transition_h5_sha256"],
                    "latent_h5_sha256": true["latent_h5_sha256"],
                }
            )
    result = {
        "status": "ok",
        "kind": "acid_alt_v3_multiseed_p1_gate",
        "analysis_role": "P1 only; before D2 outcome generation",
        "all_pass": all_pass,
        "decision": "authorize_D2" if all_pass else "stop_before_D2",
        "records": records,
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "protected_c1_i1_read": False,
    }
    atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not all_pass:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
