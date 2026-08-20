#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from train_m2_diffusion_head import (
    atomic_json,
    enumerate_pairs,
    null_episode_map,
    read_tsv,
    sha256_file,
)


ROLES = ("P1_train", "P1_val")


def sha256_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def validate_role(
    rows: list[dict[str, str]], role: str, seed: int, namespace: str
) -> dict[str, Any]:
    mapping, mapping_sha = null_episode_map(rows, role, seed, namespace)
    repeated_mapping, repeated_mapping_sha = null_episode_map(
        rows, role, seed, namespace
    )
    if mapping != repeated_mapping or mapping_sha != repeated_mapping_sha:
        raise RuntimeError(f"{role} null episode mapping is not deterministic")
    if set(mapping) != set(mapping.values()):
        raise RuntimeError(f"{role} null episode mapping is not a permutation")
    if any(target == source for target, source in mapping.items()):
        raise RuntimeError(f"{role} null episode mapping contains a fixed point")

    source, target, info = enumerate_pairs(
        rows, role, "mismatched", seed, namespace
    )
    source_repeat, target_repeat, info_repeat = enumerate_pairs(
        rows, role, "mismatched", seed, namespace
    )
    true_source, true_target, _ = enumerate_pairs(rows, role, "true", seed, namespace)
    if not (
        np.array_equal(source, source_repeat)
        and np.array_equal(target, target_repeat)
        and info == info_repeat
    ):
        raise RuntimeError(f"{role} mismatched row enumeration is not deterministic")
    if not np.array_equal(target, true_target):
        raise RuntimeError(f"{role} mismatched null changed target rows")
    if np.array_equal(source, true_source):
        raise RuntimeError(f"{role} mismatched null did not change source rows")
    if info.get("null_hash_namespace") != namespace:
        raise RuntimeError(f"{role} did not record the requested hash namespace")

    legacy_source, legacy_target, legacy_info = enumerate_pairs(
        rows, role, "mismatched", seed, "pusht_expert_train"
    )
    if not np.array_equal(target, legacy_target):
        raise RuntimeError(f"{role} namespace adapter changed target rows")
    if np.array_equal(source, legacy_source):
        raise RuntimeError(f"{role} TwoRoom and legacy source mappings are identical")
    if info["null_episode_mapping_sha256"] == legacy_info[
        "null_episode_mapping_sha256"
    ]:
        raise RuntimeError(f"{role} TwoRoom and legacy episode maps are identical")

    return {
        "role": role,
        "episodes": len(mapping),
        "pairs": int(len(source)),
        "mapping_is_bijective": True,
        "fixed_points": 0,
        "mapping_sha256": mapping_sha,
        "source_rows_sha256": sha256_array(source),
        "target_rows_sha256": sha256_array(target),
        "legacy_mapping_sha256": legacy_info["null_episode_mapping_sha256"],
        "legacy_source_rows_sha256": sha256_array(legacy_source),
        "differs_from_legacy_namespace": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-plan", type=Path, required=True)
    parser.add_argument("--pair-summary", type=Path, required=True)
    parser.add_argument("--dataset-hash-namespace", default="tworoom")
    parser.add_argument("--seed", type=int, default=20260728)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.output_json.exists():
        raise SystemExit("refusing to overwrite M2 null-namespace validation")
    if args.dataset_hash_namespace != "tworoom":
        raise SystemExit("the TwoRoom null adapter is frozen to namespace 'tworoom'")

    summary = json.loads(args.pair_summary.read_text(encoding="utf-8"))
    pair_sha = sha256_file(args.pair_plan)
    if pair_sha != summary["m1_m2"]["manifest_sha256"]:
        raise RuntimeError("pair plan differs from its frozen summary")
    rows = read_tsv(args.pair_plan)
    records = [
        validate_role(rows, role, args.seed, args.dataset_hash_namespace)
        for role in ROLES
    ]
    result = {
        "status": "ok",
        "classification": "tworoom_m2_mismatched_null_namespace_validation",
        "dataset_hash_namespace": args.dataset_hash_namespace,
        "seed": args.seed,
        "pair_plan_sha256": pair_sha,
        "pair_summary_sha256": sha256_file(args.pair_summary),
        "roles": records,
        "assertions": {
            "deterministic_repeat": True,
            "episode_derangement": True,
            "target_rows_unchanged": True,
            "source_rows_changed": True,
            "different_from_legacy_pusht_namespace": True,
        },
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
