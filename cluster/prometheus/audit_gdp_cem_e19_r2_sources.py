"""Read-only R1 warning and pinned source audit; creates no environments."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path('/lustreFS/data/superworld/ckontzias/thesis')
P=ROOT/'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0'
OLD=ROOT/'experiments/gdp-cem-e19-r1/run-20260905-2c5ea97a'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    h,n=(p.parent/'sha256.txt').read_text().strip().split(maxsplit=1)
    assert h==sha(p) and n==p.name
    return json.loads(p.read_text())
def audit_observation(obs,stack):
    fields={}
    for k,size in [('proprio',4),('state',7)]:
        x=obs[k]; v=np.asarray(x['values'])
        low=np.zeros(size); high=np.full(size,512.)
        if k=='state': high[4]=2*np.pi
        if stack=='sage': low[-2:]=-512
        repaired_low=low.copy(); repaired_low[-2:]=-512
        fields[k]=dict(dtype=x['dtype'],shape=x['shape'],finite=bool(np.isfinite(v).all()),
            below=np.flatnonzero(v<low).tolist(),above=np.flatnonzero(v>high).tolist(),
            native_contains=bool(v.shape==(size,) and x['dtype']=='float64' and np.all(v>=low) and np.all(v<=high)),
            signed_velocity_bounds_contains=bool(v.shape==(size,) and x['dtype']=='float64' and np.all(v>=repaired_low) and np.all(v<=high)),values=v.tolist())
    return fields
def main(out):
    source={}
    files={'sage_cube':P/'official-sage/sage/eval/cube.py',
        'sage_pusht':P/'official-sage/sage/eval/pusht.py',
        'sage_world':P/'official-sage/stable_worldmodel/world/world.py',
        'sage_env':P/'official-sage/stable_worldmodel/envs/pusht/env.py',
        'e18_env':ROOT/'envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/stable_worldmodel/envs/pusht/env.py',
        'passive_checker':ROOT/'envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/gymnasium/utils/passive_env_checker.py',
        'r1_harness':ROOT/'snapshots/gdp-cem-e19-r1-549757ef959a79ba/gdp_cem_e19_r1.py'}
    for name,p in files.items():
        text=p.read_text(); tree=ast.parse(text)
        source[name]=dict(path=str(p),sha256=sha(p),
            relevant_functions={n.name:ast.get_source_segment(text,n) for n in ast.walk(tree)
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in
                ('main','set_determinism','evaluate','_evaluate_from_dataset','_set_state','check_obs','env_step_passive_checker')})
    traces=[]
    for stack in ('sage','e18'):
        for case in range(3):
            for repeat in (0,1):
                path=OLD/stack/f'case-{case}'/f'repeat-{repeat}'/'TRACE.json'; t=read(path)
                checks=[dict(stage=e['stage'],fields=audit_observation(e['observation'],stack)) for e in t['events'] if e['stage'].startswith('after_step:')]
                assert len(checks)==15
                traces.append(dict(stack=stack,case=case,repeat=repeat,path=str(path),sha256=sha(path),checks=checks))
    allchecks=[r['fields'] for t in traces for r in t['checks']]
    payload=dict(source=source,traces=traces,observations_checked=len(allchecks),
        observations_outside_native_bounds=sum(not all(f['native_contains'] for f in c.values()) for c in allchecks),
        all_match_signed_velocity_bounds=all(f['signed_velocity_bounds_contains'] for c in allchecks for f in c.values()),
        r1_cube_calls_pusht_global_determinism=True,official_cube_has_no_global_determinism_call=True,
        official_cube_local_cem_generator_seeded=True,
        r1_cube_evaluate_seed_32_ignored_in_dataset_dispatch=True,
        caveat='R1 Cube is an additionally globally seeded engineering diagnostic, not exact official entry-point seeding; no native global-seeding effect is inferred.',
        simulator_executed=False,planning=False,protected_read=False,historical_results_changed=False,
        audit_source_sha256=sha(Path(__file__)))
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f: json.dump(payload,f,indent=2,sort_keys=True); f.write('\n')
    with (out.parent/'sha256.txt').open('x') as f:f.write(sha(out)+'  '+out.name+'\n')
    print(json.dumps({k:v for k,v in payload.items() if k not in ('source','traces')}))
if __name__=='__main__': main(Path(sys.argv[1]))
