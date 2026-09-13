"""Read-only physical failure decomposition of the completed 450-shard grid.

Requires the original raw trajectory archive. Never reads stage-1/stage-2
payloads, never reruns a planner, and refuses output inside the input study.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import hashlib
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

from diffusion_bottleneck import (
    ARMS, HORIZONS, SEEDS, N, LOCK_SHA, SUMMARY_SHA, SCOPE, SOURCE_COMMIT,
    IntegrityError, checked_archive, checked_child, read_json, require,
    require_sha, sha256, trajectory_diagnostics, write_report,
)


def expected_tasks() -> list[dict[str, Any]]:
    rows = []
    for arm in ARMS:
        for seed in SEEDS:
            for begin in range(0, N, 64):
                rows.append(dict(task=len(rows), arm=arm, seed=seed,
                                 begin=begin, end=min(begin + 64, N)))
    return rows


def sealed_stage(study: Path) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any]]:
    """Validate every expected stage-0 result hash before opening any result."""
    require_sha(study / "INPUT-LOCK.json", LOCK_SHA)
    lock = read_json(study / "INPUT-LOCK.json")
    require_sha(study / "CONFIG.json", lock["config_sha256"])
    require_sha(study / "REGISTRY.json", lock["registry_sha256"])
    config, registry = read_json(study / "CONFIG.json"), read_json(study / "REGISTRY.json")
    require(config["arms"] == list(ARMS), "Arm order mismatch")
    require(config["training_seed_blocks"] == list(SEEDS), "Seed order mismatch")
    require(config["horizons"] == list(HORIZONS), "Horizon order mismatch")
    tasks = expected_tasks()
    require(registry["stages"][0] == tasks, "Stage-0 registry differs from fixed exposed grid")
    files = []
    for task in tasks:
        root = study / "stage-0" / f'task-{task["task"]:04d}'
        done = read_json(root / "DONE.json")
        require(done["task"] == task, "Task identity mismatch")
        require(done["config_sha256"] == lock["config_sha256"], "Task config mismatch")
        require(done["source_manifest_sha256"] == lock["source_manifest_sha256"], "Task source mismatch")
        result = root / "results" / "RESULT.json"
        require_sha(result, done["result_sha256"])
        files.append((result, task))
    return files, lock


def reduce_traces(study: Path) -> dict[str, Any]:
    tensor, summary = checked_archive(study / "analysis-0")
    files, lock = sealed_stage(study)
    require_sha(study / 'collection/COLLECTION.json', lock['collection_sha256'])
    collection = read_json(study / 'collection/COLLECTION.json')
    reference_data = {}
    for i, ref in enumerate(collection['records'][:N]):
        require(ref['index'] == i, 'Reference ordering mismatch')
        path = checked_child(study / 'collection', ref['file'])
        require_sha(path, ref['sha256'])
        with np.load(path, allow_pickle=False) as data:
            reference_data[i] = (data['initial_request'].copy(),
                                 data['states'][75].copy(), data['states'][150].copy())
    require(len(reference_data) == N, 'Reference completeness')
    seed_categories = defaultdict(Counter)
    categories: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    numerical: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[int, int, int, str]] = set()
    initial_identity, goal_identity, model_identity = {}, {}, {}
    inspected_bytes = 0
    for path, task in files:
        result = read_json(path)
        require(result.get("completed") is True and result.get("pilot") is False, "Incomplete/pilot result")
        require(result.get("models_unchanged") is True, "Model changed during evaluation")
        require(result["arm"] == task["arm"] and result["train_seed"] == task["seed"], "Result identity mismatch")
        require(result["action_rule"] == "native_finite", "Wrong historical action rule")
        require(result["collection_sha256"] == lock["collection_sha256"], "Collection identity mismatch")
        group = (task["arm"], task["seed"])
        require(model_identity.setdefault(group, result["model_state_sha256"]) == result["model_state_sha256"], "Checkpoint group mismatch")
        rows = result["rows"]
        expected = {(i, h) for i in range(task["begin"], task["end"]) for h in HORIZONS}
        require(len(rows) == len(expected), "Wrong row count")
        require({(r["reference_index"], r["horizon"]) for r in rows} == expected, "Missing/duplicate row")
        for row in rows:
            i, h, seed, arm = row["reference_index"], row["horizon"], row["train_seed"], row["arm"]
            key = (i, h, seed, arm)
            require(key not in seen and 0 <= i < N, "Duplicate or unexposed reference")
            seen.add(key)
            require(arm == task["arm"] and seed == task["seed"], "Row arm/seed mismatch")
            require(row["budget"] == 2 * h, "Changed action budget")
            ref = collection['records'][i]
            require(row['reference_attempt'] == ref['attempt'], 'Reference attempt mismatch')
            seed_text = f'independent-pusht-reference-v1|{collection["namespace"]}|{ref["attempt"]}|planner|h={h}|seed={seed}'
            expected_seed = int.from_bytes(hashlib.sha256(seed_text.encode()).digest()[:4], 'little')
            require(row['seed'] == expected_seed, 'Planner RNG identity mismatch')
            require(initial_identity.setdefault((i, h), row["initial_hash"]) == row["initial_hash"], "Unpaired initial inputs")
            trajectory = checked_child(path.parent, row["trajectory_file"])
            require_sha(trajectory, row["trajectory_sha256"])
            inspected_bytes += trajectory.stat().st_size
            with np.load(trajectory, allow_pickle=False) as data:
                require(set(data.files) == {"states", "actions", "raw_actions", "goal_state"}, "Unknown trajectory schema")
                states, actions, raw, goal = (data[k].copy() for k in ("states", "actions", "raw_actions", "goal_state"))
            delivered = row["delivered"]
            require(isinstance(delivered, int) and 0 <= delivered <= 2 * h, "Bad delivered-action count")
            require(states.shape == (delivered + 1, 7) and actions.shape == raw.shape == (delivered, 2), "Trace count mismatch")
            require(bool(np.isfinite(actions).all() and np.isfinite(raw).all()), "Nonfinite action")
            require(bool(np.array_equal(actions, raw)), "Unexpected action clipping")
            np.testing.assert_allclose(states[0], reference_data[i][0], rtol=0, atol=1e-10)
            np.testing.assert_array_equal(goal, reference_data[i][1 if h == 75 else 2])
            # Shared actual starts/goals are checked across all methods and fixed blocks.
            identity = hashlib_array(states[0]) + hashlib_array(goal)
            require(goal_identity.setdefault((i, h), identity) == identity, "Physical start/goal pairing mismatch")
            metrics = trajectory_diagnostics(states, goal)
            independent = independent_physical_success(states, goal)
            require(independent == metrics['success'], 'Independent physical predicate disagreement')
            recorded = tensor[i, HORIZONS.index(h), SEEDS.index(seed), ARMS.index(arm)]
            require(int(metrics["success"]) == row["success"] == recorded, "Physical success disagrees with sealed outcome")
            if metrics["success"]:
                require(metrics["first_success_step"] == delivered, "Execution continued after success")
            failure = row["failure"]
            if failure is not None:
                require(not metrics["success"], "Planner failure marked successful")
            else:
                require(delivered > 0, "No action without planner failure")
                require([c["at"] for c in row["calls"]] == list(range(0, delivered, 15)), "Replan positions mismatch")
                if not metrics["success"]:
                    require(row["native_truncation"] or delivered == 2 * h, "Unexplained early stop")
            k = (arm, h)
            categories[k]["planner_failure" if failure is not None else metrics["terminal_category"]] += 1
            category = 'planner_failure' if failure is not None else metrics['terminal_category']
            sk = (arm, h, seed)
            seed_categories[sk][category] += 1
            seed_categories[sk]['runs'] += 1
            if row['native_truncation']:
                categories[k]['native_truncation_flag'] += 1
                seed_categories[sk]['native_truncation_flag'] += 1
                if not metrics['success']:
                    categories[k]['native_truncation_without_success'] += 1
                    seed_categories[sk]['native_truncation_without_success'] += 1
            if not metrics["success"] and metrics.get("ever_block_pose_within_component_thresholds", False):
                categories[k]["supplement_block_pose_reached_but_joint_success_failed"] += 1
            if metrics.get("ever_individual_positions_both_within_20_but_joint_outside", False):
                categories[k]["supplement_component_thresholds_not_joint_threshold"] += 1
            for name in ("closest_joint_margin", "agent_distance_at_closest", "block_distance_at_closest", "angle_error_at_closest"):
                if name in metrics:
                    numerical[k][name].append(float(metrics[name]))
            require(np.isfinite(row["wall_seconds"]) and row["wall_seconds"] >= 0, "Invalid elapsed time")
            numerical[k]["episode_loop_wall_seconds"].append(float(row["wall_seconds"]))
            for call in row["calls"]:
                require(np.isfinite(call["seconds"]) and call["seconds"] >= 0, "Invalid solver time")
                numerical[k]["timed_solver_seconds"].append(float(call["seconds"]))
    require(len(seen) == 57600, "Incomplete physical grid")
    require(len(seed_categories) == 36 and all(v['runs'] == N for v in seed_categories.values()),
            'Incomplete arm/horizon/seed blocks')
    groups = {}
    for (arm, h), counts in sorted(categories.items()):
        terminal_sum = sum(counts[name] for name in (
            "joint_success", "angle_only_miss", "joint_position_only_miss", "both_miss", "planner_failure"))
        require(terminal_sum == N * 3, "Terminal categories are not exhaustive/disjoint")
        groups[f"{arm}/h{h}"] = {
            "paired_measurements": N * 3, "counts": dict(counts),
            "descriptive_values": {name: {"n": len(v), "mean": float(np.mean(v)),
                                          "median": float(np.median(v)), "p90": float(np.quantile(v, .9))}
                                   for name, v in numerical[(arm, h)].items()},
        }
    return {
        "scope": SCOPE, "source_commit": SOURCE_COMMIT, "summary_sha256": SUMMARY_SHA,
        "historical_decision_unchanged": summary["decision"],
        "raw_trajectories_read": len(seen), "trajectory_bytes_verified": inspected_bytes,
        "verified_shards": len(files), "model_runs": 0, "groups": groups,
        "per_arm_horizon_seed_counts": {f'{a}/h{h}/seed{s}':dict(v)
                                       for (a,h,s),v in sorted(seed_categories.items())},
        "technical_invalid_records": 0,
        "independent_scalar_predicate_checked": True,
        "reference_requests_and_planner_seeds_checked": True,
        "goal_rule": "norm of joint [agent_xy,block_xy] error <20 AND wrapped angle error <pi/9 at the SAME post-action step",
        "interpretation": "Failure categories are descriptive outcomes, not proofs of causes. Supplement counts overlap terminal categories.",
        "timing_scope": "Episode-loop time excludes initialization. Solver calls exclude some preprocessing. No equal-compute or deployment-latency claim.",
        "unevaluated_reference_payloads_read": 0,
    }


def independent_physical_success(states, goal):
    """Scalar math implementation; no vector reducer or historical helper call.

