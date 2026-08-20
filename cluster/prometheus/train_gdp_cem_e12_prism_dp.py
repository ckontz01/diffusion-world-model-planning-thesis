#!/usr/bin/env python3
"""Train one P1-only PRISM-DP best-of-N reconstruction for E12."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

from gdp_cem_e12_prism_data import PrismDPP1Dataset
from gdp_cem_e12_prism_models import (
    PRISM_DP_DOC_SHA256,
    PRISM_UPSTREAM_COMMIT,
    CosineDDIMSchedule,
    PrismDPModel,
    cpu_state_dict,
    update_ema,
)


TRAIN_STEPS = 100_000
BATCH_SIZE = 128
LEARNING_RATE = 1.0e-4
WEIGHT_DECAY = 1.0e-6
WARMUP_STEPS = 500
EMA_DECAY = 0.999
GRADIENT_CLIP = 1.0
VALIDATION_EVERY = 2_000
LOG_EVERY = 100


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_torch_save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("xb") as stream:
            torch.save(value, stream)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def derived_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "little") % (
        2**63 - 1
    )


def learning_rate(step: int) -> float:
    if step <= WARMUP_STEPS:
        return LEARNING_RATE * step / max(WARMUP_STEPS, 1)
    progress = (step - WARMUP_STEPS) / max(TRAIN_STEPS - WARMUP_STEPS, 1)
    return LEARNING_RATE * 0.5 * (1.0 + math.cos(math.pi * progress))


def seed_worker(worker_id: int) -> None:
    worker_seed = torch.initial_seed() % (2**32)
    np.random.seed(worker_seed)
    random.seed(worker_seed)


@torch.inference_mode()
def validate(
    model: PrismDPModel,
    loader: DataLoader,
    schedule: CosineDDIMSchedule,
    *,
    device: torch.device,
    validation_seed: int,
) -> float:
    model.eval()
    generator = torch.Generator(device=device).manual_seed(validation_seed)
    total = 0.0
    count = 0
    alpha_bar = schedule.alpha_bar.to(device)
    for batch in loader:
        observation = batch["observation"].to(device, non_blocking=True)
        goal = batch["goal"].to(device, non_blocking=True)
        clean = batch["action"].to(device, non_blocking=True)
        timestep = torch.randint(
            0,
            schedule.num_train_timesteps,
            (clean.shape[0],),
            generator=generator,
            device=device,
        )
        noise = torch.randn(
            clean.shape,
            generator=generator,
            device=device,
            dtype=clean.dtype,
        )
        alpha = alpha_bar[timestep].reshape(-1, 1, 1)
        noisy = alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
        prediction = model(noisy, timestep, observation, goal)
        loss = F.mse_loss(prediction, noise)
        if not torch.isfinite(loss):
            raise RuntimeError("non-finite E12 PRISM-DP validation objective")
        total += float(loss.cpu()) * clean.shape[0]
        count += clean.shape[0]
    model.train()
    if not count:
        raise RuntimeError("empty E12 PRISM-DP P1 validation")
    return total / count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "reacher", "cube"), required=True)
    parser.add_argument("--seed", type=int, choices=(6101, 6102, 6103), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--dataset-h5", type=Path, required=True)
    parser.add_argument("--sequence-h5", type=Path, required=True)
    parser.add_argument("--sequence-manifest", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-workers", type=int, default=8)
    args = parser.parse_args()

    for path in (
        args.protocol,
        args.source_manifest,
        args.dataset_h5,
        args.sequence_h5,
        args.sequence_manifest,
        args.latent_h5,
        args.latent_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
        lowered = {component.lower() for component in path.parts}
        if lowered.intersection({"c1", "i1", "p4", "d3", "d4"}):
            raise RuntimeError(f"protected/confirmation input forbidden in E12 training: {path}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E12 PRISM-DP output")
    if args.num_workers < 0:
        raise ValueError("negative E12 PRISM-DP worker count")
    if not torch.cuda.is_available():
        raise RuntimeError("E12 PRISM-DP training requires CUDA")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    started = time.time()

    train_dataset = PrismDPP1Dataset(
        dataset_h5=args.dataset_h5,
        sequence_h5=args.sequence_h5,
        latent_h5=args.latent_h5,
        role="P1_train",
    )
    validation_dataset = PrismDPP1Dataset(
        dataset_h5=args.dataset_h5,
        sequence_h5=args.sequence_h5,
        latent_h5=args.latent_h5,
        role="P1_val",
        action_min=train_dataset.action_min,
        action_max=train_dataset.action_max,
    )
    if set(train_dataset.episode_ids.tolist()).intersection(
        validation_dataset.episode_ids.tolist()
    ):
        raise RuntimeError("E12 PRISM-DP P1 train/validation episodes overlap")

    loader_generator = torch.Generator().manual_seed(
        derived_seed(f"gdp-e12-prism-dp-loader|{args.task}|{args.seed}")
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        drop_last=True,
        num_workers=args.num_workers,
        pin_memory=True,
        persistent_workers=args.num_workers > 0,
        worker_init_fn=seed_worker,
        generator=loader_generator,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        drop_last=False,
        num_workers=max(1, args.num_workers // 2),
        pin_memory=True,
        persistent_workers=False,
        worker_init_fn=seed_worker,
        generator=torch.Generator().manual_seed(
            derived_seed(f"gdp-e12-prism-dp-validation-loader|{args.task}|{args.seed}")
        ),
    )
    model = PrismDPModel(action_dim=train_dataset.action_dim).to(device)
    ema = copy.deepcopy(model).eval().requires_grad_(False)
    expected_parameters = {2: 19_302_466, 3: 19_302_787, 4: 19_303_108, 5: 19_303_429}
    if model.action_dim not in expected_parameters or model.num_params != expected_parameters[
        model.action_dim
    ]:
        raise RuntimeError(
            f"E12 PRISM-DP parameter count {model.num_params} is not frozen for "
            f"action_dim={model.action_dim}"
        )
    schedule = CosineDDIMSchedule.build(100)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    diffusion_generator = torch.Generator(device=device).manual_seed(
        derived_seed(f"gdp-e12-prism-dp-noise|{args.task}|{args.seed}")
    )
    validation_seed = derived_seed(
        f"gdp-e12-prism-dp-validation-noise|{args.task}|{args.seed}"
    )
    initial_validation = validate(
        ema,
        validation_loader,
        schedule,
        device=device,
        validation_seed=validation_seed,
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    trace_path = args.output_dir / "training.jsonl"
    best_validation = math.inf
    best_step = -1
    best_ema_state: dict[str, torch.Tensor] | None = None
    best_model_state: dict[str, torch.Tensor] | None = None
    train_iterator = iter(train_loader)
    interval_loss = 0.0
    interval_samples = 0
    interval_started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for step in range(1, TRAIN_STEPS + 1):
            try:
                batch = next(train_iterator)
            except StopIteration:
                train_iterator = iter(train_loader)
                batch = next(train_iterator)
            observation = batch["observation"].to(device, non_blocking=True)
            goal = batch["goal"].to(device, non_blocking=True)
            clean = batch["action"].to(device, non_blocking=True)
            timestep = torch.randint(
                0,
                schedule.num_train_timesteps,
                (clean.shape[0],),
                generator=diffusion_generator,
                device=device,
            )
            noise = torch.randn(
                clean.shape,
                generator=diffusion_generator,
                device=device,
                dtype=clean.dtype,
            )
            noisy = schedule.add_noise(clean, noise, timestep)
            prediction = model(noisy, timestep, observation, goal)
            loss = F.mse_loss(prediction, noise)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite E12 PRISM-DP training objective")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), GRADIENT_CLIP
            )
            if not torch.isfinite(gradient_norm):
                raise RuntimeError("non-finite E12 PRISM-DP gradient")
            rate = learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            update_ema(ema, model, EMA_DECAY)
            interval_loss += float(loss.detach().cpu()) * clean.shape[0]
            interval_samples += clean.shape[0]

            if step % LOG_EVERY == 0:
                record = {
                    "type": "train",
                    "step": step,
                    "objective": interval_loss / interval_samples,
                    "learning_rate": rate,
                    "preclip_gradient_norm": float(gradient_norm.detach().cpu()),
                    "interval_seconds": time.time() - interval_started,
                }
                trace.write(json.dumps(record, sort_keys=True) + "\n")
                trace.flush()
                print(json.dumps(record, sort_keys=True), flush=True)
                interval_loss = 0.0
                interval_samples = 0
                interval_started = time.time()

            if step % VALIDATION_EVERY == 0 or step == TRAIN_STEPS:
                objective = validate(
                    ema,
                    validation_loader,
                    schedule,
                    device=device,
                    validation_seed=validation_seed,
                )
                record = {
                    "type": "validation",
                    "step": step,
                    "epsilon_mse": objective,
                }
                trace.write(json.dumps(record, sort_keys=True) + "\n")
                trace.flush()
                print(json.dumps(record, sort_keys=True), flush=True)
                if objective < best_validation:
                    best_validation = objective
                    best_step = step
                    best_ema_state = cpu_state_dict(ema)
                    best_model_state = cpu_state_dict(model)

    if best_ema_state is None or best_model_state is None:
        raise RuntimeError("E12 PRISM-DP never produced a checkpoint")
    relative_improvement = (initial_validation - best_validation) / max(
        initial_validation, 1.0e-12
    )
    validity = {
        "finite": math.isfinite(best_validation),
        "validation_relative_improvement": relative_improvement,
        "validation_improvement_at_least_5_percent": relative_improvement >= 0.05,
        "parameter_count_matches_documented_19_3m": 19.25e6 <= model.num_params <= 19.35e6,
        "p1_episode_disjoint": True,
    }
    validity["passed"] = all(
        (
            validity["finite"],
            validity["validation_improvement_at_least_5_percent"],
            validity["parameter_count_matches_documented_19_3m"],
            validity["p1_episode_disjoint"],
        )
    )
    checkpoint_path = args.output_dir / "best.pt"
    checkpoint = {
        "kind": "gdp_cem_e12_prism_dp_reconstruction_checkpoint",
        "analysis_role": "P1_only_matched_PRISM_DP_reconstruction",
        "reconstruction_not_official": True,
        "missing_public_modules": [
            "dp_baseline/model.py",
            "dp_baseline/scheduler.py",
            "dp_baseline/policy.py",
        ],
        "task": args.task,
        "seed": args.seed,
        "model_state_dict": best_model_state,
        "ema_state_dict": best_ema_state,
        "model_config": {
            "action_dim": model.action_dim,
            "action_horizon": model.action_horizon,
            "feature_dim": model.feature_dim,
            "condition_dim": model.condition_dim,
            "time_embedding_dim": model.time_embedding_dim,
            "channels": model.channels,
            "residual_blocks_per_level": model.residual_blocks_per_level,
            "middle_blocks": model.middle_blocks,
        },
        "parameter_count": model.num_params,
        "action_min": train_dataset.action_min,
        "action_max": train_dataset.action_max,
        "best_step": best_step,
        "initial_validation_epsilon_mse": initial_validation,
        "best_validation_epsilon_mse": best_validation,
        "validity": validity,
        "training_recipe": {
            "steps": TRAIN_STEPS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "warmup_steps": WARMUP_STEPS,
            "schedule": "linear_warmup_then_cosine",
            "ema_decay": EMA_DECAY,
            "gradient_clip": GRADIENT_CLIP,
            "prediction_type": "epsilon",
            "diffusion_train_steps": 100,
            "diffusion_schedule": "squaredcos_cap_v2",
            "evaluation_sampler": "deterministic_DDIM",
            "evaluation_reverse_steps": 10,
            "goal_offset_steps": 25,
            "action_horizon": 25,
            "numeric_precision": "float32",
        },
        "prism_upstream_commit": PRISM_UPSTREAM_COMMIT,
        "prism_dp_document_sha256": PRISM_DP_DOC_SHA256,
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "sequence_h5_sha256": sha256_file(args.sequence_h5),
        "sequence_manifest_sha256": sha256_file(args.sequence_manifest),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "dataset_file_identity": {
            "path": str(args.dataset_h5.resolve()),
            "size": args.dataset_h5.stat().st_size,
            "mtime_ns": args.dataset_h5.stat().st_mtime_ns,
            "inode": args.dataset_h5.stat().st_ino,
            "device": args.dataset_h5.stat().st_dev,
        },
        "p1_train_sequences": len(train_dataset),
        "p1_validation_sequences": len(validation_dataset),
        "p1_train_episode_count": len(set(train_dataset.episode_ids.tolist())),
        "p1_validation_episode_count": len(
            set(validation_dataset.episode_ids.tolist())
        ),
        "protected_inputs_read": False,
    }
    atomic_torch_save(checkpoint_path, checkpoint)
    summary = {
        "status": "ok" if validity["passed"] else "invalid",
        "kind": "gdp_cem_e12_prism_dp_reconstruction_training",
        "analysis_role": "P1_only_matched_PRISM_DP_reconstruction",
        "reconstruction_not_official": True,
        "task": args.task,
        "seed": args.seed,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "training_trace": str(trace_path),
        "training_trace_sha256": sha256_file(trace_path),
        "parameter_count": model.num_params,
        "best_step": best_step,
        "initial_validation_epsilon_mse": initial_validation,
        "best_validation_epsilon_mse": best_validation,
        "validity": validity,
        "elapsed_seconds": time.time() - started,
        "protocol_sha256": checkpoint["protocol_sha256"],
        "source_manifest_sha256": checkpoint["source_manifest_sha256"],
        "sequence_h5_sha256": checkpoint["sequence_h5_sha256"],
        "latent_h5_sha256": checkpoint["latent_h5_sha256"],
        "protected_p4_c1_i1_read": False,
        "d3_read": False,
        "d4_read": False,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
        },
    }
    atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
