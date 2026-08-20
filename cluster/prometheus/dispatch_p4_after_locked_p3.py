#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path("/lustreFS/data/superworld/ckontzias/thesis")
PROMOTION_JOB_ID = 295115
BASELINE_ARRAY_JOB_ID = 295131
LEARNED_METHODS = ("M1", "M2", "M3")
PROMOTION_DIR = (
    ROOT
    / "data/stablewm/derived/scorer-audits/pusht-v1"
    / f"p3-locked-audit-job-{PROMOTION_JOB_ID}"
)
LEARNED_LAUNCHER = ROOT / "scripts/run_p4_augmented_closed_loop_arm_array.slurm"
AGGREGATE_LAUNCHER = ROOT / "scripts/run_aggregate_p4_closed_loop_confirmation.slurm"
BASELINE_LAUNCHER = ROOT / "scripts/run_p4_b0_b1_d75_array.slurm"
EXPECTED_LAUNCHER_HASHES = {
    LEARNED_LAUNCHER: "f061839827adddeaa048a2c24d3654a83399dcb2d5ba565de509d10e594775ce",
    AGGREGATE_LAUNCHER: "cd99b35053a6dad973bc4d837cda31cc77f924b6f5e7f5c7de462bc0c8b0ba80",
    BASELINE_LAUNCHER: "45ccb18293fd5512c11dc6265a88ba454890ec9c89bf26fda90377b56ec3c15a",
}


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def verify_inventory(directory: Path) -> Dict[str, str]:
    inventory_path = directory / "checksums.sha256"
    if not inventory_path.is_file():
        raise RuntimeError(f"missing checksum inventory: {directory}")
    root = directory.resolve()
    found = {}  # type: Dict[str, str]
    for raw in inventory_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, raw_path = raw.split(maxsplit=1)
        path = Path(raw_path.lstrip("* "))
        if not path.is_absolute():
            path = directory / path
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            raise RuntimeError(f"checksum path escapes promotion directory: {path}")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid promotion file: {path}")
        found[str(relative)] = digest
    return found


def atomic_json(path: Path, value: Dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite dispatch receipt: {path}")
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def checked_output(arguments: List[str]) -> str:
    process = subprocess.run(
        arguments,
        check=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process.stdout.strip()


def submit(arguments: List[str]) -> Tuple[int, List[str]]:
    command = ["/usr/bin/sbatch", "--parsable", *arguments]
    output = checked_output(command)
    match = re.fullmatch(r"([0-9]+)(?:;[^\s]+)?", output)
    if match is None:
        raise RuntimeError(f"unexpected sbatch response: {output!r}")
    return int(match.group(1)), command


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        raise SystemExit("refusing to repeat a completed P4 dispatch")
    started = time.time()

    for launcher, expected_hash in EXPECTED_LAUNCHER_HASHES.items():
        if not launcher.is_file() or sha256_file(launcher) != expected_hash:
            raise RuntimeError(f"P4 launcher is missing or changed: {launcher}")

    inventory = verify_inventory(PROMOTION_DIR)
    if set(inventory) != {"audit.h5", "manifest.json", "provenance.txt"}:
        raise RuntimeError("unexpected P3 promotion artifact inventory")
    promotion = json.loads((PROMOTION_DIR / "manifest.json").read_text(encoding="utf-8"))
    if (
        promotion.get("status") != "ok"
        or promotion.get("classification") != "p3_locked_scorer_audit_and_promotion"
        or promotion.get("partition") != "P3-locked"
        or promotion.get("output_h5_sha256") != inventory["audit.h5"]
    ):
        raise RuntimeError("invalid locked P3 promotion artifact")
    promoted = promotion.get("promoted_arms")
    records = promotion.get("promotion")
    if (
        not isinstance(promoted, list)
        or len(set(promoted)) != len(promoted)
        or any(method not in LEARNED_METHODS for method in promoted)
        or not isinstance(records, dict)
    ):
        raise RuntimeError("invalid promoted-arm list")
    promoted = [method for method in LEARNED_METHODS if method in promoted]
    for method in LEARNED_METHODS:
        record = records.get(method)
        if not isinstance(record, dict) or record.get("promoted") is not (
            method in promoted
        ):
            raise RuntimeError(f"P3 promotion list/record mismatch for {method}")

    baseline_job = checked_output(
        ["/usr/bin/scontrol", "show", "job", "-o", str(BASELINE_ARRAY_JOB_ID)]
    )
    if not baseline_job or f"Command={BASELINE_LAUNCHER}" not in baseline_job:
        raise RuntimeError("the frozen P4 baseline array job is missing or uses another launcher")

    predecessor = BASELINE_ARRAY_JOB_ID
    learned_jobs = {}  # type: Dict[str, int]
    submissions = []  # type: List[Dict[str, Any]]
    for method in promoted:
        learned_job_id, command = submit(
            [
                f"--dependency=afterok:{predecessor}",
                f"--export=ALL,METHOD={method},PROMOTION_JOB_ID={PROMOTION_JOB_ID}",
                str(LEARNED_LAUNCHER),
            ]
        )
        learned_jobs[method] = learned_job_id
        submissions.append(
            {
                "role": f"P4 promoted {method} array",
                "job_id": learned_job_id,
                "afterok": predecessor,
                "command": command,
            }
        )
        predecessor = learned_job_id

    exports = [
        "ALL",
        f"PROMOTION_JOB_ID={PROMOTION_JOB_ID}",
        f"BASELINE_ARRAY_JOB_ID={BASELINE_ARRAY_JOB_ID}",
        *(f"{method}_ARRAY_JOB_ID={job_id}" for method, job_id in learned_jobs.items()),
    ]
    aggregate_job_id, aggregate_command = submit(
        [
            f"--dependency=afterok:{predecessor}",
            f"--export={','.join(exports)}",
            str(AGGREGATE_LAUNCHER),
        ]
    )
    submissions.append(
        {
            "role": "P4 locked aggregate",
            "job_id": aggregate_job_id,
            "afterok": predecessor,
            "command": aggregate_command,
        }
    )

    receipt = {
        "status": "ok",
        "classification": "p4_dispatch_from_locked_p3_promotion",
        "reporting_rule": "mechanical gate dispatch only; no P4 outcome was read",
        "promotion_job_id": PROMOTION_JOB_ID,
        "promotion_h5_sha256": inventory["audit.h5"],
        "promotion_manifest_sha256": inventory["manifest.json"],
        "promoted_arms": promoted,
        "baseline_array_job_id": BASELINE_ARRAY_JOB_ID,
        "learned_array_jobs": learned_jobs,
        "aggregate_job_id": aggregate_job_id,
        "submissions": submissions,
        "launcher_sha256": {
            str(path): digest for path, digest in EXPECTED_LAUNCHER_HASHES.items()
        },
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_json, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
