"""Models and samplers for frozen E14 long-horizon development."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import torch
from torch import nn


def sinusoidal_embedding(value: torch.Tensor, dimension: int) -> torch.Tensor:
    if value.ndim != 1 or dimension < 4:
        raise ValueError("invalid sinusoidal embedding input")
    half = dimension // 2
    scale = math.log(10_000.0) / max(half - 1, 1)
    frequency = torch.exp(
        -scale * torch.arange(half, device=value.device, dtype=torch.float32)
    )
    phase = value.float()[:, None] * frequency[None]
    result = torch.cat((phase.sin(), phase.cos()), dim=-1)
    if result.shape[1] < dimension:
        result = torch.nn.functional.pad(result, (0, dimension - result.shape[1]))
    return result


class FiLMResidualBlock(nn.Module):
    def __init__(self, width: int) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.film = nn.Linear(width, 2 * width)
        self.input = nn.Linear(width, 2 * width)
        self.output = nn.Linear(2 * width, width)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, value: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        scale, shift = self.film(condition).chunk(2, dim=-1)
        hidden = self.norm(value) * (1.0 + scale) + shift
        hidden = self.output(torch.nn.functional.silu(self.input(hidden)))
        return value + hidden


class VariableConditionEncoder(nn.Module):
    def __init__(
        self,
        *,
        latent_dim: int,
        state_dim: int,
        width: int,
        scalar_embedding_dim: int = 64,
    ) -> None:
        super().__init__()
        self.latent_dim = int(latent_dim)
        self.state_dim = int(state_dim)
        self.width = int(width)
        self.scalar_embedding_dim = int(scalar_embedding_dim)
        input_dim = 3 * latent_dim + state_dim + 2 * scalar_embedding_dim
        self.network = nn.Sequential(
            nn.Linear(input_dim, width),
            nn.SiLU(),
            nn.Linear(width, width),
        )

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
    ) -> torch.Tensor:
        batch = current.shape[0]
        if (
            current.shape != (batch, self.latent_dim)
            or goal.shape != current.shape
            or state.shape != (batch, self.state_dim)
            or delta.shape != (batch,)
            or tau.shape != (batch,)
        ):
            raise ValueError("E14 condition shape differs")
        delta_embedding = sinusoidal_embedding(delta, self.scalar_embedding_dim)
        tau_embedding = sinusoidal_embedding(tau, self.scalar_embedding_dim)
        return self.network(
            torch.cat(
                (
                    current,
                    goal,
                    goal - current,
                    state,
                    delta_embedding,
                    tau_embedding,
                ),
                dim=-1,
            )
        )


class VariableVectorBackbone(nn.Module):
    def __init__(
        self,
        *,
        latent_dim: int,
        state_dim: int,
        output_dim: int,
        width: int = 512,
        depth: int = 4,
        time_embedding_dim: int = 128,
    ) -> None:
        super().__init__()
        if min(latent_dim, state_dim, output_dim, width, depth) <= 0:
            raise ValueError("invalid E14 backbone dimension")
        self.latent_dim = int(latent_dim)
        self.state_dim = int(state_dim)
        self.output_dim = int(output_dim)
        self.width = int(width)
        self.depth = int(depth)
        self.time_embedding_dim = int(time_embedding_dim)
        self.value_input = nn.Linear(output_dim, width)
        self.condition = VariableConditionEncoder(
            latent_dim=latent_dim, state_dim=state_dim, width=width
        )
        self.time = nn.Sequential(
            nn.Linear(time_embedding_dim, width),
            nn.SiLU(),
            nn.Linear(width, width),
        )
        self.blocks = nn.ModuleList([FiLMResidualBlock(width) for _ in range(depth)])
        self.output_norm = nn.LayerNorm(width)

    def forward_features(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
        noisy: torch.Tensor,
        timestep: torch.Tensor,
    ) -> torch.Tensor:
        if noisy.shape != (current.shape[0], self.output_dim):
            raise ValueError("E14 noisy vector shape differs")
        if timestep.shape != (current.shape[0],):
            raise ValueError("E14 diffusion timestep shape differs")
        condition = self.condition(current, goal, state, delta, tau)
        condition = condition + self.time(
            sinusoidal_embedding(timestep, self.time_embedding_dim)
        )
        hidden = self.value_input(noisy) + condition
        for block in self.blocks:
            hidden = block(hidden, condition)
        return self.output_norm(hidden)


class VariableVelocityDiffusion(nn.Module):
    """Classifier-free velocity model for an arbitrary fixed-width vector."""

    def __init__(self, **config: int) -> None:
        super().__init__()
        self.backbone = VariableVectorBackbone(**config)
        self.head = nn.Linear(self.backbone.width, self.backbone.output_dim)
        self.null_goal = nn.Parameter(torch.zeros(self.backbone.latent_dim))

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
        noisy: torch.Tensor,
        timestep: torch.Tensor,
        conditioned: bool | torch.Tensor = True,
    ) -> torch.Tensor:
        if isinstance(conditioned, bool):
            mask = torch.full(
                (current.shape[0],), conditioned, device=current.device, dtype=torch.bool
            )
        elif torch.is_tensor(conditioned) and conditioned.shape == (current.shape[0],):
            mask = conditioned.to(device=current.device, dtype=torch.bool)
        else:
            raise ValueError("E14 classifier-free mask differs")
        null = self.null_goal.to(dtype=goal.dtype)[None].expand_as(goal)
        effective_goal = torch.where(mask[:, None], goal, null)
        features = self.backbone.forward_features(
            current, effective_goal, state, delta, tau, noisy, timestep
        )
        return self.head(features)


class VariableDiagonalGaussian(nn.Module):
    def __init__(self, **config: int) -> None:
        super().__init__()
        self.backbone = VariableVectorBackbone(**config)
        self.query = nn.Parameter(torch.zeros(1, self.backbone.output_dim))
        self.head = nn.Linear(self.backbone.width, 2 * self.backbone.output_dim)

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch = current.shape[0]
        query = self.query.expand(batch, -1)
        timestep = torch.zeros(batch, device=current.device, dtype=torch.long)
        features = self.backbone.forward_features(
            current, goal, state, delta, tau, query, timestep
        )
        mean, log_std = self.head(features).chunk(2, dim=-1)
        return mean, log_std.clamp(-5.0, 2.0)


@dataclass(frozen=True)
class CosineSchedule:
    alpha_bar: torch.Tensor

    @classmethod
    def build(cls, steps: int = 100, offset: float = 0.008) -> "CosineSchedule":
        if steps <= 1 or offset < 0:
            raise ValueError("invalid E14 diffusion schedule")
        point = torch.linspace(0, steps, steps + 1, dtype=torch.float64)
        cumulative = torch.cos(
            ((point / steps + offset) / (1.0 + offset)) * math.pi / 2.0
        ).square()
        cumulative = cumulative / cumulative[0]
        beta = (1.0 - cumulative[1:] / cumulative[:-1]).clamp(1.0e-5, 0.999)
        return cls(torch.cumprod(1.0 - beta, dim=0).float())


def velocity_target(clean: torch.Tensor, noise: torch.Tensor, alpha: torch.Tensor) -> torch.Tensor:
    if clean.shape != noise.shape or alpha.shape != (clean.shape[0], 1):
        raise ValueError("E14 velocity-target shape differs")
    return alpha.sqrt() * noise - (1.0 - alpha).sqrt() * clean


@torch.inference_mode()
def velocity_ddim_sample(
    model: VariableVelocityDiffusion,
    *,
    current: torch.Tensor,
    goal: torch.Tensor,
    state: torch.Tensor,
    delta: torch.Tensor,
    tau: torch.Tensor,
    initial_noise: torch.Tensor,
    active_mask: torch.Tensor,
    schedule: CosineSchedule,
    evaluations: int = 5,
    guidance_scale: float = 1.5,
) -> torch.Tensor:
    """Deterministic velocity-DDIM sampling with exact inactive-dimension masking."""

    batch, count, output_dim = initial_noise.shape
    if (
        current.shape[0] != batch
        or goal.shape != current.shape
        or state.shape[0] != batch
        or delta.shape != (batch,)
        or tau.shape != (batch,)
        or active_mask.shape != (batch, output_dim)
        or output_dim != model.backbone.output_dim
        or not 1 <= evaluations <= len(schedule.alpha_bar)
    ):
        raise ValueError("E14 velocity sampler input shape differs")
    value = initial_noise * active_mask[:, None].to(initial_noise.dtype)
    indices = torch.linspace(
        len(schedule.alpha_bar) - 1,
        0,
        evaluations,
        device=value.device,
        dtype=torch.float64,
    ).round().long()
    indices = torch.unique_consecutive(indices)
    expanded = lambda tensor: tensor[:, None].expand(batch, count, *tensor.shape[1:]).reshape(
        batch * count, *tensor.shape[1:]
    )
    flat_current = expanded(current)
    flat_goal = expanded(goal)
    flat_state = expanded(state)
    flat_delta = expanded(delta)
    flat_tau = expanded(tau)
    flat_mask = expanded(active_mask).to(value.dtype)
    alpha_bar = schedule.alpha_bar.to(device=value.device, dtype=value.dtype)
    for position, index in enumerate(indices):
        flat_value = value.reshape(batch * count, output_dim)
        timestep = torch.full(
            (batch * count,), int(index), device=value.device, dtype=torch.long
        )
        if guidance_scale == 0.0:
            velocity = model(
                flat_current,
                flat_goal,
                flat_state,
                flat_delta,
                flat_tau,
                flat_value,
                timestep,
                conditioned=False,
            )
        else:
            unconditional = model(
                flat_current,
                flat_goal,
                flat_state,
                flat_delta,
                flat_tau,
                flat_value,
                timestep,
                conditioned=False,
            )
            conditional = model(
                flat_current,
                flat_goal,
                flat_state,
                flat_delta,
                flat_tau,
                flat_value,
                timestep,
                conditioned=True,
            )
            velocity = unconditional + guidance_scale * (conditional - unconditional)
        velocity = velocity * flat_mask
        alpha = alpha_bar[index]
        clean = alpha.sqrt() * flat_value - (1.0 - alpha).sqrt() * velocity
        noise = (1.0 - alpha).sqrt() * flat_value + alpha.sqrt() * velocity
        if position + 1 < len(indices):
            next_alpha = alpha_bar[indices[position + 1]]
            flat_value = next_alpha.sqrt() * clean + (1.0 - next_alpha).sqrt() * noise
        else:
            flat_value = clean
        value = flat_value.reshape(batch, count, output_dim)
        value = value * active_mask[:, None].to(value.dtype)
    if not torch.isfinite(value).all():
        raise RuntimeError("E14 velocity sampler produced non-finite values")
    return value


class TypedTransformerCondition(nn.Module):
    """Five typed tokens shared by the disclosed SAGE reconstruction."""

    def __init__(self, *, latent_dim: int, state_dim: int, width: int = 512) -> None:
        super().__init__()
        self.latent_dim = int(latent_dim)
        self.state_dim = int(state_dim)
        self.width = int(width)
        self.current = nn.Linear(latent_dim, width)
        self.goal = nn.Linear(latent_dim, width)
        self.state = nn.Linear(state_dim, width)
        self.delta = nn.Linear(64, width)
        self.tau = nn.Linear(64, width)
        self.types = nn.Parameter(torch.zeros(5, width))
        nn.init.normal_(self.types, std=0.02)

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
    ) -> torch.Tensor:
        batch = current.shape[0]
        if (
            current.shape != (batch, self.latent_dim)
            or goal.shape != current.shape
            or state.shape != (batch, self.state_dim)
            or delta.shape != (batch,)
            or tau.shape != (batch,)
        ):
            raise ValueError("E14 SAGE condition shape differs")
        tokens = torch.stack(
            (
                self.current(current),
                self.goal(goal),
                self.state(state),
                self.delta(sinusoidal_embedding(delta, 64)),
                self.tau(sinusoidal_embedding(tau, 64)),
            ),
            dim=1,
        )
        return tokens + self.types[None]


class SAGESubgoalGenerator(nn.Module):
    def __init__(
        self,
        *,
        latent_dim: int,
        state_dim: int,
        width: int = 512,
        depth: int = 4,
        heads: int = 8,
        feedforward_dim: int = 2816,
    ) -> None:
        super().__init__()
        self.condition = TypedTransformerCondition(
            latent_dim=latent_dim, state_dim=state_dim, width=width
        )
        layer = nn.TransformerDecoderLayer(
            d_model=width,
            nhead=heads,
            dim_feedforward=feedforward_dim,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.decoder = nn.TransformerDecoder(layer, num_layers=depth, norm=nn.LayerNorm(width))
        self.query = nn.Linear(latent_dim, width)
        self.output = nn.Linear(width, latent_dim)

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
    ) -> torch.Tensor:
        memory = self.condition(current, goal, state, delta, tau)
        query = self.query(goal)[:, None]
        residual = self.output(self.decoder(query, memory)[:, 0])
        return goal + residual


class SAGEOptionPrior(nn.Module):
    def __init__(
        self,
        *,
        latent_dim: int,
        state_dim: int,
        primitive_action_dim: int,
        width: int = 512,
        depth: int = 3,
        heads: int = 8,
        feedforward_dim: int = 2048,
        modes: int = 8,
        action_blocks: int = 5,
        block_size: int = 5,
    ) -> None:
        super().__init__()
        self.primitive_action_dim = int(primitive_action_dim)
        self.modes = int(modes)
        self.action_blocks = int(action_blocks)
        self.block_size = int(block_size)
        self.condition = TypedTransformerCondition(
            latent_dim=latent_dim, state_dim=state_dim, width=width
        )
        self.local = nn.Linear(latent_dim, width)
        self.local_type = nn.Parameter(torch.zeros(width))
        layer = nn.TransformerDecoderLayer(
            d_model=width,
            nhead=heads,
            dim_feedforward=feedforward_dim,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.decoder = nn.TransformerDecoder(layer, num_layers=depth, norm=nn.LayerNorm(width))
        self.queries = nn.Parameter(torch.zeros(action_blocks, width))
        head_dim = modes * block_size * primitive_action_dim
        self.mean_head = nn.Linear(width, head_dim)
        self.log_std_head = nn.Linear(width, head_dim)
        self.mode_head = nn.Linear(width, modes)
        nn.init.normal_(self.queries, std=0.02)
        nn.init.normal_(self.local_type, std=0.02)

    @property
    def action_horizon(self) -> int:
        return self.action_blocks * self.block_size

    def forward(
        self,
        current: torch.Tensor,
        goal: torch.Tensor,
        local: torch.Tensor,
        state: torch.Tensor,
        delta: torch.Tensor,
        tau: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        memory = self.condition(current, goal, state, delta, tau)
        local_token = self.local(local) + self.local_type
        memory = torch.cat((memory, local_token[:, None]), dim=1)
        query = self.queries[None].expand(current.shape[0], -1, -1)
        decoded = self.decoder(query, memory)
        shape = (
            current.shape[0],
            self.action_blocks,
            self.modes,
            self.block_size,
            self.primitive_action_dim,
        )
        means = self.mean_head(decoded).reshape(shape).permute(0, 2, 1, 3, 4)
        log_stds = self.log_std_head(decoded).reshape(shape).permute(0, 2, 1, 3, 4)
        means = means.reshape(current.shape[0], self.modes, self.action_horizon, self.primitive_action_dim)
        log_stds = log_stds.reshape_as(means).clamp(-5.0, 2.0)
        logits = self.mode_head(decoded.mean(dim=1))
        return logits, means, log_stds


def trajectory_gmm_nll(
    logits: torch.Tensor,
    means: torch.Tensor,
    log_stds: torch.Tensor,
    target: torch.Tensor,
    active_mask: torch.Tensor,
) -> torch.Tensor:
    batch, modes, horizon, action_dim = means.shape
    if (
        logits.shape != (batch, modes)
        or log_stds.shape != means.shape
        or target.shape != (batch, horizon, action_dim)
        or active_mask.shape != (batch, horizon)
    ):
        raise ValueError("E14 GMM NLL shape differs")
    mask = active_mask[:, None, :, None].to(means.dtype)
    standardized = (target[:, None] - means) / log_stds.exp()
    element = 0.5 * standardized.square() + log_stds + 0.5 * math.log(2.0 * math.pi)
    log_probability = -(element * mask).sum(dim=(-1, -2))
    mixture = torch.log_softmax(logits, dim=-1) + log_probability
    return -torch.logsumexp(mixture, dim=-1)


@torch.inference_mode()
def sample_trajectory_gmm(
    logits: torch.Tensor,
    means: torch.Tensor,
    log_stds: torch.Tensor,
    *,
    count: int,
    active_mask: torch.Tensor,
    generator: torch.Generator,
) -> torch.Tensor:
    batch, modes, horizon, action_dim = means.shape
    if count <= 0 or active_mask.shape != (batch, horizon):
        raise ValueError("E14 GMM sampler shape differs")
    if str(generator.device) != "cpu":
        raise ValueError("E14 GMM sampling requires a deterministic CPU generator")
    # CUDA multinomial calls a cumsum kernel that PyTorch 2.5 marks as
    # nondeterministic.  The bank is small, so draw both categorical modes and
    # Gaussian noise on CPU, then transfer once.  This keeps strict determinism
    # without disabling the global safeguard used by every scientific job.
    probabilities_cpu = torch.softmax(logits.float(), dim=-1).cpu()
    mode_cpu = torch.multinomial(
        probabilities_cpu, count, replacement=True, generator=generator
    )
    mode = mode_cpu.to(device=means.device)
    batch_index = torch.arange(batch, device=means.device)[:, None]
    selected_mean = means[batch_index, mode]
    selected_std = log_stds[batch_index, mode].exp()
    noise = torch.randn(
        selected_mean.shape,
        device="cpu",
        dtype=means.dtype,
        generator=generator,
    ).to(device=means.device)
    samples = selected_mean + selected_std * noise
    samples = samples * active_mask[:, None, :, None].to(samples.dtype)
    if not torch.isfinite(samples).all():
        raise RuntimeError("E14 GMM sampler produced non-finite values")
    return samples


Endpoint = Literal["vad", "cvd"]


def endpoint_output_dim(
    endpoint: Endpoint, *, latent_dim: int, primitive_action_dim: int, horizon: int = 25
) -> int:
    action_dim = horizon * primitive_action_dim
    if endpoint == "vad":
        return action_dim
    if endpoint == "cvd":
        return latent_dim + action_dim
    raise ValueError(f"unknown E14 endpoint: {endpoint}")


def endpoint_active_mask(
    endpoint: Endpoint,
    tau: torch.Tensor,
    *,
    latent_dim: int,
    primitive_action_dim: int,
    horizon: int = 25,
) -> torch.Tensor:
    action = (
        torch.arange(horizon, device=tau.device)[None, :] < tau[:, None]
    )[:, :, None].expand(-1, -1, primitive_action_dim).reshape(tau.shape[0], -1)
    if endpoint == "vad":
        return action
    if endpoint == "cvd":
        latent = torch.ones(tau.shape[0], latent_dim, device=tau.device, dtype=torch.bool)
        return torch.cat((latent, action), dim=-1)
    raise ValueError(f"unknown E14 endpoint: {endpoint}")
