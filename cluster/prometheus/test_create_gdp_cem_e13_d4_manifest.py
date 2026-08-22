#!/usr/bin/env python3
"""Synthetic determinism/isolation test for the E13 D4 manifest generator."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

import create_gdp_cem_e13_d4_manifest as create


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_identifier(path: Path, episodes: list[int]) -> None:
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("episode_id",), delimiter="\t")
        writer.writeheader()
        for episode in episodes:
            writer.writerow({"episode_id": episode})


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="e13-manifest-test-") as temporary:
        root = Path(temporary)
        dataset = root / "dataset.h5"
        episode_count = 410
        lengths = np.full(episode_count, 30, dtype=np.int64)
        offsets = np.arange(episode_count, dtype=np.int64) * 30
        with h5py.File(dataset, "x") as handle:
            handle.create_dataset("ep_len", data=lengths)
            handle.create_dataset("ep_offset", data=offsets)
        partition = root / "partition.tsv"
        with partition.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=("episode_id", "episode_length", "partition"),
                delimiter="\t",
            )
            writer.writeheader()
            for episode in range(episode_count):
                writer.writerow(
                    {
                        "episode_id": episode,
                        "episode_length": 30,
                        "partition": "P3",
                    }
                )
        exclusions = {}
        for label, episode in (("r0", 0), ("d1", 1), ("d2", 2), ("d3", 3)):
            path = root / f"{label}.tsv"
            write_identifier(path, [episode])
            exclusions[label] = path
        protocol = Path(__file__).with_name(
            "ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md"
        )
        source_manifest = root / "SOURCE-MANIFEST.sha256"
        source_manifest.write_text("synthetic\n", encoding="utf-8")
        output_tsv = root / "selected.tsv"
        output_json = root / "provenance.json"

        create.EXPECTED_DATASET_SHA256["pusht"] = sha(dataset)
        create.EXPECTED_PARTITION_SHA256["pusht"] = sha(partition)
        create.EXPECTED_EXCLUSION_SHA256["pusht"] = {
            label: sha(path) for label, path in exclusions.items()
        }
        create.spec.UNTOUCHED_P3_CAPACITY["pusht"] = 406
        previous = sys.argv
        try:
            sys.argv = [
                "create_gdp_cem_e13_d4_manifest.py",
                "--task",
                "pusht",
                "--dataset",
                str(dataset),
                "--partition-manifest",
                str(partition),
                "--exclusion",
                "r0",
                str(exclusions["r0"]),
                "--exclusion",
                "d1",
                str(exclusions["d1"]),
                "--exclusion",
                "d2",
                str(exclusions["d2"]),
                "--exclusion",
                "d3",
                str(exclusions["d3"]),
                "--protocol",
                str(protocol),
                "--source-manifest",
                str(source_manifest),
                "--output-tsv",
                str(output_tsv),
                "--output-json",
                str(output_json),
            ]
            create.main()
        finally:
            sys.argv = previous
        with output_tsv.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        provenance = json.loads(output_json.read_text(encoding="utf-8"))
        episodes = [int(row["episode_id"]) for row in rows]
        if (
            len(rows) != create.COUNT
            or len(set(episodes)) != create.COUNT
            or set(episodes).intersection({0, 1, 2, 3})
            or provenance["eligible_untouched_p3_episodes"] != 406
            or provenance["selected_exclusion_intersections"]
            != {"r0": 0, "d1": 0, "d2": 0, "d3": 0}
            or any(
                row["selection_hash"]
                != create.selection_hash(
                    "pusht", int(row["episode_id"]), int(row["start_step"])
                )
                for row in rows
            )
        ):
            raise RuntimeError("E13 synthetic manifest selection failed")
        try:
            create.atomic_text(output_tsv, "must not replace\n")
        except FileExistsError:
            pass
        else:
            raise RuntimeError("E13 atomic publisher overwrote an existing output")
    print("E13 synthetic manifest tests: ok")


if __name__ == "__main__":
    main()
