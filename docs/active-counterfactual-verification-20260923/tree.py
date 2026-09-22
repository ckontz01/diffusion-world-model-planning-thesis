"""Explicit pre-observation tree. No simulator or historical planner import."""
from dataclasses import dataclass, field
import hashlib
import numpy as np


def finite(x):
    a = np.asarray(x, dtype=np.float64)
    if not a.size or not np.isfinite(a).all(): raise ValueError('Empty/nonfinite array')
    return a


def identity(x):
    a = finite(x).copy(); a[a == 0] = 0
    return hashlib.sha256(a.astype('<f8').tobytes()).hexdigest()


def tie_argmax(values, keys):
    v = finite(values)
    if len(v) != len(keys): raise ValueError('Tie key association')
    return min(range(len(v)), key=lambda i: (-float(v[i]), keys[i]))


@dataclass
class Ledger:
    rollout_calls: int = 0
    sequences: int = 0
    latent_transitions: int = 0
    physical_steps: int = 0
    observations: int = 0
    integration_responses: int = 0
    outcome_queries: int = 0
    prefix_planning_calls: int = 0
    cem_solves: int = 0
    learned_module_forward_calls: int = 0
    prior_candidate_predictions: int = 0

    def charge_rollout(self, n, steps):
        self.rollout_calls += 1; self.sequences += n; self.latent_transitions += n*steps
        if self.sequences > 150000 or self.latent_transitions > 450000:
            raise RuntimeError('Per-episode search cap exceeded')


class FrozenPort:
    """Already-supplied frozen latent rollout; never loads a model or physics.

    rollout(current[D], normalized[N,3,10]) -> [N,4,D], current first.
    This exactly matches the inspected horizon+1 latent/action-block association.
    Real image/tensor loading is deliberately not enabled by this preparation.
    """
    mean = np.array([-.007812564379916172,.006860687229453032])
    scale = np.array([.20846744284501714,.20674862637362224])

    def __init__(self, current, goal, rollout, ledger):
        self.current = finite(current).copy(); self.goal = finite(goal).copy()
        self.rollout = rollout; self.ledger = ledger

    def evaluate(self, plans):
        x = finite(plans)
        if x.ndim != 3 or x.shape[1:] != (15,2) or np.max(abs(x)) > 1:
            raise ValueError('Expected physical [N,15,2] in Box')
        self.ledger.charge_rollout(len(x),3)
        z = finite(self.rollout(self.current.copy(), ((x-self.mean)/self.scale).reshape(len(x),3,10)))
        if z.shape != (len(x),4,len(self.current)) or not np.all(z[:,0] == self.current):
            raise ValueError('Frozen rollout temporal identity')
        cost = np.sum((z[:,-1]-self.goal)**2,axis=-1)
        return cost, z


@dataclass(frozen=True)
class Solve:
    baseline: np.ndarray
    proposals: np.ndarray
    costs: np.ndarray


def cem(port, rng, *, prefix=None, population=300, elites=30, rounds=30):
    if not (1 < elites <= population <= 300 and 1 <= rounds <= 30): raise ValueError('CEM bounds')
    start = 0 if prefix is None else 5
    if prefix is not None and finite(prefix).shape != (5,2): raise ValueError('Fixed prefix shape')
    port.ledger.cem_solves+=1
    if prefix is not None:port.ledger.prefix_planning_calls+=1
    mean = np.zeros((15-start,2)); sd = np.ones_like(mean)
    for _ in range(rounds):
        normal = rng.normal(size=(population,15-start,2))*sd+mean
        physical = np.clip(normal*port.scale+port.mean,-1,1)
        bank = physical if start == 0 else np.concatenate((np.broadcast_to(prefix,(population,5,2)),physical),axis=1)
        costs,_ = port.evaluate(bank)
        order = np.argsort(costs,kind='stable')[:elites]
        elite = (physical[order]-port.mean)/port.scale
        mean,sd = elite.mean(0),elite.std(0,ddof=0)
    returned = np.clip(mean*port.scale+port.mean,-1,1)
    if start: returned = np.concatenate((prefix,returned))
    return Solve(returned.copy(),bank.copy(),costs.copy())


