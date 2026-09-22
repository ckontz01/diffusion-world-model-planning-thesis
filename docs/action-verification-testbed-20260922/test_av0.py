import itertools
import math
import unittest
from controls import *
from pc_racp import BinaryPCRACP, g
from planning import *


class Tests(unittest.TestCase):
    def test_acid_equation(self):
        self.assertEqual(inverse_consistency(((1.,2.),(3.,4.)),((0.,0.),(0.,0.))),15.)
        s,w=acid_cost((1.,3.,5.),(2.,4.,6.),.5)
        self.assertEqual(w,.5); self.assertEqual(s,(2.,5.,8.))

    def test_acid_constant_residual(self):
        s,w=acid_cost((1.,2.),(0.,0.))
        self.assertEqual(s,(1.,2.));self.assertTrue(math.isfinite(w))

    def test_acid_location(self):
        calls=[]
        def cost(o,bank):
            calls.append(bank)
            return tuple((a[0]-2)**2 for a in bank),tuple((a[0]+2)**2 for a in bank)
        args=dict(seed=4,dimensions=2,population=20,elites=4,iterations=3)
        b=cem(0,cost,**args); self.assertEqual(len(calls),3)
        a=cem(0,cost,acid=True,lam=1.,**args)
        self.assertEqual(len(calls),6);self.assertEqual(calls[0],calls[3])
        self.assertNotEqual(calls[1],calls[4]);self.assertNotEqual(b.baseline,a.baseline)

    def test_shortlist_mean_and_dedup(self):
        s=Solve((.25,),((.25,),(0.,),(0.,),(1.,)),(0.,1.,1.,2.),(),4)
        b=shortlist(s)
        self.assertEqual(b.actions[0],(.25,));self.assertEqual(b.actions[1:3],((0.,),(1.,)))
        self.assertEqual(b.duplicate_slots,5);self.assertEqual(len(b.actions),8)
        self.assertEqual(action_id((-0.,)),action_id((0.,)))

    def test_no_future_or_replacement_callback(self):
        calls=[]
        def plan(obs):
            calls.append(obs);return Solve((obs,),tuple((float(i),) for i in range(10)),tuple(range(10)),(),10)
        tr=checked_path(0,plan,lambda o,b:(.5,)*8,point,
                        lambda o,a:(o+1,False,False),3)
        self.assertEqual(calls,[0,1,2]);self.assertEqual([r[2] for r in tr],[0]*3)

    def test_native_actual_observations(self):
        def plan(o):return Solve((o+1,),(),(),(),0)
        tr=native_path(0,plan,lambda o,a:(o+a[0],False,False),3)
        self.assertEqual([r[0] for r in tr],[0,1,3])

    def test_success_in_chunk_counts(self):
        self.assertTrue(full_budget_success([True],[False]));self.assertFalse(full_budget_success([],[]))

    def test_ties_preserve_baseline(self):
        self.assertEqual(point((.5,)*8),0);self.assertEqual(threshold_rule((.5,)*8,0),0)

    def test_conformal_rank(self):
        self.assertEqual(split_quantile(list(range(19)),.05),18)
        self.assertTrue(math.isinf(split_quantile(list(range(18)),.05)))
        self.assertTrue(math.isinf(split_quantile([],.05)))

    def test_simultaneous_algebra(self):
        p=(.4,.7,.2,.9,.3,.5,.6,.1)
        for y in itertools.product((0,1),repeat=8):
            q=max((p[i]-p[0])-(y[i]-y[0]) for i in range(1,8))
            checker=Simultaneous(q)
            self.assertTrue(all(y[i]-y[0] >= b-1e-12 for i,b in enumerate(checker.bounds(p))))
            self.assertGreaterEqual(y[checker.choose(p)],y[0])

    def test_ltt_binomial_exact(self):
        self.assertAlmostEqual(binomial_cdf(0,90,.05),.95**90)
        self.assertAlmostEqual(binomial_cdf(2,4,.5),11/16)
        p=(.2,.8)+(.1,)*6
        good=[(p,(0,1,0,0,0,0,0,0))]*100
        l=LearnThenTest.calibrate(good,(0,.05,.1,.2,.4))
        self.assertEqual(l.choose(p),1);self.assertEqual(len(l.accepted),5)

    def test_ltt_no_override_undefined(self):
        l=LearnThenTest.calibrate([((.5,)*8,(1,)*8)]*200,(0,.1))
        self.assertFalse(l.accepted);self.assertEqual(l.choose((.5,)*8),0)
        m=metrics([dict(outcomes=(1,)*8,truth=(.5,)*8)],[0])
        self.assertIsNone(m['conditional_harm'])

    def test_ltt_harm_fails(self):
        p=(.2,.8)+(.1,)*6
        l=LearnThenTest.calibrate([(p,(1,0,0,0,0,0,0,0))]*100,(0,.1))
        self.assertFalse(l.accepted)

    def test_pc_g_exact_binary_envelope(self):
        p=(.4,.8)+(.2,)*6
        self.assertEqual(g(p,0),(.8,1.,1))
        self.assertEqual(g(p,6),(1.,0.,0))
        for beta in (0.,1.,4.,6.):
            t,theta,_=g(p,beta)
            self.assertAlmostEqual(theta+beta*t,max(1+beta*.8,beta))

    def test_pc_policy_separation_and_degeneracy(self):
        p=(.1,.99)+(.1,)*6
        pc=BinaryPCRACP([p]*100)
        self.assertEqual(pc.action(p),1)
        pc.calibrate([(p,(1,0,0,0,0,0,0,0),1,(.125,)*8)]*100)
        result=pc.predict(p)
        self.assertEqual(result['action'],1) # calibration NEVER reselects baseline
        self.assertEqual(result['sets'][1],(0,1));self.assertEqual(result['certificate'],0)

    def test_pc_uniform_known_propensity(self):
        p=(.1,.99)+(.1,)*6
        rec=[(p,(0,1,0,0,0,0,0,0),i%8,(.125,)*8) for i in range(160)]
        pc=BinaryPCRACP([p]*10).calibrate(rec)
        self.assertEqual(pc.used,20);self.assertEqual(pc.predict(p)['sets'][1],(1,))
        full=BinaryPCRACP([p]*10).calibrate(rec,complete_branch=True)
        self.assertEqual(full.used,160)

    def test_pc_insufficient_matches_not_fake_certificate(self):
        p=(.1,.99)+(.1,)*6
        pc=BinaryPCRACP([p]*10).calibrate([])
        self.assertEqual(pc.predict(p)['sets'][1],(0,1))
        self.assertEqual(pc.predict(p,full=False)['sets'][1],(0,1))

    def test_pc_equation42_and45(self):
        p=(.1,.99)+(.1,)*6
        for n in (0,1,18,19,20,30):
            for fail in (0,n//2,n):
                rec=[(p,(0,int(i>=fail),0,0,0,0,0,0),1,(.125,)*8) for i in range(n)]
                pc=BinaryPCRACP([p]*20).calibrate(rec)
                expected=(1,) if (n-fail)/(n+1) >= .95-1e-12 else (0,1)
                self.assertEqual(pc.predict(p,full=False)['sets'][1],expected)
                self.assertEqual(pc.predict(p)['sets'][1],expected)

    def test_pc_rejects_fake_propensity(self):
        p=(.1,.99)+(.1,)*6
        with self.assertRaises(ValueError):
            BinaryPCRACP([p]).calibrate([(p,(1,)*8,1,(0.,1.)+(0.,)*6)])

    def test_point_fitting_only(self):
        fit=[dict(id=str(i),context=1,outcomes=(0,1,0,0,0,0,0,0),logged_action=1) for i in range(10)]
        model=TablePredictor(fit)
        self.assertEqual(point(model.predict(1)),1);self.assertEqual(point(model.predict(99)),0)
        with self.assertRaises(ValueError):TablePredictor(fit+fit[:1])

    def test_aliases_not_overrides(self):
        s=Solve((0.,),((0.,),),(0.,),(),1)
        tr=checked_path(0,lambda o:s,lambda o,b:(.1,)+(.9,)*7,point,
                        lambda o,a:(o,False,True),1)
        self.assertEqual(tr[0][2],0)

    def test_latent_port_goal_and_residual(self):
        def rollout(z,actions):
            out=[z]
            for a in actions:out.append((out[-1][0]+a[0],))
            return out
        port=FrozenLatentCost(rollout,lambda z,n,t:(n[0]-z[0],),block_width=1)
        goal,residual=port(((0.,),(3.,)),((1.,2.),(2.,2.)))
        self.assertEqual(goal,(0.,1.));self.assertEqual(residual,(0.,0.))
        with self.assertRaises(ValueError):
            FrozenLatentCost(lambda z,a:[(9.,)]*3,block_width=1)(((0.,),(3.,)),((1.,2.),))


if __name__=='__main__':unittest.main(verbosity=2)
