"""One fixed CPU-only objective x capacity study on accepted saved CVL-1 data."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

import numpy as np
import torch
from torch import nn

VERSION = 'cvl1-objective-capacity-20260915-v1'
ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis')
SOURCE_SHA = '521a0e6627c570ffa30d12adc63f92cf9ba76dee2c9bc4c59d24f4982f4f45f2'
CAPSULE_SHA = 'a1f152f66a1a6f1b766691b4a12c18fc6489d921f82ca7fbca29d86714b21469'
SOURCE = ROOT / 'snapshots/candidate-value-learning-20260914-521a0e6627c570ff'
RUN = ROOT / 'experiments/candidate-value-learning-20260914/run-521a0e6627c570ff'
ACCEPTED_RESULT = '36d953e5cf366965564cc09b2e8c9a33d407550a'
ACCEPTED_DIAGNOSIS = 'ea31f4447f7014778d980695768c8a3afd02ce6b'
FIT_SEAL = '90e491a7a186e7ef1968c70f29ecf49b3bfbe481f013ba051c10e33c77eb669c'
CONFIGS = ('original_bce', 'compact_bce', 'original_relative', 'compact_relative')
SEEDS = (8201, 8202, 8203)
# Ties in the training-fold recommendation prefer compact capacity, then BCE.
RECOMMEND_ORDER = ('compact_bce', 'compact_relative', 'original_bce', 'original_relative')
FIT_CAP = 100
FIT_COUNT = 60
OVERHEAD_CAP = 1100
WORKER_CAP = FIT_COUNT * FIT_CAP + OVERHEAD_CAP
ARTIFACT_CAP = 1_000_000_000


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class Output:
    """Exclusive, size-reserved writes; leave 20MB for logs/source/accounting."""
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(exist_ok=False)
        self.bytes = 0

    def put(self, rel, value):
        assert self.bytes + len(value) <= ARTIFACT_CAP - 20_000_000
        p = self.root / rel
        assert p.resolve().is_relative_to(self.root.resolve())
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as f:
            f.write(value)
        self.bytes += len(value)
        return sha(p)

    def json(self, rel, value):
        return self.put(rel, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())

    def npz(self, rel, **arrays):
        b = io.BytesIO()
        np.savez_compressed(b, **arrays)
        return self.put(rel, b.getvalue())

    def seal(self, directory=''):
        p = self.root / directory
        files = sorted(f for f in p.rglob('*') if f.is_file() and f.name != 'sha256.txt')
        value = ''.join(f'{sha(f)}  {f.relative_to(p).as_posix()}\n' for f in files).encode()
        return self.put(str(Path(directory)/'sha256.txt'), value)


class Budget:
    """Reserve the complete workload; each fit has its own non-transferable cap."""
    def __init__(self):
        self.started = time.monotonic()
        self.fit_seconds = 0.
        self.completed = 0
        signal.signal(signal.SIGALRM, self.timeout)
        self.check()

    @staticmethod
    def timeout(*_):
        raise TimeoutError('Fixed CPU reservation exhausted; no retry or expansion')

    def check(self):
        elapsed = time.monotonic()-self.started
        overhead = elapsed-self.fit_seconds
        assert overhead < OVERHEAD_CAP, 'Setup/analysis reservation exhausted'
        remaining = (FIT_COUNT-self.completed)*FIT_CAP + OVERHEAD_CAP-overhead
        assert elapsed+remaining <= WORKER_CAP+.01, 'Complete fixed workload cannot fit'
        assert elapsed < WORKER_CAP
        signal.setitimer(signal.ITIMER_REAL, min(OVERHEAD_CAP-overhead, WORKER_CAP-elapsed))

    def begin_fit(self):
        self.check()
        assert self.completed < FIT_COUNT
        signal.setitimer(signal.ITIMER_REAL, FIT_CAP)
        return time.monotonic(), time.process_time()

    def end_fit(self, start):
        wall, cpu = time.monotonic()-start[0], time.process_time()-start[1]
        assert wall <= FIT_CAP, 'Per-fit reservation exhausted'
        self.fit_seconds += wall
        self.completed += 1
        self.check()
        return dict(wall_seconds=wall, process_cpu_seconds=cpu)


def folds(refs):
    assert len(refs) == len(set(refs)) == 96
    order = sorted(refs, key=lambda r: (hashlib.sha256(f'{VERSION}|fold|{r}'.encode()).hexdigest(), r))
    return [order[i:i+24] for i in range(0, 96, 24)]


def choose(scores, ids, baseline=None):
    scores, ids = np.asarray(scores), np.asarray(ids)
    assert np.isfinite(scores).all()
    tied = np.flatnonzero(scores == scores.max())
    if baseline is not None and baseline in tied:
        return int(baseline)
    return int(tied[np.argmin(ids[tied])])


class Model(nn.Module):
    def __init__(self, compact):
        super().__init__()
        self.net = (nn.Sequential(nn.Linear(619, 32), nn.ReLU(), nn.Linear(32, 1)) if compact else
                    nn.Sequential(nn.Linear(619, 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1)))

    def forward(self, x):
        return self.net(x).squeeze(-1)


def table(banks, relative=False):
    """Pair each label with SAME bank, SAME draw baseline; retain all zeros."""
    from candidate_value_learning import row_weights
    x, bx, y, keys = [], [], [], []
    for b in banks:
        assert b['x'].shape == (8, 619) and b['y'].shape == (8, 2)
        assert np.isin(b['y'], (0, 1)).all()
        base = b['base']
        assert 0 <= base < 8 and b['ids'][base] == b['continuation_index']
        for i, original in enumerate(b['ids']):
            if relative and i == base:
                continue
            for d in (0, 1):
                x.append(b['x'][i]); bx.append(b['x'][base])
                y.append(b['y'][i, d] - b['y'][base, d] if relative else b['y'][i, d])
                keys.append((b['reference'], b['horizon'], b['anchor'], original, d))
    return (np.asarray(x, np.float32), np.asarray(bx, np.float32), np.asarray(y, np.float32),
            row_weights(keys), keys)


def fit_preprocessing(banks, fitting_refs):
    from candidate_value_models import normalize_fit
    assert {b['reference'] for b in banks} == set(fitting_refs)
    # Same eight-candidate/draw normalization for BOTH objectives, training only.
    x, _, _, w, _ = table(banks)
    return normalize_fit(x, w)


def fit(banks, config, model_seed, mean, scale, epochs=40):
    from candidate_value_learning import seed
    from candidate_value_models import transform
    relative = config.endswith('relative')
    x, bx, y, w, keys = table(banks, relative)
    assert np.isfinite(x).all() and np.isfinite(y).all() and np.isclose(w.sum(), 1.)
    tx, tb, ty, tw = map(torch.from_numpy, (transform(x, mean, scale), transform(bx, mean, scale), y, w))
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(model_seed)
        model = Model(config.startswith('compact'))
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    gen = torch.Generator().manual_seed(seed('training-order', model_seed))
    steps = 0
    for _ in range(epochs):
        order = torch.randperm(len(x), generator=gen)
        for ids in order.split(256):
            opt.zero_grad(set_to_none=True)
            pred = model(tx[ids])
            loss = ((pred-model(tb[ids])-ty[ids]).square() if relative else
                    nn.functional.binary_cross_entropy_with_logits(pred, ty[ids], reduction='none'))
            objective = (loss*tw[ids]*len(x)).mean()
            assert torch.isfinite(objective), 'Non-finite loss; no fallback'
            objective.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            opt.step(); steps += 1
    model.eval().requires_grad_(False)
    assert all(p.device.type == 'cpu' and torch.isfinite(p).all() for p in model.parameters())
    return model, dict(rows=len(keys), zero_targets=int(np.sum(y == 0)),
                       negative_targets=int(np.sum(y < 0)), positive_targets=int(np.sum(y > 0)),
                       optimizer_steps=steps, parameters=sum(p.numel() for p in model.parameters()))


def scores(models, config, x, base, mean, scale):
    from candidate_value_models import transform
    z = torch.from_numpy(transform(x, mean, scale))
    with torch.inference_mode():
        raw = torch.stack([m(z) for m in models])
        values = raw-raw[:, base:base+1] if config.endswith('relative') else raw.sigmoid()
        ensemble = values.mean(0)
    values, ensemble = values.numpy(), ensemble.numpy()
    assert np.isfinite(values).all() and np.isfinite(ensemble).all()
    if config.endswith('relative'):
        assert np.all(values[:, base] == 0) and ensemble[base] == 0
    return values, ensemble


def concordance(p, q):
    vals = [.5 if p[i] == p[j] else float((p[i]-p[j])*(q[i]-q[j]) > 0)
            for i in range(len(q)) for j in range(i) if q[i] != q[j]]
    return float(np.mean(vals)) if vals else None


def metrics(p, b, probability, new_rule, chosen=None):
    y, base = b['y'], b['base']; q = y.mean(1)
    s = choose(p, b['ids'], base if new_rule else None) if chosen is None else chosen
    delta = y[s]-y[base]
    m = dict(selected_success=float(q[s]), continuation_success=float(q[base]),
             effect=float(delta.mean()), gain=float(np.mean(delta > 0)), loss=float(np.mean(delta < 0)),
             departure=float(s != base), predicted_advantage=float(p[s]-p[base]),
             concordance=concordance(p, q), informative_pairs=sum(q[i] != q[j] for i in range(8) for j in range(i)),
             score_min=float(p.min()), score_max=float(p.max()), score_range=float(np.ptp(p)),
             score_std=float(p.std()), top_gap=float(np.sort(p)[-1]-np.sort(p)[-2]),
             maximum_ties=int(np.sum(p == p.max())), tied_maximum=float(np.sum(p == p.max()) > 1),
             continuation_at_maximum=float(p[base] == p.max()),
             brier=None, log_loss=None, calibration=None)
    m['informative_pairs'] = int(m['informative_pairs'])
    assert abs(m['gain']-m['loss']-m['effect']) < 1e-12
    if probability:
        pp = np.clip(p, 1e-7, 1-1e-7)
        m.update(brier=float(np.mean((p[:, None]-y)**2)),
                 log_loss=float(-np.mean(q*np.log(pp)+(1-q)*np.log(1-pp))))
        # Bin masses/sums are reduced hierarchically BEFORE taking ratios.
        for k in range(5):
            mask = np.minimum((p*5).astype(int), 4) == k
            m[f'cal{k}_mass'] = float(mask.mean())
            m[f'cal{k}_p_sum'] = float(np.where(mask, p, 0).mean())
            m[f'cal{k}_y_sum'] = float(np.where(mask, q, 0).mean())
    return s, m


def reduce_rows(rows):
    keys = sorted(set().union(*(r['metrics'].keys() for r in rows))) if rows else []
    means, defined = {}, {}
    for key in keys:
        groups = {}
        for r in rows:
            value = r['metrics'].get(key)
            if value is not None:
                groups.setdefault(r['reference'], {}).setdefault(r['horizon'], []).append(value)
        values = [np.mean([np.mean(v) for v in hs.values()]) for hs in groups.values()]
        means[key] = float(np.mean(values)) if values else None
        defined[key] = sum(r['metrics'].get(key) is not None for r in rows)
    return dict(banks=len(rows), references=len({r['reference'] for r in rows}), means=means, defined_banks=defined)


def summary(rows):
    from candidate_value_learning import reference_interval
    models = sorted({r['model'] for r in rows}); refs = sorted({r['reference'] for r in rows})
    overall = {m: reduce_rows([r for r in rows if r['model'] == m]) for m in models}
    reference_rows = [dict(reference=ref, models={m: reduce_rows([r for r in rows if r['model'] == m and
                         r['reference'] == ref])['means'] for m in models}) for ref in refs]
    for m, agg in overall.items():
        agg['descriptive_reference_interval'] = reference_interval([r['models'][m]['effect'] for r in reference_rows])
        means = agg['means']
        if 'cal0_mass' in means:
            agg['calibration'] = [dict(mass=means[f'cal{k}_mass'],
                probability=means[f'cal{k}_p_sum']/means[f'cal{k}_mass'] if means[f'cal{k}_mass'] else None,
                outcome=means[f'cal{k}_y_sum']/means[f'cal{k}_mass'] if means[f'cal{k}_mass'] else None) for k in range(5)]
    strata = {f'H{h}-slot{s}': {m: reduce_rows([r for r in rows if r['model'] == m and r['horizon'] == h
                                             and r['slot'] == s]) for m in models} for h in (75, 150) for s in range(4)}
    return dict(models=overall, reference_rows=reference_rows, strata=strata)


def contrasts(s):
    e = {k: s['models'][k]['means']['effect'] for k in CONFIGS}
    return dict(objective_original=e['original_relative']-e['original_bce'],
                objective_compact=e['compact_relative']-e['compact_bce'],
                capacity_bce=e['compact_bce']-e['original_bce'],
                capacity_relative=e['compact_relative']-e['original_relative'],
                interaction=(e['compact_relative']-e['compact_bce'])-(e['original_relative']-e['original_bce']))


def recommend(s):
    effects = {k: s['models'][k]['means']['effect'] for k in CONFIGS}
    top = max(effects.values())
    winner = next(k for k in RECOMMEND_ORDER if effects[k] == top) if top > 0 else None
    return dict(configuration=winner, effects=effects, basis='training-only source-held-out ensemble effect',
                action='candidate_for_later_review' if winner else 'retain_continuation_no_model_recommended',
                no_automatic_downstream_launch=True, validation_used=False)


def authenticate_code():
    assert sha(SOURCE/'SOURCE-MANIFEST.sha256') == SOURCE_SHA
    seals = dict((n, h) for h, n in (s.split('  ', 1) for s in (SOURCE/'SOURCE-MANIFEST.sha256').read_text().splitlines()))
    for name in ('candidate_value_learning.py', 'candidate_value_contract.py', 'candidate_value_models.py', 'candidate_value_data.py'):
        rel = 'cluster/prometheus/'+name
        assert sha(SOURCE/rel) == seals[rel]
    sys.path.insert(0, str(SOURCE/'cluster/prometheus'))


def read_saved(role, opened, budget, validation_freeze=None):
    import candidate_value_contract as ct
    import candidate_value_learning as c
    from candidate_value_data import read_npz
    assert role in ('train', 'validation')
    if role == 'validation':
        assert validation_freeze is not None and validation_freeze.is_file()
        freeze = ct.json_read(validation_freeze)
        assert freeze['completed_fits'] == 60 and freeze['validation_read'] is False
        for rel, digest in freeze['members'].items():
            assert sha(validation_freeze.parent/rel) == digest
    request = ct.json_read(RUN/f'BACKUP-REQUEST-{role}.json')
    banks = []; unavailable = []
    refs = ct.allocation()[role]
    for index in range(2*len(refs)):
        budget.check()
        p = RUN/f'{role}-{index}'
        assert sha(p/'sha256.txt') == request['seals'][p.name]
        seals = dict((n, h) for h, n in (s.split('  ', 1) for s in (p/'sha256.txt').read_text().splitlines()))
        def consumed(rel):
            f = ct.child(p, rel)
            assert sha(f) == seals[rel]
            opened.append(dict(file=str(f.relative_to(RUN)), sha256=seals[rel]))
            return f
        report = ct.json_read(consumed('REPORT.json'))
        ref = refs[index//2]; h = 75 if index % 2 == 0 else 150
        assert (report['reference'], report['horizon'], report['kind'], report['index']) == (ref, h, role, index)
        assert report['source_sha256'] == SOURCE_SHA and report['capsule_sha256'] == CAPSULE_SHA
        for slot, b in enumerate(report['banks']):
            assert b['anchor'] == c.anchors(h)[slot]
            meta = dict(reference=ref, horizon=h, anchor=b['anchor'], slot=slot)
            if not b['available']:
                unavailable.append(meta); continue
            z = read_npz(consumed(f'bank-{b["anchor"]}.npz'))
            ids = b['coverage']['indices']
            assert len(ids) == len(set(ids)) == 8
            y = np.full((8, 2), -1, np.int64)
            for label in b['labels']:
                i, d = ids.index(label['candidate']), label['draw']
                assert d in (0, 1) and y[i, d] == -1 and label['target']['success'] in (0, 1)
                y[i, d] = label['target']['success']
            assert np.isin(y, (0, 1)).all()
            base = ids.index(int(z['continuation_index']))
            assert choose(-z['continuation'][ids], ids) == base
            immediate = ids.index(int(z['immediate_index']))
            assert choose(-z['immediate'][ids], ids) == immediate
            x = z['x'][ids]
            assert x.shape == (8, 619) and x.dtype == np.float32 and np.isfinite(x).all()
            banks.append({**meta, 'ids': ids, 'x': x, 'y': y, 'base': base, 'immediate_index': immediate,
                          'continuation_index': ids[base], 'continuation': -z['continuation'][ids],
                          'immediate': -z['immediate'][ids]})
    assert {b['reference'] for b in banks} == set(refs)
    assert all({b['horizon'] for b in banks if b['reference'] == r} == {75, 150} for r in refs)
    return banks, unavailable


def evaluate(banks, config_models, norm, predictor, fold_id, budget):
    import candidate_value_learning as c
    from candidate_value_models import transform
    rows = []; predictions = []
    mean, scale = norm
    for b in banks:
        budget.check()
        meta = {k: b[k] for k in ('reference', 'horizon', 'anchor', 'slot')}
        meta['fold'] = fold_id
        ps = {}; attrs = {}; disagreements = {}
        for config, models in config_models.items():
            single, ensemble = scores(models, config, b['x'], b['base'], mean, scale)
            ps[config] = ensemble; attrs[config] = (config.endswith('bce'), True)
            choices = []
            for seed, p in zip(SEEDS, single):
                name = f'{config}_seed{seed}'
                ps[name] = p; attrs[name] = attrs[config]
                choices.append(choose(p, b['ids'], b['base']))
            disagreements[config] = dict(seed_winner_disagreement=float(len(set(choices)) > 1),
                                          seed_score_std=float(single.std(0).mean()))
        z = transform(b['x'], predictor.mean, predictor.scale)
        for seed, model in zip(SEEDS, predictor.models['value']):
            ps[f'historical_mlp{seed}'] = c.probabilities([model], z)
        ps.update(historical_ensemble=predictor('value', b['x']), historical_linear=predictor('linear', b['x']),
                  historical_context=predictor('context', b['x']),
                  historical_constant=np.full(8, predictor.report['constant_probability']),
                  continuation=b['continuation'], immediate=b['immediate'])
        for name in ps:
            if name not in attrs:
                attrs[name] = (name.startswith('historical'), False)
        pred = {**meta, 'ids': b['ids'], 'outcomes': b['y'].tolist(), 'continuation_index': b['continuation_index'], 'scores': {}}
        for name, p in ps.items():
            s, m = metrics(p, b, *attrs[name])
            m.update(disagreements.get(name, {}))
            rows.append({**meta, 'model': name, 'selected_original_index': b['ids'][s], 'metrics': m})
            pred['scores'][name] = p.tolist()
        rows.append({**meta, 'model': 'uniform_sampled8', 'selected_original_index': None, 'metrics': {
            'selected_success': float(b['y'].mean()), 'effect': float(b['y'].mean()-b['y'][b['base']].mean()),
            'continuation_success': float(b['y'][b['base']].mean())}})
        predictions.append(pred)
    return rows, predictions


def main(out_path):
    out = Output(out_path); budget = Budget()
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '' and os.environ.get('SLURM_JOB_ID')
    torch.set_num_threads(4); torch.set_num_interop_threads(1)
    authenticate_code()
    import candidate_value_contract as ct
    from candidate_value_models import Predictor
    assert tuple(ct.TRAIN_SEEDS) == SEEDS
    assert sha(RUN/'fit-0/sha256.txt') == FIT_SEAL
    predictor = Predictor(RUN, SOURCE_SHA, CAPSULE_SHA)
    opened = [dict(file='fit-0/'+n, sha256=h) for h, n in
              (line.split('  ', 1) for line in (RUN/'fit-0/sha256.txt').read_text().splitlines())]
    train_refs = ct.allocation()['train']; fold_refs = folds(train_refs)
    out.json('FOLDS.json', dict(namespace=VERSION+'|fold|reference', held_out=fold_refs,
                              all_training=train_refs, validation_used=False))
    train, train_unavailable = read_saved('train', opened, budget)
    ledger = []; cross_rows = []; cross_predictions = []; fold_summaries = {}
    full_models = None; full_norm = None
    for f in range(5):
        tag = f'fold{f}' if f < 4 else 'full'
        fitting_refs = [r for r in train_refs if f == 4 or r not in fold_refs[f]]
        fitting = [b for b in train if b['reference'] in fitting_refs]
        norm = fit_preprocessing(fitting, fitting_refs)
        out.npz(f'models/{tag}/normalization.npz', mean=norm[0], scale=norm[1])
        out.json(f'models/{tag}/REFERENCES.json', dict(fitting=fitting_refs,
                 held_out=fold_refs[f] if f < 4 else [], validation_used=False))
        models = {}
        for config in CONFIGS:
            models[config] = []
            for seed in SEEDS:
                start = budget.begin_fit()
                model, receipt = fit(fitting, config, seed, *norm)
                charge = budget.end_fit(start)
                digest = out.npz(f'models/{tag}/{config}-{seed}.npz',
                                 **{k: v.detach().numpy() for k, v in model.state_dict().items()})
                models[config].append(model)
                entry = dict(stage=tag, configuration=config, seed=seed, sha256=digest,
                             fitting_references=len(fitting_refs), **receipt, **charge)
                ledger.append(entry)
                out.json(f'charges/fit-{budget.completed:02}.json', entry)
                print(json.dumps(dict(fit_completed=budget.completed, stage=tag, configuration=config,
                                      seed=seed, wall_seconds=charge['wall_seconds'])), flush=True)
        out.seal(f'models/{tag}')
        if f < 4:
            held = [b for b in train if b['reference'] in fold_refs[f]]
            rows, pred = evaluate(held, models, norm, predictor, f, budget)
            cross_rows.extend(rows); cross_predictions.extend(pred)
            fold_summaries[str(f)] = summary(rows)
            fold_summaries[str(f)]['contrasts'] = contrasts(fold_summaries[str(f)])
        else:
            full_models, full_norm = models, norm
    assert budget.completed == FIT_COUNT
    cross_summary = summary(cross_rows)
    cross_summary['contrasts'] = contrasts(cross_summary)
    recommendation = recommend(cross_summary)
    out.json('TRAINING-FOLD-RECOMMENDATION.json', recommendation)
    out.json('CROSSFIT.json', dict(aggregate=cross_summary, folds=fold_summaries,
        historical_learned_controls_are_in_sample=True,
        historical_controls_not_source_held_out=True, new_models_are_source_held_out=True))
    out.json('crossfit/BANK-ROWS.json', cross_rows)
    out.json('crossfit/PREDICTIONS.json', cross_predictions)
    full_rows, full_pred = evaluate(train, full_models, full_norm, predictor, None, budget)
    full_summary = summary(full_rows); full_summary['contrasts'] = contrasts(full_summary)
    out.json('TRAIN.json', full_summary)
    out.json('train/BANK-ROWS.json', full_rows); out.json('train/PREDICTIONS.json', full_pred)
    out.json('FIT-LEDGER.json', ledger)
    source_manifest = Path(__file__).parent/'SOURCE.sha256'
    assert source_manifest.is_file()
    # Explicit freeze of ALL full models, train-only recommendation, and reporting code.
    members = {p.relative_to(out.root).as_posix(): sha(p) for p in sorted(out.root.rglob('*')) if p.is_file()}
    freeze_hash = out.json('PRE-VALIDATION-FREEZE.json', dict(completed_fits=60, validation_read=False,
        source_manifest_sha256=sha(source_manifest), protocol_sha256=sha(Path(__file__).parent/'PROTOCOL.md'),
        members=members, recommendation=recommendation, monotonic_time=time.monotonic()))
    validation, val_unavailable = read_saved('validation', opened, budget, out.root/'PRE-VALIDATION-FREEZE.json')
    val_rows, val_pred = evaluate(validation, full_models, full_norm, predictor, None, budget)
    val_summary = summary(val_rows); val_summary['contrasts'] = contrasts(val_summary)
    out.json('VALIDATION.json', val_summary)
    out.json('validation/BANK-ROWS.json', val_rows); out.json('validation/PREDICTIONS.json', val_pred)
    out.json('CONSUMED-FILES.json', opened)
    counts = {role: dict(references=len({b['reference'] for b in bs}), available_banks=len(bs),
              unavailable_banks=len(missing), candidate_rows=len(bs)*8, binary_draws=len(bs)*16,
              positive_draws=int(sum(b['y'].sum() for b in bs)), unavailable=missing)
              for role, bs, missing in [('train', train, train_unavailable), ('validation', validation, val_unavailable)]}
    report = dict(version=VERSION, accepted_result_commit=ACCEPTED_RESULT, accepted_diagnosis_commit=ACCEPTED_DIAGNOSIS,
        original_decision='stop_no_ranking_promise', source_sha256=SOURCE_SHA, capsule_sha256=CAPSULE_SHA,
        new_source_manifest_sha256=sha(source_manifest), pre_validation_freeze_sha256=freeze_hash,
        configurations=list(CONFIGS), seeds=list(SEEDS), fits_completed=len(ledger), optimizer_steps=sum(e['optimizer_steps'] for e in ledger),
        counts=counts, recommendation_frozen_before_validation=recommendation,
        crossfit=cross_summary, training=full_summary, validation=val_summary,
        job_id=os.environ['SLURM_JOB_ID'], wall_seconds=time.monotonic()-budget.started,
        runtime=dict(python=sys.version, torch=torch.__version__, numpy=np.__version__),
        process_cpu_seconds=time.process_time(), maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        reserved_allocated_wall_seconds=7200, cpus=4, memory_gib=8, gpu_allocations=0,
        new_labels=0, simulator_calls=0, world_model_calls=0, proposer_calls=0, adapter_calls=0,
        closed_loop_payload_reads=0, heldout_1600_5999_payload_reads=0, historical_artifacts_modified=False,
        validation_is_exposed_development=True, no_confirmatory_or_post_selection_coverage_claim=True)
    budget.check()
    out.json('REPORT.json', report)
    out.seal()
    assert out.bytes <= ARTIFACT_CAP-20_000_000
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(completed=True, fits=60, artifact_bytes=out.bytes,
                         wall_seconds=time.monotonic()-budget.started,
                         process_cpu_seconds=time.process_time())), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', required=True)
    main(p.parse_args().out)
