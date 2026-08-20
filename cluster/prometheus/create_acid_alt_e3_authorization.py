#!/usr/bin/env python3
"""Create the post-v3 exploratory-only E3 authorization record."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


E3_PROTOCOL_SHA256 = (
    "c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0"
)
V3_PROTOCOL_SHA256 = (
    "c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb"
)
V3_SOURCE_MANIFEST_SHA256 = (
    "2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea"
)
V3_UPSTREAM_SOURCE_MANIFEST_SHA256 = (
    "875a9cbc19dba78db1706169b7f2d8bc97a70913d82b55f793735dfe8c2df388"
)
STAGE_A_SUMMARY_SHA256 = (
    "0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37"
)
STAGE_A_MANIFEST_SHA256 = (
    "3558b8612787035cfa92c17d8a36f46f379bb2812f67aa0a73438d8cab974053"
)
D2_HASHES = {
    "pusht": {
        "manifest": "85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89",
        "provenance": "fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede",
    },
    "reacher": {
        "manifest": "a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61",
        "provenance": "f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11",
    },
    "cube": {
        "manifest": "bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388",
        "provenance": "fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b",
    },
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
    parser.add_argument("--stage-a-summary", type=Path, required=True)
    parser.add_argument("--stage-a-manifest", type=Path, required=True)
    parser.add_argument(
        "--d2-input",
        nargs=3,
        action="append",
        metavar=("TASK", "MANIFEST", "PROVENANCE"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    required_files = (
        args.protocol,
        args.source_manifest,
        args.stage_a_summary,
        args.stage_a_manifest,
    )
    if any(not path.is_file() for path in required_files):
        raise FileNotFoundError("an E3 authorization input is missing")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E3 authorization output")
    if sha256_file(args.protocol) != E3_PROTOCOL_SHA256:
        raise RuntimeError("E3 protocol hash mismatch")
    if sha256_file(args.stage_a_summary) != STAGE_A_SUMMARY_SHA256:
        raise RuntimeError("v3 Stage-A summary hash mismatch")
    if sha256_file(args.stage_a_manifest) != STAGE_A_MANIFEST_SHA256:
        raise RuntimeError("v3 Stage-A manifest hash mismatch")

    stage_a = json.loads(args.stage_a_summary.read_text(encoding="utf-8"))
    stage_a_manifest = json.loads(
        args.stage_a_manifest.read_text(encoding="utf-8")
    )
    expected_gates = {
        "1_rdx_positive_all_tasks_and_pooled": True,
        "2_rdx_beats_shuffled": True,
        "3_rdx_noninferior_forward_and_acid": False,
        "4_ae_beats_shuffled_without_negative_task": True,
        "5_ae_selection_noninferior_acid": True,
    }
    if (
        stage_a.get("status") != "ok"
        or stage_a.get("kind") != "acid_alt_v3_d2_stage_a_analysis"
        or stage_a.get("decision") != "stop_before_stage_b"
        or stage_a.get("all_stage_a_gates_pass") is not False
        or stage_a.get("gates") != expected_gates
        or stage_a.get("protocol_sha256") != V3_PROTOCOL_SHA256
        or stage_a.get("source_manifest_sha256")
        != V3_SOURCE_MANIFEST_SHA256
        or stage_a.get("upstream_source_manifest_sha256")
        != V3_UPSTREAM_SOURCE_MANIFEST_SHA256
        or stage_a.get("protected_c1_i1_read") is not False
        or stage_a_manifest.get("stage_b_authorized") is not False
        or stage_a_manifest.get("summary_sha256") != STAGE_A_SUMMARY_SHA256
        or stage_a_manifest.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("v3 Stage-A failure identity is not the frozen result")

    d2_inputs: dict[str, dict[str, str]] = {}
    for task, manifest_text, provenance_text in args.d2_input:
        if task not in D2_HASHES or task in d2_inputs:
            raise ValueError(f"unexpected or duplicate D2 task: {task}")
        manifest = Path(manifest_text)
        provenance = Path(provenance_text)
        if not manifest.is_file() or not provenance.is_file():
            raise FileNotFoundError(f"missing D2 input for {task}")
        manifest_sha = sha256_file(manifest)
        provenance_sha = sha256_file(provenance)
        if (
            manifest_sha != D2_HASHES[task]["manifest"]
            or provenance_sha != D2_HASHES[task]["provenance"]
        ):
            raise RuntimeError(f"D2 input hash mismatch for {task}")
        d2_inputs[task] = {
            "manifest": str(manifest),
            "manifest_sha256": manifest_sha,
            "provenance": str(provenance),
            "provenance_sha256": provenance_sha,
        }
    if set(d2_inputs) != set(D2_HASHES):
        raise RuntimeError("E3 authorization requires all three D2 tasks")

    authorization = {
        "status": "authorized_for_exploratory_development_only",
        "kind": "acid_alt_e3_d2_exploratory_authorization",
        "analysis_role": "post_v3_exploratory_d2_closed_loop_development",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "user_authorized_date": "2026-08-16",
        "protocol": str(args.protocol),
        "protocol_sha256": E3_PROTOCOL_SHA256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "v3_protocol_sha256": V3_PROTOCOL_SHA256,
        "v3_source_manifest_sha256": V3_SOURCE_MANIFEST_SHA256,
        "v3_upstream_source_manifest_sha256": (
            V3_UPSTREAM_SOURCE_MANIFEST_SHA256
        ),
        "stage_a_summary": str(args.stage_a_summary),
        "stage_a_summary_sha256": STAGE_A_SUMMARY_SHA256,
        "stage_a_manifest": str(args.stage_a_manifest),
        "stage_a_manifest_sha256": STAGE_A_MANIFEST_SHA256,
        "v3_stage_a_decision": "stop_before_stage_b",
        "v3_stage_b_authorized": False,
        "d2_manifest_job_id": 297535,
        "residual_training_job_id": 297533,
        "d2_inputs": d2_inputs,
        "arms": ["b0", "acid", "forward", "rdx", "ae", "ae_shuffled"],
        "scorer_seeds": [6101, 6102, 6103],
        "planner_seeds": [8301, 8302, 8303],
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "protected_c1_i1_read": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "authorization.json"
    atomic_json(output, authorization)
    atomic_json(
        args.output_dir / "manifest.json",
        {
            "status": "ok",
            "kind": "acid_alt_e3_d2_exploratory_authorization_manifest",
            "authorization": str(output),
            "authorization_sha256": sha256_file(output),
            "protocol_sha256": E3_PROTOCOL_SHA256,
            "source_manifest_sha256": sha256_file(args.source_manifest),
            "stage_a_summary_sha256": STAGE_A_SUMMARY_SHA256,
            "stage_a_manifest_sha256": STAGE_A_MANIFEST_SHA256,
            "v3_stage_b_authorized": False,
            "protected_c1_i1_read": False,
        },
    )
    print(json.dumps(authorization, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
