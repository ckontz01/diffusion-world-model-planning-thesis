"""Frozen scorer definitions for the v3 multi-seed D2 study."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
from torch import nn

from acid_alternative.costs import SharedRolloutCostModel
from acid_alternative.evaluate_matched import load_scorer
from acid_alternative.models import (
    ConditionalDiffusionVerifier,
    FlowInverseDynamics,
    TemporalReachabilityHead,
)


PROTOCOL_SHA256 = "c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb"
V2_PROTOCOL_SHA256 = "a6c33f33cc20da6e93ccdeb77269438de34869cb60c91b20e6da47801861ebff"
V2_TRAINER_SHA256 = "871ebc12c4af778031155f78b060e017c7060775d3f2e32bb49dc986925a52ad"
PRE_AMENDMENT_3_SOURCE_MANIFEST_SHA256 = (
    "875a9cbc19dba78db1706169b7f2d8bc97a70913d82b55f793735dfe8c2df388"
)
SIGMAS = (0.25, 1.0, 4.0)
LEGACY_DTV_SIGMAS = (0.10, 0.25, 0.50)
NOISE_DRAWS = 8
DIFFUSION_LAMBDA = 0.005
ACID_LAMBDA = 0.07
SPREAD_EPSILON = 1.0e-8
LOG_EPSILON = 1.0e-12
SEEDS = (6101, 6102, 6103)

Arm = Literal[
    "b0",
    "acid",
    "reachability",
    "dtv",
    "forward",
    "rdx",
    "ae",
    "ae_shuffled",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def derived_seed(label: str) -> int:
    value = int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "little")
    return value % (2**63 - 1)


def residual_noise_seed(task: str, scorer_seed: int, sigma: float, draw: int) -> int:
    return derived_seed(
        f"acid-alt-v3-d2-residual|task={task}|scorer={scorer_seed}|"
        f"sigma={sigma:.8f}|draw={draw}"
    )


def acid_noise_seed(
    task: str, scorer_seed: int, planner_seed: int, cost_call_index: int
) -> int:
    if cost_call_index < 0:
        raise ValueError("ACID cost-call index must be nonnegative")
    return derived_seed(
        f"acid-alt-v3-d2-acid|task={task}|scorer={scorer_seed}|planner={planner_seed}"
        f"|call={cost_call_index}"
    )


def load_training_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("status") != "ok":
        raise RuntimeError(f"training summary is incomplete: {path}")
    return summary


def load_residual_model(
    summary_path: Path,
    *,
    expected_condition: str,
    trainer_module: Any,
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], dict[str, Any]]:
    summary = load_training_summary(summary_path)
    seed = int(summary.get("seed", -1))
    if seed not in SEEDS or summary.get("condition") != expected_condition:
        raise RuntimeError(f"residual training identity mismatch: {summary_path}")
    expected_kind = (
        "residual_diffusion_x0_pilot_training"
        if seed == 6101
        else "residual_diffusion_x0_multiseed_d2_training"
    )
    expected_protocol = V2_PROTOCOL_SHA256 if seed == 6101 else PROTOCOL_SHA256
    if (
        summary.get("kind") != expected_kind
        or summary.get("protocol_sha256") != expected_protocol
        or summary.get("confirmation_data_read") is not False
    ):
        raise RuntimeError(f"residual training provenance mismatch: {summary_path}")
    checkpoint = Path(summary["checkpoint"])
    if not checkpoint.is_file() or sha256_file(checkpoint) != summary.get(
        "checkpoint_sha256"
    ):
        raise RuntimeError(f"residual checkpoint hash mismatch: {checkpoint}")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    config = payload.get("model_config", {})
    if (
        payload.get("model_name") != "residual_diffusion_x0"
        or payload.get("condition") != expected_condition
        or int(payload.get("seed", -1)) != seed
        or payload.get("protocol_sha256") != expected_protocol
        or config.get("name") != "residual_diffusion_x0"
    ):
        raise RuntimeError(f"residual checkpoint payload mismatch: {checkpoint}")
    model = trainer_module.ResidualDiffusionX0Verifier(
        latent_dim=int(config["latent_dim"]),
        action_dim=int(config["action_dim"]),
        width=int(config["width"]),
        depth=int(config["depth"]),
        noise_embedding_dim=int(config["noise_embedding_dim"]),
    )
    model.load_state_dict(payload["state_dict"], strict=True)
    model = model.to(device).eval().requires_grad_(False)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    if parameter_count != int(summary["parameter_count"]):
        raise RuntimeError(f"residual parameter-count mismatch: {summary_path}")
    return model, payload, {
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": summary["checkpoint_sha256"],
        "condition": expected_condition,
        "seed": seed,
        "kind": expected_kind,
        "protocol_sha256": expected_protocol,
        "parameter_count": parameter_count,
        "best_step": int(summary["best_step"]),
        "final_validation": summary["final_validation"],
    }


def validate_residual_pair(
    true_payload: dict[str, Any], shuffled_payload: dict[str, Any]
) -> None:
    for key in ("latent_mean", "latent_std", "residual_mean", "residual_std"):
        if not torch.equal(
            torch.as_tensor(true_payload[key]).float(),
            torch.as_tensor(shuffled_payload[key]).float(),
        ):
            raise RuntimeError(f"true/shuffled residual statistic differs: {key}")
    if int(true_payload["seed"]) != int(shuffled_payload["seed"]):
        raise RuntimeError("true/shuffled residual seeds differ")


def standardized_residual_inputs(
    trajectory: torch.Tensor, payload: dict[str, Any]
) -> tuple[torch.Tensor, torch.Tensor]:
    latent_mean = torch.as_tensor(
        payload["latent_mean"], device=trajectory.device, dtype=trajectory.dtype
    )
    latent_std = torch.as_tensor(
        payload["latent_std"], device=trajectory.device, dtype=trajectory.dtype
    )
    residual_mean = torch.as_tensor(
        payload["residual_mean"], device=trajectory.device, dtype=trajectory.dtype
    )
    residual_std = torch.as_tensor(
        payload["residual_std"], device=trajectory.device, dtype=trajectory.dtype
    )
    if torch.any(latent_std <= 1.0e-6) or torch.any(residual_std <= 1.0e-6):
        raise RuntimeError("residual checkpoint has degenerate standardization")
    current = (trajectory[..., :-1, :] - latent_mean) / latent_std
    successor = (trajectory[..., 1:, :] - latent_mean) / latent_std
    clean = (successor - current - residual_mean) / residual_std
    if not torch.isfinite(current).all() or not torch.isfinite(clean).all():
        raise RuntimeError("standardized residual inputs are non-finite")
    return current, clean


def build_residual_noise_bank(
    *, task: str, scorer_seed: int, horizon: int, latent_dim: int
) -> torch.Tensor:
    levels: list[torch.Tensor] = []
    for sigma in SIGMAS:
        draws: list[torch.Tensor] = []
        for draw in range(NOISE_DRAWS):
            generator = torch.Generator(device="cpu").manual_seed(
                residual_noise_seed(task, scorer_seed, sigma, draw)
            )
            draws.append(
                torch.randn(horizon, latent_dim, generator=generator, dtype=torch.float32)
            )
        levels.append(torch.stack(draws))
    return torch.stack(levels)


@torch.inference_mode()
def residual_endpoint_costs(
    model: nn.Module,
    *,
    current: torch.Tensor,
    clean: torch.Tensor,
    actions: torch.Tensor,
    noise_bank: torch.Tensor,
    batch_size: int | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return RDX, AE, and unconditional costs with the frozen reductions."""

    if current.shape != clean.shape or current.shape[:-1] != actions.shape[:-1]:
        raise ValueError("residual endpoint tensor shapes differ")
    leading = current.shape[:-1]
    horizon, latent_dim = current.shape[-2:]
    if noise_bank.shape != (len(SIGMAS), NOISE_DRAWS, horizon, latent_dim):
        raise ValueError("residual noise bank shape differs from frozen design")
    flat_count = math.prod(leading)
    current_flat = current.reshape(flat_count, latent_dim)
    clean_flat = clean.reshape(flat_count, latent_dim)
    action_flat = actions.reshape(flat_count, actions.shape[-1])
    chunk = flat_count if batch_size is None else int(batch_size)
    if chunk <= 0:
        raise ValueError("batch size must be positive")
    conditional_sum = torch.zeros(leading[:-1], device=current.device, dtype=torch.float64)
    unconditional_sum = torch.zeros_like(conditional_sum)
    for level, sigma_value in enumerate(SIGMAS):
        for draw in range(NOISE_DRAWS):
            step_noise = noise_bank[level, draw].to(
                device=current.device, dtype=current.dtype
            )
            expanded_noise = step_noise.expand(*leading[:-1], horizon, latent_dim)
            noise_flat = expanded_noise.reshape(flat_count, latent_dim)
            conditional_values: list[torch.Tensor] = []
            unconditional_values: list[torch.Tensor] = []
            for start in range(0, flat_count, chunk):
                stop = min(start + chunk, flat_count)
                count = stop - start
                sigma = torch.full(
                    (count,), sigma_value, device=current.device, dtype=current.dtype
                )
                noisy = clean_flat[start:stop] + sigma[:, None] * noise_flat[start:stop]
                selected_action = action_flat[start:stop]
                conditional = model(
                    current_flat[start:stop],
                    selected_action,
                    noisy,
                    sigma,
                    torch.ones(count, device=current.device, dtype=current.dtype),
                )
                unconditional = model(
                    current_flat[start:stop],
                    torch.zeros_like(selected_action),
                    noisy,
                    sigma,
                    torch.zeros(count, device=current.device, dtype=current.dtype),
                )
                target = clean_flat[start:stop]
                conditional_values.append(
                    (conditional - target).square().mean(dim=-1).float()
                )
                unconditional_values.append(
                    (unconditional - target).square().mean(dim=-1).float()
                )
            conditional_transition = torch.cat(conditional_values).reshape(*leading[:-1], horizon)
            unconditional_transition = torch.cat(unconditional_values).reshape(*leading[:-1], horizon)
            conditional_sum += conditional_transition.mean(dim=-1).double()
            unconditional_sum += unconditional_transition.mean(dim=-1).double()
    denominator = float(len(SIGMAS) * NOISE_DRAWS)
    rdx = (conditional_sum / denominator).float()
    unconditional = (unconditional_sum / denominator).float()
    ae = torch.log(rdx.double() + LOG_EPSILON) - torch.log(
        unconditional.double() + LOG_EPSILON
    )
    if not torch.isfinite(rdx).all() or not torch.isfinite(ae).all():
        raise RuntimeError("residual endpoint returned non-finite costs")
    return rdx, ae.float(), unconditional


