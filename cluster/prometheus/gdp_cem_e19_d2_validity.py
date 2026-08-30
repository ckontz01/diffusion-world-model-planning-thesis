#!/usr/bin/env python3
"""Run the non-metric Stage-A validity gate for E19-D2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch

import analyze_gdp_cem_e19_discrepancy as legacy
import gdp_cem_e19_d2_specs as d2
import gdp_cem_e19_discrepancy_specs as spec
from trace_gdp_cem_e19_discrepancy import canonical_sha256


METHOD_CHECK_KEYS = frozenset({"latents_present", "history_semantics_valid"})


def method_event_checks(events: list[dict[str, Any]], method: str) -> dict[str, bool]:
    history_present = any(row.get("kind") == "history_latents" for row in events)
    final_goal_present = any(
        row.get("kind") == "final_goal_latents" for row in events
    )
    local_goal_present = any(
        row.get("kind") in {"local_goal", "cube_local_goal_cache"}
        for row in events
    )
    if method in d2.HISTORY_CONDITIONED_METHODS:
        history_semantics_valid = history_present
    elif method in d2.HISTORY_FREE_METHODS:
        history_semantics_valid = not history_present
    else:
        history_semantics_valid = False
    return {
        "final_goal_present": final_goal_present,
        "local_goal_present": local_goal_present,
        "history_semantics_valid": history_semantics_valid,
    }


def trace_gate(
    trace: dict[str, Any], sentinel: spec.Sentinel, repeat: int
) -> dict[str, Any]:
    """Apply the frozen gate with only the history expectation made method-aware."""

    gate = legacy.trace_gate(trace, sentinel, repeat)
    method_checks = method_event_checks(trace["events"], sentinel.method)
    gate["checks"]["history_semantics_valid"] = method_checks[
        "history_semantics_valid"
    ]
    gate["checks"]["latents_present"] = all(method_checks.values())
    gate["method_event_checks"] = method_checks
    gate["passed"] = all(gate["checks"].values())
    return gate


def _mark(
    checks: dict[str, bool],
    failed: list[str],
    category: str,
    passed: bool,
    detail: str,
) -> None:
    checks[category] = checks[category] and bool(passed)
    if not passed:
        failed.append(f"{category}:{detail}")


def _forbidden_flags_valid(payload: dict[str, Any]) -> bool:
    return all(
        (
            payload.get("official_sage_source_modified") is False,
            payload.get("checkpoint_modified") is False,
            payload.get("planner_parameter_modified") is False,
            payload.get("protected_metric_artifact_read") is False,
            payload.get("e18_vs_sage_comparison_run") is False,
            payload.get("d5_read") is False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d2-snapshot", type=Path, required=True)
    parser.add_argument("--raw-snapshot", type=Path, required=True)
    parser.add_argument("--raw-run-root", type=Path, required=True)
    parser.add_argument("--e19-run-root", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)

    checks = {
        "bank_hash_valid": True,
        "trace_schema_valid": True,
        "method_event_semantics_valid": True,
        "identity_hashes_valid": True,
        "comparison_schema_valid": True,
        "forbidden_read_flags_valid": True,
    }
    failed: list[str] = []

    identity_files = {
        args.raw_snapshot / "SOURCE-MANIFEST.sha256": d2.PARENT_SOURCE_MANIFEST_SHA256,
        args.raw_snapshot / spec.PROTOCOL_FILENAME: d2.PARENT_PROTOCOL_SHA256,
        args.d2_snapshot / "analyze_gdp_cem_e19_discrepancy.py": d2.LEGACY_ANALYZER_SHA256,
        args.d2_snapshot / "gdp_cem_e19_discrepancy_specs.py": d2.PARENT_SPECS_SHA256,
        args.d2_snapshot / "trace_gdp_cem_e19_discrepancy.py": d2.PARENT_TRACER_SHA256,
    }
    expected_paths = {
        "raw_snapshot": (args.raw_snapshot, Path(d2.PARENT_SNAPSHOT)),
        "raw_run_root": (args.raw_run_root, Path(d2.PARENT_RUN_ROOT)),
        "e19_run_root": (args.e19_run_root, Path(d2.E19_RUN_ROOT)),
        "comparison": (
            args.comparison,
            Path(d2.PARENT_RUN_ROOT) / "comparison" / "COMPARISON-AUDIT.json",
        ),
    }
    for label, (actual, expected) in expected_paths.items():
        _mark(
            checks,
            failed,
            "identity_hashes_valid",
            actual.resolve() == expected.resolve(),
            label,
        )
    for path, expected in identity_files.items():
        try:
            passed = legacy.sha256_file(path) == expected
        except Exception:
            passed = False
        _mark(
            checks,
            failed,
            "identity_hashes_valid",
            passed,
            path.name,
        )

    for sentinel in spec.SENTINELS:
        e19_path = legacy.e19_result_path(args.e19_run_root, sentinel)
        try:
            e19_hash_valid = (
                legacy.sha256_file(e19_path) == sentinel.e19_result_sha256
            )
        except Exception:
            e19_hash_valid = False
        _mark(
            checks,
            failed,
            "identity_hashes_valid",
            e19_hash_valid,
            f"e19_result_s{sentinel.sentinel_id}",
        )
        for repeat in spec.REPEATS:
            label = f"s{sentinel.sentinel_id}_r{repeat}"
            directory = (
                args.raw_run_root
                / "sentinels"
                / f"s{sentinel.sentinel_id}"
                / f"r{repeat}"
            )
            try:
                legacy.verify_sha256_file(directory)
                result = legacy.load_json(directory / "results.json")
                trace = legacy.load_json(directory / "trace.json")
                bank = torch.load(
                    directory / "comparison-bank.pt",
                    map_location="cpu",
                    weights_only=False,
                )
            except Exception:
                for category in (
                    "bank_hash_valid",
                    "trace_schema_valid",
                    "method_event_semantics_valid",
                    "identity_hashes_valid",
                    "forbidden_read_flags_valid",
                ):
                    _mark(checks, failed, category, False, label)
                continue

            bank_content = {
                key: value for key, value in bank.items() if key != "content_sha256"
            }
            _mark(
                checks,
                failed,
                "bank_hash_valid",
                canonical_sha256(bank_content) == bank.get("content_sha256"),
                label,
            )
            try:
                gate = trace_gate(trace, sentinel, repeat)
            except Exception:
                _mark(checks, failed, "trace_schema_valid", False, label)
                _mark(
                    checks,
                    failed,
                    "method_event_semantics_valid",
                    False,
                    label,
                )
            else:
                schema_valid = all(
                    passed
                    for key, passed in gate["checks"].items()
                    if key not in METHOD_CHECK_KEYS
                )
                method_valid = gate["checks"]["latents_present"] and gate[
                    "checks"
                ]["history_semantics_valid"]
                _mark(
                    checks,
                    failed,
                    "trace_schema_valid",
                    schema_valid,
                    label,
                )
                _mark(
                    checks,
                    failed,
                    "method_event_semantics_valid",
                    method_valid,
                    label,
                )

            result_identity_valid = all(
                (
                    result.get("benchmark") == sentinel.benchmark,
                    result.get("method") == sentinel.method,
                    result.get("seed") == sentinel.seed,
                    result.get("horizon") == sentinel.horizon,
                    result.get("num_eval") == spec.EXPECTED_EPISODES_PER_RUN,
                    trace.get("diagnostic_source_manifest_sha256")
                    == d2.PARENT_SOURCE_MANIFEST_SHA256,
                    trace.get("diagnostic_protocol_sha256")
                    == d2.PARENT_PROTOCOL_SHA256,
                    trace.get("e19_source_manifest_sha256")
                    == spec.E19_SOURCE_MANIFEST_SHA256,
                    trace.get("e19_protocol_sha256") == spec.E19_PROTOCOL_SHA256,
                    trace.get("official_sage_commit") == spec.SAGE_GIT_COMMIT,
                    trace.get("official_sage_tree") == spec.SAGE_GIT_TREE,
                )
            )
            _mark(
                checks,
                failed,
                "identity_hashes_valid",
                result_identity_valid,
                label,
            )
            _mark(
                checks,
                failed,
                "forbidden_read_flags_valid",
                _forbidden_flags_valid(trace)
                and trace.get("observational_only") is True,
                label,
            )

    comparison_dir = args.comparison.parent
    try:
        legacy.verify_sha256_file(comparison_dir)
        comparison = legacy.load_json(args.comparison)
    except Exception:
        comparison = {}
        _mark(
            checks,
            failed,
            "comparison_schema_valid",
            False,
            "load_or_checksum",
        )
    required_comparison_fields = {
        "diagnostic_source_manifest_sha256",
        "diagnostic_protocol_sha256",
        "e19_source_manifest_sha256",
        "e19_protocol_sha256",
        "official_sage_commit",
        "official_sage_tree",
        "transport_comparisons_valid",
        "runtime_bank_reconstruction_valid",
        "model_state_mismatch",
        "runtime_mismatch",
        "transport_mismatch",
        "episode_executed",
        "official_sage_source_modified",
        "checkpoint_modified",
        "planner_parameter_modified",
        "expected_values_modified",
        "tolerance_modified",
        "manifest_modified",
        "e19_result_modified",
        "protected_metric_artifact_read",
        "e18_vs_sage_comparison_run",
        "d5_read",
    }
    comparison_schema_valid = all(
        (
            required_comparison_fields.issubset(comparison),
            comparison.get("transport_comparisons_valid") is True,
            comparison.get("runtime_bank_reconstruction_valid") is True,
        )
    )
    _mark(
        checks,
        failed,
        "comparison_schema_valid",
        comparison_schema_valid,
        "required_fields_and_validity",
    )
    comparison_identity_valid = all(
        (
            comparison.get("diagnostic_source_manifest_sha256")
            == d2.PARENT_SOURCE_MANIFEST_SHA256,
            comparison.get("diagnostic_protocol_sha256")
            == d2.PARENT_PROTOCOL_SHA256,
            comparison.get("e19_source_manifest_sha256")
            == spec.E19_SOURCE_MANIFEST_SHA256,
            comparison.get("e19_protocol_sha256") == spec.E19_PROTOCOL_SHA256,
            comparison.get("official_sage_commit") == spec.SAGE_GIT_COMMIT,
            comparison.get("official_sage_tree") == spec.SAGE_GIT_TREE,
        )
    )
    _mark(
        checks,
        failed,
        "identity_hashes_valid",
        comparison_identity_valid,
        "comparison",
    )
    comparison_forbidden_valid = all(
        (
            _forbidden_flags_valid(comparison),
            comparison.get("episode_executed") is False,
            comparison.get("expected_values_modified") is False,
            comparison.get("tolerance_modified") is False,
            comparison.get("manifest_modified") is False,
            comparison.get("e19_result_modified") is False,
        )
    )
    _mark(
        checks,
        failed,
        "forbidden_read_flags_valid",
        comparison_forbidden_valid,
        "comparison",
    )

    all_passed = all(checks.values())
    payload = {
        "kind": "gdp_cem_e19_d2_validity_only",
        "all_passed": all_passed,
        **checks,
        "failed_checks": sorted(set(failed)),
    }
    result_path = args.output / "VALIDITY-ONLY.json"
    result_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output / "sha256.txt").open("x", encoding="utf-8") as stream:
        stream.write(f"{legacy.sha256_file(result_path)}  {result_path.name}\n")
    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
