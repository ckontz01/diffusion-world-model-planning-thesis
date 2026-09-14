"""Synthetic CPU-only tests: no checkpoint loads, real model or physics calls."""
import ast
import hashlib
import json
import sys
import tempfile
import types
import unittest
from collections import deque
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
import single_anchor_ranking as s
from single_anchor_ranking_runner import capture_selection,exact,match_saved
from single_anchor_ranking_dispatch import allowed
from verify_single_anchor_ranking import check_row
from diffusion_bottleneck_branch import array_hash


def real_policy_class():
    # Execute the actual policy class alone against a synthetic BasePolicy. This
    # avoids importing stable_worldmodel or any real environment/model dependency.
    path=Path(__file__).with_name('gdp_cem_e18_runtime.py')
    tree=ast.parse(path.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='E18ScheduledPolicy')
    node.bases=[ast.Name(id='object',ctx=ast.Load())]
    module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    ns={'Any':object,'np':np,'torch':torch,'deque':deque,'deepcopy':deepcopy}
    exec(compile(module,str(path),'exec'),ns)
    return ns['E18ScheduledPolicy']


class SyntheticSolver:
    def __init__(self):
        self.proposal_generator=torch.Generator().manual_seed(4)
        self.gmm_generator=torch.Generator().manual_seed(4)
        self.device=torch.device('cpu');self.primitive_action_dim=2
        self.n_propose=0;self.n_rollout=0
    def _propose(self,**kw):
        self.n_propose+=1
        torch.rand(1,generator=self.proposal_generator)
        n=1 if kw['count']==64 else 64
        x=torch.zeros(n,kw['count'],25,2)
        if n==1:x[0,1]=.1
        return x,x.clone(),x.clone()
    def _rollout(self,*a,**kw):
        self.n_rollout+=1
        if self.n_rollout==1:
            z=torch.ones(1,64,192);z[0,1]=0
        else:
            z=torch.ones(64,8,192);z[0]=0
        return z
    def _encode(self,*a,**kw):return torch.zeros(1,192),torch.zeros(1,192)
    def _predict_intermediate_state(self,**kw):return torch.zeros(64,7),torch.zeros(64,192)
    def solve(self,*args,**kw):
        self._encode()
        first=self._propose(count=64,current=torch.zeros(1,192),goal=torch.zeros(1,192),state=torch.zeros(1,7))
        self._rollout(None,None)
        self._predict_intermediate_state()
        self._propose(count=8,current=torch.zeros(64,192),goal=torch.zeros(64,192),state=torch.zeros(64,7))
        self._rollout(None,None)
        return {'actions':first[1][0,0,:15].reshape(1,3,10),'solver_seconds':0}


