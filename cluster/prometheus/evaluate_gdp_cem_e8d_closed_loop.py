#!/usr/bin/env python3
"""Run one frozen E8D GADR arm on the exposed D2 closed-loop starts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import hydra
import numpy as np
import stable_pretraining as spt
import stable_worldmodel as swm
import torch
from omegaconf import OmegaConf
from sklearn import preprocessing
from torchvision.transforms import v2 as transforms

import acid_alt_d2_models as d2
import evaluate_acid_alt_e3_d2 as e3
import evaluate_gdp_cem_e7p_selection as e7
from acid_alternative.action_standardization import (
    validate_planner_action_standardizer,
)
from acid_alternative.io_utils import atomic_write_json, resolve_policy_checkpoint
from gdp_cem_models import (
    ConditionalDiagonalGaussian,
    GaussianAnchoredRefinementSampler,
    JointActionDiffusion,
    ProposalCEMSolver,
)


TASKS = ("pusht", "reacher", "cube")
ARMS = (
    "b0",
    "custom_b0",
    "acid",
    "gaussian_refresh",
    "gadr_shuffled_refresh",
    "gadr_true_refresh",
    "gadr_true_first",
    "gaussian_select",
    "gadr_shuffled_select",
    "gadr_true_select",
)
PROPOSAL_ARMS = ARMS[3:]
EVAL_COUNT = 50
SCORER_SEED = 6101
PLANNER_SEED = 8301
PROPOSAL_SEED = 9101
E8D_PROTOCOL_SHA256 = "da502adde1bb53794e6552a185799ea7a19fdd557f0a927f2b1b395830f6a5ba"
E8A_PROTOCOL_SHA256 = "e6ad569e0313276bff2cf79835bcd53c4b1604113b34bacdb5004a4bae034141"
E8A_AGGREGATE_SHA256 = "d7d804d8ccf38c0b5dad3c5e46c3ad2f1a7396b892bf40d36d73d8bb16e35521"
E8A_SOURCE_MANIFEST_SHA256 = (
    "d4003deb1f5b068112dd3023ab96ce45c0e2f24efd53af8ca75c1b6e36bd5bea"
)
EXPECTED_PROPOSAL_CHECKPOINTS = {
    "pusht": {
        "diffusion_true": "c97dcc80da47121b5cb04aea5a2273af191beb9e80f87a1cca8c968e486d9242",
        "diffusion_shuffled_goal": "b18e24dba361a1358a14d3161bf5f27611c5abf6e291c7c63aed21c8ba32de09",
        "gaussian_true": "c6e73b84d2b159dc1272df494563281561a64066f096853e5142fde9838b24ff",
    },
    "reacher": {
        "diffusion_true": "5978c9fa6997aa9581d4622d41ac3a162379077ce0c183c8cad82613f5f923ca",
        "diffusion_shuffled_goal": "e642a35a0ef6fc79e6876818a01e34b366385e439e0c769bf1ef0bce55f1015c",
        "gaussian_true": "320187e4106db767fc57ea1fcc1e37eee1e767eea34f110623ef8903f1ba0b7a",
    },
    "cube": {
        "diffusion_true": "a7be54e0cbab724b361077ea62e9e6894944b4d3a73940376f0af3b43992bee4",
        "diffusion_shuffled_goal": "b147056b56cc69953b9f0d70e2c07eb4afb926444d33cbd0df4dadb58d0149b4",
        "gaussian_true": "3481fe922c93183943f84bd72a0c53ad8671db3e5f36792ee38d502920d3e3ab",
    },
}
EXPECTED_ACID_CHECKPOINTS = {
    "pusht": "6b49d24ab9a3cfdbe4695343f3a9c30723f9ee4d70c892fe603f8e9818b3f9d2",
    "reacher": "8e0a7bad0f8c9d4ce574fca611d2642e5213e8831e7db0c7b4559939146ae5ab",
    "cube": "dade8d6afd8392f475d1e56c031f330c4e72c924e2c4254c2bcca5bf6d6be416",
}
EXPECTED_RUNTIME_ARTIFACTS = {
    "pusht": {
        "dataset_name": "pusht_expert_train",
        "dataset_sha256": "b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb",
        "world_model_policy": "pusht/lewm_hf_22b330c",
        "world_model_checkpoint_sha256": "c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659",
    },
    "reacher": {
        "dataset_name": "dmc/reacher_random",
        "dataset_sha256": "85a7dddfa1801302abcb175a80a23bb69c78291dd977ce40d69aedcb9123da06",
        "world_model_policy": "reacher/lewm",
        "world_model_checkpoint_sha256": "6b03b0e39f00a601b83dc94765e4b022c48127ced762543bddb1398ce52c310d",
    },
    "cube": {
        "dataset_name": "ogbench/cube_single_expert",
        "dataset_sha256": "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625",
        "world_model_policy": "cube/lewm_hf_b0747c5",
        "world_model_checkpoint_sha256": "5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07",
    },
}


def image_transform(image_size: int):
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=image_size),
        ]
    )


def reject_protected_path(path: Path) -> None:
    tokens = {
        token
        for component in path.parts
        for token in re.split(r"[^a-z0-9]+", component.lower())
        if token
    }
    if tokens.intersection({"d3", "c1", "i1"}):
        raise RuntimeError(f"protected D3/C1/I1 path is forbidden: {path}")


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if torch.is_tensor(value):
        return value.detach().cpu().tolist()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def validate_e8a(path: Path, *, task: str) -> dict[str, Any]:
    reject_protected_path(path)
    if d2.sha256_file(path) != E8A_AGGREGATE_SHA256:
        raise RuntimeError("E8D prerequisite E8A aggregate hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    selected = value.get("selected_configuration", {})
    task_record = value.get("task_summaries", {}).get(task, {})
    task_summary = Path(task_record.get("path", ""))
    reject_protected_path(task_summary)
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e8a_p1_refinement_aggregate"
        or value.get("analysis_role") != "P1_disjoint_validation_method_rescue"
        or value.get("protocol_sha256") != E8A_PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != E8A_SOURCE_MANIFEST_SHA256
        or value.get("e8a_p1_gate_pass") is not True
        or value.get("decision")
        != "authorize_separately_frozen_exposed_d2_gadr_diagnostic"
        or value.get("eligible_configuration_count") != 2
        or selected.get("restart_timestep") != 40
        or selected.get("reverse_evaluations") != 1
        or selected.get("refined_fraction") != 0.5
        or selected.get("labels")
        != {"shuffled": "shuffled_r40_k1_q50", "true": "true_r40_k1_q50"}
        or not selected.get("gates")
        or not all(selected["gates"].values())
        or not task_summary.is_file()
        or d2.sha256_file(task_summary) != task_record.get("sha256")
        or value.get("d2_read") is not False
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError("E8D prerequisite E8A decision differs")
    return value


def load_proposals(
    summary_values: list[list[str]], *, task: str, device: torch.device
) -> tuple[dict[str, torch.nn.Module], dict[str, dict[str, Any]], dict[str, Any]]:
    paths = {condition: Path(path) for condition, path in summary_values}
    if set(paths) != set(e7.CONDITIONS):
        raise RuntimeError("E8D requires exactly three proposal summaries")
    models: dict[str, torch.nn.Module] = {}
    payloads: dict[str, dict[str, Any]] = {}
    records: dict[str, dict[str, Any]] = {}
    for condition in e7.CONDITIONS:
        reject_protected_path(paths[condition])
        raw_summary = json.loads(paths[condition].read_text(encoding="utf-8"))
        reject_protected_path(Path(raw_summary.get("checkpoint", "")))
        models[condition], payloads[condition], records[condition] = e7.load_checkpoint(
            paths[condition], task=task, condition=condition, device=device
        )
        if (
            records[condition]["checkpoint_sha256"]
            != EXPECTED_PROPOSAL_CHECKPOINTS[task][condition]
        ):
            raise RuntimeError("E8D proposal checkpoint differs from E8A")
    for key in (
        "latent_mean",
        "latent_std",
        "action_mean",
        "action_std",
        "robust_low",
        "robust_high",
    ):
        reference = torch.as_tensor(payloads["diffusion_true"][key]).float()
        if any(
            not torch.equal(reference, torch.as_tensor(payloads[item][key]).float())
            for item in e7.CONDITIONS[1:]
        ):
            raise RuntimeError(f"E8D proposal statistic differs: {key}")
    if not (
        isinstance(models["diffusion_true"], JointActionDiffusion)
        and isinstance(models["diffusion_shuffled_goal"], JointActionDiffusion)
        and isinstance(models["gaussian_true"], ConditionalDiagonalGaussian)
    ):
        raise RuntimeError("E8D proposal model classes differ")
    return models, payloads, records


def build_sampler(
    *,
    arm: str,
    world_model: torch.nn.Module,
    models: dict[str, torch.nn.Module],
    payload: dict[str, Any],
) -> GaussianAnchoredRefinementSampler:
    gaussian = models["gaussian_true"]
    assert isinstance(gaussian, ConditionalDiagonalGaussian)
    if arm.startswith("gaussian_"):
        condition = "gaussian"
        refinement = None
    elif "shuffled" in arm:
        condition = "shuffled"
        refinement = models["diffusion_shuffled_goal"]
    else:
        condition = "true"
        refinement = models["diffusion_true"]
    assert refinement is None or isinstance(refinement, JointActionDiffusion)
    return GaussianAnchoredRefinementSampler(
        world_model,
        gaussian,
        refinement,
        condition=condition,
        latent_mean=payload["latent_mean"],
        latent_std=payload["latent_std"],
        action_mean=payload["action_mean"],
        action_std=payload["action_std"],
        robust_low=payload["robust_low"],
        robust_high=payload["robust_high"],
        restart_timestep=40,
        inference_steps=1,
        refined_fraction=0.5,
        schedule_steps=100,
    )


@torch.inference_mode()
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--method-protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--e8a-aggregate", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--world-model-policy", required=True)
    parser.add_argument("--world-model-checkpoint", type=Path, required=True)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--eval-provenance", type=Path, required=True)
    parser.add_argument("--proposal-summary", nargs=2, action="append", default=[])
    parser.add_argument("--acid-checkpoint", type=Path)
    parser.add_argument("--save-video", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    required = (
        args.protocol,
        args.method_protocol,
        args.source_manifest,
        args.e8a_aggregate,
        args.code_root,
        args.stablewm_home,
        args.dataset,
        args.world_model_checkpoint,
        args.eval_manifest,
        args.eval_provenance,
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
        reject_protected_path(path)
    reject_protected_path(args.output_dir)
    for _, path in args.proposal_summary:
        reject_protected_path(Path(path))
    if args.acid_checkpoint is not None:
        reject_protected_path(args.acid_checkpoint)
    snapshot_root = Path(__file__).resolve().parent
    expected_snapshot_files = {
        args.protocol.resolve(): snapshot_root
        / "ACID-ALTERNATIVE-E8D-GADR-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md",
        args.method_protocol.resolve(): snapshot_root
        / "ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md",
        args.source_manifest.resolve(): snapshot_root / "SOURCE-MANIFEST.sha256",
    }
    if any(actual != expected.resolve() for actual, expected in expected_snapshot_files.items()):
        raise RuntimeError("E8D protocol/source files are not from the executing snapshot")
    if (
        d2.sha256_file(args.protocol) != E8D_PROTOCOL_SHA256
        or d2.sha256_file(args.method_protocol) != d2.PROTOCOL_SHA256
    ):
        raise RuntimeError("E8D protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E8D output")
    if args.arm == "acid":
        if args.acid_checkpoint is None or args.proposal_summary:
            raise ValueError("E8D ACID requires only its checkpoint")
    elif args.arm in PROPOSAL_ARMS:
        if args.acid_checkpoint is not None or len(args.proposal_summary) != 3:
            raise ValueError("E8D proposal arm requires three proposal summaries")
    elif args.acid_checkpoint is not None or args.proposal_summary:
        raise ValueError("E8D baseline arm received a scorer")

    e8a = validate_e8a(args.e8a_aggregate, task=args.task)
    expected_runtime = EXPECTED_RUNTIME_ARTIFACTS[args.task]
    world_model_checkpoint_sha256 = d2.sha256_file(args.world_model_checkpoint)
    manifest_provenance = json.loads(args.eval_provenance.read_text(encoding="utf-8"))
    if (
        args.dataset_name != expected_runtime["dataset_name"]
        or args.world_model_policy != expected_runtime["world_model_policy"]
        or manifest_provenance.get("dataset_sha256")
        != expected_runtime["dataset_sha256"]
        or world_model_checkpoint_sha256
        != expected_runtime["world_model_checkpoint_sha256"]
    ):
        raise RuntimeError("E8D dataset/world-model lineage differs")
    rows = e3.read_d2_manifest(
        args.eval_manifest,
        args.eval_provenance,
        task=args.task,
        dataset=args.dataset,
        source_manifest=args.source_manifest,
    )

    torch.manual_seed(PLANNER_SEED)
    np.random.seed(PLANNER_SEED)
    torch.cuda.manual_seed_all(PLANNER_SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError("E8D closed-loop evaluation requires CUDA")
    device = torch.device("cuda")

    config_dir = (args.code_root / "third_party" / "lewm" / "config" / "eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(config_name=args.task)
    cfg.world.num_envs = EVAL_COUNT
    cfg.world.max_episode_steps = 100
    cfg.eval.num_eval = EVAL_COUNT
    cfg.eval.goal_offset_steps = 25
    cfg.eval.eval_budget = 50
    cfg.eval.dataset_name = args.dataset_name
    cfg.plan_config.horizon = 5
    cfg.plan_config.receding_horizon = 5
    cfg.plan_config.action_block = 5

    world = swm.World(**cfg.world, image_shape=(224, 224))
    dataset = swm.data.HDF5Dataset(
        args.dataset_name,
        keys_to_cache=list(cfg.dataset.keys_to_cache),
        cache_dir=args.stablewm_home,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("E8D dataset-name resolves to a different file")
    transform = {
        "pixels": image_transform(int(cfg.eval.img_size)),
        "goal": image_transform(int(cfg.eval.img_size)),
    }
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

    resolved_checkpoint = resolve_policy_checkpoint(
        args.world_model_policy, args.stablewm_home
    )
    if resolved_checkpoint != args.world_model_checkpoint.resolve():
        raise RuntimeError("E8D world-model policy resolves differently")
    world_model = swm.policy.AutoCostModel(
        args.world_model_policy, cache_dir=args.stablewm_home
    ).to(device).eval().requires_grad_(False)
    if hasattr(world_model, "interpolate_pos_encoding"):
        world_model.interpolate_pos_encoding = True

    scorer_record = None
    proposal_records = None
    proposal_sampler = None
    cost_model: Any = world_model
    if args.arm == "acid":
        assert args.acid_checkpoint is not None
        scorer, payload, scorer_record = d2.load_core_scorer(
            args.acid_checkpoint,
            arm="acid",
            expected_seed=SCORER_SEED,
            device=device,
        )
        if scorer_record["checkpoint_sha256"] != EXPECTED_ACID_CHECKPOINTS[args.task]:
            raise RuntimeError("E8D ACID checkpoint hash differs")
        processor = process.get("action")
        if processor is None:
            raise RuntimeError("E8D has no action standardizer")
        action_standardization = validate_planner_action_standardizer(
            dataset.get_col_data("action"),
            processor.mean_,
            processor.scale_,
            np.asarray(payload["planner_primitive_action_mean"], dtype=np.float64),
            np.asarray(payload["planner_primitive_action_std"], dtype=np.float64),
        )
        cost_model = d2.D2CostModel(
            world_model,
            arm="acid",
            task=args.task,
            planner_seed=PLANNER_SEED,
            scorer=scorer,
            payload=payload,
            horizon=5,
            record_diagnostics=True,
        ).to(device)
    else:
        action_standardization = None

    models = None
    if args.arm in PROPOSAL_ARMS:
        models, payloads, proposal_records = load_proposals(
            args.proposal_summary, task=args.task, device=device
        )
        proposal_sampler = build_sampler(
            arm=args.arm,
            world_model=world_model,
            models=models,
            payload=payloads["diffusion_true"],
        )

    plan_config = swm.PlanConfig(horizon=5, receding_horizon=5, action_block=5)
    if args.arm in {"b0", "acid"}:
        solver: Any = swm.solver.CEMSolver(
            model=cost_model,
            batch_size=1,
            num_samples=300,
            var_scale=1.0,
            n_steps=30,
            topk=30,
            device=device,
            seed=PLANNER_SEED,
        )
        integration = "released_cem"
    else:
        selector = args.arm.endswith("_select")
        if args.arm == "custom_b0":
            proposal_fraction = 0.0
            refresh_mode = "none"
        else:
            proposal_fraction = 1.0 if selector else 0.5
            refresh_mode = "first" if selector or args.arm == "gadr_true_first" else "all"
        solver = ProposalCEMSolver(
            world_model,
            proposal_sampler=proposal_sampler,
            proposal_fraction=proposal_fraction,
            refresh_mode=refresh_mode,
            batch_size=1,
            num_samples=300,
            var_scale=1.0,
            n_steps=1 if selector else 30,
            topk=30,
            device=device,
            seed=PLANNER_SEED,
            proposal_seed=PROPOSAL_SEED,
            return_mode="best" if selector else "mean",
            preserve_mean_candidate=not selector,
        )
        integration = "selector" if selector else refresh_mode
    policy = swm.policy.WorldModelPolicy(
        solver=solver,
        config=plan_config,
        process=process,
        transform=transform,
    )
    world.set_policy(policy)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    resolved_config = {
        "task": args.task,
        "arm": args.arm,
        "scorer_seed": SCORER_SEED,
        "planner_seed": PLANNER_SEED,
        "proposal_seed": PROPOSAL_SEED,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "cem_samples": 300,
        "cem_steps": 1 if args.arm.endswith("_select") else 30,
        "cem_topk": 30,
        "proposal_injection_fraction": (
            1.0 if args.arm.endswith("_select") else 0.5 if args.arm in PROPOSAL_ARMS else 0.0
        ),
        "proposal_refresh": integration,
        "preserve_cem_mean": not args.arm.endswith("_select"),
        "return_mode": "best" if args.arm.endswith("_select") else "mean",
        "gadr_restart_timestep": 40 if args.arm in PROPOSAL_ARMS else None,
        "gadr_reverse_evaluations": 1 if args.arm in PROPOSAL_ARMS else None,
        "gadr_refined_fraction": 0.5 if args.arm in PROPOSAL_ARMS else None,
        "gadr_rounding": "floor((M-1)*fraction+0.5)",
        "acid_lambda": 0.07 if args.arm == "acid" else None,
        "acid_noise_stream": (
            "SHA-256(task, scorer seed, planner seed, cost-call index)"
            if args.arm == "acid"
            else None
        ),
        "action_standardization": action_standardization,
        "world": OmegaConf.to_container(cfg.world, resolve=True),
        "callables": OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
    }
    atomic_write_json(args.output_dir / "resolved-config.json", resolved_config)

    torch.cuda.reset_peak_memory_stats(device)
    started = time.time()
    metrics = world.evaluate_from_dataset(
        dataset=dataset,
        episodes_idx=[int(row["episode_id"]) for row in rows],
        start_steps=[int(row["start_step"]) for row in rows],
        goal_offset_steps=25,
        eval_budget=50,
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        save_video=args.save_video,
        video_path=args.output_dir / "videos",
    )
    torch.cuda.synchronize()
    elapsed = time.time() - started
    successes = np.asarray(metrics["episode_successes"], dtype=bool)
    if successes.shape != (EVAL_COUNT,):
        raise RuntimeError("E8D evaluator returned an unexpected episode count")

    solver_diagnostics = list(getattr(solver, "diagnostic_history", []))
    cost_diagnostics = list(getattr(cost_model, "diagnostic_history", []))
    proposal_diagnostics = (
        list(proposal_sampler.diagnostic_history) if proposal_sampler is not None else []
    )
    expected_solver_calls = (
        100
        if args.arm.endswith("_select")
        else 3000
        if args.arm not in {"b0", "acid"}
        else 0
    )
    expected_cost_calls = 3000 if args.arm == "acid" else 0
    expected_proposal_calls = (
        100
        if args.arm.endswith("_select") or args.arm == "gadr_true_first"
        else 3000
        if args.arm in PROPOSAL_ARMS
        else 0
    )
    if (
        len(solver_diagnostics) != expected_solver_calls
        or len(cost_diagnostics) != expected_cost_calls
        or len(proposal_diagnostics) != expected_proposal_calls
    ):
        raise RuntimeError("E8D solver/proposal call count differs")

    episode_path = args.output_dir / "episodes.tsv"
    with episode_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("eval_index", "episode_id", "start_step", "arm", "success"),
            delimiter="\t",
        )
        writer.writeheader()
        for row, success in zip(rows, successes.tolist()):
            writer.writerow(
                {
                    "eval_index": row["eval_index"],
                    "episode_id": row["episode_id"],
                    "start_step": row["start_step"],
                    "arm": args.arm,
                    "success": int(success),
                }
            )
    solver_path = args.output_dir / "solver-diagnostics.jsonl"
    with solver_path.open("x", encoding="utf-8") as stream:
        for record in solver_diagnostics:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    proposal_path = args.output_dir / "proposal-diagnostics.jsonl"
    with proposal_path.open("x", encoding="utf-8") as stream:
        for record in proposal_diagnostics:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    cost_path = args.output_dir / "cost-diagnostics.jsonl"
    with cost_path.open("x", encoding="utf-8") as stream:
        for record in cost_diagnostics:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    summary = {
        "status": "ok",
        "kind": "gdp_cem_e8d_exposed_d2_closed_loop_evaluation",
        "analysis_role": "post_E8A_exposed_D2_one_seed_development",
        "task": args.task,
        "arm": args.arm,
        "scorer_seed": SCORER_SEED,
        "planner_seed": PLANNER_SEED,
        "proposal_seed": PROPOSAL_SEED,
        "metrics": jsonable(metrics),
        "success_count": int(successes.sum()),
        "episode_count": EVAL_COUNT,
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "protocol": str(args.protocol),
        "protocol_sha256": E8D_PROTOCOL_SHA256,
        "method_protocol_sha256": d2.PROTOCOL_SHA256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "e8a_aggregate": str(args.e8a_aggregate),
        "e8a_aggregate_sha256": E8A_AGGREGATE_SHA256,
        "e8a_decision": e8a["decision"],
        "eval_manifest": str(args.eval_manifest),
        "eval_manifest_sha256": d2.sha256_file(args.eval_manifest),
        "eval_provenance": str(args.eval_provenance),
        "eval_provenance_sha256": d2.sha256_file(args.eval_provenance),
        "dataset": str(args.dataset),
        # read_d2_manifest byte-hashed the dataset and matched this value to the
        # immutable D2 provenance.  Reuse that audited digest rather than
        # reading a 40--93 GB HDF5 file a second time in every array job.
        "dataset_sha256": expected_runtime["dataset_sha256"],
        "world_model_policy": args.world_model_policy,
        "world_model_checkpoint": str(args.world_model_checkpoint),
        "world_model_checkpoint_sha256": world_model_checkpoint_sha256,
        "resolved_world_model_checkpoint": str(resolved_checkpoint),
        "acid_scorer": scorer_record,
        "proposal_models": proposal_records,
        "resolved_config": resolved_config,
        "episodes_tsv": str(episode_path),
        "episodes_tsv_sha256": d2.sha256_file(episode_path),
        "solver_diagnostics": str(solver_path),
        "solver_diagnostics_sha256": d2.sha256_file(solver_path),
        "solver_diagnostic_count": len(solver_diagnostics),
        "proposal_diagnostics": str(proposal_path),
        "proposal_diagnostics_sha256": d2.sha256_file(proposal_path),
        "proposal_diagnostic_count": len(proposal_diagnostics),
        "cost_diagnostics": str(cost_path),
        "cost_diagnostics_sha256": d2.sha256_file(cost_path),
        "cost_diagnostic_count": len(cost_diagnostics),
        "proposal_seconds_total": float(
            sum(float(item.get("proposal_seconds", 0.0)) for item in solver_diagnostics)
        ),
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
            "peak_cuda_memory_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
        },
        "d2_read": True,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
