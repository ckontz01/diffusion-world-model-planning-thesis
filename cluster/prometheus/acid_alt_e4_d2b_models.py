"""Frozen E4-D2B closed-loop cost integration.

Every arm reuses one Le-WM rollout per CEM cost call.  The module contains no
outcome-dependent choices; arm names and weights are frozen in the D2B design.
"""

from __future__ import annotations

import time
from typing import Any

import torch
from torch import nn

import acid_alt_d2_models as d2
from acid_alt_e4_controls import (
    ConditionalGaussianInverse,
    DeterministicInverseRegressor,
    deterministic_inverse_costs,
    gaussian_inverse_costs,
)
from acid_alt_e4_models import ConditionalActionDenoiser
from acid_alt_e4_scoring import (
    acid_flow_training_energy,
    acid_multisample_costs,
    build_acid_sample_noise_bank,
    build_action_noise_bank,
    inverse_diffusion_costs,
)
from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.models import FlowInverseDynamics, TemporalReachabilityHead


ARMS = (
    "b0",
    "acid_l002",
    "acid",
    "acid_l014",
    "acid_flow",
    "acid_16_mean",
    "acid_16_min",
    "forward",
    "reachability",
    "deterministic_inverse",
    "gaussian_tail",
    "cider_tail_l002",
    "cider_tail",
    "cider_tail_l014",
    "cider_shuffled",
    "dide",
    "cider_raw",
    "cider_mean_violation",
)
E4_ARMS = {
    "cider_tail_l002",
    "cider_tail",
    "cider_tail_l014",
    "cider_shuffled",
    "dide",
    "cider_raw",
    "cider_mean_violation",
}
ACID_SAMPLE_ARMS = {"acid_16_mean", "acid_16_min"}
ACID_ONE_SAMPLE_ARMS = {"acid_l002", "acid", "acid_l014"}
SPREAD_EPSILON = 1.0e-8
HORIZON = 5
ACID_SAMPLE_DRAWS = 16


def arm_lambda(arm: str) -> float:
    if arm in {"acid_l002", "cider_tail_l002"}:
        return 0.02
    if arm in {"acid_l014", "cider_tail_l014"}:
        return 0.14
    if arm in ARMS:
        return 0.07
    raise ValueError(f"unknown E4-D2B arm: {arm}")


def expected_artifact_family(arm: str) -> str:
    if arm == "b0":
        return "none"
    if arm in ACID_ONE_SAMPLE_ARMS | ACID_SAMPLE_ARMS | {"acid_flow"}:
        return "acid"
    if arm in {"forward", "reachability"}:
        return arm
    if arm == "deterministic_inverse":
        return "deterministic"
    if arm == "gaussian_tail":
        return "gaussian"
    if arm == "cider_shuffled":
        return "e4_shuffled"
    if arm in E4_ARMS:
        return "e4_true"
    raise ValueError(f"unknown E4-D2B arm: {arm}")


