#!/usr/bin/env python3
"""Create an authorization record for only the E6D exposed-D2 controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from acid_alt_e6d_allgate import ARMS


PROTOCOL_SHA256 = "808f16435775c04b36862637efa200bc4eb47797089ac3f913be962035ed9fd4"
E6_SUMMARY_SHA256 = "84ae66457c70f5a8c386d682dab5a77bfd807f3fdf0c52de0ea7b3264ebbc0cc"
D2_HASHES = {
    "pusht": ("85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89", "fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede"),
    "reacher": ("a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61", "f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11"),
    "cube": ("bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388", "fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    parser.add_argument("--e6-summary", type=Path, required=True)
    parser.add_argument("--d2-input", nargs=3, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E6D authorization output")
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E6D protocol hash mismatch")
    if sha256_file(args.e6_summary) != E6_SUMMARY_SHA256:
        raise RuntimeError("E6 result hash mismatch")
    inputs = {}
    for task, manifest_text, provenance_text in args.d2_input:
        if task not in D2_HASHES or task in inputs:
            raise ValueError(f"invalid E6D D2 task: {task}")
        manifest, provenance = Path(manifest_text), Path(provenance_text)
        expected_manifest, expected_provenance = D2_HASHES[task]
        if (
            not manifest.is_file()
            or not provenance.is_file()
            or sha256_file(manifest) != expected_manifest
            or sha256_file(provenance) != expected_provenance
        ):
            raise RuntimeError(f"E6D D2 input differs: {task}")
        inputs[task] = {
            "manifest": str(manifest), "manifest_sha256": expected_manifest,
            "provenance": str(provenance), "provenance_sha256": expected_provenance,
        }
    if set(inputs) != set(D2_HASHES):
        raise RuntimeError("E6D requires all three D2 inputs")
    value = {
        "status": "authorized_for_exposed_d2_diagnostic_only",
        "kind": "acid_alt_e6d_d2_authorization",
        "analysis_role": "post_e6_exposed_d2_allgate_diagnostic",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": str(args.protocol), "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest": str(args.source_manifest), "source_manifest_sha256": sha256_file(args.source_manifest),
        "e6_summary": str(args.e6_summary), "e6_summary_sha256": E6_SUMMARY_SHA256,
        "e3_summary_sha256": "2a4134b49f770cd3f339d73233183d5bd2013b562aee751abc0e8a744959fdbb",
        "e5_summary_sha256": "0c956e95e258eeb440bad12e71de3528b317c49c06f50519e5bc110e3c5da553",
        "d2_inputs": inputs,
        "arms": list(ARMS), "scorer_seed": 6101, "planner_seed": 8301,
        "confirmation_claim_allowed": False, "alternative_to_acid_claim_allowed": False,
        "d3_access_allowed": False, "protected_c1_i1_read": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output_dir / "authorization.json", value)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
