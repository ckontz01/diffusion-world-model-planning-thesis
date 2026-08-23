#!/usr/bin/env python3
"""Train one frozen E14 VAD/CVD diffusion or matched Gaussian endpoint."""

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

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import E14ArrayStore, GoalMode, sha256_file
from gdp_cem_e14_models import (
    CosineSchedule,
    Endpoint,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    endpoint_output_dim,
    velocity_target,
)


CONDITIONS = tuple(
    f"{endpoint}_{family}"
    for endpoint in ("vad", "cvd")
    for family in ("true", "gaussian", "shuffled_goal", "unconditional")
)


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "d4", "d5", "p3", "p4", "c1", "i1"}):
        raise RuntimeError(f"E14 protected path is forbidden: {path}")


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


def array_sha256(value: np.ndarray | torch.Tensor) -> str:
    if torch.is_tensor(value):
        value = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


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
        raise ValueError("E14 masked-mean shapes differ")
    weight = mask.to(value.dtype)
    denominator = weight.sum(dim=-1)
    if torch.any(denominator <= 0):
        raise RuntimeError("E14 endpoint row has no active target dimensions")
    return ((value * weight).sum(dim=-1) / denominator).mean()


@torch.inference_mode()
def validate(
    model: torch.nn.Module,
    *,
    store: E14ArrayStore,
    rows: np.ndarray,
    endpoint: Endpoint,
    family: str,
    timestep_bank: torch.Tensor,
    noise_bank: torch.Tensor,
    schedule: CosineSchedule,
    device: torch.device,
) -> dict[str, float]:
    objective_parts: list[torch.Tensor] = []
    error_parts: list[torch.Tensor] = []
    goal_mode: GoalMode = "shuffled" if family == "shuffled_goal" else "true"
    model.eval()
    for start in range(0, len(rows), spec.VALIDATION_BATCH_SIZE):
        stop = min(start + spec.VALIDATION_BATCH_SIZE, len(rows))
        batch = store.batch(rows[start:stop], goal_mode=goal_mode)
        clean, mask = batch.endpoint_target(endpoint)
        current = batch.current.to(device)
        goal = batch.goal.to(device)
        state = batch.state.to(device)
        delta = batch.delta.to(device)
        tau = batch.tau.to(device)
        clean = clean.to(device)
        mask = mask.to(device)
        if family == "gaussian":
            assert isinstance(model, VariableDiagonalGaussian)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                mean, log_std = model(current, goal, state, delta, tau)
            mean = mean.float()
            log_std = log_std.float()
            standardized = (clean - mean) / log_std.exp()
            element = 0.5 * standardized.square() + log_std + 0.5 * math.log(
                2.0 * math.pi
            )
            weight = mask.to(element.dtype)
            objective_parts.append(
                ((element * weight).sum(dim=-1) / weight.sum(dim=-1)).cpu()
            )
            error_parts.append(
                (((mean - clean).square() * weight).sum(dim=-1) / weight.sum(dim=-1)).cpu()
            )
        else:
            assert isinstance(model, VariableVelocityDiffusion)
            timestep = timestep_bank[start:stop].to(device)
            noise = noise_bank[start:stop].to(device)
            alpha = schedule.alpha_bar.to(device)[timestep, None]
            noisy = (
                alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
            ) * mask
            target = velocity_target(clean, noise, alpha) * mask
            conditioned = family != "unconditional"
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
            error = (prediction.float() - target).square()
            weight = mask.to(error.dtype)
            objective_parts.append(
                ((error * weight).sum(dim=-1) / weight.sum(dim=-1)).cpu()
            )
            error_parts.append(
                (((prediction.float() * weight) - (target * weight)).abs().sum(dim=-1)
                 / weight.sum(dim=-1)).cpu()
            )
    objective = float(torch.cat(objective_parts).double().mean())
    secondary = float(torch.cat(error_parts).double().mean())
    return {
        "family_objective": objective,
        "masked_mean_absolute_error": secondary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--seed", type=int, choices=spec.MODEL_SEEDS, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    endpoint, family = args.condition.split("_", maxsplit=1)
    if endpoint not in ("vad", "cvd"):
        raise RuntimeError("invalid E14 endpoint condition")
    if family in ("shuffled_goal", "unconditional") and args.seed != spec.DIAGNOSTIC_SEED:
        raise RuntimeError("E14 diagnostic controls are frozen to seed 6101")
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
        raise RuntimeError("E14 protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E14 training output")

    started = time.time()
    store = E14ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    checkpoint_rows = store.checkpoint_validation_rows(seed=args.seed)
    output_dim = endpoint_output_dim(
        endpoint,
        latent_dim=store.latent_dim,
        primitive_action_dim=store.primitive_action_dim,
        horizon=spec.ACTION_HORIZON,
    )
    config = {
        "latent_dim": store.latent_dim,
        "state_dim": store.state_dim,
        "output_dim": output_dim,
        "width": spec.MODEL_WIDTH,
        "depth": spec.MODEL_DEPTH,
        "time_embedding_dim": spec.TIME_EMBEDDING_DIM,
    }
    gaussian = family == "gaussian"

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E14 endpoint training requires CUDA")
    device = torch.device("cuda")
    model: torch.nn.Module = (
        VariableDiagonalGaussian(**config)
        if gaussian
        else VariableVelocityDiffusion(**config)
    )
    model = model.to(device)
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
    validation_generator = torch.Generator(device="cpu").manual_seed(
        spec.derived_seed(
            f"checkpoint-noise|task={args.task}|condition={args.condition}|seed={args.seed}"
        )
    )
    validation_timestep = torch.randint(
        0,
        spec.DIFFUSION_STEPS,
        (len(checkpoint_rows),),
        generator=validation_generator,
    )
    validation_noise = torch.randn(
        len(checkpoint_rows), output_dim, generator=validation_generator
    )
    goal_mode: GoalMode = "shuffled" if family == "shuffled_goal" else "true"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "training.jsonl"
    checkpoint_path = args.output_dir / "best.pt"
    best_objective = math.inf
    best_step = -1
    best_validation: dict[str, float] | None = None
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for step in range(1, spec.TRAIN_STEPS + 1):
            model.train()
            positions = torch.randint(
                len(store.train_rows),
                (spec.BATCH_SIZE,),
                generator=batch_generator,
            ).numpy()
            rows = store.train_rows[positions]
            batch = store.batch(rows, goal_mode=goal_mode)
            clean, mask = batch.endpoint_target(endpoint)
            current = batch.current.to(device)
            goal = batch.goal.to(device)
            state = batch.state.to(device)
            delta = batch.delta.to(device)
            tau = batch.tau.to(device)
            clean = clean.to(device)
            mask = mask.to(device)
            optimizer.zero_grad(set_to_none=True)
            if gaussian:
                assert isinstance(model, VariableDiagonalGaussian)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    mean, log_std = model(current, goal, state, delta, tau)
                mean = mean.float()
                log_std = log_std.float()
                standardized = (clean - mean) / log_std.exp()
                element = 0.5 * standardized.square() + log_std + 0.5 * math.log(
                    2.0 * math.pi
                )
                loss = masked_mean(element, mask)
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
                    clean.shape,
                    generator=noise_generator,
                    device=device,
                    dtype=clean.dtype,
                )
                alpha = alpha_bar[timestep, None]
                noisy = (
                    alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
                ) * mask
                target = velocity_target(clean, noise, alpha) * mask
                if family == "unconditional":
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
                loss = masked_mean((prediction.float() - target).square(), mask)
            if not torch.isfinite(loss):
                raise RuntimeError("E14 training loss is non-finite")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), spec.GRADIENT_CLIP
            )
            if not torch.isfinite(gradient_norm):
                raise RuntimeError("E14 gradient norm is non-finite")
            rate = learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            update_ema(ema, model)

            if step % spec.VALIDATION_EVERY == 0:
                metrics = validate(
                    ema,
                    store=store,
                    rows=checkpoint_rows,
                    endpoint=endpoint,
                    family=family,
                    timestep_bank=validation_timestep,
                    noise_bank=validation_noise,
                    schedule=schedule,
                    device=device,
                )
                record = {
                    "step": step,
                    "train_objective": float(loss.detach().cpu()),
                    "gradient_norm": float(gradient_norm.detach().cpu()),
                    "learning_rate": rate,
                    "validation": metrics,
                }
                trace.write(json.dumps(record, sort_keys=True) + "\n")
                trace.flush()
                if metrics["family_objective"] < best_objective:
                    best_objective = metrics["family_objective"]
                    best_step = step
                    best_validation = metrics
                    payload = {
                        "kind": "gdp_cem_e14_p1_endpoint_checkpoint",
                        "task": args.task,
                        "condition": args.condition,
                        "endpoint": endpoint,
                        "family": family,
                        "seed": args.seed,
                        "model_kind": "diagonal_gaussian" if gaussian else "velocity_diffusion",
                        "model_config": config,
                        "state_dict": cpu_state_dict(model),
                        "ema_state_dict": cpu_state_dict(ema),
                        "diffusion_steps": None if gaussian else spec.DIFFUSION_STEPS,
                        "condition_dropout": None if gaussian or family == "unconditional" else spec.CONDITION_DROPOUT,
                        "guidance_scale": None if gaussian else (0.0 if family == "unconditional" else spec.GUIDANCE_SCALE),
                        "best_step": best_step,
                        "best_validation": best_validation,
                        "parameter_count": parameter_count,
                        "checkpoint_validation_rows": torch.from_numpy(checkpoint_rows),
                        "checkpoint_validation_rows_sha256": array_sha256(checkpoint_rows),
                        "latent_mean": torch.from_numpy(store.latent_mean),
                        "latent_std": torch.from_numpy(store.latent_std),
                        "state_mean": torch.from_numpy(store.state_mean),
                        "state_std": torch.from_numpy(store.state_std),
                        "action_mean": torch.from_numpy(store.action_mean),
                        "action_std": torch.from_numpy(store.action_std),
                        "action_robust_low": torch.from_numpy(store.action_robust_low),
                        "action_robust_high": torch.from_numpy(store.action_robust_high),
                        "local_residual_mean": torch.from_numpy(store.local_residual_mean),
                        "local_residual_std": torch.from_numpy(store.local_residual_std),
                        "lineage": store.lineage,
                        "protocol_sha256": spec.PROTOCOL_SHA256,
                        "source_manifest_sha256": sha256_file(args.source_manifest),
                    }
                    atomic_torch_save(checkpoint_path, payload)

    if best_step < 0 or best_validation is None or not checkpoint_path.is_file():
        raise RuntimeError("E14 training produced no checkpoint")
    torch.cuda.synchronize()
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e14_p1_endpoint_training",
        "analysis_role": "P1_only_long_horizon_method_development",
        "task": args.task,
        "condition": args.condition,
        "endpoint": endpoint,
        "family": family,
        "seed": args.seed,
        "model_kind": "diagonal_gaussian" if gaussian else "velocity_diffusion",
        "model_config": config,
        "parameter_count": parameter_count,
        "optimization": {
            "optimizer": "AdamW",
            "peak_learning_rate": spec.LEARNING_RATE,
            "warmup_steps": spec.WARMUP_STEPS,
            "weight_decay": spec.WEIGHT_DECAY,
            "batch_size": spec.BATCH_SIZE,
            "train_steps": spec.TRAIN_STEPS,
            "ema_decay": spec.EMA_DECAY,
            "condition_dropout": None if gaussian or family == "unconditional" else spec.CONDITION_DROPOUT,
        },
        "best_step": best_step,
        "best_validation": best_validation,
        "checkpoint_validation_rows_sha256": array_sha256(checkpoint_rows),
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "training_trace": str(trace_path),
        "training_trace_sha256": sha256_file(trace_path),
        "lineage": store.lineage,
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

