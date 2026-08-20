#!/usr/bin/env python3
"""Evaluate Gaussian-anchored epsilon-diffusion refinement on fresh P1 rows."""

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

import evaluate_gdp_cem_e7p_selection as e7
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
    ddim_refine_epsilon,
)


PROTOCOL_SHA256 = "e6ad569e0313276bff2cf79835bcd53c4b1604113b34bacdb5004a4bae034141"
E7_AGGREGATE_SHA256 = "bcd49f6fa7b7d1b03d8f95b4d46001e08b97c4725b43a55a953afc4ebe25544d"
CONTEXT_COUNT = 512
CANDIDATE_COUNT = 300
RESTARTS = (10, 20, 40)
REVERSE_STEPS = (1, 5, 10)
FRACTIONS = (0.25, 0.50, 0.75, 1.00)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(value: np.ndarray | torch.Tensor) -> str:
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def select_fresh_rows(
    *, validation_rows: np.ndarray, task: str
) -> tuple[np.ndarray, dict[str, Any]]:
    old_generator = np.random.default_rng(
        e7.numpy_seed_from_sha256(
            f"gdp-cem-e7p-selection|task={task}|seed=2026081702"
        )
    )
    old_rows = old_generator.choice(
        validation_rows, size=e7.CONTEXT_COUNT, replace=False
    ).astype(np.int64)
    training_generator = np.random.default_rng(
        e7.derived_seed(f"gdp-e7p-validation-rows|{task}|6101")
    )
    training_positions = training_generator.choice(
        len(validation_rows), size=8192, replace=False
    ).astype(np.int64)
    training_rows = validation_rows[training_positions]
    excluded = np.unique(np.concatenate((old_rows, training_rows)))
    available = np.setdiff1d(validation_rows, excluded, assume_unique=False)
    generator = np.random.default_rng(
        e7.numpy_seed_from_sha256(
            f"gdp-cem-e8a-selection|task={task}|seed=2026081703"
        )
    )
    selected = generator.choice(
        available, size=CONTEXT_COUNT, replace=False
    ).astype(np.int64)
    if (
        len(np.intersect1d(selected, old_rows))
        or len(np.intersect1d(selected, training_rows))
        or len(np.unique(selected)) != CONTEXT_COUNT
    ):
        raise RuntimeError("E8A fresh P1 selection overlaps excluded rows")
    return selected, {
        "validation_rows_count": int(len(validation_rows)),
        "validation_rows_sha256": array_sha256(validation_rows),
        "e7_selection_rows_count": int(len(old_rows)),
        "e7_selection_rows_sha256": array_sha256(old_rows),
        "training_validation_rows_count": int(len(training_rows)),
        "training_validation_rows_sha256": array_sha256(training_rows),
        "excluded_unique_rows_count": int(len(excluded)),
        "excluded_unique_rows_sha256": array_sha256(excluded),
        "available_rows_count": int(len(available)),
        "available_rows_sha256": array_sha256(available),
        "selected_rows_count": int(len(selected)),
        "selected_rows_sha256": array_sha256(selected),
    }


@torch.inference_mode()
def normalized_gaussian_bank(
    model: ConditionalDiagonalGaussian,
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    count: int,
    generator: torch.Generator,
    low: torch.Tensor,
    high: torch.Tensor,
) -> torch.Tensor:
    mean, log_std = model(current, goal)
    noise = torch.randn(
        current.shape[0],
        count,
        model.action_horizon,
        model.primitive_action_dim,
        generator=generator,
        device=current.device,
        dtype=current.dtype,
    )
    bank = mean[:, None] + log_std.exp()[:, None] * noise
    bank[:, 0] = mean
    bank = torch.maximum(torch.minimum(bank, high), low)
    if (
        bank.shape
        != (
            current.shape[0],
            count,
            model.action_horizon,
            model.primitive_action_dim,
        )
        or not torch.isfinite(bank).all()
    ):
        raise RuntimeError("E8A conditional-Gaussian base bank is invalid")
    return bank


def planner_coordinates(
    normalized: torch.Tensor,
    *,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    robust_low: torch.Tensor,
    robust_high: torch.Tensor,
) -> torch.Tensor:
    planner = normalized * action_std + action_mean
    planner = torch.maximum(torch.minimum(planner, robust_high), robust_low)
    if not torch.isfinite(planner).all():
        raise RuntimeError("E8A planner-coordinate bank is non-finite")
    return planner


