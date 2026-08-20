#!/usr/bin/env python3
"""Analyze frozen same-candidate scores against physical execution outcomes."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from acid_alternative.io_utils import atomic_write_json, sha256_file


def rankdata(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("rankdata expects one-dimensional finite values")
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        average_rank = 0.5 * ((start + 1) + end)
        ranks[order[start:end]] = average_rank
        start = end
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    x_rank = rankdata(x)
    y_rank = rankdata(y)
    if np.std(x_rank) == 0 or np.std(y_rank) == 0:
        return float("nan")
    return float(np.corrcoef(x_rank, y_rank)[0, 1])


def finite_mean(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=np.float64)
    finite = values[np.isfinite(values)]
    return float(finite.mean()) if finite.size else None


def cluster_bootstrap_mean(
    values: np.ndarray, *, seed: int, repetitions: int = 10_000
) -> dict[str, float | int]:
    """Resample pool identities, preserving all scorer seeds per pool."""

    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("bootstrap values must be (seed,pool)")
    if not np.isfinite(values).all():
        raise ValueError("bootstrap values contain non-finite entries")
    generator = np.random.default_rng(seed)
    estimates = np.empty(repetitions, dtype=np.float64)
    for index in range(repetitions):
        sampled = generator.integers(0, values.shape[1], size=values.shape[1])
        estimates[index] = values[:, sampled].mean()
    return {
        "estimate": float(values.mean()),
        "lower_95": float(np.quantile(estimates, 0.025)),
        "upper_95": float(np.quantile(estimates, 0.975)),
        "bootstrap_repetitions": repetitions,
        "bootstrap_seed": seed,
    }


def condition_index(
    scores: dict[str, dict[str, Any]], arm: str, condition: str
) -> dict[int, str]:
    result: dict[int, str] = {}
    for label, record in scores.items():
        if record.get("arm") != arm or record.get("condition") != condition:
            continue
        seed = int(record["training_seed"])
        if seed in result:
            raise RuntimeError(f"duplicate {arm}/{condition}/seed-{seed}")
        result[seed] = label
    return result


def main() -> None:
    # Keep rank/bootstrap helpers usable in the CPU-only integrity suite.  Torch
    # is needed only for loading the scored candidate artifact below.
    import torch

    parser = argparse.ArgumentParser()
    parser.add_argument("--score-artifact", type=Path, required=True)
    parser.add_argument("--score-manifest", type=Path, required=True)
    parser.add_argument("--execution-h5", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--analysis-role", choices=("D1", "C1"), required=True)
    parser.add_argument("--bootstrap-seed", type=int, default=2026081301)
    parser.add_argument("--bootstrap-repetitions", type=int, default=10_000)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.score_artifact,
        args.score_manifest,
        args.execution_h5,
        args.execution_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if args.bootstrap_repetitions <= 0:
        raise ValueError("bootstrap repetitions must be positive")
    score_manifest = json.loads(args.score_manifest.read_text(encoding="utf-8"))
    execution_manifest = json.loads(args.execution_manifest.read_text(encoding="utf-8"))
    if score_manifest.get("status") != "ok" or sha256_file(
        args.score_artifact
    ) != score_manifest.get("artifact_sha256"):
        raise RuntimeError("score artifact does not match its manifest")
    if execution_manifest.get("status") != "ok" or sha256_file(
        args.execution_h5
    ) != execution_manifest.get("output_h5_sha256"):
        raise RuntimeError("execution HDF5 does not match its manifest")
    if score_manifest.get("candidate_artifact_sha256") != execution_manifest.get(
        "candidate_artifact_sha256"
    ):
        raise RuntimeError("scores and executions use different candidate pools")
    matching_fields = (
        "analysis_role",
        "confirmation_authorization_sha256",
        "candidate_manifest_sha256",
        "eval_manifest_sha256",
        "dataset_sha256",
        "world_model_checkpoint_sha256",
        "source_manifest_sha256",
    )
    for field in matching_fields:
        score_value = score_manifest.get(field)
        execution_value = execution_manifest.get(field)
        if score_value != execution_value or (
            field != "confirmation_authorization_sha256" and score_value is None
        ):
            raise RuntimeError(f"score/execution {field} mismatch")
    if score_manifest["analysis_role"] != args.analysis_role:
        raise RuntimeError("declared analysis role differs from candidate artifacts")
    authorization_hash = score_manifest["confirmation_authorization_sha256"]
    if (args.analysis_role == "C1") != (authorization_hash is not None):
        raise RuntimeError("candidate artifact authorization does not match role")

    artifact = torch.load(args.score_artifact, map_location="cpu", weights_only=False)
    if artifact.get("kind") != "flat_same_candidate_shared_rollout_scores":
        raise RuntimeError("unexpected score artifact kind")
    predicted = torch.as_tensor(artifact["predicted_trajectory"]).float().numpy()
    scores = artifact["scores"]
    with h5py.File(args.execution_h5, "r") as execution:
        executed = np.asarray(execution["executed_latent"][:], dtype=np.float32)
        final_distance = (
            np.asarray(execution["final_task_distance"][:], dtype=np.float32)
            if "final_task_distance" in execution
            else None
        )
        minimum_distance = (
            np.asarray(execution["minimum_task_distance"][:], dtype=np.float32)
            if "minimum_task_distance" in execution
            else None
        )
        success = np.asarray(execution["environment_success"][:], dtype=bool)
    if predicted.shape != executed.shape or predicted.ndim != 4:
        raise RuntimeError(
            f"predicted/executed latent shape mismatch: {predicted.shape}/{executed.shape}"
        )
    pool_count, candidate_count, _steps, latent_dim = predicted.shape
    if final_distance is not None and final_distance.shape != (
        pool_count,
        candidate_count,
    ):
        raise RuntimeError("physical metric shape differs from candidate pools")
    latent_std = artifact.get("transition_latent_std")
    if latent_std is None:
        raise RuntimeError("score artifact lacks frozen transition latent statistics")
    latent_std = torch.as_tensor(latent_std).float().numpy()
    if latent_std.shape != (latent_dim,) or np.any(latent_std <= 0):
        raise RuntimeError("invalid transition latent standard deviations")
    residual = predicted[:, :, 1:] - executed[:, :, 1:]
    raw_rollout_rmse = np.sqrt(np.mean(np.square(residual), axis=(2, 3)))
    standardized_rollout_rmse = np.sqrt(
        np.mean(np.square(residual / latent_std), axis=(2, 3))
    )
    terminal_latent_rmse = np.sqrt(
        np.mean(np.square(predicted[:, :, -1] - executed[:, :, -1]), axis=2)
    )
    metrics = {
        "standardized_rollout_rmse": standardized_rollout_rmse,
        "raw_rollout_rmse": raw_rollout_rmse,
        "terminal_latent_rmse": terminal_latent_rmse,
    }
    if final_distance is not None and minimum_distance is not None:
        metrics["final_task_distance"] = final_distance
        metrics["minimum_task_distance"] = minimum_distance

    detail_rows: list[dict[str, Any]] = []
    summary_by_label: dict[str, Any] = {}
    primary_correlations: dict[str, np.ndarray] = {}
    for label, record in scores.items():
        raw_cost = torch.as_tensor(record["raw_verifier_cost"]).float().numpy()
        combined = torch.as_tensor(record["combined_cost"]).float().numpy()
        if (
            raw_cost.shape != (pool_count, candidate_count)
            or combined.shape != raw_cost.shape
        ):
            raise RuntimeError(f"{label}: score tensor shape mismatch")
        label_correlations: dict[str, list[float]] = {key: [] for key in metrics}
        combined_correlations: dict[str, list[float]] = {key: [] for key in metrics}
        selected_values: dict[str, list[float]] = {key: [] for key in metrics}
        oracle_ranks: dict[str, list[float]] = {key: [] for key in metrics}
        raw_stds: list[float] = []
        for pool in range(pool_count):
            raw_stds.append(float(raw_cost[pool].std(ddof=1)))
            selected = int(np.argmin(combined[pool]))
            cost_ranks = rankdata(combined[pool])
            row: dict[str, Any] = {
                "label": label,
                "arm": record.get("arm"),
                "condition": record.get("condition"),
                "training_seed": record.get("training_seed"),
                "pool": pool,
                "selected_candidate": selected,
                "raw_cost_std": raw_stds[-1],
            }
            for metric_name, metric_values in metrics.items():
                raw_correlation = spearman(raw_cost[pool], metric_values[pool])
                combined_correlation = spearman(combined[pool], metric_values[pool])
                oracle = int(np.argmin(metric_values[pool]))
                oracle_rank = float(cost_ranks[oracle])
                selected_value = float(metric_values[pool, selected])
                label_correlations[metric_name].append(raw_correlation)
                combined_correlations[metric_name].append(combined_correlation)
                selected_values[metric_name].append(selected_value)
                oracle_ranks[metric_name].append(oracle_rank)
                row[f"raw_spearman_{metric_name}"] = raw_correlation
                row[f"combined_spearman_{metric_name}"] = combined_correlation
                row[f"selected_{metric_name}"] = selected_value
                row[f"oracle_best_rank_{metric_name}"] = oracle_rank
            row["selected_success"] = int(success[pool, selected])
            detail_rows.append(row)
        primary = np.asarray(
            label_correlations["standardized_rollout_rmse"], dtype=np.float64
        )
        primary_correlations[label] = primary
        summary_by_label[label] = {
            "arm": record.get("arm"),
            "condition": record.get("condition"),
            "training_seed": record.get("training_seed"),
            "checkpoint_sha256": record.get("checkpoint_sha256"),
            "parameter_count": record.get("parameter_count"),
            "cost_collapse_pool_fraction": float(
                np.mean(np.asarray(raw_stds) <= 1.0e-8)
            ),
            "mean_raw_spearman": {
                key: finite_mean(np.asarray(values))
                for key, values in label_correlations.items()
            },
            "mean_combined_spearman": {
                key: finite_mean(np.asarray(values))
                for key, values in combined_correlations.items()
            },
            "mean_selected_metric": {
                key: finite_mean(np.asarray(values))
                for key, values in selected_values.items()
            },
            "mean_oracle_best_rank": {
                key: finite_mean(np.asarray(values))
                for key, values in oracle_ranks.items()
            },
            "selected_success_rate": float(
                np.mean(
                    [
                        success[pool, int(np.argmin(combined[pool]))]
                        for pool in range(pool_count)
                    ]
                )
            ),
        }

    true_index = condition_index(scores, "diffusion", "true")
    shuffled_index = condition_index(scores, "diffusion", "shuffled_action")
    ablated_index = condition_index(scores, "diffusion", "action_ablated")
    forward_index = condition_index(scores, "forward", "true")
    expected_seeds = {6101, 6102, 6103}
    for name, index in (
        ("diffusion_true", true_index),
        ("diffusion_shuffled", shuffled_index),
        ("diffusion_action_ablated", ablated_index),
        ("forward_true", forward_index),
    ):
        if set(index) != expected_seeds:
            raise RuntimeError(
                f"{name} does not contain exactly seeds {sorted(expected_seeds)}"
            )
    ordered_seeds = sorted(expected_seeds)
    true_matrix = np.stack(
        [primary_correlations[true_index[seed]] for seed in ordered_seeds]
    )
    shuffled_matrix = np.stack(
        [primary_correlations[shuffled_index[seed]] for seed in ordered_seeds]
    )
    ablated_matrix = np.stack(
        [primary_correlations[ablated_index[seed]] for seed in ordered_seeds]
    )
    forward_matrix = np.stack(
        [primary_correlations[forward_index[seed]] for seed in ordered_seeds]
    )
    matrices = {
        "diffusion_positive_rank": true_matrix,
        "diffusion_minus_shuffled": true_matrix - shuffled_matrix,
        "diffusion_minus_action_ablated": true_matrix - ablated_matrix,
        "diffusion_minus_forward_rank_correlation": true_matrix - forward_matrix,
    }
    bootstrap: dict[str, Any] = {}
    for offset, (name, value) in enumerate(matrices.items()):
        if np.isfinite(value).all():
            bootstrap[name] = cluster_bootstrap_mean(
                value,
                seed=args.bootstrap_seed + offset,
                repetitions=args.bootstrap_repetitions,
            )
        else:
            bootstrap[name] = {
                "estimate": finite_mean(value),
                "lower_95": None,
                "upper_95": None,
                "bootstrap_repetitions": 0,
                "bootstrap_seed": args.bootstrap_seed + offset,
                "undefined_values": int((~np.isfinite(value)).sum()),
                "status": "undefined_due_to_cost_or_metric_collapse",
            }

    def lower_is_positive(name: str) -> bool:
        lower = bootstrap[name].get("lower_95")
        return isinstance(lower, (int, float)) and math.isfinite(lower) and lower > 0.0

    mechanism_gates = {
        "diffusion_cost_positively_ranks_realized_error": lower_is_positive(
            "diffusion_positive_rank"
        ),
        "true_action_conditioning_beats_shuffled": lower_is_positive(
            "diffusion_minus_shuffled"
        ),
        "true_action_conditioning_beats_action_ablated": lower_is_positive(
            "diffusion_minus_action_ablated"
        ),
    }
    result = {
        "status": "ok",
        "kind": "flat_same_candidate_mechanism_audit",
        "analysis_role": args.analysis_role,
        "outcome_role": (
            "development diagnostic; cannot redefine C1 primary methods"
            if args.analysis_role == "D1"
            else "locked confirmation diagnostic run after the primary analysis was frozen"
        ),
        "primary_mechanism_metric": "within-pool Spearman(raw verifier cost, mean standardized successor-latent rollout RMSE)",
        "pool_count": pool_count,
        "candidates_per_pool": candidate_count,
        "score_artifact": str(args.score_artifact),
        "score_artifact_sha256": sha256_file(args.score_artifact),
        "execution_h5": str(args.execution_h5),
        "execution_h5_sha256": sha256_file(args.execution_h5),
        "summaries": summary_by_label,
        "cluster_bootstrap": bootstrap,
        "mechanism_gates": mechanism_gates,
        "development_mechanism_gates": (
            mechanism_gates if args.analysis_role == "D1" else None
        ),
        "all_required_mechanism_gates_pass": all(mechanism_gates.values()),
        "candidate_success_fraction": float(success.mean()),
        "task_state_metrics_available": final_distance is not None,
        "source_manifest_sha256": score_manifest["source_manifest_sha256"],
        "eval_manifest_sha256": score_manifest["eval_manifest_sha256"],
        "dataset_sha256": score_manifest["dataset_sha256"],
        "world_model_checkpoint_sha256": score_manifest[
            "world_model_checkpoint_sha256"
        ],
        "confirmation_authorization_sha256": score_manifest[
            "confirmation_authorization_sha256"
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "pool-level-audit.tsv"
    with detail_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detail_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(detail_rows)
    result["pool_level_tsv"] = str(detail_path)
    result["pool_level_tsv_sha256"] = sha256_file(detail_path)
    atomic_write_json(args.output_dir / "summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
