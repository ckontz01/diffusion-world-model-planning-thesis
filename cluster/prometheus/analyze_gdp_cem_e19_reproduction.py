#!/usr/bin/env python3
"""Open the sealed 180-cell SAGE reproduction and run its summarizer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

import gdp_cem_e19_specs as spec


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum_file(root: Path) -> None:
    for line in (root / "sha256.txt").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", maxsplit=1)
        path = root / name
        if sha256_file(path) != expected:
            raise RuntimeError(f"checksum mismatch: {path}")


def result_dir(root: Path, row: spec.Cell) -> Path:
    return (
        root
        / row.benchmark
        / row.method
        / f"seed{row.seed}"
        / f"h{row.horizon}"
    )


def verify_cell_manifest(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != [
            "array_id",
            "benchmark",
            "method",
            "seed",
            "horizon",
        ]:
            raise RuntimeError("E19 cell-manifest header drift")
        observed = [
            spec.Cell(
                array_id=int(row["array_id"]),
                benchmark=row["benchmark"],
                method=row["method"],
                seed=int(row["seed"]),
                horizon=int(row["horizon"]),
            )
            for row in reader
        ]
    if tuple(observed) != spec.cells():
        raise RuntimeError("E19 cell manifest does not equal frozen registry")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sage-root", type=Path, required=True)
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--release-audit-root", type=Path, required=True)
    parser.add_argument("--data-audit-root", type=Path, required=True)
    parser.add_argument("--cell-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    verify_checksum_file(args.release_audit_root)
    verify_checksum_file(args.data_audit_root)
    release = json.loads(
        (args.release_audit_root / "RELEASE-AUDIT.json").read_text(encoding="utf-8")
    )
    data = json.loads(
        (args.data_audit_root / "DATA-OVERLAP-AUDIT.json").read_text(encoding="utf-8")
    )
    if not release.get("release_gate_passed"):
        raise RuntimeError("E19 release gate did not pass")
    if not data.get("data_identity_gate_passed"):
        raise RuntimeError("E19 data-identity gate did not pass")
    verify_cell_manifest(args.cell_manifest)

    cells = spec.cells()
    cell_rows = []
    grouped: dict[tuple[str, str, int], list[float]] = {}
    total_episodes = 0
    for row in cells:
        directory = result_dir(args.evaluation_root, row)
        verify_checksum_file(directory)
        status = json.loads((directory / "cell-status.json").read_text(encoding="utf-8"))
        if status.get("status") != "passed" or not all(status.get("checks", {}).values()):
            raise RuntimeError(f"failed E19 cell integrity: {directory}")
        for key, expected in (
            ("benchmark", row.benchmark),
            ("method", row.method),
            ("seed", row.seed),
            ("horizon", row.horizon),
        ):
            if status.get(key) != expected:
                raise RuntimeError(f"E19 status identity mismatch: {directory}/{key}")
        result_path = directory / "results.json"
        if status.get("result_sha256") != sha256_file(result_path):
            raise RuntimeError(f"result identity mismatch: {result_path}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        success = float(result["metrics"]["success_rate"])
        episode_count = len(result["metrics"]["episode_successes"])
        total_episodes += episode_count
        grouped.setdefault((row.benchmark, row.method, row.horizon), []).append(success)
        cell_rows.append(
            {
                "array_id": row.array_id,
                "benchmark": row.benchmark,
                "method": row.method,
                "seed": row.seed,
                "horizon": row.horizon,
                "success_rate": success,
                "episode_count": episode_count,
                "result_sha256": sha256_file(result_path),
            }
        )
    if len(cell_rows) != spec.EXPECTED_CELLS or total_episodes != spec.EXPECTED_TOTAL_EPISODES:
        raise RuntimeError("E19 180-cell/9000-episode information barrier failed")

    summarizer_command = [
        sys.executable,
        str(args.sage_root / "scripts" / "summarize_results.py"),
        "--root",
        str(args.evaluation_root),
        "--paper-config",
        str(args.sage_root / "configs" / "paper.json"),
        "--out",
        str(output / "official-component-table.json"),
        "--expected-tolerance",
        str(spec.EXPECTED_TOLERANCE_POINTS),
    ]
    environment = os.environ.copy()
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
    summarizer = subprocess.run(
        summarizer_command,
        cwd=args.sage_root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (output / "official-summarizer.stdout.txt").write_text(
        summarizer.stdout, encoding="utf-8"
    )
    (output / "official-summarizer.stderr.txt").write_text(
        summarizer.stderr, encoding="utf-8"
    )

    paper = json.loads(
        (args.sage_root / "configs" / "paper.json").read_text(encoding="utf-8")
    )
    summary_rows = []
    for benchmark in spec.BENCHMARKS:
        for method in spec.METHODS:
            for horizon_index, horizon in enumerate(spec.HORIZONS):
                values = grouped[(benchmark, method, horizon)]
                if len(values) != len(spec.SEEDS):
                    raise RuntimeError("missing E19 seed value")
                mean = float(np.mean(values))
                expected = float(
                    paper["expected_success_percent"][benchmark][method][horizon_index]
                )
                summary_rows.append(
                    {
                        "benchmark": benchmark,
                        "method": method,
                        "horizon": horizon,
                        "mean": mean,
                        "recorded_mean": expected,
                        "absolute_difference_points": abs(mean - expected),
                        "within_two_points": abs(mean - expected)
                        <= spec.EXPECTED_TOLERANCE_POINTS,
                    }
                )
    with (output / "cell-results.tsv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cell_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(cell_rows)
    with (output / "summary.tsv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    summarizer_passed = summarizer.returncode == 0 and all(
        row["within_two_points"] for row in summary_rows
    )
    zero_overlap = bool(data.get("critical_zero_overlap_all_tasks"))
    payload = {
        "kind": "gdp_cem_e19_official_sage_native_reproduction_audit",
        "status": "passed" if summarizer_passed else "failed",
        "cell_count": len(cell_rows),
        "episode_count": total_episodes,
        "aggregate_row_count": len(summary_rows),
        "official_summarizer_returncode": summarizer.returncode,
        "official_two_point_tolerance_passed": summarizer_passed,
        "maximum_absolute_difference_points": max(
            row["absolute_difference_points"] for row in summary_rows
        ),
        "release_audit_sha256": sha256_file(
            args.release_audit_root / "RELEASE-AUDIT.json"
        ),
        "data_overlap_audit_sha256": sha256_file(
            args.data_audit_root / "DATA-OVERLAP-AUDIT.json"
        ),
        "cell_manifest_sha256": sha256_file(args.cell_manifest),
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "critical_zero_overlap_all_tasks": zero_overlap,
        "matched_protocol_drafting_authorized": summarizer_passed and zero_overlap,
        "matched_performance_evaluation_launched": False,
        "next_action": (
            "draft_separate_matched_h75_h150_protocol"
            if summarizer_passed and zero_overlap
            else "use_common_untouched_episode_candidates"
            if summarizer_passed
            else "stop_native_reproduction_failed"
        ),
        "d5_read": False,
        "protected_comparison_run": False,
    }
    (output / "NATIVE-REPRODUCTION-AUDIT.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in output.iterdir() if path.name != "sha256.txt")
    with (output / "sha256.txt").open("x", encoding="utf-8") as stream:
        for path in files:
            stream.write(f"{sha256_file(path)}  {path.name}\n")
    if not summarizer_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
