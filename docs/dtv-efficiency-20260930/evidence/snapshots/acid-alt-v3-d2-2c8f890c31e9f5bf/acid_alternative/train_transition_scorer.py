#!/usr/bin/env python3
"""Train native ACID, diffusion, or deterministic forward transition scorers."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import time
from pathlib import Path
from typing import Any, Literal

import h5py
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from acid_alternative.io_utils import atomic_write_json, sha256_file
from acid_alternative.models import (
    ConditionalDiffusionVerifier,
    DeterministicForwardVerifier,
    FlowInverseDynamics,
    count_parameters,
    select_capacity_matched_width,
)

ModelName = Literal["acid", "diffusion", "forward"]
ConditionName = Literal["true", "shuffled_action", "action_ablated"]
VALIDATION_PERMUTATION_SEED = 2026081306
TRAINING_PERMUTATION_SEED_OFFSET = 2026081307


def configure_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def atomic_save_npz(path: Path, **arrays: np.ndarray) -> None:
    """Durably write a compressed NumPy archive without exposing partial bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fixed_derangement_indices(length: int, *, seed: int) -> torch.Tensor:
    """Return a reproducible single-cycle permutation without fixed points."""

    if length < 2:
        raise ValueError("a derangement requires at least two examples")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    cycle = torch.randperm(length, generator=generator)
    mapping = torch.empty(length, dtype=torch.int64)
    mapping[cycle] = cycle.roll(shifts=-1)
    if torch.any(mapping == torch.arange(length)):
        raise RuntimeError("constructed validation permutation has a fixed point")
    return mapping


def validation_selection_action(
    condition: ConditionName,
    true_action: torch.Tensor,
    permuted_action: torch.Tensor,
) -> torch.Tensor:
    """Return the action matching a condition's held-out training objective."""

    if true_action.shape != permuted_action.shape:
        raise ValueError("true and permuted validation actions differ in shape")
    if condition == "true":
        return true_action
    if condition == "shuffled_action":
        return permuted_action
    if condition == "action_ablated":
        return torch.zeros_like(true_action)
    raise ValueError(condition)


