#!/usr/bin/env python3
"""Synthetic full-grid tests for the frozen E13 D4 analyzer."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import analyze_gdp_cem_e13_d4 as analyze
import create_gdp_cem_e13_d4_manifest as create
import gdp_cem_e13_specs as spec


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def success(arm: str, index: int) -> int:
    thresholds = {
        "latent_gaussian_select_k300": 8,
        "vp_select_k300": 9,
        "prism_dp_select_k300": 7,
        "vp_select_k16": 6,
        "prism_dp_select_k16": 5,
    }
    return int(index % 10 < thresholds[arm])


def make_manifest(root: Path, task: str, source_sha: str) -> tuple[Path, Path]:
    directory = root / "manifests/gdp-cem-e13-d4" / task / "job-888"
    directory.mkdir(parents=True)
    path = directory / "d4-untouched.tsv"
    fields = (
        "eval_index",
        "shard_index",
        "episode_id",
        "start_step",
        "dataset_goal_step",
        "declared_goal_offset",
        "source_global_row",
        "goal_global_row",
        "selection_hash",
    )
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for index in range(spec.COUNT):
            episode = 1000 + index
            start = index % 5
            writer.writerow(
                {
                    "eval_index": index,
                    "shard_index": index // spec.SHARD_SIZE,
                    "episode_id": episode,
                    "start_step": start,
                    "dataset_goal_step": start + 24,
                    "declared_goal_offset": 25,
                    "source_global_row": episode * 100 + start,
                    "goal_global_row": episode * 100 + start + 24,
                    "selection_hash": create.selection_hash(task, episode, start),
                }
            )
    provenance_path = directory / "provenance.json"
    write_json(
        provenance_path,
        {
            "status": "ok",
            "kind": "gdp_cem_e13_untouched_d4_manifest",
            "task": task,
            "count": spec.COUNT,
            "protocol_sha256": spec.PROTOCOL_SHA256,
            "manifest_tsv_sha256": sha(path),
            "selection_namespace": spec.SELECTION_NAMESPACE,
            "selection_seed": spec.SELECTION_SEED,
            "selected_exclusion_intersections": {
                "d1": 0,
                "d2": 0,
                "d3": 0,
                "r0": 0,
            },
            "source_manifest_sha256": source_sha,
            "dataset_sha256": spec.TASK_SPEC[task]["dataset_sha256"],
            "d3_outcomes_read": False,
            "d4_outcomes_read": False,
            "protected_p4_c1_i1_paths_read": False,
        },
    )
    return path, provenance_path


def make_shard(
    root: Path,
    *,
    task: str,
    seed: int,
    arm: str,
    shard: int,
    protocol: Path,
    source: Path,
    manifest: Path,
    provenance: Path,
) -> None:
    index = analyze.expected_array_index(task, seed, arm, shard)
    directory = analyze.locate_shard(
        root,
        evaluation_job_id="999",
        task=task,
        seed=seed,
        arm=arm,
        shard=shard,
    )
    directory.mkdir(parents=True)
    first = shard * spec.SHARD_SIZE
    values = [success(arm, item) for item in range(first, first + spec.SHARD_SIZE)]
    summary = {
        "status": "ok",
        "kind": "gdp_cem_e13_untouched_d4_closed_loop_shard",
        "analysis_role": "untouched_D4_confirmation",
        "task": task,
        "arm": arm,
        "model_seed": seed,
        "shard": shard,
        "episode_count": spec.SHARD_SIZE,
        "eval_index_start": first,
        "eval_index_stop": first + spec.SHARD_SIZE,
        "success_count": sum(values),
        "success_rate_fraction": sum(values) / spec.SHARD_SIZE,
        "elapsed_seconds": 25.0 if arm == "vp_select_k300" else 50.0,
        "proposal_seconds": 5.0 if arm.startswith("vp_") else 10.0,
        "lewm_cost_calls": 100,
        "planning_decisions": 100,
        "candidate_evaluations": 100 * spec.CANDIDATE_COUNT[arm],
        "active_learned_parameter_count": (
            10_000 if arm.startswith("vp_") else 20_000
        ),
        "total_inference_parameter_count": (
            110_000 if arm.startswith("vp_") else 120_000
        ),
        "requires_second_image_encoder": arm.startswith("prism_dp_"),
        "proposal": {
            "summary_sha256": f"summary-{task}-{seed}-{arm}",
            "checkpoint_sha256": f"checkpoint-{task}-{seed}-{arm}",
            **(
                {
                    "support_e11_velocity_artifact": {
                        "checkpoint_sha256": f"support-{task}-{seed}"
                    }
                }
                if arm.startswith("prism_dp_")
                else {}
            ),
        },
        "proposal_diagnostics": {
            "all_finite": True,
            "boundary_fraction_max": 0.01,
            "robust_clip_fraction_max": 0.01,
            "mean_coordinate_std_min": 0.2,
        },
        "protocol_sha256": sha(protocol),
        "source_manifest_sha256": sha(source),
        "e12_stage_b_audit_sha256": spec.E12_STAGE_B_AUDIT_SHA256,
        "e12_training_source_manifest_sha256": (
            spec.E12_TRAINING_SOURCE_MANIFEST_SHA256
        ),
        "e10m_aggregate_sha256": spec.E10M_AGGREGATE_SHA256,
        "eval_manifest_sha256": sha(manifest),
        "eval_provenance_sha256": sha(provenance),
        "manifest_dataset_sha256": spec.TASK_SPEC[task]["dataset_sha256"],
        "world_model_checkpoint_sha256": spec.TASK_SPEC[task][
            "world_model_sha256"
        ],
        "d3_outcomes_read": False,
        "d4_read": True,
        "d4_outcomes_read_before_full_launch": False,
        "protected_p4_c1_i1_read": False,
        "claim_allowed_per_shard": False,
        "runtime": {
            "gpu": spec.EXPECTED_GPU_NAME,
            "hostname": spec.EXPECTED_HOSTNAME,
            "slurm_array_job_id": "999",
            "slurm_array_task_id": str(index),
            "peak_cuda_memory_allocated_bytes": (
                1_000 if arm == "vp_select_k300" else 2_000
            ),
        },
    }
    write_json(directory / "summary.json", summary)
    (directory / "resolved-config.json").write_text("{}\n", encoding="utf-8")
    (directory / "solver-diagnostics.jsonl").write_text("{}\n", encoding="utf-8")
    (directory / "proposal-diagnostics.jsonl").write_text("{}\n", encoding="utf-8")
    with (directory / "episodes.tsv").open("x", newline="", encoding="utf-8") as stream:
        fields = (
            "eval_index",
            "episode_id",
            "start_step",
            "task",
            "model_seed",
            "arm",
            "success",
        )
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for offset, value in enumerate(values):
            eval_index = first + offset
            writer.writerow(
                {
                    "eval_index": eval_index,
                    "episode_id": 1000 + eval_index,
                    "start_step": eval_index % 5,
                    "task": task,
                    "model_seed": seed,
                    "arm": arm,
                    "success": value,
                }
            )
    (directory / "audit.txt").write_text(
        "\n".join(
            (
                "study=gdp_cem_e13_d4",
                f"task={task}",
                f"arm={arm}",
                f"model_seed={seed}",
                f"shard={shard}",
                "job_id=999",
                f"array_task_id={index}",
                "d4_read=true",
                "partial_metrics_inspected=false",
                "protected_p4_c1_i1_read=false",
                "",
            )
        ),
        encoding="utf-8",
    )
    with (directory / "sha256.txt").open("x", encoding="utf-8") as stream:
        for name in sorted(analyze.EXPECTED_HASHED_FILES):
            stream.write(f"{sha(directory / name)}  {name}\n")


def main() -> None:
    indices = {
        analyze.expected_array_index(task, seed, arm, shard)
        for task in spec.TASKS
        for seed in spec.SEEDS
        for arm in spec.ARMS
        for shard in range(spec.SHARD_COUNT)
    }
    if indices != set(range(360)):
        raise RuntimeError("E13 synthetic array mapping failed")
    with tempfile.TemporaryDirectory(prefix="e13-analysis-test-") as temporary:
        root = Path(temporary)
        protocol = Path(__file__).with_name(
            "ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md"
        )
        source = root / "SOURCE-MANIFEST.sha256"
        source.write_text("synthetic\n", encoding="utf-8")
        manifests = {
            task: make_manifest(root, task, sha(source)) for task in spec.TASKS
        }
        for task in spec.TASKS:
            for seed in spec.SEEDS:
                for arm in spec.ARMS:
                    for shard in range(spec.SHARD_COUNT):
                        make_shard(
                            root,
                            task=task,
                            seed=seed,
                            arm=arm,
                            shard=shard,
                            protocol=protocol,
                            source=source,
                            manifest=manifests[task][0],
                            provenance=manifests[task][1],
                        )
        output = root / "analysis"
        previous_argv = sys.argv
        previous_repetitions = spec.BOOTSTRAP_REPETITIONS
        previous_validator = analyze.validate_shard_configuration
        try:
            spec.BOOTSTRAP_REPETITIONS = 200
            analyze.validate_shard_configuration = lambda *args, **kwargs: None
            sys.argv = [
                "analyze_gdp_cem_e13_d4.py",
                "--root",
                str(root),
                "--evaluation-job-id",
                "999",
                "--manifest-job-id",
                "888",
                "--protocol",
                str(protocol),
                "--source-manifest",
                str(source),
                "--output-dir",
                str(output),
            ]
            analyze.main()
        finally:
            sys.argv = previous_argv
            spec.BOOTSTRAP_REPETITIONS = previous_repetitions
            analyze.validate_shard_configuration = previous_validator
        result = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        if (
            result["shard_count"] != 360
            or result["episode_count"] != 18_000
            or result["gates"][
                "primary_superiority_to_disclosed_prism_dp_reconstruction"
            ]
            is not True
            or result["gates"]["secondary_diffusion_mechanism_replication"]
            is not True
            or result["all_shards_complete_before_metric_read"] is not True
        ):
            raise RuntimeError("E13 synthetic full-grid aggregate failed")
    print("E13 synthetic analyzer tests: ok")


if __name__ == "__main__":
    main()
