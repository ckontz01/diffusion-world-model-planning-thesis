#!/usr/bin/env python3
"""Aggregate same-candidate audits with equal task weight and paired pool clusters."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from acid_alternative.io_utils import atomic_write_json, sha256_file

TASKS = {"pusht", "reacher", "cube"}
SEEDS = (6101, 6102, 6103)
CONDITIONS = {
    "true": ("diffusion", "true"),
    "shuffled": ("diffusion", "shuffled_action"),
    "ablated": ("diffusion", "action_ablated"),
    "forward": ("forward", "true"),
}
METRIC_COLUMN = "raw_spearman_standardized_rollout_rmse"


def parse_audit(value: str) -> tuple[str, Path]:
    parts = value.split("=", 1)
    if len(parts) != 2 or parts[0] not in TASKS:
        raise argparse.ArgumentTypeError("audit must be TASK=SUMMARY_JSON")
    return parts[0], Path(parts[1])


def resolve_artifact(summary_path: Path, declared: str) -> Path:
    path = Path(declared)
    if path.is_file():
        return path
    for candidate in (summary_path.parent / path, summary_path.parent / path.name):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(path)


def load_task(
    task: str, summary_path: Path, analysis_role: str, source_hash: str
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "ok" or summary.get("kind") != (
        "flat_same_candidate_mechanism_audit"
    ):
        raise RuntimeError(f"{summary_path}: invalid audit summary")
    if (
        summary.get("analysis_role") != analysis_role
        or summary.get("source_manifest_sha256") != source_hash
    ):
        raise RuntimeError(f"{summary_path}: role or source snapshot mismatch")
    detail_path = resolve_artifact(summary_path, summary["pool_level_tsv"])
    if sha256_file(detail_path) != summary.get("pool_level_tsv_sha256"):
        raise RuntimeError(f"{detail_path}: detail hash mismatch")
    with detail_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or METRIC_COLUMN not in rows[0]:
        raise RuntimeError(f"{detail_path}: missing mechanism metric")
    result: dict[str, np.ndarray] = {}
    reference_pools: list[int] | None = None
    for name, (arm, condition) in CONDITIONS.items():
        by_seed: list[np.ndarray] = []
        pools_for_condition: list[int] | None = None
        for seed in SEEDS:
            selected = [
                row
                for row in rows
                if row["arm"] == arm
                and row["condition"] == condition
                and int(row["training_seed"]) == seed
            ]
            selected.sort(key=lambda row: int(row["pool"]))
            pools = [int(row["pool"]) for row in selected]
            values = np.asarray(
                [float(row[METRIC_COLUMN]) for row in selected], dtype=np.float64
            )
            if not pools or not np.isfinite(values).all():
                raise RuntimeError(
                    f"{task}/{name}/seed-{seed}: incomplete finite audit"
                )
            if pools_for_condition is None:
                pools_for_condition = pools
            elif pools != pools_for_condition:
                raise RuntimeError(f"{task}/{name}: pool identities differ by seed")
            by_seed.append(values)
        if reference_pools is None:
            reference_pools = pools_for_condition
        elif pools_for_condition != reference_pools:
            raise RuntimeError(f"{task}/{name}: pool identities differ by condition")
        result[name] = np.stack(by_seed)
    return result, {
        "task": task,
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "pool_level_tsv": str(detail_path),
        "pool_level_tsv_sha256": sha256_file(detail_path),
        "pool_count": len(reference_pools or []),
        "confirmation_authorization_sha256": summary.get(
            "confirmation_authorization_sha256"
        ),
    }


def stratified_bootstrap(
    values: dict[str, np.ndarray], *, seed: int, repetitions: int
) -> dict[str, Any]:
    if set(values) != TASKS or repetitions <= 0:
        raise ValueError("bootstrap requires the frozen three-task suite")
    generator = np.random.default_rng(seed)
    draws = np.empty(repetitions, dtype=np.float64)
    per_task: dict[str, Any] = {}
    task_draws: dict[str, np.ndarray] = {}
    for task in sorted(TASKS):
        matrix = np.asarray(values[task], dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[0] != 3 or not np.isfinite(matrix).all():
            raise ValueError(f"{task}: expected finite (3,pools) matrix")
        indices = generator.integers(
            0, matrix.shape[1], size=(repetitions, matrix.shape[1])
        )
        sampled = np.take(matrix, indices, axis=1).mean(axis=(0, 2))
        task_draws[task] = sampled
        per_task[task] = {
            "estimate": float(matrix.mean()),
            "lower_95": float(np.quantile(sampled, 0.025)),
            "upper_95": float(np.quantile(sampled, 0.975)),
            "pool_clusters": int(matrix.shape[1]),
        }
    draws[:] = np.stack([task_draws[task] for task in sorted(TASKS)]).mean(axis=0)
    return {
        "estimate": float(np.mean([values[task].mean() for task in TASKS])),
        "lower_95": float(np.quantile(draws, 0.025)),
        "upper_95": float(np.quantile(draws, 0.975)),
        "per_task": per_task,
        "task_weighting": "equal",
        "cluster_unit": "candidate pool; all three scorer seeds retained",
        "bootstrap_seed": seed,
        "bootstrap_repetitions": repetitions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=parse_audit, action="append", required=True)
    parser.add_argument("--analysis-role", choices=("D1", "C1"), required=True)
    parser.add_argument("--bootstrap-seed", type=int, default=2026081309)
    parser.add_argument("--bootstrap-repetitions", type=int, default=100_000)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    declared = dict(args.audit)
    if len(declared) != len(args.audit) or set(declared) != TASKS:
        raise RuntimeError("requires one audit for each of PushT, Reacher, and Cube")
    matrices: dict[str, dict[str, np.ndarray]] = {}
    provenance = []
    source_hash = sha256_file(args.source_manifest)
    for task in sorted(TASKS):
        matrices[task], record = load_task(
            task, declared[task], args.analysis_role, source_hash
        )
        provenance.append(record)
    authorization_hashes = {
        record["confirmation_authorization_sha256"] for record in provenance
    }
    if args.analysis_role == "C1":
        if len(authorization_hashes) != 1 or None in authorization_hashes:
            raise RuntimeError("C1 mechanism audits do not share one authorization")
    elif authorization_hashes != {None}:
        raise RuntimeError("D1 mechanism unexpectedly declares C1 authorization")
    contrasts = {
        "diffusion_positive_rank": {task: matrices[task]["true"] for task in TASKS},
        "diffusion_minus_shuffled": {
            task: matrices[task]["true"] - matrices[task]["shuffled"] for task in TASKS
        },
        "diffusion_minus_action_ablated": {
            task: matrices[task]["true"] - matrices[task]["ablated"] for task in TASKS
        },
        "diffusion_minus_forward_rank": {
            task: matrices[task]["true"] - matrices[task]["forward"] for task in TASKS
        },
    }
    analyses = {
        name: stratified_bootstrap(
            values,
            seed=args.bootstrap_seed + offset,
            repetitions=args.bootstrap_repetitions,
        )
        for offset, (name, values) in enumerate(contrasts.items())
    }

    def passes(name: str) -> bool:
        result = analyses[name]
        return result["lower_95"] > 0 and all(
            record["estimate"] > 0 for record in result["per_task"].values()
        )

    gates = {
        "diffusion_cost_positively_ranks_realized_error": passes(
            "diffusion_positive_rank"
        ),
        "true_action_conditioning_beats_shuffled": passes("diffusion_minus_shuffled"),
        "true_action_conditioning_beats_action_ablated": passes(
            "diffusion_minus_action_ablated"
        ),
    }
    result = {
        "status": "ok",
        "kind": "three_task_same_candidate_mechanism_analysis",
        "analysis_role": args.analysis_role,
        "outcome_role": (
            "development mechanism diagnostic; primary C1 remains frozen"
            if args.analysis_role == "D1"
            else "locked confirmation mechanism diagnostic"
        ),
        "tasks": sorted(TASKS),
        "primary_metric": METRIC_COLUMN,
        "contrasts": analyses,
        "mechanism_gates": gates,
        "all_required_mechanism_gates_pass": all(gates.values()),
        "gate_rule": "pooled lower 95% bound above zero and positive point estimate on every task",
        "audits": provenance,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_hash,
        "confirmation_authorization_sha256": (
            next(iter(authorization_hashes)) if args.analysis_role == "C1" else None
        ),
    }
    if not all(math.isfinite(analyses[name]["estimate"]) for name in analyses):
        raise RuntimeError("non-finite aggregate mechanism estimate")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(args.output_dir / "summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
