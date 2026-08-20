#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata as metadata
import json
import os
import time
from pathlib import Path

import h5py
import hydra
import numpy as np
import stable_pretraining as spt
import stable_worldmodel as swm
import torch

from h_le_wm.eval.determinism import configure_process_determinism
from h_le_wm.eval.hierarchical import force_torch_load_map_location, img_transform


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


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


def vectorized_preprocess(pixels_nhwc: np.ndarray, device: torch.device) -> torch.Tensor:
    pixels = torch.from_numpy(pixels_nhwc).permute(0, 3, 1, 2).contiguous()
    pixels = pixels.to(device=device, dtype=torch.float32).div_(255.0)
    stats = spt.data.dataset_stats.ImageNet
    mean = torch.as_tensor(stats["mean"], device=device, dtype=torch.float32).view(1, 3, 1, 1)
    std = torch.as_tensor(stats["std"], device=device, dtype=torch.float32).view(1, 3, 1, 1)
    return (pixels - mean) / std


@torch.inference_mode()
def encode(model: torch.nn.Module, pixels_bchw: torch.Tensor) -> torch.Tensor:
    output = model.encode({"pixels": pixels_bchw.unsqueeze(1)}, encode_actions=False)
    embedding = output["emb"]
    if embedding.ndim == 3:
        embedding = embedding[:, -1]
    if embedding.ndim != 2:
        raise RuntimeError(f"unexpected encoder output shape: {tuple(embedding.shape)}")
    return embedding.float()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--eval-config-dir", type=Path, default=None)
    parser.add_argument("--eval-config-name", default="hi_pusht")
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--partition", action="append", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--episode-limit", type=int, default=None)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite an existing latent cache or manifest")
    if args.episode_limit is not None and args.episode_limit <= 0:
        raise SystemExit("episode-limit must be positive when supplied")
    selected = set(args.partition)
    partition_rows = load_partition_rows(args.partition_manifest, selected)
    eligible_episode_count = len(partition_rows)
    if args.episode_limit is not None:
        partition_rows = partition_rows[: args.episode_limit]
    expected_rows = sum(int(row["episode_length"]) for row in partition_rows)

    determinism = configure_process_determinism(seed=args.seed, mode="strict")
    config_dir_path = (
        args.eval_config_dir
        if args.eval_config_dir is not None
        else args.code_root / "h_le_wm" / "config" / "eval"
    ).resolve()
    config_file = config_dir_path / f"{args.eval_config_name}.yaml"
    if not config_file.is_file():
        raise FileNotFoundError(config_file)
    config_dir = str(config_dir_path)
    with hydra.initialize_config_dir(version_base=None, config_dir=config_dir):
        cfg = hydra.compose(
            config_name=args.eval_config_name,
            overrides=[
                f"cache_dir={args.stablewm_home}",
                f"policy={args.policy}",
                f"seed={args.seed}",
                "planning.high.solver.device=cuda",
                "planning.low.solver.device=cuda",
                "solver.device=cuda",
            ],
        )

    device = torch.device("cuda")
    with force_torch_load_map_location("cuda"):
        model = swm.policy.AutoCostModel(cfg.policy)
    model = model.to(device).eval()
    model.requires_grad_(False)
    model.interpolate_pos_encoding = True

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    if partial.exists():
        raise SystemExit(f"refusing to reuse partial cache: {partial}")

    started = time.time()
    first_preprocess_max_abs = None
    first_repeat_max_abs = None
    first_latent_sha256 = None
    latent_dim = None
    total_written = 0
    latent_sum = 0.0
    latent_sq_sum = 0.0
    latent_min = float("inf")
    latent_max = float("-inf")
    source_episode_key = None

    try:
        with h5py.File(args.dataset, "r") as source:
            source_episode_key = next(
                (key for key in ("episode_idx", "ep_idx") if key in source), None
            )
            if source_episode_key is None:
                raise KeyError("dataset has neither 'episode_idx' nor 'ep_idx'")
            offsets = np.asarray(source["ep_offset"][:], dtype=np.int64)
            lengths = np.asarray(source["ep_len"][:], dtype=np.int64)
            selected_indices = np.concatenate(
                [
                    np.arange(
                        offsets[int(row["episode_id"])],
                        offsets[int(row["episode_id"])] + lengths[int(row["episode_id"])],
                        dtype=np.int64,
                    )
                    for row in partition_rows
                ]
            )
            selected_indices.sort()
            if selected_indices.size != expected_rows:
                raise RuntimeError(
                    f"partition row mismatch: manifest={expected_rows}, selected={selected_indices.size}"
                )

            with h5py.File(partial, "x") as target:
                row_ds = target.create_dataset("row_index", shape=(expected_rows,), dtype="i8")
                episode_ds = target.create_dataset("episode_idx", shape=(expected_rows,), dtype="i8")
                step_ds = target.create_dataset("step_idx", shape=(expected_rows,), dtype="i8")
                latent_ds = None

                for start in range(0, expected_rows, args.batch_size):
                    end = min(start + args.batch_size, expected_rows)
                    batch_indices = selected_indices[start:end]
                    pixels_np = np.asarray(source["pixels"][batch_indices])
                    pixels = vectorized_preprocess(pixels_np, device)

                    if first_preprocess_max_abs is None:
                        reference_transform = img_transform(cfg)
                        reference = torch.stack(
                            [
                                reference_transform(
                                    torch.from_numpy(image).permute(2, 0, 1).contiguous()
                                )
                                for image in pixels_np[: min(4, len(pixels_np))]
                            ]
                        ).to(device)
                        first_preprocess_max_abs = float(
                            (pixels[: reference.size(0)] - reference).abs().max().item()
                        )
                        if first_preprocess_max_abs > 1.0e-7:
                            raise RuntimeError(
                                "vectorized preprocessing does not match released evaluator: "
                                f"max_abs={first_preprocess_max_abs}"
                            )

                    latents = encode(model, pixels)
                    if first_repeat_max_abs is None:
                        repeated = encode(model, pixels)
                        first_repeat_max_abs = float((latents - repeated).abs().max().item())
                        if first_repeat_max_abs != 0.0:
                            raise RuntimeError(
                                f"encoder repeat is not exact: max_abs={first_repeat_max_abs}"
                            )
                        first_latent_sha256 = hashlib.sha256(
                            latents.detach().cpu().contiguous().numpy().tobytes()
                        ).hexdigest()

                    latent_np = latents.detach().cpu().contiguous().numpy().astype(
                        np.float32, copy=False
                    )
                    if latent_dim is None:
                        latent_dim = int(latent_np.shape[1])
                        latent_ds = target.create_dataset(
                            "latent",
                            shape=(expected_rows, latent_dim),
                            dtype="f4",
                            chunks=(min(4096, expected_rows), latent_dim),
                            compression="lzf",
                        )
                    if latent_np.shape[1] != latent_dim or latent_ds is None:
                        raise RuntimeError("latent dimensionality changed during extraction")
                    if not np.isfinite(latent_np).all():
                        raise RuntimeError("non-finite latent encountered")

                    row_ds[start:end] = batch_indices
                    episode_ds[start:end] = source[source_episode_key][batch_indices]
                    step_ds[start:end] = source["step_idx"][batch_indices]
                    latent_ds[start:end] = latent_np

                    total_written += latent_np.shape[0]
                    latent_sum += float(latent_np.sum(dtype=np.float64))
                    latent_sq_sum += float(
                        np.square(latent_np.astype(np.float64, copy=False)).sum()
                    )
                    latent_min = min(latent_min, float(latent_np.min()))
                    latent_max = max(latent_max, float(latent_np.max()))
                    if total_written % (args.batch_size * 25) == 0 or total_written == expected_rows:
                        print(f"encoded_rows={total_written}/{expected_rows}", flush=True)

                if total_written != expected_rows or latent_dim is None:
                    raise RuntimeError(
                        f"incomplete extraction: wrote={total_written}, expected={expected_rows}"
                    )
                target.attrs["dataset"] = str(args.dataset)
                target.attrs["partition_manifest_sha256"] = sha256_file(args.partition_manifest)
                target.attrs["partitions"] = json.dumps(sorted(selected))
                target.attrs["episode_limit"] = (
                    -1 if args.episode_limit is None else args.episode_limit
                )
                target.attrs["policy"] = args.policy
                target.attrs["checkpoint_sha256"] = sha256_file(args.checkpoint_file)
                target.attrs["eval_config_name"] = args.eval_config_name
                target.attrs["eval_config_sha256"] = sha256_file(config_file)
                target.attrs["source_episode_dataset"] = source_episode_key
                target.attrs["seed"] = args.seed
                target.flush()
        os.replace(partial, args.output_h5)
    except BaseException:
        if partial.exists():
            print(f"partial_cache_retained={partial}")
        raise

    num_values = total_written * int(latent_dim)
    latent_mean = latent_sum / num_values
    latent_variance = max(0.0, latent_sq_sum / num_values - latent_mean**2)
    result = {
        "status": "ok",
        "classification": (
            "frozen_encoder_latent_cache"
            if args.episode_limit is None
            else "frozen_encoder_latent_cache_implementation_smoke"
        ),
        "partitions": sorted(selected),
        "episodes": len(partition_rows),
        "eligible_episodes": eligible_episode_count,
        "episode_limit": args.episode_limit,
        "rows": total_written,
        "latent_dim": latent_dim,
        "latent_dtype": "float32",
        "elapsed_seconds": time.time() - started,
        "rows_per_second": total_written / (time.time() - started),
        "preprocess_reference_max_abs": first_preprocess_max_abs,
        "first_batch_repeat_max_abs": first_repeat_max_abs,
        "first_batch_latent_sha256": first_latent_sha256,
        "latent_stats": {
            "min": latent_min,
            "max": latent_max,
            "mean": latent_mean,
            "std": latent_variance**0.5,
        },
        "dataset": str(args.dataset),
        "dataset_bytes": args.dataset.stat().st_size,
        "source_episode_dataset": source_episode_key,
        "partition_manifest": str(args.partition_manifest),
        "partition_manifest_sha256": sha256_file(args.partition_manifest),
        "eval_config_name": args.eval_config_name,
        "eval_config_file": str(config_file),
        "eval_config_sha256": sha256_file(config_file),
        "checkpoint_file": str(args.checkpoint_file),
        "checkpoint_sha256": sha256_file(args.checkpoint_file),
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "runtime": {
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "pythonhashseed_at_process_start": os.environ.get("PYTHONHASHSEED"),
            "cublas_workspace_config_at_process_start": os.environ.get(
                "CUBLAS_WORKSPACE_CONFIG"
            ),
        },
        "determinism": determinism,
    }
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