@torch.inference_mode()
def forward_literal_costs(
    scorer: nn.Module,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    batch_size: int | None = None,
) -> torch.Tensor:
    """Return the deterministic-forward residual through an auditable batch path."""

    if trajectory.shape[:-2] != actions.shape[:-2]:
        raise ValueError("forward trajectory/action leading shapes differ")
    current = trajectory[..., :-1, :]
    successor = trajectory[..., 1:, :]
    if current.shape[:-1] != actions.shape[:-1]:
        raise ValueError("forward horizon shape differs")
    mean = torch.as_tensor(
        latent_mean, device=trajectory.device, dtype=trajectory.dtype
    )
    std = torch.as_tensor(latent_std, device=trajectory.device, dtype=trajectory.dtype)
    if mean.shape != trajectory.shape[-1:] or std.shape != trajectory.shape[-1:]:
        raise RuntimeError("forward latent standardizer shape differs")
    if torch.any(std <= 1.0e-6):
        raise RuntimeError("forward latent standardizer is degenerate")
    current = (current - mean) / std
    successor = (successor - mean) / std
    leading = current.shape[:-1]
    flat_count = math.prod(leading)
    chunk = flat_count if batch_size is None else int(batch_size)
    if chunk <= 0:
        raise ValueError("batch size must be positive")
    current_flat = current.reshape(flat_count, current.shape[-1])
    successor_flat = successor.reshape(flat_count, successor.shape[-1])
    action_flat = actions.reshape(flat_count, actions.shape[-1])
    losses: list[torch.Tensor] = []
    for start in range(0, flat_count, chunk):
        stop = min(start + chunk, flat_count)
        prediction = scorer(current_flat[start:stop], action_flat[start:stop])
        losses.append(
            (prediction - successor_flat[start:stop]).square().mean(dim=-1).float()
        )
    transition_cost = torch.cat(losses).reshape(*leading)
    cost = transition_cost.mean(dim=-1)
    if not torch.isfinite(cost).all():
        raise RuntimeError("literal forward cost is non-finite")
    return cost


