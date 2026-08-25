#!/usr/bin/env python3
"""Apply the frozen E15 Gate-B rules after the 22-cell information barrier."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import gdp_cem_e15_specs as spec
from gdp_cem_e15_data import sha256_file
from evaluate_gdp_cem_e15_offline import TRAINING_SOURCE_MANIFEST_SHA256


PRIMARY_CONDITIONS = ("vad", "diagonal_gaussian", "direct_gmm")
PRIMARY_METRICS = (
    "oracle_projected_action_mse",
    "selected_true_local_lewm_cost",
)
EVALUATION_SOURCE_MANIFEST_SHA256 = (
    "d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e"
)


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


def atomic_text(path: Path, value: str) -> None:
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def scientific_label(value: float) -> str:
    return f"{value:.0e}".replace("e-0", "e-").replace("e+0", "e+")


def manifest_scientific_label(value: float) -> str:
    """Match the NumPy-style labels frozen in the data-preflight manifest."""

    return f"{value:.0e}"


def expected_cells() -> list[tuple[str, str, int]]:
    cells: list[tuple[str, str, int]] = []
    for task in spec.TASKS:
        for condition in PRIMARY_CONDITIONS:
            cells.extend((task, condition, seed) for seed in spec.MODEL_SEEDS)
        cells.extend(
            (
                (task, "vad_shuffled", spec.NULL_SEED),
                (task, "vad_unconditional", spec.NULL_SEED),
            )
        )
    if len(cells) != 22 or len(set(cells)) != 22:
        raise RuntimeError("E15 expected-cell registry differs")
    return cells


def verify_checksum_file(directory: Path) -> None:
    path = directory / "sha256.txt"
    if not path.is_file():
        raise FileNotFoundError(path)
    records: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        if name in records or len(digest) != 64:
            raise RuntimeError("E15 offline checksum manifest differs")
        records[name] = digest
    if set(records) != {"metrics.h5", "summary.json"}:
        raise RuntimeError("E15 offline checksum names differ")
    for name, digest in records.items():
        target = directory / name
        if not target.is_file() or sha256_file(target) != digest:
            raise RuntimeError(f"E15 offline checksum differs: {target}")


def load_record(
    directory: Path,
    *,
    task: str,
    condition: str,
    seed: int,
    source_hash: str,
) -> dict[str, Any]:
    verify_checksum_file(directory)
    summary_path = directory / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e15_offline_proposer_evaluation"
        or summary.get("analysis_role") != "P1_validation_only_Gate_B_development"
        or summary.get("mode") != "full"
        or summary.get("task") != task
        or summary.get("condition") != condition
        or int(summary.get("seed", -1)) != seed
        or int(summary.get("row_count", -1)) != spec.VALIDATION_ROWS
        or int(summary.get("candidate_count", -1)) != spec.CANDIDATE_COUNT
        or summary.get("protocol_sha256") != spec.PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != source_hash
        or summary.get("training_source_manifest_sha256")
        != TRAINING_SOURCE_MANIFEST_SHA256
        or summary.get("p2_read") is not False
        or summary.get("d3_metric_read") is not False
        or summary.get("d4_metric_read") is not False
        or summary.get("d5_read") is not False
        or summary.get("protected_p3_p4_c1_i1_read") is not False
        or summary.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"E15 offline summary identity differs: {summary_path}")
    metrics_path = directory / "metrics.h5"
    if sha256_file(metrics_path) != summary.get("metrics_h5_sha256"):
        raise RuntimeError("E15 offline metrics hash differs")
    with h5py.File(metrics_path, "r") as handle:
        if (
            handle.attrs.get("mode") != "full"
            or handle.attrs.get("task") != task
            or handle.attrs.get("condition") != condition
            or int(handle.attrs.get("seed", -1)) != seed
            or handle.attrs.get("protocol_sha256") != spec.PROTOCOL_SHA256
            or len(handle["cache_row"]) != spec.VALIDATION_ROWS
        ):
            raise RuntimeError("E15 offline HDF5 identity differs")
        arrays = {
            name: np.asarray(dataset[:], dtype=np.float64)
            for name, dataset in handle["metrics"].items()
        }
        cache_row = np.asarray(handle["cache_row"][:], dtype=np.int64)
        episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        delta = np.asarray(handle["delta"][:], dtype=np.int64)
        tau = np.asarray(handle["tau"][:], dtype=np.int64)
        gmm = (
            {
                name: np.asarray(dataset[:], dtype=np.float64)
                for name, dataset in handle["gmm"].items()
            }
            if "gmm" in handle
            else {}
        )
    if (
        not arrays
        or any(value.shape != (spec.VALIDATION_ROWS,) for value in arrays.values())
        or any(not np.isfinite(value).all() for value in arrays.values())
        or any(not np.isfinite(value).all() for value in gmm.values())
        or set(np.unique(delta).tolist()) != set(spec.DELTA_VALUES)
        or set(np.unique(tau).tolist()) != set(spec.TAU_VALUES)
        or not all(
            np.count_nonzero((delta == d) & (tau == t))
            == spec.VALIDATION_ROWS_PER_CELL
            for d, t in spec.DELTA_TAU_PAIRS
        )
    ):
        raise RuntimeError("E15 offline metric payload differs")
    if condition == "direct_gmm":
        expected_gmm_shapes = {
            "prior_probability": (spec.VALIDATION_ROWS, spec.GMM_MODES),
            "posterior_probability": (spec.VALIDATION_ROWS, spec.GMM_MODES),
            "sampled_mode_fraction": (spec.VALIDATION_ROWS, spec.GMM_MODES),
            "normalized_prior_entropy": (spec.VALIDATION_ROWS,),
            "effective_prior_modes": (spec.VALIDATION_ROWS,),
        }
        if set(gmm) != set(expected_gmm_shapes) or any(
            gmm[name].shape != shape for name, shape in expected_gmm_shapes.items()
        ):
            raise RuntimeError("E15 GMM diagnostic payload differs")
    elif gmm:
        raise RuntimeError("non-GMM E15 evaluation contains GMM payload")
    return {
        "summary": summary,
        "summary_path": summary_path,
        "metrics_path": metrics_path,
        "metrics": arrays,
        "cache_row": cache_row,
        "episode": episode,
        "delta": delta,
        "tau": tau,
        "gmm": gmm,
    }


def aggregate_record(record: dict[str, Any]) -> dict[str, Any]:
    arrays = record["metrics"]
    delta = record["delta"]
    tau = record["tau"]
    per_cell: dict[tuple[int, int], dict[str, float]] = {}
    for delta_value, tau_value in spec.DELTA_TAU_PAIRS:
        mask = (delta == delta_value) & (tau == tau_value)
        per_cell[(delta_value, tau_value)] = {
            name: float(value[mask].mean()) for name, value in arrays.items()
        }
    equal_cell = {
        name: float(np.mean([cell[name] for cell in per_cell.values()]))
        for name in arrays
    }
    per_tau = {
        str(tau_value): {
            name: float(
                np.mean(
                    [
                        values[name]
                        for (delta_value, cell_tau), values in per_cell.items()
                        if cell_tau == tau_value
                    ]
                )
            )
            for name in arrays
        }
        for tau_value in spec.TAU_VALUES
    }
    return {
        "equal_cell_mean": equal_cell,
        "per_tau_equal_cell_mean": per_tau,
        "per_cell": per_cell,
    }


def expert_manifest_mean(
    manifest: dict[str, Any], *, tau: int, diagnostic: str
) -> float:
    dimensions = manifest["expert_geometry"]["E15_val"][str(tau)]
    return float(np.mean([float(item[diagnostic]) for item in dimensions]))


def common_integrity(
    records: dict[tuple[str, str, int], dict[str, Any]],
    data_manifests: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    all_pass = True
    for key in expected_cells():
        task, _, _ = key
        record = records[key]
        arrays = record["metrics"]
        tau_values = record["tau"]
        boundary: dict[str, Any] = {}
        boundary_pass = True
        for tau in spec.TAU_VALUES:
            mask = tau_values == tau
            diagnostics: dict[str, Any] = {}
            for generated_name, expert_name in (
                ("near_1e-2_fraction", "expert_near_1e-2_fraction"),
                (
                    "jacobian_below_1e-3_fraction",
                    "expert_jacobian_below_1e-3_fraction",
                ),
            ):
                generated = arrays[generated_name][mask]
                expert = arrays[expert_name][mask]
                generated_mean = float(generated.mean())
                generated_q99 = float(np.quantile(generated, 0.99))
                expert_mean = float(expert.mean())
                expert_q99 = float(np.quantile(expert, 0.99))
                mean_limit = max(
                    2.0 * expert_mean,
                    expert_mean + spec.EXPERT_MEAN_ADDITIVE_ALLOWANCE,
                )
                q99_limit = min(
                    1.0, expert_q99 + spec.EXPERT_Q99_ADDITIVE_ALLOWANCE
                )
                passed = (
                    generated_mean <= mean_limit and generated_q99 <= q99_limit
                )
                boundary_pass &= passed
                diagnostics[generated_name] = {
                    "generated_mean": generated_mean,
                    "generated_q99": generated_q99,
                    "expert_mean": expert_mean,
                    "expert_q99": expert_q99,
                    "mean_limit": mean_limit,
                    "q99_limit": q99_limit,
                    "pass": passed,
                }
            boundary[str(tau)] = diagnostics
        expert_reference_matches = True
        for tau in spec.TAU_VALUES:
            for margin in spec.NEAR_BOUNDARY_MARGINS:
                suffix = scientific_label(margin)
                observed = float(
                    arrays[f"expert_near_{suffix}_fraction"][tau_values == tau].mean()
                )
                manifest_suffix = manifest_scientific_label(margin)
                expected = expert_manifest_mean(
                    data_manifests[task],
                    tau=tau,
                    diagnostic=f"projected_near_{manifest_suffix}_fraction",
                )
                expert_reference_matches &= bool(
                    np.isclose(observed, expected, rtol=0.0, atol=2.0e-8)
                )
            for threshold in spec.JACOBIAN_THRESHOLDS:
                suffix = scientific_label(threshold)
                observed = float(
                    arrays[f"expert_jacobian_below_{suffix}_fraction"][
                        tau_values == tau
                    ].mean()
                )
                manifest_suffix = manifest_scientific_label(threshold)
                expected = expert_manifest_mean(
                    data_manifests[task],
                    tau=tau,
                    diagnostic=f"jacobian_below_{manifest_suffix}_fraction",
                )
                expert_reference_matches &= bool(
                    np.isclose(observed, expected, rtol=0.0, atol=2.0e-8)
                )
        finite = all(np.isfinite(value).all() for value in arrays.values())
        minimum_unique = int(arrays["minimum_unique_candidates"].min())
        strict_oob_max = float(arrays["strict_legal_oob_fraction"].max())
        exact_boundary_max = float(arrays["exact_legal_boundary_fraction"].max())
        passed = (
            finite
            and minimum_unique >= spec.MINIMUM_UNIQUE_CANDIDATES
            and strict_oob_max == 0.0
            and exact_boundary_max == 0.0
            and expert_reference_matches
            and boundary_pass
        )
        all_pass &= passed
        details["|".join(map(str, key))] = {
            "all_finite": finite,
            "minimum_unique_candidates": minimum_unique,
            "strict_legal_oob_fraction_maximum": strict_oob_max,
            "exact_legal_boundary_fraction_maximum": exact_boundary_max,
            "expert_reference_matches_data_manifest": expert_reference_matches,
            "expert_relative_boundary": boundary,
            "pass": passed,
        }
    if len(details) != 22:
        raise RuntimeError("E15 common-integrity bank registry differs")
    return {"pass": all_pass, "banks": details}


def gmm_structural(
    records: dict[tuple[str, str, int], dict[str, Any]]
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    all_pass = True
    for task in spec.TASKS:
        for seed in spec.MODEL_SEEDS:
            record = records[(task, "direct_gmm", seed)]
            gmm = record["gmm"]
            prior_mass = gmm["prior_probability"].mean(axis=0)
            posterior_winner = gmm["posterior_probability"].argmax(axis=1)
            posterior_win_fraction = np.bincount(
                posterior_winner, minlength=spec.GMM_MODES
            ) / len(posterior_winner)
            used_modes = int(
                np.count_nonzero(
                    posterior_win_fraction
                    >= spec.GMM_MINIMUM_POSTERIOR_WIN_FRACTION
                )
            )
            per_cell_entropy = []
            for delta, tau in spec.DELTA_TAU_PAIRS:
                mask = (record["delta"] == delta) & (record["tau"] == tau)
                per_cell_entropy.append(gmm["normalized_prior_entropy"][mask].mean())
            equal_cell_entropy = float(np.mean(per_cell_entropy))
            sampled_fraction = gmm["sampled_mode_fraction"].mean(axis=0)
            passed = (
                bool(
                    np.all(prior_mass >= spec.GMM_MINIMUM_GLOBAL_MODE_MASS)
                )
                and used_modes >= spec.GMM_MINIMUM_POSTERIOR_USED_MODES
                and equal_cell_entropy >= spec.GMM_MINIMUM_NORMALIZED_ENTROPY
            )
            all_pass &= passed
            details[f"{task}|{seed}"] = {
                "global_mean_prior_mass": prior_mass.tolist(),
                "posterior_winning_mode_fraction": posterior_win_fraction.tolist(),
                "posterior_used_modes": used_modes,
                "equal_cell_mean_normalized_prior_entropy": equal_cell_entropy,
                "global_sampled_mode_fraction": sampled_fraction.tolist(),
                "pass": passed,
            }
    return {"pass": all_pass, "banks": details}


def metric_value(
    aggregates: dict[tuple[str, str, int], dict[str, Any]],
    key: tuple[str, str, int],
    metric: str,
    *,
    tau: int | None = None,
) -> float:
    if tau is None:
        return float(aggregates[key]["equal_cell_mean"][metric])
    return float(aggregates[key]["per_tau_equal_cell_mean"][str(tau)][metric])


def two_of_three_durations(
    aggregates: dict[tuple[str, str, int], dict[str, Any]],
    *,
    task: str,
    seed: int,
    reference: str,
) -> dict[str, Any]:
    winning = [
        tau
        for tau in spec.TAU_VALUES
        if all(
            metric_value(aggregates, (task, "vad", seed), metric, tau=tau)
            < metric_value(aggregates, (task, reference, seed), metric, tau=tau)
            for metric in PRIMARY_METRICS
        )
    ]
    return {"winning_tau": winning, "pass": len(winning) >= 2}


def vad_mechanism(
    aggregates: dict[tuple[str, str, int], dict[str, Any]]
) -> dict[str, Any]:
    seed_results: dict[str, Any] = {}
    seeds_pass = True
    for seed in spec.MODEL_SEEDS:
        equal_task: dict[str, Any] = {}
        matched_pass = True
        for metric in PRIMARY_METRICS:
            vad_value = float(
                np.mean(
                    [
                        metric_value(aggregates, (task, "vad", seed), metric)
                        for task in spec.TASKS
                    ]
                )
            )
            gaussian_value = float(
                np.mean(
                    [
                        metric_value(
                            aggregates,
                            (task, "diagonal_gaussian", seed),
                            metric,
                        )
                        for task in spec.TASKS
                    ]
                )
            )
            won = vad_value < gaussian_value
            matched_pass &= won
            equal_task[metric] = {
                "vad": vad_value,
                "diagonal_gaussian": gaussian_value,
                "pass": won,
            }
        task_directions = {
            task: two_of_three_durations(
                aggregates,
                task=task,
                seed=seed,
                reference="diagonal_gaussian",
            )
            for task in spec.TASKS
        }
        passed = matched_pass and all(x["pass"] for x in task_directions.values())
        seeds_pass &= passed
        seed_results[str(seed)] = {
            "equal_task": equal_task,
            "per_task_two_of_three_durations": task_directions,
            "pass": passed,
        }

    null_results: dict[str, Any] = {}
    nulls_pass = True
    for condition in ("vad_shuffled", "vad_unconditional"):
        equal_task = {}
        equal_task_pass = True
        for metric in PRIMARY_METRICS:
            true_value = float(
                np.mean(
                    [
                        metric_value(
                            aggregates, (task, "vad", spec.NULL_SEED), metric
                        )
                        for task in spec.TASKS
                    ]
                )
            )
            null_value = float(
                np.mean(
                    [
                        metric_value(
                            aggregates, (task, condition, spec.NULL_SEED), metric
                        )
                        for task in spec.TASKS
                    ]
                )
            )
            won = true_value < null_value
            equal_task_pass &= won
            equal_task[metric] = {
                "vad": true_value,
                "null": null_value,
                "pass": won,
            }
        task_directions = {
            task: two_of_three_durations(
                aggregates,
                task=task,
                seed=spec.NULL_SEED,
                reference=condition,
            )
            for task in spec.TASKS
        }
        passed = equal_task_pass and all(x["pass"] for x in task_directions.values())
        nulls_pass &= passed
        null_results[condition] = {
            "equal_task": equal_task,
            "per_task_two_of_three_durations": task_directions,
            "pass": passed,
        }
    return {
        "pass": seeds_pass and nulls_pass,
        "vad_beats_gaussian_every_seed": seeds_pass,
        "true_vad_beats_both_nulls_at_seed_7201": nulls_pass,
        "seed_results": seed_results,
        "null_results": null_results,
    }


def write_task_first_table(
    path: Path,
    records: dict[tuple[str, str, int], dict[str, Any]],
    aggregates: dict[tuple[str, str, int], dict[str, Any]],
) -> None:
    metric_names = sorted(next(iter(records.values()))["metrics"])
    fields = ["task", "condition", "seed", "delta", "tau", *metric_names]
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with partial.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            for key in expected_cells():
                task, condition, seed = key
                for delta, tau in spec.DELTA_TAU_PAIRS:
                    writer.writerow(
                        {
                            "task": task,
                            "condition": condition,
                            "seed": seed,
                            "delta": delta,
                            "tau": tau,
                            **aggregates[key]["per_cell"][(delta, tau)],
                        }
                    )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.evaluation_root,
        args.data_root,
        args.protocol,
        args.source_manifest,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E15 Gate-B analysis output")
    if sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E15 Gate-B protocol hash differs")
    source_hash = sha256_file(args.source_manifest)
    data_manifests: dict[str, dict[str, Any]] = {}
    for task in spec.TASKS:
        path = args.data_root / task / "manifest.json"
        if sha256_file(path) != spec.TASK_SPEC[task]["e15_cache_manifest_sha256"]:
            raise RuntimeError("E15 Gate-B data-manifest hash differs")
        data_manifests[task] = json.loads(path.read_text(encoding="utf-8"))

    records: dict[tuple[str, str, int], dict[str, Any]] = {}
    artifacts: dict[str, Any] = {}
    task_rows: dict[str, np.ndarray] = {}
    task_episodes: dict[str, np.ndarray] = {}
    task_experts: dict[str, dict[str, np.ndarray]] = {}
    expert_metric_names = [
        *(f"expert_near_{scientific_label(x)}_fraction" for x in spec.NEAR_BOUNDARY_MARGINS),
        *(
            f"expert_jacobian_below_{scientific_label(x)}_fraction"
            for x in spec.JACOBIAN_THRESHOLDS
        ),
        "expert_target_projection_fraction",
    ]
    for key in expected_cells():
        task, condition, seed = key
        directory = args.evaluation_root / task / condition / f"seed-{seed}"
        record = load_record(
            directory,
            task=task,
            condition=condition,
            seed=seed,
            source_hash=EVALUATION_SOURCE_MANIFEST_SHA256,
        )
        if task not in task_rows:
            task_rows[task] = record["cache_row"]
            task_episodes[task] = record["episode"]
            task_experts[task] = {
                name: record["metrics"][name] for name in expert_metric_names
            }
        elif (
            not np.array_equal(record["cache_row"], task_rows[task])
            or not np.array_equal(record["episode"], task_episodes[task])
            or any(
                not np.array_equal(record["metrics"][name], task_experts[task][name])
                for name in expert_metric_names
            )
        ):
            raise RuntimeError("E15 validation rows/expert references differ across arms")
        records[key] = record
        artifacts["|".join(map(str, key))] = {
            "summary": str(record["summary_path"]),
            "summary_sha256": sha256_file(record["summary_path"]),
            "metrics_h5": str(record["metrics_path"]),
            "metrics_h5_sha256": sha256_file(record["metrics_path"]),
        }
    aggregates = {key: aggregate_record(value) for key, value in records.items()}
    common = common_integrity(records, data_manifests)
    gmm = gmm_structural(records)
    mechanism = vad_mechanism(aggregates)
    gate_passed = common["pass"] and gmm["pass"] and mechanism["pass"]
    decision = (
        "authorize_fixed_gate_c_p2_long_horizon_development"
        if gate_passed
        else "stop_before_gate_c_frozen_gate_b_failed"
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    table_path = args.output_dir / "TASK-FIRST-PER-CELL.tsv"
    write_task_first_table(table_path, records, aggregates)
    compact_aggregates = {
        "|".join(map(str, key)): {
            "equal_cell_mean": value["equal_cell_mean"],
            "per_tau_equal_cell_mean": value["per_tau_equal_cell_mean"],
        }
        for key, value in aggregates.items()
    }
    result = {
        "status": "ok",
        "kind": "gdp_cem_e15_gate_b_offline_analysis",
        "analysis_role": "P1_validation_only_Gate_B_development",
        "decision": decision,
        "gate_b_passed": gate_passed,
        "gates": {
            "common_bank_integrity": common,
            "direct_gmm_structural_validity": gmm,
            "vad_mechanism_and_conditioning": mechanism,
        },
        "task_first_aggregates": compact_aggregates,
        "task_first_per_cell_tsv": str(table_path),
        "task_first_per_cell_tsv_sha256": sha256_file(table_path),
        "task_validation_rows_sha256": {
            task: records[(task, "vad", spec.MODEL_SEEDS[0])]["summary"][
                "evaluation_rows_sha256"
            ]
            for task in spec.TASKS
        },
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "training_source_manifest_sha256": TRAINING_SOURCE_MANIFEST_SHA256,
        "source_manifest_sha256": source_hash,
        "evaluation_source_manifest_sha256": EVALUATION_SOURCE_MANIFEST_SHA256,
        "analyzer_source_sha256": sha256_file(Path(__file__)),
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    audit_path = args.output_dir / "GATE-B-AUDIT.json"
    atomic_json(audit_path, result)
    atomic_text(
        args.output_dir / "sha256.txt",
        f"{sha256_file(audit_path)}  GATE-B-AUDIT.json\n"
        f"{sha256_file(table_path)}  TASK-FIRST-PER-CELL.tsv\n",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
