#!/usr/bin/env python3
"""Apply the frozen E14 Gate-C rules to complete P2 closed-loop results."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

import gdp_cem_e14_specs as spec
from create_gdp_cem_e14_gate_c_manifest import validate_normalization
from evaluate_gdp_cem_e14_gate_c import read_gate_b
from gdp_cem_e14_data import sha256_file


BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 2026082302


def atomic_json(path: Path, value: object) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def read_manifest(path: Path) -> list[dict[str, str]]:
    if b"\r" in path.read_bytes():
        raise RuntimeError("E14 Gate-C manifest contains CR bytes")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        rows = list(reader)
    fields = ["array_id", "task", "arm", "model_seed", "horizon", "shard"]
    if reader.fieldnames != fields or any(
        int(row["array_id"]) != index for index, row in enumerate(rows)
    ):
        raise RuntimeError("E14 Gate-C evaluation manifest differs")
    return rows


def verify_result_directory(directory: Path) -> None:
    checksum = directory / "sha256.txt"
    expected_names = {"episodes.tsv", "planner-diagnostics.jsonl", "summary.json"}
    if not checksum.is_file():
        raise FileNotFoundError(checksum)
    records: dict[str, str] = {}
    for line in checksum.read_text(encoding="utf-8").splitlines():
        digest, filename = line.split(maxsplit=1)
        records[Path(filename.lstrip("* ")).name] = digest
    if set(records) != expected_names or any(
        not (directory / name).is_file()
        or sha256_file(directory / name) != digest
        for name, digest in records.items()
    ):
        raise RuntimeError("E14 Gate-C shard checksum differs")


def paired_bootstrap(
    outcomes: dict[tuple[str, int, int, str, int], int],
    *,
    true_arm: str,
    control_arm: str,
) -> dict[str, Any]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    cells = [(task, horizon) for task in spec.TASKS for horizon in spec.GATE_C_HORIZONS]

    def draw(indices_by_cell: dict[tuple[str, int], np.ndarray]) -> float:
        cell_values = []
        for task, horizon in cells:
            values = []
            for base_index in indices_by_cell[(task, horizon)].tolist():
                values.append(
                    np.mean(
                        [
                            outcomes[(task, horizon, seed, true_arm, base_index)]
                            - outcomes[(task, horizon, seed, control_arm, base_index)]
                            for seed in spec.MODEL_SEEDS
                        ]
                    )
                )
            cell_values.append(float(np.mean(values)))
        return float(np.mean(cell_values))

    identity = {
        cell: np.arange(spec.GATE_C_BASE_STARTS, dtype=np.int64) for cell in cells
    }
    point = draw(identity)
    samples = np.empty(BOOTSTRAP_DRAWS, dtype=np.float64)
    for position in range(BOOTSTRAP_DRAWS):
        samples[position] = draw(
            {
                cell: rng.integers(
                    0,
                    spec.GATE_C_BASE_STARTS,
                    size=spec.GATE_C_BASE_STARTS,
                    dtype=np.int64,
                )
                for cell in cells
            }
        )
    low, high = np.quantile(samples, (0.025, 0.975))
    return {
        "point_difference_fraction": point,
        "ci95_fraction": [float(low), float(high)],
        "draws": BOOTSTRAP_DRAWS,
        "seed": BOOTSTRAP_SEED,
        "resampling_unit": "base_start_with_all_arms_and_model_seeds_paired_within_task_horizon",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--gate-c-manifest", type=Path, required=True)
    parser.add_argument("--gate-c-manifest-sha256", required=True)
    parser.add_argument("--gate-c-provenance", type=Path, required=True)
    parser.add_argument("--gate-c-provenance-sha256", required=True)
    parser.add_argument("--normalized-root", type=Path, required=True)
    parser.add_argument("--normalization-audit", type=Path, required=True)
    parser.add_argument("--normalization-audit-sha256", required=True)
    parser.add_argument("--gate-b-audit", type=Path, required=True)
    parser.add_argument("--gate-b-audit-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--implementation-decisions", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.evaluation_root,
        args.gate_c_manifest,
        args.gate_c_provenance,
        args.normalized_root,
        args.normalization_audit,
        args.gate_b_audit,
        args.protocol,
        args.implementation_decisions,
        args.source_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E14 Gate-C analysis output")
    if (
        sha256_file(args.gate_c_manifest) != args.gate_c_manifest_sha256
        or sha256_file(args.gate_c_provenance) != args.gate_c_provenance_sha256
        or sha256_file(args.protocol) != spec.PROTOCOL_SHA256
    ):
        raise RuntimeError("E14 Gate-C analysis input hash differs")
    source_hash = sha256_file(args.source_manifest)
    gate_b = read_gate_b(args.gate_b_audit, args.gate_b_audit_sha256)
    validate_normalization(
        args.normalization_audit,
        expected_sha256=args.normalization_audit_sha256,
        normalized_root=args.normalized_root,
        source_manifest_sha256=source_hash,
    )
    provenance = json.loads(args.gate_c_provenance.read_text(encoding="utf-8"))
    rows = read_manifest(args.gate_c_manifest)
    expected_arms = ["base_cem", "sage_reconstruction"]
    for endpoint in gate_b["eligible_endpoints"]:
        expected_arms.extend((f"{endpoint}_true", f"{endpoint}_gaussian"))
    if (
        provenance.get("status") != "ok"
        or provenance.get("kind") != "gdp_cem_e14_p2_gate_c_evaluation_manifest"
        or provenance.get("analysis_role")
        != "P2_closed_loop_endpoint_selection_development"
        or provenance.get("eligible_endpoints") != gate_b["eligible_endpoints"]
        or provenance.get("arms") != expected_arms
        or provenance.get("tasks") != list(spec.TASKS)
        or provenance.get("horizons") != list(spec.GATE_C_HORIZONS)
        or provenance.get("model_seeds") != list(spec.MODEL_SEEDS)
        or int(provenance.get("shard_size", -1)) != spec.GATE_C_SHARD_SIZE
        or int(provenance.get("shard_count", -1)) != spec.GATE_C_SHARD_COUNT
        or int(provenance.get("row_count", -1)) != len(rows)
        or provenance.get("gate_b_audit_sha256") != args.gate_b_audit_sha256
        or provenance.get("normalization_audit_sha256")
        != args.normalization_audit_sha256
        or provenance.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or provenance.get("source_manifest_sha256") != source_hash
        or provenance.get("output_tsv_sha256")
        != args.gate_c_manifest_sha256
        or provenance.get("d3_metric_read") is not False
        or provenance.get("d4_metric_read") is not False
        or provenance.get("d5_read") is not False
        or provenance.get("protected_p3_p4_c1_i1_read") is not False
        or provenance.get("claim_allowed") is not False
    ):
        raise RuntimeError("E14 Gate-C manifest provenance differs")

    outcomes: dict[tuple[str, int, int, str, int], int] = {}
    latencies: dict[tuple[str, int, int, str], list[float]] = defaultdict(list)
    artifacts: dict[str, Any] = {}
    start_identity: dict[tuple[str, int], tuple[int, int]] = {}
    p2_hashes: dict[str, set[tuple[str, str]]] = defaultdict(set)
    decisions_sha256 = sha256_file(args.implementation_decisions)
    for row in rows:
        task = row["task"]
        arm = row["arm"]
        seed = int(row["model_seed"])
        horizon = int(row["horizon"])
        shard = int(row["shard"])
        directory = (
            args.evaluation_root
            / task
            / f"horizon-{horizon}"
            / arm
            / f"seed-{seed}"
            / f"shard-{shard}"
        )
        verify_result_directory(directory)
        summary_path = directory / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if (
            summary.get("status") != "ok"
            or summary.get("kind") != "gdp_cem_e14_p2_gate_c_closed_loop_shard"
            or summary.get("analysis_role")
            != "P2_closed_loop_endpoint_selection_development"
            or summary.get("task") != task
            or summary.get("arm") != arm
            or int(summary.get("model_seed", -1)) != seed
            or int(summary.get("horizon", -1)) != horizon
            or int(summary.get("shard", -1)) != shard
            or int(summary.get("episode_count", -1)) != spec.GATE_C_SHARD_SIZE
            or summary.get("gate_b_audit_sha256") != args.gate_b_audit_sha256
            or summary.get("gate_b_eligible_endpoints")
            != gate_b["eligible_endpoints"]
            or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
            or summary.get("implementation_decisions_sha256")
            != decisions_sha256
            or summary.get("source_manifest_sha256") != source_hash
            or summary.get("dataset_sha256")
            != spec.TASK_SPEC[task]["dataset_sha256"]
            or summary.get("world_model_checkpoint_sha256")
            != spec.TASK_SPEC[task]["world_model_sha256"]
            or summary.get("d3_metric_read") is not False
            or summary.get("d4_metric_read") is not False
            or summary.get("d5_read") is not False
            or summary.get("protected_p3_p4_c1_i1_read") is not False
            or summary.get("claim_allowed") is not False
        ):
            raise RuntimeError(f"E14 Gate-C shard identity differs: {summary_path}")
        episodes_path = directory / "episodes.tsv"
        diagnostics_path = directory / "planner-diagnostics.jsonl"
        if (
            summary.get("episodes_tsv_sha256") != sha256_file(episodes_path)
            or summary.get("planner_diagnostics_sha256")
            != sha256_file(diagnostics_path)
        ):
            raise RuntimeError("E14 Gate-C episodes hash differs")
        with episodes_path.open(newline="", encoding="utf-8") as stream:
            episode_rows = list(csv.DictReader(stream, delimiter="\t"))
        if len(episode_rows) != spec.GATE_C_SHARD_SIZE:
            raise RuntimeError("E14 Gate-C episode rows differ")
        for episode in episode_rows:
            base_index = int(episode["base_index"])
            if base_index not in range(spec.GATE_C_BASE_STARTS):
                raise RuntimeError("E14 Gate-C base index differs")
            key = (task, horizon, seed, arm, base_index)
            if key in outcomes:
                raise RuntimeError("duplicate E14 Gate-C outcome")
            if (
                episode["task"] != task
                or episode["arm"] != arm
                or int(episode["model_seed"]) != seed
                or int(episode["horizon"]) != horizon
                or int(episode["shard"]) != shard
                or int(episode["success"]) not in (0, 1)
            ):
                raise RuntimeError("E14 Gate-C episode identity differs")
            identity_key = (task, base_index)
            identity = (int(episode["episode_id"]), int(episode["start_step"]))
            if identity_key in start_identity and start_identity[identity_key] != identity:
                raise RuntimeError("E14 Gate-C shared start differs across arms")
            start_identity[identity_key] = identity
            outcomes[key] = int(episode["success"])
        if (
            int(summary.get("success_count", -1))
            != sum(int(episode["success"]) for episode in episode_rows)
            or not np.isclose(
                float(summary.get("success_rate_fraction", np.nan)),
                np.mean([int(episode["success"]) for episode in episode_rows]),
            )
        ):
            raise RuntimeError("E14 Gate-C shard success summary differs")
        p2_hashes[task].add(
            (
                str(summary.get("p2_queries_sha256")),
                str(summary.get("p2_provenance_sha256")),
            )
        )
        latencies[(task, horizon, seed, arm)].append(
            float(summary["median_planner_seconds_per_context_stage"])
        )
        artifacts["|".join((task, str(horizon), str(seed), arm, str(shard)))] = {
            "summary": str(summary_path),
            "summary_sha256": sha256_file(summary_path),
            "episodes_sha256": sha256_file(episodes_path),
        }

    expected_outcomes = (
        len(spec.TASKS)
        * len(spec.GATE_C_HORIZONS)
        * len(spec.MODEL_SEEDS)
        * len(expected_arms)
        * spec.GATE_C_BASE_STARTS
    )
    if len(outcomes) != expected_outcomes or len(start_identity) != (
        len(spec.TASKS) * spec.GATE_C_BASE_STARTS
    ):
        raise RuntimeError("E14 Gate-C complete outcome cardinality differs")
    if any(len(values) != spec.GATE_C_SHARD_COUNT for values in latencies.values()):
        raise RuntimeError("E14 Gate-C latency shard count differs")
    if any(len(values) != 1 for values in p2_hashes.values()):
        raise RuntimeError("E14 Gate-C P2 manifests differ across arms")

    per_seed: dict[str, Any] = {}
    task_first: dict[str, Any] = {task: {} for task in spec.TASKS}
    overall_success: dict[str, float] = {}
    overall_latency: dict[str, float] = {}
    for arm in expected_arms:
        success_cells = []
        latency_cells = []
        for task in spec.TASKS:
            for horizon in spec.GATE_C_HORIZONS:
                seed_success = []
                seed_latency = []
                for seed in spec.MODEL_SEEDS:
                    successes = [
                        outcomes[(task, horizon, seed, arm, base)]
                        for base in range(spec.GATE_C_BASE_STARTS)
                    ]
                    success = float(np.mean(successes))
                    latency = float(np.mean(latencies[(task, horizon, seed, arm)]))
                    per_seed["|".join((task, str(horizon), str(seed), arm))] = {
                        "success_fraction": success,
                        "median_context_stage_seconds_equal_shard_mean": latency,
                    }
                    seed_success.append(success)
                    seed_latency.append(latency)
                task_first[task].setdefault(str(horizon), {})[arm] = {
                    "success_fraction_equal_seed_mean": float(np.mean(seed_success)),
                    "context_stage_seconds_equal_seed_shard_mean": float(
                        np.mean(seed_latency)
                    ),
                }
                success_cells.append(float(np.mean(seed_success)))
                latency_cells.append(float(np.mean(seed_latency)))
        overall_success[arm] = float(np.mean(success_cells))
        overall_latency[arm] = float(np.mean(latency_cells))

    endpoint_results: dict[str, Any] = {}
    confirmable: list[str] = []
    for endpoint in gate_b["eligible_endpoints"]:
        true_arm = f"{endpoint}_true"
        gaussian_arm = f"{endpoint}_gaussian"
        matched_gain = overall_success[true_arm] - overall_success[gaussian_arm]
        per_cell_gain = {
            f"{task}|{horizon}": (
                task_first[task][str(horizon)][true_arm][
                    "success_fraction_equal_seed_mean"
                ]
                - task_first[task][str(horizon)][gaussian_arm][
                    "success_fraction_equal_seed_mean"
                ]
            )
            for task in spec.TASKS
            for horizon in spec.GATE_C_HORIZONS
        }
        h150_base_gain = {
            task: (
                task_first[task]["150"][true_arm][
                    "success_fraction_equal_seed_mean"
                ]
                - task_first[task]["150"]["base_cem"][
                    "success_fraction_equal_seed_mean"
                ]
            )
            for task in spec.TASKS
        }
        sage_gap = overall_success[true_arm] - overall_success["sage_reconstruction"]
        if overall_latency[true_arm] <= 0.0:
            raise RuntimeError("E14 Gate-C endpoint latency is not positive")
        sage_speedup = overall_latency["sage_reconstruction"] / overall_latency[true_arm]
        gates = {
            "exceeds_matched_gaussian_equal_task_horizon": matched_gain > 0.0,
            "no_task_horizon_loss_worse_than_five_points": min(
                per_cell_gain.values()
            )
            >= -0.05,
            "fifteen_points_above_base_at_h150_one_task": max(
                h150_base_gain.values()
            )
            >= 0.15,
            "within_five_points_of_sage_or_five_times_faster": (
                sage_gap >= -0.05 or sage_speedup >= 5.0
            ),
        }
        passed = all(gates.values())
        if passed:
            confirmable.append(endpoint)
        endpoint_results[endpoint] = {
            "confirmable": passed,
            "gates": gates,
            "overall_true_success_fraction": overall_success[true_arm],
            "overall_gaussian_success_fraction": overall_success[gaussian_arm],
            "matched_gaussian_gain_fraction": matched_gain,
            "per_task_horizon_gaussian_gain_fraction": per_cell_gain,
            "horizon_150_base_gain_fraction": h150_base_gain,
            "sage_success_gap_fraction": sage_gap,
            "sage_stage_latency_speedup": sage_speedup,
            "paired_start_bootstrap": paired_bootstrap(
                outcomes, true_arm=true_arm, control_arm=gaussian_arm
            ),
        }

    selected: str | None = None
    selection_reason: str | None = None
    if len(confirmable) == 1:
        selected = confirmable[0]
        selection_reason = "only_endpoint_passing_all_frozen_gate_c_rules"
    elif len(confirmable) == 2:
        first, second = confirmable
        first_gain = endpoint_results[first]["matched_gaussian_gain_fraction"]
        second_gain = endpoint_results[second]["matched_gaussian_gain_fraction"]
        if abs(first_gain - second_gain) > 0.01:
            selected = first if first_gain > second_gain else second
            selection_reason = "larger_paired_matched_gaussian_gain"
        else:
            selected = min(
                confirmable,
                key=lambda value: overall_latency[f"{value}_true"],
            )
            selection_reason = "gain_tie_within_one_point_lower_stage_latency"
    decision = (
        "authorize_separately_frozen_d5_confirmation_protocol"
        if selected is not None
        else "stop_before_d5_no_endpoint_passed_gate_c"
    )
    result = {
        "status": "ok",
        "kind": "gdp_cem_e14_p2_gate_c_analysis",
        "analysis_role": "P2_closed_loop_endpoint_selection_development",
        "decision": decision,
        "selected_endpoint": selected,
        "selection_reason": selection_reason,
        "confirmable_endpoints": confirmable,
        "task_first": task_first,
        "overall_equal_task_horizon_success_fraction": overall_success,
        "overall_equal_task_horizon_context_stage_seconds": overall_latency,
        "endpoint_results": endpoint_results,
        "per_seed": per_seed,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "gate_c_manifest": str(args.gate_c_manifest),
        "gate_c_manifest_sha256": args.gate_c_manifest_sha256,
        "gate_c_provenance_sha256": args.gate_c_provenance_sha256,
        "normalization_audit_sha256": args.normalization_audit_sha256,
        "gate_b_audit_sha256": args.gate_b_audit_sha256,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "implementation_decisions_sha256": decisions_sha256,
        "source_manifest_sha256": source_hash,
        "bootstrap": {
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
            "resampling_unit": "base_start_with_all_arms_and_model_seeds_paired_within_task_horizon",
        },
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output_dir / "GATE-C-AUDIT.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
