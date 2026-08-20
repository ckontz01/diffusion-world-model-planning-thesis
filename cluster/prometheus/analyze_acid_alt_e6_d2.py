#!/usr/bin/env python3
"""Analyze the frozen one-seed E6 exposed-D2 closed-loop pilot."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_d2_models as d2
import acid_alt_e6_quantile_models as e6


TASKS = ("pusht", "reacher", "cube")
EVAL_COUNT = 50
SCORER_SEED = 6101
PLANNER_SEED = 8301
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081606
PROTOCOL_SHA256 = "2a7facb513f6fcda8a6d923e736d30820aa59e14735bf621b960756d13e9b196"
E3_SUMMARY_SHA256 = "2a4134b49f770cd3f339d73233183d5bd2013b562aee751abc0e8a744959fdbb"
E5_SUMMARY_SHA256 = "0c956e95e258eeb440bad12e71de3528b317c49c06f50519e5bc110e3c5da553"


def parse_run(values: list[str]) -> tuple[str, str, Path]:
    task, arm, path = values
    if task not in TASKS or arm not in e6.ARMS:
        raise ValueError(f"invalid E6 run identity: {values}")
    return task, arm, Path(path)


def load_run(
    task: str,
    arm: str,
    path: Path,
    *,
    source_manifest_sha: str,
    authorization_sha: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind") != "acid_alt_e6_d2_quantile_closed_loop_evaluation"
        or value.get("analysis_role")
        != "post_e3_e5_exposed_d2_planner_integration_development"
        or value.get("task") != task
        or value.get("arm") != arm
        or value.get("arm_spec") != e6.arm_spec(arm)  # type: ignore[arg-type]
        or value.get("scorer_seed") != SCORER_SEED
        or value.get("planner_seed") != PLANNER_SEED
        or value.get("episode_count") != EVAL_COUNT
        or value.get("protocol_sha256") != PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != source_manifest_sha
        or value.get("authorization_sha256") != authorization_sha
        or value.get("e3_summary_sha256") != E3_SUMMARY_SHA256
        or value.get("e5_summary_sha256") != E5_SUMMARY_SHA256
        or value.get("confirmation_claim_allowed") is not False
        or value.get("alternative_to_acid_claim_allowed") is not False
        or value.get("d3_selected") is not False
        or value.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError(f"invalid E6 summary: {path}")
    episodes = Path(value["episodes_tsv"])
    if not episodes.is_file() or d2.sha256_file(episodes) != value["episodes_tsv_sha256"]:
        raise RuntimeError(f"E6 episode hash mismatch: {path}")
    with episodes.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != EVAL_COUNT or [int(row["eval_index"]) for row in rows] != list(range(EVAL_COUNT)):
        raise RuntimeError(f"E6 episode vector is invalid: {path}")
    if any(
        row["arm"] != arm
        or int(row["scorer_seed"]) != SCORER_SEED
        or int(row["planner_seed"]) != PLANNER_SEED
        or int(row["success"]) not in (0, 1)
        for row in rows
    ):
        raise RuntimeError(f"E6 episode identity mismatch: {path}")
    outcomes = np.asarray([int(row["success"]) for row in rows], dtype=np.float64)
    if int(outcomes.sum()) != int(value["success_count"]):
        raise RuntimeError(f"E6 success count mismatch: {path}")
    return {
        "outcomes": outcomes,
        "starts": [(int(row["episode_id"]), int(row["start_step"])) for row in rows],
        "summary": str(path),
        "summary_sha256": d2.sha256_file(path),
        "episodes_sha256": value["episodes_tsv_sha256"],
        "eval_manifest_sha256": value["eval_manifest_sha256"],
        "dataset_sha256": value["dataset_sha256"],
        "world_model_checkpoint_sha256": value["world_model_checkpoint_sha256"],
        "elapsed_seconds": float(value["elapsed_seconds"]),
        "cem_cost_calls": int(value["cem_cost_calls"]),
        "runtime": value["runtime"],
    }


def bootstrap_indices() -> dict[str, np.ndarray]:
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    return {
        task: generator.integers(0, EVAL_COUNT, size=(BOOTSTRAP_REPETITIONS, EVAL_COUNT), dtype=np.int16)
        for task in TASKS
    }


def summarize(vectors: dict[str, np.ndarray], indices: dict[str, np.ndarray]) -> dict[str, Any]:
    sampled = {task: vectors[task][indices[task]].mean(axis=1) for task in TASKS}
    pooled = np.stack([sampled[task] for task in TASKS]).mean(axis=0)
    def record(estimate: float, samples: np.ndarray) -> dict[str, float]:
        return {
            "estimate": float(estimate),
            "lower_95_two_sided": float(np.quantile(samples, 0.025)),
            "upper_95_two_sided": float(np.quantile(samples, 0.975)),
            "lower_95_one_sided": float(np.quantile(samples, 0.05)),
        }
    return {
        "per_task": {task: record(vectors[task].mean(), sampled[task]) for task in TASKS},
        "equal_task": record(np.mean([vectors[task].mean() for task in TASKS]), pooled),
    }


def analyze(outcomes: dict[str, dict[str, np.ndarray]]) -> dict[str, Any]:
    indices = bootstrap_indices()
    levels = {
        arm: summarize({task: outcomes[task][arm] for task in TASKS}, indices)
        for arm in e6.ARMS
    }
    pairs = {
        "primary_minus_acid_cont": (e6.PRIMARY_ARM, "acid_cont"),
        "primary_minus_shuffled": (e6.PRIMARY_ARM, "rdx_shuffled_gate_tail5_q40"),
        "primary_minus_b0": (e6.PRIMARY_ARM, "b0"),
        "primary_minus_forward_gate": (e6.PRIMARY_ARM, "forward_gate_tail5_q40"),
        "primary_minus_acid_gate": (e6.PRIMARY_ARM, "acid_gate_tail5_q40"),
        "primary_minus_rdx_cont": (e6.PRIMARY_ARM, "rdx_cont"),
        "q20_minus_primary": ("rdx_gate_tail5_q20", e6.PRIMARY_ARM),
        "all_q40_minus_primary": ("rdx_gate_all_q40", e6.PRIMARY_ARM),
    }
    contrast_vectors = {
        label: {task: outcomes[task][left] - outcomes[task][right] for task in TASKS}
        for label, (left, right) in pairs.items()
    }
    contrasts = {label: summarize(vectors, indices) for label, vectors in contrast_vectors.items()}
    primary_acid = contrasts["primary_minus_acid_cont"]
    primary_b0 = contrasts["primary_minus_b0"]
    gates = {
        "1_primary_beats_acid_equal_task": primary_acid["equal_task"]["estimate"] > 0,
        "2_primary_beats_shuffled_equal_task": contrasts["primary_minus_shuffled"]["equal_task"]["estimate"] > 0,
        "3_primary_not_below_b0_equal_task": primary_b0["equal_task"]["estimate"] >= 0,
        "4_primary_task_robustness": (
            all(primary_acid["per_task"][task]["estimate"] >= -0.10 for task in TASKS)
            and all(primary_b0["per_task"][task]["estimate"] >= -0.10 for task in TASKS)
            and sum(primary_acid["per_task"][task]["estimate"] > 0 for task in TASKS) >= 2
        ),
        "5_primary_noninferior_forward_gate": contrasts["primary_minus_forward_gate"]["equal_task"]["estimate"] >= -0.02,
    }
    passed = all(gates.values())
    return {
        "levels": levels,
        "contrasts": contrasts,
        "gates": gates,
        "all_pilot_promotion_gates_pass": passed,
        "decision": "authorize_three_seed_d2_replication" if passed else "stop_e6_before_d3",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--run", nargs=3, action="append", metavar=("TASK", "ARM", "SUMMARY"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.protocol, args.source_manifest, args.authorization):
        if not path.is_file():
            raise FileNotFoundError(path)
    if d2.sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E6 protocol hash mismatch")
    source_manifest_sha = d2.sha256_file(args.source_manifest)
    authorization_sha = d2.sha256_file(args.authorization)
    authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
    if (
        authorization.get("kind") != "acid_alt_e6_d2_authorization"
        or authorization.get("source_manifest_sha256") != source_manifest_sha
        or authorization.get("protocol_sha256") != PROTOCOL_SHA256
        or authorization.get("arms") != list(e6.ARMS)
        or authorization.get("primary_arm") != e6.PRIMARY_ARM
        or authorization.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E6 authorization mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E6 analysis output")
    identities = [parse_run(value) for value in args.run]
    expected = {(task, arm) for task in TASKS for arm in e6.ARMS}
    observed = {(task, arm) for task, arm, _ in identities}
    if observed != expected or len(identities) != len(expected):
        raise RuntimeError(f"E6 run grid mismatch: missing={sorted(expected-observed)}, extra={sorted(observed-expected)}")
    loaded = {
        (task, arm): load_run(task, arm, path, source_manifest_sha=source_manifest_sha, authorization_sha=authorization_sha)
        for task, arm, path in identities
    }
    for task in TASKS:
        reference = loaded[(task, "b0")]
        for arm in e6.ARMS:
            run = loaded[(task, arm)]
            if any(
                run[key] != reference[key]
                for key in ("starts", "eval_manifest_sha256", "dataset_sha256", "world_model_checkpoint_sha256")
            ):
                raise RuntimeError(f"unpaired E6 inputs: {task}/{arm}")
    outcomes = {
        task: {arm: loaded[(task, arm)]["outcomes"] for arm in e6.ARMS}
        for task in TASKS
    }
    statistics = analyze(outcomes)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = args.output_dir / "runs.tsv"
    with runs_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("task", "arm", "success_count", "success_rate", "elapsed_seconds", "cem_cost_calls", "summary_sha256", "episodes_sha256", "gpu"), delimiter="\t")
        writer.writeheader()
        for task in TASKS:
            for arm in e6.ARMS:
                run = loaded[(task, arm)]
                writer.writerow({
                    "task": task,
                    "arm": arm,
                    "success_count": int(run["outcomes"].sum()),
                    "success_rate": float(run["outcomes"].mean()),
                    "elapsed_seconds": run["elapsed_seconds"],
                    "cem_cost_calls": run["cem_cost_calls"],
                    "summary_sha256": run["summary_sha256"],
                    "episodes_sha256": run["episodes_sha256"],
                    "gpu": run["runtime"]["gpu"],
                })
    result = {
        "status": "ok",
        "kind": "acid_alt_e6_d2_quantile_closed_loop_analysis",
        "analysis_role": "post_e3_e5_exposed_d2_planner_integration_development",
        "primary_arm": e6.PRIMARY_ARM,
        "scorer_seed": SCORER_SEED,
        "planner_seed": PLANNER_SEED,
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        **statistics,
        "claim_decision": "no_claim_from_exposed_d2_pilot",
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": source_manifest_sha,
        "authorization_sha256": authorization_sha,
        "runs_tsv": str(runs_path),
        "runs_tsv_sha256": d2.sha256_file(runs_path),
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "protected_c1_i1_read": False,
    }
    output = args.output_dir / "summary.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
