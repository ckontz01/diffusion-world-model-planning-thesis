#!/usr/bin/env python3
"""Independent read-only audit of the completed frozen E13 aggregate.

This verifier is post-result code.  It cannot alter E13's frozen decision; it
only recomputes the task-first rates, paired contrasts, bootstrap intervals,
and gates from the immutable aggregate bundle.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


TASKS = ("pusht", "reacher", "cube")
SEEDS = (6101, 6102, 6103)
ARMS = (
    "latent_gaussian_select_k300",
    "vp_select_k300",
    "prism_dp_select_k300",
    "vp_select_k16",
    "prism_dp_select_k16",
)
COUNT = 400
REPETITIONS = 100_000
PRIMARY_SEED = 2026082202
TWO_WAY_SEED = 2026082203
PROTOCOL_SHA256 = "65d56b613f12ad896c395e6feb4fc6d39f404bc802045369d0a88b638690af58"
SOURCE_MANIFEST_SHA256 = (
    "3f66e2a3ca673c5d3c3ddff74d41927e8ad412cd9baa89dddcf95f2ab062ee7a"
)
CONTRASTS = (
    ("vp_select_k300", "prism_dp_select_k300"),
    ("vp_select_k300", "latent_gaussian_select_k300"),
    ("vp_select_k16", "prism_dp_select_k16"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(first: float, second: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(float(first), float(second), rel_tol=0.0, abs_tol=tolerance)


def exact_sign(values: np.ndarray) -> dict[str, int | float]:
    positive = int(np.count_nonzero(values > 0.0))
    negative = int(np.count_nonzero(values < 0.0))
    ties = int(values.size - positive - negative)
    count = positive + negative
    if count == 0:
        return {
            "positive": positive,
            "negative": negative,
            "ties": ties,
            "one_sided_greater_p": 1.0,
            "two_sided_p": 1.0,
        }
    denominator = 2**count
    greater = sum(math.comb(count, value) for value in range(positive, count + 1))
    smaller_tail = sum(
        math.comb(count, value) for value in range(min(positive, negative) + 1)
    )
    return {
        "positive": positive,
        "negative": negative,
        "ties": ties,
        "one_sided_greater_p": float(greater / denominator),
        "two_sided_p": float(min(1.0, 2.0 * smaller_tail / denominator)),
    }


def primary_bootstrap(values: dict[str, np.ndarray]) -> np.ndarray:
    rng = np.random.default_rng(PRIMARY_SEED)
    output = np.empty(REPETITIONS, dtype=np.float64)
    cursor = 0
    while cursor < REPETITIONS:
        size = min(500, REPETITIONS - cursor)
        task_means = []
        for task in TASKS:
            task_values = values[task]
            indices = rng.integers(0, COUNT, size=(size, COUNT))
            task_means.append(task_values[indices].mean(axis=1))
        output[cursor : cursor + size] = np.stack(task_means, axis=1).mean(axis=1)
        cursor += size
    return output


def two_way_bootstrap(values: dict[str, np.ndarray]) -> np.ndarray:
    rng = np.random.default_rng(TWO_WAY_SEED)
    output = np.empty(REPETITIONS, dtype=np.float64)
    cursor = 0
    while cursor < REPETITIONS:
        size = min(250, REPETITIONS - cursor)
        seed_positions = rng.integers(0, len(SEEDS), size=(size, len(SEEDS)))
        task_means = []
        for task in TASKS:
            starts = rng.integers(0, COUNT, size=(size, COUNT))
            sampled = values[task][seed_positions[:, :, None], starts[:, None, :]]
            task_means.append(sampled.mean(axis=(1, 2)))
        output[cursor : cursor + size] = np.stack(task_means, axis=1).mean(axis=1)
        cursor += size
    return output


def recompute_contrast(
    outcomes: dict[str, dict[int, dict[str, np.ndarray]]],
    treatment: str,
    control: str,
) -> dict[str, Any]:
    seed_start: dict[str, np.ndarray] = {}
    clusters: dict[str, np.ndarray] = {}
    task_effects: dict[str, float] = {}
    for task in TASKS:
        values = np.stack(
            [outcomes[task][seed][treatment] - outcomes[task][seed][control] for seed in SEEDS]
        )
        seed_start[task] = values
        clusters[task] = values.mean(axis=0)
        task_effects[task] = float(clusters[task].mean())
    primary = primary_bootstrap(clusters)
    secondary = two_way_bootstrap(seed_start)
    return {
        "equal_task_point_difference": float(np.mean(list(task_effects.values()))),
        "per_task_point_difference": task_effects,
        "primary_two_sided_95": [
            float(np.quantile(primary, 0.025)),
            float(np.quantile(primary, 0.975)),
        ],
        "primary_one_sided_95_lower": float(np.quantile(primary, 0.05)),
        "secondary_two_sided_95": [
            float(np.quantile(secondary, 0.025)),
            float(np.quantile(secondary, 0.975)),
        ],
        "secondary_one_sided_95_lower": float(np.quantile(secondary, 0.05)),
        "sign_test": exact_sign(np.concatenate([clusters[task] for task in TASKS])),
    }


def assert_contrast_matches(observed: dict[str, Any], expected: dict[str, Any]) -> None:
    assert close(observed["equal_task_point_difference"], expected["equal_task_point_difference"])
    for task in TASKS:
        assert close(observed["per_task_point_difference"][task], expected["per_task_point_difference"][task])
    primary = expected["primary_start_cluster_interval"]
    secondary = expected["secondary_two_way_interval"]
    for first, second in zip(observed["primary_two_sided_95"], primary["two_sided_95"]):
        assert close(first, second)
    assert close(observed["primary_one_sided_95_lower"], primary["one_sided_95_lower"])
    for first, second in zip(observed["secondary_two_sided_95"], secondary["two_sided_95"]):
        assert close(first, second)
    assert close(observed["secondary_one_sided_95_lower"], secondary["one_sided_95_lower"])
    for key, value in observed["sign_test"].items():
        if isinstance(value, float):
            assert close(value, expected["exact_start_cluster_sign_test"][key])
        else:
            assert value == expected["exact_start_cluster_sign_test"][key]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--paired-outcomes", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    input_manifest = json.loads(args.input_manifest.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "ok"
        or summary.get("kind") != "gdp_cem_e13_untouched_d4_aggregate"
        or summary.get("protocol_sha256") != PROTOCOL_SHA256
        or summary.get("source_manifest_sha256") != SOURCE_MANIFEST_SHA256
        or summary.get("episode_count") != 18_000
        or summary.get("shard_count") != 360
        or summary.get("all_shards_complete_before_metric_read") is not True
        or summary.get("partial_d4_metrics_read_before_aggregate") is not False
        or summary.get("d3_outcomes_read") is not False
        or summary.get("protected_p4_c1_i1_read") is not False
        or summary.get("paired_outcomes_sha256") != sha256_file(args.paired_outcomes)
        or summary.get("input_manifest_sha256") != sha256_file(args.input_manifest)
        or input_manifest.get("expected_shards") != 360
        or input_manifest.get("verified_shards") != 360
        or len(input_manifest.get("shards", [])) != 360
        or input_manifest.get("all_shards_complete_before_metric_read") is not True
        or input_manifest.get("protocol_sha256") != PROTOCOL_SHA256
        or input_manifest.get("source_manifest_sha256") != SOURCE_MANIFEST_SHA256
    ):
        raise RuntimeError("E13 aggregate provenance or information barrier differs")

    outcomes = {
        task: {
            seed: {arm: np.full(COUNT, np.nan, dtype=np.float64) for arm in ARMS}
            for seed in SEEDS
        }
        for task in TASKS
    }
    starts: dict[tuple[str, int], tuple[int, int]] = {}
    keys: set[tuple[str, int, int]] = set()
    with args.paired_outcomes.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != len(TASKS) * len(SEEDS) * COUNT:
        raise RuntimeError("E13 paired row count differs")
    for row in rows:
        task = row["task"]
        seed = int(row["seed"])
        index = int(row["eval_index"])
        key = (task, seed, index)
        identity = (int(row["episode_id"]), int(row["start_step"]))
        if task not in TASKS or seed not in SEEDS or index not in range(COUNT) or key in keys:
            raise RuntimeError("E13 paired key grid differs")
        keys.add(key)
        if (task, index) in starts and starts[(task, index)] != identity:
            raise RuntimeError("E13 paired start identity varies across seeds")
        starts[(task, index)] = identity
        for arm in ARMS:
            value = int(row[arm])
            if value not in (0, 1):
                raise RuntimeError("E13 paired outcome is not binary")
            outcomes[task][seed][arm][index] = value
    if len(keys) != 3_600 or len(starts) != 1_200:
        raise RuntimeError("E13 paired outcome grid is incomplete")

    rates: dict[str, dict[str, float]] = {}
    for task in TASKS:
        rates[task] = {}
        for arm in ARMS:
            value = float(np.mean([outcomes[task][seed][arm].mean() for seed in SEEDS]))
            rates[task][arm] = value
            assert close(value, summary["success_by_task"][task][arm])
            for seed in SEEDS:
                assert close(
                    outcomes[task][seed][arm].mean(),
                    summary["success_by_task_seed"][task][str(seed)][arm],
                )

    recomputed: dict[str, Any] = {}
    for treatment, control in CONTRASTS:
        name = f"{treatment}_minus_{control}"
        recomputed[name] = recompute_contrast(outcomes, treatment, control)
        assert_contrast_matches(recomputed[name], summary["contrasts"][name])

    primary = recomputed["vp_select_k300_minus_prism_dp_select_k300"]
    mechanism = recomputed["vp_select_k300_minus_latent_gaussian_select_k300"]
    integrity = summary["proposal_integrity"]
    primary_integrity = all(
        integrity[arm][task][str(seed)]["all_finite"] is True
        and integrity[arm][task][str(seed)]["passed_finite_non_degenerate"] is True
        for arm in ("vp_select_k300", "prism_dp_select_k300")
        for task in TASKS
        for seed in SEEDS
    )
    mechanism_failures = [
        {
            "arm": arm,
            "task": task,
            "seed": seed,
            "boundary_fraction_max": integrity[arm][task][str(seed)]["boundary_fraction_max"],
        }
        for arm in ("vp_select_k300", "latent_gaussian_select_k300")
        for task in TASKS
        for seed in SEEDS
        if integrity[arm][task][str(seed)]["all_finite"] is not True
        or integrity[arm][task][str(seed)]["passed_finite_non_degenerate"] is not True
        or integrity[arm][task][str(seed)]["boundary_fraction_max"] >= 0.25
    ]
    primary_gate = (
        primary["equal_task_point_difference"] > 0.0
        and primary["primary_one_sided_95_lower"] > 0.0
        and sum(value > 0.0 for value in primary["per_task_point_difference"].values()) >= 2
        and min(primary["per_task_point_difference"].values()) >= -0.05
        and primary_integrity
    )
    mechanism_gate = (
        mechanism["equal_task_point_difference"] > 0.0
        and mechanism["primary_one_sided_95_lower"] > 0.0
        and sum(value > 0.0 for value in mechanism["per_task_point_difference"].values()) >= 2
        and min(mechanism["per_task_point_difference"].values()) >= -0.05
        and not mechanism_failures
    )
    resources = summary["resource_advantage"]
    efficiency_gate = (
        not primary_gate
        and primary["primary_one_sided_95_lower"] >= -0.03
        and summary["timing"]["treatment_lower_on_every_task"] is True
        and any(
            resources[name] is True
            for name in (
                "fewer_active_learned_parameters",
                "no_second_image_encoder",
                "lower_peak_cuda_memory",
            )
        )
    )
    expected_gates = summary["gates"]
    if (
        primary_gate is not expected_gates["primary_superiority_to_disclosed_prism_dp_reconstruction"]
        or mechanism_gate is not expected_gates["secondary_diffusion_mechanism_replication"]
        or efficiency_gate is not expected_gates["compute_efficient_alternative"]
        or summary["decision"]
        != "compute_efficient_alternative_to_disclosed_prism_dp_reconstruction"
    ):
        raise RuntimeError("E13 independently recomputed gate differs")

    result = {
        "status": "independently_verified",
        "paired_rows": len(rows),
        "unique_task_start_clusters": len(starts),
        "input_shards_verified_by_frozen_analyzer": input_manifest["verified_shards"],
        "rates": rates,
        "contrasts": recomputed,
        "mechanism_integrity_failures": mechanism_failures,
        "gates": {
            "primary_superiority": primary_gate,
            "diffusion_mechanism_replication": mechanism_gate,
            "compute_efficient_alternative": efficiency_gate,
        },
        "decision": summary["decision"],
        "hashes": {
            "summary": sha256_file(args.summary),
            "paired_outcomes": sha256_file(args.paired_outcomes),
            "input_manifest": sha256_file(args.input_manifest),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
