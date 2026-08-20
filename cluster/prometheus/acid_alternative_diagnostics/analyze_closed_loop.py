#!/usr/bin/env python3
"""Analyze paired five-arm closed-loop evaluations without pooling raw episodes."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from acid_alternative.io_utils import atomic_write_json, sha256_file

ARMS = ("b0", "acid", "reachability", "diffusion", "forward")
TRAIN_TO_PLANNER = {6101: 7101, 6102: 7102, 6103: 7103}
CONFIRMATION_TASKS = {"pusht", "reacher", "cube"}


def validate_task_set(role: str, tasks: set[str]) -> None:
    if role == "confirmation" and tasks != CONFIRMATION_TASKS:
        missing = sorted(CONFIRMATION_TASKS - tasks)
        extra = sorted(tasks - CONFIRMATION_TASKS)
        raise RuntimeError(
            "confirmation requires exactly PushT, Reacher, and Cube; "
            f"missing={missing}, extra={extra}"
        )


def parse_run(value: str) -> tuple[str, str, int, Path]:
    parts = value.split("=", 3)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("run must be TASK=ARM=PAIR_SEED=SUMMARY")
    task, arm, seed_text, path = parts
    if not task or arm not in ARMS:
        raise argparse.ArgumentTypeError(f"invalid run declaration: {value}")
    try:
        seed = int(seed_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("pair seed must be an integer") from error
    if seed not in TRAIN_TO_PLANNER:
        raise argparse.ArgumentTypeError(f"unexpected pair seed: {seed}")
    return task, arm, seed, Path(path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def read_successes(path: Path) -> dict[tuple[int, int, int], int]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"eval_index", "episode_id", "start_step", "success"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"invalid episode TSV: {path}")
    result: dict[tuple[int, int, int], int] = {}
    for row in rows:
        key = (int(row["eval_index"]), int(row["episode_id"]), int(row["start_step"]))
        success = int(row["success"])
        if success not in (0, 1) or key in result:
            raise ValueError(f"invalid/duplicate episode row in {path}: {key}")
        result[key] = success
    return result


def exact_paired_two_sided(
    first: np.ndarray, second: np.ndarray
) -> dict[str, int | float]:
    first = np.asarray(first, dtype=np.int8)
    second = np.asarray(second, dtype=np.int8)
    if first.shape != second.shape:
        raise ValueError("paired arrays differ in shape")
    wins = int(np.sum((first == 1) & (second == 0)))
    losses = int(np.sum((first == 0) & (second == 1)))
    discordant = wins + losses
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, index) for index in range(min(wins, losses) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2.0 * tail)
    return {
        "first_wins": wins,
        "first_losses": losses,
        "discordant": discordant,
        "two_sided_exact_p": p_value,
    }


def bootstrap_contrast(
    task_values: dict[str, np.ndarray],
    *,
    seed: int,
    repetitions: int,
) -> dict[str, Any]:
    """Resample starts within task, retaining all three paired seed outcomes."""

    if not task_values or repetitions <= 0:
        raise ValueError("bootstrap requires tasks and positive repetitions")
    generator = np.random.default_rng(seed)
    task_names = sorted(task_values)
    for task, values in task_values.items():
        if values.ndim != 2 or values.shape[0] != 3 or not np.isfinite(values).all():
            raise ValueError(f"{task}: contrast must have shape (3,starts)")
    estimates = np.empty(repetitions, dtype=np.float64)
    task_estimates = {
        task: np.empty(repetitions, dtype=np.float64) for task in task_names
    }
    for repetition in range(repetitions):
        current = []
        for task in task_names:
            values = task_values[task]
            selected = generator.integers(0, values.shape[1], size=values.shape[1])
            estimate = float(values[:, selected].mean())
            task_estimates[task][repetition] = estimate
            current.append(estimate)
        # Equal task weights are frozen even if manifest sizes differ.
        estimates[repetition] = np.mean(current)
    per_task = {}
    for task in task_names:
        values = task_values[task]
        draws = task_estimates[task]
        per_task[task] = {
            "estimate": float(values.mean()),
            "lower_95_two_sided": float(np.quantile(draws, 0.025)),
            "upper_95_two_sided": float(np.quantile(draws, 0.975)),
            "lower_95_one_sided": float(np.quantile(draws, 0.05)),
        }
    return {
        "estimate": float(np.mean([task_values[task].mean() for task in task_names])),
        "lower_95_two_sided": float(np.quantile(estimates, 0.025)),
        "upper_95_two_sided": float(np.quantile(estimates, 0.975)),
        "lower_95_one_sided": float(np.quantile(estimates, 0.05)),
        "task_weighting": "equal task weight",
        "cluster_unit": "start identity; all three paired seed runs retained",
        "bootstrap_seed": seed,
        "bootstrap_repetitions": repetitions,
        "per_task": per_task,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--role", choices=("development", "confirmation"), required=True
    )
    parser.add_argument("--expected-starts", type=int, required=True)
    parser.add_argument("--run", type=parse_run, action="append", required=True)
    parser.add_argument("--bootstrap-seed", type=int, required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=100_000)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.expected_starts <= 0 or args.bootstrap_repetitions <= 0:
        raise ValueError("start and bootstrap counts must be positive")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")

    declared: dict[tuple[str, str, int], Path] = {}
    for task, arm, seed, path in args.run:
        key = (task, arm, seed)
        if key in declared:
            raise ValueError(f"duplicate run declaration: {key}")
        if not path.is_file():
            raise FileNotFoundError(path)
        declared[key] = path
    tasks = sorted({task for task, _, _ in declared})
    validate_task_set(args.role, set(tasks))
    expected = {
        (task, arm, seed)
        for task in tasks
        for arm in ARMS
        for seed in sorted(TRAIN_TO_PLANNER)
    }
    if set(declared) != expected:
        missing = sorted(expected - set(declared))
        extra = sorted(set(declared) - expected)
        raise RuntimeError(
            f"incomplete five-arm matrix; missing={missing}, extra={extra}"
        )

    outcomes: dict[tuple[str, str, int], dict[tuple[int, int, int], int]] = {}
    run_records: list[dict[str, Any]] = []
    task_invariants: dict[str, dict[str, Any]] = {}
    for key in sorted(declared):
        task, arm, pair_seed = key
        path = declared[key]
        summary = read_json(path)
        if summary.get("status") != "ok" or summary.get("arm") != arm:
            raise RuntimeError(f"{path}: status/arm mismatch")
        if summary.get("planner_seed") != TRAIN_TO_PLANNER[pair_seed]:
            raise RuntimeError(f"{path}: planner seed does not match pair seed")
        if arm == "b0":
            if summary.get("scorer_training_seed") is not None:
                raise RuntimeError(f"{path}: B0 unexpectedly has a scorer seed")
        elif summary.get("scorer_training_seed") != pair_seed:
            raise RuntimeError(f"{path}: scorer seed does not match pair seed")
        if summary.get("episode_count") != args.expected_starts:
            raise RuntimeError(f"{path}: unexpected start count")
        invariants = {
            "eval_manifest_sha256": summary.get("eval_manifest_sha256"),
            "dataset_sha256": summary.get("dataset_sha256"),
            "world_model_checkpoint_sha256": summary.get(
                "world_model_checkpoint_sha256"
            ),
            "source_manifest_sha256": summary.get("source_manifest_sha256"),
            "confirmation_authorization_sha256": summary.get(
                "confirmation_authorization_sha256"
            ),
        }
        if task not in task_invariants:
            task_invariants[task] = invariants
        elif task_invariants[task] != invariants:
            raise RuntimeError(f"{path}: task-level matched inputs differ")
        episodes_path = Path(str(summary.get("episode_tsv", "")))
        if not episodes_path.is_file():
            raise FileNotFoundError(episodes_path)
        outcomes[key] = read_successes(episodes_path)
        if len(outcomes[key]) != args.expected_starts:
            raise RuntimeError(f"{episodes_path}: unexpected episode row count")
        run_records.append(
            {
                "task": task,
                "arm": arm,
                "pair_seed": pair_seed,
                "planner_seed": TRAIN_TO_PLANNER[pair_seed],
                "summary": str(path),
                "summary_sha256": sha256_file(path),
                "episode_tsv": str(episodes_path),
                "episode_tsv_sha256": sha256_file(episodes_path),
                "success_rate_fraction": summary.get("success_rate_fraction"),
                "elapsed_seconds": summary.get("elapsed_seconds"),
                "peak_cuda_memory_allocated_bytes": (summary.get("runtime") or {}).get(
                    "peak_cuda_memory_allocated_bytes"
                ),
                "source_manifest_sha256": summary.get("source_manifest_sha256"),
            }
        )

    source_hashes = {record["source_manifest_sha256"] for record in run_records}
    if len(source_hashes) != 1 or None in source_hashes:
        raise RuntimeError("closed-loop runs do not share one source manifest")
    authorization_hashes = {
        value["confirmation_authorization_sha256"] for value in task_invariants.values()
    }
    if args.role == "confirmation":
        if len(authorization_hashes) != 1 or None in authorization_hashes:
            raise RuntimeError("confirmation runs do not share one C1 authorization")
    elif authorization_hashes != {None}:
        raise RuntimeError("development runs unexpectedly declare C1 authorization")

    task_keys: dict[str, list[tuple[int, int, int]]] = {}
    for task in tasks:
        reference = outcomes[(task, "b0", 6101)]
        task_keys[task] = sorted(reference)
        if len(reference) != args.expected_starts:
            raise RuntimeError(f"{task}: wrong number of start identities")
        for arm in ARMS:
            for seed in TRAIN_TO_PLANNER:
                if outcomes[(task, arm, seed)].keys() != reference.keys():
                    raise RuntimeError(f"{task}/{arm}/{seed}: start identities differ")

    rates: dict[str, dict[str, Any]] = {}
    arrays: dict[tuple[str, str], np.ndarray] = {}
    detail_rows: list[dict[str, Any]] = []
    for task in tasks:
        rates[task] = {}
        keys = task_keys[task]
        for arm in ARMS:
            matrix = np.asarray(
                [
                    [outcomes[(task, arm, seed)][key] for key in keys]
                    for seed in sorted(TRAIN_TO_PLANNER)
                ],
                dtype=np.int8,
            )
            arrays[(task, arm)] = matrix
            rates[task][arm] = {
                "success_count": int(matrix.sum()),
                "trials": int(matrix.size),
                "rate": float(matrix.mean()),
                "per_pair_seed_rate": {
                    str(seed): float(matrix[index].mean())
                    for index, seed in enumerate(sorted(TRAIN_TO_PLANNER))
                },
            }
        for seed_index, seed in enumerate(sorted(TRAIN_TO_PLANNER)):
            for start_index, key in enumerate(keys):
                row = {
                    "task": task,
                    "eval_index": key[0],
                    "episode_id": key[1],
                    "start_step": key[2],
                    "pair_seed": seed,
                    "planner_seed": TRAIN_TO_PLANNER[seed],
                }
                for arm in ARMS:
                    row[arm] = int(arrays[(task, arm)][seed_index, start_index])
                detail_rows.append(row)

    contrasts = {
        "diffusion_minus_b0": ("diffusion", "b0"),
        "diffusion_minus_acid": ("diffusion", "acid"),
        "diffusion_minus_forward": ("diffusion", "forward"),
    }
    contrast_results: dict[str, Any] = {}
    for offset, (name, (first_arm, second_arm)) in enumerate(contrasts.items()):
        task_values = {
            task: arrays[(task, first_arm)].astype(np.float64)
            - arrays[(task, second_arm)].astype(np.float64)
            for task in tasks
        }
        result = bootstrap_contrast(
            task_values,
            seed=args.bootstrap_seed + offset,
            repetitions=args.bootstrap_repetitions,
        )
        exact = {}
        for task in tasks:
            exact[task] = exact_paired_two_sided(
                arrays[(task, first_arm)].ravel(),
                arrays[(task, second_arm)].ravel(),
            )
        result["exact_paired_sensitivity"] = exact
        contrast_results[name] = result

    useful = contrast_results["diffusion_minus_b0"]["lower_95_two_sided"] > 0.0
    acid_noninferior = contrast_results["diffusion_minus_acid"][
        "lower_95_one_sided"
    ] > -0.05 and all(
        task_result["lower_95_one_sided"] > -0.10
        for task_result in contrast_results["diffusion_minus_acid"]["per_task"].values()
    )
    diffusion_specific = (
        contrast_results["diffusion_minus_forward"]["lower_95_two_sided"] > 0.0
    )
    breadth = (
        all(
            rates[task]["diffusion"]["rate"] - rates[task]["b0"]["rate"] >= -0.10
            for task in tasks
        )
        and sum(
            rates[task]["diffusion"]["rate"] > rates[task]["b0"]["rate"]
            for task in tasks
        )
        >= 2
    )
    gates = {
        "useful_diffusion_vs_b0": useful,
        "acid_noninferiority": acid_noninferior,
        "diffusion_specific_closed_loop": diffusion_specific,
        "breadth": breadth,
        "mechanism": None,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paired_path = args.output_dir / "paired-outcomes.tsv"
    with paired_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detail_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(detail_rows)
    result = {
        "status": "ok",
        "kind": "matched_five_arm_closed_loop_analysis",
        "role": args.role,
        "tasks": tasks,
        "expected_starts_per_task": args.expected_starts,
        "pair_seeds": sorted(TRAIN_TO_PLANNER),
        "planner_seeds": [TRAIN_TO_PLANNER[seed] for seed in sorted(TRAIN_TO_PLANNER)],
        "rates": rates,
        "contrasts": contrast_results,
        "claim_gates_closed_loop_only": gates,
        "claim_gate_interpretation": (
            "confirmatory"
            if args.role == "confirmation"
            else "development diagnostic only"
        ),
        "runs": run_records,
        "task_invariants": task_invariants,
        "source_manifest_sha256": next(iter(source_hashes)),
        "confirmation_authorization_sha256": (
            next(iter(authorization_hashes)) if args.role == "confirmation" else None
        ),
        "paired_outcomes_tsv": str(paired_path),
        "paired_outcomes_tsv_sha256": sha256_file(paired_path),
    }
    atomic_write_json(args.output_dir / "summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
