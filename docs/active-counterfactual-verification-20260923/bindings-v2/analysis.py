"""Independent32-source reporting. No checkpoint/reference/physics access."""
import common as c
import numpy as np
from verify import load_verify


def aggregate(run,authorization=None):
    jobs=c.grid(); outcomes={}; checks=[];decisions=[];predictive=[]
    from fitting import load_models
    from policy import context,features
    from tree import Node
    joint,ordinary,bayes=load_models(run)
    for j in jobs[:-1]:
        c.verify_seal(run/j['key'],j)
        if j['stage'] in ('collection','evaluation'):
            arrays,m,check=load_verify(run/j['key'],authorization=authorization);checks.append(check)
            if j['stage']=='evaluation':
                c.require(m['reference']==j['reference'] and m['control']==j['control'],'Evaluation cell identity')
                key=(j['reference'],j['control']);c.require(key not in outcomes,'Duplicate cell')
                outcomes[key]=check['successes'][0]
                b=m['branches'][0]
                decisions.append({'reference':j['reference'],'control':j['control'],'prefix':b['prefix'],
                                  'suffix':b['suffix'],'steps':b['steps'],'terminal_prefix':b['steps']<=5,
                                  'terminal_suffix':5<b['steps']<=15,'native_success':check['successes'][0]})
                if b['prefix'] is not None:
                    p=b['prefix'];n=int(arrays['tree/count'][p])
                    node=Node(arrays['tree/prefix'][p],tuple(arrays['tree/suffix'][p,:n]),arrays['tree/predicted_prefix'][p],
                              tuple(arrays['tree/predicted_terminal'][p,:n]),tuple('saved' for _ in range(n)))
                    h=context([arrays['b0/initial_latent']],[],arrays['goal_latent'],0);x,a=features(h,node)
                    observed=b['steps']>5;res=(arrays['b0/latent'][4]-node.predicted_prefix)[None] if observed else None
                    prediction=joint.forward(x,a,res)[0]
                    row={'reference':j['reference'],'control':j['control'],'actual_selected_prefix':p,
                         'terminal_ce':float(-np.log(max(prediction['terminal'][0,2 if observed else 0],1e-300))),
                         'conditional_response_nll_per_coordinate':None,'bce':None,'brier':None}
                    if observed:
                        q=prediction['q'][0,b['suffix']]
                        if j['control']=='ordinary':q=ordinary.forward(x,a,res)[0][0,b['suffix']]
                        if j['control']=='bayesian':q=bayes.predict(x,a,res)[0,b['suffix']]
                        q=float(np.clip(q,1e-12,1-1e-12));y=check['successes'][0]
                        row.update(conditional_response_nll_per_coordinate=float(-prediction['log_density'][0]/192),
                                   bce=float(-y*np.log(q)-(1-y)*np.log1p(-q)),brier=float((q-y)**2))
                    predictive.append(row)
    refs=c.roles()['final_development'];arms=c.CONTROLS
    c.require(len(outcomes)==256,'All32x8 outcomes')
    y=np.array([[outcomes[r,a] for a in arms] for r in refs],np.int64)
    rng=np.random.default_rng(94301); indices=rng.integers(0,32,(10000,32))
    comparisons={}
    for control in ('ordinary','bayesian','early-replan'):
        effect=y[:,arms.index('active')]-y[:,arms.index(control)]
        draws=effect[indices].mean(1)
        comparisons['active-minus-'+control]={'source_effects':effect.tolist(),'mean':float(effect.mean()),
            'gains':int((effect==1).sum()),'losses':int((effect==-1).sum()),'ties':int((effect==0).sum()),
            'nominal95':np.quantile(draws,[.025,.975]).tolist(),
            'nominal_bonferroni98_333':np.quantile(draws,[.05/6,1-.05/6]).tolist()}
    rows=c.read(run/'PRE-ANALYSIS-ACCOUNTING.json')['jobs']
    c.require(len(rows)==338 and [r['spec'] for r in rows]==jobs[:-1],'Complete allocation grid before analysis')
    c.require(len({r['job'] for r in rows})==338,'Unique allocation IDs')
    return {'status':'developmental pilot, not untouched confirmation','source_ids':refs,'controls':arms,
            'binary_outcomes_by_source':y.tolist(),'success_mean':dict(zip(arms,y.mean(0).tolist())),
            'primary_comparisons':comparisons,'bootstrap_seed':94301,'resamples':10000,
            'supporting_active_minus':{control:(y[:,arms.index('active')]-y[:,arms.index(control)]).tolist()
                                      for control in ('vanilla','static','passive','no_update')},
            'chosen_branches_and_endpoints':decisions,'observed_prefix_predictive_diagnostics':predictive,
            'predictive_scope':'Descriptive actual selected prefix/suffix only. Conditional model diagnostics do not supply unavailable branch outcomes or alter deployed decisions.',
            'interval_interpretation':'Nominal small-development summaries, not finite-sample simultaneous-coverage proof',
            'source_is_statistical_unit':True,'independent_checks':checks,
            'allocation_before_analysis':{'gpu_seconds':sum(r['seconds'] for r in rows if r['spec']['gpu']),
                                          'cpu_seconds':sum(r['seconds'] for r in rows if not r['spec']['gpu'])},
            'analysis_allocation':'Charged in controller COMPUTE-COMPLETE.json after this job terminates',
            'all_worker_resources':{j['key']:c.read(run/j['key']/'TECHNICAL.json') for j in jobs[:-1]}}
