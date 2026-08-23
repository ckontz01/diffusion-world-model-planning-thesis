"""Scheduled long-horizon planners and policy used by E14 Gate C."""

from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import stable_worldmodel as swm
import torch

import gdp_cem_e14_specs as spec
from gdp_cem_e14_models import (
    CosineSchedule,
    SAGEOptionPrior,
    SAGESubgoalGenerator,
    VariableDiagonalGaussian,
    VariableVelocityDiffusion,
    endpoint_active_mask,
    sample_trajectory_gmm,
    velocity_ddim_sample,
)
from gdp_cem_latent_rollout import rollout_from_single_latent


Arm = Literal[
    "base_cem",
    "sage_reconstruction",
    "vad_true",
    "vad_gaussian",
    "cvd_true",
    "cvd_gaussian",
]
ARMS: tuple[str, ...] = (
    "base_cem",
    "sage_reconstruction",
    "vad_true",
    "vad_gaussian",
    "cvd_true",
    "cvd_gaussian",
)


@dataclass(frozen=True)
class E14Statistics:
    latent_mean: torch.Tensor
    latent_std: torch.Tensor
    state_mean: torch.Tensor
    state_std: torch.Tensor
    action_mean: torch.Tensor
    action_std: torch.Tensor
    action_robust_low: torch.Tensor
    action_robust_high: torch.Tensor
    local_residual_mean: torch.Tensor
    local_residual_std: torch.Tensor

    def to(self, device: torch.device) -> "E14Statistics":
        return E14Statistics(
            **{
                name: value.to(device=device, dtype=torch.float32)
                for name, value in self.__dict__.items()
            }
        )

    def validate(self, *, state_dim: int, primitive_action_dim: int) -> None:
        expected = {
            "latent_mean": (spec.LATENT_DIM,),
            "latent_std": (spec.LATENT_DIM,),
            "state_mean": (state_dim,),
            "state_std": (state_dim,),
            "action_mean": (primitive_action_dim,),
            "action_std": (primitive_action_dim,),
            "action_robust_low": (primitive_action_dim,),
            "action_robust_high": (primitive_action_dim,),
            "local_residual_mean": (spec.LATENT_DIM,),
            "local_residual_std": (spec.LATENT_DIM,),
        }
        for name, shape in expected.items():
            value = getattr(self, name)
            if value.shape != shape or not torch.isfinite(value).all():
                raise ValueError(f"invalid E14 statistic: {name}")
        if (
            torch.any(self.latent_std <= 1.0e-6)
            or torch.any(self.state_std <= 1.0e-8)
            or torch.any(self.action_std <= 1.0e-6)
            or torch.any(self.local_residual_std <= 1.0e-6)
            or torch.any(self.action_robust_high <= self.action_robust_low)
        ):
            raise ValueError("invalid E14 statistic range")


def generator_state_sha256(generator: torch.Generator) -> str:
    return hashlib.sha256(generator.get_state().cpu().numpy().tobytes()).hexdigest()


