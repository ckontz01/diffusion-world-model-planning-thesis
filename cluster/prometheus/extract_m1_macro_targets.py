#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from hi_diagnostics import DiagnosticConfig, build_context, encode_macro_actions


ROLES = ("P1_train", "P1_val")


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


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise RuntimeError(f"empty TSV: {path}")
    return rows


def enumerate_role_pairs(
    rows: list[dict[str, str]], role: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    selected = sorted(
        (row for row in rows if row["p1_role"] == role),
        key=lambda row: int(row["episode_id"]),
    )
    if not selected:
        raise RuntimeError(f"pair plan contains no rows for {role}")
    deltas = {int(row["delta"]) for row in selected}
    if len(deltas) != 1:
        raise RuntimeError(f"inconsistent deltas for {role}: {sorted(deltas)}")
    delta = deltas.pop()
    source_parts: list[np.ndarray] = []
    target_parts: list[np.ndarray] = []
    episode_parts: list[np.ndarray] = []
    for row in selected:
        episode_id = int(row["episode_id"])
        pair_count = int(row["pair_count"])
        source = np.arange(
            int(row["source_start_row"]),
            int(row["source_end_exclusive"]),
            dtype=np.int64,
        )
        target = np.arange(
            int(row["target_start_row"]),
            int(row["target_end_exclusive"]),
            dtype=np.int64,
        )
        if source.size != pair_count or target.size != pair_count:
            raise RuntimeError(f"pair-count mismatch for episode {episode_id}")
        if not np.array_equal(target - source, np.full(pair_count, delta)):
            raise RuntimeError(f"delta mismatch for episode {episode_id}")
        source_parts.append(source)
        target_parts.append(target)
        episode_parts.append(np.full(pair_count, episode_id, dtype=np.int64))
    return (
        np.concatenate(source_parts),
        np.concatenate(target_parts),
        np.concatenate(episode_parts),
        delta,
    )


def deterministic_subset(
    arrays: tuple[np.ndarray, np.ndarray, np.ndarray],
    limit: int | None,
    seed: int,
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], str | None]:
    count = len(arrays[0])
    if limit is None or limit >= count:
        return arrays, None
    rng = np.random.Generator(np.random.PCG64(seed))
    selected = np.sort(rng.choice(count, size=limit, replace=False))
    return tuple(value[selected] for value in arrays), sha256_array(selected)


