#!/usr/bin/env python3
"""Validate and summarize a predeclared CEM, weight, and sigma sweep."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from acid_alternative.io_utils import atomic_write_json, sha256_file

TASKS = {"pusht", "reacher", "cube"}
ARMS = ("b0", "acid", "reachability", "diffusion", "forward")
SEEDS = (6101, 6102, 6103)
PLANNER = {6101: 7101, 6102: 7102, 6103: 7103}
BUDGET_SETTINGS = {
    "pop30-lambda007": (30, 3, 0.07),
    "pop50-lambda007": (50, 5, 0.07),
    "pop150-lambda007": (150, 15, 0.07),
    "pop300-lambda007": (300, 30, 0.07),
}
WEIGHT_SETTINGS = {
    "pop300-lambda0005": (300, 30, 0.005),
    "pop300-lambda004": (300, 30, 0.04),
    "pop300-lambda010": (300, 30, 0.10),
}
SIGMA_SETTINGS = {
    "pop300-lambda007-sigma010": 0.10,
    "pop300-lambda007-sigma025": 0.25,
    "pop300-lambda007-sigma050": 0.50,
}


def parse_run(value: str) -> tuple[str, str, str, int, Path]:
    parts = value.split("=", 4)
    if len(parts) != 5:
        raise argparse.ArgumentTypeError("run must be TASK=SETTING=ARM=SEED=SUMMARY")
    task, setting, arm, seed_text, path = parts
    try:
        seed = int(seed_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("seed must be an integer") from error
    if task not in TASKS or arm not in ARMS or seed not in SEEDS:
        raise argparse.ArgumentTypeError(f"invalid sensitivity run: {value}")
    return task, setting, arm, seed, Path(path)


def expected_keys() -> set[tuple[str, str, str, int]]:
    keys = {
        (task, setting, arm, seed)
        for task in TASKS
        for setting in BUDGET_SETTINGS
        for arm in ARMS
        for seed in SEEDS
    }
    keys.update(
        (task, setting, arm, seed)
        for task in TASKS
        for setting in WEIGHT_SETTINGS
        for arm in ARMS[1:]
        for seed in SEEDS
    )
    keys.update(
        (task, setting, "diffusion", seed)
        for task in TASKS
        for setting in SIGMA_SETTINGS
        for seed in SEEDS
    )
    return keys


def read_success(path: Path) -> tuple[dict[str, Any], dict[tuple[int, int, int], int]]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("status") != "ok" or summary.get("kind") != (
        "matched_flat_closed_loop_evaluation"
    ):
        raise RuntimeError(f"{path}: invalid evaluation summary")
    episode_path = Path(summary["episode_tsv"])
    if not episode_path.is_file():
        episode_path = path.parent / episode_path.name
    if sha256_file(episode_path) != summary.get("episode_tsv_sha256"):
        raise RuntimeError(f"{path}: episode artifact hash mismatch")
    with episode_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    outcomes: dict[tuple[int, int, int], int] = {}
    for row in rows:
        key = (int(row["eval_index"]), int(row["episode_id"]), int(row["start_step"]))
        value = int(row["success"])
        if key in outcomes or value not in (0, 1):
            raise RuntimeError(f"{episode_path}: duplicate or invalid outcome")
        outcomes[key] = value
    return summary, outcomes


def expected_configuration(setting: str) -> tuple[int, int, float, list[float]]:
    if setting in BUDGET_SETTINGS:
        population, topk, weight = BUDGET_SETTINGS[setting]
        return population, topk, weight, [0.10, 0.25, 0.50]
    if setting in WEIGHT_SETTINGS:
        population, topk, weight = WEIGHT_SETTINGS[setting]
        return population, topk, weight, [0.10, 0.25, 0.50]
    if setting in SIGMA_SETTINGS:
        return 300, 30, 0.07, [SIGMA_SETTINGS[setting]]
    raise RuntimeError(f"unexpected setting: {setting}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=parse_run, action="append", required=True)
    parser.add_argument("--analysis-role", choices=("D1", "C1"), required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    declared = {
        (task, setting, arm, seed): path for task, setting, arm, seed, path in args.run
    }
    if len(declared) != len(args.run) or set(declared) != expected_keys():
        raise RuntimeError(
            f"incomplete sensitivity matrix: missing={len(expected_keys() - set(declared))}, "
            f"extra={len(set(declared) - expected_keys())}"
        )
    source_hash = sha256_file(args.source_manifest)
    expected_episode_count = 24 if args.analysis_role == "D1" else 50
    outcomes: dict[tuple[str, str, str, int], dict[tuple[int, int, int], int]] = {}
    provenance = []
    task_reference: dict[str, tuple[set[tuple[int, int, int]], str, str, str]] = {}
    authorization_hashes: set[str | None] = set()
    for key in sorted(declared):
        task, setting, arm, seed = key
        path = declared[key]
        if not path.is_file():
            raise FileNotFoundError(path)
        summary, run_outcomes = read_success(path)
        authorization_hashes.add(summary.get("confirmation_authorization_sha256"))
        population, topk, weight, sigmas = expected_configuration(setting)
        config = summary.get("resolved_config", {})
        if (
            summary.get("arm") != arm
            or summary.get("planner_seed") != PLANNER[seed]
            or summary.get("episode_count") != expected_episode_count
            or summary.get("source_manifest_sha256") != source_hash
            or config.get("cem_samples") != population
            or config.get("cem_topk") != topk
            or config.get("cem_steps") != 30
            or config.get("lambda_weight") != weight
            or config.get("diffusion_sigmas") != sigmas
        ):
            raise RuntimeError(f"{path}: sensitivity declaration/config mismatch")
        if arm == "b0":
            if summary.get("scorer_training_seed") is not None:
                raise RuntimeError(f"{path}: B0 has a scorer seed")
        elif summary.get("scorer_training_seed") != seed:
            raise RuntimeError(f"{path}: scorer seed mismatch")
        invariant = (
            set(run_outcomes),
            summary.get("eval_manifest_sha256"),
            summary.get("dataset_sha256"),
            summary.get("world_model_checkpoint_sha256"),
        )
        if task not in task_reference:
            task_reference[task] = invariant
        elif task_reference[task] != invariant:
            raise RuntimeError(f"{path}: task inputs/start identities differ")
        outcomes[key] = run_outcomes
        provenance.append(
            {
                "task": task,
                "setting": setting,
                "arm": arm,
                "seed": seed,
                "summary": str(path),
                "summary_sha256": sha256_file(path),
            }
        )
    if args.analysis_role == "C1":
        if len(authorization_hashes) != 1 or None in authorization_hashes:
            raise RuntimeError("C1 sensitivity does not share one authorization")
    elif authorization_hashes != {None}:
        raise RuntimeError("D1 sensitivity unexpectedly declares C1 authorization")
    rates: dict[str, dict[str, dict[str, float]]] = {}
    detail_rows = []
    for task in sorted(TASKS):
        rates[task] = {}
        settings = sorted(BUDGET_SETTINGS | WEIGHT_SETTINGS | SIGMA_SETTINGS)
        for setting in settings:
            allowed_arms = (
                ARMS
                if setting in BUDGET_SETTINGS
                else (("diffusion",) if setting in SIGMA_SETTINGS else ARMS[1:])
            )
            rates[task][setting] = {}
            for arm in allowed_arms:
                values = np.asarray(
                    [
                        value
                        for seed in SEEDS
                        for value in outcomes[(task, setting, arm, seed)].values()
                    ],
                    dtype=np.float64,
                )
                rates[task][setting][arm] = float(values.mean())
                detail_rows.append(
                    {
                        "task": task,
                        "setting": setting,
                        "arm": arm,
                        "rate": float(values.mean()),
                        "successes": int(values.sum()),
                        "trials": int(values.size),
                    }
                )
    pooled_equal_task = {
        setting: {
            arm: float(
                np.mean(
                    [
                        rates[task][setting][arm]
                        for task in sorted(TASKS)
                        if arm in rates[task][setting]
                    ]
                )
            )
            for arm in sorted(set().union(*(rates[task][setting] for task in TASKS)))
        }
        for setting in sorted(BUDGET_SETTINGS | WEIGHT_SETTINGS | SIGMA_SETTINGS)
    }
    result = {
        "status": "ok",
        "kind": "three_task_cem_weight_sigma_sensitivity_analysis",
        "analysis_role": args.analysis_role,
        "outcome_role": (
            "descriptive development sensitivity; no claim gate or multiplicity-adjusted inference"
            if args.analysis_role == "D1"
            else "locked post-primary confirmation sensitivity; no claim gate or multiplicity-adjusted inference"
        ),
        "tasks": sorted(TASKS),
        "rates": rates,
        "pooled_equal_task_rates": pooled_equal_task,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_hash,
        "confirmation_authorization_sha256": (
            next(iter(authorization_hashes)) if args.analysis_role == "C1" else None
        ),
        "runs": provenance,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "sensitivity-rates.tsv"
    with detail_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=tuple(detail_rows[0]), delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(detail_rows)
    result["rates_tsv"] = str(detail_path)
    result["rates_tsv_sha256"] = sha256_file(detail_path)
    atomic_write_json(args.output_dir / "summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
