"""Frozen E18 greedy and action-conditioned continuation planners."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Literal

import numpy as np
import torch

import gdp_cem_e15_specs as e15
import gdp_cem_e18_specs as spec
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
from gdp_cem_e17_models import TransitionStateAdapter
from gdp_cem_e18_runtime import E15Statistics, cuda_interval, cuda_interval_seconds
from gdp_cem_latent_rollout import rollout_from_single_latent


E18Arm = Literal[
    "vad_greedy_300",
    "vad_greedy_576",
    "vad_continuation",
    "diagonal_gaussian_continuation",
    "direct_gmm_continuation",
]


def generator_state_sha256(generator: torch.Generator) -> str:
    """Hash a generator state without depending on the omitted E14 wrapper."""

    return hashlib.sha256(generator.get_state().cpu().numpy().tobytes()).hexdigest()


def family_for_arm(arm: E18Arm) -> str:
    return spec.family_for_arm(arm)


def is_continuation_arm(arm: E18Arm) -> bool:
    return spec.is_continuation_arm(arm)


def candidate_count_for_arm(arm: E18Arm) -> int:
    return spec.first_candidate_count(arm)


def continuation_score(final_cost: torch.Tensor) -> torch.Tensor:
    """Mean the frozen lower tail of each first branch's continuations."""

    if (
        final_cost.ndim != 3
        or final_cost.shape[-1] != spec.CONTINUATIONS_PER_FIRST
        or not torch.isfinite(final_cost).all()
    ):
        raise ValueError("invalid E18 continuation cost")
    return torch.topk(
        final_cost,
        k=spec.CONTINUATION_BEST_COUNT,
        dim=-1,
        largest=False,
        sorted=False,
    ).values.mean(dim=-1)


