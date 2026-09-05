"""Actual checkpoint-backed arm setup, stopped before any planner invocation.

Checks physical/raw policy-input equivalence, plus native image/action
preprocessing. E18 non-action scalers are intentionally not refitted here.
"""
import argparse
from copy import deepcopy
import gc
import inspect
import json
from pathlib import Path
import numpy as np
import torch
import gdp_cem_e19_r1 as r1
from gdp_cem_e19_r3_validation import inputs, physical, check_start, ENV_SHA, R1_RUN
from pusht_fresh_initialization import register, reset_world

CORE=r1.ROOT/'experiments/gdp-cem-e19-r3/run-20260905-30215e7f'
SAGE_ARMS=('base_cem','far_goal_prior_cem','lewm_generator','generator_prior_top','sage')
E18_ARMS=('vad_greedy_300','vad_greedy_576','vad_continuation',
          'diagonal_gaussian_continuation','direct_gmm_continuation')

def setup(stack, arm):
    import stable_worldmodel as swm
    device=torch.device('cuda')
    lewm_path=r1.ROOT/'data/stablewm/pusht/lewm_hf_22b330c_object.ckpt'
    assert r1.sha(lewm_path)=='c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659'
    hashes={str(lewm_path):r1.sha(lewm_path)}
    if stack=='sage':
        from sage.eval import pusht as p
        p.set_determinism(32)
        release=json.loads((r1.PARENT/'official-sage/configs/checkpoints.json').read_text())
        prior_name='pusht_far_action_prior' if arm=='far_goal_prior_cem' else 'pusht_action_prior'
        def checkpoint(name):
            path=r1.E19/'checkpoints'/release[name]['filename']
            assert r1.sha(path)==release[name]['sha256'];hashes[str(path)]=r1.sha(path)
            return path
        uses_generator=arm in ('lewm_generator','generator_prior_top','sage')
        uses_prior=arm in ('far_goal_prior_cem','generator_prior_top','sage')
        generator,gs,_=p.load_subgoal_prior(checkpoint('pusht_generator'),device) if uses_generator else (None,None,None)
        loaded,ps,_=p.load_action_prior(checkpoint(prior_name),device)
        lewm=p.load_lewm(lewm_path,device=device,bf16=True)
        model=p.SAGECostModel(lewm,generator,gs or ps,loaded if uses_prior else None,ps,
            goal_offset_steps=75,action_block=5,image_size=224).to(device).eval().requires_grad_(False)
        if arm=='generator_prior_top': solver=p.PriorTopMode(model)
        else:
            constructor=p.PriorInitializedCEM if arm in ('far_goal_prior_cem','sage') else p.GaussianCEM
            solver=constructor(model,candidates=300,rounds=30,elites=30,seed=32,device=device)
        scaler=p.ArrayNormalizer(ps['action_mean'].cpu().numpy(),ps['action_std'].cpu().numpy())
        def make_policy():
            return p.ScheduledPolicy(solver=solver,config=swm.PlanConfig(horizon=3,receding_horizon=3,
                action_block=5,warm_start=False),process={'action':scaler},
                transform={'pixels':p.image_transform(224,torch.bfloat16),'goal':p.image_transform(224,torch.bfloat16)},
                schedule_steps=[15]*5,goal_offset_steps=75,history_length=3,frameskip=5)
        policy=make_policy()
        modules=[model,loaded]+([generator] if generator is not None else [])
        setup_detail=dict(horizon=75,schedule=[15]*5,candidates=300,rounds=30,elites=30,global_seed=32,
            non_action_scalers='not used by official SAGE PushT policy')
    else:
        import gdp_cem_e18_specs as s
        from gdp_cem_e18_runtime import load_e15_proposer, E18ScheduledPolicy
        from gdp_cem_e18_inputs import load_e17_adapter
        from gdp_cem_e18_closed_loop import E18Planner
        from evaluate_gdp_cem_e18 import image_transform
        from sklearn.preprocessing import StandardScaler
        seed=s.derived_seed('planner|task=pusht|h=75|replicate=1|shard=0')
        proposal_seed=s.derived_seed('proposal|task=pusht|h=75|replicate=1|shard=0')
        torch.manual_seed(seed);np.random.seed(seed%(2**32));torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
        torch.use_deterministic_algorithms(True)
        model=swm.policy.AutoCostModel('pusht/lewm_hf_22b330c',cache_dir=r1.ROOT/'data/stablewm').to(device).eval().requires_grad_(False)
        if hasattr(model,'interpolate_pos_encoding'): model.interpolate_pos_encoding=True
        train=r1.ROOT/'experiments/gdp-cem-e15/development-run-20260825-ebd6109b/training'
        proposer,stats,pr=load_e15_proposer(train,task='pusht',condition=s.family_for_arm(arm),seed=7201,device=device)
        adapter=None
        if s.is_continuation_arm(arm):
            adapter,ar=load_e17_adapter(r1.ROOT/'experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2/models/pusht',task='pusht',device=device)
        solver=E18Planner(model,arm=arm,statistics=stats,state_dim=7,primitive_action_dim=2,
            proposer=proposer,state_adapter=adapter,batch_size=1,proposal_seed=proposal_seed)
        # Exact already-exposed R1 action scaler, not a fit to any dataset rows.
        trace=R1_RUN/'e18/case-0/repeat-0/TRACE.json';r1.verified(trace)
        ss=json.loads(trace.read_text())['action_scaler']
        scaler=StandardScaler();scaler.mean_=np.asarray(ss['mean_']['values'])
        scaler.scale_=np.asarray(ss['scale_']['values']);scaler.n_features_in_=2
        def make_policy():
            return E18ScheduledPolicy(solver,schedule=s.schedule_for(75),environment_budget=150,
                state_key='state',process={'action':scaler},
                transform={'pixels':image_transform(224),'goal':image_transform(224)})
        policy=make_policy()
        modules=[model,proposer]+([adapter] if adapter is not None else [])
        cp=train/'pusht'/s.family_for_arm(arm)/'seed-7201/final.pt';hashes[str(cp)]=r1.sha(cp)
        if adapter is not None:
            hashes['e17_expected_checkpoint_sha256']=s.E17_CHECKPOINT_SHA256['pusht']
        setup_detail=dict(horizon=75,schedule=list(s.schedule_for(75)),global_seed=seed,
            proposal_seed=proposal_seed,learned_seed=7201,proposer_record=pr,
            non_action_scalers='not refitted or substituted: raw state/proprio equality boundary only; native image/action preprocessing checked')
    return make_policy,solver,modules,dict(arm=arm,checkpoints=hashes,details=setup_detail,
        types=[type(m).__module__+'.'+type(m).__name__ for m in [*modules,solver,policy]],
        parameter_counts=[sum(p.numel() for p in m.parameters()) for m in modules])

