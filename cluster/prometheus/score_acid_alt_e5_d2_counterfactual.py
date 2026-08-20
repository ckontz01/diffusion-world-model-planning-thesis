#!/usr/bin/env python3
"""Score frozen E4 models with E5 counterfactual endpoints on exposed D2."""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from acid_alt_e4_scoring import build_action_noise_bank, load_e4_model, sha256_file
from acid_alt_e5_counterfactual import (
    COUNTERFACTUAL_OFFSETS,
    PRIMARY_COUNTERFACTUAL_COUNT,
    counterfactual_successor_costs,
    network_pairs_per_sequence,
)


TASKS = ("pusht", "reacher", "cube")
POOL_COUNT = 50
CANDIDATE_COUNT = 300
PRIMARY_E4_SEED = 7101
E4_D2A_SOURCE_MANIFEST_SHA256 = (
    "36a6c04fe47e8bfc0bb6e375e5d2d3448879e06146af433d504c523842af70bd"
)
E4_P1_GATE_SHA256 = (
    "5a1e176141bfa904e89bdfcdeb3fbae75c7ab5320e4394a8db0f320675ca98c3"
)


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
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.partial-", dir=path.parent
    )
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
    elapsed: float,
    *,
    batch_size: int,
    outputs: list[str],
    network_pairs: int,
) -> dict[str, Any]:
    sequences = POOL_COUNT * CANDIDATE_COUNT
    horizon_transitions = sequences * 5
    return {
        "measurement": (
            "one 300-sequence warmup pool followed by one CUDA-synchronized "
            "full exposed-D2 scorer pass; excludes model loading and shared rollout"
        ),
        "outputs_computed_jointly": outputs,
        "candidate_sequences": sequences,
        "horizon_transitions": horizon_transitions,
        "network_pairs_per_sequence": network_pairs,
        "network_pair_evaluations": sequences * network_pairs,
        "transition_batch_size": batch_size,
        "elapsed_seconds": elapsed,
        "milliseconds_per_candidate_sequence": 1000.0 * elapsed / sequences,
        "microseconds_per_horizon_transition": 1.0e6
        * elapsed
        / horizon_transitions,
        "candidate_sequences_per_second": sequences / elapsed,
    }


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def _load_json(path: Path) -> dict[str, Any]:
    _require_file(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _validate_e4_d2a(
    *,
    task: str,
    artifact_path: Path,
    manifest_path: Path,
    shared_scores: Path,
    shared_manifest: Path,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    manifest = _load_json(manifest_path)
    expected = {
        "status": "ok",
        "kind": "acid_alt_e4_d2a_task_scores",
        "task": task,
        "analysis_role": "post-E3 exposed D2 exploratory development",
        "source_manifest_sha256": E4_D2A_SOURCE_MANIFEST_SHA256,
        "p1_gate_sha256": E4_P1_GATE_SHA256,
        "pool_count": POOL_COUNT,
        "candidates_per_pool": CANDIDATE_COUNT,
        "protected_c1_i1_read": False,
        "confirmation_claim_allowed": False,
    }
    for key, wanted in expected.items():
        if manifest.get(key) != wanted:
            raise RuntimeError(
                f"E4-D2A manifest {key}={manifest.get(key)!r}, expected {wanted!r}"
            )
    for path, field, hash_field in (
        (artifact_path, "artifact", "artifact_sha256"),
        (shared_scores, "shared_scores", "shared_scores_sha256"),
        (shared_manifest, "shared_score_manifest", "shared_score_manifest_sha256"),
    ):
        _require_file(path)
        if str(path) != manifest.get(field) or sha256_file(path) != manifest.get(
            hash_field
        ):
            raise RuntimeError(f"E4-D2A lineage mismatch for {field}")
    with np.load(artifact_path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    required = {
        "goal",
        "standardized_rmse",
        "success",
        "e4_dide",
        "e4_shuffled_dide",
        "acid_seed_6101",
        "acid_flow_seed_6101",
        "acid_16_min_seed_6101",
        "deterministic_inverse",
        "gaussian_nll",
        "forward_seed_6101",
    }
    if not required.issubset(arrays):
        raise RuntimeError("E4-D2A artifact lacks required comparator arrays")
    for name in required:
        if arrays[name].shape != (POOL_COUNT, CANDIDATE_COUNT):
            raise RuntimeError(f"E4-D2A {name} has shape {arrays[name].shape}")
        if not np.isfinite(arrays[name]).all():
            raise RuntimeError(f"E4-D2A {name} is non-finite")
    return arrays, manifest


def _load_shared_scores(path: Path) -> tuple[torch.Tensor, torch.Tensor]:
    artifact = torch.load(path, map_location="cpu", weights_only=False)
    if artifact.get("kind") != "flat_same_candidate_shared_rollout_scores":
        raise RuntimeError("unexpected shared-score artifact kind")
    trajectory = torch.as_tensor(artifact["predicted_trajectory"]).float()
    candidates = torch.as_tensor(artifact["candidates"]).float()
    if trajectory.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("shared predicted trajectory pool shape differs")
    if candidates.shape[:2] != (POOL_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("shared candidate pool shape differs")
    if trajectory.shape[2] != candidates.shape[2] + 1:
        raise RuntimeError("shared trajectory/action horizon mismatch")
    if not torch.isfinite(trajectory).all() or not torch.isfinite(candidates).all():
        raise RuntimeError("shared candidate tensors are non-finite")
    return trajectory, candidates


def _score_model(
    *,
    model: torch.nn.Module,
    payload: dict[str, Any],
    trajectory: torch.Tensor,
    candidates: torch.Tensor,
    noise_bank: torch.Tensor,
    batch_size: int,
) -> tuple[dict[str, torch.Tensor], float]:
    counterfactual_successor_costs(
        model,
        trajectory=trajectory[:1],
        actions=candidates[:1],
        payload=payload,
        noise_bank=noise_bank,
        batch_size=batch_size,
    )
    return timed_cuda_call(
        lambda: counterfactual_successor_costs(
            model,
            trajectory=trajectory,
            actions=candidates,
            payload=payload,
            noise_bank=noise_bank,
            batch_size=batch_size,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--shared-scores", type=Path, required=True)
    parser.add_argument("--shared-score-manifest", type=Path, required=True)
    parser.add_argument("--e4-d2a-scores", type=Path, required=True)
    parser.add_argument("--e4-d2a-manifest", type=Path, required=True)
    parser.add_argument("--e4-true-summary", type=Path, required=True)
    parser.add_argument("--e4-shuffled-summary", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    for path in (
        args.source_manifest,
        args.shared_scores,
        args.shared_score_manifest,
        args.e4_d2a_scores,
        args.e4_d2a_manifest,
        args.e4_true_summary,
        args.e4_shuffled_summary,
    ):
        _require_file(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E5-D2 output directory")
    if args.batch_size <= 0 or not torch.cuda.is_available():
        raise RuntimeError("positive batch size and CUDA are required")

    baseline, e4_manifest = _validate_e4_d2a(
        task=args.task,
        artifact_path=args.e4_d2a_scores,
        manifest_path=args.e4_d2a_manifest,
        shared_scores=args.shared_scores,
        shared_manifest=args.shared_score_manifest,
    )
    trajectory, candidates = _load_shared_scores(args.shared_scores)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    trajectory = trajectory.to(device)
    candidates = candidates.to(device)
    noise_bank = build_action_noise_bank(
        task=args.task,
        scorer_seed=PRIMARY_E4_SEED,
        horizon=candidates.shape[-2],
        action_dim=candidates.shape[-1],
    ).to(device)

    true_model, true_payload, _, true_record = load_e4_model(
        args.e4_true_summary,
        task=args.task,
        expected_condition="true_successor",
        device=device,
    )
    shuffled_model, shuffled_payload, _, shuffled_record = load_e4_model(
        args.e4_shuffled_summary,
        task=args.task,
        expected_condition="shuffled_successor",
        device=device,
    )
    true_scores, true_elapsed = _score_model(
        model=true_model,
        payload=true_payload,
        trajectory=trajectory,
        candidates=candidates,
        noise_bank=noise_bank,
        batch_size=args.batch_size,
    )
    shuffled_scores, shuffled_elapsed = _score_model(
        model=shuffled_model,
        payload=shuffled_payload,
        trajectory=trajectory,
        candidates=candidates,
        noise_bank=noise_bank,
        batch_size=args.batch_size,
    )
    replay_max_abs = {
        "true": float(
            np.max(
                np.abs(
                    true_scores["dide_replay"].double().cpu().numpy()
                    - baseline["e4_dide"]
                )
            )
        ),
        "shuffled": float(
            np.max(
                np.abs(
                    shuffled_scores["dide_replay"].double().cpu().numpy()
                    - baseline["e4_shuffled_dide"]
                )
            )
        ),
    }
    if max(replay_max_abs.values()) > 1.0e-6:
        raise RuntimeError(f"E4 DIDE replay mismatch: {replay_max_abs}")

    arrays: dict[str, np.ndarray] = {}
    candidate_keys = (
        "dide_replay",
        "csda_log_tail_k4",
        "csda_log_tail_k8",
        "csda_log_tail_k16",
        "csda_log_mean_k8",
        "csda_pairwise_tail_k8",
        "csda_softplus_tail_k8",
    )
    for prefix, values in (("true", true_scores), ("shuffled", shuffled_scores)):
        for key in candidate_keys:
            value = values[key].double().cpu().numpy()
            if value.shape != (POOL_COUNT, CANDIDATE_COUNT):
                raise RuntimeError(f"{prefix}/{key} shape differs: {value.shape}")
            arrays[f"{prefix}_{key}"] = value
    output_artifact = args.output_dir / "e5-counterfactual-scores.npz"
    output_manifest = args.output_dir / "manifest.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_npz(output_artifact, arrays)
    endpoints = sorted(arrays)
    for record, elapsed, condition in (
        (true_record, true_elapsed, "true_successor"),
        (shuffled_record, shuffled_elapsed, "shuffled_successor"),
    ):
        record.update(
            condition=condition,
            endpoints=[name for name in endpoints if name.startswith(condition.split("_")[0])],
            latency=latency_profile(
                elapsed,
                batch_size=args.batch_size,
                outputs=["CSDA nested K=4/8/16 and diagnostics"],
                network_pairs=network_pairs_per_sequence(
                    len(COUNTERFACTUAL_OFFSETS)
                ),
            ),
        )
    manifest = {
        "status": "ok",
        "kind": "acid_alt_e5_counterfactual_d2_scores",
        "analysis_role": "post-outcome exposed-D2 E5 method development",
        "task": args.task,
        "artifact": str(output_artifact),
        "artifact_sha256": sha256_file(output_artifact),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "e4_d2a_artifact": str(args.e4_d2a_scores),
        "e4_d2a_artifact_sha256": sha256_file(args.e4_d2a_scores),
        "e4_d2a_manifest": str(args.e4_d2a_manifest),
        "e4_d2a_manifest_sha256": sha256_file(args.e4_d2a_manifest),
        "shared_scores": str(args.shared_scores),
        "shared_scores_sha256": sha256_file(args.shared_scores),
        "shared_score_manifest": str(args.shared_score_manifest),
        "shared_score_manifest_sha256": sha256_file(args.shared_score_manifest),
        "e4_d2a_source_manifest_sha256": e4_manifest["source_manifest_sha256"],
        "counterfactual_offsets": list(COUNTERFACTUAL_OFFSETS),
        "primary_counterfactual_count": PRIMARY_COUNTERFACTUAL_COUNT,
        "endpoints": endpoints,
        "dide_replay_max_abs": replay_max_abs,
        "scorers": [true_record, shuffled_record],
        "pool_count": POOL_COUNT,
        "candidates_per_pool": CANDIDATE_COUNT,
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
        },
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "protected_c1_i1_read": False,
    }
    atomic_json(output_manifest, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