def build_legacy_dtv_noise_bank(
    *, scorer_seed: int, horizon: int, latent_dim: int
) -> torch.Tensor:
    generator = torch.Generator(device="cpu").manual_seed(int(scorer_seed))
    return torch.randn(
        len(LEGACY_DTV_SIGMAS), horizon, latent_dim, generator=generator
    )


@torch.inference_mode()
def legacy_dtv_costs(
    scorer: ConditionalDiffusionVerifier,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    latent_mean: torch.Tensor,
    latent_std: torch.Tensor,
    noise_bank: torch.Tensor,
    batch_size: int | None = None,
) -> torch.Tensor:
    """Reproduce the frozen v1 raw diffusion-transition-verifier cost."""

    if trajectory.shape[:-2] != actions.shape[:-2]:
        raise ValueError("legacy DTV trajectory/action leading shapes differ")
    current = trajectory[..., :-1, :]
    successor = trajectory[..., 1:, :]
    if current.shape[:-1] != actions.shape[:-1]:
        raise ValueError("legacy DTV horizon shape differs")
    mean = torch.as_tensor(
        latent_mean, device=trajectory.device, dtype=trajectory.dtype
    )
    std = torch.as_tensor(latent_std, device=trajectory.device, dtype=trajectory.dtype)
    if mean.shape != trajectory.shape[-1:] or std.shape != trajectory.shape[-1:]:
        raise RuntimeError("legacy DTV latent standardizer shape differs")
    if torch.any(std <= 1.0e-6):
        raise RuntimeError("legacy DTV latent standardizer is degenerate")
    current = (current - mean) / std
    successor = (successor - mean) / std
    leading = current.shape[:-1]
    horizon, latent_dim = current.shape[-2:]
    if noise_bank.shape != (len(LEGACY_DTV_SIGMAS), horizon, latent_dim):
        raise RuntimeError("legacy DTV noise-bank shape differs")
    flat_count = math.prod(leading)
    chunk = flat_count if batch_size is None else int(batch_size)
    if chunk <= 0:
        raise ValueError("batch size must be positive")
    current_flat = current.reshape(flat_count, latent_dim)
    successor_flat = successor.reshape(flat_count, latent_dim)
    action_flat = actions.reshape(flat_count, actions.shape[-1])
    per_level: list[torch.Tensor] = []
    for level, sigma_value in enumerate(LEGACY_DTV_SIGMAS):
        expanded_noise = noise_bank[level].to(
            device=trajectory.device, dtype=trajectory.dtype
        ).expand(*leading[:-1], horizon, latent_dim)
        noise_flat = expanded_noise.reshape(flat_count, latent_dim)
        losses: list[torch.Tensor] = []
        for start in range(0, flat_count, chunk):
            stop = min(start + chunk, flat_count)
            sigma = torch.full(
                (stop - start,),
                sigma_value,
                device=trajectory.device,
                dtype=trajectory.dtype,
            )
            noisy = successor_flat[start:stop] + sigma[:, None] * noise_flat[start:stop]
            prediction = scorer(
                current_flat[start:stop],
                action_flat[start:stop],
                noisy,
                sigma,
            )
            losses.append(
                (prediction - noise_flat[start:stop]).square().mean(dim=-1).float()
            )
        transition_cost = torch.cat(losses).reshape(*leading)
        per_level.append(transition_cost.mean(dim=-1))
    cost = torch.stack(per_level).mean(dim=0)
    if not torch.isfinite(cost).all():
        raise RuntimeError("legacy DTV cost is non-finite")
    return cost


