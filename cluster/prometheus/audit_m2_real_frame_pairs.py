#!/usr/bin/env python3
"""P2-only real-frame reachability diagnostic for the frozen PushT M2."""

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
import torch
from sklearn.metrics import average_precision_score, roc_auc_score

from audit_m2_conditioning_use import score_loaded
from score_nulls_autoencoder_and_fit_p2_calibrators import score_autoencoder
from train_m2_diffusion_head import ConditionalEpsilonMLP


LATENT_DIM = 192
WIDTH = 1024
SIGMA = 0.25
NOISE_DRAWS = 8
SEEDS = (20260728, 20260729, 20260730)
CONDITIONS = (
    "true_correct_source",
    "true_wrong_source",
    "true_mean_source",
    "true_conditional_penalty",
    "mismatched_training_null",
    "autoencoder_control",
)
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260812


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


def metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, float | int]:
    labels = np.asarray(labels, dtype=np.bool_).reshape(-1)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    if labels.all() or not labels.any() or not np.isfinite(scores).all():
        raise RuntimeError("metrics require finite scores and both classes")
    prevalence = float(labels.mean())
    ap = float(average_precision_score(labels, scores))
    return {
        "count": int(labels.size),
        "failure_count": int(labels.sum()),
        "failure_prevalence": prevalence,
        "auroc": float(roc_auc_score(labels, scores)),
        "average_precision": ap,
        "average_precision_minus_prevalence": ap - prevalence,
    }


def stratified_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    per_stratum = [metrics(labels[index], scores[index]) for index in range(2)]
    return {
        "combined": metrics(labels, scores),
        "per_stratum": {
            "same_trajectory_delta25": per_stratum[0],
            "cross_trajectory": per_stratum[1],
        },
        "macro_stratum_auroc": float(np.mean([record["auroc"] for record in per_stratum])),
    }