def validation_diagnostic_actions(
    condition: ConditionName,
    true_action: torch.Tensor,
    permuted_action: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return deployed actions for the true/permuted validation diagnostic."""

    if true_action.shape != permuted_action.shape:
        raise ValueError("true and permuted validation actions differ in shape")
    if condition == "action_ablated":
        ablated = torch.zeros_like(true_action)
        return ablated, ablated
    if condition in ("true", "shuffled_action"):
        return true_action, permuted_action
    raise ValueError(condition)


def make_model(
    name: ModelName, latent_dim: int, action_dim: int
) -> tuple[nn.Module, dict[str, Any]]:
    if name == "acid":
        model = FlowInverseDynamics(
            latent_dim=latent_dim,
            action_dim=action_dim,
            width=192,
            depth=4,
            heads=3,
            mlp_ratio=4,
        )
        config = {
            "name": name,
            "latent_dim": latent_dim,
            "action_dim": action_dim,
            "width": 192,
            "depth": 4,
            "heads": 3,
            "mlp_ratio": 4,
            "reconstruction_choices": {
                "normalization": "pre_layer_norm",
                "activation": "GELU",
                "dropout": 0.0,
                "mlp_ratio": 4,
                "token_position": "learned_three_token_embedding",
                "latent_projection": "one_shared_biased_linear_for_both_prefix_tokens",
                "action_projection": "biased_linear",
                "velocity_head": "final_layer_norm_then_biased_linear",
                "time_embedding": "sinusoidal_tau_max_period_10000",
                "transformer_implementation": "torch.nn.TransformerEncoderLayer",
            },
        }
        return model, config
    diffusion_reference = ConditionalDiffusionVerifier(
        latent_dim=latent_dim,
        action_dim=action_dim,
        width=384,
        depth=3,
        noise_embedding_dim=64,
    )
    if name == "diffusion":
        return diffusion_reference, {
            "name": name,
            "latent_dim": latent_dim,
            "action_dim": action_dim,
            "width": 384,
            "depth": 3,
            "noise_embedding_dim": 64,
            "sigma_distribution": "log_uniform",
            "sigma_min": 0.01,
            "sigma_max": 1.0,
        }
    if name == "forward":
        width, candidate_count, relative_difference = select_capacity_matched_width(
            diffusion_reference,
            lambda candidate_width: DeterministicForwardVerifier(
                latent_dim=latent_dim,
                action_dim=action_dim,
                width=candidate_width,
                depth=3,
            ),
            minimum=128,
            maximum=640,
            step=8,
        )
        if relative_difference > 0.02:
            raise RuntimeError(
                "frozen width grid cannot match diffusion capacity within 2%: "
                f"relative_difference={relative_difference}"
            )
        model = DeterministicForwardVerifier(
            latent_dim=latent_dim,
            action_dim=action_dim,
            width=width,
            depth=3,
        )
        return model, {
            "name": name,
            "latent_dim": latent_dim,
            "action_dim": action_dim,
            "width": width,
            "depth": 3,
            "capacity_reference": {
                "model": "diffusion",
                "parameter_count": count_parameters(diffusion_reference),
                "matched_parameter_count": candidate_count,
                "relative_difference": relative_difference,
                "width_grid": {"minimum": 128, "maximum": 640, "step": 8},
            },
        }
    raise ValueError(name)


def learning_rate_at_step(
    step: int, *, maximum_steps: int, warmup_steps: int, peak: float
) -> float:
    if step <= warmup_steps:
        return peak * step / max(warmup_steps, 1)
    progress = (step - warmup_steps) / max(maximum_steps - warmup_steps, 1)
    return peak * 0.5 * (1.0 + math.cos(math.pi * min(max(progress, 0.0), 1.0)))


def gather_batch(
    selected_pairs: torch.Tensor,
    *,
    source_index: torch.Tensor,
    target_index: torch.Tensor,
    latents: torch.Tensor,
    actions: torch.Tensor,
    action_pair_override: torch.Tensor | None,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    acid_action_mean: torch.Tensor,
    acid_action_std: torch.Tensor,
    model_name: ModelName,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    source = source_index.index_select(0, selected_pairs)
    target = target_index.index_select(0, selected_pairs)
    action_pairs = (
        selected_pairs if action_pair_override is None else action_pair_override
    )
    batch_action = actions.index_select(0, action_pairs)
    current = latents.index_select(0, source)
    nxt = latents.index_select(0, target)
    if model_name == "acid":
        # Native frozen-encoder latents, as specified by ACID.  D1/F1 use the
        # explicitly predeclared standardized representation.
        current = current.to(device, non_blocking=True)
        nxt = nxt.to(device, non_blocking=True)
    else:
        current = ((current - latent_mean) / latent_std).to(device, non_blocking=True)
        nxt = ((nxt - latent_mean) / latent_std).to(device, non_blocking=True)
    batch_action = batch_action.to(device, non_blocking=True)
    if model_name == "acid":
        batch_action = (
            batch_action - acid_action_mean.to(device)
        ) / acid_action_std.to(device)
    return current, nxt, batch_action


def training_loss(
    model_name: ModelName,
    model: nn.Module,
    current: torch.Tensor,
    nxt: torch.Tensor,
    action: torch.Tensor,
    *,
    generator: torch.Generator,
) -> torch.Tensor:
    if model_name == "acid":
        assert isinstance(model, FlowInverseDynamics)
        noise = torch.randn(
            action.shape, generator=generator, device=action.device, dtype=action.dtype
        )
        # Beta(1.5, 1.0) has CDF tau**1.5, so inverse-CDF sampling is exact.
        tau = torch.rand(
            action.shape[:-1], generator=generator, device=action.device
        ).pow(2.0 / 3.0)
        return model.flow_loss(current, nxt, action, tau=tau, noise=noise)
    if model_name == "diffusion":
        assert isinstance(model, ConditionalDiffusionVerifier)
        uniform = torch.rand(nxt.shape[:-1], generator=generator, device=nxt.device)
        sigma = torch.exp(math.log(0.01) + uniform * (math.log(1.0) - math.log(0.01)))
        noise = torch.randn(
            nxt.shape, generator=generator, device=nxt.device, dtype=nxt.dtype
        )
        return model.denoising_loss(current, action, nxt, sigma=sigma, noise=noise)
    if model_name == "forward":
        assert isinstance(model, DeterministicForwardVerifier)
        return F.mse_loss(model(current, action), nxt)
    raise ValueError(model_name)


@torch.inference_mode()
def validate(
    model_name: ModelName,
    model: nn.Module,
    validation_pairs: torch.Tensor,
    *,
    source_index: torch.Tensor,
    target_index: torch.Tensor,
    latents: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    acid_action_mean: torch.Tensor,
    acid_action_std: torch.Tensor,
    device: torch.device,
    batch_size: int,
    seed: int,
    condition: ConditionName = "true",
    collect_examples: bool = False,
    permutation_seed: int = VALIDATION_PERMUTATION_SEED,
) -> dict[str, Any]:
    model.eval()
    generator = torch.Generator(device=device.type).manual_seed(seed)
    total_loss = 0.0
    total_examples = 0
    correct_better = 0
    correct_cost_sum = 0.0
    mismatch_cost_sum = 0.0
    correct_dimension_sum: torch.Tensor | None = None
    mismatch_dimension_sum: torch.Tensor | None = None
    correct_example_costs: list[torch.Tensor] = []
    mismatch_example_costs: list[torch.Tensor] = []
    permutation = fixed_derangement_indices(
        len(validation_pairs), seed=permutation_seed
    )
    permuted_pairs = validation_pairs.index_select(0, permutation)
    for start in range(0, len(validation_pairs), batch_size):
        selected = validation_pairs[start : start + batch_size]
        permuted = permuted_pairs[start : start + batch_size]
        current, nxt, action = gather_batch(
            selected,
            source_index=source_index,
            target_index=target_index,
            latents=latents,
            actions=actions,
            action_pair_override=None,
            latent_mean=latent_mean,
            latent_std=latent_std,
            acid_action_mean=acid_action_mean,
            acid_action_std=acid_action_std,
            model_name=model_name,
            device=device,
        )
        _, _, mismatch_action = gather_batch(
            selected,
            source_index=source_index,
            target_index=target_index,
            latents=latents,
            actions=actions,
            action_pair_override=permuted,
            latent_mean=latent_mean,
            latent_std=latent_std,
            acid_action_mean=acid_action_mean,
            acid_action_std=acid_action_std,
            model_name=model_name,
            device=device,
        )
        selection_action = validation_selection_action(
            condition, action, mismatch_action
        )
        diagnostic_action, diagnostic_mismatch_action = validation_diagnostic_actions(
            condition, action, mismatch_action
        )
        count = len(selected)
        if model_name == "acid":
            assert isinstance(model, FlowInverseDynamics)
            noise = torch.randn(
                selection_action.shape, generator=generator, device=device
            )
            tau = torch.rand(
                selection_action.shape[:-1], generator=generator, device=device
            ).pow(2.0 / 3.0)
            tau_action = tau.unsqueeze(-1)
            noisy_action = tau_action * noise + (1.0 - tau_action) * selection_action
            target_velocity = noise - selection_action
            prediction = model(current, nxt, noisy_action, tau)
            loss = (prediction - target_velocity).square().mean(dim=-1)
            inference_noise = torch.randn(
                action.shape, generator=generator, device=device
            )
            inferred_standardized = model.one_step_action(current, nxt, inference_noise)
            action_std = acid_action_std.to(device)
            action_mean = acid_action_mean.to(device)
            inferred = inferred_standardized * action_std + action_mean
            action_planner = diagnostic_action * action_std + action_mean
            mismatch_planner = diagnostic_mismatch_action * action_std + action_mean
            correct_dimension_cost = (inferred - action_planner).square()
            mismatch_dimension_cost = (inferred - mismatch_planner).square()
            correct_cost = correct_dimension_cost.sum(dim=-1)
            mismatch_cost = mismatch_dimension_cost.sum(dim=-1)
        elif model_name == "diffusion":
            assert isinstance(model, ConditionalDiffusionVerifier)
            losses: list[torch.Tensor] = []
            mismatch_losses: list[torch.Tensor] = []
            selection_losses: list[torch.Tensor] = []
            dimension_losses: list[torch.Tensor] = []
            mismatch_dimension_losses: list[torch.Tensor] = []
            for sigma_value in (0.10, 0.25, 0.50):
                noise = torch.randn(nxt.shape, generator=generator, device=device)
                sigma = torch.full(nxt.shape[:-1], sigma_value, device=device)
                noisy = nxt + sigma.unsqueeze(-1) * noise
                dimension_loss = (
                    model(current, diagnostic_action, noisy, sigma) - noise
                ).square()
                mismatch_dimension_loss = (
                    model(current, diagnostic_mismatch_action, noisy, sigma) - noise
                ).square()
                dimension_losses.append(dimension_loss)
                mismatch_dimension_losses.append(mismatch_dimension_loss)
                losses.append(dimension_loss.mean(dim=-1))
                mismatch_losses.append(mismatch_dimension_loss.mean(dim=-1))
                selection_losses.append(
                    (model(current, selection_action, noisy, sigma) - noise)
                    .square()
                    .mean(dim=-1)
                )
            correct_dimension_cost = torch.stack(dimension_losses).mean(dim=0)
            mismatch_dimension_cost = torch.stack(mismatch_dimension_losses).mean(dim=0)
            correct_cost = torch.stack(losses).mean(dim=0)
            mismatch_cost = torch.stack(mismatch_losses).mean(dim=0)
            loss = torch.stack(selection_losses).mean(dim=0)
        elif model_name == "forward":
            assert isinstance(model, DeterministicForwardVerifier)
            correct_dimension_cost = (model(current, diagnostic_action) - nxt).square()
            mismatch_dimension_cost = (
                model(current, diagnostic_mismatch_action) - nxt
            ).square()
            correct_cost = correct_dimension_cost.mean(dim=-1)
            mismatch_cost = mismatch_dimension_cost.mean(dim=-1)
            loss = (model(current, selection_action) - nxt).square().mean(dim=-1)
        else:
            raise ValueError(model_name)
        batch_correct_dimension_sum = correct_dimension_cost.sum(dim=0).double().cpu()
        batch_mismatch_dimension_sum = mismatch_dimension_cost.sum(dim=0).double().cpu()
        if correct_dimension_sum is None:
            correct_dimension_sum = torch.zeros_like(batch_correct_dimension_sum)
            mismatch_dimension_sum = torch.zeros_like(batch_mismatch_dimension_sum)
        correct_dimension_sum += batch_correct_dimension_sum
        assert mismatch_dimension_sum is not None
        mismatch_dimension_sum += batch_mismatch_dimension_sum
        if collect_examples:
            correct_example_costs.append(correct_cost.detach().float().cpu())
            mismatch_example_costs.append(mismatch_cost.detach().float().cpu())
        total_loss += float(loss.sum().item())
        correct_cost_sum += float(correct_cost.sum().item())
        mismatch_cost_sum += float(mismatch_cost.sum().item())
        correct_better += int((correct_cost < mismatch_cost).sum().item())
        total_examples += count
    if correct_dimension_sum is None or mismatch_dimension_sum is None:
        raise RuntimeError("validation contains no examples")
    result: dict[str, Any] = {
        "loss": total_loss / total_examples,
        "correct_action_cost": correct_cost_sum / total_examples,
        "permuted_action_cost": mismatch_cost_sum / total_examples,
        "correct_action_pairwise_accuracy": correct_better / total_examples,
        "correct_cost_per_dimension": (correct_dimension_sum / total_examples).tolist(),
        "permuted_cost_per_dimension": (
            mismatch_dimension_sum / total_examples
        ).tolist(),
        "examples": float(total_examples),
    }
    if collect_examples:
        result["_correct_cost_by_example"] = torch.cat(correct_example_costs).tolist()
        result["_permuted_cost_by_example"] = torch.cat(mismatch_example_costs).tolist()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", choices=("acid", "diffusion", "forward"), required=True
    )
    parser.add_argument(
        "--condition",
        choices=("true", "shuffled_action", "action_ablated"),
        default="true",
    )
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--latent-manifest", type=Path, required=True)
    parser.add_argument("--transition-h5", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--maximum-steps", type=int, default=200_000)
    parser.add_argument("--warmup-steps", type=int, default=1_000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--validation-batch-size", type=int, default=4096)
    parser.add_argument("--validation-interval", type=int, default=5_000)
    parser.add_argument("--validation-limit", type=int, default=100_000)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--gradient-clip", type=float, default=1.0)
    args = parser.parse_args()

    for path in (
        args.latent_h5,
        args.latent_manifest,
        args.transition_h5,
        args.transition_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.source_manifest is not None and not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if (
        min(
            args.maximum_steps,
            args.batch_size,
            args.validation_batch_size,
            args.validation_interval,
            args.validation_limit,
            args.learning_rate,
            args.gradient_clip,
        )
        <= 0
    ):
        raise ValueError("training arguments must be positive")
    if args.warmup_steps < 0 or args.warmup_steps > args.maximum_steps:
        raise ValueError("warmup must lie within the training schedule")
    if args.condition == "action_ablated" and args.model != "diffusion":
        raise ValueError(
            "the frozen action-ablated control is defined only for diffusion"
        )
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")

    latent_manifest = json.loads(args.latent_manifest.read_text(encoding="utf-8"))
    transition_manifest = json.loads(
        args.transition_manifest.read_text(encoding="utf-8")
    )
    if sha256_file(args.latent_h5) != latent_manifest.get("output_h5_sha256"):
        raise RuntimeError("latent cache hash mismatch")
    if sha256_file(args.transition_h5) != transition_manifest.get("output_h5_sha256"):
        raise RuntimeError("transition cache hash mismatch")
    if transition_manifest.get("latent_h5_sha256") != latent_manifest.get(
        "output_h5_sha256"
    ):
        raise RuntimeError("transition cache was built from another latent cache")

    configure_seed(args.seed)
    device = torch.device(args.device)
    with h5py.File(args.latent_h5, "r") as handle:
        latents = torch.from_numpy(np.asarray(handle["latent"][:], dtype=np.float32))
    with h5py.File(args.transition_h5, "r") as handle:
        source_index = torch.from_numpy(
            np.asarray(handle["source_index"][:], dtype=np.int64)
        )
        target_index = torch.from_numpy(
            np.asarray(handle["target_index"][:], dtype=np.int64)
        )
        actions = torch.from_numpy(np.asarray(handle["action"][:], dtype=np.float32))
        role = torch.from_numpy(np.asarray(handle["role"][:], dtype=np.uint8))
        pair_episode = torch.from_numpy(
            np.asarray(handle["episode_idx"][:], dtype=np.int64)
        )
        pair_step = torch.from_numpy(np.asarray(handle["step_idx"][:], dtype=np.int64))
        latent_mean = torch.from_numpy(
            np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        )
        latent_std = torch.from_numpy(
            np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        )
        acid_action_mean = torch.from_numpy(
            np.asarray(handle["stats/acid_action_mean"][:], dtype=np.float32)
        )
        acid_action_std = torch.from_numpy(
            np.asarray(handle["stats/acid_action_std"][:], dtype=np.float32)
        )
        planner_primitive_action_mean = torch.from_numpy(
            np.asarray(
                handle["stats/planner_primitive_action_mean"][:], dtype=np.float64
            )
        )
        planner_primitive_action_std = torch.from_numpy(
            np.asarray(
                handle["stats/planner_primitive_action_std"][:], dtype=np.float64
            )
        )
    train_pairs = torch.nonzero(role == 0, as_tuple=False).flatten()
    validation_pairs = torch.nonzero(role == 1, as_tuple=False).flatten()
    if len(train_pairs) == 0 or len(validation_pairs) == 0:
        raise RuntimeError("empty train or validation role")
    validation_pairs = validation_pairs[
        : min(args.validation_limit, len(validation_pairs))
    ]

    shuffled_lookup: torch.Tensor | None = None
    sampling_generator = torch.Generator(device="cpu").manual_seed(args.seed + 101)
    if args.condition == "shuffled_action":
        shuffled_mapping = fixed_derangement_indices(
            len(train_pairs), seed=TRAINING_PERMUTATION_SEED_OFFSET + args.seed
        )
        shuffled_lookup = train_pairs.index_select(0, shuffled_mapping)
    model, model_config = make_model(
        args.model, latent_dim=latents.shape[1], action_dim=actions.shape[1]
    )
    model = model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        betas=(0.9, 0.999),
        weight_decay=args.weight_decay,
    )
    train_generator = torch.Generator(device=device.type).manual_seed(args.seed + 202)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "best.pt"
    log_path = args.output_dir / "training.jsonl"
    started = time.time()
    best_loss = float("inf")
    best_step = -1
    last_validation: dict[str, Any] | None = None

    for step in range(1, args.maximum_steps + 1):
        model.train()
        local_positions = torch.randint(
            len(train_pairs),
            (args.batch_size,),
            generator=sampling_generator,
        )
        selected = train_pairs.index_select(0, local_positions)
        action_override = (
            None
            if shuffled_lookup is None
            else shuffled_lookup.index_select(0, local_positions)
        )
        current, nxt, action = gather_batch(
            selected,
            source_index=source_index,
            target_index=target_index,
            latents=latents,
            actions=actions,
            action_pair_override=action_override,
            latent_mean=latent_mean,
            latent_std=latent_std,
            acid_action_mean=acid_action_mean,
            acid_action_std=acid_action_std,
            model_name=args.model,
            device=device,
        )
        if args.condition == "action_ablated":
            action = torch.zeros_like(action)
        learning_rate = learning_rate_at_step(
            step,
            maximum_steps=args.maximum_steps,
            warmup_steps=args.warmup_steps,
            peak=args.learning_rate,
        )
        for group in optimizer.param_groups:
            group["lr"] = learning_rate
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(
            device_type=device.type,
            dtype=torch.bfloat16,
            enabled=device.type == "cuda",
        ):
            loss = training_loss(
                args.model,
                model,
                current,
                nxt,
                action,
                generator=train_generator,
            )
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite training loss at step {step}")
        loss.backward()
        gradient_norm = torch.nn.utils.clip_grad_norm_(
            model.parameters(), args.gradient_clip
        )
        if not torch.isfinite(torch.as_tensor(gradient_norm)):
            raise RuntimeError(f"non-finite gradient norm at step {step}")
        optimizer.step()

        should_validate = (
            step == args.maximum_steps or step % args.validation_interval == 0
        )
        if should_validate:
            last_validation = validate(
                args.model,
                model,
                validation_pairs,
                source_index=source_index,
                target_index=target_index,
                latents=latents,
                actions=actions,
                latent_mean=latent_mean,
                latent_std=latent_std,
                acid_action_mean=acid_action_mean,
                acid_action_std=acid_action_std,
                device=device,
                batch_size=args.validation_batch_size,
                seed=args.seed + 303,
                condition=args.condition,
            )
            record = {
                "step": step,
                "training_loss": float(loss.detach().cpu()),
                "validation": last_validation,
                "learning_rate": learning_rate,
                "gradient_norm": float(torch.as_tensor(gradient_norm).detach().cpu()),
                "elapsed_seconds": time.time() - started,
            }
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps(record, sort_keys=True), flush=True)
            if last_validation["loss"] < best_loss:
                best_loss = last_validation["loss"]
                best_step = step
                payload = {
                    "format_version": 1,
                    "model_name": args.model,
                    "condition": args.condition,
                    "model_config": model_config,
                    "state_dict": {
                        key: value.detach().cpu()
                        for key, value in model.state_dict().items()
                    },
                    "latent_mean": latent_mean,
                    "latent_std": latent_std,
                    "acid_action_mean": acid_action_mean,
                    "acid_action_std": acid_action_std,
                    "planner_primitive_action_mean": planner_primitive_action_mean,
                    "planner_primitive_action_std": planner_primitive_action_std,
                    "step": step,
                    "validation": last_validation,
                    "seed": args.seed,
                    "control_design": {
                        "validation_permutation_kind": (
                            "single_cycle_random_derangement"
                        ),
                        "validation_permutation_seed": VALIDATION_PERMUTATION_SEED,
                        "training_permutation_seed": (
                            TRAINING_PERMUTATION_SEED_OFFSET + args.seed
                            if args.condition == "shuffled_action"
                            else None
                        ),
                        "minibatch_rng_stream_changed_by_control": False,
                    },
                    "transition_h5_sha256": transition_manifest["output_h5_sha256"],
                    "latent_h5_sha256": latent_manifest["output_h5_sha256"],
                    "source_manifest_sha256": (
                        sha256_file(args.source_manifest)
                        if args.source_manifest
                        else None
                    ),
                }
                temporary = checkpoint_path.with_name(
                    f".{checkpoint_path.name}.partial-{os.getpid()}"
                )
                torch.save(payload, temporary)
                os.replace(temporary, checkpoint_path)

    if not checkpoint_path.is_file() or last_validation is None:
        raise RuntimeError("training completed without a checkpoint")
    best_payload = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(best_payload["state_dict"], strict=True)
    final_validation = validate(
        args.model,
        model,
        validation_pairs,
        source_index=source_index,
        target_index=target_index,
        latents=latents,
        actions=actions,
        latent_mean=latent_mean,
        latent_std=latent_std,
        acid_action_mean=acid_action_mean,
        acid_action_std=acid_action_std,
        device=device,
        batch_size=args.validation_batch_size,
        seed=args.seed + 303,
        condition=args.condition,
        collect_examples=True,
    )
    correct_cost_by_example = np.asarray(
        final_validation.pop("_correct_cost_by_example"), dtype=np.float32
    )
    permuted_cost_by_example = np.asarray(
        final_validation.pop("_permuted_cost_by_example"), dtype=np.float32
    )
    validation_pair_numpy = validation_pairs.numpy().astype(np.int64, copy=False)
    validation_permutation = fixed_derangement_indices(
        len(validation_pairs), seed=VALIDATION_PERMUTATION_SEED
    )
    permuted_validation_pairs = validation_pairs.index_select(0, validation_permutation)
    if correct_cost_by_example.shape != validation_pair_numpy.shape or (
        permuted_cost_by_example.shape != validation_pair_numpy.shape
    ):
        raise RuntimeError("validation example diagnostic has the wrong shape")
    validation_examples_path = args.output_dir / "validation-examples.npz"
    atomic_save_npz(
        validation_examples_path,
        pair_index=validation_pair_numpy,
        episode_idx=pair_episode.index_select(0, validation_pairs).numpy(),
        step_idx=pair_step.index_select(0, validation_pairs).numpy(),
        permuted_pair_index=permuted_validation_pairs.numpy(),
        permuted_episode_idx=pair_episode.index_select(
            0, permuted_validation_pairs
        ).numpy(),
        permuted_step_idx=pair_step.index_select(0, permuted_validation_pairs).numpy(),
        correct_cost=correct_cost_by_example,
        permuted_cost=permuted_cost_by_example,
        correct_minus_permuted_margin=(
            permuted_cost_by_example - correct_cost_by_example
        ),
    )
    if (
        abs(final_validation["loss"] - float(best_payload["validation"]["loss"]))
        > 1.0e-9
    ):
        raise RuntimeError(
            "reloaded best checkpoint does not reproduce validation loss"
        )
    summary = {
        "status": "ok",
        "kind": "flat_transition_scorer_training",
        "model": args.model,
        "condition": args.condition,
        "model_config": model_config,
        "parameter_count": count_parameters(model),
        "seed": args.seed,
        "optimization": {
            "maximum_steps": args.maximum_steps,
            "warmup_steps": args.warmup_steps,
            "batch_size": args.batch_size,
            "peak_learning_rate": args.learning_rate,
            "betas": [0.9, 0.999],
            "weight_decay": args.weight_decay,
            "gradient_clip": args.gradient_clip,
            "mixed_precision": "bf16" if device.type == "cuda" else "disabled",
        },
        "train_pairs": len(train_pairs),
        "validation_pairs_total": int((role == 1).sum()),
        "validation_pairs_evaluated": len(validation_pairs),
        "confirmation_identification_data": "external I1 episodes are absent from this training cache",
        "confirmation_test_outcomes_computed": False,
        "best_step": best_step,
        "best_validation_loss": best_loss,
        "final_validation": final_validation,
        "validation_examples": str(validation_examples_path),
        "validation_examples_sha256": sha256_file(validation_examples_path),
        "validation_example_definition": (
            "development-only P1_val diagnostic: positive "
            "correct_minus_permuted_margin means the frozen scorer "
            "assigned lower cost to the true action than to the fixed "
            "permutation"
        ),
        "validation_action_permutation": {
            "kind": "single_cycle_random_derangement",
            "seed": VALIDATION_PERMUTATION_SEED,
            "fixed_points": 0,
        },
        "training_action_permutation": (
            {
                "kind": "single_cycle_random_derangement",
                "seed": TRAINING_PERMUTATION_SEED_OFFSET + args.seed,
                "fixed_points": 0,
                "minibatch_rng_stream_changed": False,
            }
            if args.condition == "shuffled_action"
            else None
        ),
        "latent_h5": str(args.latent_h5),
        "latent_h5_sha256": latent_manifest["output_h5_sha256"],
        "transition_h5": str(args.transition_h5),
        "transition_h5_sha256": transition_manifest["output_h5_sha256"],
        "source_manifest": str(args.source_manifest) if args.source_manifest else None,
        "source_manifest_sha256": (
            sha256_file(args.source_manifest) if args.source_manifest else None
        ),
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "training_log": str(log_path),
        "training_log_sha256": sha256_file(log_path),
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": str(device),
            "gpu": torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else None,
        },
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
