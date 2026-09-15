"""Fixed, saved-feature-only CVL-1 learning diagnosis. No training or simulator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
import numpy as np

SOURCE_SHA = '521a0e6627c570ffa30d12adc63f92cf9ba76dee2c9bc4c59d24f4982f4f45f2'
CAPSULE_SHA = 'a1f152f66a1a6f1b766691b4a12c18fc6489d921f82ca7fbca29d86714b21469'
ACCEPTED_COMMIT = '36d953e5cf366965564cc09b2e8c9a33d407550a'
ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis')
SOURCE = ROOT / 'snapshots/candidate-value-learning-20260914-521a0e6627c570ff'
RUN = ROOT / 'experiments/candidate-value-learning-20260914/run-521a0e6627c570ff'
LEARNED = ['mlp8201', 'mlp8202', 'mlp8203', 'ensemble', 'linear', 'context']


def choose(scores, ids):
    scores, ids = np.asarray(scores), np.asarray(ids)
    tied = np.flatnonzero(scores == scores.max())
    return int(tied[np.argmin(ids[tied])])


def concordance(p, q):
    vals = []
    for i in range(len(q)):
        for j in range(i):
            if q[i] != q[j]:
                vals.append(.5 if p[i] == p[j] else float((p[i]-p[j])*(q[i]-q[j]) > 0))
    return float(np.mean(vals)) if vals else None


def scalar(x):
    return x.item() if isinstance(x, np.generic) else x


def reduce_rows(rows):
    """Equal ref/H/live-anchor; missing concordance remains explicitly conditional."""
    if not rows:
        return {'banks': 0, 'references': 0, 'means': {}, 'defined_banks': {}}
    keys = sorted(set().union(*(r['metrics'] for r in rows)))
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
    return dict(banks=len(rows), references=len({r['reference'] for r in rows}),
                means=means, defined_banks=defined)


def score_metrics(p, y, ids, baseline, probability=True):
    q = y.mean(1); selected = choose(p, ids); top = np.sort(p)
    out = dict(selected_success=float(q[selected]), effect=float(q[selected]-q[baseline]),
               selected_draw0=float(y[selected, 0]), selected_draw1=float(y[selected, 1]),
               departure=float(selected != baseline),
               concordance=concordance(p, q), concordance_draw0=concordance(p, y[:, 0]),
               concordance_draw1=concordance(p, y[:, 1]),
               score_min=float(p.min()), score_max=float(p.max()),
               score_range=float(np.ptp(p)), score_std=float(np.std(p)),
               score_variance=float(np.var(p)), top_gap=float(top[-1]-top[-2]),
               maximum_ties=int(np.sum(p == p.max())),
               tied_maximum=float(np.sum(p == p.max()) > 1),
               brier=None, log_loss=None, saturation=None)
    if probability:
        pp = np.clip(p, 1e-7, 1-1e-7)
        out.update(brier=float(np.mean((p[:, None]-y)**2)),
                   log_loss=float(-np.mean(q*np.log(pp)+(1-q)*np.log(1-pp))),
                   saturation=float(np.mean((p <= .01) | (p >= .99))))
    return selected, out


def draw_metrics(y, ids, baseline):
    out = {'candidate_disagreement': float(np.mean(y[:, 0] != y[:, 1])),
           'candidate_0win_1loss': float(np.mean((y[:, 0] == 1) & (y[:, 1] == 0))),
           'candidate_0loss_1win': float(np.mean((y[:, 0] == 0) & (y[:, 1] == 1)))}
    for d in (0, 1):
        delta = y[:, d]-y[baseline, d]
        for name, val in [('gain', delta > 0), ('loss', delta < 0), ('tie', delta == 0)]:
            out[f'candidate_draw{d}_{name}'] = float(np.mean(val))
        out[f'candidate_draw{d}_mean_difference'] = float(np.mean(delta))
        s = choose(y[:, d], ids); e = 1-d
        out.update({f'cross{d}_selection_success': float(y[s, d]),
                    f'cross{d}_evaluation_success': float(y[s, e]),
                    f'cross{d}_continuation_success': float(y[baseline, e]),
                    f'cross{d}_effect': float(y[s, e]-y[baseline, e]),
                    f'cross{d}_maximum_ties': int(np.sum(y[:, d] == y[:, d].max())),
                    f'cross{d}_tied_maximum': float(np.sum(y[:, d] == y[:, d].max()) > 1),
                    f'cross{d}_all_zero': float(not y[:, d].any()),
                    f'cross{d}_departure': float(s != baseline)})
    out['cross_mean_effect'] = .5*(out['cross0_effect']+out['cross1_effect'])
    return out


def decompose(p, y, ids, baseline, scores):
    s = choose(p, ids); diff = y[s]-y[baseline]; std = float(p.std())
    gains, losses = float(np.mean(diff > 0)), float(np.mean(diff < 0))
    out = dict(departure=float(s != baseline), gain=gains, loss=losses,
               empirical_advantage=float(diff.mean()),
               selected_probability=float(p[s]), baseline_probability=float(p[baseline]),
               selected_success=float(y[s].mean()), baseline_success=float(y[baseline].mean()),
               predicted_advantage=float(p[s]-p[baseline]),
               advantage_prediction_error=float(p[s]-p[baseline]-diff.mean()),
               score_std=std, score_range=float(np.ptp(p)),
               standardized_advantage=float((p[s]-p[baseline])/std) if std > 0 else None,
               top_gap=float(np.sort(p)[-1]-np.sort(p)[-2]))
    assert abs(gains-losses-out['empirical_advantage']) < 1e-12
    choices = {name: choose(scores[name], ids) for name in LEARNED}
    for i, a in enumerate(LEARNED):
        for b in LEARNED[:i]:
            out[f'disagree_{b}_{a}'] = float(choices[a] != choices[b])
    seed_scores = np.stack([scores[name] for name in LEARNED[:3]])
    out['seed_probability_std'] = float(seed_scores.std(0).mean())
    out['seed_winner_disagreement'] = float(len({choices[k] for k in LEARNED[:3]}) > 1)
    out['seed_advantage_std'] = float((seed_scores[:, s]-seed_scores[:, baseline]).std())
    return out


def summarize(rows):
    return dict(overall=reduce_rows(rows),
                horizons={str(h): reduce_rows([r for r in rows if r['horizon'] == h]) for h in (75, 150)},
                strata={f'H{h}-slot{k}': reduce_rows([r for r in rows if r['horizon'] == h and r['slot'] == k])
                        for h in (75, 150) for k in range(4)},
                tail_scope={scope: reduce_rows([r for r in rows if r['final_budget'] == flag])
                            for scope, flag in [('final_budget_no_stochastic_tail', True), ('earlier_anchors', False)]})


def main(out):
    began = time.monotonic(); out = Path(out); out.mkdir(exist_ok=False)
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    sys.path.insert(0, str(SOURCE/'cluster/prometheus'))
    # Authenticate consumed code only. Do not scan a model/data/runtime tree.
    manifest = SOURCE/'SOURCE-MANIFEST.sha256'
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == SOURCE_SHA
    code_seals = dict((n, h) for h, n in (s.split('  ', 1) for s in manifest.read_text().splitlines()))
    for name in ['candidate_value_learning.py', 'candidate_value_contract.py',
                 'candidate_value_models.py', 'candidate_value_data.py']:
        rel = 'cluster/prometheus/'+name
        assert hashlib.sha256((SOURCE/rel).read_bytes()).hexdigest() == code_seals[rel]
    import torch
    import candidate_value_contract as ct
    import candidate_value_learning as c
    from candidate_value_models import Predictor, transform
    from candidate_value_data import read_npz
    torch.set_num_threads(4); torch.set_num_interop_threads(1)
    # The accepted fit reader verifies its small model seal, not collection traces.
    predictor = Predictor(RUN, SOURCE_SHA, CAPSULE_SHA)
    assert all(not p.requires_grad and p.device.type == 'cpu'
               for models in predictor.models.values() for m in models for p in m.parameters())
    accepted = ct.json_read(RUN/'DISPATCH-FINAL.json')
    assert accepted['decision'] == 'stop_no_ranking_promise'
    opened = []; datasets = {}; all_banks = {}; candidates = {}
    for line in (RUN/'fit-0/sha256.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        opened.append(dict(file='fit-0/'+name, sha256=digest))
    requests = {stage: ct.json_read(RUN/f'BACKUP-REQUEST-{stage}.json') for stage in ('train', 'validation')}
    def consumed(directory, rel, seals):
        p = ct.child(directory, rel)
        assert rel in seals and ct.sha(p) == seals[rel]
        opened.append(dict(file=str(p.relative_to(RUN)), sha256=seals[rel]))
        return p
    for role in ('train', 'validation'):
        metrics = {}; bank_rows = []; candidate_rows = []; draw_rows = []; decomposition = []
        counts = dict(references=len(ct.allocation()[role]), available_banks=0, unavailable_banks=0,
                      candidate_rows=0, draw_disagreements=0, positive_draw0=0, positive_draw1=0,
                      final_budget_banks=0, final_budget_disagreements=0,
                      ensemble_departure_banks=0, ensemble_gain_draws=0, ensemble_loss_draws=0)
        score_extrema = {}; calibration = {}; reference_identity = []
        for index in range(counts['references']*2):
            directory = RUN/f'{role}-{index}'; seal = directory/'sha256.txt'
            assert ct.sha(seal) == requests[role]['seals'][directory.name]
            seals = dict((n, h) for h, n in (s.split('  ', 1) for s in seal.read_text().splitlines()))
            report = ct.json_read(consumed(directory, 'REPORT.json', seals))
            ref = ct.allocation()[role][index//2]; h = 75 if index % 2 == 0 else 150
            assert (report['reference'], report['horizon'], report['kind'], report['index']) == (ref, h, role, index)
            assert report['source_sha256'] == SOURCE_SHA and report['capsule_sha256'] == CAPSULE_SHA
            reference_identity.append((ref, h))
            available = [b for b in report['banks'] if b['available']]
            weight = 1/counts['references']/2/len(available)
            for slot, b in enumerate(report['banks']):
                if not b['available']:
                    counts['unavailable_banks'] += 1; continue
                t = b['anchor']; assert t == c.anchors(h)[slot]
                bank = read_npz(consumed(directory, f'bank-{t}.npz', seals))
                ids = b['coverage']['indices']; assert len(ids) == len(set(ids)) == 8
                y = np.full((8, 2), -1, dtype=np.int64)
                for label in b['labels']:
                    pos, d = ids.index(label['candidate']), label['draw']
                    assert y[pos, d] == -1; y[pos, d] = int(label['target']['success'])
                assert np.isin(y, (0, 1)).all()
                x = bank['x'][ids]; base = ids.index(int(bank['continuation_index']))
                immediate = ids.index(int(bank['immediate_index']))
                z = transform(x, predictor.mean, predictor.scale)
                scores = {f'mlp{s}': c.probabilities([m], z)
                          for s, m in zip(ct.TRAIN_SEEDS, predictor.models['value'])}
                scores.update(ensemble=predictor('value', x), linear=predictor('linear', x),
                              context=predictor('context', x),
                              constant=np.full(8, predictor.report['constant_probability']),
                              continuation=-bank['continuation'][ids], immediate=-bank['immediate'][ids])
                assert np.all(scores['context'] == scores['context'][0])
                assert choose(scores['continuation'], ids) == base and choose(scores['immediate'], ids) == immediate
                meta = dict(reference=ref, horizon=h, anchor=t, slot=slot, final_budget=t == 2*h-15)
                br = {**meta, 'weight': weight, 'ids': ids, 'continuation_index': ids[base], 'scorers': {}}
                for name, p in scores.items():
                    prob = name not in ('continuation', 'immediate')
                    selected, sm = score_metrics(p, y, ids, base, probability=prob)
                    metrics.setdefault(name, []).append({**meta, 'metrics': sm})
                    br['scorers'][name] = dict(selected_original_index=ids[selected], **sm)
                    bounds = score_extrema.setdefault(name, [float('inf'), float('-inf')])
                    bounds[0], bounds[1] = min(bounds[0], float(p.min())), max(bounds[1], float(p.max()))
                    if prob:
                        bins = calibration.setdefault(name, [dict(count=0, mass=0., probability=0., outcome=0.) for _ in range(5)])
                        for pp, qq in zip(p, y.mean(1)):
                            cb = bins[min(int(pp*5), 4)]; w = weight/8
                            cb['count'] += 1; cb['mass'] += w; cb['probability'] += w*float(pp); cb['outcome'] += w*float(qq)
                metrics.setdefault('uniform_sampled8', []).append({**meta, 'metrics': {
                    'selected_success': float(y.mean()), 'effect': float(y.mean()-y[base].mean()),
                    'selected_draw0': float(y[:, 0].mean()), 'selected_draw1': float(y[:, 1].mean())}})
                dm = draw_metrics(y, ids, base); dec = decompose(scores['ensemble'], y, ids, base, scores)
                counts['ensemble_departure_banks'] += int(dec['departure'])
                counts['ensemble_gain_draws'] += int(dec['gain']*2)
                counts['ensemble_loss_draws'] += int(dec['loss']*2)
                draw_rows.append({**meta, 'metrics': dm}); decomposition.append({**meta, 'metrics': dec})
                br['draws'], br['decomposition'] = dm, dec; bank_rows.append(br)
                for k, original in enumerate(ids):
                    candidate_rows.append({**meta, 'candidate': original, 'outcomes': y[k].tolist(),
                        'minus_continuation_draws': (y[k]-y[base]).tolist(),
                        'empirical_difference': float((y[k]-y[base]).mean()),
                        'probabilities': {a: float(scores[a][k]) for a in LEARNED+['constant']}})
                disagree = int(np.sum(y[:, 0] != y[:, 1]))
                counts['available_banks'] += 1; counts['candidate_rows'] += 8
                counts['draw_disagreements'] += disagree
                counts['positive_draw0'] += int(y[:, 0].sum()); counts['positive_draw1'] += int(y[:, 1].sum())
                if meta['final_budget']:
                    counts['final_budget_banks'] += 1; counts['final_budget_disagreements'] += disagree
        models = {name: summarize(rr) for name, rr in metrics.items()}
        for name, bins in calibration.items():
            for cb in bins:
                for key in ('probability', 'outcome'):
                    cb[key] = cb[key]/cb['mass'] if cb['mass'] else None
        decomp = summarize(decomposition); means = decomp['overall']['means']; departure = means['departure']
        decomp['conditional_on_departure'] = {k: means[k]/departure if departure else None
                                              for k in ('gain', 'loss', 'empirical_advantage', 'predicted_advantage')}
        reference_rows = []
        for ref in ct.allocation()[role]:
            reference_rows.append(dict(reference=ref,
                models={name: reduce_rows([r for r in rr if r['reference'] == ref])['means'] for name, rr in metrics.items()},
                decomposition=reduce_rows([r for r in decomposition if r['reference'] == ref])['means'],
                draws=reduce_rows([r for r in draw_rows if r['reference'] == ref])['means']))
        datasets[role] = dict(counts=counts, models=models, score_extrema=score_extrema,
                             calibration=calibration, draws=summarize(draw_rows), decomposition=decomp,
                             reference_rows=reference_rows)
        all_banks[role], candidates[role] = bank_rows, candidate_rows
    report = dict(version='cvl1-learning-diagnosis-20260915-v1', accepted_commit=ACCEPTED_COMMIT,
                  source_sha256=SOURCE_SHA, capsule_sha256=CAPSULE_SHA,
                  original_decision='stop_no_ranking_promise', train_is_in_sample=True,
                  frozen_forward_only=True, optimizer_steps=0, simulator_calls=0, world_model_calls=0,
                  gpu_allocations=0, closed_loop_payload_reads=0, new_labels=0, datasets=datasets,
                  job_id=os.environ.get('SLURM_JOB_ID'), torch_threads=torch.get_num_threads(),
                  wall_seconds=time.monotonic()-began, process_cpu_seconds=time.process_time(),
                  maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    for name, value in [('REPORT.json', report), ('BANK-ROWS.json', all_banks),
                        ('CANDIDATE-ROWS.json', candidates), ('CONSUMED-FILES.json', opened)]:
        ct.json_write(out/name, value)
    ct.seal(out)
    print(json.dumps({'completed': True, 'job_id': report['job_id'], 'wall_seconds': report['wall_seconds'],
                      'maxrss_bytes': report['maxrss_bytes']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True)
    main(parser.parse_args().out)