@dataclass(frozen=True)
class Node:
    prefix: np.ndarray
    suffixes: tuple
    predicted_prefix: np.ndarray
    predicted_terminals: tuple
    origins: tuple


@dataclass(frozen=True)
class Tree:
    nodes: tuple
    baseline_plan: np.ndarray
    duplicates_skipped: int
    source_clock: int = 0

    def validate(self):
        if self.source_clock != 0 or not 1 <= len(self.nodes) <= 4: raise ValueError('Initial-only tree')
        seen = set()
        for node in self.nodes:
            if finite(node.prefix).shape != (5,2) or not 1 <= len(node.suffixes) <= 4: raise ValueError('Tree shape')
            if identity(node.prefix) in seen: raise ValueError('Duplicate prefix')
            seen.add(identity(node.prefix)); suffix_seen=set()
            for suffix in node.suffixes:
                if finite(suffix).shape != (10,2) or identity(suffix) in suffix_seen: raise ValueError('Duplicate/malformed suffix')
                suffix_seen.add(identity(suffix))
            if len(node.predicted_terminals) != len(node.suffixes): raise ValueError('Feature association')
        if not np.array_equal(np.concatenate((self.nodes[0].prefix,self.nodes[0].suffixes[0])),self.baseline_plan):
            raise ValueError('Baseline sequence changed')
        return self


def construct_tree(port, baseline, *, seed=94001, population=300, elites=30, rounds=30):
    """Baseline first; other prefixes ranked by original final cost then index.

    Four independent suffix-constrained CEM solves, all BEFORE observation.
    Deduplicate exact physical bytes, never approximate prefixes or pad aliases.
    Returned constrained mean then final-cost/index order; original baseline first.
    Missing unique slots remain absent. No candidate is regenerated after response.
    """
    if baseline.baseline.shape != (15,2): raise ValueError('Baseline length')
    prefixes = [baseline.baseline[:5].copy()]; seen={identity(prefixes[0])}; skipped=0
    for i in np.argsort(baseline.costs,kind='stable'):
        p=baseline.proposals[i,:5]
        if identity(p) in seen: skipped+=1; continue
        prefixes.append(p.copy()); seen.add(identity(p))
        if len(prefixes)==4: break
    nodes=[]
    for pindex,prefix in enumerate(prefixes):
        # Substream keyed to prefix bytes, not slot numbering or outcomes.
        key=int(identity(prefix)[:8],16)
        solved=cem(port,np.random.default_rng(np.random.SeedSequence([seed,key])),prefix=prefix,
                   population=population,elites=elites,rounds=rounds)
        candidates=[]
        if pindex==0: candidates.append((baseline.baseline[5:].copy(),'unmodified-baseline'))
        candidates.append((solved.baseline[5:].copy(),'constrained-final-elite-mean'))
        candidates.extend((solved.proposals[i,5:].copy(),f'constrained-final-sample-{i}')
                          for i in np.argsort(solved.costs,kind='stable'))
        unique=[]; origins=[]; suffix_seen=set()
        for suffix,origin in candidates:
            key=identity(suffix)
            if key in suffix_seen: skipped+=1; continue
            unique.append(suffix); origins.append(origin); suffix_seen.add(key)
            if len(unique)==4:break
        nodes.append((prefix,tuple(unique),tuple(origins)))
    plans=np.stack([np.concatenate((p,a)) for p,aa,_ in nodes for a in aa])
    _,features=port.evaluate(plans)  # charged, includes otherwise-unscored baseline mean
    result=[]; j=0
    for p,aa,origins in nodes:
        z=features[j:j+len(aa)];j+=len(aa)
        if not np.all(z[:,1]==z[0,1]):raise ValueError('Future suffix changed predicted physical prefix')
        result.append(Node(p,aa,z[0,1].copy(),tuple(v[-1].copy() for v in z),origins))
    tree=Tree(tuple(result),baseline.baseline.copy(),skipped).validate()
    # Prevent accidental mutation of preconstructed candidates and predictions.
    for node in tree.nodes:
        for a in (node.prefix,*node.suffixes,node.predicted_prefix,*node.predicted_terminals):a.setflags(write=False)
    tree.baseline_plan.setflags(write=False)
    return tree
