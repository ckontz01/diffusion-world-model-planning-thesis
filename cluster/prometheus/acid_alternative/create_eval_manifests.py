#!/usr/bin/env python3
"""Freeze official-reproduction, fresh-development, and confirmation starts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

import h5py
import numpy as np

from acid_alternative.io_utils import atomic_write_json, sha256_file

Pair = tuple[int, int]


def read_partitions(path: Path) -> dict[int, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"episode_id", "partition"}.issubset(rows[0]):
        raise ValueError("invalid episode partition manifest")
    return {int(row["episode_id"]): row["partition"] for row in rows}


def _pairs_from_h5(path: Path) -> set[Pair]:
    pairs: set[Pair] = set()
    try:
        with h5py.File(path, "r") as handle:
            possibilities = (
                ("episode_id", "start_step"),
                ("episode_id", "source_step"),
                ("source_episode_id", "source_step"),
            )
            for episode_key, step_key in possibilities:
                if episode_key in handle and step_key in handle:
                    episodes = np.asarray(
                        handle[episode_key][:], dtype=np.int64
                    ).reshape(-1)
                    steps = np.asarray(handle[step_key][:], dtype=np.int64).reshape(-1)
                    if len(episodes) == len(steps):
                        pairs.update(zip(episodes.tolist(), steps.tolist()))
    except OSError:
        return set()
    return pairs


def _pairs_from_tsv(path: Path) -> set[Pair]:
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
    except (OSError, UnicodeDecodeError):
        return set()
    if not rows:
        return set()
    episode_key = next(
        (key for key in ("episode_id", "source_episode_id") if key in rows[0]), None
    )
    step_key = next(
        (key for key in ("start_step", "source_step") if key in rows[0]), None
    )
    if episode_key is None or step_key is None:
        return set()
    return {(int(row[episode_key]), int(row[step_key])) for row in rows}


def find_legacy_pairs(
    paths: Iterable[Path],
    maximum_h5_bytes: int,
    *,
    excluded_path_tokens: Iterable[str] = (),
) -> tuple[set[Pair], list[dict]]:
    pairs: set[Pair] = set()
    sources: list[dict] = []
    files: dict[Path, Path] = {}
    excluded_tokens = tuple(
        token.strip().lower() for token in excluded_path_tokens if token.strip()
    )
    for supplied in paths:
        if supplied.is_file():
            files.setdefault(supplied, Path(supplied.name))
        elif supplied.is_dir():
            for candidate in supplied.rglob("*.tsv"):
                files.setdefault(candidate, candidate.relative_to(supplied))
            for candidate in supplied.rglob("*.h5"):
                if candidate.stat().st_size <= maximum_h5_bytes:
                    files.setdefault(candidate, candidate.relative_to(supplied))
        else:
            # Legacy-result roots are advisory contamination sources.  A clean
            # checkout legitimately will not contain every historical output
            # directory, so record the absence rather than making manifest
            # creation depend on an unrelated optional path.
            sources.append(
                {
                    "path": str(supplied),
                    "status": "missing_optional_root",
                    "pairs_found": 0,
                }
            )
    skipped_other_task = 0
    for path in sorted(files):
        normalized_path = str(files[path]).replace("\\", "/").lower()
        if any(token in normalized_path for token in excluded_tokens):
            skipped_other_task += 1
            continue
        found = _pairs_from_h5(path) if path.suffix == ".h5" else _pairs_from_tsv(path)
        if found:
            pairs.update(found)
            sources.append(
                {
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "pairs_found": len(found),
                }
            )
    if skipped_other_task:
        sources.append(
            {
                "status": "excluded_other_task_paths",
                "tokens": list(excluded_tokens),
                "files_skipped": skipped_other_task,
                "pairs_found": 0,
            }
        )
    return pairs, sources


def write_namespace(
    path: Path,
    selected: list[tuple[int, int, str]],
    *,
    offsets: np.ndarray,
    goal_offset: int,
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    with path.open("w", newline="", encoding="utf-8") as stream:
        fieldnames = (
            "eval_index",
            "episode_id",
            "start_step",
            "dataset_goal_step",
            "declared_goal_offset",
            "source_global_row",
            "goal_global_row",
            "selection_hash",
        )
        writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for index, (episode, start, digest) in enumerate(selected):
            writer.writerow(
                {
                    "eval_index": index,
                    "episode_id": episode,
                    "start_step": start,
                    # StableWorldModel load_chunk uses an exclusive end and then
                    # selects the final element, so an offset of 25 yields +24.
                    "dataset_goal_step": start + goal_offset - 1,
                    "declared_goal_offset": goal_offset,
                    "source_global_row": int(offsets[episode]) + start,
                    "goal_global_row": int(offsets[episode]) + start + goal_offset - 1,
                    "selection_hash": digest,
                }
            )
    return sha256_file(path)


def hashed_selection(
    eligible: list[Pair], *, task: str, seed: int, count: int
) -> list[tuple[int, int, str]]:
    ranked: list[tuple[str, int, int]] = []
    for episode, start in eligible:
        payload = f"{task}\0{seed}\0{episode}\0{start}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        ranked.append((digest, episode, start))
    ranked.sort()
    if len(ranked) < count:
        raise RuntimeError(f"need {count} eligible starts, found {len(ranked)}")
    return [(episode, start, digest) for digest, episode, start in ranked[:count]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--partition-manifest", type=Path, required=True)
    parser.add_argument("--legacy-root", type=Path, action="append", default=[])
    parser.add_argument(
        "--legacy-exclude-path-token",
        action="append",
        default=[],
        help="Case-insensitive path token identifying another task's legacy artifacts.",
    )
    parser.add_argument("--goal-offset", type=int, default=25)
    parser.add_argument("--r0-seed", type=int, default=42)
    parser.add_argument("--r0-count", type=int, default=50)
    parser.add_argument("--development-seed", type=int, default=2026081201)
    parser.add_argument("--development-count", type=int, default=24)
    parser.add_argument("--development-partition", default="P2")
    parser.add_argument("--confirmation-seed", type=int, default=2026081202)
    parser.add_argument("--confirmation-count", type=int, default=50)
    parser.add_argument("--confirmation-partition", default="P4")
    parser.add_argument(
        "--maximum-legacy-h5-bytes", type=int, default=128 * 1024 * 1024
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("refusing a nonempty output directory")
    if (
        min(
            args.goal_offset,
            args.r0_count,
            args.development_count,
            args.confirmation_count,
            args.maximum_legacy_h5_bytes,
        )
        <= 0
    ):
        raise ValueError("counts, offset, and scan size must be positive")
    partitions = read_partitions(args.partition_manifest)
    with h5py.File(args.dataset, "r") as handle:
        offsets = np.asarray(handle["ep_offset"][:], dtype=np.int64)
        lengths = np.asarray(handle["ep_len"][:], dtype=np.int64)
        episode_key = "episode_idx" if "episode_idx" in handle else "ep_idx"
        row_episodes = np.asarray(handle[episode_key][:], dtype=np.int64)
        row_steps = np.asarray(handle["step_idx"][:], dtype=np.int64)
    if len(offsets) != len(lengths) or set(partitions) != set(range(len(lengths))):
        raise RuntimeError("partition and dataset episode sets differ")

    max_start = lengths - args.goal_offset - 1
    valid_mask = row_steps <= max_start[row_episodes]
    valid_global_rows = np.nonzero(valid_mask)[0]
    official_generator = np.random.default_rng(args.r0_seed)
    official_positions = official_generator.choice(
        len(valid_global_rows) - 1, size=args.r0_count, replace=False
    )
    official_rows = np.sort(valid_global_rows[official_positions])
    r0_selected = [
        (
            int(row_episodes[row]),
            int(row_steps[row]),
            hashlib.sha256(
                f"official-lewm\0{args.r0_seed}\0{int(row)}".encode()
            ).hexdigest(),
        )
        for row in official_rows
    ]
    r0_pairs = {(episode, start) for episode, start, _ in r0_selected}

    legacy_pairs, legacy_sources = find_legacy_pairs(
        args.legacy_root,
        args.maximum_legacy_h5_bytes,
        excluded_path_tokens=args.legacy_exclude_path_token,
    )
    all_pairs = [
        (episode, start)
        for episode, length in enumerate(lengths.tolist())
        for start in range(max(0, length - args.goal_offset))
    ]
    development_eligible = [
        pair
        for pair in all_pairs
        if partitions[pair[0]] == args.development_partition
        and pair not in r0_pairs
        and pair not in legacy_pairs
    ]
    development_selected = hashed_selection(
        development_eligible,
        task=args.task,
        seed=args.development_seed,
        count=args.development_count,
    )
    development_pairs = {(episode, start) for episode, start, _ in development_selected}
    confirmation_eligible = [
        pair
        for pair in all_pairs
        if partitions[pair[0]] == args.confirmation_partition
        and pair not in r0_pairs
        and pair not in legacy_pairs
        and pair not in development_pairs
    ]
    confirmation_selected = hashed_selection(
        confirmation_eligible,
        task=args.task,
        seed=args.confirmation_seed,
        count=args.confirmation_count,
    )
    confirmation_pairs = {
        (episode, start) for episode, start, _ in confirmation_selected
    }
    if (
        r0_pairs & development_pairs
        or r0_pairs & confirmation_pairs
        or development_pairs & confirmation_pairs
    ):
        raise RuntimeError("evaluation namespaces overlap")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "R0": args.output_dir / "r0-official-seed42.tsv",
        "D1": args.output_dir / "d1-fresh-development.tsv",
        "C1": args.output_dir / "c1-locked-confirmation.tsv",
    }
    hashes = {
        "R0": write_namespace(
            paths["R0"], r0_selected, offsets=offsets, goal_offset=args.goal_offset
        ),
        "D1": write_namespace(
            paths["D1"],
            development_selected,
            offsets=offsets,
            goal_offset=args.goal_offset,
        ),
        "C1": write_namespace(
            paths["C1"],
            confirmation_selected,
            offsets=offsets,
            goal_offset=args.goal_offset,
        ),
    }
    summary = {
        "status": "ok",
        "kind": "flat_matched_evaluation_manifests",
        "task": args.task,
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "partition_manifest": str(args.partition_manifest),
        "partition_manifest_sha256": sha256_file(args.partition_manifest),
        "goal_offset": args.goal_offset,
        "stable_worldmodel_goal_step_note": "load_chunk end is exclusive; declared offset 25 selects dataset step start+24",
        "namespaces": {
            "R0": {
                "count": len(r0_selected),
                "seed": args.r0_seed,
                "path": str(paths["R0"]),
                "sha256": hashes["R0"],
            },
            "D1": {
                "count": len(development_selected),
                "seed": args.development_seed,
                "partition": args.development_partition,
                "eligible_count": len(development_eligible),
                "path": str(paths["D1"]),
                "sha256": hashes["D1"],
            },
            "C1": {
                "count": len(confirmation_selected),
                "seed": args.confirmation_seed,
                "partition": args.confirmation_partition,
                "eligible_count": len(confirmation_eligible),
                "path": str(paths["C1"]),
                "sha256": hashes["C1"],
            },
        },
        "legacy_unique_pairs_excluded": len(legacy_pairs),
        "legacy_sources": legacy_sources,
        "legacy_excluded_path_tokens": args.legacy_exclude_path_token,
        "maximum_legacy_h5_bytes": args.maximum_legacy_h5_bytes,
        "selection_rule": "ascending SHA256(task + NUL + seed + NUL + episode + NUL + start)",
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
