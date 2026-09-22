"""Fixed artificial stress cases; complete results, never research-data execution."""
import hashlib
import json
import math
from pathlib import Path
import random
from controls import TablePredictor, Simultaneous, LearnThenTest, point, metrics
from pc_racp import BinaryPCRACP
from planning import cem, shortlist, native_path

ROOT = Path(__file__).resolve().parent


def rows(case, seed, role, n):
    rng = random.Random(f'{case}|{seed}|{role}')
    result = []
    for j in range(n):
        c = rng.randrange(16)
        p = [.45+.01*c] + [.40+.025*((c+a)%8) for a in range(1,8)]
        if case == 'shared_error':
            common = rng.choice([-.18,.18])
            p = [v+common for v in p]
        if case == 'rare_override': p = [.80]+[.20]*7
        if case == 'sparse_binary': p = [.01]+[.005+.001*a for a in range(1,8)]
        if case == 'progress_conflict': p = [.70,.15,.80,.40,.40,.40,.40,.40]
        if case == 'sequential_shift': p = [.50,.80,.40,.40,.40,.40,.40,.40]
        # Shared U defines paired counterfactual draws; sources are independent.
        u = rng.random()
        result.append(dict(id=f'{case}/{seed}/{role}/{j}', context=c, truth=p,
                           outcomes=[int(u < v) for v in p], logged_action=rng.randrange(8),
                           prediction_seed=rng.getrandbits(64)))
    return result


def predict(model, r, case):
    p = list(model.predict(r['context']))
    rng = random.Random(r['prediction_seed'])
    # Deliberate, predeclared prediction-channel perturbations. Applied identically
    # to EVERY checker and every learn/calibration/test source, not outcome tuning.
    if case == 'optimistic_search':
        p = [min(.999, max(.001,v+rng.gauss(0,.30))) for v in p]
    if case == 'rare_override' and rng.random() < .02:
        p[1] = .99
    return tuple(p)


def one(case, seed, config):
    splits = {k:rows(case,seed,k,n) for k,n in config['sources_per_seed_scenario'].items()}
    all_ids = [r['id'] for part in splits.values() for r in part]
    assert len(all_ids) == len(set(all_ids))
    fit = TablePredictor(splits['fit'])
    logged_fit = TablePredictor(splits['fit'], logged=True)
    pred = {k:[predict(fit,r,case) for r in rr] for k,rr in splits.items() if k != 'fit'}
    logged_pred = {k:[predict(logged_fit,r,case) for r in rr] for k,rr in splits.items() if k != 'fit'}
    calibration = list(zip(pred['calibration'],[r['outcomes'] for r in splits['calibration']]))
    simultaneous = Simultaneous.calibrate(calibration,config['alpha'])
    ltt = LearnThenTest.calibrate(calibration, config['ltt_thresholds'],config['alpha'],config['delta'])
    pcs = {}
    for label, pp, complete in [('pc_complete',pred,True),('pc_logged',logged_pred,False)]:
        pc = BinaryPCRACP(pp['learn'],config['alpha'])
        pc.calibrate([(p,r['outcomes'],r['logged_action'],(.125,)*8)
                      for p,r in zip(pp['calibration'],splits['calibration'])], complete_branch=complete)
        pcs[label] = [pc.predict(p) for p in pp['test']]
    test = splits['test']
    choices = {'baseline':[0]*len(test), 'point':[point(p) for p in pred['test']],
               'point_logged':[point(p) for p in logged_pred['test']],
               'simultaneous':[simultaneous.choose(p) for p in pred['test']],
               'ltt':[ltt.choose(p) for p in pred['test']]}
    for label, pp in pcs.items(): choices[label] = [d['action'] for d in pp]
    results = {label:metrics(test,aa) for label,aa in choices.items()}
    for label, pp in pcs.items():
        results[label].update(coverage=sum(r['outcomes'][d['action']] in d['sets'][d['action']]
                                          for r,d in zip(test,pp))/len(test),
                              nonzero_certificate_fraction=sum(d['certificate'] > 0 for d in pp)/len(test),
                              calibration_sources=pp[0]['calibration_sources'], beta_hat=pp[0]['beta_hat'])
    results['simultaneous']['simultaneous_advantage_coverage'] = sum(
        all(y[i]-y[0] >= b for i,b in enumerate(simultaneous.bounds(p)))
        for p,y in zip(pred['test'],[r['outcomes'] for r in test]))/len(test)
    diagnostics = {}
    if case == 'progress_conflict':
        diagnostics = {'short_progress_selector_slot':1, 'short_progress_success_probability':.15,
                       'full_success_point_oracle_slot':2,'oracle_success_probability':.8}
    if case == 'sequential_shift':
        # Two-step probability tree, NOT a physics simulator. After any override,
        # a repeated checker reaches a new law where its chosen alternative has
        # success .10, while the fixed baseline tail has success .80. The first
        # intervention outcomes above concern only that fixed tail.
        diagnostics = {'training_context':'unshifted', 'after_override_context':'new-state',
                       'single_intervention_fixed_tail_success':.8,
                       'repeat_override_shifted_success':.1,
                       'reuse_of_old_certificate_on_shifted_state_authorized':False}
        for name, aa in choices.items():
            results[name]['two_step_repeated_policy_known_success'] = sum(.5 if a==0 else .1 for a in aa)/len(aa)
    digest = hashlib.sha256(json.dumps(splits,sort_keys=True).encode()).hexdigest()
    return dict(case=case,seed=seed,source_data_sha256=digest,metrics=results,
                simultaneous_q=simultaneous.q,ltt_tests=ltt.tests,ltt_accepted=ltt.accepted,
                scenario_diagnostics=diagnostics)


