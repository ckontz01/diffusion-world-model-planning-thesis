#!/usr/bin/env python3
"""Post-hoc diagnosis of the preregistered E4 DIDE secondary endpoint.

This is explicitly exposed-D2 method development.  It quantifies whether the
direct conditional diffusion energy, rather than the failed CIDER ratio, has a
stable signal worth testing in a separately frozen E5 study.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np


TASKS = ("pusht", "reacher", "cube")
POOL_COUNT = 50
CANDIDATE_COUNT = 300
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081613
LAMBDA = 0.07
SPREAD_EPSILON = 1.0e-8
METHODS = {
    "dide": "e4_dide",
    "shuffled_dide": "e4_shuffled_dide",
    "acid": "acid_seed_6101",
    "acid_flow": "acid_flow_seed_6101",
    "acid_16_min": "acid_16_min_seed_6101",
    "deterministic_inverse": "deterministic_inverse",
    "gaussian_nll": "gaussian_nll",
    "forward": "forward_seed_6101",
    "reachability": "reachability_seed_6101",
}
COMPARATORS = tuple(name for name in METHODS if name != "dide")


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def parse_task(values: list[str]) -> tuple[str, Path]:
    task, artifact = values
    if task not in TASKS:
        raise ValueError(f"unexpected task: {task}")
    return task, Path(artifact)


def load_task(task: str, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as archive:
        required = {"goal", "standardized_rmse", "success", *METHODS.values()}
        if not required.issubset(archive.files):
            raise RuntimeError(f"{task}: incomplete D2A artifact")
        arrays = {name: np.asarray(archive[name], dtype=np.float64) for name in required}
    for name, value in arrays.items():
        if value.shape != (POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError(f"{task}/{name}: unexpected shape {value.shape}")
        if not np.isfinite(value).all():
            raise RuntimeError(f"{task}/{name}: non-finite values")
    ranks: dict[str, np.ndarray] = {}
    rmse = arrays["standardized_rmse"]
    for method, key in METHODS.items():
        ranks[method] = np.asarray(
            [safe_spearman(arrays[key][pool], rmse[pool])[0] for pool in range(POOL_COUNT)]
        )
    selections: dict[str, dict[str, np.ndarray]] = {}
    for method, key in METHODS.items():
        selected = np.asarray(
            [
                select_candidate(arrays["goal"][pool], arrays[key][pool], LAMBDA)
                for pool in range(POOL_COUNT)
            ],
            dtype=np.int16,
        )
        index = np.arange(POOL_COUNT)
        selections[method] = {
            "index": selected,
            "success": arrays["success"][index, selected],
            "rmse": rmse[index, selected],
            "oracle_regret": rmse[index, selected] - rmse.min(axis=1),
        }
    b0_index = arrays["goal"].argmin(axis=1)
    index = np.arange(POOL_COUNT)
    selections["b0"] = {
        "index": b0_index,
        "success": arrays["success"][index, b0_index],
        "rmse": rmse[index, b0_index],
        "oracle_regret": rmse[index, b0_index] - rmse.min(axis=1),
    }
    return {
        "artifact": str(path),
        "artifact_sha256": sha256_file(path),
        "arrays": arrays,
        "ranks": ranks,
        "selections": selections,
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


def summarize(vectors: dict[str, np.ndarray], indices: dict[str, np.ndarray]) -> dict[str, Any]:
    task_draws: list[np.ndarray] = []
    per_task: dict[str, Any] = {}
    for task in TASKS:
        values = np.asarray(vectors[task], dtype=np.float64)
        if values.shape != (POOL_COUNT,) or not np.isfinite(values).all():
            raise RuntimeError(f"{task}: invalid diagnostic vector")
        draws = values[indices[task]].mean(axis=1)
        task_draws.append(draws)
        per_task[task] = {
            "estimate": float(values.mean()),
            "lower_95_two_sided": float(np.quantile(draws, 0.025)),
            "upper_95_two_sided": float(np.quantile(draws, 0.975)),
            "lower_95_one_sided": float(np.quantile(draws, 0.05)),
            "upper_95_one_sided": float(np.quantile(draws, 0.95)),
        }
    equal_draws = np.stack(task_draws).mean(axis=0)
    return {
        "per_task": per_task,
        "equal_task": {
            "estimate": float(np.mean([vectors[task].mean() for task in TASKS])),
            "lower_95_two_sided": float(np.quantile(equal_draws, 0.025)),
            "upper_95_two_sided": float(np.quantile(equal_draws, 0.975)),
            "lower_95_one_sided": float(np.quantile(equal_draws, 0.05)),
            "upper_95_one_sided": float(np.quantile(equal_draws, 0.95)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task", nargs=2, action="append", metavar=("TASK", "NPZ"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    specs = [parse_task(values) for values in args.task]
    if len(specs) != len(TASKS) or {task for task, _ in specs} != set(TASKS):
        raise RuntimeError("one artifact for each task is required")
    tasks = {task: load_task(task, path) for task, path in specs}
    indices = bootstrap_indices()
    rank_levels = {
        method: summarize({task: tasks[task]["ranks"][method] for task in TASKS}, indices)
        for method in METHODS
    }
    rank_contrasts = {
        f"dide_minus_{method}": summarize(
            {
                task: tasks[task]["ranks"]["dide"] - tasks[task]["ranks"][method]
                for task in TASKS
            },
            indices,
        )
        for method in COMPARATORS
    }
    selection_methods = ("b0", *METHODS)
    selection_levels = {
        method: {
            metric: summarize(
                {
                    task: tasks[task]["selections"][method][metric]
                    for task in TASKS
                },
                indices,
            )
            for metric in ("success", "rmse", "oracle_regret")
        }
        for method in selection_methods
    }
    selection_contrasts = {
        f"dide_minus_{method}": {
            metric: summarize(
                {
                    task: (
                        tasks[task]["selections"]["dide"][metric]
                        - tasks[task]["selections"][method][metric]
                    )
                    for task in TASKS
                },
                indices,
            )
            for metric in ("success", "rmse", "oracle_regret")
        }
        for method in ("b0", *COMPARATORS)
    }
    pool_wins = {
        method: {
            task: {
                "dide_higher_rank": int(
                    np.count_nonzero(
                        tasks[task]["ranks"]["dide"] > tasks[task]["ranks"][method]
                    )
                ),
                "dide_lower_rank": int(
                    np.count_nonzero(
                        tasks[task]["ranks"]["dide"] < tasks[task]["ranks"][method]
                    )
                ),
                "ties": int(
                    np.count_nonzero(
                        tasks[task]["ranks"]["dide"] == tasks[task]["ranks"][method]
                    )
                ),
            }
            for task in TASKS
        }
        for method in COMPARATORS
    }
    score_correlations = {
        method: {
            task: float(
                safe_spearman(
                    tasks[task]["arrays"][METHODS["dide"]].reshape(-1),
                    tasks[task]["arrays"][METHODS[method]].reshape(-1),
                )[0]
            )
            for task in TASKS
        }
        for method in COMPARATORS
    }
    result = {
        "status": "ok",
        "kind": "acid_alt_e5_dide_posthoc_d2_diagnostic",
        "analysis_role": "post-outcome exposed-D2 method development",
        "finding_under_test": (
            "whether preregistered direct inverse-denoising energy merits a "
            "separately frozen fresh E5 study"
        ),
        "rank_levels": rank_levels,
        "rank_contrasts": rank_contrasts,
        "selection_levels_lambda_0_07": selection_levels,
        "selection_contrasts_lambda_0_07": selection_contrasts,
        "pool_rank_win_counts": pool_wins,
        "candidate_score_correlations_with_dide": score_correlations,
        "inputs": {
            task: {
                "artifact": tasks[task]["artifact"],
                "artifact_sha256": tasks[task]["artifact_sha256"],
            }
            for task in TASKS
        },
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "lambda": LAMBDA,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "protected_c1_i1_read": False,
    }
    if args.output.exists():
        raise SystemExit("refusing to overwrite E5 post-hoc diagnostic")
    atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
