"""Small artificial interface/unit tests only; not research simulations."""
import base
import sys, unittest
import numpy as np
from model import JointModel, OrdinaryModel
from tree import Ledger, Node, Tree, identity
from policy import Selector, context, execute_episode
from mock import abstract_tree, VectorEnv
from committed_feedback import CommittedFeedbackSelector, MODE, evaluate_supplied
from decomposition import prefix_values

class TestMechanism(unittest.TestCase):
    def setUp(self):
        self.tree=abstract_tree(); self.h=context([np.zeros(4)],[],np.zeros(4),0)
        self.joint=JointModel(56,24,4); self.ordinary=OrdinaryModel(56,24,4)
        self.new=CommittedFeedbackSelector(self.joint,self.ordinary)
    def test_original_hashes(self): base.authenticate_code()
    def test_prefix_is_exact_static_and_accounting_equal(self):
        a,b=Ledger(),Ledger()
        s=Selector(self.joint).select(self.tree,self.h,a,'static')
        d=self.new.select(self.tree,self.h,b)
        self.assertEqual(d.prefix,s.prefix); self.assertIsNone(d.suffix)
        self.assertEqual(vars(a),vars(b)); self.assertEqual(d.values,s.values)
    def test_existing_modes_bit_identical(self):
        old=Selector(self.joint,self.ordinary)
        for mode in ('static','active','no_update','passive','ordinary'):
            a,b=Ledger(),Ledger(); x=old.select(self.tree,self.h,a,mode); y=self.new.select(self.tree,self.h,b,mode)
            self.assertEqual(x,y); self.assertEqual(old.after(x,self.tree,self.h,np.ones(4),a),self.new.after(y,self.tree,self.h,np.ones(4),b))
            self.assertEqual(vars(a),vars(b))
    def test_feedback_not_committed_suffix(self):
        d=self.new.select(self.tree,self.h,Ledger())
        old=self.new.conditional
        self.new.conditional=lambda x,a,r,mode,ledger:np.array([[0.,0.,1.]])
        self.assertEqual(self.new.after(d,self.tree,self.h,np.ones(4),Ledger()),2)
        self.new.conditional=old
    def test_baseline_tie_still_updates(self):
        for p in self.joint.params: p[:]=0
        d=self.new.select(self.tree,self.h,Ledger()); self.assertEqual(d.prefix,0); self.assertIsNone(d.suffix)
        self.assertFalse(d.direct_baseline)
    def test_terminal_prefix_no_suffix_query(self):
        env=VectorEnv(success_at=3); led=Ledger()
        self.new.after=lambda *args: (_ for _ in ()).throw(AssertionError('post-terminal query'))
        r=execute_episode(env,self.tree,self.new,np.zeros(4),lambda *x:np.zeros((15,2)),led,MODE)
        self.assertEqual(r['steps'],3); self.assertIsNone(r['selected_suffix'])
    def test_suffix_locality_and_no_tree_mutation(self):
        before=[identity(n.prefix) for n in self.tree.nodes]
        d=self.new.select(self.tree,self.h,Ledger())
        i=self.new.after(d,self.tree,self.h,np.ones(4),Ledger())
        self.assertIn(i,range(len(self.tree.nodes[d.prefix].suffixes)))
        self.assertEqual(before,[identity(n.prefix) for n in self.tree.nodes])
    def test_decomposition_exact_original_score(self):
        rows=prefix_values(self.joint,self.tree,self.h)
        d=Selector(self.joint).select(self.tree,self.h,Ledger(),'active')
        for r,v in zip(rows,d.values):
            self.assertAlmostEqual(r['active_value'],v,places=13)
            self.assertAlmostEqual(r['active_value'],r['terminal_success']+r['committed_active_value']+r['anticipated_feedback_increment'],places=13)
            self.assertGreaterEqual(r['same_draw_feedback_increment'],-1e-15)
    def test_terminal_success_not_counted_twice(self):
        rows=prefix_values(self.joint,self.tree,self.h)
        for r in rows: self.assertAlmostEqual(r['committed_total'],r['terminal_success']+r['committed_active_value'])
    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError): self.new.select(self.tree,self.h,Ledger(),'invented')
    def test_actual_response_passed_unchanged(self):
        d=self.new.select(self.tree,self.h,Ledger()); seen=[]
        self.new.conditional=lambda x,a,r,mode,ledger:(seen.append(r.copy()) or np.zeros((1,a.shape[1])))
        actual=np.array([.1,.2,.3,.4]); self.new.after(d,self.tree,self.h,actual,Ledger())
        np.testing.assert_array_equal(seen[0][0],actual-self.tree.nodes[d.prefix].predicted_prefix)
    def test_real_executor_adapter_artificial_interface(self):
        sys.path.insert(0,str(base.OLD/'bindings-r1'))
        from artificial import FakeTorch, FakeLeWM, factory
        from bridge import LeWMBridge
        backend=LeWMBridge(FakeLeWM(),FakeTorch,'artificial-cpu'); owned=[]
        j=JointModel(996,212,192); selector=CommittedFeedbackSelector(j)
        a,m=evaluate_supplied(factory(backend,success_at=7,owned=owned),backend.rollout,999,selector,
                              settings={'population':6,'elites':2,'rounds':1})
        self.assertEqual(m['control'],MODE); self.assertEqual(m['branches'][0]['steps'],7)
        self.assertTrue(all(w.closed for w in owned)); self.assertIn('b0/plan1',a)
    def test_no_research_import(self):
        self.assertNotIn('torch',sys.modules); self.assertNotIn('stable_worldmodel',sys.modules)

if __name__=='__main__': unittest.main(verbosity=2)
