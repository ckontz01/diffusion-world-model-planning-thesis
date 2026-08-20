#!/usr/bin/env python3
"""Analyze the frozen E10V pure velocity-diffusion P1 study."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

import evaluate_gdp_cem_e10v_p1 as e10


TASKS = e10.TASKS
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


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d2", "d3", "c1", "i1"}):
        raise RuntimeError(f"E10V protected path is forbidden: {path}")


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


def expected_labels() -> set[str]:
    labels = {
        f"{condition}_k{steps:02d}_{e10.scale_label(scale)}"
        for condition in e10.VP_CONDITIONS
        for steps in e10.REVERSE_STEPS
        for scale in e10.GUIDANCE_SCALES
    }
    labels.update(("epsilon_true_k10", "epsilon_shuffled_k10", "gaussian_true"))
    return labels


def validate_model_records(records: dict[str, Any]) -> None:
    for record in records.values():
        summary = Path(record.get("summary", ""))
        checkpoint = Path(record.get("checkpoint", ""))
        reject_protected_path(summary)
        reject_protected_path(checkpoint)
        if (
            not summary.is_file()
            or not checkpoint.is_file()
            or sha256_file(summary) != record.get("summary_sha256")
            or sha256_file(checkpoint) != record.get("checkpoint_sha256")
        ):
            raise RuntimeError("E10V model lineage artifact differs")


def load_task(
    task: str, path: Path, *, source_manifest_sha256: str
) -> dict[str, Any]:
    reject_protected_path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    detail = Path(value.get("per_context", ""))
    reject_protected_path(detail)
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e10v_p1_velocity_task_evaluation"
        or value.get("analysis_role")
        != "post_E8D_P1_only_pure_diffusion_development"
        or value.get("task") != task
        or value.get("context_count") != e10.CONTEXT_COUNT
        or value.get("candidate_count") != e10.CANDIDATE_COUNT
        or value.get("reverse_steps") != list(e10.REVERSE_STEPS)
        or value.get("guidance_scales") != list(e10.GUIDANCE_SCALES)
        or value.get("protocol_sha256") != e10.PROTOCOL_SHA256
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
        raise RuntimeError(f"E10V task summary differs: {path}")
    if (
        set(value.get("velocity_models", {})) != set(e10.VP_CONDITIONS)
        or set(value.get("e7_controls", {})) != set(e10.e7.CONDITIONS)
    ):
        raise RuntimeError("E10V model-record set differs")
    validate_model_records(value["velocity_models"])
    validate_model_records(value["e7_controls"])
    labels = expected_labels()
    records: dict[str, list[dict[str, float]]] = {label: [] for label in labels}
    seen_pairs: set[tuple[int, str]] = set()
    row_by_ordinal: dict[int, int] = {}
    with detail.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            label = item.get("label")
            ordinal = item.get("ordinal")
            row = item.get("row")
            if (
                label not in labels
                or not isinstance(ordinal, int)
                or not 0 <= ordinal < e10.CONTEXT_COUNT
                or not isinstance(row, int)
                or (ordinal, label) in seen_pairs
                or any(
                    key not in item or not math.isfinite(float(item[key]))
                    for key in METRICS
                )
                or not 0.0 <= float(item["boundary_fraction"]) <= 1.0
                or not 1.0 <= float(item["unique_candidates"]) <= 300.0
                or float(item["candidate_variance"]) < 0.0
                or float(item["generation_seconds"]) < 0.0
                or float(item["rollout_seconds"]) < 0.0
            ):
                raise RuntimeError("E10V per-context record differs")
            if ordinal in row_by_ordinal and row_by_ordinal[ordinal] != row:
                raise RuntimeError("E10V row pairing differs across labels")
            row_by_ordinal[ordinal] = row
            seen_pairs.add((ordinal, label))
            records[label].append({key: float(item[key]) for key in METRICS})
    if (
        len(row_by_ordinal) != e10.CONTEXT_COUNT
        or set(row_by_ordinal) != set(range(e10.CONTEXT_COUNT))
        or any(len(records[label]) != e10.CONTEXT_COUNT for label in labels)
        or len(seen_pairs) != len(labels) * e10.CONTEXT_COUNT
    ):
        raise RuntimeError("E10V per-context grid is incomplete")
    recomputed = {
        label: {
            metric: float(np.median([record[metric] for record in rows]))
            for metric in METRICS
        }
        for label, rows in records.items()
    }
    reported = value.get("per_task_medians", {})
    if set(reported) != labels:
        raise RuntimeError("E10V reported label set differs")
    for label in labels:
        for metric in METRICS:
            if not math.isclose(
                recomputed[label][metric],
                float(reported[label][metric]),
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise RuntimeError("E10V reported median differs")
    return {
        "summary": str(path),
        "summary_sha256": sha256_file(path),
        "medians": recomputed,
        "rows": [row_by_ordinal[index] for index in range(e10.CONTEXT_COUNT)],
        "final_rows_sha256": value["final_rows_sha256"],
        "row_selection": value["row_selection"],
        "elapsed_seconds": float(value["elapsed_seconds"]),
        "peak_cuda_memory_allocated_bytes": int(
            value["peak_cuda_memory_allocated_bytes"]
        ),
    }


def equal_task(
    tasks: dict[str, dict[str, Any]], label: str, metric: str
) -> float:
    return float(np.mean([tasks[task]["medians"][label][metric] for task in TASKS]))


def configuration_record(
    tasks: dict[str, dict[str, Any]], *, steps: int, scale: float
) -> dict[str, Any]:
    true_label = f"vp_true_k{steps:02d}_{e10.scale_label(scale)}"
    shuffled_label = f"vp_shuffled_goal_k{steps:02d}_{e10.scale_label(scale)}"
    unconditional_label = f"vp_true_k{steps:02d}_{e10.scale_label(0.0)}"
    controls = {
        "true": true_label,
        "shuffled": shuffled_label,
        "unconditional": unconditional_label,
        "gaussian": "gaussian_true",
        "epsilon_true": "epsilon_true_k10",
        "epsilon_shuffled": "epsilon_shuffled_k10",
    }
    aggregates = {
        name: {
            metric: equal_task(tasks, label, metric) for metric in METRICS
        }
        for name, label in controls.items()
    }
    task_values = {
        task: {
            name: {
                metric: tasks[task]["medians"][label][metric]
                for metric in METRICS
            }
            for name, label in controls.items()
        }
        for task in TASKS
    }
    selected_task_wins = sum(
        task_values[task]["true"]["selected_action_mse"]
        < task_values[task]["shuffled"]["selected_action_mse"]
        and task_values[task]["true"]["selected_action_mse"]
        < task_values[task]["gaussian"]["selected_action_mse"]
        for task in TASKS
    )
    goal_task_wins = sum(
        task_values[task]["true"]["minimum_goal_cost"]
        < task_values[task]["shuffled"]["minimum_goal_cost"]
        and task_values[task]["true"]["minimum_goal_cost"]
        < task_values[task]["gaussian"]["minimum_goal_cost"]
        for task in TASKS
    )
    gates = {
        "1_selected_better_shuffled_gaussian_epsilon": all(
            aggregates["true"]["selected_action_mse"]
            < aggregates[control]["selected_action_mse"]
            for control in ("shuffled", "gaussian", "epsilon_true")
        ),
        "2_oracle_better_shuffled_gaussian_epsilon": all(
            aggregates["true"]["oracle_action_mse"]
            < aggregates[control]["oracle_action_mse"]
            for control in ("shuffled", "gaussian", "epsilon_true")
        ),
        "3_goal_better_shuffled_and_gaussian": all(
            aggregates["true"]["minimum_goal_cost"]
            < aggregates[control]["minimum_goal_cost"]
            for control in ("shuffled", "gaussian")
        ),
        "4_selected_wins_at_least_two_tasks": selected_task_wins >= 2,
        "5_goal_wins_at_least_two_tasks": goal_task_wins >= 2,
        "6_better_than_same_model_unconditional": (
            aggregates["true"]["selected_action_mse"]
            < aggregates["unconditional"]["selected_action_mse"]
            and aggregates["true"]["minimum_goal_cost"]
            < aggregates["unconditional"]["minimum_goal_cost"]
        ),
        "7_diversity_variance_and_boundary": all(
            task_values[task]["true"]["candidate_variance"] > 0.0
            and task_values[task]["true"]["unique_candidates"] >= 285.0
            and task_values[task]["true"]["boundary_fraction"]
            <= task_values[task]["gaussian"]["boundary_fraction"] + 0.05
            for task in TASKS
        ),
        "8_integrity": True,
    }
    return {
        "reverse_evaluations": steps,
        "guidance_scale": scale,
        "labels": controls,
        "equal_task_metrics": aggregates,
        "per_task_metrics": task_values,
        "selected_task_wins": selected_task_wins,
        "goal_task_wins": goal_task_wins,
        "gates": gates,
        "eligible": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--task-summary", nargs=2, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.protocol, args.source_manifest, args.output_dir):
        reject_protected_path(path)
    if (
        sha256_file(args.protocol) != e10.PROTOCOL_SHA256
        or not args.source_manifest.is_file()
    ):
        raise RuntimeError("E10V analysis prerequisite differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E10V analysis output")
    paths = {task: Path(path) for task, path in args.task_summary}
    if set(paths) != set(TASKS) or len(args.task_summary) != len(TASKS):
        raise RuntimeError("E10V analysis requires exactly three task summaries")
    source_hash = sha256_file(args.source_manifest)
    tasks = {
        task: load_task(task, paths[task], source_manifest_sha256=source_hash)
        for task in TASKS
    }
    configurations = [
        configuration_record(tasks, steps=steps, scale=scale)
        for steps in e10.REVERSE_STEPS
        for scale in e10.GUIDANCE_SCALES
    ]
    eligible = [record for record in configurations if record["eligible"]]
    selected = (
        min(
            eligible,
            key=lambda record: (
                record["equal_task_metrics"]["true"]["selected_action_mse"],
                record["equal_task_metrics"]["true"]["minimum_goal_cost"],
                record["reverse_evaluations"],
                abs(record["guidance_scale"] - 1.0),
            ),
        )
        if eligible
        else None
    )
    decision = (
        "authorize_separately_frozen_multiseed_p1_velocity_replication"
        if selected is not None
        else "stop_pure_velocity_diffusion_before_multiseed_or_protected_data"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "ok",
        "kind": "gdp_cem_e10v_p1_velocity_aggregate",
        "analysis_role": "post_E8D_P1_only_pure_diffusion_development",
        "configuration_table": configurations,
        "eligible_configuration_count": len(eligible),
        "selected_configuration": selected,
        "e10v_p1_gate_pass": selected is not None,
        "decision": decision,
        "task_summaries": {
            task: {
                "path": tasks[task]["summary"],
                "sha256": tasks[task]["summary_sha256"],
                "final_rows_sha256": tasks[task]["final_rows_sha256"],
                "elapsed_seconds": tasks[task]["elapsed_seconds"],
                "peak_cuda_memory_allocated_bytes": tasks[task][
                    "peak_cuda_memory_allocated_bytes"
                ],
            }
            for task in TASKS
        },
        "protocol_sha256": e10.PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "prior_e8d_summary_sha256": (
            "89d76ee15d4fa4420288dc5306f7f18565d39fa13c959a0c52168995b10e531f"
        ),
        "d2_read": False,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_dir / "summary.json", result)
    manifest = {
        "status": "ok",
        "kind": "gdp_cem_e10v_p1_velocity_manifest",
        "summary_sha256": sha256_file(args.output_dir / "summary.json"),
        "task_summary_counts": dict(Counter(task for task in paths)),
        "protocol_sha256": e10.PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "d2_read": False,
        "d3_read": False,
        "protected_c1_i1_read": False,
    }
    atomic_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
