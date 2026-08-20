#!/usr/bin/env python3
"""Record E12 Stage-B validity without turning failed artifacts into a registry.

This audit reads P1-only training summaries.  It deliberately accepts a
well-formed ``invalid`` training result so that a predeclared Stage-B failure
is preserved as evidence, while provenance or file-integrity errors still
fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import gdp_cem_e12_specs as spec


METHODS = {
    "prism_head_h25": (
        "prism-head-h25",
        "gdp_cem_e12_prism_prior_head_training",
        "h25",
    ),
    "prism_head_endframe": (
        "prism-head-endframe",
        "gdp_cem_e12_prism_prior_head_training",
        "endframe",
    ),
    "prism_dp": (
        "prism-dp",
        "gdp_cem_e12_prism_dp_reconstruction_training",
        None,
    ),
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


def audit_entry(
    summary_path: Path,
    *,
    task: str,
    seed: int,
    method: str,
    expected_kind: str,
    expected_goal_mode: str | None,
    source_sha256: str,
) -> tuple[dict[str, Any], bool]:
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validity = summary.get("validity")
    if not isinstance(validity, dict) or not isinstance(validity.get("passed"), bool):
        raise RuntimeError(f"malformed validity object: {summary_path}")
    passed = validity["passed"]
    expected_status = "ok" if passed else "invalid"
    checks = {
        "status_matches_validity": summary.get("status") == expected_status,
        "kind": summary.get("kind") == expected_kind,
        "task": summary.get("task") == task,
        "seed": summary.get("seed") == seed,
        "protocol": summary.get("protocol_sha256") == spec.PROTOCOL_SHA256,
        "training_source": summary.get("source_manifest_sha256") == source_sha256,
        "no_protected_p4_c1_i1": summary.get("protected_p4_c1_i1_read") is False,
        "no_d3": summary.get("d3_read") is False,
        "no_d4": summary.get("d4_read") is False,
        "goal_mode": (
            expected_goal_mode is None
            or summary.get("goal_mode") == expected_goal_mode
        ),
    }
    failed_checks = sorted(name for name, value in checks.items() if not value)
    if failed_checks:
        raise RuntimeError(
            f"provenance mismatch for {task}/{seed}/{method}: {failed_checks}"
        )

    checkpoint = Path(summary.get("checkpoint", ""))
    trace = Path(summary.get("training_trace", ""))
    expected_parent = summary_path.parent.resolve()
    for label, path, claimed_hash in (
        ("checkpoint", checkpoint, summary.get("checkpoint_sha256")),
        ("training trace", trace, summary.get("training_trace_sha256")),
    ):
        if not path.is_file() or path.resolve().parent != expected_parent:
            raise RuntimeError(f"invalid {label} path for {task}/{seed}/{method}")
        if sha256_file(path) != claimed_hash:
            raise RuntimeError(f"{label} hash mismatch for {task}/{seed}/{method}")

    diagnostics: dict[str, Any]
    if method.startswith("prism_head"):
        diagnostics = {
            "best_epoch": summary.get("best_epoch"),
            "initial_validation": summary.get("initial_validation"),
            "best_validation": summary.get("best_validation"),
        }
    else:
        diagnostics = {
            "best_step": summary.get("best_step"),
            "initial_validation_epsilon_mse": summary.get(
                "initial_validation_epsilon_mse"
            ),
            "best_validation_epsilon_mse": summary.get(
                "best_validation_epsilon_mse"
            ),
            "reconstruction_not_official": summary.get(
                "reconstruction_not_official"
            ),
        }
    return (
        {
            "status": summary["status"],
            "validity": validity,
            "summary": str(summary_path.resolve()),
            "summary_sha256": sha256_file(summary_path),
            "checkpoint": str(checkpoint.resolve()),
            "checkpoint_sha256": summary["checkpoint_sha256"],
            "training_trace": str(trace.resolve()),
            "training_trace_sha256": summary["training_trace_sha256"],
            "parameter_count": int(summary["parameter_count"]),
            "elapsed_seconds": float(summary["elapsed_seconds"]),
            "runtime": summary.get("runtime"),
            "diagnostics": diagnostics,
        },
        passed,
    )


def build_audit(
    results_root: Path,
    protocol: Path,
    training_source_manifest: Path,
) -> dict[str, Any]:
    if sha256_file(protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E12 Stage-B audit protocol hash differs")
    source_sha256 = sha256_file(training_source_manifest)
    entries: dict[str, dict[str, dict[str, Any]]] = {}
    failures: list[dict[str, Any]] = []
    for task in spec.TASKS:
        entries[task] = {}
        for seed in spec.SEEDS:
            entries[task][str(seed)] = {}
            for method, (directory, kind, goal_mode) in METHODS.items():
                summary_path = (
                    results_root / task / f"seed-{seed}" / directory / "summary.json"
                )
                entry, passed = audit_entry(
                    summary_path,
                    task=task,
                    seed=seed,
                    method=method,
                    expected_kind=kind,
                    expected_goal_mode=goal_mode,
                    source_sha256=source_sha256,
                )
                entries[task][str(seed)][method] = entry
                if not passed:
                    failures.append(
                        {
                            "task": task,
                            "seed": seed,
                            "method": method,
                            "validity": entry["validity"],
                        }
                    )

    passed = not failures
    return {
        "status": "passed" if passed else "blocked",
        "kind": "gdp_cem_e12_stage_b_validity_audit",
        "analysis_role": "P1_only_stage_gate_audit",
        "protocol": str(protocol.resolve()),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest": str(training_source_manifest.resolve()),
        "training_source_manifest_sha256": source_sha256,
        "expected_artifact_count": len(spec.TASKS) * len(spec.SEEDS) * len(METHODS),
        "audited_artifact_count": len(spec.TASKS) * len(spec.SEEDS) * len(METHODS),
        "invalid_artifact_count": len(failures),
        "failed_artifacts": failures,
        "entries": entries,
        "stage_b_passed": passed,
        "stage_c_authorized": passed,
        "stage_d_authorized": False,
        "stage_d_reason": (
            "pending_stage_c" if passed else "blocked_by_stage_b_validity_failure"
        ),
        "d3_outcomes_read": False,
        "d4_outcomes_read": False,
        "protected_p4_c1_i1_read": False,
    }


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
    report = build_audit(args.results_root, args.protocol, args.training_source_manifest)
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
