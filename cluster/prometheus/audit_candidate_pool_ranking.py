#!/usr/bin/env python3
"""Read-only within-pool audit for the frozen PushT P2/P3 scorer results."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score


BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260812
TOP_K = (1, 4, 8)
METHOD_KEYS = {
    "M1_true": "raw_scores/M1_true",
    "M1_permuted_null": "raw_scores/M1_permuted_null",
    "M2_true": "raw_scores/M2_true",
    "M2_mismatched_null": "raw_scores/M2_mismatched_null",
    "M2_autoencoder_control": "raw_scores/M2_autoencoder_control",
    "M3_true": "raw_scores/M3_true",
    "M3_shuffled_null": "raw_scores/M3_shuffled_null",
    "G0a_macro_knn": "raw_scores/G0a_macro_knn",
    "G0b_subgoal_knn": "raw_scores/G0b_subgoal_knn",
}


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def get_dataset(handle: h5py.File, name: str) -> np.ndarray | None:
    try:
        return np.asarray(handle[name][:])
    except KeyError:
        return None


def label_structure(labels: np.ndarray) -> dict[str, Any]:
    prevalence = labels.mean(axis=1)
    mixed = (prevalence > 0.0) & (prevalence < 1.0)
    return {
        "pool_count": int(labels.shape[0]),
        "candidates_per_pool": int(labels.shape[1]),
        "candidate_count": int(labels.size),
        "failure_prevalence": float(labels.mean()),
        "all_attained_pool_count": int(np.count_nonzero(prevalence == 0.0)),
        "all_failure_pool_count": int(np.count_nonzero(prevalence == 1.0)),
        "mixed_pool_count": int(np.count_nonzero(mixed)),
        "mixed_pool_fraction": float(mixed.mean()),
        "per_pool_failure_prevalence": prevalence.tolist(),
    }


def core_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=np.bool_)
    scores = np.asarray(scores, dtype=np.float64)
    if labels.shape != scores.shape or labels.ndim != 2 or not np.isfinite(scores).all():
        raise RuntimeError("labels and scores must be finite, matching pool-by-candidate matrices")
    flat_labels = labels.reshape(-1)
    flat_scores = scores.reshape(-1)
    if flat_labels.all() or not flat_labels.any():
        raise RuntimeError("globally pooled labels contain one class")
    prevalence = labels.mean(axis=1)
    mixed_indices = np.flatnonzero((prevalence > 0.0) & (prevalence < 1.0))
    per_pool_auroc = []
    pair_weights = []
    for pool in mixed_indices:
        current_labels = labels[pool]
        per_pool_auroc.append(float(roc_auc_score(current_labels, scores[pool])))
        positives = int(current_labels.sum())
        pair_weights.append(positives * (len(current_labels) - positives))
    per_pool_auroc_np = np.asarray(per_pool_auroc, dtype=np.float64)
    pair_weights_np = np.asarray(pair_weights, dtype=np.float64)
    centered = scores - scores.mean(axis=1, keepdims=True)
    pool_mean = scores.mean(axis=1)
    total_variance = float(np.var(scores))
    between_variance = float(np.var(pool_mean))
    output: dict[str, Any] = {
        "pooled_auroc": float(roc_auc_score(flat_labels, flat_scores)),
        "mixed_pool_count": int(len(mixed_indices)),
        "mixed_pool_indices": mixed_indices.tolist(),
        "mixed_pool_auroc": per_pool_auroc_np.tolist(),
        "macro_mixed_pool_auroc": float(per_pool_auroc_np.mean()) if len(per_pool_auroc_np) else None,
        "pair_weighted_within_pool_auroc": (
            float(np.average(per_pool_auroc_np, weights=pair_weights_np)) if pair_weights_np.sum() else None
        ),
        "pool_centered_global_auroc": float(roc_auc_score(flat_labels, centered.reshape(-1))),
        "pool_mean_score_vs_failure_prevalence_spearman": float(spearmanr(pool_mean, prevalence).statistic),
        "between_pool_score_variance_fraction": between_variance / total_variance if total_variance else 0.0,
        "baseline_failure_rate_mean_over_pools": float(prevalence.mean()),
        "lowest_score_selection": {},
    }
    for k in TOP_K:
        selected_failure = np.empty(labels.shape[0], dtype=np.float64)
        for pool in range(labels.shape[0]):
            # Stable sorting makes score ties deterministic by candidate index.
            selected = np.argsort(scores[pool], kind="stable")[:k]
            selected_failure[pool] = labels[pool, selected].mean()
        reduction = prevalence - selected_failure
        output["lowest_score_selection"][f"top_{k}"] = {
            "failure_rate_mean_over_pools": float(selected_failure.mean()),
            "baseline_minus_selected_failure_rate_mean": float(reduction.mean()),
            "per_pool_failure_rate": selected_failure.tolist(),
        }
    return output


def bootstrap(
    labels: np.ndarray,
    scores: np.ndarray,
    rng: np.random.Generator,
) -> dict[str, Any]:
    pool_count = labels.shape[0]
    distributions: dict[str, list[float]] = {
        "pooled_auroc": [],
        "pair_weighted_within_pool_auroc": [],
        **{f"top_{k}_failure_rate_reduction": [] for k in TOP_K},
    }
    attempts = 0
    while len(distributions["pooled_auroc"]) < BOOTSTRAP_REPLICATES:
        attempts += 1
        if attempts > BOOTSTRAP_REPLICATES * 10:
            raise RuntimeError("could not obtain enough valid pool bootstrap samples")
        chosen = rng.integers(0, pool_count, size=pool_count)
        current_labels = labels[chosen]
        current_scores = scores[chosen]
        flat_labels = current_labels.reshape(-1)
        if flat_labels.all() or not flat_labels.any():
            continue
        prevalence = current_labels.mean(axis=1)
        mixed = np.flatnonzero((prevalence > 0.0) & (prevalence < 1.0))
        if len(mixed) == 0:
            continue
        pool_auc = []
        pair_weights = []
        for pool in mixed:
            pool_auc.append(float(roc_auc_score(current_labels[pool], current_scores[pool])))
            positives = int(current_labels[pool].sum())
            pair_weights.append(positives * (current_labels.shape[1] - positives))
        distributions["pooled_auroc"].append(float(roc_auc_score(flat_labels, current_scores.reshape(-1))))
        distributions["pair_weighted_within_pool_auroc"].append(
            float(np.average(np.asarray(pool_auc), weights=np.asarray(pair_weights)))
        )
        for k in TOP_K:
            selected_failure = []
            for pool in range(pool_count):
                selected = np.argsort(current_scores[pool], kind="stable")[:k]
                selected_failure.append(float(current_labels[pool, selected].mean()))
            reduction = float(prevalence.mean() - np.mean(selected_failure))
            distributions[f"top_{k}_failure_rate_reduction"].append(reduction)
    result: dict[str, Any] = {
        "valid_replicates": BOOTSTRAP_REPLICATES,
        "attempts": attempts,
        "discarded_replicates": attempts - BOOTSTRAP_REPLICATES,
        "ci95": {},
    }
    for name, values in distributions.items():
        array = np.asarray(values, dtype=np.float64)
        result["ci95"][name] = [
            float(np.quantile(array, 0.025)),
            float(np.quantile(array, 0.975)),
        ]
    return result


def analyze_partition(
    name: str,
    h5_path: Path,
    manifest_path: Path,
    label_key: str,
    rng_seed_sequence: np.random.SeedSequence,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_h5_sha = manifest.get("output_h5_sha256")
    actual_h5_sha = sha256_file(h5_path)
    if expected_h5_sha != actual_h5_sha:
        raise RuntimeError(f"{name} HDF5 differs from manifest")
    with h5py.File(h5_path, "r") as handle:
        labels_raw = get_dataset(handle, label_key)
        if labels_raw is None:
            raise RuntimeError(f"missing label dataset {label_key}")
        labels = np.asarray(labels_raw, dtype=np.bool_)
        methods: dict[str, np.ndarray] = {}
        for method, key in METHOD_KEYS.items():
            score = get_dataset(handle, key)
            if score is not None:
                methods[method] = np.asarray(score, dtype=np.float64)
    if labels.ndim != 2:
        raise RuntimeError(f"{name} labels are not pool by candidate")
    result: dict[str, Any] = {
        "label_structure": label_structure(labels),
        "methods": {},
        "inputs": {
            "h5": str(h5_path),
            "h5_sha256": actual_h5_sha,
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "label_key": label_key,
        },
    }
    child_sequences = rng_seed_sequence.spawn(len(methods))
    ensemble_arrays: dict[str, np.ndarray] = {}
    for (method, raw), child in zip(methods.items(), child_sequences, strict=True):
        if raw.ndim == 3:
            if raw.shape[1:] != labels.shape:
                raise RuntimeError(f"{name} {method} shape mismatch: {raw.shape}")
            ensemble = raw.mean(axis=0)
            seed_records = [core_metrics(labels, raw[index]) for index in range(raw.shape[0])]
        elif raw.ndim == 2:
            if raw.shape != labels.shape:
                raise RuntimeError(f"{name} {method} shape mismatch: {raw.shape}")
            ensemble = raw
            seed_records = None
        else:
            raise RuntimeError(f"{name} {method} score rank unsupported: {raw.shape}")
        ensemble_arrays[method] = ensemble
        ensemble_metrics = core_metrics(labels, ensemble)
        bootstrap_result = bootstrap(labels, ensemble, np.random.default_rng(child))
        interpretation = {
            "pool_structure_limits_global_auroc": bool(
                result["label_structure"]["mixed_pool_fraction"] < 0.5
            ),
            "global_signal_without_within_pool_ranking": bool(
                ensemble_metrics["pooled_auroc"] >= 0.70
                and ensemble_metrics["pair_weighted_within_pool_auroc"] <= 0.55
            ),
            "useful_top4_ranking": bool(
                bootstrap_result["ci95"]["top_4_failure_rate_reduction"][0] > 0.0
            ),
            "within_pool_ranking_above_chance": bool(
                bootstrap_result["ci95"]["pair_weighted_within_pool_auroc"][0] > 0.5
            ),
        }
        result["methods"][method] = {
            "seed_records": seed_records,
            "ensemble": ensemble_metrics,
            "pool_bootstrap": bootstrap_result,
            "interpretations_under_prefrozen_rules": interpretation,
        }
    return result, {"labels": labels, **ensemble_arrays}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p2-h5", type=Path, required=True)
    parser.add_argument("--p2-manifest", type=Path, required=True)
    parser.add_argument("--p3-h5", type=Path, required=True)
    parser.add_argument("--p3-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite pool-ranking audit")
    started = time.time()
    master = np.random.SeedSequence(BOOTSTRAP_SEED)
    p2_result, p2_arrays = analyze_partition(
        "P2", args.p2_h5, args.p2_manifest, "failure_label", master.spawn(1)[0]
    )
    p3_result, p3_arrays = analyze_partition(
        "P3", args.p3_h5, args.p3_manifest, "labels/primary", master.spawn(1)[0]
    )

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    with h5py.File(partial, "x") as output:
        output.attrs["classification"] = "pusht_candidate_pool_ranking_audit"
        output.attrs["status"] = "ok"
        for partition, arrays in (("P2", p2_arrays), ("P3", p3_arrays)):
            group = output.create_group(partition)
            for name, value in arrays.items():
                group.create_dataset(name, data=value, compression="gzip" if value.ndim >= 2 else None)
        output.flush()
    os.replace(partial, args.output_h5)
    result = {
        "status": "ok",
        "classification": "pusht_candidate_pool_ranking_audit",
        "post_hoc_boundary": "read-only diagnosis; no selection, promotion, P3, or P4 decision changed",
        "bootstrap": {"replicates": BOOTSTRAP_REPLICATES, "seed": BOOTSTRAP_SEED},
        "P2": p2_result,
        "P3": p3_result,
        "inputs": {"spec": str(args.spec), "spec_sha256": sha256_file(args.spec)},
        "output_h5": str(args.output_h5),
        "output_h5_sha256": sha256_file(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
