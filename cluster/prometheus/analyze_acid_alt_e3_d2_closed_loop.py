#!/usr/bin/env python3
"""Analyze the frozen post-v3 exploratory E3 D2 closed-loop experiment."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_d2_models as d2


TASKS = ("pusht", "reacher", "cube")
ARMS = (
    "b0",
    "acid",
    "forward",
    "rdx",
    "ae",
    "ae_shuffled",
)
PLANNER_SEEDS = (8301, 8302, 8303)
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081605
EVAL_COUNT = 50
E3_PROTOCOL_SHA256 = (
    "c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0"
)
V3_SOURCE_MANIFEST_SHA256 = (
    "2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea"
)
STAGE_A_SUMMARY_SHA256 = (
    "0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37"
)
STAGE_A_MANIFEST_SHA256 = (
    "3558b8612787035cfa92c17d8a36f46f379bb2812f67aa0a73438d8cab974053"
)
EXPECTED_STAGE_A_GATES = {
    "1_rdx_positive_all_tasks_and_pooled": True,
    "2_rdx_beats_shuffled": True,
    "3_rdx_noninferior_forward_and_acid": False,
    "4_ae_beats_shuffled_without_negative_task": True,
    "5_ae_selection_noninferior_acid": True,
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_run(values: list[str]) -> tuple[str, str, int, int, Path]:
    task, arm, scorer_text, planner_text, summary_text = values
    if task not in TASKS or arm not in ARMS:
        raise ValueError(f"invalid run identity: {values}")
    scorer_seed = int(scorer_text)
    planner_seed = int(planner_text)
    if scorer_seed not in d2.SEEDS or planner_seed not in PLANNER_SEEDS:
        raise ValueError(f"invalid paired seeds: {values}")
    if planner_seed - scorer_seed != 2200:
        raise ValueError(f"unpaired scorer/planner seeds: {values}")
    return task, arm, scorer_seed, planner_seed, Path(summary_text)


def read_episode_vector(
    path: Path, *, task: str, arm: str, scorer_seed: int, planner_seed: int
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {
        "eval_index",
        "episode_id",
        "start_step",
        "scorer_seed",
        "planner_seed",
        "arm",
        "success",
    }
    if len(rows) != EVAL_COUNT or not required.issubset(rows[0]):
        raise RuntimeError(f"{task}/{arm}: invalid episodes TSV")
    if [int(row["eval_index"]) for row in rows] != list(range(EVAL_COUNT)):
        raise RuntimeError(f"{task}/{arm}: noncontiguous evaluation indices")
    if any(
        row["arm"] != arm
        or int(row["scorer_seed"]) != scorer_seed
        or int(row["planner_seed"]) != planner_seed
        or int(row["success"]) not in (0, 1)
        for row in rows
    ):
        raise RuntimeError(f"{task}/{arm}: episode identity mismatch")
    starts = [(int(row["episode_id"]), int(row["start_step"])) for row in rows]
    return np.asarray([int(row["success"]) for row in rows], dtype=np.float64), starts


def load_run(
    identity: tuple[str, str, int, int, Path],
    *,
    protocol_sha: str,
    source_manifest_sha: str,
    authorization_sha: str,
) -> dict[str, Any]:
    task, arm, scorer_seed, planner_seed, summary_path = identity
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "acid_alt_e3_d2_exploratory_closed_loop_evaluation"
        or summary.get("analysis_role") != "post_v3_exploratory_d2_closed_loop_development"
        or summary.get("task") != task
        or summary.get("arm") != arm
        or int(summary.get("scorer_seed", -1)) != scorer_seed
        or int(summary.get("planner_seed", -1)) != planner_seed
        or summary.get("episode_count") != EVAL_COUNT
        or summary.get("protocol_sha256") != protocol_sha
        or summary.get("source_manifest_sha256") != source_manifest_sha
        or summary.get("upstream_source_manifest_sha256")
        != V3_SOURCE_MANIFEST_SHA256
        or summary.get("v3_upstream_source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or summary.get("exploratory_authorization_sha256") != authorization_sha
        or summary.get("v3_stage_b_authorized") is not False
        or summary.get("confirmation_claim_allowed") is not False
        or summary.get("alternative_to_acid_claim_allowed") is not False
        or summary.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError(f"invalid D2 closed-loop summary: {summary_path}")
    episode_path = Path(summary["episodes_tsv"])
    if (
        not episode_path.is_file()
        or d2.sha256_file(episode_path) != summary.get("episodes_tsv_sha256")
    ):
        raise RuntimeError(f"episode TSV hash mismatch: {summary_path}")
    success, starts = read_episode_vector(
        episode_path,
        task=task,
        arm=arm,
        scorer_seed=scorer_seed,
        planner_seed=planner_seed,
    )
    if int(success.sum()) != int(summary["success_count"]):
        raise RuntimeError(f"success count mismatch: {summary_path}")
    return {
        "success": success,
        "starts": starts,
        "summary": str(summary_path),
        "summary_sha256": d2.sha256_file(summary_path),
        "episodes": str(episode_path),
        "episodes_sha256": d2.sha256_file(episode_path),
        "eval_manifest_sha256": summary["eval_manifest_sha256"],
        "dataset_sha256": summary["dataset_sha256"],
        "world_model_checkpoint_sha256": summary[
            "world_model_checkpoint_sha256"
        ],
        "elapsed_seconds": float(summary["elapsed_seconds"]),
        "cem_cost_calls": int(summary["cem_cost_calls"]),
        "runtime": summary["runtime"],
    }


def bootstrap_indices() -> dict[str, np.ndarray]:
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    return {
        task: generator.integers(
            0, EVAL_COUNT, size=(BOOTSTRAP_REPETITIONS, EVAL_COUNT), dtype=np.int16
        )
        for task in TASKS
    }


def bootstrap_task(matrix: np.ndarray, indices: np.ndarray) -> np.ndarray:
    if matrix.shape != (len(d2.SEEDS), EVAL_COUNT):
        raise ValueError("paired outcome matrix has an unexpected shape")
    result = np.empty(BOOTSTRAP_REPETITIONS, dtype=np.float64)
    batch = 5_000
    for start in range(0, BOOTSTRAP_REPETITIONS, batch):
        stop = min(start + batch, BOOTSTRAP_REPETITIONS)
        selected = matrix[:, indices[start:stop]]
        result[start:stop] = selected.mean(axis=(0, 2))
    return result


def summarize(
    matrices: dict[str, np.ndarray], indices: dict[str, np.ndarray]
) -> dict[str, Any]:
    per_task_boot = {
        task: bootstrap_task(matrices[task], indices[task]) for task in TASKS
    }
    pooled = np.mean(np.stack([per_task_boot[task] for task in TASKS]), axis=0)

    def interval(values: np.ndarray) -> dict[str, float]:
        return {
            "lower_95_two_sided": float(np.quantile(values, 0.025)),
            "upper_95_two_sided": float(np.quantile(values, 0.975)),
            "lower_95_one_sided": float(np.quantile(values, 0.05)),
            "upper_95_one_sided": float(np.quantile(values, 0.95)),
        }

    return {
        "per_task": {
            task: {
                "estimate": float(matrices[task].mean()),
                **interval(per_task_boot[task]),
            }
            for task in TASKS
        },
        "equal_task": {
            "estimate": float(
                np.mean([matrices[task].mean() for task in TASKS])
            ),
            **interval(pooled),
        },
    }


def exact_cluster_sign_test(matrix: np.ndarray) -> dict[str, Any]:
    """Two-sided exact sign test on paired start clusters, averaging seeds."""

    by_start = matrix.mean(axis=0)
    positive = int(np.count_nonzero(by_start > 0))
    negative = int(np.count_nonzero(by_start < 0))
    ties = int(np.count_nonzero(by_start == 0))
    trials = positive + negative
    if trials == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(trials, k) for k in range(min(positive, negative) + 1))
        p_value = min(1.0, 2.0 * tail / (2.0**trials))
    return {
        "unit": "start cluster; three paired scorer/planner seeds averaged",
        "positive": positive,
        "negative": negative,
        "ties": ties,
        "two_sided_exact_p": float(p_value),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--exploratory-authorization", type=Path, required=True)
    parser.add_argument(
        "--run",
        nargs=5,
        action="append",
        metavar=("TASK", "ARM", "SCORER_SEED", "PLANNER_SEED", "SUMMARY"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.protocol, args.source_manifest, args.exploratory_authorization):
        if not path.is_file():
            raise FileNotFoundError(path)
    protocol_sha = d2.sha256_file(args.protocol)
    source_manifest_sha = d2.sha256_file(args.source_manifest)
    authorization_sha = d2.sha256_file(args.exploratory_authorization)
    if protocol_sha != E3_PROTOCOL_SHA256:
        raise RuntimeError("E3 protocol hash mismatch")
    authorization = json.loads(
        args.exploratory_authorization.read_text(encoding="utf-8")
    )
    if (
        authorization.get("status")
        != "authorized_for_exploratory_development_only"
        or authorization.get("kind")
        != "acid_alt_e3_d2_exploratory_authorization"
        or authorization.get("analysis_role")
        != "post_v3_exploratory_d2_closed_loop_development"
        or authorization.get("protocol_sha256") != protocol_sha
        or authorization.get("source_manifest_sha256") != source_manifest_sha
        or authorization.get("v3_protocol_sha256") != d2.PROTOCOL_SHA256
        or authorization.get("v3_source_manifest_sha256")
        != V3_SOURCE_MANIFEST_SHA256
        or authorization.get("v3_upstream_source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or authorization.get("stage_a_summary_sha256")
        != STAGE_A_SUMMARY_SHA256
        or authorization.get("stage_a_manifest_sha256")
        != STAGE_A_MANIFEST_SHA256
        or authorization.get("v3_stage_b_authorized") is not False
        or authorization.get("confirmation_claim_allowed") is not False
        or authorization.get("alternative_to_acid_claim_allowed") is not False
        or authorization.get("arms") != list(ARMS)
        or authorization.get("scorer_seeds") != list(d2.SEEDS)
        or authorization.get("planner_seeds") != list(PLANNER_SEEDS)
        or authorization.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E3 exploratory authorization is invalid")
    stage_a = Path(authorization["stage_a_summary"])
    stage_a_manifest = Path(authorization["stage_a_manifest"])
    if (
        not stage_a.is_file()
        or not stage_a_manifest.is_file()
        or d2.sha256_file(stage_a) != STAGE_A_SUMMARY_SHA256
        or d2.sha256_file(stage_a_manifest) != STAGE_A_MANIFEST_SHA256
    ):
        raise RuntimeError("frozen failed Stage-A evidence hash mismatch")
    stage_a_payload = json.loads(stage_a.read_text(encoding="utf-8"))
    stage_a_manifest_payload = json.loads(
        stage_a_manifest.read_text(encoding="utf-8")
    )
    if (
        stage_a_payload.get("status") != "ok"
        or stage_a_payload.get("kind") != "acid_alt_v3_d2_stage_a_analysis"
        or stage_a_payload.get("all_stage_a_gates_pass") is not False
        or stage_a_payload.get("decision") != "stop_before_stage_b"
        or stage_a_payload.get("gates") != EXPECTED_STAGE_A_GATES
        or stage_a_payload.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or stage_a_payload.get("source_manifest_sha256")
        != V3_SOURCE_MANIFEST_SHA256
        or stage_a_payload.get("protected_c1_i1_read") is not False
        or stage_a_manifest_payload.get("stage_b_authorized") is not False
        or stage_a_manifest_payload.get("summary_sha256")
        != STAGE_A_SUMMARY_SHA256
        or stage_a_manifest_payload.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E3 requires the exact failed v3 Stage-A result")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E3 analysis output")

    identities = [parse_run(values) for values in args.run]
    expected_grid = {
        (task, arm, scorer_seed, scorer_seed + 2200)
        for task in TASKS
        for arm in ARMS
        for scorer_seed in d2.SEEDS
    }
    observed_grid = {(a, b, c, d) for a, b, c, d, _ in identities}
    if observed_grid != expected_grid or len(identities) != len(expected_grid):
        missing = sorted(expected_grid - observed_grid)
        extra = sorted(observed_grid - expected_grid)
        raise RuntimeError(f"E3 grid mismatch; missing={missing}, extra={extra}")

    loaded = {
        (task, arm, scorer_seed): load_run(
            identity,
            protocol_sha=protocol_sha,
            source_manifest_sha=source_manifest_sha,
            authorization_sha=authorization_sha,
        )
        for identity in identities
        for task, arm, scorer_seed, _, _ in (identity,)
    }
    for task in TASKS:
        reference = loaded[(task, "b0", d2.SEEDS[0])]
        for arm in ARMS:
            for seed in d2.SEEDS:
                record = loaded[(task, arm, seed)]
                if (
                    record["starts"] != reference["starts"]
                    or record["eval_manifest_sha256"]
                    != reference["eval_manifest_sha256"]
                    or record["dataset_sha256"] != reference["dataset_sha256"]
                    or record["world_model_checkpoint_sha256"]
                    != reference["world_model_checkpoint_sha256"]
                ):
                    raise RuntimeError(f"unpaired E3 inputs: {task}/{arm}/{seed}")

    matrices = {
        task: {
            arm: np.stack(
                [loaded[(task, arm, seed)]["success"] for seed in d2.SEEDS]
            )
            for arm in ARMS
        }
        for task in TASKS
    }
    indices = bootstrap_indices()
    levels = {
        arm: summarize({task: matrices[task][arm] for task in TASKS}, indices)
        for arm in ARMS
    }
    contrast_pairs = {
        "ae_minus_acid": ("ae", "acid"),
        "ae_minus_b0": ("ae", "b0"),
        "ae_minus_ae_shuffled": ("ae", "ae_shuffled"),
        "ae_minus_forward": ("ae", "forward"),
        "rdx_minus_acid": ("rdx", "acid"),
        "rdx_minus_b0": ("rdx", "b0"),
    }
    contrast_matrices = {
        label: {
            task: matrices[task][left] - matrices[task][right]
            for task in TASKS
        }
        for label, (left, right) in contrast_pairs.items()
    }
    contrasts = {
        label: summarize(values, indices)
        for label, values in contrast_matrices.items()
    }
    exact_sensitivity = {
        label: {
            "per_task": {
                task: exact_cluster_sign_test(values[task]) for task in TASKS
            },
            "pooled_equal_task_descriptive": exact_cluster_sign_test(
                np.concatenate([values[task] for task in TASKS], axis=1)
            ),
        }
        for label, values in contrast_matrices.items()
    }

    ae_b0 = contrasts["ae_minus_b0"]
    gates = {
        "1_ae_noninferior_acid": (
            contrasts["ae_minus_acid"]["equal_task"]["lower_95_one_sided"]
            > -0.05
            and all(
                contrasts["ae_minus_acid"]["per_task"][task][
                    "lower_95_one_sided"
                ]
                > -0.10
                for task in TASKS
            )
        ),
        "2_ae_beats_b0": ae_b0["equal_task"]["lower_95_two_sided"] > 0,
        "3_ae_beats_shuffled": contrasts["ae_minus_ae_shuffled"][
            "equal_task"
        ]["lower_95_two_sided"]
        > 0,
        "4_ae_task_pattern_vs_b0": (
            all(ae_b0["per_task"][task]["estimate"] >= -0.10 for task in TASKS)
            and sum(
                ae_b0["per_task"][task]["estimate"] > 0 for task in TASKS
            )
            >= 2
        ),
        "5_ae_noninferior_forward": contrasts["ae_minus_forward"][
            "equal_task"
        ]["lower_95_one_sided"]
        > -0.05,
    }
    all_pass = all(gates.values())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_table = args.output_dir / "runs.tsv"
    with run_table.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "task",
                "arm",
                "scorer_seed",
                "planner_seed",
                "success_count",
                "success_rate",
                "summary_sha256",
                "episodes_sha256",
                "elapsed_seconds",
                "cem_cost_calls",
                "gpu",
                "peak_cuda_memory_allocated_bytes",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for task in TASKS:
            for arm in ARMS:
                for seed in d2.SEEDS:
                    record = loaded[(task, arm, seed)]
                    writer.writerow(
                        {
                            "task": task,
                            "arm": arm,
                            "scorer_seed": seed,
                            "planner_seed": seed + 2200,
                            "success_count": int(record["success"].sum()),
                            "success_rate": float(record["success"].mean()),
                            "summary_sha256": record["summary_sha256"],
                            "episodes_sha256": record["episodes_sha256"],
                            "elapsed_seconds": record["elapsed_seconds"],
                            "cem_cost_calls": record["cem_cost_calls"],
                            "gpu": record["runtime"]["gpu"],
                            "peak_cuda_memory_allocated_bytes": record["runtime"][
                                "peak_cuda_memory_allocated_bytes"
                            ],
                        }
                    )

    result = {
        "status": "ok",
        "kind": "acid_alt_e3_d2_exploratory_closed_loop_analysis",
        "analysis_role": "post_v3_exploratory_d2_closed_loop_development",
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "levels": levels,
        "contrasts": contrasts,
        "exact_paired_sensitivity": exact_sensitivity,
        "gates": gates,
        "all_e3_promotion_gates_pass": all_pass,
        "decision": (
            "promote_ae_to_new_confirmation"
            if all_pass
            else "stop_diffusion_development_and_pivot"
        ),
        "claim_decision": "no_publication_claim_from_exploratory_e3",
        "run_inputs": {
            f"{task}/{arm}/{seed}": {
                key: value
                for key, value in loaded[(task, arm, seed)].items()
                if key not in {"success", "starts"}
            }
            for task in TASKS
            for arm in ARMS
            for seed in d2.SEEDS
        },
        "runs_tsv": str(run_table),
        "runs_tsv_sha256": d2.sha256_file(run_table),
        "protocol": str(args.protocol),
        "protocol_sha256": protocol_sha,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_manifest_sha,
        "exploratory_authorization": str(args.exploratory_authorization),
        "exploratory_authorization_sha256": authorization_sha,
        "stage_a_summary_sha256": STAGE_A_SUMMARY_SHA256,
        "stage_a_manifest_sha256": STAGE_A_MANIFEST_SHA256,
        "v3_stage_b_authorized": False,
        "confirmation_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "protected_c1_i1_read": False,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, result)
    atomic_json(
        args.output_dir / "manifest.json",
        {
            "status": "ok",
            "kind": "acid_alt_e3_d2_exploratory_closed_loop_manifest",
            "summary": str(summary_path),
            "summary_sha256": d2.sha256_file(summary_path),
            "runs_tsv_sha256": d2.sha256_file(run_table),
            "all_e3_promotion_gates_pass": all_pass,
            "protocol_sha256": protocol_sha,
            "source_manifest_sha256": source_manifest_sha,
            "protected_c1_i1_read": False,
        },
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


