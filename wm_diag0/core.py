"""Pure-array fixed-bank interventions; no torch, data loader or simulator imports."""
from dataclasses import dataclass
import hashlib
import json
from typing import Protocol
import numpy as np


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def array_id(a):
    a = np.asarray(a)
    if a.dtype.hasobject or not np.isfinite(a).all():
        raise ValueError('Object/nonfinite array')
    return hashlib.sha256(json.dumps([a.dtype.str, list(a.shape)]).encode()
                          + a.tobytes(order='C')).hexdigest()


def frozen(a, dtype=None):
    out = np.array(a, dtype=dtype, copy=True, order='C')
    array_id(out)
    out.flags.writeable = False
    return out


@dataclass(frozen=True)
class Candidate:
    actions: np.ndarray
    origin: str
    predicted_cost: float | None

    @property
    def identity(self):
        return array_id(self.actions)


@dataclass(frozen=True)
class Bank:
    candidates: tuple
    native_index: int
    trace_digest: str

    @property
    def identity(self):
        return digest({'actions': [c.identity for c in self.candidates],
                       'native': self.native_index, 'trace': self.trace_digest})


def capture_bank(native, trace_actions, trace_costs, maximum=16):
    """Native return + 7 strongest + 8 nonwinning quantiles; no labels accepted.

    Native is slot zero even if final elite mean was not a sampled candidate.
    Trace is flattened in iteration/slot order; exact duplicates are skipped.
    If fewer unique alternatives exist, retain a smaller bank, never resample.
    """
    native = frozen(native)
    actions = np.asarray(trace_actions)
    costs = np.asarray(trace_costs, dtype=np.float64)
    if maximum != 16 or actions.ndim != native.ndim + 1 or actions.shape[1:] != native.shape:
        raise ValueError('Declared 16-chunk trace shape')
    if costs.shape != (len(actions),) or not np.isfinite(costs).all():
        raise ValueError('Finite trace costs required')
    order = sorted(range(len(actions)), key=lambda i: (float(costs[i]), i))
    unique, seen = [], {array_id(native)}
    for i in order:
        aid = array_id(actions[i])
        if aid not in seen:
            unique.append(i)
            seen.add(aid)
    strong = unique[:7]
    rest = unique[7:]
    # Fixed evenly spaced order-statistic alternatives, including the worst.
    q = sorted(set(np.linspace(0, len(rest)-1, min(8, len(rest))).astype(int))) if rest else []
    picked = strong + [rest[i] for i in q]
    candidates = (Candidate(native, 'native_return', None),) + tuple(
        Candidate(frozen(actions[i]), f'trace:{i}', float(costs[i])) for i in picked)
    return Bank(candidates, 0, digest({'actions': array_id(actions), 'costs': array_id(costs)}))


@dataclass(frozen=True)
class FeatureContract:
    backbone: str
    checkpoint_sha256: str
    preprocessing_sha256: str
    feature_shape: tuple
    positions: tuple
    history_length: int
    native_score_id: str

    @property
    def identity(self):
        return digest(self.__dict__)


@dataclass(frozen=True)
class Features:
    values: np.ndarray  # [candidate, sampling time, *native feature shape]
    contract: FeatureContract
    bank_id: str
    source_id: str
    kind: str

    def validate(self, bank):
        expected = (len(bank.candidates), len(self.contract.positions), *self.contract.feature_shape)
        if self.values.shape != expected or self.bank_id != bank.identity:
            raise ValueError('Action/time/native-layout binding mismatch')
        if self.kind not in ('predicted', 'realized'):
            raise ValueError('Consequence kind')
        array_id(self.values)


class BackboneAdapter(Protocol):
    contract: FeatureContract
    def encode(self, visual_history: np.ndarray) -> np.ndarray: ...
    def predict(self, visual_history: np.ndarray, bank: Bank) -> Features: ...
    def original_score(self, consequences: Features, goal_features: np.ndarray) -> np.ndarray: ...


class ResearchBackend:
    """Exact blocked entry point, not a launchable campaign or model loader."""
    def __init__(self, *args, **kwargs):
        raise PermissionError('WM-DIAG0 research disabled: artifact/role/runtime binding and separate execution instruction required')


def aligned_realized(observed, positions, terminal_step=None):
    """Index primitive-action endpoints. Absorb last real visual feature only.

    observed contains root at index zero and every ACTUAL step. No physics is
    invented after terminal. Predicted cells are never given terminal_step.
    """
    observed = np.asarray(observed)
    if not positions or tuple(sorted(set(positions))) != tuple(positions) or min(positions) < 1:
        raise ValueError('Strictly increasing positive sampling positions')
    if terminal_step is not None and (terminal_step < 0 or terminal_step != len(observed)-1):
        raise ValueError('Terminal must be last actual observation')
    if terminal_step is None and max(positions) >= len(observed):
        raise ValueError('Missing realized sampling position')
    return frozen(np.stack([observed[min(p, terminal_step)] if terminal_step is not None
                            else observed[p] for p in positions]))


def native_terminal_mse(features, goal):
    """Array implementation only for a separately authenticated terminal-MSE S0.

    It preserves all patches; it does not mean-pool tokens or claim that an
    uninspected DINO release uses this objective.
    """
    if np.asarray(goal).shape != features.contract.feature_shape:
        raise ValueError('Own-backbone goal feature shape')
    d = features.values[:, -1] - goal
    return np.mean(d*d, axis=tuple(range(1, d.ndim)))


def native_terminal_score(features, goal):
    if np.asarray(goal).shape != features.contract.feature_shape:
        raise ValueError('Own-backbone goal feature shape')
    d = features.values[:, -1] - goal
    axes = tuple(range(1,d.ndim))
    if features.contract.native_score_id == 'terminal_sum':
        return np.sum(d*d,axis=axes)
    if features.contract.native_score_id == 'terminal_mse':
        return np.mean(d*d,axis=axes)
    raise ValueError('Unbound native score reduction')


@dataclass(frozen=True)
class Selection:
    bank_id: str
    source_id: str
    contract_id: str
    goal_id: str
    s1_id: str
    choices: tuple
    cost_ids: tuple

    @property
    def identity(self):
        return digest(self.__dict__)


def select_four(bank, predicted, realized, goal, s0, s1):
    predicted.validate(bank)
    realized.validate(bank)
    if predicted.kind != 'predicted' or realized.kind != 'realized':
        raise ValueError('Matrix rows')
    if predicted.contract != realized.contract or predicted.source_id != realized.source_id:
        raise ValueError('Own-backbone/source/normalization mismatch')
    if s1.contract != predicted.contract:
        raise ValueError('Cross-backbone readout')
    # Tail outcomes are absent from the signature, and costs are sealed before
    # downstream outcome files may be joined.
    costs = [np.asarray(f(x, goal), dtype=np.float64) for x, f in
             ((predicted, s0), (predicted, s1), (realized, s0), (realized, s1))]
    if any(c.shape != (len(bank.candidates),) or not np.isfinite(c).all() for c in costs):
        raise ValueError('One finite cost per candidate required')
    return Selection(bank.identity, predicted.source_id, predicted.contract.identity,
                     array_id(goal), s1.identity, tuple(int(np.argmin(c)) for c in costs),
                     tuple(array_id(c) for c in costs))
