#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_npy(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("xb") as stream:
        np.save(stream, value, allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def generate(seed: int, draws: int, latent_dim: int) -> np.ndarray:
    generator = np.random.Generator(np.random.PCG64(seed))
    # Freeze the byte representation explicitly: draw float64 values using
    # NumPy's declared PCG64 generator, then round once to little-endian f32.
    values = generator.standard_normal((draws, latent_dim)).astype("<f4")
    if values.dtype != np.dtype("<f4") or not np.isfinite(values).all():
        raise RuntimeError("invalid fixed M2 score-noise bank")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--draws", type=int, default=8)
    parser.add_argument("--latent-dim", type=int, default=192)
    parser.add_argument("--output-npy", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.draws != 8 or args.latent_dim != 192:
        raise SystemExit("the primary PushT M2 bank is frozen to shape (8, 192)")
    if args.output_npy.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing M2 score-noise bank")

    bank = generate(args.seed, args.draws, args.latent_dim)
    repeated = generate(args.seed, args.draws, args.latent_dim)
    if not np.array_equal(bank, repeated):
        raise RuntimeError("fixed-noise regeneration was not byte-identical in memory")

    atomic_npy(args.output_npy, bank)
    reloaded = np.load(args.output_npy, allow_pickle=False)
    if not np.array_equal(bank, reloaded):
        raise RuntimeError("saved M2 score-noise bank did not round-trip exactly")

    result = {
        "status": "ok",
        "classification": "frozen_m2_deployment_common_random_numbers",
        "algorithm": "numpy.random.Generator(numpy.random.PCG64(seed)).standard_normal(float64), cast once to little-endian float32",
        "seed": args.seed,
        "shape": list(bank.shape),
        "dtype": bank.dtype.str,
        "mean": float(bank.mean(dtype=np.float64)),
        "population_std": float(bank.std(dtype=np.float64)),
        "output_npy": str(args.output_npy),
        "output_npy_sha256": sha256_file(args.output_npy),
        "runtime": {
            "python": sys.version,
            "numpy": np.__version__,
        },
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
