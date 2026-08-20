#!/usr/bin/env python3
"""Outcome-free cache, row-isolation, control, and model preflight for E10V."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import torch

import evaluate_gdp_cem_e7p_selection as e7
import train_gdp_cem_vp_proposal as train
from gdp_cem_models import VelocityActionDiffusion


TASK_SPEC = {
    "pusht": {
        "artifact": "lewm-hf-22b330c",
        "latent_job": 296628,
        "cache_index": 0,
        "e7_base": 0,
    },
    "reacher": {
        "artifact": "lewm",
        "latent_job": 296647,
        "cache_index": 1,
        "e7_base": 3,
    },
    "cube": {
        "artifact": "lewm-hf-b0747c5",
        "latent_job": 296666,
        "cache_index": 2,
        "e7_base": 6,
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.root, args.source_manifest, args.protocol):
        train.reject_protected_path(path)
    if train.sha256_file(args.protocol) != train.PROTOCOL_SHA256:
        raise RuntimeError("E10V preflight protocol hash differs")
    device = torch.device("cpu")
    row_hashes = {}
    control_count = 0
    for task, spec in TASK_SPEC.items():
        base = (
            args.root
            / "data/stablewm/derived/acid-alternative-v1"
            / task
            / spec["artifact"]
        )
        latent = base / f"p1-flat-latents-job-{spec['latent_job']}"
        sequence = base / f"gdp-cem-sequence-cache-job-297698-{spec['cache_index']}"
        manifest_path = sequence / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        task_spec = e7.TASK_SPEC[task]
        if (
            train.sha256_file(manifest_path)
            != task_spec["sequence_manifest_sha256"]
            or manifest.get("output_h5_sha256") != task_spec["sequence_h5_sha256"]
            or manifest.get("latent_h5_sha256") != task_spec["latent_h5_sha256"]
            or manifest.get("d2_read") is not False
            or manifest.get("d3_read") is not False
            or manifest.get("protected_c1_i1_read") is not False
        ):
            raise RuntimeError("E10V preflight cache lineage differs")
        with h5py.File(sequence / "sequences.h5", "r") as handle:
            role = np.asarray(handle["role"][:], dtype=np.uint8)
        checkpoint, final, record = train.select_fresh_rows(
            np.flatnonzero(role == 1), task=task
        )
        if (
            len(checkpoint) != train.VALIDATION_COUNT
            or len(final) != 512
            or len(np.intersect1d(checkpoint, final))
            or record["checkpoint_rows_sha256"] != train.array_sha256(checkpoint)
            or record["final_rows_sha256"] != train.array_sha256(final)
        ):
            raise RuntimeError("E10V preflight row isolation differs")
        row_hashes[task] = {
            "checkpoint": record["checkpoint_rows_sha256"],
            "final": record["final_rows_sha256"],
        }
        conditions = ("diffusion_true", "diffusion_shuffled_goal", "gaussian_true")
        for offset, condition in enumerate(conditions):
            index = spec["e7_base"] + offset
            summary = (
                args.root
                / "results/acid-alternative/gdp-cem-e7p-proposals"
                / task
                / condition
                / f"seed-6101-job-297703-{index}/summary.json"
            )
            model, _, _ = e7.load_checkpoint(
                summary, task=task, condition=condition, device=device
            )
            del model
            control_count += 1
        config = {
            "latent_dim": 192,
            "primitive_action_dim": int(task_spec["primitive_action_dim"]),
            "action_horizon": 25,
            "width": 512,
            "depth": 4,
            "time_embedding_dim": 128,
        }
        model = VelocityActionDiffusion(**config)
        conditioned = torch.ones(2, dtype=torch.bool)
        output = model(
            torch.zeros(2, 192),
            torch.zeros(2, 192),
            torch.zeros(2, 25, config["primitive_action_dim"]),
            torch.tensor((0, 99)),
            conditioned=conditioned,
        )
        if output.shape != (2, 25, config["primitive_action_dim"]):
            raise RuntimeError("E10V preflight model shape differs")
    if control_count != 9:
        raise RuntimeError("E10V preflight control count differs")
    print(
        json.dumps(
            {
                "status": "ok",
                "controls": control_count,
                "row_hashes": row_hashes,
                "d2_read": False,
                "d3_read": False,
                "protected_c1_i1_read": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
