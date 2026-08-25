from __future__ import annotations

import numpy as np
import torch

from evaluate_gdp_cem_e15_offline import array_sha256, scientific_label


def test_offline_metric_labels_cover_frozen_scientific_notation() -> None:
    assert [scientific_label(x) for x in (1.0e-6, 1.0e-4, 1.0e-3, 1.0e-2, 5.0e-2)] == [
        "1e-6",
        "1e-4",
        "1e-3",
        "1e-2",
        "5e-2",
    ]


def test_array_hash_is_identical_for_numpy_and_cpu_tensor() -> None:
    value = np.arange(18, dtype=np.int64).reshape(3, 6)
    assert array_sha256(value) == array_sha256(torch.from_numpy(value.copy()))
