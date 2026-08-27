#!/usr/bin/env python3
"""Independently recompute and validate the sealed E18 aggregate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


TASKS = ("pusht", "cube")
ARMS = (
    "vad_greedy_300",
    "vad_greedy_576",
    "vad_continuation",
    "diagonal_gaussian_continuation",
    "direct_gmm_continuation",
)
HORIZONS = (75, 150)
REPLICATES = (1, 2, 3)
PROTOCOL_SHA256 = "aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459"
SOURCE_SHA256 = "182ed1e7d1e9994638ab1fbc773c79cac8d68858b716e67ff8969e5b2e74e29c"
INPUT_AUDIT_SHA256 = "8f6185d9b05cbff90a6766a865d68d0ff919980b9ac55911f0cb9265a2a3e4e4"
P2_HASHES = {
    "pusht": (
        "54f5f974b745ac70ddf0f599bd141df8dda97926beca75efce7de47b068cfef1",
        "934cf02377ad9a5719c183cb97704d2a31f4dbd31e7fb96e7b41cdc9f0634606",
    ),
    "cube": (
        "e5af2ac0acec6ebbcad26bc35c2723ff3c4bc09694f435f65aaac43cacedaf93",
        "1bff112bd9c85bc9557bd5ab63d84697f54fbd10ce54dbf4515718eced08fb4a",
    ),
}
ADAPTER_IDENTITY = {
    "pusht": (
        "c58726a3502bf52bbbaad6263c1f636ef393ecbd34835b021750f7451bed88b8",
        "9921b24e853259ddb5e7f1a4c530c11b1bf52346516d92e053a49ee900784b0a",
        True,
    ),
    "cube": (
        "008311d81dcf3753170a7ecfd886cfb23fddc0ec932150e609071d3c830214a0",
        "86bcc74435e3aed62377ed354eb90866e047d77baf61fbefbb6ad3c444831a33",
        False,
    ),
}
FIRST_COUNT = {
    "vad_greedy_300": 300,
    "vad_greedy_576": 576,
    "vad_continuation": 64,
    "diagonal_gaussian_continuation": 64,
    "direct_gmm_continuation": 64,
}
MINIMUM_FIRST_UNIQUE = {
    "vad_greedy_300": 285,
    "vad_greedy_576": 548,
    "vad_continuation": 61,
    "diagonal_gaussian_continuation": 61,
    "direct_gmm_continuation": 61,
}
FAMILY = {
    "vad_greedy_300": "vad",
    "vad_greedy_576": "vad",
    "vad_continuation": "vad",
    "diagonal_gaussian_continuation": "diagonal_gaussian",
    "direct_gmm_continuation": "direct_gmm",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checksum_records(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        result[name.lstrip(" *")] = digest
    return result


def assert_close(actual: Any, expected: Any) -> None:
    if not np.allclose(actual, expected, atol=0.0, rtol=0.0):
        raise AssertionError((actual, expected))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))

    success = np.full((2, 12, 5, 2, 3), np.nan, dtype=np.float64)
    start_identity: dict[tuple[str, int], tuple[int, int]] = {}
    post_timing: dict[str, list[tuple[str, int, float]]] = {
        arm: [] for arm in ARMS
    }
    predicted_maximum: dict[tuple[str, str, int], float] = {}
    cell_count = 0
    episode_count = 0
    diagnostic_count = 0

    for task_index, task in enumerate(TASKS):
        for arm_index, arm in enumerate(ARMS):
            for replicate_index, replicate in enumerate(REPLICATES):
                for horizon_index, horizon in enumerate(HORIZONS):
                    for shard in range(4):
                        directory = (
                            args.evaluation_root
                            / task
                            / arm
                            / f"replicate-{replicate}"
                            / f"horizon-{horizon}"
                            / f"shard-{shard}"
                        )
                        records = checksum_records(directory / "sha256.txt")
                        if set(records) != {
                            "episodes.tsv",
                            "planner-diagnostics.jsonl",
                            "summary.json",
                        } or any(
                            sha256_file(directory / name) != digest
                            for name, digest in records.items()
                        ):
                            raise AssertionError(f"checksum mismatch: {directory}")

                        summary = json.loads(
                            (directory / "summary.json").read_text(encoding="utf-8")
                        )
                        if not (
                            summary["status"] == "ok"
                            and summary["task"] == task
                            and summary["arm"] == arm
                            and summary["replicate"] == replicate
                            and summary["learned_seed"] == 7200 + replicate
                            and summary["horizon"] == horizon
                            and summary["shard"] == shard
                            and summary["episode_count"] == 3
                            and summary["schedule"] == [15] * (horizon // 15)
                            and summary["environment_budget"]
                            == horizon * (2 if task == "pusht" else 1)
                            and summary["planning_stage_count"]
                            == (horizon // 15) * (2 if task == "pusht" else 1)
                            and summary["protocol_sha256"] == PROTOCOL_SHA256
                            and summary["source_manifest_sha256"] == SOURCE_SHA256
                            and summary["input_audit_sha256"] == INPUT_AUDIT_SHA256
                            and (
                                summary["p2_queries_sha256"],
                                summary["p2_provenance_sha256"],
                            )
                            == P2_HASHES[task]
                            and summary["e17_decision_preserved"]
                            == "stop_transition_adapter_preflight_failed"
                            and summary["e17_used_as_authorization"] is False
                            and summary["d3_metric_read"] is False
                            and summary["d4_metric_read"] is False
                            and summary["d5_read"] is False
                            and summary["protected_p3_p4_c1_i1_read"] is False
                            and summary["claim_allowed"] is False
                        ):
                            raise AssertionError(f"summary mismatch: {directory}")

                        model_artifacts = summary["model_artifacts"]
                        proposer = model_artifacts["e15_proposer"]
                        if not (
                            proposer["condition"] == FAMILY[arm]
                            and proposer["seed"] == 7200 + replicate
                            and model_artifacts["e17_failure_preserved"] is True
                            and model_artifacts["e17_used_as_authorization"] is False
                        ):
                            raise AssertionError(f"proposer mismatch: {directory}")
                        adapter = model_artifacts["e17_transition_state_adapter"]
                        if arm.endswith("_continuation"):
                            identity = ADAPTER_IDENTITY[task]
                            if not (
                                adapter["checkpoint_sha256"] == identity[0]
                                and adapter["summary_sha256"] == identity[1]
                                and adapter["e17_gate_passed"] is identity[2]
                                and adapter["e17_failure_preserved"] is True
                                and adapter["e17_used_as_authorization"] is False
                            ):
                                raise AssertionError(f"adapter mismatch: {directory}")
                        elif adapter is not None:
                            raise AssertionError(f"greedy loaded adapter: {directory}")

                        with (directory / "episodes.tsv").open(
                            newline="", encoding="utf-8"
                        ) as stream:
                            episodes = list(csv.DictReader(stream, delimiter="\t"))
                        expected_base = list(range(shard * 3, (shard + 1) * 3))
                        if (
                            len(episodes) != 3
                            or [int(row["base_index"]) for row in episodes]
                            != expected_base
                            or sum(int(row["success"]) for row in episodes)
                            != summary["success_count"]
                        ):
                            raise AssertionError(f"episode mismatch: {directory}")
                        for row in episodes:
                            base = int(row["base_index"])
                            identity = (int(row["episode_id"]), int(row["start_step"]))
                            key = (task, base)
                            if start_identity.setdefault(key, identity) != identity:
                                raise AssertionError("paired start mismatch")
                            if not (
                                row["task"] == task
                                and row["arm"] == arm
                                and int(row["replicate"]) == replicate
                                and int(row["horizon"]) == horizon
                                and int(row["shard"]) == shard
                            ):
                                raise AssertionError(f"episode identity: {directory}")
                            if math.isfinite(
                                success[
                                    task_index,
                                    base,
                                    arm_index,
                                    horizon_index,
                                    replicate_index,
                                ]
                            ):
                                raise AssertionError("duplicate paired outcome")
                            success[
                                task_index,
                                base,
                                arm_index,
                                horizon_index,
                                replicate_index,
                            ] = int(row["success"])
                            episode_count += 1

                        diagnostics = [
                            json.loads(line)
                            for line in (
                                directory / "planner-diagnostics.jsonl"
                            ).read_text(encoding="utf-8").splitlines()
                            if line
                        ]
                        if len(diagnostics) != summary["planning_stage_count"]:
                            raise AssertionError(f"diagnostic count: {directory}")
                        rollout_total = 0
                        for call, record in enumerate(diagnostics):
                            if not (
                                record["call"] == call
                                and record["arm"] == arm
                                and record["tau"] == 15
                                and record["first_candidate_count"]
                                == FIRST_COUNT[arm]
                                and record["minimum_first_unique_candidates"]
                                >= MINIMUM_FIRST_UNIQUE[arm]
                                and record["strict_legal_oob_fraction"] == 0.0
                                and record["exact_legal_boundary_fraction"] == 0.0
                                and record["component_timing_method"]
                                == "cuda_events_resolved_after_outer_stage_synchronize"
                            ):
                                raise AssertionError(f"diagnostic identity: {directory}")
                            continuation = (
                                arm.endswith("_continuation")
                                and int(record["delta"]) >= 30
                            )
                            expected_rollouts = (
                                576
                                if continuation or arm == "vad_greedy_576"
                                else 300
                                if arm == "vad_greedy_300"
                                else 64
                            )
                            if not (
                                record["continuations_per_first"]
                                == (8 if continuation else 0)
                                and record["continuation_best_count"]
                                == (2 if continuation else 0)
                                and record["lewm_rollout_trajectories"]
                                == 3 * expected_rollouts
                            ):
                                raise AssertionError(f"rollout budget: {directory}")
                            if continuation:
                                if not (
                                    record[
                                        "minimum_second_unique_candidates_per_first"
                                    ]
                                    >= 7
                                    and math.isfinite(
                                        record["predicted_state_absolute_max"]
                                    )
                                    and math.isfinite(
                                        record["predicted_state_absolute_q99"]
                                    )
                                ):
                                    raise AssertionError(
                                        f"continuation diagnostic: {directory}"
                                    )
                                predicted_key = (task, arm, horizon)
                                predicted_maximum[predicted_key] = max(
                                    predicted_maximum.get(predicted_key, 0.0),
                                    record["predicted_state_absolute_max"],
                                )
                            elif not (
                                record["minimum_second_unique_candidates_per_first"]
                                is None
                                and record["predicted_state_absolute_max"] is None
                                and record["predicted_state_absolute_q99"] is None
                            ):
                                raise AssertionError(f"terminal diagnostic: {directory}")
                            for field in (
                                "end_to_end_stage_seconds",
                                "proposal_and_selection_seconds",
                                "adapter_seconds",
                                "lewm_scoring_seconds",
                                "encoding_seconds",
                            ):
                                value = float(record[field])
                                if not math.isfinite(value) or value < 0.0:
                                    raise AssertionError(f"timing: {directory}")
                            if call > 0:
                                post_timing[arm].append(
                                    (
                                        task,
                                        horizon,
                                        record["end_to_end_stage_seconds"] / 3,
                                    )
                                )
                            rollout_total += record["lewm_rollout_trajectories"]
                            diagnostic_count += 1
                        if rollout_total != summary["lewm_rollout_trajectories"]:
                            raise AssertionError(f"summary rollout total: {directory}")
                        cell_count += 1

    if not (
        cell_count == 240
        and episode_count == 720
        and diagnostic_count == 2700
        and len(start_identity) == 24
        and np.isfinite(success).all()
    ):
        raise AssertionError("information barrier or pairing")

    task_horizon = success.mean(axis=(1, 4))
    task_average = task_horizon.mean(axis=2)
    equal_rate = task_horizon.mean(axis=(0, 2))
    reported_rates = audit["success_rates"]
    for task_index, task in enumerate(TASKS):
        for arm_index, arm in enumerate(ARMS):
            assert_close(
                task_average[task_index, arm_index],
                reported_rates["task_average"][task][arm],
            )
            for horizon_index, horizon in enumerate(HORIZONS):
                assert_close(
                    task_horizon[task_index, arm_index, horizon_index],
                    reported_rates["task_horizon"][task][arm][str(horizon)],
                )
    for arm_index, arm in enumerate(ARMS):
        assert_close(
            equal_rate[arm_index],
            reported_rates["equal_task_equal_horizon"][arm],
        )

    treatment = ARMS.index("vad_continuation")
    differences: dict[str, float] = {}
    minimum_task_average: dict[str, float] = {}
    for comparator in ARMS:
        if comparator == "vad_continuation":
            continue
        comparator_index = ARMS.index(comparator)
        cells = task_horizon[:, treatment] - task_horizon[:, comparator_index]
        differences[comparator] = float(cells.mean())
        minimum_task_average[comparator] = float(cells.mean(axis=1).min())
        reported = audit["vad_continuation_paired_differences"][comparator]
        assert_close(differences[comparator], reported["equal_task_equal_horizon"])
        assert_close(
            minimum_task_average[comparator], reported["minimum_task_average"]
        )

    seed = int.from_bytes(
        hashlib.sha256(b"gdp-cem-e18|clustered-bootstrap").digest()[:8],
        "little",
    ) % (2**63 - 1)
    rng = np.random.default_rng(seed)
    bootstrap_samples = {
        arm: np.empty(10_000, dtype=np.float64) for arm in differences
    }
    for draw in range(10_000):
        rate = np.empty((2, 5, 2), dtype=np.float64)
        for task_index in range(2):
            indices = rng.integers(0, 12, 12)
            rate[task_index] = success[task_index, indices].mean(axis=(0, 3))
        for comparator in differences:
            cells = rate[:, treatment] - rate[:, ARMS.index(comparator)]
            bootstrap_samples[comparator][draw] = cells.mean()
    intervals: dict[str, list[float]] = {}
    for comparator, values in bootstrap_samples.items():
        intervals[comparator] = [
            float(np.quantile(values, 0.025)),
            float(np.quantile(values, 0.975)),
        ]
        assert_close(
            intervals[comparator],
            audit["clustered_bootstrap"][
                "vad_continuation_minus_comparator_equal_95ci"
            ][comparator],
        )

    timings: dict[str, float] = {}
    for arm in ARMS:
        cell_medians = []
        for task in TASKS:
            for horizon in HORIZONS:
                values = [
                    value
                    for row_task, row_horizon, value in post_timing[arm]
                    if row_task == task and row_horizon == horizon
                ]
                cell_medians.append(float(np.median(values)))
        timings[arm] = float(np.mean(cell_medians))
        assert_close(
            timings[arm],
            audit["timing_and_adapter_domain"][
                "equal_task_equal_horizon_mean_post_first_end_to_end_median_seconds"
            ][arm],
        )

    comparator_pass = {
        comparator: differences[comparator] > 0.0
        and minimum_task_average[comparator] >= -0.05
        for comparator in differences
    }
    if not (
        all(comparator_pass.values())
        and audit["gates"]["joint_exploratory_signal_passed"] is True
        and audit["decision"]
        == "authorize_drafting_separate_frozen_confirmation_protocol"
        and audit["clustered_bootstrap"]["unit"] == "task_base_start_cluster"
        and audit["clustered_bootstrap"]["seeds_resampled_as_independent"]
        is False
        and audit["cell_count"] == 240
        and audit["episode_row_count"] == 720
        and audit["base_start_cluster_count"] == 24
    ):
        raise AssertionError("gate or aggregation identity")

    result = {
        "status": "independent_validation_passed",
        "cell_count": cell_count,
        "episode_count": episode_count,
        "diagnostic_call_count": diagnostic_count,
        "paired_start_clusters": len(start_identity),
        "equal_task_equal_horizon_success": {
            arm: float(equal_rate[index]) for index, arm in enumerate(ARMS)
        },
        "task_average_success": {
            task: {
                arm: float(task_average[task_index, arm_index])
                for arm_index, arm in enumerate(ARMS)
            }
            for task_index, task in enumerate(TASKS)
        },
        "vad_continuation_differences": differences,
        "vad_continuation_difference_95ci": intervals,
        "post_first_seconds": timings,
        "maximum_adapter_predicted_state_absolute_standardized": {
            "|".join(map(str, key)): value
            for key, value in sorted(predicted_maximum.items())
        },
        "comparator_gate_pass": comparator_pass,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
