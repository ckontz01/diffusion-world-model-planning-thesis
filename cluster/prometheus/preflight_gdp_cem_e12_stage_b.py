#!/usr/bin/env python3
"""Outcome-free real-artifact preflight for E12 Stage-B P1 training."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

import gdp_cem_e12_specs as spec
from gdp_cem_e12_prism_data import PrismDPP1Dataset, load_prism_head_arrays
from gdp_cem_e12_prism_models import (
    PRISM_DP_DOC_SHA256,
    PRISM_MPPI_SHA256,
    PRISM_PRIOR_HEAD_SHA256,
    PRISM_UPSTREAM_COMMIT,
    PrismDPModel,
    PrismPriorHead,
    prism_beta_nll_loss,
    prism_pog_fusion,
)


REFERENCE_HASHES = {
    "prior_head.py": PRISM_PRIOR_HEAD_SHA256,
    "prism_mppi.py": PRISM_MPPI_SHA256,
    "docs/23_diffusion_policy_baseline.md": PRISM_DP_DOC_SHA256,
    "train_prior_head.py": "0524f78bd796665213cc1045e576dc68ae8dc2fe015084620ee6cc3340ec5881",
    "dp_baseline/dataset.py": "07a3c2706b79242c16778c8a79b3c92605e4495a58b0ffd38b7a0ee5d55d2b62",
    "dp_baseline/train.py": "e9a617a8abb9e8d9c5970c8d9ef96e237ec14170fa80068d6317f9c7e25e6feb",
    "eval_dp_prior.py": "983279b6d6fd9562061f0593efad7473a5d8312233982a3697791d499181f01e",
    "dp_prior_policy.py": "4f34dd683427ee28ff3677d97ae0603f732bda5684382101bda2a880df8af494",
    "LICENSE": "1e9c03c85e67143e960a8a3befc5cc14f14008456d563e9c3f9ac7cdbc411df5",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_protocol_crlf(path: Path) -> str:
    """Hash the audited Windows-checkout representation used in the protocol."""

    value = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(value.replace(b"\n", b"\r\n")).hexdigest()


def load_module(name: str, path: Path) -> Any:
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot load reference module {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def resolve_git_head(repository: Path) -> str:
    """Resolve a normal clone's HEAD without requiring git in the container."""

    git_dir = repository / ".git"
    if git_dir.is_file():
        marker = git_dir.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir: "):
            raise RuntimeError(f"invalid gitdir marker in {repository}")
        git_dir = (repository / marker.removeprefix("gitdir: ")).resolve()
    head = (git_dir / "HEAD").read_text(encoding="ascii").strip()
    if head.startswith("ref: "):
        reference = head.removeprefix("ref: ")
        loose = git_dir / reference
        if loose.is_file():
            head = loose.read_text(encoding="ascii").strip()
        else:
            packed = git_dir / "packed-refs"
            matches = []
            for line in packed.read_text(encoding="ascii").splitlines():
                if not line or line.startswith(("#", "^")):
                    continue
                commit, name = line.split(" ", 1)
                if name == reference:
                    matches.append(commit)
            if len(matches) != 1:
                raise RuntimeError(f"cannot resolve {reference} in {repository}")
            head = matches[0]
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise RuntimeError(f"invalid Git HEAD in {repository}: {head!r}")
    return head


