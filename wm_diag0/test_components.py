"""Focused artificial tests. No historical outcomes, checkpoints or simulator."""
import inspect
from pathlib import Path
import tempfile
import unittest
import numpy as np
from wm_diag0.core import *
from wm_diag0.adapters import LeWMAdapter, DinoWMAdapter
from wm_diag0.readout import fit_artificial, check_roles, task_margin, realized_quality
from wm_diag0.branches import SourceHistory, run_branch
from wm_diag0.accept import check_branch, check_draws
from wm_diag0.saved import save_artificial, load_artificial, sha
from wm_diag0.analysis import estimate


def contract(backbone='lewm',shape=(6,)):
    return FeatureContract(backbone,'1'*64,'2'*64,shape,(5,10,15,20,25),1,'terminal_sum' if backbone=='lewm' else 'terminal_mse')


def bank():
    actions = np.arange(40*25*2,dtype=np.float32).reshape(40,25,2)/10000
    return capture_bank(np.zeros((25,2),np.float32),actions,np.arange(40,dtype=float))


def ridge(c=None):
    c = c or contract()
    rng = np.random.default_rng(20261004)
    x = rng.normal(size=(128,*c.feature_shape))
    y = rng.normal(size=(128,6))
    return fit_artificial(x,y,['fit']*128,(['fit'],['validation'],['diagnostic']),c,'pusht',domain='artificial')


class FakeWorld:
    def __init__(self,stop=100,success_at=100,truncated=False):
        self.t=0;self.stop=stop;self.success_at=success_at;self.truncated=truncated;self.closed=False
    def observation(self):return np.array([self.t],dtype=np.float32)
    def reset(self):return self.observation(),self.success_at==0,self.stop==0,False
    def step(self,action):
        if self.t >= self.stop or self.t >= self.success_at: raise AssertionError('Postterminal physics')
        self.t += 1
        return self.observation(),self.t>=self.success_at,self.t>=self.stop and not self.truncated,self.t>=self.stop and self.truncated
    def close(self):self.closed=True


def source(elapsed=0):
    return SourceHistory('parent','fresh-construction',np.zeros((elapsed,2),np.float32),
                         tuple(array_id(np.array([i],np.float32)) for i in range(elapsed+1)),elapsed)


def tail(obs,elapsed,remaining,draw):
    assert remaining == 50-elapsed
    return np.array([draw,0],np.float32)


