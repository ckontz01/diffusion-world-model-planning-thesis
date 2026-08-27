#!/usr/bin/env python3
"""Analyze E18 only after its complete 240-cell information barrier."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

import gdp_cem_e18_specs as spec
from create_gdp_cem_e18_cells import rows as expected_cells
from gdp_cem_e15_data import sha256_file


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


def atomic_text(path: Path, value: str) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def checksum_records(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        result[name.lstrip("*")] = digest
    return result


def verify_checksums(directory: Path) -> None:
    manifest = directory / "sha256.txt"
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    records = checksum_records(manifest)
    if set(records) != {"episodes.tsv", "planner-diagnostics.jsonl", "summary.json"}:
        raise RuntimeError("E18 cell checksum names differ")
    for name, digest in records.items():
        if sha256_file(directory / name) != digest:
            raise RuntimeError("E18 cell checksum differs")


def verify_input_audit(
    path: Path, expected_sha256: str, source_sha256: str
) -> dict[str, Any]:
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise RuntimeError("E18 input-audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "passed"
        or value.get("kind") != "gdp_cem_e18_nonmetric_input_audit"
        or value.get("e18_exploratory_study") is not True
        or value.get("e17_decision_preserved")
        != "stop_transition_adapter_preflight_failed"
        or value.get("e17_both_tasks_passed") is not False
        or value.get("e17_used_as_authorization") is not False
        or int(value.get("adapter_count", -1)) != 2
        or int(value.get("proposer_count", -1)) != 18
        or value.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != source_sha256
        or value.get("e17_audit_sha256") != spec.E17_AUDIT_SHA256
        or value.get("p2_outcomes_read") is not False
        or value.get("d5_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E18 input-audit content differs")
    return value


def verify_p2_root(
    root: Path,
    *,
    source_sha256: str,
    input_audit_sha256: str,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for task in spec.TASKS:
        directory = root / task
        query_path = directory / "queries.tsv"
        manifest_path = directory / "manifest.json"
        checksum_path = directory / "sha256.txt"
        if not all(path.is_file() for path in (query_path, manifest_path, checksum_path)):
            raise FileNotFoundError(f"incomplete E18 P2 manifest: {directory}")
        records = checksum_records(checksum_path)
        if records != {
            "queries.tsv": sha256_file(query_path),
            "manifest.json": sha256_file(manifest_path),
        }:
            raise RuntimeError("E18 P2 checksum differs")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        task_spec = spec.TASK_SPEC[task]
        if (
            manifest.get("status") != "ok"
            or manifest.get("kind")
            != "gdp_cem_e18_fresh_shared_start_p2_manifest"
            or manifest.get("analysis_role")
            != "P2_exploratory_continuation_development"
            or manifest.get("task") != task
            or manifest.get("partition") != "P2"
            or int(manifest.get("base_start_count", -1)) != spec.BASE_STARTS
            or manifest.get("horizons") != list(spec.HORIZONS)
            or manifest.get("selection_salt") != spec.SELECTION_SALT
            or int(manifest.get("excluded_old_pair_count", -1)) != 20
            or manifest.get("excluded_old_queries_sha256")
            != task_spec["p2_queries_sha256"]
            or manifest.get("excluded_old_provenance_sha256")
            != task_spec["p2_manifest_sha256"]
            or manifest.get("e17_audit_sha256") != spec.E17_AUDIT_SHA256
            or manifest.get("input_audit_sha256") != input_audit_sha256
            or manifest.get("e17_decision_preserved")
            != "stop_transition_adapter_preflight_failed"
            or manifest.get("e17_used_as_authorization") is not False
            or manifest.get("protocol_sha256") != spec.PROTOCOL_SHA256
            or manifest.get("source_manifest_sha256") != source_sha256
            or manifest.get("output_tsv_sha256") != sha256_file(query_path)
            or manifest.get("p2_outcomes_read") is not False
            or manifest.get("d5_read") is not False
            or manifest.get("claim_allowed") is not False
        ):
            raise RuntimeError("E18 P2 manifest content differs")
        with query_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        if len(rows) != spec.BASE_STARTS * len(spec.HORIZONS):
            raise RuntimeError("E18 P2 row count differs")
        pairs = []
        for horizon in spec.HORIZONS:
            group = sorted(
                [row for row in rows if int(row["goal_horizon"]) == horizon],
                key=lambda row: int(row["base_index"]),
            )
            if [int(row["base_index"]) for row in group] != list(
                range(spec.BASE_STARTS)
            ):
                raise RuntimeError("E18 P2 base order differs")
            pairs.append(
                [(int(row["episode_id"]), int(row["start_step"])) for row in group]
            )
        if pairs[0] != pairs[1]:
            raise RuntimeError("E18 starts are not paired across horizons")
        result[task] = {
            "queries_sha256": sha256_file(query_path),
            "manifest_sha256": sha256_file(manifest_path),
        }
    return result


def validate_diagnostic(arm: str, record: dict[str, Any], call: int) -> None:
    if (
        int(record.get("call", -1)) != call
        or record.get("arm") != arm
        or int(record.get("tau", -1)) != spec.TAU
        or int(record.get("first_candidate_count", -1))
        != spec.first_candidate_count(arm)
        or int(record.get("minimum_first_unique_candidates", -1))
        < spec.MINIMUM_FIRST_UNIQUE[arm]
        or float(record.get("strict_legal_oob_fraction", -1.0)) != 0.0
        or float(record.get("exact_legal_boundary_fraction", -1.0)) != 0.0
        or record.get("component_timing_method")
        != "cuda_events_resolved_after_outer_stage_synchronize"
    ):
        raise RuntimeError("E18 diagnostic identity/validity differs")
    delta = int(record["delta"])
    continuation = spec.is_continuation_arm(arm) and delta >= 2 * spec.TAU
    expected_per_context = (
        spec.GREEDY_COMPUTE_MATCHED_CANDIDATES
        if continuation or arm == "vad_greedy_576"
        else spec.GREEDY_CANDIDATES
        if arm == "vad_greedy_300"
        else spec.FIRST_CANDIDATES
    )
    if (
        int(record.get("continuations_per_first", -1))
        != (spec.CONTINUATIONS_PER_FIRST if continuation else 0)
        or int(record.get("continuation_best_count", -1))
        != (spec.CONTINUATION_BEST_COUNT if continuation else 0)
        or int(record.get("lewm_rollout_trajectories", -1))
        != spec.SHARD_SIZE * expected_per_context
    ):
        raise RuntimeError("E18 diagnostic rollout budget differs")
    second_unique = record.get("minimum_second_unique_candidates_per_first")
    state_max = record.get("predicted_state_absolute_max")
    state_q99 = record.get("predicted_state_absolute_q99")
    if continuation:
        if (
            int(second_unique) < spec.MINIMUM_SECOND_UNIQUE
            or not np.isfinite(float(state_max))
            or not np.isfinite(float(state_q99))
        ):
            raise RuntimeError("E18 continuation diagnostic differs")
    elif second_unique is not None or state_max is not None or state_q99 is not None:
        raise RuntimeError("E18 terminal/greedy diagnostic differs")
    for field in (
        "end_to_end_stage_seconds",
        "proposal_and_selection_seconds",
        "adapter_seconds",
        "lewm_scoring_seconds",
        "encoding_seconds",
    ):
        value = float(record.get(field, np.nan))
        if not np.isfinite(value) or value < 0.0:
            raise RuntimeError("E18 diagnostic timing differs")


def load_cell(
    evaluation_root: Path,
    cell: dict[str, Any],
    *,
    source_sha256: str,
    input_audit_sha256: str,
    p2_hashes: dict[str, dict[str, str]],
) -> dict[str, Any]:
    task = str(cell["task"])
    arm = str(cell["arm"])
    replicate = int(cell["replicate"])
    horizon = int(cell["horizon"])
    shard = int(cell["shard"])
    directory = (
        evaluation_root
        / task
        / arm
        / f"replicate-{replicate}"
        / f"horizon-{horizon}"
        / f"shard-{shard}"
    )
    verify_checksums(directory)
    summary_path = directory / "summary.json"
    episodes_path = directory / "episodes.tsv"
    diagnostics_path = directory / "planner-diagnostics.jsonl"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cycles = 2 if task == "pusht" else 1
    expected_stages = len(spec.schedule_for(horizon)) * cycles
    if (
        summary.get("status") != "ok"
        or summary.get("kind")
        != "gdp_cem_e18_p2_exploratory_closed_loop_shard"
        or summary.get("analysis_role")
        != "P2_exploratory_continuation_development"
        or summary.get("task") != task
        or summary.get("arm") != arm
        or int(summary.get("replicate", -1)) != replicate
        or int(summary.get("learned_seed", -1)) != int(cell["learned_seed"])
        or int(summary.get("horizon", -1)) != horizon
        or int(summary.get("shard", -1)) != shard
        or int(summary.get("episode_count", -1)) != spec.SHARD_SIZE
        or summary.get("schedule") != list(spec.schedule_for(horizon))
        or int(summary.get("environment_budget", -1)) != horizon * cycles
        or int(summary.get("planning_stage_count", -1)) != expected_stages
        or summary.get("episodes_tsv_sha256") != sha256_file(episodes_path)
        or summary.get("planner_diagnostics_sha256")
        != sha256_file(diagnostics_path)
        or summary.get("p2_queries_sha256") != p2_hashes[task]["queries_sha256"]
        or summary.get("p2_provenance_sha256")
        != p2_hashes[task]["manifest_sha256"]
        or summary.get("p2_selection_salt") != spec.SELECTION_SALT
        or summary.get("input_audit_sha256") != input_audit_sha256
        or summary.get("e17_decision_preserved")
        != "stop_transition_adapter_preflight_failed"
        or summary.get("e17_used_as_authorization") is not False
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_sha256
        or summary.get("d5_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"E18 summary identity differs: {summary_path}")
    artifacts = summary.get("model_artifacts", {})
    proposer = artifacts.get("e15_proposer", {})
    adapter = artifacts.get("e17_transition_state_adapter")
    expected_family = spec.family_for_arm(arm)
    if (
        proposer.get("condition") != expected_family
        or int(proposer.get("seed", -1)) != int(cell["learned_seed"])
        or artifacts.get("e17_failure_preserved") is not True
        or artifacts.get("e17_used_as_authorization") is not False
    ):
        raise RuntimeError("E18 model-artifact identity differs")
    if spec.is_continuation_arm(arm):
        if (
            not isinstance(adapter, dict)
            or adapter.get("summary_sha256") != spec.E17_SUMMARY_SHA256[task]
            or adapter.get("checkpoint_sha256")
            != spec.E17_CHECKPOINT_SHA256[task]
            or adapter.get("e17_gate_passed") is not spec.E17_GATE_PASSED[task]
            or adapter.get("e17_failure_preserved") is not True
            or adapter.get("e17_used_as_authorization") is not False
        ):
            raise RuntimeError("E18 adapter artifact differs")
    elif adapter is not None:
        raise RuntimeError("E18 greedy arm loaded an adapter")
    with episodes_path.open(newline="", encoding="utf-8") as stream:
        episodes = list(csv.DictReader(stream, delimiter="\t"))
    expected_base = list(
        range(shard * spec.SHARD_SIZE, (shard + 1) * spec.SHARD_SIZE)
    )
    if (
        len(episodes) != spec.SHARD_SIZE
        or [int(row["base_index"]) for row in episodes] != expected_base
        or any(
            row["task"] != task
            or row["arm"] != arm
            or int(row["replicate"]) != replicate
            or int(row["horizon"]) != horizon
            or int(row["shard"]) != shard
            or int(row["success"]) not in (0, 1)
            for row in episodes
        )
    ):
        raise RuntimeError("E18 episode rows differ")
    diagnostics = [
        json.loads(line)
        for line in diagnostics_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(diagnostics) != expected_stages:
        raise RuntimeError("E18 diagnostic count differs")
    for call, diagnostic in enumerate(diagnostics):
        validate_diagnostic(arm, diagnostic, call)
    if int(summary.get("lewm_rollout_trajectories", -1)) != sum(
        int(record["lewm_rollout_trajectories"]) for record in diagnostics
    ):
        raise RuntimeError("E18 summary rollout total differs")
    return {
        "cell": cell,
        "summary": summary,
        "summary_path": summary_path,
        "episodes": episodes,
        "diagnostics": diagnostics,
    }


def interval(values: np.ndarray) -> list[float]:
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]


def rate_tables(success: np.ndarray) -> dict[str, Any]:
    # Axes: task, base start, arm, horizon, replicate.
    task_horizon = success.mean(axis=(1, 4))
    task = task_horizon.mean(axis=2)
    by_replicate = success.mean(axis=1)
    equal = task_horizon.mean(axis=(0, 2))
    return {
        "task_horizon": {
            task_name: {
                arm: {
                    str(horizon): float(task_horizon[t, a, h])
                    for h, horizon in enumerate(spec.HORIZONS)
                }
                for a, arm in enumerate(spec.ARMS)
            }
            for t, task_name in enumerate(spec.TASKS)
        },
        "task_average": {
            task_name: {
                arm: float(task[t, a]) for a, arm in enumerate(spec.ARMS)
            }
            for t, task_name in enumerate(spec.TASKS)
        },
        "task_horizon_replicate": {
            task_name: {
                arm: {
                    str(horizon): {
                        str(replicate): float(by_replicate[t, a, h, r])
                        for r, replicate in enumerate((1, 2, 3))
                    }
                    for h, horizon in enumerate(spec.HORIZONS)
                }
                for a, arm in enumerate(spec.ARMS)
            }
            for t, task_name in enumerate(spec.TASKS)
        },
        "equal_task_equal_horizon": {
            arm: float(equal[a]) for a, arm in enumerate(spec.ARMS)
        },
    }


def paired_differences(success: np.ndarray) -> dict[str, Any]:
    treatment = spec.ARMS.index("vad_continuation")
    task_horizon = success.mean(axis=(1, 4))
    result: dict[str, Any] = {}
    for comparator in spec.ARMS:
        if comparator == "vad_continuation":
            continue
        other = spec.ARMS.index(comparator)
        cells = task_horizon[:, treatment] - task_horizon[:, other]
        result[comparator] = {
            "task_horizon": {
                task: {
                    str(horizon): float(cells[t, h])
                    for h, horizon in enumerate(spec.HORIZONS)
                }
                for t, task in enumerate(spec.TASKS)
            },
            "task_average": {
                task: float(cells[t].mean())
                for t, task in enumerate(spec.TASKS)
            },
            "equal_task_equal_horizon": float(cells.mean()),
            "minimum_task_average": float(cells.mean(axis=1).min()),
            "minimum_task_horizon": float(cells.min()),
        }
    return result


def clustered_bootstrap(success: np.ndarray) -> dict[str, Any]:
    rng = np.random.default_rng(spec.derived_seed("clustered-bootstrap"))
    arm_samples = np.empty(
        (spec.BOOTSTRAP_RESAMPLES, len(spec.ARMS)), dtype=np.float64
    )
    comparators = [arm for arm in spec.ARMS if arm != "vad_continuation"]
    difference_samples = {
        arm: np.empty(spec.BOOTSTRAP_RESAMPLES, dtype=np.float64)
        for arm in comparators
    }
    task_difference_samples = {
        arm: np.empty(
            (spec.BOOTSTRAP_RESAMPLES, len(spec.TASKS)), dtype=np.float64
        )
        for arm in comparators
    }
    task_horizon_difference_samples = {
        arm: np.empty(
            (
                spec.BOOTSTRAP_RESAMPLES,
                len(spec.TASKS),
                len(spec.HORIZONS),
            ),
            dtype=np.float64,
        )
        for arm in comparators
    }
    treatment = spec.ARMS.index("vad_continuation")
    for draw in range(spec.BOOTSTRAP_RESAMPLES):
        task_rates = np.empty(
            (len(spec.TASKS), len(spec.ARMS), len(spec.HORIZONS)),
            dtype=np.float64,
        )
        for task in range(len(spec.TASKS)):
            indices = rng.integers(0, spec.BASE_STARTS, spec.BASE_STARTS)
            task_rates[task] = success[task, indices].mean(axis=(0, 3))
        arm_samples[draw] = task_rates.mean(axis=(0, 2))
        for comparator in comparators:
            other = spec.ARMS.index(comparator)
            cells = task_rates[:, treatment] - task_rates[:, other]
            difference_samples[comparator][draw] = cells.mean()
            task_difference_samples[comparator][draw] = cells.mean(axis=1)
            task_horizon_difference_samples[comparator][draw] = cells
    return {
        "resamples": spec.BOOTSTRAP_RESAMPLES,
        "unit": "task_base_start_cluster",
        "stratified_by_task": True,
        "arms_horizons_replicates_retained_paired": True,
        "seeds_resampled_as_independent": False,
        "arm_success_95ci": {
            arm: interval(arm_samples[:, a]) for a, arm in enumerate(spec.ARMS)
        },
        "vad_continuation_minus_comparator_equal_95ci": {
            arm: interval(values) for arm, values in difference_samples.items()
        },
        "vad_continuation_minus_comparator_task_95ci": {
            arm: {
                task: interval(values[:, t])
                for t, task in enumerate(spec.TASKS)
            }
            for arm, values in task_difference_samples.items()
        },
        "vad_continuation_minus_comparator_task_horizon_95ci": {
            arm: {
                task: {
                    str(horizon): interval(values[:, t, h])
                    for h, horizon in enumerate(spec.HORIZONS)
                }
                for t, task in enumerate(spec.TASKS)
            }
            for arm, values in task_horizon_difference_samples.items()
        },
    }


def timing_tables(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = {
        "end_to_end": "end_to_end_stage_seconds",
        "proposal_and_selection": "proposal_and_selection_seconds",
        "adapter": "adapter_seconds",
        "lewm_scoring": "lewm_scoring_seconds",
        "encoding": "encoding_seconds",
    }
    values: dict[tuple[str, int, str, str], list[float]] = {}
    post_values: dict[tuple[str, int, str, str], list[float]] = {}
    resources: dict[tuple[str, int, str], list[tuple[int, int]]] = {}
    predicted: dict[tuple[str, int, str], list[tuple[float, float]]] = {}
    for record in records:
        cell = record["cell"]
        summary = record["summary"]
        resource_key = (str(cell["task"]), int(cell["horizon"]), str(cell["arm"]))
        resources.setdefault(resource_key, []).append(
            (
                int(summary["active_learned_parameters"]),
                int(summary["runtime"]["peak_cuda_memory_allocated_bytes"]),
            )
        )
        for diagnostic in record["diagnostics"]:
            for label, field in fields.items():
                key = (*resource_key, label)
                value = float(diagnostic[field]) / spec.SHARD_SIZE
                values.setdefault(key, []).append(value)
                if int(diagnostic["call"]) > 0:
                    post_values.setdefault(key, []).append(value)
            if diagnostic["predicted_state_absolute_max"] is not None:
                predicted.setdefault(resource_key, []).append(
                    (
                        float(diagnostic["predicted_state_absolute_max"]),
                        float(diagnostic["predicted_state_absolute_q99"]),
                    )
                )
    task_horizon: dict[str, Any] = {}
    for task in spec.TASKS:
        task_horizon[task] = {}
        for arm in spec.ARMS:
            task_horizon[task][arm] = {}
            for horizon in spec.HORIZONS:
                resource_key = (task, horizon, arm)
                resource_rows = resources[resource_key]
                entry: dict[str, Any] = {
                    "active_learned_parameters": sorted(
                        {value[0] for value in resource_rows}
                    ),
                    "peak_cuda_memory_median_bytes": float(
                        np.median([value[1] for value in resource_rows])
                    ),
                }
                for label in fields:
                    key = (*resource_key, label)
                    all_value = np.asarray(values[key])
                    post_value = np.asarray(post_values.get(key, []))
                    entry[label] = {
                        "all_call_median_seconds": float(np.median(all_value)),
                        "post_first_call_median_seconds": (
                            float(np.median(post_value)) if len(post_value) else None
                        ),
                        "all_call_count": len(all_value),
                        "post_first_call_count": len(post_value),
                    }
                predicted_rows = predicted.get(resource_key, [])
                entry["adapter_predicted_state"] = (
                    {
                        "maximum_absolute_standardized_value": max(
                            value[0] for value in predicted_rows
                        ),
                        "maximum_stage_q99_absolute_standardized_value": max(
                            value[1] for value in predicted_rows
                        ),
                    }
                    if predicted_rows
                    else None
                )
                task_horizon[task][arm][str(horizon)] = entry
    equal_post: dict[str, float] = {}
    for arm in spec.ARMS:
        cell_values = [
            task_horizon[task][arm][str(horizon)]["end_to_end"][
                "post_first_call_median_seconds"
            ]
            for task in spec.TASKS
            for horizon in spec.HORIZONS
        ]
        if any(value is None for value in cell_values):
            raise RuntimeError("E18 post-first timing is missing")
        equal_post[arm] = float(np.mean(cell_values))
    return {
        "task_horizon": task_horizon,
        "equal_task_equal_horizon_mean_post_first_end_to_end_median_seconds": (
            equal_post
        ),
    }


def gate_decision(differences: dict[str, Any]) -> dict[str, Any]:
    def passes(comparator: str) -> bool:
        value = differences[comparator]
        return bool(
            value["equal_task_equal_horizon"] > 0.0
            and value["minimum_task_average"]
            >= -spec.MAXIMUM_TASK_AVERAGE_LOSS
        )

    comparator_pass = {
        comparator: passes(comparator)
        for comparator in differences
    }
    mechanism = comparator_pass["vad_greedy_300"] and comparator_pass[
        "vad_greedy_576"
    ]
    specificity = comparator_pass[
        "diagonal_gaussian_continuation"
    ] and comparator_pass["direct_gmm_continuation"]
    joint = mechanism and specificity
    return {
        "maximum_allowed_task_average_loss": spec.MAXIMUM_TASK_AVERAGE_LOSS,
        "comparator_rules": comparator_pass,
        "continuation_mechanism_passed": mechanism,
        "diffusion_specificity_passed": specificity,
        "joint_exploratory_signal_passed": joint,
        "separate_confirmation_protocol_draft_authorized": joint,
        "confirmation_automatically_launched": False,
        "decision": (
            "authorize_drafting_separate_frozen_confirmation_protocol"
            if joint
            else "stop_e18_without_confirmation_authorization"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--cell-manifest", type=Path, required=True)
    parser.add_argument("--cell-manifest-sha256", required=True)
    parser.add_argument("--input-audit", type=Path, required=True)
    parser.add_argument("--input-audit-sha256", required=True)
    parser.add_argument("--p2-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.evaluation_root,
        args.cell_manifest,
        args.input_audit,
        args.p2_root,
        args.protocol,
        args.source_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E18 analysis output")
    if (
        sha256_file(args.protocol) != spec.PROTOCOL_SHA256
        or sha256_file(args.cell_manifest) != args.cell_manifest_sha256
    ):
        raise RuntimeError("E18 frozen input hash differs")
    source_sha256 = sha256_file(args.source_manifest)
    verify_input_audit(args.input_audit, args.input_audit_sha256, source_sha256)
    p2_hashes = verify_p2_root(
        args.p2_root,
        source_sha256=source_sha256,
        input_audit_sha256=args.input_audit_sha256,
    )
    with args.cell_manifest.open(newline="", encoding="utf-8") as stream:
        manifest_rows = list(csv.DictReader(stream, delimiter="\t"))
    expected = expected_cells()
    if len(manifest_rows) != len(expected) or any(
        {key: str(value) for key, value in expected_row.items()} != manifest_row
        for expected_row, manifest_row in zip(expected, manifest_rows)
    ):
        raise RuntimeError("E18 cell-manifest content differs")
    records = [
        load_cell(
            args.evaluation_root,
            cell,
            source_sha256=source_sha256,
            input_audit_sha256=args.input_audit_sha256,
            p2_hashes=p2_hashes,
        )
        for cell in expected
    ]
    success = np.full(
        (
            len(spec.TASKS),
            spec.BASE_STARTS,
            len(spec.ARMS),
            len(spec.HORIZONS),
            len(spec.MODEL_SEEDS),
        ),
        np.nan,
        dtype=np.float64,
    )
    start_identity: dict[tuple[str, int], tuple[int, int]] = {}
    combined_rows: list[dict[str, Any]] = []
    for record in records:
        cell = record["cell"]
        t = spec.TASKS.index(str(cell["task"]))
        a = spec.ARMS.index(str(cell["arm"]))
        h = spec.HORIZONS.index(int(cell["horizon"]))
        r = int(cell["replicate"]) - 1
        for row in record["episodes"]:
            base = int(row["base_index"])
            identity = (int(row["episode_id"]), int(row["start_step"]))
            key = (str(cell["task"]), base)
            if key in start_identity and start_identity[key] != identity:
                raise RuntimeError("E18 paired starts differ")
            start_identity[key] = identity
            if np.isfinite(success[t, base, a, h, r]):
                raise RuntimeError("duplicate E18 paired outcome")
            success[t, base, a, h, r] = int(row["success"])
            combined_rows.append(row)
    if (
        not np.isfinite(success).all()
        or len(records) != 240
        or len(start_identity) != len(spec.TASKS) * spec.BASE_STARTS
        or len(combined_rows) != 720
    ):
        raise RuntimeError("E18 information barrier/pairing differs")
    rates = rate_tables(success)
    differences = paired_differences(success)
    bootstrap = clustered_bootstrap(success)
    timing = timing_tables(records)
    gates = gate_decision(differences)
    cube_ceiling = {
        arm: {
            horizon: value >= 0.95
            for horizon, value in rates["task_horizon"]["cube"][arm].items()
        }
        for arm in spec.ARMS
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    episodes_output = args.output_dir / "ALL-EPISODES.tsv"
    fields = list(combined_rows[0])
    with episodes_output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(combined_rows)
    task_first_output = args.output_dir / "TASK-FIRST.tsv"
    with task_first_output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("task", "horizon", "arm", "replicate", "success_rate"),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        by_seed = rates["task_horizon_replicate"]
        for task in spec.TASKS:
            for horizon in spec.HORIZONS:
                for arm in spec.ARMS:
                    for replicate in (1, 2, 3):
                        writer.writerow(
                            {
                                "task": task,
                                "horizon": horizon,
                                "arm": arm,
                                "replicate": replicate,
                                "success_rate": by_seed[task][arm][str(horizon)][
                                    str(replicate)
                                ],
                            }
                        )
    artifacts = {
        "|".join(
            str(record["cell"][key])
            for key in ("task", "arm", "replicate", "horizon", "shard")
        ): {
            "summary": str(record["summary_path"]),
            "summary_sha256": sha256_file(record["summary_path"]),
        }
        for record in records
    }
    result = {
        "status": "ok",
        "kind": "gdp_cem_e18_p2_exploratory_continuation_analysis",
        "analysis_role": "P2_exploratory_continuation_development",
        "decision": gates["decision"],
        "gates": gates,
        "success_rates": rates,
        "vad_continuation_paired_differences": differences,
        "clustered_bootstrap": bootstrap,
        "timing_and_adapter_domain": timing,
        "cube_ceiling_at_or_above_95_percent": cube_ceiling,
        "cell_count": len(records),
        "episode_row_count": len(combined_rows),
        "base_start_cluster_count": len(start_identity),
        "artifacts": artifacts,
        "all_episodes_tsv_sha256": sha256_file(episodes_output),
        "task_first_tsv_sha256": sha256_file(task_first_output),
        "cell_manifest_sha256": args.cell_manifest_sha256,
        "input_audit_sha256": args.input_audit_sha256,
        "p2_manifests": p2_hashes,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": source_sha256,
        "e17_decision_preserved": "stop_transition_adapter_preflight_failed",
        "e17_used_as_authorization": False,
        "confirmation_automatically_launched": False,
        "p2_read": True,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "d5_created": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    audit_path = args.output_dir / "E18-AUDIT.json"
    atomic_json(audit_path, result)
    atomic_text(
        args.output_dir / "sha256.txt",
        f"{sha256_file(audit_path)}  E18-AUDIT.json\n"
        f"{sha256_file(episodes_output)}  ALL-EPISODES.tsv\n"
        f"{sha256_file(task_first_output)}  TASK-FIRST.tsv\n",
    )


if __name__ == "__main__":
    main()
