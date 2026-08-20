#!/usr/bin/env python3
"""Analyze the frozen E4 same-candidate D2A audit across all three tasks."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from acid_alt_e4_scoring import E4_P1_PROTOCOL_SHA256, sha256_file


TASKS = ("pusht", "reacher", "cube")
POOL_COUNT = 50
CANDIDATE_COUNT = 300
PRIMARY_ACID_SEED = 6101
ACID_SEEDS = (6101, 6102, 6103)
PRIMARY_LAMBDA = 0.07
SENSITIVITY_LAMBDAS = (0.02, 0.14)
SPREAD_EPSILON = 1.0e-8
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 20260816108
IMPLEMENTATION_FREEZE_SHA256 = (
    "193f5679ec91377c0d2411b9092cc4d2c8308d64f509917244d1b89dcb7354b9"
)


PRIMARY_METHODS = (
    "e4_cider_tail",
    "e4_dide",
    "e4_cider_raw",
    "e4_cider_mean_violation",
    "e4_shuffled_cider_tail_raw",
    "deterministic_inverse",
    "gaussian_nll",
    "gaussian_ratio",
    "gaussian_tail",
    "acid",
    "acid_flow",
    "acid_16_mean",
    "acid_16_min",
    "forward",
    "reachability",
)


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


def rankdata(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("rankdata requires a finite vector")
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and sorted_values[stop] == sorted_values[start]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * (start + stop - 1)
        start = stop
    return ranks


def safe_spearman(first: np.ndarray, second: np.ndarray) -> tuple[float, bool]:
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    if first.std(ddof=1) <= SPREAD_EPSILON:
        return 0.0, True
    left, right = rankdata(first), rankdata(second)
    if right.std(ddof=0) <= 0:
        raise RuntimeError("physical RMSE collapsed within a pool")
    return float(np.corrcoef(left, right)[0, 1]), False


def parse_task(values: list[str]) -> tuple[str, Path, Path]:
    if len(values) != 3:
        raise ValueError("task requires TASK ARTIFACT MANIFEST")
    task, artifact, manifest = values
    if task not in TASKS:
        raise ValueError(f"unexpected task {task}")
    return task, Path(artifact), Path(manifest)


def load_task(
    task: str,
    artifact_path: Path,
    manifest_path: Path,
    *,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    for path in (artifact_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("kind") != "acid_alt_e4_d2a_task_scores"
        or manifest.get("analysis_role")
        != "post-E3 exposed D2 exploratory development"
        or manifest.get("task") != task
        or manifest.get("pool_count") != POOL_COUNT
        or manifest.get("candidates_per_pool") != CANDIDATE_COUNT
        or manifest.get("primary_e4_seed") != 7101
        or manifest.get("primary_acid_seed") != PRIMARY_ACID_SEED
        or manifest.get("parent_protocol_sha256") != E4_P1_PROTOCOL_SHA256
        or manifest.get("implementation_freeze_sha256")
        != IMPLEMENTATION_FREEZE_SHA256
        or manifest.get("source_manifest_sha256") != source_manifest_sha256
        or manifest.get("protected_c1_i1_read") is not False
        or manifest.get("confirmation_claim_allowed") is not False
        or manifest.get("shuffled_deployment_reliability") != 0
        or sha256_file(artifact_path) != manifest.get("artifact_sha256")
    ):
        raise RuntimeError(f"{task}: invalid E4-D2A score artifact")
    with np.load(artifact_path, allow_pickle=False) as archive:
        arrays = {key: np.asarray(archive[key]) for key in archive.files}
    required = {
        "goal",
        "standardized_rmse",
        "success",
        "e4_cider_tail",
        "e4_dide",
        "e4_cider_raw",
        "e4_cider_mean_violation",
        "e4_shuffled_cider_tail_raw",
        "deterministic_inverse",
        "gaussian_nll",
        "gaussian_ratio",
        "gaussian_tail",
    }
    for seed in ACID_SEEDS:
        required.update(
            {
                f"acid_seed_{seed}",
                f"acid_flow_seed_{seed}",
                f"acid_16_mean_seed_{seed}",
                f"acid_16_min_seed_{seed}",
                f"forward_seed_{seed}",
                f"reachability_seed_{seed}",
            }
        )
    if not required.issubset(arrays):
        raise RuntimeError(f"{task}: incomplete E4-D2A archive")
    for name in required:
        values = arrays[name]
        if values.shape != (POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError(f"{task}/{name}: unexpected shape {values.shape}")
        if not np.isfinite(values).all():
            raise RuntimeError(f"{task}/{name}: non-finite values")
    methods = {
        "e4_cider_tail": arrays["e4_cider_tail"],
        "e4_dide": arrays["e4_dide"],
        "e4_cider_raw": arrays["e4_cider_raw"],
        "e4_cider_mean_violation": arrays["e4_cider_mean_violation"],
        "e4_shuffled_cider_tail_raw": arrays["e4_shuffled_cider_tail_raw"],
        "deterministic_inverse": arrays["deterministic_inverse"],
        "gaussian_nll": arrays["gaussian_nll"],
        "gaussian_ratio": arrays["gaussian_ratio"],
        "gaussian_tail": arrays["gaussian_tail"],
        "acid": arrays[f"acid_seed_{PRIMARY_ACID_SEED}"],
        "acid_flow": arrays[f"acid_flow_seed_{PRIMARY_ACID_SEED}"],
        "acid_16_mean": arrays[f"acid_16_mean_seed_{PRIMARY_ACID_SEED}"],
        "acid_16_min": arrays[f"acid_16_min_seed_{PRIMARY_ACID_SEED}"],
        "forward": arrays[f"forward_seed_{PRIMARY_ACID_SEED}"],
        "reachability": arrays[f"reachability_seed_{PRIMARY_ACID_SEED}"],
    }
    correlations: dict[str, np.ndarray] = {}
    enrichments: dict[str, np.ndarray] = {}
    collapsed: dict[str, np.ndarray] = {}
    rmse = arrays["standardized_rmse"].astype(np.float64)
    top_count = CANDIDATE_COUNT // 10
    for method, score in methods.items():
        correlations[method] = np.empty(POOL_COUNT, dtype=np.float64)
        enrichments[method] = np.empty(POOL_COUNT, dtype=np.float64)
        collapsed[method] = np.zeros(POOL_COUNT, dtype=bool)
        for pool in range(POOL_COUNT):
            correlation, is_collapsed = safe_spearman(score[pool], rmse[pool])
            correlations[method][pool] = correlation
            collapsed[method][pool] = is_collapsed
            if is_collapsed:
                enrichments[method][pool] = 0.0
            else:
                order = np.argsort(score[pool], kind="mergesort")
                enrichments[method][pool] = (
                    rmse[pool, order[-top_count:]].mean() - rmse[pool].mean()
                )
    sensitivity: dict[str, dict[int, np.ndarray]] = {}
    for family, prefix in (
        ("acid", "acid_seed"),
        ("acid_flow", "acid_flow_seed"),
        ("acid_16_mean", "acid_16_mean_seed"),
        ("acid_16_min", "acid_16_min_seed"),
        ("forward", "forward_seed"),
        ("reachability", "reachability_seed"),
    ):
        sensitivity[family] = {}
        for seed in ACID_SEEDS:
            matrix = np.asarray(arrays[f"{prefix}_{seed}"], dtype=np.float64)
            sensitivity[family][seed] = np.asarray(
                [safe_spearman(matrix[pool], rmse[pool])[0] for pool in range(POOL_COUNT)]
            )
    return {
        "arrays": arrays,
        "methods": methods,
        "correlations": correlations,
        "enrichments": enrichments,
        "collapsed": collapsed,
        "sensitivity": sensitivity,
        "manifest": manifest,
        "input": {
            "artifact": str(artifact_path),
            "artifact_sha256": sha256_file(artifact_path),
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
        },
    }


def bootstrap_indices() -> dict[str, np.ndarray]:
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    return {
        task: generator.integers(
            0,
            POOL_COUNT,
            size=(BOOTSTRAP_REPETITIONS, POOL_COUNT),
            dtype=np.int16,
        )
        for task in TASKS
    }


def summarize(
    vectors: dict[str, np.ndarray], indices: dict[str, np.ndarray]
) -> dict[str, Any]:
    draws = []
    per_task: dict[str, Any] = {}
    for task in TASKS:
        values = np.asarray(vectors[task], dtype=np.float64)
        if values.shape != (POOL_COUNT,) or not np.isfinite(values).all():
            raise RuntimeError(f"{task}: invalid bootstrap vector")
        task_draw = values[indices[task]].mean(axis=1)
        draws.append(task_draw)
        per_task[task] = {
            "estimate": float(values.mean()),
            "lower_95_two_sided": float(np.quantile(task_draw, 0.025)),
            "upper_95_two_sided": float(np.quantile(task_draw, 0.975)),
            "lower_95_one_sided": float(np.quantile(task_draw, 0.05)),
            "upper_95_one_sided": float(np.quantile(task_draw, 0.95)),
        }
    equal_draw = np.stack(draws).mean(axis=0)
    return {
        "equal_task": {
            "estimate": float(np.mean([vectors[task].mean() for task in TASKS])),
            "lower_95_two_sided": float(np.quantile(equal_draw, 0.025)),
            "upper_95_two_sided": float(np.quantile(equal_draw, 0.975)),
            "lower_95_one_sided": float(np.quantile(equal_draw, 0.05)),
            "upper_95_one_sided": float(np.quantile(equal_draw, 0.95)),
        },
        "per_task": per_task,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "cluster_unit": "D2 start",
        "task_weighting": "equal",
    }


def select_candidate(goal: np.ndarray, score: np.ndarray, weight: float) -> int:
    goal_spread = float(goal.std(ddof=1))
    score_spread = float(score.std(ddof=1))
    if score_spread <= SPREAD_EPSILON:
        return int(np.argmin(goal))
    if goal_spread <= 0:
        raise RuntimeError("goal cost collapsed")
    combined = goal + weight * goal_spread / score_spread * score
    if not np.isfinite(combined).all():
        raise RuntimeError("combined candidate cost is non-finite")
    return int(np.argmin(combined))


def selection_vectors(
    task: dict[str, Any], method: str, *, weight: float
) -> dict[str, np.ndarray]:
    arrays = task["arrays"]
    goal = arrays["goal"].astype(np.float64)
    rmse = arrays["standardized_rmse"].astype(np.float64)
    success = arrays["success"].astype(np.float64)
    if method == "b0" or method == "e4_shuffled_deployment":
        score = None
    else:
        score = task["methods"][method]
    selected_rmse = np.empty(POOL_COUNT, dtype=np.float64)
    selected_success = np.empty(POOL_COUNT, dtype=np.float64)
    selected_regret = np.empty(POOL_COUNT, dtype=np.float64)
    selected_index = np.empty(POOL_COUNT, dtype=np.int16)
    for pool in range(POOL_COUNT):
        index = (
            int(np.argmin(goal[pool]))
            if score is None
            else select_candidate(goal[pool], score[pool], weight)
        )
        selected_index[pool] = index
        selected_rmse[pool] = rmse[pool, index]
        selected_success[pool] = success[pool, index]
        selected_regret[pool] = rmse[pool, index] - rmse[pool].min()
    return {
        "rmse": selected_rmse,
        "success": selected_success,
        "oracle_regret": selected_regret,
        "index": selected_index,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-protocol", type=Path, required=True)
    parser.add_argument("--implementation-freeze", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--p1-gate", type=Path, required=True)
    parser.add_argument(
        "--task",
        nargs=3,
        action="append",
        metavar=("TASK", "ARTIFACT", "MANIFEST"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.parent_protocol,
        args.implementation_freeze,
        args.source_manifest,
        args.p1_gate,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.parent_protocol) != E4_P1_PROTOCOL_SHA256:
        raise RuntimeError("E4 parent protocol hash mismatch")
    if sha256_file(args.implementation_freeze) != IMPLEMENTATION_FREEZE_SHA256:
        raise RuntimeError("E4-D2A implementation-freeze hash mismatch")
    gate = json.loads(args.p1_gate.read_text(encoding="utf-8"))
    if (
        gate.get("status") != "ok"
        or gate.get("kind") != "e4_p1_mechanism_gate"
        or gate.get("all_e4_p1_gates_pass") is not True
        or gate.get("decision") != "advance_to_e4_d2a_exposed_candidate_audit"
        or gate.get("protocol_sha256") != E4_P1_PROTOCOL_SHA256
        or gate.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("invalid E4-P1 gate")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E4-D2A analysis output")
    parsed = [parse_task(value) for value in args.task]
    if len(parsed) != len(TASKS) or {value[0] for value in parsed} != set(TASKS):
        raise RuntimeError("E4-D2A requires exactly one artifact per task")
    source_manifest_sha256 = sha256_file(args.source_manifest)
    tasks = {
        task: load_task(
            task,
            artifact,
            manifest,
            source_manifest_sha256=source_manifest_sha256,
        )
        for task, artifact, manifest in parsed
    }
    indices = bootstrap_indices()

    rank_levels = {
        method: summarize(
            {task: tasks[task]["correlations"][method] for task in TASKS}, indices
        )
        for method in PRIMARY_METHODS
    }
    enrichment_levels = {
        method: summarize(
            {task: tasks[task]["enrichments"][method] for task in TASKS}, indices
        )
        for method in PRIMARY_METHODS
    }
    rank_contrasts = {}
    for comparator in (
        "e4_shuffled_cider_tail_raw",
        "acid",
        "acid_flow",
        "acid_16_mean",
        "acid_16_min",
        "deterministic_inverse",
        "gaussian_tail",
        "forward",
        "reachability",
    ):
        rank_contrasts[f"e4_cider_tail_minus_{comparator}"] = summarize(
            {
                task: tasks[task]["correlations"]["e4_cider_tail"]
                - tasks[task]["correlations"][comparator]
                for task in TASKS
            },
            indices,
        )

    selection_methods = (
        "b0",
        "e4_cider_tail",
        "e4_dide",
        "e4_cider_raw",
        "e4_cider_mean_violation",
        "e4_shuffled_deployment",
        "deterministic_inverse",
        "gaussian_nll",
        "gaussian_ratio",
        "gaussian_tail",
        "acid",
        "acid_flow",
        "acid_16_mean",
        "acid_16_min",
        "forward",
        "reachability",
    )
    selected = {
        task: {
            method: selection_vectors(tasks[task], method, weight=PRIMARY_LAMBDA)
            for method in selection_methods
        }
        for task in TASKS
    }
    selection_levels = {
        method: {
            metric: summarize(
                {task: selected[task][method][metric] for task in TASKS}, indices
            )
            for metric in ("success", "rmse", "oracle_regret")
        }
        for method in selection_methods
    }
    selection_contrasts = {}
    for comparator in (
        "b0",
        "acid",
        "acid_flow",
        "acid_16_mean",
        "acid_16_min",
        "deterministic_inverse",
        "gaussian_tail",
        "forward",
        "reachability",
    ):
        for metric in ("success", "rmse", "oracle_regret"):
            selection_contrasts[
                f"e4_cider_tail_minus_{comparator}_{metric}"
            ] = summarize(
                {
                    task: selected[task]["e4_cider_tail"][metric]
                    - selected[task][comparator][metric]
                    for task in TASKS
                },
                indices,
            )

    lambda_sensitivity: dict[str, Any] = {}
    for weight in SENSITIVITY_LAMBDAS:
        label = f"{weight:g}"
        lambda_sensitivity[label] = {}
        for method in ("e4_cider_tail", "acid"):
            values = {
                task: selection_vectors(tasks[task], method, weight=weight)
                for task in TASKS
            }
            lambda_sensitivity[label][method] = {
                metric: summarize(
                    {task: values[task][metric] for task in TASKS}, indices
                )
                for metric in ("success", "rmse", "oracle_regret")
            }

    seed_sensitivity = {
        family: {
            str(seed): summarize(
                {
                    task: tasks[task]["sensitivity"][family][seed]
                    for task in TASKS
                },
                indices,
            )
            for seed in ACID_SEEDS
        }
        for family in (
            "acid",
            "acid_flow",
            "acid_16_mean",
            "acid_16_min",
            "forward",
            "reachability",
        )
    }
    collapse_counts = {
        method: {
            task: int(tasks[task]["collapsed"][method].sum()) for task in TASKS
        }
        for method in PRIMARY_METHODS
    }

    primary_rank = rank_levels["e4_cider_tail"]
    versus_shuffled = rank_contrasts[
        "e4_cider_tail_minus_e4_shuffled_cider_tail_raw"
    ]
    versus_acid = rank_contrasts["e4_cider_tail_minus_acid"]
    e4_success = selection_levels["e4_cider_tail"]["success"]["equal_task"][
        "estimate"
    ]
    b0_success = selection_levels["b0"]["success"]["equal_task"]["estimate"]
    acid_success = selection_levels["acid"]["success"]["equal_task"]["estimate"]
    gates = {
        "1_positive_rank_all_tasks": all(
            primary_rank["per_task"][task]["estimate"] > 0 for task in TASKS
        ),
        "2_equal_task_rank_lower_95_above_zero": primary_rank["equal_task"][
            "lower_95_two_sided"
        ]
        > 0,
        "3_beats_shuffled_lower_95_above_zero": versus_shuffled["equal_task"][
            "lower_95_two_sided"
        ]
        > 0,
        "4_rank_noninferior_acid_margin_0_03": versus_acid["equal_task"][
            "lower_95_one_sided"
        ]
        > -0.03,
        "5_selection_success_not_below_b0_or_acid": (
            e4_success >= b0_success and e4_success >= acid_success - 0.03
        ),
    }
    all_pass = all(gates.values())
    diffusion_specific_gates = {
        comparator: {
            "higher_point_estimate": (
                rank_levels["e4_cider_tail"]["equal_task"]["estimate"]
                > rank_levels[comparator]["equal_task"]["estimate"]
            ),
            "one_sided_lower_bound_above_minus_0_03": (
                rank_contrasts[f"e4_cider_tail_minus_{comparator}"]["equal_task"][
                    "lower_95_one_sided"
                ]
                > -0.03
            ),
        }
        for comparator in ("deterministic_inverse", "gaussian_tail")
    }
    diffusion_specific_interpretation = all(
        all(values.values()) for values in diffusion_specific_gates.values()
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "pool-level.tsv"
    with detail_path.open("x", newline="", encoding="utf-8") as stream:
        fields = ["task", "pool"]
        for method in PRIMARY_METHODS:
            fields.extend(
                (
                    f"{method}_rank",
                    f"{method}_top_decile_enrichment",
                    f"{method}_collapsed",
                )
            )
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for task in TASKS:
            for pool in range(POOL_COUNT):
                row: dict[str, Any] = {"task": task, "pool": pool}
                for method in PRIMARY_METHODS:
                    row.update(
                        {
                            f"{method}_rank": tasks[task]["correlations"][method][pool],
                            f"{method}_top_decile_enrichment": tasks[task][
                                "enrichments"
                            ][method][pool],
                            f"{method}_collapsed": int(
                                tasks[task]["collapsed"][method][pool]
                            ),
                        }
                    )
                writer.writerow(row)

    summary = {
        "status": "ok",
        "kind": "acid_alt_e4_d2a_analysis",
        "analysis_role": "post-E3 exposed D2 exploratory development",
        "rank_levels": rank_levels,
        "rank_contrasts": rank_contrasts,
        "top_decile_rmse_enrichment": enrichment_levels,
        "selection_levels": selection_levels,
        "selection_contrasts": selection_contrasts,
        "lambda_sensitivity": lambda_sensitivity,
        "legacy_seed_sensitivity": seed_sensitivity,
        "collapsed_pool_counts": collapse_counts,
        "gates": gates,
        "all_d2a_gates_pass": all_pass,
        "decision": "authorize_e4_d2b_closed_loop" if all_pass else "stop_before_e4_d2b",
        "diffusion_specific_interpretation_gates": diffusion_specific_gates,
        "diffusion_specific_interpretation_allowed": diffusion_specific_interpretation,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "inputs": {task: tasks[task]["input"] for task in TASKS},
        "p1_gate": str(args.p1_gate),
        "p1_gate_sha256": sha256_file(args.p1_gate),
        "pool_level_tsv": str(detail_path),
        "pool_level_tsv_sha256": sha256_file(detail_path),
        "parent_protocol": str(args.parent_protocol),
        "parent_protocol_sha256": sha256_file(args.parent_protocol),
        "implementation_freeze": str(args.implementation_freeze),
        "implementation_freeze_sha256": sha256_file(args.implementation_freeze),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_manifest_sha256,
        "protected_c1_i1_read": False,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, summary)
    if all_pass:
        atomic_json(
            args.output_dir / "e4-d2b-authorization.json",
            {
                "status": "authorized",
                "kind": "acid_alt_e4_d2b_authorization",
                "d2a_summary": str(summary_path),
                "d2a_summary_sha256": sha256_file(summary_path),
                "parent_protocol_sha256": E4_P1_PROTOCOL_SHA256,
                "implementation_freeze_sha256": IMPLEMENTATION_FREEZE_SHA256,
                "source_manifest_sha256": source_manifest_sha256,
                "protected_c1_i1_read": False,
                "confirmation_claim_allowed": False,
            },
        )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
