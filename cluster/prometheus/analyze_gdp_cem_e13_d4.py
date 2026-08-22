#!/usr/bin/env python3
"""Aggregate the complete frozen E13 D4 grid and apply prespecified gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_d2_models as d2
import create_gdp_cem_e13_d4_manifest as d4_manifest
import gdp_cem_e13_specs as spec


TREATMENT = "vp_select_k300"
PRIMARY_CONTROL = "prism_dp_select_k300"
MECHANISM_CONTROL = "latent_gaussian_select_k300"
K16_TREATMENT = "vp_select_k16"
K16_CONTROL = "prism_dp_select_k16"
CONTRASTS = (
    (TREATMENT, PRIMARY_CONTROL),
    (TREATMENT, MECHANISM_CONTROL),
    (K16_TREATMENT, K16_CONTROL),
)
EXPECTED_HASHED_FILES = {
    "summary.json",
    "episodes.tsv",
    "resolved-config.json",
    "solver-diagnostics.jsonl",
    "proposal-diagnostics.jsonl",
    "audit.txt",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_array_index(task: str, seed: int, arm: str, shard: int) -> int:
    return (
        spec.TASKS.index(task) * len(spec.SEEDS) * len(spec.ARMS) * spec.SHARD_COUNT
        + spec.SEEDS.index(seed) * len(spec.ARMS) * spec.SHARD_COUNT
        + spec.ARMS.index(arm) * spec.SHARD_COUNT
        + shard
    )


def read_sha256_manifest(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, filename = line.split(maxsplit=1)
        name = Path(filename.lstrip("* ")).name
        if name in values:
            raise RuntimeError(f"duplicate E13 hash-manifest entry: {name}")
        values[name] = digest
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
    one_sided = sum(math.comb(n, k) for k in range(positive, n + 1))
    tail = sum(math.comb(n, k) for k in range(min(positive, negative) + 1))
    return {
        "positive": positive,
        "negative": negative,
        "ties": ties,
        "one_sided_greater_p": float(one_sided / denominator),
        "two_sided_p": float(min(1.0, 2.0 * tail / denominator)),
    }


def bootstrap_primary(
    values: dict[str, np.ndarray], rng: np.random.Generator
) -> np.ndarray:
    output = np.empty(spec.BOOTSTRAP_REPETITIONS, dtype=np.float64)
    cursor = 0
    while cursor < len(output):
        size = min(500, len(output) - cursor)
        task_means = []
        for task in spec.TASKS:
            task_values = values[task]
            indices = rng.integers(0, task_values.size, size=(size, task_values.size))
            task_means.append(task_values[indices].mean(axis=1))
        output[cursor : cursor + size] = np.stack(task_means, axis=1).mean(axis=1)
        cursor += size
    return output


def bootstrap_two_way(
    values: dict[str, np.ndarray], rng: np.random.Generator
) -> np.ndarray:
    output = np.empty(spec.BOOTSTRAP_REPETITIONS, dtype=np.float64)
    cursor = 0
    while cursor < len(output):
        size = min(250, len(output) - cursor)
        seed_positions = rng.integers(
            0, len(spec.SEEDS), size=(size, len(spec.SEEDS))
        )
        task_means = []
        for task in spec.TASKS:
            task_values = values[task]
            starts = rng.integers(0, spec.COUNT, size=(size, spec.COUNT))
            sampled = task_values[seed_positions[:, :, None], starts[:, None, :]]
            task_means.append(sampled.mean(axis=(1, 2)))
        output[cursor : cursor + size] = np.stack(task_means, axis=1).mean(axis=1)
        cursor += size
    return output


def contrast_record(
    outcomes: dict[str, dict[int, dict[str, np.ndarray]]],
    *,
    treatment: str,
    control: str,
) -> dict[str, Any]:
    seed_start: dict[str, np.ndarray] = {}
    start_clusters: dict[str, np.ndarray] = {}
    per_task: dict[str, float] = {}
    discordance: dict[str, dict[str, int]] = {}
    seed_discordance: dict[str, dict[str, dict[str, int]]] = {}
    for task in spec.TASKS:
        values = np.stack(
            [
                outcomes[task][seed][treatment]
                - outcomes[task][seed][control]
                for seed in spec.SEEDS
            ]
        )
        seed_start[task] = values
        start_clusters[task] = values.mean(axis=0)
        per_task[task] = float(start_clusters[task].mean())
        discordance[task] = {
            "treatment_only_success": int(np.count_nonzero(values > 0.0)),
            "control_only_success": int(np.count_nonzero(values < 0.0)),
            "ties": int(np.count_nonzero(values == 0.0)),
        }
        seed_discordance[task] = {
            str(seed): {
                "treatment_only_success": int(np.count_nonzero(values[index] > 0.0)),
                "control_only_success": int(np.count_nonzero(values[index] < 0.0)),
                "ties": int(np.count_nonzero(values[index] == 0.0)),
            }
            for index, seed in enumerate(spec.SEEDS)
        }
    primary = bootstrap_primary(
        start_clusters,
        np.random.default_rng(spec.PRIMARY_BOOTSTRAP_SEED),
    )
    secondary = bootstrap_two_way(
        seed_start,
        np.random.default_rng(spec.TWO_WAY_BOOTSTRAP_SEED),
    )
    pooled = np.concatenate([start_clusters[task] for task in spec.TASKS])
    return {
        "treatment": treatment,
        "control": control,
        "equal_task_point_difference": float(np.mean(list(per_task.values()))),
        "per_task_point_difference": per_task,
        "paired_seed_episode_discordance": discordance,
        "paired_discordance_by_task_seed": seed_discordance,
        "primary_start_cluster_interval": {
            "repetitions": spec.BOOTSTRAP_REPETITIONS,
            "two_sided_95": [
                float(np.quantile(primary, 0.025)),
                float(np.quantile(primary, 0.975)),
            ],
            "one_sided_95_lower": float(np.quantile(primary, 0.05)),
        },
        "secondary_two_way_interval": {
            "repetitions": spec.BOOTSTRAP_REPETITIONS,
            "two_sided_95": [
                float(np.quantile(secondary, 0.025)),
                float(np.quantile(secondary, 0.975)),
            ],
            "one_sided_95_lower": float(np.quantile(secondary, 0.05)),
        },
        "exact_start_cluster_sign_test": exact_sign_test(pooled),
    }


def expected_proposal_identity(arm: str) -> tuple[str, str, float | None, int]:
    if arm == MECHANISM_CONTROL:
        return "gaussian_true", "gaussian", 1.0, 0
    if arm.startswith("vp_select"):
        return "vp_true", "velocity", 1.5, 5
    if arm.startswith("prism_dp_select"):
        return "h25_pixels", "prism_dp_reconstruction", None, 10
    raise ValueError(f"unknown E13 arm: {arm}")


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
    dp_seed = spec.derived_seed(
        "prism_dp", task, spec.PRISM_DP_BASE_SEEDS[position], shard
    )
    condition, kind, guidance, reverse_evaluations = expected_proposal_identity(arm)
    active_seed = (
        gaussian_seed
        if kind == "gaussian"
        else velocity_seed if kind == "velocity" else dp_seed
    )
    candidate_count = spec.CANDIDATE_COUNT[arm]
    config = summary.get("resolved_config", {})
    if (
        config.get("mode") != "d4"
        or config.get("task") != task
        or config.get("arm") != arm
        or config.get("model_seed") != seed
        or config.get("shard") != shard
        or config.get("planner_seed") != planner_seed
        or config.get("velocity_proposal_seed") != velocity_seed
        or config.get("gaussian_proposal_seed") != gaussian_seed
        or config.get("prism_dp_proposal_seed") != dp_seed
        or config.get("active_proposal_seed") != active_seed
        or config.get("proposal_condition") != condition
        or config.get("proposal_kind") != kind
        or config.get("guidance_scale") != guidance
        or config.get("reverse_evaluations") != (reverse_evaluations or None)
        or config.get("integration") != "pure_one_pool_selector"
        or config.get("goal_offset") != 25
        or config.get("eval_budget") != 50
        or config.get("horizon") != 5
        or config.get("receding_horizon") != 5
        or config.get("action_block") != 5
        or config.get("candidate_count") != candidate_count
        or config.get("optimizer_steps") != 1
        or config.get("topk") != min(30, candidate_count)
        or config.get("iterations_per_planning_decision") != 1
        or config.get("candidate_evaluations_per_planning_decision") != candidate_count
        or config.get("requires_second_image_encoder")
        != (kind == "prism_dp_reconstruction")
        or int(config.get("active_learned_parameter_count", 0)) <= 0
        or int(config.get("world_model_parameter_count", 0)) <= 0
        or int(config.get("total_inference_parameter_count", 0))
        != int(config.get("world_model_parameter_count", 0))
        + int(config.get("active_learned_parameter_count", 0))
        or summary.get("iterations_per_planning_decision") != 1
        or summary.get("candidate_evaluations_per_planning_decision")
        != candidate_count
        or int(summary.get("planning_decisions", 0)) <= 0
        or int(summary.get("lewm_cost_calls", 0))
        != int(summary.get("planning_decisions", -1))
        or int(summary.get("candidate_evaluations", 0))
        != int(summary.get("lewm_cost_calls", -1)) * candidate_count
    ):
        raise RuntimeError(f"E13 shard configuration differs: {task}/{seed}/{arm}/{shard}")

    proposal = summary.get("proposal")
    if not isinstance(proposal, dict):
        raise RuntimeError("E13 proposal artifact record is absent")
    if kind == "prism_dp_reconstruction":
        expected_summary, expected_checkpoint = spec.PRISM_DP_ARTIFACT_SHA256[task][seed]
        support = proposal.get("support_e11_velocity_artifact", {})
        expected_support = spec.PROPOSAL_ARTIFACT_SHA256[task]["vp_true"][position]
        if (
            proposal.get("method") != "prism_dp_reconstruction"
            or proposal.get("reconstruction_not_official") is not True
            or proposal.get("summary_sha256") != expected_summary
            or proposal.get("checkpoint_sha256") != expected_checkpoint
            or support.get("checkpoint_sha256") != expected_support[1]
        ):
            raise RuntimeError("E13 PRISM-DP artifact identity differs")
    else:
        expected_summary, expected_checkpoint = spec.PROPOSAL_ARTIFACT_SHA256[task][
            condition
        ][position]
        if (
            proposal.get("checkpoint_sha256") != expected_checkpoint
            or d2.sha256_file(Path(proposal["summary"])) != expected_summary
        ):
            raise RuntimeError("E13 E11 proposal artifact identity differs")

    diagnostics = summary.get("proposal_diagnostics", {})
    if (
        diagnostics.get("candidate_counts") != [candidate_count]
        or diagnostics.get("all_finite") is not True
        or int(diagnostics.get("call_count", 0))
        != int(summary.get("planning_decisions", -1))
        or float(diagnostics.get("mean_coordinate_std_min", 0.0)) <= 0.0
        or not math.isfinite(float(diagnostics.get("boundary_fraction_max", math.nan)))
        or not math.isfinite(
            float(diagnostics.get("robust_clip_fraction_max", math.nan))
        )
    ):
        raise RuntimeError("E13 proposal diagnostics differ")


def d4_manifest_rows(
    path: Path, provenance_path: Path, *, task: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (
        len(rows) != spec.COUNT
        or [int(row["eval_index"]) for row in rows] != list(range(spec.COUNT))
        or len({int(row["episode_id"]) for row in rows}) != spec.COUNT
        or provenance.get("status") != "ok"
        or provenance.get("kind") != "gdp_cem_e13_untouched_d4_manifest"
        or provenance.get("task") != task
        or provenance.get("count") != spec.COUNT
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("manifest_tsv_sha256") != sha256_file(path)
        or provenance.get("selection_namespace") != spec.SELECTION_NAMESPACE
        or provenance.get("selection_seed") != spec.SELECTION_SEED
        or provenance.get("selected_exclusion_intersections")
        != {"d1": 0, "d2": 0, "d3": 0, "r0": 0}
        or provenance.get("d3_outcomes_read") is not False
        or provenance.get("d4_outcomes_read") is not False
        or provenance.get("protected_p4_c1_i1_paths_read") is not False
        or any(
            int(row["shard_index"]) != int(row["eval_index"]) // spec.SHARD_SIZE
            or int(row["dataset_goal_step"]) != int(row["start_step"]) + 24
            or row["selection_hash"]
            != d4_manifest.selection_hash(
                task, int(row["episode_id"]), int(row["start_step"])
            )
            for row in rows
        )
    ):
        raise RuntimeError(f"invalid E13 D4 manifest for {task}")
    return rows, provenance


def validate_manifest(
    root: Path, *, task: str, manifest_job_id: str, source_manifest: Path
) -> tuple[list[dict[str, str]], dict[str, Any], Path, Path]:
    directory = root / "manifests/gdp-cem-e13-d4" / task / f"job-{manifest_job_id}"
    path = directory / "d4-untouched.tsv"
    provenance_path = directory / "provenance.json"
    rows, provenance = d4_manifest_rows(path, provenance_path, task=task)
    if provenance.get("source_manifest_sha256") != sha256_file(source_manifest):
        raise RuntimeError("E13 manifest source hash differs")
    return rows, provenance, path, provenance_path


def locate_shard(
    root: Path,
    *,
    evaluation_job_id: str,
    task: str,
    seed: int,
    arm: str,
    shard: int,
) -> Path:
    index = expected_array_index(task, seed, arm, shard)
    return (
        root
        / "results/acid-alternative/gdp-cem-e13-d4/closed-loop"
        / task
        / arm
        / f"model-seed-{seed}"
        / f"shard-{shard}-job-{evaluation_job_id}-{index}"
    )


def integrity_pass(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for directory in paths:
        if not directory.is_dir():
            raise FileNotFoundError(directory)
        hash_path = directory / "sha256.txt"
        if not hash_path.is_file():
            raise FileNotFoundError(hash_path)
        declared = read_sha256_manifest(hash_path)
        if set(declared) != EXPECTED_HASHED_FILES:
            raise RuntimeError(f"E13 shard hash file set differs: {directory}")
        observed = {}
        for name in sorted(EXPECTED_HASHED_FILES):
            path = directory / name
            if not path.is_file():
                raise FileNotFoundError(path)
            observed[name] = sha256_file(path)
            if observed[name] != declared[name]:
                raise RuntimeError(f"E13 shard hash differs: {path}")
        records.append(
            {
                "directory": str(directory),
                "sha256_manifest": str(hash_path),
                "sha256_manifest_sha256": sha256_file(hash_path),
                "files": observed,
            }
        )
    return records


def proposal_integrity(
    records: dict[tuple[str, int, str, int], dict[str, Any]], arm: str
) -> dict[str, dict[str, dict[str, float | bool]]]:
    output: dict[str, dict[str, dict[str, float | bool]]] = {}
    for task in spec.TASKS:
        output[task] = {}
        for seed in spec.SEEDS:
            cells = [
                records[(task, seed, arm, shard)]
                for shard in range(spec.SHARD_COUNT)
            ]
            boundary = max(
                float(cell["proposal_diagnostics"]["boundary_fraction_max"])
                for cell in cells
            )
            diversity = min(
                float(cell["proposal_diagnostics"]["mean_coordinate_std_min"])
                for cell in cells
            )
            robust_clip = max(
                float(cell["proposal_diagnostics"]["robust_clip_fraction_max"])
                for cell in cells
            )
            output[task][str(seed)] = {
                "all_finite": all(
                    cell["proposal_diagnostics"]["all_finite"] is True
                    for cell in cells
                ),
                "boundary_fraction_max": boundary,
                "robust_clip_fraction_max": robust_clip,
                "mean_coordinate_std_min": diversity,
                "passed_finite_non_degenerate": diversity > 0.0,
            }
    return output


def operational_summary(
    records: dict[tuple[str, int, str, int], dict[str, Any]],
    outcomes: dict[str, dict[int, dict[str, np.ndarray]]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Task/seed/arm accounting required by the frozen reporting protocol."""
    output: dict[str, dict[str, dict[str, Any]]] = {}
    for task in spec.TASKS:
        output[task] = {}
        for seed in spec.SEEDS:
            output[task][str(seed)] = {}
            for arm in spec.ARMS:
                cells = [records[(task, seed, arm, shard)] for shard in range(spec.SHARD_COUNT)]
                elapsed = sum(float(cell["elapsed_seconds"]) for cell in cells)
                proposal_seconds = sum(float(cell["proposal_seconds"]) for cell in cells)
                episodes = sum(int(cell["episode_count"]) for cell in cells)
                proposal = cells[0]["proposal"]
                artifact_summary_sha = proposal.get("summary_sha256")
                if artifact_summary_sha is None:
                    artifact_summary_sha = d2.sha256_file(Path(proposal["summary"]))
                support_checkpoint_sha = None
                if arm.startswith("prism_dp_select"):
                    support_checkpoint_sha = proposal[
                        "support_e11_velocity_artifact"
                    ]["checkpoint_sha256"]
                parameters = {
                    int(cell["active_learned_parameter_count"]) for cell in cells
                }
                total_parameters = {
                    int(cell["total_inference_parameter_count"]) for cell in cells
                }
                second_encoder = {
                    bool(cell["requires_second_image_encoder"]) for cell in cells
                }
                if len(parameters) != 1 or len(total_parameters) != 1 or len(second_encoder) != 1:
                    raise RuntimeError(
                        f"E13 operational identity varies: {task}/{seed}/{arm}"
                    )
                output[task][str(seed)][arm] = {
                    "success_count": int(outcomes[task][seed][arm].sum()),
                    "episode_count": episodes,
                    "success_rate": float(outcomes[task][seed][arm].mean()),
                    "closed_loop_elapsed_seconds": elapsed,
                    "closed_loop_seconds_per_episode": elapsed / episodes,
                    "proposal_generation_seconds": proposal_seconds,
                    "proposal_seconds_per_episode": proposal_seconds / episodes,
                    "lewm_cost_calls": sum(int(cell["lewm_cost_calls"]) for cell in cells),
                    "planning_decisions": sum(int(cell["planning_decisions"]) for cell in cells),
                    "candidate_evaluations": sum(int(cell["candidate_evaluations"]) for cell in cells),
                    "active_learned_parameter_count": next(iter(parameters)),
                    "total_inference_parameter_count": next(iter(total_parameters)),
                    "requires_second_image_encoder": next(iter(second_encoder)),
                    "peak_cuda_memory_allocated_bytes": max(
                        int(cell["runtime"]["peak_cuda_memory_allocated_bytes"])
                        for cell in cells
                    ),
                    "proposal_boundary_fraction_max": max(
                        float(cell["proposal_diagnostics"]["boundary_fraction_max"])
                        for cell in cells
                    ),
                    "proposal_robust_clip_fraction_max": max(
                        float(cell["proposal_diagnostics"]["robust_clip_fraction_max"])
                        for cell in cells
                    ),
                    "proposal_mean_coordinate_std_min": min(
                        float(cell["proposal_diagnostics"]["mean_coordinate_std_min"])
                        for cell in cells
                    ),
                    "proposal_all_finite": all(
                        cell["proposal_diagnostics"]["all_finite"] is True
                        for cell in cells
                    ),
                    "artifact_summary_sha256": artifact_summary_sha,
                    "artifact_checkpoint_sha256": proposal["checkpoint_sha256"],
                    "support_e11_velocity_checkpoint_sha256": support_checkpoint_sha,
                    "protocol_sha256": cells[0]["protocol_sha256"],
                    "source_manifest_sha256": cells[0]["source_manifest_sha256"],
                    "eval_manifest_sha256": cells[0]["eval_manifest_sha256"],
                    "hardware": {
                        "gpu": cells[0]["runtime"]["gpu"],
                        "hostname": cells[0]["runtime"]["hostname"],
                    },
                }
    return output


