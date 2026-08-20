#!/usr/bin/env python3
"""Outcome-free checkpoint, manifest, and method preflight for E8D."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import acid_alt_d2_models as d2
import evaluate_gdp_cem_e8d_closed_loop as e8d
from gdp_cem_models import GaussianAnchoredRefinementSampler


TASK_SPEC = {
    "pusht": {
        "dataset": "pusht_expert_train.h5",
        "world_model_checkpoint": "pusht/lewm_hf_22b330c_object.ckpt",
        "core_job": 296631,
        "proposal_indices": (0, 1, 2),
    },
    "reacher": {
        "dataset": "reacher.h5",
        "world_model_checkpoint": "reacher/lewm_object.ckpt",
        "core_job": 296650,
        "proposal_indices": (3, 4, 5),
    },
    "cube": {
        "dataset": "cube_single_expert.h5",
        "world_model_checkpoint": "cube/lewm_hf_b0747c5_object.ckpt",
        "core_job": 296669,
        "proposal_indices": (6, 7, 8),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    args = parser.parse_args()
    device = torch.device("cpu")
    proposal_count = 0
    acid_count = 0
    row_count = 0
    aggregate = (
        args.root
        / "results/acid-alternative/gdp-cem-e8a-refinement/analysis/job-297721/summary.json"
    )
    conditions = e8d.e7.CONDITIONS
    for task, spec in TASK_SPEC.items():
        e8d.validate_e8a(aggregate, task=task)
        manifest_dir = (
            args.root / f"manifests/acid-alternative-v3-d2/{task}/job-297535"
        )
        dataset = args.root / "data/stablewm" / spec["dataset"]
        world_model_checkpoint = (
            args.root / "data/stablewm" / spec["world_model_checkpoint"]
        )
        expected_runtime = e8d.EXPECTED_RUNTIME_ARTIFACTS[task]
        provenance_path = manifest_dir / "provenance.json"
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        if (
            provenance.get("dataset_sha256") != expected_runtime["dataset_sha256"]
            or d2.sha256_file(world_model_checkpoint)
            != expected_runtime["world_model_checkpoint_sha256"]
        ):
            raise RuntimeError("E8D preflight dataset/world-model lineage differs")
        rows = e8d.e3.read_d2_manifest(
            manifest_dir / "d2-fresh.tsv",
            provenance_path,
            task=task,
            dataset=dataset,
            source_manifest=args.source_manifest,
        )
        row_count += len(rows)
        summary_values = []
        for condition, index in zip(conditions, spec["proposal_indices"]):
            summary = (
                args.root
                / "results/acid-alternative/gdp-cem-e7p-proposals"
                / task
                / condition
                / f"seed-6101-job-297703-{index}/summary.json"
            )
            summary_values.append([condition, str(summary)])
        models, _, _ = e8d.load_proposals(
            summary_values, task=task, device=device
        )
        proposal_count += len(models)
        acid_path = (
            args.root
            / "results/acid-alternative/scorers"
            / task
            / "acid/true"
            / f"seed-6101-job-{spec['core_job']}-0/best.pt"
        )
        acid, _, record = d2.load_core_scorer(
            acid_path, arm="acid", expected_seed=6101, device=device
        )
        if record["checkpoint_sha256"] != e8d.EXPECTED_ACID_CHECKPOINTS[task]:
            raise RuntimeError("E8D preflight ACID checkpoint differs")
        acid_count += 1
        del acid, models
    if (
        proposal_count != 9
        or acid_count != 3
        or row_count != 150
        or GaussianAnchoredRefinementSampler.refined_count(150, 0.5) != 75
        or GaussianAnchoredRefinementSampler.refined_count(300, 0.5) != 150
    ):
        raise RuntimeError("E8D preflight count or rounding differs")
    for protected in ("d3", "C1", "i1"):
        try:
            e8d.reject_protected_path(Path("/tmp") / protected / "artifact")
        except RuntimeError:
            pass
        else:
            raise RuntimeError(f"E8D preflight accepted protected path: {protected}")
    print("E8D preflight passed: proposals=9 acid=3 D2_rows=150")


if __name__ == "__main__":
    main()
