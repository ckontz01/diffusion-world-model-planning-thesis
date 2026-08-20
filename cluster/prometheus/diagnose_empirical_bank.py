#!/usr/bin/env python3

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import time
from pathlib import Path

import hydra
import numpy as np
import stable_worldmodel as swm
import torch

from h_le_wm.eval.determinism import configure_process_determinism
from h_le_wm.eval.hierarchical import (
    build_process_map,
    force_torch_load_map_location,
    get_dataset,
)
from h_le_wm.planning.policies import build_empirical_macro_action_bank


def array_digest(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(json.dumps(contiguous.shape).encode("ascii"))
    digest.update(contiguous.tobytes())
    return digest.hexdigest()


def array_record(array: np.ndarray) -> dict:
    value = np.asarray(array)
    record = {
        "shape": list(value.shape),
        "dtype": str(value.dtype),
        "sha256": array_digest(value),
    }
    if np.issubdtype(value.dtype, np.floating):
        record.update(
            {
                "finite": bool(np.isfinite(value).all()),
                "min": float(value.min()),
                "max": float(value.max()),
                "mean": float(value.mean()),
                "std": float(value.std()),
                "rounded_1e-7_sha256": array_digest(np.round(value, 7)),
                "rounded_1e-6_sha256": array_digest(np.round(value, 6)),
                "rounded_1e-5_sha256": array_digest(np.round(value, 5)),
            }
        )
    return record


def build(args: argparse.Namespace) -> None:
    determinism = configure_process_determinism(seed=args.seed, mode="strict")
    config_dir = str((Path(args.code_root) / "h_le_wm" / "config" / "eval").resolve())
    overrides = [
        f"cache_dir={args.stablewm_home}",
        f"policy={args.policy}",
        f"seed={args.seed}",
        "planning.high.solver.device=cuda",
        "planning.low.solver.device=cuda",
        "solver.device=cuda",
        "planning.high.plan_config.horizon=1",
        "planning.high.plan_config.action_block=1",
        "planning.high.empirical_macro.enabled=true",
        f"planning.high.empirical_macro.num_sequences={args.num_sequences}",
        "planning.high.empirical_macro.chunk_len=5",
        "planning.high.empirical_macro.encode_batch_size=4096",
        f"planning.high.empirical_macro.seed={args.seed}",
    ]
    with hydra.initialize_config_dir(version_base=None, config_dir=config_dir):
        cfg = hydra.compose(config_name="hi_pusht", overrides=overrides)

    started = time.time()
    dataset = get_dataset(cfg, cfg.eval.dataset_name)
    process = build_process_map(cfg, dataset)
    with force_torch_load_map_location("cuda"):
        model = swm.policy.AutoCostModel(cfg.policy)
    model = model.to("cuda").eval()
    model.requires_grad_(False)
    model.interpolate_pos_encoding = True

    bank = build_empirical_macro_action_bank(
        model=model,
        dataset=dataset,
        cfg=cfg.planning.high.empirical_macro,
        high_horizon=1,
        high_action_block=1,
        process=process,
        seed=args.seed,
    )
    arrays = {
        key: np.asarray(value)
        for key, value in bank.items()
        if isinstance(value, (np.ndarray, np.generic))
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output_npz, **arrays)

    record = {
        "status": "ok",
        "classification": "empirical_macro_determinism_diagnostic",
        "seed": args.seed,
        "num_sequences": args.num_sequences,
        "elapsed_seconds": time.time() - started,
        "runtime": {
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "stable_worldmodel": metadata.version("stable-worldmodel"),
            "gpu": torch.cuda.get_device_name(0),
            "pythonhashseed_at_process_start": os.environ.get("PYTHONHASHSEED"),
            "cublas_workspace_config_at_process_start": os.environ.get(
                "CUBLAS_WORKSPACE_CONFIG"
            ),
        },
        "determinism": determinism,
        "arrays": {key: array_record(value) for key, value in arrays.items()},
    }
    args.output_json.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True))


def compare(args: argparse.Namespace) -> None:
    with np.load(args.first_npz) as first, np.load(args.second_npz) as second:
        first_keys = sorted(first.files)
        second_keys = sorted(second.files)
        if first_keys != second_keys:
            raise SystemExit(
                f"array-key mismatch: first={first_keys}, second={second_keys}"
            )
        comparisons = {}
        all_exact = True
        for key in first_keys:
            left = first[key]
            right = second[key]
            exact = bool(np.array_equal(left, right))
            all_exact &= exact
            item = {
                "exact_match": exact,
                "shape_match": left.shape == right.shape,
                "dtype_match": left.dtype == right.dtype,
                "first_sha256": array_digest(left),
                "second_sha256": array_digest(right),
            }
            if left.shape == right.shape and np.issubdtype(left.dtype, np.number):
                delta = np.asarray(left, dtype=np.float64) - np.asarray(
                    right, dtype=np.float64
                )
                item.update(
                    {
                        "unequal_elements": int(np.count_nonzero(delta)),
                        "max_abs_difference": float(np.max(np.abs(delta))),
                        "mean_abs_difference": float(np.mean(np.abs(delta))),
                    }
                )
            comparisons[key] = item

    result = {
        "status": "ok",
        "classification": "empirical_macro_determinism_comparison",
        "all_arrays_exact": all_exact,
        "arrays": comparisons,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="operation", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--code-root", type=Path, required=True)
    build_parser.add_argument("--stablewm-home", type=Path, required=True)
    build_parser.add_argument("--policy", required=True)
    build_parser.add_argument("--seed", type=int, default=42)
    build_parser.add_argument("--num-sequences", type=int, default=4096)
    build_parser.add_argument("--output-json", type=Path, required=True)
    build_parser.add_argument("--output-npz", type=Path, required=True)
    build_parser.set_defaults(func=build)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("first_npz", type=Path)
    compare_parser.add_argument("second_npz", type=Path)
    compare_parser.add_argument("--output-json", type=Path, required=True)
    compare_parser.set_defaults(func=compare)
    return result


if __name__ == "__main__":
    parsed = parser().parse_args()
    parsed.func(parsed)