def block_timing(
    records: dict[tuple[str, int, str, int], dict[str, Any]],
    *,
    treatment: str,
    control: str,
) -> dict[str, Any]:
    per_task: dict[str, Any] = {}
    all_lower = True
    for task in spec.TASKS:
        differences = []
        ratios = []
        for seed in spec.SEEDS:
            for shard in range(spec.SHARD_COUNT):
                first = records[(task, seed, treatment, shard)]
                second = records[(task, seed, control, shard)]
                first_time = float(first["elapsed_seconds"]) / int(
                    first["episode_count"]
                )
                second_time = float(second["elapsed_seconds"]) / int(
                    second["episode_count"]
                )
                differences.append(first_time - second_time)
                ratios.append(first_time / second_time)
        median_difference = float(np.median(differences))
        per_task[task] = {
            "matched_block_count": len(differences),
            "median_seconds_per_episode_difference": median_difference,
            "median_seconds_per_episode_ratio": float(np.median(ratios)),
        }
        all_lower = all_lower and median_difference < 0.0
    return {"per_task": per_task, "treatment_lower_on_every_task": all_lower}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evaluation-job-id", required=True)
    parser.add_argument("--manifest-job-id", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E13 analyzer protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E13 analysis output")

    manifest_rows: dict[str, list[dict[str, str]]] = {}
    manifest_inputs: dict[str, Any] = {}
    for task in spec.TASKS:
        rows, provenance, path, provenance_path = validate_manifest(
            args.root,
            task=task,
            manifest_job_id=args.manifest_job_id,
            source_manifest=args.source_manifest,
        )
        manifest_rows[task] = rows
        manifest_inputs[task] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "provenance": str(provenance_path),
            "provenance_sha256": sha256_file(provenance_path),
            "dataset_sha256": provenance["dataset_sha256"],
        }

    grid = [
        (task, seed, arm, shard)
        for task in spec.TASKS
        for seed in spec.SEEDS
        for arm in spec.ARMS
        for shard in range(spec.SHARD_COUNT)
    ]
    indices = {expected_array_index(*cell) for cell in grid}
    if len(grid) != 360 or indices != set(range(360)):
        raise RuntimeError("E13 array grid is not a 360-cell bijection")
    directories = [
        locate_shard(
            args.root,
            evaluation_job_id=args.evaluation_job_id,
            task=task,
            seed=seed,
            arm=arm,
            shard=shard,
        )
        for task, seed, arm, shard in grid
    ]

    # This is the information barrier: verify existence and byte hashes for
    # all 360 cells before deserializing any metric-bearing file.
    integrity_records = integrity_pass(directories)

    source_sha256 = sha256_file(args.source_manifest)
    protocol_sha256 = sha256_file(args.protocol)
    summaries: dict[tuple[str, int, str, int], dict[str, Any]] = {}
    outcome_chunks: dict[tuple[str, int, str, int], np.ndarray] = {}
    for (task, seed, arm, shard), directory in zip(grid, directories):
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        audit = dict(
            line.split("=", 1)
            for line in (directory / "audit.txt").read_text(encoding="utf-8").splitlines()
        )
        expected_index = expected_array_index(task, seed, arm, shard)
        if (
            summary.get("status") != "ok"
            or summary.get("kind") != "gdp_cem_e13_untouched_d4_closed_loop_shard"
            or summary.get("analysis_role") != "untouched_D4_confirmation"
            or summary.get("task") != task
            or summary.get("arm") != arm
            or summary.get("model_seed") != seed
            or summary.get("shard") != shard
            or summary.get("episode_count") != spec.SHARD_SIZE
            or summary.get("eval_index_start") != shard * spec.SHARD_SIZE
            or summary.get("eval_index_stop") != (shard + 1) * spec.SHARD_SIZE
            or summary.get("protocol_sha256") != protocol_sha256
            or summary.get("source_manifest_sha256") != source_sha256
            or summary.get("e12_stage_b_audit_sha256")
            != spec.E12_STAGE_B_AUDIT_SHA256
            or summary.get("e12_training_source_manifest_sha256")
            != spec.E12_TRAINING_SOURCE_MANIFEST_SHA256
            or summary.get("e10m_aggregate_sha256") != spec.E10M_AGGREGATE_SHA256
            or summary.get("eval_manifest_sha256") != manifest_inputs[task]["sha256"]
            or summary.get("eval_provenance_sha256")
            != manifest_inputs[task]["provenance_sha256"]
            or summary.get("manifest_dataset_sha256")
            != spec.TASK_SPEC[task]["dataset_sha256"]
            or summary.get("world_model_checkpoint_sha256")
            != spec.TASK_SPEC[task]["world_model_sha256"]
            or summary.get("d3_outcomes_read") is not False
            or summary.get("d4_read") is not True
            or summary.get("d4_outcomes_read_before_full_launch") is not False
            or summary.get("protected_p4_c1_i1_read") is not False
            or summary.get("claim_allowed_per_shard") is not False
            or summary.get("runtime", {}).get("gpu") != spec.EXPECTED_GPU_NAME
            or summary.get("runtime", {}).get("hostname") != spec.EXPECTED_HOSTNAME
            or str(summary.get("runtime", {}).get("slurm_array_job_id"))
            != str(args.evaluation_job_id)
            or int(summary.get("runtime", {}).get("slurm_array_task_id", -1))
            != expected_index
            or audit
            != {
                "study": "gdp_cem_e13_d4",
                "task": task,
                "arm": arm,
                "model_seed": str(seed),
                "shard": str(shard),
                "job_id": str(args.evaluation_job_id),
                "array_task_id": str(expected_index),
                "d4_read": "true",
                "partial_metrics_inspected": "false",
                "protected_p4_c1_i1_read": "false",
            }
        ):
            raise RuntimeError(
                f"E13 shard provenance differs: {task}/{seed}/{arm}/{shard}"
            )
        validate_shard_configuration(
            summary, task=task, seed=seed, arm=arm, shard=shard
        )

        with (directory / "episodes.tsv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        expected_rows = manifest_rows[task][
            shard * spec.SHARD_SIZE : (shard + 1) * spec.SHARD_SIZE
        ]
        if (
            len(rows) != spec.SHARD_SIZE
            or [int(row["eval_index"]) for row in rows]
            != [int(row["eval_index"]) for row in expected_rows]
            or any(
                int(row["episode_id"]) != int(expected["episode_id"])
                or int(row["start_step"]) != int(expected["start_step"])
                or row["task"] != task
                or int(row["model_seed"]) != seed
                or row["arm"] != arm
                or int(row["success"]) not in (0, 1)
                for row, expected in zip(rows, expected_rows)
            )
        ):
            raise RuntimeError(
                f"E13 episode rows differ: {task}/{seed}/{arm}/{shard}"
            )
        successes = np.asarray(
            [int(row["success"]) for row in rows], dtype=np.float64
        )
        if (
            int(successes.sum()) != summary.get("success_count")
            or not math.isclose(
                float(successes.mean()),
                float(summary.get("success_rate_fraction", math.nan)),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise RuntimeError("E13 shard success summary differs")
        summaries[(task, seed, arm, shard)] = summary
        outcome_chunks[(task, seed, arm, shard)] = successes

    outcomes: dict[str, dict[int, dict[str, np.ndarray]]] = {
        task: {seed: {} for seed in spec.SEEDS} for task in spec.TASKS
    }
    for task in spec.TASKS:
        for seed in spec.SEEDS:
            for arm in spec.ARMS:
                values = np.concatenate(
                    [
                        outcome_chunks[(task, seed, arm, shard)]
                        for shard in range(spec.SHARD_COUNT)
                    ]
                )
                if values.shape != (spec.COUNT,) or not np.isfinite(values).all():
                    raise RuntimeError("E13 aggregate outcome grid contains gaps")
                outcomes[task][seed][arm] = values

    success_by_task_seed = {
        task: {
            str(seed): {
                arm: float(outcomes[task][seed][arm].mean()) for arm in spec.ARMS
            }
            for seed in spec.SEEDS
        }
        for task in spec.TASKS
    }
    success_count_by_task_seed = {
        task: {
            str(seed): {
                arm: int(outcomes[task][seed][arm].sum()) for arm in spec.ARMS
            }
            for seed in spec.SEEDS
        }
        for task in spec.TASKS
    }
    success_by_task = {
        task: {
            arm: float(
                np.mean([outcomes[task][seed][arm].mean() for seed in spec.SEEDS])
            )
            for arm in spec.ARMS
        }
        for task in spec.TASKS
    }
    equal_task_success = {
        arm: float(np.mean([success_by_task[task][arm] for task in spec.TASKS]))
        for arm in spec.ARMS
    }

    contrasts = {
        f"{treatment}_minus_{control}": contrast_record(
            outcomes, treatment=treatment, control=control
        )
        for treatment, control in CONTRASTS
    }
    primary = contrasts[f"{TREATMENT}_minus_{PRIMARY_CONTROL}"]
    mechanism = contrasts[f"{TREATMENT}_minus_{MECHANISM_CONTROL}"]
    k16 = contrasts[f"{K16_TREATMENT}_minus_{K16_CONTROL}"]
    integrity = {arm: proposal_integrity(summaries, arm) for arm in spec.ARMS}
    operations = operational_summary(summaries, outcomes)
    primary_integrity = all(
        bool(integrity[arm][task][str(seed)]["passed_finite_non_degenerate"])
        and bool(integrity[arm][task][str(seed)]["all_finite"])
        for arm in (TREATMENT, PRIMARY_CONTROL)
        for task in spec.TASKS
        for seed in spec.SEEDS
    )
    mechanism_integrity = all(
        bool(integrity[arm][task][str(seed)]["passed_finite_non_degenerate"])
        and bool(integrity[arm][task][str(seed)]["all_finite"])
        and float(integrity[arm][task][str(seed)]["boundary_fraction_max"]) < 0.25
        for arm in (TREATMENT, MECHANISM_CONTROL)
        for task in spec.TASKS
        for seed in spec.SEEDS
    )
    primary_gate = (
        primary["equal_task_point_difference"] > 0.0
        and primary["primary_start_cluster_interval"]["one_sided_95_lower"] > 0.0
        and sum(value > 0.0 for value in primary["per_task_point_difference"].values())
        >= 2
        and min(primary["per_task_point_difference"].values()) >= -0.05
        and primary_integrity
    )
    mechanism_gate = (
        mechanism["equal_task_point_difference"] > 0.0
        and mechanism["primary_start_cluster_interval"]["one_sided_95_lower"]
        > 0.0
        and sum(
            value > 0.0 for value in mechanism["per_task_point_difference"].values()
        )
        >= 2
        and min(mechanism["per_task_point_difference"].values()) >= -0.05
        and mechanism_integrity
    )

    timing = block_timing(summaries, treatment=TREATMENT, control=PRIMARY_CONTROL)
    treatment_params = {
        int(
            summaries[(task, seed, TREATMENT, shard)][
                "active_learned_parameter_count"
            ]
        )
        for task in spec.TASKS
        for seed in spec.SEEDS
        for shard in range(spec.SHARD_COUNT)
    }
    control_params = {
        int(
            summaries[(task, seed, PRIMARY_CONTROL, shard)][
                "active_learned_parameter_count"
            ]
        )
        for task in spec.TASKS
        for seed in spec.SEEDS
        for shard in range(spec.SHARD_COUNT)
    }
    treatment_memory = max(
        int(
            summaries[(task, seed, TREATMENT, shard)]["runtime"][
                "peak_cuda_memory_allocated_bytes"
            ]
        )
        for task in spec.TASKS
        for seed in spec.SEEDS
        for shard in range(spec.SHARD_COUNT)
    )
    control_memory = max(
        int(
            summaries[(task, seed, PRIMARY_CONTROL, shard)]["runtime"][
                "peak_cuda_memory_allocated_bytes"
            ]
        )
        for task in spec.TASKS
        for seed in spec.SEEDS
        for shard in range(spec.SHARD_COUNT)
    )
    resource_advantage = {
        "fewer_active_learned_parameters": max(treatment_params)
        < min(control_params),
        "no_second_image_encoder": all(
            summaries[(task, seed, TREATMENT, shard)][
                "requires_second_image_encoder"
            ]
            is False
            and summaries[(task, seed, PRIMARY_CONTROL, shard)][
                "requires_second_image_encoder"
            ]
            is True
            for task in spec.TASKS
            for seed in spec.SEEDS
            for shard in range(spec.SHARD_COUNT)
        ),
        "lower_peak_cuda_memory": treatment_memory < control_memory,
        "treatment_active_parameter_counts": sorted(treatment_params),
        "control_active_parameter_counts": sorted(control_params),
        "treatment_peak_cuda_memory_bytes": treatment_memory,
        "control_peak_cuda_memory_bytes": control_memory,
    }
    efficiency_gate = (
        not primary_gate
        and primary["primary_start_cluster_interval"]["one_sided_95_lower"] >= -0.03
        and timing["treatment_lower_on_every_task"]
        and any(
            resource_advantage[name]
            for name in (
                "fewer_active_learned_parameters",
                "no_second_image_encoder",
                "lower_peak_cuda_memory",
            )
        )
    )
    if primary_gate:
        decision = "superior_to_disclosed_prism_dp_reconstruction"
    elif efficiency_gate:
        decision = (
            "compute_efficient_alternative_to_disclosed_prism_dp_reconstruction"
        )
    else:
        decision = "primary_prism_dp_claim_not_supported"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    paired_path = args.output_dir / "paired-outcomes.tsv"
    with paired_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "task",
                "eval_index",
                "episode_id",
                "start_step",
                "seed",
                *spec.ARMS,
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for task in spec.TASKS:
            for seed in spec.SEEDS:
                for index, manifest_row in enumerate(manifest_rows[task]):
                    writer.writerow(
                        {
                            "task": task,
                            "eval_index": index,
                            "episode_id": manifest_row["episode_id"],
                            "start_step": manifest_row["start_step"],
                            "seed": seed,
                            **{
                                arm: int(outcomes[task][seed][arm][index])
                                for arm in spec.ARMS
                            },
                        }
                    )

    input_manifest = {
        "status": "ok",
        "kind": "gdp_cem_e13_complete_input_manifest",
        "evaluation_job_id": str(args.evaluation_job_id),
        "manifest_job_id": str(args.manifest_job_id),
        "expected_shards": 360,
        "verified_shards": len(integrity_records),
        "protocol_sha256": protocol_sha256,
        "source_manifest_sha256": source_sha256,
        "manifests": manifest_inputs,
        "shards": integrity_records,
        "all_shards_complete_before_metric_read": True,
    }
    d4_manifest.atomic_json(args.output_dir / "input-manifest.json", input_manifest)
    aggregate = {
        "status": "ok",
        "kind": "gdp_cem_e13_untouched_d4_aggregate",
        "analysis_role": "untouched_D4_confirmation",
        "decision": decision,
        "task_count": len(spec.TASKS),
        "model_seed_count": len(spec.SEEDS),
        "arm_count": len(spec.ARMS),
        "starts_per_task": spec.COUNT,
        "episode_count": (
            len(spec.TASKS) * len(spec.SEEDS) * len(spec.ARMS) * spec.COUNT
        ),
        "shard_count": len(grid),
        "success_by_task_seed": success_by_task_seed,
        "success_count_by_task_seed": success_count_by_task_seed,
        "success_by_task": success_by_task,
        "equal_task_success": equal_task_success,
        "contrasts": contrasts,
        "operational_by_task_seed_arm": operations,
        "proposal_integrity": integrity,
        "timing": timing,
        "resource_advantage": resource_advantage,
        "gates": {
            "primary_superiority_to_disclosed_prism_dp_reconstruction": primary_gate,
            "secondary_diffusion_mechanism_replication": mechanism_gate,
            "compute_efficient_alternative": efficiency_gate,
            "k16_is_secondary_only": True,
            "k16_point_difference": k16["equal_task_point_difference"],
        },
        "claim_allowed": primary_gate or efficiency_gate,
        "claim_scope": (
            "disclosed_prism_dp_reconstruction_only_not_official_prism"
            if primary_gate or efficiency_gate
            else "none"
        ),
        "protocol": str(args.protocol),
        "protocol_sha256": protocol_sha256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_sha256,
        "input_manifest": str(args.output_dir / "input-manifest.json"),
        "input_manifest_sha256": sha256_file(
            args.output_dir / "input-manifest.json"
        ),
        "paired_outcomes": str(paired_path),
        "paired_outcomes_sha256": sha256_file(paired_path),
        "inference": {
            "primary_unit": (
                "task-stratified paired start cluster after averaging fixed seeds"
            ),
            "primary_repetitions": spec.BOOTSTRAP_REPETITIONS,
            "primary_seed": spec.PRIMARY_BOOTSTRAP_SEED,
            "secondary_unit": "paired two-way seed-block and start resampling",
            "secondary_repetitions": spec.BOOTSTRAP_REPETITIONS,
            "secondary_seed": spec.TWO_WAY_BOOTSTRAP_SEED,
            "episodes_bootstrapped_independently": False,
        },
        "all_shards_complete_before_metric_read": True,
        "partial_d4_metrics_read_before_aggregate": False,
        "d3_outcomes_read": False,
        "d4_outcomes_read": True,
        "protected_p4_c1_i1_read": False,
    }
    d4_manifest.atomic_json(args.output_dir / "summary.json", aggregate)
    print(json.dumps(aggregate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
