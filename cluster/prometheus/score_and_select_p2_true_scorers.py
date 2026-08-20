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

from train_m1_macro_cycle_head import MacroInverseDynamicsMLP
from train_m2_diffusion_head import ConditionalEpsilonMLP
from train_m3_temporal_head import TemporalPairHead


SEEDS = (20260728, 20260729, 20260730)
M1_WIDTHS = (256, 512)
M2_WIDTHS = (512, 1024)
SIGMAS = (0.1, 0.25, 0.5, 0.75, 1.0)
POOL_COUNT = 12
CANDIDATE_COUNT = 64
LATENT_DIM = 192
MACRO_DIM = 32
NOISE_DRAWS = 8
TRAINING_JOBS = {
    "pusht": {"m1": 294616, "m2": 294599, "m3": 294595},
    "tworoom": {"m1": 295653, "m2": 295652, "m3": 295644},
}


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def verify_inventory(directory: Path) -> dict[str, str]:
    inventory = directory / "checksums.sha256"
    if not inventory.is_file():
        raise RuntimeError(f"missing checksum inventory: {directory}")
    root = directory.resolve()
    found: dict[str, str] = {}
    for raw in inventory.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, raw_path = raw.split(maxsplit=1)
        path = Path(raw_path.lstrip("* "))
        if not path.is_absolute():
            path = directory / path
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise RuntimeError(f"checksum path escapes training directory: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid training file: {path}")
        found[str(resolved.relative_to(root))] = digest
    if not found:
        raise RuntimeError(f"empty checksum inventory: {directory}")
    return found


def verify_labeled_input(
    directory: Path, environment: str
) -> tuple[dict[str, Any], Path]:
    inventory = verify_inventory(directory)
    expected = {"labeled-candidates.h5", "manifest.json", "provenance.txt"}
    if set(inventory) != expected:
        raise RuntimeError(f"unexpected labeled-input inventory: {sorted(inventory)}")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prefix = "tworoom_" if environment == "tworoom" else ""
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification")
        != f"{prefix}p2_stratum3_labeled_candidate_audit"
        or manifest.get("environment", "pusht") != environment
    ):
        raise RuntimeError("input is not the completed P2 labeled stratum-3 audit")
    h5_path = directory / "labeled-candidates.h5"
    if manifest["output_h5_sha256"] != inventory["labeled-candidates.h5"]:
        raise RuntimeError("labeled HDF5 hash differs from its manifest")
    return manifest, h5_path


def binary_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, float | int]:
    labels = np.asarray(labels, dtype=np.bool_).reshape(-1)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    if labels.shape != scores.shape or not np.isfinite(scores).all():
        raise RuntimeError("invalid inputs to binary score metrics")
    positives = int(labels.sum())
    negatives = int(len(labels) - positives)
    if positives == 0 or negatives == 0:
        raise RuntimeError("AUROC requires both failure and attainment examples")

    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        ranks[order[start:end]] = 0.5 * ((start + 1) + end)
        start = end
    auroc = (
        float(ranks[labels].sum()) - positives * (positives + 1) / 2.0
    ) / (positives * negatives)

    descending = np.argsort(-scores, kind="mergesort")
    sorted_desc = scores[descending]
    sorted_labels = labels[descending].astype(np.int64)
    cumulative_true = np.cumsum(sorted_labels)
    cumulative_false = np.cumsum(1 - sorted_labels)
    endpoints = np.flatnonzero(
        np.r_[sorted_desc[1:] != sorted_desc[:-1], True]
    )
    recall = cumulative_true[endpoints] / positives
    precision = cumulative_true[endpoints] / (
        cumulative_true[endpoints] + cumulative_false[endpoints]
    )
    previous_recall = np.r_[0.0, recall[:-1]]
    average_precision = float(np.sum((recall - previous_recall) * precision))
    return {
        "candidate_count": int(len(labels)),
        "failure_count": positives,
        "attainment_count": negatives,
        "failure_prevalence": positives / len(labels),
        "auroc": float(auroc),
        "average_precision": average_precision,
        "average_precision_minus_prevalence": average_precision - positives / len(labels),
    }


