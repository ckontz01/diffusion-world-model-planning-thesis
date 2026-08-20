#!/usr/bin/env python3
"""Evaluate the fixed E10V configuration across three model seeds on fresh P1."""

from __future__ import annotations

import argparse
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
import evaluate_gdp_cem_e8a_refinement as e8
import evaluate_gdp_cem_e10v_p1 as e10v_eval
import train_gdp_cem_e10m_models as train
from acid_alternative.io_utils import atomic_write_json, resolve_policy_checkpoint
from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    CosineDiffusionSchedule,
    VelocityActionDiffusion,
    load_proposal_model,
    velocity_ddim_sample,
)


TASKS = train.TASKS
SEEDS = (6101, 6102, 6103)
CONDITIONS = train.CONDITIONS
CONTEXT_COUNT = 1_024
CANDIDATE_COUNT = 300
REVERSE_EVALUATIONS = 5
GUIDANCE_SCALE = 1.5
PROTOCOL_SHA256 = "02606573e4c7e4341814c76974ff2020f35fedcf2e8d1d08e531dd553e9787b9"
E10V_AGGREGATE_SHA256 = (
    "5d23323681904fe369afcb4796976782cd6e4068b90fbc0e0d163e35092bacd9"
)
E10V_SOURCE_MANIFEST_SHA256 = (
    "b843a68dda3355499cada1d580853654efa404bc5f5d2375fbee14b4121e3e5d"
)