@torch.inference_mode()
def reachability_literal_costs(
    scorer: TemporalReachabilityHead,
    *,
    trajectory: torch.Tensor,
    goal_embedding: torch.Tensor,
    batch_size: int | None = None,
) -> torch.Tensor:
    """Reproduce the frozen terminal-to-goal learned-reachability cost."""

    if trajectory.ndim != 4:
        raise ValueError("reachability trajectory must have shape (P,C,T,D)")
    terminal = trajectory[..., -1, :]
    pools, candidates, latent_dim = terminal.shape
    if goal_embedding.ndim == 2 and goal_embedding.shape == (pools, latent_dim):
        goal = goal_embedding[:, None, :].expand_as(terminal)
    elif (
        goal_embedding.ndim == 3
        and goal_embedding.shape[0] == pools
        and goal_embedding.shape[-1] == latent_dim
    ):
        if goal_embedding.shape[1] == candidates:
            goal = goal_embedding
        else:
            goal = goal_embedding[:, -1, :][:, None, :].expand_as(terminal)
    elif (
        goal_embedding.ndim == 4
        and goal_embedding.shape[:2] == (pools, candidates)
        and goal_embedding.shape[-1] == latent_dim
    ):
        goal = goal_embedding[..., -1, :]
    else:
        raise RuntimeError("reachability goal-embedding shape differs")
    flat_terminal = terminal.reshape(-1, latent_dim)
    flat_goal = goal.reshape(-1, latent_dim)
    chunk = len(flat_terminal) if batch_size is None else int(batch_size)
    if chunk <= 0:
        raise ValueError("batch size must be positive")
    costs: list[torch.Tensor] = []
    for start in range(0, len(flat_terminal), chunk):
        stop = min(start + chunk, len(flat_terminal))
        costs.append(scorer(flat_terminal[start:stop], flat_goal[start:stop]).float())
    cost = torch.cat(costs).reshape(pools, candidates)
    if not torch.isfinite(cost).all():
        raise RuntimeError("literal reachability cost is non-finite")
    return cost


