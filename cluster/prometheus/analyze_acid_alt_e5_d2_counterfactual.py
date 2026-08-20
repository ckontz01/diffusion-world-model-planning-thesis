#!/usr/bin/env python3
"""Analyze E5 counterfactual diffusion scores on exposed D2 development data."""

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
BOOTSTRAP_SEED = 2026081614
LAMBDA = 0.07
SPREAD_EPSILON = 1.0e-8

BASELINE_KEYS = {
    "dide": "e4_dide",
    "shuffled_dide": "e4_shuffled_dide",
    "acid": "acid_seed_6101",
    "acid_flow": "acid_flow_seed_6101",
    "acid_16_min": "acid_16_min_seed_6101",
    "deterministic_inverse": "deterministic_inverse",
    "gaussian_nll": "gaussian_nll",
    "forward": "forward_seed_6101",
}
E5_KEYS = {
    "csda_k4": "true_csda_log_tail_k4",
    "csda": "true_csda_log_tail_k8",
    "csda_k16": "true_csda_log_tail_k16",
    "csda_mean": "true_csda_log_mean_k8",
    "csda_pairwise": "true_csda_pairwise_tail_k8",
    "csda_softplus": "true_csda_softplus_tail_k8",
    "shuffled_csda": "shuffled_csda_log_tail_k8",
}


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


def pool_unit_rank(values: np.ndarray) -> np.ndarray:
    if values.shape != (POOL_COUNT, CANDIDATE_COUNT):
        raise ValueError("pool rank input shape differs")
    return np.stack([rankdata(row) / (CANDIDATE_COUNT - 1) for row in values])


def safe_spearman(first: np.ndarray, second: np.ndarray) -> float:
    if first.std(ddof=1) <= SPREAD_EPSILON:
        return 0.0
    left, right = rankdata(first), rankdata(second)
    if right.std(ddof=0) <= 0:
        raise RuntimeError("physical RMSE collapsed within a pool")
    return float(np.corrcoef(left, right)[0, 1])


def select_candidate(goal: np.ndarray, score: np.ndarray) -> int:
    goal_spread = float(goal.std(ddof=1))
    score_spread = float(score.std(ddof=1))
    if score_spread <= SPREAD_EPSILON:
        return int(np.argmin(goal))
    if goal_spread <= 0:
        raise RuntimeError("goal cost collapsed")
    combined = goal + LAMBDA * goal_spread / score_spread * score
    return int(np.argmin(combined))


def parse_task(values: list[str]) -> tuple[str, Path, Path]:
    task, baseline, e5 = values
    if task not in TASKS:
        raise ValueError(f"unexpected task: {task}")
    return task, Path(baseline), Path(e5)


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as archive:
        return {
            name: np.asarray(archive[name], dtype=np.float64)
            for name in archive.files
        }


