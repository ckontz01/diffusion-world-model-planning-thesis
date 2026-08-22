#!/usr/bin/env python3
"""Outcome-free external-artifact and remaining-capacity preflight for E13."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

import acid_alt_d2_models as d2
import create_gdp_cem_e13_d4_manifest as create
import evaluate_gdp_cem_e13_d4 as evaluate
import gdp_cem_e13_specs as spec


SMOKE_COUNT = 4


def proposal_summary_path(root: Path, task: str, condition: str, seed: int) -> Path:
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


def identifier_paths(root: Path, task: str) -> dict[str, Path]:
    return {
        "r0": root
        / "manifests/acid-alternative-v1"
        / task
        / "r0-official-seed42.tsv",
        "d1": root
        / "manifests/acid-alternative-v1"
        / task
        / "d1-fresh-development.tsv",
        "d2": root
        / "manifests/acid-alternative-v3-d2"
        / task
        / "job-297535/d2-fresh.tsv",
        "d3": root
        / "manifests/gdp-cem-e11-d3"
        / task
        / "job-297834/d3-untouched.tsv",
    }


def partition_path(root: Path, task: str) -> Path:
    return (
        root
        / "manifests/partitions"
        / spec.TASK_SPEC[task]["partition_variant"]
        / "episodes-seed-20260728.tsv"
    )


def select_p1_smoke(
    partition: dict[int, dict[str, str]], lengths: np.ndarray, task: str
) -> list[tuple[str, int, int]]:
    ranked = []
    for episode, length_value in enumerate(lengths.tolist()):
        if partition[episode]["partition"] != "P1" or int(length_value) <= 25:
            continue
        start = int.from_bytes(
            hashlib.sha256(f"gdp-e13-p1-smoke|{task}|{episode}".encode()).digest()[:8],
            "little",
        ) % (int(length_value) - 25)
        digest = hashlib.sha256(
            f"gdp-e13-p1-smoke|{task}|{episode}|{start}".encode()
        ).hexdigest()
        ranked.append((digest, episode, start))
    ranked.sort()
    selected = ranked[:SMOKE_COUNT]
    if len(selected) != SMOKE_COUNT or len({item[1] for item in selected}) != SMOKE_COUNT:
        raise RuntimeError(f"E13 P1 smoke selection differs for {task}")
    return selected


def write_smoke_manifest(
    output_root: Path,
    *,
    task: str,
    selected: list[tuple[str, int, int]],
    offsets: np.ndarray,
    protocol: Path,
    source_manifest: Path,
    dataset: Path,
    partition: Path,
) -> dict[str, Any]:
    directory = output_root / task
    tsv = directory / "p1-smoke.tsv"
    provenance = directory / "provenance.json"
    if tsv.exists() or provenance.exists():
        raise FileExistsError(f"refusing to overwrite E13 P1 smoke manifest: {task}")
    fields = (
        "eval_index",
        "shard_index",
        "episode_id",
        "start_step",
        "dataset_goal_step",
        "declared_goal_offset",
        "source_global_row",
        "goal_global_row",
        "selection_hash",
    )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    for index, (digest, episode, start) in enumerate(selected):
        writer.writerow(
            {
                "eval_index": index,
                "shard_index": 0,
                "episode_id": episode,
                "start_step": start,
                "dataset_goal_step": start + 24,
                "declared_goal_offset": 25,
                "source_global_row": int(offsets[episode]) + start,
                "goal_global_row": int(offsets[episode]) + start + 24,
                "selection_hash": digest,
            }
        )
    create.atomic_text(tsv, buffer.getvalue())
    value = {
        "status": "ok",
        "kind": "gdp_cem_e13_p1_smoke_manifest",
        "analysis_role": "non_confirmatory_P1_integration_only",
        "task": task,
        "count": SMOKE_COUNT,
        "partition": "P1",
        "selection_namespace": "gdp-e13-p1-smoke",
        "goal_offset": 25,
        "dataset": str(dataset),
        "dataset_sha256": spec.TASK_SPEC[task]["dataset_sha256"],
        "dataset_file_identity": {
            "size": dataset.stat().st_size,
            "mtime_ns": dataset.stat().st_mtime_ns,
            "device": dataset.stat().st_dev,
            "inode": dataset.stat().st_ino,
            "mode": dataset.stat().st_mode,
        },
        "partition_manifest": str(partition),
        "partition_manifest_sha256": spec.EXPECTED_PARTITION_SHA256[task],
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": d2.sha256_file(source_manifest),
        "manifest_tsv": str(tsv),
        "manifest_tsv_sha256": d2.sha256_file(tsv),
        "d3_identifiers_read": False,
        "d3_outcomes_read": False,
        "d4_read": False,
        "protected_p4_c1_i1_read": False,
    }
    create.atomic_json(provenance, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--e12-stage-b-audit", type=Path, required=True)
    parser.add_argument("--e12-training-source-manifest", type=Path, required=True)
    parser.add_argument("--smoke-manifest-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = args.snapshot / (
        "ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md"
    )
    source_manifest = args.snapshot / "SOURCE-MANIFEST.sha256"
    if (
        not protocol.is_file()
        or d2.sha256_file(protocol) != spec.PROTOCOL_SHA256
        or not source_manifest.is_file()
        or os.access(args.snapshot, os.W_OK)
        or args.output.exists()
        or args.smoke_manifest_root.exists()
        or (args.root / "manifests/gdp-cem-e13-d4").exists()
        or (args.root / "results/acid-alternative/gdp-cem-e13-d4").exists()
    ):
        raise RuntimeError("E13 preflight snapshot/output barrier differs")

    evaluate.validate_e10m(
        args.root
        / "results/acid-alternative/gdp-cem-e10m-p1/analysis/job-297790/summary.json"
    )
    e12_audit = evaluate.load_e12_stage_b_audit(
        args.e12_stage_b_audit,
        training_source_manifest=args.e12_training_source_manifest,
    )
    artifact_records: list[dict[str, Any]] = []
    capacities: dict[str, int] = {}
    smoke_records: dict[str, Any] = {}
    device = torch.device("cpu")
    for task in spec.TASKS:
        task_spec = spec.TASK_SPEC[task]
        dataset = args.root / "data/stablewm" / task_spec["dataset_file"]
        world_model = args.root / "data/stablewm" / task_spec["world_model_file"]
        partition_file = partition_path(args.root, task)
        exclusions = identifier_paths(args.root, task)
        for path in (dataset, world_model, partition_file, *exclusions.values()):
            evaluate.reject_protected_path(path)
            if not path.is_file():
                raise FileNotFoundError(path)
        if (
            dataset.stat().st_mode & 0o222
            or world_model.stat().st_mode & 0o222
            or d2.sha256_file(dataset) != task_spec["dataset_sha256"]
            or d2.sha256_file(world_model) != task_spec["world_model_sha256"]
            or d2.sha256_file(partition_file) != spec.EXPECTED_PARTITION_SHA256[task]
            or any(
                d2.sha256_file(path) != spec.EXPECTED_EXCLUSION_SHA256[task][label]
                for label, path in exclusions.items()
            )
        ):
            raise RuntimeError(f"E13 sealed input hash differs for {task}")
        partition = create.read_partition(partition_file)
        excluded = set().union(
            *(create.read_identifier_episodes(path) for path in exclusions.values())
        )
        with h5py.File(dataset, "r") as handle:
            lengths = np.asarray(handle["ep_len"][:], dtype=np.int64).reshape(-1)
            offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64).reshape(-1)
        if (
            len(lengths) != len(offsets)
            or set(partition) != set(range(len(lengths)))
            or any(
                int(partition[episode]["episode_length"]) != int(length)
                for episode, length in enumerate(lengths.tolist())
            )
        ):
            raise RuntimeError(
                f"E13 dataset and partition episode identities differ for {task}"
            )
        capacity = sum(
            partition[episode]["partition"] == "P3"
            and episode not in excluded
            and int(length) > 25
            for episode, length in enumerate(lengths.tolist())
        )
        if capacity != spec.UNTOUCHED_P3_CAPACITY[task]:
            raise RuntimeError(f"E13 untouched P3 capacity differs for {task}")
        capacities[task] = capacity
        selected = select_p1_smoke(partition, lengths, task)
        smoke_records[task] = write_smoke_manifest(
            args.smoke_manifest_root,
            task=task,
            selected=selected,
            offsets=offsets,
            protocol=protocol,
            source_manifest=source_manifest,
            dataset=dataset,
            partition=partition_file,
        )
        for seed in spec.SEEDS:
            for condition in ("vp_true", "gaussian_true"):
                summary = proposal_summary_path(args.root, task, condition, seed)
                model, _, record = evaluate.load_proposal(
                    summary,
                    task=task,
                    condition=condition,
                    seed=seed,
                    device=device,
                )
                del model
                artifact_records.append(
                    {
                        "task": task,
                        "seed": seed,
                        "method": condition,
                        "summary": str(summary),
                        "summary_sha256": d2.sha256_file(summary),
                        "checkpoint_sha256": record["checkpoint_sha256"],
                    }
                )
            entry = evaluate.prism_dp_artifact_entry(
                e12_audit, task=task, seed=seed
            )
            model, _, record = evaluate.load_prism_dp(
                entry, task=task, seed=seed, device=device
            )
            del model
            artifact_records.append(
                {
                    "task": task,
                    "seed": seed,
                    "method": "prism_dp_reconstruction",
                    **record,
                }
            )
    if len(artifact_records) != 27:
        raise RuntimeError("E13 external artifact grid differs")
    output = {
        "status": "ok",
        "kind": "gdp_cem_e13_outcome_free_preflight",
        "analysis_role": "artifact_and_identifier_only_preflight",
        "protocol_sha256": spec.PROTOCOL_SHA256,
        "source_manifest_sha256": d2.sha256_file(source_manifest),
        "e12_stage_b_audit_sha256": e12_audit["audit_sha256"],
        "e12_overall_status_preserved": e12_audit["status"],
        "authorized_e12_prism_dp_artifacts": 9,
        "artifacts": artifact_records,
        "untouched_p3_capacity": capacities,
        "required_starts_per_task": spec.COUNT,
        "p1_smoke_manifests": smoke_records,
        "d3_identifiers_read": True,
        "d3_outcomes_read": False,
        "d4_read": False,
        "protected_p4_c1_i1_read": False,
        "claim_allowed": False,
    }
    create.atomic_json(args.output, output)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
