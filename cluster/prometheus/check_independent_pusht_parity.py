"""Compare new E18 transport with the accepted FreshEpisode on pilot records."""
import json,sys
from pathlib import Path
import numpy as np
import torch
import stable_worldmodel as swm
from independent_pusht_runtime import build,tensor_hash
from independent_pusht_evaluate import evaluate_one
from e18_fresh_driver import FreshEpisode
from pusht_fresh_initialization import register

def main(data,out):
    data=Path(data);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    p=json.loads((data/'COLLECTION.json').read_text());ref=p['records'][0]
    with np.load(data/ref['file']) as f:s=f['states'].copy()
    results=[]
    for arm in ('vad_continuation','vad_greedy_300','diagonal_gaussian_continuation','vad_greedy_576','direct_gmm_continuation'):
        factory,modules,prov=build(arm,7201);before=tensor_hash(modules)
        w=swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,correct_velocity_space=True,verbose=0)
        rec={'state':s[0],'goal_state':s[75],'proprio':s[0,[0,1,5,6]]}
        try:
            row,trace=evaluate_one(w,factory,rec,75,33117,arm,cap=31,action_rule='native_finite')
            assert row['failure'] is None
            actions=[];states=[]
            def observe(event,**kw):
                if event=='initialized':states.append(w.envs.envs[0].unwrapped._get_obs().copy())
                elif event=='action':actions.append(kw['action'][0].copy())
                elif event=='after_action':states.append(w.envs.envs[0].unwrapped._get_obs().copy())
            ep=FreshEpisode(w,factory,observe=observe);ep.start(rec,horizon=75,budget=31,seed=33117)
            while ep.status=='running':ep.advance()
            np.testing.assert_array_equal(trace['actions'],np.array(actions))
            np.testing.assert_array_equal(trace['states'],np.array(states))
            assert tensor_hash(modules)==before
            results.append({'arm':arm,'exact_actions':True,'exact_states':True,'delivered':ep.steps})
        finally:w.close()
        del factory,modules;torch.cuda.empty_cache()
    (out/'PARITY.json').write_text(json.dumps({'all_passed':True,'results':results,'pilot_only':True},indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main(*sys.argv[1:])
