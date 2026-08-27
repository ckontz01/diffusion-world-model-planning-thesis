from __future__ import annotations

import pytest

from gdp_cem_e16_closed_loop import (
    candidate_count_for_arm,
    family_for_arm,
    is_continuation_arm,
)


def test_arm_registry() -> None:
    assert family_for_arm("vad_greedy_300") == "vad"
    assert family_for_arm("vad_continuation") == "vad"
    assert family_for_arm("diagonal_gaussian_continuation") == "diagonal_gaussian"
    assert family_for_arm("direct_gmm_continuation") == "direct_gmm"
    assert candidate_count_for_arm("vad_greedy_300") == 300
    assert candidate_count_for_arm("vad_greedy_576") == 576
    assert candidate_count_for_arm("vad_continuation") == 64
    assert is_continuation_arm("vad_continuation")
    assert not is_continuation_arm("vad_greedy_576")


def test_invalid_arm_rejected() -> None:
    with pytest.raises(ValueError):
        family_for_arm("invalid")  # type: ignore[arg-type]
