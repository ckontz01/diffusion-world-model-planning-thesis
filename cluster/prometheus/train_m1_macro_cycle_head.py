#!/usr/bin/env python3

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


LINEAR_LAYERS = 3


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def atomic_torch_save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("xb") as stream:
        torch.save(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def configure_determinism(seed: int) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed % (1 << 32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    return {
        "seed": seed,
        "pythonhashseed_at_process_start": os.environ.get("PYTHONHASHSEED"),
        "cublas_workspace_config_at_process_start": os.environ.get(
            "CUBLAS_WORKSPACE_CONFIG"
        ),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
    }


def resolve_device(raw: str) -> torch.device:
    if raw == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(raw)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


class MacroInverseDynamicsMLP(nn.Module):
    """Three-linear-layer inverse model for the frozen Hi-LeWM macro space."""

    def __init__(self, latent_dim: int, macro_dim: int, hidden_width: int) -> None:
        super().__init__()
        if hidden_width not in {256, 512}:
            raise ValueError("M1 hidden width must be 256 or 512")
        self.latent_dim = int(latent_dim)
        self.macro_dim = int(macro_dim)
        self.hidden_width = int(hidden_width)
        self.network = nn.Sequential(
            nn.Linear(2 * self.latent_dim, self.hidden_width),
            nn.Mish(),
            nn.Linear(self.hidden_width, self.hidden_width),
            nn.Mish(),
            nn.Linear(self.hidden_width, self.macro_dim),
        )

    def forward(self, source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        return self.network(torch.cat((source, target), dim=-1))


def map_global_rows(cache_rows: np.ndarray, requested: np.ndarray) -> np.ndarray:
    positions = np.searchsorted(cache_rows, requested)
    if np.any(positions >= cache_rows.size):
        raise RuntimeError("requested global row lies outside the P1 latent cache")
    if not np.array_equal(cache_rows[positions], requested):
        missing = requested[cache_rows[positions] != requested][:10]
        raise RuntimeError(f"requested rows are absent from P1 cache: {missing}")
    return positions.astype(np.int64, copy=False)


def deranged_label_indices(count: int, seed: int) -> tuple[np.ndarray, str]:
    if count < 2:
        raise RuntimeError("permuted M1 null requires at least two labels")
    rng = np.random.Generator(np.random.PCG64(seed))
    order = rng.permutation(count)
    mapping = np.empty(count, dtype=np.int64)
    mapping[order] = np.roll(order, 1)
    if np.any(mapping == np.arange(count)):
        raise RuntimeError("M1 null permutation contains a fixed point")
    return mapping, sha256_array(mapping)


def subset_indices(count: int, limit: int | None, seed: int) -> tuple[np.ndarray, str | None]:
    if limit is None or limit >= count:
        return np.arange(count, dtype=np.int64), None
    rng = np.random.Generator(np.random.PCG64(seed))
    selected = np.sort(rng.choice(count, size=limit, replace=False))
    return selected, sha256_array(selected)


@torch.inference_mode()
def evaluate(
    model: nn.Module,
    latents: torch.Tensor,
    source_index: np.ndarray,
    target_index: np.ndarray,
    macro_targets: torch.Tensor,
    label_index: np.ndarray,
    macro_mean: torch.Tensor,
    macro_std: torch.Tensor,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    standardized_error_sum = 0.0
    raw_error_sum = 0.0
    element_count = 0
    example_count = 0
    for start in range(0, len(source_index), batch_size):
        stop = min(start + batch_size, len(source_index))
        source = torch.as_tensor(source_index[start:stop], device=device)
        target = torch.as_tensor(target_index[start:stop], device=device)
        labels = torch.as_tensor(label_index[start:stop], device=device)
        raw_macro = macro_targets.index_select(0, labels)
        standardized_macro = (raw_macro - macro_mean) / macro_std
        prediction = model(
            latents.index_select(0, source), latents.index_select(0, target)
        )
        if not torch.isfinite(prediction).all():
            raise RuntimeError("non-finite M1 validation prediction")
        standardized_error = prediction - standardized_macro
        raw_prediction = prediction * macro_std + macro_mean
        raw_error = raw_prediction - raw_macro
        standardized_error_sum += float(standardized_error.square().sum().item())
        raw_error_sum += float(raw_error.square().sum().item())
        element_count += standardized_error.numel()
        example_count += len(source)
    standardized_mse = standardized_error_sum / element_count
    raw_mse = raw_error_sum / element_count
    macro_dim = int(macro_targets.shape[1])
    return {
        "standardized_macro_mse": standardized_mse,
        "standardized_macro_rmse": standardized_mse**0.5,
        "raw_macro_mse": raw_mse,
        "raw_macro_rmse": raw_mse**0.5,
        "raw_squared_l2_mean": raw_error_sum / example_count,
        "macro_dim": macro_dim,
    }


def load_role(
    handle: h5py.File,
    role: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    group = handle[role]
    source = np.asarray(group["source_global_row"][:], dtype=np.int64)
    target = np.asarray(group["target_global_row"][:], dtype=np.int64)
    episode = np.asarray(group["episode_id"][:], dtype=np.int64)
    macro = np.asarray(group["macro_action"][:], dtype=np.float32)
    count = len(source)
    if len(target) != count or len(episode) != count or len(macro) != count:
        raise RuntimeError(f"M1 target-cache length mismatch for {role}")
    if macro.ndim != 2 or not np.isfinite(macro).all():
        raise RuntimeError(f"invalid M1 macro targets for {role}")
    if not np.all(target - source == 25):
        raise RuntimeError(f"non-Delta=25 target cache for {role}")
    return source, target, episode, macro


def train(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint_path = args.output_dir / "best-checkpoint.pt"
    result_path = args.output_dir / "training-result.json"
    if checkpoint_path.exists() or result_path.exists():
        raise SystemExit(f"refusing to overwrite an existing M1 run: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    determinism = configure_determinism(args.seed)
    device = resolve_device(args.device)
    started = time.time()

    pair_summary = json.loads(args.pair_summary.read_text(encoding="utf-8"))
    if sha256_file(args.pair_plan) != pair_summary["m1_m2"]["manifest_sha256"]:
        raise RuntimeError("M1 pair plan does not match its frozen summary")
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    stats_manifest = json.loads(args.stats_manifest.read_text(encoding="utf-8"))
    target_manifest = json.loads(args.macro_target_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok" or latent_manifest.get("partitions") != ["P1"]:
        raise RuntimeError("latent manifest is not a completed P1 cache")
    if stats_manifest.get("status") != "ok":
        raise RuntimeError("P1 latent statistics are incomplete")
    if target_manifest.get("status") != "ok" or target_manifest.get("classification") != "p1_frozen_m1_macro_targets":
        raise RuntimeError("M1 macro-target cache is not a completed full extraction")
    if stats_manifest["source"]["latent_cache_sha256"] != latent_manifest["output_h5_sha256"]:
        raise RuntimeError("P1 statistics were computed from a different latent cache")
    if sha256_file(args.stats_npz) != stats_manifest["output_npz_sha256"]:
        raise RuntimeError("P1 statistics NPZ does not match its manifest")
    if sha256_file(args.macro_target_h5) != target_manifest["output_h5_sha256"]:
        raise RuntimeError("M1 macro-target HDF5 does not match its manifest")
    if target_manifest["inputs"]["pair_plan_sha256"] != pair_summary["m1_m2"]["manifest_sha256"]:
        raise RuntimeError("M1 target cache used a different pair plan")
    if target_manifest["inputs"]["checkpoint_sha256"] != args.world_model_checkpoint_sha256:
        raise RuntimeError("M1 target cache used an unexpected world-model checkpoint")

    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_np = np.asarray(handle["latent"][:], dtype=np.float32)
    if cache_rows.ndim != 1 or latent_np.ndim != 2 or len(cache_rows) != len(latent_np):
        raise RuntimeError("invalid P1 latent cache shapes")
    if not np.all(cache_rows[1:] > cache_rows[:-1]) or not np.isfinite(latent_np).all():
        raise RuntimeError("invalid P1 latent-cache contents")

    with h5py.File(args.macro_target_h5, "r") as handle:
        train_source_global, train_target_global, train_episode, train_macro_np = load_role(
            handle, "P1_train"
        )
        val_source_global, val_target_global, val_episode, val_macro_np = load_role(
            handle, "P1_val"
        )
        macro_mean_np = np.asarray(handle["p1_train_macro_mean"][:], dtype=np.float32)
        macro_std_np = np.asarray(handle["p1_train_macro_std"][:], dtype=np.float32)

    for role, source, target, episode, macro in (
        ("P1_train", train_source_global, train_target_global, train_episode, train_macro_np),
        ("P1_val", val_source_global, val_target_global, val_episode, val_macro_np),
    ):
        info = target_manifest["roles"][role]
        if len(source) != int(info["written_pair_count"]):
            raise RuntimeError(f"M1 target count mismatch for {role}")
        if sha256_array(source) != info["source_global_rows_sha256"]:
            raise RuntimeError(f"M1 source-row hash mismatch for {role}")
        if sha256_array(target) != info["target_global_rows_sha256"]:
            raise RuntimeError(f"M1 target-row hash mismatch for {role}")
        if sha256_array(episode) != info["episode_ids_sha256"]:
            raise RuntimeError(f"M1 episode hash mismatch for {role}")
        if len(source) != int(pair_summary["m1_m2"]["pair_counts"][role]):
            raise RuntimeError(f"M1 full pair count mismatch for {role}")
        if macro.shape[1] != int(target_manifest["macro_action_dim"]):
            raise RuntimeError(f"M1 macro dimension mismatch for {role}")

    train_source = map_global_rows(cache_rows, train_source_global)
    train_target = map_global_rows(cache_rows, train_target_global)
    val_source = map_global_rows(cache_rows, val_source_global)
    val_target = map_global_rows(cache_rows, val_target_global)

    with np.load(args.stats_npz) as stats:
        latent_mean_np = np.asarray(stats["mean"], dtype=np.float32)
        latent_std_np = np.asarray(stats["std"], dtype=np.float32)
        stats_count = int(np.asarray(stats["count"]).item())
    if latent_mean_np.shape != (latent_np.shape[1],) or latent_std_np.shape != latent_mean_np.shape:
        raise RuntimeError("latent statistics dimensionality mismatch")
    if stats_count != int(stats_manifest["count"]) or np.any(latent_std_np < 1.0e-6):
        raise RuntimeError("invalid frozen latent statistics")
    if macro_mean_np.shape != (train_macro_np.shape[1],) or macro_std_np.shape != macro_mean_np.shape:
        raise RuntimeError("macro statistics dimensionality mismatch")
    if np.any(macro_std_np < 1.0e-8):
        raise RuntimeError("invalid frozen macro-target statistics")

    if args.condition == "true":
        train_label_full = np.arange(len(train_macro_np), dtype=np.int64)
        val_label_full = np.arange(len(val_macro_np), dtype=np.int64)
        train_permutation_sha256 = None
        val_permutation_sha256 = None
    else:
        train_label_full, train_permutation_sha256 = deranged_label_indices(
            len(train_macro_np), args.seed ^ 0x4D315452
        )
        val_label_full, val_permutation_sha256 = deranged_label_indices(
            len(val_macro_np), args.seed ^ 0x4D315641
        )

    train_selected, train_subset_sha256 = subset_indices(
        len(train_source), args.train_pair_limit, args.seed ^ 0x13579BDF
    )
    val_selected, val_subset_sha256 = subset_indices(
        len(val_source), args.validation_pair_limit, args.seed ^ 0x2468ACE0
    )
    train_source = train_source[train_selected]
    train_target = train_target[train_selected]
    train_label = train_label_full[train_selected]
    val_source = val_source[val_selected]
    val_target = val_target[val_selected]
    val_label = val_label_full[val_selected]

    latents = torch.from_numpy(latent_np).to(device=device, dtype=torch.float32)
    latent_mean = torch.from_numpy(latent_mean_np).to(device=device)
    latent_std = torch.from_numpy(latent_std_np).to(device=device)
    latents.sub_(latent_mean).div_(latent_std)
    train_macro = torch.from_numpy(train_macro_np).to(device=device, dtype=torch.float32)
    val_macro = torch.from_numpy(val_macro_np).to(device=device, dtype=torch.float32)
    macro_mean = torch.from_numpy(macro_mean_np).to(device=device)
    macro_std = torch.from_numpy(macro_std_np).to(device=device)
    del latent_np, train_macro_np, val_macro_np

    model = MacroInverseDynamicsMLP(
        latent_dim=int(latents.shape[1]),
        macro_dim=int(train_macro.shape[1]),
        hidden_width=args.hidden_width,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.max_epochs
    )
    epoch_rng = np.random.Generator(np.random.PCG64(args.seed ^ 0xA1D1FF05))

    history: list[dict[str, Any]] = []
    best_epoch = 0
    best_validation_loss = float("inf")
    epochs_without_improvement = 0
    for epoch in range(1, args.max_epochs + 1):
        model.train()
        order = epoch_rng.permutation(len(train_source))
        squared_error_sum = 0.0
        element_count = 0
        for start in range(0, len(order), args.batch_size):
            selected = order[start : start + args.batch_size]
            source = torch.as_tensor(train_source[selected], device=device)
            target = torch.as_tensor(train_target[selected], device=device)
            labels = torch.as_tensor(train_label[selected], device=device)
            macro_raw = train_macro.index_select(0, labels)
            macro_standardized = (macro_raw - macro_mean) / macro_std
            optimizer.zero_grad(set_to_none=True)
            prediction = model(
                latents.index_select(0, source), latents.index_select(0, target)
            )
            loss = torch.mean((prediction - macro_standardized) ** 2)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite M1 training loss")
            loss.backward()
            optimizer.step()
            squared_error_sum += float(
                (prediction.detach() - macro_standardized).square().sum().item()
            )
            element_count += prediction.numel()

        validation = evaluate(
            model,
            latents,
            val_source,
            val_target,
            val_macro,
            val_label,
            macro_mean,
            macro_std,
            batch_size=args.batch_size,
            device=device,
        )
        epoch_record = {
            "epoch": epoch,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "train_standardized_macro_mse": squared_error_sum / element_count,
            **{f"validation_{key}": value for key, value in validation.items()},
        }
        history.append(epoch_record)
        print(json.dumps(epoch_record, sort_keys=True), flush=True)

        validation_loss = validation["standardized_macro_mse"]
        if validation_loss < best_validation_loss - args.min_delta:
            best_validation_loss = validation_loss
            best_epoch = epoch
            epochs_without_improvement = 0
            atomic_torch_save(
                checkpoint_path,
                {
                    "state_dict": {
                        key: value.detach().cpu() for key, value in model.state_dict().items()
                    },
                    "latent_dim": int(latents.shape[1]),
                    "macro_dim": int(train_macro.shape[1]),
                    "hidden_width": args.hidden_width,
                    "linear_layers": LINEAR_LAYERS,
                    "activation": "Mish",
                    "condition": args.condition,
                    "training_seed": args.seed,
                    "best_epoch": best_epoch,
                    "best_validation_standardized_macro_mse": best_validation_loss,
                    "latent_mean": latent_mean.detach().cpu(),
                    "latent_std": latent_std.detach().cpu(),
                    "macro_mean": macro_mean.detach().cpu(),
                    "macro_std": macro_std.detach().cpu(),
                    "pair_plan_sha256": pair_summary["m1_m2"]["manifest_sha256"],
                    "latent_cache_sha256": latent_manifest["output_h5_sha256"],
                    "macro_target_cache_sha256": target_manifest["output_h5_sha256"],
                    "stats_npz_sha256": stats_manifest["output_npz_sha256"],
                    "world_model_checkpoint_sha256": args.world_model_checkpoint_sha256,
                },
            )
        else:
            epochs_without_improvement += 1
        scheduler.step()
        if epochs_without_improvement >= args.patience:
            break

    best_payload = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(best_payload["state_dict"])
    final_validation = evaluate(
        model,
        latents,
        val_source,
        val_target,
        val_macro,
        val_label,
        macro_mean,
        macro_std,
        batch_size=args.batch_size,
        device=device,
    )
    if abs(final_validation["standardized_macro_mse"] - best_validation_loss) > 1.0e-10:
        raise RuntimeError("reloaded M1 checkpoint does not reproduce validation loss")

    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    result = {
        "status": "ok",
        "classification": "development_smoke" if args.smoke else "m1_training",
        "method": "M1_single_macro_cycle_consistency",
        "condition": args.condition,
        "model_spec": {
            "latent_dim": int(latents.shape[1]),
            "macro_dim": int(train_macro.shape[1]),
            "input": "concatenated standardized source and Delta=25 target latents",
            "linear_layers": LINEAR_LAYERS,
            "hidden_width": args.hidden_width,
            "activation": "Mish after the first two linear layers",
            "output": "standardized frozen macro-action latent; de-standardized before scoring",
            "parameter_count": parameter_count,
        },
        "score": {
            "primary": "squared L2 residual in the original frozen macro-action latent space",
            "training_loss": "per-element MSE in P1-train-standardized macro space",
        },
        "null": {
            "kind": None if args.condition == "true" else "within-role deranged macro labels",
            "train_permutation_sha256": train_permutation_sha256,
            "validation_permutation_sha256": val_permutation_sha256,
            "fixed_points": 0 if args.condition == "permuted" else None,
        },
        "optimizer": {
            "name": "AdamW",
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "schedule": "CosineAnnealingLR",
            "batch_size": args.batch_size,
            "max_epochs": args.max_epochs,
            "early_stopping_patience": args.patience,
            "early_stopping_min_delta": args.min_delta,
        },
        "training_seed": args.seed,
        "determinism": determinism,
        "device": str(device),
        "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "runtime": {
            "python": os.sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "numpy": np.__version__,
            "h5py": h5py.__version__,
        },
        "inputs": {
            "latent_h5": str(args.latent_h5),
            "latent_cache_sha256": latent_manifest["output_h5_sha256"],
            "latent_manifest_sha256": sha256_file(args.latent_manifest),
            "pair_plan": str(args.pair_plan),
            "pair_plan_sha256": pair_summary["m1_m2"]["manifest_sha256"],
            "pair_summary_sha256": sha256_file(args.pair_summary),
            "stats_npz_sha256": stats_manifest["output_npz_sha256"],
            "stats_manifest_sha256": sha256_file(args.stats_manifest),
            "macro_target_h5": str(args.macro_target_h5),
            "macro_target_cache_sha256": target_manifest["output_h5_sha256"],
            "macro_target_manifest_sha256": sha256_file(args.macro_target_manifest),
            "world_model_checkpoint_sha256": args.world_model_checkpoint_sha256,
        },
        "data": {
            "train_pairs": len(train_source),
            "validation_pairs": len(val_source),
            "full_train_pairs": len(train_source_global),
            "full_validation_pairs": len(val_source_global),
            "train_subset_sha256": train_subset_sha256,
            "validation_subset_sha256": val_subset_sha256,
            "latent_standardization_count": stats_count,
            "macro_standardization_count": int(
                target_manifest["p1_train_macro_statistics"]["count"]
            ),
        },
        "best_epoch": best_epoch,
        "epochs_completed": len(history),
        "best_validation": final_validation,
        "elapsed_seconds": time.time() - started,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "history": history,
    }
    atomic_json(result_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def self_test() -> None:
    configure_determinism(123)
    model = MacroInverseDynamicsMLP(latent_dim=8, macro_dim=4, hidden_width=256)
    source = torch.randn(16, 8)
    target = torch.randn(16, 8)
    expected = torch.randn(16, 4)
    prediction = model(source, target)
    if prediction.shape != expected.shape or not torch.isfinite(prediction).all():
        raise RuntimeError("M1 self-test forward pass failed")
    loss = torch.mean((prediction - expected) ** 2)
    loss.backward()
    if not all(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        raise RuntimeError("M1 self-test backward pass failed")
    mapping, mapping_sha = deranged_label_indices(257, 123)
    if np.any(mapping == np.arange(len(mapping))) or len(np.unique(mapping)) != len(mapping):
        raise RuntimeError("M1 self-test derangement failed")
    print(
        json.dumps(
            {
                "status": "ok",
                "self_test": True,
                "linear_layers": LINEAR_LAYERS,
                "permutation_sha256": mapping_sha,
                "parameter_count": sum(p.numel() for p in model.parameters()),
            }
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-h5", type=Path)
    parser.add_argument("--latent-manifest", type=Path)
    parser.add_argument("--pair-plan", type=Path)
    parser.add_argument("--pair-summary", type=Path)
    parser.add_argument("--stats-npz", type=Path)
    parser.add_argument("--stats-manifest", type=Path)
    parser.add_argument("--macro-target-h5", type=Path)
    parser.add_argument("--macro-target-manifest", type=Path)
    parser.add_argument("--world-model-checkpoint-sha256")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--condition", choices=("true", "permuted"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--hidden-width", type=int, choices=(256, 512))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--max-epochs", type=int, default=50)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--min-delta", type=float, default=1.0e-8)
    parser.add_argument("--train-pair-limit", type=int)
    parser.add_argument("--validation-pair-limit", type=int)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.self_test:
        self_test()
        return
    required = (
        "latent_h5",
        "latent_manifest",
        "pair_plan",
        "pair_summary",
        "stats_npz",
        "stats_manifest",
        "macro_target_h5",
        "macro_target_manifest",
        "world_model_checkpoint_sha256",
        "output_dir",
        "condition",
        "seed",
        "hidden_width",
    )
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        raise SystemExit(f"missing required training arguments: {', '.join(missing)}")
    if args.batch_size != 256 or args.learning_rate != 3.0e-4:
        raise SystemExit("batch size and learning rate are frozen by the master protocol")
    if len(args.world_model_checkpoint_sha256) != 64:
        raise SystemExit("world-model checkpoint SHA-256 is malformed")
    if args.smoke:
        if args.train_pair_limit is None or args.validation_pair_limit is None:
            raise SystemExit("smoke mode requires both pair limits")
    elif args.train_pair_limit is not None or args.validation_pair_limit is not None:
        raise SystemExit("pair limits are permitted only for a labeled smoke run")
    train(args)


if __name__ == "__main__":
    main()
