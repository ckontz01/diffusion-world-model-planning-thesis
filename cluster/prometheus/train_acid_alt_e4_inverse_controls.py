#!/usr/bin/env python3
"""Train capacity-matched deterministic and Gaussian inverse controls for E4."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Literal

import h5py
import numpy as np
import torch
from torch import nn

from acid_alt_e4_controls import (
    ConditionalGaussianInverse,
    DeterministicInverseRegressor,
    diagonal_gaussian_nll,
)
from train_acid_alt_e4_didm import (
    BATCH_SIZE,
    CONDITION_DROPOUT,
    FINAL_VALIDATION_BATCH_SIZE,
    FINAL_VALIDATION_LIMIT,
    GRADIENT_CLIP,
    LEARNING_RATE,
    MAXIMUM_STEPS,
    SELECTION_VALIDATION_BATCH_SIZE,
    SELECTION_VALIDATION_LIMIT,
    VALIDATION_ACTION_SHUFFLE_SEED,
    VALIDATION_INTERVAL,
    VALIDATION_SUCCESSOR_SHUFFLE_SEED,
    WARMUP_STEPS,
    WEIGHT_DECAY,
    atomic_json,
    atomic_npz,
    checkpoint_parameter_count,
    configure_seed,
    fixed_derangement,
    gather_triplet,
    learning_rate_at_step,
    sha256_file,
)


EXPECTED_PROTOCOL_SHA256 = (
    "eec19adf1558a7366bbc13bd5077c5c26ac4dd73fd5c03b5be2651fe288dfc12"
)
ModelKind = Literal["deterministic", "gaussian"]


def build_model(kind: ModelKind, latent_dim: int, action_dim: int) -> nn.Module:
    if kind == "deterministic":
        return DeterministicInverseRegressor(latent_dim, action_dim)
    if kind == "gaussian":
        return ConditionalGaussianInverse(latent_dim, action_dim)
    raise ValueError(kind)


@torch.inference_mode()
def selection_validation(
    kind: ModelKind,
    model: nn.Module,
    *,
    validation_pairs: torch.Tensor,
    latents: torch.Tensor,
    source_index: torch.Tensor,
    target_index: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    total_loss = 0.0
    total = 0
    for start in range(0, len(validation_pairs), SELECTION_VALIDATION_BATCH_SIZE):
        pairs = validation_pairs[start : start + SELECTION_VALIDATION_BATCH_SIZE]
        current, successor, action = gather_triplet(
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
        if kind == "deterministic":
            assert isinstance(model, DeterministicInverseRegressor)
            loss = (model(current, successor) - action).square().mean(dim=-1)
        else:
            assert isinstance(model, ConditionalGaussianInverse)
            count = len(pairs)
            conditional_mean, conditional_scale = model(
                current, successor, torch.ones(count, device=device)
            )
            current_mean, current_scale = model(
                current,
                torch.zeros_like(successor),
                torch.zeros(count, device=device),
            )
            conditional = diagonal_gaussian_nll(
                conditional_mean, conditional_scale, action
            )
            current_only = diagonal_gaussian_nll(
                current_mean, current_scale, action
            )
            loss = (1.0 - CONDITION_DROPOUT) * conditional + CONDITION_DROPOUT * current_only
        total_loss += float(loss.sum().item())
        total += len(pairs)
    return {"loss": total_loss / total, "examples": total}


@torch.inference_mode()
def final_validation(
    kind: ModelKind,
    model: nn.Module,
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
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, float] | None]:
    model.eval()
    names = (
        "matching_cost",
        "deranged_successor_cost",
        "deranged_action_cost",
        "current_only_cost",
        "matching_ratio",
        "deranged_successor_ratio",
    )
    arrays = {name: np.zeros(len(validation_pairs), dtype=np.float64) for name in names}
    for start in range(0, len(validation_pairs), FINAL_VALIDATION_BATCH_SIZE):
        stop = min(start + FINAL_VALIDATION_BATCH_SIZE, len(validation_pairs))
        pairs = validation_pairs[start:stop]
        wrong_successor_pairs = wrong_successor_lookup[start:stop]
        wrong_action_pairs = wrong_action_lookup[start:stop]
        current, successor, action = gather_triplet(
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
        if kind == "deterministic":
            assert isinstance(model, DeterministicInverseRegressor)
            matching_prediction = model(current, successor)
            wrong_successor_prediction = model(current, wrong_successor)
            matching = (matching_prediction - action).square().mean(dim=-1)
            deranged_successor = (
                wrong_successor_prediction - action
            ).square().mean(dim=-1)
            deranged_action = (
                matching_prediction - wrong_action
            ).square().mean(dim=-1)
            current_only = torch.zeros_like(matching)
            matching_ratio = matching
            wrong_ratio = deranged_successor
        else:
            assert isinstance(model, ConditionalGaussianInverse)
            present = torch.ones(count, device=device)
            absent = torch.zeros(count, device=device)
            matching_mean, matching_scale = model(current, successor, present)
            wrong_mean, wrong_scale = model(current, wrong_successor, present)
            current_mean, current_scale = model(
                current, torch.zeros_like(successor), absent
            )
            matching = diagonal_gaussian_nll(
                matching_mean, matching_scale, action
            )
            deranged_successor = diagonal_gaussian_nll(
                wrong_mean, wrong_scale, action
            )
            deranged_action = diagonal_gaussian_nll(
                matching_mean, matching_scale, wrong_action
            )
            current_only = diagonal_gaussian_nll(
                current_mean, current_scale, action
            )
            matching_ratio = matching - current_only
            wrong_ratio = deranged_successor - current_only
        values = {
            "matching_cost": matching,
            "deranged_successor_cost": deranged_successor,
            "deranged_action_cost": deranged_action,
            "current_only_cost": current_only,
            "matching_ratio": matching_ratio,
            "deranged_successor_ratio": wrong_ratio,
        }
        for name, value in values.items():
            arrays[name][start:stop] = value.double().cpu().numpy()

    matching = arrays["matching_cost"]
    wrong_successor = arrays["deranged_successor_cost"]
    wrong_action = arrays["deranged_action_cost"]
    matching_ratio = arrays["matching_ratio"]
    wrong_ratio = arrays["deranged_successor_ratio"]
    summary = {
        "examples": len(validation_pairs),
        "matching_cost_mean": float(matching.mean()),
        "matching_cost_std": float(matching.std(ddof=1)),
        "successor_pairwise_accuracy": float(np.mean(matching < wrong_successor)),
        "action_pairwise_accuracy": float(np.mean(matching < wrong_action)),
        "deranged_successor_minus_matching_margin": float(
            np.mean(wrong_successor - matching)
        ),
        "deranged_action_minus_matching_margin": float(
            np.mean(wrong_action - matching)
        ),
        "matching_ratio_mean": float(matching_ratio.mean()),
        "deranged_successor_ratio_mean": float(wrong_ratio.mean()),
        "ratio_pairwise_accuracy": float(np.mean(matching_ratio < wrong_ratio)),
        "ratio_wrong_minus_matching_margin": float(
            np.mean(wrong_ratio - matching_ratio)
        ),
    }
    calibration = None
    if kind == "gaussian":
        calibration = {
            "ratio_q50": float(np.quantile(matching_ratio, 0.50)),
            "ratio_q95": float(np.quantile(matching_ratio, 0.95)),
            "ratio_q99": float(np.quantile(matching_ratio, 0.99)),
        }
    return summary, arrays, calibration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "reacher", "cube"), required=True)
    parser.add_argument("--model", choices=("deterministic", "gaussian"), required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--acid-checkpoint", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7101)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for path in (
        args.latent_h5,
        args.latent_manifest,
        args.transition_h5,
        args.transition_manifest,
        args.acid_checkpoint,
        args.protocol,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("E4 protocol hash mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if args.seed != 7101:
        raise ValueError("E4-D2A controls are frozen to seed 7101")
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
        or transition_manifest.get("kind") != "flat_one_model_step_transition_cache"
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
        latent_mean_np = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        latent_std_np = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        action_mean_np = np.asarray(
            handle["stats/acid_action_mean"][:], dtype=np.float32
        )
        action_std_np = np.asarray(
            handle["stats/acid_action_std"][:], dtype=np.float32
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
    final_pairs_np = all_validation_pairs_np[
        : min(FINAL_VALIDATION_LIMIT, len(all_validation_pairs_np))
    ]
    selection_pairs_np = final_pairs_np[
        : min(SELECTION_VALIDATION_LIMIT, len(final_pairs_np))
    ]
    if not len(train_pairs_np) or not len(selection_pairs_np):
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
    selection_pairs = torch.from_numpy(selection_pairs_np)
    final_pairs = torch.from_numpy(final_pairs_np)
    wrong_successor = final_pairs.index_select(
        0,
        fixed_derangement(
            len(final_pairs), seed=VALIDATION_SUCCESSOR_SHUFFLE_SEED
        ),
    )
    wrong_action = final_pairs.index_select(
        0,
        fixed_derangement(len(final_pairs), seed=VALIDATION_ACTION_SHUFFLE_SEED),
    )

    model = build_model(
        args.model, latent_dim=latents.shape[1], action_dim=actions.shape[1]
    ).to(device)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    acid_parameter_count, acid_hash = checkpoint_parameter_count(
        args.acid_checkpoint
    )
    capacity_difference = abs(parameter_count - acid_parameter_count) / acid_parameter_count
    if capacity_difference > 0.10:
        raise RuntimeError("inverse control is not capacity matched to ACID within 10%")

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=WEIGHT_DECAY,
    )
    sampling_generator = torch.Generator(device="cpu").manual_seed(args.seed + 301)
    dropout_generator = torch.Generator(device="cuda").manual_seed(args.seed + 302)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "best.pt"
    log_path = args.output_dir / "training.jsonl"
    started = time.time()
    best_loss = float("inf")
    best_step = -1

    for step in range(1, MAXIMUM_STEPS + 1):
        model.train()
        positions = torch.randint(
            len(train_pairs), (BATCH_SIZE,), generator=sampling_generator
        )
        pairs = train_pairs.index_select(0, positions)
        current, successor, action = gather_triplet(
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
        lr = learning_rate_at_step(step)
        for group in optimizer.param_groups:
            group["lr"] = lr
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            if args.model == "deterministic":
                assert isinstance(model, DeterministicInverseRegressor)
                loss = (model(current, successor) - action).square().mean()
            else:
                assert isinstance(model, ConditionalGaussianInverse)
                dropped = (
                    torch.rand(
                        BATCH_SIZE, generator=dropout_generator, device=device
                    )
                    < CONDITION_DROPOUT
                )
                model_successor = successor.masked_fill(dropped[:, None], 0.0)
                mean, log_scale = model(
                    current,
                    model_successor,
                    (~dropped).to(dtype=current.dtype),
                )
                loss = diagonal_gaussian_nll(mean, log_scale, action).mean()
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss at step {step}")
        loss.backward()
        gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
        if not torch.isfinite(torch.as_tensor(gradient_norm)):
            raise RuntimeError(f"non-finite gradient at step {step}")
        optimizer.step()

        if step == MAXIMUM_STEPS or step % VALIDATION_INTERVAL == 0:
            validation = selection_validation(
                args.model,
                model,
                validation_pairs=selection_pairs,
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
            record = {
                "step": step,
                "training_loss": float(loss.detach().cpu()),
                "selection_validation": validation,
                "learning_rate": lr,
                "gradient_norm": float(torch.as_tensor(gradient_norm).detach().cpu()),
                "elapsed_seconds": time.time() - started,
            }
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps(record, sort_keys=True), flush=True)
            if float(validation["loss"]) < best_loss:
                best_loss = float(validation["loss"])
                best_step = step
                model_config = {
                    "name": f"e4_{args.model}_inverse_control",
                    "latent_dim": int(latents.shape[1]),
                    "action_dim": int(actions.shape[1]),
                    "width": 384,
                    "depth": 3,
                }
                if args.model == "gaussian":
                    model_config.update(
                        minimum_log_scale=-5.0,
                        maximum_log_scale=2.0,
                        successor_dropout=CONDITION_DROPOUT,
                    )
                payload = {
                    "format_version": 1,
                    "model_name": model_config["name"],
                    "task": args.task,
                    "condition": "true_successor",
                    "model_config": model_config,
                    "state_dict": {
                        key: value.detach().cpu()
                        for key, value in model.state_dict().items()
                    },
                    "latent_mean": latent_mean,
                    "latent_std": latent_std,
                    "acid_action_mean": action_mean,
                    "acid_action_std": action_std,
                    "step": step,
                    "selection_validation": validation,
                    "seed": args.seed,
                    "transition_h5_sha256": transition_manifest["output_h5_sha256"],
                    "latent_h5_sha256": latent_manifest["output_h5_sha256"],
                    "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
                    "source_manifest_sha256": sha256_file(args.source_manifest),
                }
                temporary = checkpoint_path.with_name(
                    f".{checkpoint_path.name}.partial-{os.getpid()}"
                )
                torch.save(payload, temporary)
                os.replace(temporary, checkpoint_path)

    payload = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(payload["state_dict"], strict=True)
    replay = selection_validation(
        args.model,
        model,
        validation_pairs=selection_pairs,
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
    if replay != payload["selection_validation"]:
        raise RuntimeError("selected checkpoint validation did not reproduce")
    validation, arrays, calibration = final_validation(
        args.model,
        model,
        validation_pairs=final_pairs,
        wrong_successor_lookup=wrong_successor,
        wrong_action_lookup=wrong_action,
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
    if validation["matching_cost_std"] <= 1.0e-8:
        raise RuntimeError("inverse-control validation score collapsed")
    examples_path = args.output_dir / "validation-examples.npz"
    atomic_npz(
        examples_path,
        pair_index=final_pairs_np,
        episode_idx=episode_np[final_pairs_np],
        step_idx=step_np[final_pairs_np],
        **{key: value.astype(np.float32) for key, value in arrays.items()},
    )
    calibration_path: Path | None = None
    if calibration is not None:
        calibration_path = args.output_dir / "calibration.json"
        atomic_json(
            calibration_path,
            {
                "status": "ok",
                "role": "P1_validation_Gaussian_inverse_ratio_calibration",
                "task": args.task,
                "condition": "true_successor",
                "seed": args.seed,
                **calibration,
                "protected_c1_i1_read": False,
            },
        )

    summary = {
        "status": "ok",
        "kind": "e4_capacity_matched_inverse_control_training",
        "analysis_role": "post-E3 P1-only exploratory control",
        "task": args.task,
        "condition": "true_successor",
        "model": args.model,
        "seed": args.seed,
        "model_config": payload["model_config"],
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
            "selection_validation_limit": SELECTION_VALIDATION_LIMIT,
            "final_validation_limit": FINAL_VALIDATION_LIMIT,
            "validation_interval": VALIDATION_INTERVAL,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "gradient_clip": GRADIENT_CLIP,
            "mixed_precision": "bf16",
            "successor_dropout": CONDITION_DROPOUT if args.model == "gaussian" else 0.0,
            "loss": "diagonal_Gaussian_NLL" if args.model == "gaussian" else "action_MSE",
        },
        "train_pairs": int(len(train_pairs)),
        "validation_pairs_total": int(len(all_validation_pairs_np)),
        "selection_validation_pairs": int(len(selection_pairs)),
        "final_validation_pairs": int(len(final_pairs)),
        "best_step": best_step,
        "best_selection_validation": payload["selection_validation"],
        "replayed_selection_validation": replay,
        "final_validation": validation,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "validation_examples": str(examples_path),
        "validation_examples_sha256": sha256_file(examples_path),
        "calibration": str(calibration_path) if calibration_path else None,
        "calibration_sha256": sha256_file(calibration_path) if calibration_path else None,
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


def self_test() -> None:
    configure_seed(123)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for kind in ("deterministic", "gaussian"):
        model = build_model(kind, 8, 4).to(device)
        current = torch.randn(9, 8, device=device)
        successor = torch.randn(9, 8, device=device)
        action = torch.randn(9, 4, device=device)
        if kind == "deterministic":
            assert isinstance(model, DeterministicInverseRegressor)
            loss = (model(current, successor) - action).square().mean()
        else:
            assert isinstance(model, ConditionalGaussianInverse)
            mean, scale = model(current, successor, torch.ones(9, device=device))
            loss = diagonal_gaussian_nll(mean, scale, action).mean()
        loss.backward()
        if not torch.isfinite(loss):
            raise RuntimeError("inverse-control self-test failed")
    print(json.dumps({"status": "ok", "device": str(device)}, sort_keys=True))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        main()
