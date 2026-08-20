#!/usr/bin/env python3
"""Analyze the frozen E4-D2B closed-loop exploratory development run.

This analyzer deliberately consumes only the one-run summaries and their
paired episode vectors.  D2A authorization and all provenance hashes are
derived from the files supplied on the command line; no outcome hash is
invented in this file.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_e4_d2b_models as d2b


TASKS = ("pusht", "reacher", "cube")
PLANNER_SEED = 8401
E4_SCORER_SEED = 7101
ACID_SCORER_SEED = 6101
EVAL_COUNT = 50
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081612
NONINFERIORITY_MARGIN = 0.05
PARENT_PROTOCOL_SHA256 = (
    "eec19adf1558a7366bbc13bd5077c5c26ac4dd73fd5c03b5be2651fe288dfc12"
)
D2B_FREEZE_SHA256 = (
    "0b8aba12023ffcd7f4f010a72452ae021e081d80f11dfc7fe21cb13c8dfb4250"
)
D2A_IMPLEMENTATION_FREEZE_SHA256 = (
    "193f5679ec91377c0d2411b9092cc4d2c8308d64f509917244d1b89dcb7354b9"
)
D2A_SOURCE_MANIFEST_SHA256 = (
    "36a6c04fe47e8bfc0bb6e375e5d2d3448879e06146af433d504c523842af70bd"
)

E4_SEED_ARMS = {
    "cider_tail_l002",
    "cider_tail",
    "cider_tail_l014",
    "cider_shuffled",
    "dide",
    "cider_raw",
    "cider_mean_violation",
    "deterministic_inverse",
    "gaussian_tail",
}
ACID_SEED_ARMS = {
    "acid_l002",
    "acid",
    "acid_l014",
    "acid_flow",
    "acid_16_mean",
    "acid_16_min",
    "forward",
    "reachability",
}


def expected_model_seed(arm: str) -> int | None:
    if arm == "b0":
        return None
    if arm in E4_SEED_ARMS:
        return E4_SCORER_SEED
    if arm in ACID_SEED_ARMS:
        return ACID_SCORER_SEED
    raise ValueError(f"unknown frozen arm: {arm}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, value: Any) -> None:
    encoded = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    atomic_bytes(path, encoded)


def parse_run(values: list[str]) -> tuple[str, str, Path]:
    if len(values) != 3:
        raise ValueError("run requires TASK ARM SUMMARY")
    task, arm, summary_text = values
    if task not in TASKS or arm not in d2b.ARMS:
        raise ValueError(f"invalid run identity: {values}")
    return task, arm, Path(summary_text)


def _number(summary: dict[str, Any], names: tuple[str, ...], label: str) -> float:
    present = [name for name in names if name in summary]
    if not present:
        raise RuntimeError(f"summary lacks required {label}")
    values = []
    for name in present:
        value = float(summary[name])
        if not np.isfinite(value) or value < 0:
            raise RuntimeError(f"invalid {label} in summary")
        values.append(value)
    if any(value != values[0] for value in values[1:]):
        raise RuntimeError(f"conflicting {label} aliases in summary")
    return values[0]


def read_episode_vector(
    path: Path, *, task: str, arm: str, planner_seed: int
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {
        "eval_index",
        "episode_id",
        "start_step",
        "planner_seed",
        "arm",
        "success",
    }
    if len(rows) != EVAL_COUNT or not rows or not required.issubset(rows[0]):
        raise RuntimeError(f"{task}/{arm}: invalid episodes TSV")
    if [int(row["eval_index"]) for row in rows] != list(range(EVAL_COUNT)):
        raise RuntimeError(f"{task}/{arm}: noncontiguous evaluation indices")
    if any(
        row["arm"] != arm
        or int(row["planner_seed"]) != planner_seed
        or int(row["success"]) not in (0, 1)
        for row in rows
    ):
        raise RuntimeError(f"{task}/{arm}: episode identity mismatch")
    starts = [(int(row["episode_id"]), int(row["start_step"])) for row in rows]
    if len(set(starts)) != EVAL_COUNT:
        raise RuntimeError(f"{task}/{arm}: duplicate paired start")
    return np.asarray([int(row["success"]) for row in rows], dtype=np.int8), starts


def load_d2a_provenance(
    *,
    d2a_summary_path: Path,
    authorization_path: Path,
    d2a_implementation_freeze_sha256: str,
    d2a_source_manifest_sha256: str,
    parent_protocol_sha256: str,
) -> tuple[dict[str, Any], str, str]:
    for path in (d2a_summary_path, authorization_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    d2a_summary_sha256 = sha256_file(d2a_summary_path)
    authorization_sha256 = sha256_file(authorization_path)
    d2a_summary = json.loads(d2a_summary_path.read_text(encoding="utf-8"))
    if (
        d2a_summary.get("status") != "ok"
        or d2a_summary.get("kind") != "acid_alt_e4_d2a_analysis"
        or d2a_summary.get("all_d2a_gates_pass") is not True
        or d2a_summary.get("decision") != "authorize_e4_d2b_closed_loop"
        or d2a_summary.get("implementation_freeze_sha256")
        != d2a_implementation_freeze_sha256
        or d2a_summary.get("source_manifest_sha256")
        != d2a_source_manifest_sha256
        or d2a_summary.get("parent_protocol_sha256") != parent_protocol_sha256
        or d2a_summary.get("confirmation_claim_allowed") is not False
        or d2a_summary.get("alternative_to_acid_claim_allowed") is not False
        or d2a_summary.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("D2A summary is not the authorized frozen result")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if (
        authorization.get("status") != "authorized"
        or authorization.get("kind") != "acid_alt_e4_d2b_authorization"
        or authorization.get("d2a_summary_sha256") != d2a_summary_sha256
        or authorization.get("implementation_freeze_sha256")
        != d2a_implementation_freeze_sha256
        or authorization.get("source_manifest_sha256")
        != d2a_source_manifest_sha256
        or authorization.get("parent_protocol_sha256") != parent_protocol_sha256
        or authorization.get("confirmation_claim_allowed") is not False
        or authorization.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError("E4-D2B authorization is invalid")
    return d2a_summary, d2a_summary_sha256, authorization_sha256


def load_isolated_d2a_latencies(d2a_summary: dict[str, Any]) -> dict[str, Any]:
    """Carry forward the already measured scorer-only D2A latency records."""

    inputs = d2a_summary.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != set(TASKS):
        raise RuntimeError("D2A summary lacks all task input manifests")
    result: dict[str, Any] = {}
    for task in TASKS:
        record = inputs[task]
        manifest_path = Path(record["manifest"])
        if (
            not manifest_path.is_file()
            or sha256_file(manifest_path) != record.get("manifest_sha256")
        ):
            raise RuntimeError(f"{task}: D2A latency manifest hash mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("status") != "ok"
            or manifest.get("kind") != "acid_alt_e4_d2a_task_scores"
            or manifest.get("task") != task
            or not isinstance(manifest.get("scorers"), list)
        ):
            raise RuntimeError(f"{task}: invalid D2A latency manifest")
        result[task] = {
            "manifest": str(manifest_path),
            "manifest_sha256": record["manifest_sha256"],
            "scorers": manifest["scorers"],
        }
    return result


def load_run(
    identity: tuple[str, str, Path],
    *,
    parent_protocol_sha256: str,
    d2b_freeze_sha256: str,
    source_manifest_sha256: str,
    d2a_summary_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    task, arm, summary_path = identity
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary_sha256 = sha256_file(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "acid_alt_e4_d2b_closed_loop_evaluation"
        or summary.get("analysis_role")
        != "post-E3 exposed D2 exploratory closed-loop development"
        or summary.get("task") != task
        or summary.get("arm") != arm
        or summary.get("model_seed") != expected_model_seed(arm)
        or int(summary.get("planner_seed", -1)) != PLANNER_SEED
        or summary.get("episode_count") != EVAL_COUNT
        or summary.get("parent_protocol_sha256") != parent_protocol_sha256
        or summary.get("d2b_freeze_sha256") != d2b_freeze_sha256
        or summary.get("source_manifest_sha256") != source_manifest_sha256
        or summary.get("d2a_summary_sha256") != d2a_summary_sha256
        or summary.get("d2a_authorization_sha256") != authorization_sha256
        or summary.get("confirmation_claim_allowed") is not False
        or summary.get("publication_claim_allowed") is not False
        or summary.get("alternative_to_acid_claim_allowed") is not False
        or summary.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError(f"invalid E4-D2B summary: {summary_path}")
    episode_path = Path(summary["episodes_tsv"])
    episode_sha256 = sha256_file(episode_path) if episode_path.is_file() else ""
    if not episode_path.is_file() or episode_sha256 != summary.get("episodes_tsv_sha256"):
        raise RuntimeError(f"episode TSV hash mismatch: {summary_path}")
    success, starts = read_episode_vector(
        episode_path,
        task=task,
        arm=arm,
        planner_seed=PLANNER_SEED,
    )
    if int(success.sum()) != int(summary["success_count"]):
        raise RuntimeError(f"success count mismatch: {summary_path}")
    runtime = summary.get("runtime")
    if not isinstance(runtime, dict):
        raise RuntimeError(f"missing runtime fields: {summary_path}")
    gpu = runtime.get("gpu", summary.get("gpu"))
    if gpu is None:
        raise RuntimeError(f"missing GPU runtime field: {summary_path}")
    peak_memory = _number(
        runtime,
        ("peak_cuda_memory_allocated_bytes", "peak_cuda_memory_bytes"),
        "peak CUDA memory",
    )
    return {
        "success": success,
        "starts": starts,
        "summary": str(summary_path),
        "summary_sha256": summary_sha256,
        "episodes": str(episode_path),
        "episodes_sha256": episode_sha256,
        "eval_manifest_sha256": summary["eval_manifest_sha256"],
        "dataset_sha256": summary["dataset_sha256"],
        "world_model_checkpoint_sha256": summary["world_model_checkpoint_sha256"],
        "elapsed_seconds": _number(summary, ("elapsed_seconds",), "elapsed time"),
        "cem_cost_calls": int(summary["cem_cost_calls"]),
        "gpu": str(gpu),
        "peak_cuda_memory_allocated_bytes": int(peak_memory),
        "model_seed": summary.get("model_seed"),
    }


def bootstrap_indices() -> dict[str, np.ndarray]:
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    return {
        task: generator.integers(
            0, EVAL_COUNT, size=(BOOTSTRAP_REPETITIONS, EVAL_COUNT), dtype=np.int16
        )
        for task in TASKS
    }


def bootstrap_task(vector: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Return paired-start bootstrap means for one task and one contrast."""
    vector = np.asarray(vector, dtype=np.float64)
    if vector.shape != (EVAL_COUNT,) or indices.shape != (
        BOOTSTRAP_REPETITIONS,
        EVAL_COUNT,
    ):
        raise ValueError("unexpected paired bootstrap shape")
    return vector[indices].mean(axis=1)


