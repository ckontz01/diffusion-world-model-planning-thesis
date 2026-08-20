#!/usr/bin/env python3
"""Analyze the frozen E9 AE-only exposed-D2 closed-loop study."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

import acid_alt_d2_models as d2
import analyze_acid_alt_d2_stage_b as v3


TASKS = ("pusht", "reacher", "cube")
ARMS = ("b0", "acid", "forward", "ae", "ae_shuffled")
PLANNER_SEEDS = (8301, 8302, 8303)
EVAL_COUNT = 50
BOOTSTRAP_REPETITIONS = 100_000
BOOTSTRAP_SEED = 2026081704
E9_PROTOCOL_SHA256 = (
    "ddabeed5f0d0cc5dd46b6d99f3e5f83f2ec122d09aac8beb48fc8a81965fa658"
)
PRIOR_STAGE_A_SHA256 = (
    "0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37"
)
CORE_JOBS = {"pusht": 296631, "reacher": 296650, "cube": 296669}
OLD_RESIDUAL_INDICES = {"pusht": (0, 1), "reacher": (2, 3), "cube": (4, 5)}
V3_RESIDUAL_BASE = {"pusht": 0, "reacher": 4, "cube": 8}
E9_D2_HASHES = {
    "pusht": {
        "manifest": "85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89",
        "provenance": "fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede",
    },
    "reacher": {
        "manifest": "a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61",
        "provenance": "f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11",
    },
    "cube": {
        "manifest": "bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388",
        "provenance": "fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b",
    },
}


def require_file_hash(path_text: Any, expected_hash: Any, label: str) -> Path:
    if not isinstance(path_text, str) or not isinstance(expected_hash, str):
        raise RuntimeError(f"missing E9 {label} lineage")
    path = Path(path_text)
    if not path.is_file() or d2.sha256_file(path) != expected_hash:
        raise RuntimeError(f"E9 {label} hash differs: {path}")
    return path


def validate_resolved_config(value: dict[str, Any], *, arm: str) -> None:
    config = value.get("resolved_config")
    expected = {
        "task": value.get("task"),
        "arm": arm,
        "scorer_seed": value.get("scorer_seed"),
        "planner_seed": value.get("planner_seed"),
        "lambda_weight": 0.07 if arm == "acid" else 0.005,
        "goal_offset": 25,
        "eval_budget": 50,
        "horizon": 5,
        "receding_horizon": 5,
        "action_block": 5,
        "cem_samples": 300,
        "cem_steps": 30,
        "cem_topk": 30,
        "residual_sigmas": [0.25, 1.0, 4.0],
        "residual_noise_draws": 8,
        "acid_noise_stream": (
            "SHA-256(task, scorer seed, planner seed, cost-call index)"
            if arm == "acid"
            else None
        ),
    }
    if not isinstance(config, dict) or any(config.get(key) != item for key, item in expected.items()):
        raise RuntimeError("E9 resolved planner/scorer configuration differs")
    if (config.get("action_standardization") is None) != (arm == "b0"):
        raise RuntimeError("E9 action-standardization record differs")


def validate_scorer_lineage(
    value: dict[str, Any], *, task: str, arm: str, scorer_seed: int
) -> None:
    record = value.get("scorer")
    seed_offset = scorer_seed - 6101
    if arm == "b0":
        if record is not None:
            raise RuntimeError("E9 B0 unexpectedly has a scorer")
        return
    if not isinstance(record, dict) or record.get("seed") != scorer_seed:
        raise RuntimeError("E9 scorer identity differs")
    checkpoint = require_file_hash(
        record.get("checkpoint"), record.get("checkpoint_sha256"), "scorer checkpoint"
    )
    normalized = checkpoint.as_posix()
    if arm in {"acid", "forward"}:
        checkpoint_index = seed_offset if arm == "acid" else seed_offset + 6
        suffix = (
            f"/results/acid-alternative/scorers/{task}/{arm}/true/"
            f"seed-{scorer_seed}-job-{CORE_JOBS[task]}-{checkpoint_index}/best.pt"
        )
        if record.get("arm") != arm or not normalized.endswith(suffix):
            raise RuntimeError("E9 core-scorer lineage differs")
        if not isinstance(record.get("parameter_count"), int) or record["parameter_count"] <= 0:
            raise RuntimeError("E9 core-scorer parameter count is invalid")
        return

    condition = "true" if arm == "ae" else "shuffled_action"
    summary = require_file_hash(
        record.get("summary"), record.get("summary_sha256"), "scorer summary"
    )
    if scorer_seed == 6101:
        index = OLD_RESIDUAL_INDICES[task][condition == "shuffled_action"]
        suffix = (
            "/results/acid-alternative/scorers-v2-residual-diffusion-pilot/"
            f"{task}/{condition}/seed-6101-job-297483-{index}/summary.json"
        )
        expected_kind = "residual_diffusion_x0_pilot_training"
        expected_protocol = d2.V2_PROTOCOL_SHA256
    else:
        condition_offset = 2 if condition == "shuffled_action" else 0
        index = V3_RESIDUAL_BASE[task] + condition_offset + scorer_seed - 6102
        suffix = (
            f"/results/acid-alternative/scorers-v3-d2/{task}/{condition}/"
            f"seed-{scorer_seed}-job-297533-{index}/summary.json"
        )
        expected_kind = "residual_diffusion_x0_multiseed_d2_training"
        expected_protocol = d2.PROTOCOL_SHA256
    training = json.loads(summary.read_text(encoding="utf-8"))
    if (
        record.get("condition") != condition
        or record.get("kind") != expected_kind
        or record.get("protocol_sha256") != expected_protocol
        or not summary.as_posix().endswith(suffix)
        or not isinstance(record.get("parameter_count"), int)
        or record["parameter_count"] <= 0
    ):
        raise RuntimeError("E9 residual-scorer lineage differs")
    if (
        training.get("status") != "ok"
        or training.get("kind") != expected_kind
        or training.get("condition") != condition
        or training.get("seed") != scorer_seed
        or training.get("protocol_sha256") != expected_protocol
        or training.get("checkpoint") != record.get("checkpoint")
        or training.get("checkpoint_sha256") != record.get("checkpoint_sha256")
        or training.get("parameter_count") != record.get("parameter_count")
    ):
        raise RuntimeError("E9 residual training-summary lineage differs")


def parse_run(values: list[str]) -> tuple[str, str, int, int, Path]:
    task, arm, scorer_text, planner_text, summary_text = values
    scorer_seed = int(scorer_text)
    planner_seed = int(planner_text)
    if (
        task not in TASKS
        or arm not in ARMS
        or scorer_seed not in d2.SEEDS
        or planner_seed not in PLANNER_SEEDS
        or planner_seed - scorer_seed != 2200
    ):
        raise ValueError(f"invalid E9 run identity: {values}")
    return task, arm, scorer_seed, planner_seed, Path(summary_text)


def load_run(
    identity: tuple[str, str, int, int, Path], *, source_manifest_sha256: str
) -> dict[str, Any]:
    task, arm, scorer_seed, planner_seed, path = identity
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "ok"
        or value.get("kind")
        != "acid_alt_e9_exposed_d2_ae_closed_loop_evaluation"
        or value.get("analysis_role")
        != "post_v3_exposed_D2_AE_closed_loop_development"
        or value.get("task") != task
        or value.get("arm") != arm
        or value.get("scorer_seed") != scorer_seed
        or value.get("planner_seed") != planner_seed
        or value.get("episode_count") != EVAL_COUNT
        or value.get("protocol_sha256") != d2.PROTOCOL_SHA256
        or value.get("e9_protocol_sha256") != E9_PROTOCOL_SHA256
        or value.get("source_manifest_sha256") != source_manifest_sha256
        or value.get("stage_a_summary_sha256") != PRIOR_STAGE_A_SHA256
        or value.get("e9_prior_stage_a_decision") != "stop_before_stage_b"
        or value.get("stage_b_authorization") is not None
        or value.get("stage_b_authorization_sha256") is not None
        or value.get("d2_read") is not True
        or value.get("d3_read") is not False
        or value.get("protected_c1_i1_read") is not False
        or value.get("claim_allowed") is not False
    ):
        raise RuntimeError(f"invalid E9 summary: {path}")
    validate_resolved_config(value, arm=arm)
    validate_scorer_lineage(
        value, task=task, arm=arm, scorer_seed=scorer_seed
    )
    episodes = Path(value["episodes_tsv"])
    if not episodes.is_file() or d2.sha256_file(episodes) != value.get(
        "episodes_tsv_sha256"
    ):
        raise RuntimeError(f"E9 episode vector hash differs: {path}")
    success, starts = v3.read_episode_vector(
        episodes,
        task=task,
        arm=arm,
        scorer_seed=scorer_seed,
        planner_seed=planner_seed,
    )
    if int(success.sum()) != int(value["success_count"]):
        raise RuntimeError(f"E9 success count differs: {path}")
    expected_d2 = E9_D2_HASHES[task]
    if (
        value.get("eval_manifest_sha256") != expected_d2["manifest"]
        or value.get("eval_provenance_sha256") != expected_d2["provenance"]
    ):
        raise RuntimeError(f"E9 exact exposed-D2 hash differs: {path}")
    return {
        "success": success,
        "starts": starts,
        "summary": str(path),
        "summary_sha256": d2.sha256_file(path),
        "episodes": str(episodes),
        "episodes_sha256": d2.sha256_file(episodes),
        "eval_manifest_sha256": value["eval_manifest_sha256"],
        "eval_provenance_sha256": value["eval_provenance_sha256"],
        "dataset_sha256": value["dataset_sha256"],
        "world_model_checkpoint_sha256": value[
            "world_model_checkpoint_sha256"
        ],
    }


def bootstrap_indices() -> dict[str, np.ndarray]:
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    return {
        task: generator.integers(
            0,
            EVAL_COUNT,
            size=(BOOTSTRAP_REPETITIONS, EVAL_COUNT),
            dtype=np.int16,
        )
        for task in TASKS
    }


def gate_results(contrasts: dict[str, Any]) -> dict[str, bool]:
    ae_acid = contrasts["ae_minus_acid"]
    ae_shuffled = contrasts["ae_minus_ae_shuffled"]
    ae_b0 = contrasts["ae_minus_b0"]
    ae_forward = contrasts["ae_minus_forward"]
    return {
        "1_ae_point_estimate_above_acid_equal_task": (
            ae_acid["equal_task"]["estimate"] > 0.0
        ),
        "2_ae_noninferior_acid_equal_and_each_task": (
            ae_acid["equal_task"]["lower_95_one_sided"] > -0.05
            and all(
                ae_acid["per_task"][task]["lower_95_one_sided"] > -0.10
                for task in TASKS
            )
        ),
        "3_ae_beats_shuffled_equal_and_positive_each_task": (
            ae_shuffled["equal_task"]["lower_95_two_sided"] > 0.0
            and all(
                ae_shuffled["per_task"][task]["estimate"] > 0.0
                for task in TASKS
            )
        ),
        "4_ae_positive_and_noninferior_b0": (
            ae_b0["equal_task"]["estimate"] > 0.0
            and ae_b0["equal_task"]["lower_95_one_sided"] > -0.05
        ),
        "5_ae_noninferior_forward_equal_task": (
            ae_forward["equal_task"]["lower_95_one_sided"] > -0.05
        ),
        "6_ae_above_acid_on_at_least_two_tasks": (
            sum(
                ae_acid["per_task"][task]["estimate"] > 0.0 for task in TASKS
            )
            >= 2
        ),
        "7_all_identity_and_pairing_checks_pass": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-protocol", type=Path, required=True)
    parser.add_argument("--e9-protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument(
        "--run",
        nargs=5,
        action="append",
        metavar=("TASK", "ARM", "SCORER_SEED", "PLANNER_SEED", "SUMMARY"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if (
        d2.sha256_file(args.method_protocol) != d2.PROTOCOL_SHA256
        or d2.sha256_file(args.e9_protocol) != E9_PROTOCOL_SHA256
    ):
        raise RuntimeError("E9 analysis protocol hash differs")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing nonempty E9 analysis output")
    source_hash = d2.sha256_file(args.source_manifest)
    identities = [parse_run(values) for values in args.run]
    expected = {
        (task, arm, scorer_seed, scorer_seed + 2200)
        for task in TASKS
        for arm in ARMS
        for scorer_seed in d2.SEEDS
    }
    observed = {(task, arm, scorer, planner) for task, arm, scorer, planner, _ in identities}
    if len(identities) != len(expected) or observed != expected:
        raise RuntimeError("E9 requires exactly 45 unique paired runs")
    runs = {
        (task, arm, scorer, planner): load_run(
            identity, source_manifest_sha256=source_hash
        )
        for identity in identities
        for task, arm, scorer, planner, _ in (identity,)
    }

    for task in TASKS:
        reference = runs[(task, "b0", 6101, 8301)]
        for arm in ARMS:
            for scorer_seed in d2.SEEDS:
                run = runs[(task, arm, scorer_seed, scorer_seed + 2200)]
                if (
                    run["starts"] != reference["starts"]
                    or run["eval_manifest_sha256"]
                    != reference["eval_manifest_sha256"]
                    or run["eval_provenance_sha256"]
                    != reference["eval_provenance_sha256"]
                    or run["dataset_sha256"] != reference["dataset_sha256"]
                    or run["world_model_checkpoint_sha256"]
                    != reference["world_model_checkpoint_sha256"]
                ):
                    raise RuntimeError(f"E9 pairing or artifact identity differs: {task}")

    matrices = {
        arm: {
            task: np.stack(
                [
                    runs[(task, arm, scorer_seed, scorer_seed + 2200)]["success"]
                    for scorer_seed in d2.SEEDS
                ]
            )
            for task in TASKS
        }
        for arm in ARMS
    }
    indices = bootstrap_indices()
    arm_results = {
        arm: v3.summarize(matrices[arm], indices) for arm in ARMS
    }
    contrasts = {}
    for control in ("acid", "ae_shuffled", "b0", "forward"):
        difference = {
            task: matrices["ae"][task] - matrices[control][task] for task in TASKS
        }
        contrasts[f"ae_minus_{control}"] = {
            **v3.summarize(difference, indices),
            "exact_sign_tests": {
                **{
                    task: v3.exact_cluster_sign_test(difference[task])
                    for task in TASKS
                },
                "equal_task": v3.exact_cluster_sign_test(
                    np.concatenate([difference[task] for task in TASKS], axis=1)
                ),
            },
        }

    gates = gate_results(contrasts)
    passed = all(gates.values())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = args.output_dir / "runs.tsv"
    with runs_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "task",
                "arm",
                "scorer_seed",
                "planner_seed",
                "success_rate",
                "summary",
                "summary_sha256",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for task, arm, scorer, planner, _ in sorted(identities):
            run = runs[(task, arm, scorer, planner)]
            writer.writerow(
                {
                    "task": task,
                    "arm": arm,
                    "scorer_seed": scorer,
                    "planner_seed": planner,
                    "success_rate": float(run["success"].mean()),
                    "summary": run["summary"],
                    "summary_sha256": run["summary_sha256"],
                }
            )
    result = {
        "status": "ok",
        "kind": "acid_alt_e9_exposed_d2_ae_closed_loop_analysis",
        "analysis_role": "post_v3_exposed_D2_AE_closed_loop_development",
        "arm_results": arm_results,
        "contrasts": contrasts,
        "gates": gates,
        "all_e9_gates_pass": passed,
        "decision": (
            "authorize_separately_frozen_fresh_d3_ae_confirmation_design"
            if passed
            else "do_not_advance_ae_closed_loop_to_fresh_d3"
        ),
        "bootstrap": {
            "repetitions": BOOTSTRAP_REPETITIONS,
            "seed": BOOTSTRAP_SEED,
            "unit": "start cluster with three paired scorer/planner seeds retained",
            "task_aggregation": "equal mean of three task estimates",
        },
        "runs_tsv": str(runs_path),
        "runs_tsv_sha256": d2.sha256_file(runs_path),
        "method_protocol_sha256": d2.PROTOCOL_SHA256,
        "e9_protocol_sha256": E9_PROTOCOL_SHA256,
        "prior_stage_a_summary_sha256": PRIOR_STAGE_A_SHA256,
        "source_manifest_sha256": source_hash,
        "d2_read": True,
        "d3_read": False,
        "protected_c1_i1_read": False,
        "claim_allowed": False,
    }
    v3.atomic_json(args.output_dir / "summary.json", result)
    manifest = {
        "status": "ok",
        "kind": "acid_alt_e9_exposed_d2_ae_closed_loop_manifest",
        "summary_sha256": d2.sha256_file(args.output_dir / "summary.json"),
        "runs_tsv_sha256": result["runs_tsv_sha256"],
        "source_manifest_sha256": source_hash,
        "e9_protocol_sha256": E9_PROTOCOL_SHA256,
        "d2_read": True,
        "d3_read": False,
        "protected_c1_i1_read": False,
    }
    v3.atomic_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
