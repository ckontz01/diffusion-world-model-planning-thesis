#!/usr/bin/env python3
"""Score all frozen v3 endpoints on one task's physical D2 candidate audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

import acid_alt_d2_models as d2


TASKS = ("pusht", "reacher", "cube")
POOL_COUNT = 50
CANDIDATE_COUNT = 300
PLANNER_SEED = 8201


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.partial-", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        with temporary.open("wb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def timed_cuda_call(call: Any) -> tuple[Any, float]:
    torch.cuda.synchronize()
    started = time.perf_counter()
    value = call()
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    if elapsed <= 0:
        raise RuntimeError("CUDA latency measurement was nonpositive")
    return value, elapsed


def latency_profile(
    elapsed_seconds: float,
    *,
    batch_size: int | None,
    outputs: list[str],
    network_pairs_per_sequence: int = 5,
) -> dict[str, Any]:
    sequences = POOL_COUNT * CANDIDATE_COUNT
    horizon_transitions = sequences * 5
    network_pairs = sequences * network_pairs_per_sequence
    return {
        "measurement": (
            "one 300-sequence warmup pool followed by one CUDA-synchronized "
            "exact full-D2 scorer pass; excludes model loading and shared world-model rollout"
        ),
        "outputs_computed_jointly": outputs,
        "candidate_sequences": sequences,
        "horizon_transitions": horizon_transitions,
        "network_pairs_per_sequence": network_pairs_per_sequence,
        "network_pair_evaluations": network_pairs,
        "transition_batch_size": batch_size,
        "elapsed_seconds": elapsed_seconds,
        "milliseconds_per_candidate_sequence": 1000.0 * elapsed_seconds / sequences,
        "microseconds_per_horizon_transition": (
            1.0e6 * elapsed_seconds / horizon_transitions
        ),
        "microseconds_per_network_pair": 1.0e6 * elapsed_seconds / network_pairs,
        "candidate_sequences_per_second": sequences / elapsed_seconds,
    }


def validate_d2_identity(
    *,
    task: str,
    manifest_path: Path,
    provenance_path: Path,
    expected_source_sha256: str,
) -> dict[str, Any]:
    if not manifest_path.is_file() or not provenance_path.is_file():
        raise FileNotFoundError("D2 manifest or provenance is missing")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (
        provenance.get("status") != "ok"
        or provenance.get("kind") != "acid_alternative_v3_fresh_d2_manifest"
        or provenance.get("analysis_role") != "D2"
        or provenance.get("task") != task
        or provenance.get("partition") != "P3"
        or provenance.get("selection_seed") != 2026081603
        or provenance.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256") != expected_source_sha256
        or provenance.get("manifest_tsv_sha256") != d2.sha256_file(manifest_path)
        or provenance.get("protected_c1_i1_paths_read") is not False
        or provenance.get("count") != POOL_COUNT
        or provenance.get("unique_episode_count") != POOL_COUNT
    ):
        raise RuntimeError(f"{task}: invalid D2 manifest provenance")
    return provenance


def load_module(path: Path, expected_hash: str, name: str) -> Any:
    if not path.is_file() or d2.sha256_file(path) != expected_hash:
        raise RuntimeError(f"{name} source hash mismatch: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_seeded(values: list[str], label: str) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for value in values:
        parts = value.split("=", 1)
        if len(parts) != 2:
            raise ValueError(f"{label} must be SEED=PATH")
        seed, path = int(parts[0]), Path(parts[1])
        if seed in result:
            raise ValueError(f"duplicate {label} seed {seed}")
        result[seed] = path
    if set(result) != set(d2.SEEDS):
        raise ValueError(f"{label} requires seeds {d2.SEEDS}")
    return result


def core_index(scores: dict[str, Any], arm: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for label, record in scores.items():
        if record.get("arm") == arm and record.get("condition") == "true":
            seed = int(record["training_seed"])
            if seed in result:
                raise RuntimeError(f"duplicate {arm} seed {seed}")
            result[seed] = label
    if set(result) != set(d2.SEEDS):
        raise RuntimeError(f"shared score artifact lacks three true {arm} scorers")
    return result


def validate_upstream(
    *,
    task: str,
    score_path: Path,
    score_manifest_path: Path,
    execution_path: Path,
    execution_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path in (
        score_path,
        score_manifest_path,
        execution_path,
        execution_manifest_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    score_manifest = json.loads(score_manifest_path.read_text(encoding="utf-8"))
    execution_manifest = json.loads(
        execution_manifest_path.read_text(encoding="utf-8")
    )
    if (
        score_manifest.get("status") != "ok"
        or score_manifest.get("analysis_role") != "D2"
        or score_manifest.get("confirmation_authorization_sha256") is not None
        or score_manifest.get("pool_count") != POOL_COUNT
        or score_manifest.get("candidates_per_pool") != CANDIDATE_COUNT
        or d2.sha256_file(score_path) != score_manifest.get("artifact_sha256")
    ):
        raise RuntimeError(f"{task}: invalid D2 shared-score artifact")
    if (
        execution_manifest.get("status") != "ok"
        or execution_manifest.get("analysis_role") != "D2"
        or execution_manifest.get("confirmation_authorization_sha256") is not None
        or execution_manifest.get("pool_count") != POOL_COUNT
        or execution_manifest.get("candidates_per_pool") != CANDIDATE_COUNT
        or d2.sha256_file(execution_path)
        != execution_manifest.get("output_h5_sha256")
    ):
        raise RuntimeError(f"{task}: invalid D2 physical execution artifact")
    for field in (
        "candidate_artifact_sha256",
        "candidate_manifest_sha256",
        "eval_manifest_sha256",
        "dataset_sha256",
        "world_model_checkpoint_sha256",
        "source_manifest_sha256",
    ):
        if not score_manifest.get(field) or score_manifest[field] != execution_manifest.get(
            field
        ):
            raise RuntimeError(f"{task}: score/execution {field} mismatch")
    artifact = torch.load(score_path, map_location="cpu", weights_only=False)
    if artifact.get("kind") != "flat_same_candidate_shared_rollout_scores":
        raise RuntimeError(f"{task}: unexpected shared-score kind")
    return artifact, score_manifest, execution_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--trainer-source", type=Path, required=True)
    parser.add_argument("--p1-gate", type=Path, required=True)
    parser.add_argument("--d2-manifest", type=Path, required=True)
    parser.add_argument("--d2-provenance", type=Path, required=True)
    parser.add_argument("--shared-scores", type=Path, required=True)
    parser.add_argument("--shared-score-manifest", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--residual-true", action="append", default=[])
    parser.add_argument("--residual-shuffled", action="append", default=[])
    parser.add_argument("--acid", action="append", default=[])
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    started = time.time()
    for path in (
        args.protocol,
        args.source_manifest,
        args.p1_gate,
        args.d2_manifest,
        args.d2_provenance,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if d2.sha256_file(args.protocol) != d2.PROTOCOL_SHA256:
        raise RuntimeError("D2 protocol hash mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty D2 task-score output")
    true_paths = parse_seeded(args.residual_true, "residual true")
    shuffled_paths = parse_seeded(args.residual_shuffled, "residual shuffled")
    acid_paths = parse_seeded(args.acid, "ACID")
    gate = json.loads(args.p1_gate.read_text(encoding="utf-8"))
    if (
        gate.get("status") != "ok"
        or gate.get("kind") != "acid_alt_v3_multiseed_p1_gate"
        or gate.get("analysis_role") != "P1 only; before D2 outcome generation"
        or gate.get("decision") != "authorize_D2"
        or gate.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or gate.get("source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or gate.get("all_pass") is not True
        or gate.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("P1 gate does not authorize D2 scoring")

    artifact, score_manifest, execution_manifest = validate_upstream(
        task=args.task,
        score_path=args.shared_scores,
        score_manifest_path=args.shared_score_manifest,
        execution_path=args.execution,
        execution_manifest_path=args.execution_manifest,
    )
    source_sha256 = d2.sha256_file(args.source_manifest)
    d2_provenance = validate_d2_identity(
        task=args.task,
        manifest_path=args.d2_manifest,
        provenance_path=args.d2_provenance,
        expected_source_sha256=d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256,
    )
    if (
        score_manifest["source_manifest_sha256"]
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or score_manifest["eval_manifest_sha256"]
        != d2.sha256_file(args.d2_manifest)
        or score_manifest["dataset_sha256"] != d2_provenance.get("dataset_sha256")
    ):
        raise RuntimeError(f"{args.task}: upstream artifacts do not bind to this D2")
    trajectory = torch.as_tensor(artifact["predicted_trajectory"]).float()
    candidates = torch.as_tensor(artifact["candidates"]).float()
    goal_embedding = torch.as_tensor(artifact["goal_embedding"]).float()
    goal = torch.as_tensor(artifact["scores"]["b0"]["raw_verifier_cost"]).double()
    if trajectory.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("D2 predicted-trajectory pool shape differs")
    if candidates.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("D2 candidate pool shape differs")
    if goal.shape != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("D2 goal cost shape differs")
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
    predicted_np = trajectory.numpy()
    if executed.shape != predicted_np.shape or success.shape != goal.shape:
        raise RuntimeError("D2 predicted/executed/success shapes differ")
    latent_std = torch.as_tensor(artifact["transition_latent_std"]).float().numpy()
    if latent_std.shape != (trajectory.shape[-1],) or np.any(latent_std <= 0):
        raise RuntimeError("D2 latent standardizer is invalid")
    standardized_rmse = np.sqrt(
        np.mean(
            np.square((predicted_np[:, :, 1:] - executed[:, :, 1:]) / latent_std),
            axis=(2, 3),
        )
    )
    if not np.isfinite(standardized_rmse).all():
        raise RuntimeError("D2 physical RMSE is non-finite")

    trainer = load_module(args.trainer_source, d2.V2_TRAINER_SHA256, "v2_trainer")
    d2.self_test(trainer)
    if not torch.cuda.is_available():
        raise RuntimeError("D2 scoring requires CUDA")
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
    for seed in d2.SEEDS:
        true_model, true_payload, true_record = d2.load_residual_model(
            true_paths[seed],
            expected_condition="true",
            trainer_module=trainer,
            device=device,
        )
        shuffled_model, shuffled_payload, shuffled_record = d2.load_residual_model(
            shuffled_paths[seed],
            expected_condition="shuffled_action",
            trainer_module=trainer,
            device=device,
        )
        d2.validate_residual_pair(true_payload, shuffled_payload)
        if int(true_payload["seed"]) != seed:
            raise RuntimeError("residual path seed differs from declaration")
        current, clean = d2.standardized_residual_inputs(trajectory_cuda, true_payload)
        bank = d2.build_residual_noise_bank(
            task=args.task,
            scorer_seed=seed,
            horizon=candidates.shape[-2],
            latent_dim=trajectory.shape[-1],
        ).to(device)
        # Warm up one complete candidate pool, then time the exact full-D2
        # inference path. RDX and AE share the same conditional/unconditional
        # denoiser passes and are therefore timed jointly rather than double-counted.
        d2.residual_endpoint_costs(
            true_model,
            current=current[:1],
            clean=clean[:1],
            actions=candidates_cuda[:1],
            noise_bank=bank,
            batch_size=args.batch_size,
        )
        (true_rdx, true_ae, _), true_elapsed = timed_cuda_call(
            lambda: d2.residual_endpoint_costs(
                true_model,
                current=current,
                clean=clean,
                actions=candidates_cuda,
                noise_bank=bank,
                batch_size=args.batch_size,
            )
        )
        d2.residual_endpoint_costs(
            shuffled_model,
            current=current[:1],
            clean=clean[:1],
            actions=candidates_cuda[:1],
            noise_bank=bank,
            batch_size=args.batch_size,
        )
        (shuffled_rdx, shuffled_ae, _), shuffled_elapsed = timed_cuda_call(
            lambda: d2.residual_endpoint_costs(
                shuffled_model,
                current=current,
                clean=clean,
                actions=candidates_cuda,
                noise_bank=bank,
                batch_size=args.batch_size,
            )
        )
        arrays[f"rdx_true_seed_{seed}"] = true_rdx.cpu().numpy()
        arrays[f"ae_true_seed_{seed}"] = true_ae.cpu().numpy()
        arrays[f"rdx_shuffled_seed_{seed}"] = shuffled_rdx.cpu().numpy()
        arrays[f"ae_shuffled_seed_{seed}"] = shuffled_ae.cpu().numpy()
        true_record.update(
            arm="residual_diffusion",
            endpoints=["RDX", "AE"],
            latency=latency_profile(
                true_elapsed,
                batch_size=args.batch_size,
                outputs=["RDX", "AE"],
                network_pairs_per_sequence=(
                    5 * len(d2.SIGMAS) * d2.NOISE_DRAWS * 2
                ),
            ),
        )
        shuffled_record.update(
            arm="residual_diffusion",
            endpoints=["RDX_shuffled", "AE_shuffled"],
            latency=latency_profile(
                shuffled_elapsed,
                batch_size=args.batch_size,
                outputs=["RDX_shuffled", "AE_shuffled"],
                network_pairs_per_sequence=(
                    5 * len(d2.SIGMAS) * d2.NOISE_DRAWS * 2
                ),
            ),
        )
        scorer_records.extend((true_record, shuffled_record))
        del true_model, shuffled_model, true_rdx, true_ae, shuffled_rdx, shuffled_ae
        torch.cuda.empty_cache()

    forward_labels = core_index(artifact["scores"], "forward")
    for seed in d2.SEEDS:
        shared_values = torch.as_tensor(
            artifact["scores"][forward_labels[seed]]["raw_verifier_cost"]
        ).double()
        if shared_values.shape != goal.shape or not torch.isfinite(shared_values).all():
            raise RuntimeError(f"forward seed {seed} cost is invalid")
        shared_record = artifact["scores"][forward_labels[seed]]
        scorer, payload, record = d2.load_core_scorer(
            Path(shared_record["checkpoint"]),
            arm="forward",
            expected_seed=seed,
            device=device,
        )
        d2.forward_literal_costs(
            scorer,
            trajectory=trajectory_cuda[:1],
            actions=candidates_cuda[:1],
            latent_mean=payload["latent_mean"],
            latent_std=payload["latent_std"],
            batch_size=args.batch_size,
        )
        values, forward_elapsed = timed_cuda_call(
            lambda: d2.forward_literal_costs(
                scorer,
                trajectory=trajectory_cuda,
                actions=candidates_cuda,
                latent_mean=payload["latent_mean"],
                latent_std=payload["latent_std"],
                batch_size=args.batch_size,
            )
        )
        maximum_difference = float(
            (values.double().cpu() - shared_values).abs().max().item()
        )
        if not torch.allclose(
            values.double().cpu(), shared_values, rtol=1.0e-6, atol=1.0e-6
        ):
            raise RuntimeError(
                f"forward seed {seed} literal/shared cost mismatch: {maximum_difference}"
            )
        arrays[f"forward_seed_{seed}"] = values.double().cpu().numpy()
        record.update(
            label=forward_labels[seed],
            validation_max_abs_against_shared_score=maximum_difference,
            latency=latency_profile(
                forward_elapsed,
                batch_size=args.batch_size,
                outputs=["forward"],
            ),
        )
        scorer_records.append(
            record
        )
        del scorer, values
        torch.cuda.empty_cache()

    dtv_labels = core_index(artifact["scores"], "diffusion")
    for seed in d2.SEEDS:
        shared_values = torch.as_tensor(
            artifact["scores"][dtv_labels[seed]]["raw_verifier_cost"]
        ).double()
        if shared_values.shape != goal.shape or not torch.isfinite(shared_values).all():
            raise RuntimeError(f"legacy DTV seed {seed} cost is invalid")
        shared_record = artifact["scores"][dtv_labels[seed]]
        scorer, payload, record = d2.load_core_scorer(
            Path(shared_record["checkpoint"]),
            arm="diffusion",
            expected_seed=seed,
            device=device,
        )
        bank = d2.build_legacy_dtv_noise_bank(
            scorer_seed=seed,
            horizon=candidates.shape[-2],
            latent_dim=trajectory.shape[-1],
        ).to(device)
        d2.legacy_dtv_costs(
            scorer,
            trajectory=trajectory_cuda[:1],
            actions=candidates_cuda[:1],
            latent_mean=payload["latent_mean"],
            latent_std=payload["latent_std"],
            noise_bank=bank,
            batch_size=args.batch_size,
        )
        values, dtv_elapsed = timed_cuda_call(
            lambda: d2.legacy_dtv_costs(
                scorer,
                trajectory=trajectory_cuda,
                actions=candidates_cuda,
                latent_mean=payload["latent_mean"],
                latent_std=payload["latent_std"],
                noise_bank=bank,
                batch_size=args.batch_size,
            )
        )
        maximum_difference = float(
            (values.double().cpu() - shared_values).abs().max().item()
        )
        if not torch.allclose(
            values.double().cpu(), shared_values, rtol=1.0e-6, atol=1.0e-6
        ):
            raise RuntimeError(
                f"legacy DTV seed {seed} literal/shared mismatch: {maximum_difference}"
            )
        arrays[f"dtv_seed_{seed}"] = values.double().cpu().numpy()
        record.update(
            arm="dtv",
            checkpoint_model_arm="diffusion",
            label=dtv_labels[seed],
            validation_max_abs_against_shared_score=maximum_difference,
            latency=latency_profile(
                dtv_elapsed,
                batch_size=args.batch_size,
                outputs=["legacy_DTV"],
                network_pairs_per_sequence=5 * len(d2.LEGACY_DTV_SIGMAS),
            ),
        )
        scorer_records.append(record)
        del scorer, values
        torch.cuda.empty_cache()

    reachability_labels = core_index(artifact["scores"], "reachability")
    for seed in d2.SEEDS:
        shared_values = torch.as_tensor(
            artifact["scores"][reachability_labels[seed]]["raw_verifier_cost"]
        ).double()
        if shared_values.shape != goal.shape or not torch.isfinite(shared_values).all():
            raise RuntimeError(f"reachability seed {seed} cost is invalid")
        shared_record = artifact["scores"][reachability_labels[seed]]
        scorer, _, record = d2.load_core_scorer(
            Path(shared_record["checkpoint"]),
            arm="reachability",
            expected_seed=seed,
            device=device,
        )
        d2.reachability_literal_costs(
            scorer,
            trajectory=trajectory_cuda[:1],
            goal_embedding=goal_embedding_cuda[:1],
            batch_size=args.batch_size,
        )
        values, reachability_elapsed = timed_cuda_call(
            lambda: d2.reachability_literal_costs(
                scorer,
                trajectory=trajectory_cuda,
                goal_embedding=goal_embedding_cuda,
                batch_size=args.batch_size,
            )
        )
        maximum_difference = float(
            (values.double().cpu() - shared_values).abs().max().item()
        )
        if not torch.allclose(
            values.double().cpu(), shared_values, rtol=1.0e-6, atol=1.0e-6
        ):
            raise RuntimeError(
                "reachability seed "
                f"{seed} literal/shared mismatch: {maximum_difference}"
            )
        arrays[f"reachability_seed_{seed}"] = values.double().cpu().numpy()
        record.update(
            label=reachability_labels[seed],
            validation_max_abs_against_shared_score=maximum_difference,
            latency=latency_profile(
                reachability_elapsed,
                batch_size=args.batch_size,
                outputs=["reachability"],
                network_pairs_per_sequence=1,
            ),
        )
        scorer_records.append(record)
        del scorer, values
        torch.cuda.empty_cache()

    for seed in d2.SEEDS:
        scorer, payload, record = d2.load_core_scorer(
            acid_paths[seed], arm="acid", expected_seed=seed, device=device
        )
        warmup_generator = torch.Generator(device="cpu").manual_seed(
            d2.acid_noise_seed(args.task, seed, PLANNER_SEED, 0)
        )
        d2.acid_literal_costs(
            scorer,
            trajectory=trajectory_cuda[:1],
            actions=candidates_cuda[:1],
            action_mean=payload["acid_action_mean"],
            action_std=payload["acid_action_std"],
            generator=warmup_generator,
            batch_size=args.batch_size,
        )
        cost_call_index = 1
        generator = torch.Generator(device="cpu").manual_seed(
            d2.acid_noise_seed(
                args.task, seed, PLANNER_SEED, cost_call_index
            )
        )
        acid, acid_elapsed = timed_cuda_call(
            lambda: d2.acid_literal_costs(
                scorer,
                trajectory=trajectory_cuda,
                actions=candidates_cuda,
                action_mean=payload["acid_action_mean"],
                action_std=payload["acid_action_std"],
                generator=generator,
                batch_size=args.batch_size,
            )
        )
        arrays[f"acid_seed_{seed}"] = acid.cpu().numpy()
        record["inference_sampling"] = (
            "one independent Gaussian draw per candidate and horizon transition"
        )
        record["noise_stream_key"] = {
            "task": args.task,
            "scorer_seed": seed,
            "planner_seed": PLANNER_SEED,
            "cost_call_index": cost_call_index,
        }
        record["noise_seed"] = d2.acid_noise_seed(
            args.task, seed, PLANNER_SEED, cost_call_index
        )
        record["latency"] = latency_profile(
            acid_elapsed,
            batch_size=args.batch_size,
            outputs=["ACID"],
        )
        scorer_records.append(record)
        del scorer, acid
        torch.cuda.empty_cache()

    for key, values in arrays.items():
        if key in {"final_distance", "minimum_distance"} and values.size == 0:
            continue
        if not np.isfinite(values).all():
            raise RuntimeError(f"non-finite D2 array: {key}")
        if key not in {"goal", "standardized_rmse", "success", "final_distance", "minimum_distance"}:
            if values.shape != (POOL_COUNT, CANDIDATE_COUNT):
                raise RuntimeError(f"unexpected D2 score shape: {key}")
            if float(values.std(ddof=1)) <= 1.0e-8:
                raise RuntimeError(f"collapsed D2 score: {key}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = args.output_dir / "d2-task-scores.npz"
    atomic_npz(artifact_path, arrays)
    torch.cuda.synchronize()
    manifest = {
        "status": "ok",
        "kind": "acid_alt_v3_d2_task_endpoint_scores",
        "analysis_role": "D2",
        "task": args.task,
        "pool_count": POOL_COUNT,
        "candidates_per_pool": CANDIDATE_COUNT,
        "scorer_seeds": list(d2.SEEDS),
        "endpoints": {
            "RDX": "conditional clean-residual MSE",
            "AE": "log conditional MSE minus log unconditional MSE",
            "legacy_DTV": "v1 multiscale epsilon-prediction error",
            "reachability": "v1 terminal-to-goal learned reachability cost",
        },
        "sigmas": list(d2.SIGMAS),
        "legacy_dtv_sigmas": list(d2.LEGACY_DTV_SIGMAS),
        "noise_draws": d2.NOISE_DRAWS,
        "diffusion_lambda": d2.DIFFUSION_LAMBDA,
        "acid_lambda": d2.ACID_LAMBDA,
        "legacy_dtv_lambda": d2.DIFFUSION_LAMBDA,
        "reachability_lambda": d2.ACID_LAMBDA,
        "acid_inference": (
            "literal candidate-specific one-sample, one-Euler-step reconstruction; "
            "SHA-256-derived stream keyed by task, scorer seed, planner seed, and cost-call index"
        ),
        "latency_measurement": (
            "one warmup pool then one synchronized full-D2 scorer pass on the same GPU; "
            "excludes loading and shared Le-WM rollout; residual RDX/AE are computed jointly"
        ),
        "scorers": scorer_records,
        "artifact": str(artifact_path),
        "artifact_sha256": d2.sha256_file(artifact_path),
        "shared_scores": str(args.shared_scores),
        "shared_scores_sha256": d2.sha256_file(args.shared_scores),
        "shared_score_manifest": str(args.shared_score_manifest),
        "shared_score_manifest_sha256": d2.sha256_file(args.shared_score_manifest),
        "execution": str(args.execution),
        "execution_sha256": d2.sha256_file(args.execution),
        "execution_manifest": str(args.execution_manifest),
        "execution_manifest_sha256": d2.sha256_file(args.execution_manifest),
        "d2_manifest": str(args.d2_manifest),
        "d2_manifest_sha256": d2.sha256_file(args.d2_manifest),
        "d2_provenance": str(args.d2_provenance),
        "d2_provenance_sha256": d2.sha256_file(args.d2_provenance),
        "eval_manifest_sha256": score_manifest["eval_manifest_sha256"],
        "dataset_sha256": score_manifest["dataset_sha256"],
        "world_model_checkpoint_sha256": score_manifest[
            "world_model_checkpoint_sha256"
        ],
        "upstream_source_manifest_sha256": score_manifest["source_manifest_sha256"],
        "p1_gate": str(args.p1_gate),
        "p1_gate_sha256": d2.sha256_file(args.p1_gate),
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "protected_c1_i1_read": False,
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
    atomic_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
