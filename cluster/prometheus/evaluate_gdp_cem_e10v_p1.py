#!/usr/bin/env python3
"""Evaluate pure classifier-free velocity proposals on fresh P1 contexts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import stable_worldmodel as swm
import torch

import evaluate_gdp_cem_e7p_selection as e7
import evaluate_gdp_cem_e8a_refinement as e8
import train_gdp_cem_vp_proposal as train
from acid_alternative.io_utils import atomic_write_json, resolve_policy_checkpoint
from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    CosineDiffusionSchedule,
    JointActionDiffusion,
    VelocityActionDiffusion,
    load_proposal_model,
    velocity_ddim_sample,
)


TASKS = ("pusht", "reacher", "cube")
VP_CONDITIONS = ("vp_true", "vp_shuffled_goal")
CANDIDATE_COUNT = 300
CONTEXT_COUNT = 512
REVERSE_STEPS = (5, 10, 20, 40)
GUIDANCE_SCALES = (0.0, 1.0, 1.5, 2.0, 3.0)
PROTOCOL_SHA256 = "2f3052637e72016d4218fd6e13c62d36589773f23a9a0b4223c9a808e9fab93a"


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


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d2", "d3", "c1", "i1"}):
        raise RuntimeError(f"E10V protected path is forbidden: {path}")


def scale_label(scale: float) -> str:
    return f"g{int(round(scale * 10)):03d}"


def load_vp_checkpoint(
    summary_path: Path,
    *,
    task: str,
    condition: str,
    source_manifest_sha256: str,
    device: torch.device,
) -> tuple[VelocityActionDiffusion, dict[str, Any], dict[str, Any]]:
    reject_protected_path(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e10v_p1_velocity_training"
        or summary.get("analysis_role")
        != "post_E8D_P1_only_pure_diffusion_development"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or summary.get("proposal_kind") != "velocity_diffusion"
        or summary.get("prediction_type") != "velocity"
        or summary.get("seed") != 6101
        or summary.get("protocol_sha256") != PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_manifest_sha256
        or summary.get("d2_read") is not False
        or summary.get("d3_read") is not False
        or summary.get("protected_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"E10V training summary differs: {summary_path}")
    checkpoint = Path(summary.get("checkpoint", ""))
    reject_protected_path(checkpoint)
    if not checkpoint.is_file() or sha256_file(checkpoint) != summary.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError("E10V checkpoint hash differs")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    expected_config = {
        "latent_dim": 192,
        "primitive_action_dim": int(e7.TASK_SPEC[task]["primitive_action_dim"]),
        "action_horizon": 25,
        "width": 512,
        "depth": 4,
        "time_embedding_dim": 128,
    }
    if (
        payload.get("kind") != "gdp_cem_e10v_p1_velocity_checkpoint"
        or payload.get("proposal_kind") != "velocity_diffusion"
        or payload.get("prediction_type") != "velocity"
        or payload.get("task") != task
        or payload.get("condition") != condition
        or payload.get("seed") != 6101
        or payload.get("model_config") != expected_config
        or payload.get("protocol_sha256") != PROTOCOL_SHA256
        or payload.get("source_manifest_sha256") != source_manifest_sha256
        or payload.get("diffusion_steps") != 100
        or payload.get("condition_dropout") != 0.15
        or summary.get("model_config") != expected_config
        or summary.get("row_selection") != payload.get("row_selection")
    ):
        raise RuntimeError("E10V checkpoint identity differs")
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
    if (
        any(statistics[key].shape != shape for key, shape in statistic_shapes.items())
        or not all(torch.isfinite(value).all() for value in statistics.values())
        or torch.any(statistics["latent_std"] <= 1.0e-6)
        or torch.any(statistics["action_std"] <= 1.0e-6)
        or torch.any(statistics["robust_high"] <= statistics["robust_low"])
    ):
        raise RuntimeError("E10V checkpoint statistics differ")
    model = load_proposal_model(payload, device=device)
    if not isinstance(model, VelocityActionDiffusion):
        raise RuntimeError("E10V checkpoint loaded the wrong model class")
    if sum(parameter.numel() for parameter in model.parameters()) != int(
        summary["parameter_count"]
    ):
        raise RuntimeError("E10V parameter count differs")
    return model, payload, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "best_step": summary["best_step"],
        "best_validation": summary["best_validation"],
        "parameter_count": summary["parameter_count"],
    }


def normalized_from_planner(
    planner: torch.Tensor,
    *,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    robust_low: torch.Tensor,
    robust_high: torch.Tensor,
) -> torch.Tensor:
    normalized = (planner - action_mean) / action_std
    normalized_low = (robust_low - action_mean) / action_std
    normalized_high = (robust_high - action_mean) / action_std
    normalized = torch.where(planner == robust_low, normalized_low, normalized)
    normalized = torch.where(planner == robust_high, normalized_high, normalized)
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--latent-h5", type=Path, required=True)
    parser.add_argument("--sequence-h5", type=Path, required=True)
    parser.add_argument("--sequence-manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--vp-summary", nargs=2, action="append", required=True)
    parser.add_argument("--e7-summary", nargs=2, action="append", required=True)
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
    for path in (*required, args.output_dir):
        reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E10V protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E10V P1 output")
    source_hash = sha256_file(args.source_manifest)

    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("E10V P1 evaluation requires CUDA")
    torch.manual_seed(2026081707)
    torch.cuda.manual_seed_all(2026081707)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)

    vp_paths = {condition: Path(path) for condition, path in args.vp_summary}
    if set(vp_paths) != set(VP_CONDITIONS):
        raise RuntimeError("E10V requires exactly two velocity conditions")
    vp_models: dict[str, VelocityActionDiffusion] = {}
    vp_payloads: dict[str, dict[str, Any]] = {}
    vp_records: dict[str, dict[str, Any]] = {}
    for condition in VP_CONDITIONS:
        vp_models[condition], vp_payloads[condition], vp_records[condition] = (
            load_vp_checkpoint(
                vp_paths[condition],
                task=args.task,
                condition=condition,
                source_manifest_sha256=source_hash,
                device=device,
            )
        )

    e7_paths = {condition: Path(path) for condition, path in args.e7_summary}
    if set(e7_paths) != set(e7.CONDITIONS):
        raise RuntimeError("E10V requires the exact three E7 controls")
    e7_models: dict[str, torch.nn.Module] = {}
    e7_payloads: dict[str, dict[str, Any]] = {}
    e7_records: dict[str, dict[str, Any]] = {}
    for condition in e7.CONDITIONS:
        reject_protected_path(e7_paths[condition])
        e7_models[condition], e7_payloads[condition], e7_records[condition] = (
            e7.load_checkpoint(
                e7_paths[condition],
                task=args.task,
                condition=condition,
                device=device,
            )
        )
    if not (
        isinstance(e7_models["diffusion_true"], JointActionDiffusion)
        and isinstance(e7_models["diffusion_shuffled_goal"], JointActionDiffusion)
        and isinstance(e7_models["gaussian_true"], ConditionalDiagonalGaussian)
    ):
        raise RuntimeError("E10V E7 control classes differ")

    for key in (
        "latent_mean",
        "latent_std",
        "action_mean",
        "action_std",
        "robust_low",
        "robust_high",
    ):
        reference = torch.as_tensor(vp_payloads["vp_true"][key]).float()
        comparisons = [
            torch.as_tensor(vp_payloads["vp_shuffled_goal"][key]).float(),
            *[
                torch.as_tensor(e7_payloads[condition][key]).float()
                for condition in e7.CONDITIONS
            ],
        ]
        if any(not torch.equal(reference, value) for value in comparisons):
            raise RuntimeError(f"E10V proposal statistic differs: {key}")
    if vp_payloads["vp_true"]["row_selection"] != vp_payloads[
        "vp_shuffled_goal"
    ]["row_selection"]:
        raise RuntimeError("E10V velocity row-selection records differ")
    selected_rows = torch.as_tensor(
        vp_payloads["vp_true"]["final_rows"], dtype=torch.int64
    ).numpy()
    if (
        selected_rows.shape != (CONTEXT_COUNT,)
        or array_sha256(selected_rows)
        != vp_payloads["vp_true"]["row_selection"]["final_rows_sha256"]
    ):
        raise RuntimeError("E10V final P1 rows differ")

    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("E10V world-model policy resolves differently")
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
        raise RuntimeError("E10V sequence-cache lineage differs")
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
    if (
        len(np.unique(selected_rows)) != CONTEXT_COUNT
        or np.any(selected_rows < 0)
        or np.any(selected_rows >= len(role))
    ):
        raise RuntimeError("E10V selected rows are invalid")
    if np.any(role[selected_rows] != 1):
        raise RuntimeError("E10V selected a non-validation row")

    payload = vp_payloads["vp_true"]
    latent_mean = torch.as_tensor(payload["latent_mean"], device=device)
    latent_std = torch.as_tensor(payload["latent_std"], device=device)
    action_mean = torch.as_tensor(payload["action_mean"], device=device)
    action_std = torch.as_tensor(payload["action_std"], device=device)
    robust_low = torch.as_tensor(payload["robust_low"], device=device)
    robust_high = torch.as_tensor(payload["robust_high"], device=device)
    normalized_low = ((robust_low - action_mean) / action_std).reshape(1, 1, 1, -1)
    normalized_high = (
        (robust_high - action_mean) / action_std
    ).reshape(1, 1, 1, -1)
    schedule = CosineDiffusionSchedule.build(100)

    first_row = int(selected_rows[0])
    first_raw = torch.from_numpy(latents[source_index[first_row]])[None].to(device)
    first_goal_raw = torch.from_numpy(latents[goal_index[first_row]])[None].to(device)
    first_current = (first_raw - latent_mean) / latent_std
    first_goal = (first_goal_raw - latent_mean) / latent_std
    test_seed = derived_seed(
        f"gdp-e10v-noise|task={args.task}|row={first_row}|k=10|seed=6101"
    )
    test_arguments = {
        "current": first_current,
        "goal": first_goal,
        "count": CANDIDATE_COUNT,
        "inference_steps": 10,
        "schedule": schedule,
        "guidance_scale": 2.0,
        "clip_low": normalized_low.flatten(),
        "clip_high": normalized_high.flatten(),
    }
    first_bank = velocity_ddim_sample(
        vp_models["vp_true"],
        generator=torch.Generator(device=device).manual_seed(test_seed),
        **test_arguments,
    )
    repeat_bank = velocity_ddim_sample(
        vp_models["vp_true"],
        generator=torch.Generator(device=device).manual_seed(test_seed),
        **test_arguments,
    )
    if not torch.equal(first_bank, repeat_bank) or not torch.isfinite(first_bank).all():
        raise RuntimeError("E10V deterministic pure-sampling preflight failed")
    equivalence = e7.real_stack_equivalence(
        world_model,
        dataset=args.dataset,
        global_row=int(global_rows[source_index[first_row]]),
        cached_current=first_raw,
        action_dim=int(spec["macro_action_dim"]),
        device=device,
        seed=derived_seed(f"gdp-e10v-equivalence|{args.task}"),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "per-context.jsonl"
    collected: dict[str, list[dict[str, float]]] = {}
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)

    def record_bank(
        *,
        stream: Any,
        row: int,
        ordinal: int,
        label: str,
        normalized: torch.Tensor,
        planner: torch.Tensor,
        current_raw: torch.Tensor,
        goal_raw: torch.Tensor,
        reference: torch.Tensor,
        generation_seconds: float,
    ) -> None:
        torch.cuda.synchronize()
        rollout_started = time.perf_counter()
        metrics = e8.metric_record(
            world_model,
            current_raw=current_raw,
            goal_raw=goal_raw,
            candidates_primitive=planner,
            candidates_normalized=normalized,
            reference_primitive=reference,
            base_primitive=planner,
            normalized_low=normalized_low,
            normalized_high=normalized_high,
        )
        torch.cuda.synchronize()
        metrics["generation_seconds"] = generation_seconds
        metrics["rollout_seconds"] = time.perf_counter() - rollout_started
        collected.setdefault(label, []).append(metrics)
        stream.write(
            json.dumps(
                {"row": row, "ordinal": ordinal, "label": label, **metrics},
                sort_keys=True,
            )
            + "\n"
        )

    with detail_path.open("x", encoding="utf-8") as stream:
        for ordinal, row in enumerate(selected_rows.tolist()):
            current_raw = torch.from_numpy(latents[source_index[row]])[None].to(device)
            goal_raw = torch.from_numpy(latents[goal_index[row]])[None].to(device)
            current = (current_raw - latent_mean) / latent_std
            goal = (goal_raw - latent_mean) / latent_std
            reference = torch.from_numpy(actions[row])[None].to(device)

            for steps in REVERSE_STEPS:
                noise_seed = derived_seed(
                    f"gdp-e10v-noise|task={args.task}|row={row}|k={steps}|seed=6101"
                )
                for condition in VP_CONDITIONS:
                    for scale in GUIDANCE_SCALES:
                        torch.cuda.synchronize()
                        generation_started = time.perf_counter()
                        normalized = velocity_ddim_sample(
                            vp_models[condition],
                            current=current,
                            goal=goal,
                            count=CANDIDATE_COUNT,
                            inference_steps=steps,
                            schedule=schedule,
                            generator=torch.Generator(device=device).manual_seed(
                                noise_seed
                            ),
                            guidance_scale=scale,
                            clip_low=normalized_low.flatten(),
                            clip_high=normalized_high.flatten(),
                        )
                        planner = e8.planner_coordinates(
                            normalized,
                            action_mean=action_mean,
                            action_std=action_std,
                            robust_low=robust_low,
                            robust_high=robust_high,
                        )
                        torch.cuda.synchronize()
                        generation_seconds = time.perf_counter() - generation_started
                        label = f"{condition}_k{steps:02d}_{scale_label(scale)}"
                        record_bank(
                            stream=stream,
                            row=row,
                            ordinal=ordinal,
                            label=label,
                            normalized=normalized,
                            planner=planner,
                            current_raw=current_raw,
                            goal_raw=goal_raw,
                            reference=reference,
                            generation_seconds=generation_seconds,
                        )

            old_noise_seed = derived_seed(
                f"gdp-e10v-old-epsilon|task={args.task}|row={row}|k=10|seed=6101"
            )
            for condition in ("diffusion_true", "diffusion_shuffled_goal"):
                torch.cuda.synchronize()
                generation_started = time.perf_counter()
                planner = e7.planner_samples(
                    e7_models[condition],
                    e7_payloads[condition],
                    current=current,
                    goal=goal,
                    count=CANDIDATE_COUNT,
                    generator=torch.Generator(device=device).manual_seed(
                        old_noise_seed
                    ),
                    ddim_steps=10,
                )
                normalized = normalized_from_planner(
                    planner,
                    action_mean=action_mean,
                    action_std=action_std,
                    robust_low=robust_low,
                    robust_high=robust_high,
                )
                torch.cuda.synchronize()
                generation_seconds = time.perf_counter() - generation_started
                label = f"epsilon_{'true' if condition == 'diffusion_true' else 'shuffled'}_k10"
                record_bank(
                    stream=stream,
                    row=row,
                    ordinal=ordinal,
                    label=label,
                    normalized=normalized,
                    planner=planner,
                    current_raw=current_raw,
                    goal_raw=goal_raw,
                    reference=reference,
                    generation_seconds=generation_seconds,
                )

            gaussian_seed = derived_seed(
                f"gdp-e10v-gaussian|task={args.task}|row={row}|seed=6101"
            )
            torch.cuda.synchronize()
            generation_started = time.perf_counter()
            gaussian_planner = e7.planner_samples(
                e7_models["gaussian_true"],
                e7_payloads["gaussian_true"],
                current=current,
                goal=goal,
                count=CANDIDATE_COUNT,
                generator=torch.Generator(device=device).manual_seed(gaussian_seed),
                ddim_steps=None,
            )
            gaussian_normalized = normalized_from_planner(
                gaussian_planner,
                action_mean=action_mean,
                action_std=action_std,
                robust_low=robust_low,
                robust_high=robust_high,
            )
            torch.cuda.synchronize()
            gaussian_seconds = time.perf_counter() - generation_started
            record_bank(
                stream=stream,
                row=row,
                ordinal=ordinal,
                label="gaussian_true",
                normalized=gaussian_normalized,
                planner=gaussian_planner,
                current_raw=current_raw,
                goal_raw=goal_raw,
                reference=reference,
                generation_seconds=gaussian_seconds,
            )
            stream.flush()

    medians = {
        label: {
            key: float(np.median([record[key] for record in records]))
            for key in records[0]
        }
        for label, records in collected.items()
    }
    normalization = {
        key: {
            "shape": list(value.shape),
            "sha256": array_sha256(value.detach().cpu().float()),
        }
        for key, value in (
            ("latent_mean", latent_mean),
            ("latent_std", latent_std),
            ("action_mean", action_mean),
            ("action_std", action_std),
            ("robust_low", robust_low),
            ("robust_high", robust_high),
            ("normalized_low", normalized_low),
            ("normalized_high", normalized_high),
        )
    }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e10v_p1_velocity_task_evaluation",
        "analysis_role": "post_E8D_P1_only_pure_diffusion_development",
        "task": args.task,
        "context_count": CONTEXT_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "reverse_steps": list(REVERSE_STEPS),
        "guidance_scales": list(GUIDANCE_SCALES),
        "per_task_medians": medians,
        "final_rows_sha256": array_sha256(selected_rows),
        "row_selection": vp_payloads["vp_true"]["row_selection"],
        "determinism_preflight": {
            "status": "ok",
            "repeat_max_abs": float((first_bank - repeat_bank).abs().max().cpu()),
        },
        "real_stack_equivalence": equivalence,
        "normalization": normalization,
        "cosine_alpha_bar_sha256": array_sha256(schedule.alpha_bar),
        "velocity_models": vp_records,
        "e7_controls": e7_records,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "latent_h5_sha256": sha256_file(args.latent_h5),
        "sequence_h5_sha256": sha256_file(args.sequence_h5),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "per_context": str(detail_path),
        "per_context_sha256": sha256_file(detail_path),
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
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        },
        "rng_namespaces": {
            "velocity_noise": (
                f"gdp-e10v-noise|task={args.task}|row={{row}}|k={{steps}}|seed=6101"
            ),
            "old_epsilon_noise": (
                f"gdp-e10v-old-epsilon|task={args.task}|row={{row}}|k=10|seed=6101"
            ),
            "gaussian_noise": (
                f"gdp-e10v-gaussian|task={args.task}|row={{row}}|seed=6101"
            ),
            "derivation": "first_64_sha256_bits_little_endian_mod_2^63_minus_1",
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
