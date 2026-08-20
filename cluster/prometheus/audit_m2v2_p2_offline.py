#!/usr/bin/env python3
"""Frozen P2 offline within-pool diagnostic for M2v2."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch
from scipy.stats import rankdata

from audit_candidate_pool_ranking import BOOTSTRAP_SEED, bootstrap, core_metrics, label_structure
from m2v2_likelihood_ratio import load_m2v2_ensemble
from score_and_select_p2_true_scorers import (
    CANDIDATE_COUNT,
    LATENT_DIM,
    MACRO_DIM,
    M1_WIDTHS,
    M2_WIDTHS,
    POOL_COUNT,
    SEEDS,
    SIGMAS,
    atomic_json,
    sha256_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=("pusht", "tworoom"), required=True)
    parser.add_argument("--labeled-dir", type=Path, required=True)
    parser.add_argument("--true-selection-dir", type=Path, required=True)
    parser.add_argument("--conditional-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--unconditional-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--reference-npz", type=Path, required=True)
    parser.add_argument("--reference-manifest", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def existing_context(true_h5: Path, labels: np.ndarray) -> dict[str, Any]:
    with h5py.File(true_h5, "r") as handle:
        stored_labels = np.asarray(handle["failure_label"][:], dtype=np.bool_)
        if not np.array_equal(labels, stored_labels):
            raise RuntimeError("M2v2 labels differ from the existing P2 scorer audit")
        m1_width = int(handle.attrs["selected_m1_width"])
        m2_width = int(handle.attrs["selected_m2_width"])
        m2_sigma = float(handle.attrs["selected_m2_sigma"])
        m1_index = M1_WIDTHS.index(m1_width)
        m2_width_index = M2_WIDTHS.index(m2_width)
        m2_sigma_index = SIGMAS.index(m2_sigma)
        arrays = {
            "M1_selected": np.asarray(handle["m1_raw_score"][m1_index], dtype=np.float64).mean(axis=0),
            "M2_original_selected": np.asarray(
                handle["m2_raw_score"][m2_width_index, :, m2_sigma_index], dtype=np.float64
            ).mean(axis=0),
            "M3_true": np.asarray(handle["m3_raw_score"][0], dtype=np.float64).mean(axis=0),
        }
    output = {
        "selected_configuration": {
            "M1_width": m1_width,
            "M2_width": m2_width,
            "M2_sigma": m2_sigma,
        },
        "methods": {},
    }
    children = np.random.SeedSequence(BOOTSTRAP_SEED ^ 0x4D327632).spawn(len(arrays))
    for (name, scores), child in zip(arrays.items(), children, strict=True):
        output["methods"][name] = {
            "metrics": core_metrics(labels, scores),
            "pool_bootstrap": bootstrap(labels, scores, np.random.default_rng(child)),
        }
    return output


def main() -> None:
    args = parse_args()
    if len(args.conditional_checkpoint) != len(SEEDS) or len(args.unconditional_checkpoint) != len(SEEDS):
        raise SystemExit("provide exactly three M2v2 checkpoint pairs")
    output_h5 = args.output_dir / "audit.h5"
    output_json = args.output_dir / "manifest.json"
    if output_h5.exists() or output_json.exists():
        raise SystemExit(f"refusing to overwrite M2v2 P2 offline audit: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not torch.cuda.is_available():
        raise RuntimeError("M2v2 P2 scoring requires CUDA")
    device = torch.device("cuda")
    started = time.time()

    labeled_manifest = json.loads((args.labeled_dir / "manifest.json").read_text(encoding="utf-8"))
    labeled_h5 = args.labeled_dir / "labeled-candidates.h5"
    if labeled_manifest.get("output_h5_sha256") != sha256_file(labeled_h5):
        raise RuntimeError("M2v2 labeled P2 input hash mismatch")
    with h5py.File(labeled_h5, "r") as handle:
        source_np = np.asarray(handle["source_latent"][:], dtype=np.float32)
        target_np = np.asarray(handle["selected_subgoal"][:], dtype=np.float32)
        macro_np = np.asarray(handle["selected_first_macro"][:], dtype=np.float32)
        attainment = np.asarray(handle["primary_label_at_least_3_of_5"][:], dtype=np.bool_)
        pool_id = np.asarray(handle["pool_id"][:], dtype=np.int64)
    expected_shapes = (
        source_np.shape == (POOL_COUNT, LATENT_DIM),
        target_np.shape == (POOL_COUNT, CANDIDATE_COUNT, LATENT_DIM),
        macro_np.shape == (POOL_COUNT, CANDIDATE_COUNT, MACRO_DIM),
        attainment.shape == (POOL_COUNT, CANDIDATE_COUNT),
        np.array_equal(pool_id, np.arange(POOL_COUNT)),
    )
    if not all(expected_shapes):
        raise RuntimeError("M2v2 labeled P2 tensor shape or pool order changed")
    labels = ~attainment
    source_flat = np.broadcast_to(
        source_np[:, None, :], (POOL_COUNT, CANDIDATE_COUNT, LATENT_DIM)
    ).reshape(-1, LATENT_DIM).copy()
    target_flat = target_np.reshape(-1, LATENT_DIM)
    macro_flat = macro_np.reshape(-1, MACRO_DIM)

    scorer = load_m2v2_ensemble(
        conditional_checkpoints=args.conditional_checkpoint,
        unconditional_checkpoints=args.unconditional_checkpoint,
        reference_npz=args.reference_npz,
        reference_manifest=args.reference_manifest,
        noise_npy=args.noise_npy,
        noise_manifest=args.noise_manifest,
        spec=args.spec,
        environment=args.environment,
        device=device,
        expected_candidate_count=None,
    )
    seed_scores = scorer.raw_scores(
        torch.from_numpy(source_flat).to(device),
        torch.from_numpy(target_flat).to(device),
        torch.from_numpy(macro_flat).to(device),
    ).cpu().numpy().reshape(len(SEEDS), POOL_COUNT, CANDIDATE_COUNT)
    score = seed_scores.mean(axis=0)
    midrank = np.stack(
        [
            (rankdata(row, method="average") - 1.0) / float(CANDIDATE_COUNT - 1)
            for row in score
        ]
    ).astype(np.float32)
    metrics = core_metrics(labels, score)
    pool_bootstrap = bootstrap(
        labels,
        score,
        np.random.default_rng(np.random.SeedSequence(BOOTSTRAP_SEED ^ 0x76325032)),
    )

    true_manifest = json.loads((args.true_selection_dir / "manifest.json").read_text(encoding="utf-8"))
    true_h5 = args.true_selection_dir / "scores.h5"
    if true_manifest.get("output_h5_sha256") != sha256_file(true_h5):
        raise RuntimeError("existing P2 true-selection artifact hash mismatch")
    context = existing_context(true_h5, labels)
    torch.cuda.synchronize(device)

    partial_h5 = output_h5.with_name(f".{output_h5.name}.partial-{os.getpid()}")
    with h5py.File(partial_h5, "x") as output:
        output.attrs["classification"] = f"{args.environment}_m2v2_p2_offline_within_pool_audit"
        output.attrs["environment"] = args.environment
        output.attrs["partition"] = "P2-development-only"
        output.create_dataset("pool_id", data=pool_id)
        output.create_dataset("failure_label", data=labels)
        output.create_dataset("m2v2_seed_score", data=seed_scores.astype(np.float32), compression="gzip")
        output.create_dataset("m2v2_score", data=score.astype(np.float32), compression="gzip")
        output.create_dataset("m2v2_within_pool_midrank", data=midrank, compression="gzip")
        output.flush()
    os.replace(partial_h5, output_h5)

    top4_reduction = metrics["lowest_score_selection"]["top_4"][
        "baseline_minus_selected_failure_rate_mean"
    ]
    result = {
        "status": "ok",
        "classification": f"{args.environment}_m2v2_p2_offline_within_pool_audit",
        "environment": args.environment,
        "partition": "P2-development-only",
        "reporting_rule": "exploratory redesign diagnostic; not a final thesis result",
        "label_structure": label_structure(labels),
        "M2v2": {
            "metrics": metrics,
            "pool_bootstrap": pool_bootstrap,
            "offline_gate_components": {
                "within_pool_auroc_above_0_5": bool(
                    metrics["pair_weighted_within_pool_auroc"] > 0.5
                ),
                "top4_failure_reduction": top4_reduction,
                "top4_reduction_positive": bool(top4_reduction > 0.0),
            },
            "scorer_artifacts": scorer.artifact_record,
        },
        "existing_P2_context": context,
        "inputs": {
            "labeled_h5": str(labeled_h5),
            "labeled_h5_sha256": labeled_manifest["output_h5_sha256"],
            "true_selection_h5": str(true_h5),
            "true_selection_h5_sha256": true_manifest["output_h5_sha256"],
            "reference_npz": str(args.reference_npz),
            "reference_npz_sha256": sha256_file(args.reference_npz),
            "spec": str(args.spec),
            "spec_sha256": sha256_file(args.spec),
        },
        "runtime": {
            "python": os.sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "gpu": torch.cuda.get_device_name(device),
            "elapsed_seconds": time.time() - started,
        },
        "output_h5": str(output_h5),
        "output_h5_sha256": sha256_file(output_h5),
    }
    atomic_json(output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
