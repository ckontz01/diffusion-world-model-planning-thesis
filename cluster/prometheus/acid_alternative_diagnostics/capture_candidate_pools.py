#!/usr/bin/env python3
"""Capture final B0 CEM populations on a frozen flat-development manifest."""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
import time
from copy import deepcopy
from importlib import metadata
from pathlib import Path
from typing import Any

import hydra
import numpy as np
import stable_pretraining as spt
import stable_worldmodel as swm
import torch
from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.evaluate_matched import read_eval_manifest
from acid_alternative.io_utils import (
    atomic_write_json,
    resolve_policy_checkpoint,
    sha256_file,
)
from omegaconf import OmegaConf
from sklearn import preprocessing
from torchvision.transforms import v2 as transforms


def image_transform(image_size: int):
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=image_size),
        ]
    )


def atomic_torch_save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.partial-", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(payload, temporary)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class FinalPopulationRecorder:
    """Transparent wrapper retaining each environment's final CEM population."""

    def __init__(
        self, base_model: SharedRolloutCostModel, *, iterations: int, topk: int
    ) -> None:
        if iterations <= 0 or topk <= 0:
            raise ValueError("iterations and topk must be positive")
        self.base_model = base_model
        self.iterations = iterations
        self.topk = topk
        self.call_count = 0
        self.candidates: list[torch.Tensor] = []
        self.costs: list[torch.Tensor] = []
        self.elite_means: list[torch.Tensor] = []
        self.info_tensors: list[dict[str, torch.Tensor]] = []

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        costs = self.base_model.get_cost(info_dict, action_candidates)
        self.call_count += 1
        if self.call_count % self.iterations != 0:
            return costs
        if action_candidates.shape[0] != 1 or costs.shape[0] != 1:
            raise RuntimeError("candidate recorder requires solver batch_size=1")
        if self.topk > action_candidates.shape[1]:
            raise RuntimeError("top-k exceeds final population")
        indices = torch.topk(costs, k=self.topk, dim=1, largest=False).indices
        batch = torch.zeros_like(indices)
        elite_mean = action_candidates[batch, indices].mean(dim=1)[0]
        captured_info: dict[str, torch.Tensor] = {}
        for key, value in info_dict.items():
            if torch.is_tensor(value):
                captured_info[key] = value[0, 0].detach().cpu().clone()
            elif isinstance(value, np.ndarray) and value.dtype.kind not in "USO":
                captured_info[key] = torch.from_numpy(np.asarray(value[0, 0]).copy())
        self.candidates.append(action_candidates[0].detach().cpu().clone())
        self.costs.append(costs[0].detach().cpu().clone())
        self.elite_means.append(elite_mean.detach().cpu().clone())
        self.info_tensors.append(captured_info)
        return costs


