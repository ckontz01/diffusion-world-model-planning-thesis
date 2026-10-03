"""Parent-paired estimator. CLI is artificial-only until a new authorization."""
import argparse
import json
from pathlib import Path
import numpy as np

CELLS = ('P0','P1','O0','O1')
CONTRASTS = {'O0-P0': (-1,0,1,0), 'P1-P0': (-1,1,0,0),
             'O1-O0': (0,0,-1,1), 'interaction': (1,-1,-1,1)}


def estimate(parent_ids, outcomes, choices, native_indices, initial_success=None, local_progress=None):
    """outcomes [parent, candidate, draw], choices [parent, four cells].

    Selection receipts must already exist before outcomes are supplied here.
    Candidates/draws never increase n. No pooled backbone-independent sample.
    """
    y, c = np.asarray(outcomes), np.asarray(choices)
    n = len(parent_ids)
    if len(set(parent_ids)) != n or n == 0 or y.ndim != 3 or y.shape[0] != n or y.shape[2] != 2:
        raise ValueError('Independent parent/two-draw structure')
    if c.shape != (n,4) or c.dtype.kind not in 'iu' or not np.isin(y,[0,1]).all():
        raise ValueError('Choices/binary outcomes')
    native = np.asarray(native_indices)
    if native.shape != (n,) or native.dtype.kind not in 'iu' or np.any(native < 0) or np.any(native >= y.shape[1]):
        raise ValueError('Native reference indices')
    if np.any(c < 0) or np.any(c >= y.shape[1]):
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
    hindsight = y.mean(2).max(1)
    split = []
    for select_draw, assess_draw in ((0,1),(1,0)):
        picked = np.argmax(y[:,:,select_draw],axis=1)  # frozen lowest-slot tie
        split.append(y[np.arange(n),picked,assess_draw])
    initial = np.zeros(n,dtype=bool) if initial_success is None else np.asarray(initial_success,dtype=bool)
    if initial.shape != (n,): raise ValueError('Initial-success shape')
    if np.any(initial & ~np.all(y==1,axis=(1,2))): raise ValueError('Initial success must be all-cell absorbed success')
    result = {'n_independent_parents': n, 'parent_ids': list(parent_ids),
            'cells': dict(zip(CELLS,selected.mean(0).tolist())), 'source_cells': selected.tolist(),
            'cell_ci95': dict(zip(CELLS,np.quantile(selected[resamples].mean(1),[.025,.975],axis=0).T.tolist())),
            'contrasts': summary, 'native_reference': float(y[np.arange(n),native].mean()),
            'native_parent': y[np.arange(n),native].mean(1).tolist(), 'selected_indices': c.tolist(),
            'identity_changes_vs_P0': (c != c[:,:1]).sum(0).tolist(),
            'candidate_mean_success': y.mean(2).tolist(),
            'hindsight_optimistic_parent': hindsight.tolist(),
            'split_draw_hindsight_parent': np.mean(split,axis=0).tolist(),
            'initial_success_count': int(initial.sum()),
            'uncertainty': 'parent-paired percentile bootstrap 10000; descriptive; no multiplicity-controlled claims'}
    if local_progress is not None:
        local = np.asarray(local_progress,dtype=np.float64)
        if local.shape != y.shape or not np.isfinite(local).all(): raise ValueError('Separate local diagnostic shape')
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
