#!/usr/bin/env python3
"""Analyze E6D against immutable E6 true-RDX and ACID anchors."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_d2_models as d2
from acid_alt_e6d_allgate import ARMS as NEW_ARMS


TASKS = ("pusht", "reacher", "cube")
ANCHOR_ARMS = ("rdx_gate_all_q40", "acid_cont")
ALL_ARMS = (*ANCHOR_ARMS, *NEW_ARMS)
EVAL_COUNT = 50
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081701
PROTOCOL_SHA256 = "808f16435775c04b36862637efa200bc4eb47797089ac3f913be962035ed9fd4"
E6_PROTOCOL_SHA256 = "2a7facb513f6fcda8a6d923e736d30820aa59e14735bf621b960756d13e9b196"
E6_SOURCE_SHA256 = "8af433ca7339f42c762b35b1f53d4e485926573531d66cd4bbe872f960240c1e"
E6_SUMMARY_SHA256 = "84ae66457c70f5a8c386d682dab5a77bfd807f3fdf0c52de0ea7b3264ebbc0cc"
ANCHOR_SUMMARY_HASHES = {
    ("pusht", "acid_cont"): "2021d263c99406c79386706b8811e46180ab80f43a6400631166b98f4820094a",
    ("pusht", "rdx_gate_all_q40"): "43e06cde30104e53e9890ab7bfbe551ad30ce5a08cc1cbb2079482905aeb95a8",
    ("reacher", "acid_cont"): "340636e2268cffa28ce01d8613092b29b55c1cd8c58b903661f8529e57c93f5f",
    ("reacher", "rdx_gate_all_q40"): "0cd511b91d7213871826dabe3f27fcad9b17e60041c444142e52c3fab7d86790",
    ("cube", "acid_cont"): "5d88a2f911c469be9b4af4933581ea1109b8584b9c5543decffee41867a19f2b",
    ("cube", "rdx_gate_all_q40"): "3769ec1d8c846fae5bc86cd2651fb6144d869b3454e12e2fb15a30475c0ae0e1",
}


def read_vector(path: Path, *, task: str, arm: str) -> tuple[np.ndarray, list[tuple[int, int]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != EVAL_COUNT or [int(row["eval_index"]) for row in rows] != list(range(EVAL_COUNT)):
        raise RuntimeError(f"invalid E6D episode vector: {task}/{arm}")
    if any(row["arm"] != arm or int(row["success"]) not in (0, 1) for row in rows):
        raise RuntimeError(f"E6D episode identity differs: {task}/{arm}")
    return (
        np.asarray([int(row["success"]) for row in rows], dtype=np.float64),
        [(int(row["episode_id"]), int(row["start_step"])) for row in rows],
    )


def load_summary(
    path: Path,
    *,
    task: str,
    arm: str,
    anchor: bool,
    source_sha: str,
    authorization_sha: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    summary_sha = d2.sha256_file(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    expected_protocol = E6_PROTOCOL_SHA256 if anchor else PROTOCOL_SHA256
    expected_source = E6_SOURCE_SHA256 if anchor else source_sha
    if (
        value.get("status") != "ok"
        or value.get("kind") != "acid_alt_e6_d2_quantile_closed_loop_evaluation"
        or value.get("task") != task
        or value.get("arm") != arm
        or value.get("scorer_seed") != 6101
        or value.get("planner_seed") != 8301
        or value.get("episode_count") != EVAL_COUNT
        or value.get("protocol_sha256") != expected_protocol
        or value.get("source_manifest_sha256") != expected_source
        or value.get("protected_c1_i1_read") is not False
        or value.get("confirmation_claim_allowed") is not False
    ):
        raise RuntimeError(f"invalid E6D input summary: {path}")
    if anchor:
        if summary_sha != ANCHOR_SUMMARY_HASHES[(task, arm)]:
            raise RuntimeError(f"E6 anchor hash changed: {task}/{arm}")
    elif value.get("authorization_sha256") != authorization_sha:
        raise RuntimeError(f"E6D authorization differs: {task}/{arm}")
    episodes = Path(value["episodes_tsv"])
    if not episodes.is_file() or d2.sha256_file(episodes) != value["episodes_tsv_sha256"]:
        raise RuntimeError(f"E6D episodes hash differs: {task}/{arm}")
    outcomes, starts = read_vector(episodes, task=task, arm=arm)
    if int(outcomes.sum()) != int(value["success_count"]):
        raise RuntimeError(f"E6D success count differs: {task}/{arm}")
    return {
        "outcomes": outcomes,
        "starts": starts,
        "summary": str(path),
        "summary_sha256": summary_sha,
        "episodes_sha256": value["episodes_tsv_sha256"],
        "manifest_sha256": value["eval_manifest_sha256"],
        "dataset_sha256": value["dataset_sha256"],
        "checkpoint_sha256": value["world_model_checkpoint_sha256"],
        "elapsed_seconds": float(value["elapsed_seconds"]),
        "runtime": value["runtime"],
    }


def summarize(vectors: dict[str, np.ndarray], indices: dict[str, np.ndarray]) -> dict[str, Any]:
    samples = {task: vectors[task][indices[task]].mean(axis=1) for task in TASKS}
    pooled = np.stack([samples[task] for task in TASKS]).mean(axis=0)
    def one(estimate: float, distribution: np.ndarray) -> dict[str, float]:
        return {
            "estimate": float(estimate),
            "lower_95_two_sided": float(np.quantile(distribution, 0.025)),
            "upper_95_two_sided": float(np.quantile(distribution, 0.975)),
        }
    return {
        "per_task": {task: one(vectors[task].mean(), samples[task]) for task in TASKS},
        "equal_task": one(np.mean([vectors[task].mean() for task in TASKS]), pooled),
    }


def analyze(outcomes: dict[str, dict[str, np.ndarray]]) -> dict[str, Any]:
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    indices = {task: generator.integers(0, EVAL_COUNT, size=(BOOTSTRAP_REPETITIONS, EVAL_COUNT), dtype=np.int16) for task in TASKS}
    levels = {arm: summarize({task: outcomes[task][arm] for task in TASKS}, indices) for arm in ALL_ARMS}
    pairs = {
        "true_minus_shuffled_allgate": ("rdx_gate_all_q40", "rdx_shuffled_gate_all_q40"),
        "true_minus_forward_allgate": ("rdx_gate_all_q40", "forward_gate_all_q40"),
        "true_minus_acid_cont": ("rdx_gate_all_q40", "acid_cont"),
        "true_minus_acid_allgate": ("rdx_gate_all_q40", "acid_gate_all_q40"),
    }
    contrast_vectors = {label: {task: outcomes[task][left] - outcomes[task][right] for task in TASKS} for label, (left, right) in pairs.items()}
    contrasts = {label: summarize(vectors, indices) for label, vectors in contrast_vectors.items()}
    shuffled = contrasts["true_minus_shuffled_allgate"]
    acid = contrasts["true_minus_acid_cont"]
    gates = {
        "1_true_beats_shuffled_equal_task": shuffled["equal_task"]["estimate"] > 0,
        "2_true_beats_forward_equal_task": contrasts["true_minus_forward_allgate"]["equal_task"]["estimate"] > 0,
        "3_true_noninferior_acid_equal_task": acid["equal_task"]["estimate"] >= -0.05,
        "4_true_task_pattern_vs_shuffled": (
            all(shuffled["per_task"][task]["estimate"] >= -0.05 for task in TASKS)
            and sum(shuffled["per_task"][task]["estimate"] > 0 for task in TASKS) >= 2
        ),
        "5_true_task_floor_vs_acid": all(acid["per_task"][task]["estimate"] >= -0.15 for task in TASKS),
    }
    passed = all(gates.values())
    return {
        "levels": levels,
        "contrasts": contrasts,
        "gates": gates,
        "all_e6d_gates_pass": passed,
        "decision": "authorize_allgate_three_seed_d2_replication" if passed else "end_rdx_verifier_gating",
    }


def parse_identity(values: list[str], allowed: tuple[str, ...]) -> tuple[str, str, Path]:
    task, arm, path = values
    if task not in TASKS or arm not in allowed:
        raise ValueError(f"invalid E6D identity: {values}")
    return task, arm, Path(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--e6-summary", type=Path, required=True)
    parser.add_argument("--anchor", nargs=3, action="append", required=True)
    parser.add_argument("--run", nargs=3, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if d2.sha256_file(args.protocol) != PROTOCOL_SHA256 or d2.sha256_file(args.e6_summary) != E6_SUMMARY_SHA256:
        raise RuntimeError("E6D frozen evidence hash mismatch")
    source_sha = d2.sha256_file(args.source_manifest)
    authorization_sha = d2.sha256_file(args.authorization)
    authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
    if (
        authorization.get("kind") != "acid_alt_e6d_d2_authorization"
        or authorization.get("source_manifest_sha256") != source_sha
        or authorization.get("protocol_sha256") != PROTOCOL_SHA256
        or authorization.get("e6_summary_sha256") != E6_SUMMARY_SHA256
        or authorization.get("arms") != list(NEW_ARMS)
        or authorization.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E6D authorization mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E6D analysis output")
    anchors = [parse_identity(value, ANCHOR_ARMS) for value in args.anchor]
    runs = [parse_identity(value, NEW_ARMS) for value in args.run]
    if {(a, b) for a, b, _ in anchors} != {(task, arm) for task in TASKS for arm in ANCHOR_ARMS} or len(anchors) != 6:
        raise RuntimeError("E6D anchor grid differs")
    if {(a, b) for a, b, _ in runs} != {(task, arm) for task in TASKS for arm in NEW_ARMS} or len(runs) != 9:
        raise RuntimeError("E6D control grid differs")
    loaded = {}
    for task, arm, path in anchors:
        loaded[(task, arm)] = load_summary(path, task=task, arm=arm, anchor=True, source_sha=source_sha, authorization_sha=authorization_sha)
    for task, arm, path in runs:
        loaded[(task, arm)] = load_summary(path, task=task, arm=arm, anchor=False, source_sha=source_sha, authorization_sha=authorization_sha)
    for task in TASKS:
        reference = loaded[(task, "rdx_gate_all_q40")]
        for arm in ALL_ARMS:
            record = loaded[(task, arm)]
            if any(record[key] != reference[key] for key in ("starts", "manifest_sha256", "dataset_sha256", "checkpoint_sha256")):
                raise RuntimeError(f"unpaired E6D input: {task}/{arm}")
    outcomes = {task: {arm: loaded[(task, arm)]["outcomes"] for arm in ALL_ARMS} for task in TASKS}
    statistics = analyze(outcomes)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "ok", "kind": "acid_alt_e6d_allgate_control_analysis",
        "analysis_role": "post_e6_exposed_d2_allgate_diagnostic",
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS, "bootstrap_seed": BOOTSTRAP_SEED,
        **statistics,
        "protocol_sha256": PROTOCOL_SHA256, "source_manifest_sha256": source_sha,
        "authorization_sha256": authorization_sha, "e6_summary_sha256": E6_SUMMARY_SHA256,
        "claim_decision": "no_claim_from_exposed_d2_diagnostic",
        "confirmation_claim_allowed": False, "d3_access_allowed": False,
        "protected_c1_i1_read": False,
    }
    output = args.output_dir / "summary.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
