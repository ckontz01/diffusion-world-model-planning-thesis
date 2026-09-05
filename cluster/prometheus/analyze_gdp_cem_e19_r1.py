"""Describe sealed reset/stimulus traces; never compute benchmark success."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    h,n=(p.parent/'sha256.txt').read_text().strip().split(maxsplit=1)
    assert n==p.name and h==sha(p)
    return json.loads(p.read_text())
def array(x):
    return np.asarray(x['values']) if isinstance(x,dict) and 'values' in x else np.asarray(x)
def delta(a,b):
    a,b=array(a),array(b)
    if a.shape!=b.shape: return {'shape_a':list(a.shape),'shape_b':list(b.shape),'exact':False}
    d=np.abs(a.astype(float)-b.astype(float))
    return {'exact':bool(np.array_equal(a,b)),'max_abs':float(d.max()) if d.size else 0.,'mean_abs':float(d.mean()) if d.size else 0.}
def differences(a,b,path=''):
    if a==b: return []
    if isinstance(a,dict) and isinstance(b,dict):
        if 'sha256' in a and 'sha256' in b:
            row={'path':path,'a_hash':a['sha256'],'b_hash':b['sha256']}
            if 'values' in a and 'values' in b:
                try: row['delta']=delta(a,b)
                except (ValueError,TypeError): pass
            return [row]
        out=[]
        for k in sorted(a.keys()|b.keys()): out+=differences(a.get(k),b.get(k),path+'.'+k if path else k)
        return out
    return [{'path':path,'a':a,'b':b}]
def stages(t):
    counts={}; result={}
    for e in t['events']:
        name=e['stage']; n=counts.get(name,0); counts[name]=n+1; result[f'{name}#{n}']=e
    return result
def core(p): return {k:v for k,v in p.items() if k not in ('outside','unavailable')}
def coverage(t):
    s=stages(t)
    return (t['steps']==15 and t['fixed_return_calls']==1 and t['stopped_at_cap']
        and 'before_first_action#0' in s
        and all(f'before_step:{i}#0' in s and f'after_step:{i+1}#0' in s for i in range(15)))
def one(t):
    s=stages(t); task=t['case']['task']; first=s['before_first_action#0']
    checks={}
    if task=='pusht':
        e=s['after_hook:_set_state#0']; target=array(e['kwargs']['state']); bodies=e['physical']['bodies']
        for body,key,goal in [('agent','position',target[:2]),('block','position',target[2:4]),('agent','velocity',target[-2:])]:
            checks[body+'.'+key]=delta(bodies[body][key],goal)
        checks['block.angle_mod_2pi']=delta(np.asarray(array(bodies['block']['angle']))%(2*np.pi),np.asarray(target[4])%(2*np.pi))
        checks['fresh_state_vs_requested_state']=delta(first['fresh_observation'],target)
        goal=s['after_hook:_set_goal_state#0']; checks['goal_state']=delta(goal['kwargs']['goal_state'],goal['physical']['outside']['goal_state'])
    else:
        e=s['after_hook:set_state#0']
        for k in ('qpos','qvel'): checks[k]=delta(e['physical']['data'][k],e['kwargs'][k])
        e=s['after_hook:set_target_pos#0']; ids=array(e['physical']['outside']['_cube_target_mocap_ids']).astype(int)
        checks['target_pos']=delta(array(e['physical']['data']['mocap_pos'])[ids[0]],e['kwargs']['target_pos'])
        checks['target_quat']=delta(array(e['physical']['data']['mocap_quat'])[ids[0]],e['kwargs']['target_quat'])
    info=[]
    for k,fresh in first['fresh_info'].items():
        key=k if k in first['supplied'] else k.replace('/','_')
        if key not in first['supplied']: continue
        try:
            supplied=array(first['supplied'][key]); actual=array(fresh)
            if supplied.size==actual.size:
                d=delta(supplied.reshape(actual.shape),actual)
                if not d['exact']: info.append({'key':key,**d})
        except (ValueError,TypeError): pass
    actual=[e['primitive_action'] for e in t['events'] if e['stage'].startswith('before_step:')]
    world=[e['world_action'] for e in t['events'] if e['stage'].startswith('policy_action:')]
    actual=np.stack([array(a) for a in actual])
    world=np.stack([array(a).reshape(-1) for a in world])
    expected=np.asarray(t['case']['physical'])[:len(actual)]
    return dict(restoration=checks,overlay_vs_fresh_info_differences=info,
        delivered_vs_stimulus=delta(actual,expected),policy_vs_env=delta(world,actual),
        steps=t['steps'],fixed_return_calls=t['fixed_return_calls'],stopped_at_cap=t['stopped_at_cap'],
        observation_probe_captured_state_unchanged=first['observation_probe_captured_state_unchanged'],
        reset_kwargs=s['after_reset#0']['reset_kwargs'],dataset_endpoints=s['dataset_endpoints#0'])
def main():
    p=argparse.ArgumentParser(); p.add_argument('run',type=Path); p.add_argument('output',type=Path); p.add_argument('--cube-run',type=Path); args=p.parse_args()
    pairs=[]; inventories={}
    prep=read(args.run/'preparation/STIMULI.json')
    if args.cube_run: assert read(args.cube_run/'preparation/STIMULI.json')==prep
    for stack in ('sage','e18'):
        for cid in range(5):
            source=args.cube_run if cid>=3 and args.cube_run else args.run
            paths=[source/stack/f'case-{cid}'/f'repeat-{r}'/'TRACE.json' for r in (0,1)]
            ts=[read(path) for path in paths]; ss=[stages(t) for t in ts]
            assert all(t['case']==prep['cases'][cid] and t['stack']==stack and t['repeat']==r for r,t in enumerate(ts))
            assert all(t['new_planning'] is False and t['protected_read'] is False for t in ts)
            assert all(coverage(t) for t in ts), 'incomplete diagnostic trace; no readiness conclusion'
            inventories.update({str(path):sha(path) for path in paths})
            comp=[]
            for stage in ss[0]:
                if stage not in ss[1]: continue
                a,b=ss[0][stage],ss[1][stage]
                row={'stage':stage}
                for key in ('physical','rng','primitive_action','world_action','observation','supplied'):
                    if key not in a: continue
                    if key=='physical':
                        row['core_physical']=differences(core(a[key]),core(b[key]))
                        row['outside_state']=differences(a[key]['outside'],b[key]['outside'])
                    else: row[key]=differences(a[key],b[key])
                comp.append(row)
            pairs.append(dict(stack=stack,case=prep['cases'][cid],stage_alignment_exact=list(ss[0])==list(ss[1]),
                repeats=[one(t) for t in ts],comparisons=comp,
                first_core_difference=next((r for r in comp if r.get('core_physical')),None),
                first_action_difference=next((r for r in comp if r.get('primitive_action') or r.get('world_action')),None),
                first_step_observation_difference=next((r for r in comp if r.get('observation')),None)))
    payload={'kind':'e19_r1_fixed_stimulus_engineering_summary','inventories':inventories,'pairs':pairs,
        'primitive_steps':sum(r['steps'] for pair in pairs for r in pair['repeats']),
        'fresh_processes':20,'new_planning':False,'benchmark_table':False,'protected_read':False,
        'analyzer_sha256':sha(__file__),'confirmation_authorized':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f: json.dump(payload,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
    with (args.output.parent/'sha256.txt').open('x') as f: f.write(sha(args.output)+'  '+args.output.name+'\n')
    print(json.dumps({'pairs':len(pairs),'primitive_steps':payload['primitive_steps']}))
if __name__=='__main__': main()
