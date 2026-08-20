#!/usr/bin/env python3
"""Outcome-free prerequisite and row-isolation preflight for E10M."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import torch

import evaluate_gdp_cem_e7p_selection as e7
import evaluate_gdp_cem_e10v_p1 as e10v_eval
import train_gdp_cem_e10m_models as train


TASK_SPEC = {
    "pusht": {"artifact": "lewm-hf-22b330c", "latent_job": 296628, "cache_index": 0, "vp": (0, 1), "gaussian": 2},
    "reacher": {"artifact": "lewm", "latent_job": 296647, "cache_index": 1, "vp": (2, 3), "gaussian": 5},
    "cube": {"artifact": "lewm-hf-b0747c5", "latent_job": 296666, "cache_index": 2, "vp": (4, 5), "gaussian": 8},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.root, args.source_manifest, args.protocol):
        train.e10v.reject_protected_path(path)
    if train.e10v.sha256_file(args.protocol) != train.PROTOCOL_SHA256:
        raise RuntimeError("E10M preflight protocol hash differs")
    aggregate = (
        args.root
        / "results/acid-alternative/gdp-cem-e10v-p1/analysis/job-297780/summary.json"
    )
    if train.e10v.sha256_file(aggregate) != (
        "5d23323681904fe369afcb4796976782cd6e4068b90fbc0e0d163e35092bacd9"
    ):
        raise RuntimeError("E10M preflight E10V aggregate hash differs")
    value = json.loads(aggregate.read_text(encoding="utf-8"))
    selected = value.get("selected_configuration", {})
    if (
        value.get("decision")
        != "authorize_separately_frozen_multiseed_p1_velocity_replication"
        or value.get("eligible_configuration_count") != 1
        or selected.get("reverse_evaluations") != 5
        or selected.get("guidance_scale") != 1.5
        or not all(selected.get("gates", {}).values())
    ):
        raise RuntimeError("E10M preflight prerequisite decision differs")
    device = torch.device("cpu")
    row_hashes = {}
    model_count = 0
    for task, spec in TASK_SPEC.items():
        base = (
            args.root
            / "data/stablewm/derived/acid-alternative-v1"
            / task
            / spec["artifact"]
        )
        sequence = base / f"gdp-cem-sequence-cache-job-297698-{spec['cache_index']}"
        with h5py.File(sequence / "sequences.h5", "r") as handle:
            role = np.asarray(handle["role"][:], dtype=np.uint8)
        checkpoint, final, confirmation, record = train.select_confirmation_rows(
            np.flatnonzero(role == 1), task=task
        )
        if (
            len(checkpoint) != 8_192
            or len(final) != 512
            or len(confirmation) != 1_024
            or len(np.intersect1d(checkpoint, confirmation))
            or len(np.intersect1d(final, confirmation))
            or record["confirmation_rows_sha256"]
            != train.e10v.array_sha256(confirmation)
        ):
            raise RuntimeError("E10M preflight confirmation rows differ")
        row_hashes[task] = record["confirmation_rows_sha256"]
        vp_indices = spec["vp"]
        for condition, index in zip(("vp_true", "vp_shuffled_goal"), vp_indices):
            summary = (
                args.root
                / "results/acid-alternative/gdp-cem-e10v-train"
                / task
                / condition
                / f"seed-6101-job-297778-{index}/summary.json"
            )
            model, _, _ = e10v_eval.load_vp_checkpoint(
                summary,
                task=task,
                condition=condition,
                source_manifest_sha256=(
                    "b843a68dda3355499cada1d580853654efa404bc5f5d2375fbee14b4121e3e5d"
                ),
                device=device,
            )
            del model
            model_count += 1
        gaussian_summary = (
            args.root
            / "results/acid-alternative/gdp-cem-e7p-proposals"
            / task
            / "gaussian_true"
            / f"seed-6101-job-297703-{spec['gaussian']}/summary.json"
        )
        gaussian, _, _ = e7.load_checkpoint(
            gaussian_summary,
            task=task,
            condition="gaussian_true",
            device=device,
        )
        del gaussian
        model_count += 1
    if model_count != 9 or len(set(row_hashes.values())) != 3:
        raise RuntimeError("E10M preflight model/row count differs")
    print(
        json.dumps(
            {
                "status": "ok",
                "seed1_models": model_count,
                "confirmation_row_hashes": row_hashes,
                "d2_read": False,
                "d3_read": False,
                "protected_c1_i1_read": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
