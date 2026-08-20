#!/usr/bin/env python3
"""Outcome-free artifact, isolation, and capacity preflight for E11."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import torch

import acid_alt_d2_models as d2
import create_gdp_cem_e11_d3_manifest as d3_manifest
import evaluate_gdp_cem_e11_d3 as evaluate
import gdp_cem_e11_specs as spec


EXPECTED_AVAILABLE = spec.UNTOUCHED_CAPACITY


def core_path(root: Path, task: str, arm: str, seed: int) -> Path:
    task_spec = spec.TASK_SPEC[task]
    position = spec.seed_index(seed)
    if arm == "reachability":
        job, index = task_spec["reachability_job"], position
    else:
        job = task_spec["scorer_job"]
        index = position if arm == "acid" else position + 6
    return (
        root
        / "results/acid-alternative/scorers"
        / task
        / arm
        / "true"
        / f"seed-{seed}-job-{job}-{index}"
        / "best.pt"
    )


def proposal_summary_path(
    root: Path, task: str, condition: str, seed: int
) -> Path:
    task_spec = spec.TASK_SPEC[task]
    if seed == 6101:
        if condition == "gaussian_true":
            return (
                root
                / "results/acid-alternative/gdp-cem-e7p-proposals"
                / task
                / condition
                / f"seed-6101-job-297703-{task_spec['e7_gaussian_index']}"
                / "summary.json"
            )
        return (
            root
            / "results/acid-alternative/gdp-cem-e10v-train"
            / task
            / condition
            / f"seed-6101-job-297778-{task_spec['e10v_indices'][condition]}"
            / "summary.json"
        )
    condition_index = ("vp_true", "vp_shuffled_goal", "gaussian_true").index(
        condition
    )
    index = task_spec["e10m_base"] + (seed - 6102) * 3 + condition_index
    return (
        root
        / "results/acid-alternative/gdp-cem-e10m-train"
        / task
        / condition
        / f"seed-{seed}-job-297788-{index}"
        / "summary.json"
    )


def read_episodes(path: Path) -> set[int]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames is None or "episode_id" not in reader.fieldnames:
            raise RuntimeError("invalid E11 preflight identifier manifest")
        if "success" in reader.fieldnames:
            raise RuntimeError("E11 preflight refuses outcome-bearing identifiers")
        return {int(row["episode_id"]) for row in reader}


def capacity(root: Path, task: str) -> int:
    task_spec = spec.TASK_SPEC[task]
    partition_path = (
        root
        / "manifests/partitions"
        / f"{task}-v1"
        / "episodes-seed-20260728.tsv"
    )
    with partition_path.open(newline="", encoding="utf-8") as stream:
        partition_rows = list(csv.DictReader(stream, delimiter="\t"))
    partition = {int(row["episode_id"]): row for row in partition_rows}
    exclusion_paths = (
        root
        / "manifests/acid-alternative-v1"
        / task
        / "r0-official-seed42.tsv",
        root
        / "manifests/acid-alternative-v1"
        / task
        / "d1-fresh-development.tsv",
        root
        / "manifests/acid-alternative-v3-d2"
        / task
        / "job-297535"
        / "d2-fresh.tsv",
    )
    excluded = set().union(*(read_episodes(path) for path in exclusion_paths))
    dataset = root / "data/stablewm" / task_spec["dataset_file"]
    with h5py.File(dataset, "r") as handle:
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
    return sum(
        partition[episode]["partition"] == "P3"
        and int(length) > 25
        and episode not in excluded
        for episode, length in enumerate(lengths.tolist())
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if d2.sha256_file(args.protocol) != spec.PROTOCOL_SHA256:
        raise RuntimeError("E11 preflight protocol hash differs")
    if not args.source_manifest.is_file():
        raise FileNotFoundError(args.source_manifest)
    if (args.root / "manifests/gdp-cem-e11-d3").exists() or (
        args.root / "results/acid-alternative/gdp-cem-e11-d3"
    ).exists():
        raise RuntimeError("E11 D3 artifact already exists before preflight")

    aggregate_path = (
        args.root
        / "results/acid-alternative/gdp-cem-e10m-p1/analysis/job-297790/summary.json"
    )
    evaluate.validate_e10m(aggregate_path)
    device = torch.device("cpu")
    core_count = 0
    proposal_count = 0
    artifact_records: list[dict[str, str | int]] = []
    statistic_hashes: dict[str, dict[str, str]] = {}
    for task in spec.TASKS:
        task_spec = spec.TASK_SPEC[task]
        dataset = args.root / "data/stablewm" / task_spec["dataset_file"]
        world_model = args.root / "data/stablewm" / task_spec["world_model_file"]
        if dataset.stat().st_mode & 0o222 or world_model.stat().st_mode & 0o222:
            raise RuntimeError(f"E11 {task} dataset/world model is not sealed read-only")
        if d2.sha256_file(dataset) != task_spec["dataset_sha256"]:
            raise RuntimeError(f"E11 {task} dataset hash differs")
        if d2.sha256_file(world_model) != task_spec["world_model_sha256"]:
            raise RuntimeError(f"E11 {task} world-model hash differs")
        artifact_records.extend(
            [
                {
                    "task": task,
                    "seed": -1,
                    "kind": "dataset",
                    "path": str(dataset),
                    "sha256": task_spec["dataset_sha256"],
                },
                {
                    "task": task,
                    "seed": -1,
                    "kind": "world_model",
                    "path": str(world_model),
                    "sha256": task_spec["world_model_sha256"],
                },
            ]
        )
        reference_stats = None
        statistic_hashes[task] = {}
        for seed in spec.SEEDS:
            for arm in spec.CORE_ARMS:
                path = core_path(args.root, task, arm, seed)
                if d2.sha256_file(path) != spec.CORE_CHECKPOINT_SHA256[task][arm][
                    spec.seed_index(seed)
                ]:
                    raise RuntimeError("E11 preflight core hash differs")
                scorer, payload, record = d2.load_core_scorer(
                    path,
                    arm=arm,
                    expected_seed=seed,
                    device=device,
                )
                del scorer, payload
                artifact_records.append(
                    {
                        "task": task,
                        "seed": seed,
                        "kind": arm,
                        "path": str(path),
                        "sha256": record["checkpoint_sha256"],
                    }
                )
                core_count += 1
            for condition in ("vp_true", "vp_shuffled_goal", "gaussian_true"):
                summary = proposal_summary_path(args.root, task, condition, seed)
                model, payload, record = evaluate.load_proposal(
                    summary,
                    task=task,
                    condition=condition,
                    seed=seed,
                    device=device,
                )
                del model
                stats = {
                    key: torch.as_tensor(payload[key]).float()
                    for key in (
                        "latent_mean",
                        "latent_std",
                        "action_mean",
                        "action_std",
                        "robust_low",
                        "robust_high",
                    )
                }
                if reference_stats is None:
                    reference_stats = stats
                elif any(
                    not torch.equal(stats[key], reference_stats[key]) for key in stats
                ):
                    raise RuntimeError(f"E11 {task} proposal statistics differ")
                digest = hashlib.sha256()
                for key in sorted(stats):
                    digest.update(key.encode("utf-8"))
                    digest.update(stats[key].numpy().tobytes())
                statistic_hashes[task][f"{condition}_{seed}"] = digest.hexdigest()
                artifact_records.append(
                    {
                        "task": task,
                        "seed": seed,
                        "kind": condition,
                        "path": str(summary),
                        "sha256": d2.sha256_file(summary),
                        "checkpoint_sha256": record["checkpoint_sha256"],
                    }
                )
                proposal_count += 1
    capacities = {task: capacity(args.root, task) for task in spec.TASKS}
    if capacities != EXPECTED_AVAILABLE or any(
        count < spec.COUNT for count in capacities.values()
    ):
        raise RuntimeError(f"E11 untouched P3 capacity differs: {capacities}")
    if core_count != 27 or proposal_count != 27:
        raise RuntimeError("E11 preflight model grid differs")
    try:
        evaluate.reject_protected_path(Path("/tmp/c1/forbidden.tsv"))
    except RuntimeError:
        protected_rejection = True
    else:
        protected_rejection = False
    if not protected_rejection:
        raise RuntimeError("E11 protected-path rejection failed")
    d3_manifest.atomic_json(
        args.output,
        {
            "status": "ok",
            "kind": "gdp_cem_e11_outcome_free_preflight",
            "core_model_count": core_count,
            "proposal_model_count": proposal_count,
            "artifacts": artifact_records,
            "proposal_statistic_hashes": statistic_hashes,
            "untouched_p3_capacity": capacities,
            "required_starts_per_task": spec.COUNT,
            "protected_path_rejection": protected_rejection,
            "protocol_sha256": d2.sha256_file(args.protocol),
            "source_manifest_sha256": d2.sha256_file(args.source_manifest),
            "e10m_aggregate_sha256": d2.sha256_file(aggregate_path),
            "identifier_inputs_only": True,
            "outcome_columns_read": False,
            "d3_read": False,
            "protected_c1_i1_read": False,
            "claim_allowed": False,
        },
    )
    print(json.dumps({"status": "ok", "capacities": capacities}, sort_keys=True))


if __name__ == "__main__":
    main()
