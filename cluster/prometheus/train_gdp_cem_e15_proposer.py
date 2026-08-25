#!/usr/bin/env python3
"""Train one frozen E15 proposer without opening validation payload rows."""

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

import numpy as np
import torch

import gdp_cem_e15_specs as spec
from gdp_cem_e15_data import E15TrainingStore, GoalMode, sha256_file
from gdp_cem_e15_models import (
    CosineSchedule,
    DirectTrajectoryGMM,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    direct_gmm_loss,
    instantiate_model,
    model_config,
    velocity_target,
)


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E15 protected path is forbidden: {path}")


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


def cpu_state_dict(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {
        key: value.detach().cpu().clone() for key, value in model.state_dict().items()
    }


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


def learning_rate(step: int) -> float:
    if step <= spec.WARMUP_STEPS:
        return spec.LEARNING_RATE * step / spec.WARMUP_STEPS
    progress = (step - spec.WARMUP_STEPS) / (
        spec.TRAIN_STEPS - spec.WARMUP_STEPS
    )
    return spec.LEARNING_RATE * 0.5 * (1.0 + math.cos(math.pi * progress))


def masked_mean(value: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    if value.shape != mask.shape:
        raise ValueError("E15 masked-mean shape differs")
    weight = mask.to(value.dtype)
    denominator = weight.sum(dim=-1)
    if torch.any(denominator <= 0):
        raise RuntimeError("E15 training row has no active action dimensions")
    return ((value * weight).sum(dim=-1) / denominator).mean()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--condition", choices=spec.TRAINING_CONDITIONS, required=True)
    parser.add_argument("--seed", type=int, choices=spec.MODEL_SEEDS, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.condition in ("vad_shuffled", "vad_unconditional") and args.seed != spec.NULL_SEED:
        raise RuntimeError("E15 conditioning nulls are frozen to seed 7201")
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
        raise RuntimeError("E15 protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E15 training output")
    if not torch.cuda.is_available():
        raise RuntimeError("E15 proposer training requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E15 training GPU model differs")

    started = time.time()
    store = E15TrainingStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    if store.validation_payload_rows_read != 0:
        raise RuntimeError("E15 training opened validation payload rows")
    config = model_config(args.task, args.condition)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    model = instantiate_model(args.task, args.condition).to(device)
    ema = copy.deepcopy(model).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=spec.LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=spec.WEIGHT_DECAY,
    )
    schedule = CosineSchedule.build(spec.DIFFUSION_STEPS)
    alpha_bar = schedule.alpha_bar.to(device)
    batch_generator = torch.Generator(device="cpu").manual_seed(
        spec.derived_seed(
            f"training-batches|task={args.task}|condition={args.condition}|seed={args.seed}"
        )
    )
    noise_generator = torch.Generator(device=device).manual_seed(
        spec.derived_seed(
            f"training-noise|task={args.task}|condition={args.condition}|seed={args.seed}"
        )
    )
    dropout_generator = torch.Generator(device=device).manual_seed(
        spec.derived_seed(
            f"training-dropout|task={args.task}|condition={args.condition}|seed={args.seed}"
        )
    )
    goal_mode: GoalMode = "shuffled" if args.condition == "vad_shuffled" else "true"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "training.jsonl"
    checkpoint_path = args.output_dir / "final.pt"
    last_record: dict[str, Any] | None = None
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for step in range(1, spec.TRAIN_STEPS + 1):
            model.train()
            positions = torch.randint(
                len(store.train_rows),
                (spec.BATCH_SIZE,),
                generator=batch_generator,
            ).numpy()
            batch = store.batch(store.train_rows[positions], goal_mode=goal_mode)
            current = batch.current.to(device)
            goal = batch.goal.to(device)
            state = batch.state.to(device)
            delta = batch.delta.to(device)
            tau = batch.tau.to(device)
            target_3d = batch.action_u.to(device)
            mask_2d = batch.action_mask.to(device)
            target_flat, mask_flat = batch.flat_target()
            target_flat = target_flat.to(device)
            mask_flat = mask_flat.to(device)
            optimizer.zero_grad(set_to_none=True)
            components: dict[str, float] = {}
            if args.condition == "diagonal_gaussian":
                assert isinstance(model, VariableDiagonalGaussian)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    mean, log_std = model(current, goal, state, delta, tau)
                mean = mean.float()
                log_std = log_std.float()
                standardized = (target_flat - mean) / log_std.exp()
                element = (
                    0.5 * standardized.square()
                    + log_std
                    + 0.5 * math.log(2.0 * math.pi)
                )
                loss = masked_mean(element, mask_flat)
            elif args.condition == "direct_gmm":
                assert isinstance(model, DirectTrajectoryGMM)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    logits, means, log_stds = model(
                        current, goal, state, delta, tau
                    )
                loss, nll, balance = direct_gmm_loss(
                    logits.float(),
                    means.float(),
                    log_stds.float(),
                    target_3d,
                    mask_2d,
                )
                components = {
                    "normalized_nll": float(nll.detach().cpu()),
                    "mode_balance_kl": float(balance.detach().cpu()),
                }
            else:
                assert isinstance(model, VariableVelocityDiffusion)
                timestep = torch.randint(
                    0,
                    spec.DIFFUSION_STEPS,
                    (spec.BATCH_SIZE,),
                    generator=noise_generator,
                    device=device,
                )
                noise = torch.randn(
                    target_flat.shape,
                    generator=noise_generator,
                    device=device,
                    dtype=target_flat.dtype,
                )
                alpha = alpha_bar[timestep, None]
                noisy = (
                    alpha.sqrt() * target_flat
                    + (1.0 - alpha).sqrt() * noise
                ) * mask_flat
                target_velocity = velocity_target(target_flat, noise, alpha) * mask_flat
                if args.condition == "vad_unconditional":
                    conditioned: bool | torch.Tensor = False
                else:
                    conditioned = torch.rand(
                        spec.BATCH_SIZE,
                        generator=dropout_generator,
                        device=device,
                    ) >= spec.CONDITION_DROPOUT
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    prediction = model(
                        current,
                        goal,
                        state,
                        delta,
                        tau,
                        noisy,
                        timestep,
                        conditioned=conditioned,
                    )
                loss = masked_mean(
                    (prediction.float() - target_velocity).square(), mask_flat
                )
            if not torch.isfinite(loss):
                raise RuntimeError("E15 training loss is non-finite")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), spec.GRADIENT_CLIP
            )
            if not torch.isfinite(gradient_norm):
                raise RuntimeError("E15 gradient norm is non-finite")
            rate = learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            update_ema(ema, model)
            if step % spec.LOG_EVERY == 0 or step == spec.TRAIN_STEPS:
                last_record = {
                    "step": step,
                    "train_objective": float(loss.detach().cpu()),
                    "gradient_norm": float(gradient_norm.detach().cpu()),
                    "learning_rate": rate,
                    **components,
                }
                trace.write(json.dumps(last_record, sort_keys=True) + "\n")
                trace.flush()

    if last_record is None or last_record["step"] != spec.TRAIN_STEPS:
        raise RuntimeError("E15 training did not reach the frozen final step")
    torch.cuda.synchronize()
    checkpoint = {
        "kind": "gdp_cem_e15_p1_final_proposer_checkpoint",
        "task": args.task,
        "condition": args.condition,
        "seed": args.seed,
        "model_config": config,
        "state_dict": cpu_state_dict(model),
        "ema_state_dict": cpu_state_dict(ema),
        "final_step": spec.TRAIN_STEPS,
        "final_train_record": last_record,
        "parameter_count": parameter_count,
        "statistics": {
            "latent_mean": torch.from_numpy(store.latent_mean),
            "latent_std": torch.from_numpy(store.latent_std),
            "state_mean": torch.from_numpy(store.state_mean),
            "state_std": torch.from_numpy(store.state_std),
            "u_mean": torch.from_numpy(store.u_mean),
            "u_std": torch.from_numpy(store.u_std),
            "planner_action_mean": torch.from_numpy(store.planner_action_mean),
            "planner_action_std": torch.from_numpy(store.planner_action_std),
            "interior_scale": store.interior_scale,
            "target_raw_limit": store.target_raw_limit,
        },
        "lineage": store.lineage,
        "validation_payload_rows_read": store.validation_payload_rows_read,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
    }
    atomic_torch_save(checkpoint_path, checkpoint)
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e15_p1_final_proposer_training",
        "analysis_role": "P1_train_only_long_horizon_method_development",
        "task": args.task,
        "condition": args.condition,
        "seed": args.seed,
        "model_config": config,
        "parameter_count": parameter_count,
        "optimization": {
            "optimizer": "AdamW",
            "peak_learning_rate": spec.LEARNING_RATE,
            "warmup_steps": spec.WARMUP_STEPS,
            "weight_decay": spec.WEIGHT_DECAY,
            "batch_size": spec.BATCH_SIZE,
            "train_steps": spec.TRAIN_STEPS,
            "gradient_clip": spec.GRADIENT_CLIP,
            "ema_decay": spec.EMA_DECAY,
            "condition_dropout": (
                spec.CONDITION_DROPOUT
                if args.condition in ("vad", "vad_shuffled")
                else None
            ),
            "gmm_modes": spec.GMM_MODES if args.condition == "direct_gmm" else None,
            "gmm_balance_weight": (
                spec.GMM_BALANCE_WEIGHT if args.condition == "direct_gmm" else None
            ),
        },
        "checkpoint_selection": "fixed_final_ema_step_30000_no_validation_access",
        "final_train_record": last_record,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "training_trace": str(trace_path),
        "training_trace_sha256": sha256_file(trace_path),
        "lineage": store.lineage,
        "training_rows": spec.TRAIN_ROWS,
        "validation_payload_rows_read": store.validation_payload_rows_read,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "trainer_source_sha256": sha256_file(Path(__file__)),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "peak_cuda_memory_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "h5py": metadata.version("h5py"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
        },
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
