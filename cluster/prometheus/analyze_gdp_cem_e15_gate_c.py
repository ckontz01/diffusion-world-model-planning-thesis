#!/usr/bin/env python3
"""Analyze the complete frozen E15 P2 Gate-C array with clustered pairing."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

import gdp_cem_e15_specs as spec
from create_gdp_cem_e15_gate_c_manifest import rows as expected_cells
from gdp_cem_e15_data import sha256_file


TRAINING_SOURCE_MANIFEST_SHA256 = (
    "ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c"
)
GATE_A_SOURCE_MANIFEST_SHA256 = (
    "d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e"
)
GATE_B_ANALYZER_SOURCE_MANIFEST_SHA256 = (
    "e0fb137d34750b0c1d7e8c239d5a7b3d9c84b2c50c81d870f12aa04ff6ccc039"
)
GATE_B_EVALUATION_SOURCE_MANIFEST_SHA256 = GATE_A_SOURCE_MANIFEST_SHA256
BOOTSTRAP_RESAMPLES = 10_000


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


def verify_checksums(directory: Path) -> None:
    manifest = directory / "sha256.txt"
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    records: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        records[name] = digest
    if set(records) != {"episodes.tsv", "planner-diagnostics.jsonl", "summary.json"}:
        raise RuntimeError("E15 Gate-C checksum names differ")
    for name, digest in records.items():
        if sha256_file(directory / name) != digest:
            raise RuntimeError("E15 Gate-C checksum differs")


def verify_gate_authorizations(
    gate_a_path: Path,
    gate_b_path: Path,
    *,
    gate_a_sha256: str,
    gate_b_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        not gate_a_path.is_file()
        or not gate_b_path.is_file()
        or sha256_file(gate_a_path) != gate_a_sha256
        or sha256_file(gate_b_path) != gate_b_sha256
    ):
        raise RuntimeError("E15 Gate-A/Gate-B audit hash differs")
    gate_a = json.loads(gate_a_path.read_text(encoding="utf-8"))
    gate_b = json.loads(gate_b_path.read_text(encoding="utf-8"))
    if (
        gate_a.get("status") != "passed"
        or gate_a.get("kind")
        != "gdp_cem_e15_gate_a_implementation_lineage_validation"
        or gate_a.get("analysis_role") != "P1_train_only_technical_preflight"
        or len(gate_a.get("smoke_artifacts", {})) != 22
        or len(gate_a.get("sage_artifacts", {})) != 6
        or gate_a.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or gate_a.get("training_source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or gate_a.get("source_manifest_sha256")
        != GATE_A_SOURCE_MANIFEST_SHA256
        or gate_a.get("d5_read") is not False
        or gate_a.get("protected_p3_p4_c1_i1_read") is not False
        or gate_a.get("claim_allowed") is not False
    ):
        raise RuntimeError("E15 Gate-A authorization differs")
    gates = gate_b.get("gates", {})
    if (
        gate_b.get("status") != "ok"
        or gate_b.get("kind") != "gdp_cem_e15_gate_b_offline_analysis"
        or gate_b.get("analysis_role")
        != "P1_validation_only_Gate_B_development"
        or gate_b.get("decision")
        != "authorize_fixed_gate_c_p2_long_horizon_development"
        or gate_b.get("gate_b_passed") is not True
        or set(gates)
        != {
            "common_bank_integrity",
            "direct_gmm_structural_validity",
            "vad_mechanism_and_conditioning",
        }
        or any(item.get("pass") is not True for item in gates.values())
        or int(gate_b.get("artifact_count", -1)) != 22
        or gate_b.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or gate_b.get("training_source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or gate_b.get("source_manifest_sha256")
        != GATE_B_ANALYZER_SOURCE_MANIFEST_SHA256
        or gate_b.get("evaluation_source_manifest_sha256")
        != GATE_B_EVALUATION_SOURCE_MANIFEST_SHA256
        or len(gates["common_bank_integrity"].get("banks", {})) != 22
        or gate_b.get("d5_read") is not False
        or gate_b.get("protected_p3_p4_c1_i1_read") is not False
        or gate_b.get("claim_allowed") is not False
    ):
        raise RuntimeError("E15 Gate-B authorization differs")
    return gate_a, gate_b


def load_cell(
    evaluation_root: Path,
    cell: dict[str, Any],
    *,
    source_hash: str,
    gate_a_hash: str,
    gate_b_hash: str,
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
    rounds = 30 if arm in ("base_cem", "sage_reconstruction") else 1
    cycles = (2 if task == "pusht" else 1)
    expected_stages = len(spec.schedule_for(horizon)) * cycles
    expected_calls = spec.GATE_C_SHARD_SIZE * expected_stages * rounds
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e15_p2_gate_c_closed_loop_shard"
        or summary.get("analysis_role")
        != "P2_long_horizon_method_selection_development"
        or summary.get("task") != task
        or summary.get("arm") != arm
        or int(summary.get("replicate", -1)) != replicate
        or int(summary.get("learned_seed", -1)) != int(cell["learned_seed"])
        or int(summary.get("sage_seed", -1)) != int(cell["sage_seed"])
        or int(summary.get("horizon", -1)) != horizon
        or int(summary.get("shard", -1)) != shard
        or int(summary.get("episode_count", -1)) != spec.GATE_C_SHARD_SIZE
        or summary.get("schedule") != list(spec.schedule_for(horizon))
        or int(summary.get("environment_budget", -1))
        != horizon * (2 if task == "pusht" else 1)
        or int(summary.get("candidate_count", -1)) != spec.CANDIDATE_COUNT
        or int(summary.get("cem_rounds_per_stage", -1)) != rounds
        or int(summary.get("planning_stage_count", -1)) != expected_stages
        or int(summary.get("lewm_population_calls", -1)) != expected_calls
        or summary.get("episodes_tsv_sha256") != sha256_file(episodes_path)
        or summary.get("planner_diagnostics_sha256")
        != sha256_file(diagnostics_path)
        or summary.get("p2_queries_sha256")
        != spec.TASK_SPEC[task]["p2_queries_sha256"]
        or summary.get("p2_provenance_sha256")
        != spec.TASK_SPEC[task]["p2_manifest_sha256"]
        or summary.get("gate_a_audit_sha256") != gate_a_hash
        or summary.get("gate_b_audit_sha256") != gate_b_hash
        or summary.get("gate_b_decision")
        != "authorize_fixed_gate_c_p2_long_horizon_development"
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_hash
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"E15 Gate-C summary identity differs: {summary_path}")
    with episodes_path.open(newline="", encoding="utf-8") as stream:
        episodes = list(csv.DictReader(stream, delimiter="\t"))
    expected_base = list(
        range(
            shard * spec.GATE_C_SHARD_SIZE,
            (shard + 1) * spec.GATE_C_SHARD_SIZE,
        )
    )
    if (
        len(episodes) != spec.GATE_C_SHARD_SIZE
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
        raise RuntimeError("E15 Gate-C episode rows differ")
    diagnostics = [
        json.loads(line)
        for line in diagnostics_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    timing_fields = (
        "end_to_end_stage_seconds",
        "proposal_and_selection_seconds",
        "lewm_scoring_seconds",
        "encoding_seconds",
    )
    if (
        len(diagnostics) != expected_stages
        or [int(row["call"]) for row in diagnostics] != list(range(expected_stages))
        or any(
            row.get("arm") != arm
            or row.get("component_timing_method")
            != "cuda_events_resolved_after_outer_stage_synchronize"
            or int(row.get("candidate_count", -1)) != spec.CANDIDATE_COUNT
            or int(row.get("cem_rounds", -1)) != rounds
            or int(row.get("lewm_population_calls", -1))
            != spec.GATE_C_SHARD_SIZE * rounds
            or any(
                not np.isfinite(float(row.get(field, np.nan)))
                or float(row.get(field, -1.0)) < 0.0
                for field in timing_fields
            )
            for row in diagnostics
        )
    ):
        raise RuntimeError("E15 Gate-C planner diagnostics differ")
    return {
        "cell": cell,
        "directory": directory,
        "summary": summary,
        "summary_path": summary_path,
        "episodes": episodes,
        "diagnostics": diagnostics,
    }


def interval(value: np.ndarray) -> list[float]:
    return [float(np.quantile(value, 0.025)), float(np.quantile(value, 0.975))]


def nested_rate_tables(success: np.ndarray) -> dict[str, Any]:
    # Axis order: task, base start, arm, horizon, replicate.
    task_horizon = success.mean(axis=(1, 4))
    by_replicate = success.mean(axis=1)
    overall = task_horizon.mean(axis=(0, 2))
    long = task_horizon[:, :, 1:].mean(axis=(0, 2))
    return {
        "task_horizon": {
            task: {
                arm: {
                    str(horizon): float(task_horizon[t, a, h])
                    for h, horizon in enumerate(spec.GATE_C_HORIZONS)
                }
                for a, arm in enumerate(spec.ARMS)
            }
            for t, task in enumerate(spec.TASKS)
        },
        "task_horizon_replicate": {
            task: {
                arm: {
                    str(horizon): {
                        str(replicate): float(by_replicate[t, a, h, r])
                        for r, replicate in enumerate((1, 2, 3))
                    }
                    for h, horizon in enumerate(spec.GATE_C_HORIZONS)
                }
                for a, arm in enumerate(spec.ARMS)
            }
            for t, task in enumerate(spec.TASKS)
        },
        "equal_task_equal_horizon": {
            arm: float(overall[a]) for a, arm in enumerate(spec.ARMS)
        },
        "equal_task_long_horizons_75_150": {
            arm: float(long[a]) for a, arm in enumerate(spec.ARMS)
        },
    }


def paired_differences(success: np.ndarray) -> dict[str, Any]:
    vad = spec.ARMS.index("vad")
    task_horizon = success.mean(axis=(1, 4))
    result: dict[str, Any] = {}
    for comparator in (
        "diagonal_gaussian",
        "direct_gmm",
        "base_cem",
        "sage_reconstruction",
        "sage_one_stage",
    ):
        other = spec.ARMS.index(comparator)
        cells = task_horizon[:, vad] - task_horizon[:, other]
        result[comparator] = {
            "task_horizon": {
                task: {
                    str(horizon): float(cells[t, h])
                    for h, horizon in enumerate(spec.GATE_C_HORIZONS)
                }
                for t, task in enumerate(spec.TASKS)
            },
            "equal_task_equal_horizon": float(cells.mean()),
            "equal_task_long_horizons_75_150": float(cells[:, 1:].mean()),
            "equal_task_horizon_150": float(cells[:, 2].mean()),
            "minimum_task_horizon_cell": float(cells.min()),
            "minimum_long_task_horizon_cell": float(cells[:, 1:].min()),
            "positive_horizon_count_by_task": {
                task: int(np.count_nonzero(cells[t] > 0.0))
                for t, task in enumerate(spec.TASKS)
            },
        }
    return result


def clustered_bootstrap(success: np.ndarray) -> dict[str, Any]:
    rng = np.random.default_rng(spec.derived_seed("gate-c|clustered-bootstrap"))
    arm_count = len(spec.ARMS)
    horizon_count = len(spec.GATE_C_HORIZONS)
    arm_samples = np.empty((BOOTSTRAP_RESAMPLES, arm_count), dtype=np.float64)
    arm_long_samples = np.empty(
        (BOOTSTRAP_RESAMPLES, arm_count), dtype=np.float64
    )
    difference_samples = {
        comparator: np.empty(BOOTSTRAP_RESAMPLES, dtype=np.float64)
        for comparator in spec.ARMS
        if comparator != "vad"
    }
    long_difference_samples = {
        comparator: np.empty(BOOTSTRAP_RESAMPLES, dtype=np.float64)
        for comparator in difference_samples
    }
    horizon_150_difference_samples = {
        comparator: np.empty(BOOTSTRAP_RESAMPLES, dtype=np.float64)
        for comparator in difference_samples
    }
    task_horizon_difference = {
        comparator: np.empty(
            (BOOTSTRAP_RESAMPLES, len(spec.TASKS), horizon_count),
            dtype=np.float64,
        )
        for comparator in difference_samples
    }
    vad = spec.ARMS.index("vad")
    for draw in range(BOOTSTRAP_RESAMPLES):
        task_rates = np.empty(
            (len(spec.TASKS), arm_count, horizon_count), dtype=np.float64
        )
        for task in range(len(spec.TASKS)):
            indices = rng.integers(0, spec.GATE_C_BASE_STARTS, spec.GATE_C_BASE_STARTS)
            task_rates[task] = success[task, indices].mean(axis=(0, 3))
        arm_samples[draw] = task_rates.mean(axis=(0, 2))
        arm_long_samples[draw] = task_rates[:, :, 1:].mean(axis=(0, 2))
        for comparator in difference_samples:
            other = spec.ARMS.index(comparator)
            cell = task_rates[:, vad] - task_rates[:, other]
            difference_samples[comparator][draw] = cell.mean()
            long_difference_samples[comparator][draw] = cell[:, 1:].mean()
            horizon_150_difference_samples[comparator][draw] = cell[:, 2].mean()
            task_horizon_difference[comparator][draw] = cell
    return {
        "resamples": BOOTSTRAP_RESAMPLES,
        "unit": "task_base_start_cluster",
        "stratified_by_task": True,
        "arms_horizons_replicates_retained_paired": True,
        "seeds_resampled_as_independent": False,
        "equal_task_equal_horizon_arm_success_95ci": {
            arm: interval(arm_samples[:, a]) for a, arm in enumerate(spec.ARMS)
        },
        "equal_task_long_horizons_75_150_arm_success_95ci": {
            arm: interval(arm_long_samples[:, a])
            for a, arm in enumerate(spec.ARMS)
        },
        "vad_minus_comparator_equal_task_equal_horizon_95ci": {
            comparator: interval(values)
            for comparator, values in difference_samples.items()
        },
        "vad_minus_comparator_equal_task_long_horizons_75_150_95ci": {
            comparator: interval(values)
            for comparator, values in long_difference_samples.items()
        },
        "vad_minus_comparator_equal_task_horizon_150_95ci": {
            comparator: interval(values)
            for comparator, values in horizon_150_difference_samples.items()
        },
        "vad_minus_comparator_task_horizon_95ci": {
            comparator: {
                task: {
                    str(horizon): interval(values[:, t, h])
                    for h, horizon in enumerate(spec.GATE_C_HORIZONS)
                }
                for t, task in enumerate(spec.TASKS)
            }
            for comparator, values in task_horizon_difference.items()
        },
    }


def timing_tables(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = {
        "end_to_end": "end_to_end_stage_seconds",
        "proposal_and_selection": "proposal_and_selection_seconds",
        "lewm_scoring": "lewm_scoring_seconds",
        "encoding": "encoding_seconds",
    }
    values: dict[tuple[str, int, str, str], list[float]] = {}
    post_values: dict[tuple[str, int, str, str], list[float]] = {}
    for record in records:
        cell = record["cell"]
        for diagnostic in record["diagnostics"]:
            for label, field in fields.items():
                key = (str(cell["task"]), int(cell["horizon"]), str(cell["arm"]), label)
                value = float(diagnostic[field]) / spec.GATE_C_SHARD_SIZE
                values.setdefault(key, []).append(value)
                if int(diagnostic["call"]) > 0:
                    post_values.setdefault(key, []).append(value)
    task_horizon: dict[str, Any] = {}
    for task in spec.TASKS:
        task_horizon[task] = {}
        for arm in spec.ARMS:
            task_horizon[task][arm] = {}
            for horizon in spec.GATE_C_HORIZONS:
                entry = {}
                for label in fields:
                    key = (task, horizon, arm, label)
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
                task_horizon[task][arm][str(horizon)] = entry
    equal_long_post: dict[str, float] = {}
    for arm in spec.ARMS:
        cell_medians = [
            task_horizon[task][arm][str(horizon)]["end_to_end"][
                "post_first_call_median_seconds"
            ]
            for task in spec.TASKS
            for horizon in spec.GATE_C_LONG_HORIZONS
        ]
        if any(value is None for value in cell_medians):
            raise RuntimeError("E15 long-horizon post-first timing is missing")
        equal_long_post[arm] = float(np.mean(cell_medians))
    ratio = equal_long_post["sage_reconstruction"] / equal_long_post["vad"]
    return {
        "task_horizon": task_horizon,
        "equal_task_equal_long_horizon_mean_post_first_end_to_end_median_seconds": equal_long_post,
        "full_sage_over_vad_post_first_latency_ratio": ratio,
        "primary_gate_timing_definition": (
            "ratio of equal-task/equal-{75,150} means of task/horizon-arm "
            "medians pooled over all post-first synchronized stage calls"
        ),
    }


def gate_decision(
    differences: dict[str, Any], timing: dict[str, Any]
) -> dict[str, Any]:
    gaussian = differences["diagonal_gaussian"]
    gmm = differences["direct_gmm"]
    base = differences["base_cem"]
    sage = differences["sage_reconstruction"]
    mechanism = (
        gaussian["equal_task_equal_horizon"] > 0.0
        and gaussian["minimum_task_horizon_cell"] >= -0.05
    )
    specificity = (
        gmm["equal_task_equal_horizon"] > 0.0
        and gmm["minimum_task_horizon_cell"] >= -0.05
        and all(
            count >= 2 for count in gmm["positive_horizon_count_by_task"].values()
        )
    )
    h150_by_task = {
        task: base["task_horizon"][task]["150"] for task in spec.TASKS
    }
    long_relevance = any(value >= 0.15 for value in h150_by_task.values())
    superiority = (
        sage["equal_task_long_horizons_75_150"] > 0.0
        and sage["equal_task_horizon_150"] >= 0.0
        and sage["minimum_long_task_horizon_cell"] >= -0.05
    )
    latency_ratio = timing["full_sage_over_vad_post_first_latency_ratio"]
    noninferiority = (
        sage["equal_task_long_horizons_75_150"] >= -0.03
        and sage["equal_task_horizon_150"] >= -0.03
        and sage["minimum_long_task_horizon_cell"] >= -0.10
        and latency_ratio >= 5.0
    )
    authorize = mechanism and specificity and long_relevance and (
        superiority or noninferiority
    )
    return {
        "mechanism_against_diagonal_gaussian": mechanism,
        "diffusion_specificity_against_direct_gmm": specificity,
        "horizon_150_relevance_against_base_cem": long_relevance,
        "horizon_150_vad_minus_base_by_task": h150_by_task,
        "full_sage_superiority_route": superiority,
        "full_sage_efficiency_noninferiority_route": noninferiority,
        "full_sage_over_vad_post_first_latency_ratio": latency_ratio,
        "authorize_separate_untouched_d5_protocol_draft": authorize,
        "decision": (
            "authorize_drafting_separate_frozen_d5_protocol"
            if authorize
            else "stop_focused_long_horizon_confirmation_line"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--cell-manifest", type=Path, required=True)
    parser.add_argument("--cell-manifest-sha256", required=True)
    parser.add_argument("--gate-a-audit", type=Path, required=True)
    parser.add_argument("--gate-a-audit-sha256", required=True)
    parser.add_argument("--gate-b-audit", type=Path, required=True)
    parser.add_argument("--gate-b-audit-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.evaluation_root,
        args.cell_manifest,
        args.gate_a_audit,
        args.gate_b_audit,
        args.protocol,
        args.source_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E15 Gate-C analysis output")
    if (
        sha256_file(args.protocol) != spec.PROTOCOL_SHA256
        or sha256_file(args.cell_manifest) != args.cell_manifest_sha256
    ):
        raise RuntimeError("E15 Gate-C frozen input hash differs")
    verify_gate_authorizations(
        args.gate_a_audit,
        args.gate_b_audit,
        gate_a_sha256=args.gate_a_audit_sha256,
        gate_b_sha256=args.gate_b_audit_sha256,
    )
    source_hash = sha256_file(args.source_manifest)
    with args.cell_manifest.open(newline="", encoding="utf-8") as stream:
        manifest_rows = list(csv.DictReader(stream, delimiter="\t"))
    expected = expected_cells()
    if len(manifest_rows) != len(expected) or any(
        {key: str(value) for key, value in expected_row.items()} != manifest_row
        for expected_row, manifest_row in zip(expected, manifest_rows)
    ):
        raise RuntimeError("E15 Gate-C cell manifest content differs")
    records = [
        load_cell(
            args.evaluation_root,
            cell,
            source_hash=source_hash,
            gate_a_hash=args.gate_a_audit_sha256,
            gate_b_hash=args.gate_b_audit_sha256,
        )
        for cell in expected
    ]

    success = np.full(
        (
            len(spec.TASKS),
            spec.GATE_C_BASE_STARTS,
            len(spec.ARMS),
            len(spec.GATE_C_HORIZONS),
            3,
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
        h = spec.GATE_C_HORIZONS.index(int(cell["horizon"]))
        r = int(cell["replicate"]) - 1
        for row in record["episodes"]:
            base = int(row["base_index"])
            identity = (int(row["episode_id"]), int(row["start_step"]))
            key = (str(cell["task"]), base)
            if key in start_identity and start_identity[key] != identity:
                raise RuntimeError("E15 Gate-C starts differ across paired cells")
            start_identity[key] = identity
            if np.isfinite(success[t, base, a, h, r]):
                raise RuntimeError("duplicate E15 Gate-C paired cell")
            success[t, base, a, h, r] = int(row["success"])
            combined_rows.append(row)
    if (
        not np.isfinite(success).all()
        or len(start_identity) != len(spec.TASKS) * spec.GATE_C_BASE_STARTS
        or len(combined_rows) != 2160
    ):
        raise RuntimeError("E15 Gate-C information barrier/pairing differs")
    rates = nested_rate_tables(success)
    differences = paired_differences(success)
    bootstrap = clustered_bootstrap(success)
    timing = timing_tables(records)
    gates = gate_decision(differences, timing)
    cube_rates = rates["task_horizon"]["cube"]
    cube_ceiling = {
        arm: {
            horizon: value >= 0.95 for horizon, value in horizons.items()
        }
        for arm, horizons in cube_rates.items()
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    episodes_output = args.output_dir / "ALL-EPISODES.tsv"
    fields = list(combined_rows[0])
    with episodes_output.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
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
            for horizon in spec.GATE_C_HORIZONS:
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
            map(
                str,
                (
                    record["cell"]["task"],
                    record["cell"]["arm"],
                    record["cell"]["replicate"],
                    record["cell"]["horizon"],
                    record["cell"]["shard"],
                ),
            )
        ): {
            "summary": str(record["summary_path"]),
            "summary_sha256": sha256_file(record["summary_path"]),
        }
        for record in records
    }
    result = {
        "status": "ok",
        "kind": "gdp_cem_e15_p2_gate_c_analysis",
        "analysis_role": "P2_long_horizon_method_selection_development",
        "decision": gates["decision"],
        "gates": gates,
        "success_rates": rates,
        "vad_paired_differences": differences,
        "clustered_bootstrap": bootstrap,
        "timing": timing,
        "cube_ceiling_at_or_above_95_percent": cube_ceiling,
        "cube_ceiling_note": (
            "Cube rates are reported task-first and any cell at or above 95% is "
            "explicitly marked; ceiling cells are not allowed to hide other tasks."
        ),
        "cell_count": len(records),
        "episode_row_count": len(combined_rows),
        "base_start_cluster_count": len(start_identity),
        "artifacts": artifacts,
        "all_episodes_tsv": str(episodes_output),
        "all_episodes_tsv_sha256": sha256_file(episodes_output),
        "task_first_tsv": str(task_first_output),
        "task_first_tsv_sha256": sha256_file(task_first_output),
        "cell_manifest": str(args.cell_manifest),
        "cell_manifest_sha256": args.cell_manifest_sha256,
        "gate_a_audit_sha256": args.gate_a_audit_sha256,
        "gate_a_audit": str(args.gate_a_audit),
        "gate_b_audit_sha256": args.gate_b_audit_sha256,
        "gate_b_audit": str(args.gate_b_audit),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "training_source_manifest_sha256": TRAINING_SOURCE_MANIFEST_SHA256,
        "gate_a_source_manifest_sha256": GATE_A_SOURCE_MANIFEST_SHA256,
        "gate_b_analyzer_source_manifest_sha256": (
            GATE_B_ANALYZER_SOURCE_MANIFEST_SHA256
        ),
        "gate_b_evaluation_source_manifest_sha256": (
            GATE_B_EVALUATION_SOURCE_MANIFEST_SHA256
        ),
        "p2_read": True,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "d5_created": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    audit_path = args.output_dir / "GATE-C-AUDIT.json"
    atomic_json(audit_path, result)
    atomic_text(
        args.output_dir / "sha256.txt",
        f"{sha256_file(audit_path)}  GATE-C-AUDIT.json\n"
        f"{sha256_file(episodes_output)}  ALL-EPISODES.tsv\n"
        f"{sha256_file(task_first_output)}  TASK-FIRST.tsv\n",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