def load_task(task: str, baseline_path: Path, e5_path: Path) -> dict[str, Any]:
    baseline = _load_npz(baseline_path)
    e5 = _load_npz(e5_path)
    required_baseline = {
        "goal",
        "standardized_rmse",
        "success",
        *BASELINE_KEYS.values(),
    }
    if not required_baseline.issubset(baseline) or not set(E5_KEYS.values()).issubset(e5):
        raise RuntimeError(f"{task}: incomplete E5 analysis inputs")
    for name in required_baseline:
        if baseline[name].shape != (POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError(f"{task}/{name}: shape differs")
    for name in E5_KEYS.values():
        if e5[name].shape != (POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError(f"{task}/{name}: shape differs")

    scores = {name: baseline[key] for name, key in BASELINE_KEYS.items()}
    scores.update({name: e5[key] for name, key in E5_KEYS.items()})
    # Fixed, scale-free composites. These formulas are independent of D2 outcomes.
    unit = {name: pool_unit_rank(value) for name, value in scores.items()}
    scores.update(
        {
            "dide_csda_anchor": 0.5 * (unit["dide"] + unit["csda"]),
            "shuffled_dide_csda_anchor": 0.5
            * (unit["shuffled_dide"] + unit["shuffled_csda"]),
            "forward_csda": 0.5 * (unit["forward"] + unit["csda"]),
            "forward_dide": 0.5 * (unit["forward"] + unit["dide"]),
        }
    )
    rmse = baseline["standardized_rmse"]
    ranks = {
        method: np.asarray(
            [safe_spearman(score[pool], rmse[pool]) for pool in range(POOL_COUNT)]
        )
        for method, score in scores.items()
    }
    selections: dict[str, dict[str, np.ndarray]] = {}
    index = np.arange(POOL_COUNT)
    for method, score in scores.items():
        chosen = np.asarray(
            [select_candidate(baseline["goal"][pool], score[pool]) for pool in range(POOL_COUNT)],
            dtype=np.int16,
        )
        selections[method] = {
            "index": chosen,
            "success": baseline["success"][index, chosen],
            "rmse": rmse[index, chosen],
            "oracle_regret": rmse[index, chosen] - rmse.min(axis=1),
        }
    b0 = baseline["goal"].argmin(axis=1)
    selections["b0"] = {
        "index": b0,
        "success": baseline["success"][index, b0],
        "rmse": rmse[index, b0],
        "oracle_regret": rmse[index, b0] - rmse.min(axis=1),
    }
    return {
        "scores": scores,
        "ranks": ranks,
        "selections": selections,
        "inputs": {
            "baseline": str(baseline_path),
            "baseline_sha256": sha256_file(baseline_path),
            "e5": str(e5_path),
            "e5_sha256": sha256_file(e5_path),
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


def summarize(vectors: dict[str, np.ndarray], indices: dict[str, np.ndarray]) -> dict[str, Any]:
    draws_by_task: list[np.ndarray] = []
    per_task: dict[str, Any] = {}
    for task in TASKS:
        values = np.asarray(vectors[task], dtype=np.float64)
        if values.shape != (POOL_COUNT,) or not np.isfinite(values).all():
            raise RuntimeError(f"{task}: invalid E5 analysis vector")
        draws = values[indices[task]].mean(axis=1)
        draws_by_task.append(draws)
        per_task[task] = {
            "estimate": float(values.mean()),
            "lower_95_two_sided": float(np.quantile(draws, 0.025)),
            "upper_95_two_sided": float(np.quantile(draws, 0.975)),
            "lower_95_one_sided": float(np.quantile(draws, 0.05)),
            "upper_95_one_sided": float(np.quantile(draws, 0.95)),
        }
    equal_draws = np.stack(draws_by_task).mean(axis=0)
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


def contrast(
    tasks: dict[str, Any],
    indices: dict[str, np.ndarray],
    left: str,
    right: str,
    *,
    field: str = "ranks",
    metric: str | None = None,
) -> dict[str, Any]:
    vectors: dict[str, np.ndarray] = {}
    for task in TASKS:
        if field == "ranks":
            vectors[task] = tasks[task][field][left] - tasks[task][field][right]
        else:
            if metric is None:
                raise ValueError("selection contrast requires a metric")
            vectors[task] = (
                tasks[task][field][left][metric]
                - tasks[task][field][right][metric]
            )
    return summarize(vectors, indices)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task",
        nargs=3,
        action="append",
        metavar=("TASK", "E4_D2A_NPZ", "E5_NPZ"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    specs = [parse_task(values) for values in args.task]
    if len(specs) != len(TASKS) or {task for task, _, _ in specs} != set(TASKS):
        raise RuntimeError("one E5 artifact pair for each task is required")
    tasks = {
        task: load_task(task, baseline, e5) for task, baseline, e5 in specs
    }
    indices = bootstrap_indices()
    methods = tuple(tasks[TASKS[0]]["scores"])
    rank_levels = {
        method: summarize(
            {task: tasks[task]["ranks"][method] for task in TASKS}, indices
        )
        for method in methods
    }
    rank_pairs = {
        "csda_minus_shuffled_csda": ("csda", "shuffled_csda"),
        "csda_minus_acid": ("csda", "acid"),
        "csda_minus_acid_flow": ("csda", "acid_flow"),
        "csda_minus_dide": ("csda", "dide"),
        "anchor_minus_acid": ("dide_csda_anchor", "acid"),
        "anchor_minus_acid_flow": ("dide_csda_anchor", "acid_flow"),
        "anchor_minus_dide": ("dide_csda_anchor", "dide"),
        "anchor_minus_shuffled_anchor": (
            "dide_csda_anchor",
            "shuffled_dide_csda_anchor",
        ),
        "forward_csda_minus_forward": ("forward_csda", "forward"),
        "forward_csda_minus_forward_dide": ("forward_csda", "forward_dide"),
        "k4_minus_k8": ("csda_k4", "csda"),
        "k16_minus_k8": ("csda_k16", "csda"),
    }
    rank_contrasts = {
        name: contrast(tasks, indices, left, right)
        for name, (left, right) in rank_pairs.items()
    }
    selection_methods = ("b0", *methods)
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
    selection_pairs = {
        "anchor_minus_acid": ("dide_csda_anchor", "acid"),
        "anchor_minus_b0": ("dide_csda_anchor", "b0"),
        "anchor_minus_dide": ("dide_csda_anchor", "dide"),
        "forward_csda_minus_forward": ("forward_csda", "forward"),
        "csda_minus_acid": ("csda", "acid"),
    }
    selection_contrasts = {
        name: {
            metric: contrast(
                tasks,
                indices,
                left,
                right,
                field="selections",
                metric=metric,
            )
            for metric in ("success", "rmse", "oracle_regret")
        }
        for name, (left, right) in selection_pairs.items()
    }

    csda_rank = rank_levels["csda"]
    csda_null = rank_contrasts["csda_minus_shuffled_csda"]
    condition_identification_gate = {
        "positive_rank_all_tasks": all(
            csda_rank["per_task"][task]["estimate"] > 0 for task in TASKS
        ),
        "higher_than_shuffled_equal_task": csda_null["equal_task"]["estimate"] > 0,
        "k4_and_k16_same_sign_as_k8_all_tasks": all(
            rank_levels[method]["per_task"][task]["estimate"] > 0
            for method in ("csda_k4", "csda_k16")
            for task in TASKS
        ),
    }
    anchor_acid = rank_contrasts["anchor_minus_acid"]
    anchor_null = rank_contrasts["anchor_minus_shuffled_anchor"]
    standalone_gate = {
        "anchor_higher_than_acid_equal_task": anchor_acid["equal_task"]["estimate"] > 0,
        "anchor_not_below_acid_by_more_than_0_03_any_task": all(
            anchor_acid["per_task"][task]["estimate"] >= -0.03 for task in TASKS
        ),
        "anchor_higher_than_shuffled_anchor": anchor_null["equal_task"]["estimate"] > 0,
        "anchor_selection_success_not_below_acid_by_more_than_0_02": (
            selection_contrasts["anchor_minus_acid"]["success"]["equal_task"]["estimate"]
            >= -0.02
        ),
        "anchor_selection_success_not_below_b0_by_more_than_0_02": (
            selection_contrasts["anchor_minus_b0"]["success"]["equal_task"]["estimate"]
            >= -0.02
        ),
    }
    hybrid_rank = rank_contrasts["forward_csda_minus_forward"]
    hybrid_gate = {
        "forward_csda_higher_than_forward_equal_task": hybrid_rank["equal_task"]["estimate"] > 0,
        "forward_csda_not_below_forward_by_more_than_0_02_any_task": all(
            hybrid_rank["per_task"][task]["estimate"] >= -0.02 for task in TASKS
        ),
        "forward_csda_selection_success_not_below_forward": (
            selection_contrasts["forward_csda_minus_forward"]["success"]["equal_task"]["estimate"]
            >= 0
        ),
        "csda_composite_higher_than_dide_composite": (
            rank_contrasts["forward_csda_minus_forward_dide"]["equal_task"]["estimate"]
            > 0
        ),
    }
    condition_pass = all(condition_identification_gate.values())
    standalone_pass = condition_pass and all(standalone_gate.values())
    hybrid_pass = condition_pass and all(hybrid_gate.values())
    if standalone_pass:
        decision = "freeze_dide_csda_anchor_for_fresh_e5_d3"
    elif hybrid_pass:
        decision = "freeze_forward_csda_hybrid_for_fresh_e5_d3"
    else:
        decision = "do_not_advance_counterfactual_e5_to_fresh_d3"

    result = {
        "status": "ok",
        "kind": "acid_alt_e5_counterfactual_d2_development_analysis",
        "analysis_role": "post-outcome exposed-D2 E5 method development",
        "method_priority": [
            "dide_csda_anchor_standalone",
            "forward_csda_hybrid",
        ],
        "rank_levels": rank_levels,
        "rank_contrasts": rank_contrasts,
        "selection_levels_lambda_0_07": selection_levels,
        "selection_contrasts_lambda_0_07": selection_contrasts,
        "development_gates": {
            "condition_identification": condition_identification_gate,
            "standalone_anchor": standalone_gate,
            "forward_hybrid": hybrid_gate,
            "condition_identification_pass": condition_pass,
            "standalone_anchor_pass": standalone_pass,
            "forward_hybrid_pass": hybrid_pass,
        },
        "decision": decision,
        "inputs": {task: tasks[task]["inputs"] for task in TASKS},
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "lambda": LAMBDA,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "protected_c1_i1_read": False,
    }
    if args.output.exists():
        raise SystemExit("refusing to overwrite E5-D2 analysis")
    atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