def create_role_datasets(
    handle: h5py.File,
    role: str,
    count: int,
    macro_dim: int,
    batch_size: int,
) -> dict[str, h5py.Dataset]:
    group = handle.create_group(role)
    row_chunk = min(batch_size, count)
    return {
        "source": group.create_dataset(
            "source_global_row", shape=(count,), dtype="i8", chunks=(row_chunk,)
        ),
        "target": group.create_dataset(
            "target_global_row", shape=(count,), dtype="i8", chunks=(row_chunk,)
        ),
        "episode": group.create_dataset(
            "episode_id", shape=(count,), dtype="i8", chunks=(row_chunk,)
        ),
        "macro": group.create_dataset(
            "macro_action",
            shape=(count, macro_dim),
            dtype="f4",
            chunks=(row_chunk, macro_dim),
            compression="lzf",
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-plan", type=Path, required=True)
    parser.add_argument("--pair-summary", type=Path, required=True)
    parser.add_argument("--dataset-file", type=Path, required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset-name", default="pusht_expert_train")
    parser.add_argument("--policy", required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--pair-limit-per-role", type=int)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite M1 macro-target output")
    if args.batch_size <= 0:
        raise SystemExit("batch size must be positive")
    if args.smoke:
        if args.pair_limit_per_role != 1024:
            raise SystemExit("M1 target smoke must use exactly 1024 pairs per role")
    elif args.pair_limit_per_role is not None:
        raise SystemExit("full M1 target extraction must use all planned pairs")
    for path in (
        args.pair_plan,
        args.pair_summary,
        args.dataset_file,
        args.checkpoint_file,
    ):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    if len(args.dataset_sha256) != 64:
        raise SystemExit("dataset SHA-256 must contain 64 hexadecimal characters")

    started = time.time()
    determinism = configure_determinism(args.seed)
    summary = json.loads(args.pair_summary.read_text(encoding="utf-8"))
    if summary.get("status") != "ok":
        raise RuntimeError("pair-summary status is not ok")
    if summary.get("dataset_name") != args.dataset_name:
        raise RuntimeError("pair-summary dataset name mismatch")
    if sha256_file(args.pair_plan) != summary["m1_m2"]["manifest_sha256"]:
        raise RuntimeError("pair-plan hash does not match pair summary")
    rows = read_tsv(args.pair_plan)

    cfg = DiagnosticConfig(
        policy=args.policy,
        experiment_kind="m1_frozen_macro_target_extraction",
        dataset_name=args.dataset_name,
        cache_dir=str(args.stablewm_home),
        goal_offset_steps=int(summary["m1_m2"]["delta"]),
        seed=args.seed,
        device="cuda",
    )
    ctx = build_context(cfg)
    if ctx.device.type != "cuda":
        raise RuntimeError("M1 macro-target extraction requires CUDA")
    delta = int(summary["m1_m2"]["delta"])
    if delta <= 0 or delta % ctx.group != 0:
        raise RuntimeError(
            f"delta={delta} is not divisible by macro grouping factor={ctx.group}"
        )
    token_count = delta // ctx.group
    macro_dim = int(ctx.latent_dim)
    if macro_dim <= 0:
        raise RuntimeError("invalid macro-action latent dimension")

    actions = np.asarray(ctx.action, dtype=np.float32)
    normalized_actions = ctx.action_scaler.transform(actions).astype(np.float32, copy=False)
    with h5py.File(args.dataset_file, "r") as source:
        source_episode_key = next(
            (key for key in ("episode_idx", "ep_idx") if key in source), None
        )
        if source_episode_key is None:
            raise KeyError("dataset has neither 'episode_idx' nor 'ep_idx'")
        episode_idx = np.asarray(source[source_episode_key], dtype=np.int64)
        step_idx = np.asarray(source["step_idx"], dtype=np.int64)
    if len(actions) != len(episode_idx) or len(actions) != len(step_idx):
        raise RuntimeError("dataset action and row metadata lengths differ")

    role_inputs: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    role_metadata: dict[str, dict[str, Any]] = {}
    for role_index, role in enumerate(ROLES):
        source_rows, target_rows, episode_ids, role_delta = enumerate_role_pairs(rows, role)
        if role_delta != delta:
            raise RuntimeError(f"{role} delta does not match pair summary")
        expected_count = int(summary["m1_m2"]["pair_counts"][role])
        if len(source_rows) != expected_count:
            raise RuntimeError(
                f"{role} expected {expected_count} pairs, found {len(source_rows)}"
            )
        (source_rows, target_rows, episode_ids), subset_sha = deterministic_subset(
            (source_rows, target_rows, episode_ids),
            args.pair_limit_per_role,
            args.seed + role_index,
        )
        role_inputs[role] = (source_rows, target_rows, episode_ids)
        role_metadata[role] = {
            "full_pair_count": expected_count,
            "written_pair_count": len(source_rows),
            "source_global_rows_sha256": sha256_array(source_rows),
            "target_global_rows_sha256": sha256_array(target_rows),
            "episode_ids_sha256": sha256_array(episode_ids),
            "subset_indices_sha256": subset_sha,
        }

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial_h5 = args.output_h5.with_name(
        f".{args.output_h5.name}.partial-{os.getpid()}"
    )
    train_sum = np.zeros(macro_dim, dtype=np.float64)
    train_sq_sum = np.zeros(macro_dim, dtype=np.float64)
    train_count = 0
    first_macro_sha256: str | None = None
    try:
        with h5py.File(partial_h5, "x") as output:
            output.attrs["classification"] = (
                "development_smoke" if args.smoke else "p1_frozen_m1_macro_targets"
            )
            output.attrs["delta_primitive_steps"] = delta
            output.attrs["macro_token_count"] = token_count
            output.attrs["raw_action_group_factor"] = ctx.group
            output.attrs["raw_action_dim"] = ctx.raw_action_dim
            output.attrs["macro_input_dim"] = ctx.macro_input_dim
            output.attrs["macro_action_dim"] = macro_dim
            output.attrs["source_episode_dataset"] = source_episode_key
            window_offsets = np.arange(delta, dtype=np.int64)
            for role in ROLES:
                source_rows, target_rows, episode_ids = role_inputs[role]
                datasets = create_role_datasets(
                    output, role, len(source_rows), macro_dim, args.batch_size
                )
                for start in range(0, len(source_rows), args.batch_size):
                    stop = min(start + args.batch_size, len(source_rows))
                    source_batch = source_rows[start:stop]
                    target_batch = target_rows[start:stop]
                    episode_batch = episode_ids[start:stop]
                    raw_indices = source_batch[:, None] + window_offsets[None, :]
                    if not np.all(episode_idx[raw_indices] == episode_batch[:, None]):
                        raise RuntimeError(f"action window crosses an episode in {role}")
                    expected_steps = step_idx[source_batch, None] + window_offsets[None, :]
                    if not np.array_equal(step_idx[raw_indices], expected_steps):
                        raise RuntimeError(f"non-contiguous action window in {role}")
                    if not np.array_equal(target_batch - source_batch, np.full(stop - start, delta)):
                        raise RuntimeError(f"target separation changed in {role}")
                    action_tokens = normalized_actions[raw_indices].reshape(
                        stop - start,
                        token_count,
                        ctx.macro_input_dim,
                    )
                    with torch.inference_mode():
                        macro = encode_macro_actions(
                            ctx.model, action_tokens, device=ctx.device
                        )
                    macro_np = (
                        macro.detach().cpu().contiguous().numpy().astype(np.float32, copy=False)
                    )
                    if macro_np.shape != (stop - start, macro_dim):
                        raise RuntimeError(
                            f"unexpected macro target shape {macro_np.shape}; "
                            f"expected {(stop - start, macro_dim)}"
                        )
                    if not np.isfinite(macro_np).all():
                        raise RuntimeError("non-finite macro target")
                    if first_macro_sha256 is None:
                        first_macro_sha256 = sha256_array(macro_np)
                    datasets["source"][start:stop] = source_batch
                    datasets["target"][start:stop] = target_batch
                    datasets["episode"][start:stop] = episode_batch
                    datasets["macro"][start:stop] = macro_np
                    if role == "P1_train":
                        macro64 = macro_np.astype(np.float64, copy=False)
                        train_sum += macro64.sum(axis=0)
                        train_sq_sum += np.square(macro64).sum(axis=0)
                        train_count += len(macro_np)
                    if stop == len(source_rows) or stop % (args.batch_size * 10) == 0:
                        print(f"role={role} encoded_pairs={stop}/{len(source_rows)}", flush=True)
            if train_count != len(role_inputs["P1_train"][0]):
                raise RuntimeError("P1 train statistics count mismatch")
            train_mean = train_sum / train_count
            train_var = np.maximum(train_sq_sum / train_count - np.square(train_mean), 0.0)
            train_std = np.sqrt(train_var)
            if np.any(train_std < 1.0e-8):
                raise RuntimeError("near-constant M1 macro target dimension")
            output.create_dataset("p1_train_macro_mean", data=train_mean.astype(np.float32))
            output.create_dataset("p1_train_macro_std", data=train_std.astype(np.float32))
            output.flush()
        os.replace(partial_h5, args.output_h5)
    except BaseException:
        if partial_h5.exists():
            print(f"partial_m1_target_cache_retained={partial_h5}", file=sys.stderr)
        raise

    result = {
        "status": "ok",
        "classification": (
            "development_smoke" if args.smoke else "p1_frozen_m1_macro_targets"
        ),
        "seed": args.seed,
        "delta_primitive_steps": delta,
        "macro_token_count": token_count,
        "raw_action_group_factor": ctx.group,
        "raw_action_dim": ctx.raw_action_dim,
        "macro_input_dim": ctx.macro_input_dim,
        "macro_action_dim": macro_dim,
        "source_episode_dataset": source_episode_key,
        "roles": role_metadata,
        "p1_train_macro_statistics": {
            "count": train_count,
            "mean": train_mean.tolist(),
            "std": train_std.tolist(),
            "ddof": 0,
        },
        "action_standardization": {
            "fit_population": "all finite actions in the released dataset, matching the artifact helper",
            "mean": ctx.action_scaler.mean_.tolist(),
            "scale": ctx.action_scaler.scale_.tolist(),
        },
        "first_encoded_batch_sha256": first_macro_sha256,
        "inputs": {
            "pair_plan": str(args.pair_plan),
            "pair_plan_sha256": sha256_file(args.pair_plan),
            "pair_summary": str(args.pair_summary),
            "pair_summary_sha256": sha256_file(args.pair_summary),
            "dataset_file": str(args.dataset_file),
            "dataset_file_bytes": args.dataset_file.stat().st_size,
            "dataset_file_verified_sha256": args.dataset_sha256.lower(),
            "checkpoint_file": str(args.checkpoint_file),
            "checkpoint_sha256": sha256_file(args.checkpoint_file),
            "policy": args.policy,
        },
        "encoder": {
            "model_class": type(ctx.model).__qualname__,
            "macro_encoder_class": type(ctx.model.latent_action_encoder).__qualname__,
            "frozen": not any(parameter.requires_grad for parameter in ctx.model.parameters()),
        },
        "determinism": determinism,
        "runtime": {
            "python": sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "gpu": torch.cuda.get_device_name(ctx.device),
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
