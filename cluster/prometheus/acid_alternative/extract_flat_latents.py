#!/usr/bin/env python3
"""Encode an episode partition with a released flat Le-WM/PLDM encoder."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from importlib import metadata
from pathlib import Path

import h5py
import numpy as np
import stable_pretraining as spt
import stable_worldmodel as swm
import torch

from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)


def load_partition_rows(path: Path, selected: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"episode_id", "episode_length", "partition"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"invalid partition manifest: {path}")
    chosen = [row for row in rows if row["partition"] in selected]
    if not chosen:
        raise SystemExit(f"no episodes selected for partitions: {sorted(selected)}")
    return chosen


def preprocess_pixels(
    pixels: np.ndarray, device: torch.device, *, image_size: int = 224
) -> torch.Tensor:
    tensor = torch.from_numpy(pixels)
    if tensor.ndim != 4:
        raise ValueError(f"expected four-dimensional pixels, got {tensor.shape}")
    if tensor.shape[-1] in (1, 3):
        tensor = tensor.permute(0, 3, 1, 2)
    elif tensor.shape[1] not in (1, 3):
        raise ValueError(f"cannot infer pixel channel axis from {tensor.shape}")
    if tuple(tensor.shape[-2:]) != (image_size, image_size):
        raise ValueError(
            f"expected released {image_size}x{image_size} input, got "
            f"{tuple(tensor.shape[-2:])}; an explicit eval-transform parity adapter is required"
        )
    tensor = tensor.contiguous().to(device=device, dtype=torch.float32).div_(255.0)
    stats = spt.data.dataset_stats.ImageNet
    mean = torch.as_tensor(stats["mean"], device=device).view(1, 3, 1, 1)
    std = torch.as_tensor(stats["std"], device=device).view(1, 3, 1, 1)
    return (tensor - mean) / std


@torch.inference_mode()
def encode(model: torch.nn.Module, pixels: torch.Tensor) -> torch.Tensor:
    info = {"pixels": pixels.unsqueeze(1)}
    try:
        output = model.encode(info, encode_actions=False)
    except TypeError:
        output = model.encode(info)
    embedding = output["emb"]
    if embedding.ndim == 3:
        embedding = embedding[:, -1]
    if embedding.ndim != 2:
        raise RuntimeError(f"unexpected encoder output shape: {tuple(embedding.shape)}")
    return embedding.float()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--partition", action="append", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--episode-limit", type=int)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.dataset,
        args.partition_manifest,
        args.checkpoint_file,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.source_manifest is not None and not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing output")
    if args.batch_size <= 0 or (
        args.episode_limit is not None and args.episode_limit <= 0
    ):
        raise SystemExit("batch size and episode limit must be positive")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    device = torch.device(args.device)
    rows = load_partition_rows(args.partition_manifest, set(args.partition))
    eligible_episodes = len(rows)
    if args.episode_limit is not None:
        rows = rows[: args.episode_limit]
    expected_rows = sum(int(row["episode_length"]) for row in rows)

    resolved_checkpoint = resolve_policy_checkpoint(args.policy, args.stablewm_home)
    if resolved_checkpoint != args.checkpoint_file.resolve():
        raise RuntimeError(
            f"policy resolves to {resolved_checkpoint}, not declared "
            f"{args.checkpoint_file.resolve()}"
        )
    model = swm.policy.AutoCostModel(args.policy, cache_dir=args.stablewm_home)
    model = model.to(device).eval()
    model.requires_grad_(False)
    if hasattr(model, "interpolate_pos_encoding"):
        model.interpolate_pos_encoding = True

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    if partial.exists():
        raise FileExistsError(partial)
    started = time.time()
    first_repeat_max_abs: float | None = None
    first_latent_sha256: str | None = None
    latent_dim: int | None = None
    written = 0

    try:
        with h5py.File(args.dataset, "r", rdcc_nbytes=512 * 1024 * 1024) as source:
            episode_key = "episode_idx" if "episode_idx" in source else "ep_idx"
            offsets = np.asarray(source["ep_offset"][:], dtype=np.int64)
            lengths = np.asarray(source["ep_len"][:], dtype=np.int64)
            selected_indices = np.concatenate(
                [
                    np.arange(
                        offsets[int(row["episode_id"])],
                        offsets[int(row["episode_id"])]
                        + lengths[int(row["episode_id"])],
                        dtype=np.int64,
                    )
                    for row in rows
                ]
            )
            selected_indices.sort()
            if len(selected_indices) != expected_rows:
                raise RuntimeError(
                    "partition manifest and HDF5 episode lengths disagree"
                )

            with h5py.File(partial, "x") as target:
                row_dataset = target.create_dataset(
                    "row_index", (expected_rows,), dtype="i8"
                )
                episode_dataset = target.create_dataset(
                    "episode_idx", (expected_rows,), dtype="i8"
                )
                step_dataset = target.create_dataset(
                    "step_idx", (expected_rows,), dtype="i8"
                )
                latent_dataset = None
                for start in range(0, expected_rows, args.batch_size):
                    end = min(start + args.batch_size, expected_rows)
                    indices = selected_indices[start:end]
                    pixels = preprocess_pixels(
                        np.asarray(source["pixels"][indices]), device
                    )
                    embeddings = encode(model, pixels)
                    if first_repeat_max_abs is None:
                        repeat = encode(model, pixels)
                        first_repeat_max_abs = float(
                            (embeddings - repeat).abs().max().item()
                        )
                        if first_repeat_max_abs != 0.0:
                            raise RuntimeError(
                                "frozen encoder is not exactly repeatable"
                            )
                        first_latent_sha256 = hashlib.sha256(
                            embeddings.detach().cpu().contiguous().numpy().tobytes()
                        ).hexdigest()
                    array = (
                        embeddings.detach().cpu().numpy().astype(np.float32, copy=False)
                    )
                    if latent_dim is None:
                        latent_dim = int(array.shape[1])
                        latent_dataset = target.create_dataset(
                            "latent",
                            (expected_rows, latent_dim),
                            dtype="f4",
                            chunks=(min(4096, expected_rows), latent_dim),
                            compression="lzf",
                        )
                    if latent_dataset is None or array.shape[1] != latent_dim:
                        raise RuntimeError("latent dimension changed")
                    if not np.isfinite(array).all():
                        raise RuntimeError("non-finite latent")
                    row_dataset[start:end] = indices
                    episode_dataset[start:end] = source[episode_key][indices]
                    step_dataset[start:end] = source["step_idx"][indices]
                    latent_dataset[start:end] = array
                    written = end
                    if (
                        written == expected_rows
                        or written % (args.batch_size * 100) == 0
                    ):
                        print(f"encoded_rows={written}/{expected_rows}", flush=True)
                target.attrs["dataset_sha256"] = sha256_file(args.dataset)
                target.attrs["partition_manifest_sha256"] = sha256_file(
                    args.partition_manifest
                )
                target.attrs["checkpoint_sha256"] = sha256_file(args.checkpoint_file)
                target.attrs["policy"] = args.policy
                target.attrs["partitions"] = json.dumps(sorted(set(args.partition)))
                target.attrs["seed"] = args.seed
        os.replace(partial, args.output_h5)
    except BaseException:
        if partial.exists():
            partial.unlink()
        raise

    manifest = {
        "status": "ok",
        "kind": "flat_frozen_encoder_latent_cache",
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "partition_manifest": str(args.partition_manifest),
        "partition_manifest_sha256": sha256_file(args.partition_manifest),
        "partitions": sorted(set(args.partition)),
        "eligible_episodes": eligible_episodes,
        "episodes": len(rows),
        "episode_limit": args.episode_limit,
        "rows": written,
        "latent_dim": latent_dim,
        "policy": args.policy,
        "checkpoint_file": str(args.checkpoint_file),
        "checkpoint_sha256": sha256_file(args.checkpoint_file),
        "resolved_checkpoint_file": str(resolved_checkpoint),
        "source_manifest": str(args.source_manifest) if args.source_manifest else None,
        "source_manifest_sha256": (
            sha256_file(args.source_manifest) if args.source_manifest else None
        ),
        "seed": args.seed,
        "first_repeat_max_abs": first_repeat_max_abs,
        "first_batch_latent_sha256": first_latent_sha256,
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
        "versions": {
            "torch": torch.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
        },
    }
    atomic_write_json(args.output_json, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
