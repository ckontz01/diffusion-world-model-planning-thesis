#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch
from torch import nn


MODEL_SPEC = {
    "feature_map": "concat(z_i, z_j, z_i-z_j, abs(z_i-z_j))",
    "hidden_layers": 2,
    "hidden_width": 256,
    "activation": "SiLU",
    "output": "Softplus scalar",
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
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
    }


def pair_features(z_i: torch.Tensor, z_j: torch.Tensor) -> torch.Tensor:
    difference = z_i - z_j
    return torch.cat((z_i, z_j, difference, difference.abs()), dim=-1)


class TemporalPairHead(nn.Module):
    def __init__(self, latent_dim: int) -> None:
        super().__init__()
        self.latent_dim = int(latent_dim)
        self.network = nn.Sequential(
            nn.Linear(4 * self.latent_dim, 256),
            nn.SiLU(),
            nn.Linear(256, 256),
            nn.SiLU(),
            nn.Linear(256, 1),
            nn.Softplus(),
        )

    def forward(self, z_i: torch.Tensor, z_j: torch.Tensor) -> torch.Tensor:
        return self.network(pair_features(z_i, z_j)).squeeze(-1)


def map_global_rows(cache_rows: np.ndarray, requested: np.ndarray) -> np.ndarray:
    positions = np.searchsorted(cache_rows, requested)
    if np.any(positions >= cache_rows.size):
        raise RuntimeError("requested global row is outside the latent cache")
    if not np.array_equal(cache_rows[positions], requested):
        missing = requested[cache_rows[positions] != requested][:10]
        raise RuntimeError(f"requested rows are absent from the P1 cache: {missing}")
    return positions.astype(np.int64, copy=False)


