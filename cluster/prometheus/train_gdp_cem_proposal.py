#!/usr/bin/env python3
"""Train one frozen P1-only GDP-CEM action-sequence proposal model."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    CosineDiffusionSchedule,
    JointActionDiffusion,
)


CONDITIONS = ("diffusion_true", "diffusion_shuffled_goal", "gaussian_true")
PROTOCOL_SHA256 = "b49e29adde3f1b0ce79c3a602f5a1af6a4159899a7941fb0f6cc30971bdb017b"
CACHE_PROTOCOL_SHA256 = "50690a07e2a2a949b0d0a9c5e43a8c4eb53b483780021ea20142031264de3299"
SEED = 6101
ACTION_HORIZON = 25
WIDTH = 512
DEPTH = 4
TIME_EMBEDDING_DIM = 128
DIFFUSION_STEPS = 100
BATCH_SIZE = 1024
TRAIN_STEPS = 30_000
WARMUP_STEPS = 1_000
VALIDATION_EVERY = 1_000
VALIDATION_COUNT = 8_192
LEARNING_RATE = 2.0e-4
WEIGHT_DECAY = 1.0e-4
EMA_DECAY = 0.999
GRADIENT_CLIP = 1.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def derived_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "little") % (
        2**63 - 1
    )


def derangement_shift(*, count: int, task: str, role: str) -> int:
    if count <= 1:
        raise ValueError("GDP-CEM goal derangement needs at least two rows")
    return 1 + derived_seed(f"gdp-cem-e7p|{task}|{role}|seed={SEED}") % (count - 1)


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
    model_parameters = dict(model.named_parameters())
    for name, value in ema.named_parameters():
        value.mul_(EMA_DECAY).add_(model_parameters[name], alpha=1.0 - EMA_DECAY)
    model_buffers = dict(model.named_buffers())
    for name, value in ema.named_buffers():
        value.copy_(model_buffers[name])


def learning_rate(step: int) -> float:
    if step <= WARMUP_STEPS:
        return LEARNING_RATE * step / WARMUP_STEPS
    progress = (step - WARMUP_STEPS) / (TRAIN_STEPS - WARMUP_STEPS)
    return LEARNING_RATE * 0.5 * (1.0 + math.cos(math.pi * progress))


def fit_action_standardizer(
    actions: np.ndarray, role: np.ndarray, primitive_action_dim: int
) -> tuple[np.ndarray, np.ndarray]:
    total = np.zeros(primitive_action_dim, dtype=np.float64)
    square = np.zeros(primitive_action_dim, dtype=np.float64)
    count = 0
    for start in range(0, len(actions), 65_536):
        stop = min(start + 65_536, len(actions))
        selected = actions[start:stop][role[start:stop] == 0]
        if not len(selected):
            continue
        value = selected.reshape(-1, primitive_action_dim).astype(np.float64)
        total += value.sum(axis=0)
        square += np.square(value).sum(axis=0)
        count += len(value)
    if count <= 1:
        raise RuntimeError("GDP-CEM has no P1-train action statistics")
    mean = total / count
    variance = square / count - np.square(mean)
    std = np.sqrt(np.maximum(variance, 0.0))
    if not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std < 1e-6):
        raise RuntimeError("GDP-CEM action standardizer is invalid")
    return mean.astype(np.float32), std.astype(np.float32)


class ArrayStore:
    def __init__(
        self,
        *,
        task: str,
        condition: str,
        latents: np.ndarray,
        source_index: np.ndarray,
        goal_index: np.ndarray,
        actions: np.ndarray,
        role: np.ndarray,
        latent_mean: np.ndarray,
        latent_std: np.ndarray,
        action_mean: np.ndarray,
        action_std: np.ndarray,
    ) -> None:
        self.task = task
        self.condition = condition
        self.latents = latents
        self.source_index = source_index
        self.goal_index = goal_index
        self.actions = actions
        self.role = role
        self.latent_mean = latent_mean
        self.latent_std = latent_std
        self.action_mean = action_mean
        self.action_std = action_std
        self.train_rows = np.flatnonzero(role == 0)
        self.validation_rows = np.flatnonzero(role == 1)
        self.train_shift = derangement_shift(
            count=len(self.train_rows), task=task, role="P1_train"
        )
        self.validation_shift = derangement_shift(
            count=len(self.validation_rows), task=task, role="P1_val"
        )

    def batch(
        self, positions: np.ndarray, *, validation: bool
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        rows = self.validation_rows if validation else self.train_rows
        shift = self.validation_shift if validation else self.train_shift
        selected = rows[positions]
        if self.condition == "diffusion_shuffled_goal":
            goal_selected = rows[(positions + shift) % len(rows)]
            if np.any(goal_selected == selected):
                raise RuntimeError("GDP-CEM shuffled goal is not a derangement")
        else:
            goal_selected = selected
        current = self.latents[self.source_index[selected]]
        goal = self.latents[self.goal_index[goal_selected]]
        action = self.actions[selected]
        current = (current - self.latent_mean) / self.latent_std
        goal = (goal - self.latent_mean) / self.latent_std
        action = (action - self.action_mean) / self.action_std
        if not (
            np.isfinite(current).all()
            and np.isfinite(goal).all()
            and np.isfinite(action).all()
        ):
            raise RuntimeError("GDP-CEM standardized batch is non-finite")
        return (
            torch.from_numpy(np.asarray(current, dtype=np.float32)),
            torch.from_numpy(np.asarray(goal, dtype=np.float32)),
            torch.from_numpy(np.asarray(action, dtype=np.float32)),
        )


@torch.inference_mode()
def validate(
    model: torch.nn.Module,
    *,
    proposal_kind: str,
    store: ArrayStore,
    positions: np.ndarray,
    validation_timestep: torch.Tensor,
    validation_noise: torch.Tensor,
    schedule: CosineDiffusionSchedule,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    losses: list[torch.Tensor] = []
    squared_errors: list[torch.Tensor] = []
    alpha_bar = schedule.alpha_bar.to(device)
    for start in range(0, len(positions), BATCH_SIZE):
        stop = min(start + BATCH_SIZE, len(positions))
        current, goal, clean = store.batch(positions[start:stop], validation=True)
        current = current.to(device)
        goal = goal.to(device)
        clean = clean.to(device)
        if proposal_kind == "diffusion":
            timestep = validation_timestep[start:stop].to(device)
            noise = validation_noise[start:stop].to(device)
            alpha = alpha_bar[timestep].view(-1, 1, 1)
            noisy = alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
            with torch.autocast("cuda", dtype=torch.bfloat16):
                prediction = model(current, goal, noisy, timestep)
            error = prediction.float() - noise
            loss = error.square().mean(dim=(1, 2))
            estimate = (noisy - (1.0 - alpha).sqrt() * prediction.float()) / alpha.sqrt()
        else:
            with torch.autocast("cuda", dtype=torch.bfloat16):
                mean, log_std = model(current, goal)
            standardized = (clean - mean.float()) / log_std.float().exp()
            loss = (0.5 * standardized.square() + log_std.float()).mean(dim=(1, 2))
            estimate = mean.float()
        losses.append(loss.cpu())
        squared_errors.append((estimate - clean).square().mean(dim=(1, 2)).cpu())
    return {
        "objective": float(torch.cat(losses).double().mean()),
        "single_prediction_action_mse": float(
            torch.cat(squared_errors).double().mean()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "reacher", "cube"), required=True)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--sequence-h5", type=Path, required=True)
    parser.add_argument("--sequence-manifest", type=Path, required=True)
    parser.add_argument("--expected-sequence-manifest-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.seed != SEED:
        raise RuntimeError("E7P proposal training permits only seed 6101")
    for path in (
        args.latent_h5,
        args.latent_manifest,
        args.sequence_h5,
        args.sequence_manifest,
        args.protocol,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty GDP-CEM training output")
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("GDP-CEM training protocol hash differs")
    sequence_manifest = json.loads(
        args.sequence_manifest.read_text(encoding="utf-8")
    )
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    sequence_sha = sha256_file(args.sequence_h5)
    latent_sha = sha256_file(args.latent_h5)
    if (
        sha256_file(args.sequence_manifest)
        != args.expected_sequence_manifest_sha256
        or len(args.expected_sequence_manifest_sha256) != 64
        or sequence_manifest.get("status") != "ok"
        or sequence_manifest.get("kind")
        != "gdp_cem_p1_goal_conditioned_action_sequence_cache"
        or sequence_manifest.get("protocol_sha256") != CACHE_PROTOCOL_SHA256
        or sequence_manifest.get("output_h5_sha256") != sequence_sha
        or sequence_manifest.get("latent_h5_sha256") != latent_sha
        or sequence_manifest.get("d2_read") is not False
        or sequence_manifest.get("d3_read") is not False
        or sequence_manifest.get("protected_c1_i1_read") is not False
        or latent_manifest.get("output_h5_sha256") != latent_sha
    ):
        raise RuntimeError("GDP-CEM proposal-training input lineage differs")

    started = time.time()
    with h5py.File(args.latent_h5, "r") as handle:
        latents = np.asarray(handle["latent"][:], dtype=np.float32)
    with h5py.File(args.sequence_h5, "r") as handle:
        source_index = np.asarray(handle["source_index"][:], dtype=np.int64)
        goal_index = np.asarray(handle["goal_index"][:], dtype=np.int64)
        role = np.asarray(handle["role"][:], dtype=np.uint8)
        macro_actions = np.asarray(handle["action"][:], dtype=np.float32)
        latent_mean = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        latent_std = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        robust_low = np.asarray(
            handle["stats/p1_train_action_robust_low"][:], dtype=np.float32
        )
        robust_high = np.asarray(
            handle["stats/p1_train_action_robust_high"][:], dtype=np.float32
        )
    primitive_action_dim = int(sequence_manifest["primitive_action_dim"])
    actions = macro_actions.reshape(
        len(macro_actions), ACTION_HORIZON, primitive_action_dim
    )
    action_mean, action_std = fit_action_standardizer(
        actions, role, primitive_action_dim
    )
    if (
        latents.shape[1] != 192
        or latent_mean.shape != (192,)
        or latent_std.shape != (192,)
        or np.any(latent_std < 1e-6)
        or np.any(source_index < 0)
        or np.any(goal_index >= len(latents))
    ):
        raise RuntimeError("GDP-CEM training arrays are invalid")
    store = ArrayStore(
        task=args.task,
        condition=args.condition,
        latents=latents,
        source_index=source_index,
        goal_index=goal_index,
        actions=actions,
        role=role,
        latent_mean=latent_mean,
        latent_std=latent_std,
        action_mean=action_mean,
        action_std=action_std,
    )

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("GDP-CEM proposal training requires CUDA")
    device = torch.device("cuda")
    config = {
        "latent_dim": 192,
        "primitive_action_dim": primitive_action_dim,
        "action_horizon": ACTION_HORIZON,
        "width": WIDTH,
        "depth": DEPTH,
        "time_embedding_dim": TIME_EMBEDDING_DIM,
    }
    proposal_kind = "gaussian" if args.condition == "gaussian_true" else "diffusion"
    if proposal_kind == "diffusion":
        model: torch.nn.Module = JointActionDiffusion(**config)
    else:
        model = ConditionalDiagonalGaussian(**config)
    model = model.to(device)
    ema = copy.deepcopy(model).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=WEIGHT_DECAY,
    )
    schedule = CosineDiffusionSchedule.build(DIFFUSION_STEPS)
    alpha_bar = schedule.alpha_bar.to(device)
    batch_generator = torch.Generator(device="cpu").manual_seed(
        derived_seed(f"gdp-e7p-batches|{args.task}|{args.condition}|{SEED}")
    )
    noise_generator = torch.Generator(device=device).manual_seed(
        derived_seed(f"gdp-e7p-noise|{args.task}|{args.condition}|{SEED}")
    )
    validation_generator = np.random.default_rng(
        derived_seed(f"gdp-e7p-validation-rows|{args.task}|{SEED}")
    )
    validation_positions = validation_generator.choice(
        len(store.validation_rows), size=VALIDATION_COUNT, replace=False
    ).astype(np.int64)
    validation_torch_generator = torch.Generator(device="cpu").manual_seed(
        derived_seed(f"gdp-e7p-validation-noise|{args.task}|{SEED}")
    )
    validation_timestep = torch.randint(
        0,
        DIFFUSION_STEPS,
        (VALIDATION_COUNT,),
        generator=validation_torch_generator,
    )
    validation_noise = torch.randn(
        VALIDATION_COUNT,
        ACTION_HORIZON,
        primitive_action_dim,
        generator=validation_torch_generator,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "training.jsonl"
    checkpoint_path = args.output_dir / "best.pt"
    best_objective = math.inf
    best_step = -1
    best_validation: dict[str, float] | None = None
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for step in range(1, TRAIN_STEPS + 1):
            model.train()
            positions = torch.randint(
                len(store.train_rows),
                (BATCH_SIZE,),
                generator=batch_generator,
            ).numpy()
            current, goal, clean = store.batch(positions, validation=False)
            current = current.to(device)
            goal = goal.to(device)
            clean = clean.to(device)
            optimizer.zero_grad(set_to_none=True)
            if proposal_kind == "diffusion":
                timestep = torch.randint(
                    0,
                    DIFFUSION_STEPS,
                    (BATCH_SIZE,),
                    generator=noise_generator,
                    device=device,
                )
                noise = torch.randn(
                    clean.shape,
                    generator=noise_generator,
                    device=device,
                    dtype=clean.dtype,
                )
                alpha = alpha_bar[timestep].view(-1, 1, 1)
                noisy = alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    prediction = model(current, goal, noisy, timestep)
                    loss = (prediction.float() - noise).square().mean()
            else:
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    mean, log_std = model(current, goal)
                    standardized = (clean - mean.float()) / log_std.float().exp()
                    loss = (0.5 * standardized.square() + log_std.float()).mean()
            if not torch.isfinite(loss):
                raise RuntimeError("GDP-CEM training loss is non-finite")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), GRADIENT_CLIP
            )
            if not torch.isfinite(gradient_norm):
                raise RuntimeError("GDP-CEM gradient norm is non-finite")
            rate = learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            update_ema(ema, model)

            if step % VALIDATION_EVERY == 0:
                metrics = validate(
                    ema,
                    proposal_kind=proposal_kind,
                    store=store,
                    positions=validation_positions,
                    validation_timestep=validation_timestep,
                    validation_noise=validation_noise,
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
                if metrics["objective"] < best_objective:
                    best_objective = metrics["objective"]
                    best_step = step
                    best_validation = metrics
                    payload = {
                        "kind": "gdp_cem_p1_proposal_checkpoint",
                        "proposal_kind": proposal_kind,
                        "condition": args.condition,
                        "task": args.task,
                        "seed": SEED,
                        "model_config": config,
                        "state_dict": cpu_state_dict(model),
                        "ema_state_dict": cpu_state_dict(ema),
                        "latent_mean": torch.from_numpy(latent_mean),
                        "latent_std": torch.from_numpy(latent_std),
                        "action_mean": torch.from_numpy(action_mean),
                        "action_std": torch.from_numpy(action_std),
                        "robust_low": torch.from_numpy(robust_low),
                        "robust_high": torch.from_numpy(robust_high),
                        "diffusion_steps": DIFFUSION_STEPS,
                        "train_shift": store.train_shift,
                        "validation_shift": store.validation_shift,
                        "best_step": best_step,
                        "best_validation": best_validation,
                        "parameter_count": parameter_count,
                        "protocol_sha256": PROTOCOL_SHA256,
                        "source_manifest_sha256": sha256_file(args.source_manifest),
                        "sequence_h5_sha256": sequence_sha,
                        "latent_h5_sha256": latent_sha,
                    }
                    atomic_torch_save(checkpoint_path, payload)
    if best_step < 0 or best_validation is None or not checkpoint_path.is_file():
        raise RuntimeError("GDP-CEM training produced no checkpoint")
    torch.cuda.synchronize()
    summary = {
        "status": "ok",
        "kind": "gdp_cem_p1_proposal_training",
        "analysis_role": "P1_only_method_development",
        "task": args.task,
        "condition": args.condition,
        "proposal_kind": proposal_kind,
        "seed": SEED,
        "model_config": config,
        "parameter_count": parameter_count,
        "optimization": {
            "optimizer": "AdamW",
            "betas": [0.9, 0.999],
            "weight_decay": WEIGHT_DECAY,
            "peak_learning_rate": LEARNING_RATE,
            "warmup_steps": WARMUP_STEPS,
            "schedule": "linear_warmup_then_cosine",
            "batch_size": BATCH_SIZE,
            "train_steps": TRAIN_STEPS,
            "gradient_clip": GRADIENT_CLIP,
            "ema_decay": EMA_DECAY,
            "precision": "CUDA_bfloat16_autocast_float32_loss",
        },
        "diffusion_steps": DIFFUSION_STEPS if proposal_kind == "diffusion" else None,
        "best_step": best_step,
        "best_validation": best_validation,
        "train_sequences": len(store.train_rows),
        "validation_sequences": len(store.validation_rows),
        "validation_count": VALIDATION_COUNT,
        "train_shift": store.train_shift,
        "validation_shift": store.validation_shift,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "training_trace": str(trace_path),
        "training_trace_sha256": sha256_file(trace_path),
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": latent_sha,
        "sequence_h5": str(args.sequence_h5),
        "sequence_h5_sha256": sequence_sha,
        "sequence_manifest_sha256": sha256_file(args.sequence_manifest),
        "protocol": str(args.protocol),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "trainer_source_sha256": sha256_file(Path(__file__)),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(
            torch.cuda.max_memory_allocated(device)
        ),
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
        "protected_c1_i1_read": False,
        "d2_read": False,
        "d3_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
