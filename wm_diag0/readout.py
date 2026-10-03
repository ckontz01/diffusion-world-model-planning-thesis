"""One fixed standardized linear ridge readout, dual form; artificial fitting only."""
from dataclasses import dataclass
import numpy as np
from .core import array_id, digest, frozen


def check_roles(fit, validation, diagnostic):
    roles = [set(x) for x in (fit, validation, diagnostic)]
    if any(len(a) != len(b) for a,b in zip(roles,(fit,validation,diagnostic))):
        raise ValueError('Duplicate parent role')
    if any(roles[i] & roles[j] for i,j in ((0,1),(0,2),(1,2))):
        raise ValueError('Whole-parent leakage')
    if not all(roles):
        raise ValueError('Empty role')


@dataclass(frozen=True)
class Ridge:
    contract: object
    task: str
    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray
    intercept: np.ndarray
    fit_parent_ids: tuple
    alpha: float = 1.0

    @property
    def identity(self):
        return digest({'contract': self.contract.identity, 'task': self.task,
                       'fit_parents': self.fit_parent_ids, 'alpha': self.alpha,
                       'arrays': [array_id(x) for x in (self.mean, self.scale, self.weights, self.intercept)]})

    def decode(self, values):
        if tuple(values.shape[-len(self.contract.feature_shape):]) != self.contract.feature_shape:
            raise ValueError('Native feature layout')
        x = np.asarray(values, dtype=np.float64).reshape(-1, self.mean.size)
        return ((x-self.mean)/self.scale) @ self.weights + self.intercept

    def __call__(self, features, goal):
        if features.contract != self.contract:
            raise ValueError('Readout contract mismatch')
        # Same endpoint-only scoring and normalization in P1 and O1.
        p, g = self.decode(features.values[:, -1]), self.decode(np.asarray(goal))[0]
        return task_margin(self.task, p, g)


def fit_artificial(features, coordinates, parents, roles, contract, task, *, domain):
    if domain != 'artificial':
        raise PermissionError('Research fitting disabled, including precomputed real features')
    check_roles(*roles)
    x = np.asarray(features, dtype=np.float64)
    y = np.asarray(coordinates, dtype=np.float64)
    nout = {'pusht': 6, 'reacher': 4}[task]
    if x.shape[1:] != contract.feature_shape or y.shape != (len(x), nout) or len(parents) != len(x):
        raise ValueError('Fit shapes')
    if not set(parents) <= set(roles[0]) or len(x) < 2 or len(x) > 256:
        raise ValueError('Permitted fitting parents/256-frame limit')
    array_id(x); array_id(y)
    x = x.reshape(len(x), -1)
    mean, scale = x.mean(0), x.std(0)
    scale = np.where(scale < 1e-6, 1.0, scale)
    z = (x-mean)/scale
    intercept = y.mean(0)
    # Objective mean squared residual + alpha*||W||²; intercept unpenalized.
    dual = np.linalg.solve(z@z.T + len(z)*np.eye(len(z)), y-intercept)
    w = z.T@dual
    return Ridge(contract, task, frozen(mean), frozen(scale), frozen(w), frozen(intercept),
                 tuple(sorted(set(parents))))


def unit_pair(pair):
    n = np.linalg.norm(pair, axis=-1, keepdims=True)
    # Fixed weak-readout convention, no cell-dependent renormalization.
    return np.divide(pair, n, out=np.broadcast_to([1., 0.], pair.shape).copy(), where=n > 1e-8)


def task_margin(task, p, g):
    if task == 'pusht':
        # Native eval_state uses ONE joint 4-coordinate norm, not separate
        # agent/object thresholds or object-only progress.
        position = np.linalg.norm(p[:, :4]-g[:4], axis=1)/20.
        a, b = unit_pair(p[:, 4:6]), unit_pair(g[4:6])
        angle = np.abs(np.arctan2(a[:,1]*b[0]-a[:,0]*b[1], a@b))/(np.pi/9)
        return np.maximum(position, angle)
    if task == 'reacher':
        # Both joint angles, circular distance; not fingertip-only distance.
        # Native raw-qpos criterion remains a separate endpoint; see protocol.
        a, b = unit_pair(p.reshape(-1,2,2)), unit_pair(g.reshape(2,2))
        cross = a[:,:,1]*b[:,0]-a[:,:,0]*b[:,1]
        dot = (a*b).sum(-1)
        return np.max(np.abs(np.arctan2(cross,dot))/.05, axis=1)
    raise ValueError(task)


def realized_quality(readout, values, targets):
    estimate = readout.decode(values)
    targets = np.asarray(targets)
    if estimate.shape != targets.shape:
        raise ValueError('Validation shapes')
    # Training-state coordinates only; this cannot tune or refit the readout.
    return {'coordinate_mae': np.mean(np.abs(estimate-targets), axis=0).tolist(),
            'coordinate_rmse': np.sqrt(np.mean((estimate-targets)**2,axis=0)).tolist()}
