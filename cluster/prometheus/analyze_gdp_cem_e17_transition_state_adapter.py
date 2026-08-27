#!/usr/bin/env python3
"""Verify and aggregate the frozen E17 adapter preflight task first."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import gdp_cem_e17_specs as spec
from gdp_cem_e15_data import sha256_file


def atomic_json(path: Path, value: Any) -> None:
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


def checksum_records(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        result[name.lstrip("*")] = digest
    return result


def verify_cache(directory: Path, *, task: str, source_sha: str) -> dict[str, Any]:
    h5_path = directory / "cache.h5"
    manifest_path = directory / "manifest.json"
    checksum_path = directory / "sha256.txt"
    if not all(path.is_file() for path in (h5_path, manifest_path, checksum_path)):
        raise FileNotFoundError(f"incomplete E17 cache: {directory}")
    if checksum_records(checksum_path) != {
        "cache.h5": sha256_file(h5_path),
        "manifest.json": sha256_file(manifest_path),
    }:
        raise RuntimeError(f"invalid E17 cache checksum: {directory}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("kind")
        != "gdp_cem_e17_action_conditioned_transition_state_cache"
        or manifest.get("task") != task
        or manifest.get("output_h5_sha256") != sha256_file(h5_path)
        or manifest.get("input_hashes", {}).get("protocol_sha256")
        != spec.PROTOCOL_SHA256
        or manifest.get("input_hashes", {}).get("source_manifest_sha256")
        != source_sha
        or manifest.get("model_training_performed") is not False
        or manifest.get("validation_metrics_computed") is not False
        or manifest.get("p2_read") is not False
        or manifest.get("d3_metric_read") is not False
        or manifest.get("d4_metric_read") is not False
        or manifest.get("d5_read") is not False
        or manifest.get("protected_p3_p4_c1_i1_read") is not False
        or manifest.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"invalid E17 cache manifest: {directory}")
    return manifest


def verify_model(
    directory: Path,
    *,
    task: str,
    source_sha: str,
    cache_directory: Path,
) -> dict[str, Any]:
    files = {
        name: directory / name
        for name in ("final.pt", "training.jsonl", "summary.json", "sha256.txt")
    }
    if not all(path.is_file() for path in files.values()):
        raise FileNotFoundError(f"incomplete E17 adapter: {directory}")
    if checksum_records(files["sha256.txt"]) != {
        "final.pt": sha256_file(files["final.pt"]),
        "training.jsonl": sha256_file(files["training.jsonl"]),
        "summary.json": sha256_file(files["summary.json"]),
    }:
        raise RuntimeError(f"invalid E17 adapter checksum: {directory}")
    summary = json.loads(files["summary.json"].read_text(encoding="utf-8"))
    task_spec = spec.TASK_SPEC[task]
    expected_architecture = {
        "latent_dim": spec.LATENT_DIM,
        "state_dim": int(task_spec["state_dim"]),
        "action_dim": int(task_spec["primitive_action_dim"]),
        "input_dim": spec.input_dim(
            state_dim=int(task_spec["state_dim"]),
            action_dim=int(task_spec["primitive_action_dim"]),
        ),
        "width": spec.MODEL_WIDTH,
        "residual_blocks": spec.MODEL_RESIDUAL_BLOCKS,
    }
    if (
        summary.get("status") != "ok"
        or summary.get("kind")
        != "gdp_cem_e17_transition_state_adapter_preflight"
        or summary.get("task") != task
        or int(summary.get("seed", -1)) != spec.MODEL_SEED
        or summary.get("architecture") != expected_architecture
        or int(summary.get("final_step", -1)) != spec.TRAIN_STEPS
        or summary.get("checkpoint_sha256") != sha256_file(files["final.pt"])
        or summary.get("training_trace_sha256")
        != sha256_file(files["training.jsonl"])
        or summary.get("cache_h5_sha256")
        != sha256_file(cache_directory / "cache.h5")
        or summary.get("cache_manifest_sha256")
        != sha256_file(cache_directory / "manifest.json")
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_sha
        or summary.get("final_checkpoint_written_before_validation_open") is not True
        or summary.get("validation_payload_rows_read_before_checkpoint") != 0
        or summary.get("validation_checkpoint_selection") is not False
        or summary.get("p2_read") is not False
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"invalid E17 adapter summary: {directory}")
    gate = summary["adapter_gate"]
    thresholds = gate.get("thresholds", {})
    expected_thresholds = {
        "overall_standardized_rmse_max": spec.OVERALL_RMSE_MAX,
        "maximum_coordinate_standardized_rmse_max": (
            spec.MAX_COORDINATE_RMSE_MAX
        ),
        "median_coordinate_r2_min": spec.MEDIAN_COORDINATE_R2_MIN,
        "copy_current_rmse_ratio_max": spec.COPY_CURRENT_RMSE_RATIO_MAX,
        "per_tau_standardized_rmse_max": spec.TAU_RMSE_MAX,
        "per_tau_median_coordinate_r2_min": (
            spec.TAU_MEDIAN_COORDINATE_R2_MIN
        ),
    }
    tau_passes = []
    for tau in spec.TAU_VALUES:
        cell = gate["by_tau"][str(tau)]
        expected_tau_pass = bool(
            cell["model"]["standardized_rmse"] <= spec.TAU_RMSE_MAX
            and cell["model"]["median_coordinate_r2"]
            >= spec.TAU_MEDIAN_COORDINATE_R2_MIN
        )
        if cell.get("passed") is not expected_tau_pass:
            raise RuntimeError(f"E17 tau gate disagrees: {task} tau={tau}")
        tau_passes.append(expected_tau_pass)
    expected_pass = bool(
        gate.get("finite") is True
        and gate["model"]["standardized_rmse"] <= spec.OVERALL_RMSE_MAX
        and gate["model"]["maximum_coordinate_standardized_rmse"]
        <= spec.MAX_COORDINATE_RMSE_MAX
        and gate["model"]["median_coordinate_r2"]
        >= spec.MEDIAN_COORDINATE_R2_MIN
        and gate["model_to_copy_current_rmse_ratio"]
        <= spec.COPY_CURRENT_RMSE_RATIO_MAX
        and all(tau_passes)
    )
    if thresholds != expected_thresholds or gate.get("passed") is not expected_pass:
        raise RuntimeError(f"E17 frozen aggregate gate disagrees: {task}")
    return summary


def row_from_metrics(
    *, task: str, tau: str, model: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    return {
        "task": task,
        "tau": tau,
        "rows": model["rows"],
        "model_standardized_rmse": model["standardized_rmse"],
        "copy_current_standardized_rmse": baseline["standardized_rmse"],
        "model_to_copy_rmse_ratio": (
            model["standardized_rmse"] / baseline["standardized_rmse"]
        ),
        "model_max_coordinate_rmse": model[
            "maximum_coordinate_standardized_rmse"
        ],
        "model_median_coordinate_r2": model["median_coordinate_r2"],
        "model_per_example_rmse_q90": model["per_example_standardized_rmse"][
            "q90"
        ],
        "model_per_example_rmse_q99": model["per_example_standardized_rmse"][
            "q99"
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if (
        len(args.source_manifest_sha256) != 64
        or sha256_file(args.protocol) != spec.PROTOCOL_SHA256
    ):
        raise RuntimeError("E17 analyzer identity differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E17 analysis output")

    inputs: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    task_results: dict[str, Any] = {}
    for task in spec.TASKS:
        cache_dir = args.cache_root / task
        model_dir = args.model_root / task
        cache = verify_cache(
            cache_dir, task=task, source_sha=args.source_manifest_sha256
        )
        summary = verify_model(
            model_dir,
            task=task,
            source_sha=args.source_manifest_sha256,
            cache_directory=cache_dir,
        )
        gate = summary["adapter_gate"]
        rows.append(
            row_from_metrics(
                task=task,
                tau="all",
                model=gate["model"],
                baseline=gate["copy_current"],
            )
        )
        for tau in spec.TAU_VALUES:
            cell = gate["by_tau"][str(tau)]
            rows.append(
                row_from_metrics(
                    task=task,
                    tau=str(tau),
                    model=cell["model"],
                    baseline=cell["copy_current"],
                )
            )
        task_results[task] = {
            "passed": gate["passed"],
            "overall": rows[-4],
            "thresholds": gate["thresholds"],
        }
        inputs[task] = {
            "cache_h5_sha256": sha256_file(cache_dir / "cache.h5"),
            "cache_manifest_sha256": sha256_file(cache_dir / "manifest.json"),
            "cache_rows": cache["rows"],
            "cache_train_rows": cache["train_rows"],
            "cache_validation_rows": cache["validation_rows"],
            "model_summary_sha256": sha256_file(model_dir / "summary.json"),
            "model_checkpoint_sha256": sha256_file(model_dir / "final.pt"),
        }

    passed = all(value["passed"] for value in task_results.values())
    decision = (
        "adapter_preflight_passed_both_tasks"
        if passed
        else "stop_transition_adapter_preflight_failed"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    table_path = args.output_dir / "task-first.tsv"
    with table_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    audit = {
        "status": "ok",
        "kind": "gdp_cem_e17_transition_state_adapter_preflight_audit",
        "analysis_role": "P1_infrastructure_preflight_only",
        "decision": decision,
        "both_tasks_passed": passed,
        "task_results": task_results,
        "inputs": inputs,
        "task_first_rows": len(rows),
        "task_first_tsv_sha256": sha256_file(table_path),
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": args.source_manifest_sha256,
        "planner_evaluation_authorized": False,
        "separate_protocol_draft_authorized": passed,
        "full_horizon_diffusion_authorized": False,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    audit_path = args.output_dir / "ADAPTER-PREFLIGHT-AUDIT.json"
    atomic_json(audit_path, audit)
    (args.output_dir / "sha256.txt").write_text(
        f"{sha256_file(audit_path)}  ADAPTER-PREFLIGHT-AUDIT.json\n"
        f"{sha256_file(table_path)}  task-first.tsv\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