Uses squared joint-position distance and modular angular distance. Canonical
input-angle validation is intentionally delegated to the strict first check;
this second computation must not silently normalize invalid historical input.
"""
    for state in states[1:]:
        squared = math.fsum((float(state[j])-float(goal[j]))**2 for j in range(4))
        angle = (float(state[4])-float(goal[4])+math.pi) % (2*math.pi)-math.pi
        if squared < 400 and abs(angle) < math.pi/9:
            return True
    return False


def hashlib_array(value: np.ndarray) -> str:
    # Cross-method values are compared at their actual saved dtype and bytes.
    import hashlib
    x = np.ascontiguousarray(value)
    return hashlib.sha256(str(x.dtype).encode() + str(x.shape).encode() + x.tobytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # Check output boundary before expensive reads.
        root, output = args.study.resolve(), args.out.resolve()
        require(output != root and root not in output.parents, "Output inside original study")
        require(not args.out.exists(), "Output already exists")
        result = reduce_traces(args.study)
        result["program_sha256"] = sha256(Path(__file__))
        write_report(args.out, result, (args.study,))
        print(json.dumps({"written": str(args.out), "raw_trajectories_read": result["raw_trajectories_read"]}))
        return 0
    except (IntegrityError, OSError, ValueError, KeyError, AssertionError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
