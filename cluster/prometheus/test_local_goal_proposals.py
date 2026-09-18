"""Synthetic-only LGP1 tests. No checkpoint, data loader, physics or optimizer."""
import unittest
import numpy as np
import torch
from local_goal_proposals import (Context, common_cem, convert_actions, local_target,
                                  lowdim_from_state, stage_clock, stream_seed)
from local_goal_models import LocalProposer, gmm_nll, velocity_loss, sample


class InterfaceTests(unittest.TestCase):
    def ctx(self,b=1):
        return Context(np.zeros((b,3,192)),np.zeros((b,1,192)),np.zeros((b,1,192)),
                       np.zeros((b,11)),np.full(b,75),np.full(b,15))

    def test_sample_only_and_budget(self):
        # A function with no density/mixture API suffices.
        def proposer(c,k,r): return r.normal(size=(len(c.history),k,3,10))
        cost=lambda c,x: np.square(x).sum((2,3))
        mean,trace=common_cem(self.ctx(3),proposer,cost,proposal_rng=np.random.default_rng(1),
                             refinement_rng=np.random.default_rng(2))
        self.assertEqual(mean.shape,(3,3,10))
        self.assertEqual(sum(x['candidates'] for x in trace),9000)
        self.assertTrue(np.isfinite(mean).all())

    def test_ties_std_and_final_mean(self):
        bank=np.arange(120.).reshape(1,4,3,10)
        result,trace=common_cem(self.ctx(),lambda *a:bank,lambda c,x:np.zeros((1,4)),
            proposal_rng=None,refinement_rng=np.random.default_rng(1),candidates=4,elites=2,rounds=1)
        np.testing.assert_array_equal(trace[0]['elite_indices'],[[0,1]])
        np.testing.assert_array_equal(result,bank[:,:2].mean(1))

    def test_equivalent_banks_ignore_sampling_consumption(self):
        bank=np.arange(120.).reshape(1,4,3,10)
        def a(c,k,r): r.normal(size=100); return bank.copy()
        def b(c,k,r): return bank.copy()
        def run(p): return common_cem(self.ctx(),p,lambda c,x: (x*x).sum((2,3)),
            proposal_rng=np.random.default_rng(7),refinement_rng=np.random.default_rng(8),
            candidates=4,elites=2,rounds=3)[0]
        np.testing.assert_array_equal(run(a),run(b))
        self.assertNotEqual(stream_seed('a',0,'proposal',1),stream_seed('a',0,'refine',1))

    def test_coordinates(self):
        x=np.arange(60.).reshape(2,3,10)/100
        y=convert_actions(x,[.1,.2],[.3,.4],[.2,.3],[.5,.6])
        z=convert_actions(y,[.2,.3],[.5,.6],[.1,.2],[.3,.4])
        np.testing.assert_allclose(x,z,atol=2e-7)
        with self.assertRaises(ValueError): convert_actions(x,[0,0],[0,1],[0,0],[1,1])

    def test_state_and_target_boundary(self):
        np.testing.assert_array_equal(lowdim_from_state(np.arange(7)[None]),[[0,1,2,3,4,5,6,0,1,5,6]])
        c=self.ctx(2); calls=[]
        def gen(h,f,s,r,t): calls.append(r.copy()); return np.ones_like(f)
        target=local_target(c.history,c.far_goal,c.lowdim,np.array([15,30]),gen)
        np.testing.assert_array_equal(target[0],c.far_goal[0])
        self.assertEqual(len(calls),1); np.testing.assert_array_equal(calls[0],[30])

    def test_full_budget_clock(self):
        for h in (75,150):
            self.assertEqual(stage_clock(h,h),(h,h))
            self.assertEqual(stage_clock(h,2*h-15),(15,15))
            self.assertEqual(len(range(0,2*h,15)),2*h//15)
            with self.assertRaises(ValueError): stage_clock(h,2*h)

    def test_bad_context_bank_cost(self):
        with self.assertRaises(ValueError): self.ctx(0).validate()
        for bank,cost in ((np.zeros((1,4,3,9)),np.zeros((1,4))),
                          (np.full((1,4,3,10),np.nan),np.zeros((1,4))),
                          (np.zeros((1,4,3,10)),np.full((1,4),np.nan))):
            with self.assertRaises(ValueError):
                common_cem(self.ctx(),lambda *a:bank,lambda *a:cost,proposal_rng=None,
                           refinement_rng=None,candidates=4,elites=2,rounds=1)

    def test_models_losses_sampling(self):
        torch.set_num_threads(1)
        c=self.ctx(2)
        inputs=tuple(torch.tensor(x,dtype=torch.float32) for x in
                     (c.history,c.local_goal,c.far_goal,c.lowdim,c.remaining))
        clean=torch.zeros(2,3,10)
        for family in ('gmm','diffusion'):
            torch.manual_seed(1)
            model=LocalProposer(family,width=16,depth=1,heads=2).eval()
            def draw(): return sample(model,inputs,4,torch.Generator().manual_seed(3))
            x=draw(); self.assertEqual(x.shape,(2,4,3,10)); self.assertTrue(torch.isfinite(x).all())
            torch.testing.assert_close(x,draw(),rtol=0,atol=0)
            loss=(gmm_nll(model(*inputs),clean) if family=='gmm' else
                  velocity_loss(model,inputs,clean,torch.ones_like(clean),torch.tensor([0,999])))
            self.assertEqual(loss.shape,(2,)); self.assertTrue(torch.isfinite(loss).all())

    def test_gmm_formula(self):
        import math
        out=(torch.zeros(2,8),torch.zeros(2,8,3,10),torch.zeros(2,8,3,10))
        torch.testing.assert_close(gmm_nll(out,torch.zeros(2,3,10)),
                                  torch.full((2,),15*math.log(2*math.pi)))

    def test_shared_projection_before_every_cost(self):
        seen=[]
        def cost(c,x):
            self.assertLessEqual(np.abs(x).max(),1)
            seen.append(x.copy()); return (x*x).sum((2,3))
        out,_=common_cem(self.ctx(),lambda c,k,r:np.full((1,k,3,10),4.),cost,
            proposal_rng=None,refinement_rng=np.random.default_rng(1),candidates=4,
            elites=2,rounds=3,project=lambda x:np.clip(x,-1,1))
        self.assertEqual(len(seen),3);self.assertLessEqual(np.abs(out).max(),1)


if __name__=='__main__': unittest.main()
