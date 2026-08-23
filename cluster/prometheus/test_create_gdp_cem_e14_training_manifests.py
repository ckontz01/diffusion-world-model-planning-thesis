"""Tests for frozen E14 identifier-only training manifests."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def test_training_manifest_bijections(tmp_path: Path) -> None:
    endpoint = tmp_path / "endpoint.tsv"
    sage = tmp_path / "sage.tsv"
    script = Path(__file__).with_name("create_gdp_cem_e14_training_manifests.py")
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--endpoint-output",
            str(endpoint),
            "--sage-output",
            str(sage),
        ],
        check=True,
    )
    with endpoint.open(newline="", encoding="utf-8") as stream:
        endpoint_rows = list(csv.DictReader(stream, delimiter="\t"))
    with sage.open(newline="", encoding="utf-8") as stream:
        sage_rows = list(csv.DictReader(stream, delimiter="\t"))
    assert [int(row["array_id"]) for row in endpoint_rows] == list(range(32))
    assert [int(row["array_id"]) for row in sage_rows] == list(range(6))
    assert len(
        {(row["task"], row["condition"], row["seed"]) for row in endpoint_rows}
    ) == 32
    assert len({(row["task"], row["seed"]) for row in sage_rows}) == 6
    for row in endpoint_rows:
        diagnostic = row["condition"].endswith(("shuffled_goal", "unconditional"))
        if diagnostic:
            assert row["seed"] == "6101"

