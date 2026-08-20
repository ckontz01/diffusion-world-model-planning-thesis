#!/usr/bin/env python3
"""Train one frozen P1-only classifier-free velocity proposal model."""

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

import train_gdp_cem_proposal as e7train
from gdp_cem_models import CosineDiffusionSchedule, VelocityActionDiffusion


TASKS = ("pusht", "reacher", "cube")
CONDITIONS = ("vp_true", "vp_shuffled_goal")
PROTOCOL_SHA256 = "2f3052637e72016d4218fd6e13c62d36589773f23a9a0b4223c9a808e9fab93a"
CACHE_PROTOCOL_SHA256 = e7train.CACHE_PROTOCOL_SHA256
SEED = 6101
ACTION_HORIZON = 25
WIDTH = 512
DEPTH = 4
TIME_EMBEDDING_DIM = 128
DIFFUSION_STEPS = 100
CONDITION_DROPOUT = 0.15
BATCH_SIZE = 1024
TRAIN_STEPS = 30_000
WARMUP_STEPS = 1_000
VALIDATION_EVERY = 1_000
VALIDATION_COUNT = 8_192
VALIDATION_BATCH_SIZE = 2_048
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


def array_sha256(value: np.ndarray | torch.Tensor) -> str:
    if torch.is_tensor(value):
        value = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def derived_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "little") % (
        2**63 - 1
    )


def numpy_seed(label: str) -> int:
    return int(hashlib.sha256(label.encode()).hexdigest()[:16], 16)


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d2", "d3", "c1", "i1"}):
        raise RuntimeError(f"E10V protected path is forbidden: {path}")


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


