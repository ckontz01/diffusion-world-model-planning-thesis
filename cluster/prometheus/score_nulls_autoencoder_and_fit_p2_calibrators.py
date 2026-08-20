#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from score_and_select_p2_true_scorers import (
    CANDIDATE_COUNT,
    LATENT_DIM,
    MACRO_DIM,
    NOISE_DRAWS,
    POOL_COUNT,
    SEEDS,
    SIGMAS,
    atomic_json,
    binary_metrics,
    sha256_file,
    verify_inventory,
    verify_labeled_input,
)
from train_m1_macro_cycle_head import MacroInverseDynamicsMLP
from train_m2_autoencoder_control import ConditionalTargetAutoencoder
from train_m2_diffusion_head import ConditionalEpsilonMLP


def sha256_array(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    return hashlib.sha256(contiguous.tobytes()).hexdigest()


def verify_scoring_input(
    directory: Path, environment: str
) -> tuple[dict[str, Any], Path]:
    inventory = verify_inventory(directory)
    expected = {"scores.h5", "manifest.json", "provenance.txt"}
    if set(inventory) != expected:
        raise RuntimeError(f"unexpected true-score inventory: {sorted(inventory)}")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    prefix = "tworoom_" if environment == "tworoom" else ""
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification")
        != f"{prefix}p2_true_scorer_raw_score_selection"
        or manifest.get("environment", "pusht") != environment
    ):
        raise RuntimeError("input is not a completed P2 true-scorer selection")
    if manifest["output_h5_sha256"] != inventory["scores.h5"]:
        raise RuntimeError("true-score HDF5 differs from its manifest")
    return manifest, directory / "scores.h5"


def verify_training_result(
    directory: Path,
    checkpoint: Path,
    result_path: Path,
    *,
    method: str,
    condition: str,
    seed: int,
    width: int,
    expected_null_hash_namespace: str | None = None,
) -> tuple[dict[str, Any], str, str]:
    inventory = verify_inventory(directory)
    root = directory.resolve()
    relative_checkpoint = str(checkpoint.resolve().relative_to(root))
    relative_result = str(result_path.resolve().relative_to(root))
    if relative_checkpoint not in inventory or relative_result not in inventory:
        raise RuntimeError(f"checkpoint or result absent from inventory: {directory}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    expected_method = {
        "M1": "M1_single_macro_cycle_consistency",
        "M2": "M2_conditional_epsilon_prediction",
        "AE": "M2_plain_autoencoder_reconstruction_control",
    }[method]
    if result.get("status") != "ok" or result.get("method") != expected_method:
        raise RuntimeError(f"invalid {method} training result: {directory}")
    if result["condition"] != condition or int(result["training_seed"]) != seed:
        raise RuntimeError(f"condition or seed mismatch: {directory}")
    if int(result["model_spec"]["hidden_width"]) != width:
        raise RuntimeError(f"width mismatch: {directory}")
    if expected_null_hash_namespace is not None:
        for key in ("full_train_pair_info", "full_validation_pair_info"):
            if result.get("data", {}).get(key, {}).get(
                "null_hash_namespace"
            ) != expected_null_hash_namespace:
                raise RuntimeError(
                    f"M2 null hash namespace mismatch in {directory}: {key}"
                )
    checkpoint_sha = sha256_file(checkpoint)
    if result["checkpoint_sha256"] != checkpoint_sha:
        raise RuntimeError(f"checkpoint hash differs from result: {directory}")
    return result, checkpoint_sha, sha256_file(result_path)