def summarize(vectors: dict[str, np.ndarray], indices: dict[str, np.ndarray]) -> dict[str, Any]:
    per_task_boot: dict[str, np.ndarray] = {}
    per_task: dict[str, Any] = {}
    for task in TASKS:
        vector = np.asarray(vectors[task], dtype=np.float64)
        if vector.shape != (EVAL_COUNT,) or not np.isfinite(vector).all():
            raise RuntimeError(f"{task}: invalid paired vector")
        draws = bootstrap_task(vector, indices[task])
        per_task_boot[task] = draws
        per_task[task] = {
            "estimate": float(vector.mean()),
            "lower_95_two_sided": float(np.quantile(draws, 0.025)),
            "upper_95_two_sided": float(np.quantile(draws, 0.975)),
            "lower_95_one_sided": float(np.quantile(draws, 0.05)),
            "upper_95_one_sided": float(np.quantile(draws, 0.95)),
        }
    equal_draw = np.mean(np.stack([per_task_boot[task] for task in TASKS]), axis=0)
    return {
        "per_task": per_task,
        "equal_task": {
            "estimate": float(np.mean([vectors[task].mean() for task in TASKS])),
            "lower_95_two_sided": float(np.quantile(equal_draw, 0.025)),
            "upper_95_two_sided": float(np.quantile(equal_draw, 0.975)),
            "lower_95_one_sided": float(np.quantile(equal_draw, 0.05)),
            "upper_95_one_sided": float(np.quantile(equal_draw, 0.95)),
        },
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "cluster_unit": "paired D2 start",
        "task_weighting": "equal",
    }


