#!/usr/bin/env python3
"""Create a clean logical tree for E14 artifacts affected by CRLF seed paths."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import gdp_cem_e14_specs as spec
from gdp_cem_e14_data import read_sha256_records, sha256_file


def atomic_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_rows(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        rows = list(reader)
    if reader.fieldnames != list(fields) or not rows:
        raise RuntimeError(f"invalid E14 identifier manifest: {path}")
    return rows


def write_lf_tsv(
    path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]
) -> None:
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    if b"\r" in path.read_bytes():
        raise RuntimeError("normalized E14 manifest still contains CR bytes")


def verify_completed_training(directory: Path) -> None:
    required = ("best.pt", "training.jsonl", "summary.json", "sha256.txt")
    if not directory.is_dir() or any(
        not (directory / name).is_file() for name in required
    ):
        raise RuntimeError(f"incomplete E14 training directory: {directory}")
    records = read_sha256_records(directory / "sha256.txt")
    if set(records) != {"best.pt", "training.jsonl", "summary.json"}:
        raise RuntimeError("E14 training checksum entries differ")
    if any(sha256_file(directory / name) != digest for name, digest in records.items()):
        raise RuntimeError("E14 training artifact checksum differs")


def resolve_seed_directory(parent: Path, seed: int) -> Path:
    clean = parent / f"seed-{seed}"
    carriage_return = parent / f"seed-{seed}\r"
    candidates = [path for path in (clean, carriage_return) if path.is_dir()]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly one physical E14 seed directory for {parent}, seed {seed}"
        )
    verify_completed_training(candidates[0])
    return candidates[0].resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("endpoint", "full"), required=True)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--endpoint-manifest", type=Path, required=True)
    parser.add_argument("--endpoint-manifest-sha256", required=True)
    parser.add_argument("--sage-manifest", type=Path)
    parser.add_argument("--sage-manifest-sha256")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "full" and (
        args.sage_manifest is None or args.sage_manifest_sha256 is None
    ):
        raise ValueError("full E14 normalization requires the SAGE manifest")
    inputs = [
        args.training_root,
        args.endpoint_manifest,
        args.protocol,
        args.source_manifest,
    ]
    if args.sage_manifest is not None:
        inputs.append(args.sage_manifest)
    for path in inputs:
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_root.exists():
        raise SystemExit("refusing existing E14 normalized logical root")
    if (
        sha256_file(args.endpoint_manifest) != args.endpoint_manifest_sha256
        or (
            args.mode == "full"
            and (
                args.sage_manifest is None
                or sha256_file(args.sage_manifest) != args.sage_manifest_sha256
            )
        )
        or sha256_file(args.protocol) != spec.PROTOCOL_SHA256
    ):
        raise RuntimeError("E14 normalization input hash differs")
    endpoint_fields = ("array_id", "task", "condition", "seed")
    sage_fields = ("array_id", "task", "seed")
    endpoint_rows = read_rows(args.endpoint_manifest, endpoint_fields)
    sage_rows = (
        read_rows(args.sage_manifest, sage_fields)
        if args.mode == "full" and args.sage_manifest is not None
        else []
    )
    if len(endpoint_rows) != 32 or (
        args.mode == "full" and len(sage_rows) != 6
    ):
        raise RuntimeError("E14 normalization manifest cardinality differs")

    staging = args.output_root.with_name(
        f".{args.output_root.name}.partial-{os.getpid()}"
    )
    if staging.exists():
        raise FileExistsError(staging)
    links: list[dict[str, str]] = []
    try:
        (staging / "manifests").mkdir(parents=True)
        clean_endpoint: list[dict[str, Any]] = []
        for position, row in enumerate(endpoint_rows):
            task = row["task"]
            condition = row["condition"]
            seed = int(row["seed"])
            if task not in spec.TASKS or int(row["array_id"]) != position:
                raise RuntimeError("E14 endpoint identifier row differs")
            physical = resolve_seed_directory(
                args.training_root / "endpoint" / task / condition, seed
            )
            logical = staging / "endpoint" / task / condition / f"seed-{seed}"
            logical.parent.mkdir(parents=True, exist_ok=True)
            logical.symlink_to(physical, target_is_directory=True)
            links.append(
                {
                    "logical": str(
                        args.output_root
                        / "endpoint"
                        / task
                        / condition
                        / f"seed-{seed}"
                    ),
                    "physical": str(physical),
                }
            )
            clean_endpoint.append(
                {
                    "array_id": position,
                    "task": task,
                    "condition": condition,
                    "seed": seed,
                }
            )
        clean_sage: list[dict[str, Any]] = []
        for position, row in enumerate(sage_rows):
            task = row["task"]
            seed = int(row["seed"])
            if task not in spec.TASKS or int(row["array_id"]) != position:
                raise RuntimeError("E14 SAGE identifier row differs")
            for component in ("subgoal", "option"):
                physical = resolve_seed_directory(
                    args.training_root / "sage" / component / task, seed
                )
                logical = (
                    staging
                    / "sage"
                    / component
                    / task
                    / f"seed-{seed}"
                )
                logical.parent.mkdir(parents=True, exist_ok=True)
                logical.symlink_to(physical, target_is_directory=True)
                links.append(
                    {
                        "logical": str(
                            args.output_root
                            / "sage"
                            / component
                            / task
                            / f"seed-{seed}"
                        ),
                        "physical": str(physical),
                    }
                )
            clean_sage.append(
                {
                    "array_id": position,
                    "task": task,
                    "seed": seed,
                }
            )
        endpoint_output = staging / "manifests" / "endpoint.tsv"
        write_lf_tsv(endpoint_output, endpoint_fields, clean_endpoint)
        sage_output = staging / "manifests" / "sage.tsv"
        if args.mode == "full":
            write_lf_tsv(sage_output, sage_fields, clean_sage)
        record = {
            "status": "ok",
            "kind": "gdp_cem_e14_crlf_path_normalization",
            "analysis_role": "non_metric_artifact_path_erratum",
            "mode": args.mode,
            "training_root": str(args.training_root),
            "endpoint_manifest_input_sha256": args.endpoint_manifest_sha256,
            "sage_manifest_input_sha256": (
                args.sage_manifest_sha256 if args.mode == "full" else None
            ),
            "endpoint_manifest_lf": str(
                args.output_root / "manifests" / "endpoint.tsv"
            ),
            "endpoint_manifest_lf_sha256": sha256_file(endpoint_output),
            "sage_manifest_lf": (
                str(args.output_root / "manifests" / "sage.tsv")
                if args.mode == "full"
                else None
            ),
            "sage_manifest_lf_sha256": (
                sha256_file(sage_output) if args.mode == "full" else None
            ),
            "logical_link_count": len(links),
            "links": links,
            "protocol_sha256": spec.PROTOCOL_SHA256,
            "source_manifest_sha256": sha256_file(args.source_manifest),
            "performance_metric_read": False,
            "model_bytes_modified": False,
            "claim_allowed": False,
        }
        atomic_json(staging / "NORMALIZATION.json", record)
        os.replace(staging, args.output_root)
    finally:
        if staging.exists():
            raise RuntimeError(f"incomplete E14 normalization staging remains: {staging}")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
