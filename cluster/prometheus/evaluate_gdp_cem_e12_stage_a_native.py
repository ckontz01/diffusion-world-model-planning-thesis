#!/usr/bin/env python3
"""Run one official-bundle PRISM artifact-sanity cell for E12 Stage A.

The policy, PriorHead, PoG solver, JEPA object, and trained weights are the
public PRISM artifacts.  This wrapper replaces only the upstream script's
hard-coded output path with fail-closed JSON/TSV provenance.
"""

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
import stable_pretraining as spt
import stable_worldmodel as swm
import torch
from omegaconf import OmegaConf
from sklearn import preprocessing
from torchvision.transforms import v2 as transforms

import gdp_cem_e12_specs as spec
from preflight_gdp_cem_e12_stage_b import resolve_git_head, sha256_protocol_crlf
from prism_head_policy import PrismHeadPolicy
from prism_mppi import PrismMPPISolver


PRISM_COMMIT = "baa0eb95efb812196b68796c258b1f0cf10b7625"
PRISM_SOURCE_CRLF_SHA256 = {
    "prior_head.py": "6a60613ea2acd10b9185d415868a9006acf27f1211df3b3e4758c2458921617c",
    "prism_mppi.py": "4e6d2430f4bf64c5d901c5bf4db986e8bf4436618591b983543b5e8f63cd62e6",
    "prism_head_policy.py": "eaa6f098505a39416d6ce9766c8a75866dcc2ac266835f0846354eafd447cd4e",
    "eval_prism_head.py": "75e9cb30ae79e3f66d6bd8f75ab2e81c00d93a5db4c2ea62f375aa9509e32cb0",
}
BUNDLE = {
    "cube": {
        "revision": "6da8f34ef31bf25b6eb78cd7669c862b11360046",
        "world_model": "lewm_object.ckpt",
        "world_model_sha256": "82d37a9d9338d8c23005017ab5c1ff91c8b5e3fd51fafbd620af8457c381d125",
        "head": "prior_head_cube.pt",
        "head_sha256": "0bbfacb047d7ea68370d07a56185099807cc1a9536034fbe53cdbfb3f6d78dec",
        "readme_sha256": "04ef1349322494ef1614cbd422577d28cd239516da264b14edc645235ea4b2ac",
    },
    "pusht": {
        "revision": "40461a2269da322c24738835880a3aef768828e8",
        "world_model": "lewm_object.ckpt",
        "world_model_sha256": "4f4a3c9cd30c4bb265c991cb7a4607f90bebddcb47b59e8020cf4b9279a1f0b3",
        "head": "prior_head_pusht.pt",
        "head_sha256": "e4dae35d16ada9768e7371e368508c3927ba1487fe10bd5402ff7869f1972191",
        "readme_sha256": "378e44561fcf9176b9a222a54d73b3c913012ac0e817adee5eeb2e68f8816f32",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_transform(size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Normalize(**spt.data.dataset_stats.ImageNet),
            transforms.Resize(size=size),
        ]
    )


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if torch.is_tensor(value):
        return value.detach().cpu().tolist()
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("pusht", "cube"), required=True)
    parser.add_argument("--mode", choices=("none", "pog"), required=True)
    parser.add_argument("--seed", type=int, choices=(0, 1, 42), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--prism-reference", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise RuntimeError("refusing existing E12 Stage-A output")
    for path in (args.protocol, args.source_manifest, args.dataset):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E12 Stage-A protocol differs")
    if resolve_git_head(args.prism_reference) != PRISM_COMMIT:
        raise RuntimeError("E12 Stage-A PRISM source revision differs")
    source_hashes = {
        relative: sha256_protocol_crlf(args.prism_reference / relative)
        for relative in PRISM_SOURCE_CRLF_SHA256
    }
    if source_hashes != PRISM_SOURCE_CRLF_SHA256:
        raise RuntimeError("E12 Stage-A PRISM source bytes differ")
    bundle_spec = BUNDLE[args.task]
    world_checkpoint = args.bundle_root / str(bundle_spec["world_model"])
    head_checkpoint = args.bundle_root / str(bundle_spec["head"])
    readme = args.bundle_root / "README.md"
    if (
        sha256_file(world_checkpoint) != bundle_spec["world_model_sha256"]
        or sha256_file(head_checkpoint) != bundle_spec["head_sha256"]
        or sha256_file(readme) != bundle_spec["readme_sha256"]
        or args.dataset.stat().st_mode & 0o222
    ):
        raise RuntimeError("E12 Stage-A bundle or dataset identity differs")
    if not torch.cuda.is_available() or torch.cuda.get_device_name(0) != spec.EXPECTED_GPU_NAME:
        raise RuntimeError("E12 Stage-A requires the frozen RTX 6000 Ada")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda")
    config_dir = (args.prism_reference / "config/eval").resolve()
    with hydra.initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = hydra.compose(
            config_name=args.task,
            overrides=["solver=mppi", "solver.num_samples=128", f"seed={args.seed}"],
        )
    cfg.world.max_episode_steps = 2 * int(cfg.eval.eval_budget)
    world = swm.World(**cfg.world, image_shape=(224, 224))
    transform = {
        "pixels": image_transform(int(cfg.eval.img_size)),
        "goal": image_transform(int(cfg.eval.img_size)),
    }
    dataset = swm.data.HDF5Dataset(
        str(cfg.eval.dataset_name),
        keys_to_cache=cfg.dataset.keys_to_cache,
        cache_dir=args.cache_root,
    )
    if dataset.h5_path.resolve() != args.dataset.resolve():
        raise RuntimeError("E12 Stage-A cache resolves a different dataset")
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

    world_model = swm.policy.AutoCostModel(
        str(cfg.policy).replace("random", f"{args.task}/lewm"),
        cache_dir=args.cache_root,
    ).to(device).eval().requires_grad_(False)
    world_model.interpolate_pos_encoding = True
    plan_config = swm.PlanConfig(**cfg.plan_config)
    solver = PrismMPPISolver(
        model=world_model,
        batch_size=1,
        num_samples=128,
        var_scale=1.0,
        n_steps=30,
        topk=30,
        temperature=0.5,
        device=device,
        seed=args.seed,
    )
    policy = PrismHeadPolicy(
        solver=solver,
        config=plan_config,
        process=process,
        transform=transform,
        head_ckpt=str(head_checkpoint),
        jepa_object_path=str(world_checkpoint),
        injection_mode=args.mode,
        sigma_scale=1.0,
        device="cuda",
        verbose=False,
    )

    episode_column = (
        "episode_idx" if "episode_idx" in dataset.column_names else "ep_idx"
    )
    episode_ids = np.unique(dataset.get_col_data(episode_column))
    episode_values = dataset.get_col_data(episode_column)
    step_values = dataset.get_col_data("step_idx")
    lengths = np.asarray(
        [np.max(step_values[episode_values == episode]) + 1 for episode in episode_ids]
    )
    maximum_start = lengths - int(cfg.eval.goal_offset_steps) - 1
    by_episode = {
        int(episode): int(maximum_start[index])
        for index, episode in enumerate(episode_ids)
    }
    valid = step_values <= np.asarray([by_episode[int(value)] for value in episode_values])
    valid_rows = np.nonzero(valid)[0]
    generator = np.random.default_rng(args.seed)
    selected_positions = generator.choice(
        len(valid_rows) - 1, size=int(cfg.eval.num_eval), replace=False
    )
    selected_rows = np.sort(valid_rows[selected_positions])
    selected = dataset.get_row_data(selected_rows)
    eval_episodes = np.asarray(selected[episode_column], dtype=np.int64)
    eval_starts = np.asarray(selected["step_idx"], dtype=np.int64)

    args.output_dir.mkdir(parents=True, exist_ok=False)
    rows_path = args.output_dir / "starts.tsv"
    with rows_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(("eval_index", "dataset_row", "episode_id", "start_step"))
        for index, (row, episode, start) in enumerate(
            zip(selected_rows, eval_episodes, eval_starts, strict=True)
        ):
            writer.writerow((index, int(row), int(episode), int(start)))

    world.set_policy(policy)
    torch.cuda.reset_peak_memory_stats(device)
    # stable-worldmodel 0.0.6 always constructs ``Path(video_path)`` even when
    # callers do not retain videos.  Render into job-local scratch so the
    # Slurm cleanup trap removes this non-result artifact after evaluation.
    scratch_video_path = Path(os.environ["TMPDIR"]) / "stage-a-videos-not-retained"
    started = time.time()
    metrics = world.evaluate_from_dataset(
        dataset,
        start_steps=eval_starts.tolist(),
        goal_offset_steps=int(cfg.eval.goal_offset_steps),
        eval_budget=int(cfg.eval.eval_budget),
        episodes_idx=eval_episodes.tolist(),
        callables=OmegaConf.to_container(cfg.eval.get("callables"), resolve=True),
        video_path=scratch_video_path,
    )
    elapsed = time.time() - started
    successes = np.asarray(metrics["episode_successes"], dtype=bool)
    if successes.shape != (50,):
        raise RuntimeError("E12 Stage-A episode count differs")
    output = {
        "status": "ok",
        "kind": "gdp_cem_e12_native_prism_artifact_sanity",
        "analysis_role": "native_PRISM_artifact_sanity_not_matched_claim_data",
        "task": args.task,
        "mode": args.mode,
        "seed": args.seed,
        "successes": successes.tolist(),
        "success_rate_fraction": float(successes.mean()),
        "elapsed_seconds": elapsed,
        "candidate_count": 128,
        "optimizer_steps": 30,
        "head_sigma_scale": 1.0,
        "goal_offset_steps": 25,
        "evaluation_budget": 50,
        "prism_source_commit": PRISM_COMMIT,
        "prism_source_crlf_sha256": source_hashes,
        "huggingface_revision": bundle_spec["revision"],
        "world_model_checkpoint": str(world_checkpoint),
        "world_model_sha256": bundle_spec["world_model_sha256"],
        "head_checkpoint": str(head_checkpoint),
        "head_sha256": bundle_spec["head_sha256"],
        "dataset": str(args.dataset),
        "dataset_expected_sha256": spec.TASK_SPEC[args.task]["dataset_sha256"],
        "starts_tsv": str(rows_path),
        "starts_tsv_sha256": sha256_file(rows_path),
        "metrics": jsonable(metrics),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "video_retained": False,
        "d3_outcomes_read": False,
        "d4_read": False,
        "protected_p4_c1_i1_read": False,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        },
    }
    summary_path = args.output_dir / "summary.json"
    with summary_path.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
