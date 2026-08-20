#!/usr/bin/env python3
"""Reanalyze the existing M2 P2 width/sigma grids with within-pool metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from audit_candidate_pool_ranking import core_metrics, label_structure


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def compact_metrics(labels: np.ndarray, score: np.ndarray) -> dict[str, Any]:
    metrics = core_metrics(labels, score)
    return {
        "pooled_auroc": metrics["pooled_auroc"],
        "pair_weighted_within_pool_auroc": metrics["pair_weighted_within_pool_auroc"],
        "macro_mixed_pool_auroc": metrics["macro_mixed_pool_auroc"],
        "pool_centered_global_auroc": metrics["pool_centered_global_auroc"],
        "mixed_pool_auroc": metrics["mixed_pool_auroc"],
        "top_1_failure_rate_reduction": metrics["lowest_score_selection"]["top_1"][
            "baseline_minus_selected_failure_rate_mean"
        ],
        "top_4_failure_rate_reduction": metrics["lowest_score_selection"]["top_4"][
            "baseline_minus_selected_failure_rate_mean"
        ],
        "top_8_failure_rate_reduction": metrics["lowest_score_selection"]["top_8"][
            "baseline_minus_selected_failure_rate_mean"
        ],
    }


def analyze(name: str, directory: Path) -> tuple[dict[str, Any], dict[tuple[int, float], dict[str, Any]]]:
    manifest_path = directory / "manifest.json"
    h5_path = directory / "scores.h5"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256_file(h5_path) != manifest["output_h5_sha256"]:
        raise RuntimeError(f"{name} score HDF5 hash mismatch")
    with h5py.File(h5_path, "r") as handle:
        labels = np.asarray(handle["failure_label"][:], dtype=np.bool_)
        widths = np.asarray(handle["m2_width"][:], dtype=np.int64)
        sigmas = np.asarray(handle["m2_sigma"][:], dtype=np.float64)
        seeds = np.asarray(handle["training_seed"][:], dtype=np.int64)
        score = np.asarray(handle["m2_raw_score"][:], dtype=np.float64)
    expected_shape = (len(widths), len(seeds), len(sigmas), *labels.shape)
    if score.shape != expected_shape:
        raise RuntimeError(f"{name} M2 grid shape mismatch: {score.shape}")

    records: list[dict[str, Any]] = []
    lookup: dict[tuple[int, float], dict[str, Any]] = {}
    for width_index, width_value in enumerate(widths):
        width = int(width_value)
        for sigma_index, sigma_value in enumerate(sigmas):
            sigma = float(sigma_value)
            ensemble = score[width_index, :, sigma_index].mean(axis=0)
            metrics = compact_metrics(labels, ensemble)
            record = {
                "width": width,
                "sigma": sigma,
                "ensemble": metrics,
                "seed_pair_weighted_within_pool_auroc": [
                    compact_metrics(labels, score[width_index, seed_index, sigma_index])[
                        "pair_weighted_within_pool_auroc"
                    ]
                    for seed_index in range(len(seeds))
                ],
            }
            records.append(record)
            lookup[(width, sigma)] = record
    records.sort(key=lambda record: (record["width"], record["sigma"]))
    selected = max(
        records,
        key=lambda record: (
            record["ensemble"]["pair_weighted_within_pool_auroc"],
            -record["width"],
            -record["sigma"],
        ),
    )
    original = (int(manifest["M2"]["selected_width"]), float(manifest["M2"]["selected_sigma"]))
    result = {
        "inputs": {
            "manifest_sha256": sha256_file(manifest_path),
            "h5_sha256": sha256_file(h5_path),
        },
        "label_structure": label_structure(labels),
        "training_seeds": seeds.tolist(),
        "grid_records": records,
        "original_global_selection": {
            "width": original[0],
            "sigma": original[1],
            "metrics": lookup[original]["ensemble"],
        },
        "descriptive_within_pool_selection": selected,
        "original_global_and_within_selection_match": bool(
            original == (selected["width"], selected["sigma"])
        ),
    }
    return result, lookup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pusht-dir", type=Path, required=True)
    parser.add_argument("--tworoom-dir", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        raise SystemExit("refusing to overwrite M2 within-pool grid audit")
    pusht, pusht_lookup = analyze("pusht", args.pusht_dir)
    tworoom, tworoom_lookup = analyze("tworoom", args.tworoom_dir)
    pusht_selected_key = (
        int(pusht["descriptive_within_pool_selection"]["width"]),
        float(pusht["descriptive_within_pool_selection"]["sigma"]),
    )
    tworoom_original_key = (
        int(tworoom["original_global_selection"]["width"]),
        float(tworoom["original_global_selection"]["sigma"]),
    )
    shared_above = [
        {"width": key[0], "sigma": key[1]}
        for key in sorted(pusht_lookup)
        if pusht_lookup[key]["ensemble"]["pair_weighted_within_pool_auroc"] > 0.60
        and tworoom_lookup[key]["ensemble"]["pair_weighted_within_pool_auroc"] > 0.60
    ]
    result = {
        "status": "ok",
        "classification": "m2_p2_within_pool_grid_reanalysis",
        "partition_scope": "P2-development-only",
        "reporting_boundary": "post-hoc exploratory search; no P3/P4 artifact was read or changed",
        "spec": str(args.spec),
        "spec_sha256": sha256_file(args.spec),
        "environments": {"pusht": pusht, "tworoom": tworoom},
        "frozen_transfer_diagnostic": {
            "pusht_within_pool_selected_configuration": {
                "width": pusht_selected_key[0],
                "sigma": pusht_selected_key[1],
            },
            "tworoom_metrics_at_pusht_selection": tworoom_lookup[pusht_selected_key]["ensemble"],
            "tworoom_original_configuration": {
                "width": tworoom_original_key[0],
                "sigma": tworoom_original_key[1],
            },
            "pusht_metrics_at_tworoom_original": pusht_lookup[tworoom_original_key]["ensemble"],
        },
        "descriptive_flags": {
            "any_shared_configuration_above_0_60": bool(shared_above),
            "shared_configurations_above_0_60": shared_above,
            "pusht_selected_transfer_above_0_60": bool(
                tworoom_lookup[pusht_selected_key]["ensemble"][
                    "pair_weighted_within_pool_auroc"
                ]
                > 0.60
            ),
        },
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

