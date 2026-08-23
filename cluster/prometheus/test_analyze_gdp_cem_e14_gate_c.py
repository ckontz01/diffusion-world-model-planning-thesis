from __future__ import annotations

from pathlib import Path

import gdp_cem_e14_specs as spec
from analyze_gdp_cem_e14_gate_c import paired_bootstrap, read_manifest


def synthetic_outcomes(
    true_value: int, control_value: int
) -> dict[tuple[str, int, int, str, int], int]:
    result = {}
    for task in spec.TASKS:
        for horizon in spec.GATE_C_HORIZONS:
            for seed in spec.MODEL_SEEDS:
                for base in range(spec.GATE_C_BASE_STARTS):
                    result[(task, horizon, seed, "vad_true", base)] = true_value
                    result[(task, horizon, seed, "vad_gaussian", base)] = control_value
    return result


def test_paired_bootstrap_keeps_start_and_seed_clusters_together() -> None:
    result = paired_bootstrap(
        synthetic_outcomes(1, 0),
        true_arm="vad_true",
        control_arm="vad_gaussian",
    )
    assert result["point_difference_fraction"] == 1.0
    assert result["ci95_fraction"] == [1.0, 1.0]
    assert result["draws"] == 10_000
    assert result["resampling_unit"].startswith("base_start")


def test_gate_c_manifest_reader_rejects_crlf(tmp_path: Path) -> None:
    path = tmp_path / "evaluation.tsv"
    header = "array_id\ttask\tarm\tmodel_seed\thorizon\tshard"
    path.write_bytes((header + "\r\n0\tpusht\tbase_cem\t6101\t25\t0\r\n").encode())
    try:
        read_manifest(path)
    except RuntimeError as error:
        assert "CR bytes" in str(error)
    else:
        raise AssertionError("CRLF Gate-C manifest was accepted")
