#!/usr/bin/env python3
"""Train the published TRM pair head and its shuffled-label null."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch
from torch import nn

from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.models import TemporalReachabilityHead, count_parameters
from acid_alternative.train_transition_scorer import fixed_derangement_indices

TRM_TRAINING_PERMUTATION_SEED_OFFSET = 2026081308


def configure_determinism(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (1 << 32))
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def atomic_torch_save(path: Path, value: dict[str, Any]) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("xb") as stream:
            torch.save(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    except BaseException:
        if partial.exists():
            partial.unlink()
        raise


@torch.inference_mode()
def evaluate(
    model: TemporalReachabilityHead,
    latents: torch.Tensor,
    first: torch.Tensor,
    second: torch.Tensor,
    labels: torch.Tensor,
    *,
    scale: float,
    batch_size: int,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    loss_sum = 0.0
    squared_error_sum = 0.0
    symmetry_sum = 0.0
    count = 0
    loss_function = nn.SmoothL1Loss(reduction="sum")
    for start in range(0, len(labels), batch_size):
        end = min(start + batch_size, len(labels))
        first_index = first[start:end].to(device, non_blocking=True)
        second_index = second[start:end].to(device, non_blocking=True)
        target_raw = labels[start:end].to(device, non_blocking=True)
        target = target_raw / scale
        first_latent = latents.index_select(0, first_index)
        second_latent = latents.index_select(0, second_index)
        prediction = model(first_latent, second_latent)
        reverse = model(second_latent, first_latent)
        if not torch.isfinite(prediction).all():
            raise RuntimeError("non-finite TRM validation prediction")
        loss_sum += float(loss_function(prediction, target).item())
        squared_error_sum += float(
            ((prediction * scale - target_raw) ** 2).sum().item()
        )
        symmetry_sum += float(((prediction - reverse).abs() * scale).sum().item())
        count += end - start
    return {
        "smooth_l1_scaled": loss_sum / count,
        "rmse_unscaled": (squared_error_sum / count) ** 0.5,
        "mean_absolute_order_asymmetry_unscaled": symmetry_sum / count,
        "examples": float(count),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--pair-h5", type=Path, required=True)
    parser.add_argument("--pair-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--condition", choices=("true", "shuffled_label"), required=True
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument(
        "--target-scale",
        type=float,
        help=(
            "Optional assertion against the frozen pair-cache scale. The cache, "
            "not this CLI, is authoritative."
        ),
    )
    parser.add_argument("--learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--maximum-epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--minimum-delta", type=float, default=1.0e-8)
    args = parser.parse_args()

    for path in (
        args.latent_h5,
        args.latent_manifest,
        args.pair_h5,
        args.pair_manifest,
        args.transition_h5,
        args.transition_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.source_manifest is not None and not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if (
        min(
            args.learning_rate,
            args.batch_size,
            args.maximum_epochs,
            args.patience,
        )
        <= 0
        or args.weight_decay < 0
        or args.minimum_delta < 0
    ):
        raise ValueError("invalid optimization setting")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    pair_manifest = json.loads(args.pair_manifest.read_text(encoding="utf-8"))
    transition_manifest = json.loads(
        args.transition_manifest.read_text(encoding="utf-8")
    )
    latent_hash = sha256_file(args.latent_h5)
    pair_hash = sha256_file(args.pair_h5)
    transition_hash = sha256_file(args.transition_h5)
    if latent_hash != latent_manifest.get("output_h5_sha256"):
        raise RuntimeError("latent hash mismatch")
    if pair_hash != pair_manifest.get("output_h5_sha256"):
        raise RuntimeError("pair cache hash mismatch")
    if transition_hash != transition_manifest.get("output_h5_sha256"):
        raise RuntimeError("transition cache hash mismatch")
    if pair_manifest.get("latent_h5_sha256") != latent_hash:
        raise RuntimeError("pair cache and latent cache lineage differ")
    if transition_manifest.get("latent_h5_sha256") != latent_hash:
        raise RuntimeError("transition cache and latent cache lineage differ")
    try:
        target_scale = float(pair_manifest["label"]["scale_for_training"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("pair manifest has no valid frozen target scale") from error
    if not np.isfinite(target_scale) or target_scale <= 0:
        raise RuntimeError("pair manifest target scale is invalid")
    if args.target_scale is not None and args.target_scale != target_scale:
        raise RuntimeError(
            f"declared target scale {args.target_scale} differs from pair cache "
            f"scale {target_scale}"
        )

    configure_determinism(args.seed)
    device = torch.device(args.device)
    with h5py.File(args.latent_h5, "r") as handle:
        latent_numpy = np.asarray(handle["latent"][:], dtype=np.float32)
    if not np.isfinite(latent_numpy).all():
        raise RuntimeError("latent cache contains non-finite values")
    with h5py.File(args.pair_h5, "r") as handle:
        first = torch.from_numpy(np.asarray(handle["first_index"][:], dtype=np.int64))
        second = torch.from_numpy(np.asarray(handle["second_index"][:], dtype=np.int64))
        labels = torch.from_numpy(np.asarray(handle["label"][:], dtype=np.float32))
        role = torch.from_numpy(np.asarray(handle["role"][:], dtype=np.uint8))
        target_name = str(handle.attrs["target"])
        target_formula = str(handle.attrs["target_formula"])
        h5_target_scale = float(handle.attrs["target_scale"])
    if h5_target_scale != target_scale:
        raise RuntimeError(
            "pair HDF5 target scale differs from its manifest: "
            f"{h5_target_scale} != {target_scale}"
        )
    with h5py.File(args.transition_h5, "r") as handle:
        latent_mean = torch.from_numpy(
            np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        )
        latent_std = torch.from_numpy(
            np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        )
        planner_action_mean = torch.from_numpy(
            np.asarray(
                handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
            )
        )
        planner_action_std = torch.from_numpy(
            np.asarray(
                handle["stats/planner_primitive_action_std"][:], dtype=np.float64
            )
        )
    train_indices = torch.nonzero(role == 0, as_tuple=False).flatten()
    validation_indices = torch.nonzero(role == 1, as_tuple=False).flatten()
    if len(train_indices) != 100_000 or len(validation_indices) != 10_000:
        raise RuntimeError("TRM cache must contain the frozen 100k/10k split")

    label_permutation_sha256 = None
    train_labels = labels.index_select(0, train_indices).clone()
    sampling_generator = torch.Generator(device="cpu").manual_seed(
        args.seed ^ 0x52544D31
    )
    if args.condition == "shuffled_label":
        permutation = fixed_derangement_indices(
            len(train_labels), seed=TRM_TRAINING_PERMUTATION_SEED_OFFSET + args.seed
        )
        train_labels = train_labels.index_select(0, permutation)
        label_permutation_sha256 = hashlib.sha256(
            permutation.numpy().astype(np.int64, copy=False).tobytes()
        ).hexdigest()

    latents = torch.from_numpy(latent_numpy).to(device, non_blocking=True)
    del latent_numpy
    model = TemporalReachabilityHead(latent_dim=int(latents.shape[1])).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    loss_function = nn.SmoothL1Loss()
    model_config = {
        "name": "reachability",
        "latent_dim": int(latents.shape[1]),
        "hidden_width": 256,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "best.pt"
    log_path = args.output_dir / "training.jsonl"
    best_loss = float("inf")
    best_epoch = -1
    epochs_without_improvement = 0
    history: list[dict[str, Any]] = []
    started = time.time()

    for epoch in range(1, args.maximum_epochs + 1):
        model.train()
        order = torch.randperm(len(train_indices), generator=sampling_generator)
        loss_sum = 0.0
        examples = 0
        for start in range(0, len(order), args.batch_size):
            positions = order[start : start + args.batch_size]
            pair_indices = train_indices.index_select(0, positions)
            first_index = first.index_select(0, pair_indices).to(
                device, non_blocking=True
            )
            second_index = second.index_select(0, pair_indices).to(
                device, non_blocking=True
            )
            target = train_labels.index_select(0, positions).to(
                device, non_blocking=True
            )
            optimizer.zero_grad(set_to_none=True)
            prediction = model(
                latents.index_select(0, first_index),
                latents.index_select(0, second_index),
            )
            loss = loss_function(prediction, target / target_scale)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite TRM training loss")
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach().cpu()) * len(positions)
            examples += len(positions)

        validation = evaluate(
            model,
            latents,
            first.index_select(0, validation_indices),
            second.index_select(0, validation_indices),
            labels.index_select(0, validation_indices),
            scale=target_scale,
            batch_size=args.batch_size,
            device=device,
        )
        record = {
            "epoch": epoch,
            "train_smooth_l1_scaled": loss_sum / examples,
            "validation": validation,
            "elapsed_seconds": time.time() - started,
        }
        history.append(record)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

        if validation["smooth_l1_scaled"] < best_loss - args.minimum_delta:
            best_loss = validation["smooth_l1_scaled"]
            best_epoch = epoch
            epochs_without_improvement = 0
            atomic_torch_save(
                checkpoint_path,
                {
                    "format_version": 1,
                    "model_name": "reachability",
                    "condition": args.condition,
                    "model_config": model_config,
                    "state_dict": {
                        key: value.detach().cpu()
                        for key, value in model.state_dict().items()
                    },
                    # Retained for common evaluator provenance; R1 itself uses
                    # native latents and does not apply these statistics.
                    "latent_mean": latent_mean,
                    "latent_std": latent_std,
                    "planner_primitive_action_mean": planner_action_mean,
                    "planner_primitive_action_std": planner_action_std,
                    "target": target_name,
                    "target_formula": target_formula,
                    "target_scale": target_scale,
                    "seed": args.seed,
                    "control_design": {
                        "training_permutation_kind": (
                            "single_cycle_random_derangement"
                            if args.condition == "shuffled_label"
                            else None
                        ),
                        "training_permutation_seed": (
                            TRM_TRAINING_PERMUTATION_SEED_OFFSET + args.seed
                            if args.condition == "shuffled_label"
                            else None
                        ),
                        "minibatch_rng_stream_changed_by_control": False,
                    },
                    "epoch": epoch,
                    "validation": validation,
                    "latent_h5_sha256": latent_hash,
                    "pair_h5_sha256": pair_hash,
                    "transition_h5_sha256": transition_hash,
                    "source_manifest_sha256": (
                        sha256_file(args.source_manifest)
                        if args.source_manifest
                        else None
                    ),
                },
            )
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= args.patience:
            break

    if not checkpoint_path.is_file():
        raise RuntimeError("TRM training produced no checkpoint")
    best_payload = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(best_payload["state_dict"], strict=True)
    final_validation = evaluate(
        model,
        latents,
        first.index_select(0, validation_indices),
        second.index_select(0, validation_indices),
        labels.index_select(0, validation_indices),
        scale=target_scale,
        batch_size=args.batch_size,
        device=device,
    )
    if abs(final_validation["smooth_l1_scaled"] - best_loss) > 1.0e-9:
        raise RuntimeError(
            "reloaded TRM checkpoint does not reproduce its validation loss"
        )

    summary = {
        "status": "ok",
        "kind": "trm_reachability_head_training",
        "model": "reachability",
        "condition": args.condition,
        "model_config": model_config,
        "parameter_count": count_parameters(model),
        "seed": args.seed,
        "target": target_name,
        "target_formula": target_formula,
        "target_scale": target_scale,
        "optimization": {
            "optimizer": "AdamW",
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "batch_size": args.batch_size,
            "loss": "SmoothL1",
            "maximum_epochs": args.maximum_epochs,
            "early_stopping_patience": args.patience,
            "minimum_delta": args.minimum_delta,
            "schedule": "constant",
        },
        "train_pairs": len(train_indices),
        "validation_pairs": len(validation_indices),
        "label_permutation_sha256": label_permutation_sha256,
        "label_permutation_kind": (
            "single_cycle_random_derangement"
            if args.condition == "shuffled_label"
            else None
        ),
        "label_permutation_seed": (
            TRM_TRAINING_PERMUTATION_SEED_OFFSET + args.seed
            if args.condition == "shuffled_label"
            else None
        ),
        "minibatch_rng_stream_changed_by_control": False,
        "validation_labels_permuted": False,
        "best_epoch": best_epoch,
        "epochs_completed": len(history),
        "best_validation": final_validation,
        "inputs": {
            "latent_h5": str(args.latent_h5),
            "latent_h5_sha256": latent_hash,
            "pair_h5": str(args.pair_h5),
            "pair_h5_sha256": pair_hash,
            "transition_h5": str(args.transition_h5),
            "transition_h5_sha256": transition_hash,
            "source_manifest": str(args.source_manifest)
            if args.source_manifest
            else None,
            "source_manifest_sha256": (
                sha256_file(args.source_manifest) if args.source_manifest else None
            ),
        },
        "runtime": {
            "device": str(device),
            "gpu": torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else None,
            "torch": torch.__version__,
            "elapsed_seconds": time.time() - started,
        },
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