def task_paths(root: Path, task: str) -> dict[str, Path]:
    task_spec = spec.TASK_SPEC[task]
    artifact = task_spec["world_model_policy"].split("/", 1)[1].replace("_", "-")
    # The on-disk directory spelling is historical and differs from policy IDs.
    artifact = {
        "pusht": "lewm-hf-22b330c",
        "reacher": "lewm",
        "cube": "lewm-hf-b0747c5",
    }[task]
    base = root / "data/stablewm/derived/acid-alternative-v1" / task / artifact
    latent = base / f"p1-flat-latents-job-{task_spec['latent_cache_job']}"
    sequence = base / f"gdp-cem-sequence-cache-job-{task_spec['sequence_cache_job']}"
    return {
        "dataset": root / "data/stablewm" / task_spec["dataset_file"],
        "latent_h5": latent / "latents.h5",
        "latent_manifest": latent / "manifest.json",
        "sequence_h5": sequence / "sequences.h5",
        "sequence_manifest": sequence / "manifest.json",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--prism-reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    protocol = args.snapshot / (
        "ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md"
    )
    source_manifest = args.snapshot / "SOURCE-MANIFEST.sha256"
    if (
        not protocol.is_file()
        or sha256_file(protocol) != spec.PROTOCOL_SHA256
        or not source_manifest.is_file()
        or args.output.exists()
        or os.access(args.snapshot, os.W_OK)
    ):
        raise RuntimeError("E12 Stage-B snapshot is not frozen")
    subprocess.run(
        ["sha256sum", "-c", source_manifest.name],
        cwd=args.snapshot,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    reference_commit = resolve_git_head(args.prism_reference)
    if reference_commit != PRISM_UPSTREAM_COMMIT:
        raise RuntimeError("public PRISM reference commit differs")
    observed_reference_hashes: dict[str, dict[str, str]] = {}
    for relative, expected in REFERENCE_HASHES.items():
        path = args.prism_reference / relative
        observed_reference_hashes[relative] = {
            "raw_lf_checkout_sha256": sha256_file(path),
            "protocol_crlf_checkout_sha256": sha256_protocol_crlf(path),
            "protocol_expected_sha256": expected,
        }
        if observed_reference_hashes[relative]["protocol_crlf_checkout_sha256"] != expected:
            raise RuntimeError(f"public PRISM reference hash differs: {relative}")
    for missing in (
        "dp_baseline/model.py",
        "dp_baseline/scheduler.py",
        "dp_baseline/policy.py",
    ):
        if (args.prism_reference / missing).exists():
            raise RuntimeError(f"PRISM-DP omitted-module status changed: {missing}")

    public_head_module = load_module(
        "e12_public_prior_head", args.prism_reference / "prior_head.py"
    )
    public_mppi_module = load_module(
        "e12_public_prism_mppi", args.prism_reference / "prism_mppi.py"
    )
    torch.manual_seed(20260820)
    public_head = public_head_module.PriorHead(
        z_dim=192, H=5, A_block=5, A_raw=2
    )
    local_head = PrismPriorHead(192, 5, 5, 2)
    local_head.load_state_dict(public_head.state_dict())
    current = torch.randn(11, 192)
    goal = torch.randn(11, 192)
    target = torch.randn(11, 5, 5, 2)
    public_mean, public_sigma = public_head(current, goal)
    local_mean, local_sigma = local_head(current, goal)
    torch.testing.assert_close(local_mean, public_mean, rtol=0.0, atol=0.0)
    torch.testing.assert_close(local_sigma, public_sigma, rtol=0.0, atol=0.0)
    torch.testing.assert_close(
        prism_beta_nll_loss(local_mean, local_sigma, target),
        public_head_module.beta_nll_loss(public_mean, public_sigma, target),
        rtol=0.0,
        atol=0.0,
    )
    base_mean = torch.randn(4, 5, 10)
    base_std = torch.rand(4, 5, 10) + 0.1
    prior_mean = torch.randn(4, 5, 10)
    prior_std = torch.rand(4, 5, 10) + 0.1
    public_fused = public_mppi_module.pog_fusion(
        base_mean, base_std, prior_mean, prior_std
    )
    local_fused = prism_pog_fusion(base_mean, base_std, prior_mean, prior_std)
    torch.testing.assert_close(local_fused[0], public_fused[0], rtol=0.0, atol=0.0)
    torch.testing.assert_close(local_fused[1], public_fused[1], rtol=0.0, atol=0.0)

    task_records: dict[str, Any] = {}
    for task in spec.TASKS:
        paths = task_paths(args.root, task)
        for path in paths.values():
            if not path.is_file():
                raise FileNotFoundError(path)
        latent_manifest = json.loads(paths["latent_manifest"].read_text(encoding="utf-8"))
        sequence_manifest = json.loads(
            paths["sequence_manifest"].read_text(encoding="utf-8")
        )
        latent_sha = sha256_file(paths["latent_h5"])
        sequence_sha = sha256_file(paths["sequence_h5"])
        dataset_stat = paths["dataset"].stat()
        if (
            latent_manifest.get("status") != "ok"
            or latent_manifest.get("kind") != "flat_frozen_encoder_latent_cache"
            or latent_manifest.get("dataset_sha256")
            != spec.TASK_SPEC[task]["dataset_sha256"]
            or latent_manifest.get("checkpoint_sha256")
            != spec.TASK_SPEC[task]["world_model_sha256"]
            or latent_manifest.get("partition_manifest_sha256")
            != spec.EXPECTED_PARTITION_SHA256[task]
            or latent_manifest.get("partitions") != ["P1"]
            or latent_manifest.get("output_h5_sha256") != latent_sha
            or sequence_manifest.get("status") != "ok"
            or sequence_manifest.get("kind")
            != "gdp_cem_p1_goal_conditioned_action_sequence_cache"
            or sequence_manifest.get("analysis_role") != "P1_only_method_development"
            or sequence_manifest.get("latent_h5_sha256") != latent_sha
            or sequence_manifest.get("output_h5_sha256") != sequence_sha
            or sequence_manifest.get("goal_offset") != 25
            or sequence_manifest.get("macro_horizon") != 5
            or sequence_manifest.get("primitive_steps_per_macro") != 5
            or sequence_manifest.get("d2_read") is not False
            or sequence_manifest.get("d3_read") is not False
            or sequence_manifest.get("protected_c1_i1_read") is not False
            or dataset_stat.st_mode & 0o222
        ):
            raise RuntimeError(f"invalid E12 P1 training lineage for {task}")
        h25 = load_prism_head_arrays(
            sequence_h5=paths["sequence_h5"],
            latent_h5=paths["latent_h5"],
            goal_mode="h25",
        )
        endframe = load_prism_head_arrays(
            sequence_h5=paths["sequence_h5"],
            latent_h5=paths["latent_h5"],
            goal_mode="endframe",
        )
        if (
            int(h25["primitive_action_dim"])
            != int(sequence_manifest["primitive_action_dim"])
            or not np.array_equal(h25["source_index"], endframe["source_index"])
            or np.array_equal(h25["goal_index"], endframe["goal_index"])
        ):
            raise RuntimeError(f"invalid E12 PRISM head goal variants for {task}")
        train_dataset = PrismDPP1Dataset(
            dataset_h5=paths["dataset"],
            sequence_h5=paths["sequence_h5"],
            latent_h5=paths["latent_h5"],
            role="P1_train",
        )
        validation_dataset = PrismDPP1Dataset(
            dataset_h5=paths["dataset"],
            sequence_h5=paths["sequence_h5"],
            latent_h5=paths["latent_h5"],
            role="P1_val",
            action_min=train_dataset.action_min,
            action_max=train_dataset.action_max,
        )
        if set(train_dataset.episode_ids.tolist()).intersection(
            validation_dataset.episode_ids.tolist()
        ):
            raise RuntimeError(f"E12 P1 roles overlap for {task}")
        item = train_dataset[0]
        if (
            item["observation"].shape != item["goal"].shape
            or item["observation"].shape != (3, 224, 224)
            or item["action"].shape != (25, train_dataset.action_dim)
            or not torch.isfinite(item["observation"]).all()
            or not torch.isfinite(item["goal"]).all()
            or not torch.isfinite(item["action"]).all()
        ):
            raise RuntimeError(f"invalid E12 PRISM-DP real item for {task}")
        dp_model = PrismDPModel(train_dataset.action_dim)
        if not 19.25e6 <= dp_model.num_params <= 19.35e6:
            raise RuntimeError(f"E12 PRISM-DP parameter count differs for {task}")
        task_records[task] = {
            "dataset": str(paths["dataset"]),
            "dataset_expected_sha256": spec.TASK_SPEC[task]["dataset_sha256"],
            "dataset_bytes": dataset_stat.st_size,
            "dataset_read_only": True,
            "latent_h5": str(paths["latent_h5"]),
            "latent_h5_sha256": latent_sha,
            "sequence_h5": str(paths["sequence_h5"]),
            "sequence_h5_sha256": sequence_sha,
            "p1_train_sequences": len(train_dataset),
            "p1_validation_sequences": len(validation_dataset),
            "p1_train_episodes": len(set(train_dataset.episode_ids.tolist())),
            "p1_validation_episodes": len(set(validation_dataset.episode_ids.tolist())),
            "action_dim": train_dataset.action_dim,
            "dp_parameter_count": dp_model.num_params,
            "real_item_shapes": {
                key: list(value.shape) for key, value in item.items()
            },
        }
        del h25, endframe, train_dataset, validation_dataset, dp_model

    output = {
        "status": "ok",
        "kind": "gdp_cem_e12_stage_b_preflight",
        "analysis_role": "P1_only_comparator_training_preflight",
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(source_manifest),
        "prism_reference_commit": reference_commit,
        "prism_reference_hashes": observed_reference_hashes,
        "prism_reference_hash_representation": (
            "protocol hashes are canonical CRLF worktree bytes; raw Prometheus "
            "LF hashes are also recorded"
        ),
        "public_prior_head_exact_parity": True,
        "public_beta_nll_exact_parity": True,
        "public_pog_exact_parity": True,
        "prism_dp_public_modules_missing": True,
        "tasks": task_records,
        "d3_outcomes_read": False,
        "d4_read": False,
        "protected_p4_c1_i1_read": False,
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "hostname": platform.node(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
