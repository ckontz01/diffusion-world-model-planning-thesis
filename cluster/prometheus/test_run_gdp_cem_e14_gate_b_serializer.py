from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from run_gdp_cem_e14_gate_b_serializer import atomic_json, json_dumps


def test_numpy_scalars_are_serialized_without_changing_values(tmp_path: Path) -> None:
    value = {
        "gate": np.bool_(True),
        "count": np.int64(7),
        "score": np.float32(1.25),
    }
    output = tmp_path / "audit.json"
    atomic_json(output, value)
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "gate": True,
        "count": 7,
        "score": 1.25,
    }
    assert json.loads(json_dumps(value))["gate"] is True
