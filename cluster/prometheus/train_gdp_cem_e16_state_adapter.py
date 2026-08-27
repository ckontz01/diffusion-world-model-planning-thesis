#!/usr/bin/env python3
"""Train and validate the frozen E16 latent-to-state interface adapter."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import re
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

import gdp_cem_e15_specs as e15
import gdp_cem_e16_specs as spec
from gdp_cem_e15_data import E15ArrayStore, E15TrainingStore, sha256_file
from gdp_cem_e16_models import LatentStateAdapter


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E16 protected path is forbidden: {path}")


def atomic_json(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def atomic_torch_save(path: Path, value: Any) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("xb") as stream:
            torch.save(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def array_sha256(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def unique_role_rows(cache_h5: Path, *, role: int) -> np.ndarray:
    if role not in (0, 1):
        raise ValueError("invalid E16 adapter role")
    with h5py.File(cache_h5, "r") as handle:
        source = np.asarray(handle["source_index"][:], dtype=np.int64)
        roles = np.asarray(handle["role"][:], dtype=np.uint8)
    rows = np.flatnonzero(roles == role).astype(np.int64)
    _, first = np.unique(source[rows], return_index=True)
    result = np.sort(rows[first]).astype(np.int64)
    if (
        len(result) == 0
        or np.any(roles[result] != role)
        or len(np.unique(source[result])) != len(result)
    ):
        raise RuntimeError("invalid E16 unique adapter rows")
    return result


def learning_rate(step: int) -> float:
    if step <= spec.ADAPTER_WARMUP_STEPS:
        return spec.ADAPTER_LEARNING_RATE * step / spec.ADAPTER_WARMUP_STEPS
    progress = (step - spec.ADAPTER_WARMUP_STEPS) / (
        spec.ADAPTER_STEPS - spec.ADAPTER_WARMUP_STEPS
    )
    return spec.ADAPTER_LEARNING_RATE * 0.5 * (1.0 + math.cos(math.pi * progress))


@torch.no_grad()
def update_ema(ema: torch.nn.Module, model: torch.nn.Module) -> None:
    parameters = dict(model.named_parameters())
    for name, value in ema.named_parameters():
        value.mul_(spec.ADAPTER_EMA_DECAY).add_(
            parameters[name], alpha=1.0 - spec.ADAPTER_EMA_DECAY
        )
    buffers = dict(model.named_buffers())
    for name, value in ema.named_buffers():
        value.copy_(buffers[name])


@torch.inference_mode()
def validate(
    model: LatentStateAdapter,
    *,
    current: np.ndarray,
    state: np.ndarray,
    device: torch.device,
    batch_size: int = 4096,
) -> dict[str, Any]:
    prediction = np.empty_like(state)
    for start in range(0, len(current), batch_size):
        stop = min(start + batch_size, len(current))
        prediction[start:stop] = (
            model(torch.from_numpy(current[start:stop]).to(device))
            .float()
            .cpu()
            .numpy()
        )
    error = prediction.astype(np.float64) - state.astype(np.float64)
    coordinate_rmse = np.sqrt(np.mean(np.square(error), axis=0))
    rmse = float(np.sqrt(np.mean(np.square(error))))
    centered = state.astype(np.float64) - state.astype(np.float64).mean(axis=0)
    denominator = np.square(centered).sum(axis=0)
    r2 = 1.0 - np.square(error).sum(axis=0) / np.maximum(denominator, 1.0e-12)
    passed = bool(
        np.isfinite(prediction).all()
        and rmse <= spec.ADAPTER_RMSE_MAX
        and float(coordinate_rmse.max()) <= spec.ADAPTER_COORDINATE_RMSE_MAX
        and float(np.median(r2)) >= spec.ADAPTER_MEDIAN_R2_MIN
    )
    return {
        "passed": passed,
        "rows": int(len(current)),
        "standardized_rmse": rmse,
        "coordinate_standardized_rmse": coordinate_rmse.tolist(),
        "maximum_coordinate_standardized_rmse": float(coordinate_rmse.max()),
        "coordinate_r2": r2.tolist(),
        "median_coordinate_r2": float(np.median(r2)),
        "prediction_sha256": array_sha256(prediction),
        "thresholds": {
            "standardized_rmse_max": spec.ADAPTER_RMSE_MAX,
            "maximum_coordinate_standardized_rmse_max": (
                spec.ADAPTER_COORDINATE_RMSE_MAX
            ),
            "median_coordinate_r2_min": spec.ADAPTER_MEDIAN_R2_MIN,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E16 protocol hash differs")
    if sha256_file(args.source_manifest) == "":
        raise RuntimeError("E16 source manifest is empty")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E16 adapter output")
    if not torch.cuda.is_available():
        raise RuntimeError("E16 adapter training requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E16 adapter GPU model differs")

    torch.manual_seed(spec.ADAPTER_SEED)
    np.random.seed(spec.ADAPTER_SEED)
    torch.cuda.manual_seed_all(spec.ADAPTER_SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    started = time.time()
    train_store = E15TrainingStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    if train_store.validation_payload_rows_read != 0:
        raise RuntimeError("E16 adapter training opened E15 validation payload")
    train_global_rows = unique_role_rows(args.cache_h5, role=0)
    if np.any(train_global_rows >= e15.TRAIN_ROWS):
        raise RuntimeError("E16 adapter train rows cross the role boundary")
    train_current = np.ascontiguousarray(train_store.current[train_global_rows])
    train_state = np.ascontiguousarray(train_store.state[train_global_rows])
    model = LatentStateAdapter(
        latent_dim=spec.LATENT_DIM,
        state_dim=train_store.state_dim,
    ).to(device)
    ema = copy.deepcopy(model).eval().requires_grad_(False)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=spec.ADAPTER_LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=spec.ADAPTER_WEIGHT_DECAY,
    )
    batch_generator = torch.Generator(device="cpu").manual_seed(
        spec.derived_seed(f"adapter-batches|task={args.task}")
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "training.jsonl"
    checkpoint_path = args.output_dir / "final.pt"
    last_loss = float("nan")
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for step in range(1, spec.ADAPTER_STEPS + 1):
            positions = torch.randint(
                len(train_current),
                (spec.ADAPTER_BATCH_SIZE,),
                generator=batch_generator,
            ).numpy()
            current = torch.from_numpy(train_current[positions]).to(device)
            state = torch.from_numpy(train_state[positions]).to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                prediction = model(current)
            loss = (prediction.float() - state).square().mean()
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite E16 adapter loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), spec.ADAPTER_GRADIENT_CLIP)
            rate = learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            update_ema(ema, model)
            last_loss = float(loss.detach().cpu())
            if step == 1 or step % 1000 == 0 or step == spec.ADAPTER_STEPS:
                record = {"step": step, "loss": last_loss, "learning_rate": rate}
                trace.write(json.dumps(record, sort_keys=True) + "\n")
                trace.flush()

    checkpoint = {
        "kind": "gdp_cem_e16_final_latent_state_adapter",
        "task": args.task,
        "seed": spec.ADAPTER_SEED,
        "architecture": {
            "latent_dim": spec.LATENT_DIM,
            "state_dim": train_store.state_dim,
            "width": spec.ADAPTER_WIDTH,
        },
        "ema_state_dict": {
            key: value.detach().cpu().clone() for key, value in ema.state_dict().items()
        },
        "final_step": spec.ADAPTER_STEPS,
        "train_unique_rows": len(train_global_rows),
        "train_unique_rows_sha256": array_sha256(train_global_rows),
        "validation_payload_rows_read_before_checkpoint": 0,
        "lineage": train_store.lineage,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
    }
    atomic_torch_save(checkpoint_path, checkpoint)
    checkpoint_sha = sha256_file(checkpoint_path)

    # The final checkpoint now exists. Only after this point may role-1 payload
    # be opened for the fixed, non-selective adapter validity audit.
    validation_store = E15ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    validation_global_rows = unique_role_rows(args.cache_h5, role=1)
    result = validate(
        ema,
        current=np.ascontiguousarray(validation_store.current[validation_global_rows]),
        state=np.ascontiguousarray(validation_store.state[validation_global_rows]),
        device=device,
    )
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e16_latent_state_adapter_training_and_gate",
        "analysis_role": "P1_train_fit_then_P1_validation_fixed_adapter_gate",
        "task": args.task,
        "seed": spec.ADAPTER_SEED,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "train_unique_rows": len(train_global_rows),
        "validation_unique_rows": len(validation_global_rows),
        "training_final_loss": last_loss,
        "adapter_gate": result,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "training_trace": str(trace_path),
        "training_trace_sha256": sha256_file(trace_path),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "runtime": {
            "python": platform.python_version(),
            "torch": metadata.version("torch"),
            "numpy": metadata.version("numpy"),
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
        },
        "validation_checkpoint_selection": False,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, summary)
    checksum = "".join(
        f"{sha256_file(args.output_dir / name)}  {name}\n"
        for name in ("final.pt", "training.jsonl", "summary.json")
    )
    (args.output_dir / "sha256.txt").write_text(checksum, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
