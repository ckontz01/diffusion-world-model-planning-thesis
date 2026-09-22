"""Dependency-free CEM/ACID reference kernel; no simulator or checkpoint loader.

Callbacks receive present observations and proposed actions only. The executable
numeric adapter is artificial. Production tensor/batched Le-WM parity is untested.
"""
from dataclasses import dataclass
import hashlib
import math
import random
import statistics
import struct


def finite(xs):
    if not xs or not all(math.isfinite(x) for x in xs):
        raise ValueError('Empty or nonfinite numeric input')


def action_id(action):
    finite(action)
    # Canonical binary64 planner coordinates; normalize signed zero.
    return hashlib.sha256(b''.join(struct.pack('<d', x if x else 0.) for x in action)).hexdigest()


def inverse_consistency(actions, inverse_actions):
    if not actions or len(actions) != len(inverse_actions):
        raise ValueError('Transition count mismatch')
    total = 0.
    for a, b in zip(actions, inverse_actions):
        finite(a); finite(b)
        if len(a) != len(b):
            raise ValueError('Action-coordinate mismatch')
        total += sum((x-y)**2 for x, y in zip(a, b))
    return total / len(actions)


def acid_cost(goal, residual, lam=.07, epsilon=1e-8):
    finite(goal); finite(residual)
    if len(goal) != len(residual) or len(goal) < 2 or lam < 0 or epsilon <= 0:
        raise ValueError('Invalid ACID population/configuration')
    if any(v < 0 for v in residual):
        raise ValueError('Negative inverse residual')
    weight = lam * statistics.stdev(goal) / max(statistics.stdev(residual), epsilon)
    scores = tuple(g + weight*r for g, r in zip(goal, residual))
    finite(scores)
    return scores, weight


@dataclass(frozen=True)
class Solve:
    baseline: tuple
    samples: tuple
    sample_costs: tuple
    weights: tuple
    scored_sequences: int


def cem(observation, score_population, *, seed, dimensions, population=300,
        elites=30, iterations=30, acid=False, lam=.07, support=None):
    """Each native method gets its own solve/RNG; no final-mean extra scoring.

    score_population(obs, actions) -> (goal_costs, inverse_residuals).
    Inverse residuals need not be supplied for vanilla goal-only mode.
    support, when supplied, is an explicit shared coordinate projection.
    """
    if not (dimensions > 0 and iterations > 0 and 1 < elites <= population):
        raise ValueError('Invalid CEM grid')
    rng = random.Random(seed)
    mean, sd = [0.]*dimensions, [1.]*dimensions
    weights = []
    for _ in range(iterations):
        bank = tuple(tuple(rng.gauss(m, s) for m, s in zip(mean, sd)) for _ in range(population))
        if support is not None:
            bank = tuple(tuple(support(a)) for a in bank)
        for a in bank: finite(a)
        goal, residual = score_population(observation, bank)
        finite(goal)
        if len(goal) != population:
            raise ValueError('Cost/action association mismatch')
        costs, weight = acid_cost(goal, residual, lam) if acid else (tuple(goal), 0.)
        weights.append(weight)
        order = sorted(range(population), key=lambda i: (costs[i], i))[:elites]
        mean = [statistics.fmean(bank[i][d] for i in order) for d in range(dimensions)]
        sd = [math.sqrt(statistics.pvariance(bank[i][d] for i in order)) for d in range(dimensions)]
    baseline = tuple(mean) if support is None else tuple(support(mean))
    return Solve(baseline, bank, costs, tuple(weights), population*iterations)


@dataclass(frozen=True)
class Bank:
    actions: tuple
    ids: tuple
    origins: tuple
    duplicate_slots: int


def shortlist(solve, size=8):
    """Exact returned mean + seven lowest-cost distinct final-population chunks.

    No extra sampling. If fewer than eight unique coordinates exist, pad with
    baseline aliases and record them. Ties: original final-population index.
    """
    actions, origins = [solve.baseline], ['returned-final-elite-mean']
    seen = {action_id(solve.baseline)}
    for i in sorted(range(len(solve.samples)), key=lambda j: (solve.sample_costs[j], j)):
        a = solve.samples[i]
        if action_id(a) not in seen:
            actions.append(a); origins.append(f'final-sample-{i}'); seen.add(action_id(a))
        if len(actions) == size: break
    duplicates = size-len(actions)
    while len(actions) < size:
        actions.append(solve.baseline); origins.append('baseline-alias-no-resampling')
    return Bank(tuple(actions), tuple(map(action_id, actions)), tuple(origins), duplicates)


def native_path(start, plan, execute_chunk, max_decisions):
    """Only synthetic callbacks in AV0; separate caller-owned state per policy."""
    obs, trace = start, []
    for _ in range(max_decisions):
        result = plan(obs)
        obs_next, success, terminal = execute_chunk(obs, result.baseline)
        trace.append((obs, result.baseline, obs_next, bool(success)))
        obs = obs_next
        if success or terminal: break
    return trace


def checked_path(start, plan, predict, choose, execute_chunk, max_decisions):
    """Freeze one bank before prediction/checking; checker cannot replace it."""
    obs, trace = start, []
    for _ in range(max_decisions):
        bank = shortlist(plan(obs))
        scores = tuple(predict(obs, bank))
        if len(scores) != 8: raise ValueError('Prediction/action association mismatch')
        # Alias slots do not create new interventions or prediction opportunities.
        scores = tuple(scores[bank.ids.index(identity)] for identity in bank.ids)
        index = choose(scores)
        if type(index) is not int or not 0 <= index < 8: raise ValueError('Invalid selection')
        index = bank.ids.index(bank.ids[index])
        nxt, success, terminal = execute_chunk(obs, bank.actions[index])
        trace.append((obs, bank.ids, index, nxt, bool(success)))
        obs = nxt
        if success or terminal: break
    return trace


def full_budget_success(chunk_success, tail_success):
    return bool(any(chunk_success) or any(tail_success))


class FrozenLatentCost:
    """Explicit Le-WM-shaped port; no model loading or physics entry point.

    observation=(current_latent, fixed_goal_latent). A caller-supplied frozen
    rollout(current, grouped_action) returns H+1 latents, including current.
    inverse(z,z_next,t) returns a planner-coordinate action block; t selects
    the predeclared common IDM noise, never a simulator query. Production
    current-image encoding/tensor decoding must be separately parity-tested.
    """
    def __init__(self, rollout, inverse=None, block_width=10):
        self.rollout=rollout;self.inverse=inverse;self.block_width=block_width

    def __call__(self, observation, bank):
        current, goal = observation
        finite(current);finite(goal)
        costs,residuals=[],[]
        for flat in bank:
            if len(flat)%self.block_width:raise ValueError('Incomplete primitive-action block')
            action=tuple(tuple(flat[t:t+self.block_width]) for t in range(0,len(flat),self.block_width))
            z=self.rollout(current,action)
            if len(z)!=len(action)+1 or tuple(z[0])!=tuple(current):
                raise ValueError('Rollout temporal/initial association')
            if any(len(v)!=len(goal) for v in z):raise ValueError('Latent dimensions')
            for v in z:finite(v)
            costs.append(sum((x-y)**2 for x,y in zip(z[-1],goal)))
            if self.inverse is not None:
                inferred=tuple(tuple(self.inverse(z[t],z[t+1],t)) for t in range(len(action)))
                residuals.append(inverse_consistency(action,inferred))
        return tuple(costs),tuple(residuals)
