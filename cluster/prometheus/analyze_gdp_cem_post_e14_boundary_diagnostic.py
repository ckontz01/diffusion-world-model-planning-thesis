#!/usr/bin/env python3
"""Validate and aggregate all six frozen post-E14 boundary cells."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import sha256_file


KEY_METRICS = (
    "bank_raw_robust_oob_fraction",
    "bank_raw_legal_oob_fraction",
    "bank_exact_robust_after_clip_fraction",
    "selected_raw_robust_oob_fraction",
    "selected_raw_legal_oob_fraction",
    "selected_exact_robust_after_clip_fraction",
    "raw_candidate_variance",
    "clipped_candidate_variance",
    "raw_unique_candidates",
    "clipped_unique_candidates",
)


def read_sha256_records(path: Path) -> dict[str, str]:
    """Read the two-file GNU checksum manifest without newer E14 helpers."""

    records: dict[str, str] = {}
    for raw_line in path.read_bytes().split(b"\n"):
        if not raw_line:
            continue
        digest_bytes, separator, filename_bytes = raw_line.partition(b" ")
        filename_bytes = filename_bytes.lstrip(b" *")
        if (
            not separator
            or len(digest_bytes) != 64
            or any(
                value not in b"0123456789abcdef"
                for value in digest_bytes.lower()
            )
            or not filename_bytes
        ):
            raise RuntimeError(f"invalid diagnostic checksum record: {path}")
        name = Path(os.fsdecode(filename_bytes)).name
        if not name or name in records:
            raise RuntimeError(f"duplicate diagnostic checksum record: {path}")
        records[name] = digest_bytes.decode("ascii").lower()
    if not records:
        raise RuntimeError(f"empty diagnostic checksum manifest: {path}")
    return records


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"protected path is forbidden: {path}")


def atomic_json(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def distribution(value: np.ndarray) -> dict[str, float]:
    value = np.asarray(value, dtype=np.float64)
    if value.ndim != 1 or len(value) != spec.VALIDATION_ROWS or not np.isfinite(value).all():
        raise RuntimeError("invalid full diagnostic row metric")
    return {
        "minimum": float(value.min()),
        "q05": float(np.quantile(value, 0.05)),
        "median": float(np.quantile(value, 0.50)),
        "q95": float(np.quantile(value, 0.95)),
        "q99": float(np.quantile(value, 0.99)),
        "maximum": float(value.max()),
        "mean": float(value.mean(dtype=np.float64)),
    }


def read_cell(
    directory: Path,
    *,
    task: str,
    seed: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    reject_protected_path(directory)
    checksum_path = directory / "sha256.txt"
    summary_path = directory / "summary.json"
    metrics_path = directory / "row-metrics.h5"
    if not checksum_path.is_file():
        raise FileNotFoundError(checksum_path)
    records = read_sha256_records(checksum_path)
    if set(records) != {"row-metrics.h5", "summary.json"}:
        raise RuntimeError("diagnostic cell checksum manifest differs")
    for name, digest in records.items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"diagnostic cell hash differs: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_post_e14_frozen_vad_boundary_diagnostic"
        or summary.get("analysis_role") != "P1_development_artifact_diagnosis_only"
        or summary.get("task") != task
        or int(summary.get("seed", -1)) != seed
        or summary.get("mode") != "full"
        or int(summary.get("row_count", -1)) != spec.VALIDATION_ROWS
        or int(summary.get("candidate_count", -1)) != spec.CANDIDATE_COUNT
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_manifest_sha256
        or summary.get("row_metrics_h5_sha256") != records["row-metrics.h5"]
        or Path(summary.get("row_metrics_h5", "")).resolve() != metrics_path.resolve()
        or summary.get("reproduction", {}).get(
            "original_e14_boundary_metric_reproduced"
        )
        is not True
        or summary.get("reproduction", {}).get("coverage") != "all_rows"
        or int(summary.get("reproduction", {}).get("compared_row_count", -1))
        != spec.VALIDATION_ROWS
        or float(summary.get("reproduction", {}).get("maximum_absolute_error", 1.0))
        > 1.0e-7
        or summary.get("descriptive_only") is not True
        or summary.get("may_modify_e14_result") is not False
        or summary.get("may_select_or_authorize_e15") is not False
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("diagnostic cell identity differs")
    with h5py.File(metrics_path, "r") as handle:
        rows = np.asarray(handle["cache_row"][:], dtype=np.int64)
        delta = np.asarray(handle["delta"][:], dtype=np.int64)
        tau = np.asarray(handle["tau"][:], dtype=np.int64)
        if (
            len(rows) != spec.VALIDATION_ROWS
            or len(np.unique(rows)) != len(rows)
            or not np.array_equal(np.unique(delta), np.asarray(spec.DELTA_VALUES))
            or not np.array_equal(np.unique(tau), np.asarray(spec.TAU_VALUES))
        ):
            raise RuntimeError("diagnostic row identifiers differ")
        distributions = {
            metric: distribution(np.asarray(handle[f"metrics/{metric}"][:]))
            for metric in KEY_METRICS
        }
    equal_cell = summary.get("aggregates", {}).get("equal_cell_mean", {})
    if any(metric not in equal_cell for metric in KEY_METRICS):
        raise RuntimeError("diagnostic equal-cell aggregate differs")
    return {
        "summary_sha256": records["summary.json"],
        "row_metrics_h5_sha256": records["row-metrics.h5"],
        "equal_cell_mean": {metric: float(equal_cell[metric]) for metric in KEY_METRICS},
        "row_distributions": distributions,
        "bounds": summary["bounds"],
        "expert_training_cache": summary["expert_training_cache"],
        "expert_validation_cache": summary["expert_validation_cache"],
        "axis_diagnostics": summary["axis_diagnostics"],
        "elapsed_seconds": float(summary["elapsed_seconds"]),
        "peak_cuda_memory_allocated_bytes": int(
            summary["peak_cuda_memory_allocated_bytes"]
        ),
    }


def summarize_cells(cells: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    task_means: dict[str, dict[str, float]] = {}
    for task in spec.TASKS:
        task_means[task] = {
            metric: float(
                np.mean(
                    [cells[task][str(seed)]["equal_cell_mean"][metric] for seed in spec.MODEL_SEEDS]
                )
            )
            for metric in KEY_METRICS
        }
    equal_task = {
        metric: float(np.mean([task_means[task][metric] for task in spec.TASKS]))
        for metric in KEY_METRICS
    }
    contrasts: dict[str, dict[str, float | None]] = {}
    for task in spec.TASKS:
        bank = task_means[task]["bank_exact_robust_after_clip_fraction"]
        selected = task_means[task]["selected_exact_robust_after_clip_fraction"]
        raw_robust = task_means[task]["bank_raw_robust_oob_fraction"]
        raw_legal = task_means[task]["bank_raw_legal_oob_fraction"]
        raw_variance = task_means[task]["raw_candidate_variance"]
        clipped_variance = task_means[task]["clipped_candidate_variance"]
        contrasts[task] = {
            "selected_minus_bank_exact_robust_boundary_fraction": selected - bank,
            "selected_to_bank_exact_robust_boundary_ratio": (
                selected / bank if bank > 0 else None
            ),
            "raw_legal_to_raw_robust_oob_ratio": (
                raw_legal / raw_robust if raw_robust > 0 else None
            ),
            "post_clip_to_raw_variance_ratio": (
                clipped_variance / raw_variance if raw_variance > 0 else None
            ),
        }
    return {
        "task_seed_equal_cell_means": {
            task: {
                seed: value["equal_cell_mean"] for seed, value in cells[task].items()
            }
            for task in spec.TASKS
        },
        "task_seed_mean": task_means,
        "equal_task_seed_mean": equal_task,
        "descriptive_contrasts": contrasts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.evaluation_root, args.source_manifest, args.output_dir):
        reject_protected_path(path)
    if not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty boundary-analysis output")
    source_manifest_sha256 = sha256_file(args.source_manifest)
    cells: dict[str, dict[str, dict[str, Any]]] = {}
    for task in spec.TASKS:
        cells[task] = {}
        for seed in spec.MODEL_SEEDS:
            cells[task][str(seed)] = read_cell(
                args.evaluation_root / task / f"seed-{seed}",
                task=task,
                seed=seed,
                source_manifest_sha256=source_manifest_sha256,
            )
    audit = {
        "status": "ok",
        "kind": "gdp_cem_post_e14_boundary_diagnostic_analysis",
        "analysis_role": "P1_development_artifact_diagnosis_only",
        "cell_count": sum(len(value) for value in cells.values()),
        "cells": cells,
        "summary": summarize_cells(cells),
        "source_manifest_sha256": source_manifest_sha256,
        "analyzer_source_sha256": sha256_file(Path(__file__)),
        "descriptive_only": True,
        "e14_decision_changed": False,
        "e15_selected_or_authorized": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output_dir / "BOUNDARY-DIAGNOSTIC-AUDIT.json", audit)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
