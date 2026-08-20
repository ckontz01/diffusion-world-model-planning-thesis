#!/usr/bin/env python3
"""Authorize only the frozen E6 exposed-D2 pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROTOCOL_SHA256 = "2a7facb513f6fcda8a6d923e736d30820aa59e14735bf621b960756d13e9b196"
E3_SUMMARY_SHA256 = "2a4134b49f770cd3f339d73233183d5bd2013b562aee751abc0e8a744959fdbb"
E5_SUMMARY_SHA256 = "0c956e95e258eeb440bad12e71de3528b317c49c06f50519e5bc110e3c5da553"
D2_HASHES = {
    "pusht": (
        "85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89",
        "fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede",
    ),
    "reacher": (
        "a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61",
        "f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11",
    ),
    "cube": (
        "bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388",
        "fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b",
    ),
}
ARMS = [
    "b0",
    "acid_cont",
    "forward_cont",
    "rdx_cont",
    "rdx_gate_tail5_q20",
    "rdx_gate_tail5_q40",
    "rdx_gate_all_q40",
    "rdx_shuffled_gate_tail5_q40",
    "acid_gate_tail5_q40",
    "forward_gate_tail5_q40",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reject_protected(path: Path) -> None:
    lowered = str(path).lower().replace("_", "-")
    if "c1" in lowered or "i1" in lowered:
        raise RuntimeError(f"protected path is forbidden: {path}")


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--e3-summary", type=Path, required=True)
    parser.add_argument("--e5-summary", type=Path, required=True)
    parser.add_argument(
        "--d2-input", nargs=3, action="append", metavar=("TASK", "TSV", "PROVENANCE"), required=True
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.protocol, args.source_manifest, args.e3_summary, args.e5_summary):
        reject_protected(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E6 authorization output")
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E6 protocol hash mismatch")
    if sha256_file(args.e3_summary) != E3_SUMMARY_SHA256:
        raise RuntimeError("E3 result hash mismatch")
    if sha256_file(args.e5_summary) != E5_SUMMARY_SHA256:
        raise RuntimeError("E5 result hash mismatch")
    inputs: dict[str, dict[str, str]] = {}
    for task, tsv_text, provenance_text in args.d2_input:
        if task not in D2_HASHES or task in inputs:
            raise ValueError(f"invalid or duplicate task: {task}")
        tsv, provenance = Path(tsv_text), Path(provenance_text)
        reject_protected(tsv)
        reject_protected(provenance)
        expected_tsv, expected_provenance = D2_HASHES[task]
        if (
            not tsv.is_file()
            or not provenance.is_file()
            or sha256_file(tsv) != expected_tsv
            or sha256_file(provenance) != expected_provenance
        ):
            raise RuntimeError(f"D2 input hash mismatch: {task}")
        inputs[task] = {
            "manifest": str(tsv),
            "manifest_sha256": expected_tsv,
            "provenance": str(provenance),
            "provenance_sha256": expected_provenance,
        }
    if set(inputs) != set(D2_HASHES):
        raise RuntimeError("E6 authorization requires all three D2 inputs")
    value = {
        "status": "authorized_for_exposed_d2_development_only",
        "kind": "acid_alt_e6_d2_authorization",
        "analysis_role": "post_e3_e5_exposed_d2_planner_integration_development",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "user_authorized_date": "2026-08-16",
        "protocol": str(args.protocol),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "e3_summary": str(args.e3_summary),
        "e3_summary_sha256": E3_SUMMARY_SHA256,
        "e5_summary": str(args.e5_summary),
        "e5_summary_sha256": E5_SUMMARY_SHA256,
        "d2_inputs": inputs,
        "arms": ARMS,
        "primary_arm": "rdx_gate_tail5_q40",
        "scorer_seed": 6101,
        "planner_seed": 8301,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "d3_selection_allowed_before_analysis": False,
        "protected_c1_i1_read": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output_dir / "authorization.json", value)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
