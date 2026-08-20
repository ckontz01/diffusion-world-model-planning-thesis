#!/usr/bin/env python3
"""Score frozen E4 and strengthened controls on one exposed D2 candidate set."""

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
import torch
from torch import nn

import acid_alt_d2_models as d2
import score_acid_alt_d2_task as legacy
from acid_alt_e4_controls import (
    ConditionalGaussianInverse,
    DeterministicInverseRegressor,
    deterministic_inverse_costs,
    gaussian_inverse_costs,
)
from acid_alt_e4_scoring import (
    E4_P1_PROTOCOL_SHA256,
    NOISE_DRAWS,
    SCORING_SIGMAS,
    acid_flow_training_energy,
    acid_multisample_costs,
    build_acid_sample_noise_bank,
    build_action_noise_bank,
    inverse_diffusion_costs,
    load_e4_model,
    sha256_file,
)


TASKS = ("pusht", "reacher", "cube")
POOL_COUNT = 50
CANDIDATE_COUNT = 300
PLANNER_SEED = 8201
PRIMARY_E4_SEED = 7101
PRIMARY_ACID_SEED = 6101
ACID_SAMPLE_DRAWS = 16
P1_SOURCE_MANIFEST_SHA256 = (
    "e2c8231048e84f52b141d639d4b96fba135e4b66a25ffaf4ad2a79d20cc13fbf"
)
IMPLEMENTATION_FREEZE_SHA256 = (
    "193f5679ec91377c0d2411b9092cc4d2c8308d64f509917244d1b89dcb7354b9"
)


def parse_seeded(values: list[str], label: str) -> dict[int, Path]:
    return legacy.parse_seeded(values, label)


def validate_p1_gate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind") != "e4_p1_mechanism_gate"
        or value.get("analysis_role") != "P1-only post-E3 exploratory development"
        or value.get("all_e4_p1_gates_pass") is not True
        or value.get("decision") != "advance_to_e4_d2a_exposed_candidate_audit"
        or value.get("protocol_sha256") != E4_P1_PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != P1_SOURCE_MANIFEST_SHA256
        or value.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E4-P1 gate does not authorize D2A")
    if set(value.get("tasks", {})) != set(TASKS) or not all(
        value["tasks"][task].get("pass") is True for task in TASKS
    ):
        raise RuntimeError("E4-P1 task gate is incomplete")
    return value


