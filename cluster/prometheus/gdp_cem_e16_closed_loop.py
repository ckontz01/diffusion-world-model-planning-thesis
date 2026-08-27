"""Frozen E16 greedy and continuation-aware direct far-goal planners."""

from __future__ import annotations

import time
from typing import Any, Literal

import numpy as np
import torch

import gdp_cem_e15_specs as e15
import gdp_cem_e16_specs as spec
from gdp_cem_e14_closed_loop import generator_state_sha256
from gdp_cem_e15_closed_loop import E15Statistics, cuda_interval, cuda_interval_seconds
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
from gdp_cem_e16_models import LatentStateAdapter, continuation_score
from gdp_cem_latent_rollout import rollout_from_single_latent


E16DirectArm = Literal[
    "vad_greedy_300",
    "vad_greedy_576",
    "vad_continuation",
    "diagonal_gaussian_continuation",
    "direct_gmm_continuation",
]


def family_for_arm(arm: E16DirectArm) -> str:
    if arm.startswith("vad_"):
        return "vad"
    if arm == "diagonal_gaussian_continuation":
        return "diagonal_gaussian"
    if arm == "direct_gmm_continuation":
        return "direct_gmm"
    raise ValueError("invalid E16 direct arm")


def is_continuation_arm(arm: E16DirectArm) -> bool:
    return arm.endswith("_continuation")


def candidate_count_for_arm(arm: E16DirectArm) -> int:
    if arm == "vad_greedy_300":
        return spec.GREEDY_CANDIDATES
    if arm == "vad_greedy_576":
        return spec.GREEDY_COMPUTE_MATCHED_CANDIDATES
    if is_continuation_arm(arm):
        return spec.CONTINUATION_FIRST_CANDIDATES
    raise ValueError("invalid E16 direct arm")


