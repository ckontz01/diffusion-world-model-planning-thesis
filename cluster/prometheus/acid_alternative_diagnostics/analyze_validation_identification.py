#!/usr/bin/env python3
"""Analyze held-out correct-action identification with paired episode clusters."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from acid_alternative.io_utils import atomic_write_json, sha256_file

EXPECTED_SEEDS = (6101, 6102, 6103)
REQUIRED_COMPARISON_ARMS = (
    ("diffusion", "true"),
    ("forward", "true"),
    ("diffusion", "shuffled_action"),
)


def parse_run_spec(value: str) -> tuple[str, Path]:
    parts = value.split("=", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise argparse.ArgumentTypeError("run must be TASK=SUMMARY_JSON")
    return parts[0], Path(parts[1])


def episode_accuracy(
    correct: np.ndarray, episode_ids: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return sorted episode IDs and equal-within-episode accuracies."""

    correct = np.asarray(correct, dtype=np.float64)
    episode_ids = np.asarray(episode_ids, dtype=np.int64)
    if correct.ndim != 1 or episode_ids.shape != correct.shape:
        raise ValueError("correctness and episode IDs must be matching vectors")
    if not np.isfinite(correct).all():
        raise ValueError("correctness contains non-finite values")
    unique = np.unique(episode_ids)
    if unique.size == 0:
        raise ValueError("no validation episodes")
    means = np.asarray(
        [correct[episode_ids == episode].mean() for episode in unique],
        dtype=np.float64,
    )
    return unique, means


def stratified_episode_bootstrap(
    values_by_task: dict[str, np.ndarray],
    *,
    seed: int,
    repetitions: int,
) -> dict[str, Any]:
    """Resample episode identities and retain all paired scorer seeds."""

    if repetitions <= 0:
        raise ValueError("bootstrap repetitions must be positive")
    if not values_by_task:
        raise ValueError("at least one task is required")
    generator = np.random.default_rng(seed)
    task_estimates: dict[str, np.ndarray] = {}
    by_task: dict[str, dict[str, float]] = {}
    for task in sorted(values_by_task):
        values = np.asarray(values_by_task[task], dtype=np.float64)
        if values.ndim != 2 or values.shape[0] != len(EXPECTED_SEEDS):
            raise ValueError(f"{task}: expected (3 seeds, episodes) values")
        if values.shape[1] == 0 or not np.isfinite(values).all():
            raise ValueError(f"{task}: invalid episode values")
        # Averaging the paired seeds first preserves all three outcomes as one
        # episode cluster. Only episode identities are resampled.
        cluster_values = values.mean(axis=0)
        sampled = generator.integers(
            0, values.shape[1], size=(repetitions, values.shape[1])
        )
        estimates = cluster_values[sampled].mean(axis=1)
        task_estimates[task] = estimates
        by_task[task] = {
            "estimate": float(values.mean()),
            "lower_95": float(np.quantile(estimates, 0.025)),
            "upper_95": float(np.quantile(estimates, 0.975)),
            "episode_clusters": int(values.shape[1]),
        }
    pooled_estimates = np.stack(
        [task_estimates[task] for task in sorted(task_estimates)]
    ).mean(axis=0)
    point = float(
        np.mean([np.asarray(values).mean() for values in values_by_task.values()])
    )
    return {
        "estimate": point,
        "lower_95": float(np.quantile(pooled_estimates, 0.025)),
        "upper_95": float(np.quantile(pooled_estimates, 0.975)),
        "by_task": by_task,
        "task_weighting": "equal",
        "bootstrap_unit": "validation_episode_with_three_paired_training_seeds",
        "bootstrap_repetitions": repetitions,
        "bootstrap_seed": seed,
    }


def resolve_artifact(summary_path: Path, declared: str) -> Path:
    artifact = Path(declared)
    if artifact.is_file():
        return artifact
    relative = summary_path.parent / artifact
    if relative.is_file():
        return relative
    sibling = summary_path.parent / artifact.name
    if sibling.is_file():
        return sibling
    raise FileNotFoundError(artifact)


