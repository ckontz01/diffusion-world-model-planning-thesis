"""CVL-1 preparation core. No filesystem, simulator, checkpoint or dispatch CLI.

Reference identifiers are orchestration metadata, never feature columns.
All numerical tests must supply synthetic fixtures until a launch is approved.
"""
import hashlib
import numpy as np
import torch
from torch import nn

VERSION = 'candidate-value-v1-20260914'
HISTORICAL = (1269,582,525,722,567,716,630,1066,1074,1565,70,867,221,905,
              1287,621,428,288,1488,757,641,855,1280,420,860,98,886,432,
              181,783,706,989)
SIZES = {'train': 96, 'validation': 32, 'closed_loop': 32}
FEATURE_KEYS = {'current', 'goal', 'predicted', 'state', 'actions', 'time'}
FEATURE_DIM = 619


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(*parts):
    return hashlib.sha256('|'.join(map(str, (VERSION,) + parts)).encode()).hexdigest()


def seed(*parts):
    return int(digest(*parts)[:8], 16)


def allocation():
    """Proposed ID-only allocation; no input or outcome file is opened."""
    ids = sorted(set(range(1600)) - set(HISTORICAL),
                 key=lambda r: (digest('reference-allocation', r), r))
    out, offset = {}, 0
    for split, n in SIZES.items():
        out[split] = ids[offset:offset+n]
        offset += n
    return out


def check_source_groups(mapping):
    """Future metadata-only preflight must verify independent source identities.

    mapping: reference -> immutable original source episode key. The collected
    independent reference is the grouping unit; aliasing aborts, never reshuffles.
    """
    ids = sum(allocation().values(), [])
    require(set(mapping) == set(ids), 'Exact proposed references required')
    require(len(set(mapping.values())) == len(ids), 'Aliased source references')


def anchors(h):
    require(h in (75, 150), 'Horizon')
    return (0, 30, h, 2*h-15)


