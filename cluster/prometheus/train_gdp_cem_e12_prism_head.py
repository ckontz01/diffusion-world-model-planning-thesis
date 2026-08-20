#!/usr/bin/env python3
"""Train one P1-only published-equation PRISM PriorHead for E12."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from gdp_cem_e12_prism_data import P1_TRAIN, P1_VALIDATION, load_prism_head_arrays
from gdp_cem_e12_prism_models import (
    PRISM_PRIOR_HEAD_SHA256,
    PRISM_UPSTREAM_COMMIT,
    PrismPriorHead,
    cpu_state_dict,
    prism_beta_nll_loss,
)


EPOCHS = 50
BATCH_SIZE = 256
LEARNING_RATE = 3.0e-4
WEIGHT_DECAY = 1.0e-4
WARMUP_STEPS = 1_000
BETA = 0.5
GRADIENT_CLIP = 1.0


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


def cosine_warmup_factor(step: int, total_steps: int) -> float:
    if step < WARMUP_STEPS:
        return step / max(WARMUP_STEPS, 1)
    progress = (step - WARMUP_STEPS) / max(total_steps - WARMUP_STEPS, 1)
    return 0.5 * (1.0 + math.cos(math.pi * min(max(progress, 0.0), 1.0)))


@torch.inference_mode()
def validate(
    head: PrismPriorHead,
    *,
    latents: torch.Tensor,
    source_index: torch.Tensor,
    goal_index: torch.Tensor,
    targets: torch.Tensor,
    rows: torch.Tensor,
) -> dict[str, float]:
    head.eval()
    nll_sum = 0.0
    mse_sum = 0.0
    sigma_sum = 0.0
    sigma_square_sum = 0.0
    sigma_min = math.inf
    sigma_max = -math.inf
    coordinate_count = 0
    sample_count = 0
    for start in range(0, len(rows), BATCH_SIZE):
        selected = rows[start : start + BATCH_SIZE]
        current = latents.index_select(0, source_index.index_select(0, selected))
        goal = latents.index_select(0, goal_index.index_select(0, selected))
        target = targets.index_select(0, selected)
        mean, sigma = head(current, goal)
        count = len(selected)
        nll_sum += float(prism_beta_nll_loss(mean, sigma, target, beta=BETA).cpu()) * count
        mse_sum += float((mean - target).square().mean().cpu()) * count
        flat = sigma.float().flatten()
        sigma_sum += float(flat.sum().cpu())
        sigma_square_sum += float(flat.square().sum().cpu())
        sigma_min = min(sigma_min, float(flat.min().cpu()))
        sigma_max = max(sigma_max, float(flat.max().cpu()))
        coordinate_count += flat.numel()
        sample_count += count
    if not sample_count or not coordinate_count:
        raise RuntimeError("empty E12 PRISM validation")
    sigma_mean = sigma_sum / coordinate_count
    sigma_variance = max(sigma_square_sum / coordinate_count - sigma_mean**2, 0.0)
    head.train()
    return {
        "beta_nll": nll_sum / sample_count,
        "mean_mse": mse_sum / sample_count,
        "sigma_mean": sigma_mean,
        "sigma_std": math.sqrt(sigma_variance),
        "sigma_min": sigma_min,
        "sigma_max": sigma_max,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "reacher", "cube"), required=True)
    parser.add_argument("--goal-mode", choices=("h25", "endframe"), required=True)
    parser.add_argument("--seed", type=int, choices=(6101, 6102, 6103), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--sequence-h5", type=Path, required=True)
    parser.add_argument("--sequence-manifest", type=Path, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.protocol,
        args.source_manifest,
        args.sequence_h5,
        args.sequence_manifest,
        args.latent_h5,
        args.latent_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
        if any(token in {"c1", "i1", "p4", "d3", "d4"} for token in path.parts):
            raise RuntimeError(f"protected/confirmation input forbidden in E12 training: {path}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E12 PRISM-head output")
    if not torch.cuda.is_available():
        raise RuntimeError("E12 PRISM-head training requires CUDA")
    device = torch.device("cuda")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)

    started = time.time()
    arrays = load_prism_head_arrays(
        sequence_h5=args.sequence_h5,
        latent_h5=args.latent_h5,
        goal_mode=args.goal_mode,
    )
    role_numpy = np.asarray(arrays["role"], dtype=np.uint8)
    train_rows_numpy = np.flatnonzero(role_numpy == P1_TRAIN).astype(np.int64)
    validation_rows_numpy = np.flatnonzero(role_numpy == P1_VALIDATION).astype(np.int64)
    if not len(train_rows_numpy) or not len(validation_rows_numpy):
        raise RuntimeError("E12 PRISM head requires both P1 roles")

    latents = torch.from_numpy(np.asarray(arrays["latents"], dtype=np.float32)).to(device)
    source_index = torch.from_numpy(
        np.asarray(arrays["source_index"], dtype=np.int64)
    ).to(device)
    goal_index = torch.from_numpy(np.asarray(arrays["goal_index"], dtype=np.int64)).to(device)
    normalized_actions = torch.from_numpy(
        np.asarray(arrays["normalized_actions"], dtype=np.float32)
    ).to(device)
    targets = normalized_actions.reshape(
        len(normalized_actions), 5, 5, int(arrays["primitive_action_dim"])
    )
    train_rows = torch.from_numpy(train_rows_numpy).to(device)
    validation_rows = torch.from_numpy(validation_rows_numpy).to(device)

    head = PrismPriorHead(
        z_dim=latents.shape[1],
        horizon=5,
        action_block=5,
        raw_action_dim=int(arrays["primitive_action_dim"]),
        hidden=512,
        sigma_floor=0.05,
    ).to(device)
    parameter_count = sum(parameter.numel() for parameter in head.parameters())
    optimizer = torch.optim.AdamW(
        head.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    steps_per_epoch = math.ceil(len(train_rows) / BATCH_SIZE)
    total_steps = EPOCHS * steps_per_epoch
    initial_validation = validate(
        head,
        latents=latents,
        source_index=source_index,
        goal_index=goal_index,
        targets=targets,
        rows=validation_rows,
    )

    history: list[dict[str, Any]] = []
    best_objective = math.inf
    best_epoch = -1
    best_state: dict[str, torch.Tensor] | None = None
    global_step = 0
    args.output_dir.mkdir(parents=True, exist_ok=False)
    trace_path = args.output_dir / "training.jsonl"
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for epoch in range(1, EPOCHS + 1):
            epoch_started = time.time()
            head.train()
            permutation = train_rows[
                torch.randperm(len(train_rows), device=device)
            ]
            objective_sum = 0.0
            sample_count = 0
            maximum_gradient_norm = 0.0
            for batch_start in range(0, len(permutation), BATCH_SIZE):
                selected = permutation[batch_start : batch_start + BATCH_SIZE]
                current = latents.index_select(0, source_index.index_select(0, selected))
                goal = latents.index_select(0, goal_index.index_select(0, selected))
                target = targets.index_select(0, selected)
                mean, sigma = head(current, goal)
                loss = prism_beta_nll_loss(mean, sigma, target, beta=BETA)
                if not torch.isfinite(loss):
                    raise RuntimeError("non-finite E12 PRISM-head objective")
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    head.parameters(), GRADIENT_CLIP
                )
                if not torch.isfinite(gradient_norm):
                    raise RuntimeError("non-finite E12 PRISM-head gradient")
                rate = LEARNING_RATE * cosine_warmup_factor(global_step, total_steps)
                for group in optimizer.param_groups:
                    group["lr"] = rate
                optimizer.step()
                count = len(selected)
                objective_sum += float(loss.detach().cpu()) * count
                sample_count += count
                maximum_gradient_norm = max(
                    maximum_gradient_norm, float(gradient_norm.detach().cpu())
                )
                global_step += 1
            validation = validate(
                head,
                latents=latents,
                source_index=source_index,
                goal_index=goal_index,
                targets=targets,
                rows=validation_rows,
            )
            record = {
                "epoch": epoch,
                "global_step": global_step,
                "train_beta_nll": objective_sum / sample_count,
                "validation": validation,
                "learning_rate": optimizer.param_groups[0]["lr"],
                "maximum_preclip_gradient_norm": maximum_gradient_norm,
                "epoch_seconds": time.time() - epoch_started,
            }
            history.append(record)
            trace.write(json.dumps(record, sort_keys=True) + "\n")
            trace.flush()
            if validation["beta_nll"] < best_objective:
                best_objective = validation["beta_nll"]
                best_epoch = epoch
                best_state = cpu_state_dict(head)
            print(json.dumps(record, sort_keys=True), flush=True)

    if best_state is None:
        raise RuntimeError("E12 PRISM head never produced a checkpoint")
    head.load_state_dict(best_state)
    best_validation = validate(
        head,
        latents=latents,
        source_index=source_index,
        goal_index=goal_index,
        targets=targets,
        rows=validation_rows,
    )
    relative_mse_drop = (
        initial_validation["mean_mse"] - best_validation["mean_mse"]
    ) / max(initial_validation["mean_mse"], 1.0e-12)
    validity = {
        "finite": all(
            math.isfinite(float(value))
            for value in best_validation.values()
        ),
        "validation_mse_relative_drop": relative_mse_drop,
        "validation_mse_drop_at_least_15_percent": relative_mse_drop >= 0.15,
        "sigma_above_floor": best_validation["sigma_min"] >= 0.05,
        "sigma_nonconstant": best_validation["sigma_std"] >= 0.01,
    }
    validity["passed"] = all(
        (
            validity["finite"],
            validity["validation_mse_drop_at_least_15_percent"],
            validity["sigma_above_floor"],
            validity["sigma_nonconstant"],
        )
    )
    checkpoint_path = args.output_dir / "best.pt"
    payload = {
        "kind": "gdp_cem_e12_prism_prior_head_checkpoint",
        "analysis_role": "P1_only_matched_PRISM_training",
        "task": args.task,
        "goal_mode": args.goal_mode,
        "seed": args.seed,
        "model_config": {
            "z_dim": int(latents.shape[1]),
            "horizon": 5,
            "action_block": 5,
            "raw_action_dim": int(arrays["primitive_action_dim"]),
            "hidden": 512,
            "sigma_floor": 0.05,
        },
        "state_dict": best_state,
        "p1_action_mean": np.asarray(arrays["action_mean"], dtype=np.float32),
        "p1_action_std": np.asarray(arrays["action_std"], dtype=np.float32),
        "parameter_count": parameter_count,
        "best_epoch": best_epoch,
        "initial_validation": initial_validation,
        "best_validation": best_validation,
        "validity": validity,
        "training_recipe": {
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "warmup_steps": WARMUP_STEPS,
            "schedule": "linear_warmup_then_cosine",
            "beta_nll_beta": BETA,
            "gradient_clip": GRADIENT_CLIP,
        },
        "prism_upstream_commit": PRISM_UPSTREAM_COMMIT,
        "prism_prior_head_sha256": PRISM_PRIOR_HEAD_SHA256,
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "sequence_h5_sha256": sha256_file(args.sequence_h5),
        "sequence_manifest_sha256": sha256_file(args.sequence_manifest),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "latent_manifest_sha256": sha256_file(args.latent_manifest),
        "p1_train_sequences": len(train_rows_numpy),
        "p1_validation_sequences": len(validation_rows_numpy),
        "protected_inputs_read": False,
    }
    atomic_torch_save(checkpoint_path, payload)
    summary = {
        "status": "ok" if validity["passed"] else "invalid",
        "kind": "gdp_cem_e12_prism_prior_head_training",
        "analysis_role": "P1_only_matched_PRISM_training",
        "task": args.task,
        "goal_mode": args.goal_mode,
        "seed": args.seed,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "training_trace": str(trace_path),
        "training_trace_sha256": sha256_file(trace_path),
        "parameter_count": parameter_count,
        "best_epoch": best_epoch,
        "initial_validation": initial_validation,
        "best_validation": best_validation,
        "validity": validity,
        "elapsed_seconds": time.time() - started,
        "protocol_sha256": payload["protocol_sha256"],
        "source_manifest_sha256": payload["source_manifest_sha256"],
        "sequence_h5_sha256": payload["sequence_h5_sha256"],
        "latent_h5_sha256": payload["latent_h5_sha256"],
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
