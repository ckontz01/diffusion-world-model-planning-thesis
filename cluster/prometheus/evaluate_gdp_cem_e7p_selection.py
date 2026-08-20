#!/usr/bin/env python3
"""Evaluate GDP-CEM proposal banks on frozen P1-validation latent rollouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

from acid_alternative.extract_flat_latents import encode, preprocess_pixels
from acid_alternative.io_utils import atomic_write_json, resolve_policy_checkpoint
from gdp_cem_latent_rollout import (
    rollout_from_single_latent,
    selected_candidate_metrics,
    terminal_goal_cost,
)
from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    CosineDiffusionSchedule,
    JointActionDiffusion,
    ddim_sample,
    gaussian_sample,
    load_proposal_model,
)


PROTOCOL_SHA256 = "3c7ff146a43bb5d87e99d92dff0f9731f7ea4b186aedaec168db284ad744dbbc"
TRAINING_PROTOCOL_SHA256 = "b49e29adde3f1b0ce79c3a602f5a1af6a4159899a7941fb0f6cc30971bdb017b"
TRAINING_SOURCE_SHA256 = "e9ceb0caee33cb1b1e042373c84f7f58205b26d026979c85b5bf287fd85edba2"
CACHE_PROTOCOL_SHA256 = "50690a07e2a2a949b0d0a9c5e43a8c4eb53b483780021ea20142031264de3299"
CACHE_SOURCE_SHA256 = "4a8350d8914aeaf40925f4df6e0aaaaa892a2bc95d8ee7c11fc56ad7ec33f18a"
CONDITIONS = ("diffusion_true", "diffusion_shuffled_goal", "gaussian_true")
DDIM_STEPS = (5, 10, 20)
FRACTIONS = (0.25, 0.50, 0.75, 1.00)
CONTEXT_COUNT = 256
CANDIDATE_COUNT = 300
ENCODER_EQUIVALENCE_ATOL = 5.0e-6
ROLLOUT_EQUIVALENCE_ATOL = 1.0e-5
TASK_SPEC = {
    "pusht": {
        "primitive_action_dim": 2,
        "macro_action_dim": 10,
        "sequences": 1_313_002,
        "train_sequences": 1_183_514,
        "validation_sequences": 129_488,
        "sequence_manifest_sha256": "b98c17f107cbfd5daca8d387d83e034460ff8f2535113a3c05467f68442ef9cb",
        "sequence_h5_sha256": "711420559aa62a3f3c2d818cf3382966b8f4abab057fe6a4a64b3c86adf4f875",
        "latent_h5_sha256": "5c8ad694712c202ce6114f68d8155a41e2cf88c1c86d1dd442f70e29dc90e7e8",
    },
    "reacher": {
        "primitive_action_dim": 2,
        "macro_action_dim": 10,
        "sequences": 1_226_896,
        "train_sequences": 1_107_568,
        "validation_sequences": 119_328,
        "sequence_manifest_sha256": "e0e202cd5da1d057b0cb6ba423eae1971f15dd38a871ad581c4f683c8eec9479",
        "sequence_h5_sha256": "58f355ad1d2417a9aed879bb5b580e21b7cea7868129b390da2e76f6bf4c3ae3",
        "latent_h5_sha256": "96bbf0a02e7368aa9636edda74edc641d95810b109605714c920522608b5f76e",
    },
    "cube": {
        "primitive_action_dim": 5,
        "macro_action_dim": 25,
        "sequences": 1_241_328,
        "train_sequences": 1_123_760,
        "validation_sequences": 117_568,
        "sequence_manifest_sha256": "dede8e8d6941008fbb7c910fa2f07666e8e77c93924c007e244f1a890790a80b",
        "sequence_h5_sha256": "3075885e9aeffa74d22492bc4d25e7f548e37774faecf6ff60699ef1d7f4ee9c",
        "latent_h5_sha256": "81eb8b967168c5f30b25a99f1f766579f40adcdd71a77861f84ffaf20f3ac69d",
    },
}


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


def numpy_seed_from_sha256(label: str) -> int:
    """Interpret the first 64 SHA-256 bits exactly as the frozen NumPy seed."""

    return int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "big")


def load_checkpoint(
    summary_path: Path,
    *,
    task: str,
    condition: str,
    device: torch.device,
) -> tuple[torch.nn.Module, dict[str, Any], dict[str, Any]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_p1_proposal_training"
        or summary.get("analysis_role") != "P1_only_method_development"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or summary.get("seed") != 6101
        or summary.get("protocol_sha256") != TRAINING_PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != TRAINING_SOURCE_SHA256
        or summary.get("d2_read") is not False
        or summary.get("d3_read") is not False
        or summary.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError(f"GDP-CEM training summary differs: {summary_path}")
    checkpoint = Path(summary["checkpoint"])
    if not checkpoint.is_file() or sha256_file(checkpoint) != summary.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError(f"GDP-CEM checkpoint hash differs: {checkpoint}")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    expected_kind = "gaussian" if condition == "gaussian_true" else "diffusion"
    expected_config = {
        "latent_dim": 192,
        "primitive_action_dim": int(TASK_SPEC[task]["primitive_action_dim"]),
        "action_horizon": 25,
        "width": 512,
        "depth": 4,
        "time_embedding_dim": 128,
    }
    if (
        payload.get("kind") != "gdp_cem_p1_proposal_checkpoint"
        or payload.get("task") != task
        or payload.get("condition") != condition
        or payload.get("proposal_kind") != expected_kind
        or payload.get("seed") != 6101
        or payload.get("protocol_sha256") != TRAINING_PROTOCOL_SHA256
        or payload.get("source_manifest_sha256") != TRAINING_SOURCE_SHA256
        or payload.get("model_config") != expected_config
        or summary.get("model_config") != expected_config
        or (expected_kind == "diffusion" and payload.get("diffusion_steps") != 100)
    ):
        raise RuntimeError(f"GDP-CEM checkpoint identity differs: {checkpoint}")
    statistic_shapes = {
        "latent_mean": (192,),
        "latent_std": (192,),
        "action_mean": (expected_config["primitive_action_dim"],),
        "action_std": (expected_config["primitive_action_dim"],),
        "robust_low": (expected_config["primitive_action_dim"],),
        "robust_high": (expected_config["primitive_action_dim"],),
    }
    statistics = {
        key: torch.as_tensor(payload[key]).float() for key in statistic_shapes
    }
    if any(statistics[key].shape != shape for key, shape in statistic_shapes.items()):
        raise RuntimeError(f"GDP-CEM checkpoint statistic shape differs: {checkpoint}")
    if (
        not all(torch.isfinite(value).all() for value in statistics.values())
        or torch.any(statistics["latent_std"] <= 1.0e-6)
        or torch.any(statistics["action_std"] <= 1.0e-6)
        or torch.any(statistics["robust_high"] <= statistics["robust_low"])
    ):
        raise RuntimeError(f"GDP-CEM checkpoint statistics are invalid: {checkpoint}")
    model = load_proposal_model(payload, device=device)
    if sum(parameter.numel() for parameter in model.parameters()) != int(
        summary["parameter_count"]
    ):
        raise RuntimeError("GDP-CEM proposal parameter count differs")
    return model, payload, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "best_step": summary["best_step"],
        "best_validation": summary["best_validation"],
        "parameter_count": summary["parameter_count"],
    }


def planner_samples(
    model: JointActionDiffusion | ConditionalDiagonalGaussian,
    payload: dict[str, Any],
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    count: int,
    generator: torch.Generator,
    ddim_steps: int | None,
) -> torch.Tensor:
    if isinstance(model, JointActionDiffusion):
        if ddim_steps is None:
            raise ValueError("diffusion proposal requires DDIM steps")
        normalized = ddim_sample(
            model,
            current=current,
            goal=goal,
            count=count,
            inference_steps=ddim_steps,
            schedule=CosineDiffusionSchedule.build(int(payload["diffusion_steps"])),
            generator=generator,
        )
    else:
        if ddim_steps is not None:
            raise ValueError("Gaussian proposal must not receive DDIM steps")
        normalized = gaussian_sample(
            model,
            current=current,
            goal=goal,
            count=count,
            generator=generator,
        )
    action_mean = torch.as_tensor(
        payload["action_mean"], device=current.device, dtype=current.dtype
    )
    action_std = torch.as_tensor(
        payload["action_std"], device=current.device, dtype=current.dtype
    )
    robust_low = torch.as_tensor(
        payload["robust_low"], device=current.device, dtype=current.dtype
    )
    robust_high = torch.as_tensor(
        payload["robust_high"], device=current.device, dtype=current.dtype
    )
    planner = normalized * action_std + action_mean
    planner = torch.maximum(torch.minimum(planner, robust_high), robust_low)
    return planner


def metric_record(
    world_model: torch.nn.Module,
    *,
    current_raw: torch.Tensor,
    goal_raw: torch.Tensor,
    candidates_primitive: torch.Tensor,
    reference_primitive: torch.Tensor,
) -> dict[str, float]:
    primitive_dim = candidates_primitive.shape[-1]
    macro = candidates_primitive.reshape(
        1, CANDIDATE_COUNT, 5, 5 * primitive_dim
    )
    trajectory = rollout_from_single_latent(
        world_model, current=current_raw, macro_actions=macro
    )
    goal_cost = terminal_goal_cost(trajectory, goal_raw)
    reference_macro = reference_primitive.reshape(1, 5, 5 * primitive_dim)
    metrics = selected_candidate_metrics(
        goal_cost=goal_cost, candidates=macro, reference=reference_macro
    )
    return {key: float(value[0].detach().cpu()) for key, value in metrics.items()}


@torch.inference_mode()
def determinism_preflight(
    world_model: torch.nn.Module,
    *,
    task: str,
    models: dict[str, torch.nn.Module],
    payloads: dict[str, dict[str, Any]],
    current: torch.Tensor,
    goal: torch.Tensor,
    current_raw: torch.Tensor,
) -> dict[str, Any]:
    expected_shape = (
        1,
        8,
        25,
        int(TASK_SPEC[task]["primitive_action_dim"]),
    )
    records: dict[str, Any] = {}
    true_bank: torch.Tensor | None = None
    for condition in CONDITIONS:
        steps = None if condition == "gaussian_true" else 5
        seed = derived_seed(f"gdp-e7p-determinism|task={task}|condition={condition}")
        first = planner_samples(
            models[condition],
            payloads[condition],
            current=current,
            goal=goal,
            count=8,
            generator=torch.Generator(device=current.device).manual_seed(seed),
            ddim_steps=steps,
        )
        second = planner_samples(
            models[condition],
            payloads[condition],
            current=current,
            goal=goal,
            count=8,
            generator=torch.Generator(device=current.device).manual_seed(seed),
            ddim_steps=steps,
        )
        if (
            first.shape != expected_shape
            or not torch.isfinite(first).all()
            or not torch.equal(first, second)
        ):
            raise RuntimeError(f"GDP-CEM deterministic proposal preflight failed: {condition}")
        records[condition] = {
            "shape": list(first.shape),
            "repeat_max_abs": float((first - second).abs().max().cpu()),
        }
        if condition == "diffusion_true":
            true_bank = first
    assert true_bank is not None
    macro = true_bank.reshape(1, 8, 5, int(TASK_SPEC[task]["macro_action_dim"]))
    first_rollout = rollout_from_single_latent(
        world_model, current=current_raw, macro_actions=macro
    )
    second_rollout = rollout_from_single_latent(
        world_model, current=current_raw, macro_actions=macro
    )
    rollout_error = float((first_rollout - second_rollout).abs().max().cpu())
    if not torch.equal(first_rollout, second_rollout) or not torch.isfinite(
        first_rollout
    ).all():
        raise RuntimeError("GDP-CEM deterministic latent-rollout preflight failed")
    return {
        "status": "ok",
        "proposal_checks": records,
        "latent_rollout_repeat_max_abs": rollout_error,
    }


@torch.inference_mode()
def real_stack_equivalence(
    world_model: torch.nn.Module,
    *,
    dataset: Path,
    global_row: int,
    cached_current: torch.Tensor,
    action_dim: int,
    device: torch.device,
    seed: int,
) -> dict[str, float | str]:
    with h5py.File(dataset, "r") as handle:
        pixels_np = np.asarray(handle["pixels"][global_row : global_row + 1])
    pixels = preprocess_pixels(pixels_np, device)
    encoded = encode(world_model, pixels)
    cached_error = float((encoded - cached_current).abs().max().cpu())
    generator = torch.Generator(device=device).manual_seed(seed)
    actions = torch.randn(1, 4, 5, action_dim, generator=generator, device=device)
    expanded_pixels = pixels[:, None, None].expand(1, 4, 1, *pixels.shape[1:])
    normal = world_model.rollout({"pixels": expanded_pixels.clone()}, actions)[
        "predicted_emb"
    ]
    direct = rollout_from_single_latent(
        world_model, current=encoded, macro_actions=actions
    )
    rollout_error = float((normal - direct).abs().max().cpu())
    if (
        cached_error > ENCODER_EQUIVALENCE_ATOL
        or rollout_error > ROLLOUT_EQUIVALENCE_ATOL
    ):
        raise RuntimeError(
            f"GDP-CEM real-stack equivalence failed: cache={cached_error}, rollout={rollout_error}"
        )
    return {
        "status": "ok",
        "cached_encoder_max_abs": cached_error,
        "rollout_max_abs": rollout_error,
        "cached_encoder_atol": ENCODER_EQUIVALENCE_ATOL,
        "rollout_atol": ROLLOUT_EQUIVALENCE_ATOL,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "reacher", "cube"), required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--sequence-h5", type=Path, required=True)
    parser.add_argument("--sequence-manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--proposal-summary", nargs=2, action="append", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    required = (
        args.latent_h5,
        args.sequence_h5,
        args.sequence_manifest,
        args.dataset,
        args.world_model_checkpoint,
        args.protocol,
        args.source_manifest,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("GDP-CEM P1 selection protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty GDP-CEM P1 selection output")
    summary_paths = {condition: Path(path) for condition, path in args.proposal_summary}
    if set(summary_paths) != set(CONDITIONS):
        raise RuntimeError("GDP-CEM P1 selection requires exactly three conditions")

    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("GDP-CEM P1 selection requires CUDA")
    torch.manual_seed(2026081702)
    torch.cuda.manual_seed_all(2026081702)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    models = {}
    payloads = {}
    model_records = {}
    for condition in CONDITIONS:
        models[condition], payloads[condition], model_records[condition] = load_checkpoint(
            summary_paths[condition], task=args.task, condition=condition, device=device
        )
    for key in ("latent_mean", "latent_std", "action_mean", "action_std", "robust_low", "robust_high"):
        reference = torch.as_tensor(payloads["diffusion_true"][key]).float()
        if any(
            not torch.equal(reference, torch.as_tensor(payloads[condition][key]).float())
            for condition in CONDITIONS[1:]
        ):
            raise RuntimeError(f"GDP-CEM proposal statistics differ: {key}")

    resolved = resolve_policy_checkpoint(
        args.world_model_policy, args.stablewm_home
    )
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("GDP-CEM world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    sequence_manifest = json.loads(
        args.sequence_manifest.read_text(encoding="utf-8")
    )
    task_spec = TASK_SPEC[args.task]
    if (
        sequence_manifest.get("status") != "ok"
        or sequence_manifest.get("kind")
        != "gdp_cem_p1_goal_conditioned_action_sequence_cache"
        or sequence_manifest.get("analysis_role") != "P1_only_method_development"
        or sequence_manifest.get("protocol_sha256") != CACHE_PROTOCOL_SHA256
        or sequence_manifest.get("source_manifest_sha256") != CACHE_SOURCE_SHA256
        or sha256_file(args.sequence_manifest)
        != task_spec["sequence_manifest_sha256"]
        or sequence_manifest.get("goal_offset") != 25
        or sequence_manifest.get("macro_horizon") != 5
        or sequence_manifest.get("primitive_steps_per_macro") != 5
        or sequence_manifest.get("latent_dim") != 192
        or sequence_manifest.get("primitive_action_dim")
        != task_spec["primitive_action_dim"]
        or sequence_manifest.get("macro_action_dim") != task_spec["macro_action_dim"]
        or sequence_manifest.get("sequences") != task_spec["sequences"]
        or sequence_manifest.get("train_sequences") != task_spec["train_sequences"]
        or sequence_manifest.get("validation_sequences")
        != task_spec["validation_sequences"]
        or sequence_manifest.get("output_h5_sha256") != sha256_file(args.sequence_h5)
        or sequence_manifest.get("output_h5_sha256")
        != task_spec["sequence_h5_sha256"]
        or sequence_manifest.get("latent_h5_sha256") != sha256_file(args.latent_h5)
        or sequence_manifest.get("latent_h5_sha256") != task_spec["latent_h5_sha256"]
        or sequence_manifest.get("d2_read") is not False
        or sequence_manifest.get("d3_read") is not False
        or sequence_manifest.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("GDP-CEM P1 selection cache lineage differs")
    with h5py.File(args.latent_h5, "r") as handle:
        latents = np.asarray(handle["latent"][:], dtype=np.float32)
        global_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
    with h5py.File(args.sequence_h5, "r") as handle:
        source_index = np.asarray(handle["source_index"][:], dtype=np.int64)
        goal_index = np.asarray(handle["goal_index"][:], dtype=np.int64)
        role = np.asarray(handle["role"][:], dtype=np.uint8)
        actions = np.asarray(handle["action"][:], dtype=np.float32).reshape(
            len(role), 25, int(sequence_manifest["primitive_action_dim"])
        )
    validation_rows = np.flatnonzero(role == 1)
    row_generator = np.random.default_rng(
        numpy_seed_from_sha256(
            f"gdp-cem-e7p-selection|task={args.task}|seed=2026081702"
        )
    )
    selected_rows = row_generator.choice(
        validation_rows, size=CONTEXT_COUNT, replace=False
    ).astype(np.int64)

    latent_mean = torch.as_tensor(payloads["diffusion_true"]["latent_mean"], device=device)
    latent_std = torch.as_tensor(payloads["diffusion_true"]["latent_std"], device=device)
    first = int(selected_rows[0])
    cached_first = torch.from_numpy(latents[source_index[first]])[None].to(device)
    goal_first = torch.from_numpy(latents[goal_index[first]])[None].to(device)
    normalized_first = (cached_first - latent_mean) / latent_std
    normalized_goal_first = (goal_first - latent_mean) / latent_std
    determinism = determinism_preflight(
        world_model,
        task=args.task,
        models=models,
        payloads=payloads,
        current=normalized_first,
        goal=normalized_goal_first,
        current_raw=cached_first,
    )
    equivalence = real_stack_equivalence(
        world_model,
        dataset=args.dataset,
        global_row=int(global_rows[source_index[first]]),
        cached_current=cached_first,
        action_dim=int(sequence_manifest["macro_action_dim"]),
        device=device,
        seed=derived_seed(f"gdp-e7p-equivalence|{args.task}"),
    )

    raw_path = args.output_dir / "per-context.jsonl"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    collected: dict[str, list[dict[str, float]]] = {}
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    with raw_path.open("x", encoding="utf-8") as stream:
        for ordinal, row in enumerate(selected_rows.tolist()):
            current_raw = torch.from_numpy(latents[source_index[row]])[None].to(device)
            goal_raw = torch.from_numpy(latents[goal_index[row]])[None].to(device)
            current = (current_raw - latent_mean) / latent_std
            goal = (goal_raw - latent_mean) / latent_std
            reference = torch.from_numpy(actions[row])[None].to(device)
            banks: dict[str, torch.Tensor] = {}
            bank_generation_seconds: dict[str, float] = {}
            for condition in ("diffusion_true", "diffusion_shuffled_goal"):
                model = models[condition]
                assert isinstance(model, JointActionDiffusion)
                for steps in DDIM_STEPS:
                    seed = derived_seed(
                        f"gdp-e7p-proposal|task={args.task}|condition={condition}|"
                        f"row={row}|ddim={steps}|seed=6101"
                    )
                    generator = torch.Generator(device=device).manual_seed(seed)
                    torch.cuda.synchronize()
                    generation_started = time.perf_counter()
                    bank = planner_samples(
                        model,
                        payloads[condition],
                        current=current,
                        goal=goal,
                        count=CANDIDATE_COUNT,
                        generator=generator,
                        ddim_steps=steps,
                    )
                    torch.cuda.synchronize()
                    generation_seconds = time.perf_counter() - generation_started
                    label = f"select_{condition}_ddim{steps}"
                    banks[label] = bank
                    bank_generation_seconds[label] = generation_seconds
                    torch.cuda.synchronize()
                    rollout_started = time.perf_counter()
                    metrics = metric_record(
                        world_model,
                        current_raw=current_raw,
                        goal_raw=goal_raw,
                        candidates_primitive=bank,
                        reference_primitive=reference,
                    )
                    torch.cuda.synchronize()
                    metrics["generation_seconds"] = generation_seconds
                    metrics["rollout_seconds"] = time.perf_counter() - rollout_started
                    collected.setdefault(label, []).append(metrics)
                    stream.write(json.dumps({"row": row, "ordinal": ordinal, "label": label, **metrics}, sort_keys=True) + "\n")

            gaussian_model = models["gaussian_true"]
            assert isinstance(gaussian_model, ConditionalDiagonalGaussian)
            gaussian_generator = torch.Generator(device=device).manual_seed(
                derived_seed(f"gdp-e7p-proposal|task={args.task}|condition=gaussian_true|row={row}|seed=6101")
            )
            torch.cuda.synchronize()
            generation_started = time.perf_counter()
            gaussian_bank = planner_samples(
                gaussian_model,
                payloads["gaussian_true"],
                current=current,
                goal=goal,
                count=CANDIDATE_COUNT,
                generator=gaussian_generator,
                ddim_steps=None,
            )
            torch.cuda.synchronize()
            generation_seconds = time.perf_counter() - generation_started
            label = "select_gaussian_true"
            torch.cuda.synchronize()
            rollout_started = time.perf_counter()
            metrics = metric_record(
                world_model,
                current_raw=current_raw,
                goal_raw=goal_raw,
                candidates_primitive=gaussian_bank,
                reference_primitive=reference,
            )
            torch.cuda.synchronize()
            metrics["generation_seconds"] = generation_seconds
            metrics["rollout_seconds"] = time.perf_counter() - rollout_started
            collected.setdefault(label, []).append(metrics)
            stream.write(json.dumps({"row": row, "ordinal": ordinal, "label": label, **metrics}, sort_keys=True) + "\n")

            primitive_dim = reference.shape[-1]
            cem_generator = torch.Generator(device=device).manual_seed(
                derived_seed(f"gdp-e7p-cem-gaussian|task={args.task}|row={row}|planner=8301")
            )
            torch.cuda.synchronize()
            cem_generation_started = time.perf_counter()
            cem_gaussian = torch.randn(
                1,
                CANDIDATE_COUNT,
                5,
                5 * primitive_dim,
                generator=cem_generator,
                device=device,
            )
            cem_gaussian[:, 0] = 0.0
            gaussian_primitive = cem_gaussian.reshape(1, CANDIDATE_COUNT, 25, primitive_dim)
            torch.cuda.synchronize()
            cem_generation_seconds = time.perf_counter() - cem_generation_started
            base_label = "matched_gaussian_only"
            torch.cuda.synchronize()
            base_rollout_started = time.perf_counter()
            base_metrics = metric_record(
                world_model,
                current_raw=current_raw,
                goal_raw=goal_raw,
                candidates_primitive=gaussian_primitive,
                reference_primitive=reference,
            )
            torch.cuda.synchronize()
            base_metrics["generation_seconds"] = cem_generation_seconds
            base_metrics["rollout_seconds"] = time.perf_counter() - base_rollout_started
            collected.setdefault(base_label, []).append(base_metrics)
            stream.write(json.dumps({"row": row, "ordinal": ordinal, "label": base_label, **base_metrics}, sort_keys=True) + "\n")
            for steps in DDIM_STEPS:
                diffusion_bank = banks[f"select_diffusion_true_ddim{steps}"]
                for fraction in FRACTIONS:
                    count = int(round((CANDIDATE_COUNT - 1) * fraction))
                    mixed = gaussian_primitive.clone()
                    mixed[:, 1 : 1 + count] = diffusion_bank[:, :count]
                    fraction_label = f"matched_diffusion_true_ddim{steps}_q{int(fraction * 100):02d}"
                    torch.cuda.synchronize()
                    fraction_rollout_started = time.perf_counter()
                    fraction_metrics = metric_record(
                        world_model,
                        current_raw=current_raw,
                        goal_raw=goal_raw,
                        candidates_primitive=mixed,
                        reference_primitive=reference,
                    )
                    torch.cuda.synchronize()
                    fraction_metrics["generation_seconds"] = (
                        cem_generation_seconds
                        + bank_generation_seconds[f"select_diffusion_true_ddim{steps}"]
                    )
                    fraction_metrics["rollout_seconds"] = (
                        time.perf_counter() - fraction_rollout_started
                    )
                    collected.setdefault(fraction_label, []).append(fraction_metrics)
                    stream.write(json.dumps({"row": row, "ordinal": ordinal, "label": fraction_label, **fraction_metrics}, sort_keys=True) + "\n")
            stream.flush()

    aggregate = {}
    for label, records in collected.items():
        aggregate[label] = {
            key: float(np.median([record[key] for record in records]))
            for key in records[0]
        }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e7p_p1_selection_task",
        "analysis_role": "P1_validation_only_method_selection",
        "task": args.task,
        "context_count": CONTEXT_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "ddim_steps": list(DDIM_STEPS),
        "proposal_fractions": list(FRACTIONS),
        "per_task_medians": aggregate,
        "real_stack_equivalence": equivalence,
        "determinism_preflight": determinism,
        "models": model_records,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "sequence_h5_sha256": sha256_file(args.sequence_h5),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "per_context": str(raw_path),
        "per_context_sha256": sha256_file(raw_path),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "peak_cuda_memory_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        },
        "d2_read": False,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