def clock(h, t):
    require(h in (75, 150) and isinstance(t, int) and 0 <= t < 2*h
            and t % 15 == 0, 'Absolute decision time')
    delta = h - t % h
    # absolute budget and cyclic schedule are not interchangeable.
    return np.array([h/150, t/(2*h), (2*h-t)/300,
                     delta/150, 1., t//h], dtype=np.float32)


def sample_bank(immediate, continuation, *, reference, h, t):
    """Eight distinct indices: both winners then hash-uniform remaining slots.

    If winners coincide, seven remaining slots. No planner RNG is consumed.
    Hash ordering is a fixed pseudorandom-without-replacement sampling rule.
    """
    split=allocation()
    require(reference in split['train']+split['validation'] and t in anchors(h),
            'Undesignated bank')
    a, b = np.asarray(immediate), np.asarray(continuation)
    require(a.shape == b.shape == (64,) and np.isfinite(a).all()
            and np.isfinite(b).all(), 'Bank costs')
    winners = list(dict.fromkeys((int(b.argmin()), int(a.argmin()))))
    remaining = sorted(set(range(64))-set(winners),
                       key=lambda i: (digest('candidate-sampling', reference,h,t,i),i))
    selected = winners + remaining[:8-len(winners)]
    return {'indices': selected, 'winners': winners,
            'other_slots': 8-len(winners), 'index_coverage': 8/64,
            'nonwinner_inclusion_probability': (8-len(winners))/(64-len(winners))}


def features(values):
    """Allowlist only. Inputs already use the pinned planner/checkpoint scaling.

    Latents current/goal/predicted: checkpoint-standardized; state: checkpoint-
    standardized seven-vector; actions: planner-space decoded-later 15x2 chunk.
    No training-, validation- or probe-fitted normalization is performed here.
    """
    require(set(values) == FEATURE_KEYS, 'Feature allowlist (no IDs/future/labels)')
    arrays = {k: np.asarray(v, dtype=np.float32) for k, v in values.items()}
    n = len(arrays['actions'])
    shapes = {'current':(n,192), 'goal':(n,192), 'predicted':(n,192),
              'state':(n,7), 'actions':(n,15,2), 'time':(n,6)}
    require(n > 0 and all(arrays[k].shape == shape for k,shape in shapes.items()),
            'Feature dimensions')
    x = np.concatenate([arrays[k].reshape(n,-1) for k in
                        ('current','goal','predicted','state','actions','time')],axis=1)
    require(x.shape == (n,FEATURE_DIM) and np.isfinite(x).all(), 'Finite features')
    return x


def success_target(native_success, truncated, *, remaining, planner_failure=False):
    """Post-action flags only, including first chunk and last budget action.

    Infrastructure/evaluator faults must never call this reducer. A verified
    planner failure is a policy failure, not censored or a synthetic distance.
    """
    s, tr = np.asarray(native_success), np.asarray(truncated)
    require(s.dtype == tr.dtype == np.bool_ and s.ndim == 1 and s.shape == tr.shape,
            'Boolean post-step flags')
    require(remaining >= 15 and remaining % 15 == 0 and len(s) <= remaining,
            'Original remaining budget')
    hits = np.flatnonzero(s | tr)
    require(not len(hits) or hits[0] == len(s)-1, 'Must stop on first terminal')
    require(len(s) == remaining or len(hits) or planner_failure, 'Censored rollout')
    return {'success': int(s.any()), 'first_chunk_success': bool(s[:15].any()),
            'steps':len(s), 'planner_failure':bool(planner_failure),
            'policy_conditional_negative':not bool(s.any())}


class ValueModel(nn.Module):
    def __init__(self, linear=False):
        super().__init__()
        self.net = (nn.Linear(FEATURE_DIM,1) if linear else nn.Sequential(
            nn.Linear(FEATURE_DIM,128),nn.ReLU(),nn.Linear(128,64),nn.ReLU(),
            nn.Linear(64,1)))

    def forward(self,x):
        return self.net(x).squeeze(-1)


def row_weights(keys):
    """Equal reference, horizon, live anchor, candidate, tail replicate weights.

    keys=(reference,horizon,anchor,candidate,tail). Missing terminal anchors are
    explicitly absent, not negative observations; paired horizons required.
    """
    require(len(keys)>0 and len(set(keys))==len(keys), 'Unique label identities')
    children = {}
    for key in keys:
        require(len(key)==5, 'Label key')
        for depth in range(5):
            children.setdefault(tuple(key[:depth]),set()).add(key[depth])
    return np.array([np.prod([1/len(children[tuple(k[:d])]) for d in range(5)])
                     for k in keys],dtype=np.float32)


def sparse_gate(keys, y):
    y=np.asarray(y)
    require(y.shape==(len(keys),) and np.isin(y,(0,1)).all(), 'Binary labels')
    positive_refs={k[0] for k,v in zip(keys,y) if v}
    return bool(y.sum()>=100 and len(positive_refs)>=20 and (y==0).sum()>=100)


def fit(x, y, keys, *, linear=False, model_seed=8201, epochs=40):
    """Fixed weighted BCE; caller owns authenticated TRAIN-only inputs.

    In this preparation only synthetic fixtures call this function. No optimizer
    is constructed on frozen modules. No validation selection/early stopping.
    """
    train=set(allocation()['train'])
    require(all(k[0] in train for k in keys), 'Training references only')
    require(sparse_gate(keys,y), 'Sparse-success stop; do not relabel or expand')
    x=np.asarray(x,dtype=np.float32);y=np.asarray(y,dtype=np.float32)
    require(x.shape==(len(keys),FEATURE_DIM) and np.isfinite(x).all(), 'Training X')
    w=row_weights(keys)
    # Isolate initialization/shuffle from every planner/global caller RNG.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(model_seed)
        model=ValueModel(linear)
    opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    gen=torch.Generator().manual_seed(seed('training-order',model_seed))
    tx,ty,tw=map(torch.from_numpy,(x,y,w))
    for _ in range(epochs):
        order=torch.randperm(len(x),generator=gen)
        for ids in order.split(256):
            opt.zero_grad(set_to_none=True)
            loss=nn.functional.binary_cross_entropy_with_logits(model(tx[ids]),ty[ids],reduction='none')
            # Unbiased mini-batch approximation to global hierarchical objective.
            (loss*tw[ids]*len(x)).mean().backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.)
            opt.step()
    return model.eval().requires_grad_(False)


def probabilities(models,x):
    require(len(models)>0, 'No learned model')
    with torch.inference_mode():
        values=torch.stack([m(torch.as_tensor(x,dtype=torch.float32)).sigmoid()
                            for m in models]).mean(0).cpu().numpy()
    require(np.isfinite(values).all(), 'Invalid learned scores: never fallback')
    return values


def reference_interval(reference_effects, *, draws=10000):
    """Exploratory percentile interval; caller reduces horizons/seeds FIRST."""
    x=np.asarray(reference_effects,dtype=float)
    require(x.ndim==1 and len(x)>1 and np.isfinite(x).all(), 'Reference effects')
    rng=np.random.default_rng(seed('reference-bootstrap'))
    boot=x[rng.integers(0,len(x),size=(draws,len(x)))].mean(1)
    return {'mean':float(x.mean()),'lower':float(np.quantile(boot,.025)),
            'upper':float(np.quantile(boot,.975)),'n_references':len(x)}


def bank_metrics(prob, outcomes, *, continuation_index, immediate_index, original_indices):
    """Eight sampled candidates, two tail draws; no full-bank oracle claim."""
    p,y=np.asarray(prob),np.asarray(outcomes)
    require(p.shape==(8,) and y.shape==(8,2) and np.isfinite(p).all()
            and ((p>=0)&(p<=1)).all() and np.isin(y,(0,1)).all(), 'Validation bank')
    require(0<=continuation_index<8 and 0<=immediate_index<8, 'Control indices')
    indices=np.asarray(original_indices)
    require(indices.shape==(8,) and np.issubdtype(indices.dtype,np.integer)
            and len(set(indices.tolist()))==8 and ((indices>=0)&(indices<64)).all(), 'Original bank indices')
    q=y.mean(1)
    tied=np.flatnonzero(p==p.max())
    chosen=int(tied[indices[tied].argmin()])
    informative=[(i,j) for i in range(8) for j in range(i) if q[i]!=q[j]]
    concordance=[float((p[i]-p[j])*(q[i]-q[j])>0) if p[i]!=p[j] else .5
                 for i,j in informative]
    pp=np.clip(p,1e-7,1-1e-7)
    return {'selected_index':chosen,'selected_empirical_success':float(q[chosen]),
            'continuation_success':float(q[continuation_index]),
            'immediate_success':float(q[immediate_index]),
            'uniform_success':float(q.mean()),
            'sampled_max_empirical_success':float(q.max()),
            'sampled_empirical_regret':float(q.max()-q[chosen]),
            'pairwise_concordance':float(np.mean(concordance)) if concordance else None,
            'informative_pairs':len(informative),
            'brier':float(((p[:,None]-y)**2).mean()),
            'log_loss':float(-(q*np.log(pp)+(1-q)*np.log(1-pp)).mean())}


def cost_plan():
    refs=SIZES['train']+SIZES['validation']
    labels=refs*2*4*8*2
    branch_steps=refs*4*8*2*(150+300)
    prefix_bank_steps=refs*(150+300)
    closed_runs=SIZES['closed_loop']*2*2*4
    closed_steps=SIZES['closed_loop']*2*4*(150+300)
    return dict(label_ceiling=labels,train_labels=96*2*4*8*2,
        validation_labels=32*2*4*8*2,distinct_sampled_candidates=labels//2,
        bank_ceiling=refs*2*4,collection_steps=branch_steps+prefix_bank_steps,
        collection_solve_calls=(branch_steps+prefix_bank_steps)//15,
        closed_loop_runs=closed_runs,closed_loop_steps=closed_steps,
        collection_jobs=256,closed_loop_jobs=32,synthetic_gpu_preflights=2,
        collection_job_cap_seconds=600,closed_job_cap_seconds=600,
        preflight_job_cap_seconds=300,maximum_scheduled_gpu_seconds=173400,
        aggregate_gpu_seconds_cap=180000,cpu_training_wall_seconds_cap=7200,
        artifact_bytes_cap=20_000_000_000,external_free_bytes_required=40_000_000_000)
