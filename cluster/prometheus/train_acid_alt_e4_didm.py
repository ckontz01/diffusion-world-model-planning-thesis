#!/usr/bin/env python3
"""Train the frozen E4 conditional inverse-diffusion mechanism pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from acid_alt_e4_models import (
    ConditionalActionDenoiser,
    cider_ratio,
    count_parameters,
    reconstruction_energy,
)


EXPECTED_PROTOCOL_SHA256 = (
    "eec19adf1558a7366bbc13bd5077c5c26ac4dd73fd5c03b5be2651fe288dfc12"
)
SIGMAS = (0.25, 0.5, 1.0, 2.0, 4.0)
PRIMARY_SIGMAS = (0.5, 1.0, 2.0, 4.0)
CONDITION_DROPOUT = 0.20
MAXIMUM_STEPS = 100_000
WARMUP_STEPS = 1_000
BATCH_SIZE = 512
SELECTION_VALIDATION_BATCH_SIZE = 4096
SELECTION_VALIDATION_LIMIT = 20_000
FINAL_VALIDATION_BATCH_SIZE = 2048
FINAL_VALIDATION_LIMIT = 100_000
FINAL_VALIDATION_DRAWS = 4
VALIDATION_INTERVAL = 5_000
LEARNING_RATE = 1.0e-4
WEIGHT_DECAY = 1.0e-4
GRADIENT_CLIP = 1.0
CIDER_EPSILON = 1.0e-6
TRAIN_SUCCESSOR_SHUFFLE_OFFSET = 20260816101
VALIDATION_SUCCESSOR_SHUFFLE_SEED = 20260816102
VALIDATION_ACTION_SHUFFLE_SEED = 20260816103
SELECTION_NOISE_OFFSET = 20260816104
FINAL_NOISE_OFFSET = 20260816105


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def configure_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def fixed_derangement(length: int, *, seed: int) -> torch.Tensor:
    """Return a deterministic single-cycle permutation without fixed points."""

    if length < 2:
        raise ValueError("derangement needs at least two values")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    cycle = torch.randperm(length, generator=generator)
    mapping = torch.empty(length, dtype=torch.int64)
    mapping[cycle] = cycle.roll(-1)
    if torch.any(mapping == torch.arange(length)):
        raise RuntimeError("derangement contains a fixed point")
    return mapping


def learning_rate_at_step(step: int) -> float:
    if step <= WARMUP_STEPS:
        return LEARNING_RATE * step / WARMUP_STEPS
    progress = (step - WARMUP_STEPS) / (MAXIMUM_STEPS - WARMUP_STEPS)
    return LEARNING_RATE * 0.5 * (1.0 + math.cos(math.pi * progress))


def checkpoint_parameter_count(path: Path) -> tuple[int, str]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if payload.get("model_name") != "acid":
        raise RuntimeError(f"reference checkpoint is not ACID: {path}")
    count = sum(value.numel() for value in payload["state_dict"].values())
    return count, sha256_file(path)


def gather_triplet(
    base_pairs: torch.Tensor,
    *,
    successor_pairs: torch.Tensor,
    action_pairs: torch.Tensor,
    latents: torch.Tensor,
    source_index: torch.Tensor,
    target_index: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Gather independently indexed current, successor, and action values."""

    if not (len(base_pairs) == len(successor_pairs) == len(action_pairs)):
        raise ValueError("triplet lookup lengths differ")
    source = source_index.index_select(0, base_pairs)
    target = target_index.index_select(0, successor_pairs)
    current = (latents.index_select(0, source) - latent_mean) / latent_std
    successor = (latents.index_select(0, target) - latent_mean) / latent_std
    action = (actions.index_select(0, action_pairs) - action_mean) / action_std
    return (
        current.to(device, non_blocking=True),
        successor.to(device, non_blocking=True),
        action.to(device, non_blocking=True),
    )


