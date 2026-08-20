"""One-rollout cost integration shared by all matched planner arms."""

from __future__ import annotations

import time
from typing import Any, Literal

import torch
from torch import nn

from .models import (
    ConditionalDiffusionVerifier,
    DeterministicForwardVerifier,
    FlowInverseDynamics,
    TemporalReachabilityHead,
    TensorStandardizer,
)

Arm = Literal["b0", "acid", "reachability", "diffusion", "forward"]


def _clone_non_tensor(value: Any) -> Any:
    return value


class SharedRolloutCostModel(nn.Module):
    """Augment a frozen Le-WM-style model without a second world-model rollout."""

    def __init__(
        self,
        world_model: nn.Module,
        *,
        arm: Arm,
        scorer: nn.Module | None = None,
        latent_mean: torch.Tensor | None = None,
        latent_std: torch.Tensor | None = None,
        action_mean: torch.Tensor | None = None,
        action_std: torch.Tensor | None = None,
        lambda_weight: float = 0.07,
        spread_epsilon: float = 1.0e-8,
        horizon: int = 5,
        noise_seed: int = 0,
        diffusion_sigmas: tuple[float, ...] = (0.10, 0.25, 0.50),
        use_action_condition: bool = True,
        record_diagnostics: bool = False,
    ) -> None:
        super().__init__()
        if arm == "b0" and scorer is not None:
            raise ValueError("B0 must not have a scorer")
        if arm != "b0" and scorer is None:
            raise ValueError(f"{arm} requires a scorer")
        expected_types: dict[str, type[nn.Module]] = {
            "acid": FlowInverseDynamics,
            "reachability": TemporalReachabilityHead,
            "diffusion": ConditionalDiffusionVerifier,
            "forward": DeterministicForwardVerifier,
        }
        if arm in expected_types and not isinstance(scorer, expected_types[arm]):
            raise TypeError(f"{arm} requires {expected_types[arm].__name__}")
        if lambda_weight < 0 or spread_epsilon <= 0 or horizon <= 0:
            raise ValueError("invalid cost configuration")
        if not diffusion_sigmas or any(sigma <= 0 for sigma in diffusion_sigmas):
            raise ValueError("diffusion sigmas must be positive")

        self.world_model = world_model
        self.arm: Arm = arm
        self.scorer = scorer
        self.lambda_weight = float(lambda_weight)
        self.spread_epsilon = float(spread_epsilon)
        self.horizon = int(horizon)
        self.diffusion_sigmas = tuple(float(value) for value in diffusion_sigmas)
        self.noise_seed = int(noise_seed)
        self.use_action_condition = bool(use_action_condition)
        self.record_diagnostics = bool(record_diagnostics)
        self.latent_standardizer: TensorStandardizer | None = None
        self.action_standardizer: TensorStandardizer | None = None
        # ACID and TRM are trained on the frozen encoder's native latents.
        # Latent standardization is an explicit D1/F1 design choice.
        if arm in ("diffusion", "forward"):
            if latent_mean is None or latent_std is None:
                raise ValueError(f"{arm} requires latent statistics")
            self.latent_standardizer = TensorStandardizer(latent_mean, latent_std)
        if arm == "acid":
            if action_mean is None or action_std is None:
                raise ValueError("ACID requires action statistics")
            self.action_standardizer = TensorStandardizer(action_mean, action_std)

        self.register_buffer("acid_noise", torch.empty(0), persistent=True)
        self.register_buffer("diffusion_noise", torch.empty(0), persistent=True)
        self._build_noise_banks()
        self.last_diagnostics: dict[str, Any] = {}
        self.diagnostic_history: list[dict[str, Any]] = []
        self.call_count = 0

    def _build_noise_banks(self) -> None:
        generator = torch.Generator(device="cpu").manual_seed(self.noise_seed)
        if isinstance(self.scorer, FlowInverseDynamics):
            self.acid_noise = torch.randn(
                self.horizon, self.scorer.action_dim, generator=generator
            )
        if isinstance(self.scorer, ConditionalDiffusionVerifier):
            self.diffusion_noise = torch.randn(
                len(self.diffusion_sigmas),
                self.horizon,
                self.scorer.latent_dim,
                generator=generator,
            )

    def begin_plan(self) -> None:
        """Reset per-solve counters while retaining common verifier noise."""

        self.call_count = 0
        self.last_diagnostics = {}

    def _record(self, diagnostics: dict[str, Any]) -> None:
        self.last_diagnostics = diagnostics
        if not self.record_diagnostics:
            return
        serializable: dict[str, Any] = {}
        for key, value in diagnostics.items():
            if torch.is_tensor(value):
                serializable[key] = value.flatten().tolist()
            else:
                serializable[key] = value
        self.diagnostic_history.append(serializable)

    def _rollout_once(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if "goal" not in info_dict:
            raise KeyError("goal not in info_dict")
        if action_candidates.ndim != 4:
            raise ValueError("action candidates must have shape (B,N,H,A)")
        if action_candidates.shape[2] != self.horizon:
            raise ValueError("candidate horizon differs from configured horizon")
        device = next(self.world_model.parameters()).device
        work: dict[str, Any] = {}
        for key, value in info_dict.items():
            work[key] = (
                value.to(device) if torch.is_tensor(value) else _clone_non_tensor(value)
            )
        candidates = action_candidates.to(device)

        goal = {
            key: value[:, 0] for key, value in work.items() if torch.is_tensor(value)
        }
        goal["pixels"] = goal["goal"]
        for key in list(goal):
            if key.startswith("goal_"):
                goal[key[len("goal_") :]] = goal.pop(key)
        goal.pop("action", None)
        goal = self.world_model.encode(goal)
        work["goal_emb"] = goal["emb"]
        work = self.world_model.rollout(work, candidates)
        goal_cost = self.world_model.criterion(work)
        trajectory = work.get("predicted_emb")
        if not torch.is_tensor(trajectory) or trajectory.ndim != 4:
            raise RuntimeError("world model did not return a (B,N,T,D) trajectory")
        expected = self.horizon + 1
        if (
            trajectory.shape[:2] != candidates.shape[:2]
            or trajectory.shape[2] != expected
        ):
            raise RuntimeError(
                f"expected trajectory (B,N,{expected},D), got {tuple(trajectory.shape)}"
            )
        if goal_cost.shape != candidates.shape[:2]:
            raise RuntimeError("goal cost has an unexpected shape")
        return goal_cost, trajectory, candidates, goal["emb"]

    def _standardized_transitions(
        self, trajectory: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if self.latent_standardizer is None:
            raise RuntimeError("latent standardizer is unavailable")
        current = self.latent_standardizer(trajectory[:, :, :-1])
        next_latent = self.latent_standardizer(trajectory[:, :, 1:])
        return current, next_latent

    def _acid_cost(
        self, trajectory: torch.Tensor, actions: torch.Tensor
    ) -> torch.Tensor:
        assert isinstance(self.scorer, FlowInverseDynamics)
        if self.action_standardizer is None:
            raise RuntimeError("action standardizer is unavailable")
        current = trajectory[:, :, :-1]
        next_latent = trajectory[:, :, 1:]
        noise = self.acid_noise.to(device=actions.device, dtype=actions.dtype)
        noise = noise.view(1, 1, self.horizon, -1).expand_as(actions)
        inferred_standardized = self.scorer.one_step_action(current, next_latent, noise)
        # The paper standardizes action targets for training and explicitly
        # de-normalizes the IDM output at inference.  The residual therefore
        # lives in the same planner-coordinate action space as `actions`.
        inferred_action = self.action_standardizer.inverse(inferred_standardized)
        return (actions - inferred_action).square().sum(dim=-1).mean(dim=-1)

    def _diffusion_cost(
        self, trajectory: torch.Tensor, actions: torch.Tensor
    ) -> torch.Tensor:
        assert isinstance(self.scorer, ConditionalDiffusionVerifier)
        current, next_latent = self._standardized_transitions(trajectory)
        per_level: list[torch.Tensor] = []
        for level, sigma_value in enumerate(self.diffusion_sigmas):
            noise = self.diffusion_noise[level].to(
                device=next_latent.device, dtype=next_latent.dtype
            )
            noise = noise.view(1, 1, self.horizon, -1).expand_as(next_latent)
            sigma = torch.full(
                next_latent.shape[:-1],
                sigma_value,
                device=next_latent.device,
                dtype=next_latent.dtype,
            )
            noisy_next = next_latent + sigma.unsqueeze(-1) * noise
            scorer_actions = (
                actions if self.use_action_condition else torch.zeros_like(actions)
            )
            prediction = self.scorer(current, scorer_actions, noisy_next, sigma)
            per_level.append((prediction - noise).square().mean(dim=-1).mean(dim=-1))
        return torch.stack(per_level, dim=0).mean(dim=0)

    def _forward_cost(
        self, trajectory: torch.Tensor, actions: torch.Tensor
    ) -> torch.Tensor:
        assert isinstance(self.scorer, DeterministicForwardVerifier)
        current, next_latent = self._standardized_transitions(trajectory)
        scorer_actions = (
            actions if self.use_action_condition else torch.zeros_like(actions)
        )
        prediction = self.scorer(current, scorer_actions)
        return (prediction - next_latent).square().mean(dim=-1).mean(dim=-1)

    def _reachability_cost(
        self, trajectory: torch.Tensor, goal_embedding: torch.Tensor
    ) -> torch.Tensor:
        assert isinstance(self.scorer, TemporalReachabilityHead)
        terminal = trajectory[:, :, -1]
        goal = goal_embedding[..., -1, :]
        if goal.ndim == 2:
            goal = goal[:, None]
        goal = goal.expand_as(terminal)
        return self.scorer(terminal, goal)

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        started = time.perf_counter()
        goal_cost, trajectory, actions, goal_embedding = self._rollout_once(
            info_dict, action_candidates
        )
        rollout_seconds = time.perf_counter() - started
        if self.arm == "b0":
            self.call_count += 1
            self._record(
                {
                    "call": self.call_count,
                    "rollout_seconds": rollout_seconds,
                    "verifier_seconds": 0.0,
                    "goal_std": goal_cost.std(dim=1, unbiased=True).detach().cpu(),
                }
            )
            return goal_cost

        verifier_started = time.perf_counter()
        if self.arm == "acid":
            verifier_cost = self._acid_cost(trajectory, actions)
        elif self.arm == "diffusion":
            verifier_cost = self._diffusion_cost(trajectory, actions)
        elif self.arm == "forward":
            verifier_cost = self._forward_cost(trajectory, actions)
        elif self.arm == "reachability":
            verifier_cost = self._reachability_cost(trajectory, goal_embedding)
        else:
            raise RuntimeError(f"unknown arm {self.arm}")
        verifier_seconds = time.perf_counter() - verifier_started
        if (
            verifier_cost.shape != goal_cost.shape
            or not torch.isfinite(verifier_cost).all()
        ):
            raise RuntimeError("verifier returned invalid costs")

        goal_spread = goal_cost.std(dim=1, unbiased=True)
        verifier_spread = verifier_cost.std(dim=1, unbiased=True)
        weight = (
            self.lambda_weight
            * goal_spread
            / verifier_spread.clamp_min(self.spread_epsilon)
        )
        combined = goal_cost + weight[:, None] * verifier_cost
        if not torch.isfinite(combined).all():
            raise RuntimeError("combined cost is not finite")
        self.call_count += 1
        self._record(
            {
                "call": self.call_count,
                "rollout_seconds": rollout_seconds,
                "verifier_seconds": verifier_seconds,
                "goal_std": goal_spread.detach().cpu(),
                "verifier_std": verifier_spread.detach().cpu(),
                "adaptive_weight": weight.detach().cpu(),
                "goal_min": goal_cost.min(dim=1).values.detach().cpu(),
                "verifier_min": verifier_cost.min(dim=1).values.detach().cpu(),
            }
        )
        return combined
