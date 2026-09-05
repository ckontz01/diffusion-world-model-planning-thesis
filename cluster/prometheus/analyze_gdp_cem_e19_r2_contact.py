"""Describe all eight sealed contact reconstructions; no performance metric."""
import json
from pathlib import Path
import sys
import numpy as np
from analyze_gdp_cem_e19_r1 import read,sha,array,delta,differences,stages
from analyze_gdp_cem_e19_r2 import center_of_mass,requested_checks

def event(t,stage,phase=None):
    events=[e for e in t['events'] if e['stage']==stage and (phase is None or e['phase']==phase)]
    assert len(events)==1
    return events[0]
def main(run,out):
    records={};inventory={}
    for stack in ('sage','e18'):
        for geometry in (0,1):
            for repeat in (0,1):
                p=run/stack/f'geometry-{geometry}'/f'repeat-{repeat}'/'CONTACT.json'
                t=read(p);assert (t['stack'],t['geometry_repeat'],t['repeat'])==(stack,geometry,repeat)
                assert t['physics_steps']==4 and t['primitive_actions']==0
                assert not any(t[k] for k in ('goal_or_model_inference','production_correction','protected_read','historical_reset_rng_reconstructed'))
                inventory[str(p)]=sha(p);records[stack,geometry,repeat]=t
    rows=[];pairs=[]
    for (stack,geometry,repeat),t in records.items():
        p=Path(t['old_trace_path']);old=read(p);assert sha(p)==t['old_trace_sha256']
        prior=stages(old);prime=event(t,'primed');restored=event(t,'restored')
        pre=event(t,'before_physics','dataset_restore');post=event(t,'after_physics','dataset_restore')
        target=array(restored['requested'])
        inferred={}
        for body in ('agent','block'):
            a,b=pre['physical']['bodies'][body],post['physical']['bodies'][body]
            inferred[body]=dict(linear=( (center_of_mass(b)-center_of_mass(a))/pre['dt']-array(a['velocity']) ).tolist(),
                angular=float((array(b['angle'])-array(a['angle']))/pre['dt']-array(a['angular_velocity'])),
                note='kinematically inferred from pinned native position-update formula, not a direct private-cache measurement')
        row=dict(stack=stack,geometry_repeat=geometry,repeat=repeat,case_id=t['case_id'],
            old_trace_sha256=sha(p),before_assignment_checks=requested_checks(pre,target),
            primed_vs_r1_reset_bodies=differences(prime['physical']['bodies'],prior['after_reset#0']['physical']['bodies']),
            restored_vs_r1_bodies=differences(restored['physical']['bodies'],prior['after_hook:_set_state#0']['physical']['bodies']),
            after_assignment_checks=requested_checks(restored,target),
            inferred_bias=inferred,primed_bodies=prime['physical']['bodies'],
            before_physics_bodies=pre['physical']['bodies'],after_physics_bodies=post['physical']['bodies'],
            chipmunk_version=t['chipmunk_version'],source_sha256=t['source_sha256'])
        rows.append(row)
    for stack in ('sage','e18'):
        for geometry in (0,1):
            a,b=[records[stack,geometry,r] for r in (0,1)]
            pairs.append(dict(stack=stack,geometry_repeat=geometry,
                restored_body_differences=differences(event(a,'restored')['physical']['bodies'],event(b,'restored')['physical']['bodies'])))
    payload=dict(inventory=inventory,rows=rows,pairs=pairs,initializations=8,physics_steps=32,primitive_actions=0,
        production_correction=False,protected_read=False,source_sha256=sha(Path(__file__)))
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(payload,f,indent=2,sort_keys=True);f.write('\n')
    with (out.parent/'sha256.txt').open('x') as f:f.write(sha(out)+'  '+out.name+'\n')
    print(json.dumps([dict(stack=r['stack'],geometry=r['geometry_repeat'],repeat=r['repeat'],
        prime_differences=len(r['primed_vs_r1_reset_bodies']),restore_differences=len(r['restored_vs_r1_bodies']),
        inferred_bias=r['inferred_bias']['block']) for r in rows]))
if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
