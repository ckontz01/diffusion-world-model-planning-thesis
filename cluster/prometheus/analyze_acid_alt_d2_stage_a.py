#!/usr/bin/env python3
"""Prospectively analyze the frozen multi-seed D2 same-candidate audit."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_d2_models as d2


TASKS = ("pusht", "reacher", "cube")
POOL_COUNT = 50
CANDIDATE_COUNT = 300
BOOTSTRAP_SEED = 2026081604
BOOTSTRAP_REPETITIONS = 100_000


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


def spearman(first: np.ndarray, second: np.ndarray) -> float:
    left, right = rankdata(first), rankdata(second)
    if left.std(ddof=0) <= 0 or right.std(ddof=0) <= 0:
        raise RuntimeError("Spearman input collapsed")
    return float(np.corrcoef(left, right)[0, 1])


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
        or manifest.get("kind") != "acid_alt_v3_d2_task_endpoint_scores"
        or manifest.get("analysis_role") != "D2"
        or manifest.get("task") != task
        or manifest.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or manifest.get("source_manifest_sha256") != source_manifest_sha256
        or manifest.get("upstream_source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or manifest.get("d2_manifest_sha256")
        != manifest.get("eval_manifest_sha256")
        or manifest.get("protected_c1_i1_read") is not False
        or d2.sha256_file(artifact_path) != manifest.get("artifact_sha256")
    ):
        raise RuntimeError(f"{task}: invalid D2 endpoint artifact")
    with np.load(artifact_path, allow_pickle=False) as archive:
        arrays = {key: np.asarray(archive[key]) for key in archive.files}
    required = {"goal", "standardized_rmse", "success"}
    for seed in d2.SEEDS:
        required.update(
            {
                f"rdx_true_seed_{seed}",
                f"rdx_shuffled_seed_{seed}",
                f"ae_true_seed_{seed}",
                f"ae_shuffled_seed_{seed}",
                f"forward_seed_{seed}",
                f"acid_seed_{seed}",
                f"dtv_seed_{seed}",
                f"reachability_seed_{seed}",
            }
        )
    if not required.issubset(arrays):
        raise RuntimeError(f"{task}: D2 endpoint archive is incomplete")
    if arrays["goal"].shape != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError(f"{task}: goal-cost shape differs")
    if arrays["standardized_rmse"].shape != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError(f"{task}: physical-RMSE shape differs")
    if arrays["success"].shape != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError(f"{task}: success shape differs")
    methods: dict[str, np.ndarray] = {}
    for method in (
        "rdx_true",
        "rdx_shuffled",
        "ae_true",
        "ae_shuffled",
        "forward",
        "acid",
        "dtv",
        "reachability",
    ):
        values = np.stack([arrays[f"{method}_seed_{seed}"] for seed in d2.SEEDS])
        if values.shape != (3, POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError(f"{task}/{method}: score tensor shape differs")
        if not np.isfinite(values).all() or float(values.std(ddof=1)) <= 1.0e-8:
            raise RuntimeError(f"{task}/{method}: invalid score tensor")
        methods[method] = values.astype(np.float64, copy=False)
    correlations: dict[str, np.ndarray] = {}
    for method, values in methods.items():
        matrix = np.empty((3, POOL_COUNT), dtype=np.float64)
        for seed_index in range(3):
            for pool in range(POOL_COUNT):
                matrix[seed_index, pool] = spearman(
                    values[seed_index, pool], arrays["standardized_rmse"][pool]
                )
        correlations[method] = matrix
    return {
        "task": task,
        "arrays": arrays,
        "methods": methods,
        "correlations": correlations,
        "manifest": manifest,
        "input": {
            "artifact": str(artifact_path),
            "artifact_sha256": d2.sha256_file(artifact_path),
            "manifest": str(manifest_path),
            "manifest_sha256": d2.sha256_file(manifest_path),
            "eval_manifest_sha256": manifest["eval_manifest_sha256"],
            "dataset_sha256": manifest["dataset_sha256"],
            "world_model_checkpoint_sha256": manifest[
                "world_model_checkpoint_sha256"
            ],
        },
    }


def compute_profile(tasks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    method_names = (
        "residual_true_RDX_AE_joint",
        "residual_shuffled_RDX_AE_joint",
        "forward",
        "acid",
        "dtv",
        "reachability",
    )
    per_task: dict[str, Any] = {}
    pooled: dict[str, list[dict[str, float]]] = {name: [] for name in method_names}
    for task in TASKS:
        indexed: dict[str, dict[int, dict[str, Any]]] = {
            name: {} for name in method_names
        }
        for record in tasks[task]["manifest"].get("scorers", []):
            arm = record.get("arm")
            condition = record.get("condition")
            if arm == "residual_diffusion" and condition == "true":
                method = "residual_true_RDX_AE_joint"
            elif arm == "residual_diffusion" and condition == "shuffled_action":
                method = "residual_shuffled_RDX_AE_joint"
            elif arm in {"forward", "acid", "dtv", "reachability"}:
                method = arm
            else:
                raise RuntimeError(f"{task}: unexpected scorer record {record}")
            seed = int(record.get("seed", -1))
            latency = record.get("latency", {})
            parameter_count = int(record.get("parameter_count", 0))
            if (
                seed not in d2.SEEDS
                or seed in indexed[method]
                or parameter_count <= 0
                or latency.get("candidate_sequences") != POOL_COUNT * CANDIDATE_COUNT
                or latency.get("horizon_transitions")
                != POOL_COUNT * CANDIDATE_COUNT * 5
                or int(latency.get("network_pair_evaluations", 0)) <= 0
                or float(latency.get("elapsed_seconds", 0)) <= 0
                or float(latency.get("microseconds_per_horizon_transition", 0))
                <= 0
                or float(latency.get("microseconds_per_network_pair", 0))
                <= 0
            ):
                raise RuntimeError(f"{task}: invalid compute record for {method}")
            indexed[method][seed] = record
        task_profile: dict[str, Any] = {}
        for method in method_names:
            if set(indexed[method]) != set(d2.SEEDS):
                raise RuntimeError(f"{task}: incomplete compute profile for {method}")
            entries = []
            for seed in d2.SEEDS:
                record = indexed[method][seed]
                latency = record["latency"]
                entry = {
                    "seed": seed,
                    "parameter_count": int(record["parameter_count"]),
                    "elapsed_seconds": float(latency["elapsed_seconds"]),
                    "milliseconds_per_candidate_sequence": float(
                        latency["milliseconds_per_candidate_sequence"]
                    ),
                    "microseconds_per_horizon_transition": float(
                        latency["microseconds_per_horizon_transition"]
                    ),
                    "microseconds_per_network_pair": float(
                        latency["microseconds_per_network_pair"]
                    ),
                    "network_pairs_per_sequence": int(
                        latency["network_pairs_per_sequence"]
                    ),
                }
                entries.append(entry)
                pooled[method].append(entry)
            task_profile[method] = {
                "per_seed": entries,
                "mean_parameter_count": float(
                    np.mean([entry["parameter_count"] for entry in entries])
                ),
                "mean_elapsed_seconds": float(
                    np.mean([entry["elapsed_seconds"] for entry in entries])
                ),
                "mean_microseconds_per_horizon_transition": float(
                    np.mean(
                        [
                            entry["microseconds_per_horizon_transition"]
                            for entry in entries
                        ]
                    )
                ),
                "mean_microseconds_per_network_pair": float(
                    np.mean(
                        [
                            entry["microseconds_per_network_pair"]
                            for entry in entries
                        ]
                    )
                ),
            }
        per_task[task] = task_profile
    equal_task = {
        method: {
            "mean_elapsed_seconds": float(
                np.mean([entry["elapsed_seconds"] for entry in pooled[method]])
            ),
            "mean_microseconds_per_horizon_transition": float(
                np.mean(
                    [
                        entry["microseconds_per_horizon_transition"]
                        for entry in pooled[method]
                    ]
                )
            ),
            "mean_microseconds_per_network_pair": float(
                np.mean(
                    [
                        entry["microseconds_per_network_pair"]
                        for entry in pooled[method]
                    ]
                )
            ),
        }
        for method in method_names
    }
    return {
        "measurement": (
            "one warmup pool followed by one CUDA-synchronized full-D2 scorer pass; "
            "loading and the shared Le-WM rollout excluded; RDX and AE computed jointly"
        ),
        "candidate_sequences_per_measurement": POOL_COUNT * CANDIDATE_COUNT,
        "horizon_transitions_per_measurement": POOL_COUNT * CANDIDATE_COUNT * 5,
        "per_task": per_task,
        "equal_task_seed_mean": equal_task,
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
    matrices: dict[str, np.ndarray], indices: dict[str, np.ndarray]
) -> dict[str, Any]:
    draws: list[np.ndarray] = []
    per_task: dict[str, Any] = {}
    for task in TASKS:
        values = np.asarray(matrices[task], dtype=np.float64)
        if values.shape != (3, POOL_COUNT) or not np.isfinite(values).all():
            raise RuntimeError(f"{task}: invalid bootstrap matrix")
        task_draw = values[:, indices[task]].mean(axis=(0, 2))
        draws.append(task_draw)
        per_task[task] = {
            "estimate": float(values.mean()),
            "lower_95_two_sided": float(np.quantile(task_draw, 0.025)),
            "upper_95_two_sided": float(np.quantile(task_draw, 0.975)),
            "lower_95_one_sided": float(np.quantile(task_draw, 0.05)),
            "upper_95_one_sided": float(np.quantile(task_draw, 0.95)),
            "per_seed": {
                str(seed): float(values[index].mean())
                for index, seed in enumerate(d2.SEEDS)
            },
        }
    equal_draw = np.stack(draws).mean(axis=0)
    return {
        "equal_task": {
            "estimate": float(np.mean([matrices[task].mean() for task in TASKS])),
            "lower_95_two_sided": float(np.quantile(equal_draw, 0.025)),
            "upper_95_two_sided": float(np.quantile(equal_draw, 0.975)),
            "lower_95_one_sided": float(np.quantile(equal_draw, 0.05)),
            "upper_95_one_sided": float(np.quantile(equal_draw, 0.95)),
        },
        "per_task": per_task,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "cluster_unit": "D2 start; all three paired scorer seeds retained",
        "task_weighting": "equal",
    }


def summarize_single_task(
    values: np.ndarray, indices: np.ndarray
) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    if values.shape != (3, POOL_COUNT) or not np.isfinite(values).all():
        raise RuntimeError("invalid per-task selection matrix")
    draws = values[:, indices].mean(axis=(0, 2))
    return {
        "estimate": float(values.mean()),
        "lower_95_two_sided": float(np.quantile(draws, 0.025)),
        "upper_95_two_sided": float(np.quantile(draws, 0.975)),
        "lower_95_one_sided": float(np.quantile(draws, 0.05)),
        "upper_95_one_sided": float(np.quantile(draws, 0.95)),
        "per_seed": {
            str(seed): float(values[index].mean())
            for index, seed in enumerate(d2.SEEDS)
        },
    }


def adaptive_index(goal: np.ndarray, score: np.ndarray, weight: float) -> int:
    goal_spread = float(goal.std(ddof=1))
    score_spread = float(score.std(ddof=1))
    if goal_spread <= 0 or score_spread <= d2.SPREAD_EPSILON:
        raise RuntimeError("adaptive candidate-selection cost collapsed")
    combined = goal + weight * goal_spread / score_spread * score
    if not np.isfinite(combined).all():
        raise RuntimeError("adaptive candidate-selection cost is non-finite")
    return int(np.argmin(combined))


def selection_matrices(task_data: dict[str, Any]) -> dict[str, dict[str, np.ndarray]]:
    goal = task_data["arrays"]["goal"].astype(np.float64)
    rmse = task_data["arrays"]["standardized_rmse"].astype(np.float64)
    success = task_data["arrays"]["success"].astype(np.float64)
    optional_distances = {
        name: task_data["arrays"][name].astype(np.float64)
        for name in ("final_distance", "minimum_distance")
        if name in task_data["arrays"] and task_data["arrays"][name].size > 0
    }
    for name, values in optional_distances.items():
        if values.shape != (POOL_COUNT, CANDIDATE_COUNT) or not np.isfinite(
            values
        ).all():
            raise RuntimeError(f"invalid physical task-distance array: {name}")
    result: dict[str, dict[str, np.ndarray]] = {}
    specifications = {
        "b0": (None, 0.0),
        "rdx_true": (task_data["methods"]["rdx_true"], d2.DIFFUSION_LAMBDA),
        "ae_true": (task_data["methods"]["ae_true"], d2.DIFFUSION_LAMBDA),
        "ae_shuffled": (
            task_data["methods"]["ae_shuffled"],
            d2.DIFFUSION_LAMBDA,
        ),
        "forward": (task_data["methods"]["forward"], d2.DIFFUSION_LAMBDA),
        "acid": (task_data["methods"]["acid"], d2.ACID_LAMBDA),
        "dtv": (task_data["methods"]["dtv"], d2.DIFFUSION_LAMBDA),
        "reachability": (
            task_data["methods"]["reachability"],
            d2.ACID_LAMBDA,
        ),
    }
    for name, (scores, weight) in specifications.items():
        selected_rmse = np.empty((3, POOL_COUNT), dtype=np.float64)
        selected_success = np.empty_like(selected_rmse)
        selected_index = np.empty((3, POOL_COUNT), dtype=np.int16)
        selected_distances = {
            distance_name: np.empty((3, POOL_COUNT), dtype=np.float64)
            for distance_name in optional_distances
        }
        for seed_index in range(3):
            for pool in range(POOL_COUNT):
                index = (
                    int(np.argmin(goal[pool]))
                    if scores is None
                    else adaptive_index(goal[pool], scores[seed_index, pool], weight)
                )
                selected_index[seed_index, pool] = index
                selected_rmse[seed_index, pool] = rmse[pool, index]
                selected_success[seed_index, pool] = success[pool, index]
                for distance_name, distance_values in optional_distances.items():
                    selected_distances[distance_name][seed_index, pool] = (
                        distance_values[pool, index]
                    )
        result[name] = {
            "rmse": selected_rmse,
            "success": selected_success,
            "index": selected_index,
            **selected_distances,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
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
    for path in (args.protocol, args.source_manifest, args.p1_gate):
        if not path.is_file():
            raise FileNotFoundError(path)
    if d2.sha256_file(args.protocol) != d2.PROTOCOL_SHA256:
        raise RuntimeError("D2 protocol hash mismatch")
    p1_gate = json.loads(args.p1_gate.read_text(encoding="utf-8"))
    if (
        p1_gate.get("status") != "ok"
        or p1_gate.get("kind") != "acid_alt_v3_multiseed_p1_gate"
        or p1_gate.get("analysis_role") != "P1 only; before D2 outcome generation"
        or p1_gate.get("decision") != "authorize_D2"
        or p1_gate.get("all_pass") is not True
        or p1_gate.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or p1_gate.get("source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or p1_gate.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("P1 gate is not valid")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty Stage-A analysis output")
    parsed = [parse_task(values) for values in args.task]
    if {task for task, _, _ in parsed} != set(TASKS) or len(parsed) != len(TASKS):
        raise RuntimeError("Stage A requires exactly one artifact per task")
    source_manifest_sha256 = d2.sha256_file(args.source_manifest)
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
    scorer_compute_profile = compute_profile(tasks)

    rank_levels = {
        method: summarize(
            {task: tasks[task]["correlations"][method] for task in TASKS}, indices
        )
        for method in (
            "rdx_true",
            "rdx_shuffled",
            "ae_true",
            "ae_shuffled",
            "forward",
            "acid",
            "dtv",
            "reachability",
        )
    }
    rank_contrasts = {
        "rdx_minus_shuffled": summarize(
            {
                task: tasks[task]["correlations"]["rdx_true"]
                - tasks[task]["correlations"]["rdx_shuffled"]
                for task in TASKS
            },
            indices,
        ),
        "rdx_minus_forward": summarize(
            {
                task: tasks[task]["correlations"]["rdx_true"]
                - tasks[task]["correlations"]["forward"]
                for task in TASKS
            },
            indices,
        ),
        "rdx_minus_acid": summarize(
            {
                task: tasks[task]["correlations"]["rdx_true"]
                - tasks[task]["correlations"]["acid"]
                for task in TASKS
            },
            indices,
        ),
        "rdx_minus_dtv": summarize(
            {
                task: tasks[task]["correlations"]["rdx_true"]
                - tasks[task]["correlations"]["dtv"]
                for task in TASKS
            },
            indices,
        ),
        "rdx_minus_reachability": summarize(
            {
                task: tasks[task]["correlations"]["rdx_true"]
                - tasks[task]["correlations"]["reachability"]
                for task in TASKS
            },
            indices,
        ),
        "ae_minus_shuffled": summarize(
            {
                task: tasks[task]["correlations"]["ae_true"]
                - tasks[task]["correlations"]["ae_shuffled"]
                for task in TASKS
            },
            indices,
        ),
    }

    selected = {task: selection_matrices(tasks[task]) for task in TASKS}
    selection_levels: dict[str, Any] = {}
    for method in (
        "b0",
        "rdx_true",
        "ae_true",
        "ae_shuffled",
        "forward",
        "acid",
        "dtv",
        "reachability",
    ):
        selection_levels[method] = {
            metric: summarize(
                {task: selected[task][method][metric] for task in TASKS}, indices
            )
            for metric in ("success", "rmse")
        }
    selection_task_distance_levels = {
        task: {
            method: {
                metric: summarize_single_task(
                    selected[task][method][metric], indices[task]
                )
                for metric in ("final_distance", "minimum_distance")
                if metric in selected[task][method]
            }
            for method in (
                "b0",
                "rdx_true",
                "ae_true",
                "ae_shuffled",
                "forward",
                "acid",
                "dtv",
                "reachability",
            )
        }
        for task in TASKS
    }
    selection_contrasts = {
        "ae_minus_acid_success": summarize(
            {
                task: selected[task]["ae_true"]["success"]
                - selected[task]["acid"]["success"]
                for task in TASKS
            },
            indices,
        ),
        "ae_minus_acid_rmse": summarize(
            {
                task: selected[task]["ae_true"]["rmse"]
                - selected[task]["acid"]["rmse"]
                for task in TASKS
            },
            indices,
        ),
        "ae_minus_dtv_success": summarize(
            {
                task: selected[task]["ae_true"]["success"]
                - selected[task]["dtv"]["success"]
                for task in TASKS
            },
            indices,
        ),
        "ae_minus_dtv_rmse": summarize(
            {
                task: selected[task]["ae_true"]["rmse"]
                - selected[task]["dtv"]["rmse"]
                for task in TASKS
            },
            indices,
        ),
        "ae_minus_reachability_success": summarize(
            {
                task: selected[task]["ae_true"]["success"]
                - selected[task]["reachability"]["success"]
                for task in TASKS
            },
            indices,
        ),
        "ae_minus_reachability_rmse": summarize(
            {
                task: selected[task]["ae_true"]["rmse"]
                - selected[task]["reachability"]["rmse"]
                for task in TASKS
            },
            indices,
        ),
    }

    gates = {
        "1_rdx_positive_all_tasks_and_pooled": (
            all(
                rank_levels["rdx_true"]["per_task"][task]["estimate"] > 0
                for task in TASKS
            )
            and rank_levels["rdx_true"]["equal_task"]["lower_95_two_sided"] > 0
        ),
        "2_rdx_beats_shuffled": rank_contrasts["rdx_minus_shuffled"][
            "equal_task"
        ]["lower_95_two_sided"]
        > 0,
        "3_rdx_noninferior_forward_and_acid": (
            rank_contrasts["rdx_minus_forward"]["equal_task"][
                "lower_95_one_sided"
            ]
            > -0.03
            and rank_contrasts["rdx_minus_acid"]["equal_task"][
                "lower_95_one_sided"
            ]
            > -0.03
        ),
        "4_ae_beats_shuffled_without_negative_task": (
            rank_contrasts["ae_minus_shuffled"]["equal_task"][
                "lower_95_two_sided"
            ]
            > 0
            and all(
                rank_contrasts["ae_minus_shuffled"]["per_task"][task]["estimate"]
                >= 0
                for task in TASKS
            )
        ),
        "5_ae_selection_noninferior_acid": (
            selection_contrasts["ae_minus_acid_success"]["equal_task"][
                "lower_95_one_sided"
            ]
            > -0.05
            and selection_contrasts["ae_minus_acid_rmse"]["equal_task"][
                "upper_95_one_sided"
            ]
            < 0.02
        ),
    }
    all_pass = all(gates.values())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "pool-level.tsv"
    with detail_path.open("x", newline="", encoding="utf-8") as stream:
        fields = (
            "task",
            "seed",
            "pool",
            "rdx_true",
            "rdx_shuffled",
            "ae_true",
            "ae_shuffled",
            "forward",
            "acid",
            "dtv",
            "reachability",
        )
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for task in TASKS:
            for seed_index, seed in enumerate(d2.SEEDS):
                for pool in range(POOL_COUNT):
                    writer.writerow(
                        {
                            "task": task,
                            "seed": seed,
                            "pool": pool,
                            **{
                                name: tasks[task]["correlations"][name][seed_index, pool]
                                for name in (
                                    "rdx_true",
                                    "rdx_shuffled",
                                    "ae_true",
                                    "ae_shuffled",
                                    "forward",
                                    "acid",
                                    "dtv",
                                    "reachability",
                                )
                            },
                        }
                    )

    summary = {
        "status": "ok",
        "kind": "acid_alt_v3_d2_stage_a_analysis",
        "analysis_role": "fresh preregistered D2 development",
        "rank_levels": rank_levels,
        "rank_contrasts": rank_contrasts,
        "selection_levels": selection_levels,
        "selection_task_distance_levels": selection_task_distance_levels,
        "selection_contrasts": selection_contrasts,
        "scorer_compute_profile": scorer_compute_profile,
        "gates": gates,
        "all_stage_a_gates_pass": all_pass,
        "decision": "authorize_stage_b" if all_pass else "stop_before_stage_b",
        "inputs": {task: tasks[task]["input"] for task in TASKS},
        "p1_gate": str(args.p1_gate),
        "p1_gate_sha256": d2.sha256_file(args.p1_gate),
        "pool_level_tsv": str(detail_path),
        "pool_level_tsv_sha256": d2.sha256_file(detail_path),
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "upstream_source_manifest_sha256": (
            d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        ),
        "protected_c1_i1_read": False,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, summary)
    if all_pass:
        authorization = {
            "status": "authorized",
            "kind": "acid_alt_v3_d2_stage_b_authorization",
            "stage_a_summary": str(summary_path),
            "stage_a_summary_sha256": d2.sha256_file(summary_path),
            "protocol_sha256": d2.PROTOCOL_SHA256,
            "source_manifest_sha256": d2.sha256_file(args.source_manifest),
            "upstream_source_manifest_sha256": (
                d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
            ),
            "protected_c1_i1_read": False,
        }
        atomic_json(args.output_dir / "stage-b-authorization.json", authorization)
    atomic_json(
        args.output_dir / "manifest.json",
        {
            "status": "ok",
            "kind": "acid_alt_v3_d2_stage_a_manifest",
            "summary": str(summary_path),
            "summary_sha256": d2.sha256_file(summary_path),
            "pool_level_tsv_sha256": d2.sha256_file(detail_path),
            "stage_b_authorized": all_pass,
            "protocol_sha256": d2.PROTOCOL_SHA256,
            "source_manifest_sha256": d2.sha256_file(args.source_manifest),
            "upstream_source_manifest_sha256": (
                d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
            ),
            "protected_c1_i1_read": False,
        },
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
