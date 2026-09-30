#!/usr/bin/env python3
"""Score one shared Le-WM rollout of each frozen diagnostic candidate pool."""

from __future__ import annotations

import argparse
import h5py
import json
import numpy as np
import os
import platform
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import stable_worldmodel as swm
import torch
from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.evaluate_matched import load_scorer
from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)

from acid_alternative_diagnostics.capture_candidate_pools import atomic_torch_save


def parse_scorer_spec(value: str) -> tuple[str, str, Path]:
    parts = value.split("=", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("scorer must be LABEL=ARM=PATH")
    label, arm, path = parts
    if not label or arm not in {"acid", "reachability", "diffusion", "forward"}:
        raise argparse.ArgumentTypeError(f"invalid scorer declaration: {value}")
    return label, arm, Path(path)


def expand_pool_tensor(
    value: torch.Tensor, count: int, device: torch.device
) -> torch.Tensor:
    value = value.to(device)
    return value.unsqueeze(0).unsqueeze(0).expand(1, count, *value.shape)


def score_raw(
    wrapper: SharedRolloutCostModel,
    arm: str,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    goal_embedding: torch.Tensor,
) -> torch.Tensor:
    if arm == "acid":
        return wrapper._acid_cost(trajectory, actions)
    if arm == "reachability":
        return wrapper._reachability_cost(trajectory, goal_embedding)
    if arm == "diffusion":
        return wrapper._diffusion_cost(trajectory, actions)
    if arm == "forward":
        return wrapper._forward_cost(trajectory, actions)
    raise ValueError(arm)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-artifact", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--lambda-weight", type=float, default=0.07)
    parser.add_argument("--diffusion-sigma", type=float, action="append")
    parser.add_argument(
        "--scorer", type=parse_scorer_spec, action="append", required=True
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.candidate_artifact,
        args.candidate_manifest,
        args.world_model_checkpoint,
        args.source_manifest,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    for _, _, path in args.scorer:
        if not path.is_file():
            raise FileNotFoundError(path)
    labels = [label for label, _, _ in args.scorer]
    if len(labels) != len(set(labels)):
        raise ValueError("scorer labels must be unique")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if args.lambda_weight < 0:
        raise ValueError("lambda must be nonnegative")

    candidate_manifest = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    if candidate_manifest.get("status") != "ok":
        raise RuntimeError("candidate manifest is not complete")
    if sha256_file(args.candidate_artifact) != candidate_manifest.get(
        "artifact_sha256"
    ):
        raise RuntimeError("candidate artifact hash mismatch")
    if candidate_manifest.get("analysis_role") not in {"D1", "D2", "C1"}:
        raise RuntimeError("candidate manifest lacks a valid analysis role")
    if candidate_manifest.get("source_manifest_sha256") != sha256_file(
        args.source_manifest
    ):
        raise RuntimeError("candidate/source manifest mismatch")
    if candidate_manifest.get("world_model_checkpoint_sha256") != sha256_file(
        args.world_model_checkpoint
    ):
        raise RuntimeError("candidate/world-model checkpoint mismatch")
    capture = torch.load(
        args.candidate_artifact, map_location="cpu", weights_only=False
    )
    if capture.get("kind") != "flat_b0_final_cem_candidate_pools":
        raise RuntimeError("unexpected candidate artifact kind")
    candidates = capture["candidates"].float()
    stored_b0 = capture["b0_cost"].float()
    info_tensors = capture["info_tensors"]
    if candidates.ndim != 4 or stored_b0.shape != candidates.shape[:2]:
        raise RuntimeError("invalid candidate-pool tensor shapes")
    pool_count, candidate_count, horizon, _ = candidates.shape
    if pool_count != len(capture["rows"]):
        raise RuntimeError("candidate rows and tensors differ")
    if not torch.isfinite(candidates).all() or not torch.isfinite(stored_b0).all():
        raise RuntimeError("candidate artifact contains non-finite values")

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("candidate scoring requires CUDA")
    resolved = resolve_policy_checkpoint(args.world_model_policy, args.stablewm_home)
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("resolved world-model checkpoint differs from declaration")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    )
    world_model = world_model.to(device).eval()
    world_model.requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    b0_wrapper = SharedRolloutCostModel(
        world_model, arm="b0", horizon=horizon, record_diagnostics=False
    ).to(device)

    started = time.time()
    trajectories: list[torch.Tensor] = []
    goal_embeddings: list[torch.Tensor] = []
    recomputed_goals: list[torch.Tensor] = []
    for pool in range(pool_count):
        pool_candidates = candidates[pool].unsqueeze(0).to(device)
        info = {
            key: expand_pool_tensor(value[pool], candidate_count, device)
            for key, value in info_tensors.items()
        }
        goal_cost, trajectory, _, goal_embedding = b0_wrapper._rollout_once(
            info, pool_candidates
        )
        recomputed_goals.append(goal_cost[0].detach().cpu())
        trajectories.append(trajectory[0].detach().cpu())
        goal_embeddings.append(goal_embedding[0, 0].detach().cpu())
    recomputed_b0 = torch.stack(recomputed_goals)
    maximum_b0_difference = float((recomputed_b0 - stored_b0).abs().max().item())
    if not torch.allclose(recomputed_b0, stored_b0, rtol=1.0e-6, atol=1.0e-6):
        raise RuntimeError(
            "shared world-model rollout does not reproduce captured B0 costs: "
            f"max_abs={maximum_b0_difference}"
        )
    trajectory_tensor = torch.stack(trajectories)
    goal_embedding_tensor = torch.stack(goal_embeddings)
    action_mean = torch.as_tensor(
        capture["planner_primitive_action_mean"], dtype=torch.float64
    )
    action_std = torch.as_tensor(
        capture["planner_primitive_action_std"], dtype=torch.float64
    )
    dataset_path = Path(candidate_manifest.get("dataset", ""))
    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)
    with h5py.File(dataset_path, "r") as dataset_handle:
        if "action" not in dataset_handle:
            raise RuntimeError("candidate dataset has no action column")
        raw_planner_actions = np.asarray(dataset_handle["action"][:])

    scores: dict[str, dict[str, Any]] = {
        "b0": {
            "arm": "b0",
            "condition": None,
            "training_seed": None,
            "checkpoint": None,
            "checkpoint_sha256": None,
            # For B0 the only raw cost is the released goal cost itself.
            "raw_verifier_cost": stored_b0,
            "adaptive_weight": torch.zeros(pool_count),
            "combined_cost": stored_b0,
        }
    }
    scorer_records: list[dict[str, Any]] = []
    reference_latent_mean: torch.Tensor | None = None
    reference_latent_std: torch.Tensor | None = None
    sigmas = tuple(args.diffusion_sigma or (0.10, 0.25, 0.50))
    for label, arm, checkpoint in args.scorer:
        scorer, payload = load_scorer(checkpoint, arm, device)
        expected_mean = torch.as_tensor(
            payload["planner_primitive_action_mean"], dtype=torch.float64
        )
        expected_std = torch.as_tensor(
            payload["planner_primitive_action_std"], dtype=torch.float64
        )
        action_standardization = validate_planner_action_standardizer(
            raw_planner_actions,
            action_mean.numpy(),
            action_std.numpy(),
            expected_mean.numpy(),
            expected_std.numpy(),
        )
        kwargs: dict[str, Any] = {
            "noise_seed": int(payload["seed"]),
            "use_action_condition": payload.get("condition") != "action_ablated",
        }
        if arm in ("diffusion", "forward"):
            current_mean = torch.as_tensor(payload["latent_mean"]).float().cpu()
            current_std = torch.as_tensor(payload["latent_std"]).float().cpu()
            if reference_latent_mean is None:
                reference_latent_mean = current_mean
                reference_latent_std = current_std
            elif not torch.equal(
                reference_latent_mean, current_mean
            ) or not torch.equal(reference_latent_std, current_std):
                raise RuntimeError(f"{label}: transition latent statistics differ")
            kwargs.update(
                latent_mean=payload["latent_mean"], latent_std=payload["latent_std"]
            )
        if arm == "acid":
            kwargs.update(
                action_mean=payload["acid_action_mean"],
                action_std=payload["acid_action_std"],
            )
        wrapper = SharedRolloutCostModel(
            world_model,
            arm=arm,
            scorer=scorer,
            lambda_weight=args.lambda_weight,
            horizon=horizon,
            diffusion_sigmas=sigmas,
            record_diagnostics=False,
            **kwargs,
        ).to(device)
        raw_pools: list[torch.Tensor] = []
        weight_pools: list[torch.Tensor] = []
        combined_pools: list[torch.Tensor] = []
        for pool in range(pool_count):
            trajectory = trajectory_tensor[pool].unsqueeze(0).to(device)
            actions = candidates[pool].unsqueeze(0).to(device)
            goal_embedding = expand_pool_tensor(
                goal_embedding_tensor[pool], candidate_count, device
            )
            raw = score_raw(wrapper, arm, trajectory, actions, goal_embedding)
            goal_cost = stored_b0[pool].unsqueeze(0).to(device)
            goal_spread = goal_cost.std(dim=1, unbiased=True)
            raw_spread = raw.std(dim=1, unbiased=True)
            weight = args.lambda_weight * goal_spread / raw_spread.clamp_min(1.0e-8)
            combined = goal_cost + weight[:, None] * raw
            if not torch.isfinite(raw).all() or not torch.isfinite(combined).all():
                raise RuntimeError(f"{label}: non-finite candidate score")
            raw_pools.append(raw[0].detach().cpu())
            weight_pools.append(weight[0].detach().cpu())
            combined_pools.append(combined[0].detach().cpu())
        checkpoint_sha = sha256_file(checkpoint)
        condition = payload.get("condition")
        scores[label] = {
            "arm": arm,
            "condition": condition,
            "training_seed": int(payload["seed"]),
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": checkpoint_sha,
            "parameter_count": sum(
                parameter.numel() for parameter in scorer.parameters()
            ),
            "validation": payload.get("validation"),
            "raw_verifier_cost": torch.stack(raw_pools),
            "adaptive_weight": torch.stack(weight_pools),
            "combined_cost": torch.stack(combined_pools),
        }
        scorer_records.append(
            {
                "label": label,
                "arm": arm,
                "condition": condition,
                "training_seed": int(payload["seed"]),
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": checkpoint_sha,
                "parameter_count": scores[label]["parameter_count"],
                "planner_action_standardization": action_standardization,
            }
        )
        del wrapper, scorer
        torch.cuda.empty_cache()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = args.output_dir / "candidate-scores.pt"
    output = {
        "format_version": 1,
        "kind": "flat_same_candidate_shared_rollout_scores",
        "rows": capture["rows"],
        "candidates": candidates,
        "predicted_trajectory": trajectory_tensor,
        "goal_embedding": goal_embedding_tensor,
        "transition_latent_mean": reference_latent_mean,
        "transition_latent_std": reference_latent_std,
        "b0_recompute_max_abs": maximum_b0_difference,
        "lambda_weight": args.lambda_weight,
        "diffusion_sigmas": sigmas,
        "scores": scores,
    }
    atomic_torch_save(artifact_path, output)
    torch.cuda.synchronize()
    manifest = {
        "status": "ok",
        "kind": output["kind"],
        "analysis_role": candidate_manifest.get("analysis_role"),
        "confirmation_authorization_sha256": candidate_manifest.get(
            "confirmation_authorization_sha256"
        ),
        "shared_world_model_rollouts": pool_count,
        "private_world_model_rollouts_per_scorer": 0,
        "pool_count": pool_count,
        "candidates_per_pool": candidate_count,
        "scorer_count_excluding_b0": len(args.scorer),
        "scorers": scorer_records,
        "candidate_artifact": str(args.candidate_artifact),
        "candidate_artifact_sha256": sha256_file(args.candidate_artifact),
        "candidate_manifest": str(args.candidate_manifest),
        "candidate_manifest_sha256": sha256_file(args.candidate_manifest),
        "eval_manifest_sha256": candidate_manifest.get("eval_manifest_sha256"),
        "dataset_sha256": candidate_manifest.get("dataset_sha256"),
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "b0_recompute_max_abs": maximum_b0_difference,
        "lambda_weight": args.lambda_weight,
        "diffusion_sigmas": list(sigmas),
        "artifact": str(artifact_path),
        "artifact_sha256": sha256_file(artifact_path),
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
            "peak_cuda_memory_reserved_bytes": int(
                torch.cuda.max_memory_reserved(device)
            ),
        },
    }
    atomic_write_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