def select_fresh_rows(
    validation_rows: np.ndarray, *, task: str
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    e7_checkpoint_generator = np.random.default_rng(
        derived_seed(f"gdp-e7p-validation-rows|{task}|6101")
    )
    e7_checkpoint_positions = e7_checkpoint_generator.choice(
        len(validation_rows), size=8_192, replace=False
    ).astype(np.int64)
    e7_checkpoint_rows = validation_rows[e7_checkpoint_positions]
    e7_selection_generator = np.random.default_rng(
        numpy_seed(f"gdp-cem-e7p-selection|task={task}|seed=2026081702")
    )
    e7_selection_rows = e7_selection_generator.choice(
        validation_rows, size=256, replace=False
    ).astype(np.int64)
    pre_e8_excluded = np.unique(
        np.concatenate((e7_checkpoint_rows, e7_selection_rows))
    )
    pre_e8_available = np.setdiff1d(
        validation_rows, pre_e8_excluded, assume_unique=False
    )
    e8_generator = np.random.default_rng(
        numpy_seed(f"gdp-cem-e8a-selection|task={task}|seed=2026081703")
    )
    e8_rows = e8_generator.choice(
        pre_e8_available, size=512, replace=False
    ).astype(np.int64)
    prior_excluded = np.unique(
        np.concatenate((pre_e8_excluded, e8_rows))
    )
    checkpoint_available = np.setdiff1d(
        validation_rows, prior_excluded, assume_unique=False
    )
    checkpoint_generator = np.random.default_rng(
        numpy_seed(f"gdp-e10v-checkpoint|task={task}|seed=2026081706")
    )
    checkpoint_rows = checkpoint_generator.choice(
        checkpoint_available, size=VALIDATION_COUNT, replace=False
    ).astype(np.int64)
    final_available = np.setdiff1d(
        checkpoint_available, checkpoint_rows, assume_unique=False
    )
    final_generator = np.random.default_rng(
        numpy_seed(f"gdp-e10v-selection|task={task}|seed=2026081707")
    )
    final_rows = final_generator.choice(
        final_available, size=512, replace=False
    ).astype(np.int64)
    sets = (
        e7_checkpoint_rows,
        e7_selection_rows,
        e8_rows,
        checkpoint_rows,
        final_rows,
    )
    if any(len(np.unique(rows)) != len(rows) for rows in sets):
        raise RuntimeError("E10V row set contains duplicates")
    if (
        len(np.intersect1d(e8_rows, pre_e8_excluded))
        or len(np.intersect1d(checkpoint_rows, prior_excluded))
        or len(np.intersect1d(final_rows, prior_excluded))
        or len(np.intersect1d(final_rows, checkpoint_rows))
    ):
        raise RuntimeError("E10V new row set overlaps an exclusion set")
    record = {
        "validation_rows_count": int(len(validation_rows)),
        "validation_rows_sha256": array_sha256(validation_rows),
        "e7_checkpoint_rows_count": int(len(e7_checkpoint_rows)),
        "e7_checkpoint_rows_sha256": array_sha256(e7_checkpoint_rows),
        "e7_selection_rows_count": int(len(e7_selection_rows)),
        "e7_selection_rows_sha256": array_sha256(e7_selection_rows),
        "e8_rows_count": int(len(e8_rows)),
        "e8_rows_sha256": array_sha256(e8_rows),
        "prior_excluded_rows_count": int(len(prior_excluded)),
        "prior_excluded_rows_sha256": array_sha256(prior_excluded),
        "checkpoint_available_rows_count": int(len(checkpoint_available)),
        "checkpoint_available_rows_sha256": array_sha256(checkpoint_available),
        "checkpoint_rows_count": int(len(checkpoint_rows)),
        "checkpoint_rows_sha256": array_sha256(checkpoint_rows),
        "final_available_rows_count": int(len(final_available)),
        "final_available_rows_sha256": array_sha256(final_available),
        "final_rows_count": int(len(final_rows)),
        "final_rows_sha256": array_sha256(final_rows),
    }
    return checkpoint_rows, final_rows, record


@torch.inference_mode()
def validate(
    model: VelocityActionDiffusion,
    *,
    store: e7train.ArrayStore,
    alternate_store: e7train.ArrayStore,
    positions: np.ndarray,
    timestep_bank: torch.Tensor,
    noise_bank: torch.Tensor,
    schedule: CosineDiffusionSchedule,
    device: torch.device,
) -> dict[str, float]:
    conditional_losses: list[torch.Tensor] = []
    unconditional_losses: list[torch.Tensor] = []
    alternate_goal_losses: list[torch.Tensor] = []
    reconstruction_losses: list[torch.Tensor] = []
    alpha_bar = schedule.alpha_bar.to(device)
    model.eval()
    for start in range(0, len(positions), VALIDATION_BATCH_SIZE):
        stop = min(start + VALIDATION_BATCH_SIZE, len(positions))
        current, goal, clean = store.batch(positions[start:stop], validation=True)
        _, alternate_goal, _ = alternate_store.batch(
            positions[start:stop], validation=True
        )
        current = current.to(device)
        goal = goal.to(device)
        alternate_goal = alternate_goal.to(device)
        clean = clean.to(device)
        timestep = timestep_bank[start:stop].to(device)
        noise = noise_bank[start:stop].to(device)
        alpha = alpha_bar[timestep].view(-1, 1, 1)
        noisy = alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
        target = alpha.sqrt() * noise - (1.0 - alpha).sqrt() * clean
        with torch.autocast("cuda", dtype=torch.bfloat16):
            conditional = model(
                current, goal, noisy, timestep, conditioned=True
            ).float()
            unconditional = model(
                current, goal, noisy, timestep, conditioned=False
            ).float()
            alternate = model(
                current, alternate_goal, noisy, timestep, conditioned=True
            ).float()
        conditional_error = (conditional - target).square().mean(dim=(1, 2))
        conditional_losses.append(conditional_error.cpu())
        unconditional_losses.append(
            (unconditional - target).square().mean(dim=(1, 2)).cpu()
        )
        alternate_goal_losses.append(
            (alternate - target).square().mean(dim=(1, 2)).cpu()
        )
        clean_prediction = (
            alpha.sqrt() * noisy - (1.0 - alpha).sqrt() * conditional
        )
        reconstruction_losses.append(
            (clean_prediction - clean).square().mean(dim=(1, 2)).cpu()
        )
    conditional = torch.cat(conditional_losses).double()
    unconditional = torch.cat(unconditional_losses).double()
    alternate = torch.cat(alternate_goal_losses).double()
    return {
        "conditional_velocity_mse": float(conditional.mean()),
        "unconditional_velocity_mse": float(unconditional.mean()),
        "alternate_goal_velocity_mse": float(alternate.mean()),
        "alternate_minus_assigned_velocity_mse": float(
            (alternate - conditional).mean()
        ),
        "unconditional_minus_correct_velocity_mse": float(
            (unconditional - conditional).mean()
        ),
        "conditional_clean_reconstruction_mse": float(
            torch.cat(reconstruction_losses).double().mean()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
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
        raise RuntimeError("E10V pilot permits only seed 6101")
    required = (
        args.latent_h5,
        args.latent_manifest,
        args.sequence_h5,
        args.sequence_manifest,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E10V training output")
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E10V protocol hash differs")

    sequence_manifest = json.loads(args.sequence_manifest.read_text(encoding="utf-8"))
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
        raise RuntimeError("E10V training input lineage differs")

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
    action_mean, action_std = e7train.fit_action_standardizer(
        actions, role, primitive_action_dim
    )
    if (
        latents.shape[1] != 192
        or latent_mean.shape != (192,)
        or latent_std.shape != (192,)
        or np.any(latent_std < 1.0e-6)
        or np.any(source_index < 0)
        or np.any(goal_index >= len(latents))
        or np.any(robust_high <= robust_low)
    ):
        raise RuntimeError("E10V training arrays differ")
    mapped_condition = (
        "diffusion_true" if args.condition == "vp_true" else "diffusion_shuffled_goal"
    )
    alternate_condition = (
        "diffusion_shuffled_goal" if args.condition == "vp_true" else "diffusion_true"
    )
    store_arguments = {
        "task": args.task,
        "latents": latents,
        "source_index": source_index,
        "goal_index": goal_index,
        "actions": actions,
        "role": role,
        "latent_mean": latent_mean,
        "latent_std": latent_std,
        "action_mean": action_mean,
        "action_std": action_std,
    }
    store = e7train.ArrayStore(condition=mapped_condition, **store_arguments)
    alternate_store = e7train.ArrayStore(
        condition=alternate_condition, **store_arguments
    )
    checkpoint_rows, final_rows, row_selection = select_fresh_rows(
        store.validation_rows, task=args.task
    )
    checkpoint_positions = np.searchsorted(store.validation_rows, checkpoint_rows)
    if not np.array_equal(
        store.validation_rows[checkpoint_positions], checkpoint_rows
    ):
        raise RuntimeError("E10V checkpoint row-position conversion differs")

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E10V training requires CUDA")
    device = torch.device("cuda")
    config = {
        "latent_dim": 192,
        "primitive_action_dim": primitive_action_dim,
        "action_horizon": ACTION_HORIZON,
        "width": WIDTH,
        "depth": DEPTH,
        "time_embedding_dim": TIME_EMBEDDING_DIM,
    }
    model = VelocityActionDiffusion(**config).to(device)
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
        derived_seed(f"gdp-e10v-batches|{args.task}|seed={SEED}")
    )
    diffusion_generator = torch.Generator(device=device).manual_seed(
        derived_seed(f"gdp-e10v-diffusion|{args.task}|seed={SEED}")
    )
    dropout_generator = torch.Generator(device=device).manual_seed(
        derived_seed(f"gdp-e10v-dropout|{args.task}|seed={SEED}")
    )
    validation_generator = torch.Generator(device="cpu").manual_seed(
        derived_seed(f"gdp-e10v-validation|{args.task}|seed={SEED}")
    )
    validation_timestep = torch.randint(
        0,
        DIFFUSION_STEPS,
        (VALIDATION_COUNT,),
        generator=validation_generator,
    )
    validation_noise = torch.randn(
        VALIDATION_COUNT,
        ACTION_HORIZON,
        primitive_action_dim,
        generator=validation_generator,
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
            timestep = torch.randint(
                0,
                DIFFUSION_STEPS,
                (BATCH_SIZE,),
                generator=diffusion_generator,
                device=device,
            )
            noise = torch.randn(
                clean.shape,
                generator=diffusion_generator,
                device=device,
                dtype=clean.dtype,
            )
            conditioned = torch.rand(
                BATCH_SIZE, generator=dropout_generator, device=device
            ) >= CONDITION_DROPOUT
            alpha = alpha_bar[timestep].view(-1, 1, 1)
            noisy = alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
            target = alpha.sqrt() * noise - (1.0 - alpha).sqrt() * clean
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                prediction = model(
                    current, goal, noisy, timestep, conditioned=conditioned
                )
                loss = (prediction.float() - target).square().mean()
            if not torch.isfinite(loss):
                raise RuntimeError("E10V training loss is non-finite")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), GRADIENT_CLIP
            )
            if not torch.isfinite(gradient_norm):
                raise RuntimeError("E10V gradient norm is non-finite")
            rate = learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            update_ema(ema, model)

            if step % VALIDATION_EVERY == 0:
                metrics = validate(
                    ema,
                    store=store,
                    alternate_store=alternate_store,
                    positions=checkpoint_positions,
                    timestep_bank=validation_timestep,
                    noise_bank=validation_noise,
                    schedule=schedule,
                    device=device,
                )
                record = {
                    "step": step,
                    "train_objective": float(loss.detach().cpu()),
                    "conditioned_fraction": float(conditioned.float().mean().cpu()),
                    "gradient_norm": float(gradient_norm.detach().cpu()),
                    "learning_rate": rate,
                    "validation": metrics,
                }
                trace.write(json.dumps(record, sort_keys=True) + "\n")
                trace.flush()
                objective = metrics["conditional_velocity_mse"]
                if objective < best_objective:
                    best_objective = objective
                    best_step = step
                    best_validation = metrics
                    payload = {
                        "kind": "gdp_cem_e10v_p1_velocity_checkpoint",
                        "proposal_kind": "velocity_diffusion",
                        "prediction_type": "velocity",
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
                        "condition_dropout": CONDITION_DROPOUT,
                        "train_shift": store.train_shift,
                        "validation_shift": store.validation_shift,
                        "best_step": best_step,
                        "best_validation": best_validation,
                        "parameter_count": parameter_count,
                        "row_selection": row_selection,
                        "checkpoint_rows": torch.from_numpy(checkpoint_rows),
                        "final_rows": torch.from_numpy(final_rows),
                        "protocol_sha256": PROTOCOL_SHA256,
                        "source_manifest_sha256": sha256_file(args.source_manifest),
                        "sequence_h5_sha256": sequence_sha,
                        "latent_h5_sha256": latent_sha,
                    }
                    atomic_torch_save(checkpoint_path, payload)
    if best_step < 0 or best_validation is None or not checkpoint_path.is_file():
        raise RuntimeError("E10V training produced no checkpoint")
    torch.cuda.synchronize()
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e10v_p1_velocity_training",
        "analysis_role": "post_E8D_P1_only_pure_diffusion_development",
        "task": args.task,
        "condition": args.condition,
        "proposal_kind": "velocity_diffusion",
        "prediction_type": "velocity",
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
            "condition_dropout": CONDITION_DROPOUT,
            "precision": "CUDA_bfloat16_autocast_float32_velocity_mse",
        },
        "diffusion_steps": DIFFUSION_STEPS,
        "best_step": best_step,
        "best_validation": best_validation,
        "train_sequences": len(store.train_rows),
        "validation_sequences": len(store.validation_rows),
        "validation_count": VALIDATION_COUNT,
        "train_shift": store.train_shift,
        "validation_shift": store.validation_shift,
        "row_selection": row_selection,
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
        "peak_cuda_memory_reserved_bytes": int(
            torch.cuda.max_memory_reserved(device)
        ),
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
