#!/usr/bin/env python3
"""Actual-cache/GPU structural preflight for frozen E14 training."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import E14ArrayStore, sha256_file
from gdp_cem_e14_models import (
    CosineSchedule,
    SAGEOptionPrior,
    SAGESubgoalGenerator,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    endpoint_output_dim,
    sample_trajectory_gmm,
    trajectory_gmm_nll,
    velocity_ddim_sample,
    velocity_target,
)
from train_gdp_cem_e14_endpoint import masked_mean
from train_gdp_cem_e14_sage import subgoal_loss


def atomic_json(path: Path, value: object) -> None:
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
    if args.output_json.exists():
        raise SystemExit("refusing to overwrite E14 preflight output")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E14 preflight protocol hash differs")
    if not torch.cuda.is_available():
        raise RuntimeError("E14 training preflight requires CUDA")
    torch.manual_seed(1414)
    torch.cuda.manual_seed_all(1414)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    store = E14ArrayStore(
        task=args.task,
        latent_h5=args.latent_h5,
        latent_manifest=args.latent_manifest,
        cache_h5=args.cache_h5,
        cache_manifest=args.cache_manifest,
    )
    selected = []
    for duration in spec.TAU_VALUES:
        candidate = store.train_rows[store.tau[store.train_rows] == duration]
        selected.append(int(candidate[0]))
    rows = np.asarray(selected, dtype=np.int64)
    batch = store.batch(rows)
    current = batch.current.to(device)
    goal = batch.goal.to(device)
    state = batch.state.to(device)
    delta = batch.delta.to(device)
    tau = batch.tau.to(device)
    schedule = CosineSchedule.build(spec.DIFFUSION_STEPS)
    checks: dict[str, object] = {}

    for endpoint in ("vad", "cvd"):
        clean, mask = batch.endpoint_target(endpoint)
        clean = clean.to(device)
        mask = mask.to(device)
        output_dim = endpoint_output_dim(
            endpoint,
            latent_dim=store.latent_dim,
            primitive_action_dim=store.primitive_action_dim,
        )
        config = {
            "latent_dim": store.latent_dim,
            "state_dim": store.state_dim,
            "output_dim": output_dim,
            "width": spec.MODEL_WIDTH,
            "depth": spec.MODEL_DEPTH,
            "time_embedding_dim": spec.TIME_EMBEDDING_DIM,
        }
        diffusion = VariableVelocityDiffusion(**config).to(device)
        timestep = torch.tensor([0, 50, 99], device=device)
        noise = torch.randn_like(clean) * mask
        alpha = schedule.alpha_bar.to(device)[timestep, None]
        noisy = (alpha.sqrt() * clean + (1.0 - alpha).sqrt() * noise) * mask
        target = velocity_target(clean, noise, alpha) * mask
        prediction = diffusion(
            current,
            goal,
            state,
            delta,
            tau,
            noisy,
            timestep,
            conditioned=torch.tensor([True, False, True], device=device),
        )
        diffusion_loss = masked_mean((prediction - target).square(), mask)
        diffusion_loss.backward()
        if not torch.isfinite(diffusion_loss):
            raise RuntimeError("E14 diffusion structural loss is non-finite")
        initial_noise = torch.randn(3, 16, output_dim, device=device) * mask[:, None]
        samples = velocity_ddim_sample(
            diffusion.eval(),
            current=current,
            goal=goal,
            state=state,
            delta=delta,
            tau=tau,
            initial_noise=initial_noise,
            active_mask=mask,
            schedule=schedule,
            evaluations=spec.DIFFUSION_EVALUATIONS,
            guidance_scale=spec.GUIDANCE_SCALE,
        )
        gaussian = VariableDiagonalGaussian(**config).to(device)
        mean, log_std = gaussian(current, goal, state, delta, tau)
        gaussian_loss = masked_mean(
            0.5 * ((clean - mean) / log_std.exp()).square() + log_std,
            mask,
        )
        gaussian_loss.backward()
        if (
            samples.shape != (3, 16, output_dim)
            or not torch.isfinite(samples).all()
            or not torch.isfinite(gaussian_loss)
        ):
            raise RuntimeError("E14 endpoint candidate shape/value differs")
        action_offset = 0 if endpoint == "vad" else store.latent_dim
        actions = samples[:, :, action_offset:].reshape(
            3, 16, spec.ACTION_HORIZON, store.primitive_action_dim
        )
        if actions.shape[-2:] != (
            spec.ACTION_HORIZON,
            store.primitive_action_dim,
        ):
            raise RuntimeError("E14 Le-WM action-candidate interface differs")
        checks[endpoint] = {
            "diffusion_parameters": sum(p.numel() for p in diffusion.parameters()),
            "gaussian_parameters": sum(p.numel() for p in gaussian.parameters()),
            "output_dim": output_dim,
            "candidate_shape": list(samples.shape),
            "action_shape": list(actions.shape),
        }
        del diffusion, gaussian, samples, prediction, mean, log_std
        torch.cuda.empty_cache()

    subgoal = SAGESubgoalGenerator(
        latent_dim=store.latent_dim, state_dim=store.state_dim
    ).to(device)
    generated_local = subgoal(current, goal, state, delta, tau)
    sage_subgoal_loss, _, _ = subgoal_loss(generated_local, batch.local.to(device))
    sage_subgoal_loss.backward()
    subgoal_parameters = sum(parameter.numel() for parameter in subgoal.parameters())
    subgoal.zero_grad(set_to_none=True)
    option = SAGEOptionPrior(
        latent_dim=store.latent_dim,
        state_dim=store.state_dim,
        primitive_action_dim=store.primitive_action_dim,
    ).to(device)
    logits, means, log_stds = option(
        current, goal, generated_local.detach(), state, delta, tau
    )
    option_loss = trajectory_gmm_nll(
        logits,
        means,
        log_stds,
        batch.action.to(device),
        batch.action_mask.to(device),
    ).mean()
    option_loss.backward()
    option_samples = sample_trajectory_gmm(
        logits.detach(),
        means.detach(),
        log_stds.detach(),
        count=16,
        active_mask=batch.action_mask.to(device),
        generator=torch.Generator(device="cpu").manual_seed(1415),
    )
    if (
        generated_local.shape != (3, store.latent_dim)
        or option_samples.shape
        != (3, 16, spec.ACTION_HORIZON, store.primitive_action_dim)
        or not torch.isfinite(sage_subgoal_loss)
        or not torch.isfinite(option_loss)
        or not torch.isfinite(option_samples).all()
    ):
        raise RuntimeError("E14 SAGE reconstruction interface differs")
    checks["sage"] = {
        "subgoal_parameters": subgoal_parameters,
        "option_parameters": sum(parameter.numel() for parameter in option.parameters()),
        "generated_local_shape": list(generated_local.shape),
        "option_candidate_shape": list(option_samples.shape),
    }

    record = {
        "status": "passed",
        "kind": "gdp_cem_e14_actual_cache_gpu_training_preflight",
        "task": args.task,
        "rows": rows.tolist(),
        "tau": tau.cpu().tolist(),
        "checks": checks,
        "lineage": store.lineage,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "performance_inspected": False,
        "claim_allowed": False,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output_json, record)
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
