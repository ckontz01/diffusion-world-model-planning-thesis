#!/usr/bin/env python3
"""Synthetic full-grid regression test for E11 aggregation and claim gates."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import analyze_gdp_cem_e11_d3 as analyze
import gdp_cem_e11_specs as spec


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def successes(arm: str) -> list[int]:
    counts = {
        "vp_true_select": 48,
        "gaussian_select": 40,
        "vp_shuffled_select": 39,
        "vp_unconditional_select": 38,
        "acid": 40,
        "b0": 39,
        "reachability": 38,
        "forward": 37,
    }
    return [int(index < counts[arm]) for index in range(spec.SHARD_SIZE)]


def main() -> None:
    analyze.BOOTSTRAP_REPETITIONS = 2_000
    with tempfile.TemporaryDirectory(prefix="gdp-e11-test-") as temporary:
        root = Path(temporary)
        protocol = root / "protocol.md"
        source_manifest = root / "SOURCE-MANIFEST.sha256"
        # The aggregate checks the frozen protocol hash. Use the real frozen
        # protocol contents while keeping all synthetic outputs isolated.
        real_protocol = Path(__file__).with_name(
            "ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md"
        )
        protocol.write_bytes(real_protocol.read_bytes())
        source_manifest.write_text("synthetic source manifest\n", encoding="utf-8")
        source_hash = sha(source_manifest)
        evaluation_job_id = "999001"
        manifest_paths = {}
        for task_index, task in enumerate(spec.TASKS):
            manifest_path = root / "synthetic-manifests" / task / "d3.tsv"
            provenance_path = root / "synthetic-manifests" / task / "provenance.json"
            manifest_path.parent.mkdir(parents=True)
            with manifest_path.open("x", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=("eval_index", "episode_id", "start_step"),
                    delimiter="\t",
                )
                writer.writeheader()
                for eval_index in range(spec.COUNT):
                    writer.writerow(
                        {
                            "eval_index": eval_index,
                            "episode_id": task_index * 10_000 + eval_index,
                            "start_step": eval_index % 17,
                        }
                    )
            write_json(provenance_path, {"synthetic": True})
            manifest_paths[task] = (manifest_path, provenance_path)
        original_manifest_validator = analyze.validate_exact_manifest
        analyze.validate_exact_manifest = lambda **kwargs: {
            "manifest": str(kwargs["manifest_path"]),
            "manifest_sha256": sha(kwargs["manifest_path"]),
            "provenance": str(kwargs["provenance_path"]),
            "provenance_sha256": sha(kwargs["provenance_path"]),
            "unique_episode_count": spec.COUNT,
            "eligible_untouched_p3_episodes": spec.COUNT,
        }
        for task_index, task in enumerate(spec.TASKS):
            for seed in spec.SEEDS:
                for arm in spec.ARMS:
                    for shard in range(spec.SHARD_COUNT):
                        array_index = analyze.expected_array_index(task, seed, arm, shard)
                        directory = (
                            root
                            / "results/acid-alternative/gdp-cem-e11-d3/closed-loop"
                            / task
                            / arm
                            / f"model-seed-{seed}"
                            / f"shard-{shard}-job-{evaluation_job_id}-{array_index}"
                        )
                        directory.mkdir(parents=True)
                        episode_path = directory / "episodes.tsv"
                        values = successes(arm)
                        with episode_path.open("x", newline="", encoding="utf-8") as stream:
                            writer = csv.DictWriter(
                                stream,
                                fieldnames=(
                                    "eval_index",
                                    "shard_index",
                                    "episode_id",
                                    "start_step",
                                    "task",
                                    "model_seed",
                                    "planner_seed",
                                    "arm",
                                    "success",
                                ),
                                delimiter="\t",
                            )
                            writer.writeheader()
                            for local_index, success in enumerate(values):
                                eval_index = shard * spec.SHARD_SIZE + local_index
                                writer.writerow(
                                    {
                                        "eval_index": eval_index,
                                        "shard_index": shard,
                                        "episode_id": task_index * 10_000 + eval_index,
                                        "start_step": eval_index % 17,
                                        "task": task,
                                        "model_seed": seed,
                                        "planner_seed": 1,
                                        "arm": arm,
                                        "success": success,
                                    }
                                )
                        selector = arm in spec.PROPOSAL_ARMS
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
                        condition, kind, guidance = analyze.expected_proposal_identity(arm)
                        iterations = 1 if selector else 30
                        planning_decisions = 10
                        cost_calls = planning_decisions * iterations
                        if selector:
                            state_namespace = "gaussian" if arm == "gaussian_select" else "velocity"
                            before_values = [
                                hashlib.sha256(
                                    f"{state_namespace}|{task}|{seed}|{shard}|{index}".encode()
                                ).hexdigest()
                                for index in range(planning_decisions)
                            ]
                            after_values = [
                                hashlib.sha256(
                                    f"{state_namespace}|after|{task}|{seed}|{shard}|{index}".encode()
                                ).hexdigest()
                                for index in range(planning_decisions)
                            ]
                            proposal_diagnostics = {
                                "candidate_counts": [spec.CANDIDATE_COUNT],
                                "boundary_fraction_max": 0.10,
                                "mean_coordinate_std_min": 0.25,
                                "all_finite": True,
                                "generator_state_before_chain_sha256": hashlib.sha256(
                                    "\n".join(before_values).encode()
                                ).hexdigest(),
                                "generator_state_after_chain_sha256": hashlib.sha256(
                                    "\n".join(after_values).encode()
                                ).hexdigest(),
                                "generator_state_before_sha256_values": before_values,
                                "generator_state_after_sha256_values": after_values,
                            }
                        else:
                            proposal_diagnostics = {
                                "boundary_fraction_max": None,
                                "mean_coordinate_std_min": None,
                            }
                        active_seed = (
                            gaussian_seed
                            if arm == "gaussian_select"
                            else velocity_seed if selector else None
                        )
                        expected_lambda = (
                            0.07
                            if arm in {"acid", "reachability"}
                            else 0.005 if arm == "forward" else None
                        )
                        resolved_config = {
                            "task": task,
                            "arm": arm,
                            "model_seed": seed,
                            "shard": shard,
                            "planner_seed": planner_seed,
                            "velocity_proposal_seed": velocity_seed,
                            "gaussian_proposal_seed": gaussian_seed,
                            "active_proposal_seed": active_seed,
                            "proposal_condition": condition,
                            "proposal_kind": kind,
                            "guidance_scale": guidance,
                            "reverse_evaluations": (
                                spec.REVERSE_EVALUATIONS if kind == "velocity" else None
                            ),
                            "integration": (
                                "pure_one_pool_selector" if selector else "released_cem"
                            ),
                            "goal_offset": 25,
                            "eval_budget": 50,
                            "horizon": 5,
                            "receding_horizon": 5,
                            "action_block": 5,
                            "cem_samples": spec.CANDIDATE_COUNT,
                            "cem_steps": iterations,
                            "cem_topk": 30,
                            "iterations_per_planning_decision": iterations,
                            "candidate_evaluations_per_planning_decision": (
                                iterations * spec.CANDIDATE_COUNT
                            ),
                            "lambda_weight": expected_lambda,
                        }
                        scorer_record = None
                        proposal_record = None
                        if arm in spec.CORE_ARMS:
                            scorer_record = {
                                "checkpoint_sha256": spec.CORE_CHECKPOINT_SHA256[task][arm][position],
                                "arm": arm,
                                "seed": seed,
                            }
                        elif selector:
                            expected_summary, expected_checkpoint = spec.PROPOSAL_ARTIFACT_SHA256[
                                task
                            ][condition][position]
                            proposal_record = {
                                "summary_sha256": expected_summary,
                                "checkpoint_sha256": expected_checkpoint,
                            }
                        manifest_path, provenance_path = manifest_paths[task]
                        summary_path = directory / "summary.json"
                        write_json(
                            summary_path,
                            {
                                "status": "ok",
                                "kind": "gdp_cem_e11_untouched_d3_closed_loop_shard",
                                "analysis_role": "untouched_D3_confirmation",
                                "task": task,
                                "arm": arm,
                                "model_seed": seed,
                                "shard": shard,
                                "episode_count": spec.SHARD_SIZE,
                                "success_count": sum(values),
                                "elapsed_seconds": 1.0 if arm == "vp_true_select" else 2.0,
                                "proposal_seconds": 0.1 if selector else 0.0,
                                "planning_decisions": planning_decisions,
                                "iterations_per_planning_decision": iterations,
                                "candidate_evaluations_per_planning_decision": (
                                    iterations * spec.CANDIDATE_COUNT
                                ),
                                "lewm_cost_calls": cost_calls,
                                "candidate_evaluations": cost_calls * spec.CANDIDATE_COUNT,
                                "proposal_diagnostics": proposal_diagnostics,
                                "resolved_config": resolved_config,
                                "scorer": scorer_record,
                                "proposal": proposal_record,
                                "world_model_checkpoint_sha256": spec.TASK_SPEC[task][
                                    "world_model_sha256"
                                ],
                                "eval_manifest": str(manifest_path),
                                "eval_manifest_sha256": sha(manifest_path),
                                "eval_provenance": str(provenance_path),
                                "eval_provenance_sha256": sha(provenance_path),
                                "protocol_sha256": spec.PROTOCOL_SHA256,
                                "source_manifest_sha256": source_hash,
                                "e10m_aggregate_sha256": spec.E10M_AGGREGATE_SHA256,
                                "d3_read": True,
                                "d3_outcomes_read_before_full_launch": False,
                                "protected_c1_i1_read": False,
                                "claim_allowed_per_shard": False,
                                "runtime": {
                                    "peak_cuda_memory_allocated_bytes": 1_000_000,
                                    "slurm_array_task_id": str(array_index),
                                    "gpu": spec.EXPECTED_GPU_NAME,
                                    "hostname": spec.EXPECTED_HOSTNAME,
                                },
                            },
                        )
                        checksum_path = directory / "sha256.txt"
                        checksum_path.write_text(
                            f"{sha(summary_path)}  {summary_path}\n"
                            f"{sha(episode_path)}  {episode_path}\n",
                            encoding="utf-8",
                        )
        output = root / "analysis"
        previous = sys.argv
        try:
            sys.argv = [
                "analyze_gdp_cem_e11_d3.py",
                "--root",
                str(root),
                "--evaluation-job-id",
                evaluation_job_id,
                "--protocol",
                str(protocol),
                "--source-manifest",
                str(source_manifest),
                "--output-dir",
                str(output),
            ]
            analyze.main()
        finally:
            sys.argv = previous
            analyze.validate_exact_manifest = original_manifest_validator
        result = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        if (
            result["episode_evaluations"] != 28_800
            or result["gates"]["diffusion_specific_mechanism"] is not True
            or result["gates"]["superiority_to_reconstructed_acid"] is not True
            or result["decision"]
            != "suite_conditional_superiority_to_reconstructed_acid"
            or result["official_acid_claim_allowed"] is not False
        ):
            raise RuntimeError("E11 synthetic aggregate gate regression failed")

    if set(
        analyze.expected_array_index(task, seed, arm, shard)
        for task in spec.TASKS
        for seed in spec.SEEDS
        for arm in spec.ARMS
        for shard in range(spec.SHARD_COUNT)
    ) != set(range(576)):
        raise RuntimeError("E11 array-index mapping is not a 0..575 bijection")
    derived = {
        spec.derived_seed(namespace, task, base_seed, shard)
        for namespace, seeds in (
            ("planner", spec.PLANNER_BASE_SEEDS),
            ("velocity", spec.VELOCITY_BASE_SEEDS),
            ("gaussian", spec.GAUSSIAN_BASE_SEEDS),
        )
        for task in spec.TASKS
        for base_seed in seeds
        for shard in range(spec.SHARD_COUNT)
    }
    if len(derived) != 3 * 3 * 3 * spec.SHARD_COUNT:
        raise RuntimeError("E11 derived seed namespaces collide")
    print("E11 synthetic aggregate tests: ok")


if __name__ == "__main__":
    main()
