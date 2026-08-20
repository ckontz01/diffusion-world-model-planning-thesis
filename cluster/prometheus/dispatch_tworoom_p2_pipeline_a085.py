#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ROOT = Path("/lustreFS/data/superworld/ckontzias/thesis")
STABLEWM = ROOT / "data/stablewm"
TRUE_SCORE_JOB_ID = 295869
LABELED_JOB_ID = 295868
NULL_MAP_JOB_ID = 295698
WEIGHTS = (0.25, 0.5, 1.0, 2.0, 4.0)
M2_SIGMAS = (0.1, 0.25, 0.5, 0.75, 1.0)
EXPECTED_CANDIDATE_H5_SHA256 = (
    "022a16c75bbcaf75a8ea77a98ea226ab7566a714d9b211ad5f9381f261285531"
)

NULL_LAUNCHER = ROOT / "scripts/run_selected_tworoom_null_scorer_array.slurm"
AUTOENCODER_LAUNCHER = (
    ROOT / "scripts/run_selected_tworoom_m2_autoencoder_array.slurm"
)
CALIBRATION_LAUNCHER = (
    ROOT / "scripts/run_score_tworoom_nulls_autoencoder_and_fit_p2_calibrators.slurm"
)
SMOKE_LAUNCHER = ROOT / "scripts/run_tworoom_p2_augmented_closed_loop_smoke.slurm"
GRID_LAUNCHER = ROOT / "scripts/run_tworoom_p2_augmented_closed_loop_array.slurm"
AGGREGATE_LAUNCHER = (
    ROOT / "scripts/run_aggregate_tworoom_p2_augmented_closed_loop_grid.slurm"
)
DISPATCH_RUNNER = ROOT / "scripts/run_dispatch_tworoom_p2_pipeline_a085.slurm"

EXPECTED_LAUNCHER_HASHES = {
    NULL_LAUNCHER: "fdf89b744ac01645cc421520fc104a0eaf418baf10a5fd1fea4d0af64a9f5d71",
    AUTOENCODER_LAUNCHER: "39fde38eb4397b162aef3970737fd5d827a9c9fc05f2ddecb6031bdde9a244d5",
    CALIBRATION_LAUNCHER: "a72727cf6e98caae4c94834543b6b535a16e7dd3951e73ddb19935f4eb72494f",
    SMOKE_LAUNCHER: "03b38bb3728605f9941c31326e08098cb78121b441209e4ef282dfa8a34dc62d",
    GRID_LAUNCHER: "27d058b82d51ffc036706d2c81e62ceab3d5885794dbc7d58c07dbdccd57d51d",
    AGGREGATE_LAUNCHER: "91a8cd9f8209bc569c981f6ab63895e225e8afc239737e398f02b1e92289c0b4",
}


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def verify_inventory(directory: Path) -> Dict[str, str]:
    inventory_path = directory / "checksums.sha256"
    if not inventory_path.is_file():
        raise RuntimeError(f"missing checksum inventory: {directory}")
    root = directory.resolve()
    found = {}  # type: Dict[str, str]
    for raw in inventory_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, raw_path = raw.split(maxsplit=1)
        path = Path(raw_path.lstrip("* "))
        if not path.is_absolute():
            path = directory / path
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as error:
            raise RuntimeError(f"checksum path escapes artifact directory: {path}") from error
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"missing or checksum-invalid artifact file: {path}")
        found[str(relative)] = digest
    return found


def load_artifact(
    directory: Path,
    *,
    files: Set[str],
    classification: str,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    inventory = verify_inventory(directory)
    if set(inventory) != files:
        raise RuntimeError(f"unexpected artifact inventory at {directory}: {sorted(inventory)}")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "ok"
        or manifest.get("classification") != classification
        or manifest.get("environment") != "tworoom"
        or manifest.get("partition") != "P2-development-only"
    ):
        raise RuntimeError(f"invalid TwoRoom P2 artifact: {directory}")
    return manifest, inventory


def validate_launchers() -> None:
    for launcher, expected_hash in EXPECTED_LAUNCHER_HASHES.items():
        if not launcher.is_file() or sha256_file(launcher) != expected_hash:
            raise RuntimeError(f"frozen launcher is missing or changed: {launcher}")
    if not DISPATCH_RUNNER.is_file():
        raise RuntimeError(f"missing pipeline dispatcher runner: {DISPATCH_RUNNER}")


