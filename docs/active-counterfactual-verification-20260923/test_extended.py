import copy
import unittest
import numpy as np
from checker import check_native_pusht,check_reference
from model import JointModel,OrdinaryModel
from mock import abstract_tree,collect_source,VectorEnv,mock_rollout,pack
from policy import Selector,execute_episode
from tree import Ledger,FrozenPort,cem,construct_tree
from runtime_adapter import BaselinePlanner,execute_reference,launch_real_pilot
from test_acv0 import zero_tail


class ExtendedTests(unittest.TestCase):
    def test_all_terminal_schema_and_zero_suffix_response_gradients(self):
        rows,r=collect_source('terminal','fit',abstract_tree(),lambda:VectorEnv(truncate_at=3),np.zeros(4),zero_tail)
        data=pack(rows);m=JointModel(56,24,4);loss,g,p=m.loss_and_grad(data)
        self.assertEqual(p['actual_response_terms'],0);self.assertEqual(p['outcome_bce'],0)
        self.assertEqual(p['response_nll'],0);self.assertTrue(np.isfinite(loss))
        self.assertTrue(all(np.all(x==0) for x in g[-4:]))
        self.assertEqual(r['constructed_episodes'],3)

    def test_common_history_mismatch_rejected(self):
        counter=[0]
        def factory():counter[0]+=1;return VectorEnv(seed=counter[0])
        with self.assertRaisesRegex(ValueError,'common-prefix'):
            collect_source('bad','fit',abstract_tree(),factory,np.zeros(4),zero_tail)

    def test_duplicate_training_suffix_rejected(self):
        rows,_=collect_source('dup','fit',abstract_tree(),VectorEnv,np.zeros(4),zero_tail)
        rows[0]['a'][1]=rows[0]['a'][0]
        with self.assertRaisesRegex(ValueError,'Duplicate'):pack(rows)

    def test_early_replan_full_search_and_clock(self):
        for early,clocks in [(False,list(range(0,150,15))),(True,[0]+list(range(5,150,15)))]:
            ledger=Ledger();p=BaselinePlanner(np.ones(4),mock_rollout,ledger)
            r=execute_reference(VectorEnv(),p,ledger,early);check_reference(r)
            self.assertEqual(p.calls,clocks);self.assertEqual(ledger.sequences,9000*len(clocks))
            self.assertEqual(ledger.cem_solves,len(clocks))
            for step in (3,5,6,15,20,149):
                ll=Ledger();pp=BaselinePlanner(np.ones(4),mock_rollout,ll,population=8,elites=2,rounds=1)
                rr=execute_reference(VectorEnv(success_at=step),pp,ll,early);check_reference(rr)
                self.assertEqual(rr['steps'],step)

    def test_full_tree_production_budget(self):
        ledger=Ledger();port=FrozenPort(np.zeros(4),np.ones(4),mock_rollout,ledger)
        baseline=cem(port,np.random.default_rng(94041));tree=construct_tree(port,baseline)
        self.assertEqual(len(tree.nodes),4);self.assertEqual(ledger.sequences,45016)
        self.assertEqual(ledger.latent_transitions,135048);self.assertEqual(ledger.rollout_calls,151)
        self.assertEqual(ledger.cem_solves,5);self.assertEqual(ledger.prefix_planning_calls,4)

    def test_all_learned_calls_counted(self):
        from policy import context
        tree=abstract_tree();ledger=Ledger();selector=Selector(JointModel(56,24,4))
        h=context([np.zeros(4)],[],np.zeros(4),0)
        d=selector.select(tree,h,ledger,'passive')
        self.assertEqual(ledger.learned_module_forward_calls,6)
        self.assertEqual(ledger.prior_candidate_predictions,9)
        self.assertEqual(ledger.outcome_queries,1152)
        selector.after(d,tree,h,np.zeros(4),ledger)
        self.assertEqual(ledger.learned_module_forward_calls,7)
        self.assertEqual(ledger.outcome_queries,1155)

    def test_independent_native_geometry_and_budget_flags(self):
        goal=np.zeros(7);s=np.ones((150,7))*100;s[:,4]=0
        result=check_native_pusht(s,goal,[False]*150,[False]*150,[False]*150,np.zeros((150,2)))
        self.assertFalse(result['success'])
        s=np.zeros((1,7));s[0,4]=2*np.pi-.01
        self.assertTrue(check_native_pusht(s,goal,[True],[True],[False],np.zeros((1,2)))['success'])
        with self.assertRaises(AssertionError):check_native_pusht(s,goal,[False],[False],[False],np.zeros((1,2)))
        with self.assertRaises(AssertionError):check_native_pusht(np.repeat(s,2,0),goal,[True,True],[True,True],[False,False],np.zeros((2,2)))

    def test_real_disabled_and_existing_ordinary_checkpoint(self):
        from pathlib import Path
        d=Path(__file__).parent/'neural-run-v1/informative_contact'
        j=JointModel.load(d/'joint.npz');o=OrdinaryModel.load(d/'ordinary.npz',j)
        self.assertEqual(o.parameter_count,9921)
        with self.assertRaises(PermissionError):launch_real_pilot()


if __name__=='__main__':unittest.main(verbosity=2)
