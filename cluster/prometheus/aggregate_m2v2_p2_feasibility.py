#!/usr/bin/env python3
"""Aggregate the prefrozen M2v2 P2 offline and paired closed-loop evidence."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy.stats import binomtest

from score_and_select_p2_true_scorers import atomic_json, sha256_file


WEIGHTS = (0.25, 0.5, 1.0, 2.0, 4.0)
POOL_COUNT = 12
TRAJECTORY_KEYS = (
    "high_plan_current_latent",
    "high_plan_subgoal_latent",
    "low_block_actual_latent",
    "low_block_subgoal_latent",
    "step_current_latent",
    "step_subgoal_latent",
    "final_state",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-job-id", type=int, required=True)
    parser.add_argument("--stablewm-home", type=Path, required=True)
    parser.add_argument("--pusht-offline-dir", type=Path, required=True)
    parser.add_argument("--tworoom-offline-dir", type=Path, required=True)
    parser.add_argument("--pusht-b0-root", type=Path, required=True)
    parser.add_argument("--tworoom-old-m2-root", type=Path, required=True)
    parser.add_argument("--pusht-context-manifest", type=Path, required=True)
    parser.add_argument("--tworoom-context-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_task(directory: Path, *, expected_method: str | None = None) -> tuple[dict[str, Any], Path]:
    manifest_path = directory / "manifest.json"
    h5_path = directory / "result.h5"
    if not manifest_path.is_file() or not h5_path.is_file():
        raise RuntimeError(f"missing closed-loop task: {directory}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "ok" or manifest.get("output_h5_sha256") != sha256_file(h5_path):
        raise RuntimeError(f"invalid closed-loop task: {directory}")
    if expected_method is not None and manifest.get("method") != expected_method:
        raise RuntimeError(f"method mismatch in {directory}")
    return manifest, h5_path


def trajectory_equal(first: Path, second: Path) -> bool:
    with h5py.File(first, "r") as left, h5py.File(second, "r") as right:
        return all(
            key in left and key in right and np.array_equal(left[key][:], right[key][:])
            for key in TRAJECTORY_KEYS
        )


def pusht_b0(args: argparse.Namespace) -> tuple[np.ndarray, list[Path], dict[str, Any]]:
    successes = []
    paths = []
    records = []
    for pool in range(POOL_COUNT):
        directory = args.pusht_b0_root / "arm-B0" / f"pool-{pool:02d}-task-{pool}"
        manifest, h5_path = load_task(directory)
        if manifest.get("arm") != "B0" or int(manifest["query"]["pool_index"]) != pool:
            raise RuntimeError("PushT B0 pool identity changed")
        successes.append(bool(manifest["episode_success"]))
        paths.append(h5_path)
        records.append({"pool_index": pool, "manifest_sha256": sha256_file(directory / "manifest.json"), "h5_sha256": manifest["output_h5_sha256"]})
    return np.asarray(successes, dtype=np.bool_), paths, {
        "source": "exact released nominal B0 array",
        "root": str(args.pusht_b0_root),
        "records": records,
    }


def tworoom_b0_surrogate(args: argparse.Namespace) -> tuple[np.ndarray, list[Path], dict[str, Any]]:
    successes = []
    paths = []
    verification = []
    for pool in range(POOL_COUNT):
        baseline_task = 60 + pool
        baseline_dir = args.tworoom_old_m2_root / "method-M2" / "weight-0.25" / f"pool-{pool:02d}-task-{baseline_task}"
        baseline_manifest, baseline_h5 = load_task(baseline_dir, expected_method="M2")
        all_identical = True
        all_success_equal = True
        for weight_index, weight in enumerate(WEIGHTS[1:], start=1):
            task = 60 + weight_index * 12 + pool
            current_dir = args.tworoom_old_m2_root / "method-M2" / f"weight-{weight}" / f"pool-{pool:02d}-task-{task}"
            current_manifest, current_h5 = load_task(current_dir, expected_method="M2")
            all_identical = all_identical and trajectory_equal(baseline_h5, current_h5)
            all_success_equal = all_success_equal and (
                bool(current_manifest["episode_success"]) == bool(baseline_manifest["episode_success"])
            )
        if not all_identical or not all_success_equal:
            raise RuntimeError("TwoRoom old M2 is not an exact non-interventional B0 surrogate")
        successes.append(bool(baseline_manifest["episode_success"]))
        paths.append(baseline_h5)
        verification.append({"pool_index": pool, "all_five_weight_trajectories_identical": all_identical, "all_five_weight_successes_identical": all_success_equal})
    return np.asarray(successes, dtype=np.bool_), paths, {
        "source": "audited old-M2 zero-slope exact nominal-cost surrogate",
        "root": str(args.tworoom_old_m2_root),
        "all_60_weight_pool_trajectories_reduce_to_12_identical_B0_trajectories": True,
        "verification": verification,
    }


def proportion_ci(successes: int, total: int) -> list[float]:
    interval = binomtest(successes, total).proportion_ci(confidence_level=0.95, method="exact")
    return [float(interval.low), float(interval.high)]


def paired_record(candidate: np.ndarray, comparator: np.ndarray) -> dict[str, Any]:
    wins = int(np.count_nonzero(candidate & ~comparator))
    losses = int(np.count_nonzero(~candidate & comparator))
    discordant = wins + losses
    return {
        "wins": wins,
        "losses": losses,
        "ties": int(len(candidate) - discordant),
        "net_wins": wins - losses,
        "exact_two_sided_p": (
            float(binomtest(wins, discordant, 0.5).pvalue) if discordant else 1.0
        ),
    }


def load_context(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    output: dict[str, Any] = {
        "source_manifest": str(path),
        "source_manifest_sha256": sha256_file(path),
        "selected_arms": {},
    }
    for method, selection in manifest["selections"].items():
        weight = float(selection["selected_weight"])
        records = sorted(
            (
                record
                for record in manifest["task_records"]
                if record["method"] == method and float(record["weight"]) == weight
            ),
            key=lambda record: int(record["pool_index"]),
        )
        if len(records) != POOL_COUNT or [int(r["pool_index"]) for r in records] != list(range(POOL_COUNT)):
            raise RuntimeError(f"incomplete selected {method} context in {path}")
        success = np.asarray([bool(record["episode_success"]) for record in records], dtype=np.bool_)
        if int(success.sum()) != int(selection["selected_success_count_of_12"]):
            raise RuntimeError(f"selected {method} context count mismatch in {path}")
        output["selected_arms"][method] = {
            "weight": weight,
            "success_count_of_12": int(success.sum()),
            "success_vector": success.tolist(),
        }
    return output


def environment_grid(
    args: argparse.Namespace,
    environment: str,
    b0_success: np.ndarray,
    b0_paths: list[Path],
) -> dict[str, Any]:
    root = args.stablewm_home / "derived" / "closed-loop-development" / f"{environment}-v1" / f"m2v2-grid-job-{args.grid_job_id}"
    offset = 0 if environment == "pusht" else 60
    weight_records = []
    all_span_pass = True
    any_changed_by_weight = []
    for weight_index, weight in enumerate(WEIGHTS):
        successes = []
        changed = []
        task_records = []
        for pool in range(POOL_COUNT):
            task = offset + weight_index * 12 + pool
            directory = root / f"weight-{weight}" / f"pool-{pool:02d}-task-{task}"
            manifest, h5_path = load_task(directory, expected_method="M2v2")
            if (
                manifest.get("environment") != environment
                or int(manifest["query"]["pool_index"]) != pool
                or float(manifest["weight"]) != weight
            ):
                raise RuntimeError("M2v2 grid query or weight identity changed")
            audit = manifest["cost"]["scorer_artifacts"]["online_population_audit"]
            span_pass = bool(audit["all_populations_passed_span_gate"])
            all_span_pass = all_span_pass and span_pass
            success = bool(manifest["episode_success"])
            trajectory_changed = not trajectory_equal(b0_paths[pool], h5_path)
            successes.append(success)
            changed.append(trajectory_changed)
            task_records.append(
                {
                    "pool_index": pool,
                    "episode_success": success,
                    "b0_success": bool(b0_success[pool]),
                    "trajectory_changed_from_B0": trajectory_changed,
                    "all_populations_passed_span_gate": span_pass,
                    "minimum_raw_score_span": float(audit["minimum_raw_score_span"]),
                    "minimum_unique_score_count": int(audit["minimum_unique_score_count"]),
                    "manifest_sha256": sha256_file(directory / "manifest.json"),
                    "h5_sha256": manifest["output_h5_sha256"],
                }
            )
        success_np = np.asarray(successes, dtype=np.bool_)
        changed_np = np.asarray(changed, dtype=np.bool_)
        comparison = paired_record(success_np, b0_success)
        record = {
            "weight": weight,
            "success_count_of_12": int(success_np.sum()),
            "success_vector": success_np.tolist(),
            "success_rate_exact_95ci": proportion_ci(int(success_np.sum()), POOL_COUNT),
            "paired_wins_vs_B0": comparison["wins"],
            "paired_losses_vs_B0": comparison["losses"],
            "paired_ties": comparison["ties"],
            "paired_net_wins": comparison["net_wins"],
            "paired_exact_two_sided_p": comparison["exact_two_sided_p"],
            "trajectory_changed_count": int(changed_np.sum()),
            "trajectory_changed_vector": changed_np.tolist(),
            "tasks": task_records,
        }
        weight_records.append(record)
        any_changed_by_weight.append(bool(changed_np.any()))
    selected_index = min(
        range(len(WEIGHTS)),
        key=lambda index: (
            -weight_records[index]["success_count_of_12"],
            -weight_records[index]["paired_net_wins"],
            WEIGHTS[index],
        ),
    )
    selected = weight_records[selected_index]
    return {
        "root": str(root),
        "B0_success_count_of_12": int(b0_success.sum()),
        "B0_success_vector": b0_success.tolist(),
        "B0_success_rate_exact_95ci": proportion_ci(int(b0_success.sum()), POOL_COUNT),
        "all_scored_populations_passed_span_gate": all_span_pass,
        "every_weight_changed_at_least_one_trajectory": bool(all(any_changed_by_weight)),
        "weight_records": weight_records,
        "selection_rule": [
            "greatest success count",
            "greatest paired wins minus losses against B0",
            "smaller weight",
        ],
        "selected_weight": selected["weight"],
        "selected_weight_index": selected_index,
        "selected_record": selected,
        "selected_gain_over_B0_successes": selected["success_count_of_12"] - int(b0_success.sum()),
    }


def load_offline(directory: Path) -> dict[str, Any]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    h5_path = directory / "audit.h5"
    if manifest.get("status") != "ok" or manifest.get("output_h5_sha256") != sha256_file(h5_path):
        raise RuntimeError(f"invalid M2v2 offline audit: {directory}")
    return manifest


def main() -> None:
    args = parse_args()
    output_json = args.output_dir / "manifest.json"
    if output_json.exists():
        raise SystemExit(f"refusing to overwrite M2v2 P2 decision: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    pusht_b0_success, pusht_b0_paths, pusht_b0_record = pusht_b0(args)
    tworoom_b0_success, tworoom_b0_paths, tworoom_b0_record = tworoom_b0_surrogate(args)
    closed_loop = {
        "pusht": environment_grid(args, "pusht", pusht_b0_success, pusht_b0_paths),
        "tworoom": environment_grid(args, "tworoom", tworoom_b0_success, tworoom_b0_paths),
    }
    offline = {
        "pusht": load_offline(args.pusht_offline_dir),
        "tworoom": load_offline(args.tworoom_offline_dir),
    }
    context = {
        "pusht": load_context(args.pusht_context_manifest),
        "tworoom": load_context(args.tworoom_context_manifest),
    }
    for environment in ("pusht", "tworoom"):
        selected_m2v2 = np.asarray(
            closed_loop[environment]["selected_record"]["success_vector"], dtype=np.bool_
        )
        for method, record in context[environment]["selected_arms"].items():
            record["paired_M2v2_vs_this_arm"] = paired_record(
                selected_m2v2, np.asarray(record["success_vector"], dtype=np.bool_)
            )

    within = {
        environment: float(
            offline[environment]["M2v2"]["metrics"]["pair_weighted_within_pool_auroc"]
        )
        for environment in ("pusht", "tworoom")
    }
    top4 = {
        environment: float(
            offline[environment]["M2v2"]["metrics"]["lowest_score_selection"]["top_4"][
                "baseline_minus_selected_failure_rate_mean"
            ]
        )
        for environment in ("pusht", "tworoom")
    }
    gains = {
        environment: int(closed_loop[environment]["selected_gain_over_B0_successes"])
        for environment in ("pusht", "tworoom")
    }
    gate = {
        "1_all_population_span_gates_pass": bool(
            all(closed_loop[e]["all_scored_populations_passed_span_gate"] for e in closed_loop)
        ),
        "2_offline_within_pool_auroc_above_chance_both": bool(all(value > 0.5 for value in within.values())),
        "3_top4_positive_one_nonnegative_other": bool(
            max(top4.values()) > 0.0 and min(top4.values()) >= 0.0
        ),
        "4_closed_loop_gain_at_least_two_one_loss_no_more_one_other": bool(
            max(gains.values()) >= 2 and min(gains.values()) >= -1
        ),
        "5_selected_arm_changes_trajectory_both": bool(
            all(closed_loop[e]["selected_record"]["trajectory_changed_count"] > 0 for e in closed_loop)
        ),
    }
    promising = bool(all(gate.values()))
    result = {
        "status": "ok",
        "classification": "m2v2_p2_prefrozen_feasibility_decision",
        "partition": "P1/P2-development-only",
        "reporting_rule": "exploratory redesign result; not P3/P4 confirmation",
        "operationally_promising_under_prefrozen_rule": promising,
        "decision": (
            "consider a separately frozen confirmation"
            if promising
            else "do not tune M2v2 repeatedly on P2; pivot to the diagnostic/comparative thesis or M3"
        ),
        "prefrozen_gate": gate,
        "offline_summary": {
            environment: {
                "within_pool_auroc": within[environment],
                "top4_failure_rate_reduction": top4[environment],
                "pool_bootstrap": offline[environment]["M2v2"]["pool_bootstrap"],
                "source_manifest_sha256": sha256_file(
                    (args.pusht_offline_dir if environment == "pusht" else args.tworoom_offline_dir) / "manifest.json"
                ),
            }
            for environment in ("pusht", "tworoom")
        },
        "closed_loop": closed_loop,
        "B0_sources": {"pusht": pusht_b0_record, "tworoom": tworoom_b0_record},
        "paired_existing_M1_M2_M3_P2_context": context,
        "spec": str(args.spec),
        "spec_sha256": sha256_file(args.spec),
        "grid_job_id": args.grid_job_id,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
