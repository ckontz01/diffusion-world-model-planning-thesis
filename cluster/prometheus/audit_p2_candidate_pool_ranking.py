#!/usr/bin/env python3
"""Run the frozen candidate-pool ranking audit on one P2 environment."""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from audit_candidate_pool_ranking import analyze_partition, atomic_json, sha256_file


BOOTSTRAP_SEED = 20260812


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--p2-h5", type=Path, required=True)
    parser.add_argument("--p2-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_h5.exists() or args.output_json.exists():
        raise SystemExit("refusing to overwrite P2 pool-ranking audit")
    if not args.spec.is_file():
        raise RuntimeError("audit specification is missing")

    started = time.time()
    p2_result, arrays = analyze_partition(
        "P2",
        args.p2_h5,
        args.p2_manifest,
        "failure_label",
        np.random.SeedSequence(BOOTSTRAP_SEED),
    )

    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output_h5.with_name(f".{args.output_h5.name}.partial-{os.getpid()}")
    try:
        with h5py.File(partial, "w") as output:
            output.attrs["classification"] = "p2_candidate_pool_ranking_audit"
            output.attrs["environment"] = args.environment
            output.attrs["partition"] = "P2-development-only"
            output.create_dataset("failure_label", data=arrays.pop("labels"))
            group = output.create_group("ensemble_raw_score")
            for name, value in arrays.items():
                group.create_dataset(name, data=value, compression="gzip")
            output.flush()
        os.replace(partial, args.output_h5)
    except BaseException:
        if partial.exists():
            partial.unlink()
        raise

    result: dict[str, Any] = {
        "status": "ok",
        "classification": "p2_candidate_pool_ranking_audit",
        "environment": args.environment,
        "partition_scope": "P2-development-only",
        "reporting_boundary": "exploratory; no P3/P4 artifact was read or changed",
        "bootstrap": {"replicates": 10000, "seed": BOOTSTRAP_SEED},
        "spec": str(args.spec),
        "spec_sha256": sha256_file(args.spec),
        "P2": p2_result,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "elapsed_seconds": time.time() - started,
        },
        "output_h5": str(args.output_h5),
        "output_h5_bytes": args.output_h5.stat().st_size,
        "output_h5_sha256": sha256_file(args.output_h5),
    }
    atomic_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

