#!/usr/bin/env python3
"""One real-P1 CUDA train/sample smoke for E12's reconstructed PRISM-DP."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import time
from pathlib import Path

import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

import gdp_cem_e12_specs as spec
from gdp_cem_e12_prism_data import PrismDPP1Dataset
from gdp_cem_e12_prism_models import CosineDDIMSchedule, PrismDPModel, update_ema
from preflight_gdp_cem_e12_stage_b import task_paths


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not torch.cuda.is_available():
        raise RuntimeError("E12 GPU smoke output exists or CUDA is unavailable")
    torch.manual_seed(20260820)
    torch.cuda.manual_seed_all(20260820)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    paths = task_paths(args.root, "pusht")
    dataset = PrismDPP1Dataset(
        dataset_h5=paths["dataset"],
        sequence_h5=paths["sequence_h5"],
        latent_h5=paths["latent_h5"],
        role="P1_train",
    )
    loader = DataLoader(
        dataset,
        batch_size=8,
        shuffle=False,
        num_workers=2,
        pin_memory=True,
        persistent_workers=False,
    )
    batch = next(iter(loader))
    model = PrismDPModel(dataset.action_dim).to(device)
    ema = copy.deepcopy(model).eval().requires_grad_(False)
    schedule = CosineDDIMSchedule.build(100)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1.0e-4, weight_decay=1.0e-6)
    observation = batch["observation"].to(device)
    goal = batch["goal"].to(device)
    clean = batch["action"].to(device)
    timestep = torch.arange(8, device=device, dtype=torch.long) * 12
    generator = torch.Generator(device=device).manual_seed(20260821)
    noise = torch.randn(clean.shape, generator=generator, device=device)
    noisy = schedule.add_noise(clean, noise, timestep)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.time()
    prediction = model(noisy, timestep, observation, goal)
    loss = F.mse_loss(prediction, noise)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    update_ema(ema, model, 0.999)
    condition = ema.encode_observation(observation[:1], goal[:1])
    sample = schedule.sample(
        ema,
        condition,
        generator=torch.Generator(device=device).manual_seed(20260822),
        inference_steps=10,
    )
    torch.cuda.synchronize()
    if (
        not torch.isfinite(loss)
        or not torch.isfinite(gradient_norm)
        or sample.shape != (1, 25, dataset.action_dim)
        or not torch.isfinite(sample).all()
    ):
        raise RuntimeError("E12 PRISM-DP CUDA smoke failed")
    output = {
        "status": "ok",
        "kind": "gdp_cem_e12_prism_dp_cuda_smoke",
        "analysis_role": "P1_only_training_and_sampling_smoke",
        "task": "pusht",
        "batch_size": 8,
        "parameter_count": model.num_params,
        "loss": float(loss.detach().cpu()),
        "preclip_gradient_norm": float(gradient_norm.detach().cpu()),
        "sample_shape": list(sample.shape),
        "sample_min": float(sample.min().cpu()),
        "sample_max": float(sample.max().cpu()),
        "elapsed_seconds": time.time() - started,
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.snapshot / "SOURCE-MANIFEST.sha256"),
        "d3_outcomes_read": False,
        "d4_read": False,
        "protected_p4_c1_i1_read": False,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0),
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
