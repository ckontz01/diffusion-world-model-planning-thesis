#!/usr/bin/env python3
"""Analyze fixed-configuration E10M multiseed P1 replication."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

import evaluate_gdp_cem_e10m_p1 as e10m


TASKS = e10m.TASKS
SEEDS = e10m.SEEDS
CONDITIONS = (
    "vp_true",
    "vp_shuffled_goal",
    "vp_true_unconditional",
    "gaussian_true",
)
METRICS = (
    "selected_action_mse",
    "oracle_action_mse",
    "minimum_goal_cost",
    "candidate_variance",
    "unique_candidates",
    "boundary_fraction",
    "generation_seconds",
    "rollout_seconds",
)
EXPECTED_WORLD_MODELS = {
    "pusht": "c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659",
    "reacher": "6b03b0e39f00a601b83dc94765e4b022c48127ced762543bddb1398ce52c310d",
    "cube": "5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def labels() -> set[str]:
    return {
        f"seed{seed}_{condition}" for seed in SEEDS for condition in CONDITIONS
    }


def validate_model_records(records: dict[str, Any]) -> None:
    if set(records) != {str(seed) for seed in SEEDS}:
        raise RuntimeError("E10M model seed-record set differs")
    for seed in SEEDS:
        seed_records = records[str(seed)]
        if set(seed_records) != {"vp_true", "vp_shuffled_goal", "gaussian_true"}:
            raise RuntimeError("E10M model condition-record set differs")
        for record in seed_records.values():
            summary = Path(record.get("summary", ""))
            checkpoint = Path(record.get("checkpoint", ""))
            e10m.train.e10v.reject_protected_path(summary)
            e10m.train.e10v.reject_protected_path(checkpoint)
            if (
                not summary.is_file()
                or not checkpoint.is_file()
                or sha256_file(summary) != record.get("summary_sha256")
                or sha256_file(checkpoint) != record.get("checkpoint_sha256")
            ):
                raise RuntimeError("E10M model-record artifact differs")


def load_task(
    task: str, path: Path, *, source_manifest_sha256: str
) -> dict[str, Any]:
    e10m.train.e10v.reject_protected_path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    detail = Path(value.get("per_context", ""))
    e10m.train.e10v.reject_protected_path(detail)
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e10m_p1_multiseed_task_evaluation"
        or value.get("analysis_role") != "fixed_configuration_multiseed_P1_replication"
        or value.get("task") != task
        or value.get("model_seeds") != list(SEEDS)
        or value.get("context_count") != e10m.CONTEXT_COUNT
        or value.get("candidate_count") != e10m.CANDIDATE_COUNT
        or value.get("reverse_evaluations") != e10m.REVERSE_EVALUATIONS
        or value.get("guidance_scale") != e10m.GUIDANCE_SCALE
        or value.get("e10v_aggregate_sha256") != e10m.E10V_AGGREGATE_SHA256
        or value.get("protocol_sha256") != e10m.PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != source_manifest_sha256
        or value.get("world_model_checkpoint_sha256")
        != EXPECTED_WORLD_MODELS[task]
        or value.get("determinism_preflight", {}).get("status") != "ok"
        or value.get("determinism_preflight", {}).get("repeat_max_abs") != 0.0
        or value.get("real_stack_equivalence", {}).get("status") != "ok"
        or value.get("d2_read") is not False
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
        or not detail.is_file()
        or sha256_file(detail) != value.get("per_context_sha256")
    ):
        raise RuntimeError("E10M task summary differs")
    validate_model_records(value.get("models", {}))
    expected_labels = labels()
    records: dict[str, list[dict[str, float]]] = {
        label: [] for label in expected_labels
    }
    rows_by_ordinal: dict[int, int] = {}
    seen: set[tuple[int, str]] = set()
    with detail.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            ordinal = item.get("ordinal")
            row = item.get("row")
            label = item.get("label")
            if (
                not isinstance(ordinal, int)
                or not 0 <= ordinal < e10m.CONTEXT_COUNT
                or not isinstance(row, int)
                or label not in expected_labels
                or (ordinal, label) in seen
                or any(
                    key not in item or not math.isfinite(float(item[key]))
                    for key in METRICS
                )
                or float(item["candidate_variance"]) < 0.0
                or not 1.0 <= float(item["unique_candidates"]) <= 300.0
                or not 0.0 <= float(item["boundary_fraction"]) <= 1.0
            ):
                raise RuntimeError("E10M per-context record differs")
            if ordinal in rows_by_ordinal and rows_by_ordinal[ordinal] != row:
                raise RuntimeError("E10M row pairing differs")
            rows_by_ordinal[ordinal] = row
            seen.add((ordinal, label))
            records[label].append({key: float(item[key]) for key in METRICS})
    if (
        len(rows_by_ordinal) != e10m.CONTEXT_COUNT
        or any(len(records[label]) != e10m.CONTEXT_COUNT for label in expected_labels)
        or len(seen) != len(expected_labels) * e10m.CONTEXT_COUNT
    ):
        raise RuntimeError("E10M per-context grid is incomplete")
    medians = {
        label: {
            metric: float(np.median([record[metric] for record in values]))
            for metric in METRICS
        }
        for label, values in records.items()
    }
    reported = value.get("per_task_medians", {})
    if set(reported) != expected_labels:
        raise RuntimeError("E10M reported label set differs")
    for label in expected_labels:
        for metric in METRICS:
            if not math.isclose(
                medians[label][metric],
                float(reported[label][metric]),
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise RuntimeError("E10M reported median differs")
    return {
        "summary": str(path),
        "summary_sha256": sha256_file(path),
        "medians": medians,
        "rows": [rows_by_ordinal[index] for index in range(e10m.CONTEXT_COUNT)],
        "confirmation_rows_sha256": value["confirmation_rows_sha256"],
        "elapsed_seconds": float(value["elapsed_seconds"]),
        "peak_cuda_memory_allocated_bytes": int(
            value["peak_cuda_memory_allocated_bytes"]
        ),
    }


def seed_record(tasks: dict[str, dict[str, Any]], seed: int) -> dict[str, Any]:
    names = {
        "true": f"seed{seed}_vp_true",
        "shuffled": f"seed{seed}_vp_shuffled_goal",
        "unconditional": f"seed{seed}_vp_true_unconditional",
        "gaussian": f"seed{seed}_gaussian_true",
    }
    per_task = {
        task: {
            name: {
                metric: tasks[task]["medians"][label][metric]
                for metric in METRICS
            }
            for name, label in names.items()
        }
        for task in TASKS
    }
    equal = {
        name: {
            metric: float(
                np.mean([per_task[task][name][metric] for task in TASKS])
            )
            for metric in METRICS
        }
        for name in names
    }
    selected_wins = sum(
        per_task[task]["true"]["selected_action_mse"]
        < per_task[task]["shuffled"]["selected_action_mse"]
        and per_task[task]["true"]["selected_action_mse"]
        < per_task[task]["gaussian"]["selected_action_mse"]
        for task in TASKS
    )
    goal_wins = sum(
        per_task[task]["true"]["minimum_goal_cost"]
        < per_task[task]["shuffled"]["minimum_goal_cost"]
        and per_task[task]["true"]["minimum_goal_cost"]
        < per_task[task]["gaussian"]["minimum_goal_cost"]
        for task in TASKS
    )
    gates = {
        "1_selected_better_shuffled_gaussian": all(
            equal["true"]["selected_action_mse"]
            < equal[control]["selected_action_mse"]
            for control in ("shuffled", "gaussian")
        ),
        "2_oracle_better_shuffled_gaussian": all(
            equal["true"]["oracle_action_mse"]
            < equal[control]["oracle_action_mse"]
            for control in ("shuffled", "gaussian")
        ),
        "3_goal_better_shuffled_gaussian": all(
            equal["true"]["minimum_goal_cost"]
            < equal[control]["minimum_goal_cost"]
            for control in ("shuffled", "gaussian")
        ),
        "4_better_same_model_unconditional": (
            equal["true"]["selected_action_mse"]
            < equal["unconditional"]["selected_action_mse"]
            and equal["true"]["minimum_goal_cost"]
            < equal["unconditional"]["minimum_goal_cost"]
        ),
        "5_selected_wins_at_least_two_tasks": selected_wins >= 2,
        "6_goal_wins_at_least_two_tasks": goal_wins >= 2,
        "7_diversity_variance_boundary": all(
            per_task[task]["true"]["candidate_variance"] > 0.0
            and per_task[task]["true"]["unique_candidates"] >= 285.0
            and per_task[task]["true"]["boundary_fraction"]
            <= per_task[task]["gaussian"]["boundary_fraction"] + 0.05
            for task in TASKS
        ),
    }
    return {
        "seed": seed,
        "equal_task_metrics": equal,
        "per_task_metrics": per_task,
        "selected_task_wins": selected_wins,
        "goal_task_wins": goal_wins,
        "gates": gates,
        "seed_pass": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--task-summary", nargs=2, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.protocol, args.source_manifest, args.output_dir):
        e10m.train.e10v.reject_protected_path(path)
    if (
        sha256_file(args.protocol) != e10m.PROTOCOL_SHA256
        or not args.source_manifest.is_file()
    ):
        raise RuntimeError("E10M analysis prerequisite differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E10M analysis output")
    paths = {task: Path(path) for task, path in args.task_summary}
    if set(paths) != set(TASKS) or len(args.task_summary) != len(TASKS):
        raise RuntimeError("E10M requires exactly three task summaries")
    source_hash = sha256_file(args.source_manifest)
    tasks = {
        task: load_task(task, paths[task], source_manifest_sha256=source_hash)
        for task in TASKS
    }
    if len({tasks[task]["confirmation_rows_sha256"] for task in TASKS}) != 3:
        # Row hashes should differ across tasks; equality would indicate an
        # accidental cross-task manifest reuse.
        raise RuntimeError("E10M cross-task confirmation row hashes are not distinct")
    seeds = {seed: seed_record(tasks, seed) for seed in SEEDS}
    controls = ("shuffled", "gaussian", "unconditional")
    contrast_metrics = (
        "selected_action_mse",
        "oracle_action_mse",
        "minimum_goal_cost",
    )
    equal_seed_contrasts = {
        f"true_minus_{control}": {
            metric: float(
                np.mean(
                    [
                        seeds[seed]["equal_task_metrics"]["true"][metric]
                        - seeds[seed]["equal_task_metrics"][control][metric]
                        for seed in SEEDS
                    ]
                )
            )
            for metric in contrast_metrics
        }
        for control in controls
    }
    equal_seed_mean_contrast_signs_pass = all(
        record["selected_action_mse"] < 0.0
        and record["minimum_goal_cost"] < 0.0
        and (control == "unconditional" or record["oracle_action_mse"] < 0.0)
        for control, record in (
            (name.removeprefix("true_minus_"), value)
            for name, value in equal_seed_contrasts.items()
        )
    )
    per_seed_contrast_signs_pass = all(
        seeds[seed]["equal_task_metrics"]["true"]["selected_action_mse"]
        < seeds[seed]["equal_task_metrics"][control]["selected_action_mse"]
        and seeds[seed]["equal_task_metrics"]["true"]["minimum_goal_cost"]
        < seeds[seed]["equal_task_metrics"][control]["minimum_goal_cost"]
        and (
            control == "unconditional"
            or seeds[seed]["equal_task_metrics"]["true"]["oracle_action_mse"]
            < seeds[seed]["equal_task_metrics"][control]["oracle_action_mse"]
        )
        for seed in SEEDS
        for control in controls
    )
    integrity = True
    replication_pass = (
        all(record["seed_pass"] for record in seeds.values())
        and per_seed_contrast_signs_pass
        and equal_seed_mean_contrast_signs_pass
        and integrity
    )
    decision = (
        "authorize_writing_separately_frozen_untouched_data_protocol"
        if replication_pass
        else "stop_fixed_pure_velocity_configuration_before_protected_data"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "ok",
        "kind": "gdp_cem_e10m_p1_multiseed_aggregate",
        "analysis_role": "fixed_configuration_multiseed_P1_replication",
        "fixed_configuration": {
            "reverse_evaluations": e10m.REVERSE_EVALUATIONS,
            "guidance_scale": e10m.GUIDANCE_SCALE,
            "candidate_count": e10m.CANDIDATE_COUNT,
        },
        "seed_results": {str(seed): seeds[seed] for seed in SEEDS},
        "equal_seed_contrasts": equal_seed_contrasts,
        "all_seed_gates_pass": all(
            record["seed_pass"] for record in seeds.values()
        ),
        "per_seed_contrast_signs_pass": per_seed_contrast_signs_pass,
        "equal_seed_mean_contrast_signs_pass": equal_seed_mean_contrast_signs_pass,
        "integrity_pass": integrity,
        "e10m_replication_pass": replication_pass,
        "decision": decision,
        "task_summaries": {
            task: {
                "path": tasks[task]["summary"],
                "sha256": tasks[task]["summary_sha256"],
                "confirmation_rows_sha256": tasks[task][
                    "confirmation_rows_sha256"
                ],
                "elapsed_seconds": tasks[task]["elapsed_seconds"],
                "peak_cuda_memory_allocated_bytes": tasks[task][
                    "peak_cuda_memory_allocated_bytes"
                ],
            }
            for task in TASKS
        },
        "e10v_aggregate_sha256": e10m.E10V_AGGREGATE_SHA256,
        "protocol_sha256": e10m.PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "d2_read": False,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_dir / "summary.json", result)
    manifest = {
        "status": "ok",
        "kind": "gdp_cem_e10m_p1_multiseed_manifest",
        "summary_sha256": sha256_file(args.output_dir / "summary.json"),
        "protocol_sha256": e10m.PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "d2_read": False,
        "d3_read": False,
        "protected_c1_i1_read": False,
    }
    atomic_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
