import dataclasses,itertools,unittest
import numpy as np
from experiment import CASES,METHODS,tables,choose,evaluate,draw_training,fit_joint

class MechanismChecks(unittest.TestCase):
    def test_joint_normalization(self):
      for c in CASES:
        for test in (False,True):
          j,obs,_=tables(c,test);self.assertTrue(np.all(j>=0));np.testing.assert_allclose(j.sum((1,3)),1)
          np.testing.assert_allclose(obs.sum(1),1)
    def test_observation_law_does_not_depend_on_future_suffix(self):
      for c in CASES:
        j,obs,_=tables(c)
        np.testing.assert_allclose(j.sum(-1),np.broadcast_to(obs[:,:,None],(3,2,3)))
    def test_hidden_modes_not_in_fit_inputs(self):
      obs,y=draw_training(CASES[0],100,np.random.default_rng(1))
      self.assertEqual(obs.shape,(100,3));self.assertEqual(y.shape,(100,3,3))
      self.assertTrue(set(np.unique(obs))<= {0,1});self.assertTrue(set(np.unique(y))<= {0,1})
    def test_learned_joint_normalized(self):
      o,y=draw_training(CASES[0],100,np.random.default_rng(3));j=fit_joint(o,y)
      np.testing.assert_allclose(j.sum((1,3)),1)
    def test_action_protocol_no_counterfactual_test_read(self):
      # The policy is a prefix plus fixed lookup of the ACTUALLY observed bit.
      for c in CASES:
        j,_,info=tables(c)
        for m in METHODS:
          p,aa=choose(j,info,m);self.assertIn(p,range(3));self.assertEqual(aa.shape,(2,))
          self.assertTrue(np.all((aa>=0)&(aa<3)))
    def test_contingent_rule_equals_exhaustive_standard_bayes(self):
      for c in CASES:
        for test in (False,True):
          j,_,info=tables(c,test)
          exact=max(evaluate((p,np.array(a)),j) for p in range(3) for a in itertools.product(range(3),repeat=2))
          self.assertAlmostEqual(exact,evaluate(choose(j,info,'oracle_contingent'),j),14)
    def test_oracle_not_worse_than_static(self):
      for c in CASES:
        j,_,info=tables(c);self.assertGreaterEqual(evaluate(choose(j,info,'oracle_contingent'),j)+1e-15,
                                                 evaluate(choose(j,info,'commit'),j))
    def test_informative_example_exact(self):
      j,_,info=tables(CASES[0]);self.assertAlmostEqual(evaluate(choose(j,info,'oracle_contingent'),j),.7566,14)
      self.assertAlmostEqual(evaluate(choose(j,info,'commit'),j),.58,14)
      self.assertGreater(info[2],info[1]);self.assertEqual(choose(j,info,'oracle_contingent')[0],1)
    def test_high_cost_probe_declined(self):
      j,_,info=tables(CASES[3]);self.assertEqual(choose(j,info,'oracle_contingent')[0],0)
    def test_no_information_declined(self):
      j,_,info=tables(CASES[2]);self.assertEqual(choose(j,info,'oracle_contingent')[0],0)
    def test_mode_known_prefers_direct(self):
      j,_,info=tables(CASES[1]);self.assertEqual(choose(j,info,'oracle_contingent')[0],0)
    def test_unstable_mode_declined(self):
      j,_,info=tables(CASES[5]);self.assertEqual(choose(j,info,'oracle_contingent')[0],0)
    def test_unannounced_reversal_is_failure_not_guarantee(self):
      j,_,info=tables(CASES[-1],False);truth,_,_=tables(CASES[-1],True)
      value=evaluate(choose(j,info,'active_counterfactual_feedback'),truth)
      self.assertAlmostEqual(value,.2134,14);self.assertLess(value,.58)
    def test_permutation_of_suffixes(self):
      c=CASES[0];j,_,info=tables(c)
      v=evaluate(choose(j,info,'active_counterfactual_feedback'),j)
      for perm in itertools.permutations(range(3)):
        jp=j[:,:,list(perm),:]
        self.assertAlmostEqual(v,evaluate(choose(jp,info,'active_counterfactual_feedback'),jp),14)
    def test_predictor_changes_ranking_after_signal(self):
      j,obs,info=tables(CASES[0]);p,aa=choose(j,info,'active_counterfactual_feedback')
      self.assertEqual(aa.tolist(),[2,1])
      # Same previously available candidates, not a new generated action.
      self.assertNotEqual(aa[0],aa[1])

if __name__=='__main__': unittest.main(verbosity=2)