@torch.inference_mode()
def acid_literal_costs(
    scorer: FlowInverseDynamics,
    *,
    trajectory: torch.Tensor,
    actions: torch.Tensor,
    action_mean: torch.Tensor,
    action_std: torch.Tensor,
    generator: torch.Generator,
    batch_size: int | None = None,
) -> torch.Tensor:
    """Published ACID residual with one independent Gaussian draw per tuple."""

    if trajectory.shape[:-2] != actions.shape[:-2]:
        raise ValueError("ACID trajectory/action leading shapes differ")
    current = trajectory[..., :-1, :]
    successor = trajectory[..., 1:, :]
    if current.shape[:-1] != actions.shape[:-1]:
        raise ValueError("ACID horizon shape differs")
    noise = torch.randn(
        actions.shape,
        generator=generator,
        device="cpu",
        dtype=torch.float32,
    ).to(device=actions.device, dtype=actions.dtype)
    leading = current.shape[:-1]
    flat_count = math.prod(leading)
    chunk = flat_count if batch_size is None else int(batch_size)
    if chunk <= 0:
        raise ValueError("batch size must be positive")
    current_flat = current.reshape(flat_count, current.shape[-1])
    successor_flat = successor.reshape(flat_count, successor.shape[-1])
    noise_flat = noise.reshape(flat_count, noise.shape[-1])
    inferred_chunks: list[torch.Tensor] = []
    for start in range(0, flat_count, chunk):
        stop = min(start + chunk, flat_count)
        inferred_chunks.append(
            scorer.one_step_action(
                current_flat[start:stop],
                successor_flat[start:stop],
                noise_flat[start:stop],
            )
        )
    inferred_standardized = torch.cat(inferred_chunks).reshape(
        *leading, actions.shape[-1]
    )
    mean = torch.as_tensor(action_mean, device=actions.device, dtype=actions.dtype)
    std = torch.as_tensor(action_std, device=actions.device, dtype=actions.dtype)
    if mean.shape != actions.shape[-1:] or std.shape != actions.shape[-1:]:
        raise RuntimeError("ACID action standardizer shape differs")
    inferred = inferred_standardized * std + mean
    cost = (actions - inferred).square().sum(dim=-1).mean(dim=-1)
    if not torch.isfinite(cost).all():
        raise RuntimeError("literal ACID cost is non-finite")
    return cost


