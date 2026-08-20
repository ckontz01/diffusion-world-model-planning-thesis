#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise SystemExit(f"empty manifest: {path}")
    return rows


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("xb") as stream:
        np.savez(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--master-partition-manifest", type=Path, required=True)
    parser.add_argument("--p1-split-manifest", type=Path, required=True)
    parser.add_argument("--output-npz", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--batch-rows", type=int, default=65536)
    parser.add_argument("--std-floor", type=float, default=1.0e-6)
    args = parser.parse_args()

    if args.output_npz.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite frozen P1 latent statistics")
    args.output_npz.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    master_rows = read_tsv(args.master_partition_manifest)
    split_rows = read_tsv(args.p1_split_manifest)
    master_by_id = {int(row["episode_id"]): row for row in master_rows}
    split_by_id = {int(row["episode_id"]): row for row in split_rows}
    if len(master_by_id) != len(master_rows) or len(split_by_id) != len(split_rows):
        raise SystemExit("duplicate episode IDs in source manifests")
    expected_ids = list(range(len(master_rows)))
    if sorted(master_by_id) != expected_ids:
        raise SystemExit("master episode IDs must be contiguous from zero")

    offsets: dict[int, int] = {}
    running = 0
    for episode_id in expected_ids:
        offsets[episode_id] = running
        running += int(master_by_id[episode_id]["episode_length"])
    p1_ids = {
        episode_id
        for episode_id, row in master_by_id.items()
        if row["partition"] == "P1"
    }
    if set(split_by_id) != p1_ids:
        raise SystemExit("P1 split does not exactly match master P1 episodes")

    train_global_rows = np.concatenate(
        [
            np.arange(
                offsets[episode_id],
                offsets[episode_id] + int(row["episode_length"]),
                dtype=np.int64,
            )
            for episode_id, row in sorted(split_by_id.items())
            if row["p1_role"] == "P1_train"
        ]
    )
    expected_train_frames = sum(
        int(row["episode_length"])
        for row in split_rows
        if row["p1_role"] == "P1_train"
    )
    if train_global_rows.size != expected_train_frames:
        raise RuntimeError("P1 training-frame enumeration mismatch")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    if latent_manifest.get("status") != "ok" or latent_manifest.get("partitions") != [
        "P1"
    ]:
        raise RuntimeError("latent manifest is not a completed P1 cache")
    if args.latent_h5.stat().st_size != int(latent_manifest["output_h5_bytes"]):
        raise RuntimeError("P1 latent cache byte size differs from its manifest")

    with h5py.File(args.latent_h5, "r") as handle:
        cache_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
        latent_ds = handle["latent"]
        if cache_rows.ndim != 1 or latent_ds.ndim != 2:
            raise RuntimeError("invalid P1 latent cache shapes")
        if len(cache_rows) != latent_ds.shape[0] or not np.all(
            cache_rows[1:] > cache_rows[:-1]
        ):
            raise RuntimeError("P1 cache rows are not strictly increasing")
        positions = np.searchsorted(cache_rows, train_global_rows)
        if np.any(positions >= cache_rows.size) or not np.array_equal(
            cache_rows[positions], train_global_rows
        ):
            raise RuntimeError("P1 training rows are absent from the latent cache")
        train_mask = np.zeros(cache_rows.size, dtype=np.bool_)
        train_mask[positions] = True

        latent_dim = int(latent_ds.shape[1])
        count = 0
        mean = np.zeros(latent_dim, dtype=np.float64)
        m2 = np.zeros(latent_dim, dtype=np.float64)
        for start in range(0, len(cache_rows), args.batch_rows):
            end = min(start + args.batch_rows, len(cache_rows))
            selected = np.asarray(latent_ds[start:end], dtype=np.float64)[
                train_mask[start:end]
            ]
            if selected.size == 0:
                continue
            if not np.isfinite(selected).all():
                raise RuntimeError("non-finite P1 latent encountered")
            batch_count = int(selected.shape[0])
            batch_mean = selected.mean(axis=0)
            centered = selected - batch_mean
            batch_m2 = np.square(centered).sum(axis=0)
            new_count = count + batch_count
            delta = batch_mean - mean
            mean = mean + delta * (batch_count / new_count)
            m2 = m2 + batch_m2 + np.square(delta) * count * batch_count / new_count
            count = new_count
            print(f"stats_rows={count}/{expected_train_frames}", flush=True)

    if count != expected_train_frames:
        raise RuntimeError(
            f"P1 statistics count mismatch: observed={count}, expected={expected_train_frames}"
        )
    variance = np.maximum(m2 / count, 0.0)
    raw_std = np.sqrt(variance)
    std = np.maximum(raw_std, args.std_floor)
    mean_f32 = mean.astype(np.float32)
    std_f32 = std.astype(np.float32)
    raw_std_f32 = raw_std.astype(np.float32)
    atomic_npz(
        args.output_npz,
        mean=mean_f32,
        std=std_f32,
        raw_std=raw_std_f32,
        count=np.asarray(count, dtype=np.int64),
    )

    result = {
        "status": "ok",
        "classification": "p1_train_latent_standardization",
        "count": count,
        "latent_dim": latent_dim,
        "population_variance": True,
        "std_floor": args.std_floor,
        "floored_dimensions": int((raw_std < args.std_floor).sum()),
        "mean_range": [float(mean.min()), float(mean.max())],
        "raw_std_range": [float(raw_std.min()), float(raw_std.max())],
        "source": {
            "latent_h5": str(args.latent_h5),
            "latent_cache_sha256": latent_manifest["output_h5_sha256"],
            "latent_manifest": str(args.latent_manifest),
            "latent_manifest_sha256": sha256_file(args.latent_manifest),
            "master_partition_manifest": str(args.master_partition_manifest),
            "master_partition_manifest_sha256": sha256_file(
                args.master_partition_manifest
            ),
            "p1_split_manifest": str(args.p1_split_manifest),
            "p1_split_manifest_sha256": sha256_file(args.p1_split_manifest),
        },
        "output_npz": str(args.output_npz),
        "output_npz_sha256": sha256_file(args.output_npz),
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
