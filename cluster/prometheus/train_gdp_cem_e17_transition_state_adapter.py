#!/usr/bin/env python3
"""Train and gate the frozen E17 action-conditioned state adapter."""

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

import gdp_cem_e17_specs as spec
from gdp_cem_e15_data import sha256_file
from gdp_cem_e17_models import TransitionStateAdapter


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p2", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E17 protected path is forbidden: {path}")


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


def learning_rate(step: int) -> float:
    if step <= spec.WARMUP_STEPS:
        return spec.LEARNING_RATE * step / spec.WARMUP_STEPS
    progress = (step - spec.WARMUP_STEPS) / (
        spec.TRAIN_STEPS - spec.WARMUP_STEPS
    )
    return spec.LEARNING_RATE * 0.5 * (1.0 + math.cos(math.pi * progress))


@torch.no_grad()
def update_ema(ema: torch.nn.Module, model: torch.nn.Module) -> None:
    parameters = dict(model.named_parameters())
    for name, value in ema.named_parameters():
        value.mul_(spec.EMA_DECAY).add_(
            parameters[name], alpha=1.0 - spec.EMA_DECAY
        )
    buffers = dict(model.named_buffers())
    for name, value in ema.named_buffers():
        value.copy_(buffers[name])


def metric_summary(prediction: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    if prediction.shape != target.shape or prediction.ndim != 2:
        raise ValueError("invalid E17 metric arrays")
    error = prediction.astype(np.float64) - target.astype(np.float64)
    coordinate_rmse = np.sqrt(np.mean(np.square(error), axis=0))
    centered = target.astype(np.float64) - target.astype(np.float64).mean(axis=0)
    denominator = np.square(centered).sum(axis=0)
    coordinate_r2 = 1.0 - np.square(error).sum(axis=0) / np.maximum(
        denominator, 1.0e-12
    )
    per_example = np.sqrt(np.mean(np.square(error), axis=1))
    return {
        "rows": int(len(target)),
        "standardized_rmse": float(np.sqrt(np.mean(np.square(error)))),
        "coordinate_standardized_rmse": coordinate_rmse.tolist(),
        "maximum_coordinate_standardized_rmse": float(coordinate_rmse.max()),
        "coordinate_r2": coordinate_r2.tolist(),
        "median_coordinate_r2": float(np.median(coordinate_r2)),
        "per_example_standardized_rmse": {
            "q50": float(np.quantile(per_example, 0.50)),
            "q90": float(np.quantile(per_example, 0.90)),
            "q95": float(np.quantile(per_example, 0.95)),
            "q99": float(np.quantile(per_example, 0.99)),
            "maximum": float(per_example.max()),
        },
    }


@torch.inference_mode()
def predict(
    model: TransitionStateAdapter,
    *,
    current_latent: np.ndarray,
    terminal_latent: np.ndarray,
    current_state: np.ndarray,
    action_raw: np.ndarray,
    action_mask: np.ndarray,
    tau: np.ndarray,
    device: torch.device,
) -> np.ndarray:
    result = np.empty_like(current_state)
    for start in range(0, len(current_state), spec.VALIDATION_BATCH_SIZE):
        stop = min(start + spec.VALIDATION_BATCH_SIZE, len(current_state))
        result[start:stop] = (
            model(
                current_latent=torch.from_numpy(current_latent[start:stop]).to(
                    device
                ),
                terminal_latent=torch.from_numpy(terminal_latent[start:stop]).to(
                    device
                ),
                current_state=torch.from_numpy(current_state[start:stop]).to(device),
                action_raw=torch.from_numpy(action_raw[start:stop]).to(device),
                action_mask=torch.from_numpy(action_mask[start:stop]).to(device),
                tau=torch.from_numpy(tau[start:stop]).to(device),
            )
            .float()
            .cpu()
            .numpy()
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
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
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E17 adapter output")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E17 protocol hash differs")
    if not torch.cuda.is_available():
        raise RuntimeError("E17 adapter training requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E17 adapter GPU model differs")

    manifest = json.loads(args.cache_manifest.read_text(encoding="utf-8"))
    cache_sha = sha256_file(args.cache_h5)
    source_sha = sha256_file(args.source_manifest)
    if (
        manifest.get("status") != "ok"
        or manifest.get("kind")
        != "gdp_cem_e17_action_conditioned_transition_state_cache"
        or manifest.get("task") != args.task
        or manifest.get("output_h5_sha256") != cache_sha
        or manifest.get("input_hashes", {}).get("protocol_sha256")
        != spec.PROTOCOL_SHA256
        or manifest.get("input_hashes", {}).get("source_manifest_sha256")
        != source_sha
        or manifest.get("model_training_performed") is not False
        or manifest.get("validation_metrics_computed") is not False
        or manifest.get("p2_read") is not False
        or manifest.get("d3_metric_read") is not False
        or manifest.get("d4_metric_read") is not False
        or manifest.get("d5_read") is not False
        or manifest.get("protected_p3_p4_c1_i1_read") is not False
    ):
        raise RuntimeError("E17 transition-cache lineage differs")

    train_rows = int(manifest["train_rows"])
    validation_rows = int(manifest["validation_rows"])
    total_rows = train_rows + validation_rows
    with h5py.File(args.cache_h5, "r") as handle:
        role = np.asarray(handle["role"][:], dtype=np.uint8)
        if (
            len(role) != total_rows
            or not np.all(role[:train_rows] == 0)
            or not np.all(role[train_rows:] == 1)
            or handle.attrs.get("task") != args.task
            or handle.attrs.get("protocol_sha256") != spec.PROTOCOL_SHA256
            or handle.attrs.get("source_manifest_sha256") != source_sha
        ):
            raise RuntimeError("E17 cache role ordering or attributes differ")
        train_slice = slice(0, train_rows)
        train = {
            "current_latent": np.asarray(
                handle["current_latent"][train_slice], dtype=np.float32
            ),
            "terminal_latent": np.asarray(
                handle["terminal_latent"][train_slice], dtype=np.float32
            ),
            "current_state": np.asarray(
                handle["current_state"][train_slice], dtype=np.float32
            ),
            "next_state": np.asarray(
                handle["next_state"][train_slice], dtype=np.float32
            ),
            "action_raw": np.asarray(
                handle["action_raw"][train_slice], dtype=np.float32
            ),
            "action_mask": np.asarray(
                handle["action_mask"][train_slice], dtype=np.bool_
            ),
            "tau": np.asarray(handle["tau"][train_slice], dtype=np.int64),
        }
    validation_payload_rows_read_before_checkpoint = 0
    task_spec = spec.TASK_SPEC[args.task]
    state_dim = int(task_spec["state_dim"])
    action_dim = int(task_spec["primitive_action_dim"])
    if (
        train["current_latent"].shape != (train_rows, spec.LATENT_DIM)
        or train["terminal_latent"].shape != (train_rows, spec.LATENT_DIM)
        or train["current_state"].shape != (train_rows, state_dim)
        or train["next_state"].shape != (train_rows, state_dim)
        or train["action_raw"].shape
        != (train_rows, spec.ACTION_HORIZON, action_dim)
        or train["action_mask"].shape != (train_rows, spec.ACTION_HORIZON)
        or set(np.unique(train["tau"]).tolist()) != set(spec.TAU_VALUES)
        or np.any(train["action_raw"][~train["action_mask"]] != 0)
        or not all(np.isfinite(value).all() for value in train.values())
    ):
        raise RuntimeError("E17 train-only payload differs")

    torch.manual_seed(spec.MODEL_SEED)
    np.random.seed(spec.MODEL_SEED)
    torch.cuda.manual_seed_all(spec.MODEL_SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    started = time.time()
    model = TransitionStateAdapter(
        state_dim=state_dim, action_dim=action_dim
    ).to(device)
    ema = copy.deepcopy(model).eval().requires_grad_(False)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=spec.LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=spec.WEIGHT_DECAY,
    )
    batch_generator = torch.Generator(device="cpu").manual_seed(
        spec.derived_seed(f"batches|task={args.task}")
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "training.jsonl"
    checkpoint_path = args.output_dir / "final.pt"
    last_loss = float("nan")
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for step in range(1, spec.TRAIN_STEPS + 1):
            rows = torch.randint(
                train_rows,
                (spec.BATCH_SIZE,),
                generator=batch_generator,
            ).numpy()
            batch = {
                name: torch.from_numpy(value[rows]).to(device)
                for name, value in train.items()
                if name != "next_state"
            }
            target = torch.from_numpy(train["next_state"][rows]).to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                prediction = model(**batch)
            loss = (prediction.float() - target).square().mean()
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite E17 adapter loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), spec.GRADIENT_CLIP)
            rate = learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            update_ema(ema, model)
            last_loss = float(loss.detach().cpu())
            if step == 1 or step % 1_000 == 0 or step == spec.TRAIN_STEPS:
                trace.write(
                    json.dumps(
                        {"step": step, "loss": last_loss, "learning_rate": rate},
                        sort_keys=True,
                    )
                    + "\n"
                )
                trace.flush()

    checkpoint = {
        "kind": "gdp_cem_e17_final_transition_state_adapter",
        "task": args.task,
        "seed": spec.MODEL_SEED,
        "architecture": {
            "latent_dim": spec.LATENT_DIM,
            "state_dim": state_dim,
            "action_dim": action_dim,
            "input_dim": model.input_dim,
            "width": spec.MODEL_WIDTH,
            "residual_blocks": spec.MODEL_RESIDUAL_BLOCKS,
        },
        "ema_state_dict": {
            key: value.detach().cpu().clone() for key, value in ema.state_dict().items()
        },
        "final_step": spec.TRAIN_STEPS,
        "train_rows": train_rows,
        "cache_h5_sha256": cache_sha,
        "cache_manifest_sha256": sha256_file(args.cache_manifest),
        "validation_payload_rows_read_before_checkpoint": (
            validation_payload_rows_read_before_checkpoint
        ),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": source_sha,
    }
    atomic_torch_save(checkpoint_path, checkpoint)
    checkpoint_sha = sha256_file(checkpoint_path)
    del train

    # Role-1 payload is opened only after the immutable final checkpoint exists.
    with h5py.File(args.cache_h5, "r") as handle:
        validation_slice = slice(train_rows, total_rows)
        validation = {
            "current_latent": np.asarray(
                handle["current_latent"][validation_slice], dtype=np.float32
            ),
            "terminal_latent": np.asarray(
                handle["terminal_latent"][validation_slice], dtype=np.float32
            ),
            "current_state": np.asarray(
                handle["current_state"][validation_slice], dtype=np.float32
            ),
            "next_state": np.asarray(
                handle["next_state"][validation_slice], dtype=np.float32
            ),
            "action_raw": np.asarray(
                handle["action_raw"][validation_slice], dtype=np.float32
            ),
            "action_mask": np.asarray(
                handle["action_mask"][validation_slice], dtype=np.bool_
            ),
            "tau": np.asarray(handle["tau"][validation_slice], dtype=np.int64),
        }
    prediction = predict(
        ema,
        current_latent=validation["current_latent"],
        terminal_latent=validation["terminal_latent"],
        current_state=validation["current_state"],
        action_raw=validation["action_raw"],
        action_mask=validation["action_mask"],
        tau=validation["tau"],
        device=device,
    )
    overall = metric_summary(prediction, validation["next_state"])
    copy_current = metric_summary(
        validation["current_state"], validation["next_state"]
    )
    ratio = overall["standardized_rmse"] / copy_current["standardized_rmse"]
    by_tau: dict[str, Any] = {}
    tau_passes = []
    for tau_value in spec.TAU_VALUES:
        rows = validation["tau"] == tau_value
        model_metrics = metric_summary(
            prediction[rows], validation["next_state"][rows]
        )
        baseline_metrics = metric_summary(
            validation["current_state"][rows], validation["next_state"][rows]
        )
        passed = bool(
            model_metrics["standardized_rmse"] <= spec.TAU_RMSE_MAX
            and model_metrics["median_coordinate_r2"]
            >= spec.TAU_MEDIAN_COORDINATE_R2_MIN
        )
        tau_passes.append(passed)
        by_tau[str(tau_value)] = {
            "model": model_metrics,
            "copy_current": baseline_metrics,
            "passed": passed,
        }
    finite = bool(
        np.isfinite(prediction).all()
        and all(
            np.isfinite(value).all()
            for value in validation.values()
            if isinstance(value, np.ndarray)
        )
    )
    passed = bool(
        finite
        and overall["standardized_rmse"] <= spec.OVERALL_RMSE_MAX
        and overall["maximum_coordinate_standardized_rmse"]
        <= spec.MAX_COORDINATE_RMSE_MAX
        and overall["median_coordinate_r2"] >= spec.MEDIAN_COORDINATE_R2_MIN
        and ratio <= spec.COPY_CURRENT_RMSE_RATIO_MAX
        and all(tau_passes)
    )
    gate = {
        "passed": passed,
        "finite": finite,
        "model": overall,
        "copy_current": copy_current,
        "model_to_copy_current_rmse_ratio": ratio,
        "by_tau": by_tau,
        "prediction_sha256": array_sha256(prediction),
        "thresholds": {
            "overall_standardized_rmse_max": spec.OVERALL_RMSE_MAX,
            "maximum_coordinate_standardized_rmse_max": (
                spec.MAX_COORDINATE_RMSE_MAX
            ),
            "median_coordinate_r2_min": spec.MEDIAN_COORDINATE_R2_MIN,
            "copy_current_rmse_ratio_max": spec.COPY_CURRENT_RMSE_RATIO_MAX,
            "per_tau_standardized_rmse_max": spec.TAU_RMSE_MAX,
            "per_tau_median_coordinate_r2_min": (
                spec.TAU_MEDIAN_COORDINATE_R2_MIN
            ),
        },
    }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e17_transition_state_adapter_preflight",
        "analysis_role": "P1_train_then_fixed_P1_role1_gate",
        "task": args.task,
        "seed": spec.MODEL_SEED,
        "architecture": checkpoint["architecture"],
        "final_step": spec.TRAIN_STEPS,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "train_rows": train_rows,
        "validation_rows": validation_rows,
        "training_final_loss": last_loss,
        "adapter_gate": gate,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "training_trace": str(trace_path),
        "training_trace_sha256": sha256_file(trace_path),
        "cache_h5_sha256": cache_sha,
        "cache_manifest_sha256": sha256_file(args.cache_manifest),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(
            torch.cuda.max_memory_allocated(device)
        ),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": source_sha,
        "runtime": {
            "python": platform.python_version(),
            "torch": metadata.version("torch"),
            "numpy": metadata.version("numpy"),
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
        },
        "final_checkpoint_written_before_validation_open": True,
        "validation_payload_rows_read_before_checkpoint": 0,
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
    (args.output_dir / "sha256.txt").write_text(
        checksum, encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
