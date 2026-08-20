#!/usr/bin/env python3
"""Join all predeclared C1 evidence into one conservative claim decision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from acid_alternative.io_utils import atomic_write_json, sha256_file

TASKS = {"pusht", "reacher", "cube"}


def read(path: Path, kind: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "ok" or value.get("kind") != kind:
        raise RuntimeError(f"{path}: expected complete {kind}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closed-loop", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--mechanism", type=Path, required=True)
    parser.add_argument("--confirmation-authorization", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing nonempty output directory: {args.output_dir}")
    closed = read(args.closed_loop, "matched_five_arm_closed_loop_analysis")
    validation = read(args.validation, "heldout_correct_action_identification_analysis")
    mechanism = read(args.mechanism, "three_task_same_candidate_mechanism_analysis")
    source_hash = sha256_file(args.source_manifest)
    if not args.confirmation_authorization.is_file():
        raise FileNotFoundError(args.confirmation_authorization)
    authorization_hash = sha256_file(args.confirmation_authorization)
    if (
        closed.get("role") != "confirmation"
        or validation.get("analysis_role") != "C1"
        or validation.get("confirmatory") is not True
        or mechanism.get("analysis_role") != "C1"
    ):
        raise RuntimeError("claim assembly requires locked confirmatory analyses")
    if any(
        set(value.get("tasks", [])) != TASKS
        for value in (closed, validation, mechanism)
    ):
        raise RuntimeError(
            "claim analyses do not contain exactly the frozen task suite"
        )
    if any(
        value.get("source_manifest_sha256") != source_hash
        for value in (closed, validation, mechanism)
    ):
        raise RuntimeError("claim analyses do not share the declared source snapshot")
    authorization_hashes = {
        closed.get("confirmation_authorization_sha256"),
        validation.get("confirmation_authorization_sha256"),
        mechanism.get("confirmation_authorization_sha256"),
    }
    if len(authorization_hashes) != 1 or None in authorization_hashes:
        raise RuntimeError("claim analyses do not share one C1 authorization")
    if authorization_hashes != {authorization_hash}:
        raise RuntimeError("claim analyses differ from the declared C1 authorization")
    closed_gates = closed["claim_gates_closed_loop_only"]
    gates = {
        "useful_diffusion_vs_b0": bool(closed_gates["useful_diffusion_vs_b0"]),
        "acid_noninferiority": bool(closed_gates["acid_noninferiority"]),
        "diffusion_specific": bool(
            closed_gates["diffusion_specific_closed_loop"]
            and validation["claim_gate"]["pass"]
        ),
        "breadth": bool(closed_gates["breadth"]),
        "mechanism": bool(mechanism["all_required_mechanism_gates_pass"]),
    }
    all_pass = all(gates.values())
    transition_verifier_only = all(
        gates[name]
        for name in (
            "useful_diffusion_vs_b0",
            "acid_noninferiority",
            "breadth",
            "mechanism",
        )
    )
    if all_pass:
        conclusion = (
            "The frozen evidence supports diffusion transition verification as an "
            "alternative to reconstructed ACID on this three-task Le-WM suite."
        )
    elif transition_verifier_only and not gates["diffusion_specific"]:
        conclusion = (
            "Learned transition verification is competitive with reconstructed ACID, "
            "but the evidence does not attribute the gain specifically to diffusion."
        )
    elif gates["acid_noninferiority"] and not gates["useful_diffusion_vs_b0"]:
        conclusion = (
            "Diffusion verification is statistically comparable to reconstructed ACID "
            "under the frozen margin, but is not established as a repair over CEM."
        )
    else:
        conclusion = (
            "The frozen evidence does not support diffusion verification as an ACID "
            "alternative under the predeclared gates."
        )
    result = {
        "status": "ok",
        "kind": "acid_alternative_c1_claim_decision",
        "scope": "Le-WM only: PushT, Reacher, and OGBench single Cube",
        "gates": gates,
        "all_five_gates_pass": all_pass,
        "conclusion": conclusion,
        "cross_backbone_generalization_supported": False,
        "cross_backbone_note": "A successful PLDM extension is still required for a world-model-family generalization claim.",
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_hash,
        "confirmation_authorization": str(args.confirmation_authorization),
        "confirmation_authorization_sha256": authorization_hash,
        "inputs": {
            "closed_loop": str(args.closed_loop),
            "closed_loop_sha256": sha256_file(args.closed_loop),
            "validation": str(args.validation),
            "validation_sha256": sha256_file(args.validation),
            "mechanism": str(args.mechanism),
            "mechanism_sha256": sha256_file(args.mechanism),
            "confirmation_authorization": str(args.confirmation_authorization),
            "confirmation_authorization_sha256": authorization_hash,
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(args.output_dir / "summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
