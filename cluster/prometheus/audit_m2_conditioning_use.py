#!/usr/bin/env python3
"""Frozen P1/P2 diagnostic for source-conditioning use by PushT M2."""

from __future__ import annotations

import argparse
import csv
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
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

from train_m2_diffusion_head import ConditionalEpsilonMLP, enumerate_pairs, map_global_rows


LATENT_DIM = 192
NOISE_DRAWS = 8
SELECTED_WIDTH = 1024
SELECTED_SIGMA = 0.25
SEEDS = (20260728, 20260729, 20260730)
PAIR_SAMPLE_SEED = 20260812
PAIR_SAMPLE_COUNT = 10_000
BOOTSTRAP_REPLICATES = 10_000
REPRODUCTION_ATOL = 2.0e-5


def sha256_file(path: Path, chunk_size: int = 16 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def safe_h5_rows(dataset: h5py.Dataset, positions: np.ndarray) -> np.ndarray:
    positions = np.asarray(positions, dtype=np.int64)
    unique, inverse = np.unique(positions, return_inverse=True)
    values = np.asarray(dataset[unique], dtype=np.float32)
    return values[inverse]


def binary_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, float | int]:
    labels = np.asarray(labels, dtype=np.bool_).reshape(-1)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    if labels.all() or not labels.any() or not np.isfinite(scores).all():
        raise RuntimeError("binary metric requires finite scores and both classes")
    prevalence = float(labels.mean())
    ap = float(average_precision_score(labels, scores))
    return {
        "count": int(labels.size),
        "positive_count": int(labels.sum()),
        "positive_prevalence": prevalence,
        "auroc": float(roc_auc_score(labels, scores)),
        "average_precision": ap,
        "average_precision_minus_prevalence": ap - prevalence,
    }


def paired_bootstrap_mean(values: np.ndarray, rng: np.random.Generator) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    estimates = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    chunk = 100
    for start in range(0, BOOTSTRAP_REPLICATES, chunk):
        stop = min(start + chunk, BOOTSTRAP_REPLICATES)
        indices = rng.integers(0, values.size, size=(stop - start, values.size))
        estimates[start:stop] = values[indices].mean(axis=1)
    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "fraction_above_zero": float(np.mean(values > 0.0)),
        "ci95": [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))],
    }


def cluster_bootstrap_aurocs(
    labels_by_pool: np.ndarray,
    score_by_name: dict[str, np.ndarray],
    rng: np.random.Generator,
) -> dict[str, Any]:
    labels_by_pool = np.asarray(labels_by_pool, dtype=np.bool_)
    pool_count = labels_by_pool.shape[0]
    distributions = {name: [] for name in score_by_name}
    difference_correct_wrong: list[float] = []
    difference_correct_mean: list[float] = []
    attempts = 0
    while len(next(iter(distributions.values()))) < BOOTSTRAP_REPLICATES:
        attempts += 1
        if attempts > BOOTSTRAP_REPLICATES * 5:
            raise RuntimeError("too few valid pool-bootstrap samples")
        chosen = rng.integers(0, pool_count, size=pool_count)
        labels = labels_by_pool[chosen].reshape(-1)
        if labels.all() or not labels.any():
            continue
        current: dict[str, float] = {}
        for name, scores_by_pool in score_by_name.items():
            score = np.asarray(scores_by_pool, dtype=np.float64)[chosen].reshape(-1)
            current[name] = float(roc_auc_score(labels, score))
            distributions[name].append(current[name])
        difference_correct_wrong.append(current["correct"] - current["wrong_pool"])
        difference_correct_mean.append(current["correct"] - current["mean_source"])
    output: dict[str, Any] = {
        "requested_valid_replicates": BOOTSTRAP_REPLICATES,
        "attempts": attempts,
        "discarded_one_class_replicates": attempts - BOOTSTRAP_REPLICATES,
        "auroc_ci95": {},
    }
    for name, values in distributions.items():
        array = np.asarray(values, dtype=np.float64)
        output["auroc_ci95"][name] = [
            float(np.quantile(array, 0.025)),
            float(np.quantile(array, 0.975)),
        ]
    for name, values in (
        ("correct_minus_wrong_pool", difference_correct_wrong),
        ("correct_minus_mean_source", difference_correct_mean),
    ):
        array = np.asarray(values, dtype=np.float64)
        output[f"{name}_ci95"] = [
            float(np.quantile(array, 0.025)),
            float(np.quantile(array, 0.975)),
        ]
    return output