class D2CostModel(nn.Module):
    """One-rollout D2 cost wrapper for the frozen closed-loop arms."""

    def __init__(
        self,
        world_model: nn.Module,
        *,
        arm: Arm,
        task: str,
        planner_seed: int,
        scorer: nn.Module | None = None,
        payload: dict[str, Any] | None = None,
        horizon: int = 5,
        record_diagnostics: bool = True,
    ) -> None:
        super().__init__()
        if arm == "b0" and (scorer is not None or payload is not None):
            raise ValueError("B0 must not receive a scorer")
        if arm != "b0" and (scorer is None or payload is None):
            raise ValueError(f"{arm} requires scorer and payload")
        self.rollout_model = SharedRolloutCostModel(
            world_model, arm="b0", horizon=horizon, record_diagnostics=False
        )
        self.arm = arm
        self.task = task
        self.planner_seed = int(planner_seed)
        self.scorer = scorer
        self.payload = payload or {}
        self.horizon = int(horizon)
        self.record_diagnostics = bool(record_diagnostics)
        self.diagnostic_history: list[dict[str, Any]] = []
        self.call_count = 0
        self.lambda_weight = (
            ACID_LAMBDA if arm in {"acid", "reachability"} else DIFFUSION_LAMBDA
        )

        self.register_buffer("residual_noise_bank", torch.empty(0), persistent=True)
        self.register_buffer("legacy_dtv_noise_bank", torch.empty(0), persistent=True)
        if arm in {"rdx", "ae", "ae_shuffled"}:
            seed = int(self.payload["seed"])
            latent_dim = int(self.payload["model_config"]["latent_dim"])
            self.residual_noise_bank = build_residual_noise_bank(
                task=task, scorer_seed=seed, horizon=horizon, latent_dim=latent_dim
            )
        if arm == "dtv":
            seed = int(self.payload["seed"])
            latent_dim = int(self.payload["model_config"]["latent_dim"])
            self.legacy_dtv_noise_bank = build_legacy_dtv_noise_bank(
                scorer_seed=seed, horizon=horizon, latent_dim=latent_dim
            )

    @torch.inference_mode()
    def raw_cost(
        self,
        trajectory: torch.Tensor,
        actions: torch.Tensor,
        goal_embedding: torch.Tensor,
    ) -> torch.Tensor:
        if self.arm == "acid":
            assert isinstance(self.scorer, FlowInverseDynamics)
            generator = torch.Generator(device="cpu").manual_seed(
                acid_noise_seed(
                    self.task,
                    int(self.payload["seed"]),
                    self.planner_seed,
                    self.call_count,
                )
            )
            return acid_literal_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                action_mean=self.payload["acid_action_mean"],
                action_std=self.payload["acid_action_std"],
                generator=generator,
            )
        if self.arm == "forward":
            assert self.scorer is not None
            return forward_literal_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                latent_mean=self.payload["latent_mean"],
                latent_std=self.payload["latent_std"],
            )
        if self.arm == "dtv":
            assert isinstance(self.scorer, ConditionalDiffusionVerifier)
            return legacy_dtv_costs(
                self.scorer,
                trajectory=trajectory,
                actions=actions,
                latent_mean=self.payload["latent_mean"],
                latent_std=self.payload["latent_std"],
                noise_bank=self.legacy_dtv_noise_bank,
            )
        if self.arm == "reachability":
            assert isinstance(self.scorer, TemporalReachabilityHead)
            return reachability_literal_costs(
                self.scorer,
                trajectory=trajectory,
                goal_embedding=goal_embedding,
            )
        if self.arm in {"rdx", "ae", "ae_shuffled"}:
            assert self.scorer is not None
            current, clean = standardized_residual_inputs(trajectory, self.payload)
            rdx, ae, _ = residual_endpoint_costs(
                self.scorer,
                current=current,
                clean=clean,
                actions=actions,
                noise_bank=self.residual_noise_bank,
            )
            return rdx if self.arm == "rdx" else ae
        raise RuntimeError(f"raw cost is unavailable for {self.arm}")

    @torch.inference_mode()
    def get_cost(
        self, info_dict: dict[str, Any], action_candidates: torch.Tensor
    ) -> torch.Tensor:
        goal_cost, trajectory, actions, goal_embedding = self.rollout_model._rollout_once(
            info_dict, action_candidates
        )
        self.call_count += 1
        if self.arm == "b0":
            if self.record_diagnostics:
                self.diagnostic_history.append(
                    {
                        "call": self.call_count,
                        "goal_std": goal_cost.std(dim=1, unbiased=True).cpu().tolist(),
                    }
                )
            return goal_cost
        raw = self.raw_cost(trajectory, actions, goal_embedding)
        if raw.shape != goal_cost.shape:
            raise RuntimeError("D2 raw verifier cost has an unexpected shape")
        goal_spread = goal_cost.std(dim=1, unbiased=True)
        raw_spread = raw.std(dim=1, unbiased=True)
        weight = self.lambda_weight * goal_spread / raw_spread.clamp_min(
            SPREAD_EPSILON
        )
        combined = goal_cost + weight[:, None] * raw
        if not torch.isfinite(combined).all():
            raise RuntimeError("D2 combined cost is non-finite")
        if self.record_diagnostics:
            self.diagnostic_history.append(
                {
                    "call": self.call_count,
                    "goal_std": goal_spread.cpu().tolist(),
                    "verifier_std": raw_spread.cpu().tolist(),
                    "adaptive_weight": weight.cpu().tolist(),
                    "verifier_min": raw.min(dim=1).values.cpu().tolist(),
                }
            )
        return combined