class E16DirectPlanner:
    """Direct far-goal proposer with a fixed greedy or two-stage selector."""

    def __init__(
        self,
        world_model: torch.nn.Module,
        *,
        arm: E16DirectArm,
        statistics: E15Statistics,
        state_dim: int,
        primitive_action_dim: int,
        proposer: VariableVelocityDiffusion
        | VariableDiagonalGaussian
        | DirectTrajectoryGMM,
        state_adapter: LatentStateAdapter,
        batch_size: int,
        proposal_seed: int,
    ) -> None:
        family = family_for_arm(arm)
        expected = {
            "vad": VariableVelocityDiffusion,
            "diagonal_gaussian": VariableDiagonalGaussian,
            "direct_gmm": DirectTrajectoryGMM,
        }[family]
        if not isinstance(proposer, expected) or batch_size <= 0:
            raise ValueError("invalid E16 direct planner configuration")
        if (
            state_adapter.latent_dim != spec.LATENT_DIM
            or state_adapter.state_dim != state_dim
        ):
            raise ValueError("E16 state-adapter dimension differs")
        self.world_model = world_model
        self.arm = arm
        self.family = family
        self.statistics = statistics
        self.state_dim = int(state_dim)
        self.primitive_action_dim = int(primitive_action_dim)
        self.proposer = proposer
        self.state_adapter = state_adapter
        self.batch_size = int(batch_size)
        self.device = next(world_model.parameters()).device
        self.statistics.validate(
            state_dim=self.state_dim, primitive_action_dim=self.primitive_action_dim
        )
        self.statistics = self.statistics.to(self.device)
        self.proposer = self.proposer.to(self.device).eval().requires_grad_(False)
        self.state_adapter = (
            self.state_adapter.to(self.device).eval().requires_grad_(False)
        )
        self.proposal_generator = torch.Generator(device=self.device).manual_seed(
            int(proposal_seed)
        )
        self.gmm_generator = torch.Generator(device="cpu").manual_seed(
            int(proposal_seed)
        )
        self.schedule = CosineSchedule.build(e15.DIFFUSION_STEPS)
        self.diagnostic_history: list[dict[str, Any]] = []
        self._configured = False

    def configure(self, *, action_space: Any, n_envs: int) -> None:
        self._n_envs = int(n_envs)
        self._action_dim = int(np.prod(action_space.shape[1:]))
        if self._action_dim != self.primitive_action_dim:
            raise RuntimeError("E16 environment action dimension differs")
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
            raise KeyError("goal not in E16 planner info")
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
            raise RuntimeError("E16 online latent encoding differs")
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
            raise RuntimeError("E16 online normalized condition differs")
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
        count: int,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if count <= 0:
            raise ValueError("invalid E16 proposal count")
        active = action_active_mask(
            tau, primitive_action_dim=self.primitive_action_dim
        )
        flat_mask = active.reshape(len(tau), -1)
        if self.family == "vad":
            assert isinstance(self.proposer, VariableVelocityDiffusion)
            noise = torch.randn(
                len(tau),
                count,
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
                evaluations=e15.DIFFUSION_EVALUATIONS,
                guidance_scale=e15.GUIDANCE_SCALE,
            ).reshape(
                len(tau), count, e15.ACTION_HORIZON, self.primitive_action_dim
            )
        elif self.family == "diagonal_gaussian":
            assert isinstance(self.proposer, VariableDiagonalGaussian)
            mean, log_std = self.proposer(current, goal, state, delta, tau)
            noise = torch.randn(
                len(tau),
                count,
                mean.shape[1],
                device=self.device,
                generator=self.proposal_generator,
            )
            standardized = (
                mean[:, None] + log_std.exp()[:, None] * noise
            ) * flat_mask[:, None]
            standardized = standardized.reshape(
                len(tau), count, e15.ACTION_HORIZON, self.primitive_action_dim
            )
        else:
            assert isinstance(self.proposer, DirectTrajectoryGMM)
            logits, means, log_stds = self.proposer(current, goal, state, delta, tau)
            standardized, _ = sample_direct_gmm_with_modes(
                logits,
                means,
                log_stds,
                count=count,
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
    def _rollout(
        self, current_raw: torch.Tensor, planner: torch.Tensor, *, tau: int
    ) -> torch.Tensor:
        macro = planner[:, :, :tau].reshape(
            len(current_raw),
            planner.shape[1],
            tau // e15.ACTION_BLOCK,
            e15.ACTION_BLOCK * self.primitive_action_dim,
        )
        return rollout_from_single_latent(
            self.world_model, current=current_raw, macro_actions=macro
        )[:, :, -1]

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
            raise RuntimeError("E16 direct planner is not configured")
        if tau_value != spec.TAU or delta_value < tau_value:
            raise ValueError("E16 online delta/tau differs")
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
            tau_value // e15.ACTION_BLOCK,
            e15.ACTION_BLOCK * self.primitive_action_dim,
        )
        proposal_before = generator_state_sha256(self.proposal_generator)
        gmm_before = generator_state_sha256(self.gmm_generator)
        proposal_intervals: list[tuple[torch.cuda.Event, torch.cuda.Event]] = []
        adapter_intervals: list[tuple[torch.cuda.Event, torch.cuda.Event]] = []
        lewm_intervals: list[tuple[torch.cuda.Event, torch.cuda.Event]] = []
        rollout_trajectories = 0
        minimum_unique = 10**9
        for start in range(0, len(current), self.batch_size):
            stop = min(start + self.batch_size, len(current))
            first_count = candidate_count_for_arm(self.arm)
            (first_raw, first_planner, _), interval = cuda_interval(
                lambda: self._propose(
                    current=current[start:stop],
                    goal=goal[start:stop],
                    state=state[start:stop],
                    delta=delta[start:stop],
                    tau=tau[start:stop],
                    count=first_count,
                )
            )
            proposal_intervals.append(interval)
            first_terminal, interval = cuda_interval(
                lambda: self._rollout(
                    current_raw[start:stop], first_planner, tau=tau_value
                )
            )
            lewm_intervals.append(interval)
            rollout_trajectories += (stop - start) * first_count
            immediate_cost = (
                first_terminal - goal_raw[start:stop, None]
            ).square().sum(dim=-1)
            if is_continuation_arm(self.arm) and delta_value >= 2 * tau_value:
                flattened = first_terminal.reshape(-1, spec.LATENT_DIM)
                normalized = (
                    flattened - self.statistics.latent_mean
                ) / self.statistics.latent_std
                imagined_state, interval = cuda_interval(
                    lambda: self.state_adapter(normalized)
                )
                adapter_intervals.append(interval)
                second_goal = goal[start:stop, None].expand(
                    -1, first_count, -1
                ).reshape(-1, spec.LATENT_DIM)
                second_delta = torch.full(
                    (len(flattened),),
                    delta_value - tau_value,
                    device=self.device,
                    dtype=torch.long,
                )
                second_tau = torch.full_like(second_delta, tau_value)
                (second_raw, second_planner, _), interval = cuda_interval(
                    lambda: self._propose(
                        current=normalized,
                        goal=second_goal,
                        state=imagined_state,
                        delta=second_delta,
                        tau=second_tau,
                        count=spec.CONTINUATIONS_PER_FIRST,
                    )
                )
                del second_raw
                proposal_intervals.append(interval)
                second_terminal, interval = cuda_interval(
                    lambda: self._rollout(
                        flattened, second_planner, tau=tau_value
                    )
                )
                lewm_intervals.append(interval)
                rollout_trajectories += (
                    (stop - start)
                    * first_count
                    * spec.CONTINUATIONS_PER_FIRST
                )
                second_terminal = second_terminal.reshape(
                    stop - start,
                    first_count,
                    spec.CONTINUATIONS_PER_FIRST,
                    spec.LATENT_DIM,
                )
                final_cost = (
                    second_terminal
                    - goal_raw[start:stop, None, None]
                ).square().sum(dim=-1)
                score = continuation_score(final_cost)
            else:
                score = immediate_cost
            best = score.argmin(dim=1)
            first_macro = first_planner[:, :, :tau_value].reshape(
                stop - start,
                first_count,
                tau_value // e15.ACTION_BLOCK,
                e15.ACTION_BLOCK * self.primitive_action_dim,
            )
            output[start:stop] = first_macro[
                torch.arange(stop - start, device=self.device), best
            ].cpu()
            rounded = torch.round(first_raw[:, :, :tau_value] * 1.0e4).to(torch.int64)
            minimum_unique = min(
                minimum_unique,
                *(torch.unique(row.flatten(1), dim=0).shape[0] for row in rounded),
            )
        torch.cuda.synchronize()
        total = time.perf_counter() - total_started
        encoding_seconds = cuda_interval_seconds([encoding_interval])
        proposal_seconds = cuda_interval_seconds(proposal_intervals)
        adapter_seconds = cuda_interval_seconds(adapter_intervals)
        lewm_seconds = cuda_interval_seconds(lewm_intervals)
        other = max(
            0.0,
            total - encoding_seconds - proposal_seconds - adapter_seconds - lewm_seconds,
        )
        diagnostics = {
            "call": len(self.diagnostic_history),
            "arm": self.arm,
            "family": self.family,
            "delta": delta_value,
            "tau": tau_value,
            "first_candidate_count": candidate_count_for_arm(self.arm),
            "continuations_per_first": (
                spec.CONTINUATIONS_PER_FIRST
                if is_continuation_arm(self.arm) and delta_value >= 2 * tau_value
                else 0
            ),
            "continuation_best_count": (
                spec.CONTINUATION_BEST_COUNT
                if is_continuation_arm(self.arm) and delta_value >= 2 * tau_value
                else 0
            ),
            "lewm_rollout_trajectories": rollout_trajectories,
            "minimum_first_unique_candidates": minimum_unique,
            "planner_seconds": total,
            "end_to_end_stage_seconds": total,
            "encoding_seconds": encoding_seconds,
            "proposal_and_selection_seconds": proposal_seconds + other,
            "adapter_seconds": adapter_seconds,
            "lewm_scoring_seconds": lewm_seconds,
            "timing_decomposition_residual_seconds": total
            - encoding_seconds
            - (proposal_seconds + other)
            - adapter_seconds
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
            "strict_legal_oob_fraction": 0.0,
            "exact_legal_boundary_fraction": 0.0,
        }
        self.diagnostic_history.append(diagnostics)
        return {"actions": output, "solver_seconds": total}


__all__ = [
    "E16DirectArm",
    "E16DirectPlanner",
    "candidate_count_for_arm",
    "family_for_arm",
    "is_continuation_arm",
]
