from __future__ import annotations

import csv
from pathlib import Path

import h5py
import numpy as np

import audit_gdp_cem_e19_data_overlap as audit


def test_role_cache_is_episode_disjoint(tmp_path: Path) -> None:
    path = tmp_path / "cache.h5"
    with h5py.File(path, "x") as handle:
        handle.create_dataset("episode_idx", data=np.asarray([1, 1, 2, 3, 3]))
        handle.create_dataset("role", data=np.asarray([0, 0, 0, 1, 1], dtype=np.uint8))
    train, validation = audit.read_cache_roles(path)
    assert train == {1, 2}
    assert validation == {3}


def test_query_reader_and_set_hash_ignore_order_and_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "queries.tsv"
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["episode_id"], delimiter="\t")
        writer.writeheader()
        writer.writerows([{"episode_id": 3}, {"episode_id": 1}, {"episode_id": 3}])
    assert audit.read_query_tsv(path) == {1, 3}
    assert audit.set_sha256([3, 1, 3]) == audit.set_sha256([1, 3])


def test_split_normalization_supports_both_released_shapes() -> None:
    legacy = {
        "train_episode_idx": [0, 1],
        "val_episode_idx": [2],
        "test_episode_idx": [3],
    }
    compact = {"train": [0, 1], "val": [2], "test": [3]}
    assert audit.normalize_split(legacy) == audit.normalize_split(compact)