def load_pair_manifest(path: Path) -> dict[str, np.ndarray]:
    roles: list[str] = []
    deltas: list[int] = []
    first_rows: list[int] = []
    second_rows: list[int] = []
    swaps: list[bool] = []
    with gzip.open(path, "rt", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        required = {
            "p1_role",
            "delta",
            "source_row",
            "target_row",
            "selection_sha256",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise RuntimeError(f"invalid M3 pair manifest schema: {path}")
        for row in reader:
            source_row = int(row["source_row"])
            target_row = int(row["target_row"])
            digest = row["selection_sha256"]
            if len(digest) != 64:
                raise RuntimeError("invalid selection SHA-256 in M3 pair manifest")
            swap = bool(int(digest[-1], 16) & 1)
            roles.append(row["p1_role"])
            deltas.append(int(row["delta"]))
            first_rows.append(target_row if swap else source_row)
            second_rows.append(source_row if swap else target_row)
            swaps.append(swap)
    if not roles:
        raise RuntimeError("empty M3 pair manifest")
    return {
        "role": np.asarray(roles),
        "delta": np.asarray(deltas, dtype=np.int64),
        "first_global_row": np.asarray(first_rows, dtype=np.int64),
        "second_global_row": np.asarray(second_rows, dtype=np.int64),
        "swapped": np.asarray(swaps, dtype=np.bool_),
    }


def resolve_device(raw: str) -> torch.device:
    if raw == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(raw)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


def evaluate(
    model: TemporalPairHead,
    latents: torch.Tensor,
    first_indices: np.ndarray,
    second_indices: np.ndarray,
    deltas: np.ndarray,
    *,
    target_scale: float,
    batch_size: int,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    loss_sum = 0.0
    squared_error_sum = 0.0
    count = 0
    loss_fn = nn.SmoothL1Loss(reduction="sum")
    with torch.inference_mode():
        for start in range(0, len(deltas), batch_size):
            end = min(start + batch_size, len(deltas))
            first = torch.as_tensor(first_indices[start:end], device=device)
            second = torch.as_tensor(second_indices[start:end], device=device)
            target_steps = torch.as_tensor(
                deltas[start:end], dtype=torch.float32, device=device
            )
            target = target_steps / target_scale
            prediction = model(
                latents.index_select(0, first), latents.index_select(0, second)
            )
            if not torch.isfinite(prediction).all():
                raise RuntimeError("non-finite M3 validation prediction")
            loss_sum += float(loss_fn(prediction, target).item())
            squared_error_sum += float(
                ((prediction * target_scale - target_steps) ** 2).sum().item()
            )
            count += end - start
    return {
        "smooth_l1": loss_sum / count,
        "rmse_steps": (squared_error_sum / count) ** 0.5,
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    checkpoint_path = output_dir / "best-checkpoint.pt"
    result_path = output_dir / "training-result.json"
    if checkpoint_path.exists() or result_path.exists():
        raise SystemExit(f"refusing to overwrite an existing M3 run: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    determinism = configure_determinism(args.seed)
    device = resolve_device(args.device)
    pair_summary = json.loads(args.pair_summary.read_text(encoding="utf-8"))
    pair_manifest_sha256 = sha256_file(args.pair_manifest)
    if pair_manifest_sha256 != pair_summary["m3"]["manifest_sha256"]:
        raise RuntimeError("M3 pair manifest does not match its frozen summary")
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok" or latent_manifest.get("partitions") != [
        "P1"
    ]:
        raise RuntimeError("latent manifest is not a completed P1 cache")
    if args.latent_h5.stat().st_size != int(latent_manifest["output_h5_bytes"]):
        raise RuntimeError("P1 latent-cache byte size differs from its manifest")

    started = time.time()
    pairs = load_pair_manifest(args.pair_manifest)
    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_np = np.asarray(handle["latent"][:], dtype=np.float32)
    if cache_rows.ndim != 1 or latent_np.ndim != 2:
        raise RuntimeError("invalid P1 latent-cache shapes")
    if len(cache_rows) != len(latent_np) or not np.all(cache_rows[1:] > cache_rows[:-1]):
        raise RuntimeError("P1 latent-cache row index is not strictly increasing")
    if not np.isfinite(latent_np).all():
        raise RuntimeError("P1 latent cache contains non-finite values")

    first_cache = map_global_rows(cache_rows, pairs["first_global_row"])
    second_cache = map_global_rows(cache_rows, pairs["second_global_row"])
    train_mask = pairs["role"] == "P1_train"
    val_mask = pairs["role"] == "P1_val"
    if int(train_mask.sum()) != 100_000 or int(val_mask.sum()) != 10_000:
        raise RuntimeError("M3 manifest does not contain the frozen 100k/10k split")
    train_first = first_cache[train_mask]
    train_second = second_cache[train_mask]
    train_delta_true = pairs["delta"][train_mask]
    val_first = first_cache[val_mask]
    val_second = second_cache[val_mask]
    val_delta = pairs["delta"][val_mask]

    label_permutation_sha256 = None
    if args.condition == "shuffled":
        permutation_rng = np.random.Generator(
            np.random.PCG64(args.seed ^ 0x5A17D1FF)
        )
        label_permutation = permutation_rng.permutation(len(train_delta_true))
        label_permutation_sha256 = hashlib.sha256(
            label_permutation.astype(np.int64, copy=False).tobytes()
        ).hexdigest()
        train_delta = train_delta_true[label_permutation]
    else:
        train_delta = train_delta_true.copy()

    latents = torch.from_numpy(latent_np).to(device=device, dtype=torch.float32)
    del latent_np
    model = TemporalPairHead(latent_dim=int(latents.shape[1])).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.max_epochs
    )
    loss_fn = nn.SmoothL1Loss(reduction="sum")
    epoch_rng = np.random.Generator(np.random.PCG64(args.seed ^ 0xE90C4A11))

    history: list[dict[str, Any]] = []
    best_epoch = 0
    best_validation_loss = float("inf")
    epochs_without_improvement = 0
    for epoch in range(1, args.max_epochs + 1):
        model.train()
        order = epoch_rng.permutation(len(train_delta))
        train_loss_sum = 0.0
        train_squared_error_sum = 0.0
        train_count = 0
        for start in range(0, len(order), args.batch_size):
            batch_order = order[start : start + args.batch_size]
            first = torch.as_tensor(train_first[batch_order], device=device)
            second = torch.as_tensor(train_second[batch_order], device=device)
            target_steps = torch.as_tensor(
                train_delta[batch_order], dtype=torch.float32, device=device
            )
            target = target_steps / args.target_scale
            optimizer.zero_grad(set_to_none=True)
            prediction = model(
                latents.index_select(0, first), latents.index_select(0, second)
            )
            loss = loss_fn(prediction, target) / len(batch_order)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite M3 training loss")
            loss.backward()
            optimizer.step()
            train_loss_sum += float(loss.item()) * len(batch_order)
            train_squared_error_sum += float(
                ((prediction.detach() * args.target_scale - target_steps) ** 2)
                .sum()
                .item()
            )
            train_count += len(batch_order)

        validation = evaluate(
            model,
            latents,
            val_first,
            val_second,
            val_delta,
            target_scale=args.target_scale,
            batch_size=args.batch_size,
            device=device,
        )
        epoch_record = {
            "epoch": epoch,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "train_smooth_l1": train_loss_sum / train_count,
            "train_rmse_steps": (train_squared_error_sum / train_count) ** 0.5,
            "validation_smooth_l1": validation["smooth_l1"],
            "validation_rmse_steps": validation["rmse_steps"],
        }
        history.append(epoch_record)
        print(json.dumps(epoch_record, sort_keys=True), flush=True)

        if validation["smooth_l1"] < best_validation_loss - args.min_delta:
            best_validation_loss = validation["smooth_l1"]
            best_epoch = epoch
            epochs_without_improvement = 0
            atomic_torch_save(
                checkpoint_path,
                {
                    "state_dict": {
                        key: value.detach().cpu()
                        for key, value in model.state_dict().items()
                    },
                    "latent_dim": int(latents.shape[1]),
                    "model_spec": MODEL_SPEC,
                    "target_scale": args.target_scale,
                    "condition": args.condition,
                    "training_seed": args.seed,
                    "best_epoch": best_epoch,
                    "best_validation_smooth_l1": best_validation_loss,
                    "pair_manifest_sha256": pair_manifest_sha256,
                    "latent_cache_sha256": latent_manifest["output_h5_sha256"],
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
        val_first,
        val_second,
        val_delta,
        target_scale=args.target_scale,
        batch_size=args.batch_size,
        device=device,
    )
    if abs(final_validation["smooth_l1"] - best_validation_loss) > 1.0e-10:
        raise RuntimeError("reloaded best checkpoint does not reproduce validation loss")

    train_delta_counts = Counter(int(value) for value in train_delta_true)
    val_delta_counts = Counter(int(value) for value in val_delta)
    result = {
        "status": "ok",
        "method": "M3_temporal_reachability_head",
        "condition": args.condition,
        "model_spec": MODEL_SPEC,
        "target": "absolute within-episode separation divided by 40",
        "target_scale": args.target_scale,
        "loss": "SmoothL1",
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
        },
        "inputs": {
            "latent_h5": str(args.latent_h5),
            "latent_manifest": str(args.latent_manifest),
            "latent_manifest_sha256": sha256_file(args.latent_manifest),
            "latent_cache_sha256": latent_manifest["output_h5_sha256"],
            "pair_manifest": str(args.pair_manifest),
            "pair_manifest_sha256": pair_manifest_sha256,
            "pair_summary": str(args.pair_summary),
            "pair_summary_sha256": sha256_file(args.pair_summary),
        },
        "data": {
            "latent_rows": int(latents.shape[0]),
            "latent_dim": int(latents.shape[1]),
            "train_pairs": int(train_mask.sum()),
            "validation_pairs": int(val_mask.sum()),
            "train_delta_counts": {
                str(key): value for key, value in sorted(train_delta_counts.items())
            },
            "validation_delta_counts": {
                str(key): value for key, value in sorted(val_delta_counts.items())
            },
            "input_order_swapped": {
                "train": int(pairs["swapped"][train_mask].sum()),
                "validation": int(pairs["swapped"][val_mask].sum()),
                "rule": "least-significant bit of selection_sha256",
            },
            "label_permutation_sha256": label_permutation_sha256,
            "validation_labels_permuted": False,
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
    first = torch.randn(16, 8)
    second = torch.randn(16, 8)
    model = TemporalPairHead(latent_dim=8)
    output = model(first, second)
    if output.shape != (16,) or not torch.isfinite(output).all() or (output < 0).any():
        raise RuntimeError("M3 self-test forward pass failed")
    loss = nn.SmoothL1Loss()(output, torch.rand(16))
    loss.backward()
    if not all(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        raise RuntimeError("M3 self-test backward pass failed")
    print(json.dumps({"status": "ok", "self_test": True, "model_spec": MODEL_SPEC}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-h5", type=Path)
    parser.add_argument("--latent-manifest", type=Path)
    parser.add_argument("--pair-manifest", type=Path)
    parser.add_argument("--pair-summary", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--condition", choices=("true", "shuffled"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--target-scale", type=float, default=40.0)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--min-delta", type=float, default=1.0e-8)
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
        "pair_manifest",
        "pair_summary",
        "output_dir",
        "condition",
        "seed",
    )
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        raise SystemExit(f"missing required training arguments: {', '.join(missing)}")
    if args.target_scale != 40.0:
        raise SystemExit("the frozen M3 target scale is exactly 40")
    if args.batch_size != 256 or args.learning_rate != 3.0e-4:
        raise SystemExit("batch size and learning rate are frozen by the master protocol")
    train(args)


if __name__ == "__main__":
    main()
