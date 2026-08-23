#!/usr/bin/env python3
"""Create the outcome-authorized but identifier-only E14 Gate-C job manifest."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import gdp_cem_e14_specs as spec
from evaluate_gdp_cem_e14_gate_c import read_gate_b
from gdp_cem_e14_data import sha256_file


def atomic_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


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
        raise RuntimeError("E14 Gate-C manifest contains CR bytes")


def validate_normalization(
    path: Path,
    *,
    expected_sha256: str,
    normalized_root: Path,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise RuntimeError("E14 normalization audit hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    endpoint_manifest = normalized_root / "manifests" / "endpoint.tsv"
    sage_manifest = normalized_root / "manifests" / "sage.tsv"
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e14_crlf_path_normalization"
        or value.get("analysis_role") != "non_metric_artifact_path_erratum"
        or value.get("mode") != "full"
        or int(value.get("logical_link_count", -1)) != 44
        or value.get("endpoint_manifest_lf_sha256")
        != sha256_file(endpoint_manifest)
        or value.get("sage_manifest_lf_sha256") != sha256_file(sage_manifest)
        or value.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != source_manifest_sha256
        or value.get("performance_metric_read") is not False
        or value.get("model_bytes_modified") is not False
        or value.get("claim_allowed") is not False
        or b"\r" in endpoint_manifest.read_bytes()
        or b"\r" in sage_manifest.read_bytes()
    ):
        raise RuntimeError("E14 normalization audit differs")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-b-audit", type=Path, required=True)
    parser.add_argument("--gate-b-audit-sha256", required=True)
    parser.add_argument("--normalized-root", type=Path, required=True)
    parser.add_argument("--normalization-audit", type=Path, required=True)
    parser.add_argument("--normalization-audit-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.gate_b_audit,
        args.normalized_root,
        args.normalization_audit,
        args.protocol,
        args.source_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_tsv.exists() or args.output_json.exists():
        raise SystemExit("refusing existing E14 Gate-C manifest artifacts")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E14 Gate-C protocol hash differs")
    source_hash = sha256_file(args.source_manifest)
    gate_b = read_gate_b(args.gate_b_audit, args.gate_b_audit_sha256)
    validate_normalization(
        args.normalization_audit,
        expected_sha256=args.normalization_audit_sha256,
        normalized_root=args.normalized_root,
        source_manifest_sha256=source_hash,
    )
    endpoint_order = tuple(
        endpoint for endpoint in ("vad", "cvd") if endpoint in gate_b["eligible_endpoints"]
    )
    if list(endpoint_order) != gate_b["eligible_endpoints"]:
        raise RuntimeError("E14 Gate-B endpoint order differs")
    arms = ["base_cem", "sage_reconstruction"]
    for endpoint in endpoint_order:
        arms.extend((f"{endpoint}_true", f"{endpoint}_gaussian"))
    rows: list[dict[str, Any]] = []
    for task in spec.TASKS:
        for horizon in spec.GATE_C_HORIZONS:
            for model_seed in spec.MODEL_SEEDS:
                for arm in arms:
                    for shard in range(spec.GATE_C_SHARD_COUNT):
                        rows.append(
                            {
                                "array_id": len(rows),
                                "task": task,
                                "arm": arm,
                                "model_seed": model_seed,
                                "horizon": horizon,
                                "shard": shard,
                            }
                        )
    expected = (
        len(spec.TASKS)
        * len(spec.GATE_C_HORIZONS)
        * len(spec.MODEL_SEEDS)
        * len(arms)
        * spec.GATE_C_SHARD_COUNT
    )
    if len(rows) != expected:
        raise RuntimeError("E14 Gate-C manifest cardinality differs")
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    fields = ("array_id", "task", "arm", "model_seed", "horizon", "shard")
    write_lf_tsv(args.output_tsv, fields, rows)
    record = {
        "status": "ok",
        "kind": "gdp_cem_e14_p2_gate_c_evaluation_manifest",
        "analysis_role": "P2_closed_loop_endpoint_selection_development",
        "eligible_endpoints": list(endpoint_order),
        "arms": arms,
        "tasks": list(spec.TASKS),
        "horizons": list(spec.GATE_C_HORIZONS),
        "model_seeds": list(spec.MODEL_SEEDS),
        "shard_size": spec.GATE_C_SHARD_SIZE,
        "shard_count": spec.GATE_C_SHARD_COUNT,
        "row_count": len(rows),
        "gate_b_audit": str(args.gate_b_audit),
        "gate_b_audit_sha256": args.gate_b_audit_sha256,
        "normalization_audit": str(args.normalization_audit),
        "normalization_audit_sha256": args.normalization_audit_sha256,
        "normalized_root": str(args.normalized_root),
        "endpoint_manifest_lf_sha256": sha256_file(
            args.normalized_root / "manifests" / "endpoint.tsv"
        ),
        "sage_manifest_lf_sha256": sha256_file(
            args.normalized_root / "manifests" / "sage.tsv"
        ),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "output_tsv": str(args.output_tsv),
        "output_tsv_sha256": sha256_file(args.output_tsv),
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    atomic_json(args.output_json, record)
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