class ScheduledE14Planner:
    """Run Base CEM, reconstructed SAGE, or a one-pass E14 endpoint."""

    def __init__(
        self,
        world_model: torch.nn.Module,
        *,
        arm: Arm,
        statistics: E14Statistics,
        state_dim: int,
        primitive_action_dim: int,
        endpoint_model: VariableVelocityDiffusion | VariableDiagonalGaussian | None = None,
        sage_subgoal: SAGESubgoalGenerator | None = None,
        sage_option: SAGEOptionPrior | None = None,
        candidate_count: int = 300,
        cem_rounds: int = 30,
        elites: int = 30,
        batch_size: int = 1,
        planner_seed: int = 1234,
        proposal_seed: int = 5678,
    ) -> None:
        if (
            arm not in ARMS
            or candidate_count <= 0
            or not 1 <= elites <= candidate_count
            or cem_rounds <= 0
            or batch_size <= 0
        ):
            raise ValueError("invalid E14 scheduled planner configuration")
        endpoint_arm = arm.startswith(("vad_", "cvd_"))
        if endpoint_arm != (endpoint_model is not None):
            raise ValueError("E14 endpoint model assignment differs")
        if (arm == "sage_reconstruction") != (
            sage_subgoal is not None and sage_option is not None
        ):
            raise ValueError("E14 SAGE model assignment differs")
        if arm != "sage_reconstruction" and (
            sage_subgoal is not None or sage_option is not None
        ):
            raise ValueError("E14 non-SAGE arm received SAGE models")
        if arm.endswith("_true") and not isinstance(
            endpoint_model, VariableVelocityDiffusion
        ):
            raise TypeError("E14 true endpoint requires velocity diffusion")
        if arm.endswith("_gaussian") and not isinstance(
            endpoint_model, VariableDiagonalGaussian
        ):
            raise TypeError("E14 Gaussian endpoint requires diagonal Gaussian")
        self.world_model = world_model
        self.arm = arm
        self.statistics = statistics
        self.state_dim = int(state_dim)
        self.primitive_action_dim = int(primitive_action_dim)
        self.endpoint_model = endpoint_model
        self.sage_subgoal = sage_subgoal
        self.sage_option = sage_option
        self.candidate_count = int(candidate_count)
        self.cem_rounds = int(cem_rounds)
        self.elites = int(elites)
        self.batch_size = int(batch_size)
        self.device = next(world_model.parameters()).device
        statistics.validate(
            state_dim=self.state_dim,
            primitive_action_dim=self.primitive_action_dim,
        )
        self.statistics = statistics.to(self.device)
        self.planner_generator = torch.Generator(device=self.device).manual_seed(
            int(planner_seed)
        )
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
            raise RuntimeError("E14 environment action dimension differs")
        self._configured = True

    @torch.inference_mode()
    def _encode(
        self, info_dict: dict[str, Any]
    ) -> tuple[torch.Tensor, torch.Tensor]:
        work = {
            key: value.to(self.device) if torch.is_tensor(value) else value
            for key, value in info_dict.items()
        }
        current = {key: value for key, value in work.items() if torch.is_tensor(value)}
        current.pop("action", None)
        goal = {key: value for key, value in work.items() if torch.is_tensor(value)}
        if "goal" not in goal:
            raise KeyError("goal not in E14 planner info")
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
            raise RuntimeError("E14 online latent encoding differs")
        return current_embedding, goal_embedding

    def _normalized_condition(
        self,
        current_raw: torch.Tensor,
        goal_raw: torch.Tensor,
        raw_state: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        stats = self.statistics
        current = (current_raw - stats.latent_mean) / stats.latent_std
        goal = (goal_raw - stats.latent_mean) / stats.latent_std
        state = (raw_state - stats.state_mean) / stats.state_std
        if (
            state.shape != (len(current), self.state_dim)
            or not torch.isfinite(current).all()
            or not torch.isfinite(goal).all()
            or not torch.isfinite(state).all()
        ):
            raise RuntimeError("E14 online normalized condition differs")
        return current, goal, state

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
        if target.ndim == 2:
            cost = (terminal - target[:, None]).square().sum(dim=-1)
        elif target.shape == terminal.shape:
            cost = (terminal - target).square().sum(dim=-1)
        else:
            raise ValueError("E14 planner target shape differs")
        return terminal, cost

    def _decode_endpoint_actions(
        self, output: torch.Tensor, *, endpoint: str, tau: int
    ) -> torch.Tensor:
        offset = 0 if endpoint == "vad" else spec.LATENT_DIM
        normalized = output[:, :, offset:].reshape(
            len(output),
            self.candidate_count,
            spec.ACTION_HORIZON,
            self.primitive_action_dim,
        )[:, :, :tau]
        low = (
            (self.statistics.action_robust_low - self.statistics.action_mean)
            / self.statistics.action_std
        )
        high = (
            (self.statistics.action_robust_high - self.statistics.action_mean)
            / self.statistics.action_std
        )
        normalized = torch.maximum(torch.minimum(normalized, high), low)
        return normalized * self.statistics.action_std + self.statistics.action_mean

    @torch.inference_mode()
    def _endpoint_bank(
        self,
        *,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau_tensor: torch.Tensor,
        tau: int,
    ) -> tuple[torch.Tensor, torch.Tensor | None, dict[str, float]]:
        endpoint = "vad" if self.arm.startswith("vad_") else "cvd"
        assert self.endpoint_model is not None
        mask = endpoint_active_mask(
            endpoint,
            tau_tensor,
            latent_dim=spec.LATENT_DIM,
            primitive_action_dim=self.primitive_action_dim,
        )
        output_dim = mask.shape[1]
        noise = torch.randn(
            len(current),
            self.candidate_count,
            output_dim,
            device=self.device,
            generator=self.proposal_generator,
        ) * mask[:, None]
        if isinstance(self.endpoint_model, VariableVelocityDiffusion):
            output = velocity_ddim_sample(
                self.endpoint_model,
                current=current,
                goal=goal,
                state=state,
                delta=delta,
                tau=tau_tensor,
                initial_noise=noise,
                active_mask=mask,
                schedule=self.schedule,
                evaluations=spec.DIFFUSION_EVALUATIONS,
                guidance_scale=spec.GUIDANCE_SCALE,
            )
        else:
            mean, log_std = self.endpoint_model(
                current, goal, state, delta, tau_tensor
            )
            output = (mean[:, None] + log_std.exp()[:, None] * noise) * mask[:, None]
        actions = self._decode_endpoint_actions(output, endpoint=endpoint, tau=tau)
        paired_local = None
        if endpoint == "cvd":
            residual = (
                output[:, :, : spec.LATENT_DIM]
                * self.statistics.local_residual_std
                + self.statistics.local_residual_mean
            )
            local_normalized = goal[:, None] + residual
            paired_local = (
                local_normalized * self.statistics.latent_std
                + self.statistics.latent_mean
            )
        normalized_action = (
            actions - self.statistics.action_mean
        ) / self.statistics.action_std
        rounded = torch.round(normalized_action * 1.0e4).to(torch.int64)
        unique = [
            torch.unique(row.flatten(1), dim=0).shape[0] for row in rounded
        ]
        low = self.statistics.action_robust_low
        high = self.statistics.action_robust_high
        boundary = torch.logical_or(actions == low, actions == high).float().mean()
        return actions, paired_local, {
            "minimum_unique_candidates": float(min(unique)),
            "boundary_fraction": float(boundary.cpu()),
        }

    @torch.inference_mode()
    def _base_cem(
        self,
        current_raw: torch.Tensor,
        goal_raw: torch.Tensor,
        *,
        tau: int,
    ) -> tuple[torch.Tensor, int]:
        batch = len(current_raw)
        horizon = tau // spec.ACTION_BLOCK
        action_dim = spec.ACTION_BLOCK * self.primitive_action_dim
        mean = torch.zeros(batch, horizon, action_dim, device=self.device)
        scale = torch.ones_like(mean)
        cost_calls = 0
        for _ in range(self.cem_rounds):
            candidates = torch.randn(
                batch,
                self.candidate_count,
                horizon,
                action_dim,
                device=self.device,
                generator=self.planner_generator,
            )
            candidates = candidates * scale[:, None] + mean[:, None]
            candidates[:, 0] = mean
            _, cost = self._terminal_and_cost(current_raw, candidates, goal_raw)
            elite_index = torch.topk(
                cost, k=self.elites, dim=1, largest=False
            ).indices
            batch_index = torch.arange(batch, device=self.device)[:, None]
            elite = candidates[batch_index, elite_index]
            mean = elite.mean(dim=1)
            scale = elite.std(dim=1)
            cost_calls += 1
        return mean, cost_calls

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
            (self.statistics.action_robust_low - self.statistics.action_mean)
            / self.statistics.action_std
        )
        high = (
            (self.statistics.action_robust_high - self.statistics.action_mean)
            / self.statistics.action_std
        )
        normalized = torch.maximum(torch.minimum(normalized, high), low)
        actions = normalized * self.statistics.action_std + self.statistics.action_mean
        horizon = tau // spec.ACTION_BLOCK
        action_dim = spec.ACTION_BLOCK * self.primitive_action_dim
        candidates = actions.reshape(
            len(actions), self.candidate_count, horizon, action_dim
        )
        _, cost = self._terminal_and_cost(
            current_raw, candidates, generated_local_raw
        )
        elite_index = torch.topk(cost, k=self.elites, dim=1, largest=False).indices
        batch_index = torch.arange(len(actions), device=self.device)[:, None]
        elite = candidates[batch_index, elite_index]
        mean = elite.mean(dim=1)
        scale = elite.std(dim=1)
        cost_calls = 1
        for _ in range(self.cem_rounds - 1):
            candidates = torch.randn(
                len(actions),
                self.candidate_count,
                horizon,
                action_dim,
                device=self.device,
                generator=self.planner_generator,
            )
            candidates = candidates * scale[:, None] + mean[:, None]
            candidates[:, 0] = mean
            _, cost = self._terminal_and_cost(
                current_raw, candidates, generated_local_raw
            )
            elite_index = torch.topk(
                cost, k=self.elites, dim=1, largest=False
            ).indices
            elite = candidates[batch_index, elite_index]
            mean = elite.mean(dim=1)
            scale = elite.std(dim=1)
            cost_calls += 1
        rounded = torch.round(normalized * 1.0e4).to(torch.int64)
        unique = [
            torch.unique(row.flatten(1), dim=0).shape[0] for row in rounded
        ]
        boundary = torch.logical_or(actions == self.statistics.action_robust_low, actions == self.statistics.action_robust_high).float().mean()
        return mean, cost_calls, {
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
        if not self._configured:
            raise RuntimeError("E14 scheduled planner is not configured")
        if tau_value not in spec.TAU_VALUES or delta_value < tau_value:
            raise ValueError("E14 online delta/tau differs")
        started = time.time()
        current_raw, goal_raw = self._encode(info_dict)
        raw_state = raw_state.to(self.device, dtype=torch.float32)
        current, goal, state = self._normalized_condition(
            current_raw, goal_raw, raw_state
        )
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
        cost_calls = 0
        minimum_unique: float | None = None
        maximum_boundary: float | None = None
        planner_state_before = generator_state_sha256(self.planner_generator)
        proposal_state_before = generator_state_sha256(self.proposal_generator)
        gmm_state_before = generator_state_sha256(self.gmm_generator)
        for start in range(0, len(current), self.batch_size):
            stop = min(start + self.batch_size, len(current))
            if self.arm == "base_cem":
                selected, calls = self._base_cem(
                    current_raw[start:stop], goal_raw[start:stop], tau=tau_value
                )
            elif self.arm == "sage_reconstruction":
                selected, calls, batch_extra = self._sage_cem(
                    current_raw[start:stop],
                    goal_raw[start:stop],
                    current[start:stop],
                    goal[start:stop],
                    state[start:stop],
                    delta[start:stop],
                    tau[start:stop],
                    tau=tau_value,
                )
                minimum_unique = min(
                    batch_extra["minimum_initial_unique_candidates"],
                    minimum_unique
                    if minimum_unique is not None
                    else batch_extra["minimum_initial_unique_candidates"],
                )
                maximum_boundary = max(
                    batch_extra["initial_boundary_fraction"],
                    maximum_boundary
                    if maximum_boundary is not None
                    else batch_extra["initial_boundary_fraction"],
                )
            else:
                actions, paired_local, batch_extra = self._endpoint_bank(
                    current=current[start:stop],
                    goal=goal[start:stop],
                    state=state[start:stop],
                    delta=delta[start:stop],
                    tau_tensor=tau[start:stop],
                    tau=tau_value,
                )
                macro = actions.reshape(
                    stop - start,
                    self.candidate_count,
                    tau_value // spec.ACTION_BLOCK,
                    spec.ACTION_BLOCK * self.primitive_action_dim,
                )
                target = (
                    goal_raw[start:stop]
                    if paired_local is None
                    else paired_local
                )
                _, cost = self._terminal_and_cost(
                    current_raw[start:stop], macro, target
                )
                best = cost.argmin(dim=1)
                selected = macro[
                    torch.arange(stop - start, device=self.device), best
                ]
                calls = 1
                minimum_unique = min(
                    batch_extra["minimum_unique_candidates"],
                    minimum_unique
                    if minimum_unique is not None
                    else batch_extra["minimum_unique_candidates"],
                )
                maximum_boundary = max(
                    batch_extra["boundary_fraction"],
                    maximum_boundary
                    if maximum_boundary is not None
                    else batch_extra["boundary_fraction"],
                )
            output[start:stop] = selected.cpu()
            cost_calls += calls
        elapsed = time.time() - started
        diagnostics: dict[str, Any] = {
            "call": len(self.diagnostic_history),
            "arm": self.arm,
            "delta": delta_value,
            "tau": tau_value,
            "candidate_count": self.candidate_count,
            "cem_rounds": (
                self.cem_rounds
                if self.arm in ("base_cem", "sage_reconstruction")
                else 1
            ),
            "lewm_population_calls": cost_calls,
            "planner_seconds": elapsed,
            "planner_generator_before_sha256": planner_state_before,
            "planner_generator_after_sha256": generator_state_sha256(
                self.planner_generator
            ),
            "proposal_generator_before_sha256": proposal_state_before,
            "proposal_generator_after_sha256": generator_state_sha256(
                self.proposal_generator
            ),
            "gmm_generator_before_sha256": gmm_state_before,
            "gmm_generator_after_sha256": generator_state_sha256(
                self.gmm_generator
            ),
        }
        if minimum_unique is not None:
            diagnostics["minimum_unique_candidates"] = minimum_unique
        if maximum_boundary is not None:
            diagnostics["maximum_boundary_fraction"] = maximum_boundary
        self.diagnostic_history.append(diagnostics)
        return {"actions": output, "solver_seconds": elapsed}


class ScheduledE14Policy(swm.policy.BasePolicy):
    """Execute a frozen duration schedule, repeating it for PushT's 2H budget."""

    def __init__(
        self,
        planner: ScheduledE14Planner,
        *,
        schedule: tuple[int, ...],
        environment_budget: int,
        state_key: str,
        process: dict[str, Any],
        transform: dict[str, Any],
    ) -> None:
        super().__init__()
        if sum(schedule) <= 0 or environment_budget % sum(schedule):
            raise ValueError("E14 environment budget is not whole schedule cycles")
        self.type = "world_model"
        self.planner = planner
        self.base_schedule = tuple(schedule)
        self.environment_budget = int(environment_budget)
        self.state_key = state_key
        self.process = process
        self.transform = transform
        cycles = environment_budget // sum(schedule)
        self.stages: list[tuple[int, int]] = []
        for _ in range(cycles):
            elapsed = 0
            for tau in schedule:
                self.stages.append((sum(schedule) - elapsed, tau))
                elapsed += tau

    def set_env(self, env: Any) -> None:
        self.env = env
        self.planner.configure(action_space=env.action_space, n_envs=env.num_envs)
        self._action_buffer: deque[torch.Tensor] = deque(
            maxlen=max(self.base_schedule)
        )
        self._stage_index = 0

    def get_action(self, info_dict: dict[str, Any], **kwargs: Any) -> np.ndarray:
        if len(self._action_buffer) == 0:
            if self._stage_index >= len(self.stages):
                raise RuntimeError("E14 duration schedule exhausted before budget")
            if self.state_key not in info_dict:
                raise KeyError(f"E14 state key absent: {self.state_key}")
            raw_state = np.asarray(info_dict[self.state_key])
            if raw_state.ndim == 3:
                raw_state = raw_state[:, -1]
            if raw_state.ndim != 2:
                raise RuntimeError("E14 online raw-state shape differs")
            prepared = self._prepare_info(deepcopy(info_dict))
            for key, value in prepared.items():
                if torch.is_tensor(value):
                    prepared[key] = value.to(self.planner.device)
            delta, tau = self.stages[self._stage_index]
            result = self.planner.solve(
                prepared,
                raw_state=torch.from_numpy(raw_state).float(),
                delta_value=delta,
                tau_value=tau,
            )
            macro = result["actions"]
            plan = macro.reshape(
                self.env.num_envs, tau, self.planner.primitive_action_dim
            )
            self._action_buffer.extend(plan.transpose(0, 1))
            self._stage_index += 1
        action = self._action_buffer.popleft().reshape(*self.env.action_space.shape)
        result = action.numpy()
        if "action" in self.process:
            result = self.process["action"].inverse_transform(result)
        return result


__all__ = [
    "Arm",
    "ARMS",
    "E14Statistics",
    "ScheduledE14Planner",
    "ScheduledE14Policy",
]