@torch.inference_mode()
def score_m1_null(
    checkpoint_path: Path,
    source_raw: torch.Tensor,
    target_raw: torch.Tensor,
    macro_raw: torch.Tensor,
    *,
    width: int,
    seed: int,
    stats_sha: str,
) -> np.ndarray:
    payload = torch.load(checkpoint_path, map_location=source_raw.device, weights_only=False)
    if (
        payload["condition"] != "permuted"
        or int(payload["hidden_width"]) != width
        or int(payload["training_seed"]) != seed
        or payload["stats_npz_sha256"] != stats_sha
    ):
        raise RuntimeError(f"unexpected M1 null checkpoint: {checkpoint_path}")
    model = MacroInverseDynamicsMLP(LATENT_DIM, MACRO_DIM, width).to(source_raw.device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    latent_mean = payload["latent_mean"].to(source_raw.device)
    latent_std = payload["latent_std"].to(source_raw.device)
    macro_mean = payload["macro_mean"].to(source_raw.device)
    macro_std = payload["macro_std"].to(source_raw.device)
    prediction = model(
        (source_raw - latent_mean) / latent_std,
        (target_raw - latent_mean) / latent_std,
    )
    raw_prediction = prediction * macro_std + macro_mean
    return (
        (macro_raw - raw_prediction)
        .square()
        .sum(dim=-1)
        .detach()
        .cpu()
        .numpy()
        .astype(np.float32)
    )


@torch.inference_mode()
def score_m2_null(
    checkpoint_path: Path,
    source_raw: torch.Tensor,
    target_raw: torch.Tensor,
    noise: torch.Tensor,
    *,
    width: int,
    sigma: float,
    seed: int,
    stats_sha: str,
    batch_size: int,
) -> np.ndarray:
    payload = torch.load(checkpoint_path, map_location=source_raw.device, weights_only=False)
    if (
        payload["condition"] != "mismatched"
        or int(payload["hidden_width"]) != width
        or int(payload["training_seed"]) != seed
        or payload["stats_npz_sha256"] != stats_sha
        or tuple(float(value) for value in payload["sigma_grid"]) != SIGMAS
    ):
        raise RuntimeError(f"unexpected M2 null checkpoint: {checkpoint_path}")
    model = ConditionalEpsilonMLP(LATENT_DIM, width).to(source_raw.device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    mean = payload["latent_mean"].to(source_raw.device)
    std = payload["latent_std"].to(source_raw.device)
    source = (source_raw - mean) / std
    target = (target_raw - mean) / std
    count = len(source)
    source_expanded = source[:, None, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(
        -1, LATENT_DIM
    )
    target_expanded = target[:, None, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(
        -1, LATENT_DIM
    )
    epsilon = noise[None, :, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(
        -1, LATENT_DIM
    )
    sigma_tensor = torch.full(
        (count * NOISE_DRAWS,), sigma, device=source.device, dtype=source.dtype
    )
    squared_l2 = torch.empty(count * NOISE_DRAWS, device=source.device)
    for start in range(0, len(squared_l2), batch_size):
        stop = min(start + batch_size, len(squared_l2))
        prediction = model(
            target_expanded[start:stop] + sigma_tensor[start:stop, None] * epsilon[start:stop],
            sigma_tensor[start:stop],
            source_expanded[start:stop],
        )
        squared_l2[start:stop] = (epsilon[start:stop] - prediction).square().sum(dim=-1)
    return (
        squared_l2.reshape(count, NOISE_DRAWS)
        .mean(dim=1)
        .detach()
        .cpu()
        .numpy()
        .astype(np.float32)
    )


@torch.inference_mode()
def score_autoencoder(
    checkpoint_path: Path,
    source_raw: torch.Tensor,
    target_raw: torch.Tensor,
    *,
    width: int,
    seed: int,
    stats_sha: str,
) -> np.ndarray:
    payload = torch.load(checkpoint_path, map_location=source_raw.device, weights_only=False)
    if (
        payload["condition"] != "plain_autoencoder_control"
        or int(payload["hidden_width"]) != width
        or int(payload["training_seed"]) != seed
        or payload["stats_npz_sha256"] != stats_sha
        or int(payload["bottleneck_dim"]) != 64
    ):
        raise RuntimeError(f"unexpected autoencoder checkpoint: {checkpoint_path}")
    model = ConditionalTargetAutoencoder(LATENT_DIM, width).to(source_raw.device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    mean = payload["latent_mean"].to(source_raw.device)
    std = payload["latent_std"].to(source_raw.device)
    source = (source_raw - mean) / std
    target = (target_raw - mean) / std
    prediction = model(source, target)
    return (
        (target - prediction)
        .square()
        .sum(dim=-1)
        .detach()
        .cpu()
        .numpy()
        .astype(np.float32)
    )


def sigmoid(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float64)
    output = np.empty_like(value)
    nonnegative = value >= 0
    output[nonnegative] = 1.0 / (1.0 + np.exp(-value[nonnegative]))
    exponential = np.exp(value[~nonnegative])
    output[~nonnegative] = exponential / (1.0 + exponential)
    return output


def fit_monotone_platt(
    scores: np.ndarray,
    labels: np.ndarray,
    *,
    l2: float = 1.0e-6,
    max_iterations: int = 100,
) -> tuple[dict[str, Any], np.ndarray]:
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    labels = np.asarray(labels, dtype=np.float64).reshape(-1)
    mean = float(scores.mean())
    std = float(scores.std(ddof=0))
    if not math.isfinite(std) or std <= 0.0:
        raise RuntimeError("cannot calibrate a constant raw score")
    x = (scores - mean) / std
    prevalence = float(labels.mean())
    if not 0.0 < prevalence < 1.0:
        raise RuntimeError("Platt fitting requires both classes")
    slope = 1.0
    intercept = math.log(prevalence / (1.0 - prevalence))

    def objective(candidate_slope: float, candidate_intercept: float) -> float:
        logits = candidate_slope * x + candidate_intercept
        return float(
            np.mean(np.logaddexp(0.0, logits) - labels * logits)
            + 0.5 * l2 * candidate_slope**2
        )

    converged = False
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        iterations = iteration
        logits = slope * x + intercept
        probability = sigmoid(logits)
        residual = probability - labels
        weight = probability * (1.0 - probability)
        gradient = np.asarray(
            [np.mean(residual * x) + l2 * slope, np.mean(residual)],
            dtype=np.float64,
        )
        hessian = np.asarray(
            [
                [np.mean(weight * x * x) + l2, np.mean(weight * x)],
                [np.mean(weight * x), np.mean(weight)],
            ],
            dtype=np.float64,
        )
        projected_gradient = np.asarray(
            [min(float(gradient[0]), 0.0) if slope == 0.0 else gradient[0], gradient[1]]
        )
        if float(np.max(np.abs(projected_gradient))) < 1.0e-10:
            converged = True
            break
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        current_objective = objective(slope, intercept)
        accepted = False
        factor = 1.0
        for _ in range(60):
            candidate_slope = max(0.0, float(slope - factor * step[0]))
            candidate_intercept = float(intercept - factor * step[1])
            if objective(candidate_slope, candidate_intercept) <= current_objective:
                slope = candidate_slope
                intercept = candidate_intercept
                accepted = True
                break
            factor *= 0.5
        if not accepted:
            break
    probabilities = sigmoid(slope * x + intercept)
    raw_slope = slope / std
    raw_intercept = intercept - slope * mean / std
    record = {
        "score_mean": mean,
        "score_population_std": std,
        "standardized_slope": float(slope),
        "standardized_intercept": float(intercept),
        "raw_score_slope": float(raw_slope),
        "raw_score_intercept": float(raw_intercept),
        "l2": l2,
        "iterations": iterations,
        "converged": converged,
        "constraint": "slope >= 0",
        "objective": objective(slope, intercept),
    }
    return record, probabilities


def fit_isotonic(
    scores: np.ndarray, labels: np.ndarray
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    labels = np.asarray(labels, dtype=np.float64).reshape(-1)
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    sorted_labels = labels[order]
    unique_scores, start_indices, counts = np.unique(
        sorted_scores, return_index=True, return_counts=True
    )
    sums = np.add.reduceat(sorted_labels, start_indices)
    blocks: list[list[float]] = []
    for value, count, total in zip(unique_scores, counts, sums, strict=True):
        blocks.append([float(value), float(value), float(count), float(total / count)])
        while len(blocks) >= 2 and blocks[-2][3] > blocks[-1][3]:
            right = blocks.pop()
            left = blocks.pop()
            weight = left[2] + right[2]
            probability = (left[2] * left[3] + right[2] * right[3]) / weight
            blocks.append([left[0], right[1], weight, probability])
    lower = np.asarray([block[0] for block in blocks], dtype=np.float64)
    upper = np.asarray([block[1] for block in blocks], dtype=np.float64)
    weight = np.asarray([block[2] for block in blocks], dtype=np.float64)
    probability = np.asarray([block[3] for block in blocks], dtype=np.float64)
    indices = np.searchsorted(upper, scores, side="left")
    indices = np.clip(indices, 0, len(probability) - 1)
    predictions = probability[indices]
    return {
        "lower_score": lower,
        "upper_score": upper,
        "weight": weight,
        "failure_probability": probability,
    }, predictions


def calibration_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=np.float64).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    if labels.shape != probabilities.shape or not np.isfinite(probabilities).all():
        raise RuntimeError("invalid calibration metric arrays")
    probabilities = np.clip(probabilities, 0.0, 1.0)
    bin_index = np.minimum((probabilities * 10.0).astype(np.int64), 9)
    ece = 0.0
    bins: list[dict[str, Any]] = []
    for index in range(10):
        mask = bin_index == index
        count = int(mask.sum())
        if count:
            confidence = float(probabilities[mask].mean())
            observed = float(labels[mask].mean())
            ece += count / len(labels) * abs(confidence - observed)
        else:
            confidence = None
            observed = None
        bins.append(
            {
                "index": index,
                "lower_inclusive": index / 10.0,
                "upper_exclusive_except_last": (index + 1) / 10.0,
                "count": count,
                "mean_probability": confidence,
                "observed_failure_rate": observed,
            }
        )
    return {
        "brier_score": float(np.mean((probabilities - labels) ** 2)),
        "ece_10_equal_width": float(ece),
        "bins": bins,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labeled-dir", type=Path, required=True)
    parser.add_argument("--true-score-dir", type=Path, required=True)
    parser.add_argument("--m1-root", type=Path, required=True)
    parser.add_argument("--m2-root", type=Path, required=True)
    parser.add_argument("--autoencoder-root", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--null-job-id", type=int, required=True)
    parser.add_argument("--autoencoder-job-id", type=int, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--m2-batch-size", type=int, default=2048)
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite P2 null/control/calibration output")
    if args.device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("P2 null/control scoring requires CUDA")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda")
    started = time.time()

    environment = args.environment
    prefix = "tworoom_" if environment == "tworoom" else ""
    true_classification = f"{prefix}p2_true_scorer_raw_score_selection"
    output_classification = f"{prefix}p2_null_control_scores_and_calibrators"
    labeled_manifest, labeled_h5 = verify_labeled_input(args.labeled_dir, environment)
    true_manifest, true_h5 = verify_scoring_input(args.true_score_dir, environment)
    if true_manifest["inputs"]["labeled_h5_sha256"] != labeled_manifest[
        "output_h5_sha256"
    ]:
        raise RuntimeError("true scores and labels use different P2 candidates")
    stats_sha = labeled_manifest["inputs"]["stats_npz_sha256"]
    selected_m1_width = int(true_manifest["M1"]["selected_width"])
    selected_m2_width = int(true_manifest["M2"]["selected_width"])
    selected_m2_sigma = float(true_manifest["M2"]["selected_sigma"])

    with h5py.File(labeled_h5, "r") as labeled:
        source_np = np.asarray(labeled["source_latent"][:], dtype=np.float32)
        target_np = np.asarray(labeled["selected_subgoal"][:], dtype=np.float32)
        macro_np = np.asarray(labeled["selected_first_macro"][:], dtype=np.float32)
        failure_label = ~np.asarray(
            labeled["primary_label_at_least_3_of_5"][:], dtype=np.bool_
        )
    source_flat_np = np.broadcast_to(
        source_np[:, None, :], target_np.shape
    ).reshape(-1, LATENT_DIM).copy()
    target_flat_np = target_np.reshape(-1, LATENT_DIM)
    macro_flat_np = macro_np.reshape(-1, MACRO_DIM)
    labels_flat = failure_label.reshape(-1)
    source = torch.from_numpy(source_flat_np).to(device)
    target = torch.from_numpy(target_flat_np).to(device)
    macro = torch.from_numpy(macro_flat_np).to(device)

    with h5py.File(true_h5, "r") as true_scores_h5:
        if (
            true_scores_h5.attrs["classification"] != true_classification
            or true_scores_h5.attrs.get("environment", "pusht") != environment
        ):
            raise RuntimeError("true-score HDF5 classification mismatch")
        if not np.array_equal(true_scores_h5["failure_label"][:], failure_label):
            raise RuntimeError("true-score labels changed")
        m1_widths = np.asarray(true_scores_h5["m1_width"][:], dtype=np.int64)
        m2_widths = np.asarray(true_scores_h5["m2_width"][:], dtype=np.int64)
        sigma_grid = np.asarray(true_scores_h5["m2_sigma"][:], dtype=np.float64)
        m1_index = int(np.flatnonzero(m1_widths == selected_m1_width)[0])
        m2_index = int(np.flatnonzero(m2_widths == selected_m2_width)[0])
        sigma_index = int(np.flatnonzero(sigma_grid == selected_m2_sigma)[0])
        m1_true = np.asarray(
            true_scores_h5["m1_raw_score"][m1_index], dtype=np.float32
        )
        m2_true = np.asarray(
            true_scores_h5["m2_raw_score"][m2_index, :, sigma_index],
            dtype=np.float32,
        )
        m3_true = np.asarray(true_scores_h5["m3_raw_score"][0], dtype=np.float32)
        m3_null = np.asarray(true_scores_h5["m3_raw_score"][1], dtype=np.float32)

    noise_manifest = json.loads(args.noise_manifest.read_text(encoding="utf-8"))
    if sha256_file(args.noise_npy) != noise_manifest["output_npy_sha256"]:
        raise RuntimeError("frozen M2 noise bank differs from its manifest")
    noise_np = np.load(args.noise_npy, allow_pickle=False)
    if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
        raise RuntimeError("unexpected M2 noise bank")
    noise = torch.from_numpy(noise_np).to(device)

    m1_null = np.empty_like(m1_true)
    m2_null = np.empty_like(m2_true)
    autoencoder = np.empty_like(m2_true)
    checkpoint_records: list[dict[str, Any]] = []
    autoencoder_capacity: list[dict[str, Any]] = []
    for seed_index, seed in enumerate(SEEDS):
        m1_task = seed_index
        m1_dir = args.m1_root / (
            f"permuted-width{selected_m1_width}-seed{seed}-job-{args.null_job_id}_{m1_task}"
        )
        m1_checkpoint = m1_dir / "run/best-checkpoint.pt"
        m1_result_path = m1_dir / "run/training-result.json"
        _, checkpoint_sha, result_sha = verify_training_result(
            m1_dir,
            m1_checkpoint,
            m1_result_path,
            method="M1",
            condition="permuted",
            seed=seed,
            width=selected_m1_width,
        )
        m1_null[seed_index] = score_m1_null(
            m1_checkpoint,
            source,
            target,
            macro,
            width=selected_m1_width,
            seed=seed,
            stats_sha=stats_sha,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        checkpoint_records.append(
            {
                "method": "M1",
                "condition": "permuted",
                "seed": seed,
                "width": selected_m1_width,
                "checkpoint_sha256": checkpoint_sha,
                "training_result_sha256": result_sha,
            }
        )

        m2_task = seed_index + 3
        m2_dir = (
            args.m2_root
            / "mismatched"
            / f"width-{selected_m2_width}"
            / f"seed-{seed}-job-{args.null_job_id}-{m2_task}"
        )
        m2_checkpoint = m2_dir / "best-checkpoint.pt"
        m2_result_path = m2_dir / "training-result.json"
        _, checkpoint_sha, result_sha = verify_training_result(
            m2_dir,
            m2_checkpoint,
            m2_result_path,
            method="M2",
            condition="mismatched",
            seed=seed,
            width=selected_m2_width,
            expected_null_hash_namespace=(
                "tworoom" if environment == "tworoom" else None
            ),
        )
        m2_null[seed_index] = score_m2_null(
            m2_checkpoint,
            source,
            target,
            noise,
            width=selected_m2_width,
            sigma=selected_m2_sigma,
            seed=seed,
            stats_sha=stats_sha,
            batch_size=args.m2_batch_size,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        checkpoint_records.append(
            {
                "method": "M2",
                "condition": "mismatched",
                "seed": seed,
                "width": selected_m2_width,
                "sigma": selected_m2_sigma,
                "checkpoint_sha256": checkpoint_sha,
                "training_result_sha256": result_sha,
            }
        )

        ae_dir = (
            args.autoencoder_root
            / f"width-{selected_m2_width}"
            / f"seed-{seed}-job-{args.autoencoder_job_id}-{seed_index}"
        )
        ae_checkpoint = ae_dir / "best-checkpoint.pt"
        ae_result_path = ae_dir / "training-result.json"
        ae_result, checkpoint_sha, result_sha = verify_training_result(
            ae_dir,
            ae_checkpoint,
            ae_result_path,
            method="AE",
            condition="plain_autoencoder_control",
            seed=seed,
            width=selected_m2_width,
        )
        autoencoder[seed_index] = score_autoencoder(
            ae_checkpoint,
            source,
            target,
            width=selected_m2_width,
            seed=seed,
            stats_sha=stats_sha,
        ).reshape(POOL_COUNT, CANDIDATE_COUNT)
        autoencoder_capacity.append(
            {
                "seed": seed,
                "parameter_count": ae_result["model_spec"]["parameter_count"],
                "matched_m2_parameter_count": ae_result["model_spec"][
                    "matched_m2_parameter_count"
                ],
                "parameter_count_ratio_to_m2": ae_result["model_spec"][
                    "parameter_count_ratio_to_m2"
                ],
            }
        )
        checkpoint_records.append(
            {
                "method": "M2-autoencoder",
                "condition": "plain_autoencoder_control",
                "seed": seed,
                "width": selected_m2_width,
                "checkpoint_sha256": checkpoint_sha,
                "training_result_sha256": result_sha,
            }
        )

    raw_score_sets = {
        "M1_true": m1_true,
        "M1_permuted_null": m1_null,
        "M2_true": m2_true,
        "M2_mismatched_null": m2_null,
        "M2_autoencoder_control": autoencoder,
        "M3_true": m3_true,
        "M3_shuffled_null": m3_null,
    }
    raw_metrics: dict[str, Any] = {}
    for name, scores in raw_score_sets.items():
        seed_records = [
            {"seed": seed, **binary_metrics(labels_flat, scores[index].reshape(-1))}
            for index, seed in enumerate(SEEDS)
        ]
        raw_metrics[name] = {
            "mean_seed_auroc": float(np.mean([record["auroc"] for record in seed_records])),
            "mean_seed_average_precision": float(
                np.mean([record["average_precision"] for record in seed_records])
            ),
            "seeds": seed_records,
        }

    true_methods = {"M1": m1_true, "M2": m2_true, "M3": m3_true}
    platt_probability = np.empty(
        (len(true_methods), len(SEEDS), POOL_COUNT, CANDIDATE_COUNT), dtype=np.float64
    )
    isotonic_probability = np.empty_like(platt_probability)
    calibration_records: dict[str, Any] = {}
    isotonic_models: dict[tuple[str, int], dict[str, np.ndarray]] = {}
    for method_index, (method, scores) in enumerate(true_methods.items()):
        seed_records = []
        for seed_index, seed in enumerate(SEEDS):
            platt_record, platt_flat = fit_monotone_platt(
                scores[seed_index].reshape(-1), labels_flat
            )
            isotonic_record, isotonic_flat = fit_isotonic(
                scores[seed_index].reshape(-1), labels_flat
            )
            platt_probability[method_index, seed_index] = platt_flat.reshape(
                POOL_COUNT, CANDIDATE_COUNT
            )
            isotonic_probability[method_index, seed_index] = isotonic_flat.reshape(
                POOL_COUNT, CANDIDATE_COUNT
            )
            isotonic_models[(method, seed_index)] = isotonic_record
            seed_records.append(
                {
                    "seed": seed,
                    "platt": platt_record,
                    "platt_development_metrics": calibration_metrics(labels_flat, platt_flat),
                    "isotonic": {
                        "block_count": int(len(isotonic_record["failure_probability"])),
                        "lower_score_sha256": sha256_array(isotonic_record["lower_score"]),
                        "upper_score_sha256": sha256_array(isotonic_record["upper_score"]),
                        "weight_sha256": sha256_array(isotonic_record["weight"]),
                        "failure_probability_sha256": sha256_array(
                            isotonic_record["failure_probability"]
                        ),
                    },
                    "isotonic_development_metrics": calibration_metrics(
                        labels_flat, isotonic_flat
                    ),
                }
            )
        platt_ensemble = platt_probability[method_index].mean(axis=0)
        isotonic_ensemble = isotonic_probability[method_index].mean(axis=0)
        calibration_records[method] = {
            "seeds": seed_records,
            "primary_platt_ensemble_development_metrics": calibration_metrics(
                labels_flat, platt_ensemble.reshape(-1)
            ),
            "sensitivity_isotonic_ensemble_development_metrics": calibration_metrics(
                labels_flat, isotonic_ensemble.reshape(-1)
            ),
        }

    torch.cuda.synchronize(device)
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = output_classification
            output.attrs["environment"] = environment
            output.attrs["partition"] = "P2-development-only"
            output.attrs["positive_class"] = "budgeted-attainment failure"
            output.attrs["selected_m1_width"] = selected_m1_width
            output.attrs["selected_m2_width"] = selected_m2_width
            output.attrs["selected_m2_sigma"] = selected_m2_sigma
            output.create_dataset("failure_label", data=failure_label)
            output.create_dataset("training_seed", data=np.asarray(SEEDS, dtype=np.int64))
            raw_group = output.require_group("raw_scores")
            for name, scores in raw_score_sets.items():
                raw_group.create_dataset(name, data=scores)
            output.create_dataset("platt_failure_probability", data=platt_probability)
            output.create_dataset("isotonic_failure_probability", data=isotonic_probability)
            output.create_dataset(
                "platt_ensemble_failure_probability", data=platt_probability.mean(axis=1)
            )
            output.create_dataset(
                "isotonic_ensemble_failure_probability",
                data=isotonic_probability.mean(axis=1),
            )
            for method_index, method in enumerate(true_methods):
                method_group = output.require_group(f"calibrators/{method}")
                method_group.attrs["method_index"] = method_index
                for seed_index, seed in enumerate(SEEDS):
                    seed_group = method_group.require_group(f"seed-{seed}")
                    platt = calibration_records[method]["seeds"][seed_index]["platt"]
                    for key, value in platt.items():
                        if isinstance(value, (int, float, bool)):
                            seed_group.attrs[f"platt_{key}"] = value
                    isotonic_group = seed_group.require_group("isotonic")
                    for key, value in isotonic_models[(method, seed_index)].items():
                        isotonic_group.create_dataset(key, data=value)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_p2_calibration_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": output_classification,
        "environment": environment,
        "partition": "P2-development-only",
        "reporting_rule": "P2 values select/fix settings and are not final thesis results",
        "positive_class": "budgeted-attainment failure",
        "selected_configuration": {
            "M1_width": selected_m1_width,
            "M2_width": selected_m2_width,
            "M2_sigma": selected_m2_sigma,
        },
        "raw_metrics": raw_metrics,
        "autoencoder_capacity": autoencoder_capacity,
        "calibration": {
            "primary": "per-seed nondecreasing Platt scaling; arithmetic mean of three probabilities",
            "sensitivity": "per-seed nondecreasing PAVA isotonic; arithmetic mean of three probabilities",
            "platt_l2": 1.0e-6,
            "ece": "10 equal-width probability bins",
            "methods": calibration_records,
        },
        "checkpoints": checkpoint_records,
        "inputs": {
            "null_training_job_id": args.null_job_id,
            "autoencoder_training_job_id": args.autoencoder_job_id,
            "labeled_h5_sha256": labeled_manifest["output_h5_sha256"],
            "labeled_manifest_sha256": sha256_file(args.labeled_dir / "manifest.json"),
            "true_score_h5_sha256": true_manifest["output_h5_sha256"],
            "true_score_manifest_sha256": sha256_file(
                args.true_score_dir / "manifest.json"
            ),
            "stats_npz_sha256": stats_sha,
            "noise_npy_sha256": noise_manifest["output_npy_sha256"],
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
