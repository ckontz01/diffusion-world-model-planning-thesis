"""Actual pinned World methods + real Policy/driver, with artificial physics only."""
import ast
import hashlib
import random
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
import lgp1_contract as c
from lgp1_runtime import Policy
from local_goal_models import LocalProposer
from e18_fresh_driver import FreshEpisode
from pusht_fresh_initialization import ENV_ID

WORLD_SHA='15fc9e4a69d2ad81d29ca8fedd689b53e96887f7614fa98223ef5ddee37bbda6'

def world_methods():
    record=c.read(Path(__file__).resolve().parents[2]/c.DOC/'PINNED-CONTRACTS-CORRECTION.json')
    item=next(v for k,v in record['sources'].items() if k.endswith('/stable_worldmodel/world.py'))
    c.require(hashlib.sha256(item['text'].encode()).hexdigest()==item['sha256']==WORLD_SHA,
              'Authenticated installed World source')
    cls=next(n for n in ast.parse(item['text']).body if isinstance(n,ast.ClassDef) and n.name=='World')
    methods={}
    for name in ('set_policy','reset','step','close'):
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
        ns={}
        exec(compile('from __future__ import annotations\n'+ast.get_source_segment(item['text'],node),
                     '<pinned World.'+name+'>','exec'),ns)
        methods[name]=ns[name]
    return type('PinnedWorldMethods',(),methods)

class SyntheticPool:
    """No Gym construction or physics; only the consumed vector-pool protocol."""
    def __init__(self,terminal_at=None,truncated_at=None):
        self.terminal_at=terminal_at;self.truncated_at=truncated_at;self.closed=False;self.resets=[]
        self.native=SimpleNamespace(spec=SimpleNamespace(id=ENV_ID),_fresh_pending=None)
        self.native.queue_instantaneous_record=lambda r:setattr(self.native,'_fresh_pending',r)
        self.native._get_obs=lambda:self.infos['state'][0,-1].copy()
        self.envs=[SimpleNamespace(unwrapped=self.native)]
    def reset(self,seed=None,options=None):
        self.resets.append(seed);r=self.native._fresh_pending
        self.native._fresh_pending=None;self.native.goal_state=r['goal_state'].copy();self.steps=0
        self.infos=dict(state=r['state'][None,None].copy(),pixels=np.zeros((1,1,2,2,3),np.uint8),
                        goal=np.ones((1,1,2,2,3),np.uint8))
        return self.infos['state'].copy(),self.infos
    def step(self,action):
        if self.steps and self.steps in (self.terminal_at,self.truncated_at):
            raise AssertionError('Post-terminal physics')
        self.steps+=1;self.infos['action']=action[:,None].copy()
        self.infos['pixels'].fill(self.steps%256)
        return self.infos['state'].copy(),np.zeros(1),np.array([self.steps==self.terminal_at]),np.array([self.steps==self.truncated_at]),self.infos
    def close(self,**kw):self.closed=True

class Backend:
    mean=np.zeros(2);std=np.ones(2)
    def encode_frames(self,frames):return np.zeros((len(frames),192),np.float32)
    def generate(self,h,f,s,r):return np.ones_like(f)
    def cost_function(self,frames,local):return lambda bank:bank.square().sum((2,3))

def setup(family='gmm',terminal_at=None,truncated_at=None):
    world=world_methods()();world.num_envs=1;world.envs=SyntheticPool(terminal_at,truncated_at)
    model=LocalProposer(family,width=16,depth=1,heads=2).eval()
    stats=dict(lowdim_mean=np.zeros(11,np.float32),lowdim_std=np.ones(11,np.float32),
               action_mean=np.zeros(2,np.float32),action_std=np.ones(2,np.float32))
    factory=lambda h,s:Policy(Backend(),model,stats,h,s,1269)
    return world,factory

