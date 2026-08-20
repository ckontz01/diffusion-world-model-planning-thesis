#!/usr/bin/env python3
"""Analyze the preregistered v3 D2 paired closed-loop experiment."""

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
    "reachability",
    "dtv",
    "forward",
    "rdx",
    "ae",
    "ae_shuffled",
)
PLANNER_SEEDS = (8301, 8302, 8303)
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081605
EVAL_COUNT = 50


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
        or summary.get("kind") != "acid_alt_v3_d2_closed_loop_evaluation"
        or summary.get("analysis_role") != "fresh preregistered D2 development"
        or summary.get("task") != task
        or summary.get("arm") != arm
        or int(summary.get("scorer_seed", -1)) != scorer_seed
        or int(summary.get("planner_seed", -1)) != planner_seed
        or summary.get("episode_count") != EVAL_COUNT
        or summary.get("protocol_sha256") != protocol_sha
        or summary.get("source_manifest_sha256") != source_manifest_sha
        or summary.get("upstream_source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or summary.get("stage_b_authorization_sha256") != authorization_sha
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
    parser.add_argument("--stage-b-authorization", type=Path, required=True)
    parser.add_argument(
        "--run",
        nargs=5,
        action="append",
        metavar=("TASK", "ARM", "SCORER_SEED", "PLANNER_SEED", "SUMMARY"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.protocol, args.source_manifest, args.stage_b_authorization):
        if not path.is_file():
            raise FileNotFoundError(path)
    protocol_sha = d2.sha256_file(args.protocol)
    source_manifest_sha = d2.sha256_file(args.source_manifest)
    authorization_sha = d2.sha256_file(args.stage_b_authorization)
    if protocol_sha != d2.PROTOCOL_SHA256:
        raise RuntimeError("D2 protocol hash mismatch")
    authorization = json.loads(
        args.stage_b_authorization.read_text(encoding="utf-8")
    )
    if (
        authorization.get("status") != "authorized"
        or authorization.get("kind")
        != "acid_alt_v3_d2_stage_b_authorization"
        or authorization.get("protocol_sha256") != protocol_sha
        or authorization.get("source_manifest_sha256") != source_manifest_sha
        or authorization.get("upstream_source_manifest_sha256")
        != d2.PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256
        or authorization.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("Stage-B authorization is invalid")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty Stage-B analysis output")

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
        raise RuntimeError(f"Stage-B grid mismatch; missing={missing}, extra={extra}")

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
                    raise RuntimeError(f"unpaired Stage-B inputs: {task}/{arm}/{seed}")

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
        "ae_minus_reachability": ("ae", "reachability"),
        "ae_minus_dtv": ("ae", "dtv"),
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
                        }
                    )

    result = {
        "status": "ok",
        "kind": "acid_alt_v3_d2_stage_b_analysis",
        "analysis_role": "fresh preregistered D2 development",
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "levels": levels,
        "contrasts": contrasts,
        "exact_paired_sensitivity": exact_sensitivity,
        "gates": gates,
        "all_stage_b_gates_pass": all_pass,
        "claim_decision": (
            "supports_lewm_suite_alternative_to_acid_reconstruction"
            if all_pass
            else "does_not_support_alternative_to_acid_claim"
        ),
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
        "stage_b_authorization": str(args.stage_b_authorization),
        "stage_b_authorization_sha256": authorization_sha,
        "protected_c1_i1_read": False,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, result)
    atomic_json(
        args.output_dir / "manifest.json",
        {
            "status": "ok",
            "kind": "acid_alt_v3_d2_stage_b_manifest",
            "summary": str(summary_path),
            "summary_sha256": d2.sha256_file(summary_path),
            "runs_tsv_sha256": d2.sha256_file(run_table),
            "all_stage_b_gates_pass": all_pass,
            "protocol_sha256": protocol_sha,
            "source_manifest_sha256": source_manifest_sha,
            "protected_c1_i1_read": False,
        },
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
