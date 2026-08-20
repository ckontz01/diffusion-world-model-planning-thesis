#!/usr/bin/env python3
"""Analyze the frozen one-seed E8D GADR exposed-D2 study."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_d2_models as d2
import evaluate_gdp_cem_e8d_closed_loop as e8d


TASKS = e8d.TASKS
ARMS = e8d.ARMS
EVAL_COUNT = e8d.EVAL_COUNT
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081705
D2_HASHES = e8d.e3.D2_HASHES


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


def parse_run(values: list[str]) -> tuple[str, str, Path]:
    task, arm, path = values
    if task not in TASKS or arm not in ARMS:
        raise ValueError(f"invalid E8D run identity: {values}")
    return task, arm, Path(path)


def read_episodes(path: Path, *, task: str, arm: str) -> tuple[np.ndarray, list[tuple[int, int]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"eval_index", "episode_id", "start_step", "arm", "success"}
    if (
        len(rows) != EVAL_COUNT
        or not rows
        or not required.issubset(rows[0])
        or [int(row["eval_index"]) for row in rows] != list(range(EVAL_COUNT))
        or any(row["arm"] != arm or int(row["success"]) not in (0, 1) for row in rows)
    ):
        raise RuntimeError(f"invalid E8D episode vector: {task}/{arm}")
    return (
        np.asarray([int(row["success"]) for row in rows], dtype=np.float64),
        [(int(row["episode_id"]), int(row["start_step"])) for row in rows],
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def expected_config(arm: str) -> dict[str, Any]:
    selector = arm.endswith("_select")
    proposal = arm in e8d.PROPOSAL_ARMS
    if arm in {"b0", "acid"}:
        refresh = "released_cem"
    elif arm == "custom_b0":
        refresh = "none"
    elif selector:
        refresh = "selector"
    elif arm == "gadr_true_first":
        refresh = "first"
    else:
        refresh = "all"
    return {
        "scorer_seed": e8d.SCORER_SEED,
        "planner_seed": e8d.PLANNER_SEED,
        "proposal_seed": e8d.PROPOSAL_SEED,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "cem_samples": 300,
        "cem_steps": 1 if selector else 30,
        "cem_topk": 30,
        "proposal_injection_fraction": 1.0 if selector else 0.5 if proposal else 0.0,
        "proposal_refresh": refresh,
        "preserve_cem_mean": not selector,
        "return_mode": "best" if selector else "mean",
        "gadr_restart_timestep": 40 if proposal else None,
        "gadr_reverse_evaluations": 1 if proposal else None,
        "gadr_refined_fraction": 0.5 if proposal else None,
        "gadr_rounding": "floor((M-1)*fraction+0.5)",
        "acid_lambda": 0.07 if arm == "acid" else None,
        "acid_noise_stream": (
            "SHA-256(task, scorer seed, planner seed, cost-call index)"
            if arm == "acid"
            else None
        ),
    }


def validate_lineage(summary: dict[str, Any], *, task: str, arm: str) -> None:
    acid = summary.get("acid_scorer")
    proposals = summary.get("proposal_models")
    if arm == "acid":
        if (
            not isinstance(acid, dict)
            or proposals is not None
            or acid.get("arm") != "acid"
            or acid.get("seed") != e8d.SCORER_SEED
            or acid.get("checkpoint_sha256") != e8d.EXPECTED_ACID_CHECKPOINTS[task]
        ):
            raise RuntimeError("E8D ACID lineage differs")
        checkpoint = Path(acid.get("checkpoint", ""))
        e8d.reject_protected_path(checkpoint)
        if not checkpoint.is_file() or d2.sha256_file(checkpoint) != acid["checkpoint_sha256"]:
            raise RuntimeError("E8D ACID checkpoint hash differs")
    elif arm in e8d.PROPOSAL_ARMS:
        if acid is not None or not isinstance(proposals, dict) or set(proposals) != set(e8d.e7.CONDITIONS):
            raise RuntimeError("E8D proposal lineage is incomplete")
        for condition in e8d.e7.CONDITIONS:
            record = proposals[condition]
            checkpoint = Path(record.get("checkpoint", ""))
            source = Path(record.get("summary", ""))
            e8d.reject_protected_path(checkpoint)
            e8d.reject_protected_path(source)
            if (
                record.get("checkpoint_sha256")
                != e8d.EXPECTED_PROPOSAL_CHECKPOINTS[task][condition]
                or not checkpoint.is_file()
                or d2.sha256_file(checkpoint) != record.get("checkpoint_sha256")
                or not source.is_file()
                or d2.sha256_file(source) != record.get("summary_sha256")
            ):
                raise RuntimeError("E8D proposal checkpoint/summary hash differs")
    elif acid is not None or proposals is not None:
        raise RuntimeError("E8D baseline unexpectedly has a learned scorer")


def validate_diagnostics(summary: dict[str, Any], *, arm: str) -> dict[str, Any]:
    solver_path = Path(summary["solver_diagnostics"])
    proposal_path = Path(summary["proposal_diagnostics"])
    cost_path = Path(summary["cost_diagnostics"])
    solver = read_jsonl(solver_path)
    proposal = read_jsonl(proposal_path)
    cost = read_jsonl(cost_path)
    selector = arm.endswith("_select")
    proposal_arm = arm in e8d.PROPOSAL_ARMS
    expected_solver = 100 if selector else 3000 if arm not in {"b0", "acid"} else 0
    expected_cost = 3000 if arm == "acid" else 0
    expected_proposal = (
        100
        if selector or arm == "gadr_true_first"
        else 3000
        if proposal_arm
        else 0
    )
    if (
        len(solver) != expected_solver
        or len(cost) != expected_cost
        or len(proposal) != expected_proposal
    ):
        raise RuntimeError("E8D diagnostic file count differs")

    expected_steps = 1 if selector else 30
    expected_injected = 300 if selector else 150
    active_solver = 0
    for item in solver:
        iteration = item.get("iteration")
        active = item.get("proposal_active")
        expected_active = (
            proposal_arm
            and (arm != "gadr_true_first" or iteration == 1)
        )
        seconds = float(item.get("proposal_seconds", -1.0))
        if (
            not isinstance(iteration, int)
            or not 1 <= iteration <= expected_steps
            or not isinstance(item.get("batch_start"), int)
            or not 0 <= item["batch_start"] < EVAL_COUNT
            or active is not expected_active
            or item.get("proposal_count")
            != (expected_injected if expected_active else 0)
            or not math.isfinite(seconds)
            or seconds < 0.0
        ):
            raise RuntimeError("E8D solver diagnostic semantics differ")
        active_solver += int(expected_active)
    if active_solver != expected_proposal:
        raise RuntimeError("E8D active proposal-call count differs")

    expected_condition = (
        "gaussian"
        if arm.startswith("gaussian_")
        else "shuffled"
        if "shuffled" in arm
        else "true"
    )
    expected_matched = 150 if selector else 75
    expected_refined = 0 if expected_condition == "gaussian" else expected_matched
    boundaries: list[float] = []
    displacements: list[float] = []
    for index, item in enumerate(proposal):
        boundary = float(item.get("boundary_fraction", math.nan))
        displacement = float(item.get("refinement_displacement_mse", math.nan))
        if (
            item.get("call") != index
            or item.get("condition") != expected_condition
            or item.get("candidate_count") != expected_injected
            or item.get("matched_refinement_slots") != expected_matched
            or item.get("refined_count") != expected_refined
            or not math.isfinite(boundary)
            or not 0.0 <= boundary <= 1.0
            or not math.isfinite(displacement)
            or displacement < 0.0
            or (expected_condition == "gaussian" and displacement != 0.0)
        ):
            raise RuntimeError("E8D proposal diagnostic semantics differ")
        boundaries.append(boundary)
        displacements.append(displacement)

    for index, item in enumerate(cost, start=1):
        numeric_lists = (
            item.get("goal_std"),
            item.get("verifier_std"),
            item.get("adaptive_weight"),
            item.get("verifier_min"),
        )
        if (
            item.get("call") != index
            or any(
                not isinstance(values, list)
                or len(values) != 1
                or not math.isfinite(float(values[0]))
                for values in numeric_lists
            )
            or float(item["adaptive_weight"][0]) < 0.0
        ):
            raise RuntimeError("E8D ACID cost diagnostic semantics differ")

    proposal_seconds = sum(float(item.get("proposal_seconds", 0.0)) for item in solver)
    if not math.isclose(
        proposal_seconds,
        float(summary.get("proposal_seconds_total", math.nan)),
        rel_tol=1.0e-12,
        abs_tol=1.0e-12,
    ):
        raise RuntimeError("E8D proposal timing total differs")
    runtime = summary.get("runtime", {})
    peak_allocated = runtime.get("peak_cuda_memory_allocated_bytes")
    peak_reserved = runtime.get("peak_cuda_memory_reserved_bytes")
    if (
        not isinstance(peak_allocated, int)
        or not isinstance(peak_reserved, int)
        or peak_allocated <= 0
        or peak_reserved < peak_allocated
    ):
        raise RuntimeError("E8D peak CUDA memory record differs")
    return {
        "lewm_cost_calls": expected_cost if arm == "acid" else expected_solver or 3000,
        "lewm_candidate_evaluations": (
            expected_cost if arm == "acid" else expected_solver or 3000
        )
        * 300,
        "proposal_calls": expected_proposal,
        "mean_boundary_fraction": float(np.mean(boundaries)) if boundaries else None,
        "mean_refinement_displacement_mse": (
            float(np.mean(displacements)) if displacements else None
        ),
        "peak_cuda_memory_allocated_bytes": peak_allocated,
        "peak_cuda_memory_reserved_bytes": peak_reserved,
    }


def load_run(
    identity: tuple[str, str, Path], *, source_manifest_sha256: str
) -> dict[str, Any]:
    task, arm, path = identity
    e8d.reject_protected_path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    config = value.get("resolved_config")
    expected = expected_config(arm)
    snapshot_root = Path(__file__).resolve().parent
    recorded_protocol = Path(value.get("protocol", ""))
    recorded_source_manifest = Path(value.get("source_manifest", ""))
    e8d.reject_protected_path(recorded_protocol)
    e8d.reject_protected_path(recorded_source_manifest)
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e8d_exposed_d2_closed_loop_evaluation"
        or value.get("analysis_role") != "post_E8A_exposed_D2_one_seed_development"
        or value.get("task") != task
        or value.get("arm") != arm
        or value.get("scorer_seed") != e8d.SCORER_SEED
        or value.get("planner_seed") != e8d.PLANNER_SEED
        or value.get("proposal_seed") != e8d.PROPOSAL_SEED
        or value.get("episode_count") != EVAL_COUNT
        or recorded_protocol.resolve()
        != (
            snapshot_root
            / "ACID-ALTERNATIVE-E8D-GADR-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md"
        ).resolve()
        or recorded_source_manifest.resolve()
        != (snapshot_root / "SOURCE-MANIFEST.sha256").resolve()
        or value.get("protocol_sha256") != e8d.E8D_PROTOCOL_SHA256
        or value.get("method_protocol_sha256") != d2.PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != source_manifest_sha256
        or value.get("e8a_aggregate_sha256") != e8d.E8A_AGGREGATE_SHA256
        or value.get("e8a_decision")
        != "authorize_separately_frozen_exposed_d2_gadr_diagnostic"
        or value.get("eval_manifest_sha256") != D2_HASHES[task]["manifest"]
        or value.get("eval_provenance_sha256") != D2_HASHES[task]["provenance"]
        or value.get("dataset_sha256")
        != e8d.EXPECTED_RUNTIME_ARTIFACTS[task]["dataset_sha256"]
        or value.get("world_model_policy")
        != e8d.EXPECTED_RUNTIME_ARTIFACTS[task]["world_model_policy"]
        or value.get("world_model_checkpoint_sha256")
        != e8d.EXPECTED_RUNTIME_ARTIFACTS[task]["world_model_checkpoint_sha256"]
        or value.get("d2_read") is not True
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
        or not isinstance(config, dict)
        or config.get("task") != task
        or config.get("arm") != arm
        or any(config.get(key) != item for key, item in expected.items())
    ):
        raise RuntimeError(f"invalid E8D summary: {path}")
    validate_lineage(value, task=task, arm=arm)
    expected_solver = 100 if arm.endswith("_select") else 3000 if arm not in {"b0", "acid"} else 0
    expected_cost = 3000 if arm == "acid" else 0
    expected_proposal = 100 if arm.endswith("_select") or arm == "gadr_true_first" else 3000 if arm in e8d.PROPOSAL_ARMS else 0
    if (
        value.get("solver_diagnostic_count") != expected_solver
        or value.get("cost_diagnostic_count") != expected_cost
        or value.get("proposal_diagnostic_count") != expected_proposal
    ):
        raise RuntimeError(f"E8D diagnostic call count differs: {path}")
    for path_key, hash_key in (
        ("episodes_tsv", "episodes_tsv_sha256"),
        ("solver_diagnostics", "solver_diagnostics_sha256"),
        ("proposal_diagnostics", "proposal_diagnostics_sha256"),
        ("cost_diagnostics", "cost_diagnostics_sha256"),
    ):
        artifact = Path(value[path_key])
        e8d.reject_protected_path(artifact)
        if not artifact.is_file() or d2.sha256_file(artifact) != value.get(hash_key):
            raise RuntimeError(f"E8D output hash differs: {path_key}")
    diagnostic_summary = validate_diagnostics(value, arm=arm)
    success, starts = read_episodes(Path(value["episodes_tsv"]), task=task, arm=arm)
    metric_success = np.asarray(
        value.get("metrics", {}).get("episode_successes", []), dtype=np.float64
    )
    if (
        int(success.sum()) != int(value["success_count"])
        or not math.isclose(
            float(success.mean()),
            float(value.get("success_rate_fraction", math.nan)),
            rel_tol=0.0,
            abs_tol=1.0e-15,
        )
        or metric_success.shape != (EVAL_COUNT,)
        or not np.array_equal(success, metric_success)
    ):
        raise RuntimeError(f"E8D success count differs: {path}")
    return {
        "success": success,
        "starts": starts,
        "summary": str(path),
        "summary_sha256": d2.sha256_file(path),
        "dataset_sha256": value["dataset_sha256"],
        "world_model_checkpoint_sha256": value["world_model_checkpoint_sha256"],
        "eval_manifest_sha256": value["eval_manifest_sha256"],
        "eval_provenance_sha256": value["eval_provenance_sha256"],
        "elapsed_seconds": float(value["elapsed_seconds"]),
        "proposal_seconds_total": float(value["proposal_seconds_total"]),
        "diagnostics": diagnostic_summary,
    }


def bootstrap_indices() -> dict[str, np.ndarray]:
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    return {
        task: generator.integers(
            0,
            EVAL_COUNT,
            size=(BOOTSTRAP_REPETITIONS, EVAL_COUNT),
            dtype=np.int16,
        )
        for task in TASKS
    }


def summarize(vectors: dict[str, np.ndarray], indices: dict[str, np.ndarray]) -> dict[str, Any]:
    boot = {task: vectors[task][indices[task]].mean(axis=1) for task in TASKS}
    equal = np.stack([boot[task] for task in TASKS]).mean(axis=0)

    def interval(values: np.ndarray) -> dict[str, float]:
        return {
            "lower_95_two_sided": float(np.quantile(values, 0.025)),
            "upper_95_two_sided": float(np.quantile(values, 0.975)),
            "lower_95_one_sided": float(np.quantile(values, 0.05)),
            "upper_95_one_sided": float(np.quantile(values, 0.95)),
        }

    return {
        "per_task": {
            task: {"estimate": float(vectors[task].mean()), **interval(boot[task])}
            for task in TASKS
        },
        "equal_task": {
            "estimate": float(np.mean([vectors[task].mean() for task in TASKS])),
            **interval(equal),
        },
    }


def exact_sign(vector: np.ndarray) -> dict[str, Any]:
    positive = int(np.count_nonzero(vector > 0))
    negative = int(np.count_nonzero(vector < 0))
    ties = int(np.count_nonzero(vector == 0))
    trials = positive + negative
    if trials == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(trials, index) for index in range(min(positive, negative) + 1))
        p_value = min(1.0, 2.0 * tail / (2.0**trials))
    return {
        "positive": positive,
        "negative": negative,
        "ties": ties,
        "two_sided_p": p_value,
    }


def contrast(
    matrices: dict[str, dict[str, np.ndarray]],
    indices: dict[str, np.ndarray],
    treatment: str,
    control: str,
) -> dict[str, Any]:
    difference = {
        task: matrices[treatment][task] - matrices[control][task] for task in TASKS
    }
    return {
        **summarize(difference, indices),
        "exact_sign": {
            **{task: exact_sign(difference[task]) for task in TASKS},
            "all_task_start_pairs": exact_sign(
                np.concatenate([difference[task] for task in TASKS])
            ),
        },
    }


def gate_results(contrasts: dict[str, Any]) -> tuple[dict[str, bool], dict[str, bool]]:
    refresh_acid = contrasts["gadr_true_refresh_minus_acid"]
    refresh_b0 = contrasts["gadr_true_refresh_minus_b0"]
    refresh_gaussian = contrasts["gadr_true_refresh_minus_gaussian_refresh"]
    refresh_shuffled = contrasts[
        "gadr_true_refresh_minus_gadr_shuffled_refresh"
    ]
    refresh = {
        "1_true_refresh_above_acid_equal_task": refresh_acid["equal_task"]["estimate"] > 0,
        "2_true_refresh_above_b0_equal_task": refresh_b0["equal_task"]["estimate"] > 0,
        "3_true_refresh_above_gaussian_equal_task": refresh_gaussian["equal_task"]["estimate"] > 0,
        "4_true_refresh_above_shuffled_equal_task": refresh_shuffled["equal_task"]["estimate"] > 0,
        "5_true_refresh_above_shuffled_at_least_two_tasks": sum(
            refresh_shuffled["per_task"][task]["estimate"] > 0 for task in TASKS
        ) >= 2,
        "6_true_refresh_within_010_acid_each_task": all(
            refresh_acid["per_task"][task]["estimate"] >= -0.10 for task in TASKS
        ),
        "7_integrity_and_b0_replay": True,
    }
    select_acid = contrasts["gadr_true_select_minus_acid"]
    select_b0 = contrasts["gadr_true_select_minus_b0"]
    select_gaussian = contrasts["gadr_true_select_minus_gaussian_select"]
    select_shuffled = contrasts["gadr_true_select_minus_gadr_shuffled_select"]
    selector = {
        "1_true_select_above_gaussian_equal_task": select_gaussian["equal_task"]["estimate"] > 0,
        "2_true_select_above_shuffled_equal_task": select_shuffled["equal_task"]["estimate"] > 0,
        "3_true_select_above_b0_equal_task": select_b0["equal_task"]["estimate"] > 0,
        "4_true_select_within_005_acid_equal_task": select_acid["equal_task"]["estimate"] >= -0.05,
        "5_true_select_above_shuffled_at_least_two_tasks": sum(
            select_shuffled["per_task"][task]["estimate"] > 0 for task in TASKS
        ) >= 2,
        "6_integrity_and_b0_replay": True,
    }
    return refresh, selector


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--method-protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--e8a-aggregate", type=Path, required=True)
    parser.add_argument("--run", nargs=3, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.protocol,
        args.method_protocol,
        args.source_manifest,
        args.e8a_aggregate,
        args.output_dir,
    ):
        e8d.reject_protected_path(path)
    snapshot_root = Path(__file__).resolve().parent
    if (
        args.protocol.resolve()
        != (
            snapshot_root
            / "ACID-ALTERNATIVE-E8D-GADR-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md"
        ).resolve()
        or args.method_protocol.resolve()
        != (snapshot_root / "ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md").resolve()
        or args.source_manifest.resolve()
        != (snapshot_root / "SOURCE-MANIFEST.sha256").resolve()
    ):
        raise RuntimeError("E8D analysis files are not from the executing snapshot")
    if (
        d2.sha256_file(args.protocol) != e8d.E8D_PROTOCOL_SHA256
        or d2.sha256_file(args.method_protocol) != d2.PROTOCOL_SHA256
        or d2.sha256_file(args.e8a_aggregate) != e8d.E8A_AGGREGATE_SHA256
    ):
        raise RuntimeError("E8D analysis prerequisite hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E8D analysis output")
    identities = [parse_run(values) for values in args.run]
    expected = {(task, arm) for task in TASKS for arm in ARMS}
    if len(identities) != len(expected) or {(task, arm) for task, arm, _ in identities} != expected:
        raise RuntimeError("E8D requires exactly 30 unique runs")
    source_hash = d2.sha256_file(args.source_manifest)
    runs = {
        (task, arm): load_run(identity, source_manifest_sha256=source_hash)
        for identity in identities
        for task, arm, _ in (identity,)
    }
    for task in TASKS:
        reference = runs[(task, "b0")]
        for arm in ARMS:
            run = runs[(task, arm)]
            if (
                run["starts"] != reference["starts"]
                or run["dataset_sha256"] != reference["dataset_sha256"]
                or run["world_model_checkpoint_sha256"]
                != reference["world_model_checkpoint_sha256"]
                or run["eval_manifest_sha256"] != reference["eval_manifest_sha256"]
                or run["eval_provenance_sha256"] != reference["eval_provenance_sha256"]
            ):
                raise RuntimeError(f"E8D pairing differs: {task}/{arm}")
        if not np.array_equal(
            runs[(task, "b0")]["success"], runs[(task, "custom_b0")]["success"]
        ):
            raise RuntimeError(f"E8D custom B0 is not bit-identical: {task}")

    matrices = {
        arm: {task: runs[(task, arm)]["success"] for task in TASKS} for arm in ARMS
    }
    indices = bootstrap_indices()
    arm_results = {arm: summarize(matrices[arm], indices) for arm in ARMS}
    resource_results = {
        arm: {
            task: {
                "elapsed_seconds": runs[(task, arm)]["elapsed_seconds"],
                "proposal_seconds_total": runs[(task, arm)]["proposal_seconds_total"],
                **runs[(task, arm)]["diagnostics"],
            }
            for task in TASKS
        }
        for arm in ARMS
    }
    pairs = (
        ("gadr_true_refresh", "acid"),
        ("gadr_true_refresh", "b0"),
        ("gadr_true_refresh", "gaussian_refresh"),
        ("gadr_true_refresh", "gadr_shuffled_refresh"),
        ("gadr_true_select", "acid"),
        ("gadr_true_select", "b0"),
        ("gadr_true_select", "gaussian_select"),
        ("gadr_true_select", "gadr_shuffled_select"),
    )
    contrasts = {
        f"{treatment}_minus_{control}": contrast(
            matrices, indices, treatment, control
        )
        for treatment, control in pairs
    }
    refresh_gates, selector_gates = gate_results(contrasts)
    select_acid = contrasts["gadr_true_select_minus_acid"]
    refresh_pass = all(refresh_gates.values())
    selector_pass = all(selector_gates.values())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = args.output_dir / "runs.tsv"
    with runs_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "task",
                "arm",
                "success_rate",
                "elapsed_seconds",
                "proposal_seconds_total",
                "summary",
                "summary_sha256",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for task, arm, _ in sorted(identities):
            run = runs[(task, arm)]
            writer.writerow(
                {
                    "task": task,
                    "arm": arm,
                    "success_rate": float(run["success"].mean()),
                    "elapsed_seconds": run["elapsed_seconds"],
                    "proposal_seconds_total": run["proposal_seconds_total"],
                    "summary": run["summary"],
                    "summary_sha256": run["summary_sha256"],
                }
            )
    result = {
        "status": "ok",
        "kind": "gdp_cem_e8d_exposed_d2_closed_loop_analysis",
        "analysis_role": "post_E8A_exposed_D2_one_seed_development",
        "arm_results": arm_results,
        "resource_results": resource_results,
        "contrasts": contrasts,
        "refresh_gates": refresh_gates,
        "selector_gates": selector_gates,
        "refresh_route_pass": refresh_pass,
        "selector_route_pass": selector_pass,
        "selector_above_acid_point_estimate": select_acid["equal_task"]["estimate"] > 0,
        "decision": (
            "authorize_separately_frozen_multiseed_d2_gadr_replication"
            if refresh_pass or selector_pass
            else "stop_gadr_before_multiseed_or_fresh_data"
        ),
        "authorized_routes": [
            route
            for route, passed in (("refresh", refresh_pass), ("selector", selector_pass))
            if passed
        ],
        "bootstrap": {
            "repetitions": BOOTSTRAP_REPETITIONS,
            "seed": BOOTSTRAP_SEED,
            "unit": "paired episode start within task",
            "task_aggregation": "equal mean of three task estimates",
        },
        "runs_tsv": str(runs_path),
        "runs_tsv_sha256": d2.sha256_file(runs_path),
        "protocol_sha256": e8d.E8D_PROTOCOL_SHA256,
        "method_protocol_sha256": d2.PROTOCOL_SHA256,
        "e8a_aggregate_sha256": e8d.E8A_AGGREGATE_SHA256,
        "source_manifest_sha256": source_hash,
        "d2_read": True,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_dir / "summary.json", result)
    manifest = {
        "status": "ok",
        "kind": "gdp_cem_e8d_exposed_d2_closed_loop_manifest",
        "summary_sha256": d2.sha256_file(args.output_dir / "summary.json"),
        "runs_tsv_sha256": result["runs_tsv_sha256"],
        "source_manifest_sha256": source_hash,
        "protocol_sha256": e8d.E8D_PROTOCOL_SHA256,
        "d2_read": True,
        "d3_read": False,
        "protected_c1_i1_read": False,
    }
    atomic_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
