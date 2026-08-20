#!/usr/bin/env python3
"""Train seed-matched E10M velocity and Gaussian P1 replication models."""

from __future__ import annotations

import argparse
import copy
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

import train_gdp_cem_proposal as e7train
import train_gdp_cem_vp_proposal as e10v
from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    CosineDiffusionSchedule,
    VelocityActionDiffusion,
)


TASKS = ("pusht", "reacher", "cube")
CONDITIONS = ("vp_true", "vp_shuffled_goal", "gaussian_true")
SEEDS = (6102, 6103)
PROTOCOL_SHA256 = "02606573e4c7e4341814c76974ff2020f35fedcf2e8d1d08e531dd553e9787b9"
VALIDATION_BATCH_SIZE = 2_048


def select_confirmation_rows(
    validation_rows: np.ndarray, *, task: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    checkpoint_rows, final_rows, e10_record = e10v.select_fresh_rows(
        validation_rows, task=task
    )
    e7_checkpoint_generator = np.random.default_rng(
        e10v.derived_seed(f"gdp-e7p-validation-rows|{task}|6101")
    )
    e7_checkpoint_rows = validation_rows[
        e7_checkpoint_generator.choice(
            len(validation_rows), size=8_192, replace=False
        ).astype(np.int64)
    ]
    e7_selection_generator = np.random.default_rng(
        e10v.numpy_seed(
            f"gdp-cem-e7p-selection|task={task}|seed=2026081702"
        )
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
        e10v.numpy_seed(f"gdp-cem-e8a-selection|task={task}|seed=2026081703")
    )
    e8_rows = e8_generator.choice(
        pre_e8_available, size=512, replace=False
    ).astype(np.int64)
    excluded = np.unique(
        np.concatenate(
            (
                e7_checkpoint_rows,
                e7_selection_rows,
                e8_rows,
                checkpoint_rows,
                final_rows,
            )
        )
    )
    available = np.setdiff1d(validation_rows, excluded, assume_unique=False)
    generator = np.random.default_rng(
        e10v.numpy_seed(
            f"gdp-e10m-confirmation|task={task}|seed=2026081708"
        )
    )
    confirmation = generator.choice(
        available, size=1_024, replace=False
    ).astype(np.int64)
    if (
        len(np.unique(confirmation)) != 1_024
        or len(np.intersect1d(confirmation, excluded))
        or e10_record["checkpoint_rows_sha256"]
        != e10v.array_sha256(checkpoint_rows)
        or e10_record["final_rows_sha256"] != e10v.array_sha256(final_rows)
    ):
        raise RuntimeError("E10M confirmation-row isolation differs")
    record = {
        **e10_record,
        "all_prior_excluded_rows_count": int(len(excluded)),
        "all_prior_excluded_rows_sha256": e10v.array_sha256(excluded),
        "confirmation_available_rows_count": int(len(available)),
        "confirmation_available_rows_sha256": e10v.array_sha256(available),
        "confirmation_rows_count": int(len(confirmation)),
        "confirmation_rows_sha256": e10v.array_sha256(confirmation),
    }
    return checkpoint_rows, final_rows, confirmation, record


@torch.inference_mode()
def validate_gaussian(
    model: ConditionalDiagonalGaussian,
    *,
    store: e7train.ArrayStore,
    positions: np.ndarray,
    device: torch.device,
) -> dict[str, float]:
    losses: list[torch.Tensor] = []
    mean_errors: list[torch.Tensor] = []
    model.eval()
    for start in range(0, len(positions), VALIDATION_BATCH_SIZE):
        stop = min(start + VALIDATION_BATCH_SIZE, len(positions))
        current, goal, clean = store.batch(positions[start:stop], validation=True)
        current = current.to(device)
        goal = goal.to(device)
        clean = clean.to(device)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            mean, log_std = model(current, goal)
        mean = mean.float()
        log_std = log_std.float()
        standardized = (clean - mean) / log_std.exp()
        losses.append(
            (0.5 * standardized.square() + log_std).mean(dim=(1, 2)).cpu()
        )
        mean_errors.append((mean - clean).square().mean(dim=(1, 2)).cpu())
    return {
        "conditional_gaussian_nll": float(torch.cat(losses).double().mean()),
        "conditional_mean_action_mse": float(
            torch.cat(mean_errors).double().mean()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--sequence-h5", type=Path, required=True)
    parser.add_argument("--sequence-manifest", type=Path, required=True)
    parser.add_argument("--expected-sequence-manifest-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.latent_h5,
        args.latent_manifest,
        args.sequence_h5,
        args.sequence_manifest,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        e10v.reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if e10v.sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E10M protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E10M training output")

    sequence_manifest = json.loads(args.sequence_manifest.read_text(encoding="utf-8"))
    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    sequence_sha = e10v.sha256_file(args.sequence_h5)
    latent_sha = e10v.sha256_file(args.latent_h5)
    if (
        e10v.sha256_file(args.sequence_manifest)
        != args.expected_sequence_manifest_sha256
        or sequence_manifest.get("status") != "ok"
        or sequence_manifest.get("kind")
        != "gdp_cem_p1_goal_conditioned_action_sequence_cache"
        or sequence_manifest.get("protocol_sha256") != e7train.CACHE_PROTOCOL_SHA256
        or sequence_manifest.get("output_h5_sha256") != sequence_sha
        or sequence_manifest.get("latent_h5_sha256") != latent_sha
        or sequence_manifest.get("d2_read") is not False
        or sequence_manifest.get("d3_read") is not False
        or sequence_manifest.get("protected_c1_i1_read") is not False
        or latent_manifest.get("output_h5_sha256") != latent_sha
    ):
        raise RuntimeError("E10M training input lineage differs")

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
        len(macro_actions), e10v.ACTION_HORIZON, primitive_action_dim
    )
    action_mean, action_std = e7train.fit_action_standardizer(
        actions, role, primitive_action_dim
    )
    mapped_condition = (
        "diffusion_shuffled_goal"
        if args.condition == "vp_shuffled_goal"
        else "diffusion_true"
    )
    alternate_condition = (
        "diffusion_true"
        if args.condition == "vp_shuffled_goal"
        else "diffusion_shuffled_goal"
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
    checkpoint_rows, final_rows, confirmation_rows, row_selection = (
        select_confirmation_rows(store.validation_rows, task=args.task)
    )
    checkpoint_positions = np.searchsorted(store.validation_rows, checkpoint_rows)
    if not np.array_equal(
        store.validation_rows[checkpoint_positions], checkpoint_rows
    ):
        raise RuntimeError("E10M checkpoint row conversion differs")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E10M training requires CUDA")
    device = torch.device("cuda")
    config = {
        "latent_dim": 192,
        "primitive_action_dim": primitive_action_dim,
        "action_horizon": e10v.ACTION_HORIZON,
        "width": e10v.WIDTH,
        "depth": e10v.DEPTH,
        "time_embedding_dim": e10v.TIME_EMBEDDING_DIM,
    }
    velocity = args.condition != "gaussian_true"
    model: torch.nn.Module = (
        VelocityActionDiffusion(**config)
        if velocity
        else ConditionalDiagonalGaussian(**config)
    )
    model = model.to(device)
    ema = copy.deepcopy(model).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=e10v.LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=e10v.WEIGHT_DECAY,
    )
    schedule = CosineDiffusionSchedule.build(e10v.DIFFUSION_STEPS)
    alpha_bar = schedule.alpha_bar.to(device)
    batch_generator = torch.Generator(device="cpu").manual_seed(
        e10v.derived_seed(f"gdp-e10m-batches|{args.task}|seed={args.seed}")
    )
    diffusion_generator = torch.Generator(device=device).manual_seed(
        e10v.derived_seed(f"gdp-e10m-diffusion|{args.task}|seed={args.seed}")
    )
    dropout_generator = torch.Generator(device=device).manual_seed(
        e10v.derived_seed(f"gdp-e10m-dropout|{args.task}|seed={args.seed}")
    )
    validation_generator = torch.Generator(device="cpu").manual_seed(
        e10v.derived_seed(f"gdp-e10m-validation|{args.task}|seed={args.seed}")
    )
    validation_timestep = torch.randint(
        0,
        e10v.DIFFUSION_STEPS,
        (e10v.VALIDATION_COUNT,),
        generator=validation_generator,
    )
    validation_noise = torch.randn(
        e10v.VALIDATION_COUNT,
        e10v.ACTION_HORIZON,
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
        for step in range(1, e10v.TRAIN_STEPS + 1):
            model.train()
            positions = torch.randint(
                len(store.train_rows),
                (e10v.BATCH_SIZE,),
                generator=batch_generator,
            ).numpy()
            current, goal, clean = store.batch(positions, validation=False)
            current = current.to(device)
            goal = goal.to(device)
            clean = clean.to(device)
            optimizer.zero_grad(set_to_none=True)
            if velocity:
                assert isinstance(model, VelocityActionDiffusion)
                timestep = torch.randint(
                    0,
                    e10v.DIFFUSION_STEPS,
                    (e10v.BATCH_SIZE,),
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
                    e10v.BATCH_SIZE,
                    generator=dropout_generator,
                    device=device,
                ) >= e10v.CONDITION_DROPOUT
                alpha = alpha_bar[timestep].view(-1, 1, 1)
                noisy = alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise
                target = alpha.sqrt() * noise - (1.0 - alpha).sqrt() * clean
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    prediction = model(
                        current, goal, noisy, timestep, conditioned=conditioned
                    )
                    loss = (prediction.float() - target).square().mean()
            else:
                assert isinstance(model, ConditionalDiagonalGaussian)
                conditioned = torch.ones(e10v.BATCH_SIZE, device=device, dtype=torch.bool)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    mean, log_std = model(current, goal)
                    standardized = (clean - mean.float()) / log_std.float().exp()
                    loss = (
                        0.5 * standardized.square() + log_std.float()
                    ).mean()
            if not torch.isfinite(loss):
                raise RuntimeError("E10M training loss is non-finite")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), e10v.GRADIENT_CLIP
            )
            if not torch.isfinite(gradient_norm):
                raise RuntimeError("E10M gradient norm is non-finite")
            rate = e10v.learning_rate(step)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            e10v.update_ema(ema, model)

            if step % e10v.VALIDATION_EVERY == 0:
                metrics = (
                    e10v.validate(
                        ema,
                        store=store,
                        alternate_store=alternate_store,
                        positions=checkpoint_positions,
                        timestep_bank=validation_timestep,
                        noise_bank=validation_noise,
                        schedule=schedule,
                        device=device,
                    )
                    if velocity
                    else validate_gaussian(
                        ema,
                        store=store,
                        positions=checkpoint_positions,
                        device=device,
                    )
                )
                objective_key = (
                    "conditional_velocity_mse"
                    if velocity
                    else "conditional_gaussian_nll"
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
                objective = metrics[objective_key]
                if objective < best_objective:
                    best_objective = objective
                    best_step = step
                    best_validation = metrics
                    payload = {
                        "kind": "gdp_cem_e10m_p1_model_checkpoint",
                        "proposal_kind": (
                            "velocity_diffusion" if velocity else "gaussian"
                        ),
                        "prediction_type": "velocity" if velocity else None,
                        "condition": args.condition,
                        "task": args.task,
                        "seed": args.seed,
                        "model_config": config,
                        "state_dict": e10v.cpu_state_dict(model),
                        "ema_state_dict": e10v.cpu_state_dict(ema),
                        "latent_mean": torch.from_numpy(latent_mean),
                        "latent_std": torch.from_numpy(latent_std),
                        "action_mean": torch.from_numpy(action_mean),
                        "action_std": torch.from_numpy(action_std),
                        "robust_low": torch.from_numpy(robust_low),
                        "robust_high": torch.from_numpy(robust_high),
                        "diffusion_steps": e10v.DIFFUSION_STEPS if velocity else None,
                        "condition_dropout": (
                            e10v.CONDITION_DROPOUT if velocity else None
                        ),
                        "best_step": best_step,
                        "best_validation": best_validation,
                        "parameter_count": parameter_count,
                        "row_selection": row_selection,
                        "checkpoint_rows": torch.from_numpy(checkpoint_rows),
                        "e10v_final_rows": torch.from_numpy(final_rows),
                        "confirmation_rows": torch.from_numpy(confirmation_rows),
                        "protocol_sha256": PROTOCOL_SHA256,
                        "source_manifest_sha256": e10v.sha256_file(
                            args.source_manifest
                        ),
                        "sequence_h5_sha256": sequence_sha,
                        "latent_h5_sha256": latent_sha,
                    }
                    e10v.atomic_torch_save(checkpoint_path, payload)
    if best_step < 0 or best_validation is None or not checkpoint_path.is_file():
        raise RuntimeError("E10M training produced no checkpoint")
    torch.cuda.synchronize()
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e10m_p1_model_training",
        "analysis_role": "fixed_configuration_multiseed_P1_replication",
        "task": args.task,
        "condition": args.condition,
        "proposal_kind": "velocity_diffusion" if velocity else "gaussian",
        "prediction_type": "velocity" if velocity else None,
        "seed": args.seed,
        "model_config": config,
        "parameter_count": parameter_count,
        "optimization": {
            "optimizer": "AdamW",
            "peak_learning_rate": e10v.LEARNING_RATE,
            "batch_size": e10v.BATCH_SIZE,
            "train_steps": e10v.TRAIN_STEPS,
            "ema_decay": e10v.EMA_DECAY,
            "condition_dropout": e10v.CONDITION_DROPOUT if velocity else None,
        },
        "best_step": best_step,
        "best_validation": best_validation,
        "row_selection": row_selection,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": e10v.sha256_file(checkpoint_path),
        "training_trace": str(trace_path),
        "training_trace_sha256": e10v.sha256_file(trace_path),
        "latent_h5_sha256": latent_sha,
        "sequence_h5_sha256": sequence_sha,
        "sequence_manifest_sha256": e10v.sha256_file(args.sequence_manifest),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": e10v.sha256_file(args.source_manifest),
        "trainer_source_sha256": e10v.sha256_file(Path(__file__)),
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
        "d2_read": False,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    e10v.atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
