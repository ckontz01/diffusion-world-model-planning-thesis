"""Check recovered executed metadata; no tensor deserialization or new outcomes."""
import json,statistics,time
from pathlib import Path
from dtv_efficiency.profile import DOC,sha

def main():
    start=time.monotonic();c=json.loads((DOC/'BINDINGS.json').read_text());rows=[]
    for p in (DOC/'evidence').glob('results/acid-alternative/sensitivity/d1/*/pop300-lambda007-sigma025/diffusion/*/summary.json'):
        s=json.loads(p.read_text());task=p.relative_to(DOC/'evidence').parts[4];seed=s['scorer_training_seed'];j=next(x for x in c['jobs'] if x['task']==task and x['scorer_seed']==seed);r=s['resolved_config']
        expected=dict(cem_samples=300,cem_steps=30,cem_topk=30,diffusion_sigmas=[.25],lambda_weight=.07,horizon=5,action_block=5)
        if any(r[k]!=v for k,v in expected.items()) or s['scorer_checkpoint_sha256']!=j['models']['diffusion']['checkpoint_sha256'] or s['source_manifest_sha256']!='52acea39e4a1f6dadfa5d5be4ec6206a9aefb46159e5def7355a8575f0062f1d':raise RuntimeError('single-noise executed identity mismatch')
        rows.append(dict(task=task,scorer_seed=seed,planner_seed=s['planner_seed'],config=r,checkpoint=s['scorer_checkpoint'],checkpoint_sha256=s['scorer_checkpoint_sha256'],artifact=str(p.relative_to(DOC/'evidence')),artifact_sha256=sha(p),elapsed_seconds=s['elapsed_seconds'],scope='24-source batched evaluator, NOT dedicated checker/solver latency',cost_calls=s['cem_cost_calls'],episode_count=s['episode_count'],recorded_successes=s['success_count'],runtime=s['runtime']))
    if len(rows)!=9:raise RuntimeError('single-noise grid missing')
    with (DOC/'SINGLE-NOISE-EXECUTIONS.json').open('x') as f:json.dump(rows,f,indent=2)
    timing=json.loads((DOC/'HISTORICAL-TIMINGS-VERIFIED.json').read_text())
    for task in ('pusht','reacher','cube'):
        selected=[r for r in timing if r['study']=='D1' and r['task']==task and r['arm'] in ('acid','diffusion','forward','b0')]
        print(task,[(r['arm'],r['scope'],r['measurement']['median_ms']) for r in selected])
    print('E6D exact totals',[(r['task'],r['arm'],r['elapsed_seconds']) for r in timing if r['study'].startswith('E6D')])
    stage=json.loads((DOC/'evidence/results/acid-alternative/v3-d2/stage-a/analysis/job-297565/summary.json').read_text())
    print('stage_a_compute_profile',json.dumps(stage['scorer_compute_profile'],indent=2))
    with (DOC/'METADATA-AUDIT.json').open('x') as f:json.dump(dict(status='passed',single_noise_execution_count=9,all_hash_config_seed_bindings_verified=True,local_wall_seconds=time.monotonic()-start),f,indent=2)
if __name__=='__main__':main()