def runtime_check(device='cpu'):
    """Inside first charged technical job: actual proposer+CEM, artificial models.

    Restore CPU/CUDA global RNG state. No optimizer, pretrained model or physics.
    This checks the pinned GPU kernels, not scientific performance or throughput.
    """
    from lgp1_sampler_check import check
    assert torch.are_deterministic_algorithms_enabled()
    devices=[torch.cuda.current_device()] if str(device).startswith('cuda') else []
    with torch.random.fork_rng(devices=devices):
        sampler=check(device)
        for family in ('gmm','diffusion'):
            world,factory=setup(family,terminal_at=1);record=dict(state=np.zeros(7),goal_state=np.zeros(7));actions=[]
            e=FreshEpisode(world,factory)
            for _ in range(2):
                p=factory(75,8301);p.model.to(device)
                e.factory=lambda h,s,p=p:p
                e.start(record,horizon=75,budget=150,seed=8301);e.advance()
                actions.append(world.infos['action'].copy());assert e.status=='done';p.finish()
            np.testing.assert_array_equal(actions[0],actions[1]);world.close()
    return dict(passed=True,device=str(device),torch=torch.__version__,strict_determinism=True,
                families=['gmm','diffusion'],pinned_world_sha256=WORLD_SHA,
                real_sampling_and_30_round_cem=True,repeat_bit_identical=True,
                sampler=sampler,research_model_calls=0,optimizer_steps=0,simulator_calls=0)

class Lifecycle(unittest.TestCase):
    def test_original_missing_method_is_detected_by_pinned_world(self):
        world,_=setup()
        old=SimpleNamespace(seed=8301,set_env=lambda env:None)
        with self.assertRaisesRegex(AttributeError,'set_seed'):world.set_policy(old)

    def test_seed_binding_idempotent_and_global_rng_untouched(self):
        world,factory=setup();p=factory(75,8301)
        py=random.getstate();npstate=np.random.get_state();t=torch.random.get_rng_state().clone()
        world.set_policy(p);p.set_seed(8301)
        self.assertIs(p.env,world.envs)
        self.assertEqual(py,random.getstate());np.testing.assert_array_equal(npstate[1],np.random.get_state()[1])
        self.assertEqual(npstate[2:],np.random.get_state()[2:]);self.assertTrue(torch.equal(t,torch.random.get_rng_state()))
        for seed in (8302,None,True,8301.0):
            with self.assertRaisesRegex(RuntimeError,'seed mismatch'):p.set_seed(seed)
        p.elapsed=1
        with self.assertRaisesRegex(RuntimeError,'Cannot reseed'):p.set_seed(8301)
        p.elapsed=0;p.finish()
        with self.assertRaisesRegex(RuntimeError,'Cannot reseed'):p.set_seed(8301)

    def test_driver_two_full_budgets_and_fresh_restart_real_sampling_cem(self):
        # Actual sampling (both families), FP32 decoder/projection and all 30 CEM
        # rounds. Only frozen neural predictions and physics are artificial.
        for family in ('gmm','diffusion'):
            world,factory=setup(family);episode=FreshEpisode(world,factory)
            record=dict(state=np.zeros(7),goal_state=np.zeros(7));prior=None
            for h in (75,150):
                episode.start(record,horizon=h,budget=2*h,seed=8301)
                self.assertIsNot(episode.policy,prior);self.assertIs(episode.policy.env,world.envs)
                actions=[]
                while episode.status=='running':
                    episode.advance();actions.append(world.infos['action'].copy())
                p=episode.policy
                self.assertEqual(episode.steps,2*h);self.assertEqual(p.elapsed,2*h)
                self.assertEqual([s['remaining'] for s in p.diagnostic_history],list(range(h,0,-15))*2)
                self.assertEqual([s['elapsed'] for s in p.diagnostic_history],list(range(0,2*h,15)))
                self.assertTrue(all(len(s['rounds'])==30 for s in p.diagnostic_history))
                self.assertTrue(all(a.dtype==np.float32 and np.isfinite(a).all() and (abs(a)<=1).all() for a in actions))
                with self.assertRaises(RuntimeError):episode.advance()
                p.finish();self.assertFalse(p.history);self.assertFalse(p._action_buffer);prior=p
            self.assertEqual(world.envs.resets,[8301,8301]);world.close();self.assertTrue(world.envs.closed)

    def test_native_terminal_truncation_and_repeat_stream_identity(self):
        for terminal,truncated in ((1,None),(None,1)):
            world,factory=setup(terminal_at=terminal,truncated_at=truncated)
            e=FreshEpisode(world,factory);record=dict(state=np.zeros(7),goal_state=np.zeros(7));actions=[]
            for _ in range(2):
                e.start(record,horizon=75,budget=150,seed=8301);self.assertTrue(e.advance())
                actions.append(world.infos['action'].copy())
                self.assertEqual(bool(world.terminateds[0]),terminal==1)
                self.assertEqual(bool(world.truncateds[0]),truncated==1)
                with self.assertRaises(RuntimeError):e.advance()
                e.policy.finish()
            np.testing.assert_array_equal(actions[0],actions[1])

if __name__=='__main__':
    torch.set_num_threads(1);unittest.main()
