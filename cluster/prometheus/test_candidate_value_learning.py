"""Synthetic-only preparation tests: no real files, environments or models."""
import unittest
from types import SimpleNamespace
import numpy as np
import torch
import candidate_value_learning as c
from candidate_value_hook import capture


class FakeSolver:
    def __init__(self):
        self.device=torch.device('cpu')
        self.statistics=SimpleNamespace(latent_mean=torch.zeros(192),latent_std=torch.ones(192))
        self.proposal_generator=torch.Generator().manual_seed(4)
        self.gmm_generator=torch.Generator().manual_seed(5)
    def _encode(self, info):return torch.zeros(1,192),torch.ones(1,192)
    def _propose(self, **kw):
        a=torch.randn(len(kw['current']),kw['count'],25,2,generator=self.proposal_generator)
        return a,a.clone(),a.clone()
    def _rollout(self,current,planner,**kw):
        return planner[:,:,:15].mean((-1,-2))[:,:,None].expand(-1,-1,192)
    def _predict_intermediate_state(self,**kw):return torch.zeros(64,7),torch.zeros(64,192)
    def solve(self,info,*,raw_state,delta_value,tau_value):
        z,g=self._encode(info)
        _,a,_=self._propose(current=z,goal=g,state=raw_state,count=64)
        end=self._rollout(z,a,tau=15)
        scores=(end-g[:,None]).square().sum(-1)
        if delta_value>=30:
            s,zz=self._predict_intermediate_state()
            _,aa,_=self._propose(current=zz,goal=g.expand(64,-1),state=s,count=8)
            ends=self._rollout(zz,aa,tau=15)
            costs=(ends-g[:,None]).square().sum(-1).reshape(1,64,8)
            scores=torch.topk(costs,2,largest=False,sorted=False).values.mean(-1)
        i=int(scores.argmin())
        return {'actions':a[:,:,:15].reshape(64,3,10)[i:i+1].clone()}


