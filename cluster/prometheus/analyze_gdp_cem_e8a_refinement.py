#!/usr/bin/env python3
"""Apply the frozen cross-task E8A Gaussian-refinement selection rule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from acid_alternative.io_utils import atomic_write_json, sha256_file


TASKS = ("pusht", "reacher", "cube")
RESTARTS = (10, 20, 40)
REVERSE_STEPS = (1, 5, 10)
FRACTIONS = (0.25, 0.50, 0.75, 1.00)
PROTOCOL_SHA256 = "e6ad569e0313276bff2cf79835bcd53c4b1604113b34bacdb5004a4bae034141"
E7_AGGREGATE_SHA256 = (
    "bcd49f6fa7b7d1b03d8f95b4d46001e08b97c4725b43a55a953afc4ebe25544d"
)
REQUIRED_METRICS = {
    "selected_action_mse",
    "oracle_action_mse",
    "minimum_goal_cost",
    "candidate_variance",
    "unique_candidates",
    "boundary_fraction",
    "refinement_displacement_mse",
    "generation_seconds",
    "rollout_seconds",
}


def label(condition: str, restart: int, reverse_steps: int, fraction: float) -> str:
    return (
        f"{condition}_r{restart}_k{reverse_steps}_q{int(fraction * 100):02d}"
    )


def expected_labels() -> set[str]:
    return {"gaussian_base"} | {
        label(condition, restart, reverse_steps, fraction)
        for condition in ("true", "shuffled")
        for restart in RESTARTS
        for reverse_steps in REVERSE_STEPS
        for fraction in FRACTIONS
    }


def load_task(path: Path, task: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e8a_p1_refinement_task"
        or value.get("analysis_role") != "P1_disjoint_validation_method_rescue"
        or value.get("task") != task
        or value.get("context_count") != 512
        or value.get("candidate_count") != 300
        or value.get("restarts") != list(RESTARTS)
        or value.get("reverse_steps") != list(REVERSE_STEPS)
        or value.get("refined_fractions") != list(FRACTIONS)
        or value.get("refined_candidate_counts")
        != {
            f"{fraction:.2f}": int(round(299 * fraction))
            for fraction in FRACTIONS
        }
        or value.get("protocol_sha256") != PROTOCOL_SHA256
        or value.get("e7_aggregate_sha256") != E7_AGGREGATE_SHA256
        or value.get("e7_decision")
        != "stop_goal_conditioned_diffusion_proposal_before_d2"
        or value.get("excluded_e7_selection_count") != 256
        or value.get("excluded_training_validation_count") != 8192
        or value.get("row_selection", {}).get("selected_rows_count") != 512
        or value.get("row_selection", {}).get("selected_rows_sha256")
        != value.get("fresh_rows_sha256")
        or set(value.get("normalization", {}))
        != {
            "latent_mean",
            "latent_std",
            "action_mean",
            "action_std",
            "robust_low",
            "robust_high",
            "normalized_low",
            "normalized_high",
        }
        or set(value.get("rng_namespaces", {}))
        != {
            "e7_selection_numpy",
            "training_validation_numpy",
            "e8a_selection_numpy",
            "gaussian_base_torch_template",
            "refinement_noise_torch_template",
            "numpy_selection_derivation",
            "torch_derivation",
        }
        or not isinstance(value.get("cosine_alpha_bar_sha256"), str)
        or len(value.get("cosine_alpha_bar_sha256", "")) != 64
        or value.get("determinism_preflight", {}).get("status") != "ok"
        or value.get("determinism_preflight", {}).get("base_repeat_max_abs") != 0.0
        or value.get("determinism_preflight", {}).get(
            "refinement_repeat_max_abs"
        )
        != 0.0
        or value.get("real_stack_equivalence", {}).get("status") != "ok"
        or value.get("d2_read") is not False
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"E8A task identity differs: {path}")
    expected_rng = {
        "e7_selection_numpy": (
            f"gdp-cem-e7p-selection|task={task}|seed=2026081702"
        ),
        "training_validation_numpy": f"gdp-e7p-validation-rows|{task}|6101",
        "e8a_selection_numpy": (
            f"gdp-cem-e8a-selection|task={task}|seed=2026081703"
        ),
        "gaussian_base_torch_template": (
            f"gdp-e8a-base|task={task}|row={{row}}|seed=6101"
        ),
        "refinement_noise_torch_template": (
            f"gdp-e8a-refine|task={task}|row={{row}}|"
            "restart={restart}|seed=6101"
        ),
        "numpy_selection_derivation": "first_64_sha256_bits_big_endian",
        "torch_derivation": "first_64_sha256_bits_little_endian_mod_2^63_minus_1",
    }
    if value["rng_namespaces"] != expected_rng:
        raise RuntimeError(f"E8A RNG namespaces differ: {path}")
    for key, record in value["normalization"].items():
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("shape"), list)
            or record.get("dtype") != "float32"
            or not isinstance(record.get("sha256"), str)
            or len(record["sha256"]) != 64
            or (key.startswith("latent_") and record["shape"] != [192])
        ):
            raise RuntimeError(f"E8A normalization record differs for {key}: {path}")
    per_task = value.get("per_task_medians")
    if not isinstance(per_task, dict) or set(per_task) != expected_labels():
        raise RuntimeError(f"E8A task configuration grid differs: {path}")
    for item_label, metrics in per_task.items():
        if not isinstance(metrics, dict) or not REQUIRED_METRICS.issubset(metrics):
            raise RuntimeError(f"E8A task metrics missing for {item_label}: {path}")
        required_values = np.asarray(
            [float(metrics[key]) for key in REQUIRED_METRICS], dtype=np.float64
        )
        if not np.isfinite(required_values).all():
            raise RuntimeError(f"E8A task metrics non-finite for {item_label}: {path}")
    detail = Path(value["per_context"])
    if not detail.is_file() or sha256_file(detail) != value.get("per_context_sha256"):
        raise RuntimeError(f"E8A task detail hash differs: {task}")
    return value


def equal_task(
    tasks: dict[str, dict[str, Any]], item_label: str, metric: str
) -> float:
    return float(
        np.mean(
            [
                float(tasks[task]["per_task_medians"][item_label][metric])
                for task in TASKS
            ]
        )
    )


def configuration_record(
    tasks: dict[str, dict[str, Any]],
    *,
    restart: int,
    reverse_steps: int,
    fraction: float,
) -> dict[str, Any]:
    true_label = label("true", restart, reverse_steps, fraction)
    shuffled_label = label("shuffled", restart, reverse_steps, fraction)
    base_label = "gaussian_base"
    metrics = {}
    for metric in (
        "selected_action_mse",
        "oracle_action_mse",
        "minimum_goal_cost",
        "candidate_variance",
        "unique_candidates",
        "boundary_fraction",
        "refinement_displacement_mse",
        "generation_seconds",
        "rollout_seconds",
    ):
        metrics[metric] = {
            "true": equal_task(tasks, true_label, metric),
            "shuffled": equal_task(tasks, shuffled_label, metric),
            "gaussian_base": equal_task(tasks, base_label, metric),
        }
    selected_task_wins = sum(
        tasks[task]["per_task_medians"][true_label]["selected_action_mse"]
        < tasks[task]["per_task_medians"][shuffled_label]["selected_action_mse"]
        and tasks[task]["per_task_medians"][true_label]["selected_action_mse"]
        < tasks[task]["per_task_medians"][base_label]["selected_action_mse"]
        for task in TASKS
    )
    goal_task_wins = sum(
        tasks[task]["per_task_medians"][true_label]["minimum_goal_cost"]
        < tasks[task]["per_task_medians"][shuffled_label]["minimum_goal_cost"]
        and tasks[task]["per_task_medians"][true_label]["minimum_goal_cost"]
        < tasks[task]["per_task_medians"][base_label]["minimum_goal_cost"]
        for task in TASKS
    )
    gates = {
        "true_beats_shuffled_and_gaussian_selected_equal_task": (
            metrics["selected_action_mse"]["true"]
            < metrics["selected_action_mse"]["shuffled"]
            and metrics["selected_action_mse"]["true"]
            < metrics["selected_action_mse"]["gaussian_base"]
        ),
        "true_beats_shuffled_and_gaussian_goal_equal_task": (
            metrics["minimum_goal_cost"]["true"]
            < metrics["minimum_goal_cost"]["shuffled"]
            and metrics["minimum_goal_cost"]["true"]
            < metrics["minimum_goal_cost"]["gaussian_base"]
        ),
        "true_beats_shuffled_oracle_equal_task": (
            metrics["oracle_action_mse"]["true"]
            < metrics["oracle_action_mse"]["shuffled"]
        ),
        "true_oracle_within_2pct_gaussian_equal_task": (
            metrics["oracle_action_mse"]["true"]
            <= 1.02 * metrics["oracle_action_mse"]["gaussian_base"]
        ),
        "selected_wins_on_at_least_two_tasks": selected_task_wins >= 2,
        "goal_wins_on_at_least_two_tasks": goal_task_wins >= 2,
        "boundary_within_005_gaussian_equal_task": (
            metrics["boundary_fraction"]["true"]
            <= metrics["boundary_fraction"]["gaussian_base"] + 0.05
        ),
        "positive_finite_variance_all_tasks": all(
            np.isfinite(
                tasks[task]["per_task_medians"][true_label]["candidate_variance"]
            )
            and tasks[task]["per_task_medians"][true_label]["candidate_variance"]
            > 0.0
            for task in TASKS
        ),
        "at_least_95pct_unique_all_tasks": all(
            tasks[task]["per_task_medians"][true_label]["unique_candidates"]
            >= 285
            for task in TASKS
        ),
    }
    per_task = {
        task: {
            "selected_true_minus_shuffled": tasks[task]["per_task_medians"][
                true_label
            ]["selected_action_mse"]
            - tasks[task]["per_task_medians"][shuffled_label][
                "selected_action_mse"
            ],
            "selected_true_minus_gaussian": tasks[task]["per_task_medians"][
                true_label
            ]["selected_action_mse"]
            - tasks[task]["per_task_medians"][base_label]["selected_action_mse"],
            "goal_true_minus_shuffled": tasks[task]["per_task_medians"][true_label][
                "minimum_goal_cost"
            ]
            - tasks[task]["per_task_medians"][shuffled_label]["minimum_goal_cost"],
            "goal_true_minus_gaussian": tasks[task]["per_task_medians"][true_label][
                "minimum_goal_cost"
            ]
            - tasks[task]["per_task_medians"][base_label]["minimum_goal_cost"],
        }
        for task in TASKS
    }
    return {
        "restart_timestep": restart,
        "reverse_evaluations": reverse_steps,
        "refined_fraction": fraction,
        "labels": {"true": true_label, "shuffled": shuffled_label},
        "equal_task_metrics": metrics,
        "selected_task_wins": selected_task_wins,
        "goal_task_wins": goal_task_wins,
        "per_task_contrasts": per_task,
        "gates": gates,
        "eligible": all(gates.values()),
    }


def choose_configuration(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [record for record in records if record["eligible"]]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda record: (
            record["equal_task_metrics"]["selected_action_mse"]["true"],
            record["equal_task_metrics"]["minimum_goal_cost"]["true"],
            record["reverse_evaluations"],
            record["restart_timestep"],
            record["refined_fraction"],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-summary", nargs=2, action="append", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("E8A aggregate protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E8A aggregate output")
    paths = {task: Path(path) for task, path in args.task_summary}
    if set(paths) != set(TASKS):
        raise RuntimeError("E8A aggregate requires all three tasks")
    tasks = {task: load_task(paths[task], task) for task in TASKS}
    source_hash = sha256_file(args.source_manifest)
    if {tasks[task]["source_manifest_sha256"] for task in TASKS} != {source_hash}:
        raise RuntimeError("E8A task source snapshots differ")

    records = [
        configuration_record(
            tasks,
            restart=restart,
            reverse_steps=reverse_steps,
            fraction=fraction,
        )
        for restart in RESTARTS
        for reverse_steps in REVERSE_STEPS
        for fraction in FRACTIONS
    ]
    selected = choose_configuration(records)
    result = {
        "status": "ok",
        "kind": "gdp_cem_e8a_p1_refinement_aggregate",
        "analysis_role": "P1_disjoint_validation_method_rescue",
        "configuration_table": records,
        "eligible_configuration_count": sum(record["eligible"] for record in records),
        "selected_configuration": (
            {
                "restart_timestep": selected["restart_timestep"],
                "reverse_evaluations": selected["reverse_evaluations"],
                "refined_fraction": selected["refined_fraction"],
                "labels": selected["labels"],
                "equal_task_metrics": selected["equal_task_metrics"],
                "gates": selected["gates"],
            }
            if selected is not None
            else None
        ),
        "e8a_p1_gate_pass": selected is not None,
        "decision": (
            "authorize_separately_frozen_exposed_d2_gadr_diagnostic"
            if selected is not None
            else "stop_gaussian_anchored_diffusion_refinement_before_d2"
        ),
        "task_summaries": {
            task: {"path": str(paths[task]), "sha256": sha256_file(paths[task])}
            for task in TASKS
        },
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": source_hash,
        "d2_read": False,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(args.output_dir / "summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
