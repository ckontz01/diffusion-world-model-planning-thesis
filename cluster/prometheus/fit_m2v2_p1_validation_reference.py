#!/usr/bin/env python3
"""Fit the frozen unlabeled P1-validation standardization for M2v2."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from m2v2_likelihood_ratio import M2V2_WIDTH, _load_checkpoint
from score_and_select_p2_true_scorers import LATENT_DIM, NOISE_DRAWS, SEEDS, SIGMAS, sha256_file
from train_m2_diffusion_head import (
    atomic_json,
    configure_determinism,
    enumerate_pairs,
    map_global_rows,
    read_tsv,
    subset_pairs,
)


REFERENCE_PAIR_COUNT = 10_000
REFERENCE_SUBSET_SEED = 20260812


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=("pusht", "tworoom"), required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--pair-plan", type=Path, required=True)
    parser.add_argument("--pair-summary", type=Path, required=True)
    parser.add_argument("--stats-npz", type=Path, required=True)
    parser.add_argument("--stats-manifest", type=Path, required=True)
    parser.add_argument("--conditional-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--unconditional-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8192)
    return parser.parse_args()


@torch.inference_mode()
def paired_difference(
    conditional: torch.nn.Module,
    unconditional: torch.nn.Module,
    source: torch.Tensor,
    target: torch.Tensor,
    noise: torch.Tensor,
    sigma_value: float,
    batch_size: int,
) -> np.ndarray:
    count = len(source)
    source_expanded = source[:, None, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(-1, LATENT_DIM)
    target_expanded = target[:, None, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(-1, LATENT_DIM)
    epsilon = noise[None, :, :].expand(count, NOISE_DRAWS, LATENT_DIM).reshape(-1, LATENT_DIM)
    sigma = torch.full((len(epsilon),), sigma_value, device=source.device, dtype=source.dtype)
    noisy_target = target_expanded + sigma[:, None] * epsilon
    zero_source = torch.zeros_like(source_expanded)
    difference = torch.empty(len(epsilon), device=source.device, dtype=source.dtype)
    for start in range(0, len(epsilon), batch_size):
        stop = min(start + batch_size, len(epsilon))
        cond = conditional(noisy_target[start:stop], sigma[start:stop], source_expanded[start:stop])
        uncond = unconditional(noisy_target[start:stop], sigma[start:stop], zero_source[start:stop])
        difference[start:stop] = (
            (epsilon[start:stop] - cond).square().sum(dim=-1)
            - (epsilon[start:stop] - uncond).square().sum(dim=-1)
        )
    return difference.reshape(count, NOISE_DRAWS).mean(dim=1).cpu().numpy().astype(np.float64)


def main() -> None:
    args = parse_args()
    if len(args.conditional_checkpoint) != len(SEEDS) or len(args.unconditional_checkpoint) != len(SEEDS):
        raise SystemExit("provide exactly three conditional and three unconditional checkpoints in seed order")
    output_npz = args.output_dir / "reference.npz"
    output_json = args.output_dir / "manifest.json"
    if output_npz.exists() or output_json.exists():
        raise SystemExit(f"refusing to overwrite M2v2 reference: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    determinism = configure_determinism(REFERENCE_SUBSET_SEED)
    if not torch.cuda.is_available():
        raise RuntimeError("M2v2 reference fitting requires CUDA")
    device = torch.device("cuda")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    stats_manifest = json.loads(args.stats_manifest.read_text(encoding="utf-8"))
    pair_summary = json.loads(args.pair_summary.read_text(encoding="utf-8"))
    if sha256_file(args.pair_plan) != pair_summary["m1_m2"]["manifest_sha256"]:
        raise RuntimeError("M2v2 P1 pair plan differs from its summary")
    if stats_manifest["source"]["latent_cache_sha256"] != latent_manifest["output_h5_sha256"]:
        raise RuntimeError("M2v2 P1 statistics/cache mismatch")
    if stats_manifest["output_npz_sha256"] != sha256_file(args.stats_npz):
        raise RuntimeError("M2v2 P1 statistics hash mismatch")

    plan_rows = read_tsv(args.pair_plan)
    source_global, target_global, pair_info = enumerate_pairs(
        plan_rows, "P1_val", "true", REFERENCE_SUBSET_SEED, args.environment
    )
    source_global, target_global, subset_sha = subset_pairs(
        source_global, target_global, REFERENCE_PAIR_COUNT, REFERENCE_SUBSET_SEED
    )
    if len(source_global) != REFERENCE_PAIR_COUNT or subset_sha is None:
        raise RuntimeError("M2v2 reference requires exactly 10,000 deterministic P1-validation pairs")
    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_np = np.asarray(handle["latent"][:], dtype=np.float32)
    source_indices = map_global_rows(cache_rows, source_global)
    target_indices = map_global_rows(cache_rows, target_global)
    with np.load(args.stats_npz, allow_pickle=False) as stats:
        mean_np = np.asarray(stats["mean"], dtype=np.float32)
        std_np = np.asarray(stats["std"], dtype=np.float32)
    latents = torch.from_numpy(latent_np).to(device)
    mean = torch.from_numpy(mean_np).to(device)
    std = torch.from_numpy(std_np).to(device)
    source = (latents.index_select(0, torch.from_numpy(source_indices).to(device)) - mean) / std
    target = (latents.index_select(0, torch.from_numpy(target_indices).to(device)) - mean) / std
    del latents, latent_np

    noise_info = json.loads(args.noise_manifest.read_text(encoding="utf-8"))
    if noise_info["output_npy_sha256"] != sha256_file(args.noise_npy):
        raise RuntimeError("M2v2 reference noise bank hash mismatch")
    noise_np = np.load(args.noise_npy, allow_pickle=False)
    if noise_np.shape != (NOISE_DRAWS, LATENT_DIM) or noise_np.dtype != np.float32:
        raise RuntimeError("M2v2 reference noise bank shape changed")
    noise = torch.from_numpy(noise_np).to(device)

    difference_mean = np.empty((len(SEEDS), len(SIGMAS)), dtype=np.float64)
    difference_std = np.empty_like(difference_mean)
    cell_summaries: list[dict[str, Any]] = []
    checkpoint_records: list[dict[str, Any]] = []
    for seed_index, seed in enumerate(SEEDS):
        conditional_path = args.conditional_checkpoint[seed_index]
        unconditional_path = args.unconditional_checkpoint[seed_index]
        conditional, conditional_payload = _load_checkpoint(
            conditional_path, seed=seed, condition="true", device=device
        )
        unconditional, unconditional_payload = _load_checkpoint(
            unconditional_path, seed=seed, condition="unconditional_zero_source", device=device
        )
        for payload in (conditional_payload, unconditional_payload):
            if payload["stats_npz_sha256"] != stats_manifest["output_npz_sha256"]:
                raise RuntimeError("M2v2 checkpoint uses different P1 statistics")
        for role, path in (("conditional", conditional_path), ("unconditional", unconditional_path)):
            checkpoint_records.append({"role": role, "seed": seed, "path": str(path), "sha256": sha256_file(path)})
        for sigma_index, sigma in enumerate(SIGMAS):
            values = paired_difference(
                conditional, unconditional, source, target, noise, sigma, args.batch_size
            )
            mu = float(values.mean())
            sd = float(values.std(ddof=0))
            if not np.isfinite(mu) or not np.isfinite(sd) or sd <= 1.0e-6:
                raise RuntimeError(f"degenerate M2v2 P1 reference cell: seed={seed}, sigma={sigma}")
            difference_mean[seed_index, sigma_index] = mu
            difference_std[seed_index, sigma_index] = sd
            cell_summaries.append(
                {
                    "seed": seed,
                    "sigma": sigma,
                    "difference_mean": mu,
                    "difference_std_population": sd,
                    "difference_min": float(values.min()),
                    "difference_max": float(values.max()),
                }
            )

    partial_npz = output_npz.with_name(f".{output_npz.name}.partial-{os.getpid()}")
    with partial_npz.open("xb") as stream:
        np.savez_compressed(
            stream,
            seeds=np.asarray(SEEDS, dtype=np.int64),
            sigmas=np.asarray(SIGMAS, dtype=np.float64),
            difference_mean=difference_mean.astype(np.float32),
            difference_std=difference_std.astype(np.float32),
        )
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial_npz, output_npz)
    result = {
        "status": "ok",
        "classification": f"{args.environment}_m2v2_p1_validation_reference",
        "environment": args.environment,
        "partition": "P1-validation-only",
        "method": "M2v2",
        "width": M2V2_WIDTH,
        "seeds": list(SEEDS),
        "sigmas": list(SIGMAS),
        "noise_draws": NOISE_DRAWS,
        "validation_pair_count": REFERENCE_PAIR_COUNT,
        "validation_subset_seed": REFERENCE_SUBSET_SEED,
        "validation_subset_sha256": subset_sha,
        "full_validation_pair_info": pair_info,
        "cell_summaries": cell_summaries,
        "checkpoints": checkpoint_records,
        "spec": str(args.spec),
        "spec_sha256": sha256_file(args.spec),
        "inputs": {
            "latent_h5_sha256": latent_manifest["output_h5_sha256"],
            "pair_plan_sha256": sha256_file(args.pair_plan),
            "pair_summary_sha256": sha256_file(args.pair_summary),
            "stats_npz_sha256": stats_manifest["output_npz_sha256"],
            "noise_npy_sha256": noise_info["output_npy_sha256"],
        },
        "determinism": determinism,
        "runtime": {
            "python": os.sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "gpu": torch.cuda.get_device_name(device),
            "elapsed_seconds": time.time() - started,
        },
        "output_npz": str(output_npz),
        "output_npz_sha256": sha256_file(output_npz),
    }
    atomic_json(output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