class E18Planner:
    """Direct proposer with frozen greedy or E17-conditioned lookahead."""

    def __init__(
        self,
        world_model: torch.nn.Module,
        *,
        arm: E18Arm,
        statistics: E15Statistics,
        state_dim: int,
        primitive_action_dim: int,
        proposer: VariableVelocityDiffusion
        | VariableDiagonalGaussian
        | DirectTrajectoryGMM,
        state_adapter: TransitionStateAdapter | None,
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
            raise ValueError("invalid E18 planner configuration")
        if is_continuation_arm(arm):
            if state_adapter is None or (
                state_adapter.latent_dim != spec.LATENT_DIM
                or state_adapter.state_dim != state_dim
                or state_adapter.action_dim != primitive_action_dim
            ):
                raise ValueError("E18 state-adapter dimension differs")
        elif state_adapter is not None:
            raise ValueError("E18 greedy planner must not load an adapter")
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
        if self.state_adapter is not None:
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
            raise RuntimeError("E18 environment action dimension differs")
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
            raise KeyError("goal not in E18 planner info")
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
            raise RuntimeError("E18 online latent encoding differs")
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
            raise RuntimeError("E18 online normalized condition differs")
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
            raise ValueError("invalid E18 proposal count")
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
    def _predict_intermediate_state(
        self,
        *,
        current: torch.Tensor,
        terminal_raw: torch.Tensor,
        state: torch.Tensor,
        first_raw: torch.Tensor,
        tau: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch, count, horizon, action_dim = first_raw.shape
        if (
            current.shape != (batch, spec.LATENT_DIM)
            or terminal_raw.shape != (batch, count, spec.LATENT_DIM)
            or state.shape != (batch, self.state_dim)
            or horizon != spec.ACTION_HORIZON
            or action_dim != self.primitive_action_dim
            or tau.shape != (batch,)
        ):
            raise ValueError("E18 adapter bridge input shape differs")
        terminal = (
            terminal_raw - self.statistics.latent_mean
        ) / self.statistics.latent_std
        expanded_tau = tau[:, None].expand(-1, count).reshape(-1)
        action_mask = action_active_mask(
            tau, primitive_action_dim=self.primitive_action_dim
        )[:, :, 0]
        action_mask = action_mask[:, None].expand(-1, count, -1).reshape(
            -1, spec.ACTION_HORIZON
        )
        if self.state_adapter is None:
            raise RuntimeError("E18 continuation adapter is absent")
        predicted = self.state_adapter(
            current_latent=current[:, None]
            .expand(-1, count, -1)
            .reshape(-1, spec.LATENT_DIM),
            terminal_latent=terminal.reshape(-1, spec.LATENT_DIM),
            current_state=state[:, None]
            .expand(-1, count, -1)
            .reshape(-1, self.state_dim),
            action_raw=first_raw.reshape(
                -1, spec.ACTION_HORIZON, self.primitive_action_dim
            ),
            action_mask=action_mask,
            tau=expanded_tau,
        )
        if not torch.isfinite(predicted).all():
            raise RuntimeError("non-finite E18 predicted intermediate state")
        return predicted, terminal.reshape(-1, spec.LATENT_DIM)

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
            raise RuntimeError("E18 planner is not configured")
        if tau_value != spec.TAU or delta_value < tau_value:
            raise ValueError("E18 online delta/tau differs")
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
        minimum_second_unique: int | None = None
        predicted_state_absolute_max: float | None = None
        predicted_state_absolute_q99: float | None = None
        raw_candidate_count = 0
        raw_strict_oob_count = 0
        raw_exact_boundary_count = 0
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
            raw_candidate_count += first_raw.numel()
            raw_strict_oob_count += int((first_raw.abs() > 1.0).sum().item())
            raw_exact_boundary_count += int((first_raw.abs() == 1.0).sum().item())
            if is_continuation_arm(self.arm) and delta_value >= 2 * tau_value:
                imagined_state, interval = cuda_interval(
                    lambda: self._predict_intermediate_state(
                        current=current[start:stop],
                        terminal_raw=first_terminal,
                        state=state[start:stop],
                        first_raw=first_raw,
                        tau=tau[start:stop],
                    )
                )
                imagined_state, normalized = imagined_state
                adapter_intervals.append(interval)
                absolute_state = imagined_state.abs()
                batch_max = float(absolute_state.max().item())
                batch_q99 = float(torch.quantile(absolute_state.float(), 0.99).item())
                predicted_state_absolute_max = max(
                    predicted_state_absolute_max or 0.0, batch_max
                )
                predicted_state_absolute_q99 = max(
                    predicted_state_absolute_q99 or 0.0, batch_q99
                )
                flattened = first_terminal.reshape(-1, spec.LATENT_DIM)
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
                proposal_intervals.append(interval)
                raw_candidate_count += second_raw.numel()
                raw_strict_oob_count += int((second_raw.abs() > 1.0).sum().item())
                raw_exact_boundary_count += int(
                    (second_raw.abs() == 1.0).sum().item()
                )
                rounded_second = torch.round(
                    second_raw[:, :, :tau_value] * 1.0e4
                ).to(torch.int64)
                batch_second_unique = min(
                    torch.unique(row.flatten(1), dim=0).shape[0]
                    for row in rounded_second
                )
                minimum_second_unique = min(
                    minimum_second_unique
                    if minimum_second_unique is not None
                    else batch_second_unique,
                    batch_second_unique,
                )
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
            "minimum_second_unique_candidates_per_first": minimum_second_unique,
            "predicted_state_absolute_max": predicted_state_absolute_max,
            "predicted_state_absolute_q99": predicted_state_absolute_q99,
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
            "strict_legal_oob_fraction": raw_strict_oob_count
            / max(1, raw_candidate_count),
            "exact_legal_boundary_fraction": raw_exact_boundary_count
            / max(1, raw_candidate_count),
        }
        self.diagnostic_history.append(diagnostics)
        return {"actions": output, "solver_seconds": total}


__all__ = [
    "E18Arm",
    "E18Planner",
    "candidate_count_for_arm",
    "continuation_score",
    "family_for_arm",
    "is_continuation_arm",
]
