#!/usr/bin/env python3
"""Actual-data/GPU preflight for the frozen E15 training snapshot."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch

import gdp_cem_e15_specs as spec
from gdp_cem_e15_data import E15TrainingStore, sha256_file
from gdp_cem_e15_models import (
    CosineSchedule,
    DirectTrajectoryGMM,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    bounded_actions_from_standardized_u,
    direct_gmm_loss,
    instantiate_model,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=spec.TASKS, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--cache-h5", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.latent_h5,
        args.latent_manifest,
        args.cache_h5,
        args.cache_manifest,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_json):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_json.exists():
        raise SystemExit("refusing existing E15 training-preflight output")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E15 protocol hash differs")
    if not torch.cuda.is_available():
        raise RuntimeError("E15 training preflight requires CUDA")
    device = torch.device("cuda")
    if torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E15 training-preflight GPU differs")
    torch.manual_seed(1515)
    torch.cuda.manual_seed_all(1515)
    torch.use_deterministic_algorithms(True)
    store = E15TrainingStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    rows = np.asarray(
        [
            store.train_rows[
                (store.delta[store.train_rows] == delta)
                & (store.tau[store.train_rows] == tau)
            ][0]
            for delta, tau in spec.DELTA_TAU_PAIRS
        ],
        dtype=np.int64,
    )
    batch = store.batch(rows)
    current = batch.current.to(device)
    goal = batch.goal.to(device)
    state = batch.state.to(device)
    delta = batch.delta.to(device)
    tau = batch.tau.to(device)
    target_3d = batch.action_u.to(device)
    target_flat, flat_mask = batch.flat_target()
    target_flat = target_flat.to(device)
    flat_mask = flat_mask.to(device)
    mask_2d = batch.action_mask.to(device)
    records: dict[str, Any] = {}
    schedule = CosineSchedule.build(spec.DIFFUSION_STEPS)
    for condition in ("vad", "diagonal_gaussian", "direct_gmm"):
        model = instantiate_model(args.task, condition).to(device)
        model.train()
        if condition == "vad":
            assert isinstance(model, VariableVelocityDiffusion)
            timestep = torch.arange(len(rows), device=device) % spec.DIFFUSION_STEPS
            noise = torch.randn_like(target_flat)
            alpha = schedule.alpha_bar.to(device)[timestep, None]
            noisy = (
                alpha.sqrt() * target_flat
                + (1.0 - alpha).sqrt() * noise
            ) * flat_mask
            target = velocity_target(target_flat, noise, alpha) * flat_mask
            output = model(
                current, goal, state, delta, tau, noisy, timestep, conditioned=True
            )
            loss = (((output - target).square() * flat_mask).sum(-1) / flat_mask.sum(-1)).mean()
        elif condition == "diagonal_gaussian":
            assert isinstance(model, VariableDiagonalGaussian)
            mean, log_std = model(current, goal, state, delta, tau)
            element = 0.5 * ((target_flat - mean) / log_std.exp()).square() + log_std
            loss = ((element * flat_mask).sum(-1) / flat_mask.sum(-1)).mean()
        else:
            assert isinstance(model, DirectTrajectoryGMM)
            logits, means, log_stds = model(current, goal, state, delta, tau)
            loss, _, _ = direct_gmm_loss(
                logits, means, log_stds, target_3d, mask_2d
            )
        loss.backward()
        if not torch.isfinite(loss) or any(
            parameter.grad is not None and not torch.isfinite(parameter.grad).all()
            for parameter in model.parameters()
        ):
            raise RuntimeError(f"E15 {condition} preflight is non-finite")
        records[condition] = {
            "parameter_count": sum(p.numel() for p in model.parameters()),
            "smoke_loss": float(loss.detach().cpu()),
        }
        del model

    zero = torch.zeros(
        len(rows),
        2,
        spec.ACTION_HORIZON,
        store.primitive_action_dim,
        device=device,
    )
    active = (
        torch.arange(spec.ACTION_HORIZON, device=device)[None, :] < tau[:, None]
    )[:, :, None].expand(-1, -1, store.primitive_action_dim)
    raw, planner, jacobian = bounded_actions_from_standardized_u(
        zero,
        u_mean=torch.from_numpy(store.u_mean).to(device),
        u_std=torch.from_numpy(store.u_std).to(device),
        planner_mean=torch.from_numpy(store.planner_action_mean).to(device),
        planner_std=torch.from_numpy(store.planner_action_std).to(device),
        interior_scale=store.interior_scale,
        active_mask=active,
    )
    if (
        torch.any(torch.abs(raw[active[:, None].expand_as(raw)]) >= 1.0)
        or not torch.isfinite(planner).all()
        or not torch.isfinite(jacobian).all()
    ):
        raise RuntimeError("E15 bounded decoder preflight failed")
    result = {
        "status": "ok",
        "kind": "gdp_cem_e15_actual_data_training_preflight",
        "task": args.task,
        "sampled_one_row_per_delta_tau_cell": True,
        "sample_row_count": len(rows),
        "models": records,
        "lineage": store.lineage,
        "training_rows": spec.TRAIN_ROWS,
        "validation_payload_rows_read": store.validation_payload_rows_read,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "gpu": torch.cuda.get_device_name(0),
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
