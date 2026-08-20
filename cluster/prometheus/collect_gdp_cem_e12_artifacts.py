#!/usr/bin/env python3
"""Build E12's outcome-free Stage-B artifact registry after all P1 jobs pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import gdp_cem_e12_specs as spec


METHOD_DIRECTORY = {
    "prism_head_h25": "prism-head-h25",
    "prism_head_endframe": "prism-head-endframe",
    "prism_dp": "prism-dp",
}
METHOD_KIND = {
    "prism_head_h25": "gdp_cem_e12_prism_prior_head_training",
    "prism_head_endframe": "gdp_cem_e12_prism_prior_head_training",
    "prism_dp": "gdp_cem_e12_prism_dp_reconstruction_training",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise FileExistsError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--training-source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.protocol, args.training_source_manifest):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E12 artifact registry protocol hash differs")
    source_sha256 = sha256_file(args.training_source_manifest)
    entries: dict[str, dict[str, dict[str, Any]]] = {}
    for task in spec.TASKS:
        entries[task] = {}
        for seed in spec.SEEDS:
            entries[task][str(seed)] = {}
            for method, directory in METHOD_DIRECTORY.items():
                summary_path = (
                    args.results_root / task / f"seed-{seed}" / directory / "summary.json"
                )
                if not summary_path.is_file():
                    raise FileNotFoundError(summary_path)
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                checkpoint_path = Path(summary.get("checkpoint", ""))
                if not checkpoint_path.is_file():
                    raise FileNotFoundError(checkpoint_path)
                expected_goal_mode = (
                    "h25"
                    if method == "prism_head_h25"
                    else "endframe" if method == "prism_head_endframe" else None
                )
                if (
                    summary.get("status") != "ok"
                    or summary.get("kind") != METHOD_KIND[method]
                    or summary.get("task") != task
                    or summary.get("seed") != seed
                    or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
                    or summary.get("source_manifest_sha256") != source_sha256
                    or summary.get("validity", {}).get("passed") is not True
                    or summary.get("d3_read") is not False
                    or summary.get("d4_read") is not False
                    or summary.get("protected_p4_c1_i1_read") is not False
                    or (expected_goal_mode is not None and summary.get("goal_mode") != expected_goal_mode)
                    or sha256_file(checkpoint_path) != summary.get("checkpoint_sha256")
                ):
                    raise RuntimeError(
                        f"invalid E12 Stage-B artifact: {task}/{seed}/{method}"
                    )
                entries[task][str(seed)][method] = {
                    "summary": str(summary_path.resolve()),
                    "summary_sha256": sha256_file(summary_path),
                    "checkpoint": str(checkpoint_path.resolve()),
                    "checkpoint_sha256": summary["checkpoint_sha256"],
                    "parameter_count": int(summary["parameter_count"]),
                    "validity": summary["validity"],
                }

    registry = {
        "status": "ok",
        "kind": "gdp_cem_e12_stage_b_artifact_registry",
        "analysis_role": "P1_only_frozen_comparator_artifacts",
        "protocol": str(args.protocol.resolve()),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest": str(args.training_source_manifest.resolve()),
        "training_source_manifest_sha256": source_sha256,
        "entries": entries,
        "task_count": len(spec.TASKS),
        "seed_count": len(spec.SEEDS),
        "method_count": len(METHOD_DIRECTORY),
        "artifact_count": len(spec.TASKS) * len(spec.SEEDS) * len(METHOD_DIRECTORY),
        "all_valid": True,
        "d3_outcomes_read": False,
        "d4_outcomes_read": False,
        "protected_p4_c1_i1_read": False,
    }
    atomic_json(args.output, registry)
    print(json.dumps(registry, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