def env_list(world):
    return world.envs.envs if hasattr(world.envs,'envs') else world.envs.unwrapped.envs

class Captured(Exception): pass

def capture_boundary(policy, info):
    original=policy._prepare_info; capture={}
    def intercept(payload):
        capture['raw']=deepcopy(payload)
        capture['prepared']=original(payload)
        raise Captured()
    policy._prepare_info=intercept
    try:
        try: policy.get_action(deepcopy(info))
        except Captured: pass
        else: raise AssertionError('policy did not stop at preprocessing boundary')
    finally: policy._prepare_info=original
    return capture

def batch_row(payload, i, n):
    keys=('state','proprio','pixels','goal','goal_state','goal_proprio',
          '_proposal_pixels_raw','_plan_call')
    return {k:payload[k][i] for k in keys if k in payload}

def run(stack,arm,out):
    import stable_worldmodel as swm
    import pymunk
    from stable_worldmodel.envs.pusht.env import PushT
    core=CORE/stack/'validation/VALIDATION.json';r1.verified(core)
    assert json.loads(core.read_text())['all_passed']
    assert r1.sha(inspect.getsourcefile(PushT))==ENV_SHA[stack]
    cases=inputs(stack);records=[c['record'] for c in cases]
    make_policy,solver,modules,provenance=setup(stack,arm)
    versions=[[(p._version,tuple(p.shape),p.requires_grad) for p in m.parameters()] for m in modules]
    register();n_full=50 if stack=='sage' else 3
    rows=[];reference={};worlds=0;initializations=0;actions=0
    native_step=pymunk.Space.step;step_calls=[]
    def count(space,dt):step_calls.append(dt);return native_step(space,dt)
    pymunk.Space.step=count
    try:
        for n in (1,n_full):
            world=swm.World('thesis/PushTFresh-v0',num_envs=n,image_shape=(224,224),
                max_episode_steps=300,correct_velocity_space=True)
            worlds+=1
            try:
                for phase in range(3 if n==1 else 2):
                    ids=[phase] if n==1 else [(i+phase)%3 for i in range(n)]
                    # Native set_env alone does not reset SAGE _plan_call.
                    # Construct a new native policy; never mutate its private counter.
                    policy=make_policy()
                    world.set_policy(policy)
                    before=len(step_calls)
                    reset_world(world,[records[i] for i in ids],seed=32+phase)
                    initializations+=n
                    assert len(step_calls)==before
                    envs=env_list(world)
                    cap=capture_boundary(policy,world.infos)
                    if stack=='sage':
                        np.testing.assert_array_equal(cap['raw']['_env_id'],np.arange(n))
                        np.testing.assert_array_equal(cap['raw']['_plan_call'],np.zeros(n,dtype=np.int64))
                    saved=[]
                    for slot,cid in enumerate(ids):
                        env=envs[slot].unwrapped
                        obs={'state':env._get_obs(),'proprio':env._get_obs()[[0,1,5,6]]}
                        check_start(env,records[cid],obs)
                        np.testing.assert_array_equal(np.asarray(world.infos['state'])[slot,-1],obs['state'])
                        # The normal image wrapper already renders/resizes. Independently
                        # render through its public interface and match supplied pixels.
                        np.testing.assert_array_equal(np.asarray(world.infos['pixels'])[slot,-1],envs[slot].render())
                        row=dict(case_id=cid,slot=slot,n=n,phase=phase,
                            initialized=r1.digest(physical(env)),
                            raw=r1.digest(batch_row(cap['raw'],slot,n)),
                            prepared=r1.digest(batch_row(cap['prepared'],slot,n)))
                        if n==1: reference[cid]=deepcopy(row)
                        else:
                            for key in ('initialized','raw','prepared'):
                                assert row[key]==reference[cid][key],(arm,n,slot,key)
                        saved.append(row)
                    # Metadata does not enter preprocessing. Re-run native preparation
                    # on byte-identical input and require the same actual tensor bytes.
                    again=policy._prepare_info(deepcopy(cap['raw']))
                    assert r1.digest(again)==r1.digest(cap['prepared'])
                    action_scaler=policy.process['action']
                    stimulus=np.concatenate([c['actions'] for c in cases])
                    normalized=action_scaler.transform(stimulus.copy())
                    reconstructed=action_scaler.inverse_transform(normalized.copy())
                    np.testing.assert_allclose(reconstructed,stimulus,rtol=1e-6,atol=1e-7)
                    assert np.isfinite(normalized).all()
                    if n==1 or phase==0:
                        trajectories=[[] for _ in range(n)]
                        for step in range(3):
                            act=np.stack([cases[c]['actions'][step] for c in ids])
                            # Exercise the native batch stepping path, no solver or benchmark reducer.
                            world.envs.step(act);actions+=n
                            for slot,env in enumerate(envs):
                                trajectories[slot].append(r1.digest(physical(env.unwrapped)))
                        assert len(step_calls)-before==n*3*10
                        for slot,cid in enumerate(ids):
                            saved[slot]['fixed_trajectory']=trajectories[slot]
                            if n==1:reference[cid]['fixed_trajectory']=trajectories[slot]
                            else:assert trajectories[slot]==reference[cid]['fixed_trajectory'],(arm,slot,'fixed actions')
                    rows.extend(saved)
            finally:world.close()
        assert versions==[[(p._version,tuple(p.shape),p.requires_grad) for p in m.parameters()] for m in modules]
        assert not getattr(solver,'diagnostic_history',[])
    finally:pymunk.Space.step=native_step
    r1.seal(out/'ARM-CHECK.json',dict(stack=stack,arm=arm,all_passed=True,provenance=provenance,rows=rows,
        worlds=worlds,initializations=initializations,primitive_actions=actions,physics_steps=len(step_calls),
        hidden_initialization_steps=0,native_source_sha256=ENV_SHA[stack],solver_invocations=0,
        image_action_preprocessing_checked=True,raw_input_equivalence_checked=True,
        e18_non_action_scaler_values_checked=False if stack=='e18' else None,
        checkpoint_parameters_modified=False,performance_metric_recorded=False,protected_read=False,
        holdout_read=False,historical_result_modified=False,diffusion_changed=False,
        duplicates='only exposed cases 0,1,2 cycled through slots; phase 1 rotates by one'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stack',choices=['sage','e18'],required=True)
    p.add_argument('--arm',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert a.arm in (SAGE_ARMS if a.stack=='sage' else E18_ARMS)
    assert r1.ROOT/'experiments/gdp-cem-e19-r3' in a.output.resolve().parents
    torch.set_num_threads(4);run(a.stack,a.arm,a.output)
