"""Parent-paired estimator. CLI is artificial-only until a new authorization."""
import argparse
import json
from pathlib import Path
import numpy as np

CELLS = ('P0','P1','O0','O1')
CONTRASTS = {'O0-P0': (-1,0,1,0), 'P1-P0': (-1,1,0,0),
             'O1-O0': (0,0,-1,1), 'interaction': (1,-1,-1,1)}


def estimate(parent_ids, outcomes, choices, native_indices, initial_success=None, local_progress=None, candidate_counts=None):
    """outcomes [parent, candidate, draw], choices [parent, four cells].

    Selection receipts must already exist before outcomes are supplied here.
    Candidates/draws never increase n. No pooled backbone-independent sample.
    """
    y, c = np.asarray(outcomes), np.asarray(choices)
    n = len(parent_ids)
    if len(set(parent_ids)) != n or n == 0 or y.ndim != 3 or y.shape[0] != n or y.shape[2] != 2:
        raise ValueError('Independent parent/two-draw structure')
    if c.shape != (n,4) or c.dtype.kind not in 'iu':
        raise ValueError('Choices/binary outcomes')
    sizes=np.full(n,y.shape[1],dtype=int) if candidate_counts is None else np.asarray(candidate_counts)
    if sizes.shape != (n,) or sizes.dtype.kind not in 'iu' or np.any(sizes<1) or np.any(sizes>y.shape[1]):
        raise ValueError('Sealed per-parent bank sizes')
    valid=np.arange(y.shape[1])[None,:] < sizes[:,None]
    if not np.isin(y[valid],[0,1]).all() or np.any(y[~valid] != -1):
        raise ValueError('Valid binary labels only; invalid padding must be -1, never a fabricated outcome')
    native = np.asarray(native_indices)
    if native.shape != (n,) or native.dtype.kind not in 'iu' or np.any(native < 0) or np.any(native >= sizes):
        raise ValueError('Native reference indices')
    if np.any(c < 0) or np.any(c >= sizes[:,None]):
        raise ValueError('Selection outside bank')
    selected = y[np.arange(n)[:,None], c].mean(2)
    rng = np.random.default_rng(20261004)
    resamples = rng.integers(0,n,size=(10000,n))
    summary = {}
    for name, weights in CONTRASTS.items():
        effect = selected @ np.asarray(weights)
        boot = effect[resamples].mean(1)
        summary[name] = {'mean': float(effect.mean()), 'parent_effects': effect.tolist(),
                         'ci95_percentile': np.quantile(boot,[.025,.975]).tolist(),
                         'gains': int((effect>0).sum()), 'losses': int((effect<0).sum()),
                         'ties': int((effect==0).sum())}
    # Hindsight max over noisy two-draw means is explicitly optimistic.
    means=np.where(valid,y.mean(2),-np.inf)
    hindsight = means.max(1)
    split = []
    for select_draw, assess_draw in ((0,1),(1,0)):
        picked = np.argmax(np.where(valid,y[:,:,select_draw],-np.inf),axis=1)
        split.append(y[np.arange(n),picked,assess_draw])
    initial = np.zeros(n,dtype=bool) if initial_success is None else np.asarray(initial_success,dtype=bool)
    if initial.shape != (n,): raise ValueError('Initial-success shape')
    if np.any(initial & ~np.all((y==1)|(~valid[:,:,None]),axis=(1,2))): raise ValueError('Initial success must be all-cell absorbed success')
    result = {'n_independent_parents': n, 'parent_ids': list(parent_ids),
            'cells': dict(zip(CELLS,selected.mean(0).tolist())), 'source_cells': selected.tolist(),
            'cell_ci95': dict(zip(CELLS,np.quantile(selected[resamples].mean(1),[.025,.975],axis=0).T.tolist())),
            'contrasts': summary, 'native_reference': float(y[np.arange(n),native].mean()),
            'native_parent': y[np.arange(n),native].mean(1).tolist(), 'selected_indices': c.tolist(),
            'candidate_counts':sizes.tolist(),
            'identity_changes_vs_P0': (c != c[:,:1]).sum(0).tolist(),
            'candidate_mean_success': [y[i,:sizes[i]].mean(1).tolist() for i in range(n)],
            'hindsight_optimistic_parent': hindsight.tolist(),
            'split_draw_hindsight_parent': np.mean(split,axis=0).tolist(),
            'initial_success_count': int(initial.sum()),
            'uncertainty': 'parent-paired percentile bootstrap 10000; descriptive; no multiplicity-controlled claims'}
    if local_progress is not None:
        local = np.asarray(local_progress,dtype=np.float64)
        if local.shape != y.shape or not np.isfinite(local[valid]).all(): raise ValueError('Separate local diagnostic shape')
        result['local_progress_source_cells'] = local[np.arange(n)[:,None],c].mean(2).tolist()
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('input'); p.add_argument('--artificial', action='store_true')
    args = p.parse_args()
    if not args.artificial:
        raise PermissionError('Research analysis remains disabled')
    data = json.loads(Path(args.input).read_text())
    if data.pop('domain', None) != 'artificial':
        raise PermissionError('Artificial fixture only')
    print(json.dumps(estimate(**data),indent=2,allow_nan=False))

if __name__ == '__main__': main()
