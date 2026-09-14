"""Production adapter to the UNCHANGED FreshEpisode and frozen VAD runtime.

Imported only by an authenticated worker, after launch approval. No legacy
dataset evaluator, simulator restoration shortcut, clipping, or retry path.
"""
import hashlib
import pickle
import random
from copy import deepcopy
import numpy as np
import torch
import candidate_value_learning as c
from candidate_value_contract import MODEL_SHA, require
from candidate_value_hook import capture


def array_sha(a):
    a=np.ascontiguousarray(a)
    return hashlib.sha256(str((a.shape,str(a.dtype))).encode()+a.tobytes()).hexdigest()


def implicit_rng():
    return (pickle.dumps(random.getstate()),pickle.dumps(np.random.get_state()),
            array_sha(torch.get_rng_state().numpy()),
            tuple(array_sha(x.cpu().numpy()) for x in torch.cuda.get_rng_state_all()))


class RealBackend:
    def __init__(self):
        from independent_pusht_runtime import build,tensor_hash
        self.factory,self.modules,self.provenance=build('vad_continuation',7201)
        self.tensor_hash=tensor_hash
        self.assert_frozen()
        torch.cuda.reset_peak_memory_stats()

    def assert_frozen(self):
        require(self.tensor_hash(self.modules)==MODEL_SHA,'Frozen model tensor identity')

    def episode(self,record,h,planner_seed,environment_seed,*,bank_times=(),
                forced=None,tail_seed=None,arm='continuation',predict=None):
        import stable_worldmodel as swm
        from pusht_fresh_initialization import register
        from e18_fresh_driver import FreshEpisode
        from independent_pusht_collect import body_fields
        from single_anchor_ranking import physical
        from verify_diffusion_branch import independent_decode
        world=swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,
                        correct_velocity_space=True,verbose=0)
        banks={};calls=[];actions=[];states=[];dynamics=[];flags=[]
        initial=None;plan_decoded=None;tail_state=None;score_seconds=0.
        def observe(event,**data):
            nonlocal initial
            if event=='initialized':
                initial=data['env']._get_obs().copy()
            elif event=='before_action':
                require(data['steps']==len(actions),'Absolute step identity')
                p=data['policy']
                if not p._action_buffer:
                    require(p._stage_index==len(actions)//15 and tuple(p.stages[p._stage_index])==
                            (h-len(actions)%h,15),'Full-budget stage/buffer lifecycle')
                np.testing.assert_array_equal(data['info']['state'][0,-1],
                                              world.envs.envs[0].unwrapped._get_obs())
            elif event=='action':
                require(plan_decoded is not None,'Missing decoded plan')
                np.testing.assert_array_equal(data['action'][0],plan_decoded[len(actions)%15])
            elif event=='after_action':
                env=world.envs.envs[0].unwrapped
                actions.append(np.asarray(world.infos['action'][0,-1]).copy())
                states.append(env._get_obs().copy());dynamics.append(body_fields(env))
                flags.append([bool(world.terminateds.any()),bool(world.truncateds.any())])
        driver=FreshEpisode(world,lambda horizon,_: self.factory(horizon,planner_seed),observe=observe)
        try:
            driver.start(record,horizon=h,budget=2*h,seed=environment_seed)
            solver=driver.policy.planner;original=solver.solve
            def solve(*args,**kw):
                nonlocal plan_decoded,tail_state,score_seconds
                import time
                t=len(actions);before=implicit_rng();solve_started=time.perf_counter()
                selection={};score_before=score_seconds
                rng_before={name:array_sha(getattr(solver,name).get_state().cpu().numpy())
                            for name in ('proposal_generator','gmm_generator')}
                require((kw['delta_value'],kw['tau_value'])==(h-t%h,15),'Solver schedule')
                at_intervention=forced is not None and t==forced[0]
                def choose(bank):
                    nonlocal score_seconds
                    selection['continuation_index']=int(bank['continuation_index'])
                    if at_intervention:return forced[1]
                    if arm=='immediate':return int(bank['immediate'].argmin())
                    if arm in ('value','linear'):
                        begin=time.perf_counter();p=predict(arm,bank['x'])
                        score_seconds+=time.perf_counter()-begin
                        require(p.shape==(64,) and np.isfinite(p).all(),'Learned scores')
                        selection.update(predict.diagnostics(bank['x'],p))
                        selection['selected_index']=int(p.argmax())
                        return int(p.argmax())
                    return bank['continuation_index']
                if t in bank_times or at_intervention or arm!='continuation':
                    result,bank=capture(solver,original,args,kw,h=h,t=t,selector=choose)
                    if t in bank_times or at_intervention:
                        decoder=driver.policy.process['action']
                        bank['decoded_actions']=independent_decode(bank['planner_actions'].reshape(-1,2),
                            decoder.scale_,decoder.mean_).reshape(64,15,2)
                        bank['anchor_state']=world.envs.envs[0].unwrapped._get_obs().copy()
                        bank['anchor_dynamics']=np.asarray(body_fields(world.envs.envs[0].unwrapped))
                        bank['pixels']=np.asarray(world.infos['pixels']).copy()
                        bank['goal_pixels']=np.asarray(world.infos['goal']).copy()
                        bank['proposal_post']=solver.proposal_generator.get_state().cpu().numpy().copy()
                        bank['gmm_post']=solver.gmm_generator.get_state().cpu().numpy().copy()
                        banks[t]=bank
                else:result=original(*args,**kw)
                require(before==implicit_rng(),'Unexpected implicit inference RNG')
                if at_intervention:
                    require(tail_seed is not None and tail_state is None,'Exactly one tail handoff')
                    solver.proposal_generator.manual_seed(tail_seed)
                    solver.gmm_generator.manual_seed(tail_seed)
                    tail_state={'seed':tail_seed,
                        'proposal':array_sha(solver.proposal_generator.get_state().cpu().numpy()),
                        'gmm':array_sha(solver.gmm_generator.get_state().cpu().numpy())}
                macro=result['actions'].float().cpu().numpy().copy()
                decoder=driver.policy.process['action']
                plan_decoded=independent_decode(macro.reshape(15,2),decoder.scale_,decoder.mean_)
                calls.append(dict(at=t,plan_sha256=array_sha(macro),
                                  solver_seconds=time.perf_counter()-solve_started,
                                  value_score_seconds=score_seconds-score_before,
                                  selection=selection,explicit_rng_before=rng_before,
                                  explicit_rng_after={name:array_sha(getattr(solver,name).get_state().cpu().numpy())
                                      for name in ('proposal_generator','gmm_generator')},
                                  diagnostics=deepcopy(solver.diagnostic_history[-1])))
                return result
            solver.solve=solve
            while driver.status=='running':driver.advance()
            require(driver.steps<=2*h and driver.status=='done','Episode completion')
            trace={'actions':np.asarray(actions),'states':np.asarray(states),'dynamics':np.asarray(dynamics),
                   'flags':np.asarray(flags,dtype=bool),'initial':initial}
            result=physical(trace['states'],trace['flags'],np.asarray(record['goal_state']),2*h)
            return dict(trace=trace,banks=banks,calls=calls,success=result['success'],
                        tail_state=tail_state,score_seconds=score_seconds)
        finally:
            world.close()
