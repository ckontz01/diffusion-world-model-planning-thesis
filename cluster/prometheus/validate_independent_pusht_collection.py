"""Validate reference integrity and fixed witness replay without learned models."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from independent_pusht_collect import sha,array_hash
from pusht_fresh_initialization import fresh_type,OPTION

def validate(data,expected=6000,witnesses=32,expected_namespace='final-20260906-primary-v1'):
    from stable_worldmodel.envs.pusht.env import PushT
    data=Path(data);m=json.loads((data/'COLLECTION.json').read_text())
    assert m['complete'] and len(m['records'])==expected and m['steps']==150
    assert m['namespace']==expected_namespace
    assert len(m['attempts'])<=30000 and sum(r['accepted'] for r in m['attempts'])==expected
    unique=set();starts=set();replays=0
    for i,ref in enumerate(m['records']):
        assert ref['index']==i and sha(data/ref['file'])==ref['sha256']
        with np.load(data/ref['file'],allow_pickle=False) as f:
            s=f['states'].copy();a=f['actions'].copy();d=f['dynamics'].copy();initial=f['initial_request'].copy()
        assert s.shape==(151,7) and a.shape==(150,2) and d.shape==(151,10) and initial.shape==(7,)
        assert np.isfinite(s).all() and np.isfinite(a).all() and np.isfinite(d).all()
        assert (abs(a)<=1).all() and (s[:,:4]>=0).all() and (s[:,:4]<=512).all()
        assert array_hash(s[[0,75,150]])==ref['fingerprint']
        assert ref['fingerprint'] not in unique and array_hash(s[0]) not in starts
        unique.add(ref['fingerprint']);starts.add(array_hash(s[0]))
        if i in set(np.linspace(0,expected-1,min(witnesses,expected),dtype=int)):
            for h in (75,150):
                env=fresh_type(PushT)(correct_velocity_space=True)
                try:
                    env.reset(options={OPTION:{'state':initial,'goal_state':s[h]}})
                    for t,action in enumerate(a[:h]):
                        obs,*_=env.step(action)
                        np.testing.assert_allclose(obs['state'],s[t+1],rtol=0,atol=1e-10)
                    assert env.eval_state(s[h],env._get_obs())[0];replays+=1
                finally:env.close()
    result={'all_passed':True,'records':expected,'unique_starts':len(starts),'witness_goal_replays':replays,
            'collection_sha256':sha(data/'COLLECTION.json'),'model_called':False,'source_sha256':sha(__file__)}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--n',type=int,default=6000)
    a=p.parse_args();r=validate(a.data,a.n);path=Path(a.out);assert not path.exists();path.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
