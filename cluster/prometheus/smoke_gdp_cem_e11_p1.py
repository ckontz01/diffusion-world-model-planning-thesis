#!/usr/bin/env python3
"""Four-start P1 closed-loop integration smoke for the frozen E11 treatment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import time
from pathlib import Path
from typing import Any

import hydra
import numpy as np
import stable_worldmodel as swm
import torch
from omegaconf import OmegaConf
from sklearn import preprocessing

import acid_alt_d2_models as d2
import create_gdp_cem_e11_d3_manifest as d3_manifest
import evaluate_gdp_cem_e8d_closed_loop as e8d
import evaluate_gdp_cem_e11_d3 as e11
import gdp_cem_e11_specs as spec
from acid_alternative.io_utils import resolve_policy_checkpoint
from gdp_cem_models import GoalConditionedProposalSampler, ProposalCEMSolver


SMOKE_COUNT = 4
TASK = "pusht"
SEED = 6101


def select_p1_starts(root: Path) -> list[tuple[int, int]]:
    partition = (
        root
        / "manifests/partitions/pusht-v1/episodes-seed-20260728.tsv"
    )
    with partition.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    ranked = []
    for row in rows:
        episode = int(row["episode_id"])
        length = int(row["episode_length"])
        if row["partition"] != "P1" or length <= 25:
            continue
        start = int.from_bytes(
            hashlib.sha256(f"e11-p1-smoke|{episode}".encode()).digest()[:4],
            "little",
        ) % (length - 25)
        digest = hashlib.sha256(
            f"e11-p1-smoke|{episode}|{start}".encode()
        ).hexdigest()
        ranked.append((digest, episode, start))
    ranked.sort()
    selected = [(episode, start) for _, episode, start in ranked[:SMOKE_COUNT]]
    if len(selected) != SMOKE_COUNT or len({episode for episode, _ in selected}) != SMOKE_COUNT:
        raise RuntimeError("E11 P1 smoke start selection differs")
    return selected


@torch.inference_mode()
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--proposal-summary", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E11 P1 smoke output")
    if d2.sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E11 P1 smoke protocol hash differs")
    for path in (
        args.root,
        args.code_root,
        args.stablewm_home,
        args.dataset,
        args.world_model_checkpoint,
        args.proposal_summary,
        args.protocol,
        args.source_manifest,
        args.output_dir,
    ):
        e11.reject_protected_path(Path(path))
    if (args.root / "manifests/gdp-cem-e11-d3").exists():
        raise RuntimeError("E11 P1 smoke must finish before D3 generation")
    starts = select_p1_starts(args.root)

    planner_seed = spec.derived_seed("planner", TASK, spec.PLANNER_BASE_SEEDS[0], 0)
    proposal_seed = spec.derived_seed("velocity", TASK, spec.VELOCITY_BASE_SEEDS[0], 0)
    torch.manual_seed(planner_seed)
    np.random.seed(planner_seed % (2**32))
    torch.cuda.manual_seed_all(planner_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E11 P1 smoke requires CUDA")
    device = torch.device("cuda")

    config_dir = (args.code_root / "third_party/lewm/config/eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=TASK)
    cfg.world.num_envs = SMOKE_COUNT
    cfg.world.max_episode_steps = 100
    cfg.eval.num_eval = SMOKE_COUNT
    cfg.eval.goal_offset_steps = 25
    cfg.eval.eval_budget = 50
    cfg.eval.dataset_name = spec.TASK_SPEC[TASK]["dataset_name"]
    cfg.plan_config.horizon = 5
    cfg.plan_config.receding_horizon = 5
    cfg.plan_config.action_block = 5
    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        spec.TASK_SPEC[TASK]["dataset_name"],
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("E11 P1 smoke dataset resolution differs")
    process: dict[str, Any] = {}
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
    transform = {
        "pixels": e8d.image_transform(int(cfg.eval.img_size)),
        "goal": e8d.image_transform(int(cfg.eval.img_size)),
    }
    resolved = resolve_policy_checkpoint(
        spec.TASK_SPEC[TASK]["world_model_policy"], args.stablewm_home
    )
    if resolved != args.world_model_checkpoint.resolve():
        raise RuntimeError("E11 P1 smoke world-model resolution differs")
    world_model = swm.policy.AutoCostModel(
        spec.TASK_SPEC[TASK]["world_model_policy"], cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True
    proposal_model, payload, proposal_record = e11.load_proposal(
        args.proposal_summary,
        task=TASK,
        condition="vp_true",
        seed=SEED,
        device=device,
    )
    sampler = GoalConditionedProposalSampler(
        world_model,
        proposal_model,
        kind="velocity",
        latent_mean=payload["latent_mean"],
        latent_std=payload["latent_std"],
        action_mean=payload["action_mean"],
        action_std=payload["action_std"],
        robust_low=payload["robust_low"],
        robust_high=payload["robust_high"],
        inference_steps=spec.REVERSE_EVALUATIONS,
        schedule_steps=100,
        guidance_scale=spec.GUIDANCE_SCALE,
    )
    counting_cost = e11.CountingGoalCost(world_model).to(device)
    solver = ProposalCEMSolver(
        counting_cost,
        proposal_sampler=sampler,
        proposal_fraction=1.0,
        refresh_mode="first",
        batch_size=1,
        num_samples=spec.CANDIDATE_COUNT,
        n_steps=1,
        topk=30,
        device=device,
        seed=planner_seed,
        proposal_seed=proposal_seed,
        return_mode="best",
        preserve_mean_candidate=False,
    )
    policy = swm.policy.WorldModelPolicy(
        solver=solver,
        config=swm.PlanConfig(horizon=5, receding_horizon=5, action_block=5),
        process=process,
        transform=transform,
    )
    world.set_policy(policy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.time()
    metrics = world.evaluate_from_dataset(
        dataset=dataset,
        episodes_idx=[episode for episode, _ in starts],
        start_steps=[start for _, start in starts],
        goal_offset_steps=25,
        eval_budget=50,
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        save_video=False,
        video_path=args.output_dir / "videos-disabled",
    )
    torch.cuda.synchronize()
    successes = np.asarray(metrics["episode_successes"], dtype=bool)
    proposal_diagnostics = e11.summarize_proposal_diagnostics(
        sampler.diagnostic_history
    )
    if (
        successes.shape != (SMOKE_COUNT,)
        or counting_cost.call_count <= 0
        or proposal_diagnostics["candidate_counts"] != [spec.CANDIDATE_COUNT]
        or proposal_diagnostics["mean_coordinate_std_min"] <= 0.0
        or proposal_diagnostics["boundary_fraction_max"] >= 0.25
    ):
        raise RuntimeError("E11 P1 closed-loop integration smoke failed")
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e11_p1_closed_loop_integration_smoke",
        "analysis_role": "non_confirmatory_P1_integration_only",
        "task": TASK,
        "seed": SEED,
        "starts": [
            {"episode_id": episode, "start_step": start} for episode, start in starts
        ],
        "successes": successes.astype(int).tolist(),
        "elapsed_seconds": time.time() - started,
        "lewm_cost_calls": counting_cost.call_count,
        "proposal_diagnostics": proposal_diagnostics,
        "proposal": proposal_record,
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
        "runtime": {
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": int(
                torch.cuda.max_memory_allocated(device)
            ),
        },
    }
    d3_manifest.atomic_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
