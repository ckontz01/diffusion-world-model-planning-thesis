"""Frozen quantile-constrained CEM integration for E6.

This module deliberately reuses the already trained E3 scorers.  It changes
only how a verifier is allowed to affect CEM: feasible candidates retain the
exact goal cost, while a fixed worst quantile is excluded from the elite set.
"""

from __future__ import annotations

from typing import Any, Literal

import torch
from torch import nn

import acid_alt_d2_models as d2


CEM_STEPS = 30
CEM_SAMPLES = 300
CEM_TOPK = 30

E6Arm = Literal[
    "b0",
    "acid_cont",
    "forward_cont",
    "rdx_cont",
    "rdx_gate_tail5_q20",
    "rdx_gate_tail5_q40",
    "rdx_gate_all_q40",
    "rdx_shuffled_gate_tail5_q40",
    "acid_gate_tail5_q40",
    "forward_gate_tail5_q40",
]

ARMS: tuple[E6Arm, ...] = (
    "b0",
    "acid_cont",
    "forward_cont",
    "rdx_cont",
    "rdx_gate_tail5_q20",
    "rdx_gate_tail5_q40",
    "rdx_gate_all_q40",
    "rdx_shuffled_gate_tail5_q40",
    "acid_gate_tail5_q40",
    "forward_gate_tail5_q40",
)

PRIMARY_ARM: E6Arm = "rdx_gate_tail5_q40"


def arm_spec(arm: E6Arm) -> dict[str, Any]:
    if arm == "b0":
        return {"score_arm": "b0", "integration": "continuous"}
    if arm == "acid_cont":
        return {"score_arm": "acid", "integration": "continuous"}
    if arm == "forward_cont":
        return {"score_arm": "forward", "integration": "continuous"}
    if arm == "rdx_cont":
        return {"score_arm": "rdx", "integration": "continuous"}
    if arm == "rdx_gate_tail5_q20":
        return {
            "score_arm": "rdx",
            "integration": "quantile_gate",
            "reject_fraction": 0.20,
            "active_tail_steps": 5,
            "shuffled": False,
        }
    if arm == "rdx_gate_tail5_q40":
        return {
            "score_arm": "rdx",
            "integration": "quantile_gate",
            "reject_fraction": 0.40,
            "active_tail_steps": 5,
            "shuffled": False,
        }
    if arm == "rdx_gate_all_q40":
        return {
            "score_arm": "rdx",
            "integration": "quantile_gate",
            "reject_fraction": 0.40,
            "active_tail_steps": CEM_STEPS,
            "shuffled": False,
        }
    if arm == "rdx_shuffled_gate_tail5_q40":
        return {
            "score_arm": "rdx",
            "integration": "quantile_gate",
            "reject_fraction": 0.40,
            "active_tail_steps": 5,
            "shuffled": True,
        }
    if arm == "acid_gate_tail5_q40":
        return {
            "score_arm": "acid",
            "integration": "quantile_gate",
            "reject_fraction": 0.40,
            "active_tail_steps": 5,
            "shuffled": False,
        }
    if arm == "forward_gate_tail5_q40":
        return {
            "score_arm": "forward",
            "integration": "quantile_gate",
            "reject_fraction": 0.40,
            "active_tail_steps": 5,
            "shuffled": False,
        }
    raise ValueError(f"unknown E6 arm: {arm}")


