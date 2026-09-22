import copy
import inspect
from pathlib import Path
import tempfile
import unittest
import numpy as np
from tree import FrozenPort,Ledger,Node,Tree,cem,construct_tree,identity
from model import JointModel,OrdinaryModel,Preprocessing,Adam,row_weights
from policy import Selector,context,features,execute_episode,real_runtime
from mock import abstract_tree,prototype_dataset,VectorEnv,mock_rollout,collect_source,pack
from checker import check_episode
from bayes import BayesianRegression,exact_artificial_policy
from prototype.experiment import CASES,tables,evaluate


def zero_tail(history,actions,obs,remaining):
    assert remaining==150-obs.clock and obs.clock>=15
    return np.zeros((15,2))


class ACV0Tests(unittest.TestCase):
    def setUp(self):
        self.data,self.tree,self.h,_=prototype_dataset(CASES[0],8,24000,'fit')
        self.pre=Preprocessing.fit(self.data)
        self.model=JointModel(56,24,4,preprocessing=self.pre)

    def test_forward_likelihood_bce_backward_finite(self):
        loss,g,parts=self.model.loss_and_grad(self.data)
        self.assertTrue(np.isfinite(loss));self.assertEqual(len(g),len(self.model.params))
        self.assertTrue(all(np.isfinite(x).all() for x in g));self.assertEqual(parts['actual_response_terms'],24)
        before=[p.copy() for p in self.model.params];Adam(self.model.params).step(g)
        self.assertTrue(any(not np.array_equal(a,b) for a,b in zip(before,self.model.params)))

    def test_exact_gradient_finite_differences_all_parameter_tensors(self):
        loss,g,_=self.model.loss_and_grad(self.data)
        for p,grad in zip(self.model.params,g):
            for index in {0,p.size//2,p.size-1}:
                old=p.flat[index];eps=1e-5;p.flat[index]=old+eps;hi=self.model.loss_and_grad(self.data)[0]
                p.flat[index]=old-eps;lo=self.model.loss_and_grad(self.data)[0];p.flat[index]=old
                self.assertAlmostEqual((hi-lo)/(2*eps),grad.flat[index],delta=2e-5)

    def test_ordinary_gradient_and_same_information(self):
        ordinary=OrdinaryModel(56,24,4,preprocessing=self.pre)
        loss,g,_=ordinary.loss_and_grad(self.data)
        self.assertTrue(np.isfinite(loss));self.assertGreater(ordinary.parameter_count,self.model.parameter_count)
        for p,grad in zip(ordinary.params,g):
            old=p.flat[0];p.flat[0]=old+1e-5;hi=ordinary.loss_and_grad(self.data)[0]
            p.flat[0]=old-1e-5;lo=ordinary.loss_and_grad(self.data)[0];p.flat[0]=old
            self.assertAlmostEqual((hi-lo)/2e-5,grad.flat[0],delta=2e-5)
        _,cache=ordinary.forward(self.data['x'],self.data['a'],self.data['r'])
        self.assertEqual(cache[0].shape[-1],56+24+8)
        # Its actual observation is exactly prediction + response, no mode label.
        expected=(self.data['x'][:,-4:]+self.data['r']-self.pre.xmean[-4:])/self.pre.xstd[-4:]
        np.testing.assert_allclose(cache[0].reshape(24,3,-1)[:,:,-8:-4],np.repeat(expected[:,None,:],3,1))

    def test_posterior_normalization_opposite_ranking(self):
        m=JointModel(1,1,1)
        for p in m.params:p[:]=0
        m.response.params[1][4:8]=[-2,2,-2,2]
        # Opposite candidate action signs create opposite component outcomes.
        m.candidate.params[0][-1,0]=1
        m.candidate.params[2][0]=[3,-3,3,-3]
        x=np.zeros((1,1));a=np.array([[[-1.],[1.]]])
        left=m.forward(x,a,np.array([[-2.]]))[0];right=m.forward(x,a,np.array([[2.]]))[0]
        self.assertAlmostEqual(left['w'].sum(),1);self.assertAlmostEqual(right['w'].sum(),1)
        self.assertNotEqual(int(left['q'].argmax()),int(right['q'].argmax()))

    def test_checkpoint_preprocessing_roundtrip(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            path=Path(temp)/'roundtrip.npz';self.model.save(path);restored=JointModel.load(path)
            a=self.model.forward(self.data['x'],self.data['a'],self.data['r'])[0]
            b=restored.forward(self.data['x'],self.data['a'],self.data['r'])[0]
            for key in a:np.testing.assert_array_equal(a[key],b[key])
            self.assertEqual(self.model.pre.fit_ids,restored.pre.fit_ids)

    def test_fit_only_preprocessing_and_source_reduction(self):
        bad=copy.deepcopy(self.data);bad['roles'][:]='test'
        with self.assertRaises(ValueError):Preprocessing.fit(bad)
        weight=row_weights(self.data)
        for source in np.unique(self.data['source_ids']):self.assertAlmostEqual(weight[self.data['source_ids']==source].sum(),1/8)
        self.assertEqual(self.model.loss_and_grad(self.data)[2]['actual_response_terms'],24)

    def test_suffix_permutation_equivariance_and_independent_response(self):
        x,a,r=self.data['x'],self.data['a'],self.data['r'];o=self.model.forward(x,a,r)[0]
        perm=[2,0,1];q=self.model.forward(x,a[:,perm],r)[0]
        np.testing.assert_array_equal(q['q'],o['q'][:,perm])
        for key in ('pi','mu','var','terminal','w'):np.testing.assert_array_equal(o[key],q[key])
        other=self.model.forward(x,a[:,:1]*73,r)[0]
        for key in ('pi','mu','var','terminal','w'):np.testing.assert_array_equal(o[key],other[key])

    def test_tree_exact_baseline_budget_and_duplicates(self):
        ledger=Ledger();port=FrozenPort(np.zeros(4),np.ones(4),mock_rollout,ledger)
        baseline=cem(port,np.random.default_rng(94001),population=8,elites=2,rounds=2)
        tree=construct_tree(port,baseline,population=8,elites=2,rounds=2)
        tree.validate();np.testing.assert_array_equal(tree.baseline_plan,baseline.baseline)
        self.assertEqual(ledger.sequences,5*16+16);self.assertEqual(ledger.latent_transitions,3*96)
        from tree import Solve
        dup=Solve(np.zeros((15,2)),np.zeros((8,15,2)),np.zeros(8))
        sparse=construct_tree(port,dup,population=8,elites=2,rounds=1)
        self.assertEqual(len(sparse.nodes),1);self.assertGreater(sparse.duplicates_skipped,0)

    def test_no_response_ablation_same_selection_and_cost(self):
        selector=Selector(self.model);a=Ledger();b=Ledger()
        active=selector.select(self.tree,self.h,a,'active');ablated=selector.select(self.tree,self.h,b,'no_update')
        self.assertEqual(active.prefix,ablated.prefix);self.assertEqual(active.values,ablated.values)
        self.assertEqual(a.__dict__,b.__dict__);self.assertIsNotNone(ablated.suffix)
        chosen=selector.after(ablated,self.tree,self.h,np.full(4,np.nan),b)
        self.assertEqual(chosen,ablated.suffix)  # actual response not even inspected

    def test_no_deployment_optimization_or_branch_query(self):
        before=[p.copy() for p in self.model.params];selector=Selector(self.model)
        result=execute_episode(VectorEnv(),self.tree,selector,np.zeros(4),zero_tail,Ledger())
        check_episode(result,self.tree)
        for a,b in zip(before,self.model.params):np.testing.assert_array_equal(a,b)
        self.assertNotIn('env',inspect.signature(Selector.select).parameters)
        self.assertNotIn('env',inspect.signature(Selector.after).parameters)
        with self.assertRaises(PermissionError):real_runtime()

    def test_clock_5_10_135_fresh_buffers(self):
        selector=Selector(self.model);env=VectorEnv();ledger=Ledger();tail_clocks=[]
        def tail(h,a,o,remaining):tail_clocks.append(o.clock);return zero_tail(h,a,o,remaining)
        first=execute_episode(env,self.tree,selector,np.zeros(4),tail,ledger,'passive')
        check_episode(first,self.tree);self.assertEqual(first['steps'],150);self.assertEqual(tail_clocks,list(range(15,150,15)))
        self.assertEqual(ledger.physical_steps,150)
        second=execute_episode(VectorEnv(),self.tree,selector,np.zeros(4),zero_tail,Ledger(),'passive')
        self.assertEqual(first['trace'],second['trace']);self.assertEqual(second['action_buffer_size'],150)

    def test_early_success_truncation_no_post_terminal_work(self):
        for step in (1,3,5,6,8,15,16,149):
            for success in (True,False):
                env=VectorEnv(success_at=step if success else None,truncate_at=None if success else step)
                ledger=Ledger();result=execute_episode(env,self.tree,Selector(self.model),np.zeros(4),zero_tail,ledger,'passive')
                check_episode(result,self.tree);self.assertEqual(env.calls,step);self.assertEqual(result['success'],success)
                if step<=5:self.assertIsNone(result['selected_suffix']);self.assertEqual(ledger.outcome_queries,1152)

    def test_checker_rejects_wrong_association_and_fictitious_endpoint(self):
        result=execute_episode(VectorEnv(success_at=8),self.tree,Selector(self.model),np.zeros(4),zero_tail,Ledger(),'passive')
        bad=copy.deepcopy(result);bad['trace'][5]['action'][0]+=1
        with self.assertRaises(AssertionError):check_episode(bad,self.tree)
        bad=copy.deepcopy(result);bad['success']=False
        with self.assertRaises(AssertionError):check_episode(bad,self.tree)

    def test_mock_collector_common_history_and_terminal_training(self):
        rows,receipt=collect_source('mock-fit','fit',self.tree,VectorEnv,np.zeros(4),zero_tail)
        self.assertEqual(receipt['physical_steps'],9*150);self.assertEqual(receipt['canonical_response_observations'],3)
        for p in range(3):self.assertEqual(len({r['common_history_sha256'] for r in receipt['branches'] if r['prefix']==p}),1)
        early,er=collect_source('terminal-fit','fit',self.tree,lambda:VectorEnv(success_at=3),np.zeros(4),zero_tail)
        self.assertEqual(er['physical_steps'],9);self.assertEqual(er['constructed_episodes'],3)
        packed=pack(rows+early);model=JointModel(56,24,4,preprocessing=Preprocessing.fit(packed))
        loss,g,parts=model.loss_and_grad(packed);self.assertTrue(np.isfinite(loss));self.assertEqual(parts['actual_response_terms'],3)

    def test_terminal_failure_value_and_survival_not_conditioning_only(self):
        # Set failure almost certain; unconditional value must be tiny despite q~.5.
        for p in self.model.params:p[:]=0
        self.model.response.params[1][-3:]=[-20,20,-20]
        decision=Selector(self.model).select(self.tree,self.h,Ledger())
        self.assertLess(max(decision.values),1e-12)

    def test_nonfinite_limits_and_no_hidden_deployment_fields(self):
        bad=self.data['x'].copy();bad[0,0]=np.nan
        with self.assertRaises(ValueError):self.model.forward(bad,self.data['a'])
        from policy import Observation
        self.assertEqual(set(Observation.__dataclass_fields__),{'latent','clock','success','terminated','truncated'})
        with self.assertRaises(RuntimeError):Selector(self.model).select(self.tree,self.h,Ledger(integration_responses=512))

    def test_bayesian_regression_and_exact_oracle_negative_cases(self):
        ordinary=OrdinaryModel(56,24,4,preprocessing=self.pre);bayes=BayesianRegression(ordinary).fit(self.data)
        q=bayes.predict(self.data['x'],self.data['a'],self.data['r']);self.assertTrue(np.all((0<=q)&(q<=1)))
        for case in CASES:
            law,_,_=tables(case,True);policy=exact_artificial_policy(case)
            self.assertGreaterEqual(evaluate(policy,law),.58-1e-12)


if __name__=='__main__':unittest.main(verbosity=2)