def load_new_checkpoint(
    summary_path: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    source_manifest_sha256: str,
    device: torch.device,
) -> tuple[torch.nn.Module, dict[str, Any], dict[str, Any]]:
    train.e10v.reject_protected_path(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected_kind = "gaussian" if condition == "gaussian_true" else "velocity_diffusion"
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e10m_p1_model_training"
        or summary.get("analysis_role") != "fixed_configuration_multiseed_P1_replication"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or summary.get("seed") != seed
        or summary.get("proposal_kind") != expected_kind
        or summary.get("prediction_type")
        != ("velocity" if expected_kind == "velocity_diffusion" else None)
        or summary.get("protocol_sha256") != PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_manifest_sha256
        or summary.get("d2_read") is not False
        or summary.get("d3_read") is not False
        or summary.get("protected_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError("E10M training summary differs")
    checkpoint = Path(summary.get("checkpoint", ""))
    train.e10v.reject_protected_path(checkpoint)
    if not checkpoint.is_file() or train.e10v.sha256_file(checkpoint) != summary.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError("E10M checkpoint hash differs")
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
        payload.get("kind") != "gdp_cem_e10m_p1_model_checkpoint"
        or payload.get("proposal_kind") != expected_kind
        or payload.get("condition") != condition
        or payload.get("task") != task
        or payload.get("seed") != seed
        or payload.get("model_config") != expected_config
        or payload.get("protocol_sha256") != PROTOCOL_SHA256
        or payload.get("source_manifest_sha256") != source_manifest_sha256
        or summary.get("model_config") != expected_config
        or summary.get("row_selection") != payload.get("row_selection")
        or (
            expected_kind == "velocity_diffusion"
            and (
                payload.get("prediction_type") != "velocity"
                or payload.get("diffusion_steps") != 100
                or payload.get("condition_dropout") != 0.15
            )
        )
        or (
            expected_kind == "gaussian"
            and (
                payload.get("prediction_type") is not None
                or payload.get("diffusion_steps") is not None
                or payload.get("condition_dropout") is not None
            )
        )
    ):
        raise RuntimeError("E10M checkpoint identity differs")
    model = load_proposal_model(payload, device=device)
    expected_class = (
        ConditionalDiagonalGaussian
        if expected_kind == "gaussian"
        else VelocityActionDiffusion
    )
    if not isinstance(model, expected_class):
        raise RuntimeError("E10M checkpoint model class differs")
    if sum(parameter.numel() for parameter in model.parameters()) != int(
        summary["parameter_count"]
    ):
        raise RuntimeError("E10M parameter count differs")
    return model, payload, {
        "summary": str(summary_path),
        "summary_sha256": train.e10v.sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "best_step": summary["best_step"],
        "best_validation": summary["best_validation"],
        "parameter_count": summary["parameter_count"],
    }


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
    parser.add_argument("--seed1-vp-summary", nargs=2, action="append", required=True)
    parser.add_argument("--seed1-gaussian-summary", type=Path, required=True)
    parser.add_argument("--new-summary", nargs=3, action="append", required=True)
    parser.add_argument("--e10v-aggregate", type=Path, required=True)
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
        args.seed1_gaussian_summary,
        args.e10v_aggregate,
        args.protocol,
        args.source_manifest,
    )
    for path in (*required, args.output_dir):
        train.e10v.reject_protected_path(path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if train.e10v.sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E10M protocol hash differs")
    if train.e10v.sha256_file(args.e10v_aggregate) != E10V_AGGREGATE_SHA256:
        raise RuntimeError("E10M E10V aggregate hash differs")
    prerequisite = json.loads(args.e10v_aggregate.read_text(encoding="utf-8"))
    selected = prerequisite.get("selected_configuration", {})
    if (
        prerequisite.get("decision")
        != "authorize_separately_frozen_multiseed_p1_velocity_replication"
        or prerequisite.get("eligible_configuration_count") != 1
        or selected.get("reverse_evaluations") != REVERSE_EVALUATIONS
        or selected.get("guidance_scale") != GUIDANCE_SCALE
        or selected.get("labels", {}).get("true") != "vp_true_k05_g015"
        or not all(selected.get("gates", {}).values())
        or prerequisite.get("d2_read") is not False
        or prerequisite.get("d3_read") is not False
    ):
        raise RuntimeError("E10M E10V prerequisite decision differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E10M evaluation output")
    source_hash = train.e10v.sha256_file(args.source_manifest)

    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("E10M evaluation requires CUDA")
    torch.manual_seed(2026081708)
    torch.cuda.manual_seed_all(2026081708)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)

    models: dict[int, dict[str, torch.nn.Module]] = {seed: {} for seed in SEEDS}
    payloads: dict[int, dict[str, dict[str, Any]]] = {seed: {} for seed in SEEDS}
    records: dict[int, dict[str, dict[str, Any]]] = {seed: {} for seed in SEEDS}
    seed1_paths = {condition: Path(path) for condition, path in args.seed1_vp_summary}
    if set(seed1_paths) != {"vp_true", "vp_shuffled_goal"}:
        raise RuntimeError("E10M seed-6101 velocity summaries differ")
    for condition in ("vp_true", "vp_shuffled_goal"):
        train.e10v.reject_protected_path(seed1_paths[condition])
        models[6101][condition], payloads[6101][condition], records[6101][condition] = (
            e10v_eval.load_vp_checkpoint(
                seed1_paths[condition],
                task=args.task,
                condition=condition,
                source_manifest_sha256=E10V_SOURCE_MANIFEST_SHA256,
                device=device,
            )
        )
    seed1_gaussian, seed1_payload, seed1_record = e7.load_checkpoint(
        args.seed1_gaussian_summary,
        task=args.task,
        condition="gaussian_true",
        device=device,
    )
    models[6101]["gaussian_true"] = seed1_gaussian
    payloads[6101]["gaussian_true"] = seed1_payload
    records[6101]["gaussian_true"] = seed1_record

    new_paths = {
        (int(seed), condition): Path(path)
        for seed, condition, path in args.new_summary
    }
    expected_new = {
        (seed, condition)
        for seed in (6102, 6103)
        for condition in CONDITIONS
    }
    if set(new_paths) != expected_new or len(args.new_summary) != len(expected_new):
        raise RuntimeError("E10M new model-summary grid differs")
    for seed, condition in sorted(expected_new):
        models[seed][condition], payloads[seed][condition], records[seed][condition] = (
            load_new_checkpoint(
                new_paths[(seed, condition)],
                task=args.task,
                condition=condition,
                seed=seed,
                source_manifest_sha256=source_hash,
                device=device,
            )
        )

    reference_payload = payloads[6101]["vp_true"]
    for key in (
        "latent_mean",
        "latent_std",
        "action_mean",
        "action_std",
        "robust_low",
        "robust_high",
    ):
        reference = torch.as_tensor(reference_payload[key]).float()
        if any(
            not torch.equal(reference, torch.as_tensor(payloads[seed][condition][key]).float())
            for seed in SEEDS
            for condition in CONDITIONS
        ):
            raise RuntimeError(f"E10M model statistic differs: {key}")
    row_selection = payloads[6102]["vp_true"]["row_selection"]
    if any(
        payloads[seed][condition].get("row_selection") != row_selection
        for seed in (6102, 6103)
        for condition in CONDITIONS
    ):
        raise RuntimeError("E10M row-selection record differs")
    confirmation_rows = torch.as_tensor(
        payloads[6102]["vp_true"]["confirmation_rows"], dtype=torch.int64
    ).numpy()
    if (
        confirmation_rows.shape != (CONTEXT_COUNT,)
        or train.e10v.array_sha256(confirmation_rows)
        != row_selection["confirmation_rows_sha256"]
        or any(
            not torch.equal(
                torch.as_tensor(payloads[seed][condition]["confirmation_rows"]),
                torch.as_tensor(confirmation_rows),
            )
            for seed in (6102, 6103)
            for condition in CONDITIONS
        )
    ):
        raise RuntimeError("E10M confirmation rows differ")

    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("E10M world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    sequence_manifest = json.loads(args.sequence_manifest.read_text(encoding="utf-8"))
    spec = e7.TASK_SPEC[args.task]
    if (
        train.e10v.sha256_file(args.sequence_manifest)
        != spec["sequence_manifest_sha256"]
        or sequence_manifest.get("output_h5_sha256")
        != train.e10v.sha256_file(args.sequence_h5)
        or sequence_manifest.get("output_h5_sha256") != spec["sequence_h5_sha256"]
        or sequence_manifest.get("latent_h5_sha256")
        != train.e10v.sha256_file(args.latent_h5)
        or sequence_manifest.get("latent_h5_sha256") != spec["latent_h5_sha256"]
        or sequence_manifest.get("d2_read") is not False
        or sequence_manifest.get("d3_read") is not False
        or sequence_manifest.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E10M cache lineage differs")
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
        len(np.unique(confirmation_rows)) != CONTEXT_COUNT
        or np.any(confirmation_rows < 0)
        or np.any(confirmation_rows >= len(role))
        or np.any(role[confirmation_rows] != 1)
    ):
        raise RuntimeError("E10M confirmation rows are invalid")

    latent_mean = torch.as_tensor(reference_payload["latent_mean"], device=device)
    latent_std = torch.as_tensor(reference_payload["latent_std"], device=device)
    action_mean = torch.as_tensor(reference_payload["action_mean"], device=device)
    action_std = torch.as_tensor(reference_payload["action_std"], device=device)
    robust_low = torch.as_tensor(reference_payload["robust_low"], device=device)
    robust_high = torch.as_tensor(reference_payload["robust_high"], device=device)
    normalized_low = ((robust_low - action_mean) / action_std).reshape(1, 1, 1, -1)
    normalized_high = ((robust_high - action_mean) / action_std).reshape(1, 1, 1, -1)
    schedule = CosineDiffusionSchedule.build(100)

    first_row = int(confirmation_rows[0])
    first_raw = torch.from_numpy(latents[source_index[first_row]])[None].to(device)
    first_goal_raw = torch.from_numpy(latents[goal_index[first_row]])[None].to(device)
    first_current = (first_raw - latent_mean) / latent_std
    first_goal = (first_goal_raw - latent_mean) / latent_std
    first_seed = e10v_eval.derived_seed(
        f"gdp-e10m-velocity|task={args.task}|model=6101|row={first_row}|seed=2026081708"
    )
    first_bank = velocity_ddim_sample(
        models[6101]["vp_true"],
        current=first_current,
        goal=first_goal,
        count=CANDIDATE_COUNT,
        inference_steps=REVERSE_EVALUATIONS,
        schedule=schedule,
        generator=torch.Generator(device=device).manual_seed(first_seed),
        guidance_scale=GUIDANCE_SCALE,
        clip_low=normalized_low.flatten(),
        clip_high=normalized_high.flatten(),
    )
    repeat_bank = velocity_ddim_sample(
        models[6101]["vp_true"],
        current=first_current,
        goal=first_goal,
        count=CANDIDATE_COUNT,
        inference_steps=REVERSE_EVALUATIONS,
        schedule=schedule,
        generator=torch.Generator(device=device).manual_seed(first_seed),
        guidance_scale=GUIDANCE_SCALE,
        clip_low=normalized_low.flatten(),
        clip_high=normalized_high.flatten(),
    )
    if not torch.equal(first_bank, repeat_bank):
        raise RuntimeError("E10M deterministic sampling preflight differs")
    equivalence = e7.real_stack_equivalence(
        world_model,
        dataset=args.dataset,
        global_row=int(global_rows[source_index[first_row]]),
        cached_current=first_raw,
        action_dim=int(spec["macro_action_dim"]),
        device=device,
        seed=e10v_eval.derived_seed(f"gdp-e10m-equivalence|{args.task}"),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "per-context.jsonl"
    collected: dict[str, list[dict[str, float]]] = {}
    started = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    with detail_path.open("x", encoding="utf-8") as stream:
        for ordinal, row in enumerate(confirmation_rows.tolist()):
            current_raw = torch.from_numpy(latents[source_index[row]])[None].to(device)
            goal_raw = torch.from_numpy(latents[goal_index[row]])[None].to(device)
            current = (current_raw - latent_mean) / latent_std
            goal = (goal_raw - latent_mean) / latent_std
            reference = torch.from_numpy(actions[row])[None].to(device)
            for seed in SEEDS:
                noise_seed = e10v_eval.derived_seed(
                    f"gdp-e10m-velocity|task={args.task}|model={seed}|row={row}|seed=2026081708"
                )
                for condition, scale in (
                    ("vp_true", GUIDANCE_SCALE),
                    ("vp_shuffled_goal", GUIDANCE_SCALE),
                    ("vp_true_unconditional", 0.0),
                ):
                    model_condition = "vp_true" if condition == "vp_true_unconditional" else condition
                    model = models[seed][model_condition]
                    assert isinstance(model, VelocityActionDiffusion)
                    torch.cuda.synchronize()
                    generation_started = time.perf_counter()
                    normalized = velocity_ddim_sample(
                        model,
                        current=current,
                        goal=goal,
                        count=CANDIDATE_COUNT,
                        inference_steps=REVERSE_EVALUATIONS,
                        schedule=schedule,
                        generator=torch.Generator(device=device).manual_seed(noise_seed),
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
                    label = f"seed{seed}_{condition}"
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
                    stream.write(json.dumps({"row": row, "ordinal": ordinal, "label": label, **metrics}, sort_keys=True) + "\n")

                gaussian = models[seed]["gaussian_true"]
                assert isinstance(gaussian, ConditionalDiagonalGaussian)
                gaussian_seed = e10v_eval.derived_seed(
                    f"gdp-e10m-gaussian|task={args.task}|model={seed}|row={row}|seed=2026081708"
                )
                torch.cuda.synchronize()
                generation_started = time.perf_counter()
                gaussian_planner = e7.planner_samples(
                    gaussian,
                    payloads[seed]["gaussian_true"],
                    current=current,
                    goal=goal,
                    count=CANDIDATE_COUNT,
                    generator=torch.Generator(device=device).manual_seed(gaussian_seed),
                    ddim_steps=None,
                )
                gaussian_normalized = e10v_eval.normalized_from_planner(
                    gaussian_planner,
                    action_mean=action_mean,
                    action_std=action_std,
                    robust_low=robust_low,
                    robust_high=robust_high,
                )
                torch.cuda.synchronize()
                generation_seconds = time.perf_counter() - generation_started
                rollout_started = time.perf_counter()
                metrics = e8.metric_record(
                    world_model,
                    current_raw=current_raw,
                    goal_raw=goal_raw,
                    candidates_primitive=gaussian_planner,
                    candidates_normalized=gaussian_normalized,
                    reference_primitive=reference,
                    base_primitive=gaussian_planner,
                    normalized_low=normalized_low,
                    normalized_high=normalized_high,
                )
                torch.cuda.synchronize()
                metrics["generation_seconds"] = generation_seconds
                metrics["rollout_seconds"] = time.perf_counter() - rollout_started
                label = f"seed{seed}_gaussian_true"
                collected.setdefault(label, []).append(metrics)
                stream.write(json.dumps({"row": row, "ordinal": ordinal, "label": label, **metrics}, sort_keys=True) + "\n")
            stream.flush()

    medians = {
        label: {
            key: float(np.median([record[key] for record in rows]))
            for key in rows[0]
        }
        for label, rows in collected.items()
    }
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e10m_p1_multiseed_task_evaluation",
        "analysis_role": "fixed_configuration_multiseed_P1_replication",
        "task": args.task,
        "model_seeds": list(SEEDS),
        "context_count": CONTEXT_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "reverse_evaluations": REVERSE_EVALUATIONS,
        "guidance_scale": GUIDANCE_SCALE,
        "per_task_medians": medians,
        "confirmation_rows_sha256": train.e10v.array_sha256(confirmation_rows),
        "row_selection": row_selection,
        "determinism_preflight": {
            "status": "ok",
            "repeat_max_abs": float((first_bank - repeat_bank).abs().max().cpu()),
        },
        "real_stack_equivalence": equivalence,
        "models": {str(seed): records[seed] for seed in SEEDS},
        "e10v_aggregate_sha256": E10V_AGGREGATE_SHA256,
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": train.e10v.sha256_file(args.world_model_checkpoint),
        "latent_h5_sha256": train.e10v.sha256_file(args.latent_h5),
        "sequence_h5_sha256": train.e10v.sha256_file(args.sequence_h5),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "per_context": str(detail_path),
        "per_context_sha256": train.e10v.sha256_file(detail_path),
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
