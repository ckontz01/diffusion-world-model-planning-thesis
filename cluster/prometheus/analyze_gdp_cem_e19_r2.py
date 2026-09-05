"""Sealed R2 boundary/seed analysis, never a performance summary."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from analyze_gdp_cem_e19_r1 import read,sha,array,delta,differences,core,stages

def event(t,stage,role=None):
    found=[e for e in t['events'] if e['stage']==stage and (role is None or e.get('role')==role)]
    assert len(found)==1,(stage,role,len(found))
    return found[0]
def requested_checks(e,target):
    b=e['physical']['bodies']
    return {k:delta(actual,wanted) for k,actual,wanted in (
        ('agent.position',b['agent']['position'],target[:2]),
        ('block.position',b['block']['position'],target[2:4]),
        ('block.angle',b['block']['angle'],target[4]),
        ('agent.velocity',b['agent']['velocity'],target[-2:]))}
def center_of_mass(body):
    angle=float(array(body['angle'])); cog=array(body['center_of_gravity'])
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    return array(body['position'])+rotation@cog
def one(t,interface):
    pre=event(t,'before_setter_physics','dataset'); post=event(t,'after_setter_physics','dataset')
    target=array(event(t,'setter_entry','dataset')['requested'])
    entry=event(t,'setter_entry','dataset')
    unchanged_fields={}
    for body in ('agent','block'):
        for field in ('velocity','angular_velocity','force','torque','center_of_gravity'):
            if (body,field)==('agent','velocity'): continue
            unchanged_fields[body+'.'+field]=delta(entry['physical']['bodies'][body][field],pre['physical']['bodies'][body][field])
    motion={}
    for body in ('agent','block'):
        a,b=pre['physical']['bodies'][body],post['physical']['bodies'][body]
        move=array(b['position'])-array(a['position'])
        velocity_dt=array(a['velocity'])*pre['dt']
        motion[body]=dict(position_change=move.tolist(),velocity_dt=velocity_dt.tolist(),
            position_residual=(move-velocity_dt).tolist(),
            center_of_mass_change=(center_of_mass(b)-center_of_mass(a)).tolist(),
            center_of_mass_residual=(center_of_mass(b)-center_of_mass(a)-velocity_dt).tolist(),
            angle_change=float(array(b['angle'])-array(a['angle'])),
            angular_velocity_dt=float(array(a['angular_velocity'])*pre['dt']))
    first=stages(interface)['before_first_action#0']
    return dict(before=requested_checks(pre,target),after=requested_checks(post,target),
        untouched_by_assignments=unchanged_fields,motion=motion,
        after_reset=event(t,'native_reset_return'),before_physics=pre,after_physics=post,
        fresh_vs_supplied=delta(first['fresh_observation'],target),
        delivered_action=event(t,'native_action_return')['action'],
        observation_check=event(t,'native_action_return')['observation_check'])
def main(run,out):
    inventory={}; records={}; singles=[]; pairs=[]
    # Verify the entire 24-run barrier before comparing values.
    for stack in ('sage','e18'):
        for cid in (0,1):
            for mode in ('native','seed32','seed33'):
                for repeat in (0,1):
                    base=run/stack/f'case-{cid}'/mode/f'repeat-{repeat}'
                    p=base/'localization/LOCALIZATION.json'; q=base/'interface/TRACE.json'
                    t,i=read(p),read(q); inventory.update({str(p):sha(p),str(q):sha(q)})
                    assert (t['stack'],t['case_id'],t['mode'],t['repeat'])==(stack,cid,mode,repeat)
                    assert t['interface_sha256']==sha(q) and t['setter_calls']==3 and t['post_restoration_steps']==1
                    assert i['steps']==1 and i['fixed_return_calls']==1 and i['stopped_at_cap']
                    assert not any(t[k] for k in ('planning','model_change','protected_read','confirmation_read','production_correction','integration_functions_replaced'))
                    for stage in ('setter_entry','before_setter_physics','after_setter_physics','setter_return'): event(t,stage,'dataset')
                    assert sum(e['stage']=='after_setter_line' and e.get('source')=='self.block.position = pos_block' for e in t['events'])==3
                    for index in range(3):
                        assignment=[e for e in t['events'] if e['stage']=='after_setter_line' and e.get('setter')==index and e.get('source')=='self.block.position = pos_block']
                        boundary=[e for e in t['events'] if e['stage']=='before_setter_physics' and e.get('setter')==index]
                        assert len(assignment)==len(boundary)==1
                        assert assignment[0]['physical']==boundary[0]['physical']
                    records[stack,cid,mode,repeat]=(t,i)
    for (stack,cid,mode,repeat),(t,i) in records.items():
        singles.append(dict(stack=stack,case=cid,mode=mode,repeat=repeat,**one(t,i)))
    for stack in ('sage','e18'):
        for cid in (0,1):
            for mode in ('native','seed32','seed33'):
                a,b=[records[stack,cid,mode,r][0] for r in (0,1)]
                comp=[]
                for stage,role in [('native_reset_return',None),('setter_entry','dataset'),('before_setter_physics','dataset'),('after_setter_physics','dataset'),('native_action_return',None)]:
                    x,y=event(a,stage,role),event(b,stage,role)
                    comp.append(dict(stage=stage,core=differences(core(x['physical']),core(y['physical'])),
                        outside=differences(x['physical']['outside'],y['physical']['outside']),
                        rng=differences(x['rng'],y['rng']),shapes=differences(x['shapes'],y['shapes'])))
                pairs.append(dict(stack=stack,case=cid,mode=mode,comparisons=comp,
                    actions_exact=event(a,'native_action_return')['action']==event(b,'native_action_return')['action']))
    cross_seed=[]
    for stack in ('sage','e18'):
        for cid in (0,1):
            a,b=[records[stack,cid,m,0][0] for m in ('seed32','seed33')]
            cross_seed.append(dict(stack=stack,case=cid,comparisons=[dict(stage=s,
                core=differences(core(event(a,s,'dataset')['physical']),core(event(b,s,'dataset')['physical'])))
                for s in ('before_setter_physics','after_setter_physics')]))
    payload=dict(inventory=inventory,processes=24,post_restoration_actions=24,
        reset_setter_steps=48,dataset_setter_steps=24,singles=singles,pairs=pairs,cross_seed=cross_seed,
        source_sha256=sha(Path(__file__)),new_planning=False,protected_read=False,
        production_correction=False,confirmation_authorized=False)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f: json.dump(payload,f,indent=2,sort_keys=True); f.write('\n')
    with (out.parent/'sha256.txt').open('x') as f:f.write(sha(out)+'  '+out.name+'\n')
    print(json.dumps({'processes':24,'actions':24,'all_requested_exact_before':all(all(d['exact'] for d in s['before'].values()) for s in singles),
        'pairs':[dict(stack=p['stack'],case=p['case'],mode=p['mode'],core_differences=[(e['stage'],len(e['core'])) for e in p['comparisons']]) for p in pairs]}))
if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