def load_control(
    summary_path: Path,
    *,
    task: str,
    model_kind: str,
    source_manifest_sha256: str,
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], dict[str, float] | None, dict[str, Any]]:
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required = {
        "status": "ok",
        "kind": "e4_capacity_matched_inverse_control_training",
        "task": task,
        "condition": "true_successor",
        "model": model_kind,
        "seed": PRIMARY_E4_SEED,
        "protocol_sha256": E4_P1_PROTOCOL_SHA256,
        "source_manifest_sha256": source_manifest_sha256,
        "protected_c1_i1_read": False,
        "confirmation_data_read": False,
    }
    for key, expected in required.items():
        if summary.get(key) != expected:
            raise RuntimeError(
                f"{model_kind} control {key}={summary.get(key)!r}, expected {expected!r}"
            )
    if summary.get("best_selection_validation") != summary.get(
        "replayed_selection_validation"
    ):
        raise RuntimeError(f"{model_kind} control checkpoint replay mismatch")
    checkpoint = Path(summary["checkpoint"])
    if not checkpoint.is_file() or sha256_file(checkpoint) != summary.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError(f"{model_kind} control checkpoint hash mismatch")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    config = payload.get("model_config", {})
    if (
        payload.get("task") != task
        or payload.get("condition") != "true_successor"
        or payload.get("seed") != PRIMARY_E4_SEED
        or payload.get("source_manifest_sha256") != source_manifest_sha256
        or payload.get("protocol_sha256") != E4_P1_PROTOCOL_SHA256
    ):
        raise RuntimeError(f"{model_kind} checkpoint identity mismatch")
    if model_kind == "deterministic":
        expected_name = "e4_deterministic_inverse_control"
        model: nn.Module = DeterministicInverseRegressor(
            int(config["latent_dim"]),
            int(config["action_dim"]),
            width=int(config["width"]),
            depth=int(config["depth"]),
        )
        calibration = None
    elif model_kind == "gaussian":
        expected_name = "e4_gaussian_inverse_control"
        model = ConditionalGaussianInverse(
            int(config["latent_dim"]),
            int(config["action_dim"]),
            width=int(config["width"]),
            depth=int(config["depth"]),
            minimum_log_scale=float(config["minimum_log_scale"]),
            maximum_log_scale=float(config["maximum_log_scale"]),
        )
        calibration_path = Path(summary["calibration"])
        if not calibration_path.is_file() or sha256_file(
            calibration_path
        ) != summary.get("calibration_sha256"):
            raise RuntimeError("Gaussian control calibration hash mismatch")
        calibration_record = json.loads(calibration_path.read_text(encoding="utf-8"))
        if (
            calibration_record.get("status") != "ok"
            or calibration_record.get("role")
            != "P1_validation_Gaussian_inverse_ratio_calibration"
            or calibration_record.get("task") != task
            or calibration_record.get("seed") != PRIMARY_E4_SEED
            or calibration_record.get("protected_c1_i1_read") is not False
        ):
            raise RuntimeError("Gaussian control calibration identity mismatch")
        calibration = {
            key: float(calibration_record[key])
            for key in ("ratio_q50", "ratio_q95", "ratio_q99")
        }
    else:
        raise ValueError(model_kind)
    if payload.get("model_name") != expected_name or config.get("name") != expected_name:
        raise RuntimeError(f"{model_kind} checkpoint model name mismatch")
    model.load_state_dict(payload["state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != int(summary["parameter_count"]):
        raise RuntimeError(f"{model_kind} parameter count mismatch")
    return model, payload, calibration, {
        "arm": f"{model_kind}_inverse",
        "seed": PRIMARY_E4_SEED,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "parameter_count": parameter_count,
        "model_config": config,
    }


def add_latency(
    record: dict[str, Any],
    elapsed: float,
    *,
    outputs: list[str],
    network_pairs_per_sequence: int,
    batch_size: int,
) -> None:
    record["latency"] = legacy.latency_profile(
        elapsed,
        batch_size=batch_size,
        outputs=outputs,
        network_pairs_per_sequence=network_pairs_per_sequence,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--parent-protocol", type=Path, required=True)
    parser.add_argument("--implementation-freeze", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--p1-gate", type=Path, required=True)
    parser.add_argument("--legacy-d2-manifest", type=Path, required=True)
    parser.add_argument("--legacy-d2-provenance", type=Path, required=True)
    parser.add_argument("--shared-scores", type=Path, required=True)
    parser.add_argument("--shared-score-manifest", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--e4-true-summary", type=Path, required=True)
    parser.add_argument("--e4-shuffled-summary", type=Path, required=True)
    parser.add_argument("--deterministic-summary", type=Path, required=True)
    parser.add_argument("--gaussian-summary", type=Path, required=True)
    parser.add_argument("--acid", action="append", default=[])
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    started = time.time()
    for path in (
        args.parent_protocol,
        args.implementation_freeze,
        args.source_manifest,
        args.p1_gate,
        args.legacy_d2_manifest,
        args.legacy_d2_provenance,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.parent_protocol) != E4_P1_PROTOCOL_SHA256:
        raise RuntimeError("E4 parent protocol hash mismatch")
    if sha256_file(args.implementation_freeze) != IMPLEMENTATION_FREEZE_SHA256:
        raise RuntimeError("E4-D2A implementation-freeze hash mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E4-D2A output directory")
    if args.batch_size <= 0 or not torch.cuda.is_available():
        raise RuntimeError("positive batch size and CUDA are required")
    validate_p1_gate(args.p1_gate)
    acid_paths = parse_seeded(args.acid, "ACID")
    source_manifest_sha256 = sha256_file(args.source_manifest)

    artifact, score_manifest, execution_manifest = legacy.validate_upstream(
        task=args.task,
        score_path=args.shared_scores,
        score_manifest_path=args.shared_score_manifest,
        execution_path=args.execution,
        execution_manifest_path=args.execution_manifest,
    )
    d2_provenance = legacy.validate_d2_identity(
        task=args.task,
        manifest_path=args.legacy_d2_manifest,
        provenance_path=args.legacy_d2_provenance,
        expected_source_sha256=d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256,
    )
    if (
        score_manifest.get("source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or score_manifest.get("eval_manifest_sha256")
        != sha256_file(args.legacy_d2_manifest)
        or score_manifest.get("dataset_sha256") != d2_provenance.get("dataset_sha256")
    ):
        raise RuntimeError("upstream D2 artifact lineage mismatch")

    trajectory = torch.as_tensor(artifact["predicted_trajectory"]).float()
    candidates = torch.as_tensor(artifact["candidates"]).float()
    goal_embedding = torch.as_tensor(artifact["goal_embedding"]).float()
    goal = torch.as_tensor(artifact["scores"]["b0"]["raw_verifier_cost"]).double()
    if trajectory.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("predicted-trajectory pool shape differs")
    if candidates.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("candidate pool shape differs")
    if goal.shape != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("goal-cost shape differs")
    with h5py.File(args.execution, "r") as handle:
        executed = np.asarray(handle["executed_latent"][:], dtype=np.float32)
        success = np.asarray(handle["environment_success"][:], dtype=bool)
        final_distance = (
            np.asarray(handle["final_task_distance"][:], dtype=np.float64)
            if "final_task_distance" in handle
            else np.empty((0,), dtype=np.float64)
        )
        minimum_distance = (
            np.asarray(handle["minimum_task_distance"][:], dtype=np.float64)
            if "minimum_task_distance" in handle
            else np.empty((0,), dtype=np.float64)
        )
    if executed.shape != tuple(trajectory.shape) or success.shape != tuple(goal.shape):
        raise RuntimeError("physical execution shape differs")
    latent_std = torch.as_tensor(artifact["transition_latent_std"]).float().numpy()
    standardized_rmse = np.sqrt(
        np.mean(
            np.square((trajectory.numpy()[:, :, 1:] - executed[:, :, 1:]) / latent_std),
            axis=(2, 3),
        )
    )
    if not np.isfinite(standardized_rmse).all():
        raise RuntimeError("physical rollout RMSE is non-finite")

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    trajectory_cuda = trajectory.to(device)
    candidates_cuda = candidates.to(device)
    goal_embedding_cuda = goal_embedding.to(device)
    arrays: dict[str, np.ndarray] = {
        "goal": goal.numpy(),
        "standardized_rmse": standardized_rmse,
        "success": success.astype(np.uint8),
        "final_distance": final_distance,
        "minimum_distance": minimum_distance,
    }
    scorer_records: list[dict[str, Any]] = []

    e4_true, e4_true_payload, e4_true_calibration, e4_true_record = load_e4_model(
        args.e4_true_summary,
        task=args.task,
        expected_condition="true_successor",
        device=device,
    )
    e4_shuffled, e4_shuffled_payload, e4_shuffled_calibration, e4_shuffled_record = (
        load_e4_model(
            args.e4_shuffled_summary,
            task=args.task,
            expected_condition="shuffled_successor",
            device=device,
        )
    )
    e4_noise = build_action_noise_bank(
        task=args.task,
        scorer_seed=PRIMARY_E4_SEED,
        horizon=candidates.shape[-2],
        action_dim=candidates.shape[-1],
    ).to(device)
    inverse_diffusion_costs(
        e4_true,
        trajectory=trajectory_cuda[:1],
        actions=candidates_cuda[:1],
        payload=e4_true_payload,
        calibration=e4_true_calibration,
        noise_bank=e4_noise,
        batch_size=args.batch_size,
    )
    true_scores, true_elapsed = legacy.timed_cuda_call(
        lambda: inverse_diffusion_costs(
            e4_true,
            trajectory=trajectory_cuda,
            actions=candidates_cuda,
            payload=e4_true_payload,
            calibration=e4_true_calibration,
            noise_bank=e4_noise,
            batch_size=args.batch_size,
        )
    )
    inverse_diffusion_costs(
        e4_shuffled,
        trajectory=trajectory_cuda[:1],
        actions=candidates_cuda[:1],
        payload=e4_shuffled_payload,
        calibration=e4_shuffled_calibration,
        noise_bank=e4_noise,
        batch_size=args.batch_size,
    )
    shuffled_scores, shuffled_elapsed = legacy.timed_cuda_call(
        lambda: inverse_diffusion_costs(
            e4_shuffled,
            trajectory=trajectory_cuda,
            actions=candidates_cuda,
            payload=e4_shuffled_payload,
            calibration=e4_shuffled_calibration,
            noise_bank=e4_noise,
            batch_size=args.batch_size,
        )
    )
    for name, value in (
        ("e4_cider_tail", true_scores["cider_tail"]),
        ("e4_dide", true_scores["dide"]),
        ("e4_cider_raw", true_scores["cider"]),
        ("e4_cider_mean_violation", true_scores["cider_mean_violation"]),
        ("e4_shuffled_cider_tail_raw", shuffled_scores["cider_tail"]),
        ("e4_shuffled_dide", shuffled_scores["dide"]),
        ("e4_shuffled_cider_raw", shuffled_scores["cider"]),
    ):
        arrays[name] = value.double().cpu().numpy()
    e4_true_record.update(
        arm="e4_inverse_diffusion",
        reliability=1,
        endpoints=["CIDER-tail", "DIDE", "CIDER-raw", "CIDER-mean-violation"],
    )
    add_latency(
        e4_true_record,
        true_elapsed,
        outputs=e4_true_record["endpoints"],
        network_pairs_per_sequence=(
            5 * len(SCORING_SIGMAS) * NOISE_DRAWS * 2
        ),
        batch_size=args.batch_size,
    )
    e4_shuffled_record.update(
        arm="e4_inverse_diffusion",
        reliability=0,
        deployment_cost="exact_B0",
        endpoints=["shuffled-CIDER-tail-raw", "shuffled-DIDE", "shuffled-CIDER-raw"],
    )
    add_latency(
        e4_shuffled_record,
        shuffled_elapsed,
        outputs=e4_shuffled_record["endpoints"],
        network_pairs_per_sequence=(
            5 * len(SCORING_SIGMAS) * NOISE_DRAWS * 2
        ),
        batch_size=args.batch_size,
    )
    scorer_records.extend((e4_true_record, e4_shuffled_record))
    del e4_true, e4_shuffled, true_scores, shuffled_scores
    torch.cuda.empty_cache()

    deterministic, deterministic_payload, _, deterministic_record = load_control(
        args.deterministic_summary,
        task=args.task,
        model_kind="deterministic",
        source_manifest_sha256=source_manifest_sha256,
        device=device,
    )
    deterministic_inverse_costs(
        deterministic,
        trajectory=trajectory_cuda[:1],
        actions=candidates_cuda[:1],
        latent_mean=deterministic_payload["latent_mean"],
        latent_std=deterministic_payload["latent_std"],
        action_mean=deterministic_payload["acid_action_mean"],
        action_std=deterministic_payload["acid_action_std"],
        batch_size=args.batch_size,
    )
    deterministic_cost, deterministic_elapsed = legacy.timed_cuda_call(
        lambda: deterministic_inverse_costs(
            deterministic,
            trajectory=trajectory_cuda,
            actions=candidates_cuda,
            latent_mean=deterministic_payload["latent_mean"],
            latent_std=deterministic_payload["latent_std"],
            action_mean=deterministic_payload["acid_action_mean"],
            action_std=deterministic_payload["acid_action_std"],
            batch_size=args.batch_size,
        )
    )
    arrays["deterministic_inverse"] = deterministic_cost.double().cpu().numpy()
    deterministic_record["endpoints"] = ["deterministic-inverse"]
    add_latency(
        deterministic_record,
        deterministic_elapsed,
        outputs=deterministic_record["endpoints"],
        network_pairs_per_sequence=5,
        batch_size=args.batch_size,
    )
    scorer_records.append(deterministic_record)
    del deterministic, deterministic_cost
    torch.cuda.empty_cache()

    gaussian, gaussian_payload, gaussian_calibration, gaussian_record = load_control(
        args.gaussian_summary,
        task=args.task,
        model_kind="gaussian",
        source_manifest_sha256=source_manifest_sha256,
        device=device,
    )
    assert gaussian_calibration is not None
    gaussian_inverse_costs(
        gaussian,
        trajectory=trajectory_cuda[:1],
        actions=candidates_cuda[:1],
        latent_mean=gaussian_payload["latent_mean"],
        latent_std=gaussian_payload["latent_std"],
        action_mean=gaussian_payload["acid_action_mean"],
        action_std=gaussian_payload["acid_action_std"],
        calibration=gaussian_calibration,
        batch_size=args.batch_size,
    )
    gaussian_scores, gaussian_elapsed = legacy.timed_cuda_call(
        lambda: gaussian_inverse_costs(
            gaussian,
            trajectory=trajectory_cuda,
            actions=candidates_cuda,
            latent_mean=gaussian_payload["latent_mean"],
            latent_std=gaussian_payload["latent_std"],
            action_mean=gaussian_payload["acid_action_mean"],
            action_std=gaussian_payload["acid_action_std"],
            calibration=gaussian_calibration,
            batch_size=args.batch_size,
        )
    )
    for name, key in (
        ("gaussian_nll", "gaussian_nll"),
        ("gaussian_ratio", "gaussian_ratio"),
        ("gaussian_tail", "gaussian_tail"),
    ):
        arrays[name] = gaussian_scores[key].double().cpu().numpy()
    gaussian_record["endpoints"] = ["Gaussian-NLL", "Gaussian-ratio", "Gaussian-tail"]
    add_latency(
        gaussian_record,
        gaussian_elapsed,
        outputs=gaussian_record["endpoints"],
        network_pairs_per_sequence=10,
        batch_size=args.batch_size,
    )
    scorer_records.append(gaussian_record)
    del gaussian, gaussian_scores
    torch.cuda.empty_cache()

    forward_labels = legacy.core_index(artifact["scores"], "forward")
    reachability_labels = legacy.core_index(artifact["scores"], "reachability")
    for seed in d2.SEEDS:
        arrays[f"forward_seed_{seed}"] = np.asarray(
            artifact["scores"][forward_labels[seed]]["raw_verifier_cost"],
            dtype=np.float64,
        )
        arrays[f"reachability_seed_{seed}"] = np.asarray(
            artifact["scores"][reachability_labels[seed]]["raw_verifier_cost"],
            dtype=np.float64,
        )
    forward, forward_payload, forward_record = d2.load_core_scorer(
        Path(artifact["scores"][forward_labels[PRIMARY_ACID_SEED]]["checkpoint"]),
        arm="forward",
        expected_seed=PRIMARY_ACID_SEED,
        device=device,
    )
    d2.forward_literal_costs(
        forward,
        trajectory=trajectory_cuda[:1],
        actions=candidates_cuda[:1],
        latent_mean=forward_payload["latent_mean"],
        latent_std=forward_payload["latent_std"],
        batch_size=args.batch_size,
    )
    forward_values, forward_elapsed = legacy.timed_cuda_call(
        lambda: d2.forward_literal_costs(
            forward,
            trajectory=trajectory_cuda,
            actions=candidates_cuda,
            latent_mean=forward_payload["latent_mean"],
            latent_std=forward_payload["latent_std"],
            batch_size=args.batch_size,
        )
    )
    if not np.allclose(
        forward_values.double().cpu().numpy(),
        arrays[f"forward_seed_{PRIMARY_ACID_SEED}"],
        rtol=1.0e-6,
        atol=1.0e-6,
    ):
        raise RuntimeError("forward score replay mismatch")
    add_latency(
        forward_record,
        forward_elapsed,
        outputs=["forward"],
        network_pairs_per_sequence=5,
        batch_size=args.batch_size,
    )
    scorer_records.append(forward_record)
    del forward, forward_values
    torch.cuda.empty_cache()

    reachability, _, reachability_record = d2.load_core_scorer(
        Path(
            artifact["scores"][reachability_labels[PRIMARY_ACID_SEED]]["checkpoint"]
        ),
        arm="reachability",
        expected_seed=PRIMARY_ACID_SEED,
        device=device,
    )
    d2.reachability_literal_costs(
        reachability,
        trajectory=trajectory_cuda[:1],
        goal_embedding=goal_embedding_cuda[:1],
        batch_size=args.batch_size,
    )
    reachability_values, reachability_elapsed = legacy.timed_cuda_call(
        lambda: d2.reachability_literal_costs(
            reachability,
            trajectory=trajectory_cuda,
            goal_embedding=goal_embedding_cuda,
            batch_size=args.batch_size,
        )
    )
    if not np.allclose(
        reachability_values.double().cpu().numpy(),
        arrays[f"reachability_seed_{PRIMARY_ACID_SEED}"],
        rtol=1.0e-6,
        atol=1.0e-6,
    ):
        raise RuntimeError("reachability score replay mismatch")
    add_latency(
        reachability_record,
        reachability_elapsed,
        outputs=["reachability"],
        network_pairs_per_sequence=1,
        batch_size=args.batch_size,
    )
    scorer_records.append(reachability_record)
    del reachability, reachability_values
    torch.cuda.empty_cache()

    for seed in d2.SEEDS:
        acid, acid_payload, acid_record = d2.load_core_scorer(
            acid_paths[seed], arm="acid", expected_seed=seed, device=device
        )
        warmup_generator = torch.Generator(device="cpu").manual_seed(
            d2.acid_noise_seed(args.task, seed, PLANNER_SEED, 0)
        )
        d2.acid_literal_costs(
            acid,
            trajectory=trajectory_cuda[:1],
            actions=candidates_cuda[:1],
            action_mean=acid_payload["acid_action_mean"],
            action_std=acid_payload["acid_action_std"],
            generator=warmup_generator,
            batch_size=args.batch_size,
        )
        generator = torch.Generator(device="cpu").manual_seed(
            d2.acid_noise_seed(args.task, seed, PLANNER_SEED, 1)
        )
        acid_one, acid_one_elapsed = legacy.timed_cuda_call(
            lambda: d2.acid_literal_costs(
                acid,
                trajectory=trajectory_cuda,
                actions=candidates_cuda,
                action_mean=acid_payload["acid_action_mean"],
                action_std=acid_payload["acid_action_std"],
                generator=generator,
                batch_size=args.batch_size,
            )
        )
        flow_noise = build_action_noise_bank(
            task=args.task,
            scorer_seed=seed,
            horizon=candidates.shape[-2],
            action_dim=candidates.shape[-1],
        ).to(device)
        acid_flow_training_energy(
            acid,
            trajectory=trajectory_cuda[:1],
            actions=candidates_cuda[:1],
            action_mean=acid_payload["acid_action_mean"],
            action_std=acid_payload["acid_action_std"],
            noise_bank=flow_noise,
            batch_size=args.batch_size,
        )
        acid_flow, acid_flow_elapsed = legacy.timed_cuda_call(
            lambda: acid_flow_training_energy(
                acid,
                trajectory=trajectory_cuda,
                actions=candidates_cuda,
                action_mean=acid_payload["acid_action_mean"],
                action_std=acid_payload["acid_action_std"],
                noise_bank=flow_noise,
                batch_size=args.batch_size,
            )
        )
        sample_noise = build_acid_sample_noise_bank(
            task=args.task,
            scorer_seed=seed,
            horizon=candidates.shape[-2],
            action_dim=candidates.shape[-1],
            draws=ACID_SAMPLE_DRAWS,
        ).to(device)
        acid_multisample_costs(
            acid,
            trajectory=trajectory_cuda[:1],
            actions=candidates_cuda[:1],
            action_mean=acid_payload["acid_action_mean"],
            action_std=acid_payload["acid_action_std"],
            noise_bank=sample_noise,
            batch_size=args.batch_size,
        )
        acid_multi, acid_multi_elapsed = legacy.timed_cuda_call(
            lambda: acid_multisample_costs(
                acid,
                trajectory=trajectory_cuda,
                actions=candidates_cuda,
                action_mean=acid_payload["acid_action_mean"],
                action_std=acid_payload["acid_action_std"],
                noise_bank=sample_noise,
                batch_size=args.batch_size,
            )
        )
        arrays[f"acid_seed_{seed}"] = acid_one.double().cpu().numpy()
        arrays[f"acid_flow_seed_{seed}"] = acid_flow.double().cpu().numpy()
        arrays[f"acid_16_mean_seed_{seed}"] = acid_multi[
            "acid_sample_mean"
        ].double().cpu().numpy()
        arrays[f"acid_16_min_seed_{seed}"] = acid_multi[
            "acid_sample_min"
        ].double().cpu().numpy()
        acid_record.update(
            primary=(seed == PRIMARY_ACID_SEED),
            endpoints=["ACID-one-sample", "ACID-flow-energy", "ACID-16-mean", "ACID-16-min"],
            one_sample_latency=legacy.latency_profile(
                acid_one_elapsed,
                batch_size=args.batch_size,
                outputs=["ACID-one-sample"],
                network_pairs_per_sequence=5,
            ),
            flow_energy_latency=legacy.latency_profile(
                acid_flow_elapsed,
                batch_size=args.batch_size,
                outputs=["ACID-flow-energy"],
                network_pairs_per_sequence=(
                    5 * len(SCORING_SIGMAS) * NOISE_DRAWS
                ),
            ),
            multisample_latency=legacy.latency_profile(
                acid_multi_elapsed,
                batch_size=args.batch_size,
                outputs=["ACID-16-mean", "ACID-16-min"],
                network_pairs_per_sequence=5 * ACID_SAMPLE_DRAWS,
            ),
        )
        scorer_records.append(acid_record)
        del acid, acid_one, acid_flow, acid_multi
        torch.cuda.empty_cache()

    score_names = [
        key
        for key in arrays
        if key
        not in {
            "goal",
            "standardized_rmse",
            "success",
            "final_distance",
            "minimum_distance",
        }
    ]
    for key, values in arrays.items():
        if key in {"final_distance", "minimum_distance"} and values.size == 0:
            continue
        if not np.isfinite(values).all():
            raise RuntimeError(f"non-finite E4-D2A array: {key}")
        if key in score_names and values.shape != (POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError(f"unexpected E4-D2A score shape: {key}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = args.output_dir / "e4-d2a-task-scores.npz"
    legacy.atomic_npz(artifact_path, arrays)
    manifest = {
        "status": "ok",
        "kind": "acid_alt_e4_d2a_task_scores",
        "analysis_role": "post-E3 exposed D2 exploratory development",
        "task": args.task,
        "pool_count": POOL_COUNT,
        "candidates_per_pool": CANDIDATE_COUNT,
        "primary_e4_seed": PRIMARY_E4_SEED,
        "primary_acid_seed": PRIMARY_ACID_SEED,
        "acid_sensitivity_seeds": list(d2.SEEDS),
        "e4_sigmas": list(SCORING_SIGMAS),
        "e4_noise_draws": NOISE_DRAWS,
        "acid_multisample_draws": ACID_SAMPLE_DRAWS,
        "lambda_primary": 0.07,
        "lambda_sensitivity": [0.02, 0.14],
        "shuffled_deployment_reliability": 0,
        "endpoints": score_names,
        "scorers": scorer_records,
        "artifact": str(artifact_path),
        "artifact_sha256": sha256_file(artifact_path),
        "shared_scores": str(args.shared_scores),
        "shared_scores_sha256": sha256_file(args.shared_scores),
        "shared_score_manifest": str(args.shared_score_manifest),
        "shared_score_manifest_sha256": sha256_file(args.shared_score_manifest),
        "execution": str(args.execution),
        "execution_sha256": sha256_file(args.execution),
        "execution_manifest": str(args.execution_manifest),
        "execution_manifest_sha256": sha256_file(args.execution_manifest),
        "legacy_d2_manifest": str(args.legacy_d2_manifest),
        "legacy_d2_manifest_sha256": sha256_file(args.legacy_d2_manifest),
        "legacy_d2_provenance": str(args.legacy_d2_provenance),
        "legacy_d2_provenance_sha256": sha256_file(args.legacy_d2_provenance),
        "dataset_sha256": score_manifest["dataset_sha256"],
        "world_model_checkpoint_sha256": score_manifest[
            "world_model_checkpoint_sha256"
        ],
        "upstream_source_manifest_sha256": score_manifest[
            "source_manifest_sha256"
        ],
        "p1_gate": str(args.p1_gate),
        "p1_gate_sha256": sha256_file(args.p1_gate),
        "parent_protocol": str(args.parent_protocol),
        "parent_protocol_sha256": sha256_file(args.parent_protocol),
        "implementation_freeze": str(args.implementation_freeze),
        "implementation_freeze_sha256": sha256_file(args.implementation_freeze),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_manifest_sha256,
        "protected_c1_i1_read": False,
        "confirmation_claim_allowed": False,
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(device),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
        },
    }
    legacy.atomic_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