def load_run(task: str, summary_path: Path, analysis_role: str) -> dict[str, Any]:
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "ok":
        raise RuntimeError(f"{summary_path}: invalid scorer summary")
    if analysis_role == "D1":
        if (
            summary.get("kind") != "flat_transition_scorer_training"
            or summary.get("confirmation_test_outcomes_computed") is not False
        ):
            raise RuntimeError(f"{summary_path}: invalid development scorer summary")
        artifact = resolve_artifact(summary_path, summary["validation_examples"])
        artifact_hash = summary.get("validation_examples_sha256")
        seed = int(summary["seed"])
        data_role = "P1_val"
    else:
        if (
            summary.get("kind") != "flat_transition_identification_evaluation"
            or summary.get("analysis_role") != "C1"
            or summary.get("data_role") != "I1"
            or summary.get("task") != task
            or summary.get("test_limit") is not None
            or summary.get("test_pairs_evaluated")
            != summary.get("test_pairs_total")
            or summary.get("identification_episodes_evaluated") != 200
            or summary.get(
                "confirmation_test_outcomes_previously_used_for_training_or_selection"
            )
            is not False
        ):
            raise RuntimeError(f"{summary_path}: invalid confirmation scorer summary")
        artifact = resolve_artifact(summary_path, summary["identification_examples"])
        artifact_hash = summary.get("identification_examples_sha256")
        seed = int(summary["training_seed"])
        data_role = "I1"
    if sha256_file(artifact) != artifact_hash:
        raise RuntimeError(f"{summary_path}: identification artifact hash mismatch")
    with np.load(artifact, allow_pickle=False) as archive:
        required = {
            "pair_index",
            "episode_idx",
            "step_idx",
            "permuted_pair_index",
            "permuted_episode_idx",
            "permuted_step_idx",
            "correct_cost",
            "permuted_cost",
            "correct_minus_permuted_margin",
        }
        if not required.issubset(archive.files):
            raise RuntimeError(f"{artifact}: incomplete validation artifact")
        arrays = {key: np.asarray(archive[key]) for key in required}
    shape = arrays["pair_index"].shape
    if len(shape) != 1 or any(value.shape != shape for value in arrays.values()):
        raise RuntimeError(f"{artifact}: validation arrays differ in shape")
    if analysis_role == "C1" and len(np.unique(arrays["episode_idx"])) != 200:
        raise RuntimeError(f"{artifact}: C1 does not contain all 200 I1 episodes")
    if len(np.unique(arrays["pair_index"])) != len(arrays["pair_index"]):
        raise RuntimeError(f"{artifact}: duplicate validation pair indices")
    if not np.array_equal(
        np.sort(arrays["pair_index"]), np.sort(arrays["permuted_pair_index"])
    ):
        raise RuntimeError(f"{artifact}: mismatches are not a pair-index permutation")
    if np.any(arrays["pair_index"] == arrays["permuted_pair_index"]):
        raise RuntimeError(f"{artifact}: validation permutation contains a fixed point")
    expected_margin = arrays["permuted_cost"] - arrays["correct_cost"]
    if not np.array_equal(expected_margin, arrays["correct_minus_permuted_margin"]):
        raise RuntimeError(f"{artifact}: stored margin is inconsistent")
    if not np.isfinite(arrays["correct_minus_permuted_margin"]).all():
        raise RuntimeError(f"{artifact}: non-finite validation margins")
    return {
        "task": task,
        "summary_path": summary_path,
        "summary_sha256": sha256_file(summary_path),
        "artifact_path": artifact,
        "artifact_sha256": sha256_file(artifact),
        "model": summary["model"],
        "condition": summary["condition"],
        "seed": seed,
        "data_role": data_role,
        "transition_h5_sha256": summary["transition_h5_sha256"],
        "identification_transition_h5_sha256": summary.get(
            "identification_transition_h5_sha256"
        ),
        "identification_episode_manifest_sha256": summary.get(
            "identification_episode_manifest_sha256"
        ),
        "latent_h5_sha256": summary.get("latent_h5_sha256"),
        "source_manifest_sha256": summary["source_manifest_sha256"],
        "confirmation_authorization_sha256": summary.get(
            "confirmation_authorization_sha256"
        ),
        "parameter_count": int(summary["parameter_count"]),
        **arrays,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=parse_run_spec, action="append", required=True)
    parser.add_argument("--analysis-role", choices=("D1", "C1"), required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--bootstrap-seed", type=int)
    parser.add_argument("--bootstrap-repetitions", type=int, default=100_000)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    bootstrap_seed = args.bootstrap_seed
    if bootstrap_seed is None:
        bootstrap_seed = 2026081304 if args.analysis_role == "D1" else 2026081305

    runs = [load_run(task, path, args.analysis_role) for task, path in args.run]
    tasks = sorted({run["task"] for run in runs})
    if args.analysis_role == "C1" and set(tasks) != {"pusht", "reacher", "cube"}:
        raise RuntimeError("C1 requires exactly PushT, Reacher, and Cube")

    indexed: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    authorization_hashes: set[str | None] = set()
    provenance: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    for run in runs:
        if run["source_manifest_sha256"] != sha256_file(args.source_manifest):
            raise RuntimeError("scorer identification uses another source snapshot")
        authorization_hashes.add(run["confirmation_authorization_sha256"])
        key = (run["task"], run["model"], run["condition"], run["seed"])
        if key in indexed:
            raise RuntimeError(f"duplicate scorer run: {key}")
        indexed[key] = run
        provenance.append(
            {
                "task": run["task"],
                "model": run["model"],
                "condition": run["condition"],
                "seed": run["seed"],
                "parameter_count": run["parameter_count"],
                "summary": str(run["summary_path"]),
                "summary_sha256": run["summary_sha256"],
                "validation_artifact": str(run["artifact_path"]),
                "validation_artifact_sha256": run["artifact_sha256"],
                "data_role": run["data_role"],
                "training_transition_h5_sha256": run["transition_h5_sha256"],
                "identification_transition_h5_sha256": run[
                    "identification_transition_h5_sha256"
                ],
                "identification_episode_manifest_sha256": run[
                    "identification_episode_manifest_sha256"
                ],
                "latent_h5_sha256": run["latent_h5_sha256"],
            }
        )
    if args.analysis_role == "C1":
        if len(authorization_hashes) != 1 or None in authorization_hashes:
            raise RuntimeError("C1 identification does not share one authorization")
    elif authorization_hashes != {None}:
        raise RuntimeError("D1 identification unexpectedly declares C1 authorization")

    accuracy_by_task_arm: dict[str, dict[tuple[str, str], np.ndarray]] = {}
    for task in tasks:
        task_runs = [run for run in runs if run["task"] == task]
        transition_hashes = {run["transition_h5_sha256"] for run in task_runs}
        if len(transition_hashes) != 1:
            raise RuntimeError(f"{task}: scorer runs use different transitions")
        if args.analysis_role == "C1":
            for field in (
                "identification_transition_h5_sha256",
                "identification_episode_manifest_sha256",
                "latent_h5_sha256",
            ):
                hashes = {run[field] for run in task_runs}
                if len(hashes) != 1 or None in hashes:
                    raise RuntimeError(f"{task}: scorer runs use different {field}")
        reference = task_runs[0]
        identity_keys = (
            "pair_index",
            "episode_idx",
            "step_idx",
            "permuted_pair_index",
            "permuted_episode_idx",
            "permuted_step_idx",
        )
        for run in task_runs[1:]:
            if any(
                not np.array_equal(reference[name], run[name]) for name in identity_keys
            ):
                raise RuntimeError(f"{task}: validation identities differ")
        episode_ids = np.unique(reference["episode_idx"])
        arm_arrays: dict[tuple[str, str], np.ndarray] = {}
        for arm_key in REQUIRED_COMPARISON_ARMS:
            seed_values: list[np.ndarray] = []
            for seed in EXPECTED_SEEDS:
                run_key = (task, arm_key[0], arm_key[1], seed)
                if run_key not in indexed:
                    raise RuntimeError(f"missing required scorer run: {run_key}")
                run = indexed[run_key]
                correct = run["correct_minus_permuted_margin"] > 0
                actual_episodes, means = episode_accuracy(correct, run["episode_idx"])
                if not np.array_equal(actual_episodes, episode_ids):
                    raise RuntimeError(f"{run_key}: validation episodes differ")
                seed_values.append(means)
            arm_arrays[arm_key] = np.stack(seed_values)
        accuracy_by_task_arm[task] = arm_arrays
        for seed_index, seed in enumerate(EXPECTED_SEEDS):
            for episode_index, episode in enumerate(episode_ids.tolist()):
                detail_rows.append(
                    {
                        "task": task,
                        "seed": seed,
                        "episode_id": episode,
                        "diffusion_true_accuracy": arm_arrays[("diffusion", "true")][
                            seed_index, episode_index
                        ],
                        "forward_true_accuracy": arm_arrays[("forward", "true")][
                            seed_index, episode_index
                        ],
                        "diffusion_shuffled_accuracy": arm_arrays[
                            ("diffusion", "shuffled_action")
                        ][seed_index, episode_index],
                    }
                )

    comparisons: dict[str, Any] = {}
    definitions = {
        "diffusion_true_minus_forward_true": (
            ("diffusion", "true"),
            ("forward", "true"),
        ),
        "diffusion_true_minus_diffusion_shuffled": (
            ("diffusion", "true"),
            ("diffusion", "shuffled_action"),
        ),
    }
    for comparison, (left, right) in definitions.items():
        differences = {
            task: accuracy_by_task_arm[task][left] - accuracy_by_task_arm[task][right]
            for task in tasks
        }
        result = stratified_episode_bootstrap(
            differences,
            seed=bootstrap_seed,
            repetitions=args.bootstrap_repetitions,
        )
        result["gate_lower_95_above_zero"] = result["lower_95"] > 0
        comparisons[comparison] = result

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "episode-identification.tsv"
    with detail_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=tuple(detail_rows[0]), delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(detail_rows)
    gate_pass = all(
        comparison["gate_lower_95_above_zero"] for comparison in comparisons.values()
    )
    summary = {
        "status": "ok",
        "kind": "heldout_correct_action_identification_analysis",
        "analysis_role": args.analysis_role,
        "confirmatory": args.analysis_role == "C1",
        "data_role": "P1_val" if args.analysis_role == "D1" else "I1",
        "tasks": tasks,
        "expected_training_seeds": list(EXPECTED_SEEDS),
        "accuracy_by_task_arm": {
            task: {
                f"{model}/{condition}": float(values.mean())
                for (model, condition), values in arms.items()
            }
            for task, arms in accuracy_by_task_arm.items()
        },
        "comparisons": comparisons,
        "claim_gate": {
            "pass": gate_pass,
            "rule": (
                "both task-stratified episode-clustered two-sided 95% lower "
                "bounds must exceed zero"
            ),
        },
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "confirmation_authorization_sha256": (
            next(iter(authorization_hashes)) if args.analysis_role == "C1" else None
        ),
        "run_provenance": provenance,
        "episode_detail": str(detail_path),
        "episode_detail_sha256": sha256_file(detail_path),
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
