#!/usr/bin/env python3
"""P2-only M2v2 runner that reuses the audited released closed-loop harness."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import h5py

import run_p2_augmented_closed_loop_query as released
from m2v2_likelihood_ratio import load_m2v2_ensemble
from score_and_select_p2_true_scorers import SEEDS, atomic_json, sha256_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=("pusht", "tworoom"), required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--eval-config", type=Path, required=True)
    parser.add_argument("--weight", type=float, choices=released.WEIGHTS, required=True)
    parser.add_argument("--pool-index", type=int, required=True)
    parser.add_argument("--conditional-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--unconditional-checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--reference-npz", type=Path, required=True)
    parser.add_argument("--reference-manifest", type=Path, required=True)
    parser.add_argument("--noise-npy", type=Path, required=True)
    parser.add_argument("--noise-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--m2v2-batch-size", type=int, default=8192)
    return parser.parse_args()


def summarize_population_diagnostics(
    scorer: Any, *, high_iterations: int
) -> dict[str, Any]:
    diagnostics = list(scorer.population_diagnostics)
    if not diagnostics or len(diagnostics) % high_iterations != 0:
        raise RuntimeError("M2v2 population diagnostic count does not match CEM solves")
    final = diagnostics[high_iterations - 1 :: high_iterations]
    spans = [float(record["raw_score_span"]) for record in diagnostics]
    margins = [
        float(record["raw_score_span"] - record["required_span"])
        for record in diagnostics
    ]
    unique = [int(record["unique_score_count"]) for record in diagnostics]
    return {
        "all_population_count": len(diagnostics),
        "all_populations_passed_span_gate": bool(min(margins) > 0.0),
        "minimum_raw_score_span": min(spans),
        "minimum_span_gate_margin": min(margins),
        "minimum_unique_score_count": min(unique),
        "maximum_unique_score_count": max(unique),
        "final_iteration_population_diagnostics": final,
    }


def main() -> None:
    args = parse_args()
    if len(args.conditional_checkpoint) != len(SEEDS) or len(args.unconditional_checkpoint) != len(SEEDS):
        raise SystemExit("provide exactly three M2v2 checkpoint pairs")
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite M2v2 P2 closed-loop output")
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    staging_h5 = args.output_h5.with_name(f".{args.output_h5.name}.m2v2-core-{os.getpid()}")
    staging_json = args.output_json.with_name(f".{args.output_json.name}.m2v2-core-{os.getpid()}")
    expected_candidate_count = int(
        released.ENVIRONMENT_SPECS[args.environment]["high_num_samples"]
    )
    scorer_holder: dict[str, Any] = {}

    def custom_loader(**kwargs: Any) -> Any:
        scorer = load_m2v2_ensemble(
            conditional_checkpoints=args.conditional_checkpoint,
            unconditional_checkpoints=args.unconditional_checkpoint,
            reference_npz=args.reference_npz,
            reference_manifest=args.reference_manifest,
            noise_npy=args.noise_npy,
            noise_manifest=args.noise_manifest,
            spec=args.spec,
            environment=args.environment,
            device=kwargs["device"],
            expected_candidate_count=expected_candidate_count,
            batch_size=args.m2v2_batch_size,
        )
        scorer_holder["scorer"] = scorer
        return scorer

    original_loader = released.load_frozen_calibrated_ensemble
    original_argv = sys.argv
    released.load_frozen_calibrated_ensemble = custom_loader
    placeholder = str(args.candidate_dir)
    sys.argv = [
        str(Path(released.__file__)),
        "--environment", args.environment,
        "--partition", "P2",
        "--candidate-dir", str(args.candidate_dir),
        "--true-selection-dir", placeholder,
        "--calibration-dir", placeholder,
        "--m1-root", placeholder,
        "--m2-root", placeholder,
        "--m3-root", placeholder,
        "--noise-npy", str(args.noise_npy),
        "--noise-manifest", str(args.noise_manifest),
        "--dataset", str(args.dataset),
        "--checkpoint-file", str(args.checkpoint_file),
        "--policy", args.policy,
        "--stablewm-home", str(args.stablewm_home),
        "--eval-config", str(args.eval_config),
        "--method", "M2",
        "--weight", str(args.weight),
        "--pool-index", str(args.pool_index),
        "--output-h5", str(staging_h5),
        "--output-json", str(staging_json),
        "--m2-batch-size", "2048",
    ]
    try:
        released.main()
    finally:
        released.load_frozen_calibrated_ensemble = original_loader
        sys.argv = original_argv
    if "scorer" not in scorer_holder or not staging_h5.is_file() or not staging_json.is_file():
        raise RuntimeError("released closed-loop core did not produce a complete M2v2 staging result")

    scorer = scorer_holder["scorer"]
    high_iterations = int(released.ENVIRONMENT_SPECS[args.environment]["high_iterations"])
    population_summary = summarize_population_diagnostics(
        scorer, high_iterations=high_iterations
    )
    scorer_artifacts = dict(scorer.artifact_record)
    scorer_artifacts.pop("population_diagnostics", None)
    scorer_artifacts["online_population_audit"] = population_summary
    classification = f"{args.environment}_p2_m2v2_closed_loop_weight_development"

    with h5py.File(staging_h5, "r+") as output:
        output.attrs["classification"] = classification
        output.attrs["method"] = "M2v2"
        output.attrs["m2v2_spec_sha256"] = sha256_file(args.spec)
        output.flush()
    os.replace(staging_h5, args.output_h5)

    result = json.loads(staging_json.read_text(encoding="utf-8"))
    staging_json.unlink()
    result["classification"] = classification
    result["method"] = "M2v2"
    result["reporting_rule"] = "exploratory P2 redesign development; not a final thesis result"
    result["cost"]["formula"] = (
        "released squared-L2 final-goal cost + weight * exact within-population "
        "midrank of the P1-standardized multiscale conditional-minus-unconditional diffusion error"
    )
    result["cost"]["scored_transition"] = (
        "current latent and first predicted D25 subgoal; macro is ignored by M2v2"
    )
    result["cost"]["scorer_artifacts"] = scorer_artifacts
    result["inputs"]["m2v2_reference_npz"] = str(args.reference_npz)
    result["inputs"]["m2v2_reference_npz_sha256"] = sha256_file(args.reference_npz)
    result["inputs"]["m2v2_spec"] = str(args.spec)
    result["inputs"]["m2v2_spec_sha256"] = sha256_file(args.spec)
    result["runtime"]["m2v2_batch_size"] = args.m2v2_batch_size
    result["output_h5"] = str(args.output_h5)
    result["output_h5_bytes"] = args.output_h5.stat().st_size
    result["output_h5_sha256"] = sha256_file(args.output_h5)
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
