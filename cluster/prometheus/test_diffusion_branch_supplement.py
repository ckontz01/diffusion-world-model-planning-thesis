import unittest
import numpy as np
from diffusion_bottleneck import IntegrityError
from verify_diffusion_branch_supplement import (checked_physical, coverage,
    immediate_cost, counters, provenance, MODEL_SHA)


class SupplementTests(unittest.TestCase):
    def trace(self, n=15):
        s=np.zeros((n,7),np.float64); s[:,0]=40
        return s,np.zeros((n,2),bool),np.zeros(7,np.float64)

    def test_full_nonterminal_cap(self):
        self.assertEqual(checked_physical(*self.trace(),15)['delivered'],15)

    def test_short_nonterminal_rejected(self):
        for n,cap in ((14,15),(15,30)):
            with self.assertRaises(IntegrityError): checked_physical(*self.trace(n),cap)

    def test_native_early_success_and_truncation(self):
        s,f,g=self.trace(4); f[-1,1]=True
        self.assertFalse(checked_physical(s,f,g,15)['success'])
        s[-1]=0; f[-1]=[True,False]
        self.assertTrue(checked_physical(s,f,g,30)['success'])

    def test_postterminal_step_rejected(self):
        s,f,g=self.trace();f[0,1]=True
        with self.assertRaises(IntegrityError):checked_physical(s,f,g,15)

    def test_false_success_rejected(self):
        s,f,g=self.trace();f[-1,0]=True
        with self.assertRaises(AssertionError):checked_physical(s,f,g,15)

    def test_exact_state_endpoint_only(self):
        s,f,g=self.trace();s[:,4]=2*np.pi
        before=s.tobytes();checked_physical(s,f,g,15);self.assertEqual(s.tobytes(),before)
        for angle in (-1e-30,np.nextafter(2*np.pi,np.inf),4*np.pi,np.nan):
            s[:,4]=angle
            with self.assertRaises(IntegrityError):checked_physical(s,f,g,15)

    def test_bad_goals_and_dtype(self):
        s,f,g=self.trace()
        for bad in (g[:6],g.astype(np.float32),np.full(7,np.nan)):
            with self.assertRaises(IntegrityError):checked_physical(s,f,bad,15)
        g[4]=2*np.pi
        with self.assertRaises(IntegrityError):checked_physical(s,f,g,15)
        with self.assertRaises(IntegrityError):checked_physical(s.astype(np.float32),f,np.zeros(7),15)

    def test_greedy_fabricated_costs_rejected(self):
        p=np.zeros((1,64,192),np.float32);g=np.zeros((64,192),np.float32)
        with self.assertRaises(AssertionError):immediate_cost(p,g,np.arange(64,0,-1),63)
        immediate_cost(p,g,np.zeros(64),0)
        with self.assertRaises(IntegrityError):immediate_cost(p,g,np.zeros(64),63)

    def rows(self):return [{'horizon':h,'anchor':t,'available':True} for h in (75,150) for t in (0,30)]

    def test_duplicate_missing_rows(self):
        rows=self.rows();h={75:{'delivered':150},150:{'delivered':300}}
        coverage(rows,h)
        for bad in (rows+rows[:1],rows[:-1],rows[:3]+rows[:1]):
            with self.assertRaises(IntegrityError):coverage(bad,h)

    def test_false_unavailability(self):
        rows=self.rows();h={75:{'delivered':150},150:{'delivered':300}}
        for r in rows:r.update(available=False,reason='historical_episode_finished')
        with self.assertRaises(IntegrityError):coverage(rows,h)
        for r in rows:r['available']=r['anchor']==0
        coverage(rows,{75:{'delivered':4},150:{'delivered':30}})

    def test_fabricated_counters(self):
        r={'physical_branch_rollouts':0,'primitive_steps_including_replays':0}
        with self.assertRaises(IntegrityError):counters(r,69,1095)
        r['physical_branch_rollouts']=69
        with self.assertRaises(IntegrityError):counters(r,69,1095)
        r['primitive_steps_including_replays']=1095;counters(r,69,1095)

    def test_wrong_provenance(self):
        r={'program_sha256':'runner','model_state_sha256':MODEL_SHA}
        provenance(r,'runner',MODEL_SHA)
        with self.assertRaises(IntegrityError):provenance(r,'other',MODEL_SHA)
        with self.assertRaises(IntegrityError):provenance(r,'runner','other')


if __name__=='__main__':unittest.main()
