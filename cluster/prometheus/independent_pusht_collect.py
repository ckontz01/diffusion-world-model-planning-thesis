"""Independent fixed-policy reference trajectories; no compared model is loaded.

H denotes elapsed reference actions, not shortest-path difficulty. Collection
uses block-near random actions matching the pinned WeakPolicy algorithm. A
reference episode has no task goal until future-state goal relabeling; native
success flags against the temporary rendering marker are logged but ignored.
"""
import argparse, hashlib, json, os
from pathlib import Path
import numpy as np
from pusht_fresh_initialization import fresh_type, OPTION

VERSION = 'independent-pusht-reference-v1'

def seed_for(namespace, index, purpose):
    text=f'{VERSION}|{namespace}|{index}|{purpose}'
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], 'little')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def array_hash(x):
    a=np.ascontiguousarray(x)
    return hashlib.sha256(str((a.shape,str(a.dtype))).encode()+a.tobytes()).hexdigest()

def weak_action(state,rng):
    # Same relative-action operations as pinned native WeakPolicy(dist_constraint=100).
    target=state[:2]+100*rng.uniform(-1,1,size=2)
    target=np.clip(target,state[2:4]-100,state[2:4]+100)
    return np.clip((target-state[:2])/100,-1,1).astype(np.float32)

def body_fields(env):
    return np.array([*env.block.velocity, env.block.angular_velocity,
                     env.agent.angular_velocity,*env.block.force,env.block.torque,
                     *env.agent.force,env.agent.torque],dtype=np.float64)

def valid_initial_geometry(env):
    for shape in env.space.shapes:
        if shape.body not in (env.agent,env.block): continue
        for hit in env.space.shape_query(shape):
            if hit.shape.body is shape.body: continue
            if any(p.distance < -1e-8 for p in hit.contact_point_set.points):
                return False
    return True

def make_reference(index, namespace, steps=150):
    from stable_worldmodel.envs.pusht.env import PushT
    cls=fresh_type(PushT)
    env=cls(correct_velocity_space=True)
    initial_rng=np.random.default_rng(seed_for(namespace,index,'initial'))
    action_rng=np.random.default_rng(seed_for(namespace,index,'collector'))
    s=np.r_[initial_rng.uniform(50,450,2), initial_rng.uniform(100,400,2),
            initial_rng.uniform(0,2*np.pi),0.,0.].astype(np.float64)
    record={'state':s,'goal_state':s.copy(),'proprio':s[[0,1,5,6]]}
    try:
        env.reset(seed=seed_for(namespace,index,'environment'),options={OPTION:record})
        if not valid_initial_geometry(env): return None, 'initial_overlap'
        states=[env._get_obs().copy()]; dyn=[body_fields(env)]
        actions=[]; contacts=[]; transient_terminations=[]
        for t in range(steps):
            action=weak_action(states[-1],action_rng)
            obs,reward,term,trunc,info=env.step(action)
            state=obs['state'].copy()
            if not np.isfinite(state).all() or not np.isfinite(body_fields(env)).all():
                return None,'nonfinite_reference'
            if np.any(state[:4]<0) or np.any(state[:4]>512): return None,'position_outside_arena'
            states.append(state);dyn.append(body_fields(env));actions.append(action)
            contacts.append(int(info['n_contacts']));transient_terminations.append(bool(term))
        values={'states':np.stack(states),'actions':np.stack(actions),'dynamics':np.stack(dyn),
                'contacts':np.array(contacts,dtype=np.int32),
                'temporary_marker_success':np.array(transient_terminations,dtype=np.bool_)}
        return values, None
    finally: env.close()

def collect(out,namespace,n,max_attempts):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    records=[];attempts=[];accepted=[];seen=set()
    for i in range(max_attempts):
        data,reason=make_reference(i,namespace)
        entry={'attempt':i,'reason':reason,'accepted':reason is None}
        if data is not None:
            ident=array_hash(data['states'][[0,75,150]])
            if ident in seen: raise RuntimeError('duplicate independent start-goal fingerprint')
            seen.add(ident)
            name=f'reference-{len(records):05d}.npz'
            np.savez_compressed(out/name,**data)
            s=data['states']; row={'index':len(records),'attempt':i,'file':name,
              'sha256':sha(out/name),'fingerprint':ident,
              'namespace':namespace,'environment_seed':seed_for(namespace,i,'environment'),
              'block_displacement':{str(h):float(np.linalg.norm(s[h,2:4]-s[0,2:4])) for h in (75,150)},
              'initially_solved':{str(h):bool(np.linalg.norm(s[h,:4]-s[0,:4])<20 and min(abs(s[h,4]-s[0,4]),2*np.pi-abs(s[h,4]-s[0,4]))<np.pi/9) for h in (75,150)},
              'contact_action_count':int(np.sum(data['contacts']>0))}
            records.append(row)
        attempts.append(entry)
        if len(records)==n: break
    payload={'version':VERSION,'namespace':namespace,'requested':n,'complete':len(records)==n,
             'records':records,'attempts':attempts,'steps':150,'comparative_models_called':False,
             'source_sha256':sha(__file__),
             'rejections':'initial shape penetration, nonfinite state, or position outside arena only; never planner outcome',
             'population':'uniform valid fresh starts; block-near random reference actions; future-state goals; not original expert distribution'}
    (out/'COLLECTION.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'complete':payload['complete'],'accepted':len(records),'attempts':len(attempts),
       'rejection_counts':{k:sum(a['reason']==k for a in attempts) for k in sorted({a['reason'] for a in attempts if a['reason']})},
       'contact_reference_fraction':float(np.mean([r['contact_action_count']>0 for r in records])) if records else None,
       'initially_solved_count':{str(h):sum(r['initially_solved'][str(h)] for r in records) for h in (75,150)}}))
    if not payload['complete']: raise RuntimeError('fixed maximum attempts exhausted; preserve incomplete collection')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--namespace',required=True)
    p.add_argument('--n',type=int,required=True);p.add_argument('--max-attempts',type=int,required=True)
    a=p.parse_args();collect(a.out,a.namespace,a.n,a.max_attempts)
