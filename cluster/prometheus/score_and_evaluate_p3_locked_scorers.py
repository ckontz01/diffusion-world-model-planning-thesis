#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from score_and_select_p2_true_scorers import (
    LATENT_DIM,
    MACRO_DIM,
    NOISE_DRAWS,
    SEEDS,
    SIGMAS,
    atomic_json,
    binary_metrics,
    score_m1,
    score_m2,
    score_m3,
    sha256_file,
    training_paths,
    verify_inventory,
    verify_training_run,
)
from score_nulls_autoencoder_and_fit_p2_calibrators import (
    calibration_metrics,
    score_autoencoder,
    score_m1_null,
    score_m2_null,
    sigmoid,
    verify_training_result,
)


POOL_COUNT = 24
CANDIDATE_COUNT = 64
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260728
SELECTED_M1_WIDTH = 512
SELECTED_M2_WIDTH = 1024
SELECTED_M2_SIGMA = 0.25
NULL_JOB_ID = 294841
AUTOENCODER_JOB_ID = 294842
P2_TRUE_H5_SHA256 = "63bad1d8c97902f682a6aacfa21ef451f8c0cee7373a501b2de0d8f3e4b10ba1"
P2_CALIBRATION_H5_SHA256 = "eced1f2842bc7ba9bda81ae4d2647200c3f30c7b1f25679025cfb9c60f9cad3f"
P2_LABEL_H5_SHA256 = "72031cd0ea7a02af2a33c61fb3db6f42c47b2982a31a544a2fe3fff011fc76c4"
P3_CANDIDATE_H5_SHA256 = "64341a03c5d618ebe1b5c6c86f701add6ee9ab841f2a20e57ead23fde35efdaf"
NOISE_H5_SHA256 = "3a94b491079e6030137480352d1ac0d985214db6ebd96f271539b2022edcf74b"


def verify_three_file_artifact(
    directory: Path,
    *,
    data_filename: str,
    classification: str,
    locked_data_sha256: str | None = None,
) -> tuple[dict[str, Any], Path]:
    inventory = verify_inventory(directory)
    expected = {data_filename, "manifest.json", "provenance.txt"}
    if set(inventory) != expected:
        raise RuntimeError(f"unexpected artifact inventory in {directory}: {sorted(inventory)}")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "ok" or manifest.get("classification") != classification:
        raise RuntimeError(f"unexpected artifact classification in {directory}")
    data_path = directory / data_filename
    data_sha = inventory[data_filename]
    manifest_sha = manifest.get("output_h5_sha256")
    if manifest_sha != data_sha:
        raise RuntimeError(f"artifact HDF5 differs from manifest in {directory}")
    if locked_data_sha256 is not None and data_sha != locked_data_sha256:
        raise RuntimeError(f"artifact differs from the immutable P3 lock: {data_path}")
    return manifest, data_path


def robust_knn_isolation(values: np.ndarray, k: int = 3) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 3 or values.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("invalid P3 candidate-pool geometry")
    output = np.empty((POOL_COUNT, CANDIDATE_COUNT), dtype=np.float64)
    for pool in range(POOL_COUNT):
        current = values[pool]
        median = np.median(current, axis=0)
        q25, q75 = np.quantile(current, (0.25, 0.75), axis=0)
        scale = q75 - q25
        scale[~np.isfinite(scale) | (scale == 0.0)] = 1.0
        standardized = (current - median) / scale
        difference = standardized[:, None, :] - standardized[None, :, :]
        distance = np.sqrt(np.sum(difference * difference, axis=-1))
        np.fill_diagonal(distance, np.inf)
        output[pool] = np.partition(distance, kth=k - 1, axis=1)[:, :k].mean(axis=1)
    if not np.isfinite(output).all():
        raise RuntimeError("non-finite G0 isolation score")
    return output.astype(np.float32)


def safe_binary_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=np.bool_).reshape(-1)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    if labels.shape != scores.shape or not np.isfinite(scores).all():
        raise RuntimeError("invalid per-pool metric input")
    positives = int(labels.sum())
    negatives = int(len(labels) - positives)
    if positives == 0 or negatives == 0:
        prevalence = positives / len(labels)
        return {
            "candidate_count": int(len(labels)),
            "failure_count": positives,
            "attainment_count": negatives,
            "failure_prevalence": prevalence,
            "auroc": None,
            "average_precision": None,
            "average_precision_minus_prevalence": None,
        }
    return binary_metrics(labels, scores)


