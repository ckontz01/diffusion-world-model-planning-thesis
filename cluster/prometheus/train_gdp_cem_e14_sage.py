#!/usr/bin/env python3
"""Train the frozen published-equation SAGE reconstruction for E14."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import time
from importlib import metadata
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
import torch.nn.functional as functional

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import E14ArrayStore, sha256_file
from gdp_cem_e14_models import (
    SAGEOptionPrior,
    SAGESubgoalGenerator,
    trajectory_gmm_nll,
)


Component = Literal["subgoal", "option"]
SAGE_BATCH_SIZE = 128
SAGE_LEARNING_RATE = 1.0e-4
SAGE_WEIGHT_DECAY = 1.0e-4
SAGE_GRADIENT_CLIP = 1.0
SAGE_SUBGOAL_EPOCHS = 5
SAGE_OPTION_EPOCHS = 3
SAGE_MODES = 8
SAGE_WIDTH = 512
SAGE_HEADS = 8
SAGE_SUBGOAL_DEPTH = 4
SAGE_OPTION_DEPTH = 3
SAGE_SUBGOAL_FEEDFORWARD = 2816
SAGE_OPTION_FEEDFORWARD = 2048


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


def subgoal_loss(
    prediction: torch.Tensor, target: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    smooth = functional.smooth_l1_loss(prediction.float(), target, reduction="none").mean(
        dim=-1
    )
    cosine = 1.0 - functional.cosine_similarity(
        prediction.float(), target, dim=-1, eps=1.0e-8
    )
    return (smooth + cosine).mean(), smooth.mean(), cosine.mean()


def load_subgoal(
    path: Path,
    *,
    task: str,
    seed: int,
    store: E14ArrayStore,
    device: torch.device,
) -> tuple[SAGESubgoalGenerator, str]:
    record = torch.load(path, map_location="cpu", weights_only=False)
    expected = {
        "latent_dim": store.latent_dim,
        "state_dim": store.state_dim,
        "width": SAGE_WIDTH,
        "depth": SAGE_SUBGOAL_DEPTH,
        "heads": SAGE_HEADS,
        "feedforward_dim": SAGE_SUBGOAL_FEEDFORWARD,
    }
    if (
        record.get("kind") != "gdp_cem_e14_sage_subgoal_checkpoint"
        or record.get("task") != task
        or int(record.get("seed", -1)) != seed
        or record.get("model_config") != expected
        or record.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or record.get("lineage") != store.lineage
    ):
        raise RuntimeError("E14 SAGE subgoal checkpoint lineage differs")
    model = SAGESubgoalGenerator(**expected)
    model.load_state_dict(record["state_dict"], strict=True)
    return model.to(device).eval().requires_grad_(False), sha256_file(path)


@torch.inference_mode()
def validate_subgoal(
    model: SAGESubgoalGenerator,
    *,
    store: E14ArrayStore,
    rows: np.ndarray,
    device: torch.device,
) -> dict[str, float]:
    objective: list[torch.Tensor] = []
    smooth: list[torch.Tensor] = []
    cosine: list[torch.Tensor] = []
    mse: list[torch.Tensor] = []
    model.eval()
    for start in range(0, len(rows), spec.VALIDATION_BATCH_SIZE):
        batch = store.batch(rows[start : start + spec.VALIDATION_BATCH_SIZE])
        current = batch.current.to(device)
        goal = batch.goal.to(device)
        state = batch.state.to(device)
        delta = batch.delta.to(device)
        tau = batch.tau.to(device)
        target = batch.local.to(device)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            prediction = model(current, goal, state, delta, tau)
        prediction = prediction.float()
        row_smooth = functional.smooth_l1_loss(
            prediction, target, reduction="none"
        ).mean(dim=-1)
        row_cosine = 1.0 - functional.cosine_similarity(
            prediction, target, dim=-1, eps=1.0e-8
        )
        objective.append((row_smooth + row_cosine).cpu())
        smooth.append(row_smooth.cpu())
        cosine.append(row_cosine.cpu())
        mse.append((prediction - target).square().mean(dim=-1).cpu())
    return {
        "objective": float(torch.cat(objective).double().mean()),
        "smooth_l1": float(torch.cat(smooth).double().mean()),
        "cosine_distance": float(torch.cat(cosine).double().mean()),
        "latent_mse": float(torch.cat(mse).double().mean()),
    }


@torch.inference_mode()
def validate_option(
    model: SAGEOptionPrior,
    subgoal: SAGESubgoalGenerator,
    *,
    store: E14ArrayStore,
    rows: np.ndarray,
    device: torch.device,
) -> dict[str, float]:
    nll: list[torch.Tensor] = []
    nll_per_dimension: list[torch.Tensor] = []
    mean_mse: list[torch.Tensor] = []
    model.eval()
    subgoal.eval()
    for start in range(0, len(rows), spec.VALIDATION_BATCH_SIZE):
        batch = store.batch(rows[start : start + spec.VALIDATION_BATCH_SIZE])
        current = batch.current.to(device)
        goal = batch.goal.to(device)
        state = batch.state.to(device)
        delta = batch.delta.to(device)
        tau = batch.tau.to(device)
        target = batch.action.to(device)
        active = batch.action_mask.to(device)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            generated_local = subgoal(current, goal, state, delta, tau)
            logits, means, log_stds = model(
                current, goal, generated_local, state, delta, tau
            )
        logits = logits.float()
        means = means.float()
        log_stds = log_stds.float()
        row_nll = trajectory_gmm_nll(
            logits, means, log_stds, target, active
        )
        dimensions = active.sum(dim=-1) * store.primitive_action_dim
        probability = torch.softmax(logits, dim=-1)
        expected = (probability[:, :, None, None] * means).sum(dim=1)
        weight = active[:, :, None].to(expected.dtype)
        row_mse = ((expected - target).square() * weight).sum(dim=(-1, -2)) / dimensions
        nll.append(row_nll.cpu())
        nll_per_dimension.append((row_nll / dimensions).cpu())
        mean_mse.append(row_mse.cpu())
    return {
        "trajectory_gmm_nll": float(torch.cat(nll).double().mean()),
        "nll_per_active_dimension": float(
            torch.cat(nll_per_dimension).double().mean()
        ),
        "mixture_mean_action_mse": float(torch.cat(mean_mse).double().mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--component", choices=("subgoal", "option"), required=True)
    parser.add_argument("--seed", type=int, choices=spec.MODEL_SEEDS, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--subgoal-checkpoint", type=Path)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    component: Component = args.component
    required = [
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.protocol,
        args.source_manifest,
    ]
    if component == "option":
        if args.subgoal_checkpoint is None:
            raise ValueError("E14 SAGE option training needs --subgoal-checkpoint")
        required.append(args.subgoal_checkpoint)
    elif args.subgoal_checkpoint is not None:
        raise ValueError("E14 SAGE subgoal training forbids --subgoal-checkpoint")
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E14 protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E14 SAGE output")

    started = time.time()
    store = E14ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E14 SAGE training requires CUDA")
    device = torch.device("cuda")
    subgoal_model: SAGESubgoalGenerator | None = None
    subgoal_checkpoint_sha256: str | None = None
    if component == "subgoal":
        model_config = {
            "latent_dim": store.latent_dim,
            "state_dim": store.state_dim,
            "width": SAGE_WIDTH,
            "depth": SAGE_SUBGOAL_DEPTH,
            "heads": SAGE_HEADS,
            "feedforward_dim": SAGE_SUBGOAL_FEEDFORWARD,
        }
        model: torch.nn.Module = SAGESubgoalGenerator(**model_config)
        epochs = SAGE_SUBGOAL_EPOCHS
    else:
        assert args.subgoal_checkpoint is not None
        subgoal_model, subgoal_checkpoint_sha256 = load_subgoal(
            args.subgoal_checkpoint,
            task=args.task,
            seed=args.seed,
            store=store,
            device=device,
        )
        model_config = {
            "latent_dim": store.latent_dim,
            "state_dim": store.state_dim,
            "primitive_action_dim": store.primitive_action_dim,
            "width": SAGE_WIDTH,
            "depth": SAGE_OPTION_DEPTH,
            "heads": SAGE_HEADS,
            "feedforward_dim": SAGE_OPTION_FEEDFORWARD,
            "modes": SAGE_MODES,
            "action_blocks": 5,
            "block_size": 5,
        }
        model = SAGEOptionPrior(**model_config)
        epochs = SAGE_OPTION_EPOCHS
    model = model.to(device)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=SAGE_LEARNING_RATE,
        betas=(0.9, 0.999),
        weight_decay=SAGE_WEIGHT_DECAY,
    )
    permutation_generator = torch.Generator(device="cpu").manual_seed(
        spec.derived_seed(
            f"sage-permutations|task={args.task}|component={component}|seed={args.seed}"
        )
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "training.jsonl"
    checkpoint_path = args.output_dir / "best.pt"
    best_objective = math.inf
    best_epoch = -1
    best_validation: dict[str, float] | None = None
    torch.cuda.reset_peak_memory_stats(device)
    with trace_path.open("x", encoding="utf-8") as trace:
        for epoch in range(1, epochs + 1):
            model.train()
            permutation = torch.randperm(
                len(store.train_rows), generator=permutation_generator
            ).numpy()
            loss_sum = 0.0
            rows_seen = 0
            last_gradient_norm = math.nan
            for start in range(0, len(permutation), SAGE_BATCH_SIZE):
                positions = permutation[start : start + SAGE_BATCH_SIZE]
                rows = store.train_rows[positions]
                batch = store.batch(rows)
                current = batch.current.to(device)
                goal = batch.goal.to(device)
                state = batch.state.to(device)
                delta = batch.delta.to(device)
                tau = batch.tau.to(device)
                optimizer.zero_grad(set_to_none=True)
                if component == "subgoal":
                    assert isinstance(model, SAGESubgoalGenerator)
                    target = batch.local.to(device)
                    with torch.autocast("cuda", dtype=torch.bfloat16):
                        prediction = model(current, goal, state, delta, tau)
                        loss, _, _ = subgoal_loss(prediction, target)
                else:
                    assert isinstance(model, SAGEOptionPrior)
                    assert subgoal_model is not None
                    target = batch.action.to(device)
                    active = batch.action_mask.to(device)
                    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                        generated_local = subgoal_model(
                            current, goal, state, delta, tau
                        )
                    with torch.autocast("cuda", dtype=torch.bfloat16):
                        logits, means, log_stds = model(
                            current, goal, generated_local, state, delta, tau
                        )
                    loss = trajectory_gmm_nll(
                        logits.float(),
                        means.float(),
                        log_stds.float(),
                        target,
                        active,
                    ).mean()
                if not torch.isfinite(loss):
                    raise RuntimeError("E14 SAGE training loss is non-finite")
                loss.backward()
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), SAGE_GRADIENT_CLIP
                )
                if not torch.isfinite(gradient_norm):
                    raise RuntimeError("E14 SAGE gradient norm is non-finite")
                optimizer.step()
                batch_rows = len(rows)
                loss_sum += float(loss.detach().cpu()) * batch_rows
                rows_seen += batch_rows
                last_gradient_norm = float(gradient_norm.detach().cpu())
            metrics = (
                validate_subgoal(
                    model,
                    store=store,
                    rows=store.validation_rows,
                    device=device,
                )
                if component == "subgoal"
                else validate_option(
                    model,
                    subgoal_model,
                    store=store,
                    rows=store.validation_rows,
                    device=device,
                )
            )
            objective_key = (
                "objective" if component == "subgoal" else "trajectory_gmm_nll"
            )
            record = {
                "epoch": epoch,
                "train_objective": loss_sum / rows_seen,
                "last_gradient_norm": last_gradient_norm,
                "validation": metrics,
            }
            trace.write(json.dumps(record, sort_keys=True) + "\n")
            trace.flush()
            if metrics[objective_key] < best_objective:
                best_objective = metrics[objective_key]
                best_epoch = epoch
                best_validation = metrics
                payload = {
                    "kind": f"gdp_cem_e14_sage_{component}_checkpoint",
                    "task": args.task,
                    "component": component,
                    "seed": args.seed,
                    "model_config": model_config,
                    "state_dict": cpu_state_dict(model),
                    "best_epoch": best_epoch,
                    "best_validation": best_validation,
                    "parameter_count": parameter_count,
                    "subgoal_checkpoint_sha256": subgoal_checkpoint_sha256,
                    "lineage": store.lineage,
                    "protocol_sha256": spec.PROTOCOL_SHA256,
                    "source_manifest_sha256": sha256_file(args.source_manifest),
                }
                atomic_torch_save(checkpoint_path, payload)

    if best_epoch < 0 or best_validation is None or not checkpoint_path.is_file():
        raise RuntimeError("E14 SAGE training produced no checkpoint")
    torch.cuda.synchronize()
    summary = {
        "status": "ok",
        "kind": f"gdp_cem_e14_sage_{component}_training",
        "analysis_role": "P1_only_published_equation_SAGE_reconstruction",
        "official_implementation": False,
        "task": args.task,
        "component": component,
        "seed": args.seed,
        "model_config": model_config,
        "parameter_count": parameter_count,
        "optimization": {
            "optimizer": "AdamW",
            "learning_rate": SAGE_LEARNING_RATE,
            "weight_decay": SAGE_WEIGHT_DECAY,
            "batch_size": SAGE_BATCH_SIZE,
            "epochs": epochs,
            "gradient_clip": SAGE_GRADIENT_CLIP,
            "precision": "BF16",
        },
        "best_epoch": best_epoch,
        "best_validation": best_validation,
        "subgoal_checkpoint_sha256": subgoal_checkpoint_sha256,
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
        "reconstruction_deviations": {
            "released_lewm_cls_latent": True,
            "history_length": 1,
            "pusht_state_key": "state",
            "cube_state_key": "observation",
            "cosine_loss_coefficient": 1.0,
            "gmm_covariance": "diagonal",
            "gmm_log_std_bounds": [-5.0, 2.0],
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

