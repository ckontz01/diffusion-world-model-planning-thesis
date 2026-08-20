#!/usr/bin/env python3
"""Apply the frozen cross-task GDP-CEM P1-selection rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from acid_alternative.io_utils import atomic_write_json, sha256_file


TASKS = ("pusht", "reacher", "cube")
DDIM_STEPS = (5, 10, 20)
FRACTIONS = (0.25, 0.50, 0.75, 1.00)
PROTOCOL_SHA256 = "3c7ff146a43bb5d87e99d92dff0f9731f7ea4b186aedaec168db284ad744dbbc"


def load_task(path: Path, task: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind") != "gdp_cem_e7p_p1_selection_task"
        or value.get("analysis_role") != "P1_validation_only_method_selection"
        or value.get("task") != task
        or value.get("context_count") != 256
        or value.get("candidate_count") != 300
        or value.get("ddim_steps") != list(DDIM_STEPS)
        or value.get("proposal_fractions") != list(FRACTIONS)
        or value.get("protocol_sha256") != PROTOCOL_SHA256
        or value.get("real_stack_equivalence", {}).get("status") != "ok"
        or value.get("determinism_preflight", {}).get("status") != "ok"
        or value.get("d2_read") is not False
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
    ):
        raise RuntimeError(f"GDP-CEM P1 task result differs: {path}")
    raw = Path(value["per_context"])
    if not raw.is_file() or sha256_file(raw) != value.get("per_context_sha256"):
        raise RuntimeError(f"GDP-CEM P1 task detail hash differs: {task}")
    return value


def equal_task(
    tasks: dict[str, dict[str, Any]], label: str, metric: str
) -> float:
    return float(
        np.mean(
            [tasks[task]["per_task_medians"][label][metric] for task in TASKS]
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-summary", nargs=2, action="append", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256_file(args.protocol) != PROTOCOL_SHA256:
        raise RuntimeError("GDP-CEM P1 aggregate protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty GDP-CEM P1 aggregate output")
    paths = {task: Path(path) for task, path in args.task_summary}
    if set(paths) != set(TASKS):
        raise RuntimeError("GDP-CEM P1 aggregate requires all three tasks")
    tasks = {task: load_task(paths[task], task) for task in TASKS}
    source_hashes = {tasks[task]["source_manifest_sha256"] for task in TASKS}
    if len(source_hashes) != 1 or source_hashes != {sha256_file(args.source_manifest)}:
        raise RuntimeError("GDP-CEM P1 task source snapshots differ")

    step_table = {}
    eligible_steps = []
    for steps in DDIM_STEPS:
        true_label = f"select_diffusion_true_ddim{steps}"
        shuffled_label = f"select_diffusion_shuffled_goal_ddim{steps}"
        true_selected = equal_task(tasks, true_label, "selected_action_mse")
        shuffled_selected = equal_task(tasks, shuffled_label, "selected_action_mse")
        true_oracle = equal_task(tasks, true_label, "oracle_action_mse")
        shuffled_oracle = equal_task(tasks, shuffled_label, "oracle_action_mse")
        eligible = true_selected < shuffled_selected and true_oracle < shuffled_oracle
        step_table[str(steps)] = {
            "true_selected_action_mse": true_selected,
            "shuffled_selected_action_mse": shuffled_selected,
            "true_oracle_action_mse": true_oracle,
            "shuffled_oracle_action_mse": shuffled_oracle,
            "eligible": eligible,
        }
        if eligible:
            eligible_steps.append(steps)
    selected_steps = (
        min(
            eligible_steps,
            key=lambda steps: (
                step_table[str(steps)]["true_selected_action_mse"],
                steps,
            ),
        )
        if eligible_steps
        else None
    )

    fraction_table = {}
    selected_fraction = None
    if selected_steps is not None:
        for fraction in FRACTIONS:
            label = f"matched_diffusion_true_ddim{selected_steps}_q{int(fraction * 100):02d}"
            fraction_table[f"{fraction:.2f}"] = {
                "selected_action_mse": equal_task(tasks, label, "selected_action_mse"),
                "minimum_goal_cost": equal_task(tasks, label, "minimum_goal_cost"),
            }
        minimum_mse = min(
            value["selected_action_mse"] for value in fraction_table.values()
        )
        gaussian_goal = equal_task(tasks, "matched_gaussian_only", "minimum_goal_cost")
        qualified_fractions = [
            fraction
            for fraction in FRACTIONS
            if fraction_table[f"{fraction:.2f}"]["selected_action_mse"]
            <= 1.02 * minimum_mse
            and fraction_table[f"{fraction:.2f}"]["minimum_goal_cost"]
            <= gaussian_goal
        ]
        if qualified_fractions:
            selected_fraction = min(qualified_fractions)

    gates: dict[str, bool] = {
        "eligible_ddim_step_exists": selected_steps is not None,
        "matched_fraction_exists": selected_fraction is not None,
    }
    task_contrasts = {}
    if selected_steps is not None:
        true_label = f"select_diffusion_true_ddim{selected_steps}"
        shuffled_label = f"select_diffusion_shuffled_goal_ddim{selected_steps}"
        gaussian_label = "select_gaussian_true"
        true_selected = equal_task(tasks, true_label, "selected_action_mse")
        shuffled_selected = equal_task(tasks, shuffled_label, "selected_action_mse")
        true_oracle = equal_task(tasks, true_label, "oracle_action_mse")
        shuffled_oracle = equal_task(tasks, shuffled_label, "oracle_action_mse")
        gaussian_selected = equal_task(tasks, gaussian_label, "selected_action_mse")
        gates.update(
            {
                "true_beats_shuffled_selected_equal_task": true_selected
                < shuffled_selected,
                "true_beats_shuffled_oracle_equal_task": true_oracle
                < shuffled_oracle,
                "true_beats_gaussian_selected_equal_task": true_selected
                < gaussian_selected,
                "true_beats_shuffled_on_two_tasks": sum(
                    tasks[task]["per_task_medians"][true_label]["selected_action_mse"]
                    < tasks[task]["per_task_medians"][shuffled_label]["selected_action_mse"]
                    for task in TASKS
                )
                >= 2,
                "true_beats_gaussian_on_two_tasks": sum(
                    tasks[task]["per_task_medians"][true_label]["selected_action_mse"]
                    < tasks[task]["per_task_medians"][gaussian_label]["selected_action_mse"]
                    for task in TASKS
                )
                >= 2,
                "positive_variance_all_tasks": all(
                    np.isfinite(
                        tasks[task]["per_task_medians"][true_label]["candidate_variance"]
                    )
                    and tasks[task]["per_task_medians"][true_label]["candidate_variance"]
                    > 0
                    for task in TASKS
                ),
                "unique_candidates_all_tasks": all(
                    tasks[task]["per_task_medians"][true_label]["unique_candidates"]
                    >= 285
                    for task in TASKS
                ),
                "real_stack_equivalence_all_tasks": all(
                    tasks[task]["real_stack_equivalence"]["status"] == "ok"
                    for task in TASKS
                ),
                "determinism_preflight_all_tasks": all(
                    tasks[task]["determinism_preflight"]["status"] == "ok"
                    for task in TASKS
                ),
            }
        )
        for task in TASKS:
            task_contrasts[task] = {
                "true_minus_shuffled_selected_action_mse": tasks[task][
                    "per_task_medians"
                ][true_label]["selected_action_mse"]
                - tasks[task]["per_task_medians"][shuffled_label][
                    "selected_action_mse"
                ],
                "true_minus_gaussian_selected_action_mse": tasks[task][
                    "per_task_medians"
                ][true_label]["selected_action_mse"]
                - tasks[task]["per_task_medians"][gaussian_label][
                    "selected_action_mse"
                ],
            }
    direct_gate_names = [name for name in gates if name != "matched_fraction_exists"]
    direct_pass = all(gates[name] for name in direct_gate_names)
    matched_pass = direct_pass and gates["matched_fraction_exists"]
    result = {
        "status": "ok",
        "kind": "gdp_cem_e7p_p1_selection_aggregate",
        "analysis_role": "P1_validation_only_method_selection",
        "step_table": step_table,
        "selected_ddim_steps": selected_steps,
        "fraction_table": fraction_table,
        "selected_proposal_fraction": selected_fraction,
        "gates": gates,
        "gdp_select_p1_gate_pass": direct_pass,
        "matched_gdp_cem_p1_gate_pass": matched_pass,
        "task_contrasts": task_contrasts,
        "decision": (
            "authorize_exposed_d2_gdp_select_and_matched_gdp_cem"
            if matched_pass
            else "authorize_exposed_d2_gdp_select_only"
            if direct_pass
            else "stop_goal_conditioned_diffusion_proposal_before_d2"
        ),
        "task_summaries": {
            task: {"path": str(paths[task]), "sha256": sha256_file(paths[task])}
            for task in TASKS
        },
        "protocol_sha256": PROTOCOL_SHA256,
        "source_manifest_sha256": sha256_file(args.source_manifest),
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
