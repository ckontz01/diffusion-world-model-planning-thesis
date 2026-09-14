"""Read ONLY selected historical call timings from the existing external archive.

No model/physics execution; ignore all unselected tar payloads. Output is a
planning-input receipt, never an estimate of efficacy under the new intervention.
"""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path
import numpy as np
from single_anchor_ranking import REFS, COMBINED_SHA, bounds
from diffusion_bottleneck import require, require_sha


def estimate(archive, combined):
    require_sha(combined,COMBINED_SHA)
    cert=json.loads(combined.read_text())
    tasks={f'stage-0/task-{r//64:04d}/results/RESULT.json' for r in REFS}
    seen=set();full=[];last=[];records=[]
    with tarfile.open(archive,'r|') as tar:
        for member in tar:
            if member.name not in tasks: continue
            require(member.isfile() and member.name not in seen and member.size<20_000_000,'Tar member')
            seen.add(member.name)
            payload=tar.extractfile(member).read()
            refs=[r for r in REFS if member.name==f'stage-0/task-{r//64:04d}/results/RESULT.json']
            digest=hashlib.sha256(payload).hexdigest()
            require(all(cert['historical_result_sha256'][str(r)]==digest for r in refs),'Historical shard identity')
            obj=json.loads(payload)
            require(obj['arm']=='vad_continuation' and obj['train_seed']==7201,'Historical arm')
            for r in obj['rows']:
                if r['reference_index'] not in refs:continue
                require(r['failure'] is None,'Historical technical failure')
                for c in r['calls']:
                    value=c['seconds'];require(np.isfinite(value) and value>=0,'Timing')
                    (full if c['diagnostics']['delta']>=30 else last).append(value)
                records.append({'reference':r['reference_index'],'horizon':r['horizon'],
                    'call_count':len(r['calls']),'call_seconds':sum(c['seconds'] for c in r['calls'])})
            if seen==tasks:break
    require(seen==tasks and len(records)==64 and full and last,'Missing selected timings')
    stats=lambda v:dict(n=len(v),mean=float(np.mean(v)),p50=float(np.median(v)),p95=float(np.quantile(v,.95)),maximum=float(max(v)))
    b=bounds(2);f,l=stats(full),stats(last)
    scenarios=[]
    for label,fc,lc in [('historical_mean',f['mean'],l['mean']),('historical_p95',f['p95'],l['p95']),
                        ('twice_p95',2*f['p95'],2*l['p95']),
                        ('historical_max_every_call',f['maximum'],l['maximum'])]:
        seconds=b['continuation_calls']*fc+b['first_only_calls']*lc
        # Explicit, unmeasured setup/physics/serialization allowances. Not fitted.
        overhead=64*30+b['physical_steps']*.02
        scenarios.append({'scenario':label,'planner_seconds_upper_call_count':seconds,
                          'assumed_other_seconds':overhead,'total_seconds':seconds+overhead})
    return {'selected_historical_timings_only':True,'archive':str(archive),
        'combined_sha256':COMBINED_SHA,'historical_rows':records,'continuation_solve_seconds':f,
        'first_only_solve_seconds':l,'two_repeat_bounds':b,'planning_scenarios':scenarios,
        'assumptions':['Measured synchronized historical solve wall, not total allocation or kernel time.',
          'New branch observations/termination and cluster load can change timing; no new real execution performed.',
          '30s/process nonplanning setup plus0.02s/primitive step are assumptions, not measured new-interface costs.',
          'Upper call counts include both independent arm prefixes and cycle-final first-only calls.'],
        'new_model_or_physics_execution':False}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('archive','combined','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=estimate(a.archive,a.combined)
    with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True,allow_nan=False)