def native_demo(config):
    cfg = config['cem_artificial']
    def cost(obs, bank):
        goal = [sum((obs+a-1)**2 for a in row) for row in bank]
        # Artificial inverse F/G mismatch, not an actual physics/world model.
        residual = [sum((2*a)**2 for a in row)/len(row) for row in bank]
        return goal,residual
    def plan(obs, acid=False):
        return cem(obs,cost,seed=cfg['seed'], dimensions=cfg['dimensions'],population=cfg['population'],
                   elites=cfg['elites'],iterations=cfg['iterations'],acid=acid,lam=cfg['lambda'])
    def step(obs,a): return obs+.2*a[0],False,False
    b,a=plan(0),plan(0,True)
    return dict(baseline=b.__dict__,acid=a.__dict__,shortlist=shortlist(b).__dict__,
                native_baseline_trace=native_path(0,plan,step,3),
                native_acid_trace=native_path(0,lambda o:plan(o,True),step,3),
                note='Arithmetic callbacks only; not simulator evidence or a Le-WM parity claim')


def run():
    config=json.loads((ROOT/'CONTRACT.json').read_text())
    result=dict(contract_sha256=hashlib.sha256((ROOT/'CONTRACT.json').read_bytes()).hexdigest(),
                classification='finite artificial draws; no scientific efficacy or theorem validation',
                results=[one(case,seed,config) for case in config['scenarios'] for seed in config['seeds']],
                native_arithmetic_demo=native_demo(config),
                sample_requirements={
                    'simultaneous_min_for_finite_95pct_rank':19,
                    'ltt_zero_harm_overrides_one_rule_95pct':math.ceil(math.log(.05)/math.log(.95)),
                    'ltt_zero_harm_overrides_five_rules_95pct':math.ceil(math.log(.05/5)/math.log(.95)),
                    'sources_expected_at_2pct_override_five_rules':math.ceil(math.log(.05/5)/math.log(.95)/.02),
                    'sources_expected_for_19_uniform_logged_matches':152,
                    'warning':'Expected counts are not finite-sample guarantees of enough overrides/matches.'})
    with (ROOT/'ARTIFICIAL-RESULTS.json').open('x',encoding='utf8') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'cases':len(result['results']),'sources':sum(config['sources_per_seed_scenario'].values())*18}))


if __name__=='__main__':run()
