"""Frozen E15 scheduled planners with matched synchronized timing."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import stable_worldmodel as swm
import torch

import gdp_cem_e15_specs as spec
from gdp_cem_e14_closed_loop import (
    E14Statistics,
    ScheduledE14Planner,
    ScheduledE14Policy,
    generator_state_sha256,
)
from gdp_cem_e14_models import (
    SAGEOptionPrior,
    SAGESubgoalGenerator,
    sample_trajectory_gmm,
)
from gdp_cem_e15_models import (
    CosineSchedule,
    DirectTrajectoryGMM,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    action_active_mask,
    bounded_actions_from_standardized_u,
    sample_direct_gmm_with_modes,
    velocity_ddim_sample,
)
from gdp_cem_latent_rollout import rollout_from_single_latent


Arm = Literal[
    "base_cem",
    "sage_reconstruction",
    "sage_one_stage",
    "vad",
    "direct_gmm",
    "diagonal_gaussian",
]


CudaInterval = tuple[torch.cuda.Event, torch.cuda.Event]


def cuda_interval(function: Any) -> tuple[Any, CudaInterval]:
    """Record one component without inserting an inner synchronization barrier."""

    started = torch.cuda.Event(enable_timing=True)
    finished = torch.cuda.Event(enable_timing=True)
    started.record()
    result = function()
    finished.record()
    return result, (started, finished)


def cuda_interval_seconds(intervals: list[CudaInterval]) -> float:
    """Resolve intervals only after the enclosing planner call is synchronized."""

    return sum(float(started.elapsed_time(finished)) for started, finished in intervals) / 1_000.0


class InstrumentedE14Planner(ScheduledE14Planner):
    """Run unchanged Base/SAGE algorithms while separating synchronized time."""

    def __init__(self, *args: Any, reported_arm: Arm, one_stage: bool = False, **kwargs: Any):
        if reported_arm not in ("base_cem", "sage_reconstruction", "sage_one_stage"):
            raise ValueError("invalid E15 instrumented E14 arm")
        internal_arm = "base_cem" if reported_arm == "base_cem" else "sage_reconstruction"
        super().__init__(*args, arm=internal_arm, **kwargs)
        self.reported_arm = reported_arm
        self.one_stage = bool(one_stage)
        if self.one_stage != (reported_arm == "sage_one_stage"):
            raise ValueError("E15 one-stage arm assignment differs")
        if self.one_stage and self.cem_rounds != 1:
            raise ValueError("E15 SAGE one-stage must use one population")
        self._encoding_intervals: list[CudaInterval] = []
        self._lewm_intervals: list[CudaInterval] = []

    @torch.inference_mode()
    def _encode(self, info_dict: dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor]:
        result, interval = cuda_interval(
            lambda: super(InstrumentedE14Planner, self)._encode(info_dict)
        )
        self._encoding_intervals.append(interval)
        return result

    @torch.inference_mode()
    def _terminal_and_cost(
        self,
        current_raw: torch.Tensor,
        candidates: torch.Tensor,
        target: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        result, interval = cuda_interval(
            lambda: super(InstrumentedE14Planner, self)._terminal_and_cost(
                current_raw, candidates, target
            )
        )
        self._lewm_intervals.append(interval)
        return result

    @torch.inference_mode()
    def _sage_cem(
        self,
        current_raw: torch.Tensor,
        goal_raw: torch.Tensor,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau_tensor: torch.Tensor,
        *,
        tau: int,
    ) -> tuple[torch.Tensor, int, dict[str, float]]:
        if not self.one_stage:
            return super()._sage_cem(
                current_raw,
                goal_raw,
                current,
                goal,
                state,
                delta,
                tau_tensor,
                tau=tau,
            )
        assert self.sage_subgoal is not None and self.sage_option is not None
        generated_local_normalized = self.sage_subgoal(
            current, goal, state, delta, tau_tensor
        )
        generated_local_raw = (
            generated_local_normalized * self.statistics.latent_std
            + self.statistics.latent_mean
        )
        logits, means, log_stds = self.sage_option(
            current,
            goal,
            generated_local_normalized,
            state,
            delta,
            tau_tensor,
        )
        normalized = sample_trajectory_gmm(
            logits,
            means,
            log_stds,
            count=self.candidate_count,
            active_mask=(
                torch.arange(spec.ACTION_HORIZON, device=self.device)[None]
                < tau_tensor[:, None]
            ),
            generator=self.gmm_generator,
        )[:, :, :tau]
        low = (
            self.statistics.action_robust_low - self.statistics.action_mean
        ) / self.statistics.action_std
        high = (
            self.statistics.action_robust_high - self.statistics.action_mean
        ) / self.statistics.action_std
        normalized = torch.maximum(torch.minimum(normalized, high), low)
        actions = normalized * self.statistics.action_std + self.statistics.action_mean
        candidates = actions.reshape(
            len(actions),
            self.candidate_count,
            tau // spec.ACTION_BLOCK,
            spec.ACTION_BLOCK * self.primitive_action_dim,
        )
        _, cost = self._terminal_and_cost(
            current_raw, candidates, generated_local_raw
        )
        best = cost.argmin(dim=1)
        selected = candidates[torch.arange(len(actions), device=self.device), best]
        rounded = torch.round(normalized * 1.0e4).to(torch.int64)
        unique = [torch.unique(row.flatten(1), dim=0).shape[0] for row in rounded]
        boundary = torch.logical_or(
            actions == self.statistics.action_robust_low,
            actions == self.statistics.action_robust_high,
        ).float().mean()
        return selected, 1, {
            "minimum_initial_unique_candidates": float(min(unique)),
            "initial_boundary_fraction": float(boundary.cpu()),
        }

    @torch.inference_mode()
    def solve(
        self,
        info_dict: dict[str, Any],
        *,
        raw_state: torch.Tensor,
        delta_value: int,
        tau_value: int,
    ) -> dict[str, Any]:
        self._encoding_intervals = []
        self._lewm_intervals = []
        torch.cuda.synchronize()
        started = time.perf_counter()
        result = super().solve(
            info_dict,
            raw_state=raw_state,
            delta_value=delta_value,
            tau_value=tau_value,
        )
        torch.cuda.synchronize()
        total = time.perf_counter() - started
        encoding_seconds = cuda_interval_seconds(self._encoding_intervals)
        lewm_seconds = cuda_interval_seconds(self._lewm_intervals)
        other = max(0.0, total - encoding_seconds - lewm_seconds)
        diagnostic = self.diagnostic_history[-1]
        diagnostic.update(
            {
                "arm": self.reported_arm,
                "planner_seconds": total,
                "end_to_end_stage_seconds": total,
                "encoding_seconds": encoding_seconds,
                "proposal_and_selection_seconds": other,
                "lewm_scoring_seconds": lewm_seconds,
                "timing_decomposition_residual_seconds": total
                - encoding_seconds
                - other
                - lewm_seconds,
                "component_timing_method": (
                    "cuda_events_resolved_after_outer_stage_synchronize"
                ),
            }
        )
        result["solver_seconds"] = total
        return result


@dataclass(frozen=True)
class E15Statistics:
    latent_mean: torch.Tensor
    latent_std: torch.Tensor
    state_mean: torch.Tensor
    state_std: torch.Tensor
    u_mean: torch.Tensor
    u_std: torch.Tensor
    planner_action_mean: torch.Tensor
    planner_action_std: torch.Tensor
    interior_scale: float
    target_raw_limit: float

    def to(self, device: torch.device) -> "E15Statistics":
        return E15Statistics(
            latent_mean=self.latent_mean.to(device=device, dtype=torch.float32),
            latent_std=self.latent_std.to(device=device, dtype=torch.float32),
            state_mean=self.state_mean.to(device=device, dtype=torch.float32),
            state_std=self.state_std.to(device=device, dtype=torch.float32),
            u_mean=self.u_mean.to(device=device, dtype=torch.float32),
            u_std=self.u_std.to(device=device, dtype=torch.float32),
            planner_action_mean=self.planner_action_mean.to(
                device=device, dtype=torch.float32
            ),
            planner_action_std=self.planner_action_std.to(
                device=device, dtype=torch.float32
            ),
            interior_scale=float(self.interior_scale),
            target_raw_limit=float(self.target_raw_limit),
        )

    def validate(self, *, state_dim: int, primitive_action_dim: int) -> None:
        expected = {
            "latent_mean": (spec.LATENT_DIM,),
            "latent_std": (spec.LATENT_DIM,),
            "state_mean": (state_dim,),
            "state_std": (state_dim,),
            "u_mean": (primitive_action_dim,),
            "u_std": (primitive_action_dim,),
            "planner_action_mean": (primitive_action_dim,),
            "planner_action_std": (primitive_action_dim,),
        }
        if any(
            getattr(self, name).shape != shape
            or not torch.isfinite(getattr(self, name)).all()
            for name, shape in expected.items()
        ):
            raise ValueError("invalid E15 online statistic shape")
        if (
            torch.any(self.latent_std <= 1.0e-6)
            or torch.any(self.state_std <= 1.0e-8)
            or torch.any(self.u_std <= 1.0e-6)
            or torch.any(self.planner_action_std <= 1.0e-8)
            or not 0.0 < self.target_raw_limit < self.interior_scale < 1.0
        ):
            raise ValueError("invalid E15 online statistic range")


class E15OnePassPlanner:
    """One-pass VAD, direct-GMM, or diagonal-Gaussian far-goal planner."""

    def __init__(
        self,
        world_model: torch.nn.Module,
        *,
        arm: Literal["vad", "direct_gmm", "diagonal_gaussian"],
        statistics: E15Statistics,
        state_dim: int,
        primitive_action_dim: int,
        proposer: VariableVelocityDiffusion | DirectTrajectoryGMM | VariableDiagonalGaussian,
        candidate_count: int,
        batch_size: int,
        proposal_seed: int,
    ) -> None:
        expected_type = {
            "vad": VariableVelocityDiffusion,
            "direct_gmm": DirectTrajectoryGMM,
            "diagonal_gaussian": VariableDiagonalGaussian,
        }[arm]
        if (
            not isinstance(proposer, expected_type)
            or candidate_count != spec.CANDIDATE_COUNT
            or batch_size <= 0
        ):
            raise ValueError("invalid E15 one-pass planner configuration")
        self.world_model = world_model
        self.arm = arm
        self.statistics = statistics
        self.state_dim = int(state_dim)
        self.primitive_action_dim = int(primitive_action_dim)
        self.proposer = proposer
        self.candidate_count = int(candidate_count)
        self.batch_size = int(batch_size)
        self.device = next(world_model.parameters()).device
        self.statistics.validate(
            state_dim=self.state_dim, primitive_action_dim=self.primitive_action_dim
        )
        self.statistics = self.statistics.to(self.device)
        self.proposal_generator = torch.Generator(device=self.device).manual_seed(
            int(proposal_seed)
        )
        self.gmm_generator = torch.Generator(device="cpu").manual_seed(
            int(proposal_seed)
        )
        self.schedule = CosineSchedule.build(spec.DIFFUSION_STEPS)
        self.diagnostic_history: list[dict[str, Any]] = []
        self._configured = False

    def configure(self, *, action_space: Any, n_envs: int) -> None:
        self._n_envs = int(n_envs)
        self._action_dim = int(np.prod(action_space.shape[1:]))
        if self._action_dim != self.primitive_action_dim:
            raise RuntimeError("E15 environment action dimension differs")
        self._configured = True

    @torch.inference_mode()
    def _encode(self, info_dict: dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor]:
        work = {
            key: value.to(self.device) if torch.is_tensor(value) else value
            for key, value in info_dict.items()
        }
        current = {key: value for key, value in work.items() if torch.is_tensor(value)}
        current.pop("action", None)
        goal = {key: value for key, value in work.items() if torch.is_tensor(value)}
        if "goal" not in goal:
            raise KeyError("goal not in E15 planner info")
        goal["pixels"] = goal["goal"]
        for key in list(goal):
            if key.startswith("goal_"):
                goal[key.removeprefix("goal_")] = goal.pop(key)
        goal.pop("action", None)
        current_embedding = self.world_model.encode(current)["emb"][:, -1]
        goal_embedding = self.world_model.encode(goal)["emb"][:, -1]
        if (
            current_embedding.shape != goal_embedding.shape
            or current_embedding.shape != (len(current_embedding), spec.LATENT_DIM)
            or not torch.isfinite(current_embedding).all()
            or not torch.isfinite(goal_embedding).all()
        ):
            raise RuntimeError("E15 online latent encoding differs")
        return current_embedding, goal_embedding

    def _condition(
        self,
        current_raw: torch.Tensor,
        goal_raw: torch.Tensor,
        raw_state: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        current = (current_raw - self.statistics.latent_mean) / self.statistics.latent_std
        goal = (goal_raw - self.statistics.latent_mean) / self.statistics.latent_std
        state = (raw_state - self.statistics.state_mean) / self.statistics.state_std
        if (
            state.shape != (len(current), self.state_dim)
            or not torch.isfinite(current).all()
            or not torch.isfinite(goal).all()
            or not torch.isfinite(state).all()
        ):
            raise RuntimeError("E15 online normalized condition differs")
        return current, goal, state

    @torch.inference_mode()
    def _propose(
        self,
        *,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        active = action_active_mask(
            tau, primitive_action_dim=self.primitive_action_dim
        )
        flat_mask = active.reshape(len(tau), -1)
        if self.arm == "vad":
            assert isinstance(self.proposer, VariableVelocityDiffusion)
            noise = torch.randn(
                len(tau),
                self.candidate_count,
                flat_mask.shape[1],
                device=self.device,
                generator=self.proposal_generator,
            ) * flat_mask[:, None]
            standardized = velocity_ddim_sample(
                self.proposer,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau,
                initial_noise=noise,
                active_mask=flat_mask,
                schedule=self.schedule,
                evaluations=spec.DIFFUSION_EVALUATIONS,
                guidance_scale=spec.GUIDANCE_SCALE,
            ).reshape(
                len(tau),
                self.candidate_count,
                spec.ACTION_HORIZON,
                self.primitive_action_dim,
            )
        elif self.arm == "diagonal_gaussian":
            assert isinstance(self.proposer, VariableDiagonalGaussian)
            mean, log_std = self.proposer(current, goal, state, delta, tau)
            noise = torch.randn(
                len(tau),
                self.candidate_count,
                mean.shape[1],
                device=self.device,
                generator=self.proposal_generator,
            )
            standardized = (
                mean[:, None] + log_std.exp()[:, None] * noise
            ) * flat_mask[:, None]
            standardized = standardized.reshape(
                len(tau),
                self.candidate_count,
                spec.ACTION_HORIZON,
                self.primitive_action_dim,
            )
        else:
            assert isinstance(self.proposer, DirectTrajectoryGMM)
            logits, means, log_stds = self.proposer(current, goal, state, delta, tau)
            standardized, _ = sample_direct_gmm_with_modes(
                logits,
                means,
                log_stds,
                count=self.candidate_count,
                active_mask=active[:, :, 0],
                generator=self.gmm_generator,
            )
        return bounded_actions_from_standardized_u(
            standardized,
            u_mean=self.statistics.u_mean,
            u_std=self.statistics.u_std,
            planner_mean=self.statistics.planner_action_mean,
            planner_std=self.statistics.planner_action_std,
            interior_scale=self.statistics.interior_scale,
            active_mask=active,
        )

    @torch.inference_mode()
    def solve(
        self,
        info_dict: dict[str, Any],
        *,
        raw_state: torch.Tensor,
        delta_value: int,
        tau_value: int,
    ) -> dict[str, Any]:
        if not self._configured:
            raise RuntimeError("E15 one-pass planner is not configured")
        if tau_value not in spec.TAU_VALUES or delta_value < tau_value:
            raise ValueError("E15 online delta/tau differs")
        torch.cuda.synchronize()
        total_started = time.perf_counter()
        (current_raw, goal_raw), encoding_interval = cuda_interval(
            lambda: self._encode(info_dict)
        )
        raw_state = raw_state.to(self.device, dtype=torch.float32)
        current, goal, state = self._condition(current_raw, goal_raw, raw_state)
        delta = torch.full(
            (len(current),), delta_value, device=self.device, dtype=torch.long
        )
        tau = torch.full(
            (len(current),), tau_value, device=self.device, dtype=torch.long
        )
        output = torch.empty(
            len(current),
            tau_value // spec.ACTION_BLOCK,
            spec.ACTION_BLOCK * self.primitive_action_dim,
        )
        proposal_before = generator_state_sha256(self.proposal_generator)
        gmm_before = generator_state_sha256(self.gmm_generator)
        proposal_intervals: list[CudaInterval] = []
        lewm_intervals: list[CudaInterval] = []
        minimum_unique = self.candidate_count
        maximum_near = 0.0
        maximum_jacobian = 0.0
        for start in range(0, len(current), self.batch_size):
            stop = min(start + self.batch_size, len(current))
            (raw, planner, jacobian), interval = cuda_interval(
                lambda: self._propose(
                    current=current[start:stop],
                    goal=goal[start:stop],
                    state=state[start:stop],
                    delta=delta[start:stop],
                    tau=tau[start:stop],
                )
            )
            proposal_intervals.append(interval)
            raw_active = raw[:, :, :tau_value]
            planner_active = planner[:, :, :tau_value]
            macro = planner_active.reshape(
                stop - start,
                self.candidate_count,
                tau_value // spec.ACTION_BLOCK,
                spec.ACTION_BLOCK * self.primitive_action_dim,
            )
            (terminal, cost), interval = cuda_interval(
                lambda: self._terminal_and_cost(
                    current_raw[start:stop], macro, goal_raw[start:stop]
                )
            )
            del terminal
            lewm_intervals.append(interval)
            best = cost.argmin(dim=1)
            selected = macro[
                torch.arange(stop - start, device=self.device), best
            ]
            output[start:stop] = selected.cpu()
            rounded = torch.round(raw_active * 1.0e4).to(torch.int64)
            minimum_unique = min(
                minimum_unique,
                *(torch.unique(row.flatten(1), dim=0).shape[0] for row in rounded),
            )
            maximum_near = max(
                maximum_near,
                float(
                    (
                        ((1.0 - raw_active.abs()) / 2.0)
                        <= spec.BOUNDARY_GATE_MARGIN
                    )
                    .float()
                    .mean()
                    .cpu()
                ),
            )
            maximum_jacobian = max(
                maximum_jacobian,
                float(
                    (jacobian[:, :, :tau_value] < spec.JACOBIAN_GATE_THRESHOLD)
                    .float()
                    .mean()
                    .cpu()
                ),
            )
        torch.cuda.synchronize()
        total = time.perf_counter() - total_started
        encoding_seconds = cuda_interval_seconds([encoding_interval])
        proposal_seconds = cuda_interval_seconds(proposal_intervals)
        lewm_seconds = cuda_interval_seconds(lewm_intervals)
        other = max(0.0, total - encoding_seconds - proposal_seconds - lewm_seconds)
        diagnostics = {
            "call": len(self.diagnostic_history),
            "arm": self.arm,
            "delta": delta_value,
            "tau": tau_value,
            "candidate_count": self.candidate_count,
            "cem_rounds": 1,
            "lewm_population_calls": len(current),
            "planner_seconds": total,
            "end_to_end_stage_seconds": total,
            "encoding_seconds": encoding_seconds,
            "proposal_and_selection_seconds": proposal_seconds + other,
            "lewm_scoring_seconds": lewm_seconds,
            "timing_decomposition_residual_seconds": total
            - encoding_seconds
            - (proposal_seconds + other)
            - lewm_seconds,
            "component_timing_method": (
                "cuda_events_resolved_after_outer_stage_synchronize"
            ),
            "proposal_generator_before_sha256": proposal_before,
            "proposal_generator_after_sha256": generator_state_sha256(
                self.proposal_generator
            ),
            "gmm_generator_before_sha256": gmm_before,
            "gmm_generator_after_sha256": generator_state_sha256(
                self.gmm_generator
            ),
            "minimum_unique_candidates": minimum_unique,
            "maximum_near_1e_2_fraction": maximum_near,
            "maximum_jacobian_below_1e_3_fraction": maximum_jacobian,
            "strict_legal_oob_fraction": 0.0,
            "exact_legal_boundary_fraction": 0.0,
        }
        self.diagnostic_history.append(diagnostics)
        return {"actions": output, "solver_seconds": total}

    @torch.inference_mode()
    def _terminal_and_cost(
        self,
        current_raw: torch.Tensor,
        candidates: torch.Tensor,
        target: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        trajectory = rollout_from_single_latent(
            self.world_model, current=current_raw, macro_actions=candidates
        )
        terminal = trajectory[:, :, -1]
        return terminal, (terminal - target[:, None]).square().sum(dim=-1)


__all__ = [
    "Arm",
    "E14Statistics",
    "E15OnePassPlanner",
    "E15Statistics",
    "InstrumentedE14Planner",
    "ScheduledE14Policy",
]
