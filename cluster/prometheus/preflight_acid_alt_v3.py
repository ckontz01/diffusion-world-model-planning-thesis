#!/usr/bin/env python3
"""Outcome-free source and checkpoint preflight for the v3 D2 study."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import torch

import acid_alt_d2_models as d2


TASKS = ("pusht", "reacher", "cube")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_module(path: Path) -> Any:
    if not path.is_file() or d2.sha256_file(path) != d2.V2_TRAINER_SHA256:
        raise RuntimeError("base residual trainer hash mismatch")
    spec = importlib.util.spec_from_file_location("v2_residual_trainer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load base residual trainer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--trainer-source", type=Path, required=True)
    parser.add_argument(
        "--residual",
        nargs=4,
        action="append",
        metavar=("TASK", "CONDITION", "SEED", "SUMMARY"),
        required=True,
    )
    parser.add_argument(
        "--core",
        nargs=4,
        action="append",
        metavar=("TASK", "ARM", "SEED", "CHECKPOINT"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if d2.sha256_file(args.protocol) != d2.PROTOCOL_SHA256:
        raise RuntimeError("D2 protocol hash mismatch")
    if not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    trainer = load_module(args.trainer_source)
    d2.self_test(trainer)
    device = torch.device("cpu")

    residual_grid = set()
    residual_records = []
    for task, condition, seed_text, summary_text in args.residual:
        seed = int(seed_text)
        if task not in TASKS or condition not in {"true", "shuffled_action"}:
            raise ValueError("invalid residual preflight identity")
        identity = (task, condition, seed)
        if identity in residual_grid:
            raise ValueError(f"duplicate residual preflight identity: {identity}")
        residual_grid.add(identity)
        model, payload, record = d2.load_residual_model(
            Path(summary_text),
            expected_condition=condition,
            trainer_module=trainer,
            device=device,
        )
        if int(payload["seed"]) != seed:
            raise RuntimeError(f"residual seed mismatch: {identity}")
        residual_records.append({"task": task, **record})
        del model
    expected_residual = {
        (task, condition, 6101)
        for task in TASKS
        for condition in ("true", "shuffled_action")
    }
    if residual_grid != expected_residual:
        raise RuntimeError("preflight requires the six retained seed-6101 residual models")

    core_grid = set()
    core_records = []
    for task, arm, seed_text, checkpoint_text in args.core:
        seed = int(seed_text)
        if task not in TASKS or arm not in {
            "acid",
            "diffusion",
            "forward",
            "reachability",
        }:
            raise ValueError("invalid core preflight identity")
        identity = (task, arm, seed)
        if identity in core_grid:
            raise ValueError(f"duplicate core preflight identity: {identity}")
        core_grid.add(identity)
        model, _, record = d2.load_core_scorer(
            Path(checkpoint_text), arm=arm, expected_seed=seed, device=device
        )
        core_records.append({"task": task, **record})
        del model
    expected_core = {
        (task, arm, seed)
        for task in TASKS
        for arm in ("acid", "diffusion", "forward", "reachability")
        for seed in d2.SEEDS
    }
    if core_grid != expected_core:
        raise RuntimeError("preflight requires all 36 retained core comparators")

    result = {
        "status": "ok",
        "kind": "acid_alt_v3_outcome_free_preflight",
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest_sha256": d2.sha256_file(args.source_manifest),
        "trainer_source_sha256": d2.sha256_file(args.trainer_source),
        "residual_records": residual_records,
        "core_records": core_records,
        "self_test": "passed",
        "protected_c1_i1_read": False,
    }
    atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
