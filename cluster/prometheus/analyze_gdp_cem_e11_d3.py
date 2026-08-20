#!/usr/bin/env python3
"""Aggregate all E11 shards and apply the frozen untouched-D3 gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import h5py

import acid_alt_d2_models as d2
import create_gdp_cem_e11_d3_manifest as d3_manifest
import gdp_cem_e11_specs as spec


BOOTSTRAP_REPETITIONS = 100_000
PRIMARY_BOOTSTRAP_SEED = 2026081710
TWO_WAY_BOOTSTRAP_SEED = 2026081711
TREATMENT = "vp_true_select"
PRIMARY_CONTROLS = (
    "gaussian_select",
    "vp_shuffled_select",
    "vp_unconditional_select",
    "acid",
)
SECONDARY_CONTROLS = ("b0", "reachability", "forward")
CONTRAST_ORDER = PRIMARY_CONTROLS + SECONDARY_CONTROLS


def expected_array_index(task: str, seed: int, arm: str, shard: int) -> int:
    task_index = spec.TASKS.index(task)
    seed_position = spec.SEEDS.index(seed)
    arm_index = spec.ARMS.index(arm)
    return (
        task_index * len(spec.SEEDS) * len(spec.ARMS) * spec.SHARD_COUNT
        + seed_position * len(spec.ARMS) * spec.SHARD_COUNT
        + arm_index * spec.SHARD_COUNT
        + shard
    )


def read_sha256_manifest(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, filename = line.split(maxsplit=1)
        filename = filename.lstrip("* ")
        values[filename] = digest
    return values


def exact_sign_test(values: np.ndarray) -> dict[str, Any]:
    positive = int(np.count_nonzero(values > 0.0))
    negative = int(np.count_nonzero(values < 0.0))
    ties = int(values.size - positive - negative)
    n = positive + negative
    if n == 0:
        return {
            "positive": positive,
            "negative": negative,
            "ties": ties,
            "one_sided_greater_p": 1.0,
            "two_sided_p": 1.0,
        }
    denominator = 2**n
    one_sided_numerator = sum(math.comb(n, k) for k in range(positive, n + 1))
    lower_numerator = sum(math.comb(n, k) for k in range(0, min(positive, negative) + 1))
    return {
        "positive": positive,
        "negative": negative,
        "ties": ties,
        "one_sided_greater_p": float(one_sided_numerator / denominator),
        "two_sided_p": float(min(1.0, 2.0 * lower_numerator / denominator)),
    }


def bootstrap_primary(
    task_start_values: dict[str, np.ndarray], rng: np.random.Generator
) -> np.ndarray:
    output = np.empty(BOOTSTRAP_REPETITIONS, dtype=np.float64)
    cursor = 0
    chunk_size = 500
    while cursor < BOOTSTRAP_REPETITIONS:
        size = min(chunk_size, BOOTSTRAP_REPETITIONS - cursor)
        task_means = []
        for task in spec.TASKS:
            values = task_start_values[task]
            indices = rng.integers(0, values.size, size=(size, values.size))
            task_means.append(values[indices].mean(axis=1))
        output[cursor : cursor + size] = np.stack(task_means, axis=1).mean(axis=1)
        cursor += size
    return output


def bootstrap_two_way(
    task_seed_start_values: dict[str, np.ndarray], rng: np.random.Generator
) -> np.ndarray:
    output = np.empty(BOOTSTRAP_REPETITIONS, dtype=np.float64)
    cursor = 0
    chunk_size = 250
    while cursor < BOOTSTRAP_REPETITIONS:
        size = min(chunk_size, BOOTSTRAP_REPETITIONS - cursor)
        task_means = []
        seed_indices = rng.integers(
            0, len(spec.SEEDS), size=(size, len(spec.SEEDS))
        )
        for task in spec.TASKS:
            values = task_seed_start_values[task]
            start_indices = rng.integers(0, spec.COUNT, size=(size, spec.COUNT))
            sampled = values[
                seed_indices[:, :, None],
                start_indices[:, None, :],
            ]
            task_means.append(sampled.mean(axis=(1, 2)))
        output[cursor : cursor + size] = np.stack(task_means, axis=1).mean(axis=1)
        cursor += size
    return output


def contrast_record(
    outcomes: dict[str, dict[int, dict[str, np.ndarray]]],
    *,
    control: str,
    primary_rng: np.random.Generator,
    two_way_rng: np.random.Generator,
) -> dict[str, Any]:
    seed_start: dict[str, np.ndarray] = {}
    start_cluster: dict[str, np.ndarray] = {}
    per_task: dict[str, float] = {}
    for task in spec.TASKS:
        values = np.stack(
            [
                outcomes[task][seed][TREATMENT]
                - outcomes[task][seed][control]
                for seed in spec.SEEDS
            ],
            axis=0,
        )
        seed_start[task] = values
        start_cluster[task] = values.mean(axis=0)
        per_task[task] = float(start_cluster[task].mean())
    point = float(np.mean(list(per_task.values())))
    primary = bootstrap_primary(start_cluster, primary_rng)
    two_way = bootstrap_two_way(seed_start, two_way_rng)
    pooled_clusters = np.concatenate([start_cluster[task] for task in spec.TASKS])
    return {
        "treatment": TREATMENT,
        "control": control,
        "equal_task_point_difference": point,
        "per_task_point_difference": per_task,
        "primary_start_cluster_interval": {
            "repetitions": BOOTSTRAP_REPETITIONS,
            "two_sided_95": [
                float(np.quantile(primary, 0.025)),
                float(np.quantile(primary, 0.975)),
            ],
            "one_sided_95_lower": float(np.quantile(primary, 0.05)),
        },
        "secondary_two_way_interval": {
            "repetitions": BOOTSTRAP_REPETITIONS,
            "two_sided_95": [
                float(np.quantile(two_way, 0.025)),
                float(np.quantile(two_way, 0.975)),
            ],
            "one_sided_95_lower": float(np.quantile(two_way, 0.05)),
        },
        "exact_start_cluster_sign_test": exact_sign_test(pooled_clusters),
    }


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=p_values.get)
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for rank, label in enumerate(ordered):
        value = min(1.0, (count - rank) * p_values[label])
        running = max(running, value)
        adjusted[label] = running
    return adjusted


def expected_proposal_identity(arm: str) -> tuple[str | None, str | None, float | None]:
    if arm == "gaussian_select":
        return "gaussian_true", "gaussian", 1.0
    if arm == "vp_shuffled_select":
        return "vp_shuffled_goal", "velocity", spec.GUIDANCE_SCALE
    if arm == "vp_unconditional_select":
        return "vp_true", "velocity", 0.0
    if arm == "vp_true_select":
        return "vp_true", "velocity", spec.GUIDANCE_SCALE
    return None, None, None


def validate_shard_configuration(
    summary: dict[str, Any], *, task: str, seed: int, arm: str, shard: int
) -> None:
    position = spec.seed_index(seed)
    planner_seed = spec.derived_seed(
        "planner", task, spec.PLANNER_BASE_SEEDS[position], shard
    )
    velocity_seed = spec.derived_seed(
        "velocity", task, spec.VELOCITY_BASE_SEEDS[position], shard
    )
    gaussian_seed = spec.derived_seed(
        "gaussian", task, spec.GAUSSIAN_BASE_SEEDS[position], shard
    )
    condition, kind, guidance = expected_proposal_identity(arm)
    selector = arm in spec.PROPOSAL_ARMS
    iterations = 1 if selector else 30
    active_seed = (
        gaussian_seed
        if arm == "gaussian_select"
        else velocity_seed if selector else None
    )
    config = summary.get("resolved_config", {})
    expected_lambda = (
        0.07
        if arm in {"acid", "reachability"}
        else 0.005 if arm == "forward" else None
    )
    if (
        config.get("task") != task
        or config.get("arm") != arm
        or config.get("model_seed") != seed
        or config.get("shard") != shard
        or config.get("planner_seed") != planner_seed
        or config.get("velocity_proposal_seed") != velocity_seed
        or config.get("gaussian_proposal_seed") != gaussian_seed
        or config.get("active_proposal_seed") != active_seed
        or config.get("proposal_condition") != condition
        or config.get("proposal_kind") != kind
        or config.get("guidance_scale") != guidance
        or config.get("reverse_evaluations")
        != (spec.REVERSE_EVALUATIONS if kind == "velocity" else None)
        or config.get("integration")
        != ("pure_one_pool_selector" if selector else "released_cem")
        or config.get("goal_offset") != 25
        or config.get("eval_budget") != 50
        or config.get("horizon") != 5
        or config.get("receding_horizon") != 5
        or config.get("action_block") != 5
        or config.get("cem_samples") != spec.CANDIDATE_COUNT
        or config.get("cem_steps") != iterations
        or config.get("cem_topk") != 30
        or config.get("iterations_per_planning_decision") != iterations
        or config.get("candidate_evaluations_per_planning_decision")
        != iterations * spec.CANDIDATE_COUNT
        or config.get("lambda_weight") != expected_lambda
        or summary.get("iterations_per_planning_decision") != iterations
        or summary.get("candidate_evaluations_per_planning_decision")
        != iterations * spec.CANDIDATE_COUNT
        or int(summary.get("planning_decisions", 0)) <= 0
        or int(summary.get("lewm_cost_calls", 0))
        != int(summary.get("planning_decisions", 0)) * iterations
        or int(summary.get("candidate_evaluations", 0))
        != int(summary.get("planning_decisions", 0))
        * iterations
        * spec.CANDIDATE_COUNT
        or summary.get("world_model_checkpoint_sha256")
        != spec.TASK_SPEC[task]["world_model_sha256"]
    ):
        raise RuntimeError("E11 shard frozen configuration differs")
    scorer = summary.get("scorer")
    proposal = summary.get("proposal")
    if arm in spec.CORE_ARMS:
        if (
            not isinstance(scorer, dict)
            or proposal is not None
            or scorer.get("checkpoint_sha256")
            != spec.CORE_CHECKPOINT_SHA256[task][arm][position]
            or scorer.get("arm") != arm
            or scorer.get("seed") != seed
        ):
            raise RuntimeError("E11 core scorer identity differs")
    elif selector:
        expected_summary, expected_checkpoint = spec.PROPOSAL_ARTIFACT_SHA256[
            task
        ][condition][position]
        if (
            scorer is not None
            or not isinstance(proposal, dict)
            or proposal.get("summary_sha256") != expected_summary
            or proposal.get("checkpoint_sha256") != expected_checkpoint
        ):
            raise RuntimeError("E11 proposal artifact identity differs")
    elif scorer is not None or proposal is not None:
        raise RuntimeError("E11 B0 learned-artifact identity differs")


def validate_exact_manifest(
    *,
    root: Path,
    task: str,
    manifest_path: Path,
    provenance_path: Path,
    expected_starts: dict[int, tuple[int, int]],
    source_manifest_sha256: str,
) -> dict[str, Any]:
    if (
        not manifest_path.is_file()
        or not provenance_path.is_file()
        or manifest_path.stat().st_mode & 0o222
        or provenance_path.stat().st_mode & 0o222
    ):
        raise RuntimeError("E11 D3 manifest is absent or not sealed read-only")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (
        provenance.get("kind") != "gdp_cem_e11_untouched_d3_manifest"
        or provenance.get("task") != task
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256") != source_manifest_sha256
        or provenance.get("manifest_tsv_sha256") != d2.sha256_file(manifest_path)
        or provenance.get("partition_manifest_sha256")
        != d3_manifest.EXPECTED_PARTITION_SHA256[task]
        or {
            label: value.get("sha256")
            for label, value in provenance.get("exclusion_manifests", {}).items()
        }
        != d3_manifest.EXPECTED_EXCLUSION_SHA256[task]
        or provenance.get("selected_exclusion_intersections")
        != {"d1": 0, "d2": 0, "r0": 0}
        or provenance.get("eligible_untouched_p3_episodes")
        != spec.UNTOUCHED_CAPACITY[task]
    ):
        raise RuntimeError("E11 D3 aggregate manifest provenance differs")
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    episodes = [int(row["episode_id"]) for row in rows]
    if (
        len(rows) != spec.COUNT
        or len(set(episodes)) != spec.COUNT
        or [int(row["eval_index"]) for row in rows] != list(range(spec.COUNT))
        or any(
            expected_starts[int(row["eval_index"])]
            != (int(row["episode_id"]), int(row["start_step"]))
            for row in rows
        )
    ):
        raise RuntimeError("E11 D3 aggregate rows are not exact unique episodes")
    partition_path = Path(provenance["partition_manifest"])
    if d2.sha256_file(partition_path) != d3_manifest.EXPECTED_PARTITION_SHA256[task]:
        raise RuntimeError("E11 D3 partition manifest changed")
    partition = d3_manifest.read_partition(partition_path)
    excluded = set()
    for label, value in provenance["exclusion_manifests"].items():
        path = Path(value["path"])
        if d2.sha256_file(path) != d3_manifest.EXPECTED_EXCLUSION_SHA256[task][label]:
            raise RuntimeError("E11 D3 exclusion manifest changed")
        excluded.update(d3_manifest.read_identifier_episodes(path))
    dataset = root / "data/stablewm" / spec.TASK_SPEC[task]["dataset_file"]
    current_stat = dataset.stat()
    current_identity = {
        "size": current_stat.st_size,
        "mtime_ns": current_stat.st_mtime_ns,
        "device": current_stat.st_dev,
        "inode": current_stat.st_ino,
        "mode": current_stat.st_mode,
    }
    if (
        provenance.get("dataset_file_identity") != current_identity
        or provenance.get("dataset_sha256") != spec.TASK_SPEC[task]["dataset_sha256"]
        or current_stat.st_mode & 0o222
    ):
        raise RuntimeError("E11 D3 dataset seal differs")
    with h5py.File(dataset, "r") as handle:
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
    ranked: list[tuple[str, int, int]] = []
    for episode, length in enumerate(lengths.tolist()):
        if partition[episode]["partition"] != "P3" or episode in excluded:
            continue
        candidates = [
            (d3_manifest.selection_hash(task, episode, start), start)
            for start in range(max(0, int(length) - 25))
        ]
        if candidates:
            digest, start = min(candidates)
            ranked.append((digest, episode, start))
    ranked.sort(key=lambda value: (value[0], value[1], value[2]))
    if len(ranked) != spec.UNTOUCHED_CAPACITY[task]:
        raise RuntimeError("E11 D3 untouched capacity changed")
    selected = ranked[: spec.COUNT]
    observed = [
        (row["selection_hash"], int(row["episode_id"]), int(row["start_step"]))
        for row in rows
    ]
    if observed != selected:
        raise RuntimeError("E11 D3 rows differ from exact frozen selection rule")
    return {
        "manifest": str(manifest_path),
        "manifest_sha256": d2.sha256_file(manifest_path),
        "provenance": str(provenance_path),
        "provenance_sha256": d2.sha256_file(provenance_path),
        "unique_episode_count": len(set(episodes)),
        "eligible_untouched_p3_episodes": len(ranked),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evaluation-job-id", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.evaluation_job_id.isdigit():
        raise ValueError("invalid E11 evaluation job ID")
    if d2.sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E11 analyzer protocol hash differs")
    source_manifest_sha256 = d2.sha256_file(args.source_manifest)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E11 analysis output")

    outcomes: dict[str, dict[int, dict[str, np.ndarray]]] = {
        task: {
            seed: {
                arm: np.full(spec.COUNT, np.nan, dtype=np.float64)
                for arm in spec.ARMS
            }
            for seed in spec.SEEDS
        }
        for task in spec.TASKS
    }
    starts_by_task: dict[str, dict[int, tuple[int, int]]] = {
        task: {} for task in spec.TASKS
    }
    shard_records: list[dict[str, Any]] = []
    input_manifest: list[dict[str, Any]] = []
    manifest_identity_by_task: dict[str, tuple[str, str, str, str]] = {}
    all_integrity = True
    for task in spec.TASKS:
        for seed in spec.SEEDS:
            for arm in spec.ARMS:
                for shard in range(spec.SHARD_COUNT):
                    array_index = expected_array_index(task, seed, arm, shard)
                    directory = (
                        args.root
                        / "results/acid-alternative/gdp-cem-e11-d3/closed-loop"
                        / task
                        / arm
                        / f"model-seed-{seed}"
                        / f"shard-{shard}-job-{args.evaluation_job_id}-{array_index}"
                    )
                    summary_path = directory / "summary.json"
                    episode_path = directory / "episodes.tsv"
                    checksum_path = directory / "sha256.txt"
                    for path in (summary_path, episode_path, checksum_path):
                        if not path.is_file():
                            raise FileNotFoundError(path)
                    checksums = read_sha256_manifest(checksum_path)
                    expected_episode_hash = checksums.get(str(episode_path))
                    expected_summary_hash = checksums.get(str(summary_path))
                    if (
                        expected_episode_hash != d2.sha256_file(episode_path)
                        or expected_summary_hash != d2.sha256_file(summary_path)
                    ):
                        raise RuntimeError("E11 shard checksum differs")
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    if (
                        summary.get("status") != "ok"
                        or summary.get("kind")
                        != "gdp_cem_e11_untouched_d3_closed_loop_shard"
                        or summary.get("analysis_role") != "untouched_D3_confirmation"
                        or summary.get("task") != task
                        or summary.get("arm") != arm
                        or summary.get("model_seed") != seed
                        or summary.get("shard") != shard
                        or summary.get("episode_count") != spec.SHARD_SIZE
                        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
                        or summary.get("source_manifest_sha256")
                        != source_manifest_sha256
                        or summary.get("e10m_aggregate_sha256")
                        != spec.E10M_AGGREGATE_SHA256
                        or summary.get("d3_read") is not True
                        or summary.get("d3_outcomes_read_before_full_launch")
                        is not False
                        or summary.get("protected_c1_i1_read") is not False
                        or summary.get("claim_allowed_per_shard") is not False
                        or str(summary.get("runtime", {}).get("slurm_array_task_id"))
                        != str(array_index)
                        or summary.get("runtime", {}).get("gpu")
                        != spec.EXPECTED_GPU_NAME
                        or summary.get("runtime", {}).get("hostname")
                        != spec.EXPECTED_HOSTNAME
                    ):
                        raise RuntimeError("E11 shard summary identity differs")
                    validate_shard_configuration(
                        summary, task=task, seed=seed, arm=arm, shard=shard
                    )
                    manifest_identity = (
                        str(summary.get("eval_manifest", "")),
                        str(summary.get("eval_manifest_sha256", "")),
                        str(summary.get("eval_provenance", "")),
                        str(summary.get("eval_provenance_sha256", "")),
                    )
                    previous_manifest = manifest_identity_by_task.get(task)
                    if previous_manifest is not None and previous_manifest != manifest_identity:
                        raise RuntimeError("E11 task shards do not share one D3 manifest seal")
                    manifest_identity_by_task[task] = manifest_identity
                    with episode_path.open(newline="", encoding="utf-8") as stream:
                        rows = list(csv.DictReader(stream, delimiter="\t"))
                    expected_indices = list(
                        range(shard * spec.SHARD_SIZE, (shard + 1) * spec.SHARD_SIZE)
                    )
                    if (
                        len(rows) != spec.SHARD_SIZE
                        or [int(row["eval_index"]) for row in rows] != expected_indices
                        or any(
                            row["task"] != task
                            or row["arm"] != arm
                            or int(row["model_seed"]) != seed
                            or int(row["shard_index"]) != shard
                            or int(row["success"]) not in (0, 1)
                            for row in rows
                        )
                    ):
                        raise RuntimeError("E11 shard episode rows differ")
                    if int(sum(int(row["success"]) for row in rows)) != int(
                        summary["success_count"]
                    ):
                        raise RuntimeError("E11 shard success count differs")
                    for row in rows:
                        index = int(row["eval_index"])
                        start = (int(row["episode_id"]), int(row["start_step"]))
                        previous = starts_by_task[task].get(index)
                        if previous is not None and previous != start:
                            raise RuntimeError("E11 arms do not share exact starts")
                        starts_by_task[task][index] = start
                        outcomes[task][seed][arm][index] = int(row["success"])
                    proposal_record = summary.get("proposal_diagnostics", {})
                    structural_ok = (
                        math.isfinite(float(summary["elapsed_seconds"]))
                        and float(summary["elapsed_seconds"]) > 0.0
                        and math.isfinite(float(summary["proposal_seconds"]))
                        and float(summary["proposal_seconds"]) >= 0.0
                        and int(summary["planning_decisions"]) > 0
                    )
                    if arm in spec.PROPOSAL_ARMS:
                        before_values = proposal_record.get(
                            "generator_state_before_sha256_values", []
                        )
                        after_values = proposal_record.get(
                            "generator_state_after_sha256_values", []
                        )
                        structural_ok = structural_ok and (
                            proposal_record.get("candidate_counts")
                            == [spec.CANDIDATE_COUNT]
                            and proposal_record.get("mean_coordinate_std_min", 0.0) > 0.0
                            and proposal_record.get("all_finite") is True
                            and isinstance(
                                proposal_record.get(
                                    "generator_state_before_chain_sha256"
                                ),
                                str,
                            )
                            and len(
                                proposal_record[
                                    "generator_state_before_chain_sha256"
                                ]
                            )
                            == 64
                            and len(before_values) == int(summary["planning_decisions"])
                            and len(after_values) == len(before_values)
                            and all(
                                isinstance(value, str)
                                and len(value) == 64
                                and all(character in "0123456789abcdef" for character in value)
                                for value in (*before_values, *after_values)
                            )
                            and hashlib.sha256(
                                "\n".join(before_values).encode("utf-8")
                            ).hexdigest()
                            == proposal_record[
                                "generator_state_before_chain_sha256"
                            ]
                            and hashlib.sha256(
                                "\n".join(after_values).encode("utf-8")
                            ).hexdigest()
                            == proposal_record[
                                "generator_state_after_chain_sha256"
                            ]
                        )
                    all_integrity = all_integrity and structural_ok
                    shard_records.append(
                        {
                            "task": task,
                            "seed": seed,
                            "arm": arm,
                            "shard": shard,
                            "success_count": int(summary["success_count"]),
                            "elapsed_seconds": float(summary["elapsed_seconds"]),
                            "proposal_seconds": float(summary["proposal_seconds"]),
                            "planning_decisions": int(summary["planning_decisions"]),
                            "iterations_per_planning_decision": int(
                                summary["iterations_per_planning_decision"]
                            ),
                            "candidate_evaluations_per_planning_decision": int(
                                summary[
                                    "candidate_evaluations_per_planning_decision"
                                ]
                            ),
                            "lewm_cost_calls": int(summary["lewm_cost_calls"]),
                            "candidate_evaluations": int(
                                summary["candidate_evaluations"]
                            ),
                            "peak_cuda_memory_allocated_bytes": int(
                                summary["runtime"]["peak_cuda_memory_allocated_bytes"]
                            ),
                            "proposal_diagnostics": proposal_record,
                            "resolved_config": summary["resolved_config"],
                            "eval_manifest": summary["eval_manifest"],
                            "eval_manifest_sha256": summary[
                                "eval_manifest_sha256"
                            ],
                            "eval_provenance": summary["eval_provenance"],
                            "eval_provenance_sha256": summary[
                                "eval_provenance_sha256"
                            ],
                            "summary": str(summary_path),
                            "summary_sha256": d2.sha256_file(summary_path),
                        }
                    )
                    input_manifest.append(
                        {
                            "array_index": array_index,
                            "summary": str(summary_path),
                            "summary_sha256": d2.sha256_file(summary_path),
                            "episodes": str(episode_path),
                            "episodes_sha256": d2.sha256_file(episode_path),
                            "checksums": str(checksum_path),
                            "checksums_sha256": d2.sha256_file(checksum_path),
                        }
                    )

    if len(shard_records) != 576 or any(
        len(starts_by_task[task]) != spec.COUNT for task in spec.TASKS
    ):
        raise RuntimeError("E11 aggregate grid is incomplete")
    manifest_seals: dict[str, Any] = {}
    for task in spec.TASKS:
        if len({episode for episode, _ in starts_by_task[task].values()}) != spec.COUNT:
            raise RuntimeError("E11 aggregate does not have 400 distinct episodes")
        manifest_path_text, manifest_hash, provenance_path_text, provenance_hash = (
            manifest_identity_by_task[task]
        )
        manifest_path = Path(manifest_path_text)
        provenance_path = Path(provenance_path_text)
        if (
            d2.sha256_file(manifest_path) != manifest_hash
            or d2.sha256_file(provenance_path) != provenance_hash
        ):
            raise RuntimeError("E11 task manifest seal hash differs")
        manifest_seals[task] = validate_exact_manifest(
            root=args.root,
            task=task,
            manifest_path=manifest_path,
            provenance_path=provenance_path,
            expected_starts=starts_by_task[task],
            source_manifest_sha256=source_manifest_sha256,
        )
    if any(
        not np.isfinite(outcomes[task][seed][arm]).all()
        for task in spec.TASKS
        for seed in spec.SEEDS
        for arm in spec.ARMS
    ):
        raise RuntimeError("E11 aggregate outcome grid contains gaps")

    success_rates: dict[str, Any] = {}
    for task in spec.TASKS:
        success_rates[task] = {}
        for seed in spec.SEEDS:
            success_rates[task][str(seed)] = {
                arm: float(outcomes[task][seed][arm].mean()) for arm in spec.ARMS
            }
    equal_task_rates = {
        arm: float(
            np.mean(
                [
                    outcomes[task][seed][arm].mean()
                    for task in spec.TASKS
                    for seed in spec.SEEDS
                ]
            )
        )
        for arm in spec.ARMS
    }
    equal_seed_rates = {
        str(seed): {
            arm: float(
                np.mean([outcomes[task][seed][arm].mean() for task in spec.TASKS])
            )
            for arm in spec.ARMS
        }
        for seed in spec.SEEDS
    }

    primary_rng = np.random.default_rng(PRIMARY_BOOTSTRAP_SEED)
    two_way_rng = np.random.default_rng(TWO_WAY_BOOTSTRAP_SEED)
    contrasts = {
        control: contrast_record(
            outcomes,
            control=control,
            primary_rng=primary_rng,
            two_way_rng=two_way_rng,
        )
        for control in CONTRAST_ORDER
    }
    secondary_raw_p = {
        control: contrasts[control]["exact_start_cluster_sign_test"]["two_sided_p"]
        for control in SECONDARY_CONTROLS
    }
    secondary_holm = holm_adjust(secondary_raw_p)
    for control in SECONDARY_CONTROLS:
        contrasts[control]["holm_adjusted_two_sided_sign_p"] = secondary_holm[control]

    record_lookup = {
        (record["task"], record["seed"], record["arm"], record["shard"]): record
        for record in shard_records
    }
    noise_stream_integrity: dict[str, Any] = {}
    matched_noise_integrity = True
    for task in spec.TASKS:
        noise_stream_integrity[task] = {}
        for seed in spec.SEEDS:
            noise_stream_integrity[task][str(seed)] = {}
            for shard in range(spec.SHARD_COUNT):
                velocity_sequences = {
                    arm: record_lookup[(task, seed, arm, shard)][
                        "proposal_diagnostics"
                    ]["generator_state_before_sha256_values"]
                    for arm in (
                        "vp_true_select",
                        "vp_shuffled_select",
                        "vp_unconditional_select",
                    )
                }
                velocity_after = {
                    arm: record_lookup[(task, seed, arm, shard)][
                        "proposal_diagnostics"
                    ]["generator_state_after_sha256_values"]
                    for arm in velocity_sequences
                }
                call_counts = {len(values) for values in velocity_sequences.values()}
                common = min(call_counts)
                reference_before = velocity_sequences["vp_true_select"]
                reference_after = velocity_after["vp_true_select"]
                gaussian_sequence = record_lookup[
                    (task, seed, "gaussian_select", shard)
                ]["proposal_diagnostics"]["generator_state_before_sha256_values"]
                passed = (
                    common > 0
                    and len(call_counts) == 1
                    and all(
                        values == reference_before
                        for values in velocity_sequences.values()
                    )
                    and all(
                        values == reference_after
                        for values in velocity_after.values()
                    )
                    and bool(gaussian_sequence)
                    and gaussian_sequence[0] != reference_before[0]
                )
                matched_noise_integrity = matched_noise_integrity and passed
                noise_stream_integrity[task][str(seed)][str(shard)] = {
                    "matched_velocity_call_count": common,
                    "velocity_call_counts": {
                        arm: len(values) for arm, values in velocity_sequences.items()
                    },
                    "gaussian_call_count": len(gaussian_sequence),
                    "matched_complete_velocity_stream": passed,
                }
    all_integrity = all_integrity and matched_noise_integrity

    resource_summary: dict[str, Any] = {}
    for task in spec.TASKS:
        resource_summary[task] = {}
        for seed in spec.SEEDS:
            resource_summary[task][str(seed)] = {}
            for arm in spec.ARMS:
                records = [
                    record
                    for record in shard_records
                    if record["task"] == task
                    and record["seed"] == seed
                    and record["arm"] == arm
                ]
                proposal_records = [
                    record["proposal_diagnostics"] for record in records
                ]
                resource_summary[task][str(seed)][arm] = {
                    "success_rate": float(outcomes[task][seed][arm].mean()),
                    "elapsed_seconds_total": float(
                        sum(record["elapsed_seconds"] for record in records)
                    ),
                    "elapsed_seconds_median_50_episode_shard": float(
                        np.median([record["elapsed_seconds"] for record in records])
                    ),
                    "proposal_seconds_total": float(
                        sum(record["proposal_seconds"] for record in records)
                    ),
                    "planning_decisions": int(
                        sum(record["planning_decisions"] for record in records)
                    ),
                    "lewm_cost_calls": int(
                        sum(record["lewm_cost_calls"] for record in records)
                    ),
                    "candidate_evaluations": int(
                        sum(record["candidate_evaluations"] for record in records)
                    ),
                    "candidate_evaluations_per_planning_decision": sorted(
                        {
                            record[
                                "candidate_evaluations_per_planning_decision"
                            ]
                            for record in records
                        }
                    ),
                    "peak_cuda_memory_allocated_bytes_max": max(
                        record["peak_cuda_memory_allocated_bytes"]
                        for record in records
                    ),
                    "boundary_fraction_max": (
                        max(
                            value["boundary_fraction_max"]
                            for value in proposal_records
                        )
                        if arm in spec.PROPOSAL_ARMS
                        else None
                    ),
                    "mean_coordinate_std_min": (
                        min(
                            value["mean_coordinate_std_min"]
                            for value in proposal_records
                        )
                        if arm in spec.PROPOSAL_ARMS
                        else None
                    ),
                }

    proposal_integrity_by_task_seed: dict[str, Any] = {}
    treatment_integrity = True
    for task in spec.TASKS:
        proposal_integrity_by_task_seed[task] = {}
        for seed in spec.SEEDS:
            records = [
                record
                for record in shard_records
                if record["task"] == task
                and record["seed"] == seed
                and record["arm"] == TREATMENT
            ]
            boundary_max = max(
                record["proposal_diagnostics"]["boundary_fraction_max"]
                for record in records
            )
            diversity_min = min(
                record["proposal_diagnostics"]["mean_coordinate_std_min"]
                for record in records
            )
            finite = all(
                record["proposal_diagnostics"].get("all_finite") is True
                for record in records
            )
            passed = boundary_max < 0.25 and diversity_min > 0.0 and finite
            treatment_integrity = treatment_integrity and passed
            proposal_integrity_by_task_seed[task][str(seed)] = {
                "boundary_fraction_max": boundary_max,
                "mean_coordinate_std_min": diversity_min,
                "all_finite": finite,
                "passed": passed,
            }

    mechanism_points = all(
        contrasts[control]["equal_task_point_difference"] > 0.0
        for control in (
            "gaussian_select",
            "vp_shuffled_select",
            "vp_unconditional_select",
        )
    )
    mechanism_intervals = all(
        contrasts[control]["primary_start_cluster_interval"][
            "one_sided_95_lower"
        ]
        > 0.0
        for control in (
            "gaussian_select",
            "vp_shuffled_select",
            "vp_unconditional_select",
        )
    )
    mechanism_task_wins = sum(
        contrasts["gaussian_select"]["per_task_point_difference"][task] > 0.0
        and contrasts["vp_shuffled_select"]["per_task_point_difference"][task]
        > 0.0
        for task in spec.TASKS
    )
    mechanism_gate = (
        mechanism_points
        and mechanism_intervals
        and mechanism_task_wins >= 2
        and treatment_integrity
        and all_integrity
    )

    acid_contrast = contrasts["acid"]
    acid_task_wins = sum(
        value > 0.0
        for value in acid_contrast["per_task_point_difference"].values()
    )
    acid_no_large_harm = all(
        value >= -0.05
        for value in acid_contrast["per_task_point_difference"].values()
    )
    superiority_gate = (
        mechanism_gate
        and acid_contrast["equal_task_point_difference"] > 0.0
        and acid_contrast["primary_start_cluster_interval"][
            "one_sided_95_lower"
        ]
        > 0.0
        and acid_task_wins >= 2
        and acid_no_large_harm
    )

    paired_time_difference_true_minus_acid: dict[str, Any] = {}
    for task in spec.TASKS:
        differences = [
            record_lookup[(task, seed, TREATMENT, shard)]["elapsed_seconds"]
            - record_lookup[(task, seed, "acid", shard)]["elapsed_seconds"]
            for seed in spec.SEEDS
            for shard in range(spec.SHARD_COUNT)
        ]
        paired_time_difference_true_minus_acid[task] = {
            "values_seconds": differences,
            "median_seconds": float(np.median(differences)),
            "mean_seconds": float(np.mean(differences)),
        }
    faster_each_task = all(
        paired_time_difference_true_minus_acid[task]["median_seconds"] < 0.0
        for task in spec.TASKS
    )
    treatment_per_decision = {
        record["candidate_evaluations_per_planning_decision"]
        for record in shard_records
        if record["arm"] == TREATMENT
    }
    acid_per_decision = {
        record["candidate_evaluations_per_planning_decision"]
        for record in shard_records
        if record["arm"] == "acid"
    }
    if len(treatment_per_decision) != 1 or len(acid_per_decision) != 1:
        raise RuntimeError("E11 per-decision candidate budgets are inconsistent")
    observed_candidate_ratio = next(iter(treatment_per_decision)) / next(
        iter(acid_per_decision)
    )
    total_candidate_ratio = sum(
        record["candidate_evaluations"]
        for record in shard_records
        if record["arm"] == TREATMENT
    ) / sum(
        record["candidate_evaluations"]
        for record in shard_records
        if record["arm"] == "acid"
    )
    efficiency_gate = (
        mechanism_gate
        and not superiority_gate
        and acid_contrast["primary_start_cluster_interval"][
            "one_sided_95_lower"
        ]
        >= -0.03
        and observed_candidate_ratio <= 1.0 / 30.0
        and faster_each_task
    )
    if superiority_gate:
        decision = "suite_conditional_superiority_to_reconstructed_acid"
    elif efficiency_gate:
        decision = "compute_efficient_alternative_to_reconstructed_acid"
    else:
        decision = "no_alternative_to_acid_claim"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    paired_path = args.output_dir / "paired-outcomes.tsv"
    with paired_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("task", "eval_index", "episode_id", "start_step", "seed", *spec.ARMS),
            delimiter="\t",
        )
        writer.writeheader()
        for task in spec.TASKS:
            for eval_index in range(spec.COUNT):
                episode_id, start_step = starts_by_task[task][eval_index]
                for seed in spec.SEEDS:
                    writer.writerow(
                        {
                            "task": task,
                            "eval_index": eval_index,
                            "episode_id": episode_id,
                            "start_step": start_step,
                            "seed": seed,
                            **{
                                arm: int(outcomes[task][seed][arm][eval_index])
                                for arm in spec.ARMS
                            },
                        }
                    )
    input_manifest_path = args.output_dir / "input-manifest.json"
    d3_manifest.atomic_json(input_manifest_path, input_manifest)
    aggregate = {
        "status": "ok",
        "kind": "gdp_cem_e11_untouched_d3_aggregate",
        "analysis_role": "untouched_D3_confirmation",
        "evaluation_job_id": args.evaluation_job_id,
        "task_count": len(spec.TASKS),
        "seed_count": len(spec.SEEDS),
        "arm_count": len(spec.ARMS),
        "starts_per_task": spec.COUNT,
        "episode_evaluations": len(spec.TASKS)
        * len(spec.SEEDS)
        * len(spec.ARMS)
        * spec.COUNT,
        "success_rates": success_rates,
        "equal_task_rates": equal_task_rates,
        "equal_seed_rates": equal_seed_rates,
        "contrasts": contrasts,
        "manifest_seals": manifest_seals,
        "resource_summary": resource_summary,
        "noise_stream_integrity": noise_stream_integrity,
        "proposal_integrity_by_task_seed": proposal_integrity_by_task_seed,
        "paired_time_difference_true_minus_acid": paired_time_difference_true_minus_acid,
        "observed_candidate_evaluation_ratio_true_to_acid_per_decision": observed_candidate_ratio,
        "observed_total_candidate_evaluation_ratio_true_to_acid": total_candidate_ratio,
        "gates": {
            "all_integrity": all_integrity,
            "matched_complete_velocity_noise_streams": matched_noise_integrity,
            "mechanism_equal_task_points": mechanism_points,
            "mechanism_all_three_control_lower_bounds": mechanism_intervals,
            "mechanism_task_wins": mechanism_task_wins,
            "treatment_proposal_integrity": treatment_integrity,
            "diffusion_specific_mechanism": mechanism_gate,
            "acid_positive_equal_task_point": acid_contrast[
                "equal_task_point_difference"
            ]
            > 0.0,
            "acid_positive_one_sided_lower_bound": acid_contrast[
                "primary_start_cluster_interval"
            ]["one_sided_95_lower"]
            > 0.0,
            "acid_task_wins": acid_task_wins,
            "acid_no_task_below_minus_005": acid_no_large_harm,
            "superiority_to_reconstructed_acid": superiority_gate,
            "efficiency_noninferiority_lower_bound": acid_contrast[
                "primary_start_cluster_interval"
            ]["one_sided_95_lower"]
            >= -0.03,
            "faster_on_every_task": faster_each_task,
            "compute_efficient_alternative": efficiency_gate,
        },
        "decision": decision,
        "claim_allowed": superiority_gate or efficiency_gate,
        "official_acid_claim_allowed": False,
        "protocol": str(args.protocol),
        "protocol_sha256": d2.sha256_file(args.protocol),
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_manifest_sha256,
        "input_manifest": str(input_manifest_path),
        "input_manifest_sha256": d2.sha256_file(input_manifest_path),
        "paired_outcomes": str(paired_path),
        "paired_outcomes_sha256": d2.sha256_file(paired_path),
        "bootstrap": {
            "primary_repetitions": BOOTSTRAP_REPETITIONS,
            "primary_seed": PRIMARY_BOOTSTRAP_SEED,
            "two_way_repetitions": BOOTSTRAP_REPETITIONS,
            "two_way_seed": TWO_WAY_BOOTSTRAP_SEED,
            "contrast_order": list(CONTRAST_ORDER),
        },
        "d3_read": True,
        "partial_d3_metrics_read_before_aggregate": False,
        "protected_c1_i1_read": False,
    }
    d3_manifest.atomic_json(args.output_dir / "summary.json", aggregate)
    print(json.dumps(aggregate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