class ComponentTests(unittest.TestCase):
    def test_native_mean_retained_not_argmin(self):
        b=bank();self.assertEqual(b.native_index,0);self.assertEqual(b.candidates[0].origin,'native_return')
        self.assertEqual(array_id(b.candidates[0].actions),array_id(np.zeros((25,2),np.float32)))
        self.assertEqual(len(b.candidates),16);self.assertIsNone(b.candidates[0].predicted_cost)
    def test_duplicates_and_tie_order(self):
        native=np.ones((25,2),np.float32)
        a=np.stack([native,np.zeros_like(native),np.zeros_like(native),2*native])
        b=capture_bank(native,a,[0,0,0,0]);self.assertEqual(len(b.candidates),3)
        self.assertEqual([c.origin for c in b.candidates],['native_return','trace:1','trace:3'])
    def test_no_outcomes_in_bank_or_selector(self):
        self.assertNotIn('outcomes',inspect.signature(capture_bank).parameters)
        self.assertNotIn('outcomes',inspect.signature(select_four).parameters)
    def test_matrix_same_actions_and_s1(self):
        b=bank();c=contract();r=ridge(c);rng=np.random.default_rng(12)
        x=rng.normal(size=(16,5,6));g=np.zeros(6)
        p=Features(x,c,b.identity,'diagnostic','predicted');o=Features(x.copy(),c,b.identity,'diagnostic','realized')
        s=select_four(b,p,o,g,native_terminal_mse,r)
        self.assertEqual(s.choices[0],s.choices[2]);self.assertEqual(s.choices[1],s.choices[3])
        self.assertEqual(s.cost_ids[1],s.cost_ids[3]);self.assertEqual(s.s1_id,r.identity)
        self.assertTrue(all(not x.actions.flags.writeable for x in b.candidates))
    def test_dino_tokens_preserved(self):
        c=contract('dinowm_noprop',(3,6));a=DinoWMAdapter(c,lambda x:np.zeros((3,6)),
            lambda root,actions,pos:np.zeros((5,3,6)),domain='artificial')
        f=a.predict(np.zeros((1,2,2,3)),bank(),'diagnostic');self.assertEqual(f.values.shape,(16,5,3,6))
        with self.assertRaises(ValueError):DinoWMAdapter(contract(),None,None,domain='artificial')
    def test_native_cost_reduction_not_silently_changed(self):
        b=bank();c=contract();p=Features(np.ones((16,5,6)),c,b.identity,'diagnostic','predicted')
        self.assertEqual(native_terminal_score(p,np.zeros(6))[0],6)
        d=contract('dinowm_noprop',(3,6));q=Features(np.ones((16,5,3,6)),d,b.identity,'diagnostic','predicted')
        self.assertEqual(native_terminal_score(q,np.zeros((3,6)))[0],1)
    def test_wrong_backbone_goal_and_preprocessing(self):
        b=bank();c=contract();p=Features(np.zeros((16,5,6)),c,b.identity,'diagnostic','predicted')
        wrong=FeatureContract('lewm','1'*64,'3'*64,(6,),c.positions,1,'terminal_mse')
        o=Features(p.values,wrong,b.identity,'diagnostic','realized')
        with self.assertRaises(ValueError):select_four(b,p,o,np.zeros(6),native_terminal_mse,ridge())
        with self.assertRaises(ValueError):native_terminal_mse(p,np.zeros(5))
    def test_temporal_alignment_absorbs_not_physics(self):
        x=np.arange(8)[:,None]
        self.assertEqual(aligned_realized(x,(5,10,15),7).ravel().tolist(),[5,7,7])
        with self.assertRaises(ValueError):aligned_realized(x,(5,10),None)
        self.assertNotIn('terminal_step',inspect.signature(select_four).parameters)
    def test_roles_whole_parent(self):
        with self.assertRaises(ValueError):check_roles(['a'],['b'],['a'])
        with self.assertRaises(ValueError):check_roles(['a','a'],['b'],['c'])
    def test_real_fitting_and_backend_disabled(self):
        with self.assertRaises(PermissionError):fit_artificial(None,None,[],([],[],[]),None,'pusht',domain='research')
        with self.assertRaises(PermissionError):ResearchBackend('checkpoint.pt')
        with self.assertRaises(PermissionError):run_branch(None,None,None,None,50,1,domain='research')
        with self.assertRaises(PermissionError):LeWMAdapter(contract(),None,None,domain='research')
    def test_ridge_fixed_quality_no_refit(self):
        r=ridge();before=r.identity
        q=realized_quality(r,np.zeros((3,6)),np.zeros((3,6)))
        self.assertEqual(len(q['coordinate_rmse']),6);self.assertEqual(r.identity,before);self.assertEqual(r.alpha,1)
    def test_joint_and_periodic_geometry(self):
        g=np.array([0,0,0,0,np.cos(-np.pi+.01),np.sin(-np.pi+.01)])
        p=np.array([[0,0,0,0,np.cos(np.pi-.01),np.sin(np.pi-.01)]])
        self.assertAlmostEqual(task_margin('pusht',p,g)[0],.02/(np.pi/9))
        p[0,0]=100;self.assertEqual(task_margin('pusht',p,g)[0],5.)
        p[0,:4]=[15,0,15,0];self.assertGreater(task_margin('pusht',p,g)[0],1.)
        rg=np.array([1,0,1,0]);rp=np.array([[1,0,0,1]])
        self.assertGreater(task_margin('reacher',rp,rg)[0],30)
    def test_terminal_during_chunk_no_tail(self):
        w=FakeWorld(stop=7,success_at=7);s=source();candidate=bank().candidates[0]
        r=run_branch(lambda *_:w,s,candidate,lambda *_:self.fail('tail after success'),50,1,domain='artificial')
        self.assertEqual(r['elapsed'],7);self.assertEqual(r['prefix_steps'],7);self.assertTrue(w.closed)
        self.assertTrue(check_branch(r,candidate,s,lambda x:x[0]>=7)['accepted'])
    def test_initial_success_absorbed(self):
        r=run_branch(lambda *_:FakeWorld(success_at=0),source(),bank().candidates[0],tail,50,1,domain='artificial')
        self.assertEqual(len(r['actions']),0);self.assertEqual(r['reason'],'success')
    def test_absolute_budget_and_separate_tail_draws(self):
        s=source(10);c=bank().candidates[0]
        rr=[run_branch(lambda *_:FakeWorld(),s,c,tail,50,d,domain='artificial') for d in (1,2)]
        self.assertEqual(len(rr[0]['actions']),40);self.assertEqual(rr[0]['elapsed'],50)
        self.assertTrue(check_draws(rr,True));self.assertNotEqual(rr[0]['tail_id'],rr[1]['tail_id'])
        for r in rr:self.assertTrue(check_branch(r,c,s,lambda _:False)['accepted'])
    def test_truncation_and_failure_not_success(self):
        for truncated in (False,True):
            r=run_branch(lambda *_:FakeWorld(stop=3,truncated=truncated),source(),bank().candidates[0],tail,50,1,domain='artificial')
            self.assertFalse(r['success']);self.assertEqual(r['reason'],'truncated' if truncated else 'terminal_failure')
            self.assertTrue(check_branch(r,bank().candidates[0],source(),lambda _:False)['accepted'])
    def test_replay_is_charged_separately_from_original_budget(self):
        s=source(10);s=SourceHistory(s.parent,s.construction_id,s.replay_actions,s.observation_ids,0)
        r=run_branch(lambda *_:FakeWorld(),s,bank().candidates[0],tail,50,1,domain='artificial')
        self.assertEqual(r['replay_steps'],10);self.assertEqual(len(r['actions']),50);self.assertEqual(r['elapsed'],50)
    def test_saved_postterminal_work_rejected(self):
        c=bank().candidates[0];s=source();r=run_branch(lambda *_:FakeWorld(),s,c,tail,50,1,domain='artificial')
        r['terminal_flags']=(False,True)+r['terminal_flags'][2:]
        with self.assertRaises(ValueError):check_branch(r,c,s,lambda _:False)
    def test_replay_mismatch_rejected_closes_world(self):
        s=source(1);s=SourceHistory(s.parent,s.construction_id,s.replay_actions,('bad',*s.observation_ids[1:]),s.elapsed)
        w=FakeWorld()
        with self.assertRaises(ValueError):run_branch(lambda *_:w,s,bank().candidates[0],tail,50,1,domain='artificial')
        self.assertTrue(w.closed)
    def test_saved_array_roundtrip_independent_acceptance(self):
        c=bank().candidates[0];s=source();r=run_branch(lambda *_:FakeWorld(stop=3),s,c,tail,50,1,domain='artificial')
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'new';save_artificial(p,r);m=sha(p/'members.json')
            loaded=load_artificial(p,m);self.assertTrue(check_branch(loaded,c,s,lambda _:False)['accepted'])
            with self.assertRaises(FileExistsError):save_artificial(p,r)
            with (p/'actions.npy').open('ab') as f:f.write(b'bad')
            with self.assertRaises(ValueError):load_artificial(p,m)
    def test_negative_zero_oracle_accepted_parent_unit(self):
        y=np.array([[[1,1],[0,0]],[[0,0],[0,0]],[[1,0],[0,1]]])
        choices=np.array([[0,0,1,1]]*3)
        r=estimate(['a','b','c'],y,choices,[0,0,0])
        self.assertEqual(r['n_independent_parents'],3);self.assertLess(r['contrasts']['O0-P0']['mean'],0)
        self.assertEqual(r['contrasts']['interaction']['mean'],0)
        with self.assertRaises(ValueError):estimate(['a','a','c'],y,choices,[0,0,0])

if __name__=='__main__':unittest.main(verbosity=2)
