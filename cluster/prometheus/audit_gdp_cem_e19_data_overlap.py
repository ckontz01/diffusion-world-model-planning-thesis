#!/usr/bin/env python3
"""Audit SAGE dataset identity and episode-only overlap with E14--E18."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np

import gdp_cem_e19_specs as spec


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_sha256(values: Iterable[int]) -> str:
    encoded = "".join(f"{int(value)}\n" for value in sorted(set(values))).encode()
    return hashlib.sha256(encoded).hexdigest()


def set_record(values: Iterable[int], *, preview: int = 20) -> dict:
    result = sorted(set(map(int, values)))
    return {
        "count": len(result),
        "sha256": set_sha256(result),
        "preview": result[:preview],
    }


def normalize_split(payload: dict) -> dict[str, set[int]]:
    def get(name: str) -> set[int]:
        key = f"{name}_episode_idx"
        values = payload[key] if key in payload else payload[name]
        return set(map(int, values))

    return {name: get(name) for name in ("train", "val", "test")}


def read_cache_roles(path: Path) -> tuple[set[int], set[int]]:
    with h5py.File(path, "r") as handle:
        episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
        role = np.asarray(handle["role"][:], dtype=np.uint8)
    if episode.ndim != 1 or role.shape != episode.shape or set(np.unique(role)) != {0, 1}:
        raise RuntimeError(f"invalid identifier/role arrays: {path}")
    train = set(map(int, np.unique(episode[role == 0])))
    validation = set(map(int, np.unique(episode[role == 1])))
    if train.intersection(validation):
        raise RuntimeError(f"episode-level role overlap: {path}")
    return train, validation


def read_episode_h5(path: Path) -> set[int]:
    with h5py.File(path, "r") as handle:
        episode = np.asarray(handle["episode_idx"][:], dtype=np.int64)
    return set(map(int, np.unique(episode)))


def read_query_tsv(path: Path) -> set[int]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream, delimiter="\t")
        if "episode_id" not in (rows.fieldnames or []):
            raise RuntimeError(f"missing episode_id column: {path}")
        return {int(row["episode_id"]) for row in rows}


def h5_identity(path: Path, expected_sha: str, expected_episodes: int) -> dict:
    observed_sha = sha256_file(path)
    with h5py.File(path, "r") as handle:
        keys = sorted(handle.keys())
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
        episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
        step_key = "step_idx" if "step_idx" in handle else "step"
        episode = np.asarray(handle[episode_key][:], dtype=np.int64)
        step = np.asarray(handle[step_key][:], dtype=np.int64)
        shapes = {key: list(handle[key].shape) for key in keys}
        dtypes = {key: str(handle[key].dtype) for key in keys}
    expected_offsets = np.concatenate(
        (np.asarray([0], dtype=np.int64), np.cumsum(lengths[:-1], dtype=np.int64))
    )
    row_count = int(lengths.sum())
    if len(episode) != row_count or len(step) != row_count:
        raise RuntimeError(f"row-count mismatch: {path}")
    episode_at_offsets = episode[offsets]
    episode_ids = np.arange(len(lengths), dtype=np.int64)
    reconstructed_episode = np.repeat(episode_ids, lengths)
    reconstructed_step = np.concatenate(
        [np.arange(int(length), dtype=np.int64) for length in lengths]
    )
    checks = {
        "sha256": observed_sha == expected_sha,
        "episode_count": len(lengths) == expected_episodes,
        "offsets": np.array_equal(offsets, expected_offsets),
        "episode_ids_at_offsets": np.array_equal(episode_at_offsets, episode_ids),
        "episode_rows": np.array_equal(episode, reconstructed_episode),
        "step_rows": np.array_equal(step, reconstructed_step),
    }
    return {
        "path": str(path),
        "expected_sha256": expected_sha,
        "observed_sha256": observed_sha,
        "episode_count": int(len(lengths)),
        "row_count": row_count,
        "minimum_episode_length": int(lengths.min()),
        "maximum_episode_length": int(lengths.max()),
        "lengths_sha256": hashlib.sha256(lengths.tobytes()).hexdigest(),
        "offsets_sha256": hashlib.sha256(offsets.tobytes()).hexdigest(),
        "keys": keys,
        "shapes": shapes,
        "dtypes": dtypes,
        "checks": checks,
        "passed": all(checks.values()),
        "lengths": lengths,
    }


def manifest_records(sage_root: Path, task: str) -> tuple[set[int], list[dict]]:
    episode_ids: set[int] = set()
    rows: list[dict] = []
    for seed in spec.SEEDS:
        for horizon in spec.HORIZONS:
            path = (
                sage_root
                / "data"
                / "manifests"
                / task
                / f"seed{seed}"
                / f"h{horizon}.json"
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            if task == "pusht":
                records = [
                    (int(row["episode_id"]), int(row["start_frame"]))
                    for row in payload["records"]
                ]
            else:
                records = list(
                    zip(
                        map(int, payload["episodes_idx"]),
                        map(int, payload["start_steps"]),
                        strict=True,
                    )
                )
            if len(records) != spec.EXPECTED_EPISODES_PER_CELL:
                raise RuntimeError(f"wrong official record count: {path}")
            for episode, start in records:
                episode_ids.add(episode)
                rows.append(
                    {
                        "task": task,
                        "seed": seed,
                        "horizon": horizon,
                        "episode_id": episode,
                        "start": start,
                        "goal": start + horizon,
                        "manifest": str(path),
                    }
                )
    return episode_ids, rows


def audit_split_and_manifests(
    sage_root: Path, task: str, dataset_identity: dict
) -> tuple[dict, set[int], dict[str, set[int]]]:
    split_path = sage_root / "data" / "splits" / spec.TASKS[task]["split_file"]
    split = normalize_split(json.loads(split_path.read_text(encoding="utf-8")))
    all_ids = set(range(spec.TASKS[task]["episodes"]))
    disjoint = not (
        split["train"].intersection(split["val"])
        or split["train"].intersection(split["test"])
        or split["val"].intersection(split["test"])
    )
    paper_ids, records = manifest_records(sage_root, task)
    lengths = dataset_identity["lengths"]
    valid_rows = all(
        row["episode_id"] in split["test"]
        and row["episode_id"] < len(lengths)
        and row["start"] >= 0
        and row["goal"] < int(lengths[row["episode_id"]])
        for row in records
    )
    result = {
        "split_path": str(split_path),
        "split_sets": {name: set_record(values) for name, values in split.items()},
        "paper_manifest_episode_set": set_record(paper_ids),
        "paper_record_count": len(records),
        "split_disjoint": disjoint,
        "split_complete": set.union(*split.values()) == all_ids,
        "paper_records_valid": valid_rows,
        "paper_records_test_only": paper_ids.issubset(split["test"]),
    }
    result["passed"] = all(
        (
            result["split_disjoint"],
            result["split_complete"],
            result["paper_records_valid"],
            result["paper_records_test_only"],
            result["paper_record_count"] == 900,
        )
    )
    return result, paper_ids, split


def push_lance_identity(h5_path: Path, lance_path: Path) -> dict:
    import stable_worldmodel as swm

    h5_dataset = swm.data.load_dataset(str(h5_path))
    lance_dataset = swm.data.load_dataset(str(lance_path))
    lengths_equal = np.array_equal(h5_dataset.lengths, lance_dataset.lengths)
    offsets_equal = np.array_equal(h5_dataset.offsets, lance_dataset.offsets)
    h5_names = set(h5_dataset.column_names)
    lance_names = set(lance_dataset.column_names)
    ignored = {"episode_idx", "ep_idx", "step_idx", "step", "pixels"}
    h5_numeric = sorted(name for name in h5_names if name not in ignored)
    comparisons = []
    for h5_name in h5_numeric:
        lance_name = h5_name.replace(".", "_")
        if lance_name not in lance_names:
            comparisons.append(
                {"h5_name": h5_name, "lance_name": lance_name, "passed": False}
            )
            continue
        left = np.asarray(h5_dataset.get_col_data(h5_name))
        right = np.asarray(lance_dataset.get_col_data(lance_name))
        if left.dtype.kind in "biuf" and right.dtype.kind in "biuf":
            expected = left.astype(np.float32, copy=False).reshape(right.shape)
            equal = np.array_equal(expected, right)
        else:
            expected = left.astype(str)
            equal = np.array_equal(expected, right.astype(str))
        comparisons.append(
            {
                "h5_name": h5_name,
                "lance_name": lance_name,
                "h5_shape": list(left.shape),
                "lance_shape": list(right.shape),
                "h5_dtype": str(left.dtype),
                "lance_dtype": str(right.dtype),
                "passed": bool(equal),
            }
        )

    total_rows = int(np.sum(h5_dataset.lengths))
    ranked = sorted(
        sorted(
            range(total_rows),
            key=lambda row: hashlib.sha256(
                f"gdp-cem-e19-pusht-frame-audit|{row}".encode()
            ).digest(),
        )[:256]
    )
    left_rows = h5_dataset.get_row_data(ranked)["pixels"]
    right_rows = lance_dataset.get_row_data(ranked)["pixels"]
    if isinstance(right_rows, np.ndarray) and right_rows.dtype == object:
        right_rows = right_rows.tolist()
    decoded = lance_dataset._decode_images(right_rows).numpy()
    left = np.asarray(left_rows)
    if left.ndim == 4 and left.shape[-1] in (1, 3):
        left = np.transpose(left, (0, 3, 1, 2))
    difference = np.abs(left.astype(np.int16) - decoded.astype(np.int16))
    mean_error = float(difference.mean())
    maximum_error = int(difference.max())
    image_gate = mean_error <= 3.0 and maximum_error <= 64
    result = {
        "hdf5_path": str(h5_path),
        "lance_path": str(lance_path),
        "lengths_equal": bool(lengths_equal),
        "offsets_equal": bool(offsets_equal),
        "hdf5_columns": sorted(h5_names),
        "lance_columns": sorted(lance_names),
        "non_image_comparisons": comparisons,
        "sampled_frame_count": len(ranked),
        "sampled_rows_sha256": set_sha256(ranked),
        "mean_absolute_pixel_error": mean_error,
        "maximum_absolute_pixel_error": maximum_error,
        "image_transport_gate_passed": image_gate,
    }
    result["passed"] = (
        lengths_equal
        and offsets_equal
        and comparisons
        and all(row["passed"] for row in comparisons)
        and image_gate
    )
    return result


def add_pairwise(overlap: dict, official: dict[str, set[int]], thesis: dict[str, set[int]]) -> None:
    for official_name, official_values in official.items():
        overlap[official_name] = {}
        for thesis_name, thesis_values in thesis.items():
            overlap[official_name][thesis_name] = set_record(
                official_values.intersection(thesis_values)
            )


def task_overlap(
    *,
    task: str,
    official_split: dict[str, set[int]],
    paper_ids: set[int],
    e14_cache: Path,
    e15_cache: Path,
    e17_cache: Path,
    e16_bank: Path,
    old_p2_queries: Path,
    e18_p2_queries: Path,
    output_dir: Path,
) -> dict:
    e14_train, e14_validation = read_cache_roles(e14_cache)
    e15_train, e15_validation = read_cache_roles(e15_cache)
    e17_train, e17_validation = read_cache_roles(e17_cache)
    e16_evaluation = read_episode_h5(e16_bank)
    old_p2 = read_query_tsv(old_p2_queries)
    e18_p2 = read_query_tsv(e18_p2_queries)
    e18_training = e15_train.union(e17_train)
    thesis_sets = {
        "e14_training": e14_train,
        "e14_offline_validation": e14_validation,
        "e14_e15_selected_p2": old_p2,
        "e15_proposer_training": e15_train,
        "e15_offline_validation": e15_validation,
        "e16_diagnostic_evaluation": e16_evaluation,
        "e17_adapter_training": e17_train,
        "e17_preflight_validation": e17_validation,
        "e18_executed_p2": e18_p2,
        "e18_training_union": e18_training,
    }
    official_sets = {
        "sage_train": official_split["train"],
        "sage_validation": official_split["val"],
        "sage_test": official_split["test"],
        "sage_paper_manifests": paper_ids,
    }
    pairwise: dict = {}
    add_pairwise(pairwise, official_sets, thesis_sets)
    development_seen = set.union(*thesis_sets.values())
    common_untouched = official_split["test"] - development_seen
    common_path = output_dir / f"{task}-common-untouched-episodes.json"
    common_payload = {
        "kind": "gdp_cem_e19_common_untouched_episode_candidates",
        "task": task,
        "selection": (
            "released SAGE test episodes minus E14--E18 known training, "
            "validation, diagnostic, selected-P2, and executed-P2 episode IDs"
        ),
        "episode_ids": sorted(common_untouched),
        "episode_set_sha256": set_sha256(common_untouched),
        "outcome_metric_read": False,
        "evaluation_authorized": False,
    }
    common_path.write_text(
        json.dumps(common_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    critical = paper_ids.intersection(e18_training)
    return {
        "task": task,
        "official_sets": {name: set_record(values) for name, values in official_sets.items()},
        "thesis_sets": {name: set_record(values) for name, values in thesis_sets.items()},
        "pairwise_intersections": pairwise,
        "critical_paper_manifest_vs_e18_training": set_record(critical),
        "critical_zero_overlap": not critical,
        "common_untouched_candidates": set_record(common_untouched),
        "common_untouched_file": common_path.name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sage-root", type=Path, required=True)
    parser.add_argument("--stablewm-root", type=Path, required=True)
    parser.add_argument("--pusht-lance", type=Path, required=True)
    parser.add_argument("--e14-cache", action="append", required=True)
    parser.add_argument("--e15-cache", action="append", required=True)
    parser.add_argument("--e17-cache", action="append", required=True)
    parser.add_argument("--e16-bank", action="append", required=True)
    parser.add_argument("--old-p2-queries", action="append", required=True)
    parser.add_argument("--e18-p2-queries", action="append", required=True)
    parser.add_argument("--lewm-identity", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    def parse_task_paths(values: list[str]) -> dict[str, Path]:
        result = {}
        for value in values:
            task, raw_path = value.split("=", maxsplit=1)
            if task in result or task not in spec.BENCHMARKS:
                raise ValueError(f"invalid task path: {value}")
            result[task] = Path(raw_path)
        if set(result) != set(spec.BENCHMARKS):
            raise ValueError("both pusht and cube task paths are required")
        return result

    roots = {
        "e14_cache": parse_task_paths(args.e14_cache),
        "e15_cache": parse_task_paths(args.e15_cache),
        "e17_cache": parse_task_paths(args.e17_cache),
        "e16_bank": parse_task_paths(args.e16_bank),
        "old_p2_queries": parse_task_paths(args.old_p2_queries),
        "e18_p2_queries": parse_task_paths(args.e18_p2_queries),
    }
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    lewm_identity = json.loads(args.lewm_identity.read_text(encoding="utf-8"))
    if lewm_identity.get("kind") != "gdp_cem_e19_lewm_parameter_identity":
        raise RuntimeError("invalid E19 LeWM identity audit")

    identities = {}
    split_audits = {}
    official_sets = {}
    for task in spec.BENCHMARKS:
        task_spec = spec.TASKS[task]
        identity = h5_identity(
            args.stablewm_root / task_spec["dataset_file"],
            task_spec["dataset_sha256"],
            task_spec["episodes"],
        )
        split_audit, paper_ids, split = audit_split_and_manifests(
            args.sage_root, task, identity
        )
        lengths = identity.pop("lengths")
        del lengths
        identities[task] = identity
        split_audits[task] = split_audit
        official_sets[task] = (paper_ids, split)

    lance = push_lance_identity(
        args.stablewm_root / spec.TASKS["pusht"]["dataset_file"],
        args.pusht_lance,
    )
    overlap = {}
    for task in spec.BENCHMARKS:
        paper_ids, split = official_sets[task]
        overlap[task] = task_overlap(
            task=task,
            official_split=split,
            paper_ids=paper_ids,
            e14_cache=roots["e14_cache"][task],
            e15_cache=roots["e15_cache"][task],
            e17_cache=roots["e17_cache"][task],
            e16_bank=roots["e16_bank"][task],
            old_p2_queries=roots["old_p2_queries"][task],
            e18_p2_queries=roots["e18_p2_queries"][task],
            output_dir=output,
        )

    data_gate = (
        all(identity["passed"] for identity in identities.values())
        and all(row["passed"] for row in split_audits.values())
        and lance["passed"]
        and bool(lewm_identity.get("all_source_files_verified"))
    )
    zero_overlap = all(row["critical_zero_overlap"] for row in overlap.values())
    payload = {
        "kind": "gdp_cem_e19_dataset_identity_and_episode_overlap_audit",
        "status": "passed" if data_gate else "failed",
        "dataset_identity": identities,
        "split_and_manifest_identity": split_audits,
        "pusht_lance_transport_identity": lance,
        "lewm_parameter_identity": lewm_identity,
        "lewm_parameter_identity_sha256": sha256_file(args.lewm_identity),
        "matched_lewm_parameter_identity_passed": bool(
            lewm_identity.get("all_parameter_identical")
        ),
        "overlap": overlap,
        "data_identity_gate_passed": data_gate,
        "critical_zero_overlap_all_tasks": zero_overlap,
        "native_reproduction_allowed_by_data": data_gate,
        "matched_paper_manifest_comparison_allowed_by_overlap": zero_overlap,
        "protocol_sha256": sha256_file(args.protocol),
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "identifier_fields_only": True,
        "performance_metric_read": False,
        "d3_d4_metric_read": False,
        "d5_read": False,
        "p3_p4_c1_i1_read": False,
        "evaluation_authorized": False,
    }
    audit_path = output / "DATA-OVERLAP-AUDIT.json"
    audit_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in output.iterdir() if path.name != "sha256.txt")
    with (output / "sha256.txt").open("x", encoding="utf-8") as stream:
        for path in files:
            stream.write(f"{sha256_file(path)}  {path.name}\n")
    if not data_gate:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
