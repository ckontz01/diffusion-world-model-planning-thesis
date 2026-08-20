#!/usr/bin/env python3
"""Numerically compare the shared wrapper to a released flat model's native cost."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.extract_flat_latents import preprocess_pixels
from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)
from acid_alternative.models import ConditionalDiffusionVerifier


def cloned(mapping):
    return {
        key: value.clone() if torch.is_tensor(value) else value
        for key, value in mapping.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--action-dim",
        type=int,
        help="Optional assertion; otherwise inferred as primitive width times frameskip.",
    )
    parser.add_argument("--frameskip", type=int, default=5)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--samples", type=int, default=17)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        raise SystemExit("refusing to overwrite output")
    if args.frameskip <= 0:
        raise ValueError("frameskip must be positive")
    torch.manual_seed(args.seed)
    device = torch.device("cuda")
    resolved_checkpoint = resolve_policy_checkpoint(args.policy, args.stablewm_home)
    if resolved_checkpoint != args.checkpoint_file.resolve():
        raise RuntimeError(
            f"policy resolves to {resolved_checkpoint}, not declared "
            f"{args.checkpoint_file.resolve()}"
        )
    model = swm.policy.AutoCostModel(args.policy, cache_dir=args.stablewm_home)
    model = model.to(device).eval()
    model.requires_grad_(False)
    if hasattr(model, "interpolate_pos_encoding"):
        model.interpolate_pos_encoding = True

    with h5py.File(args.dataset, "r") as handle:
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
        if len(offsets) == 0 or lengths[0] <= 25:
            raise RuntimeError("first dataset episode cannot supply a +25 goal")
        first_row = int(offsets[0])
        pixels = np.asarray(handle["pixels"][[first_row, first_row + 25]])
        primitive_action_dim = int(handle["action"].shape[-1])
    inferred_action_dim = primitive_action_dim * args.frameskip
    if args.action_dim is not None and args.action_dim != inferred_action_dim:
        raise RuntimeError(
            f"declared action dimension {args.action_dim} differs from inferred "
            f"dimension {inferred_action_dim}"
        )
    action_dim = inferred_action_dim
    transformed = preprocess_pixels(pixels, device)
    current = transformed[0].view(1, 1, 1, *transformed.shape[1:])
    goal = transformed[1].view(1, 1, 1, *transformed.shape[1:])
    current = current.expand(1, args.samples, *current.shape[2:]).clone()
    goal = goal.expand(1, args.samples, *goal.shape[2:]).clone()
    generator = torch.Generator(device="cuda").manual_seed(args.seed)
    candidates = torch.randn(
        1,
        args.samples,
        args.horizon,
        action_dim,
        generator=generator,
        device=device,
    )
    info = {
        "pixels": current,
        "goal": goal,
        "action": torch.zeros(
            1, args.samples, 1, action_dim, device=device, dtype=torch.float32
        ),
    }
    with torch.inference_mode():
        native = model.get_cost(cloned(info), candidates.clone())
        b0_wrapper = SharedRolloutCostModel(model, arm="b0", horizon=args.horizon)
        wrapped = b0_wrapper.get_cost(cloned(info), candidates.clone())
    b0_max_abs = float((native - wrapped).abs().max().item())
    if b0_max_abs > 1.0e-6:
        raise RuntimeError(f"B0 wrapper differs from native cost: {b0_max_abs}")

    with torch.inference_mode():
        # Recover the latent dimension from the real rollout rather than a config guess.
        _, trajectory, _, _ = b0_wrapper._rollout_once(cloned(info), candidates.clone())
        latent_dim = int(trajectory.shape[-1])
        diffusion = (
            ConditionalDiffusionVerifier(latent_dim, action_dim, width=64)
            .to(device)
            .eval()
        )
        zero_wrapper = SharedRolloutCostModel(
            model,
            arm="diffusion",
            scorer=diffusion,
            latent_mean=torch.zeros(latent_dim),
            latent_std=torch.ones(latent_dim),
            lambda_weight=0.0,
            horizon=args.horizon,
            noise_seed=args.seed,
        ).to(device)
        zero_cost = zero_wrapper.get_cost(cloned(info), candidates.clone())
    zero_weight_max_abs = float((wrapped - zero_cost).abs().max().item())
    if zero_weight_max_abs != 0.0:
        raise RuntimeError(f"zero-weight verifier changed B0: {zero_weight_max_abs}")

    payload = {
        "status": "ok",
        "kind": "released_flat_world_model_wrapper_smoke",
        "policy": args.policy,
        "checkpoint_file": str(args.checkpoint_file),
        "checkpoint_sha256": sha256_file(args.checkpoint_file),
        "resolved_checkpoint_file": str(resolved_checkpoint),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "seed": args.seed,
        "samples": args.samples,
        "horizon": args.horizon,
        "primitive_action_dim": primitive_action_dim,
        "frameskip": args.frameskip,
        "action_dim": action_dim,
        "latent_dim": latent_dim,
        "trajectory_shape": list(trajectory.shape),
        "native_cost_shape": list(native.shape),
        "b0_native_max_abs": b0_max_abs,
        "zero_weight_max_abs": zero_weight_max_abs,
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
    }
    atomic_write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
