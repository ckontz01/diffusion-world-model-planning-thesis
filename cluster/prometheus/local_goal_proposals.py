"""LGP1 preparation: sample-only boundary and explicit common CEM control.

No dataset, checkpoint, environment, job submission or execution entry point.
Arrays are planner-standardized primitive-action blocks [B,K,3,10].
This NumPy reference is not the released BF16 SAGE solver.
"""
from dataclasses import dataclass
import hashlib
import numpy as np


@dataclass(frozen=True)
class Context:
    history: np.ndarray             # [B,3,192], actual history at five-step spacing
    local_goal: np.ndarray          # [B,1,192], one shared generated target
    far_goal: np.ndarray            # [B,1,192]
    lowdim: np.ndarray              # [B,11], state7 then proprio4
    remaining: np.ndarray           # [B], remaining in schedule cycle
    duration: np.ndarray            # [B], exactly 15

    def validate(self):
        b = len(self.history)
        for x, shape in ((self.history, (b,3,192)), (self.local_goal, (b,1,192)),
                         (self.far_goal, (b,1,192)), (self.lowdim, (b,11)),
                         (self.remaining, (b,)), (self.duration, (b,))):
            if np.shape(x) != shape or not np.isfinite(x).all():
                raise ValueError('Nonfinite or mismatched context')
        if b < 1 or (self.duration != 15).any() or (self.remaining < 15).any():
            raise ValueError('Invalid local clock')
        return b


def stream_seed(episode, stage, purpose, seed):
    # Separate proposal consumption from refinement; never an input feature.
    return int.from_bytes(hashlib.sha256(
        f'lgp1|{episode}|{stage}|{purpose}|{seed}'.encode()).digest()[:8], 'little')


def convert_actions(blocks, source_mean, source_std, target_mean, target_std):
    """Normalize -> raw displacement -> destination normalization; no clipping."""
    x = np.asarray(blocks)
    stats = [np.asarray(v) for v in (source_mean, source_std, target_mean, target_std)]
    if x.shape[-2:] != (3,10) or not np.isfinite(x).all():
        raise ValueError('Expected three five-action blocks')
    if any(v.shape != (2,) or not np.isfinite(v).all() for v in stats):
        raise ValueError('Invalid two-axis affine statistics')
    sm, ss, tm, ts = stats
    if (ss <= 0).any() or (ts <= 0).any():
        raise ValueError('Nonpositive action scale')
    return (((x.reshape(*x.shape[:-2],15,2)*ss+sm)-tm)/ts).reshape(x.shape)


def lowdim_from_state(state):
    x = np.asarray(state)
    if x.ndim != 2 or x.shape[-1] != 7 or not np.isfinite(x).all():
        raise ValueError('Raw state7 required')
    return np.concatenate([x, x[:,[0,1,5,6]]], axis=1)


def common_cem(context, sample, cost, *, proposal_rng, refinement_rng,
               candidates=300, rounds=30, elites=30, project=None):
    """Only sample(context,K,rng) is family-specific. Return final elite mean.

    Explicit shared departure from native topk: stable lowest-index elite ties.
    ddof=1, no variance floor, no warm start or prior density. The runtime must
    supply the declared shared raw-action support projection; identity is for
    unconstrained synthetic tests only.
    """
    b = context.validate()
    if not 2 <= elites <= candidates or rounds < 1:
        raise ValueError('Invalid CEM budget')
    bank = np.asarray(sample(context,candidates,proposal_rng))
    expected = (b,candidates,3,10)
    calls = []
    for iteration in range(rounds):
        if bank.shape != expected or not np.isfinite(bank).all():
            raise ValueError('Invalid proposal/refinement bank')
        if project is not None:
            bank = np.asarray(project(bank))
            if bank.shape != expected or not np.isfinite(bank).all():
                raise ValueError('Invalid projected bank')
        values = np.asarray(cost(context,bank))
        if values.shape != (b,candidates) or not np.isfinite(values).all():
            raise ValueError('Invalid shared cost')
        order = np.argsort(values,axis=1,kind='stable')[:,:elites]
        selected = bank[np.arange(b)[:,None],order]
        mean, std = selected.mean(1), selected.std(1,ddof=1)
        calls.append(dict(round=iteration,candidates=candidates,elite_indices=order.copy()))
        if iteration+1 < rounds:
            bank = refinement_rng.standard_normal(expected)*std[:,None]+mean[:,None]
            bank[:,0] = mean
    return mean, calls


def local_target(history, far, lowdim, remaining, generator):
    """Stage-local call, no persistent cache; final stage uses actual far target."""
    rem = np.asarray(remaining)
    b = len(history)
    if rem.shape != (b,) or (rem < 15).any():
        raise ValueError('Invalid remaining clock')
    target = np.asarray(far).copy()
    if target.shape != (b,1,192):
        raise ValueError('Invalid goal representation')
    active = rem > 15
    if active.any():
        target[active] = generator(history[active],far[active],lowdim[active],
                                   rem[active],np.full(active.sum(),15))
    if not np.isfinite(target).all():
        raise ValueError('Nonfinite local target')
    return target


def stage_clock(horizon, elapsed):
    if horizon not in (75,150) or not 0 <= elapsed < 2*horizon or elapsed % 15:
        raise ValueError('Invalid or completed stage')
    return horizon-elapsed%horizon, 2*horizon-elapsed
