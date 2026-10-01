"""Actual accepted scorer, solver and buffered policy with artificial weights."""
import contextlib
import importlib.util
import io
import sys
import types
import unittest
from unittest.mock import patch
import numpy as np
import torch
from torch import nn
from gymnasium.spaces import Box
from dtv_efficiency.test_profile import core,m,d2,cem,p,E
from dtv_success_cost.native import Decoder

class World(nn.Module):
    def __init__(self):super().__init__();self.marker=nn.Parameter(torch.zeros(1))
    def encode(self,info):info['emb']=info['pixels'];info['goal_emb']=info['goal'];return info
    def rollout(self,info,actions):
        start=info['pixels'][...,0,:];increments=torch.cat((actions[...,:2],actions[...,:2]),dim=-1)
        info['predicted_emb']=torch.cat((start[:,:,None],start[:,:,None]+increments.cumsum(dim=2)),dim=2);return info
    def criterion(self,info):return (info['predicted_emb'][:,:,-1]-info['goal_emb'][:,None,-1,:]).square().mean(-1)

class ActualComponents(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(99);self.world=World();self.job=dict(task='pusht',scorer_seed=6101,planner_seed=7101)
        self.models=dict(acid=m.FlowInverseDynamics(4,10,width=6,depth=1,heads=2,mlp_ratio=2),diffusion=m.ConditionalDiffusionVerifier(4,10,width=8,depth=1,noise_embedding_dim=4),forward=m.DeterministicForwardVerifier(4,10,width=8,depth=1))
        self.payloads={a:dict(seed=6101,model_config=dict(latent_dim=4),latent_mean=torch.zeros(4),latent_std=torch.ones(4),acid_action_mean=torch.zeros(10),acid_action_std=torch.ones(10)) for a in self.models}
        self.info=dict(pixels=torch.zeros(1,1,4),goal=torch.ones(1,1,4))
    def wrapper(self,a):return p.make_wrapper(core,d2,self.world,self.models,self.payloads,self.job,'d1_sigma025' if a=='dtv' else a,'cpu')
    def solver(self,w,r):
        s=cem.CEMSolver(w,num_samples=300,topk=30,n_steps=r,seed=7101)
        s.configure(action_space=Box(-np.inf,np.inf,shape=(1,2),dtype=np.float32),n_envs=1,config=types.SimpleNamespace(horizon=5,action_block=5));return s
    def test_28_prefix_of_30_and_exact_final_elite_mean_every_method(self):
        for method in ('dtv','acid','forward','plain'):
            t28=p.Trace(self.wrapper(method));t30=p.Trace(self.wrapper(method));s28=self.solver(t28,28);s30=self.solver(t30,30)
            self.assertIsNot(s28.torch_gen,s30.torch_gen)
            with torch.inference_mode(),contextlib.redirect_stdout(io.StringIO()):r28=s28.solve(self.info);r30=s30.solve(self.info)
            self.assertEqual(len(t28.rows),28);self.assertEqual(len(t30.rows),30)
            for a,b in zip(t28.rows,t30.rows):
                for x,y in zip(a,b):self.assertTrue(torch.equal(x,y))
            for t,result in ((t28,r28),(t30,r30)):
                action,cost,index=t.rows[-1];final=action[torch.zeros_like(index),index].mean(dim=1)
                self.assertTrue(torch.equal(result['actions'],final))
                self.assertEqual(tuple(result['actions'].shape),(1,5,10))
    def test_exact_single_bank_not_sliced_and_lambda_routing(self):
        w=self.wrapper('dtv');self.assertEqual(w.diffusion_sigmas,(.25,));self.assertEqual(w.lambda_weight,.07)
        self.assertTrue(torch.equal(w.diffusion_noise,torch.randn(1,5,4,generator=torch.Generator().manual_seed(6101))))
        self.assertEqual(self.wrapper('forward').lambda_weight,.005);self.assertEqual(self.wrapper('acid').lambda_weight,.07)
    def test_actual_world_model_policy_cadence_and_decoder(self):
        solver_module=types.ModuleType('stable_worldmodel.solver');solver_module.Solver=object
        stub=types.ModuleType('stable_worldmodel');stub.solver=solver_module
        path=E/'runtime/stable_worldmodel/policy.py'
        spec=importlib.util.spec_from_file_location('_dtv_artificial_policy',path);module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'stable_worldmodel':stub,'stable_worldmodel.solver':solver_module,'_dtv_artificial_policy':module}):spec.loader.exec_module(module)
        trace=p.Trace(self.wrapper('plain'));s=self.solver(trace,28);env=types.SimpleNamespace(action_space=Box(-np.inf,np.inf,shape=(1,2),dtype=np.float32),num_envs=1)
        decoder=Decoder(np.array([2.,3.]),np.array([.2,.3]));policy=module.WorldModelPolicy(s,module.PlanConfig(5,5,action_block=5),process={'action':decoder});policy.set_env(env)
        with torch.inference_mode(),contextlib.redirect_stdout(io.StringIO()):
            first=policy.get_action(dict(self.info));self.assertEqual(len(trace.rows),28)
            for _ in range(24):policy.get_action(dict(self.info))
            self.assertEqual(len(trace.rows),28);policy.get_action(dict(self.info));self.assertEqual(len(trace.rows),56)
        self.assertEqual(first.shape,(1,2));self.assertEqual(len(policy._action_buffer),24)
    def test_fresh_initializer_factories_use_actual_saved_state_before_wrapper(self):
        # Real binding function, all native/env constructors replaced by doubles.
        from dtv_success_cost import native
        registry={'dtveff1/Reacher-v0':1,'dtveff1/Cube-v0':1};seen=[]
        fake=types.ModuleType('stable_worldmodel')
        class FakeWorld:
            def __init__(self,**kw):seen.append(kw)
            def reset(self,**kw):seen.append(kw)
        fake.World=FakeWorld
        with patch.dict(sys.modules,{'stable_worldmodel':fake}),patch('gymnasium.registry',registry):
            data=dict(qpos=np.array([1,2]),qvel=np.array([3,4]));goal=dict(qpos=np.array([5,6]),privileged_block_0_pos=np.ones(3),privileged_block_0_quat=np.ones(4))
            _,reset=native.environment('reacher',data,goal,7);reset()
            self.assertTrue(np.array_equal(seen[-1]['options']['state'],[1,2,3,4]));self.assertTrue(np.array_equal(seen[-1]['options']['target_qpos'],[5,6]))
            _,reset=native.environment('cube',data,goal,7);reset();self.assertEqual(seen[-1]['seed'],7)
    def test_frozen_decoder_exact_sklearn_float32_no_refit(self):
        from sklearn.preprocessing import StandardScaler
        mean=np.array([.00342421,-.2948209]);scale=np.array([.0072955,1.432442])
        standard=StandardScaler();standard.mean_=mean;standard.scale_=scale
        data=np.array([[.552444,-.333442]],dtype=np.float32)
        actual=Decoder(mean,scale).inverse_transform(data)
        self.assertEqual(actual.dtype,np.float32);self.assertTrue(np.array_equal(actual,standard.inverse_transform(data)))
    def test_actual_cube_subclass_applies_state_and_goal_before_observation(self):
        from dtv_success_cost import native
        registry={};events=[];fake=types.ModuleType('stable_worldmodel');module=types.ModuleType('stable_worldmodel.envs.ogbench.cube_env')
        class Cube:
            def __init__(self,**kw):self._model=types.SimpleNamespace(nq=2)
            def reset(self,**kw):events.append('native_reset')
            def set_state(self,qpos,qvel):events.append(('set_state',qpos.tolist(),qvel.tolist()))
            def pre_step(self):events.append('pre_step')
            def set_target_pos(self,i,pos,quat):events.append(('set_target',i,pos.tolist(),quat.tolist()))
            def post_step(self):events.append('post_step')
            def compute_observation(self):events.append('fresh_observation');return np.zeros(1)
            def get_reset_info(self):return {}
        class FakeWorld:
            def __init__(self,env_name,**kw):self.env=registry[env_name](**kw)
            def reset(self,**kw):return self.env.reset(**kw)
        fake.World=FakeWorld;module.CubeEnv=Cube
        def register(name,entry_point):registry[name]=entry_point
        with patch.dict(sys.modules,{'stable_worldmodel':fake,'stable_worldmodel.envs.ogbench.cube_env':module}),patch('gymnasium.registry',registry),patch('gymnasium.register',side_effect=register):
            data=dict(qpos=np.array([1.,2.]),qvel=np.array([3.,4.]));target=dict(privileged_block_0_pos=np.array([5.,6.,7.]),privileged_block_0_quat=np.array([1.,0.,0.,0.]))
            _,reset=native.environment('cube',data,target,7);reset()
        self.assertEqual(events,['native_reset',('set_state',[1.,2.],[3.,4.]),'pre_step',('set_target',0,[5.,6.,7.],[1.,0.,0.,0.]),'post_step','fresh_observation'])
if __name__=='__main__':unittest.main()
