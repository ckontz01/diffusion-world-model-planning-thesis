#!/usr/bin/env python3
"""Outcome-free synthetic integration test for the frozen E3 analyzer."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


TASKS = ("pusht", "reacher", "cube")
ARMS = ("b0", "acid", "forward", "rdx", "ae", "ae_shuffled")
SEEDS = (6101, 6102, 6103)
PROTOCOL_SHA256 = (
    "c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0"
)
V3_SOURCE_MANIFEST_SHA256 = (
    "2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea"
)
V3_UPSTREAM_SOURCE_MANIFEST_SHA256 = (
    "875a9cbc19dba78db1706169b7f2d8bc97a70913d82b55f793735dfe8c2df388"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_acid_alt_e3_analyzer.py SNAPSHOT AUTH")
    snapshot = Path(sys.argv[1]).resolve()
    authorization = Path(sys.argv[2]).resolve()
    protocol = snapshot / (
        "ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-"
        "PROTOCOL-2026-08-16.md"
    )
    source_manifest = snapshot / "SOURCE-MANIFEST.sha256"
    analyzer = snapshot / "analyze_acid_alt_e3_d2_closed_loop.py"
    if sha256_file(protocol) != PROTOCOL_SHA256:
        raise RuntimeError("synthetic test received the wrong E3 protocol")
    authorization_payload = json.loads(authorization.read_text(encoding="utf-8"))
    if (
        authorization_payload.get("status")
        != "authorized_for_exploratory_development_only"
        or authorization_payload.get("v3_stage_b_authorized") is not False
        or authorization_payload.get("confirmation_claim_allowed") is not False
    ):
        raise RuntimeError("synthetic test requires a valid exploratory authorization")

    root = Path(tempfile.mkdtemp(prefix="acid-e3-analyzer-test-"))
    source_sha = sha256_file(source_manifest)
    authorization_sha = sha256_file(authorization)
    success_counts = {
        "b0": 20,
        "acid": 25,
        "forward": 24,
        "rdx": 27,
        "ae": 35,
        "ae_shuffled": 22,
    }
    run_args: list[str] = []
    first_summary: Path | None = None
    for task_index, task in enumerate(TASKS):
        starts = [(1000 * task_index + index, 3) for index in range(50)]
        for arm in ARMS:
            for seed in SEEDS:
                planner = seed + 2200
                run_dir = root / "runs" / task / arm / str(seed)
                run_dir.mkdir(parents=True)
                episodes = run_dir / "episodes.tsv"
                with episodes.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(
                        stream,
                        fieldnames=(
                            "eval_index",
                            "episode_id",
                            "start_step",
                            "scorer_seed",
                            "planner_seed",
                            "arm",
                            "success",
                        ),
                        delimiter="\t",
                    )
                    writer.writeheader()
                    for index, (episode, start) in enumerate(starts):
                        writer.writerow(
                            {
                                "eval_index": index,
                                "episode_id": episode,
                                "start_step": start,
                                "scorer_seed": seed,
                                "planner_seed": planner,
                                "arm": arm,
                                "success": int(index < success_counts[arm]),
                            }
                        )
                summary = run_dir / "summary.json"
                dump(
                    summary,
                    {
                        "status": "ok",
                        "kind": (
                            "acid_alt_e3_d2_exploratory_closed_loop_evaluation"
                        ),
                        "analysis_role": (
                            "post_v3_exploratory_d2_closed_loop_development"
                        ),
                        "task": task,
                        "arm": arm,
                        "scorer_seed": seed,
                        "planner_seed": planner,
                        "episode_count": 50,
                        "success_count": success_counts[arm],
                        "protocol_sha256": PROTOCOL_SHA256,
                        "source_manifest_sha256": source_sha,
                        "upstream_source_manifest_sha256": (
                            V3_SOURCE_MANIFEST_SHA256
                        ),
                        "v3_upstream_source_manifest_sha256": (
                            V3_UPSTREAM_SOURCE_MANIFEST_SHA256
                        ),
                        "exploratory_authorization_sha256": authorization_sha,
                        "v3_stage_b_authorized": False,
                        "confirmation_claim_allowed": False,
                        "alternative_to_acid_claim_allowed": False,
                        "protected_c1_i1_read": False,
                        "episodes_tsv": str(episodes),
                        "episodes_tsv_sha256": sha256_file(episodes),
                        "eval_manifest_sha256": f"eval-{task_index}",
                        "dataset_sha256": f"data-{task_index}",
                        "world_model_checkpoint_sha256": f"world-{task_index}",
                        "elapsed_seconds": 12.5,
                        "cem_cost_calls": 1500,
                        "runtime": {
                            "gpu": "synthetic",
                            "peak_cuda_memory_allocated_bytes": 1234,
                        },
                    },
                )
                if first_summary is None:
                    first_summary = summary
                run_args.extend(
                    ["--run", task, arm, str(seed), str(planner), str(summary)]
                )

    output = root / "analysis-pass"
    command = [
        sys.executable,
        str(analyzer),
        "--protocol",
        str(protocol),
        "--source-manifest",
        str(source_manifest),
        "--exploratory-authorization",
        str(authorization),
        *run_args,
    ]
    subprocess.run(
        [*command, "--output-dir", str(output)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    result = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if (
        result.get("all_e3_promotion_gates_pass") is not True
        or result.get("decision") != "promote_ae_to_new_confirmation"
        or result.get("claim_decision")
        != "no_publication_claim_from_exploratory_e3"
        or result.get("v3_stage_b_authorized") is not False
    ):
        raise RuntimeError("synthetic E3 promotion result is incorrect")

    assert first_summary is not None
    tampered = json.loads(first_summary.read_text(encoding="utf-8"))
    tampered["confirmation_claim_allowed"] = True
    dump(first_summary, tampered)
    rejected = subprocess.run(
        [*command, "--output-dir", str(root / "analysis-must-fail")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if rejected.returncode == 0:
        raise RuntimeError("E3 analyzer accepted a confirmatory-claim tamper")

    print(
        json.dumps(
            {
                "status": "ok",
                "synthetic_grid_runs": len(TASKS) * len(ARMS) * len(SEEDS),
                "all_e3_promotion_gates_pass": True,
                "claim_tamper_rejected": True,
                "temporary": str(root),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