@torch.inference_mode()
def selection_validation(
    model: ConditionalActionDenoiser,
    *,
    validation_pairs: torch.Tensor,
    selected_successor_lookup: torch.Tensor,
    latents: torch.Tensor,
    source_index: torch.Tensor,
    target_index: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    device: torch.device,
    seed: int,
) -> dict[str, Any]:
    """Cheap fixed validation used only for checkpoint selection."""

    model.eval()
    generator = torch.Generator(device=device.type).manual_seed(seed)
    by_sigma = {sigma: 0.0 for sigma in SIGMAS}
    total = 0
    for start in range(0, len(validation_pairs), SELECTION_VALIDATION_BATCH_SIZE):
        stop = min(start + SELECTION_VALIDATION_BATCH_SIZE, len(validation_pairs))
        pairs = validation_pairs[start:stop]
        successor_pairs = selected_successor_lookup[start:stop]
        current, successor, clean_action = gather_triplet(
            pairs,
            successor_pairs=successor_pairs,
            action_pairs=pairs,
            latents=latents,
            source_index=source_index,
            target_index=target_index,
            actions=actions,
            latent_mean=latent_mean,
            latent_std=latent_std,
            action_mean=action_mean,
            action_std=action_std,
            device=device,
        )
        count = len(pairs)
        present = torch.ones(count, device=device)
        for sigma_value in SIGMAS:
            sigma = torch.full((count,), sigma_value, device=device)
            noise = torch.randn(
                clean_action.shape,
                generator=generator,
                device=device,
                dtype=clean_action.dtype,
            )
            prediction = model(
                current,
                successor,
                clean_action + sigma[:, None] * noise,
                sigma,
                present,
            )
            by_sigma[sigma_value] += float(
                reconstruction_energy(prediction, clean_action).sum().item()
            )
        total += count
    result = {str(sigma): value / total for sigma, value in by_sigma.items()}
    return {
        "mean_x0_energy": float(np.mean(list(result.values()))),
        "by_sigma": result,
        "examples": total,
        "draws": 1,
        "seed": seed,
    }


def _empty_final_arrays(length: int) -> dict[str, np.ndarray]:
    names = (
        "matching_energy",
        "deranged_successor_energy",
        "deranged_action_energy",
        "current_only_energy",
        "matching_cider",
        "deranged_successor_cider",
    )
    arrays: dict[str, np.ndarray] = {}
    for sigma in SIGMAS:
        for name in names:
            arrays[f"sigma_{sigma:g}_{name}"] = np.zeros(length, dtype=np.float64)
    return arrays