def per_pool_diagnostics(
    labels: np.ndarray, scores: np.ndarray, *, calibrated: bool
) -> list[dict[str, Any]]:
    labels = np.asarray(labels, dtype=np.bool_)
    scores = np.asarray(scores, dtype=np.float64)
    if labels.shape != (POOL_COUNT, CANDIDATE_COUNT) or scores.shape != labels.shape:
        raise RuntimeError("invalid per-pool diagnostic geometry")
    records: list[dict[str, Any]] = []
    for pool in range(POOL_COUNT):
        record: dict[str, Any] = {
            "pool_index": pool,
            **safe_binary_metrics(labels[pool], scores[pool]),
            "mean_score": float(scores[pool].mean()),
        }
        if calibrated:
            record["calibration"] = calibration_metrics(labels[pool], scores[pool])
        records.append(record)
    return records


def apply_isotonic(
    scores: np.ndarray, upper_score: np.ndarray, failure_probability: np.ndarray
) -> np.ndarray:
    indices = np.searchsorted(upper_score, scores, side="left")
    indices = np.clip(indices, 0, len(failure_probability) - 1)
    return failure_probability[indices]


def load_calibrators(calibration_h5: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    with h5py.File(calibration_h5, "r") as handle:
        if handle.attrs.get("classification") != "p2_null_control_scores_and_calibrators":
            raise RuntimeError("P2 calibration HDF5 classification changed")
        if (
            int(handle.attrs["selected_m1_width"]) != SELECTED_M1_WIDTH
            or int(handle.attrs["selected_m2_width"]) != SELECTED_M2_WIDTH
            or float(handle.attrs["selected_m2_sigma"]) != SELECTED_M2_SIGMA
        ):
            raise RuntimeError("P2 calibration HDF5 selected settings changed")
        if not np.array_equal(handle["training_seed"][:], np.asarray(SEEDS)):
            raise RuntimeError("P2 calibration seed order changed")
        for method in ("M1", "M2", "M3"):
            method_records: list[dict[str, Any]] = []
            group = handle[f"calibrators/{method}"]
            for seed in SEEDS:
                seed_group = group[f"seed-{seed}"]
                slope = float(seed_group.attrs["platt_raw_score_slope"])
                intercept = float(seed_group.attrs["platt_raw_score_intercept"])
                if not np.isfinite((slope, intercept)).all() or slope < 0.0:
                    raise RuntimeError(f"invalid frozen Platt map for {method}, seed {seed}")
                isotonic = seed_group["isotonic"]
                upper = np.asarray(isotonic["upper_score"][:], dtype=np.float64)
                probability = np.asarray(
                    isotonic["failure_probability"][:], dtype=np.float64
                )
                if (
                    upper.ndim != 1
                    or probability.shape != upper.shape
                    or len(upper) == 0
                    or np.any(np.diff(upper) < 0.0)
                    or np.any(np.diff(probability) < -1.0e-15)
                ):
                    raise RuntimeError(f"invalid frozen isotonic map for {method}, seed {seed}")
                method_records.append(
                    {
                        "seed": seed,
                        "platt_slope": slope,
                        "platt_intercept": intercept,
                        "isotonic_upper_score": upper,
                        "isotonic_failure_probability": probability,
                    }
                )
            result[method] = method_records
    return result


def calibrate_scores(
    raw_scores: np.ndarray, calibrators: list[dict[str, Any]]
) -> tuple[np.ndarray, np.ndarray]:
    raw_scores = np.asarray(raw_scores, dtype=np.float64)
    if raw_scores.shape != (len(SEEDS), POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("invalid raw-score ensemble geometry")
    platt = np.empty_like(raw_scores)
    isotonic = np.empty_like(raw_scores)
    for seed_index, record in enumerate(calibrators):
        platt[seed_index] = sigmoid(
            record["platt_slope"] * raw_scores[seed_index]
            + record["platt_intercept"]
        )
        isotonic[seed_index] = apply_isotonic(
            raw_scores[seed_index],
            record["isotonic_upper_score"],
            record["isotonic_failure_probability"],
        )
    if np.any(platt < 0.0) or np.any(platt > 1.0):
        raise RuntimeError("invalid Platt probability")
    return platt, isotonic


def calibrated_report(
    labels_by_rule: dict[str, np.ndarray],
    platt: np.ndarray,
    isotonic: np.ndarray,
) -> dict[str, Any]:
    platt_ensemble = platt.mean(axis=0)
    isotonic_ensemble = isotonic.mean(axis=0)
    report: dict[str, Any] = {}
    for rule, labels in labels_by_rule.items():
        flat_labels = labels.reshape(-1)
        seedwise = [
            {
                "seed": seed,
                **binary_metrics(flat_labels, platt[index].reshape(-1)),
            }
            for index, seed in enumerate(SEEDS)
        ]
        ensemble_metrics = binary_metrics(flat_labels, platt_ensemble.reshape(-1))
        ensemble_metrics["calibration"] = calibration_metrics(
            flat_labels, platt_ensemble.reshape(-1)
        )
        isotonic_metrics = binary_metrics(
            flat_labels, isotonic_ensemble.reshape(-1)
        )
        isotonic_metrics["calibration"] = calibration_metrics(
            flat_labels, isotonic_ensemble.reshape(-1)
        )
        report[rule] = {
            "seedwise_platt": seedwise,
            "primary_platt_ensemble": ensemble_metrics,
            "isotonic_ensemble_sensitivity": isotonic_metrics,
        }
    report["per_pool_primary_platt"] = per_pool_diagnostics(
        labels_by_rule["primary"], platt_ensemble, calibrated=True
    )
    return report


def uncalibrated_report(
    labels_by_rule: dict[str, np.ndarray], scores: np.ndarray
) -> dict[str, Any]:
    scores = np.asarray(scores)
    if scores.ndim == 3:
        if scores.shape != (len(SEEDS), POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError("invalid seedwise diagnostic score geometry")
        ensemble = scores.mean(axis=0)
        seedwise_scores = scores
    elif scores.shape == (POOL_COUNT, CANDIDATE_COUNT):
        ensemble = scores
        seedwise_scores = None
    else:
        raise RuntimeError("invalid diagnostic score geometry")
    report: dict[str, Any] = {}
    for rule, labels in labels_by_rule.items():
        flat_labels = labels.reshape(-1)
        record: dict[str, Any] = {
            "ensemble": binary_metrics(flat_labels, ensemble.reshape(-1))
        }
        if seedwise_scores is not None:
            record["seedwise"] = [
                {
                    "seed": seed,
                    **binary_metrics(flat_labels, seedwise_scores[index].reshape(-1)),
                }
                for index, seed in enumerate(SEEDS)
            ]
        report[rule] = record
    report["per_pool_primary"] = per_pool_diagnostics(
        labels_by_rule["primary"], ensemble, calibrated=False
    )
    return report


def auroc_only(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=np.bool_).reshape(-1)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    positives = int(labels.sum())
    negatives = int(len(labels) - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    sorted_labels = labels[order]
    if np.all(sorted_scores[1:] != sorted_scores[:-1]):
        positive_rank_sum = float((np.flatnonzero(sorted_labels) + 1).sum())
    else:
        _, inverse, counts = np.unique(
            sorted_scores, return_inverse=True, return_counts=True
        )
        starts = np.cumsum(np.r_[0, counts[:-1]])
        average_rank = starts + 0.5 * (counts + 1.0)
        positive_rank_sum = float(average_rank[inverse][sorted_labels].sum())
    return float(
        (positive_rank_sum - positives * (positives + 1) / 2.0)
        / (positives * negatives)
    )


def bootstrap_auroc(
    labels: np.ndarray, scores: np.ndarray, pool_resamples: np.ndarray
) -> np.ndarray:
    output = np.empty(len(pool_resamples), dtype=np.float64)
    for index, pools in enumerate(pool_resamples):
        output[index] = auroc_only(labels[pools], scores[pools])
    if not np.isfinite(output).all():
        raise RuntimeError("a pool-cluster bootstrap resample contains only one class")
    return output


def interval(values: np.ndarray) -> list[float]:
    low, high = np.quantile(values, (0.025, 0.975), method="linear")
    return [float(low), float(high)]


def checkpoint_record_map(records: list[dict[str, Any]]) -> dict[tuple[Any, ...], str]:
    output: dict[tuple[Any, ...], str] = {}
    for record in records:
        key = (
            record["method"],
            record["condition"],
            record.get("width"),
            int(record["seed"]),
        )
        if key in output:
            raise RuntimeError(f"duplicate frozen checkpoint record: {key}")
        output[key] = record["checkpoint_sha256"]
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p3-labeled-dir", type=Path, required=True)
    parser.add_argument("--p2-true-score-dir", type=Path, required=True)
    parser.add_argument("--p2-calibration-dir", type=Path, required=True)
    parser.add_argument("--m1-root", type=Path, required=True)
    parser.add_argument("--m2-root", type=Path, required=True)
    parser.add_argument("--m3-root", type=Path, required=True)
    parser.add_argument("--autoencoder-root", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--m2-batch-size", type=int, default=2048)
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite locked P3 scorer audit")
    if args.device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("locked P3 scorer audit requires CUDA")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda")
    started = time.time()

    p3_manifest, p3_h5 = verify_three_file_artifact(
        args.p3_labeled_dir,
        data_filename="labeled-candidates.h5",
        classification="p3_stratum3_labeled_candidate_audit",
    )
    if p3_manifest.get("partition") != "P3-locked":
        raise RuntimeError("P3 labels are not marked locked")
    if p3_manifest["inputs"]["candidate_h5_sha256"] != P3_CANDIDATE_H5_SHA256:
        raise RuntimeError("P3 labels do not derive from the locked candidate artifact")

    true_manifest, true_h5 = verify_three_file_artifact(
        args.p2_true_score_dir,
        data_filename="scores.h5",
        classification="p2_true_scorer_raw_score_selection",
        locked_data_sha256=P2_TRUE_H5_SHA256,
    )
    calibration_manifest, calibration_h5 = verify_three_file_artifact(
        args.p2_calibration_dir,
        data_filename="audit-and-calibrators.h5",
        classification="p2_null_control_scores_and_calibrators",
        locked_data_sha256=P2_CALIBRATION_H5_SHA256,
    )
    if (
        true_manifest["inputs"]["labeled_h5_sha256"] != P2_LABEL_H5_SHA256
        or calibration_manifest["inputs"]["labeled_h5_sha256"] != P2_LABEL_H5_SHA256
        or calibration_manifest["inputs"]["true_score_h5_sha256"] != P2_TRUE_H5_SHA256
    ):
        raise RuntimeError("P2 selection/calibration lineage differs from the lock")
    if (
        int(true_manifest["M1"]["selected_width"]) != SELECTED_M1_WIDTH
        or int(true_manifest["M2"]["selected_width"]) != SELECTED_M2_WIDTH
        or float(true_manifest["M2"]["selected_sigma"]) != SELECTED_M2_SIGMA
    ):
        raise RuntimeError("P2 true-scorer selections differ from the lock")
    selected = calibration_manifest["selected_configuration"]
    if (
        int(selected["M1_width"]) != SELECTED_M1_WIDTH
        or int(selected["M2_width"]) != SELECTED_M2_WIDTH
        or float(selected["M2_sigma"]) != SELECTED_M2_SIGMA
    ):
        raise RuntimeError("P2 calibration selections differ from the lock")

    with h5py.File(p3_h5, "r") as labeled:
        if (
            labeled.attrs.get("classification")
            != "p3_stratum3_labeled_candidate_audit"
            or labeled.attrs.get("partition") != "P3-locked"
        ):
            raise RuntimeError("P3 labeled HDF5 classification changed")
        if not np.isclose(
            float(labeled.attrs["selected_delta"]),
            0.7168711644368866,
            rtol=0.0,
            atol=1.0e-15,
        ):
            raise RuntimeError("P3 label tolerance differs from the lock")
        pool_id = np.asarray(labeled["pool_id"][:], dtype=np.int64)
        source_np = np.asarray(labeled["source_latent"][:], dtype=np.float32)
        target_np = np.asarray(labeled["selected_subgoal"][:], dtype=np.float32)
        macro_np = np.asarray(labeled["selected_first_macro"][:], dtype=np.float32)
        attainment_rate = np.asarray(labeled["attainment_rate"][:], dtype=np.float32)
        attained_2 = np.asarray(labeled["label_at_least_2_of_5"][:], dtype=np.bool_)
        attained_3 = np.asarray(
            labeled["primary_label_at_least_3_of_5"][:], dtype=np.bool_
        )
        attained_4 = np.asarray(labeled["label_at_least_4_of_5"][:], dtype=np.bool_)
    if not np.array_equal(pool_id, np.arange(POOL_COUNT)):
        raise RuntimeError("P3 pool IDs are incomplete or unordered")
    if source_np.shape != (POOL_COUNT, LATENT_DIM):
        raise RuntimeError("unexpected P3 source-latent shape")
    if target_np.shape != (POOL_COUNT, CANDIDATE_COUNT, LATENT_DIM):
        raise RuntimeError("unexpected P3 target-latent shape")
    if macro_np.shape != (POOL_COUNT, CANDIDATE_COUNT, MACRO_DIM):
        raise RuntimeError("unexpected P3 macro shape")
    expected_label_shape = (POOL_COUNT, CANDIDATE_COUNT)
    if any(value.shape != expected_label_shape for value in (attainment_rate, attained_2, attained_3, attained_4)):
        raise RuntimeError("unexpected P3 attainment-label shape")
    if np.any(attained_4 & ~attained_3) or np.any(attained_3 & ~attained_2):
        raise RuntimeError("P3 sensitivity labels are not nested")
    labels_by_rule = {
        "primary": ~attained_3,
        "failure_at_2_of_5": ~attained_2,
        "failure_at_4_of_5": ~attained_4,
    }
    for name, labels in labels_by_rule.items():
        if labels.all() or not labels.any():
            raise RuntimeError(f"P3 {name} has only one class")

    stats_sha = p3_manifest["inputs"]["stats_npz_sha256"]
    if stats_sha != calibration_manifest["inputs"]["stats_npz_sha256"]:
        raise RuntimeError("P3 labels and P2 calibrators use different P1 statistics")
    source_flat_np = np.broadcast_to(source_np[:, None, :], target_np.shape).reshape(
        -1, LATENT_DIM
    ).copy()
    source = torch.from_numpy(source_flat_np).to(device)
    target = torch.from_numpy(target_np.reshape(-1, LATENT_DIM)).to(device)
    macro = torch.from_numpy(macro_np.reshape(-1, MACRO_DIM)).to(device)

    noise_manifest = json.loads(args.noise_manifest.read_text(encoding="utf-8"))
    if (
        noise_manifest.get("status") != "ok"
        or noise_manifest.get("classification")
        != "frozen_m2_deployment_common_random_numbers"
        or sha256_file(args.noise_npy) != NOISE_H5_SHA256
        or noise_manifest.get("output_npy_sha256") != NOISE_H5_SHA256
    ):
        raise RuntimeError("M2 noise bank differs from the P3 lock")
    noise_np = np.load(args.noise_npy, allow_pickle=False)
    if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
        raise RuntimeError("unexpected locked M2 noise bank")
    noise = torch.from_numpy(noise_np).to(device)

    locked_true_checkpoints = checkpoint_record_map(true_manifest["checkpoints"])
    locked_control_checkpoints = checkpoint_record_map(calibration_manifest["checkpoints"])
    raw_scores = {
        name: np.empty((len(SEEDS), POOL_COUNT, CANDIDATE_COUNT), dtype=np.float32)
        for name in (
            "M1_true",
            "M1_permuted_null",
            "M2_true",
            "M2_mismatched_null",
            "M2_autoencoder_control",
            "M3_true",
            "M3_shuffled_null",
        )
    }
    checkpoint_records: list[dict[str, Any]] = []
    for seed_index, seed in enumerate(SEEDS):
        m1_dir, m1_checkpoint, m1_result = training_paths(
            args.m1_root, "m1", "true", SELECTED_M1_WIDTH, seed_index
        )
        _, checkpoint_sha, result_sha = verify_training_run(
            m1_dir,
            m1_checkpoint,
            m1_result,
            method="m1",
            condition="true",
            width=SELECTED_M1_WIDTH,
            seed=seed,
        )
        if locked_true_checkpoints[("M1", "true", SELECTED_M1_WIDTH, seed)] != checkpoint_sha:
            raise RuntimeError("M1 true checkpoint differs from P2 selection")
        raw_scores["M1_true"][seed_index] = score_m1(
            m1_checkpoint,
            source,
            target,
            macro,
            expected_width=SELECTED_M1_WIDTH,
            expected_seed=seed,
            expected_stats_sha=stats_sha,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        checkpoint_records.append({"method": "M1", "condition": "true", "seed": seed, "checkpoint_sha256": checkpoint_sha, "training_result_sha256": result_sha})

        m1_null_dir = args.m1_root / f"permuted-width{SELECTED_M1_WIDTH}-seed{seed}-job-{NULL_JOB_ID}_{seed_index}"
        m1_null_checkpoint = m1_null_dir / "run/best-checkpoint.pt"
        m1_null_result = m1_null_dir / "run/training-result.json"
        _, checkpoint_sha, result_sha = verify_training_result(
            m1_null_dir,
            m1_null_checkpoint,
            m1_null_result,
            method="M1",
            condition="permuted",
            seed=seed,
            width=SELECTED_M1_WIDTH,
        )
        if locked_control_checkpoints[("M1", "permuted", SELECTED_M1_WIDTH, seed)] != checkpoint_sha:
            raise RuntimeError("M1 null checkpoint differs from P2 calibration")
        raw_scores["M1_permuted_null"][seed_index] = score_m1_null(
            m1_null_checkpoint,
            source,
            target,
            macro,
            width=SELECTED_M1_WIDTH,
            seed=seed,
            stats_sha=stats_sha,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        checkpoint_records.append({"method": "M1", "condition": "permuted", "seed": seed, "checkpoint_sha256": checkpoint_sha, "training_result_sha256": result_sha})

        m2_dir, m2_checkpoint, m2_result = training_paths(
            args.m2_root, "m2", "true", SELECTED_M2_WIDTH, seed_index
        )
        _, checkpoint_sha, result_sha = verify_training_run(
            m2_dir,
            m2_checkpoint,
            m2_result,
            method="m2",
            condition="true",
            width=SELECTED_M2_WIDTH,
            seed=seed,
        )
        if locked_true_checkpoints[("M2", "true", SELECTED_M2_WIDTH, seed)] != checkpoint_sha:
            raise RuntimeError("M2 true checkpoint differs from P2 selection")
        raw_scores["M2_true"][seed_index] = score_m2(
            m2_checkpoint,
            source,
            target,
            noise,
            SELECTED_M2_SIGMA,
            expected_width=SELECTED_M2_WIDTH,
            expected_seed=seed,
            expected_stats_sha=stats_sha,
            batch_size=args.m2_batch_size,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        checkpoint_records.append({"method": "M2", "condition": "true", "seed": seed, "checkpoint_sha256": checkpoint_sha, "training_result_sha256": result_sha})

        m2_null_dir = args.m2_root / "mismatched" / f"width-{SELECTED_M2_WIDTH}" / f"seed-{seed}-job-{NULL_JOB_ID}-{seed_index + 3}"
        m2_null_checkpoint = m2_null_dir / "best-checkpoint.pt"
        m2_null_result = m2_null_dir / "training-result.json"
        _, checkpoint_sha, result_sha = verify_training_result(
            m2_null_dir,
            m2_null_checkpoint,
            m2_null_result,
            method="M2",
            condition="mismatched",
            seed=seed,
            width=SELECTED_M2_WIDTH,
        )
        if locked_control_checkpoints[("M2", "mismatched", SELECTED_M2_WIDTH, seed)] != checkpoint_sha:
            raise RuntimeError("M2 null checkpoint differs from P2 calibration")
        raw_scores["M2_mismatched_null"][seed_index] = score_m2_null(
            m2_null_checkpoint,
            source,
            target,
            noise,
            width=SELECTED_M2_WIDTH,
            sigma=SELECTED_M2_SIGMA,
            seed=seed,
            stats_sha=stats_sha,
            batch_size=args.m2_batch_size,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        checkpoint_records.append({"method": "M2", "condition": "mismatched", "seed": seed, "checkpoint_sha256": checkpoint_sha, "training_result_sha256": result_sha})

        ae_dir = args.autoencoder_root / f"width-{SELECTED_M2_WIDTH}" / f"seed-{seed}-job-{AUTOENCODER_JOB_ID}-{seed_index}"
        ae_checkpoint = ae_dir / "best-checkpoint.pt"
        ae_result = ae_dir / "training-result.json"
        _, checkpoint_sha, result_sha = verify_training_result(
            ae_dir,
            ae_checkpoint,
            ae_result,
            method="AE",
            condition="plain_autoencoder_control",
            seed=seed,
            width=SELECTED_M2_WIDTH,
        )
        if locked_control_checkpoints[("M2-autoencoder", "plain_autoencoder_control", SELECTED_M2_WIDTH, seed)] != checkpoint_sha:
            raise RuntimeError("M2 autoencoder checkpoint differs from P2 calibration")
        raw_scores["M2_autoencoder_control"][seed_index] = score_autoencoder(
            ae_checkpoint,
            source,
            target,
            width=SELECTED_M2_WIDTH,
            seed=seed,
            stats_sha=stats_sha,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        checkpoint_records.append({"method": "M2-autoencoder", "condition": "plain_autoencoder_control", "seed": seed, "checkpoint_sha256": checkpoint_sha, "training_result_sha256": result_sha})

        for condition, output_name in (("true", "M3_true"), ("shuffled", "M3_shuffled_null")):
            m3_dir, m3_checkpoint, m3_result = training_paths(
                args.m3_root, "m3", condition, None, seed_index
            )
            _, checkpoint_sha, result_sha = verify_training_run(
                m3_dir,
                m3_checkpoint,
                m3_result,
                method="m3",
                condition=condition,
                width=None,
                seed=seed,
            )
            if locked_true_checkpoints[("M3", condition, None, seed)] != checkpoint_sha:
                raise RuntimeError(f"M3 {condition} checkpoint differs from P2 selection")
            raw_scores[output_name][seed_index] = score_m3(
                m3_checkpoint,
                source,
                target,
                expected_condition=condition,
                expected_seed=seed,
            ).reshape(POOL_COUNT, CANDIDATE_COUNT)
            checkpoint_records.append({"method": "M3", "condition": condition, "seed": seed, "checkpoint_sha256": checkpoint_sha, "training_result_sha256": result_sha})

    calibrators = load_calibrators(calibration_h5)
    method_inputs = {
        "M1": (raw_scores["M1_true"], raw_scores["M1_permuted_null"]),
        "M2": (raw_scores["M2_true"], raw_scores["M2_mismatched_null"]),
        "M3": (raw_scores["M3_true"], raw_scores["M3_shuffled_null"]),
    }
    platt_true: dict[str, np.ndarray] = {}
    isotonic_true: dict[str, np.ndarray] = {}
    methods: dict[str, Any] = {}
    for method, (true_raw, null_raw) in method_inputs.items():
        platt_true[method], isotonic_true[method] = calibrate_scores(
            true_raw, calibrators[method]
        )
        methods[method] = {
            "true": calibrated_report(
                labels_by_rule, platt_true[method], isotonic_true[method]
            ),
            "own_null": uncalibrated_report(labels_by_rule, null_raw),
        }

    g0a = robust_knn_isolation(macro_np)
    g0b = robust_knn_isolation(target_np)
    controls = {
        "M2_autoencoder": uncalibrated_report(
            labels_by_rule, raw_scores["M2_autoencoder_control"]
        ),
        "G0a_macro_knn": uncalibrated_report(labels_by_rule, g0a),
        "G0b_subgoal_knn": uncalibrated_report(labels_by_rule, g0b),
    }

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    pool_resamples = rng.integers(
        0, POOL_COUNT, size=(BOOTSTRAP_REPLICATES, POOL_COUNT), dtype=np.uint8
    )
    primary_labels = labels_by_rule["primary"]
    bootstrap_values: dict[str, dict[str, np.ndarray]] = {}
    promotion: dict[str, Any] = {}
    for method in ("M1", "M2", "M3"):
        true_ensemble = platt_true[method].mean(axis=0)
        null_ensemble = method_inputs[method][1].mean(axis=0)
        true_auc = bootstrap_auroc(primary_labels, true_ensemble, pool_resamples)
        null_auc = bootstrap_auroc(primary_labels, null_ensemble, pool_resamples)
        improvement = true_auc - null_auc
        true_point = float(
            methods[method]["true"]["primary"]["primary_platt_ensemble"]["auroc"]
        )
        null_point = float(
            methods[method]["own_null"]["primary"]["ensemble"]["auroc"]
        )
        improvement_interval = interval(improvement)
        passes_absolute = true_point >= 0.70
        passes_null = improvement_interval[0] > 0.0
        promotion[method] = {
            "primary_ensemble_auroc": true_point,
            "own_null_ensemble_auroc": null_point,
            "point_improvement": true_point - null_point,
            "true_auroc_bootstrap_95_percentile_interval": interval(true_auc),
            "own_null_auroc_bootstrap_95_percentile_interval": interval(null_auc),
            "paired_improvement_bootstrap_95_percentile_interval": improvement_interval,
            "passes_auroc_at_least_0_70": passes_absolute,
            "passes_positive_improvement_interval": passes_null,
            "promoted": bool(passes_absolute and passes_null),
        }
        bootstrap_values[method] = {
            "true_auroc": true_auc,
            "null_auroc": null_auc,
            "improvement": improvement,
        }

    ae_ensemble = raw_scores["M2_autoencoder_control"].mean(axis=0)
    ae_auc = bootstrap_auroc(primary_labels, ae_ensemble, pool_resamples)
    m2_ae_difference = bootstrap_values["M2"]["true_auroc"] - ae_auc
    ae_point = float(controls["M2_autoencoder"]["primary"]["ensemble"]["auroc"])
    m2_point = float(promotion["M2"]["primary_ensemble_auroc"])
    m2_beats_ae = m2_point > ae_point
    if promotion["M2"]["promoted"] and m2_beats_ae:
        m2_interpretation = "diffusion-specific interpretation permitted"
    elif promotion["M2"]["promoted"]:
        m2_interpretation = "reconstruction-error signal only"
    else:
        m2_interpretation = "not promoted; no diffusion-specific claim"
    promotion["M2"]["autoencoder_control"] = {
        "ensemble_auroc": ae_point,
        "point_improvement_over_autoencoder": m2_point - ae_point,
        "paired_improvement_bootstrap_95_percentile_interval": interval(
            m2_ae_difference
        ),
        "beats_autoencoder_by_frozen_point_comparison": m2_beats_ae,
        "interpretation": m2_interpretation,
    }

    torch.cuda.synchronize(device)
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = "p3_locked_scorer_audit_and_promotion"
            output.attrs["partition"] = "P3-locked"
            output.attrs["positive_class"] = "budgeted-attainment failure"
            output.attrs["bootstrap_seed"] = BOOTSTRAP_SEED
            output.attrs["bootstrap_replicates"] = BOOTSTRAP_REPLICATES
            output.create_dataset("pool_id", data=pool_id)
            output.create_dataset("training_seed", data=np.asarray(SEEDS, dtype=np.int64))
            output.create_dataset("attainment_rate", data=attainment_rate)
            for name, labels in labels_by_rule.items():
                output.create_dataset(f"labels/{name}", data=labels)
            raw_group = output.require_group("raw_scores")
            for name, scores in raw_scores.items():
                raw_group.create_dataset(name, data=scores, compression="gzip")
            raw_group.create_dataset("G0a_macro_knn", data=g0a)
            raw_group.create_dataset("G0b_subgoal_knn", data=g0b)
            for method in ("M1", "M2", "M3"):
                group = output.require_group(f"probabilities/{method}")
                group.create_dataset("true_platt_seedwise", data=platt_true[method])
                group.create_dataset("true_platt_ensemble", data=platt_true[method].mean(axis=0))
                group.create_dataset("true_isotonic_seedwise", data=isotonic_true[method])
                bootstrap_group = output.require_group(f"bootstrap/{method}")
                for name, values in bootstrap_values[method].items():
                    bootstrap_group.create_dataset(name, data=values)
            output.create_dataset("bootstrap/pool_resample_index", data=pool_resamples)
            output.create_dataset("bootstrap/M2/autoencoder_auroc", data=ae_auc)
            output.create_dataset(
                "bootstrap/M2/improvement_over_autoencoder", data=m2_ae_difference
            )
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_p3_scorer_audit_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": "p3_locked_scorer_audit_and_promotion",
        "partition": "P3-locked",
        "reporting_rule": "one locked confirmation; no setting may be revised from these values",
        "positive_class": "budgeted-attainment failure",
        "coverage": {
            "pools": POOL_COUNT,
            "candidates_per_pool": CANDIDATE_COUNT,
            "candidates": POOL_COUNT * CANDIDATE_COUNT,
            "training_seeds": list(SEEDS),
            "failure_prevalence": {
                name: float(labels.mean()) for name, labels in labels_by_rule.items()
            },
        },
        "selected_configuration": {
            "M1_width": SELECTED_M1_WIDTH,
            "M2_width": SELECTED_M2_WIDTH,
            "M2_sigma": SELECTED_M2_SIGMA,
            "M2_noise_draws": NOISE_DRAWS,
        },
        "ensemble_rule": "apply each seed's P2-frozen calibrator, then arithmetic-mean the three failure probabilities",
        "null_ensemble_rule": "arithmetic mean of the three same-unit raw null scores; no null calibrator is fit or applied",
        "methods": methods,
        "controls_and_geometry": controls,
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "unit": "complete 64-candidate query pool",
            "interval": "2.5th and 97.5th percentiles using NumPy linear quantiles",
            "paired": True,
        },
        "promotion": promotion,
        "promoted_arms": [
            method for method in ("M1", "M2", "M3") if promotion[method]["promoted"]
        ],
        "G0_promotion_status": "diagnostic only; the frozen protocol defines no own null for G0",
        "checkpoints": checkpoint_records,
        "inputs": {
            "p3_labeled_h5_sha256": p3_manifest["output_h5_sha256"],
            "p3_labeled_manifest_sha256": sha256_file(args.p3_labeled_dir / "manifest.json"),
            "p3_candidate_h5_sha256": P3_CANDIDATE_H5_SHA256,
            "p2_true_score_h5_sha256": sha256_file(true_h5),
            "p2_true_score_manifest_sha256": sha256_file(args.p2_true_score_dir / "manifest.json"),
            "p2_calibration_h5_sha256": sha256_file(calibration_h5),
            "p2_calibration_manifest_sha256": sha256_file(args.p2_calibration_dir / "manifest.json"),
            "stats_npz_sha256": stats_sha,
            "noise_npy_sha256": sha256_file(args.noise_npy),
            "noise_manifest_sha256": sha256_file(args.noise_manifest),
        },
        "runtime": {
            "device": str(device),
            "gpu": torch.cuda.get_device_name(device),
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "numpy": np.__version__,
            "h5py": h5py.__version__,
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