def robust_knn_isolation(values: np.ndarray, k: int = 3) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 3 or values.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("invalid candidate-pool geometry")
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
        nearest = np.partition(distance, kth=k - 1, axis=1)[:, :k]
        output[pool] = nearest.mean(axis=1)
    if not np.isfinite(output).all():
        raise RuntimeError("non-finite G0 isolation score")
    return output.astype(np.float32)


def training_paths(
    root: Path,
    method: str,
    condition: str,
    width: int | None,
    seed_index: int,
    environment: str,
) -> tuple[Path, Path, Path]:
    seed = SEEDS[seed_index]
    jobs = TRAINING_JOBS[environment]
    if method == "m1":
        assert width is not None and condition == "true"
        task = seed_index if width == 256 else seed_index + 3
        directory = root / f"true-width{width}-seed{seed}-job-{jobs['m1']}_{task}"
        return directory, directory / "run/best-checkpoint.pt", directory / "run/training-result.json"
    if method == "m2":
        assert width is not None and condition == "true"
        task = seed_index if width == 512 else seed_index + 3
        directory = root / "true" / f"width-{width}" / f"seed-{seed}-job-{jobs['m2']}-{task}"
        return directory, directory / "best-checkpoint.pt", directory / "training-result.json"
    if method == "m3":
        assert width is None and condition in {"true", "shuffled"}
        task = seed_index if condition == "true" else seed_index + 3
        directory = root / condition / f"seed-{seed}-job-{jobs['m3']}-{task}"
        return directory, directory / "best-checkpoint.pt", directory / "training-result.json"
    raise AssertionError(method)


def verify_training_run(
    directory: Path,
    checkpoint_path: Path,
    result_path: Path,
    *,
    method: str,
    condition: str,
    width: int | None,
    seed: int,
) -> tuple[dict[str, Any], str, str]:
    inventory = verify_inventory(directory)
    relative_checkpoint = str(checkpoint_path.resolve().relative_to(directory.resolve()))
    relative_result = str(result_path.resolve().relative_to(directory.resolve()))
    if relative_checkpoint not in inventory or relative_result not in inventory:
        raise RuntimeError(f"checkpoint or result absent from inventory: {directory}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    expected_method = {
        "m1": "M1_single_macro_cycle_consistency",
        "m2": "M2_conditional_epsilon_prediction",
        "m3": "M3_temporal_reachability_head",
    }[method]
    if result.get("status") != "ok" or result.get("method") != expected_method:
        raise RuntimeError(f"invalid {method.upper()} training result: {directory}")
    if result["condition"] != condition or int(result["training_seed"]) != seed:
        raise RuntimeError(f"condition or seed mismatch: {directory}")
    if width is not None and int(result["model_spec"]["hidden_width"]) != width:
        raise RuntimeError(f"hidden-width mismatch: {directory}")
    checkpoint_sha = sha256_file(checkpoint_path)
    if result["checkpoint_sha256"] != checkpoint_sha:
        raise RuntimeError(f"checkpoint hash differs from result: {directory}")
    return result, checkpoint_sha, sha256_file(result_path)