@torch.inference_mode()
def final_validation(
    model: ConditionalActionDenoiser,
    *,
    validation_pairs: torch.Tensor,
    wrong_successor_lookup: torch.Tensor,
    wrong_action_lookup: torch.Tensor,
    latents: torch.Tensor,
    source_index: torch.Tensor,
    target_index: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    device: torch.device,
    seed: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Run the complete four-draw condition-use diagnostic."""

    model.eval()
    generator = torch.Generator(device=device.type).manual_seed(seed)
    arrays = _empty_final_arrays(len(validation_pairs))
    total = 0
    for start in range(0, len(validation_pairs), FINAL_VALIDATION_BATCH_SIZE):
        stop = min(start + FINAL_VALIDATION_BATCH_SIZE, len(validation_pairs))
        pairs = validation_pairs[start:stop]
        wrong_successor_pairs = wrong_successor_lookup[start:stop]
        wrong_action_pairs = wrong_action_lookup[start:stop]
        current, matching_successor, clean_action = gather_triplet(
            pairs,
            successor_pairs=pairs,
            action_pairs=pairs,
            latents=latents,
            source_index=source_index,
            target_index=target_index,
            actions=actions,
            latent_mean=latent_mean,
            latent_std=latent_std,
            action_mean=action_mean,
            action_std=action_std,
            device=device,
        )
        _, wrong_successor, _ = gather_triplet(
            pairs,
            successor_pairs=wrong_successor_pairs,
            action_pairs=pairs,
            latents=latents,
            source_index=source_index,
            target_index=target_index,
            actions=actions,
            latent_mean=latent_mean,
            latent_std=latent_std,
            action_mean=action_mean,
            action_std=action_std,
            device=device,
        )
        _, _, wrong_action = gather_triplet(
            pairs,
            successor_pairs=pairs,
            action_pairs=wrong_action_pairs,
            latents=latents,
            source_index=source_index,
            target_index=target_index,
            actions=actions,
            latent_mean=latent_mean,
            latent_std=latent_std,
            action_mean=action_mean,
            action_std=action_std,
            device=device,
        )
        count = len(pairs)
        present = torch.ones(count, device=device)
        absent = torch.zeros(count, device=device)
        zero_successor = torch.zeros_like(matching_successor)

        for sigma_value in SIGMAS:
            matching_sum = torch.zeros(count, device=device)
            wrong_successor_sum = torch.zeros(count, device=device)
            wrong_action_sum = torch.zeros(count, device=device)
            current_only_sum = torch.zeros(count, device=device)
            sigma = torch.full((count,), sigma_value, device=device)
            for _ in range(FINAL_VALIDATION_DRAWS):
                noise = torch.randn(
                    clean_action.shape,
                    generator=generator,
                    device=device,
                    dtype=clean_action.dtype,
                )
                noisy_action = clean_action + sigma[:, None] * noise
                matching_sum += reconstruction_energy(
                    model(
                        current,
                        matching_successor,
                        noisy_action,
                        sigma,
                        present,
                    ),
                    clean_action,
                )
                wrong_successor_sum += reconstruction_energy(
                    model(current, wrong_successor, noisy_action, sigma, present),
                    clean_action,
                )
                current_only_sum += reconstruction_energy(
                    model(current, zero_successor, noisy_action, sigma, absent),
                    clean_action,
                )
                wrong_noisy_action = wrong_action + sigma[:, None] * noise
                wrong_action_sum += reconstruction_energy(
                    model(
                        current,
                        matching_successor,
                        wrong_noisy_action,
                        sigma,
                        present,
                    ),
                    wrong_action,
                )

            matching = matching_sum / FINAL_VALIDATION_DRAWS
            wrong_successor_energy = wrong_successor_sum / FINAL_VALIDATION_DRAWS
            wrong_action_energy = wrong_action_sum / FINAL_VALIDATION_DRAWS
            current_only = current_only_sum / FINAL_VALIDATION_DRAWS
            matching_cider = cider_ratio(
                matching, current_only, epsilon=CIDER_EPSILON
            )
            wrong_successor_cider = cider_ratio(
                wrong_successor_energy, current_only, epsilon=CIDER_EPSILON
            )
            values = {
                "matching_energy": matching,
                "deranged_successor_energy": wrong_successor_energy,
                "deranged_action_energy": wrong_action_energy,
                "current_only_energy": current_only,
                "matching_cider": matching_cider,
                "deranged_successor_cider": wrong_successor_cider,
            }
            for name, value in values.items():
                arrays[f"sigma_{sigma_value:g}_{name}"][start:stop] = (
                    value.double().cpu().numpy()
                )
        total += count

    primary_prefixes = [f"sigma_{sigma:g}_" for sigma in PRIMARY_SIGMAS]

    def primary_mean(name: str) -> np.ndarray:
        return np.mean(
            np.stack([arrays[f"{prefix}{name}"] for prefix in primary_prefixes]),
            axis=0,
        )

    matching = primary_mean("matching_energy")
    wrong_successor = primary_mean("deranged_successor_energy")
    wrong_action = primary_mean("deranged_action_energy")
    current_only = primary_mean("current_only_energy")
    matching_cider = primary_mean("matching_cider")
    wrong_successor_cider = primary_mean("deranged_successor_cider")
    arrays.update(
        {
            "primary_matching_energy": matching,
            "primary_deranged_successor_energy": wrong_successor,
            "primary_deranged_action_energy": wrong_action,
            "primary_current_only_energy": current_only,
            "primary_matching_cider": matching_cider,
            "primary_deranged_successor_cider": wrong_successor_cider,
        }
    )

    by_sigma: dict[str, Any] = {}
    calibration: dict[str, Any] = {}
    for sigma_value in SIGMAS:
        prefix = f"sigma_{sigma_value:g}_"
        sigma_matching = arrays[f"{prefix}matching_energy"]
        sigma_wrong_successor = arrays[f"{prefix}deranged_successor_energy"]
        sigma_wrong_action = arrays[f"{prefix}deranged_action_energy"]
        sigma_current_only = arrays[f"{prefix}current_only_energy"]
        sigma_cider = arrays[f"{prefix}matching_cider"]
        sigma_wrong_cider = arrays[f"{prefix}deranged_successor_cider"]
        by_sigma[str(sigma_value)] = {
            "matching_energy_mean": float(sigma_matching.mean()),
            "deranged_successor_energy_mean": float(
                sigma_wrong_successor.mean()
            ),
            "deranged_action_energy_mean": float(sigma_wrong_action.mean()),
            "current_only_energy_mean": float(sigma_current_only.mean()),
            "successor_pairwise_accuracy": float(
                np.mean(sigma_matching < sigma_wrong_successor)
            ),
            "action_pairwise_accuracy": float(
                np.mean(sigma_matching < sigma_wrong_action)
            ),
            "deranged_successor_minus_matching_margin": float(
                np.mean(sigma_wrong_successor - sigma_matching)
            ),
            "deranged_action_minus_matching_margin": float(
                np.mean(sigma_wrong_action - sigma_matching)
            ),
            "matching_cider_mean": float(sigma_cider.mean()),
            "deranged_successor_cider_mean": float(sigma_wrong_cider.mean()),
            "cider_pairwise_accuracy": float(
                np.mean(sigma_cider < sigma_wrong_cider)
            ),
        }
        calibration[str(sigma_value)] = {
            "cider_q50": float(np.quantile(sigma_cider, 0.50)),
            "cider_q95": float(np.quantile(sigma_cider, 0.95)),
            "cider_q99": float(np.quantile(sigma_cider, 0.99)),
        }

    result = {
        "examples": total,
        "draws": FINAL_VALIDATION_DRAWS,
        "seed": seed,
        "primary_sigmas": list(PRIMARY_SIGMAS),
        "matching_energy_mean": float(matching.mean()),
        "deranged_successor_energy_mean": float(wrong_successor.mean()),
        "deranged_action_energy_mean": float(wrong_action.mean()),
        "current_only_energy_mean": float(current_only.mean()),
        "successor_pairwise_accuracy": float(np.mean(matching < wrong_successor)),
        "action_pairwise_accuracy": float(np.mean(matching < wrong_action)),
        "deranged_successor_minus_matching_margin": float(
            np.mean(wrong_successor - matching)
        ),
        "deranged_action_minus_matching_margin": float(
            np.mean(wrong_action - matching)
        ),
        "matching_cider_mean": float(matching_cider.mean()),
        "deranged_successor_cider_mean": float(wrong_successor_cider.mean()),
        "cider_wrong_minus_matching_margin": float(
            np.mean(wrong_successor_cider - matching_cider)
        ),
        "cider_pairwise_accuracy": float(
            np.mean(matching_cider < wrong_successor_cider)
        ),
        "matching_energy_std": float(matching.std(ddof=1)),
        "matching_cider_std": float(matching_cider.std(ddof=1)),
        "by_sigma": by_sigma,
        "calibration": calibration,
    }
    return result, arrays


def self_test() -> None:
    configure_seed(123)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ConditionalActionDenoiser(8, 4, width=32, depth=2).to(device)
    current = torch.randn(7, 8, device=device)
    successor = torch.randn(7, 8, device=device)
    action = torch.randn(7, 4, device=device)
    sigma = torch.tensor(
        [0.25, 0.5, 1.0, 2.0, 4.0, 1.0, 0.5], device=device
    )
    noise = torch.randn_like(action)
    prediction = model(
        current,
        successor,
        action + sigma[:, None] * noise,
        sigma,
        torch.ones(7, device=device),
    )
    energy = reconstruction_energy(prediction, action)
    ratio = cider_ratio(energy, energy + 0.5)
    if prediction.shape != action.shape or not torch.isfinite(ratio).all():
        raise RuntimeError("forward self-test failed")
    loss = energy.mean()
    loss.backward()
    if not all(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        raise RuntimeError("backward self-test failed")
    mapping = fixed_derangement(17, seed=456)
    if torch.any(mapping == torch.arange(17)):
        raise RuntimeError("derangement self-test failed")
    print(
        json.dumps(
            {
                "status": "ok",
                "device": str(device),
                "parameter_count": count_parameters(model),
                "loss": float(loss.detach().cpu()),
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "reacher", "cube"), required=True)
    parser.add_argument(
        "--condition",
        choices=("true_successor", "shuffled_successor"),
        required=True,
    )
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--acid-checkpoint", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.seed != 7101:
        raise RuntimeError("E4-P1 permits only seed 7101")
    required = (
        args.latent_h5,
        args.latent_manifest,
        args.transition_h5,
        args.transition_manifest,
        args.acid_checkpoint,
        args.protocol,
        args.source_manifest,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("E4 protocol hash mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    transition_manifest = json.loads(
        args.transition_manifest.read_text(encoding="utf-8")
    )
    if (
        latent_manifest.get("status") != "ok"
        or sha256_file(args.latent_h5) != latent_manifest.get("output_h5_sha256")
    ):
        raise RuntimeError("latent cache does not match its manifest")
    if (
        transition_manifest.get("status") != "ok"
        or transition_manifest.get("kind")
        != "flat_one_model_step_transition_cache"
        or sha256_file(args.transition_h5)
        != transition_manifest.get("output_h5_sha256")
        or transition_manifest.get("latent_h5_sha256")
        != latent_manifest.get("output_h5_sha256")
    ):
        raise RuntimeError("transition-cache lineage mismatch")

    configure_seed(args.seed)
    device = torch.device("cuda")
    with h5py.File(args.latent_h5, "r") as handle:
        latents_np = np.asarray(handle["latent"][:], dtype=np.float32)
    with h5py.File(args.transition_h5, "r") as handle:
        source_np = np.asarray(handle["source_index"][:], dtype=np.int64)
        target_np = np.asarray(handle["target_index"][:], dtype=np.int64)
        actions_np = np.asarray(handle["action"][:], dtype=np.float32)
        role_np = np.asarray(handle["role"][:], dtype=np.uint8)
        episode_np = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        step_np = np.asarray(handle["step_idx"][:], dtype=np.int64)
        latent_mean_np = np.asarray(
            handle["stats/latent_mean"][:], dtype=np.float32
        )
        latent_std_np = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        action_mean_np = np.asarray(
            handle["stats/acid_action_mean"][:], dtype=np.float32
        )
        action_std_np = np.asarray(
            handle["stats/acid_action_std"][:], dtype=np.float32
        )
        planner_mean_np = np.asarray(
            handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
        )
        planner_std_np = np.asarray(
            handle["stats/planner_primitive_action_std"][:], dtype=np.float64
        )
    if (
        not np.isfinite(latents_np).all()
        or not np.isfinite(actions_np).all()
        or np.any(latent_std_np <= 1.0e-6)
        or np.any(action_std_np <= 1.0e-6)
    ):
        raise RuntimeError("non-finite or degenerate training cache")

    train_pairs_np = np.flatnonzero(role_np == 0).astype(np.int64)
    all_validation_pairs_np = np.flatnonzero(role_np == 1).astype(np.int64)
    final_validation_pairs_np = all_validation_pairs_np[
        : min(FINAL_VALIDATION_LIMIT, len(all_validation_pairs_np))
    ]
    selection_validation_pairs_np = final_validation_pairs_np[
        : min(SELECTION_VALIDATION_LIMIT, len(final_validation_pairs_np))
    ]
    if not len(train_pairs_np) or not len(selection_validation_pairs_np):
        raise RuntimeError("empty P1 train or validation split")

    latents = torch.from_numpy(latents_np)
    source_index = torch.from_numpy(source_np)
    target_index = torch.from_numpy(target_np)
    actions = torch.from_numpy(actions_np)
    latent_mean = torch.from_numpy(latent_mean_np)
    latent_std = torch.from_numpy(latent_std_np)
    action_mean = torch.from_numpy(action_mean_np)
    action_std = torch.from_numpy(action_std_np)
    train_pairs = torch.from_numpy(train_pairs_np)
    selection_pairs = torch.from_numpy(selection_validation_pairs_np)
    final_pairs = torch.from_numpy(final_validation_pairs_np)

    train_derangement = fixed_derangement(
        len(train_pairs), seed=TRAIN_SUCCESSOR_SHUFFLE_OFFSET + args.seed
    )
    train_shuffled_successor_lookup = train_pairs.index_select(
        0, train_derangement
    )
    selection_wrong_mapping = fixed_derangement(
        len(selection_pairs), seed=VALIDATION_SUCCESSOR_SHUFFLE_SEED
    )
    selection_wrong_successor_lookup = selection_pairs.index_select(
        0, selection_wrong_mapping
    )
    final_wrong_successor_mapping = fixed_derangement(
        len(final_pairs), seed=VALIDATION_SUCCESSOR_SHUFFLE_SEED
    )
    final_wrong_successor_lookup = final_pairs.index_select(
        0, final_wrong_successor_mapping
    )
    final_wrong_action_mapping = fixed_derangement(
        len(final_pairs), seed=VALIDATION_ACTION_SHUFFLE_SEED
    )
    final_wrong_action_lookup = final_pairs.index_select(
        0, final_wrong_action_mapping
    )
    if args.condition == "true_successor":
        selection_successor_lookup = selection_pairs
    else:
        selection_successor_lookup = selection_wrong_successor_lookup

    model = ConditionalActionDenoiser(
        latent_dim=latents.shape[1], action_dim=actions.shape[1]
    ).to(device)
    parameter_count = count_parameters(model)
    acid_parameter_count, acid_hash = checkpoint_parameter_count(
        args.acid_checkpoint
    )
    capacity_difference = abs(parameter_count - acid_parameter_count) / acid_parameter_count
    if capacity_difference > 0.10:
        raise RuntimeError("E4 denoiser is not capacity matched to ACID within 10%")

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=WEIGHT_DECAY,
    )
    sampling_generator = torch.Generator(device="cpu").manual_seed(args.seed + 101)
    noise_generator = torch.Generator(device="cuda").manual_seed(args.seed + 202)
    dropout_generator = torch.Generator(device="cuda").manual_seed(args.seed + 203)
    sigma_generator = torch.Generator(device="cuda").manual_seed(args.seed + 204)
    sigma_values = torch.tensor(SIGMAS, device=device, dtype=torch.float32)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "best.pt"
    log_path = args.output_dir / "training.jsonl"
    started = time.time()
    best_loss = float("inf")
    best_step = -1
    last_selection: dict[str, Any] | None = None

    for step in range(1, MAXIMUM_STEPS + 1):
        model.train()
        local_positions = torch.randint(
            len(train_pairs), (BATCH_SIZE,), generator=sampling_generator
        )
        selected_pairs = train_pairs.index_select(0, local_positions)
        if args.condition == "true_successor":
            successor_pairs = selected_pairs
        else:
            successor_pairs = train_shuffled_successor_lookup.index_select(
                0, local_positions
            )
        current, successor, clean_action = gather_triplet(
            selected_pairs,
            successor_pairs=successor_pairs,
            action_pairs=selected_pairs,
            latents=latents,
            source_index=source_index,
            target_index=target_index,
            actions=actions,
            latent_mean=latent_mean,
            latent_std=latent_std,
            action_mean=action_mean,
            action_std=action_std,
            device=device,
        )
        sigma_index = torch.randint(
            len(SIGMAS),
            (BATCH_SIZE,),
            generator=sigma_generator,
            device=device,
        )
        sigma = sigma_values.index_select(0, sigma_index)
        noise = torch.randn(
            clean_action.shape,
            generator=noise_generator,
            device=device,
            dtype=clean_action.dtype,
        )
        noisy_action = clean_action + sigma[:, None] * noise
        dropped = (
            torch.rand(BATCH_SIZE, generator=dropout_generator, device=device)
            < CONDITION_DROPOUT
        )
        model_successor = successor.masked_fill(dropped[:, None], 0.0)
        successor_present = (~dropped).to(dtype=current.dtype)

        lr = learning_rate_at_step(step)
        for group in optimizer.param_groups:
            group["lr"] = lr
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            prediction = model(
                current,
                model_successor,
                noisy_action,
                sigma,
                successor_present,
            )
            loss = reconstruction_energy(prediction, clean_action).mean()
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss at step {step}")
        loss.backward()
        gradient_norm = torch.nn.utils.clip_grad_norm_(
            model.parameters(), GRADIENT_CLIP
        )
        if not torch.isfinite(torch.as_tensor(gradient_norm)):
            raise RuntimeError(f"non-finite gradient at step {step}")
        optimizer.step()

        if step == MAXIMUM_STEPS or step % VALIDATION_INTERVAL == 0:
            last_selection = selection_validation(
                model,
                validation_pairs=selection_pairs,
                selected_successor_lookup=selection_successor_lookup,
                latents=latents,
                source_index=source_index,
                target_index=target_index,
                actions=actions,
                latent_mean=latent_mean,
                latent_std=latent_std,
                action_mean=action_mean,
                action_std=action_std,
                device=device,
                seed=SELECTION_NOISE_OFFSET + args.seed,
            )
            record = {
                "step": step,
                "training_loss": float(loss.detach().cpu()),
                "selection_validation": last_selection,
                "learning_rate": lr,
                "gradient_norm": float(
                    torch.as_tensor(gradient_norm).detach().cpu()
                ),
                "elapsed_seconds": time.time() - started,
            }
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps(record, sort_keys=True), flush=True)
            selection_loss = float(last_selection["mean_x0_energy"])
            if selection_loss < best_loss:
                best_loss = selection_loss
                best_step = step
                payload = {
                    "format_version": 1,
                    "model_name": "e4_conditional_action_denoiser",
                    "condition": args.condition,
                    "task": args.task,
                    "model_config": {
                        "name": "e4_conditional_action_denoiser",
                        "latent_dim": int(latents.shape[1]),
                        "action_dim": int(actions.shape[1]),
                        "width": 384,
                        "depth": 3,
                        "noise_embedding_dim": 64,
                        "prediction": "clean_standardized_action_x0",
                        "successor_dropout_keeps_current": True,
                    },
                    "state_dict": {
                        key: value.detach().cpu()
                        for key, value in model.state_dict().items()
                    },
                    "latent_mean": latent_mean,
                    "latent_std": latent_std,
                    "acid_action_mean": action_mean,
                    "acid_action_std": action_std,
                    "planner_primitive_action_mean": torch.from_numpy(
                        planner_mean_np
                    ),
                    "planner_primitive_action_std": torch.from_numpy(
                        planner_std_np
                    ),
                    "step": step,
                    "selection_validation": last_selection,
                    "seed": args.seed,
                    "training_design": {
                        "sigmas": list(SIGMAS),
                        "primary_sigmas": list(PRIMARY_SIGMAS),
                        "condition_dropout": CONDITION_DROPOUT,
                        "loss": "clean_action_x0_mse_only",
                        "train_successor_shuffle_seed": (
                            TRAIN_SUCCESSOR_SHUFFLE_OFFSET + args.seed
                            if args.condition == "shuffled_successor"
                            else None
                        ),
                        "validation_successor_shuffle_seed": VALIDATION_SUCCESSOR_SHUFFLE_SEED,
                        "validation_action_shuffle_seed": VALIDATION_ACTION_SHUFFLE_SEED,
                    },
                    "transition_h5_sha256": transition_manifest[
                        "output_h5_sha256"
                    ],
                    "latent_h5_sha256": latent_manifest["output_h5_sha256"],
                    "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
                    "source_manifest_sha256": sha256_file(args.source_manifest),
                }
                temporary = checkpoint_path.with_name(
                    f".{checkpoint_path.name}.partial-{os.getpid()}"
                )
                torch.save(payload, temporary)
                os.replace(temporary, checkpoint_path)

    if not checkpoint_path.is_file() or last_selection is None:
        raise RuntimeError("training completed without a selected checkpoint")
    best_payload = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(best_payload["state_dict"], strict=True)
    replay_selection = selection_validation(
        model,
        validation_pairs=selection_pairs,
        selected_successor_lookup=selection_successor_lookup,
        latents=latents,
        source_index=source_index,
        target_index=target_index,
        actions=actions,
        latent_mean=latent_mean,
        latent_std=latent_std,
        action_mean=action_mean,
        action_std=action_std,
        device=device,
        seed=SELECTION_NOISE_OFFSET + args.seed,
    )
    if replay_selection != best_payload["selection_validation"]:
        raise RuntimeError("selected checkpoint validation did not reproduce exactly")

    final_result, final_arrays = final_validation(
        model,
        validation_pairs=final_pairs,
        wrong_successor_lookup=final_wrong_successor_lookup,
        wrong_action_lookup=final_wrong_action_lookup,
        latents=latents,
        source_index=source_index,
        target_index=target_index,
        actions=actions,
        latent_mean=latent_mean,
        latent_std=latent_std,
        action_mean=action_mean,
        action_std=action_std,
        device=device,
        seed=FINAL_NOISE_OFFSET + args.seed,
    )
    if (
        not np.isfinite(final_arrays["primary_matching_energy"]).all()
        or final_result["matching_energy_std"] <= 1.0e-8
        or final_result["matching_cider_std"] <= 1.0e-8
    ):
        raise RuntimeError("final E4 validation score collapsed or is non-finite")

    validation_path = args.output_dir / "validation-examples.npz"
    atomic_npz(
        validation_path,
        pair_index=final_validation_pairs_np,
        episode_idx=episode_np[final_validation_pairs_np],
        step_idx=step_np[final_validation_pairs_np],
        **{key: value.astype(np.float32) for key, value in final_arrays.items()},
    )
    calibration_path = args.output_dir / "calibration.json"
    atomic_json(
        calibration_path,
        {
            "status": "ok",
            "role": "P1_validation_CIDER_calibration",
            "task": args.task,
            "condition": args.condition,
            "seed": args.seed,
            "sigmas": list(SIGMAS),
            "primary_scoring_sigmas": list(PRIMARY_SIGMAS),
            "draws": FINAL_VALIDATION_DRAWS,
            "cider_epsilon": CIDER_EPSILON,
            "quantiles": final_result["calibration"],
            "protected_c1_i1_read": False,
        },
    )

    summary = {
        "status": "ok",
        "kind": "e4_conditional_inverse_diffusion_p1_training",
        "analysis_role": "post-E3 P1-only exploratory mechanism development",
        "task": args.task,
        "condition": args.condition,
        "seed": args.seed,
        "model_config": best_payload["model_config"],
        "parameter_count": parameter_count,
        "capacity_match": {
            "acid_parameter_count": acid_parameter_count,
            "relative_difference_to_acid": capacity_difference,
            "acid_checkpoint": str(args.acid_checkpoint),
            "acid_checkpoint_sha256": acid_hash,
        },
        "optimization": {
            "maximum_steps": MAXIMUM_STEPS,
            "warmup_steps": WARMUP_STEPS,
            "batch_size": BATCH_SIZE,
            "selection_validation_batch_size": SELECTION_VALIDATION_BATCH_SIZE,
            "selection_validation_limit": SELECTION_VALIDATION_LIMIT,
            "final_validation_batch_size": FINAL_VALIDATION_BATCH_SIZE,
            "final_validation_limit": FINAL_VALIDATION_LIMIT,
            "final_validation_draws": FINAL_VALIDATION_DRAWS,
            "validation_interval": VALIDATION_INTERVAL,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "gradient_clip": GRADIENT_CLIP,
            "mixed_precision": "bf16",
            "sigmas": list(SIGMAS),
            "primary_sigmas": list(PRIMARY_SIGMAS),
            "condition_dropout": CONDITION_DROPOUT,
            "loss": "clean_action_x0_mse_only",
        },
        "train_pairs": int(len(train_pairs)),
        "validation_pairs_total": int(len(all_validation_pairs_np)),
        "selection_validation_pairs": int(len(selection_pairs)),
        "final_validation_pairs": int(len(final_pairs)),
        "best_step": best_step,
        "best_selection_validation": best_payload["selection_validation"],
        "replayed_selection_validation": replay_selection,
        "final_validation": final_result,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "validation_examples": str(validation_path),
        "validation_examples_sha256": sha256_file(validation_path),
        "calibration": str(calibration_path),
        "calibration_sha256": sha256_file(calibration_path),
        "training_log": str(log_path),
        "training_log_sha256": sha256_file(log_path),
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": latent_manifest["output_h5_sha256"],
        "transition_h5": str(args.transition_h5),
        "transition_h5_sha256": transition_manifest["output_h5_sha256"],
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "protected_c1_i1_read": False,
        "confirmation_data_read": False,
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": str(device),
            "gpu": torch.cuda.get_device_name(device),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
        },
    }
    atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        main()
