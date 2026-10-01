"""Fixed source-paired estimation. No acceptable-loss or promotion flag."""
import math
import random
import statistics
from dtv_success_cost.common import CONFIGS,TASKS,SEEDS

def mean(x):return statistics.fmean(x)
def percentile(x,q):
    a=sorted(x);position=q*(len(a)-1);i=int(position)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(position-i)

def analyze(records,spec):
    indexed={}
    for e in records:
        key=(e['task'],e['source'],e['scorer_seed'],e['config'])
        if key in indexed:raise RuntimeError('duplicate scientific observation')
        indexed[key]=e
    sources={t:sorted({e['source'] for e in records if e['task']==t}) for t in TASKS}
    if any(not sources[t] for t in TASKS):raise RuntimeError('empty task')
    if len(indexed)!=sum(len(s) for s in sources.values())*3*8:raise RuntimeError('incomplete source/seed/configuration axes')
    metrics=('success','planning_seconds','solve_seconds','episode_operational_seconds','episode_elapsed_including_audit_seconds','first_decision_seconds','decisions','actions','audit_seconds','process_cpu_seconds','decision_observation_to_action_seconds','later_decision_seconds','reset_seconds','environment_construction_seconds')
    per_source={};points={};fixed_seeds={};contrasts={};draws={}
    for t in TASKS:
        for config in CONFIGS:
            vector={m:[mean([float(indexed[t,s,seed,config][m]) for seed in SEEDS]) for s in sources[t]] for m in metrics}
            per_source[t,config]=vector;points[f'{t}:{config}']={m:mean(v) for m,v in vector.items()}
            for seed in SEEDS:fixed_seeds[f'{t}:{config}:{seed}']={m:mean([float(indexed[t,s,seed,config][m]) for s in sources[t]]) for m in metrics}
        for baseline in spec['comparisons']:
            # All paired sources, not successful subsets; seed blocks remain inside source.
            contrasts[t,baseline]={m:[a-b for a,b in zip(per_source[t,'dtv30'][m],per_source[t,baseline][m])] for m in metrics}
    rng=random.Random(spec['seed'])
    # Shared whole-parent resamples for all points/contrasts and fixed model blocks.
    boots={key:[] for key in [(t,b,m) for t in TASKS+('equal_task',) for b in spec['comparisons'] for m in ('success','planning_seconds')]}
    point_boots={(t,a,m):[] for t in TASKS+('equal_task',) for a in CONFIGS for m in ('success','planning_seconds')}
    for _ in range(spec['bootstrap']):
        estimates={}
        for t in TASKS:
            indices=[rng.randrange(len(sources[t])) for _ in sources[t]]
            for a in CONFIGS:
                for m in ('success','planning_seconds'):
                    point_boots[t,a,m].append(mean([per_source[t,a][m][i] for i in indices]))
            for b in spec['comparisons']:
                for m in ('success','planning_seconds'):
                    estimates[t,b,m]=mean([contrasts[t,b][m][i] for i in indices]);boots[t,b,m].append(estimates[t,b,m])
        for b in spec['comparisons']:
            for m in ('success','planning_seconds'):boots['equal_task',b,m].append(mean([estimates[t,b,m] for t in TASKS]))
        for a in CONFIGS:
            for m in ('success','planning_seconds'):point_boots['equal_task',a,m].append(mean([point_boots[t,a,m][-1] for t in TASKS]))
    result={}
    for (t,b,m),v in boots.items():
        point=mean(contrasts[t,b][m]) if t!='equal_task' else mean([mean(contrasts[k,b][m]) for k in TASKS])
        q=spec['alpha']/(2*spec['family_size'])
        result[f'{t}:dtv30-minus-{b}:{m}']=dict(estimate=point,nominal_percentile95=[percentile(v,.025),percentile(v,.975)],
                    bonferroni_percentile_family=[percentile(v,q),percentile(v,1-q)],finite_sample_guarantee=False)
    for a in CONFIGS:points[f'equal_task:{a}']={m:mean([points[f'{t}:{a}'][m] for t in TASKS]) for m in metrics}
    for (t,a,m),v in point_boots.items():points[f'{t}:{a}'][m+'_nominal95']=[percentile(v,.025),percentile(v,.975)]
    return dict(study='DTV-EFF1',status='fixed_complete_estimation',sources={t:len(v) for t,v in sources.items()},
                episode_count=len(records),points=points,fixed_checkpoint_blocks=fixed_seeds,contrasts=result,
                source_effects={f'{t}:{b}':[dict(source=s,parent=indexed[t,s,SEEDS[0],'dtv30']['parent'],**{m:v[i] for m,v in vector.items()}) for i,s in enumerate(sources[t])] for (t,b),vector in contrasts.items()},
                all_episode_summaries=records,analysis=spec,noninferiority_claim=False,independent_training_seed_inference=False,
                no_success_conditioned_filter=True,outcome_informed=True,no_model_promotion=True)

def precision(n=320):
    # q >= |d| is necessary for a binary pair. Exclude impossible combinations
    # and the zero-loss boundary rather than quietly presume no losses.
    return [dict(discordance=q,difference=d,gain_probability=(q+d)/2,loss_probability=(q-d)/2,
                 task_nominal_halfwidth=1.96*math.sqrt((q-d*d)/n),equal_task_nominal_halfwidth=1.96*math.sqrt((q-d*d)/(3*n)))
            for q in (.02,.05,.10,.20,.40) for d in (.01,.02,.03) if q>d]
