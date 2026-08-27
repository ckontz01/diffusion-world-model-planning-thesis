from __future__ import annotations

import numpy as np
import pytest

from build_gdp_cem_e17_transition_state_cache import select_unique_transition_rows


def arrays():
    role = np.asarray([0, 0, 0, 1], dtype=np.uint8)
    source = np.asarray([3, 3, 3, 9], dtype=np.int64)
    local = np.asarray([18, 18, 23, 24], dtype=np.int64)
    raw = np.asarray([100, 100, 100, 200], dtype=np.int64)
    episode = np.asarray([4, 4, 4, 8], dtype=np.int64)
    step = np.asarray([7, 7, 7, 11], dtype=np.int64)
    tau = np.asarray([15, 15, 20, 15], dtype=np.int64)
    state = np.arange(8, dtype=np.float32).reshape(4, 2)
    state[1] = state[0]
    action = np.zeros((4, 25, 1), dtype=np.float32)
    action[0, :15] = 0.25
    action[1] = action[0]
    action[2, :20] = 0.5
    action[3, :15] = -0.25
    mask = np.arange(25)[None] < tau[:, None]
    return {
        "role": role,
        "source": source,
        "local": local,
        "raw_row": raw,
        "episode": episode,
        "step": step,
        "tau": tau,
        "state": state,
        "action_raw": action,
        "action_mask": mask,
    }


def test_unique_transition_rows_collapse_only_same_source_tau() -> None:
    selected = select_unique_transition_rows(**arrays())
    assert selected.tolist() == [0, 2, 3]


def test_unique_transition_rows_reject_payload_disagreement() -> None:
    value = arrays()
    value["action_raw"][1, 0, 0] = 0.75
    with pytest.raises(RuntimeError, match="action_raw"):
        select_unique_transition_rows(**value)
