"""Common physical evaluation for fixed E18 arms and released SAGE."""
import argparse,hashlib,json,time,traceback
from pathlib import Path
from copy import deepcopy
import numpy as np
import torch
import stable_worldmodel as swm
from pusht_fresh_initialization import register,reset_world
from independent_pusht_collect import seed_for,sha,array_hash
from independent_pusht_runtime import ARMS,build,tensor_hash
from e18_fresh_driver import computational_info

def initial_hash(info):
    return hashlib.sha256(''.join(array_hash(info[k]) for k in ('state','pixels','goal')).encode()).hexdigest()

def evaluate_one(world,factory,record,horizon,seed,arm,cap=None,action_rule='strict'):
    policy=factory(horizon,seed)
    world.set_policy(policy)
    reset_world(world,[record],seed=seed)
    np.testing.assert_allclose(world.envs.envs[0].unwrapped._get_obs(),record['state'],rtol=0,atol=1e-10)
    start_hash=initial_hash(world.infos)
    goal=np.asarray(world.infos['goal']).copy()
    actions=[];raw_actions=[];states=[world.envs.envs[0].unwrapped._get_obs().copy()]
    calls=[];solver=getattr(policy,'planner',getattr(policy,'solver',None))
    original=solver.solve
    def traced(*args,**kwargs):
        torch.cuda.synchronize();start=time.perf_counter()
        result=original(*args,**kwargs)
        torch.cuda.synchronize()
        calls.append({'at':len(actions),'seconds':time.perf_counter()-start,
                      'plan_hash':array_hash(result['actions'].float().numpy())})
        return result
    solver.solve=traced
    success=False;failure=None;violations=0;max_raw=0.;truncation=False
    max_steps=2*horizon if cap is None else min(cap,2*horizon)
    began=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    try:
        for t in range(max_steps):
            np.testing.assert_array_equal(world.infos['goal'],goal)
            np.testing.assert_array_equal(world.infos['state'][0,-1],world.envs.envs[0].unwrapped._get_obs())
            info=deepcopy(world.infos) if arm=='sage' else computational_info(world.infos)
            try:
                raw=np.asarray(policy.get_action(info)).copy()
                if raw.shape!=(1,2) or not np.isfinite(raw).all():raise ValueError('nonfinite/invalid-shaped action')
                bad=int(np.sum(abs(raw)>1));violations+=bad;max_raw=max(max_raw,float(abs(raw).max()))
                if action_rule=='strict' and bad:raise ValueError('decoded action outside common Box')
                action=np.clip(raw,-1,1) if action_rule=='project_box' else raw
            except Exception as e:
                failure={'category':'planner','type':type(e).__name__,'message':str(e),
                         'traceback':traceback.format_exc()};break
            obs,reward,terminated,truncated,info=world.envs.step(action)
            world.states=obs;world.infos=info;world.terminateds=terminated;world.truncateds=truncated
            actions.append(action[0].copy());raw_actions.append(raw[0].copy())
            state=world.envs.envs[0].unwrapped._get_obs().copy()
            if not np.isfinite(state).all():raise RuntimeError('nonfinite simulator state')
            states.append(state)
            success=bool(np.asarray(terminated).any());truncation=bool(np.asarray(truncated).any())
            if success or truncation:break
    finally: solver.solve=original
    summary={'initial_hash':start_hash,'success':int(success),'delivered':len(actions),
             'native_truncation':truncation,'failure':failure,'horizon':horizon,
             'seed':seed,'budget':max_steps,'calls':calls,'wall_seconds':time.perf_counter()-began,
             'decoded_outside_box_coordinates':violations,'maximum_raw_action':max_raw,
             'action_rule':action_rule,'peak_cuda_allocated':torch.cuda.max_memory_allocated()}
    trajectory={'actions':np.array(actions,dtype=np.float32).reshape(-1,2),
                'raw_actions':np.array(raw_actions,dtype=np.float32).reshape(-1,2),
                'states':np.stack(states),'goal_state':record['goal_state']}
    if failure is None:
        assert [c['at'] for c in calls]==list(range(0,len(actions),15))
    return summary,trajectory

def run(data,out,arm,train_seed,indices=None,pilot=False,cap=None,action_rule='strict'):
    torch.set_num_threads(4);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    data=Path(data);manifest=json.loads((data/'COLLECTION.json').read_text())
    assert manifest['complete']
    if pilot: assert manifest['namespace'].startswith('pilot')
    else: assert manifest['namespace'].startswith('final')
    factory,modules,provenance=build(arm,train_seed)
    before=tensor_hash(modules)
    records=manifest['records'] if indices is None else [manifest['records'][i] for i in indices]
    world=swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,
                    correct_velocity_space=True,verbose=0)
    rows=[]
    try:
        for ref in records:
            assert sha(data/ref['file'])==ref['sha256']
            with np.load(data/ref['file'],allow_pickle=False) as f: s=f['states'].copy()
            for h in (75,150):
                record={'state':s[0],'goal_state':s[h],'proprio':s[0,[0,1,5,6]]}
                seed=seed_for(manifest['namespace'],ref['attempt'],f'planner|h={h}|seed={train_seed}')
                row,trace=evaluate_one(world,factory,record,h,seed,arm,cap=cap,action_rule=action_rule)
                row.update(reference_index=ref['index'],reference_attempt=ref['attempt'],arm=arm,train_seed=train_seed)
                name=f'episode-{ref["index"]:05d}-h{h}.npz'
                np.savez_compressed(out/name,**trace)
                row['trajectory_file']=name;row['trajectory_sha256']=sha(out/name)
                path=out/f'episode-{ref["index"]:05d}-h{h}.json'
                with path.open('x') as stream:json.dump(row,stream,sort_keys=True,allow_nan=False)
                rows.append(row)
                print(json.dumps({'completed_record':ref['index'],'horizon':h,
                    'technical_status':'planner_failure' if row['failure'] else 'completed'}),flush=True)
    finally: world.close()
    assert tensor_hash(modules)==before
    report={'arm':arm,'train_seed':train_seed,'pilot':pilot,'collection_sha256':sha(data/'COLLECTION.json'),
            'source_sha256':sha(__file__),'rows':rows,'model_state_sha256':before,
            'provenance':provenance,'models_unchanged':True,'action_rule':action_rule,'completed':True}
    (out/'RESULT.json').write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    (out/'sha256.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='sha256.txt'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True)
    p.add_argument('--arm',choices=ARMS,required=True);p.add_argument('--train-seed',type=int,default=7201)
    p.add_argument('--indices',type=str);p.add_argument('--pilot',action='store_true');p.add_argument('--cap',type=int)
    p.add_argument('--action-rule',choices=['strict','project_box'],default='strict')
    a=p.parse_args();run(a.data,a.out,a.arm,a.train_seed,
      indices=[int(i) for i in a.indices.split(',')] if a.indices else None,pilot=a.pilot,cap=a.cap,action_rule=a.action_rule)
