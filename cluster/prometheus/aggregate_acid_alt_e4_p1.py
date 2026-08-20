#!/usr/bin/env python3
"""Aggregate the frozen E4-P1 mechanism gate across tasks and null controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_PROTOCOL_SHA256 = (
    "eec19adf1558a7366bbc13bd5077c5c26ac4dd73fd5c03b5be2651fe288dfc12"
)
TASKS = ("pusht", "reacher", "cube")
CONDITIONS = ("true_successor", "shuffled_successor")
BOOTSTRAP_REPETITIONS = 10_000
BOOTSTRAP_SEED = 20260816107


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def parse_run(value: str) -> tuple[str, str, Path]:
    fields = value.split("=", 2)
    if len(fields) != 3 or fields[0] not in TASKS or fields[1] not in CONDITIONS:
        raise argparse.ArgumentTypeError("run must be task=condition=summary.json")
    return fields[0], fields[1], Path(fields[2])


def cluster_interval(
    values: np.ndarray,
    episodes: np.ndarray,
    *,
    seed: int,
) -> dict[str, float]:
    """Episode-cluster bootstrap interval for an example-level mean."""

    values = np.asarray(values, dtype=np.float64)
    episodes = np.asarray(episodes, dtype=np.int64)
    if values.ndim != 1 or episodes.shape != values.shape or not len(values):
        raise ValueError("invalid bootstrap arrays")
    unique, inverse = np.unique(episodes, return_inverse=True)
    sums = np.bincount(inverse, weights=values, minlength=len(unique))
    counts = np.bincount(inverse, minlength=len(unique)).astype(np.float64)
    generator = np.random.default_rng(seed)
    estimates = np.empty(BOOTSTRAP_REPETITIONS, dtype=np.float64)
    batch_size = 100
    for start in range(0, BOOTSTRAP_REPETITIONS, batch_size):
        stop = min(start + batch_size, BOOTSTRAP_REPETITIONS)
        sampled = generator.integers(
            0, len(unique), size=(stop - start, len(unique)), endpoint=False
        )
        estimates[start:stop] = sums[sampled].sum(axis=1) / counts[sampled].sum(
            axis=1
        )
    lower, upper = np.quantile(estimates, (0.025, 0.975))
    return {
        "estimate": float(values.mean()),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "clusters": int(len(unique)),
        "examples": int(len(values)),
    }


def load_and_verify(
    task: str,
    condition: str,
    summary_path: Path,
    *,
    expected_source_manifest_sha256: str,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required = {
        "status": "ok",
        "kind": "e4_conditional_inverse_diffusion_p1_training",
        "task": task,
        "condition": condition,
        "seed": 7101,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "source_manifest_sha256": expected_source_manifest_sha256,
        "protected_c1_i1_read": False,
        "confirmation_data_read": False,
    }
    for key, expected in required.items():
        if summary.get(key) != expected:
            raise RuntimeError(
                f"{task}/{condition}: summary {key}={summary.get(key)!r}, "
                f"expected {expected!r}"
            )
    if summary["best_selection_validation"] != summary["replayed_selection_validation"]:
        raise RuntimeError(f"{task}/{condition}: checkpoint replay mismatch")
    examples_path = Path(summary["validation_examples"])
    if (
        not examples_path.is_file()
        or sha256_file(examples_path) != summary["validation_examples_sha256"]
    ):
        raise RuntimeError(f"{task}/{condition}: validation artifact hash mismatch")
    with np.load(examples_path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    required_arrays = {
        "pair_index",
        "episode_idx",
        "primary_matching_energy",
        "primary_deranged_successor_energy",
        "primary_deranged_action_energy",
        "primary_matching_cider",
        "primary_deranged_successor_cider",
    }
    if not required_arrays.issubset(arrays):
        raise RuntimeError(f"{task}/{condition}: incomplete validation arrays")
    if not all(np.isfinite(arrays[name]).all() for name in required_arrays - {"pair_index", "episode_idx"}):
        raise RuntimeError(f"{task}/{condition}: non-finite validation arrays")
    return summary, arrays


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", type=parse_run, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.protocol.is_file() or not args.source_manifest.is_file():
        raise FileNotFoundError("protocol or source manifest is missing")
    if sha256_file(args.protocol) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("E4 protocol hash mismatch")
    expected_source_hash = sha256_file(args.source_manifest)
    grid = {(task, condition): path for task, condition, path in args.run}
    expected_grid = {(task, condition) for task in TASKS for condition in CONDITIONS}
    if len(args.run) != 6 or set(grid) != expected_grid:
        raise RuntimeError("exactly one run for each task/condition is required")

    summaries: dict[tuple[str, str], dict[str, Any]] = {}
    arrays: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    for key, path in grid.items():
        summaries[key], arrays[key] = load_and_verify(
            *key, path, expected_source_manifest_sha256=expected_source_hash
        )

    task_results: dict[str, Any] = {}
    all_pass = True
    for task_index, task in enumerate(TASKS):
        true_summary = summaries[(task, "true_successor")]
        null_summary = summaries[(task, "shuffled_successor")]
        true = arrays[(task, "true_successor")]
        null = arrays[(task, "shuffled_successor")]
        if not np.array_equal(true["pair_index"], null["pair_index"]):
            raise RuntimeError(f"{task}: true/null validation pairs differ")
        if not np.array_equal(true["episode_idx"], null["episode_idx"]):
            raise RuntimeError(f"{task}: true/null validation episodes differ")
        episodes = true["episode_idx"]
        true_successor_indicator = (
            true["primary_matching_energy"]
            < true["primary_deranged_successor_energy"]
        ).astype(np.float64)
        null_successor_indicator = (
            null["primary_matching_energy"]
            < null["primary_deranged_successor_energy"]
        ).astype(np.float64)
        true_action_indicator = (
            true["primary_matching_energy"]
            < true["primary_deranged_action_energy"]
        ).astype(np.float64)
        successor_margin = (
            true["primary_deranged_successor_energy"]
            - true["primary_matching_energy"]
        )
        cider_margin = (
            true["primary_deranged_successor_cider"]
            - true["primary_matching_cider"]
        )
        true_minus_null = true_successor_indicator - null_successor_indicator
        seed_base = BOOTSTRAP_SEED + 100 * task_index
        intervals = {
            "true_successor_accuracy": cluster_interval(
                true_successor_indicator, episodes, seed=seed_base + 1
            ),
            "true_action_accuracy": cluster_interval(
                true_action_indicator, episodes, seed=seed_base + 2
            ),
            "successor_energy_margin": cluster_interval(
                successor_margin, episodes, seed=seed_base + 3
            ),
            "true_minus_shuffled_successor_accuracy": cluster_interval(
                true_minus_null, episodes, seed=seed_base + 4
            ),
            "cider_wrong_minus_matching_margin": cluster_interval(
                cider_margin, episodes, seed=seed_base + 5
            ),
        }
        true_validation = true_summary["final_validation"]
        null_validation = null_summary["final_validation"]
        gates = {
            "true_successor_accuracy_at_least_0_65": bool(
                true_validation["successor_pairwise_accuracy"] >= 0.65
            ),
            "true_action_accuracy_at_least_0_65": bool(
                true_validation["action_pairwise_accuracy"] >= 0.65
            ),
            "positive_successor_energy_margin": bool(
                true_validation["deranged_successor_minus_matching_margin"] > 0
            ),
            "true_minus_shuffled_successor_accuracy_at_least_0_10": bool(
                true_validation["successor_pairwise_accuracy"]
                - null_validation["successor_pairwise_accuracy"]
                >= 0.10
            ),
            "matching_cider_lower_than_deranged_successor": bool(
                true_validation["matching_cider_mean"]
                < true_validation["deranged_successor_cider_mean"]
            ),
            "finite_noncollapsed_reproduced": bool(
                true_validation["matching_energy_std"] > 1.0e-8
                and true_validation["matching_cider_std"] > 1.0e-8
                and null_validation["matching_energy_std"] > 1.0e-8
                and null_validation["matching_cider_std"] > 1.0e-8
                and true_summary["best_selection_validation"]
                == true_summary["replayed_selection_validation"]
                and null_summary["best_selection_validation"]
                == null_summary["replayed_selection_validation"]
            ),
        }
        task_pass = all(gates.values())
        all_pass = all_pass and task_pass
        task_results[task] = {
            "pass": task_pass,
            "gates": gates,
            "true": {
                "successor_pairwise_accuracy": true_validation[
                    "successor_pairwise_accuracy"
                ],
                "action_pairwise_accuracy": true_validation[
                    "action_pairwise_accuracy"
                ],
                "deranged_successor_minus_matching_margin": true_validation[
                    "deranged_successor_minus_matching_margin"
                ],
                "matching_cider_mean": true_validation["matching_cider_mean"],
                "deranged_successor_cider_mean": true_validation[
                    "deranged_successor_cider_mean"
                ],
            },
            "shuffled": {
                "successor_pairwise_accuracy": null_validation[
                    "successor_pairwise_accuracy"
                ],
                "action_pairwise_accuracy": null_validation[
                    "action_pairwise_accuracy"
                ],
            },
            "true_minus_shuffled_successor_accuracy": (
                true_validation["successor_pairwise_accuracy"]
                - null_validation["successor_pairwise_accuracy"]
            ),
            "cluster_bootstrap_intervals": intervals,
            "true_summary": str(grid[(task, "true_successor")]),
            "shuffled_summary": str(grid[(task, "shuffled_successor")]),
            "true_checkpoint_sha256": true_summary["checkpoint_sha256"],
            "shuffled_checkpoint_sha256": null_summary["checkpoint_sha256"],
            "calibration": true_validation["calibration"],
        }

    decision = "advance_to_e4_d2a_exposed_candidate_audit" if all_pass else "stop_e4_before_d2"
    payload = {
        "status": "ok",
        "kind": "e4_p1_mechanism_gate",
        "analysis_role": "P1-only post-E3 exploratory development",
        "all_e4_p1_gates_pass": all_pass,
        "decision": decision,
        "tasks": task_results,
        "bootstrap": {
            "kind": "P1_validation_episode_cluster",
            "repetitions": BOOTSTRAP_REPETITIONS,
            "seed": BOOTSTRAP_SEED,
        },
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": expected_source_hash,
        "protected_c1_i1_read": False,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    atomic_json(args.output_dir / "summary.json", payload)
    with (args.output_dir / "runs.tsv").open("x", encoding="utf-8", newline="") as stream:
        stream.write("task\tcondition\tsummary\tcheckpoint_sha256\n")
        for task in TASKS:
            for condition in CONDITIONS:
                summary = summaries[(task, condition)]
                stream.write(
                    f"{task}\t{condition}\t{grid[(task, condition)]}\t"
                    f"{summary['checkpoint_sha256']}\n"
                )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