def checked_output(arguments: List[str]) -> str:
    process = subprocess.run(
        arguments,
        check=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process.stdout.strip()


def submit(arguments: List[str]) -> Tuple[int, List[str]]:
    command = ["/usr/bin/sbatch", "--parsable", *arguments]
    output = checked_output(command)
    match = re.fullmatch(r"([0-9]+)(?:;[^\s]+)?", output)
    if match is None:
        raise RuntimeError(f"unexpected sbatch response: {output!r}")
    return int(match.group(1)), command


def atomic_json(path: Path, value: Dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite dispatch receipt: {path}")
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, path)


def true_selection(job_id: int) -> Tuple[Dict[str, Any], Dict[str, str]]:
    if job_id != TRUE_SCORE_JOB_ID:
        raise RuntimeError("dispatcher received an unrecognized true-score job ID")
    directory = (
        STABLEWM
        / "derived/scorer-audits/tworoom-v1"
        / f"p2-true-selection-job-{job_id}"
    )
    manifest, inventory = load_artifact(
        directory,
        files={"scores.h5", "manifest.json", "provenance.txt"},
        classification="tworoom_p2_true_scorer_raw_score_selection",
    )
    if (
        int(manifest.get("candidate_count", -1)) != 768
        or int(manifest["M1"]["selected_width"]) not in {256, 512}
        or int(manifest["M2"]["selected_width"]) not in {512, 1024}
        or float(manifest["M2"]["selected_sigma"]) not in M2_SIGMAS
        or manifest.get("output_h5_sha256") != inventory["scores.h5"]
    ):
        raise RuntimeError("invalid completed TwoRoom true-scorer selection")
    return manifest, inventory


def calibration(
    job_id: int, true_manifest: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    if job_id <= 0:
        raise RuntimeError("invalid calibration job ID")
    directory = (
        STABLEWM
        / "derived/scorer-audits/tworoom-v1"
        / f"p2-null-control-calibration-job-{job_id}"
    )
    manifest, inventory = load_artifact(
        directory,
        files={"audit-and-calibrators.h5", "manifest.json", "provenance.txt"},
        classification="tworoom_p2_null_control_scores_and_calibrators",
    )
    selected = manifest.get("selected_configuration", {})
    if (
        int(selected.get("M1_width", -1)) != int(true_manifest["M1"]["selected_width"])
        or int(selected.get("M2_width", -1))
        != int(true_manifest["M2"]["selected_width"])
        or float(selected.get("M2_sigma", -1.0))
        != float(true_manifest["M2"]["selected_sigma"])
        or manifest.get("output_h5_sha256") != inventory["audit-and-calibrators.h5"]
        or manifest.get("inputs", {}).get("true_score_h5_sha256")
        != true_manifest["output_h5_sha256"]
    ):
        raise RuntimeError("calibration artifact changed the selected true configuration")
    return manifest, inventory


def smoke(
    job_id: int,
    true_manifest: Dict[str, Any],
    calibration_manifest: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    if job_id <= 0:
        raise RuntimeError("invalid augmented-smoke job ID")
    directory = (
        STABLEWM
        / "derived/closed-loop-development/tworoom-v1"
        / f"augmented-smoke-job-{job_id}"
    )
    manifest, inventory = load_artifact(
        directory,
        files={"result.h5", "manifest.json", "provenance.txt"},
        classification="tworoom_p2_augmented_closed_loop_weight_development",
    )
    planner = manifest.get("planner", {})
    high = planner.get("high", {})
    low = planner.get("low", {})
    timing = manifest.get("cost", {}).get("timing", {})
    equivalence = manifest.get("cost", {}).get("nominal_equivalence")
    scorer_inputs = manifest.get("cost", {}).get("scorer_artifacts", {})
    if (
        manifest.get("method") != "M2"
        or float(manifest.get("weight", -1.0)) != 1.0
        or int(manifest.get("query", {}).get("pool_index", -1)) != 0
        or int(planner.get("eval_budget_primitive_steps", -1)) != 50
        or int(planner.get("goal_offset_primitive_steps", -1)) != 25
        or tuple(
            int(high.get(key, -1))
            for key in (
                "horizon",
                "receding_horizon",
                "action_block",
                "replan_interval",
                "num_samples",
                "iterations",
                "topk",
            )
        )
        != (2, 1, 1, 5, 300, 20, 10)
        or tuple(
            int(low.get(key, -1))
            for key in (
                "horizon",
                "receding_horizon",
                "action_block",
                "num_samples",
                "iterations",
                "topk",
            )
        )
        != (5, 1, 5, 300, 30, 10)
        or equivalence != {"max_abs": 0.0, "shape": [1, 4], "status": "ok"}
        or int(timing.get("cost_calls", -1)) != 200
        or int(timing.get("completed_high_solves", -1)) != 10
        or int(timing.get("candidate_evaluations", -1)) != 60_000
        or int(manifest.get("diagnostics", {}).get("step_count", -1)) != 50
        or scorer_inputs.get("true_selection_h5_sha256")
        != true_manifest["output_h5_sha256"]
        or scorer_inputs.get("calibration_h5_sha256")
        != calibration_manifest["output_h5_sha256"]
        or manifest.get("inputs", {}).get("candidate_h5_sha256")
        != EXPECTED_CANDIDATE_H5_SHA256
        or manifest.get("output_h5_sha256") != inventory["result.h5"]
    ):
        raise RuntimeError("TwoRoom augmented-planner release smoke did not pass exactly")
    return manifest, inventory


def aggregate(
    job_id: int,
    grid_job_id: int,
    true_manifest: Dict[str, Any],
    calibration_manifest: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    if job_id <= 0 or grid_job_id <= 0:
        raise RuntimeError("invalid augmented-grid or aggregate job ID")
    directory = (
        STABLEWM
        / "derived/closed-loop-development/tworoom-v1"
        / f"augmented-selection-job-{job_id}"
    )
    manifest, inventory = load_artifact(
        directory,
        files={"selection.h5", "manifest.json", "provenance.txt"},
        classification="tworoom_p2_augmented_closed_loop_weight_selection",
    )
    selections = manifest.get("selections", {})
    matching = manifest.get("matching_audit", {})
    if (
        int(manifest.get("array_job_id", -1)) != grid_job_id
        or int(manifest.get("query_count_per_weight", -1)) != 12
        or int(manifest.get("task_count", -1)) != 180
        or set(selections) != {"M1", "M2", "M3"}
        or any(float(selections[method]["selected_weight"]) not in WEIGHTS for method in selections)
        or any(
            not 0 <= int(selections[method]["selected_success_count_of_12"]) <= 12
            for method in selections
        )
        or matching.get("candidate_h5_sha256") != EXPECTED_CANDIDATE_H5_SHA256
        or matching.get("true_selection_h5_sha256")
        != true_manifest["output_h5_sha256"]
        or matching.get("calibration_h5_sha256")
        != calibration_manifest["output_h5_sha256"]
        or manifest.get("output_h5_sha256") != inventory["selection.h5"]
    ):
        raise RuntimeError("invalid completed TwoRoom augmented weight selection")
    canonical = directory.parent / "augmented-selection"
    if not canonical.is_symlink() or canonical.resolve() != directory.resolve():
        raise RuntimeError("TwoRoom augmented-selection canonical link is missing or stale")
    return manifest, inventory


def submission_record(
    role: str, job_id: int, command: List[str], afterok: Optional[str]
) -> Dict[str, Any]:
    return {
        "role": role,
        "job_id": job_id,
        "afterok": afterok,
        "command": command,
    }


def dispatch_after_selection(true_job_id: int) -> Dict[str, Any]:
    true_manifest, true_inventory = true_selection(true_job_id)
    null_id, null_command = submit(
        [
            f"--export=ALL,TRUE_SCORE_JOB_ID={true_job_id},NULL_MAP_JOB_ID={NULL_MAP_JOB_ID}",
            str(NULL_LAUNCHER),
        ]
    )
    autoencoder_id, autoencoder_command = submit(
        [f"--export=ALL,TRUE_SCORE_JOB_ID={true_job_id}", str(AUTOENCODER_LAUNCHER)]
    )
    calibration_dependency = f"{null_id}:{autoencoder_id}"
    calibration_id, calibration_command = submit(
        [
            f"--dependency=afterok:{calibration_dependency}",
            "--export=ALL,"
            f"LABELED_JOB_ID={LABELED_JOB_ID},TRUE_SCORE_JOB_ID={true_job_id},"
            f"NULL_TRAINING_JOB_ID={null_id},AUTOENCODER_TRAINING_JOB_ID={autoencoder_id}",
            str(CALIBRATION_LAUNCHER),
        ]
    )
    next_id, next_command = submit(
        [
            f"--dependency=afterok:{calibration_id}",
            "--export=ALL,PIPELINE_STAGE=after-calibration,"
            f"TRUE_SCORE_JOB_ID={true_job_id},CALIBRATION_JOB_ID={calibration_id}",
            str(DISPATCH_RUNNER),
        ]
    )
    return {
        "input_artifact": {
            "true_score_job_id": true_job_id,
            "true_score_h5_sha256": true_inventory["scores.h5"],
            "true_score_manifest_sha256": true_inventory["manifest.json"],
            "selected_m1_width": true_manifest["M1"]["selected_width"],
            "selected_m2_width": true_manifest["M2"]["selected_width"],
            "selected_m2_sigma": true_manifest["M2"]["selected_sigma"],
        },
        "submissions": [
            submission_record("selected matched-null array", null_id, null_command, None),
            submission_record("selected M2 autoencoder array", autoencoder_id, autoencoder_command, None),
            submission_record(
                "null/control scoring and calibration",
                calibration_id,
                calibration_command,
                calibration_dependency,
            ),
            submission_record(
                "post-calibration dispatcher",
                next_id,
                next_command,
                str(calibration_id),
            ),
        ],
    }


def dispatch_after_calibration(
    true_job_id: int, calibration_job_id: int
) -> Dict[str, Any]:
    true_manifest, _ = true_selection(true_job_id)
    calibration_manifest, calibration_inventory = calibration(
        calibration_job_id, true_manifest
    )
    smoke_id, smoke_command = submit(
        [
            "--export=ALL,"
            f"TRUE_SCORE_JOB_ID={true_job_id},CALIBRATION_JOB_ID={calibration_job_id}",
            str(SMOKE_LAUNCHER),
        ]
    )
    next_id, next_command = submit(
        [
            f"--dependency=afterok:{smoke_id}",
            "--export=ALL,PIPELINE_STAGE=after-smoke,"
            f"TRUE_SCORE_JOB_ID={true_job_id},CALIBRATION_JOB_ID={calibration_job_id},"
            f"SMOKE_JOB_ID={smoke_id}",
            str(DISPATCH_RUNNER),
        ]
    )
    return {
        "input_artifact": {
            "calibration_job_id": calibration_job_id,
            "calibration_h5_sha256": calibration_inventory["audit-and-calibrators.h5"],
            "calibration_manifest_sha256": calibration_inventory["manifest.json"],
            "selected_configuration": calibration_manifest["selected_configuration"],
        },
        "submissions": [
            submission_record("full-budget augmented release smoke", smoke_id, smoke_command, None),
            submission_record("post-smoke dispatcher", next_id, next_command, str(smoke_id)),
        ],
    }


def dispatch_after_smoke(
    true_job_id: int, calibration_job_id: int, smoke_job_id: int
) -> Dict[str, Any]:
    true_manifest, _ = true_selection(true_job_id)
    calibration_manifest, _ = calibration(calibration_job_id, true_manifest)
    smoke_manifest, smoke_inventory = smoke(
        smoke_job_id, true_manifest, calibration_manifest
    )
    grid_id, grid_command = submit(
        [
            "--export=ALL,"
            f"TRUE_SCORE_JOB_ID={true_job_id},CALIBRATION_JOB_ID={calibration_job_id}",
            str(GRID_LAUNCHER),
        ]
    )
    aggregate_id, aggregate_command = submit(
        [
            f"--dependency=afterok:{grid_id}",
            f"--export=ALL,INPUT_ARRAY_JOB_ID={grid_id}",
            str(AGGREGATE_LAUNCHER),
        ]
    )
    final_id, final_command = submit(
        [
            f"--dependency=afterok:{aggregate_id}",
            "--export=ALL,PIPELINE_STAGE=after-aggregate,"
            f"TRUE_SCORE_JOB_ID={true_job_id},CALIBRATION_JOB_ID={calibration_job_id},"
            f"SMOKE_JOB_ID={smoke_job_id},GRID_JOB_ID={grid_id},"
            f"AGGREGATE_JOB_ID={aggregate_id}",
            str(DISPATCH_RUNNER),
        ]
    )
    return {
        "input_artifact": {
            "smoke_job_id": smoke_job_id,
            "smoke_h5_sha256": smoke_inventory["result.h5"],
            "smoke_manifest_sha256": smoke_inventory["manifest.json"],
            "smoke_episode_success": smoke_manifest["episode_success"],
        },
        "submissions": [
            submission_record("180-task augmented weight grid", grid_id, grid_command, None),
            submission_record("augmented weight selection", aggregate_id, aggregate_command, str(grid_id)),
            submission_record("pipeline completion validator", final_id, final_command, str(aggregate_id)),
        ],
    }


def validate_after_aggregate(
    true_job_id: int,
    calibration_job_id: int,
    smoke_job_id: int,
    grid_job_id: int,
    aggregate_job_id: int,
) -> Dict[str, Any]:
    true_manifest, _ = true_selection(true_job_id)
    calibration_manifest, _ = calibration(calibration_job_id, true_manifest)
    smoke(smoke_job_id, true_manifest, calibration_manifest)
    aggregate_manifest, aggregate_inventory = aggregate(
        aggregate_job_id, grid_job_id, true_manifest, calibration_manifest
    )
    return {
        "input_artifact": {
            "grid_job_id": grid_job_id,
            "aggregate_job_id": aggregate_job_id,
            "selection_h5_sha256": aggregate_inventory["selection.h5"],
            "selection_manifest_sha256": aggregate_inventory["manifest.json"],
            "selected_weights": {
                method: aggregate_manifest["selections"][method]["selected_weight"]
                for method in ("M1", "M2", "M3")
            },
        },
        "submissions": [],
        "pipeline_complete": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("after-selection", "after-calibration", "after-smoke", "after-aggregate"),
        required=True,
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--true-score-job-id", type=int, required=True)
    parser.add_argument("--calibration-job-id", type=int)
    parser.add_argument("--smoke-job-id", type=int)
    parser.add_argument("--grid-job-id", type=int)
    parser.add_argument("--aggregate-job-id", type=int)
    args = parser.parse_args()
    if args.output_json.exists():
        raise SystemExit("refusing to repeat a completed TwoRoom P2 dispatch stage")
    started = time.time()
    validate_launchers()

    if args.stage == "after-selection":
        payload = dispatch_after_selection(args.true_score_job_id)
    elif args.stage == "after-calibration":
        if args.calibration_job_id is None:
            raise SystemExit("after-calibration requires --calibration-job-id")
        payload = dispatch_after_calibration(
            args.true_score_job_id, args.calibration_job_id
        )
    elif args.stage == "after-smoke":
        if args.calibration_job_id is None or args.smoke_job_id is None:
            raise SystemExit("after-smoke requires calibration and smoke job IDs")
        payload = dispatch_after_smoke(
            args.true_score_job_id, args.calibration_job_id, args.smoke_job_id
        )
    else:
        required = (
            args.calibration_job_id,
            args.smoke_job_id,
            args.grid_job_id,
            args.aggregate_job_id,
        )
        if any(value is None for value in required):
            raise SystemExit("after-aggregate requires all upstream job IDs")
        payload = validate_after_aggregate(
            args.true_score_job_id,
            int(args.calibration_job_id),
            int(args.smoke_job_id),
            int(args.grid_job_id),
            int(args.aggregate_job_id),
        )

    receipt = {
        "status": "ok",
        "classification": f"tworoom_p2_pipeline_dispatch_{args.stage}",
        "environment": "tworoom",
        "partition": "P2-development-only",
        "reporting_rule": "mechanical dependency gate only; P2 values are not confirmatory results",
        "stage": args.stage,
        "launcher_sha256": {
            str(path): digest for path, digest in EXPECTED_LAUNCHER_HASHES.items()
        },
        "dispatcher_runner": str(DISPATCH_RUNNER),
        "elapsed_seconds": time.time() - started,
        **payload,
    }
    atomic_json(args.output_json, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
