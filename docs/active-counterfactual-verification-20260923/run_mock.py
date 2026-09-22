"""One fixed end-to-end contract smoke; not a new efficacy scenario."""
import json
from pathlib import Path
import numpy as np
from tree import FrozenPort,Ledger,cem,construct_tree
from mock import VectorEnv,mock_rollout,collect_source,pack
from model import JointModel,OrdinaryModel,Preprocessing,train
from bayes import BayesianRegression
from policy import Selector,execute_episode
from runtime_adapter import BaselinePlanner,execute_reference
from checker import check_episode,check_reference


class AuditedVector(VectorEnv):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.trace=[]
    def step(self,action):
        obs=super().step(action)
        self.trace.append(dict(clock=obs.clock,action=np.asarray(action).tolist(),latent=obs.latent.tolist(),
                              stage='prefix' if obs.clock<=5 else 'suffix' if obs.clock<=15 else 'baseline-tail',
                              success=bool(obs.success),terminated=bool(obs.terminated),truncated=bool(obs.truncated)))
        return obs


def main():
    out=Path(__file__).parent/'mock-run-v2';out.mkdir(exist_ok=False)
    config=dict(purpose='contracts only; no efficacy inference',revision='v2 adds complete CEM/learned-forward/prior counters; v1 preserved',fit_source_seeds=[94200,94201,94202,94203],
                fit_events=['prefix-success-3','prefix-truncation-3','tail-success-18','budget-exhaustion'],
                heldout_seed=94204,population=8,elites=2,rounds=2,epochs=12,batch_sources=64,
                joint_seed=94011,ordinary_seed=94012,shuffle_seed=94013,integration_seed=94021)
    (out/'CONFIG.json').write_text(json.dumps(config,indent=2)+'\n')
    goal=np.ones(4)*.1;search=Ledger();planner=BaselinePlanner(goal,mock_rollout,search,population=8,elites=2,rounds=2)
    baseline=planner.solve(np.zeros(4),0)
    tree=construct_tree(FrozenPort(np.zeros(4),goal,mock_rollout,search),baseline,population=8,elites=2,rounds=2)
    rows=[];receipts=[];collection_ledgers=[];independent_checks=0
    for index,event in enumerate(config['fit_events']):
        instances=[];ledgers=[]
        def factory():
            e=AuditedVector(seed=94200+index,success_at=3 if index==0 else 18 if index==2 else None,
                            truncate_at=3 if index==1 else None)
            instances.append(e);ledgers.append(Ledger())
            return e
        def tail(h,a,o,remaining):
            return BaselinePlanner(goal,mock_rollout,ledgers[-1],population=8,elites=2,rounds=2)(h,a,o,remaining)
        rr,receipt=collect_source(f'mock-fit-{index}','fit',tree,factory,goal,tail)
        for env,b in zip(instances,receipt['branches']):
            r=dict(trace=env.trace,decision=dict(prefix=b['prefix']),steps=env.calls,
                   selected_suffix=b.get('suffix'),success=any(t['success'] for t in env.trace))
            check_episode(r,tree);independent_checks+=1
        rows.extend(rr);receipts.append(receipt);collection_ledgers.extend(l.__dict__ for l in ledgers)
    data=pack(rows);pre=Preprocessing.fit(data)
    joint=JointModel(56,24,4,preprocessing=pre);ordinary=OrdinaryModel(56,24,4,preprocessing=pre)
    fit=[train(joint,data),train(ordinary,data)]
    joint.save(out/'joint.npz')
    with (out/'ordinary.npz').open('xb') as f:
        np.savez(f,**{f'p{i}':p for i,p in enumerate(ordinary.params)},metadata=np.array(json.dumps(
            dict(kind='ACV0-ordinary',dims=ordinary.net.dims,preprocessing='joint.npz',seed=94012))))
    restored=JointModel.load(out/'joint.npz');ordinary_restored=OrdinaryModel.load(out/'ordinary.npz',restored)
    for a,b in zip(joint.params,restored.params):np.testing.assert_array_equal(a,b)
    np.testing.assert_array_equal(ordinary.forward(data['x'],data['a'],data['r'])[0],
                                  ordinary_restored.forward(data['x'],data['a'],data['r'])[0])
    bayes=BayesianRegression(ordinary_restored).fit(data);selector=Selector(restored,ordinary_restored,bayes)
    results=[]
    for mode in list(Selector.MODES)+['vanilla','early-replan']:
        ledger=Ledger();env=AuditedVector(seed=94204)
        tail=BaselinePlanner(goal,mock_rollout,ledger,population=8,elites=2,rounds=2)
        if mode in Selector.MODES:
            result=execute_episode(env,tree,selector,goal,tail,ledger,mode);check_episode(result,tree)
            result['shared_preconstructed_tree_cost']=search.__dict__
        else:result=execute_reference(env,tail,ledger,mode=='early-replan');check_reference(result)
        independent_checks+=1;result['control']=mode;result['cost']=ledger.__dict__;results.append(result)
    report=dict(status='MOCK_ONLY',fit=fit,collection=receipts,collection_search=collection_ledgers,
                independent_episode_checks=independent_checks,checkpoint_identity=True,
                results=results,tree_search=search.__dict__)
    (out/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='MOCK_ONLY',fits=[f['updates'] for f in fit],checks=independent_checks,
                         collection_episodes=sum(r['constructed_episodes'] for r in receipts),
                         collection_physical_steps=sum(r['physical_steps'] for r in receipts),controls=len(results))))


if __name__=='__main__':main()
