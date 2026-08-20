#!/usr/bin/env python3
"""CPU tests for E6's frozen feasibility-gate semantics."""

from __future__ import annotations

from typing import Any

import torch
from torch import nn

import acid_alt_e6_quantile_models as e6


class ProbeBase(nn.Module):
    def __init__(self, *, tail_steps: int, reject_fraction: float) -> None:
        super().__init__()
        self.call_count = 0
        self.lambda_weight = 0.0
        self.diagnostic_history: list[dict[str, Any]] = []
        self.raw = torch.arange(e6.CEM_SAMPLES, dtype=torch.float32)[None]
        self.spec = {
            "integration": "quantile_gate",
            "active_tail_steps": tail_steps,
            "reject_fraction": reject_fraction,
        }

    @property
    def rollout_model(self):
        return self

    def _rollout_once(self, info: dict[str, Any], actions: torch.Tensor):
        del info
        goal = torch.arange(e6.CEM_SAMPLES - 1, -1, -1, dtype=torch.float32)[None]
        trajectory = torch.zeros(1, e6.CEM_SAMPLES, 6, 2)
        action_tensor = torch.zeros(1, e6.CEM_SAMPLES, 5, 1)
        goal_embedding = torch.zeros(1, 2)
        return goal, trajectory, action_tensor, goal_embedding

    def raw_cost(self, trajectory, actions, goal_embedding):
        del trajectory, actions, goal_embedding
        return self.raw


def build_probe(*, tail_steps: int = 5, reject_fraction: float = 0.40):
    probe = object.__new__(e6.E6CostModel)
    nn.Module.__init__(probe)
    probe.arm = "rdx_gate_tail5_q40"
    probe.spec = {
        "score_arm": "rdx",
        "integration": "quantile_gate",
        "active_tail_steps": tail_steps,
        "reject_fraction": reject_fraction,
    }
    probe.base = ProbeBase(tail_steps=tail_steps, reject_fraction=reject_fraction)
    probe.record_diagnostics = True
    probe.diagnostic_history = []
    return probe


def main() -> None:
    e6.self_test()
    actions = torch.zeros(1, e6.CEM_SAMPLES, 5, 1)
    model = build_probe()
    for index in range(25):
        returned = model.get_cost({}, actions)
        expected = torch.arange(299, -1, -1, dtype=torch.float32)[None]
        if not torch.equal(returned, expected):
            raise RuntimeError(f"inactive E6 call {index + 1} changed goal costs")
    gated = model.get_cost({}, actions)
    if int((gated == gated.max()).sum()) != 120:
        raise RuntimeError("q40 must reject exactly 120 candidates")
    if model.diagnostic_history[-1]["iteration_in_solve"] != 26:
        raise RuntimeError("tail-five activation starts on the wrong iteration")
    if model.diagnostic_history[-1]["goal_elite_rejected_count"] != [30]:
        raise RuntimeError("probe did not veto the deliberately conflicting elites")
    for _ in range(4):
        model.get_cost({}, actions)
    wrapped = model.get_cost({}, actions)
    if not torch.equal(
        wrapped, torch.arange(299, -1, -1, dtype=torch.float32)[None]
    ):
        raise RuntimeError("E6 solve-relative iteration did not wrap after 30 calls")

    q20 = build_probe(tail_steps=30, reject_fraction=0.20)
    output = q20.get_cost({}, actions)
    if int((output == output.max()).sum()) != 60:
        raise RuntimeError("q20 must reject exactly 60 candidates")
    print("E6 quantile-model tests: ok")


if __name__ == "__main__":
    main()
