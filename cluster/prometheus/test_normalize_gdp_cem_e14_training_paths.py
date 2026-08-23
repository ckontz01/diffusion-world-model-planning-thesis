from __future__ import annotations

import hashlib
from pathlib import Path

from normalize_gdp_cem_e14_training_paths import (
    resolve_seed_directory,
    verify_completed_training,
    write_lf_tsv,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_training_directory(path: Path) -> None:
    path.mkdir(parents=True)
    names = ("best.pt", "training.jsonl", "summary.json")
    for name in names:
        (path / name).write_text(name, encoding="utf-8")
    (path / "sha256.txt").write_text(
        "".join(
            f"{digest(path / name)}  /physical/{name}\n" for name in names
        ),
        encoding="utf-8",
    )


def test_hidden_carriage_return_directory_is_resolved_without_mutation(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "endpoint" / "pusht" / "vad_true"
    physical = parent / "seed-6101\r"
    make_training_directory(physical)
    resolved = resolve_seed_directory(parent, 6101)
    assert resolved == physical.resolve()
    verify_completed_training(resolved)
    assert not (parent / "seed-6101").exists()


def test_clean_manifest_writer_contains_no_carriage_returns(tmp_path: Path) -> None:
    output = tmp_path / "endpoint.tsv"
    write_lf_tsv(
        output,
        ("array_id", "task", "condition", "seed"),
        [
            {
                "array_id": 0,
                "task": "pusht",
                "condition": "vad_true",
                "seed": 6101,
            }
        ],
    )
    assert b"\r" not in output.read_bytes()
    assert output.read_bytes().endswith(b"\n")