class CapturingCEMSolver(swm.solver.CEMSolver):
    """Released CEM plus an exact final-elite consistency assertion."""

    def __init__(self, *args: Any, recorder: FinalPopulationRecorder, **kwargs: Any):
        self.recorder = recorder
        self.returned_actions: torch.Tensor | None = None
        super().__init__(*args, model=recorder, **kwargs)

    def solve(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        before = len(self.recorder.elite_means)
        outputs = super().solve(*args, **kwargs)
        captured = torch.stack(self.recorder.elite_means[before:])
        returned = outputs["actions"].detach().cpu()
        if not torch.equal(captured, returned):
            difference = float((captured - returned).abs().max().item())
            raise RuntimeError(
                "captured final elites do not reproduce released CEM output: "
                f"max_abs={difference}"
            )
        self.returned_actions = returned.clone()
        return outputs


def stack_info(records: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    if not records:
        raise RuntimeError("no CEM info tensors were captured")
    keys = set(records[0])
    if any(set(record) != keys for record in records[1:]):
        raise RuntimeError("captured info keys differ between pools")
    result: dict[str, torch.Tensor] = {}
    for key in sorted(keys):
        values = [record[key] for record in records]
        if any(
            value.shape != values[0].shape or value.dtype != values[0].dtype
            for value in values
        ):
            raise RuntimeError(f"captured info tensor {key} has inconsistent metadata")
        result[key] = torch.stack(values)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument(
        "--eval-config-name", choices=("pusht", "reacher", "cube"), required=True
    )
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument(
        "--analysis-role", choices=("D1", "D2", "C1"), required=True
    )
    parser.add_argument("--confirmation-authorization", type=Path)
    parser.add_argument("--planner-seed", type=int, required=True)
    parser.add_argument("--goal-offset", type=int, default=25)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--receding-horizon", type=int, default=5)
    parser.add_argument("--action-block", type=int, default=5)
    parser.add_argument("--cem-samples", type=int, default=300)
    parser.add_argument("--cem-steps", type=int, default=30)
    parser.add_argument("--cem-topk", type=int, default=30)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        args.code_root,
        args.dataset,
        args.world_model_checkpoint,
        args.source_manifest,
        args.eval_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.analysis_role == "C1":
        if (
            args.confirmation_authorization is None
            or not args.confirmation_authorization.is_file()
        ):
            raise FileNotFoundError("C1 capture requires its authorization")
    elif args.confirmation_authorization is not None:
        raise ValueError("development capture must not receive a C1 authorization")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    if args.cem_topk > args.cem_samples:
        raise ValueError("CEM top-k exceeds population")
    rows = read_eval_manifest(args.eval_manifest, args.goal_offset)
    torch.manual_seed(args.planner_seed)
    np.random.seed(args.planner_seed)
    torch.cuda.manual_seed_all(args.planner_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("candidate capture requires CUDA")

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.eval_config_name)
    cfg.world.num_envs = len(rows)
    cfg.world.max_episode_steps = 2 * args.goal_offset
    cfg.eval.num_eval = len(rows)
    cfg.eval.goal_offset_steps = args.goal_offset
    cfg.eval.eval_budget = 1
    cfg.eval.dataset_name = args.dataset_name
    cfg.plan_config.horizon = args.horizon
    cfg.plan_config.receding_horizon = args.receding_horizon
    cfg.plan_config.action_block = args.action_block

    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        args.dataset_name,
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("dataset name resolves to different bytes")
    transform = {
        "pixels": image_transform(int(cfg.eval.img_size)),
        "goal": image_transform(int(cfg.eval.img_size)),
    }
    process = {}
    for column in cfg.dataset.keys_to_cache:
        if column == "pixels":
            continue
        processor = preprocessing.StandardScaler()
        values = dataset.get_col_data(column)
        values = values[~np.isnan(values).any(axis=1)]
        processor.fit(values)
        process[column] = processor
        if column != "action":
            process[f"goal_{column}"] = processor

    resolved_checkpoint = resolve_policy_checkpoint(
        args.world_model_policy, args.stablewm_home
    )
    if resolved_checkpoint != args.world_model_checkpoint.resolve():
        raise RuntimeError("resolved world-model checkpoint differs from declaration")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    )
    world_model = world_model.to(device).eval()
    world_model.requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    b0 = SharedRolloutCostModel(
        world_model,
        arm="b0",
        horizon=args.horizon,
        record_diagnostics=False,
    ).to(device)
    recorder = FinalPopulationRecorder(
        b0, iterations=args.cem_steps, topk=args.cem_topk
    )
    solver = CapturingCEMSolver(
        recorder=recorder,
        batch_size=1,
        num_samples=args.cem_samples,
        var_scale=1.0,
        n_steps=args.cem_steps,
        topk=args.cem_topk,
        device=device,
        seed=args.planner_seed,
    )
    policy = swm.policy.WorldModelPolicy(
        solver=solver,
        config=swm.PlanConfig(
            horizon=args.horizon,
            receding_horizon=args.receding_horizon,
            action_block=args.action_block,
        ),
        process=process,
        transform=transform,
    )
    world.set_policy(policy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.time()
    # One environment action is sufficient to trigger the initial full CEM
    # solve. No success metric from this setup step is retained or analyzed.
    world.evaluate_from_dataset(
        dataset=dataset,
        episodes_idx=[int(row["episode_id"]) for row in rows],
        start_steps=[int(row["start_step"]) for row in rows],
        goal_offset_steps=args.goal_offset,
        eval_budget=1,
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        save_video=False,
    )
    torch.cuda.synchronize()
    elapsed = time.time() - started
    expected_calls = len(rows) * args.cem_steps
    if recorder.call_count != expected_calls or len(recorder.candidates) != len(rows):
        raise RuntimeError(
            f"expected {expected_calls} calls/{len(rows)} pools, observed "
            f"{recorder.call_count}/{len(recorder.candidates)}"
        )
    if solver.returned_actions is None:
        raise RuntimeError("capturing solver did not retain returned actions")

    artifact_path = args.output_dir / "candidate-pools.pt"
    payload = {
        "format_version": 1,
        "kind": "flat_b0_final_cem_candidate_pools",
        "planner_seed": args.planner_seed,
        "rows": deepcopy(rows),
        "candidates": torch.stack(recorder.candidates),
        "b0_cost": torch.stack(recorder.costs),
        "returned_actions": solver.returned_actions,
        "info_tensors": stack_info(recorder.info_tensors),
        # Preserve sklearn's float64 fitted statistics. The executor applies
        # them in-place to float32 candidates, matching inverse_transform.
        "planner_primitive_action_mean": torch.as_tensor(
            process["action"].mean_, dtype=torch.float64
        ),
        "planner_primitive_action_std": torch.as_tensor(
            process["action"].scale_, dtype=torch.float64
        ),
        "configuration": {
            "horizon": args.horizon,
            "receding_horizon": args.receding_horizon,
            "action_block": args.action_block,
            "cem_samples": args.cem_samples,
            "cem_steps": args.cem_steps,
            "cem_topk": args.cem_topk,
            "goal_offset": args.goal_offset,
        },
    }
    atomic_torch_save(artifact_path, payload)
    manifest = {
        "status": "ok",
        "kind": payload["kind"],
        "analysis_role": args.analysis_role,
        "confirmation_authorization": (
            str(args.confirmation_authorization)
            if args.confirmation_authorization
            else None
        ),
        "confirmation_authorization_sha256": (
            sha256_file(args.confirmation_authorization)
            if args.confirmation_authorization
            else None
        ),
        "outcome_role": {
            "D1": "development mechanism audit; no efficacy endpoint retained",
            "D2": "fresh preregistered development mechanism audit",
            "C1": "locked confirmation mechanism audit; no primary efficacy endpoint retained",
        }[args.analysis_role],
        "eval_config_name": args.eval_config_name,
        "pool_count": len(rows),
        "candidates_per_pool": args.cem_samples,
        "artifact": str(artifact_path),
        "artifact_sha256": sha256_file(artifact_path),
        "eval_manifest": str(args.eval_manifest),
        "eval_manifest_sha256": sha256_file(args.eval_manifest),
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": sha256_file(args.world_model_checkpoint),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "planner_seed": args.planner_seed,
        "configuration": payload["configuration"],
        "elapsed_seconds": elapsed,
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
