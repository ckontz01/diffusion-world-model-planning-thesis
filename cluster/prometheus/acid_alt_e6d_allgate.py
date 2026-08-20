"""Install the three frozen E6D all-iteration control arm definitions."""

from __future__ import annotations

from typing import Any

import acid_alt_e6_quantile_models as e6


ARMS = (
    "rdx_shuffled_gate_all_q40",
    "forward_gate_all_q40",
    "acid_gate_all_q40",
)


def arm_spec(arm: str) -> dict[str, Any]:
    common = {
        "integration": "quantile_gate",
        "reject_fraction": 0.40,
        "active_tail_steps": e6.CEM_STEPS,
    }
    if arm == "rdx_shuffled_gate_all_q40":
        return {"score_arm": "rdx", **common, "shuffled": True}
    if arm == "forward_gate_all_q40":
        return {"score_arm": "forward", **common, "shuffled": False}
    if arm == "acid_gate_all_q40":
        return {"score_arm": "acid", **common, "shuffled": False}
    raise ValueError(f"unknown E6D arm: {arm}")


def install() -> None:
    e6.ARMS = ARMS  # type: ignore[assignment]
    e6.arm_spec = arm_spec  # type: ignore[assignment]


def self_test() -> None:
    if len(ARMS) != len(set(ARMS)):
        raise RuntimeError("duplicate E6D arm")
    for arm in ARMS:
        spec = arm_spec(arm)
        if (
            spec["integration"] != "quantile_gate"
            or spec["reject_fraction"] != 0.40
            or spec["active_tail_steps"] != 30
        ):
            raise RuntimeError(f"E6D arm changed: {arm}")


if __name__ == "__main__":
    self_test()