class Tests(unittest.TestCase):
    def test_allocation(self):
        a=c.allocation();ids=sum(a.values(),[])
        self.assertEqual({k:len(v) for k,v in a.items()},c.SIZES)
        self.assertEqual(len(set(ids)),160)
        self.assertTrue(all(0<=r<1600 and r not in c.HISTORICAL for r in ids))
        c.check_source_groups({r:str(r) for r in ids})
        with self.assertRaises(ValueError):c.check_source_groups({r:'alias' for r in ids})
    def test_sampling(self):
        ref=c.allocation()['train'][0];a=np.arange(64.);b=a[::-1]
        torch_before=torch.get_rng_state().clone()
        plan=c.sample_bank(a,b,reference=ref,h=75,t=0)
        self.assertEqual(plan['indices'][:2],[63,0])
        self.assertEqual(len(set(plan['indices'])),8)
        self.assertEqual(plan['other_slots'],6)
        self.assertEqual(plan,c.sample_bank(a,b,reference=ref,h=75,t=0))
        self.assertTrue(torch.equal(torch_before,torch.get_rng_state()))
        self.assertEqual(c.sample_bank(a,a,reference=ref,h=75,t=135)['other_slots'],7)
        with self.assertRaises(ValueError):c.sample_bank(a,b,reference=1600,h=75,t=0)
        with self.assertRaises(ValueError):
            c.sample_bank(a,b,reference=c.allocation()['closed_loop'][0],h=75,t=0)
    def test_clock(self):
        for h in (75,150):
            for t in range(0,2*h,15):
                values=c.clock(h,t)
                self.assertAlmostEqual(values[2],(2*h-t)/300,places=6)
                self.assertAlmostEqual(values[3],(h-t%h)/150,places=6)
            self.assertEqual(c.clock(h,h)[-1],1.)
            self.assertAlmostEqual(c.clock(h,2*h-15)[2],.05,places=6)
        with self.assertRaises(ValueError):c.clock(75,150)
    def test_feature_allowlist(self):
        v=dict(current=np.zeros((2,192)),goal=np.zeros((2,192)),predicted=np.zeros((2,192)),
               state=np.zeros((2,7)),actions=np.zeros((2,15,2)),time=np.tile(c.clock(75,0),(2,1)))
        self.assertEqual(c.features(v).shape,(2,619))
        for bad in ('reference','success','actual_future'):
            with self.assertRaises(ValueError):c.features({**v,bad:0})
        v['state'][0,0]=np.nan
        with self.assertRaises(ValueError):c.features(v)
    def test_targets(self):
        for at in (0,14,29):
            s=np.zeros(at+1,bool);s[-1]=True
            r=c.success_target(s,np.zeros_like(s),remaining=30)
            self.assertEqual(r['success'],1)
            self.assertEqual(r['first_chunk_success'],at<15)
        r=c.success_target(np.zeros(30,bool),np.zeros(30,bool),remaining=30)
        self.assertEqual(r['success'],0)
        self.assertTrue(r['policy_conditional_negative'])
        with self.assertRaises(ValueError):c.success_target(np.zeros(29,bool),np.zeros(29,bool),remaining=30)
        with self.assertRaises(ValueError):c.success_target(np.array([True,False]),np.zeros(2,bool),remaining=30)
        self.assertEqual(c.success_target(np.zeros(0,bool),np.zeros(0,bool),remaining=30,planner_failure=True)['success'],0)
    def test_hierarchical_weights(self):
        keys=[(r,h,t,i,j) for r in (1,2) for h in (75,150)
              for t in ((0,30) if r==1 else (0,)) for i in range(8) for j in range(2)]
        w=c.row_weights(keys)
        self.assertAlmostEqual(float(w.sum()),1.)
        self.assertAlmostEqual(float(w[[k[0]==1 for k in keys]].sum()),.5)
    def test_models_and_synthetic_optimizer(self):
        self.assertEqual(sum(p.numel() for p in c.ValueModel().parameters()),87681)
        self.assertEqual(sum(p.numel() for p in c.ValueModel(True).parameters()),620)
        ids=c.allocation()['train'][:20]
        keys=[(r,75,0,i,j) for r in ids for i in range(8) for j in range(2)]
        y=np.array([i%2 for _,_,_,i,_ in keys],dtype=np.float32)
        x=np.zeros((len(keys),619),np.float32);x[:,0]=2*y-1
        before=torch.get_rng_state().clone()
        model=c.fit(x,y,keys,epochs=2)
        p=c.probabilities([model],x)
        self.assertEqual(p.shape,y.shape)
        self.assertTrue(np.isfinite(p).all())
        self.assertTrue(torch.equal(before,torch.get_rng_state()))
        with self.assertRaises(ValueError):c.fit(x,np.zeros_like(y),keys,epochs=1)
        bad=[(c.allocation()['validation'][0],)+k[1:] for k in keys]
        with self.assertRaises(ValueError):c.fit(x,y,bad,epochs=1)
    def test_bank_metrics(self):
        p=np.arange(8)/8;y=np.zeros((8,2),int);y[7]=1
        out=c.bank_metrics(p,y,continuation_index=0,immediate_index=1,original_indices=np.arange(8))
        self.assertEqual(out['selected_index'],7)
        self.assertEqual(out['selected_empirical_success'],1)
        self.assertEqual(out['sampled_empirical_regret'],0)
        self.assertIsNone(c.bank_metrics(p,y*0,continuation_index=0,immediate_index=1,original_indices=np.arange(8))['pairwise_concordance'])
        tied=c.bank_metrics(p*0,y,continuation_index=0,immediate_index=1,original_indices=np.arange(8)[::-1])
        self.assertEqual(tied['selected_index'],7)
    def test_cost(self):
        p=c.cost_plan()
        self.assertEqual(p['label_ceiling'],16384)
        self.assertEqual(p['collection_steps'],3744000)
        self.assertEqual(p['closed_loop_runs'],512)
        self.assertEqual(p['maximum_scheduled_gpu_seconds'],256*600+32*600+2*300)
        self.assertLess(p['maximum_scheduled_gpu_seconds'],p['aggregate_gpu_seconds_cap'])
    def test_reference_interval(self):
        out=c.reference_interval(np.zeros(32))
        self.assertEqual(out['n_references'],32)
        self.assertEqual(out['lower'],0)
        self.assertEqual(out['upper'],0)
    def test_hook_all_stages_and_episode_reset(self):
        # Fake native solves at every decision, including final stage and restart.
        for episode in range(2):
            for h in (75,150):
                solver=FakeSolver()
                for t in range(0,2*h,15):
                    original=solver.solve;methods={k:getattr(solver,k) for k in ('_encode','_propose','_rollout')}
                    kw=dict(raw_state=torch.zeros(1,7),delta_value=h-t%h,tau_value=15)
                    out,bank=capture(solver,original,({},),kw,h=h,t=t,
                                     selector=lambda b: int(b['immediate'].argmin()))
                    self.assertEqual(bank['x'].shape,(64,619))
                    np.testing.assert_array_equal(out['actions'].numpy().reshape(15,2),
                                                  bank['planner_actions'][bank['immediate_index']])
                    for k,v in methods.items():self.assertEqual(getattr(solver,k),v)
    def test_hook_restores_on_failure(self):
        s=FakeSolver();original=s._encode
        def fail(*a,**kw):raise RuntimeError('synthetic fault')
        with self.assertRaises(RuntimeError):capture(s,fail,({},),dict(delta_value=75,tau_value=15),h=75,t=0)
        self.assertEqual(s._encode,original)
    def test_hook_bad_score_does_not_fallback(self):
        s=FakeSolver()
        with self.assertRaises(ValueError):
            capture(s,s.solve,({},),dict(raw_state=torch.zeros(1,7),delta_value=75,tau_value=15),
                    h=75,t=0,selector=lambda b: -1)


if __name__=='__main__':
    torch.set_num_threads(1)
    unittest.main()