@torch.inference_mode()
def score_m1(
    checkpoint_path: Path,
    source_raw: torch.Tensor,
    target_raw: torch.Tensor,
    macro_raw: torch.Tensor,
    *,
    expected_width: int,
    expected_seed: int,
    expected_stats_sha: str,
) -> np.ndarray:
    payload = torch.load(checkpoint_path, map_location=source_raw.device, weights_only=False)
    if (
        payload["condition"] != "true"
        or int(payload["hidden_width"]) != expected_width
        or int(payload["training_seed"]) != expected_seed
        or payload["stats_npz_sha256"] != expected_stats_sha
    ):
        raise RuntimeError(f"unexpected M1 checkpoint payload: {checkpoint_path}")
    model = MacroInverseDynamicsMLP(LATENT_DIM, MACRO_DIM, expected_width).to(source_raw.device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    mean = payload["latent_mean"].to(source_raw.device)
    std = payload["latent_std"].to(source_raw.device)
    macro_mean = payload["macro_mean"].to(source_raw.device)
    macro_std = payload["macro_std"].to(source_raw.device)
    prediction_standardized = model(
        (source_raw - mean) / std, (target_raw - mean) / std
    )
    prediction_raw = prediction_standardized * macro_std + macro_mean
    score = (macro_raw - prediction_raw).square().sum(dim=-1)
    return score.detach().cpu().numpy().astype(np.float32)


@torch.inference_mode()
def score_m2(
    checkpoint_path: Path,
    source_raw: torch.Tensor,
    target_raw: torch.Tensor,
    noise: torch.Tensor,
    sigma: float,
    *,
    expected_width: int,
    expected_seed: int,
    expected_stats_sha: str,
    batch_size: int,
) -> np.ndarray:
    payload = torch.load(checkpoint_path, map_location=source_raw.device, weights_only=False)
    if (
        payload["condition"] != "true"
        or int(payload["hidden_width"]) != expected_width
        or int(payload["training_seed"]) != expected_seed
        or payload["stats_npz_sha256"] != expected_stats_sha
        or tuple(float(value) for value in payload["sigma_grid"]) != SIGMAS
    ):
        raise RuntimeError(f"unexpected M2 checkpoint payload: {checkpoint_path}")
    model = ConditionalEpsilonMLP(LATENT_DIM, expected_width).to(source_raw.device)
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
        (count * NOISE_DRAWS,), float(sigma), device=source.device, dtype=source.dtype
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
    score = squared_l2.reshape(count, NOISE_DRAWS).mean(dim=1)
    return score.detach().cpu().numpy().astype(np.float32)


@torch.inference_mode()
def score_m3(
    checkpoint_path: Path,
    source_raw: torch.Tensor,
    target_raw: torch.Tensor,
    *,
    expected_condition: str,
    expected_seed: int,
) -> np.ndarray:
    payload = torch.load(checkpoint_path, map_location=source_raw.device, weights_only=False)
    if (
        payload["condition"] != expected_condition
        or int(payload["training_seed"]) != expected_seed
        or float(payload["target_scale"]) != 40.0
    ):
        raise RuntimeError(f"unexpected M3 checkpoint payload: {checkpoint_path}")
    model = TemporalPairHead(LATENT_DIM).to(source_raw.device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return (
        (model(source_raw, target_raw) * 40.0)
        .detach()
        .cpu()
        .numpy()
        .astype(np.float32)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labeled-dir", type=Path, required=True)
    parser.add_argument("--m1-root", type=Path, required=True)
    parser.add_argument("--m2-root", type=Path, required=True)
    parser.add_argument("--m3-root", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--m2-batch-size", type=int, default=2048)
    parser.add_argument("--environment", choices=("pusht", "tworoom"), default="pusht")
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite P2 true-scorer selection output")
    if args.device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("P2 scorer selection requires CUDA")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda")
    started = time.time()

    environment = args.environment
    prefix = "tworoom_" if environment == "tworoom" else ""
    output_classification = f"{prefix}p2_true_scorer_raw_score_selection"
    labeled_classification = f"{prefix}p2_stratum3_labeled_candidate_audit"
    labeled_manifest, labeled_h5 = verify_labeled_input(args.labeled_dir, environment)
    expected_stats_sha = labeled_manifest["inputs"]["stats_npz_sha256"]
    with h5py.File(labeled_h5, "r") as labeled:
        if (
            labeled.attrs["classification"] != labeled_classification
            or labeled.attrs.get("environment", "pusht") != environment
        ):
            raise RuntimeError("labeled-candidate HDF5 classification mismatch")
        pool_id = np.asarray(labeled["pool_id"][:], dtype=np.int64)
        source_np = np.asarray(labeled["source_latent"][:], dtype=np.float32)
        target_np = np.asarray(labeled["selected_subgoal"][:], dtype=np.float32)
        macro_np = np.asarray(labeled["selected_first_macro"][:], dtype=np.float32)
        attainment_label = np.asarray(
            labeled["primary_label_at_least_3_of_5"][:], dtype=np.bool_
        )
        attainment_rate = np.asarray(labeled["attainment_rate"][:], dtype=np.float32)
    if not np.array_equal(pool_id, np.arange(POOL_COUNT)):
        raise RuntimeError("labeled candidate pools are incomplete")
    if source_np.shape != (POOL_COUNT, LATENT_DIM):
        raise RuntimeError("unexpected labeled source shape")
    if target_np.shape != (POOL_COUNT, CANDIDATE_COUNT, LATENT_DIM):
        raise RuntimeError("unexpected labeled target shape")
    if macro_np.shape != (POOL_COUNT, CANDIDATE_COUNT, MACRO_DIM):
        raise RuntimeError("unexpected labeled macro shape")
    failure_label = ~attainment_label
    if failure_label.all() or not failure_label.any():
        raise RuntimeError("P2 stratum 3 has only one label class")

    source_flat_np = np.broadcast_to(
        source_np[:, None, :], target_np.shape
    ).reshape(-1, LATENT_DIM).copy()
    target_flat_np = target_np.reshape(-1, LATENT_DIM)
    macro_flat_np = macro_np.reshape(-1, MACRO_DIM)
    failure_flat = failure_label.reshape(-1)
    source = torch.from_numpy(source_flat_np).to(device)
    target = torch.from_numpy(target_flat_np).to(device)
    macro = torch.from_numpy(macro_flat_np).to(device)

    noise_manifest = json.loads(args.noise_manifest.read_text(encoding="utf-8"))
    if noise_manifest.get("status") != "ok" or noise_manifest.get(
        "classification"
    ) != "frozen_m2_deployment_common_random_numbers":
        raise RuntimeError("invalid frozen M2 score-noise manifest")
    if sha256_file(args.noise_npy) != noise_manifest["output_npy_sha256"]:
        raise RuntimeError("M2 score-noise bank differs from its manifest")
    noise_np = np.load(args.noise_npy, allow_pickle=False)
    if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
        raise RuntimeError("unexpected M2 score-noise shape or dtype")
    noise = torch.from_numpy(noise_np).to(device)

    checkpoint_records: list[dict[str, Any]] = []
    m1_scores = np.empty(
        (len(M1_WIDTHS), len(SEEDS), POOL_COUNT, CANDIDATE_COUNT), dtype=np.float32
    )
    m1_metrics: list[dict[str, Any]] = []
    for width_index, width in enumerate(M1_WIDTHS):
        seed_records = []
        for seed_index, seed in enumerate(SEEDS):
            directory, checkpoint, result_path = training_paths(
                args.m1_root, "m1", "true", width, seed_index, environment
            )
            _, checkpoint_sha, result_sha = verify_training_run(
                directory,
                checkpoint,
                result_path,
                method="m1",
                condition="true",
                width=width,
                seed=seed,
            )
            score = score_m1(
                checkpoint,
                source,
                target,
                macro,
                expected_width=width,
                expected_seed=seed,
                expected_stats_sha=expected_stats_sha,
            ).reshape(POOL_COUNT, CANDIDATE_COUNT)
            m1_scores[width_index, seed_index] = score
            metrics = binary_metrics(failure_flat, score.reshape(-1))
            seed_records.append({"seed": seed, **metrics})
            checkpoint_records.append(
                {
                    "method": "M1",
                    "condition": "true",
                    "width": width,
                    "seed": seed,
                    "directory": str(directory),
                    "checkpoint_sha256": checkpoint_sha,
                    "training_result_sha256": result_sha,
                }
            )
        m1_metrics.append(
            {
                "width": width,
                "mean_seed_auroc": float(np.mean([r["auroc"] for r in seed_records])),
                "seeds": seed_records,
            }
        )
    m1_objective = np.asarray([record["mean_seed_auroc"] for record in m1_metrics])
    m1_max = float(m1_objective.max())
    m1_tied = np.flatnonzero(np.isclose(m1_objective, m1_max, rtol=0.0, atol=1e-15))
    selected_m1_width_index = int(m1_tied[0])
    selected_m1_width = M1_WIDTHS[selected_m1_width_index]

    m2_scores = np.empty(
        (
            len(M2_WIDTHS),
            len(SEEDS),
            len(SIGMAS),
            POOL_COUNT,
            CANDIDATE_COUNT,
        ),
        dtype=np.float32,
    )
    m2_metrics: list[dict[str, Any]] = []
    for width_index, width in enumerate(M2_WIDTHS):
        seed_checkpoints: list[Path] = []
        for seed_index, seed in enumerate(SEEDS):
            directory, checkpoint, result_path = training_paths(
                args.m2_root, "m2", "true", width, seed_index, environment
            )
            _, checkpoint_sha, result_sha = verify_training_run(
                directory,
                checkpoint,
                result_path,
                method="m2",
                condition="true",
                width=width,
                seed=seed,
            )
            seed_checkpoints.append(checkpoint)
            checkpoint_records.append(
                {
                    "method": "M2",
                    "condition": "true",
                    "width": width,
                    "seed": seed,
                    "directory": str(directory),
                    "checkpoint_sha256": checkpoint_sha,
                    "training_result_sha256": result_sha,
                }
            )
        for sigma_index, sigma in enumerate(SIGMAS):
            seed_records = []
            for seed_index, seed in enumerate(SEEDS):
                score = score_m2(
                    seed_checkpoints[seed_index],
                    source,
                    target,
                    noise,
                    sigma,
                    expected_width=width,
                    expected_seed=seed,
                    expected_stats_sha=expected_stats_sha,
                    batch_size=args.m2_batch_size,
                ).reshape(POOL_COUNT, CANDIDATE_COUNT)
                m2_scores[width_index, seed_index, sigma_index] = score
                metrics = binary_metrics(failure_flat, score.reshape(-1))
                seed_records.append({"seed": seed, **metrics})
            m2_metrics.append(
                {
                    "width": width,
                    "sigma": sigma,
                    "width_index": width_index,
                    "sigma_index": sigma_index,
                    "mean_seed_auroc": float(
                        np.mean([record["auroc"] for record in seed_records])
                    ),
                    "seeds": seed_records,
                }
            )
    m2_max = max(record["mean_seed_auroc"] for record in m2_metrics)
    selected_m2_record = next(
        record
        for record in m2_metrics
        if math.isclose(record["mean_seed_auroc"], m2_max, rel_tol=0.0, abs_tol=1e-15)
    )
    selected_m2_width = int(selected_m2_record["width"])
    selected_m2_sigma = float(selected_m2_record["sigma"])

    m3_scores = np.empty(
        (2, len(SEEDS), POOL_COUNT, CANDIDATE_COUNT), dtype=np.float32
    )
    m3_metrics: list[dict[str, Any]] = []
    for condition_index, condition in enumerate(("true", "shuffled")):
        seed_records = []
        for seed_index, seed in enumerate(SEEDS):
            directory, checkpoint, result_path = training_paths(
                args.m3_root, "m3", condition, None, seed_index, environment
            )
            _, checkpoint_sha, result_sha = verify_training_run(
                directory,
                checkpoint,
                result_path,
                method="m3",
                condition=condition,
                width=None,
                seed=seed,
            )
            score = score_m3(
                checkpoint,
                source,
                target,
                expected_condition=condition,
                expected_seed=seed,
            ).reshape(POOL_COUNT, CANDIDATE_COUNT)
            m3_scores[condition_index, seed_index] = score
            metrics = binary_metrics(failure_flat, score.reshape(-1))
            seed_records.append({"seed": seed, **metrics})
            checkpoint_records.append(
                {
                    "method": "M3",
                    "condition": condition,
                    "width": None,
                    "seed": seed,
                    "directory": str(directory),
                    "checkpoint_sha256": checkpoint_sha,
                    "training_result_sha256": result_sha,
                }
            )
        m3_metrics.append(
            {
                "condition": condition,
                "mean_seed_auroc": float(np.mean([r["auroc"] for r in seed_records])),
                "seeds": seed_records,
            }
        )

    g0a = robust_knn_isolation(macro_np, k=3)
    g0b = robust_knn_isolation(target_np, k=3)
    g0_metrics = {
        "G0a_macro": binary_metrics(failure_flat, g0a.reshape(-1)),
        "G0b_subgoal": binary_metrics(failure_flat, g0b.reshape(-1)),
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
            output.create_dataset("pool_id", data=pool_id)
            output.create_dataset("attainment_label", data=attainment_label)
            output.create_dataset("failure_label", data=failure_label)
            output.create_dataset("attainment_rate", data=attainment_rate)
            output.create_dataset("m1_width", data=np.asarray(M1_WIDTHS, dtype=np.int64))
            output.create_dataset("m2_width", data=np.asarray(M2_WIDTHS, dtype=np.int64))
            output.create_dataset("training_seed", data=np.asarray(SEEDS, dtype=np.int64))
            output.create_dataset("m2_sigma", data=np.asarray(SIGMAS, dtype=np.float64))
            output.create_dataset("m1_raw_score", data=m1_scores)
            output.create_dataset("m2_raw_score", data=m2_scores)
            output.create_dataset("m3_raw_score", data=m3_scores)
            output.create_dataset("g0a_macro_knn_isolation", data=g0a)
            output.create_dataset("g0b_subgoal_knn_isolation", data=g0b)
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_p2_scorer_selection_retained={partial_h5}")
        raise

    result = {
        "status": "ok",
        "classification": output_classification,
        "environment": environment,
        "partition": "P2-development-only",
        "reporting_rule": "P2 values select frozen settings and are not final thesis results",
        "positive_class": "budgeted-attainment failure (1 - primary at-least-3-of-5 label)",
        "candidate_count": POOL_COUNT * CANDIDATE_COUNT,
        "failure_prevalence": float(failure_label.mean()),
        "selection_rule": {
            "objective": "arithmetic mean of three seed-specific raw-score AUROCs",
            "M1_tie_break": "narrower width",
            "M2_tie_break": "narrower width, then smaller sigma",
        },
        "M1": {
            "score": "squared L2 residual in raw frozen macro-action latent space",
            "width_records": m1_metrics,
            "selected_width": selected_m1_width,
            "selected_width_index": selected_m1_width_index,
        },
        "M2": {
            "score": "mean over 8 fixed draws of squared L2 epsilon-prediction residual",
            "noise_npy_sha256": noise_manifest["output_npy_sha256"],
            "records": m2_metrics,
            "selected_width": selected_m2_width,
            "selected_sigma": selected_m2_sigma,
            "selected_width_index": int(selected_m2_record["width_index"]),
            "selected_sigma_index": int(selected_m2_record["sigma_index"]),
        },
        "M3": {
            "score": "predicted temporal separation in primitive steps",
            "condition_records": m3_metrics,
        },
        "G0": {
            "definition": "within-pool median/IQR standardization then mean Euclidean distance to 3 nearest other candidates",
            "metrics": g0_metrics,
        },
        "checkpoints": checkpoint_records,
        "inputs": {
            "labeled_dir": str(args.labeled_dir),
            "labeled_h5_sha256": labeled_manifest["output_h5_sha256"],
            "labeled_manifest_sha256": sha256_file(args.labeled_dir / "manifest.json"),
            "stats_npz_sha256": expected_stats_sha,
            "noise_npy": str(args.noise_npy),
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
