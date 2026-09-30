"""Build immutable metadata bindings and compact historical timing ledger."""
import base64, hashlib, json, subprocess, time
from pathlib import Path
from recover import ROOT, OUT

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def save(name,value):
    p=ROOT/'docs/dtv-efficiency-20260930'/name
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')

def main():
    started=time.monotonic(); bindings=[]; fetch=[]; byte_specs=[]; timings=[]
    authenticated=json.loads((OUT/'AUTHENTICATED-BYTES.json').read_text())
    for task in ('pusht','reacher','cube'):
        capture_path=next(OUT.glob(f'results/acid-alternative/diagnostics/{task}/d1-b0-candidate-pools/*/manifest.json'))
        score_path=next(OUT.glob(f'results/acid-alternative/diagnostics/{task}/d1-candidate-scores/*/manifest.json'))
        c=json.loads(capture_path.read_text());s=json.loads(score_path.read_text())
        v=next(OUT.glob(f'results/acid-alternative/v3-d2/stage-a/{task}/shared-score/*/manifest.json'))
        v=json.loads(v.read_text())
        vc=next(OUT.glob(f'results/acid-alternative/v3-d2/stage-a/{task}/capture/*/manifest.json'))
        vc=json.loads(vc.read_text())
        for value,key in [(c,'eval_manifest'),(vc,'eval_manifest')]:
            fetch.append(value[key])
        for value in (s,v):
            byte_specs.append(dict(path=value['artifact'],sha256=value['artifact_sha256'],kind='saved_score_input'))
        for seed in (6101,6102,6103):
            models={}
            for arm in ('acid','diffusion','forward'):
                p=next(OUT.glob(f'results/acid-alternative/scorers/{task}/{arm}/true/seed-{seed}-*/summary.json'))
                m=json.loads(p.read_text())
                models[arm]={k:m[k] for k in ('checkpoint','checkpoint_sha256','model_config','parameter_count','seed','source_manifest_sha256','best_step','optimization')}
            bindings.append(dict(id=f'{task}-{seed}',task=task,scorer_seed=seed,planner_seed=7101,models=models,capture=c,saved_scores=s,offline_capture=vc,offline_scores=v,context_indices=[0,1],context_role='historical task-specific D1 development; first two manifest rows, fixed without outcomes',wall_limit_seconds=800,output_limit_bytes=4000000))
    # Recovered metadata only; byte hashing is not deserialization.
    remote="""
import base64,hashlib,json,pathlib,time
fetch=FETCH; specs=SPECS
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
files=[]
for path in fetch:
 p=pathlib.Path(path);b=p.read_bytes();files.append(dict(path=str(p),data=base64.b64encode(b).decode(),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
records=[]
for spec in specs:
 p=pathlib.Path(spec['path']);actual=sha(p)
 if actual!=spec['sha256']:raise RuntimeError('saved input hash mismatch')
 records.append(dict(spec,bytes=p.stat().st_size,actual_sha256=actual))
env=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/stable_worldmodel')
p=env/'policy.py';b=p.read_bytes();files.append(dict(path='runtime/stable_worldmodel/policy.py',data=base64.b64encode(b).decode(),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
print(json.dumps(dict(files=files,records=records,observed_unix=time.time())))
""".replace('FETCH',repr(fetch)).replace('SPECS',repr(byte_specs))
    r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','prometheus','python3.9 -'],input=remote.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    if r.returncode:raise RuntimeError(r.stderr.decode())
    new=json.loads(r.stdout)
    for f in new['files']:
        b=base64.b64decode(f.pop('data'));assert hashlib.sha256(b).hexdigest()==f['sha256']
        relative=f['path'].removeprefix('/lustreFS/data/superworld/ckontzias/thesis/')
        p=OUT/relative;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as o:o.write(b)
    save('INPUT-AUTHENTICATION.json',new)
    # Authenticate every recovered member against its actual executed manifest.
    source_checks=[]
    for manifest in OUT.glob('snapshots/*/SOURCE-MANIFEST.sha256'):
        entries={line.split(maxsplit=1)[1].strip().removeprefix('./'):line.split()[0] for line in manifest.read_text().splitlines()}
        checked=[]
        for name,digest in entries.items():
            p=manifest.parent/name
            if p.is_file():
                if sha(p)!=digest:raise RuntimeError('executed source member mismatch '+str(p))
                checked.append(name)
        source_checks.append(dict(path=str(manifest.relative_to(ROOT)),sha256=sha(manifest),authenticated_recovered_members=checked,unretrieved_members=len(entries)-len(checked)))
    for job in bindings:
        p=OUT/job['capture']['eval_manifest'].removeprefix('/lustreFS/data/superworld/ckontzias/thesis/')
        import csv
        rows=list(csv.DictReader(p.open(),delimiter='\t'))
        job['contexts']=[rows[i] for i in job['context_indices']]
        if sha(p)!=job['capture']['eval_manifest_sha256']:raise RuntimeError('row manifest mismatch')
    for p in OUT.glob('results/acid-alternative/latency/*/**/summary.json'):
        s=json.loads(p.read_text());task=p.relative_to(OUT).parts[3]
        for arm,a in s['results'].items():
            for field in ('verifier_only','total_cost_call','full_released_cem_solve','end_to_end_episode_wall_clock'):
                if field in a:timings.append(dict(study='D1',task=task,scorer_seed=a.get('training_seed'),arm=arm,scope=field,units='milliseconds',statistic='median and recorded quantiles',measurement=a[field],configuration=s['configuration'],runtime=s['runtime'],artifact=str(p.relative_to(OUT)),artifact_sha256=sha(p),source_manifest_sha256=s['source_manifest_sha256'],candidate_sequences=300 if 'episode' not in field else None,horizon_transitions=1500 if 'episode' not in field else None))
    for p in OUT.glob('results/acid-alternative/v3-d2/stage-a/*/frozen-scores/*/manifest.json'):
        s=json.loads(p.read_text())
        for a in s['scorers']:
            timings.append(dict(study='v3 Stage A',task=s['task'],scorer_seed=a['seed'],arm=a['arm'],scope='offline checker pass',units='seconds',statistic='one pass, not a repeated-call median',measurement=a['latency'],artifact=str(p.relative_to(OUT)),artifact_sha256=sha(p),source_manifest_sha256=s['source_manifest_sha256'],runtime=s['runtime'],candidate_sequences=15000,horizon_transitions=75000))
    for pattern in ('results/acid-alternative/e6d-allgate-controls/closed-loop/*/*/*/summary.json','results/acid-alternative/e6-d2-quantile/closed-loop/*/*/*/summary.json'):
        for p in OUT.glob(pattern):
            s=json.loads(p.read_text());timings.append(dict(study='E6D (including reused E6 anchors)',task=s['task'],scorer_seed=s['scorer_seed'],planner_seed=s['planner_seed'],arm=s['arm'],scope='50-episode evaluator',units='seconds',statistic='one evaluator total',elapsed_seconds=s['elapsed_seconds'],episode_count=s['episode_count'],cost_calls=s['cem_cost_calls'],candidate_sequences=300*s['cem_cost_calls'],horizon_transitions=1500*s['cem_cost_calls'],runtime=s['runtime'],artifact=str(p.relative_to(OUT)),artifact_sha256=sha(p),source_manifest_sha256=s['source_manifest_sha256'],warmup='not a dedicated latency warmup; evaluator execution'))
    save('HISTORICAL-TIMINGS.json',timings)
    save('SOURCE-AUTHENTICATION.json',source_checks)
    contract=dict(study='DTV-EFF0',execute=False,jobs=bindings,arms=['plain','acid','forward','legacy_dtv','d1_sigma025'],blocks=5,repetitions=2,warmup_calls=3,warmup_solves=1,offline_repetitions=2,context_count_distinct=6,context_seed_pairs=18,gpu_allocation_seconds_cap=7200,serial=True,cpu_threads=4,ram_bytes=8*1024**3,worker_output_bytes_cap=4000000,live_bytes_cap=60000000,archive_bytes_cap=62000000,inclusive_new_bytes_cap=250000000,utility_min_solver_fraction=0.10,rtol=1e-6,atol=1e-6,runtime=authenticated['runtime'],source_manifests=source_checks)
    save('BINDINGS.json',contract)
    save('EXECUTION-APPROVAL.json',dict(execute=False,study='DTV-EFF0',bindings_sha256=sha(ROOT/'docs/dtv-efficiency-20260930/BINDINGS.json'),research_execution_authorized=False,preparation_only=True))
    save('PREPARATION-PASS.json',dict(local_wall_seconds=time.monotonic()-started,torch_deserialization=False,physics=False,gpu=False))
    print('jobs',len(bindings),'timing_records',len(timings),'new_input_byte_records',len(new['records']))
if __name__=='__main__':main()
