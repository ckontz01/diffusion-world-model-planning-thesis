#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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


SIGMA_GRID = (0.1, 0.25, 0.5, 0.75, 1.0)
SIGMA_EMBED_DIM = 64
HIDDEN_LAYERS = 4
VALIDATION_NOISE_SEED = 20260728


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


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise RuntimeError(f"empty TSV: {path}")
    return rows


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


def resolve_device(raw: str) -> torch.device:
    if raw == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(raw)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


class LogSigmaEmbedding(nn.Module):
    def __init__(self, embedding_dim: int = SIGMA_EMBED_DIM) -> None:
        super().__init__()
        if embedding_dim % 2 != 0:
            raise ValueError("sigma embedding dimension must be even")
        frequencies = torch.logspace(
            0.0, 2.0, embedding_dim // 2, dtype=torch.float32
        )
        self.register_buffer("frequencies", frequencies, persistent=True)

    def forward(self, sigma: torch.Tensor) -> torch.Tensor:
        angles = sigma.clamp_min(1.0e-12).log().unsqueeze(-1)
        angles = angles * self.frequencies.unsqueeze(0) * (2.0 * math.pi)
        return torch.cat((angles.sin(), angles.cos()), dim=-1)


class ConditionalEpsilonMLP(nn.Module):
    def __init__(self, latent_dim: int, hidden_width: int) -> None:
        super().__init__()
        if hidden_width not in {512, 1024}:
            raise ValueError("M2 hidden width must be 512 or 1024")
        self.latent_dim = int(latent_dim)
        self.hidden_width = int(hidden_width)
        self.sigma_embedding = LogSigmaEmbedding(SIGMA_EMBED_DIM)
        layers: list[nn.Module] = []
        input_dim = 2 * self.latent_dim + SIGMA_EMBED_DIM
        for layer_index in range(HIDDEN_LAYERS):
            layers.append(
                nn.Linear(input_dim if layer_index == 0 else hidden_width, hidden_width)
            )
            layers.append(nn.Mish())
        layers.append(nn.Linear(hidden_width, self.latent_dim))
        self.network = nn.Sequential(*layers)

    def forward(
        self, noisy_target: torch.Tensor, sigma: torch.Tensor, source: torch.Tensor
    ) -> torch.Tensor:
        embedded_sigma = self.sigma_embedding(sigma)
        return self.network(torch.cat((noisy_target, source, embedded_sigma), dim=-1))


def map_global_rows(cache_rows: np.ndarray, requested: np.ndarray) -> np.ndarray:
    positions = np.searchsorted(cache_rows, requested)
    if np.any(positions >= cache_rows.size):
        raise RuntimeError("requested global row lies outside the P1 latent cache")
    if not np.array_equal(cache_rows[positions], requested):
        missing = requested[cache_rows[positions] != requested][:10]
        raise RuntimeError(f"requested rows are absent from P1 cache: {missing}")
    return positions.astype(np.int64, copy=False)


