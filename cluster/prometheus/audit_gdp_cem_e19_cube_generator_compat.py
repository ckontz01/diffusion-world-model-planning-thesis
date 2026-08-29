#!/usr/bin/env python3
"""Validate the E19 Cube generator cache shim without running an episode."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from gdp_cem_e19_cube_generator_compat import (
    install_cube_generator_cache_compat,
)
from sage.eval import cube
from sage.models.action_prior import load_action_prior
from sage.models.subgoal import load_subgoal_prior
from sage.runtime.lewm import load_lewm


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lowdim_keys_and_width(stats: dict, checkpoint: dict) -> tuple[list[str], int]:
    run_args = checkpoint.get("run_manifest", {}).get("args", {})
    keys = [
        *stats.get("lowdim_keys", run_args.get("lowdim_keys", ["observation"])),
        *stats.get("goal_lowdim_keys", run_args.get("goal_lowdim_keys", [])),
    ]
    width = int(stats["lowdim_mean"].numel())
    if not keys or width <= 0:
        raise AssertionError((keys, width))
    return list(keys), width


@torch.inference_mode()
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lewm", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--action-prior", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(args.output)
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA Cube compatibility preflight requires a GPU")

    generator, generator_stats, generator_checkpoint = load_subgoal_prior(
        args.generator, device
    )
    _, prior_stats, prior_checkpoint = load_action_prior(args.action_prior, device)
    lowdim_keys, lowdim_width = lowdim_keys_and_width(
        prior_stats, prior_checkpoint
    )
    run_args = prior_checkpoint.get("run_manifest", {}).get("args", {})
    context = int(run_args.get("context_len", run_args.get("history_len", 3)))
    lewm = load_lewm(str(args.lewm), device=device, bf16=True)
    model = cube.CubeSAGEModel(
        lewm=lewm,
        generator=generator,
        generator_stats=generator_stats or prior_stats,
        prior=None,
        prior_stats=prior_stats,
        lowdim_keys=lowdim_keys,
        context_length=context,
        goal_offset_steps=50,
        action_block=5,
        device=device,
    ).to(device)
    model.eval().requires_grad_(False)

    dtype = next(lewm.parameters()).dtype
    image = torch.zeros(1, 1, 1, 3, 224, 224, device=device, dtype=dtype)
    info: dict = {
        "pixels": image.clone(),
        "prior_pixels": image[:, 0].expand(-1, context, -1, -1, -1).clone(),
        "goal": image.clone(),
        "_env_id": np.asarray([0], dtype=np.int64),
        "_plan_call": np.asarray([0], dtype=np.int64),
        "_remaining_steps": np.asarray([50], dtype=np.int64),
        "_option_duration_steps": np.asarray([25], dtype=np.int64),
    }
    for index, key in enumerate(lowdim_keys):
        width = lowdim_width if index == 0 else 0
        info[key] = torch.zeros(1, width, device=device, dtype=torch.float32)

    solver = cube.GaussianCEM(
        model,
        candidates=2,
        rounds=1,
        elites=1,
        seed=1902,
        score_batch_size=2,
    )
    expanded = solver._expand(info, 2)
    uncached_failure = None
    model._cache.clear()
    try:
        model.local_goal(expanded)
    except RuntimeError as error:
        uncached_failure = str(error)
    uncached_rank_failure_observed = bool(
        uncached_failure
        and "same number of dimensions" in uncached_failure
        and int(info["goal"].ndim) == 6
        and int(expanded["goal"].ndim) == 7
    )

    model._cache.clear()
    direct = model.local_goal(info)
    cache_entries_after_prime = len(model._cache)
    cached = model.local_goal(expanded)
    cached_exact = bool(torch.equal(direct, cached))
    cached_shape = list(cached.shape)

    install_cube_generator_cache_compat(cube)
    shim_installed = bool(
        getattr(cube.GaussianCEM.solve, "_e19_cube_cache_compat", False)
    )
    all_passed = bool(
        uncached_rank_failure_observed
        and cache_entries_after_prime == 1
        and cached_exact
        and len(cached_shape) == 3
        and shim_installed
    )
    payload = {
        "kind": "gdp_cem_e19_cube_generator_cache_compatibility_audit",
        "all_passed": all_passed,
        "lewm_sha256": sha256_file(args.lewm),
        "generator_sha256": sha256_file(args.generator),
        "action_prior_sha256": sha256_file(args.action_prior),
        "generator_checkpoint_epoch": generator_checkpoint.get("epoch"),
        "goal_rank_unexpanded": int(info["goal"].ndim),
        "goal_rank_candidate_expanded": int(expanded["goal"].ndim),
        "uncached_rank_failure_observed": uncached_rank_failure_observed,
        "uncached_error_type": "RuntimeError" if uncached_failure else None,
        "cache_entries_after_prime": cache_entries_after_prime,
        "cached_goal_shape": cached_shape,
        "cached_goal_bit_exact": cached_exact,
        "shim_installed": shim_installed,
        "official_sage_source_modified": False,
        "checkpoint_tensor_modified": False,
        "episode_executed": False,
        "performance_metric_read": False,
        "protected_metric_artifact_read": False,
        "d5_read": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
