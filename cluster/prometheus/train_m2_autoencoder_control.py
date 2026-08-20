#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch
from torch import nn

from train_m2_diffusion_head import (
    ConditionalEpsilonMLP,
    atomic_json,
    atomic_torch_save,
    configure_determinism,
    enumerate_pairs,
    map_global_rows,
    read_tsv,
    resolve_device,
    sha256_file,
    subset_pairs,
)


BOTTLENECK_DIM = 64


class ConditionalTargetAutoencoder(nn.Module):
    def __init__(self, latent_dim: int, hidden_width: int) -> None:
        super().__init__()
        if hidden_width not in {512, 1024}:
            raise ValueError("autoencoder width must inherit 512 or 1024 from M2")
        self.latent_dim = int(latent_dim)
        self.hidden_width = int(hidden_width)
        self.network = nn.Sequential(
            nn.Linear(2 * self.latent_dim, self.hidden_width),
            nn.Mish(),
            nn.Linear(self.hidden_width, self.hidden_width),
            nn.Mish(),
            nn.Linear(self.hidden_width, BOTTLENECK_DIM),
            nn.Mish(),
            nn.Linear(BOTTLENECK_DIM, self.hidden_width),
            nn.Mish(),
            nn.Linear(self.hidden_width, self.hidden_width),
            nn.Mish(),
            nn.Linear(self.hidden_width, self.hidden_width),
            nn.Mish(),
            nn.Linear(self.hidden_width, self.latent_dim),
        )

    def forward(self, source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        return self.network(torch.cat((source, target), dim=-1))


@torch.inference_mode()
def evaluate(
    model: ConditionalTargetAutoencoder,
    latents: torch.Tensor,
    source_indices: np.ndarray,
    target_indices: np.ndarray,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    squared_error_sum = 0.0
    element_count = 0
    example_count = 0
    for start in range(0, len(source_indices), batch_size):
        stop = min(start + batch_size, len(source_indices))
        source = torch.as_tensor(source_indices[start:stop], device=device)
        target = torch.as_tensor(target_indices[start:stop], device=device)
        source_latent = latents.index_select(0, source)
        target_latent = latents.index_select(0, target)
        prediction = model(source_latent, target_latent)
        if not torch.isfinite(prediction).all():
            raise RuntimeError("non-finite autoencoder validation prediction")
        squared_error_sum += float((prediction - target_latent).square().sum().item())
        element_count += prediction.numel()
        example_count += len(source)
    mse = squared_error_sum / element_count
    return {
        "standardized_target_mse": mse,
        "standardized_target_rmse": mse**0.5,
        "standardized_squared_l2_mean": squared_error_sum / example_count,
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint_path = args.output_dir / "best-checkpoint.pt"
    result_path = args.output_dir / "training-result.json"
    if checkpoint_path.exists() or result_path.exists():
        raise SystemExit(f"refusing to overwrite autoencoder run: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    determinism = configure_determinism(args.seed)
    device = resolve_device(args.device)
    started = time.time()
    pair_summary = json.loads(args.pair_summary.read_text(encoding="utf-8"))
    pair_plan_sha = sha256_file(args.pair_plan)
    if pair_plan_sha != pair_summary["m1_m2"]["manifest_sha256"]:
        raise RuntimeError("M1/M2 pair plan does not match its frozen summary")
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    stats_manifest = json.loads(args.stats_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok" or latent_manifest.get(
        "partitions"
    ) != ["P1"]:
        raise RuntimeError("latent manifest is not a completed P1 cache")
    if stats_manifest.get("status") != "ok" or stats_manifest["source"][
        "latent_cache_sha256"
    ] != latent_manifest["output_h5_sha256"]:
        raise RuntimeError("P1 statistics do not match the latent cache")
    if sha256_file(args.stats_npz) != stats_manifest["output_npz_sha256"]:
        raise RuntimeError("P1 statistics NPZ does not match its manifest")

    plan_rows = read_tsv(args.pair_plan)
    train_source_global, train_target_global, train_pair_info = enumerate_pairs(
        plan_rows, "P1_train", "true", args.seed
    )
    val_source_global, val_target_global, val_pair_info = enumerate_pairs(
        plan_rows, "P1_val", "true", args.seed
    )
    train_source_global, train_target_global, train_subset_sha = subset_pairs(
        train_source_global,
        train_target_global,
        args.train_pair_limit,
        args.seed ^ 0x13579BDF,
    )
    val_source_global, val_target_global, val_subset_sha = subset_pairs(
        val_source_global,
        val_target_global,
        args.validation_pair_limit,
        args.seed ^ 0x2468ACE0,
    )

    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_np = np.asarray(handle["latent"][:], dtype=np.float32)
    if cache_rows.ndim != 1 or latent_np.ndim != 2 or len(cache_rows) != len(latent_np):
        raise RuntimeError("invalid P1 latent-cache shapes")
    if not np.all(cache_rows[1:] > cache_rows[:-1]) or not np.isfinite(latent_np).all():
        raise RuntimeError("invalid P1 latent-cache contents")
    train_source = map_global_rows(cache_rows, train_source_global)
    train_target = map_global_rows(cache_rows, train_target_global)
    val_source = map_global_rows(cache_rows, val_source_global)
    val_target = map_global_rows(cache_rows, val_target_global)

    with np.load(args.stats_npz) as stats:
        mean_np = np.asarray(stats["mean"], dtype=np.float32)
        std_np = np.asarray(stats["std"], dtype=np.float32)
        stats_count = int(np.asarray(stats["count"]).item())
    if mean_np.shape != (latent_np.shape[1],) or std_np.shape != mean_np.shape:
        raise RuntimeError("latent statistics dimensionality mismatch")
    if stats_count != int(stats_manifest["count"]) or np.any(std_np < 1.0e-6):
        raise RuntimeError("invalid frozen latent statistics")

    latents = torch.from_numpy(latent_np).to(device=device, dtype=torch.float32)
    mean = torch.from_numpy(mean_np).to(device)
    std = torch.from_numpy(std_np).to(device)
    latents.sub_(mean).div_(std)
    del latent_np

    model = ConditionalTargetAutoencoder(
        latent_dim=int(latents.shape[1]), hidden_width=args.hidden_width
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.max_epochs
    )
    epoch_rng = np.random.Generator(np.random.PCG64(args.seed ^ 0xAE00FF05))
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
            source_index = torch.as_tensor(train_source[selected], device=device)
            target_index = torch.as_tensor(train_target[selected], device=device)
            source_latent = latents.index_select(0, source_index)
            target_latent = latents.index_select(0, target_index)
            optimizer.zero_grad(set_to_none=True)
            prediction = model(source_latent, target_latent)
            loss = torch.mean((prediction - target_latent) ** 2)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite autoencoder training loss")
            loss.backward()
            optimizer.step()
            squared_error_sum += float(
                (prediction.detach() - target_latent).square().sum().item()
            )
            element_count += prediction.numel()

        validation = evaluate(
            model,
            latents,
            val_source,
            val_target,
            batch_size=args.batch_size,
            device=device,
        )
        epoch_record = {
            "epoch": epoch,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "train_standardized_target_mse": squared_error_sum / element_count,
            **{f"validation_{key}": value for key, value in validation.items()},
        }
        history.append(epoch_record)
        print(json.dumps(epoch_record, sort_keys=True), flush=True)
        validation_loss = validation["standardized_target_mse"]
        if validation_loss < best_validation_loss - args.min_delta:
            best_validation_loss = validation_loss
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
                    "hidden_width": args.hidden_width,
                    "bottleneck_dim": BOTTLENECK_DIM,
                    "condition": "plain_autoencoder_control",
                    "training_seed": args.seed,
                    "best_epoch": best_epoch,
                    "best_validation_standardized_target_mse": best_validation_loss,
                    "latent_mean": mean.detach().cpu(),
                    "latent_std": std.detach().cpu(),
                    "pair_plan_sha256": pair_plan_sha,
                    "latent_cache_sha256": latent_manifest["output_h5_sha256"],
                    "stats_npz_sha256": stats_manifest["output_npz_sha256"],
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
        batch_size=args.batch_size,
        device=device,
    )
    if (
        abs(
            final_validation["standardized_target_mse"] - best_validation_loss
        )
        > 1.0e-10
    ):
        raise RuntimeError("reloaded autoencoder checkpoint does not reproduce validation")

    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    m2_reference = ConditionalEpsilonMLP(
        latent_dim=int(latents.shape[1]), hidden_width=args.hidden_width
    )
    m2_parameter_count = sum(parameter.numel() for parameter in m2_reference.parameters())
    result = {
        "status": "ok",
        "classification": (
            "development_smoke" if args.smoke else "m2_autoencoder_control_training"
        ),
        "method": "M2_plain_autoencoder_reconstruction_control",
        "condition": "plain_autoencoder_control",
        "training_seed": args.seed,
        "model_spec": {
            "latent_dim": int(latents.shape[1]),
            "hidden_width": args.hidden_width,
            "bottleneck_dim": BOTTLENECK_DIM,
            "linear_dimensions": [
                2 * int(latents.shape[1]),
                args.hidden_width,
                args.hidden_width,
                BOTTLENECK_DIM,
                args.hidden_width,
                args.hidden_width,
                args.hidden_width,
                int(latents.shape[1]),
            ],
            "activation": "Mish after every linear layer except output",
            "input": "clean standardized source and target latents",
            "output": "reconstructed standardized target latent",
            "parameter_count": parameter_count,
            "matched_m2_parameter_count": m2_parameter_count,
            "parameter_count_ratio_to_m2": parameter_count / m2_parameter_count,
        },
        "score": "squared L2 target-reconstruction residual in standardized latent coordinates",
        "optimizer": {
            "name": "AdamW",
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "batch_size": args.batch_size,
            "schedule": "CosineAnnealingLR",
            "max_epochs": args.max_epochs,
            "early_stopping_patience": args.patience,
            "early_stopping_min_delta": args.min_delta,
        },
        "best_epoch": best_epoch,
        "epochs_completed": len(history),
        "best_validation": final_validation,
        "history": history,
        "data": {
            "train_pairs": len(train_source),
            "validation_pairs": len(val_source),
            "full_train_pair_info": train_pair_info,
            "full_validation_pair_info": val_pair_info,
            "train_subset_sha256": train_subset_sha,
            "validation_subset_sha256": val_subset_sha,
            "latent_standardization_count": stats_count,
        },
        "inputs": {
            "latent_h5": str(args.latent_h5),
            "latent_cache_sha256": latent_manifest["output_h5_sha256"],
            "latent_manifest_sha256": sha256_file(args.latent_manifest),
            "pair_plan": str(args.pair_plan),
            "pair_plan_sha256": pair_plan_sha,
            "pair_summary_sha256": sha256_file(args.pair_summary),
            "stats_npz_sha256": stats_manifest["output_npz_sha256"],
            "stats_manifest_sha256": sha256_file(args.stats_manifest),
        },
        "determinism": determinism,
        "device": str(device),
        "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "runtime": {
            "python_torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "numpy": np.__version__,
            "h5py": h5py.__version__,
        },
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(result_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def self_test() -> None:
    torch.manual_seed(123)
    model = ConditionalTargetAutoencoder(latent_dim=8, hidden_width=512)
    source = torch.randn(16, 8)
    target = torch.randn(16, 8)
    output = model(source, target)
    if output.shape != target.shape or not torch.isfinite(output).all():
        raise RuntimeError("autoencoder self-test forward pass failed")
    loss = torch.mean((output - target) ** 2)
    loss.backward()
    if not all(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        raise RuntimeError("autoencoder self-test backward pass failed")
    print(
        json.dumps(
            {
                "status": "ok",
                "self_test": True,
                "bottleneck_dim": BOTTLENECK_DIM,
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
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--hidden-width", type=int, choices=(512, 1024))
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
        "output_dir",
        "seed",
        "hidden_width",
    )
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        raise SystemExit(f"missing required training arguments: {', '.join(missing)}")
    if args.batch_size != 256 or args.learning_rate != 3.0e-4:
        raise SystemExit("batch size and learning rate are frozen by the master protocol")
    if args.smoke:
        if args.train_pair_limit is None or args.validation_pair_limit is None:
            raise SystemExit("smoke mode requires both pair limits")
    elif args.train_pair_limit is not None or args.validation_pair_limit is not None:
        raise SystemExit("pair limits are permitted only for a labeled smoke run")
    train(args)


if __name__ == "__main__":
    main()