def hash_u64(payload: str) -> int:
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def null_episode_map(
    rows: list[dict[str, str]],
    role: str,
    seed: int,
    dataset_hash_namespace: str,
) -> tuple[dict[int, int], str]:
    episode_ids = sorted(int(row["episode_id"]) for row in rows if row["p1_role"] == role)
    if len(episode_ids) < 2:
        raise RuntimeError(f"M2 null requires at least two episodes in {role}")
    ordered = sorted(
        episode_ids,
        key=lambda episode_id: hash_u64(
            f"{dataset_hash_namespace}\0{seed}\0m2_null_episode_order\0{role}\0{episode_id}"
        ),
    )
    mapping = {
        episode_id: ordered[(index + 1) % len(ordered)]
        for index, episode_id in enumerate(ordered)
    }
    if any(source == target for target, source in mapping.items()):
        raise RuntimeError("M2 null episode mapping is not a derangement")
    serialized = "\n".join(f"{target}\t{mapping[target]}" for target in sorted(mapping))
    return mapping, hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def enumerate_pairs(
    rows: list[dict[str, str]],
    role: str,
    condition: str,
    seed: int,
    dataset_hash_namespace: str = "pusht_expert_train",
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    role_rows = sorted(
        (row for row in rows if row["p1_role"] == role),
        key=lambda row: int(row["episode_id"]),
    )
    if not role_rows:
        raise RuntimeError(f"pair plan contains no rows for {role}")
    by_episode = {int(row["episode_id"]): row for row in role_rows}
    mapping: dict[int, int] | None = None
    mapping_sha256 = None
    if condition == "mismatched":
        mapping, mapping_sha256 = null_episode_map(
            rows, role, seed, dataset_hash_namespace
        )

    source_parts: list[np.ndarray] = []
    target_parts: list[np.ndarray] = []
    for row in role_rows:
        episode_id = int(row["episode_id"])
        pair_count = int(row["pair_count"])
        target = np.arange(
            int(row["target_start_row"]),
            int(row["target_end_exclusive"]),
            dtype=np.int64,
        )
        if target.size != pair_count:
            raise RuntimeError(f"target pair count mismatch for episode {episode_id}")
        if condition == "true":
            source = np.arange(
                int(row["source_start_row"]),
                int(row["source_end_exclusive"]),
                dtype=np.int64,
            )
        else:
            assert mapping is not None
            source_episode = mapping[episode_id]
            source_row = by_episode[source_episode]
            source_pair_count = int(source_row["pair_count"])
            offset = hash_u64(
                f"{dataset_hash_namespace}\0{seed}\0m2_null_offset\0{role}\0{episode_id}"
            ) % source_pair_count
            source = int(source_row["source_start_row"]) + (
                np.arange(pair_count, dtype=np.int64) + offset
            ) % source_pair_count
        if source.size != pair_count:
            raise RuntimeError(f"source pair count mismatch for episode {episode_id}")
        source_parts.append(source)
        target_parts.append(target)

    source_rows = np.concatenate(source_parts)
    target_rows = np.concatenate(target_parts)
    return source_rows, target_rows, {
        "role": role,
        "pairs": int(source_rows.size),
        "null_episode_mapping_sha256": mapping_sha256,
        "null_hash_namespace": (
            dataset_hash_namespace if condition == "mismatched" else None
        ),
    }


def subset_pairs(
    first: np.ndarray,
    second: np.ndarray,
    limit: int | None,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, str | None]:
    if limit is None or limit >= len(first):
        return first, second, None
    rng = np.random.Generator(np.random.PCG64(seed))
    selected = np.sort(rng.choice(len(first), size=limit, replace=False))
    return (
        first[selected],
        second[selected],
        hashlib.sha256(selected.astype(np.int64, copy=False).tobytes()).hexdigest(),
    )


def validation_sigma_indices(count: int) -> np.ndarray:
    indices = np.arange(count, dtype=np.int64) % len(SIGMA_GRID)
    rng = np.random.Generator(np.random.PCG64(VALIDATION_NOISE_SEED))
    rng.shuffle(indices)
    return indices


def evaluate(
    model: ConditionalEpsilonMLP,
    latents: torch.Tensor,
    source_indices: np.ndarray,
    target_indices: np.ndarray,
    sigma_indices: np.ndarray,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    sigma_grid = torch.tensor(SIGMA_GRID, dtype=torch.float32, device=device)
    generator = torch.Generator(device=device).manual_seed(VALIDATION_NOISE_SEED)
    squared_error_sum = 0.0
    count = 0
    element_count = 0
    with torch.inference_mode():
        for start in range(0, len(source_indices), batch_size):
            end = min(start + batch_size, len(source_indices))
            source = torch.as_tensor(source_indices[start:end], device=device)
            target = torch.as_tensor(target_indices[start:end], device=device)
            sigma_index = torch.as_tensor(sigma_indices[start:end], device=device)
            sigma = sigma_grid.index_select(0, sigma_index)
            target_latent = latents.index_select(0, target)
            source_latent = latents.index_select(0, source)
            epsilon = torch.randn(
                target_latent.shape,
                generator=generator,
                device=device,
                dtype=target_latent.dtype,
            )
            prediction = model(
                target_latent + sigma.unsqueeze(-1) * epsilon,
                sigma,
                source_latent,
            )
            if not torch.isfinite(prediction).all():
                raise RuntimeError("non-finite M2 validation prediction")
            squared_error_sum += float(((prediction - epsilon) ** 2).sum().item())
            count += end - start
            element_count += prediction.numel()
    return {
        "epsilon_mse": squared_error_sum / element_count,
        "epsilon_rmse": (squared_error_sum / element_count) ** 0.5,
        "pairs": count,
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint_path = args.output_dir / "best-checkpoint.pt"
    result_path = args.output_dir / "training-result.json"
    if checkpoint_path.exists() or result_path.exists():
        raise SystemExit(f"refusing to overwrite an existing M2 run: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    determinism = configure_determinism(args.seed)
    device = resolve_device(args.device)
    pair_summary = json.loads(args.pair_summary.read_text(encoding="utf-8"))
    pair_plan_sha256 = sha256_file(args.pair_plan)
    if pair_plan_sha256 != pair_summary["m1_m2"]["manifest_sha256"]:
        raise RuntimeError("M1/M2 pair plan does not match its frozen summary")
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    stats_manifest = json.loads(args.stats_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok" or latent_manifest.get("partitions") != [
        "P1"
    ]:
        raise RuntimeError("latent manifest is not a completed P1 cache")
    if stats_manifest.get("status") != "ok":
        raise RuntimeError("P1 latent statistics are incomplete")
    if stats_manifest["source"]["latent_cache_sha256"] != latent_manifest[
        "output_h5_sha256"
    ]:
        raise RuntimeError("P1 statistics were computed from a different latent cache")
    if sha256_file(args.stats_npz) != stats_manifest["output_npz_sha256"]:
        raise RuntimeError("P1 statistics NPZ does not match its manifest")

    started = time.time()
    plan_rows = read_tsv(args.pair_plan)
    train_source_global, train_target_global, train_pair_info = enumerate_pairs(
        plan_rows,
        "P1_train",
        args.condition,
        args.seed,
        args.dataset_hash_namespace,
    )
    val_source_global, val_target_global, val_pair_info = enumerate_pairs(
        plan_rows,
        "P1_val",
        args.condition,
        args.seed,
        args.dataset_hash_namespace,
    )
    train_source_global, train_target_global, train_subset_sha256 = subset_pairs(
        train_source_global,
        train_target_global,
        args.train_pair_limit,
        args.seed ^ 0x13579BDF,
    )
    val_source_global, val_target_global, val_subset_sha256 = subset_pairs(
        val_source_global,
        val_target_global,
        args.validation_pair_limit,
        args.seed ^ 0x2468ACE0,
    )

    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_np = np.asarray(handle["latent"][:], dtype=np.float32)
    if cache_rows.ndim != 1 or latent_np.ndim != 2:
        raise RuntimeError("invalid P1 latent cache shapes")
    if len(cache_rows) != len(latent_np) or not np.all(cache_rows[1:] > cache_rows[:-1]):
        raise RuntimeError("P1 latent-cache row index is not strictly increasing")
    if not np.isfinite(latent_np).all():
        raise RuntimeError("P1 latent cache contains non-finite values")
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
    mean = torch.from_numpy(mean_np).to(device=device)
    std = torch.from_numpy(std_np).to(device=device)
    latents.sub_(mean).div_(std)
    del latent_np

    model = ConditionalEpsilonMLP(
        latent_dim=int(latents.shape[1]), hidden_width=args.hidden_width
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.max_epochs
    )
    sigma_grid = torch.tensor(SIGMA_GRID, dtype=torch.float32, device=device)
    validation_sigmas = validation_sigma_indices(len(val_source))
    epoch_rng = np.random.Generator(np.random.PCG64(args.seed ^ 0xA2D1FF05))
    diffusion_generator = torch.Generator(device=device).manual_seed(
        args.seed ^ 0x4D3200D5
    )

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
            target_latent = latents.index_select(0, target)
            source_latent = latents.index_select(0, source)
            sigma_index = torch.randint(
                len(SIGMA_GRID),
                (len(selected),),
                generator=diffusion_generator,
                device=device,
            )
            sigma = sigma_grid.index_select(0, sigma_index)
            epsilon = torch.randn(
                target_latent.shape,
                generator=diffusion_generator,
                device=device,
                dtype=target_latent.dtype,
            )
            optimizer.zero_grad(set_to_none=True)
            prediction = model(
                target_latent + sigma.unsqueeze(-1) * epsilon,
                sigma,
                source_latent,
            )
            loss = torch.mean((prediction - epsilon) ** 2)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite M2 training loss")
            loss.backward()
            optimizer.step()
            squared_error_sum += float(((prediction.detach() - epsilon) ** 2).sum().item())
            element_count += prediction.numel()

        validation = evaluate(
            model,
            latents,
            val_source,
            val_target,
            validation_sigmas,
            batch_size=args.batch_size,
            device=device,
        )
        epoch_record = {
            "epoch": epoch,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "train_epsilon_mse": squared_error_sum / element_count,
            "validation_epsilon_mse": validation["epsilon_mse"],
            "validation_epsilon_rmse": validation["epsilon_rmse"],
        }
        history.append(epoch_record)
        print(json.dumps(epoch_record, sort_keys=True), flush=True)

        if validation["epsilon_mse"] < best_validation_loss - args.min_delta:
            best_validation_loss = validation["epsilon_mse"]
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
                    "hidden_layers": HIDDEN_LAYERS,
                    "sigma_embedding_dim": SIGMA_EMBED_DIM,
                    "sigma_grid": SIGMA_GRID,
                    "condition": args.condition,
                    "training_seed": args.seed,
                    "best_epoch": best_epoch,
                    "best_validation_epsilon_mse": best_validation_loss,
                    "latent_mean": mean.detach().cpu(),
                    "latent_std": std.detach().cpu(),
                    "pair_plan_sha256": pair_plan_sha256,
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
        validation_sigmas,
        batch_size=args.batch_size,
        device=device,
    )
    if abs(final_validation["epsilon_mse"] - best_validation_loss) > 1.0e-10:
        raise RuntimeError("reloaded M2 checkpoint does not reproduce validation loss")

    sigma_counts = Counter(int(value) for value in validation_sigmas)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    result = {
        "status": "ok",
        "classification": "development_smoke" if args.smoke else "m2_training",
        "method": "M2_conditional_epsilon_prediction",
        "condition": args.condition,
        "model_spec": {
            "latent_dim": int(latents.shape[1]),
            "input": "noisy standardized target + clean standardized source + log-sigma embedding",
            "sigma_embedding": "64D fixed log-spaced sinusoidal",
            "hidden_layers": HIDDEN_LAYERS,
            "hidden_width": args.hidden_width,
            "activation": "Mish",
            "output": "linear epsilon prediction",
            "parameter_count": parameter_count,
        },
        "diffusion": {
            "training_target": "epsilon",
            "training_sigma_distribution": "uniform discrete",
            "sigma_grid": list(SIGMA_GRID),
            "validation_noise_seed": VALIDATION_NOISE_SEED,
            "validation_sigma_counts": {
                str(SIGMA_GRID[key]): value for key, value in sorted(sigma_counts.items())
            },
            "edm_preconditioning": False,
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
            "pair_plan_sha256": pair_plan_sha256,
            "pair_summary_sha256": sha256_file(args.pair_summary),
            "stats_npz_sha256": stats_manifest["output_npz_sha256"],
            "stats_manifest_sha256": sha256_file(args.stats_manifest),
        },
        "data": {
            "train_pairs": len(train_source),
            "validation_pairs": len(val_source),
            "full_train_pair_info": train_pair_info,
            "full_validation_pair_info": val_pair_info,
            "train_subset_sha256": train_subset_sha256,
            "validation_subset_sha256": val_subset_sha256,
            "latent_standardization_count": stats_count,
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
    model = ConditionalEpsilonMLP(latent_dim=8, hidden_width=512)
    source = torch.randn(16, 8)
    target = torch.randn(16, 8)
    sigma = torch.tensor(SIGMA_GRID * 4, dtype=torch.float32)[:16]
    epsilon = torch.randn_like(target)
    output = model(target + sigma.unsqueeze(-1) * epsilon, sigma, source)
    if output.shape != target.shape or not torch.isfinite(output).all():
        raise RuntimeError("M2 self-test forward pass failed")
    loss = torch.mean((output - epsilon) ** 2)
    loss.backward()
    if not all(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        raise RuntimeError("M2 self-test backward pass failed")
    print(
        json.dumps(
            {
                "status": "ok",
                "self_test": True,
                "sigma_grid": SIGMA_GRID,
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
    parser.add_argument("--condition", choices=("true", "mismatched"))
    parser.add_argument(
        "--dataset-hash-namespace", default="pusht_expert_train"
    )
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
        "condition",
        "seed",
        "hidden_width",
    )
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        raise SystemExit(f"missing required training arguments: {', '.join(missing)}")
    if args.batch_size != 256 or args.learning_rate != 3.0e-4:
        raise SystemExit("batch size and learning rate are frozen by the master protocol")
    if (
        not args.dataset_hash_namespace
        or "\0" in args.dataset_hash_namespace
        or "\n" in args.dataset_hash_namespace
    ):
        raise SystemExit("dataset hash namespace must be a non-empty single field")
    if args.smoke:
        if args.train_pair_limit is None or args.validation_pair_limit is None:
            raise SystemExit("smoke mode requires both pair limits")
    elif args.train_pair_limit is not None or args.validation_pair_limit is not None:
        raise SystemExit("pair limits are permitted only for a labeled smoke run")
    train(args)


if __name__ == "__main__":
    main()
