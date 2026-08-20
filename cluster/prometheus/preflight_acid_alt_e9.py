#!/usr/bin/env python3
"""Outcome-free E9 model/checkpoint and equation preflight."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

import acid_alt_d2_models as d2
from preflight_acid_alt_v3 import load_module


TASK_SPEC = {
    "pusht": {"core_job": 296631, "old": (0, 1), "train_base": 0},
    "reacher": {"core_job": 296650, "old": (2, 3), "train_base": 4},
    "cube": {"core_job": 296669, "old": (4, 5), "train_base": 8},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--trainer", type=Path, required=True)
    args = parser.parse_args()
    trainer = load_module(args.trainer)
    d2.self_test(trainer)
    device = torch.device("cpu")
    residual_count = 0
    core_count = 0
    for task, spec in TASK_SPEC.items():
        for seed_offset, seed in enumerate(d2.SEEDS):
            payloads = {}
            for condition in ("true", "shuffled_action"):
                if seed == 6101:
                    old_index = spec["old"][condition == "shuffled_action"]
                    summary = (
                        args.root
                        / "results/acid-alternative/scorers-v2-residual-diffusion-pilot"
                        / task
                        / condition
                        / f"seed-6101-job-297483-{old_index}/summary.json"
                    )
                else:
                    condition_offset = 2 if condition == "shuffled_action" else 0
                    train_index = spec["train_base"] + condition_offset + seed - 6102
                    summary = (
                        args.root
                        / "results/acid-alternative/scorers-v3-d2"
                        / task
                        / condition
                        / f"seed-{seed}-job-297533-{train_index}/summary.json"
                    )
                model, payload, _ = d2.load_residual_model(
                    summary,
                    expected_condition=condition,
                    trainer_module=trainer,
                    device=device,
                )
                if int(payload["seed"]) != seed:
                    raise RuntimeError("E9 residual seed differs")
                payloads[condition] = payload
                residual_count += 1
                del model
            d2.validate_residual_pair(payloads["true"], payloads["shuffled_action"])

            for arm, index in (("acid", seed_offset), ("forward", seed_offset + 6)):
                checkpoint = (
                    args.root
                    / "results/acid-alternative/scorers"
                    / task
                    / arm
                    / "true"
                    / f"seed-{seed}-job-{spec['core_job']}-{index}/best.pt"
                )
                model, _, _ = d2.load_core_scorer(
                    checkpoint, arm=arm, expected_seed=seed, device=device
                )
                core_count += 1
                del model
    if residual_count != 18 or core_count != 18:
        raise RuntimeError("E9 preflight model grid differs")
    print("E9 model/checkpoint preflight passed: residual=18 core=18")


if __name__ == "__main__":
    main()