def load_diffusion(
    checkpoint: Path,
    device: torch.device,
    *,
    condition: str,
    seed: int,
    expected_stats_sha: str,
    expected_hash: str,
) -> tuple[ConditionalEpsilonMLP, dict[str, Any]]:
    actual_hash = sha256_file(checkpoint)
    if actual_hash != expected_hash:
        raise RuntimeError(f"checkpoint differs from frozen audit record: {checkpoint}")
    payload = torch.load(checkpoint, map_location=device, weights_only=False)
    if (
        payload["condition"] != condition
        or int(payload["latent_dim"]) != LATENT_DIM
        or int(payload["hidden_width"]) != WIDTH
        or int(payload["training_seed"]) != seed
        or payload["stats_npz_sha256"] != expected_stats_sha
    ):
        raise RuntimeError(f"checkpoint payload mismatch: {checkpoint}")
    model = ConditionalEpsilonMLP(LATENT_DIM, WIDTH).to(device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model, payload


def frozen_checkpoint_hashes(
    selection_manifest: dict[str, Any], calibration_manifest: dict[str, Any]
) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
    true_hashes = {
        int(record["seed"]): record["checkpoint_sha256"]
        for record in selection_manifest["checkpoints"]
        if record["method"] == "M2" and record["condition"] == "true" and int(record["width"]) == WIDTH
    }
    null_hashes = {
        int(record["seed"]): record["checkpoint_sha256"]
        for record in calibration_manifest["checkpoints"]
        if record["method"] == "M2" and record["condition"] == "mismatched"
    }
    autoencoder_hashes = {
        int(record["seed"]): record["checkpoint_sha256"]
        for record in calibration_manifest["checkpoints"]
        if record["method"] == "M2-autoencoder" and record["condition"] == "plain_autoencoder_control"
    }
    for name, values in (
        ("true", true_hashes), ("null", null_hashes), ("autoencoder", autoencoder_hashes)
    ):
        if set(values) != set(SEEDS):
            raise RuntimeError(f"frozen {name} checkpoint set is incomplete")
    return true_hashes, null_hashes, autoencoder_hashes


def bootstrap(
    labels: np.ndarray,
    ensemble_scores: np.ndarray,
    rng: np.random.Generator,
) -> dict[str, Any]:
    distributions = {name: [] for name in CONDITIONS}
    differences = {
        "true_correct_minus_mismatched_training_null": [],
        "true_correct_minus_autoencoder_control": [],
        "true_correct_minus_true_wrong_source": [],
        "true_correct_minus_true_mean_source": [],
    }
    attempts = 0
    while len(distributions[CONDITIONS[0]]) < BOOTSTRAP_REPLICATES:
        attempts += 1
        if attempts > BOOTSTRAP_REPLICATES * 10:
            raise RuntimeError("too few valid stratified pool-bootstrap samples")
        chosen = np.stack(
            [rng.integers(0, labels.shape[1], size=labels.shape[1]) for _ in range(2)], axis=0
        )
        stratum_labels = [labels[stratum, chosen[stratum]].reshape(-1) for stratum in range(2)]
        if any(current.all() or not current.any() for current in stratum_labels):
            continue
        values: dict[str, float] = {}
        for condition_index, condition in enumerate(CONDITIONS):
            stratum_auc = []
            for stratum in range(2):
                current_score = ensemble_scores[condition_index, stratum, chosen[stratum]].reshape(-1)
                stratum_auc.append(float(roc_auc_score(stratum_labels[stratum], current_score)))
            values[condition] = float(np.mean(stratum_auc))
            distributions[condition].append(values[condition])
        true_value = values["true_correct_source"]
        differences["true_correct_minus_mismatched_training_null"].append(
            true_value - values["mismatched_training_null"]
        )
        differences["true_correct_minus_autoencoder_control"].append(
            true_value - values["autoencoder_control"]
        )
        differences["true_correct_minus_true_wrong_source"].append(
            true_value - values["true_wrong_source"]
        )
        differences["true_correct_minus_true_mean_source"].append(
            true_value - values["true_mean_source"]
        )
    result: dict[str, Any] = {
        "valid_replicates": BOOTSTRAP_REPLICATES,
        "attempts": attempts,
        "discarded_one_class_replicates": attempts - BOOTSTRAP_REPLICATES,
        "macro_stratum_auroc_ci95": {},
        "difference_ci95": {},
    }
    for name, values in distributions.items():
        array = np.asarray(values, dtype=np.float64)
        result["macro_stratum_auroc_ci95"][name] = [
            float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))
        ]
    for name, values in differences.items():
        array = np.asarray(values, dtype=np.float64)
        result["difference_ci95"][name] = [
            float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))
        ]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate-h5", type=Path, required=True)
    parser.add_argument("--aggregate-manifest", type=Path, required=True)
    parser.add_argument("--stats-npz", type=Path, required=True)
    parser.add_argument("--stats-manifest", type=Path, required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--calibration-manifest", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--true-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--null-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--autoencoder-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=2048)
    args = parser.parse_args()
    if any(len(values) != 3 for values in (args.true_checkpoint, args.null_checkpoint, args.autoencoder_checkpoint)):
        raise RuntimeError("exactly three checkpoints are required for each condition")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite real-frame audit")
    started = time.time()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    torch.manual_seed(BOOTSTRAP_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(BOOTSTRAP_SEED)
    torch.use_deterministic_algorithms(True)

    aggregate_manifest = json.loads(args.aggregate_manifest.read_text(encoding="utf-8"))
    stats_manifest = json.loads(args.stats_manifest.read_text(encoding="utf-8"))
    selection_manifest = json.loads(args.selection_manifest.read_text(encoding="utf-8"))
    calibration_manifest = json.loads(args.calibration_manifest.read_text(encoding="utf-8"))
    noise_manifest = json.loads(args.noise_manifest.read_text(encoding="utf-8"))
    aggregate_sha = sha256_file(args.aggregate_h5)
    stats_sha = sha256_file(args.stats_npz)
    noise_sha = sha256_file(args.noise_npy)
    if aggregate_sha != aggregate_manifest["output_h5_sha256"]:
        raise RuntimeError("real-frame aggregate hash mismatch")
    if stats_sha != stats_manifest["output_npz_sha256"]:
        raise RuntimeError("P1 statistics hash mismatch")
    if noise_sha != noise_manifest["output_npy_sha256"]:
        raise RuntimeError("score-noise hash mismatch")
    if int(selection_manifest["M2"]["selected_width"]) != WIDTH or float(
        selection_manifest["M2"]["selected_sigma"]
    ) != SIGMA:
        raise RuntimeError("selected M2 configuration differs")
    true_hashes, null_hashes, autoencoder_hashes = frozen_checkpoint_hashes(
        selection_manifest, calibration_manifest
    )

    with h5py.File(args.aggregate_h5, "r") as aggregate:
        source = np.asarray(aggregate["source_latent"][:], dtype=np.float32)
        target = np.asarray(aggregate["target_latent"][:], dtype=np.float32)
        source_episode = np.asarray(aggregate["source_episode_id"][:], dtype=np.int64)
        attained = np.asarray(aggregate["primary_label_at_least_3_of_5"][:], dtype=np.bool_)
    if source.shape != (2, 12, 64, LATENT_DIM) or target.shape != source.shape:
        raise RuntimeError(f"unexpected real-frame latent shape: {source.shape}")
    failure = ~attained
    source_flat_by_stratum = source.reshape(2, 768, LATENT_DIM)
    wrong_source = np.roll(source_flat_by_stratum, shift=-1, axis=1).reshape(source.shape)
    wrong_episode = np.roll(source_episode.reshape(2, 768), shift=-1, axis=1).reshape(source_episode.shape)
    if np.any(source_episode == wrong_episode):
        raise RuntimeError("wrong-source cyclic mapping contains a same-episode match")
    source_flat = source.reshape(-1, LATENT_DIM)
    wrong_flat = wrong_source.reshape(-1, LATENT_DIM)
    target_flat = target.reshape(-1, LATENT_DIM)
    noise_np = np.load(args.noise_npy, allow_pickle=False)
    if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
        raise RuntimeError("invalid score-noise bank")
    noise = torch.from_numpy(noise_np).to(device)
    source_tensor = torch.from_numpy(source_flat).to(device)
    target_tensor = torch.from_numpy(target_flat).to(device)

    score = np.empty((3, len(CONDITIONS), 2, 12, 64), dtype=np.float32)
    checkpoint_records = []
    for seed_index, seed in enumerate(SEEDS):
        true_checkpoint = args.true_checkpoint[seed_index]
        null_checkpoint = args.null_checkpoint[seed_index]
        autoencoder_checkpoint = args.autoencoder_checkpoint[seed_index]
        true_model, true_payload = load_diffusion(
            true_checkpoint, device, condition="true", seed=seed,
            expected_stats_sha=stats_sha, expected_hash=true_hashes[seed]
        )
        null_model, null_payload = load_diffusion(
            null_checkpoint, device, condition="mismatched", seed=seed,
            expected_stats_sha=stats_sha, expected_hash=null_hashes[seed]
        )
        mean_source = np.broadcast_to(true_payload["latent_mean"].cpu().numpy(), source_flat.shape).copy()
        true_correct = score_loaded(
            true_model, true_payload, source_flat, target_flat, noise, device, args.batch_size
        )
        true_wrong = score_loaded(
            true_model, true_payload, wrong_flat, target_flat, noise, device, args.batch_size
        )
        true_mean = score_loaded(
            true_model, true_payload, mean_source, target_flat, noise, device, args.batch_size
        )
        null_correct = score_loaded(
            null_model, null_payload, source_flat, target_flat, noise, device, args.batch_size
        )
        autoencoder = score_autoencoder(
            autoencoder_checkpoint, source_tensor, target_tensor,
            width=WIDTH, seed=seed, stats_sha=stats_sha
        )
        condition_values = (
            true_correct,
            true_wrong,
            true_mean,
            true_correct - true_wrong,
            null_correct,
            autoencoder,
        )
        for condition_index, value in enumerate(condition_values):
            score[seed_index, condition_index] = np.asarray(value, dtype=np.float32).reshape(2, 12, 64)
        checkpoint_records.extend(
            [
                {"kind": "true", "seed": seed, "path": str(true_checkpoint), "sha256": true_hashes[seed]},
                {"kind": "mismatched_null", "seed": seed, "path": str(null_checkpoint), "sha256": null_hashes[seed]},
                {"kind": "autoencoder", "seed": seed, "path": str(autoencoder_checkpoint), "sha256": autoencoder_hashes[seed]},
            ]
        )
        if sha256_file(autoencoder_checkpoint) != autoencoder_hashes[seed]:
            raise RuntimeError(f"autoencoder checkpoint hash mismatch: {autoencoder_checkpoint}")

    seed_records = []
    for seed_index, seed in enumerate(SEEDS):
        seed_records.append(
            {
                "seed": seed,
                "conditions": {
                    condition: stratified_metrics(failure, score[seed_index, condition_index])
                    for condition_index, condition in enumerate(CONDITIONS)
                },
            }
        )
    ensemble = score.mean(axis=0)
    ensemble_metrics = {
        condition: stratified_metrics(failure, ensemble[condition_index])
        for condition_index, condition in enumerate(CONDITIONS)
    }
    bootstrap_result = bootstrap(failure, ensemble, np.random.default_rng(BOOTSTRAP_SEED))
    ci = bootstrap_result["macro_stratum_auroc_ci95"]
    diff = bootstrap_result["difference_ci95"]
    correct_point = ensemble_metrics["true_correct_source"]["macro_stratum_auroc"]
    interpretations = {
        "real_frame_discrimination_supported": bool(
            correct_point >= 0.65 and ci["true_correct_source"][0] > 0.50
        ),
        "beats_mismatched_training_null": bool(
            diff["true_correct_minus_mismatched_training_null"][0] > 0.0
        ),
        "beats_autoencoder_control": bool(
            diff["true_correct_minus_autoencoder_control"][0] > 0.0
        ),
        "correct_source_beats_wrong_source": bool(
            diff["true_correct_minus_true_wrong_source"][0] > 0.0
        ),
        "correct_source_beats_mean_source": bool(
            diff["true_correct_minus_true_mean_source"][0] > 0.0
        ),
    }
    interpretations["strong_specific_support_for_conditional_diffusion"] = bool(
        all(interpretations.values())
    )

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    with h5py.File(partial, "x") as output:
        output.attrs["classification"] = "pusht_m2_real_frame_reachability_audit"
        output.attrs["partition_scope"] = "P2-development-only"
        output.create_dataset("condition", data=np.asarray([name.encode("ascii") for name in CONDITIONS]))
        output.create_dataset("training_seed", data=np.asarray(SEEDS, dtype=np.int64))
        output.create_dataset("failure_label", data=failure)
        output.create_dataset("source_episode_id", data=source_episode)
        output.create_dataset("wrong_source_episode_id", data=wrong_episode)
        output.create_dataset("score", data=score, compression="gzip")
        output.flush()
    os.replace(partial, args.output_h5)

    result = {
        "status": "ok",
        "classification": "pusht_m2_real_frame_reachability_audit",
        "partition_scope": "P2-development-only",
        "reporting_boundary": "exploratory; locked P3/P4 were not read or changed",
        "frozen_configuration": {
            "width": WIDTH,
            "sigma": SIGMA,
            "noise_draws": NOISE_DRAWS,
            "training_seeds": list(SEEDS),
            "wrong_source_mapping": "next flattened candidate within stratum, cyclic",
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "label_summary": {
            "positive_class": "primary physical budgeted-attainment failure",
            "combined_failure_prevalence": float(failure.mean()),
            "same_trajectory_delta25_failure_prevalence": float(failure[0].mean()),
            "cross_trajectory_failure_prevalence": float(failure[1].mean()),
        },
        "seed_records": seed_records,
        "ensemble_metrics": ensemble_metrics,
        "stratified_pool_bootstrap": bootstrap_result,
        "interpretations_under_prefrozen_rules": interpretations,
        "inputs": {
            "spec": str(args.spec),
            "spec_sha256": sha256_file(args.spec),
            "aggregate_h5": str(args.aggregate_h5),
            "aggregate_h5_sha256": aggregate_sha,
            "aggregate_manifest_sha256": sha256_file(args.aggregate_manifest),
            "stats_npz_sha256": stats_sha,
            "selection_manifest_sha256": sha256_file(args.selection_manifest),
            "calibration_manifest_sha256": sha256_file(args.calibration_manifest),
            "noise_npy_sha256": noise_sha,
            "checkpoints": checkpoint_records,
        },
        "output_h5": str(args.output_h5),
        "output_h5_sha256": sha256_file(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
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