def correlations(first: np.ndarray, second: np.ndarray) -> dict[str, float]:
    first = np.asarray(first, dtype=np.float64).reshape(-1)
    second = np.asarray(second, dtype=np.float64).reshape(-1)
    return {
        "pearson": float(np.corrcoef(first, second)[0, 1]),
        "spearman": float(spearmanr(first, second).statistic),
    }


def relative_change(reference: np.ndarray, ablated: np.ndarray) -> dict[str, float]:
    reference = np.asarray(reference, dtype=np.float64).reshape(-1)
    ablated = np.asarray(ablated, dtype=np.float64).reshape(-1)
    absolute = np.abs(reference - ablated)
    standard_deviation = float(np.std(reference))
    q25, q75 = np.quantile(reference, (0.25, 0.75))
    iqr = float(q75 - q25)
    return {
        "mean_absolute_change": float(absolute.mean()),
        "median_absolute_change": float(np.median(absolute)),
        "mean_absolute_change_over_reference_std": float(absolute.mean() / max(standard_deviation, 1e-12)),
        "median_absolute_change_over_reference_iqr": float(np.median(absolute) / max(iqr, 1e-12)),
    }


def load_checkpoint(
    path: Path,
    device: torch.device,
    expected_seed: int,
    expected_stats_sha: str,
    expected_pair_sha: str,
    expected_latent_sha: str,
) -> tuple[ConditionalEpsilonMLP, dict[str, Any], dict[str, float]]:
    payload = torch.load(path, map_location=device, weights_only=False)
    checks = (
        payload["condition"] == "true",
        int(payload["latent_dim"]) == LATENT_DIM,
        int(payload["hidden_width"]) == SELECTED_WIDTH,
        int(payload["training_seed"]) == expected_seed,
        payload["stats_npz_sha256"] == expected_stats_sha,
        payload["pair_plan_sha256"] == expected_pair_sha,
        payload["latent_cache_sha256"] == expected_latent_sha,
    )
    if not all(checks):
        raise RuntimeError(f"checkpoint lineage mismatch: {path}")
    model = ConditionalEpsilonMLP(LATENT_DIM, SELECTED_WIDTH).to(device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    first_weight = payload["state_dict"]["network.0.weight"].float()
    target_norm = float(torch.linalg.vector_norm(first_weight[:, :LATENT_DIM]).item())
    source_norm = float(torch.linalg.vector_norm(first_weight[:, LATENT_DIM : 2 * LATENT_DIM]).item())
    sigma_norm = float(torch.linalg.vector_norm(first_weight[:, 2 * LATENT_DIM :]).item())
    norms = {
        "noisy_target_frobenius": target_norm,
        "source_frobenius": source_norm,
        "sigma_embedding_frobenius": sigma_norm,
        "source_over_target": source_norm / target_norm,
    }
    return model, payload, norms


@torch.inference_mode()
def score_loaded(
    model: ConditionalEpsilonMLP,
    payload: dict[str, Any],
    source_raw: np.ndarray,
    target_raw: np.ndarray,
    noise: torch.Tensor,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    source_raw_t = torch.from_numpy(np.asarray(source_raw, dtype=np.float32)).to(device)
    target_raw_t = torch.from_numpy(np.asarray(target_raw, dtype=np.float32)).to(device)
    mean = payload["latent_mean"].to(device)
    std = payload["latent_std"].to(device)
    source = (source_raw_t - mean) / std
    target = (target_raw_t - mean) / std
    count = len(source)
    source_expanded = source[:, None, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(-1, LATENT_DIM)
    target_expanded = target[:, None, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(-1, LATENT_DIM)
    epsilon = noise[None, :, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(-1, LATENT_DIM)
    sigma = torch.full((count * NOISE_DRAWS,), SELECTED_SIGMA, device=device, dtype=torch.float32)
    squared_l2 = torch.empty(count * NOISE_DRAWS, dtype=torch.float32, device=device)
    # This is intentionally identical to the original job-294839 deployment
    # batching so the first diagnostic is an implementation-reproduction gate.
    for start in range(0, len(squared_l2), batch_size):
        stop = min(start + batch_size, len(squared_l2))
        prediction = model(
            target_expanded[start:stop] + sigma[start:stop, None] * epsilon[start:stop],
            sigma[start:stop],
            source_expanded[start:stop],
        )
        squared_l2[start:stop] = (epsilon[start:stop] - prediction).square().sum(dim=-1)
    return squared_l2.reshape(count, NOISE_DRAWS).mean(dim=1).cpu().numpy().astype(np.float32)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--pair-plan", type=Path, required=True)
    parser.add_argument("--stats-npz", type=Path, required=True)
    parser.add_argument("--stats-manifest", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--labeled-dir", type=Path, required=True)
    parser.add_argument("--selection-dir", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=2048)
    args = parser.parse_args()
    if len(args.checkpoint) != 3:
        raise RuntimeError("exactly three selected checkpoints are required")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite conditioning-audit output")

    started = time.time()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    torch.manual_seed(PAIR_SAMPLE_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(PAIR_SAMPLE_SEED)
    torch.use_deterministic_algorithms(True)

    latent_manifest = read_json(args.latent_manifest)
    stats_manifest = read_json(args.stats_manifest)
    noise_manifest = read_json(args.noise_manifest)
    labeled_manifest = read_json(args.labeled_dir / "manifest.json")
    selection_manifest = read_json(args.selection_dir / "manifest.json")
    labeled_h5 = args.labeled_dir / "labeled-candidates.h5"
    selection_h5 = args.selection_dir / "scores.h5"
    expected_stats_sha = sha256_file(args.stats_npz)
    expected_latent_sha = sha256_file(args.latent_h5)
    pair_sha = sha256_file(args.pair_plan)
    noise_sha = sha256_file(args.noise_npy)
    if expected_stats_sha != stats_manifest["output_npz_sha256"]:
        raise RuntimeError("statistics hash mismatch")
    if expected_latent_sha != latent_manifest["output_h5_sha256"]:
        raise RuntimeError("latent-cache hash mismatch")
    if noise_sha != noise_manifest["output_npy_sha256"]:
        raise RuntimeError("noise-bank hash mismatch")
    if sha256_file(labeled_h5) != labeled_manifest["output_h5_sha256"]:
        raise RuntimeError("labeled-candidate hash mismatch")
    if sha256_file(selection_h5) != selection_manifest["output_h5_sha256"]:
        raise RuntimeError("selection-score hash mismatch")
    if (
        int(selection_manifest["M2"]["selected_width"]) != SELECTED_WIDTH
        or float(selection_manifest["M2"]["selected_sigma"]) != SELECTED_SIGMA
    ):
        raise RuntimeError("selected M2 configuration changed")

    checkpoint_hash_records = []
    selected_records = {
        int(record["seed"]): record
        for record in selection_manifest["checkpoints"]
        if record["method"] == "M2" and record["condition"] == "true" and int(record["width"]) == SELECTED_WIDTH
    }
    if set(selected_records) != set(SEEDS):
        raise RuntimeError("selection manifest lacks the three selected M2 checkpoints")

    noise_np = np.load(args.noise_npy, allow_pickle=False)
    if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
        raise RuntimeError("invalid noise bank")
    noise = torch.from_numpy(noise_np).to(device)

    pair_rows = read_tsv(args.pair_plan)
    correct_source_global, target_global, correct_info = enumerate_pairs(
        pair_rows, "P1_val", "true", 20260728
    )
    wrong_source_global, wrong_target_global, wrong_info = enumerate_pairs(
        pair_rows, "P1_val", "mismatched", 20260728
    )
    if not np.array_equal(target_global, wrong_target_global):
        raise RuntimeError("correct and wrong-source P1 targets differ")
    if len(target_global) < PAIR_SAMPLE_COUNT:
        raise RuntimeError("too few P1 validation pairs")
    sample_rng = np.random.Generator(np.random.PCG64(PAIR_SAMPLE_SEED))
    sample_indices = np.sort(sample_rng.choice(len(target_global), PAIR_SAMPLE_COUNT, replace=False))
    correct_source_global = correct_source_global[sample_indices]
    wrong_source_global = wrong_source_global[sample_indices]
    target_global = target_global[sample_indices]

    with h5py.File(args.latent_h5, "r") as latent_file:
        cache_rows = np.asarray(latent_file["row_index"][:], dtype=np.int64)
        correct_positions = map_global_rows(cache_rows, correct_source_global)
        wrong_positions = map_global_rows(cache_rows, wrong_source_global)
        target_positions = map_global_rows(cache_rows, target_global)
        p1_correct_source = safe_h5_rows(latent_file["latent"], correct_positions)
        p1_wrong_source = safe_h5_rows(latent_file["latent"], wrong_positions)
        p1_target = safe_h5_rows(latent_file["latent"], target_positions)

    with h5py.File(labeled_h5, "r") as labeled:
        pool_id = np.asarray(labeled["pool_id"][:], dtype=np.int64)
        p2_source_pool = np.asarray(labeled["source_latent"][:], dtype=np.float32)
        p2_target_pool = np.asarray(labeled["selected_subgoal"][:], dtype=np.float32)
        attainment = np.asarray(labeled["primary_label_at_least_3_of_5"][:], dtype=np.bool_)
    if not np.array_equal(pool_id, np.arange(12)) or p2_target_pool.shape != (12, 64, LATENT_DIM):
        raise RuntimeError("unexpected P2 labeled-candidate shape")
    failure = ~attainment
    p2_correct_source = np.broadcast_to(p2_source_pool[:, None, :], p2_target_pool.shape).reshape(-1, LATENT_DIM).copy()
    p2_wrong_source_pool = np.roll(p2_source_pool, shift=-1, axis=0)
    p2_wrong_source = np.broadcast_to(p2_wrong_source_pool[:, None, :], p2_target_pool.shape).reshape(-1, LATENT_DIM).copy()
    p2_target = p2_target_pool.reshape(-1, LATENT_DIM)

    with h5py.File(selection_h5, "r") as selected_scores:
        width_values = np.asarray(selected_scores["m2_width"][:], dtype=np.int64)
        sigma_values = np.asarray(selected_scores["m2_sigma"][:], dtype=np.float64)
        seed_values = np.asarray(selected_scores["training_seed"][:], dtype=np.int64)
        width_index = int(np.flatnonzero(width_values == SELECTED_WIDTH)[0])
        sigma_index = int(np.flatnonzero(sigma_values == SELECTED_SIGMA)[0])
        if not np.array_equal(seed_values, np.asarray(SEEDS, dtype=np.int64)):
            raise RuntimeError("selection seed order changed")
        original_p2_correct = np.asarray(
            selected_scores["m2_raw_score"][width_index, :, sigma_index], dtype=np.float32
        )

    p1_scores = np.empty((3, 3, PAIR_SAMPLE_COUNT), dtype=np.float32)
    p2_scores = np.empty((3, 4, 12, 64), dtype=np.float32)
    first_layer_norms = []
    reproduction_max_abs = 0.0
    checkpoint_shas: list[str] = []
    for seed_index, (seed, checkpoint) in enumerate(zip(SEEDS, args.checkpoint, strict=True)):
        checkpoint_sha = sha256_file(checkpoint)
        if checkpoint_sha != selected_records[seed]["checkpoint_sha256"]:
            raise RuntimeError(f"checkpoint hash differs from selection manifest: {checkpoint}")
        checkpoint_shas.append(checkpoint_sha)
        model, payload, norms = load_checkpoint(
            checkpoint, device, seed, expected_stats_sha, pair_sha, expected_latent_sha
        )
        norms["seed"] = seed
        first_layer_norms.append(norms)
        mean_source_p1 = np.broadcast_to(payload["latent_mean"].cpu().numpy(), p1_correct_source.shape).copy()
        mean_source_p2 = np.broadcast_to(payload["latent_mean"].cpu().numpy(), p2_correct_source.shape).copy()
        p1_scores[seed_index, 0] = score_loaded(model, payload, p1_correct_source, p1_target, noise, device, args.batch_size)
        p1_scores[seed_index, 1] = score_loaded(model, payload, p1_wrong_source, p1_target, noise, device, args.batch_size)
        p1_scores[seed_index, 2] = score_loaded(model, payload, mean_source_p1, p1_target, noise, device, args.batch_size)
        p2_correct = score_loaded(model, payload, p2_correct_source, p2_target, noise, device, args.batch_size)
        p2_wrong = score_loaded(model, payload, p2_wrong_source, p2_target, noise, device, args.batch_size)
        p2_mean = score_loaded(model, payload, mean_source_p2, p2_target, noise, device, args.batch_size)
        p2_scores[seed_index, 0] = p2_correct.reshape(12, 64)
        p2_scores[seed_index, 1] = p2_wrong.reshape(12, 64)
        p2_scores[seed_index, 2] = p2_mean.reshape(12, 64)
        p2_scores[seed_index, 3] = (p2_correct - p2_wrong).reshape(12, 64)
        current_reproduction = float(np.max(np.abs(p2_scores[seed_index, 0] - original_p2_correct[seed_index])))
        reproduction_max_abs = max(reproduction_max_abs, current_reproduction)
        checkpoint_hash_records.append({"seed": seed, "path": str(checkpoint), "sha256": checkpoint_sha})
    if reproduction_max_abs > REPRODUCTION_ATOL:
        raise RuntimeError(
            f"original P2 score reproduction failed: max_abs={reproduction_max_abs} > {REPRODUCTION_ATOL}"
        )

    p1_ensemble = p1_scores.mean(axis=0)
    p1_difference = p1_ensemble[1] - p1_ensemble[0]
    seed_sequence = np.random.SeedSequence(PAIR_SAMPLE_SEED)
    p1_rng, p2_rng = [np.random.default_rng(child) for child in seed_sequence.spawn(2)]
    d1_bootstrap = paired_bootstrap_mean(p1_difference, p1_rng)
    d1_seed_records = []
    for seed_index, seed in enumerate(SEEDS):
        difference = p1_scores[seed_index, 1] - p1_scores[seed_index, 0]
        d1_seed_records.append(
            {
                "seed": seed,
                "correct_mean": float(p1_scores[seed_index, 0].mean()),
                "wrong_episode_mean": float(p1_scores[seed_index, 1].mean()),
                "mean_source_mean": float(p1_scores[seed_index, 2].mean()),
                "wrong_minus_correct_mean": float(difference.mean()),
                "wrong_minus_correct_fraction_above_zero": float(np.mean(difference > 0.0)),
            }
        )

    condition_names = ("correct", "wrong_pool", "mean_source", "conditional_penalty")
    p2_seed_records = []
    for seed_index, seed in enumerate(SEEDS):
        p2_seed_records.append(
            {
                "seed": seed,
                "conditions": {
                    name: binary_metrics(failure, p2_scores[seed_index, condition_index])
                    for condition_index, name in enumerate(condition_names)
                },
            }
        )
    p2_ensemble = p2_scores.mean(axis=0)
    p2_ensemble_metrics = {
        name: binary_metrics(failure, p2_ensemble[index]) for index, name in enumerate(condition_names)
    }
    p2_correlations = {
        name: correlations(p2_ensemble[0], p2_ensemble[index])
        for index, name in ((1, "wrong_pool"), (2, "mean_source"))
    }
    p2_changes = {
        name: relative_change(p2_ensemble[0], p2_ensemble[index])
        for index, name in ((1, "wrong_pool"), (2, "mean_source"))
    }
    p2_bootstrap = cluster_bootstrap_aurocs(
        failure,
        {name: p2_ensemble[index] for index, name in enumerate(condition_names)},
        p2_rng,
    )

    correct_auroc = float(p2_ensemble_metrics["correct"]["auroc"])
    wrong_auroc = float(p2_ensemble_metrics["wrong_pool"]["auroc"])
    mean_auroc = float(p2_ensemble_metrics["mean_source"]["auroc"])
    penalty_auroc = float(p2_ensemble_metrics["conditional_penalty"]["auroc"])
    interpretations = {
        "uses_source_on_real_D25": bool(d1_bootstrap["ci95"][0] > 0.0),
        "conditioning_improves_P2_failure_ranking": bool(
            p2_bootstrap["correct_minus_wrong_pool_ci95"][0] > 0.0
        ),
        "conditional_penalty_is_promising": bool(
            penalty_auroc >= 0.65 and p2_bootstrap["auroc_ci95"]["conditional_penalty"][0] > 0.50
        ),
        "target_dominated_on_P2": bool(
            p2_correlations["wrong_pool"]["pearson"] >= 0.95
            and p2_correlations["mean_source"]["pearson"] >= 0.95
            and correct_auroc - wrong_auroc <= 0.02
            and correct_auroc - mean_auroc <= 0.02
        ),
    }

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    with h5py.File(partial_h5, "x") as output:
        output.attrs["classification"] = "pusht_m2_conditioning_use_audit"
        output.attrs["partition_scope"] = "P1-validation-and-P2-development-only"
        output.attrs["selected_width"] = SELECTED_WIDTH
        output.attrs["selected_sigma"] = SELECTED_SIGMA
        output.create_dataset("training_seed", data=np.asarray(SEEDS, dtype=np.int64))
        output.create_dataset("p1_condition", data=np.asarray([b"correct", b"wrong_episode", b"mean_source"]))
        output.create_dataset("p1_source_global_row", data=correct_source_global)
        output.create_dataset("p1_wrong_source_global_row", data=wrong_source_global)
        output.create_dataset("p1_target_global_row", data=target_global)
        output.create_dataset("p1_score", data=p1_scores, compression="gzip")
        output.create_dataset("p2_condition", data=np.asarray([name.encode("ascii") for name in condition_names]))
        output.create_dataset("p2_failure_label", data=failure)
        output.create_dataset("p2_score", data=p2_scores, compression="gzip")
        output.flush()
    os.replace(partial_h5, args.output_h5)

    result = {
        "status": "ok",
        "classification": "pusht_m2_conditioning_use_audit",
        "partition_scope": "P1-validation-and-P2-development-only",
        "reporting_boundary": "exploratory diagnosis; locked PushT P3/P4 were neither read nor changed",
        "frozen_configuration": {
            "hidden_width": SELECTED_WIDTH,
            "deployment_sigma": SELECTED_SIGMA,
            "training_seeds": list(SEEDS),
            "noise_draws": NOISE_DRAWS,
            "p1_pair_sample_seed": PAIR_SAMPLE_SEED,
            "p1_pair_sample_count": PAIR_SAMPLE_COUNT,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "wrong_pool_mapping": "(pool + 1) mod 12",
        },
        "score_reproduction": {
            "source_job": 294839,
            "maximum_absolute_error": reproduction_max_abs,
            "required_maximum_absolute_error": REPRODUCTION_ATOL,
            "status": "passed",
        },
        "D1_p1_held_out_real_d25": {
            "correct_pair_info": correct_info,
            "wrong_pair_info": wrong_info,
            "seed_records": d1_seed_records,
            "ensemble_wrong_episode_minus_correct": d1_bootstrap,
            "ensemble_correlations": {
                "correct_vs_wrong_episode": correlations(p1_ensemble[0], p1_ensemble[1]),
                "correct_vs_mean_source": correlations(p1_ensemble[0], p1_ensemble[2]),
            },
        },
        "D2_p2_imagined_candidates": {
            "positive_class": "budgeted-attainment failure",
            "failure_prevalence": float(failure.mean()),
            "seed_records": p2_seed_records,
            "ensemble_metrics": p2_ensemble_metrics,
            "ensemble_correlations": p2_correlations,
            "ensemble_ablation_changes": p2_changes,
            "pool_cluster_bootstrap": p2_bootstrap,
        },
        "interpretations_under_prefrozen_rules": interpretations,
        "architectural_first_layer_input_norms": first_layer_norms,
        "inputs": {
            "spec": str(args.spec),
            "spec_sha256": sha256_file(args.spec),
            "latent_h5": str(args.latent_h5),
            "latent_h5_sha256": expected_latent_sha,
            "latent_manifest_sha256": sha256_file(args.latent_manifest),
            "pair_plan": str(args.pair_plan),
            "pair_plan_sha256": pair_sha,
            "stats_npz": str(args.stats_npz),
            "stats_npz_sha256": expected_stats_sha,
            "stats_manifest_sha256": sha256_file(args.stats_manifest),
            "labeled_h5_sha256": labeled_manifest["output_h5_sha256"],
            "selection_h5_sha256": selection_manifest["output_h5_sha256"],
            "noise_npy_sha256": noise_sha,
            "checkpoints": checkpoint_hash_records,
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "runtime": {
            "device": str(device),
            "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
            "torch": torch.__version__,
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "elapsed_seconds": time.time() - started,
        },
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