class E4D2BCostModel(nn.Module):
    """One-rollout, null-safe cost wrapper for every frozen E4-D2B arm."""

    def __init__(
        self,
        world_model: nn.Module,
        *,
        arm: str,
        task: str,
        planner_seed: int,
        scorer: nn.Module | None = None,
        payload: dict[str, Any] | None = None,
        calibration: dict[str, Any] | None = None,
        horizon: int = HORIZON,
        record_diagnostics: bool = True,
    ) -> None:
        super().__init__()
        if arm not in ARMS:
            raise ValueError(f"unknown E4-D2B arm: {arm}")
        family = expected_artifact_family(arm)
        if family == "none":
            if scorer is not None or payload is not None or calibration is not None:
                raise ValueError("B0 cannot receive a scorer artifact")
        elif scorer is None or payload is None:
            raise ValueError(f"{arm} requires a scorer and payload")
        if arm in E4_ARMS | {"gaussian_tail"} and calibration is None:
            raise ValueError(f"{arm} requires calibration")

        self.rollout_model = SharedRolloutCostModel(
            world_model, arm="b0", horizon=horizon, record_diagnostics=False
        )
        self.arm = arm
        self.task = task
        self.planner_seed = int(planner_seed)
        self.scorer = scorer
        self.payload = payload or {}
        self.calibration = calibration
        self.horizon = int(horizon)
        self.lambda_weight = arm_lambda(arm)
        self.record_diagnostics = bool(record_diagnostics)
        self.call_count = 0
        self.diagnostic_history: list[dict[str, Any]] = []

        self.register_buffer("action_noise_bank", torch.empty(0), persistent=True)
        self.register_buffer("acid_sample_noise_bank", torch.empty(0), persistent=True)
        if arm in E4_ARMS | {"acid_flow"}:
            action_dim = int(self.payload["model_config"]["action_dim"])
            seed = int(self.payload["seed"])
            self.action_noise_bank = build_action_noise_bank(
                task=task,
                scorer_seed=seed,
                horizon=self.horizon,
                action_dim=action_dim,
            )
        if arm in ACID_SAMPLE_ARMS:
            action_dim = int(self.payload["model_config"]["action_dim"])
            seed = int(self.payload["seed"])
            self.acid_sample_noise_bank = build_acid_sample_noise_bank(
                task=task,
                scorer_seed=seed,
                horizon=self.horizon,
                action_dim=action_dim,
                draws=ACID_SAMPLE_DRAWS,
            )

    def begin_plan(self) -> None:
        self.call_count = 0

    def _record(self, value: dict[str, Any]) -> None:
        if self.record_diagnostics:
            self.diagnostic_history.append(value)

    @torch.inference_mode()
    def raw_cost(
        self,
        trajectory: torch.Tensor,
        actions: torch.Tensor,
        goal_embedding: torch.Tensor,
    ) -> torch.Tensor:
        if self.arm in ACID_ONE_SAMPLE_ARMS:
            if not isinstance(self.scorer, FlowInverseDynamics):
                raise TypeError("published ACID arm requires FlowInverseDynamics")
            generator = torch.Generator(device="cpu").manual_seed(
                d2.acid_noise_seed(
                    self.task,
                    int(self.payload["seed"]),
                    self.planner_seed,
                    self.call_count,
                )
            )
            return d2.acid_literal_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                action_mean=self.payload["acid_action_mean"],
                action_std=self.payload["acid_action_std"],
                generator=generator,
            )
        if self.arm == "acid_flow":
            if not isinstance(self.scorer, FlowInverseDynamics):
                raise TypeError("ACID flow arm requires FlowInverseDynamics")
            return acid_flow_training_energy(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                action_mean=self.payload["acid_action_mean"],
                action_std=self.payload["acid_action_std"],
                noise_bank=self.action_noise_bank,
            )
        if self.arm in ACID_SAMPLE_ARMS:
            if not isinstance(self.scorer, FlowInverseDynamics):
                raise TypeError("ACID multisample arm requires FlowInverseDynamics")
            values = acid_multisample_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                action_mean=self.payload["acid_action_mean"],
                action_std=self.payload["acid_action_std"],
                noise_bank=self.acid_sample_noise_bank,
            )
            key = (
                "acid_sample_mean"
                if self.arm == "acid_16_mean"
                else "acid_sample_min"
            )
            return values[key]
        if self.arm == "forward":
            if self.scorer is None:
                raise RuntimeError("forward scorer is absent")
            return d2.forward_literal_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                latent_mean=self.payload["latent_mean"],
                latent_std=self.payload["latent_std"],
            )
        if self.arm == "reachability":
            if not isinstance(self.scorer, TemporalReachabilityHead):
                raise TypeError("reachability arm requires TemporalReachabilityHead")
            return d2.reachability_literal_costs(
                self.scorer,
                trajectory=trajectory,
                goal_embedding=goal_embedding,
            )
        if self.arm == "deterministic_inverse":
            if not isinstance(self.scorer, DeterministicInverseRegressor):
                raise TypeError("deterministic inverse scorer type differs")
            return deterministic_inverse_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                latent_mean=self.payload["latent_mean"],
                latent_std=self.payload["latent_std"],
                action_mean=self.payload["acid_action_mean"],
                action_std=self.payload["acid_action_std"],
            )
        if self.arm == "gaussian_tail":
            if not isinstance(self.scorer, ConditionalGaussianInverse):
                raise TypeError("Gaussian inverse scorer type differs")
            assert self.calibration is not None
            return gaussian_inverse_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                latent_mean=self.payload["latent_mean"],
                latent_std=self.payload["latent_std"],
                action_mean=self.payload["acid_action_mean"],
                action_std=self.payload["acid_action_std"],
                calibration=self.calibration,
            )["gaussian_tail"]
        if self.arm in E4_ARMS:
            if not isinstance(self.scorer, ConditionalActionDenoiser):
                raise TypeError("E4 arm requires ConditionalActionDenoiser")
            assert self.calibration is not None
            values = inverse_diffusion_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                payload=self.payload,
                calibration=self.calibration,
                noise_bank=self.action_noise_bank,
            )
            key = {
                "cider_tail_l002": "cider_tail",
                "cider_tail": "cider_tail",
                "cider_tail_l014": "cider_tail",
                "cider_shuffled": "cider_tail",
                "dide": "dide",
                "cider_raw": "cider",
                "cider_mean_violation": "cider_mean_violation",
            }[self.arm]
            return values[key]
        raise RuntimeError(f"raw cost unavailable for {self.arm}")

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        rollout_started = time.perf_counter()
        goal_cost, trajectory, actions, goal_embedding = self.rollout_model._rollout_once(
            info_dict, action_candidates
        )
        rollout_seconds = time.perf_counter() - rollout_started
        self.call_count += 1

        if self.arm in {"b0", "cider_shuffled"}:
            self._record(
                {
                    "call": self.call_count,
                    "reliability": 0 if self.arm == "cider_shuffled" else None,
                    "rollout_seconds": rollout_seconds,
                    "verifier_seconds": 0.0,
                    "goal_std": goal_cost.std(dim=1, unbiased=True).cpu().tolist(),
                    "active_weight": [False] * goal_cost.shape[0],
                }
            )
            return goal_cost

        verifier_started = time.perf_counter()
        raw = self.raw_cost(trajectory, actions, goal_embedding)
        verifier_seconds = time.perf_counter() - verifier_started
        if raw.shape != goal_cost.shape or not torch.isfinite(raw).all():
            raise RuntimeError("E4-D2B verifier returned invalid costs")
        goal_spread = goal_cost.std(dim=1, unbiased=True)
        verifier_spread = raw.std(dim=1, unbiased=True)
        active = verifier_spread > SPREAD_EPSILON
        weight = self.lambda_weight * goal_spread / verifier_spread.clamp_min(
            SPREAD_EPSILON
        )
        weight = torch.where(active, weight, torch.zeros_like(weight))
        combined = goal_cost + weight[:, None] * raw
        if not torch.isfinite(combined).all():
            raise RuntimeError("E4-D2B combined cost is non-finite")
        self._record(
            {
                "call": self.call_count,
                "reliability": 1,
                "rollout_seconds": rollout_seconds,
                "verifier_seconds": verifier_seconds,
                "goal_std": goal_spread.cpu().tolist(),
                "verifier_std": verifier_spread.cpu().tolist(),
                "adaptive_weight": weight.cpu().tolist(),
                "active_weight": active.cpu().tolist(),
                "verifier_min": raw.min(dim=1).values.cpu().tolist(),
                "verifier_max": raw.max(dim=1).values.cpu().tolist(),
            }
        )
        return combined


__all__ = [
    "ACID_SAMPLE_DRAWS",
    "ARMS",
    "E4D2BCostModel",
    "E4_ARMS",
    "HORIZON",
    "SPREAD_EPSILON",
    "arm_lambda",
    "expected_artifact_family",
]

