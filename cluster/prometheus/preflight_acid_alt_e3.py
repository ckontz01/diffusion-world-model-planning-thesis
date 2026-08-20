#!/usr/bin/env python3
"""Outcome-free source and grid preflight for exploratory E3."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import acid_alt_d2_models as d2


PROTOCOL_SHA256 = (
    "c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0"
)
ARMS = ("b0", "acid", "forward", "rdx", "ae", "ae_shuffled")
TASKS = ("pusht", "reacher", "cube")
SCORER_SEEDS = (6101, 6102, 6103)
PLANNER_SEEDS = (8301, 8302, 8303)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: preflight_acid_alt_e3.py SNAPSHOT")
    snapshot = Path(sys.argv[1]).resolve()
    protocol = snapshot / (
        "ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-"
        "PROTOCOL-2026-08-16.md"
    )
    if sha256_file(protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E3 protocol hash mismatch")
    if sha256_file(snapshot / "SOURCE-MANIFEST.sha256") == (
        "2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea"
    ):
        raise RuntimeError("E3 must not reuse the v3 source-manifest identity")

    trainer_path = snapshot / "train_residual_diffusion_pilot_20260816.py"
    if sha256_file(trainer_path) != d2.V2_TRAINER_SHA256:
        raise RuntimeError("frozen residual trainer source differs")
    trainer = load_module(trainer_path, "e3_preflight_frozen_trainer")
    d2.self_test(trainer)

    evaluator = load_module(
        snapshot / "evaluate_acid_alt_e3_d2.py", "e3_preflight_evaluator"
    )
    analyzer = load_module(
        snapshot / "analyze_acid_alt_e3_d2_closed_loop.py",
        "e3_preflight_analyzer",
    )
    authorization = load_module(
        snapshot / "create_acid_alt_e3_authorization.py",
        "e3_preflight_authorization",
    )
    if tuple(evaluator.ARMS) != ARMS or tuple(analyzer.ARMS) != ARMS:
        raise RuntimeError("E3 evaluator/analyzer arm grids differ")
    if (
        evaluator.E3_PROTOCOL_SHA256 != PROTOCOL_SHA256
        or analyzer.E3_PROTOCOL_SHA256 != PROTOCOL_SHA256
        or authorization.E3_PROTOCOL_SHA256 != PROTOCOL_SHA256
    ):
        raise RuntimeError("E3 modules disagree on protocol identity")
    if tuple(evaluator.PLANNER_SEEDS) != PLANNER_SEEDS:
        raise RuntimeError("E3 evaluator planner seeds differ")
    if tuple(d2.SEEDS) != SCORER_SEEDS:
        raise RuntimeError("E3 scorer seeds differ")

    grid = []
    for index in range(54):
        task_index = index // 18
        within = index % 18
        arm_index = within // 3
        seed_offset = within % 3
        grid.append(
            (
                TASKS[task_index],
                ARMS[arm_index],
                SCORER_SEEDS[seed_offset],
                PLANNER_SEEDS[seed_offset],
            )
        )
    expected = {
        (task, arm, scorer_seed, scorer_seed + 2200)
        for task in TASKS
        for arm in ARMS
        for scorer_seed in SCORER_SEEDS
    }
    if len(grid) != 54 or len(set(grid)) != 54 or set(grid) != expected:
        raise RuntimeError("E3 Slurm grid does not map bijectively to 54 runs")

    slurm = (snapshot / "run_acid_alt_e3_d2_closed_loop.slurm").read_text(
        encoding="utf-8"
    )
    required_fragments = (
        "#SBATCH --array=0-53%4",
        "SLURM_ARRAY_TASK_ID / 18",
        "SLURM_ARRAY_TASK_ID % 18",
        "ARMS=(b0 acid forward rdx ae ae_shuffled)",
        "--exploratory-authorization",
        "v3_stage_b_authorized=false",
        "protected_c1_i1_read=false",
    )
    if any(fragment not in slurm for fragment in required_fragments):
        raise RuntimeError("E3 Slurm launcher contract is incomplete")
    if "stage-b-authorization" in slurm or "ARMS=(b0 acid reachability" in slurm:
        raise RuntimeError("E3 launcher contains a v3 Stage-B bypass")

    print(
        json.dumps(
            {
                "status": "ok",
                "protocol_sha256": PROTOCOL_SHA256,
                "arms": list(ARMS),
                "grid_runs": len(grid),
                "model_self_test": "passed",
                "v3_stage_b_bypass_present": False,
                "protected_c1_i1_read": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