def metric_record(
    world_model: torch.nn.Module,
    *,
    current_raw: torch.Tensor,
    goal_raw: torch.Tensor,
    candidates_primitive: torch.Tensor,
    candidates_normalized: torch.Tensor,
    reference_primitive: torch.Tensor,
    base_primitive: torch.Tensor,
    normalized_low: torch.Tensor,
    normalized_high: torch.Tensor,
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
    boundary = torch.logical_or(
        candidates_normalized == normalized_low,
        candidates_normalized == normalized_high,
    )
    result = {
        key: float(value[0].detach().cpu()) for key, value in metrics.items()
    }
    result["boundary_fraction"] = float(boundary.float().mean().cpu())
    result["refinement_displacement_mse"] = float(
        (candidates_primitive - base_primitive).square().mean().cpu()
    )
    return result


def validate_e7_aggregate(path: Path) -> dict[str, Any]:
    if sha256_file(path) != E7_AGGREGATE_SHA256:
        raise RuntimeError("E8A prerequisite E7P aggregate hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e7p_p1_selection_aggregate"
        or value.get("analysis_role") != "P1_validation_only_method_selection"
        or value.get("decision") != "stop_goal_conditioned_diffusion_proposal_before_d2"
        or value.get("gdp_select_p1_gate_pass") is not False
        or value.get("matched_gdp_cem_p1_gate_pass") is not False
        or value.get("d2_read") is not False
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E8A prerequisite E7P decision differs")
    return value


@torch.inference_mode()
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
    parser.add_argument("--e7-aggregate", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.latent_h5,
        args.sequence_h5,
        args.sequence_manifest,
        args.dataset,
        args.world_model_checkpoint,
        args.e7_aggregate,
        args.protocol,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E8A protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E8A output")
    e7_aggregate = validate_e7_aggregate(args.e7_aggregate)
    summary_paths = {condition: Path(path) for condition, path in args.proposal_summary}
    if set(summary_paths) != set(e7.CONDITIONS):
        raise RuntimeError("E8A requires the three exact E7P proposal conditions")

    if not torch.cuda.is_available():
        raise RuntimeError("E8A requires CUDA")
    device = torch.device("cuda")
    torch.manual_seed(2026081703)
    torch.cuda.manual_seed_all(2026081703)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    models: dict[str, torch.nn.Module] = {}
    payloads: dict[str, dict[str, Any]] = {}
    model_records: dict[str, dict[str, Any]] = {}
    for condition in e7.CONDITIONS:
        models[condition], payloads[condition], model_records[condition] = (
            e7.load_checkpoint(
                summary_paths[condition],
                task=args.task,
                condition=condition,
                device=device,
            )
        )
    for key in (
        "latent_mean",
        "latent_std",
        "action_mean",
        "action_std",
        "robust_low",
        "robust_high",
    ):
        reference_statistic = torch.as_tensor(payloads["diffusion_true"][key]).float()
        if any(
            not torch.equal(
                reference_statistic, torch.as_tensor(payloads[condition][key]).float()
            )
            for condition in e7.CONDITIONS
        ):
            raise RuntimeError(f"E8A proposal statistics differ: {key}")
    true_model = models["diffusion_true"]
    shuffled_model = models["diffusion_shuffled_goal"]
    gaussian_model = models["gaussian_true"]
    if not (
        isinstance(true_model, JointActionDiffusion)
        and isinstance(shuffled_model, JointActionDiffusion)
        and isinstance(gaussian_model, ConditionalDiagonalGaussian)
    ):
        raise RuntimeError("E8A proposal model classes differ")

    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("E8A world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    sequence_manifest = json.loads(args.sequence_manifest.read_text(encoding="utf-8"))
    spec = e7.TASK_SPEC[args.task]
    if (
        sha256_file(args.sequence_manifest) != spec["sequence_manifest_sha256"]
        or sequence_manifest.get("status") != "ok"
        or sequence_manifest.get("kind")
        != "gdp_cem_p1_goal_conditioned_action_sequence_cache"
        or sequence_manifest.get("analysis_role") != "P1_only_method_development"
        or sequence_manifest.get("protocol_sha256") != e7.CACHE_PROTOCOL_SHA256
        or sequence_manifest.get("source_manifest_sha256") != e7.CACHE_SOURCE_SHA256
        or sequence_manifest.get("output_h5_sha256") != sha256_file(args.sequence_h5)
        or sequence_manifest.get("output_h5_sha256") != spec["sequence_h5_sha256"]
        or sequence_manifest.get("latent_h5_sha256") != sha256_file(args.latent_h5)
        or sequence_manifest.get("latent_h5_sha256") != spec["latent_h5_sha256"]
        or sequence_manifest.get("goal_offset") != 25
        or sequence_manifest.get("macro_horizon") != 5
        or sequence_manifest.get("primitive_steps_per_macro") != 5
        or sequence_manifest.get("primitive_action_dim")
        != spec["primitive_action_dim"]
        or sequence_manifest.get("d2_read") is not False
        or sequence_manifest.get("d3_read") is not False
        or sequence_manifest.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E8A cache lineage differs")
    with h5py.File(args.latent_h5, "r") as handle:
        latents = np.asarray(handle["latent"][:], dtype=np.float32)
        global_rows = np.asarray(handle["row_index"][:], dtype=np.int64)
    with h5py.File(args.sequence_h5, "r") as handle:
        source_index = np.asarray(handle["source_index"][:], dtype=np.int64)
        goal_index = np.asarray(handle["goal_index"][:], dtype=np.int64)
        role = np.asarray(handle["role"][:], dtype=np.uint8)
        actions = np.asarray(handle["action"][:], dtype=np.float32).reshape(
            len(role), 25, int(spec["primitive_action_dim"])
        )
    selected_rows, row_selection = select_fresh_rows(
        validation_rows=np.flatnonzero(role == 1), task=args.task
    )

    payload = payloads["diffusion_true"]
    latent_mean = torch.as_tensor(payload["latent_mean"], device=device)
    latent_std = torch.as_tensor(payload["latent_std"], device=device)
    action_mean = torch.as_tensor(payload["action_mean"], device=device)
    action_std = torch.as_tensor(payload["action_std"], device=device)
    robust_low = torch.as_tensor(payload["robust_low"], device=device)
    robust_high = torch.as_tensor(payload["robust_high"], device=device)
    normalized_low = ((robust_low - action_mean) / action_std).reshape(1, 1, 1, -1)
    normalized_high = ((robust_high - action_mean) / action_std).reshape(1, 1, 1, -1)
    schedule = CosineDiffusionSchedule.build(100)
    normalization = {}
    for key, tensor in (
        ("latent_mean", latent_mean),
        ("latent_std", latent_std),
        ("action_mean", action_mean),
        ("action_std", action_std),
        ("robust_low", robust_low),
        ("robust_high", robust_high),
        ("normalized_low", normalized_low),
        ("normalized_high", normalized_high),
    ):
        cpu = tensor.detach().cpu().contiguous().float()
        record: dict[str, Any] = {
            "shape": list(cpu.shape),
            "dtype": str(cpu.numpy().dtype),
            "sha256": array_sha256(cpu),
        }
        if cpu.numel() <= 16:
            record["values"] = cpu.flatten().tolist()
        normalization[key] = record

    first_row = int(selected_rows[0])
    first_raw = torch.from_numpy(latents[source_index[first_row]])[None].to(device)
    first_goal_raw = torch.from_numpy(latents[goal_index[first_row]])[None].to(device)
    first_current = (first_raw - latent_mean) / latent_std
    first_goal = (first_goal_raw - latent_mean) / latent_std
    base_seed = e7.derived_seed(f"gdp-e8a-base|task={args.task}|row={first_row}|seed=6101")
    first_base = normalized_gaussian_bank(
        gaussian_model,
        current=first_current,
        goal=first_goal,
        count=CANDIDATE_COUNT,
        generator=torch.Generator(device=device).manual_seed(base_seed),
        low=normalized_low,
        high=normalized_high,
    )
    repeat_base = normalized_gaussian_bank(
        gaussian_model,
        current=first_current,
        goal=first_goal,
        count=CANDIDATE_COUNT,
        generator=torch.Generator(device=device).manual_seed(base_seed),
        low=normalized_low,
        high=normalized_high,
    )
    refine_seed = e7.derived_seed(
        f"gdp-e8a-refine|task={args.task}|row={first_row}|restart=20|seed=6101"
    )
    first_refined = ddim_refine_epsilon(
        true_model,
        current=first_current,
        goal=first_goal,
        clean=first_base,
        restart_timestep=20,
        inference_steps=5,
        schedule=schedule,
        generator=torch.Generator(device=device).manual_seed(refine_seed),
        clip_low=normalized_low.flatten(),
        clip_high=normalized_high.flatten(),
    )
    repeat_refined = ddim_refine_epsilon(
        true_model,
        current=first_current,
        goal=first_goal,
        clean=first_base,
        restart_timestep=20,
        inference_steps=5,
        schedule=schedule,
        generator=torch.Generator(device=device).manual_seed(refine_seed),
        clip_low=normalized_low.flatten(),
        clip_high=normalized_high.flatten(),
    )
    if (
        not torch.equal(first_base, repeat_base)
        or not torch.equal(first_refined, repeat_refined)
        or not torch.isfinite(first_refined).all()
    ):
        raise RuntimeError("E8A deterministic candidate preflight failed")
    equivalence = e7.real_stack_equivalence(
        world_model,
        dataset=args.dataset,
        global_row=int(global_rows[source_index[first_row]]),
        cached_current=first_raw,
        action_dim=int(spec["macro_action_dim"]),
        device=device,
        seed=e7.derived_seed(f"gdp-e8a-equivalence|{args.task}"),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "per-context.jsonl"
    collected: dict[str, list[dict[str, float]]] = {}
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    with detail_path.open("x", encoding="utf-8") as stream:
        for ordinal, row in enumerate(selected_rows.tolist()):
            current_raw = torch.from_numpy(latents[source_index[row]])[None].to(device)
            goal_raw = torch.from_numpy(latents[goal_index[row]])[None].to(device)
            current = (current_raw - latent_mean) / latent_std
            goal = (goal_raw - latent_mean) / latent_std
            reference = torch.from_numpy(actions[row])[None].to(device)
            base_generator = torch.Generator(device=device).manual_seed(
                e7.derived_seed(f"gdp-e8a-base|task={args.task}|row={row}|seed=6101")
            )
            torch.cuda.synchronize()
            base_started = time.perf_counter()
            base_normalized = normalized_gaussian_bank(
                gaussian_model,
                current=current,
                goal=goal,
                count=CANDIDATE_COUNT,
                generator=base_generator,
                low=normalized_low,
                high=normalized_high,
            )
            base_planner = planner_coordinates(
                base_normalized,
                action_mean=action_mean,
                action_std=action_std,
                robust_low=robust_low,
                robust_high=robust_high,
            )
            torch.cuda.synchronize()
            base_generation_seconds = time.perf_counter() - base_started
            torch.cuda.synchronize()
            rollout_started = time.perf_counter()
            base_metrics = metric_record(
                world_model,
                current_raw=current_raw,
                goal_raw=goal_raw,
                candidates_primitive=base_planner,
                candidates_normalized=base_normalized,
                reference_primitive=reference,
                base_primitive=base_planner,
                normalized_low=normalized_low,
                normalized_high=normalized_high,
            )
            torch.cuda.synchronize()
            base_metrics["generation_seconds"] = base_generation_seconds
            base_metrics["rollout_seconds"] = time.perf_counter() - rollout_started
            collected.setdefault("gaussian_base", []).append(base_metrics)
            stream.write(
                json.dumps(
                    {"row": row, "ordinal": ordinal, "label": "gaussian_base", **base_metrics},
                    sort_keys=True,
                )
                + "\n"
            )

            for restart in RESTARTS:
                for reverse_steps in REVERSE_STEPS:
                    noise_seed = e7.derived_seed(
                        f"gdp-e8a-refine|task={args.task}|row={row}|"
                        f"restart={restart}|seed=6101"
                    )
                    refined_banks: dict[str, torch.Tensor] = {}
                    refinement_seconds: dict[str, float] = {}
                    for condition, model in (
                        ("true", true_model),
                        ("shuffled", shuffled_model),
                    ):
                        torch.cuda.synchronize()
                        refinement_started = time.perf_counter()
                        refined_banks[condition] = ddim_refine_epsilon(
                            model,
                            current=current,
                            goal=goal,
                            clean=base_normalized,
                            restart_timestep=restart,
                            inference_steps=reverse_steps,
                            schedule=schedule,
                            generator=torch.Generator(device=device).manual_seed(noise_seed),
                            clip_low=normalized_low.flatten(),
                            clip_high=normalized_high.flatten(),
                        )
                        torch.cuda.synchronize()
                        refinement_seconds[condition] = (
                            time.perf_counter() - refinement_started
                        )
                    for fraction in FRACTIONS:
                        count = int(round((CANDIDATE_COUNT - 1) * fraction))
                        for condition in ("true", "shuffled"):
                            mixed = base_normalized.clone()
                            mixed[:, 1 : 1 + count] = refined_banks[condition][
                                :, 1 : 1 + count
                            ]
                            mixed_planner = planner_coordinates(
                                mixed,
                                action_mean=action_mean,
                                action_std=action_std,
                                robust_low=robust_low,
                                robust_high=robust_high,
                            )
                            label = (
                                f"{condition}_r{restart}_k{reverse_steps}_"
                                f"q{int(fraction * 100):02d}"
                            )
                            torch.cuda.synchronize()
                            rollout_started = time.perf_counter()
                            metrics = metric_record(
                                world_model,
                                current_raw=current_raw,
                                goal_raw=goal_raw,
                                candidates_primitive=mixed_planner,
                                candidates_normalized=mixed,
                                reference_primitive=reference,
                                base_primitive=base_planner,
                                normalized_low=normalized_low,
                                normalized_high=normalized_high,
                            )
                            torch.cuda.synchronize()
                            metrics["generation_seconds"] = (
                                base_generation_seconds
                                + refinement_seconds[condition]
                            )
                            metrics["rollout_seconds"] = (
                                time.perf_counter() - rollout_started
                            )
                            collected.setdefault(label, []).append(metrics)
                            stream.write(
                                json.dumps(
                                    {
                                        "row": row,
                                        "ordinal": ordinal,
                                        "label": label,
                                        **metrics,
                                    },
                                    sort_keys=True,
                                )
                                + "\n"
                            )
            stream.flush()

    medians = {
        label: {
            key: float(np.median([record[key] for record in records]))
            for key in records[0]
        }
        for label, records in collected.items()
    }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e8a_p1_refinement_task",
        "analysis_role": "P1_disjoint_validation_method_rescue",
        "task": args.task,
        "context_count": CONTEXT_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "restarts": list(RESTARTS),
        "reverse_steps": list(REVERSE_STEPS),
        "refined_fractions": list(FRACTIONS),
        "refined_candidate_counts": {
            f"{fraction:.2f}": int(round((CANDIDATE_COUNT - 1) * fraction))
            for fraction in FRACTIONS
        },
        "per_task_medians": medians,
        "fresh_rows_sha256": array_sha256(selected_rows),
        "row_selection": row_selection,
        "excluded_e7_selection_count": e7.CONTEXT_COUNT,
        "excluded_training_validation_count": 8192,
        "determinism_preflight": {
            "status": "ok",
            "base_repeat_max_abs": float((first_base - repeat_base).abs().max().cpu()),
            "refinement_repeat_max_abs": float(
                (first_refined - repeat_refined).abs().max().cpu()
            ),
        },
        "rng_namespaces": {
            "e7_selection_numpy": (
                f"gdp-cem-e7p-selection|task={args.task}|seed=2026081702"
            ),
            "training_validation_numpy": (
                f"gdp-e7p-validation-rows|{args.task}|6101"
            ),
            "e8a_selection_numpy": (
                f"gdp-cem-e8a-selection|task={args.task}|seed=2026081703"
            ),
            "gaussian_base_torch_template": (
                f"gdp-e8a-base|task={args.task}|row={{row}}|seed=6101"
            ),
            "refinement_noise_torch_template": (
                f"gdp-e8a-refine|task={args.task}|row={{row}}|"
                "restart={restart}|seed=6101"
            ),
            "numpy_selection_derivation": "first_64_sha256_bits_big_endian",
            "torch_derivation": "first_64_sha256_bits_little_endian_mod_2^63_minus_1",
        },
        "normalization": normalization,
        "cosine_alpha_bar_sha256": array_sha256(schedule.alpha_bar),
        "real_stack_equivalence": equivalence,
        "models": model_records,
        "e7_aggregate": str(args.e7_aggregate),
        "e7_aggregate_sha256": E7_AGGREGATE_SHA256,
        "e7_decision": e7_aggregate["decision"],
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "sequence_h5_sha256": sha256_file(args.sequence_h5),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "per_context": str(detail_path),
        "per_context_sha256": sha256_file(detail_path),
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
