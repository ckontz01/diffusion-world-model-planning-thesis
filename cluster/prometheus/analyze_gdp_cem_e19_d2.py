#!/usr/bin/env python3
"""Run the sealed E19-D2 classification after its readable validity gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import analyze_gdp_cem_e19_discrepancy as legacy
import gdp_cem_e19_d2_specs as d2
from gdp_cem_e19_d2_validity import trace_gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d2-snapshot", type=Path, required=True)
    parser.add_argument("--raw-snapshot", type=Path, required=True)
    parser.add_argument("--raw-run-root", type=Path, required=True)
    parser.add_argument("--e19-run-root", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--validity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    legacy.verify_sha256_file(args.validity.parent)
    validity = legacy.load_json(args.validity)
    if validity.get("kind") != "gdp_cem_e19_d2_validity_only":
        raise RuntimeError("unexpected E19-D2 validity kind")
    if validity.get("all_passed") is not True or validity.get("failed_checks") != []:
        raise RuntimeError("E19-D2 validity gate did not pass")
    if args.raw_snapshot.resolve() != Path(d2.PARENT_SNAPSHOT).resolve():
        raise RuntimeError("raw snapshot identity drift")
    if args.raw_run_root.resolve() != Path(d2.PARENT_RUN_ROOT).resolve():
        raise RuntimeError("raw run-root identity drift")
    if args.e19_run_root.resolve() != Path(d2.E19_RUN_ROOT).resolve():
        raise RuntimeError("E19 run-root identity drift")

    d2_source_sha256 = legacy.sha256_file(
        args.d2_snapshot / "SOURCE-MANIFEST.sha256"
    )
    d2_protocol_sha256 = legacy.sha256_file(
        args.d2_snapshot / d2.PROTOCOL_FILENAME
    )
    validity_sha256 = legacy.sha256_file(args.validity)

    legacy.trace_gate = trace_gate
    saved_argv = sys.argv
    try:
        sys.argv = [
            str(Path(legacy.__file__)),
            "--snapshot",
            str(args.raw_snapshot),
            "--run-root",
            str(args.raw_run_root),
            "--e19-run-root",
            str(args.e19_run_root),
            "--comparison",
            str(args.comparison),
            "--output",
            str(args.output),
        ]
        legacy.main()
    finally:
        sys.argv = saved_argv

    provenance = {
        "kind": "gdp_cem_e19_d2_method_aware_reanalysis_provenance",
        "d2_source_manifest_sha256": d2_source_sha256,
        "d2_protocol_sha256": d2_protocol_sha256,
        "parent_source_manifest_sha256": d2.PARENT_SOURCE_MANIFEST_SHA256,
        "parent_protocol_sha256": d2.PARENT_PROTOCOL_SHA256,
        "parent_analyzer_sha256": d2.LEGACY_ANALYZER_SHA256,
        "validity_only_sha256": validity_sha256,
        "only_correction": "method_aware_history_latent_expectation",
        "raw_artifacts_reused_without_episode_rerun": True,
        "old_analyzer_output_read": False,
        "e19_decision_preserved": "stop_native_reproduction_failed",
        "parent_diagnostic_preserved_failed": True,
        "protected_metric_artifact_read": False,
        "e18_vs_sage_comparison_run": False,
        "d5_read": False,
        "author_contact_performed": False,
    }
    provenance_path = args.output / "D2-PROVENANCE.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = args.output / "sha256.txt"
    manifest.unlink()
    files = sorted(
        path
        for path in args.output.rglob("*")
        if path.is_file() and path != manifest
    )
    with manifest.open("x", encoding="utf-8") as stream:
        for path in files:
            stream.write(
                f"{legacy.sha256_file(path)}  {path.relative_to(args.output)}\n"
            )


if __name__ == "__main__":
    main()
