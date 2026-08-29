from __future__ import annotations

import gc
import os
from pathlib import Path

import numpy as np
import pytest
import torch

from compare_gdp_cem_e19_discrepancy import (
    FLAT_DIRS,
    OBJECT_FILES,
    load_compat,
    load_official_runtime,
    mean_spearman,
    rank_positions,
    replace_first_plan_images,
    sha256_file,
    state_record,
    to_chw,
)
import gdp_cem_e19_specs as e19_spec


def test_rank_positions_and_spearman_are_exact() -> None:
    left = torch.tensor([[3.0, 1.0, 2.0]])
    same = torch.tensor([[30.0, 10.0, 20.0]])
    reversed_cost = torch.tensor([[1.0, 3.0, 2.0]])
    assert torch.equal(rank_positions(left), torch.tensor([[2, 0, 1]]))
    assert mean_spearman(left, same) == 1.0
    assert mean_spearman(left, reversed_cost) == -1.0


def test_to_chw_accepts_hwc_and_chw() -> None:
    hwc = np.zeros((2, 8, 9, 3), dtype=np.uint8)
    chw = np.zeros((2, 3, 8, 9), dtype=np.uint8)
    assert to_chw(hwc).shape == (2, 3, 8, 9)
    assert to_chw(chw).shape == (2, 3, 8, 9)


def test_replace_first_plan_images_preserves_non_image_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        "compare_gdp_cem_e19_discrepancy.prepared_images",
        lambda rows: torch.from_numpy(rows).to(torch.bfloat16),
    )
    info = {
        "pixels": torch.zeros(2, 1, 3, 4, 5, dtype=torch.bfloat16),
        "goal": torch.zeros(2, 2, 3, 4, 5, dtype=torch.bfloat16),
        "_proposal_pixels_raw": torch.zeros(2, 3, 4, 5, 3, dtype=torch.uint8),
        "state": torch.tensor([[1.0], [2.0]]),
    }
    current = np.zeros((2, 3, 4, 5), dtype=np.uint8)
    goal = np.ones((2, 3, 4, 5), dtype=np.uint8)
    output = replace_first_plan_images(info, current, goal)
    assert output["pixels"].shape == info["pixels"].shape
    assert output["goal"].shape == info["goal"].shape
    assert output["_proposal_pixels_raw"].shape == info["_proposal_pixels_raw"].shape
    assert torch.equal(output["state"], info["state"])
    assert output["goal"].bool().all()


@pytest.mark.parametrize("task", e19_spec.BENCHMARKS)
def test_exact_release_loads_match_on_cluster(task: str) -> None:
    flat_text = os.environ.get("E19_DIAGNOSTIC_FLAT_ROOT")
    stablewm_text = os.environ.get("E19_DIAGNOSTIC_STABLEWM_ROOT")
    if flat_text is None or stablewm_text is None:
        pytest.skip("cluster checkpoint roots not supplied")
    flat = Path(flat_text) / FLAT_DIRS[task]
    object_path = Path(stablewm_text) / OBJECT_FILES[task]
    expected = e19_spec.TASKS[task]
    assert sha256_file(flat / "config.json") == expected["lewm_config_sha256"]
    assert sha256_file(flat / "weights.pt") == expected["lewm_weights_sha256"]
    assert sha256_file(object_path) == expected["e18_object_sha256"]
    compatibility = load_compat(object_path)
    official, _ = load_official_runtime(
        flat / "config.json", flat / "weights.pt"
    )
    assert state_record(compatibility)["tensors"] == state_record(official)["tensors"]
    del compatibility, official
    gc.collect()
