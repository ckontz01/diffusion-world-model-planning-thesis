#!/usr/bin/env python3
"""Audit the pinned official SAGE tree, tests, and checkpoint snapshot."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import gdp_cem_e19_specs as spec


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_manifest_hash(payload: dict) -> str:
    if "records" in payload:
        records = [
            {
                "episode_id": int(row["episode_id"]),
                "start_frame": int(row["start_frame"]),
                "goal_frame": int(row["goal_frame"]),
                "goal_offset_steps": int(row["goal_offset_steps"]),
                "record_id": str(row["record_id"]),
                "split": str(row.get("split", "test")),
            }
            for row in payload["records"]
        ]
    else:
        horizon = int(payload["goal_offset_steps"])
        records = [
            {
                "episode_id": int(episode),
                "start_frame": int(start),
                "goal_frame": int(start) + horizon,
                "goal_offset_steps": horizon,
                "record_id": (
                    f"test_ep{int(episode)}_s{int(start):04d}_"
                    f"g{int(start) + horizon:04d}"
                ),
                "split": str(payload.get("split_name", "test")),
            }
            for episode, start in zip(
                payload["episodes_idx"], payload["start_steps"], strict=True
            )
        ]
    encoded = json.dumps(
        records, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(encoded)


def run_checked_capture(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def audit_git(sage_root: Path) -> dict:
    head = run_checked_capture(
        ["git", "rev-parse", "HEAD"], cwd=sage_root
    )
    tree = run_checked_capture(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=sage_root
    )
    status = run_checked_capture(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=sage_root
    )
    fsck = run_checked_capture(
        ["git", "fsck", "--no-dangling"], cwd=sage_root
    )
    result = {
        "head": head.stdout.strip(),
        "tree": tree.stdout.strip(),
        "status": status.stdout,
        "fsck_stdout": fsck.stdout,
        "fsck_stderr": fsck.stderr,
        "returncodes": {
            "head": head.returncode,
            "tree": tree.returncode,
            "status": status.returncode,
            "fsck": fsck.returncode,
        },
    }
    result["passed"] = (
        all(value == 0 for value in result["returncodes"].values())
        and result["head"] == spec.SAGE_GIT_COMMIT
        and result["tree"] == spec.SAGE_GIT_TREE
        and not result["status"]
    )
    return result


def audit_manifest_line_endings(sage_root: Path) -> dict:
    sums = sage_root / "data" / "manifests" / "SHA256SUMS"
    rows = []
    for line in sums.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        path = sage_root / "data" / "manifests" / relative
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        raw_hash = sha256_bytes(raw)
        crlf = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        crlf_hash = sha256_bytes(crlf)
        semantic = semantic_manifest_hash(payload)
        row = {
            "path": relative,
            "expected_byte_sha256": expected,
            "checkout_byte_sha256": raw_hash,
            "lf_to_crlf_sha256": crlf_hash,
            "semantic_expected": payload.get("semantic_manifest_sha256"),
            "semantic_observed": semantic,
            "checkout_is_lf": b"\r\n" not in raw and b"\n" in raw,
            "checkout_byte_matches": raw_hash == expected,
            "crlf_compatibility_matches": crlf_hash == expected,
            "semantic_matches": semantic == payload.get("semantic_manifest_sha256"),
        }
        rows.append(row)
    return {
        "manifest_count": len(rows),
        "checkout_byte_match_count": sum(row["checkout_byte_matches"] for row in rows),
        "crlf_compatibility_match_count": sum(
            row["crlf_compatibility_matches"] for row in rows
        ),
        "semantic_match_count": sum(row["semantic_matches"] for row in rows),
        "all_checkout_lf": all(row["checkout_is_lf"] for row in rows),
        "rows": rows,
        "passed": (
            len(rows) == spec.EXPECTED_MANIFESTS
            and not any(row["checkout_byte_matches"] for row in rows)
            and all(row["crlf_compatibility_matches"] for row in rows)
            and all(row["semantic_matches"] for row in rows)
            and all(row["checkout_is_lf"] for row in rows)
        ),
    }


def audit_registry_and_files(sage_root: Path, checkpoint_root: Path) -> dict:
    registry = json.loads(
        (sage_root / "configs" / "checkpoints.json").read_text(encoding="utf-8")
    )
    rows = []
    for key, expected in spec.CHECKPOINTS.items():
        release_entry = registry.get(key, {})
        path = checkpoint_root / expected["filename"]
        row = {
            "key": key,
            "path": str(path),
            "exists": path.is_file(),
            "expected_filename": expected["filename"],
            "registry_filename": release_entry.get("filename"),
            "expected_bytes": expected["bytes"],
            "registry_bytes": release_entry.get("size_bytes"),
            "expected_sha256": expected["sha256"],
            "registry_sha256": release_entry.get("sha256"),
        }
        if path.is_file():
            row["observed_bytes"] = path.stat().st_size
            row["observed_sha256"] = sha256_file(path)
        else:
            row["observed_bytes"] = None
            row["observed_sha256"] = None
        row["passed"] = (
            row["exists"]
            and row["registry_filename"] == row["expected_filename"]
            and row["registry_bytes"] == row["expected_bytes"]
            and row["registry_sha256"] == row["expected_sha256"]
            and row["observed_bytes"] == row["expected_bytes"]
            and row["observed_sha256"] == row["expected_sha256"]
            and release_entry.get("hf_repo") == spec.SAGE_HF_REPO
        )
        rows.append(row)
    return {
        "hf_repo": spec.SAGE_HF_REPO,
        "hf_revision": spec.SAGE_HF_REVISION,
        "registry_keys": sorted(registry),
        "rows": rows,
        "passed": set(registry) == set(spec.CHECKPOINTS)
        and all(row["passed"] for row in rows),
    }


def classify_upstream_audit(process: subprocess.CompletedProcess[str]) -> dict:
    combined = "\n".join(part for part in (process.stdout, process.stderr) if part)
    bullet_lines = [
        line.strip()[2:]
        for line in combined.splitlines()
        if line.strip().startswith("- ")
    ]
    expected_pattern = re.compile(r"^manifest byte hash mismatch: (?:pusht|cube)/seed(?:32|42|52)/h(?:25|50|75|100|125|150)\.json$")
    byte_failures = [line for line in bullet_lines if expected_pattern.fullmatch(line)]
    unexpected = [line for line in bullet_lines if not expected_pattern.fullmatch(line)]
    return {
        "returncode": process.returncode,
        "error_line_count": len(bullet_lines),
        "expected_byte_mismatch_count": len(byte_failures),
        "unexpected_error_lines": unexpected,
        "pristine_audit_passed": process.returncode == 0,
        "classified_packaging_defect_only": (
            process.returncode != 0
            and len(byte_failures) == spec.EXPECTED_RELEASE_BYTE_MISMATCHES
            and not unexpected
        ),
    }


def classify_pytest(process: subprocess.CompletedProcess[str]) -> dict:
    combined = "\n".join(part for part in (process.stdout, process.stderr) if part)
    match = re.search(r"(\d+) passed(?: in [0-9.]+s)?", combined)
    passed_count = int(match.group(1)) if match else None
    forbidden = re.search(r"\b(?:failed|skipped|xfailed|xpassed|error)s?\b", combined, re.I)
    return {
        "returncode": process.returncode,
        "passed_count": passed_count,
        "forbidden_outcome_token": forbidden.group(0) if forbidden else None,
        "passed": (
            process.returncode == 0
            and passed_count == spec.EXPECTED_UPSTREAM_TESTS
            and forbidden is None
        ),
    }


def audit_environment_compatibility(sage_root: Path) -> dict:
    environment_text = (sage_root / "environment.yml").read_text(encoding="utf-8")
    import_probe = run_checked_capture(
        [
            sys.executable,
            "-c",
            (
                "import sys; import sage.eval.pusht, sage.eval.cube; "
                "assert 'transformers' not in sys.modules"
            ),
        ],
        cwd=sage_root,
    )
    installed_transformers = importlib.metadata.version("transformers")
    installed_huggingface_hub = importlib.metadata.version("huggingface-hub")
    installed_hdf5plugin = importlib.metadata.version("hdf5plugin")
    result = {
        "upstream_transformers_pin": "5.1.2",
        "upstream_pin_present": "transformers==5.1.2" in environment_text,
        "upstream_hdf5plugin_declared": "hdf5plugin" in environment_text,
        "installed_transformers": installed_transformers,
        "installed_huggingface_hub": installed_huggingface_hub,
        "installed_hdf5plugin": installed_hdf5plugin,
        "transformers_import_probe_returncode": import_probe.returncode,
        "transformers_import_probe_stdout": import_probe.stdout,
        "transformers_import_probe_stderr": import_probe.stderr,
        "classification": (
            "unpublished upstream pin corrected to nearest published version "
            "in the same minor series; lazy PreJEPA-only dependency"
        ),
    }
    result["passed"] = (
        result["upstream_pin_present"]
        and not result["upstream_hdf5plugin_declared"]
        and installed_transformers == "5.1.0"
        and installed_huggingface_hub == "1.3.0"
        and installed_hdf5plugin == "7.0.0"
        and import_probe.returncode == 0
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sage-root", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    sage_root = args.sage_root.resolve()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    upstream_audit = run_checked_capture(
        [sys.executable, "scripts/audit_release.py"], cwd=sage_root
    )
    upstream_pytest = run_checked_capture(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
        ],
        cwd=sage_root,
    )
    (output / "upstream-release-audit.stdout.txt").write_text(
        upstream_audit.stdout, encoding="utf-8"
    )
    (output / "upstream-release-audit.stderr.txt").write_text(
        upstream_audit.stderr, encoding="utf-8"
    )
    (output / "upstream-pytest.stdout.txt").write_text(
        upstream_pytest.stdout, encoding="utf-8"
    )
    (output / "upstream-pytest.stderr.txt").write_text(
        upstream_pytest.stderr, encoding="utf-8"
    )

    git = audit_git(sage_root)
    line_endings = audit_manifest_line_endings(sage_root)
    audit_classification = classify_upstream_audit(upstream_audit)
    pytest_classification = classify_pytest(upstream_pytest)
    checkpoints = audit_registry_and_files(sage_root, args.checkpoint_root)
    environment_compatibility = audit_environment_compatibility(sage_root)
    protocol_hash = sha256_file(args.protocol)
    source_manifest_hash = sha256_file(args.source_manifest)
    payload = {
        "kind": "gdp_cem_e19_official_sage_release_audit",
        "status": "passed",
        "upstream": {
            "git_url": spec.SAGE_GIT_URL,
            "git_commit": spec.SAGE_GIT_COMMIT,
            "git_tree": spec.SAGE_GIT_TREE,
            "git_audit": git,
        },
        "release_audit": audit_classification,
        "manifest_line_endings": line_endings,
        "upstream_tests": pytest_classification,
        "checkpoints": checkpoints,
        "environment_compatibility": environment_compatibility,
        "protocol_sha256": protocol_hash,
        "source_manifest_sha256": source_manifest_hash,
        "runtime": {
            "python": sys.version,
            "python_executable": sys.executable,
        },
        "scientific_sage_modification": False,
        "performance_metric_read": False,
        "d5_read": False,
        "protected_metric_artifact_read": False,
    }
    payload["release_gate_passed"] = (
        git["passed"]
        and audit_classification["classified_packaging_defect_only"]
        and line_endings["passed"]
        and pytest_classification["passed"]
        and checkpoints["passed"]
        and environment_compatibility["passed"]
    )
    if not payload["release_gate_passed"]:
        payload["status"] = "failed"
    audit_path = output / "RELEASE-AUDIT.json"
    audit_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in output.iterdir() if path.name != "sha256.txt")
    with (output / "sha256.txt").open("x", encoding="utf-8") as stream:
        for path in files:
            stream.write(f"{sha256_file(path)}  {path.name}\n")
    if not payload["release_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