def paired_discordance(left: np.ndarray, right: np.ndarray) -> dict[str, int]:
    left = np.asarray(left, dtype=np.int8)
    right = np.asarray(right, dtype=np.int8)
    return {
        "left_success_right_failure": int(np.count_nonzero((left == 1) & (right == 0))),
        "left_failure_right_success": int(np.count_nonzero((left == 0) & (right == 1))),
        "both_success": int(np.count_nonzero((left == 1) & (right == 1))),
        "both_failure": int(np.count_nonzero((left == 0) & (right == 0))),
        "discordant_total": int(np.count_nonzero(left != right)),
    }


def write_runs_table(path: Path, loaded: dict[tuple[str, str], dict[str, Any]]) -> None:
    fields = (
        "task", "arm", "model_seed", "planner_seed", "success_count", "success_rate",
        "summary_sha256", "episodes_sha256", "elapsed_seconds", "cem_cost_calls", "gpu",
        "peak_cuda_memory_allocated_bytes",
    )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for task in TASKS:
        for arm in d2b.ARMS:
            record = loaded[(task, arm)]
            writer.writerow(
                {
                    "task": task,
                    "arm": arm,
                    "model_seed": record["model_seed"],
                    "planner_seed": PLANNER_SEED,
                    "success_count": int(record["success"].sum()),
                    "success_rate": float(record["success"].mean()),
                    "summary_sha256": record["summary_sha256"],
                    "episodes_sha256": record["episodes_sha256"],
                    "elapsed_seconds": record["elapsed_seconds"],
                    "cem_cost_calls": record["cem_cost_calls"],
                    "gpu": record["gpu"],
                    "peak_cuda_memory_allocated_bytes": record["peak_cuda_memory_allocated_bytes"],
                }
            )
    atomic_bytes(path, buffer.getvalue().encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-protocol", type=Path, required=True)
    parser.add_argument("--d2b-freeze", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--d2a-implementation-freeze", type=Path, required=True)
    parser.add_argument("--d2a-source-manifest", type=Path, required=True)
    parser.add_argument("--d2a-summary", type=Path, required=True)
    parser.add_argument("--d2b-authorization", type=Path, required=True)
    parser.add_argument(
        "--run", nargs=3, action="append", metavar=("TASK", "ARM", "SUMMARY"), required=True
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    input_paths = (
        args.parent_protocol,
        args.d2b_freeze,
        args.source_manifest,
        args.d2a_implementation_freeze,
        args.d2a_source_manifest,
    )
    for path in input_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    parent_protocol_sha256 = sha256_file(args.parent_protocol)
    d2b_freeze_sha256 = sha256_file(args.d2b_freeze)
    source_manifest_sha256 = sha256_file(args.source_manifest)
    d2a_implementation_freeze_sha256 = sha256_file(args.d2a_implementation_freeze)
    d2a_source_manifest_sha256 = sha256_file(args.d2a_source_manifest)
    if (
        parent_protocol_sha256 != PARENT_PROTOCOL_SHA256
        or d2b_freeze_sha256 != D2B_FREEZE_SHA256
        or d2a_implementation_freeze_sha256
        != D2A_IMPLEMENTATION_FREEZE_SHA256
        or d2a_source_manifest_sha256 != D2A_SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("frozen E4-D2A/D2B input hash mismatch")
    d2a_summary, d2a_summary_sha256, authorization_sha256 = load_d2a_provenance(
        d2a_summary_path=args.d2a_summary,
        authorization_path=args.d2b_authorization,
        d2a_implementation_freeze_sha256=d2a_implementation_freeze_sha256,
        d2a_source_manifest_sha256=d2a_source_manifest_sha256,
        parent_protocol_sha256=parent_protocol_sha256,
    )
    isolated_d2a_latencies = load_isolated_d2a_latencies(d2a_summary)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E4-D2B analysis output")

    identities = [parse_run(values) for values in args.run]
    expected_grid = {
        (task, arm)
        for task in TASKS
        for arm in d2b.ARMS
    }
    observed_grid = {(task, arm) for task, arm, _ in identities}
    if len(identities) != len(expected_grid) or observed_grid != expected_grid:
        raise RuntimeError(
            f"E4-D2B grid mismatch; missing={sorted(expected_grid - observed_grid)}, "
            f"extra={sorted(observed_grid - expected_grid)}"
        )
    loaded = {
        (task, arm): load_run(
            identity,
            parent_protocol_sha256=parent_protocol_sha256,
            d2b_freeze_sha256=d2b_freeze_sha256,
            source_manifest_sha256=source_manifest_sha256,
            d2a_summary_sha256=d2a_summary_sha256,
            authorization_sha256=authorization_sha256,
        )
        for identity in identities
        for task, arm, _ in (identity,)
    }
    for task in TASKS:
        reference = loaded[(task, "b0")]
        for arm in d2b.ARMS:
            record = loaded[(task, arm)]
            if (
                record["starts"] != reference["starts"]
                or record["eval_manifest_sha256"] != reference["eval_manifest_sha256"]
                or record["dataset_sha256"] != reference["dataset_sha256"]
                or record["world_model_checkpoint_sha256"] != reference["world_model_checkpoint_sha256"]
            ):
                raise RuntimeError(f"unpaired E4-D2B inputs: {task}/{arm}")
        if loaded[(task, "cider_shuffled")]["success"].tobytes() != reference["success"].tobytes():
            raise RuntimeError(f"{task}: cider_shuffled episode vector is not bit-identical to B0")

    matrices = {task: {arm: loaded[(task, arm)]["success"].astype(np.float64) for arm in d2b.ARMS} for task in TASKS}
    indices = bootstrap_indices()
    levels = {arm: summarize({task: matrices[task][arm] for task in TASKS}, indices) for arm in d2b.ARMS}
    contrast_pairs = {
        "cider_tail_minus_acid": ("cider_tail", "acid"),
        "cider_tail_minus_b0": ("cider_tail", "b0"),
        "cider_tail_minus_cider_shuffled": ("cider_tail", "cider_shuffled"),
        "cider_tail_minus_deterministic_inverse": ("cider_tail", "deterministic_inverse"),
        "cider_tail_minus_gaussian_tail": ("cider_tail", "gaussian_tail"),
        "cider_tail_minus_acid_flow": ("cider_tail", "acid_flow"),
        "cider_tail_minus_acid_16_mean": ("cider_tail", "acid_16_mean"),
        "cider_tail_minus_acid_16_min": ("cider_tail", "acid_16_min"),
        "cider_tail_l002_minus_cider_tail": ("cider_tail_l002", "cider_tail"),
        "cider_tail_l014_minus_cider_tail": ("cider_tail_l014", "cider_tail"),
        "acid_l002_minus_acid": ("acid_l002", "acid"),
        "acid_l014_minus_acid": ("acid_l014", "acid"),
    }
    contrast_vectors = {
        label: {task: matrices[task][left] - matrices[task][right] for task in TASKS}
        for label, (left, right) in contrast_pairs.items()
    }
    contrasts = {label: summarize(values, indices) for label, values in contrast_vectors.items()}
    discordance = {
        label: {
            "per_task": {
                task: paired_discordance(matrices[task][left], matrices[task][right])
                for task in TASKS
            },
            "equal_task_descriptive": paired_discordance(
                np.concatenate([matrices[task][left] for task in TASKS]),
                np.concatenate([matrices[task][right] for task in TASKS]),
            ),
        }
        for label, (left, right) in contrast_pairs.items()
    }

    primary_acid = contrasts["cider_tail_minus_acid"]
    primary_b0 = contrasts["cider_tail_minus_b0"]
    primary_shuffled = contrasts["cider_tail_minus_cider_shuffled"]
    gates = {
        "1_cider_tail_higher_equal_task_than_primary_acid": primary_acid["equal_task"]["estimate"] > 0,
        "2_cider_tail_higher_equal_task_than_b0": primary_b0["equal_task"]["estimate"] > 0,
        "3_cider_tail_not_below_acid_by_more_than_0_05_any_task": all(
            primary_acid["per_task"][task]["estimate"] >= -NONINFERIORITY_MARGIN for task in TASKS
        ),
        "4_cider_tail_not_below_b0_by_more_than_0_05_any_task": all(
            primary_b0["per_task"][task]["estimate"] >= -NONINFERIORITY_MARGIN for task in TASKS
        ),
        "5_cider_tail_exceeds_bit_identical_cider_shuffled": (
            primary_shuffled["equal_task"]["estimate"] > 0
            and all(
                matrices[task]["cider_shuffled"].tobytes() == matrices[task]["b0"].tobytes()
                for task in TASKS
            )
        ),
    }
    diffusion_specific = {
        "higher_than_deterministic_inverse_equal_task": contrasts["cider_tail_minus_deterministic_inverse"]["equal_task"]["estimate"] > 0,
        "higher_than_gaussian_tail_equal_task": contrasts["cider_tail_minus_gaussian_tail"]["equal_task"]["estimate"] > 0,
        "lower_bound_vs_deterministic_inverse_above_minus_0_05": contrasts["cider_tail_minus_deterministic_inverse"]["equal_task"]["lower_95_one_sided"] > -NONINFERIORITY_MARGIN,
        "lower_bound_vs_gaussian_tail_above_minus_0_05": contrasts["cider_tail_minus_gaussian_tail"]["equal_task"]["lower_95_one_sided"] > -NONINFERIORITY_MARGIN,
    }
    strong_acid = {
        f"higher_than_{arm}_equal_task": contrasts[f"cider_tail_minus_{arm}"]["equal_task"]["estimate"] > 0
        for arm in ("acid_flow", "acid_16_mean", "acid_16_min")
    }
    weight_robustness = {
        "cider": {
            "l002_not_worse_than_primary_by_more_than_0_05": contrasts["cider_tail_l002_minus_cider_tail"]["equal_task"]["estimate"] >= -NONINFERIORITY_MARGIN,
            "l014_not_worse_than_primary_by_more_than_0_05": contrasts["cider_tail_l014_minus_cider_tail"]["equal_task"]["estimate"] >= -NONINFERIORITY_MARGIN,
        },
        "acid": {
            "l002_minus_primary": contrasts["acid_l002_minus_acid"],
            "l014_minus_primary": contrasts["acid_l014_minus_acid"],
        },
    }
    all_pass = all(gates.values())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_table = args.output_dir / "runs.tsv"
    write_runs_table(run_table, loaded)
    result = {
        "status": "ok",
        "kind": "acid_alt_e4_d2b_closed_loop_analysis",
        "analysis_role": "post_e4_d2a_authorized_closed_loop_exploratory_development",
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "levels": levels,
        "contrasts": contrasts,
        "exact_paired_discordant_counts": discordance,
        "gates": gates,
        "all_d2b_advancement_gates_pass": all_pass,
        "decision": "advance_to_e4_m" if all_pass else "stop_e4_d2b",
        "development_labels": {
            "diffusion_specific": diffusion_specific,
            "diffusion_specific_signal": all(diffusion_specific.values()),
            "strong_acid": strong_acid,
            "strong_acid_signal": all(strong_acid.values()),
            "weight_robustness": weight_robustness,
            "weight_robustness_signal": all(weight_robustness["cider"].values()),
        },
        "isolated_d2a_scorer_latency": isolated_d2a_latencies,
        "confirmation_claim_allowed": False,
        "publication_claim_allowed": False,
        "alternative_to_acid_claim_allowed": False,
        "protected_c1_i1_read": False,
        "run_inputs": {
            f"{task}/{arm}": {key: value for key, value in loaded[(task, arm)].items() if key not in {"success", "starts"}}
            for task in TASKS for arm in d2b.ARMS
        },
        "runs_tsv": str(run_table),
        "runs_tsv_sha256": sha256_file(run_table),
        "parent_protocol": str(args.parent_protocol),
        "parent_protocol_sha256": parent_protocol_sha256,
        "d2b_freeze": str(args.d2b_freeze),
        "d2b_freeze_sha256": d2b_freeze_sha256,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": source_manifest_sha256,
        "d2a_implementation_freeze": str(args.d2a_implementation_freeze),
        "d2a_implementation_freeze_sha256": d2a_implementation_freeze_sha256,
        "d2a_source_manifest": str(args.d2a_source_manifest),
        "d2a_source_manifest_sha256": d2a_source_manifest_sha256,
        "d2a_summary": str(args.d2a_summary),
        "d2a_summary_sha256": d2a_summary_sha256,
        "d2b_authorization": str(args.d2b_authorization),
        "d2b_authorization_sha256": authorization_sha256,
    }
    summary_path = args.output_dir / "summary.json"
    atomic_json(summary_path, result)
    atomic_json(
        args.output_dir / "manifest.json",
        {
            "status": "ok",
            "kind": "acid_alt_e4_d2b_closed_loop_manifest",
            "summary": str(summary_path),
            "summary_sha256": sha256_file(summary_path),
            "runs_tsv_sha256": sha256_file(run_table),
            "all_d2b_advancement_gates_pass": all_pass,
            "parent_protocol_sha256": parent_protocol_sha256,
            "d2b_freeze_sha256": d2b_freeze_sha256,
            "source_manifest_sha256": source_manifest_sha256,
            "d2a_implementation_freeze_sha256": d2a_implementation_freeze_sha256,
            "d2a_source_manifest_sha256": d2a_source_manifest_sha256,
            "d2a_summary_sha256": d2a_summary_sha256,
            "d2b_authorization_sha256": authorization_sha256,
            "confirmation_claim_allowed": False,
            "publication_claim_allowed": False,
            "alternative_to_acid_claim_allowed": False,
            "protected_c1_i1_read": False,
        },
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
