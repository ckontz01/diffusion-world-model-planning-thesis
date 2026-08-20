#!/usr/bin/env python3
"""Independent structural and arithmetic audit of a completed E6 result."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any


TASKS = ("pusht", "reacher", "cube")
ARMS = (
    "b0",
    "acid_cont",
    "forward_cont",
    "rdx_cont",
    "rdx_gate_tail5_q20",
    "rdx_gate_tail5_q40",
    "rdx_gate_all_q40",
    "rdx_shuffled_gate_tail5_q40",
    "acid_gate_tail5_q40",
    "forward_gate_tail5_q40",
)
PRIMARY = "rdx_gate_tail5_q40"
EXPECTED_EPISODES = 50


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reject_protected(path: Path) -> None:
    lowered = str(path).lower().replace("_", "-")
    if "c1" in lowered or "i1" in lowered:
        raise RuntimeError(f"protected path is forbidden: {path}")


def load_run(path: Path) -> dict[str, Any]:
    reject_protected(path)
    summary = json.loads(path.read_text(encoding="utf-8"))
    task, arm = summary.get("task"), summary.get("arm")
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "acid_alt_e6_d2_quantile_closed_loop_evaluation"
        or task not in TASKS
        or arm not in ARMS
        or summary.get("episode_count") != EXPECTED_EPISODES
        or summary.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError(f"invalid E6 run summary: {path}")
    episodes_path = Path(summary["episodes_tsv"])
    reject_protected(episodes_path)
    if not episodes_path.is_file() or sha256_file(episodes_path) != summary["episodes_tsv_sha256"]:
        raise RuntimeError(f"episode artifact hash mismatch: {path}")
    with episodes_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != EXPECTED_EPISODES:
        raise RuntimeError(f"wrong episode count: {path}")
    if [int(row["eval_index"]) for row in rows] != list(range(EXPECTED_EPISODES)):
        raise RuntimeError(f"noncontiguous episode indices: {path}")
    successes = tuple(int(row["success"]) for row in rows)
    if any(value not in (0, 1) for value in successes):
        raise RuntimeError(f"invalid success value: {path}")
    if sum(successes) != int(summary["success_count"]):
        raise RuntimeError(f"success count differs: {path}")
    return {
        "task": task,
        "arm": arm,
        "successes": successes,
        "starts": tuple((int(row["episode_id"]), int(row["start_step"])) for row in rows),
        "summary": str(path),
        "summary_sha256": sha256_file(path),
        "episodes_sha256": summary["episodes_tsv_sha256"],
        "manifest_sha256": summary["eval_manifest_sha256"],
        "dataset_sha256": summary["dataset_sha256"],
        "checkpoint_sha256": summary["world_model_checkpoint_sha256"],
        "protocol_sha256": summary["protocol_sha256"],
        "source_manifest_sha256": summary["source_manifest_sha256"],
        "authorization_sha256": summary["authorization_sha256"],
    }


def rate(values: tuple[int, ...]) -> float:
    return sum(values) / len(values)


def difference(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(a - b for a, b in zip(left, right))


def equal_task(vectors: dict[str, tuple[int, ...]]) -> float:
    return sum(rate(vectors[task]) for task in TASKS) / len(TASKS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closed-loop-root", type=Path, required=True)
    parser.add_argument("--official-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.closed_loop_root, args.official_summary, args.output.parent):
        reject_protected(path)
    paths = sorted(args.closed_loop_root.glob("*/*/*/summary.json"))
    if len(paths) != len(TASKS) * len(ARMS):
        raise RuntimeError(f"expected 30 summaries, found {len(paths)}")
    records = [load_run(path) for path in paths]
    keyed = {(record["task"], record["arm"]): record for record in records}
    expected = {(task, arm) for task in TASKS for arm in ARMS}
    if set(keyed) != expected or len(keyed) != len(records):
        raise RuntimeError("E6 grid is duplicate or incomplete")
    for task in TASKS:
        reference = keyed[(task, "b0")]
        for arm in ARMS:
            record = keyed[(task, arm)]
            for key in ("starts", "manifest_sha256", "dataset_sha256", "checkpoint_sha256"):
                if record[key] != reference[key]:
                    raise RuntimeError(f"unpaired input {key}: {task}/{arm}")
    singleton_fields = ("protocol_sha256", "source_manifest_sha256", "authorization_sha256")
    identities = {
        key: sorted({record[key] for record in records}) for key in singleton_fields
    }
    if any(len(values) != 1 for values in identities.values()):
        raise RuntimeError(f"E6 run provenance differs: {identities}")

    outcomes = {
        task: {arm: keyed[(task, arm)]["successes"] for arm in ARMS}
        for task in TASKS
    }
    levels = {
        arm: {
            "per_task": {task: rate(outcomes[task][arm]) for task in TASKS},
            "equal_task": sum(rate(outcomes[task][arm]) for task in TASKS) / len(TASKS),
        }
        for arm in ARMS
    }
    pairs = {
        "primary_minus_acid_cont": (PRIMARY, "acid_cont"),
        "primary_minus_shuffled": (PRIMARY, "rdx_shuffled_gate_tail5_q40"),
        "primary_minus_b0": (PRIMARY, "b0"),
        "primary_minus_forward_gate": (PRIMARY, "forward_gate_tail5_q40"),
        "primary_minus_acid_gate": (PRIMARY, "acid_gate_tail5_q40"),
        "primary_minus_rdx_cont": (PRIMARY, "rdx_cont"),
        "q20_minus_primary": ("rdx_gate_tail5_q20", PRIMARY),
        "all_q40_minus_primary": ("rdx_gate_all_q40", PRIMARY),
    }
    contrasts: dict[str, dict[str, Any]] = {}
    for label, (left, right) in pairs.items():
        vectors = {task: difference(outcomes[task][left], outcomes[task][right]) for task in TASKS}
        contrasts[label] = {
            "per_task": {task: rate(vectors[task]) for task in TASKS},
            "equal_task": equal_task(vectors),
        }
    acid = contrasts["primary_minus_acid_cont"]
    b0 = contrasts["primary_minus_b0"]
    gates = {
        "1_primary_beats_acid_equal_task": acid["equal_task"] > 0,
        "2_primary_beats_shuffled_equal_task": contrasts["primary_minus_shuffled"]["equal_task"] > 0,
        "3_primary_not_below_b0_equal_task": b0["equal_task"] >= 0,
        "4_primary_task_robustness": (
            all(acid["per_task"][task] >= -0.10 for task in TASKS)
            and all(b0["per_task"][task] >= -0.10 for task in TASKS)
            and sum(acid["per_task"][task] > 0 for task in TASKS) >= 2
        ),
        "5_primary_noninferior_forward_gate": contrasts["primary_minus_forward_gate"]["equal_task"] >= -0.02,
    }
    decision = "authorize_three_seed_d2_replication" if all(gates.values()) else "stop_e6_before_d3"
    official = json.loads(args.official_summary.read_text(encoding="utf-8"))
    if official.get("gates") != gates or official.get("decision") != decision:
        raise RuntimeError("independent E6 decision differs from official analysis")
    max_difference = 0.0
    for arm in ARMS:
        max_difference = max(
            max_difference,
            abs(levels[arm]["equal_task"] - official["levels"][arm]["equal_task"]["estimate"]),
            *(abs(levels[arm]["per_task"][task] - official["levels"][arm]["per_task"][task]["estimate"]) for task in TASKS),
        )
    for label in pairs:
        max_difference = max(
            max_difference,
            abs(contrasts[label]["equal_task"] - official["contrasts"][label]["equal_task"]["estimate"]),
            *(abs(contrasts[label]["per_task"][task] - official["contrasts"][label]["per_task"][task]["estimate"]) for task in TASKS),
        )
    audit = {
        "status": "ok",
        "kind": "independent_acid_alt_e6_result_audit",
        "run_count": len(records),
        "episode_row_count": len(records) * EXPECTED_EPISODES,
        "levels": levels,
        "contrasts": contrasts,
        "gates": gates,
        "decision": decision,
        "maximum_numeric_difference_from_official_estimates": max_difference,
        "official_summary": str(args.official_summary),
        "official_summary_sha256": sha256_file(args.official_summary),
        "input_identities": identities,
        "protected_c1_i1_read": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.partial-{os.getpid()}")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