class E6CostModel(nn.Module):
    """Continuous E3 control or fixed within-population verifier veto."""

    def __init__(
        self,
        world_model: nn.Module,
        *,
        arm: E6Arm,
        task: str,
        planner_seed: int,
        scorer: nn.Module | None = None,
        payload: dict[str, Any] | None = None,
        horizon: int = 5,
        record_diagnostics: bool = True,
    ) -> None:
        super().__init__()
        if arm not in ARMS:
            raise ValueError(f"unknown E6 arm: {arm}")
        self.arm = arm
        self.spec = arm_spec(arm)
        self.base = d2.D2CostModel(
            world_model,
            arm=self.spec["score_arm"],
            task=task,
            planner_seed=planner_seed,
            scorer=scorer,
            payload=payload,
            horizon=horizon,
            record_diagnostics=(
                record_diagnostics and self.spec["integration"] == "continuous"
            ),
        )
        self.record_diagnostics = bool(record_diagnostics)
        self.diagnostic_history: list[dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        return self.base.call_count

    @property
    def lambda_weight(self) -> float:
        return self.base.lambda_weight

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        if self.spec["integration"] == "continuous":
            value = self.base.get_cost(info_dict, action_candidates)
            self.diagnostic_history = self.base.diagnostic_history
            return value

        goal, trajectory, actions, goal_embedding = self.base.rollout_model._rollout_once(
            info_dict, action_candidates
        )
        self.base.call_count += 1
        call = self.base.call_count
        iteration = (call - 1) % CEM_STEPS + 1
        tail_steps = int(self.spec["active_tail_steps"])
        active = iteration > CEM_STEPS - tail_steps

        if goal.ndim != 2 or goal.shape[1] != CEM_SAMPLES:
            raise RuntimeError(
                f"E6 requires one or more {CEM_SAMPLES}-candidate pools, got {goal.shape}"
            )
        if not torch.isfinite(goal).all():
            raise RuntimeError("E6 goal cost is non-finite")

        if not active:
            if self.record_diagnostics:
                self.diagnostic_history.append(
                    {
                        "call": call,
                        "iteration_in_solve": iteration,
                        "gate_active": False,
                        "feasible_count": CEM_SAMPLES,
                        "rejected_count": 0,
                        "goal_elite_rejected_count": 0,
                    }
                )
            return goal

        raw = self.base.raw_cost(trajectory, actions, goal_embedding)
        if raw.shape != goal.shape or not torch.isfinite(raw).all():
            raise RuntimeError("E6 verifier cost has an invalid shape or value")
        reject_fraction = float(self.spec["reject_fraction"])
        reject_count = int(round(CEM_SAMPLES * reject_fraction))
        keep_count = CEM_SAMPLES - reject_count
        if keep_count < CEM_TOPK or reject_count <= 0:
            raise RuntimeError("E6 gate would leave too few feasible candidates")

        # Stable sorting makes the tie policy deterministic: lower candidate
        # index wins exact verifier ties.
        order = torch.argsort(raw, dim=1, descending=False, stable=True)
        feasible = torch.zeros_like(raw, dtype=torch.bool)
        feasible.scatter_(1, order[:, :keep_count], True)
        if not torch.all(feasible.sum(dim=1) == keep_count):
            raise RuntimeError("E6 feasible-count invariant failed")

        goal_max = goal.max(dim=1).values
        goal_min = goal.min(dim=1).values
        goal_span = (goal_max - goal_min).abs().clamp_min(1.0)
        sentinel = goal_max + goal_span + 1.0
        combined = torch.where(feasible, goal, sentinel[:, None])
        if not torch.isfinite(combined).all():
            raise RuntimeError("E6 gated cost is non-finite")
        feasible_max = torch.where(feasible, combined, -torch.inf).max(dim=1).values
        rejected_min = torch.where(~feasible, combined, torch.inf).min(dim=1).values
        if not torch.all(rejected_min > feasible_max):
            raise RuntimeError("E6 rejected candidates can enter the elite set")

        goal_elites = torch.topk(
            goal, k=CEM_TOPK, dim=1, largest=False, sorted=False
        ).indices
        vetoed_elites = (~feasible.gather(1, goal_elites)).sum(dim=1)
        threshold = raw.gather(1, order[:, keep_count - 1 : keep_count]).squeeze(1)
        if self.record_diagnostics:
            self.diagnostic_history.append(
                {
                    "call": call,
                    "iteration_in_solve": iteration,
                    "gate_active": True,
                    "reject_fraction": reject_fraction,
                    "feasible_count": feasible.sum(dim=1).cpu().tolist(),
                    "rejected_count": (~feasible).sum(dim=1).cpu().tolist(),
                    "goal_elite_rejected_count": vetoed_elites.cpu().tolist(),
                    "verifier_threshold": threshold.cpu().tolist(),
                    "verifier_min": raw.min(dim=1).values.cpu().tolist(),
                    "verifier_max": raw.max(dim=1).values.cpu().tolist(),
                    "goal_min": goal_min.cpu().tolist(),
                    "goal_max": goal_max.cpu().tolist(),
                    "sentinel": sentinel.cpu().tolist(),
                }
            )
        return combined


def self_test() -> None:
    if len(ARMS) != len(set(ARMS)) or PRIMARY_ARM not in ARMS:
        raise RuntimeError("E6 arm registry is invalid")
    expected = {
        "rdx_gate_tail5_q20": (0.20, 5),
        "rdx_gate_tail5_q40": (0.40, 5),
        "rdx_gate_all_q40": (0.40, 30),
        "rdx_shuffled_gate_tail5_q40": (0.40, 5),
        "acid_gate_tail5_q40": (0.40, 5),
        "forward_gate_tail5_q40": (0.40, 5),
    }
    for arm, (fraction, steps) in expected.items():
        spec = arm_spec(arm)  # type: ignore[arg-type]
        if spec["reject_fraction"] != fraction or spec["active_tail_steps"] != steps:
            raise RuntimeError(f"E6 arm specification changed: {arm}")


if __name__ == "__main__":
    self_test()