def load_core_scorer(
    checkpoint: Path, *, arm: str, expected_seed: int, device: torch.device
) -> tuple[nn.Module, dict[str, Any], dict[str, Any]]:
    scorer, payload = load_scorer(checkpoint, arm, device)
    if int(payload.get("seed", -1)) != expected_seed:
        raise RuntimeError(f"{arm} checkpoint seed mismatch: {checkpoint}")
    return scorer, payload, {
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "arm": arm,
        "seed": expected_seed,
        "parameter_count": sum(parameter.numel() for parameter in scorer.parameters()),
        "source_manifest_sha256": payload.get("source_manifest_sha256"),
        "model_config": payload.get("model_config"),
    }


def self_test(trainer_module: Any) -> None:
    model = trainer_module.ResidualDiffusionX0Verifier(8, 4, width=32, depth=2)
    trajectory = torch.randn(2, 3, 6, 8)
    actions = torch.randn(2, 3, 5, 4)
    payload = {
        "latent_mean": torch.zeros(8),
        "latent_std": torch.ones(8),
        "residual_mean": torch.zeros(8),
        "residual_std": torch.ones(8),
    }
    current, clean = standardized_residual_inputs(trajectory, payload)
    bank = build_residual_noise_bank(
        task="pusht", scorer_seed=6101, horizon=5, latent_dim=8
    )
    rdx, ae, unconditional = residual_endpoint_costs(
        model,
        current=current,
        clean=clean,
        actions=actions,
        noise_bank=bank,
        batch_size=7,
    )
    if rdx.shape != (2, 3) or ae.shape != (2, 3):
        raise RuntimeError("D2 residual endpoint self-test shape failed")
    if not torch.isfinite(torch.stack((rdx, ae, unconditional))).all():
        raise RuntimeError("D2 residual endpoint self-test finiteness failed")

    class _ForwardProbe(nn.Module):
        def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
            return state + action[..., :1]

    forward = _ForwardProbe()
    forward_full = forward_literal_costs(
        forward,
        trajectory=trajectory,
        actions=actions,
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
    )
    forward_batched = forward_literal_costs(
        forward,
        trajectory=trajectory,
        actions=actions,
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
        batch_size=7,
    )
    if not torch.allclose(forward_full, forward_batched, rtol=1.0e-6, atol=1.0e-6):
        raise RuntimeError("D2 literal forward batching self-test failed")

    legacy_dtv = ConditionalDiffusionVerifier(8, 4, width=32, depth=2)
    legacy_bank = build_legacy_dtv_noise_bank(
        scorer_seed=6101, horizon=5, latent_dim=8
    )
    legacy_full = legacy_dtv_costs(
        legacy_dtv,
        trajectory=trajectory,
        actions=actions,
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
        noise_bank=legacy_bank,
    )
    legacy_batched = legacy_dtv_costs(
        legacy_dtv,
        trajectory=trajectory,
        actions=actions,
        latent_mean=torch.zeros(8),
        latent_std=torch.ones(8),
        noise_bank=legacy_bank,
        batch_size=7,
    )
    if not torch.allclose(legacy_full, legacy_batched, rtol=1.0e-6, atol=1.0e-6):
        raise RuntimeError("D2 legacy DTV batching self-test failed")

    reachability = TemporalReachabilityHead(8, hidden_width=16)
    goal = torch.randn(2, 8)
    reach_full = reachability_literal_costs(
        reachability, trajectory=trajectory, goal_embedding=goal
    )
    reach_batched = reachability_literal_costs(
        reachability,
        trajectory=trajectory,
        goal_embedding=goal,
        batch_size=4,
    )
    if not torch.allclose(reach_full, reach_batched, rtol=1.0e-6, atol=1.0e-6):
        raise RuntimeError("D2 reachability batching self-test failed")

    acid = FlowInverseDynamics(8, 4, width=12, depth=1, heads=3)
    acid_generator = torch.Generator(device="cpu").manual_seed(917)
    acid_cost = acid_literal_costs(
        acid,
        trajectory=trajectory,
        actions=actions,
        action_mean=torch.zeros(4),
        action_std=torch.ones(4),
        generator=acid_generator,
    )
    acid_batched_generator = torch.Generator(device="cpu").manual_seed(917)
    acid_batched_cost = acid_literal_costs(
        acid,
        trajectory=trajectory,
        actions=actions,
        action_mean=torch.zeros(4),
        action_std=torch.ones(4),
        generator=acid_batched_generator,
        batch_size=7,
    )
    if acid_cost.shape != (2, 3) or not torch.isfinite(acid_cost).all():
        raise RuntimeError("D2 literal ACID endpoint self-test failed")
    if not torch.allclose(
        acid_cost, acid_batched_cost, rtol=1.0e-6, atol=1.0e-6
    ):
        raise RuntimeError("D2 literal ACID batching self-test failed")