class RankingTests(unittest.TestCase):
    def test_bounds_independent_sum(self):
        b=s.bounds(1)
        self.assertEqual(b['logical_branches'],256)
        self.assertEqual(b['post_anchor_steps'],32*2*(150+120+300+270))
        self.assertEqual(b['prefix_steps'],32*2*2*30)
        self.assertEqual(b['physical_steps'],57600)
        self.assertEqual(b['planning_calls'],3840)
        self.assertEqual(b['continuation_calls'],3328)
        self.assertEqual(s.bounds(2)['model_constructions'],64)

    def test_protected_coordinate_rejected(self):
        for ref in (-1,1600,5999):
            with self.assertRaises(ValueError):s.coordinate(ref,75,0,'immediate',0)

    def test_schedule_restart_and_budget(self):
        self.assertEqual([s.schedule(75,t)[0] for t in (0,30,45,60,75,135)],[75,45,30,15,75,15])
        with self.assertRaises(ValueError):s.schedule(75,150)

    def test_real_policy_lifecycle_all_budgets(self):
        Policy=real_policy_class()
        for h in s.HORIZONS:
            for anchor in s.ANCHORS:
                calls=[];manipulated=[]
                class Planner:
                    device='cpu';primitive_action_dim=2
                    def configure(self,**kw):pass
                    def solve(self,*args,**kwargs):
                        absolute=len(calls)*15;calls.append((absolute,kwargs['delta_value']))
                        if absolute==anchor:manipulated.append(absolute)
                        return {'actions':torch.full((1,3,10),.1 if absolute==anchor else 0.)}
                p=Policy(Planner(),schedule=(15,)*(h//15),environment_budget=2*h,
                         state_key='state',process={},transform={})
                p.set_env(types.SimpleNamespace(num_envs=1,action_space=types.SimpleNamespace(shape=(1,2))))
                p._prepare_info=lambda info:info
                state=np.zeros(7,np.float64);history={'actions':np.zeros((300,2),np.float32),'states':np.zeros((301,7))}
                after=[]
                trace=s.execute_branch(p,lambda:{'state':np.zeros((1,7))},
                    lambda action:(state.copy(),np.array([False,False])),lambda absolute,policy:after.append(absolute),
                    horizon=h,anchor=anchor,history=history)
                self.assertEqual(len(trace['actions']),2*h-anchor)
                self.assertEqual(manipulated,[anchor]);self.assertEqual(after[-1],2*h)
                self.assertEqual(calls,[(t,h-t%h) for t in range(0,2*h,15)])
                self.assertEqual(p._stage_index,2*h//15);self.assertFalse(p._action_buffer)
                np.testing.assert_array_equal(trace['actions'][:15],np.full((15,2),.1,np.float32))
                self.assertTrue((trace['actions'][15:]==0).all())

    def test_termination_first_and_tail_never_poststeps(self):
        for anchor,stop,trunc in ((0,4,False),(30,34,False),(30,62,False),(0,19,True)):
            class P:
                _stage_index=0;_action_buffer=deque();stages=[s.schedule(75,t) for t in range(0,150,15)]
                def get_action(self,info):
                    if not self._action_buffer:self._action_buffer.extend([0]*15);self._stage_index+=1
                    self._action_buffer.popleft();return np.zeros((1,2),np.float32)
            count=[0]
            def step(action):
                count[0]+=1
                self.assertLessEqual(count[0],stop)
                return np.zeros(7),np.array([count[0]==stop and not trunc,count[0]==stop and trunc])
            r=s.execute_branch(P(),lambda:{},step,lambda *args:None,horizon=75,anchor=anchor,
                history={'actions':np.zeros((30,2),np.float32),'states':np.zeros((31,7))})
            self.assertEqual(len(r['states']),stop-anchor);self.assertEqual(count[0],stop)

    def test_hook_matched_calls_and_no_random_draw(self):
        production=types.SimpleNamespace(continuation_score=lambda cost:torch.topk(cost,2,dim=-1,largest=False,sorted=False).values.mean(-1))
        pair=[]
        with patch.dict(sys.modules,{'gdp_cem_e18_closed_loop':production}):
            for arm in s.ARMS:
                solver=SyntheticSolver();original=solver.solve;global_before=torch.get_rng_state().clone()
                output,bank=capture_selection(solver,original,(),{},arm)
                self.assertEqual((solver.n_propose,solver.n_rollout),(2,2))
                self.assertTrue(torch.equal(global_before,torch.get_rng_state()))
                self.assertEqual(int(bank['chosen']),0 if arm=='continuation' else 1)
                self.assertTrue((output['actions']==(0 if arm=='continuation' else .1)).all())
                self.assertEqual(solver._propose.__func__,SyntheticSolver._propose)
                pair.append(bank)
        for key in pair[0]:
            if key!='chosen':exact(pair[0][key],pair[1][key])

    def test_hook_restores_on_failure(self):
        production=types.SimpleNamespace(continuation_score=lambda x:x)
        solver=SyntheticSolver()
        with patch.dict(sys.modules,{'gdp_cem_e18_closed_loop':production}):
            with self.assertRaisesRegex(RuntimeError,'synthetic'):
                capture_selection(solver,lambda:(_ for _ in ()).throw(RuntimeError('synthetic')),(),{},'immediate')
        self.assertEqual(solver._rollout.__func__,SyntheticSolver._rollout)

    def test_first_index_tie_and_same_choice(self):
        class Tied(SyntheticSolver):
            def _rollout(self,*a,**kw):
                z=super()._rollout(*a,**kw)
                return z*0
        production=types.SimpleNamespace(continuation_score=lambda cost:torch.topk(cost,2,dim=-1,largest=False,sorted=False).values.mean(-1))
        result=[]
        with patch.dict(sys.modules,{'gdp_cem_e18_closed_loop':production}):
            for arm in s.ARMS:
                solver=Tied();output,bank=capture_selection(solver,solver.solve,(),{},arm)
                self.assertEqual(int(bank['chosen']),0)
                result.append(output['actions'].numpy())
        exact(*result)

    def test_no_treatment_origin_for_t30(self):
        # Source-level guard complements the actual policy's prefix/budget tests:
        # world/factory/reset calls must remain INSIDE the per-arm loop.
        tree=ast.parse(Path(__file__).with_name('single_anchor_ranking_runner.py').read_text())
        run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        arm_loop=next(n for n in ast.walk(run) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='arm')
        names=[n.func.id if isinstance(n.func,ast.Name) else n.func.attr if isinstance(n.func,ast.Attribute) else ''
               for n in ast.walk(arm_loop) if isinstance(n,ast.Call)]
        self.assertIn('World',names);self.assertIn('factory',names);self.assertIn('reset_world',names)

    def test_dispatch_approval_before_submission(self):
        tree=ast.parse(Path(__file__).with_name('single_anchor_ranking_dispatch.py').read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        approval=min(n.lineno for n in calls if n.func.id=='check_approval')
        submit=min(n.lineno for n in calls if n.func.id=='command' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='sbatch')
        self.assertLess(approval,submit)

    def test_same_step_predicate_and_no_initial_success(self):
        goal=np.zeros(7,np.float64);states=np.zeros((2,7),np.float64)
        states[0,4]=1;states[1,0]=21
        r=s.physical(states,np.zeros((2,2),bool),goal,2)
        self.assertFalse(r['success'])
        # No initial state is passed into the reducer, even if anchor was at goal.
        self.assertEqual(r['delivered'],2)

    def test_success_first_included_no_survivor_filter(self):
        states=np.zeros((4,7),np.float64);states[:3,0]=50
        flags=np.zeros((4,2),bool);flags[-1,0]=True
        r=s.physical(states,flags,np.zeros(7),150)
        self.assertTrue(r['success']);self.assertTrue(r['first_success']);self.assertIsNone(r['handoff_margin'])

    def test_domain_caps_flags(self):
        states=np.zeros((150,7));states[:,0]=50;goal=np.zeros(7);flags=np.zeros((150,2),bool)
        self.assertEqual(s.physical(states,flags,goal,150)['delivered'],150)
        for bad,fl,cap in ((states[:10],flags[:10],150),(states,flags,149)):
            with self.assertRaises(ValueError):s.physical(bad,fl,goal,cap)
        states[0,4]=4*np.pi
        with self.assertRaises(ValueError):s.physical(states,flags,goal,150)
        states[0,4]=2*np.pi
        self.assertFalse(s.physical(states,flags,goal,150)['success'])
        flags[3,1]=True
        with self.assertRaises(ValueError):s.physical(states,flags,goal,150)

    def test_reference_weighting_and_repeat_rejection(self):
        rows=[]
        for ref in s.REFS:
            for h in s.HORIZONS:
                for a in s.ANCHORS:
                    rows.append(dict(reference=ref,repeat=0,horizon=h,anchor=a,
                        immediate={'success':h==75 and a==0,'closest_margin':1},
                        continuation={'success':False,'closest_margin':2}))
        result=s.reference_effects(rows)
        self.assertEqual(result['summary']['success_difference_pp']['mean'],25)
        self.assertEqual(result['independent_references'],32)
        with self.assertRaises(ValueError):s.reference_effects(rows+rows)
        rows[0]['repeat']=1
        with self.assertRaises(ValueError):s.reference_effects(rows)

    def test_reservation_and_outstanding_charge(self):
        self.assertTrue(allowed(13500,1_936_000_000))
        self.assertFalse(allowed(13501,0));self.assertFalse(allowed(0,1_936_000_001))
        self.assertFalse(allowed(13500,0,1));self.assertFalse(allowed(-1,0))

    def test_no_approval_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'approval.json';path.write_text('{}')
            with self.assertRaises(ValueError):s.check_approval(path,'a'*64,'b'*64)

    def test_changed_saved_bank_rejected(self):
        with self.assertRaises((KeyError,ValueError)):
            match_saved({'first_raw':np.zeros(1)},{'h75/t0/first_raw':np.ones(1)},75,0)

    def test_independent_full_trace_and_corruption_rejection(self):
        production=types.SimpleNamespace(continuation_score=lambda cost:torch.topk(cost,2,dim=-1,largest=False,sorted=False).values.mean(-1))
        solver=SyntheticSolver()
        with patch.dict(sys.modules,{'gdp_cem_e18_closed_loop':production}):
            _,bank=capture_selection(solver,solver.solve,(),{},'continuation')
        bank.update(states=np.zeros((150,7)),flags=np.zeros((150,2),bool),
            actions=np.zeros((150,2),np.float32),goal_state=np.zeros(7),prefix_actions=np.zeros((0,2),np.float32),
            anchor_state=np.zeros(7),anchor_controller=np.zeros(10),decoder_mean=np.zeros(2),decoder_scale=np.ones(2))
        bank['states'][:,0]=50;bank['anchor_state'][0]=50
        mapping={'second_raw':'baseline/second_raw','second_planner':'baseline/second_planner',
            'scoring_terminal':'baseline/scoring_terminal','supplied_state':'baseline/supplied_state',
            'supplied_latent':'baseline/supplied_latent','costs':'baseline/costs',
            'immediate':'greedy64/costs','continuation':'baseline/scores','proposal_after':'post_baseline_rng'}
        saved={'h75/t0/'+mapping.get(k,k):v.copy() for k,v in bank.items()}
        calls=[]
        for i,at in enumerate(range(0,150,15)):
            plan=np.zeros((1,3,10),np.float32);bank[f'plan-{at}']=plan
            diag=dict(call=i,delta=75-at%75,tau=15,arm='vad_continuation',family='vad',first_candidate_count=64,
                      continuations_per_first=8 if 75-at%75>=30 else 0)
            for name,key in (('proposal','proposal_after'),('gmm','gmm_after')):
                digest=hashlib.sha256(bank[key].tobytes()).hexdigest()
                diag[name+'_generator_before_sha256']=digest;diag[name+'_generator_after_sha256']=digest
            calls.append(dict(at=at,plan_hash=array_hash(plan),diagnostics=diag))
        trace=dict(states=np.vstack([bank['anchor_state'],bank['states']]),actions=bank['actions'],goal_state=bank['goal_state'])
        historical=dict(calls=deepcopy(calls),delivered=150,success=0,native_truncation=False)
        row=dict(horizon=75,anchor=0,arm='continuation',interventions=1,calls=calls,
                 metrics=s.physical(bank['states'],bank['flags'],bank['goal_state'],150),
                 handoff=dict(absolute=15,stage_index=1,buffer_length=0))
        check_row(bank.__getitem__,row,historical,trace,saved)
        for mutate in (lambda d:d.update(interventions=2),lambda d:d['handoff'].update(absolute=0),
                       lambda d:d['calls'][5]['diagnostics'].update(delta=15)):
            bad=deepcopy(row);mutate(bad)
            with self.assertRaises((ValueError,AssertionError)):check_row(bank.__getitem__,bad,historical,trace,saved)
        corrupt={k:v.copy() for k,v in bank.items()};corrupt['actions'][15,0]=.2
        with self.assertRaises((ValueError,AssertionError)):check_row(corrupt.__getitem__,row,historical,trace,saved)


if __name__=='__main__':unittest.main()
