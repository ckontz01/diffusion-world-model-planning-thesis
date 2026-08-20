#!/usr/bin/env python3
"""Real-cache CUDA and lineage preflight for the E4 P1 training array."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from acid_alt_e4_models import (
    ConditionalActionDenoiser,
    count_parameters,
    reconstruction_energy,
)


EXPECTED_PROTOCOL_SHA256 = (
    "eec19adf1558a7366bbc13bd5077c5c26ac4dd73fd5c03b5be2651fe288dfc12"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def reject_protected_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/").lower()
    protected = ("/c1/", "/i1/", "c1-confirm", "i1-ident")
    if any(token in normalized for token in protected):
        raise RuntimeError(f"protected C1/I1 path rejected: {path}")


def parse_task_spec(value: str) -> tuple[str, list[Path]]:
    fields = value.split("=", 5)
    if len(fields) != 6:
        raise argparse.ArgumentTypeError(
            "task spec must be task=latent_h5=latent_manifest=transition_h5="
            "transition_manifest=acid_checkpoint"
        )
    task = fields[0]
    if task not in {"pusht", "reacher", "cube"}:
        raise argparse.ArgumentTypeError(f"invalid task {task}")
    return task, [Path(field) for field in fields[1:]]


def inspect_task(task: str, paths: list[Path], device: torch.device) -> dict[str, Any]:
    latent_h5, latent_manifest_path, transition_h5, transition_manifest_path, acid = paths
    for path in paths:
        reject_protected_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    latent_manifest = json.loads(latent_manifest_path.read_text(encoding="utf-8"))
    transition_manifest = json.loads(
        transition_manifest_path.read_text(encoding="utf-8")
    )
    if (
        latent_manifest.get("status") != "ok"
        or sha256_file(latent_h5) != latent_manifest.get("output_h5_sha256")
    ):
        raise RuntimeError(f"{task}: latent lineage failed")
    if (
        transition_manifest.get("status") != "ok"
        or transition_manifest.get("kind") != "flat_one_model_step_transition_cache"
        or sha256_file(transition_h5)
        != transition_manifest.get("output_h5_sha256")
        or transition_manifest.get("latent_h5_sha256")
        != latent_manifest.get("output_h5_sha256")
    ):
        raise RuntimeError(f"{task}: transition lineage failed")

    with h5py.File(transition_h5, "r") as handle:
        source = np.asarray(handle["source_index"][:32], dtype=np.int64)
        target = np.asarray(handle["target_index"][:32], dtype=np.int64)
        action = np.asarray(handle["action"][:32], dtype=np.float32)
        latent_mean = np.asarray(handle["stats/latent_mean"][:], dtype=np.float32)
        latent_std = np.asarray(handle["stats/latent_std"][:], dtype=np.float32)
        action_mean = np.asarray(handle["stats/acid_action_mean"][:], dtype=np.float32)
        action_std = np.asarray(handle["stats/acid_action_std"][:], dtype=np.float32)
        pair_total = len(handle["source_index"])
    with h5py.File(latent_h5, "r") as handle:
        latent_dataset = handle["latent"]
        latent_total = len(latent_dataset)
        current_rows = np.stack(
            [np.asarray(latent_dataset[int(index)], dtype=np.float32) for index in source]
        )
        target_rows = np.stack(
            [np.asarray(latent_dataset[int(index)], dtype=np.float32) for index in target]
        )
    if max(int(source.max()), int(target.max())) >= latent_total:
        raise RuntimeError(f"{task}: transition index exceeds latent cache")
    if (
        current_rows.shape[1] != len(latent_mean)
        or action.shape[1] != len(action_mean)
        or np.any(latent_std <= 1.0e-6)
        or np.any(action_std <= 1.0e-6)
    ):
        raise RuntimeError(f"{task}: inconsistent or degenerate cache statistics")

    acid_payload = torch.load(acid, map_location="cpu", weights_only=False)
    if acid_payload.get("model_name") != "acid":
        raise RuntimeError(f"{task}: reference checkpoint is not ACID")
    acid_parameters = sum(
        value.numel() for value in acid_payload["state_dict"].values()
    )
    model = ConditionalActionDenoiser(len(latent_mean), len(action_mean)).to(device)
    e4_parameters = count_parameters(model)
    relative_difference = abs(e4_parameters - acid_parameters) / acid_parameters
    if relative_difference > 0.10:
        raise RuntimeError(f"{task}: E4/ACID capacity difference exceeds 10%")

    # Use real cache dimensions and values for a CUDA forward/backward smoke.
    current = torch.from_numpy(
        (current_rows - latent_mean) / latent_std
    ).to(device)
    successor = torch.from_numpy(
        (target_rows - latent_mean) / latent_std
    ).to(device)
    clean_action = torch.from_numpy((action - action_mean) / action_std).to(device)
    sigma = torch.tensor(
        [0.25, 0.5, 1.0, 2.0, 4.0] * 7, device=device
    )[: len(clean_action)]
    generator = torch.Generator(device=device.type).manual_seed(20260816106)
    noise = torch.randn(
        clean_action.shape, generator=generator, device=device, dtype=clean_action.dtype
    )
    prediction = model(
        current,
        successor,
        clean_action + sigma[:, None] * noise,
        sigma,
        torch.ones(len(clean_action), device=device),
    )
    loss = reconstruction_energy(prediction, clean_action).mean()
    loss.backward()
    if not torch.isfinite(loss) or not all(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        raise RuntimeError(f"{task}: real-cache CUDA forward/backward failed")
    return {
        "task": task,
        "latent_dim": len(latent_mean),
        "action_dim": len(action_mean),
        "latent_rows": latent_total,
        "transition_pairs": pair_total,
        "e4_parameter_count": e4_parameters,
        "acid_parameter_count": acid_parameters,
        "relative_capacity_difference": relative_difference,
        "smoke_loss": float(loss.detach().cpu()),
        "latent_h5_sha256": latent_manifest["output_h5_sha256"],
        "transition_h5_sha256": transition_manifest["output_h5_sha256"],
        "acid_checkpoint_sha256": sha256_file(acid),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-spec", action="append", type=parse_task_spec, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.task_spec) != 3 or {task for task, _ in args.task_spec} != {
        "pusht",
        "reacher",
        "cube",
    }:
        raise RuntimeError("exactly one spec for each of PushT, Reacher, Cube is required")
    for path in (args.protocol, args.source_manifest):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("E4 protocol hash mismatch")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for E4 preflight")
    device = torch.device("cuda")
    results = [inspect_task(task, paths, device) for task, paths in args.task_spec]
    payload = {
        "status": "pass",
        "kind": "e4_p0_real_cache_cuda_preflight",
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "tasks": results,
        "gpu": torch.cuda.get_device_name(device),
        "torch": torch.__version__,
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "protected_c1_i1_read": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
