"""New tiny synthetic tests only. Never read accepted scientific numeric data."""
import copy,json,time,unittest
from pathlib import Path
import numpy as np
from .common import DOC,ROOT,canonical,identity,write_new,read_bound,unique
from .numerics import decompose,s0,ranks,clock_summary,paired_bootstraps
from .worker_v2 import process_parent
from wm_diag0.core import array_id

FIXTURE=DOC/'artificial-002'
def parts(p,r,g=None,score='terminal_sum'):
    p=np.array(p,dtype=np.float32);r=np.array(r,dtype=np.float32);g=np.zeros(p.shape[1:],np.float32) if g is None else np.array(g,np.float32)
    cp=s0(p,g,score).astype(np.float64);cr=s0(r,g,score).astype(np.float64);costs=np.stack([cp,cp,cr,cr]);choices=np.argmin(costs,axis=1).tolist()
    return decompose(p,r,g,costs,choices,score)
def event(i,success=False,terminated=False,truncated=False):return {'clock':i,'success':success,'terminated':terminated,'truncated':truncated}
def prefix(actions=25,success=False,truncated=False):
    events=[event(i) for i in range(actions+1)];events[-1]=event(actions,success,success,truncated)
    return {'actions':actions,'events':events,'sampling':[5,10,15,20,25],'absorbed_after_stop':success or truncated}
def branch(actions=50,success=False):
    events=[event(i) for i in range(actions+1)];events[-1]=event(actions,success,success)
    return {'elapsed':actions,'events':events,'tail_replans':int(actions>25),'replay_steps':20,'reason':'success' if success else 'budget_failure','draw_seed':77}

class FixedTests(unittest.TestCase):
    def test_squared_identity_signed_and_reductions(self):
        for score in ('terminal_sum','terminal_mse'):
            x=parts([[0.,2.,3.],[4.,1.,2.]],[[1.,2.,1.],[2.,3.,2.]],score=score)
            self.assertLess(x['max_absolute_candidate_identity_residual'],1e-11)
            for c in x['candidates']:self.assertAlmostEqual(c['float64_predicted_S0']-c['float64_realized_S0'],c['signed_goal_direction_term']+c['squared_error_term'])
            self.assertAlmostEqual(x['energies']['total_mean_L2_squared'],x['energies']['common_L2_squared']+x['energies']['specific_mean_L2_squared'])
    def test_common_vector_and_scalar_are_not_same(self):
        x=parts([[0.],[2.]],[[-2.],[0.]])
        self.assertEqual((x['P0_index'],x['O0_index'],x['A_index'],x['B_index']),(0,1,1,0))
        self.assertEqual(np.argmin(np.array([0.,4.])+7),0)
        self.assertEqual(x['energies']['specific_mean_L2_squared'],0)
    def test_specific_only_and_zero_error(self):
        x=parts([[0.],[2.]],[[1.],[1.]])
        self.assertEqual(x['energies']['common_L2_squared'],0)
        self.assertEqual((x['A_index'],x['B_index']),(x['P0_index'],x['O0_index']))
        z=parts([[1.,2.]],[[1.,2.]])
        self.assertIsNone(z['energies']['common_energy_fraction_not_failure_attribution'])
    def test_tie_native_and_ragged_banks(self):
        self.assertEqual(ranks([1.,1.,0.]),[2,3,1])
        for n in (1,3,16):
            p=np.arange(n,dtype=np.float32)[:,None];r=p[::-1].copy();x=parts(p,r)
            self.assertEqual(len(x['candidates']),n);self.assertEqual(x['P0_index'],0)
        x=parts([[2.],[0.]],[[0.],[2.]])
        self.assertEqual(x['P0_index'],1);self.assertNotEqual(x['P0_index'],0) # Native return remains slot0.
    def test_negative_zero_outcomes_are_not_forced_positive(self):
        x=parts([[0.],[2.]],[[-2.],[0.]])
        y=np.array([[1.,1.],[0.,0.]])
        self.assertEqual(y[x['A_index']].mean()-y[x['P0_index']].mean(),-1)
        self.assertEqual(y[x['B_index']].mean()-y[x['P0_index']].mean(),0)
    def test_native_dtype_cast_and_object_refusal(self):
        x=parts([[.1,.2],[.3,.4]],[[.2,.3],[.4,.5]])
        self.assertEqual(x['native_dtype'],'<f4')
        with self.assertRaises(ValueError):parts([[float('nan')]],[[0.]])
        with self.assertRaises(ValueError):decompose(np.array([[None]],object),np.array([[None]],object),np.array([None],object),np.zeros((4,1)),[0]*4,'terminal_sum')
    def test_clock_absorption_and_tail(self):
        p=clock_summary(prefix(3,True),True)
        self.assertEqual(p['absorbed_sampling_positions'],[5,10,15,20,25]);self.assertTrue(p['terminal_feature_post_stop_absorbed'])
        q=clock_summary(prefix(25,True),True);self.assertTrue(q['stopped_exactly_at_horizon']);self.assertFalse(q['terminal_feature_post_stop_absorbed'])
        self.assertEqual(clock_summary(branch(25,True))['phase'],'prefix_success')
        self.assertEqual(clock_summary(branch(26,True))['phase'],'tail_success')
        self.assertEqual(clock_summary(branch())['phase'],'failure')
        bad=branch(26,True);bad['events'][25]['success']=True
        with self.assertRaises(ValueError):clock_summary(bad)
    def test_exact_input_and_immutable_outputs(self):
        p=FIXTURE/'immutable-control.json';write_new(p,{'fixture':True});want=identity(p)
        self.assertEqual(read_bound(p,want),canonical({'fixture':True}))
        with self.assertRaises(FileExistsError):write_new(p,{'other':True})
        with self.assertRaises(ValueError):read_bound(p,dict(want,sha256='0'*64))
        with self.assertRaises(ValueError):unique([('a',1),('a',2)])
    def test_source_paired_bootstrap(self):
        rows=[]
        for task in ('pusht','reacher'):
            for backbone in ('lewm','dinowm_noprop'):
                for i in range(32):rows.append({'task':task,'backbone':backbone,'root_index':i,'root_id':task+'-'+str(i),
                    'outcomes':{'P0':{'mean':float(i%2)},'A':{'mean':0.},'B':{'mean':float(i%2)}},'decomposition':{'A_index':0,'B_index':1,'O0_index':1}})
        result,ids=paired_bootstraps(rows)
        self.assertEqual(len(ids),2);self.assertEqual(result['pusht|lewm'],result['pusht|dinowm_noprop'])
        self.assertEqual(result['pusht|lewm']['B']['ci95_percentile'],[0.,0.])
        rows[-1]['root_id']='WRONG_SOURCE'
        with self.assertRaises(ValueError):paired_bootstraps(rows)
    def test_real_saved_parent_join_on_tiny_synthetic_files(self):
        parent=FIXTURE/'synthetic-parent';out=parent/'output';out.mkdir(parents=True);(parent/'controls').mkdir()
        n=3;goal=np.zeros(192,np.float32);p=np.zeros((n,5,192),np.float32);r=p.copy();p[:,:,0]=np.array([0,1,2])[:,None];r[:,:,0]=np.array([3,0,2])[:,None]
        actions=np.stack([np.full((25,2),i,np.float32) for i in range(n)]);cost=np.stack([s0(p[:,-1],goal,'terminal_sum')]*2+[s0(r[:,-1],goal,'terminal_sum')]*2).astype(np.float64);choices=np.argmin(cost,axis=1).tolist()
        values={'actions.npy':actions,'predicted.npy':p,'realized.npy':r,'goal.npy':goal,'costs.npy':cost}
        for name,value in values.items():
            with (out/name).open('xb') as f:np.save(f,value,allow_pickle=False)
        route={'native_score_id':'terminal_sum','feature_shape':[192],'positions':[5,10,15,20,25]}
        selected={'candidate_ids':[array_id(a) for a in actions],'route':route,'source_id':'SYNTHETIC','readout_id':'SYNTHETIC','selection':{'choices':choices,'goal_id':array_id(goal)},'evaluation_draws':[77,77]}
        write_new(out/'SELECTION.json',selected)
        for candidate in range(n):
            pre=prefix(3,True) if candidate==1 else prefix()
            write_new(out/('oracle/'+str(candidate)+'/PREFIX.json'),pre)
            for draw in (0,1):
                b=branch(3,True) if candidate==1 else branch(26,True) if candidate==2 else branch()
                write_new(out/('evaluation/'+str(candidate)+'-'+str(draw)+'/BRANCH.json'),b)
        members={f.relative_to(out).as_posix():identity(f) for f in out.rglob('*') if f.is_file()};write_new(out/'MEMBERS.json',members)
        ctl={'accepted':True,'output_seal':identity(out/'MEMBERS.json')};write_new(parent/'controls/ACCEPTED.json',ctl);write_new(parent/'controls/RESULT.json',{'status':'ACCEPTED'})
        write_new(parent/'controls/SELECTION-EXTERNAL.json',{'seal':members['SELECTION.json']})
        meta={'setting':0,'task':'pusht','backbone':'lewm','root_index':0,'root_id':'SYNTHETIC','candidate_count':3,'candidate_ids':selected['candidate_ids'],'native_index':0,'source_id':'SYNTHETIC','source_seal':{},'route':route,'readout_id':'SYNTHETIC','active_head':{},'parent_path':str(parent),'output':str(out),'output_seal':ctl['output_seal'],'required_members':members,
            'accepted_control':identity(parent/'controls/ACCEPTED.json'),'accepted_result':identity(parent/'controls/RESULT.json'),'external_selection':identity(parent/'controls/SELECTION-EXTERNAL.json'),
            'array_headers':{name:{'shape':list(value.shape),'dtype':value.dtype.str} for name,value in values.items()}}
        baseline={'settings':{'pusht|lewm':{'parent_ids':['SYNTHETIC'],'candidate_counts':[3],'selected_indices':[choices],'source_cells':[[0.,0.,1.,1.]],'native_parent':[0.]}}}
        target=FIXTURE/'synthetic-join';target.mkdir();(target/'controls').mkdir()
        result=process_parent(meta,baseline,target,time.monotonic()+20)
        self.assertEqual(result['original_O0_minus_P0'],1);self.assertTrue(result['candidates'][1]['oracle_prefix']['terminal_feature_post_stop_absorbed'])
        self.assertEqual(result['candidates'][2]['evaluation_draws'][0]['phase'],'tail_success')
        self.assertEqual(len(result['candidates']),3)

def main():
    FIXTURE.mkdir(exist_ok=False)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FixedTests);result=unittest.TextTestRunner(verbosity=2).run(suite)
    files={p.relative_to(FIXTURE).as_posix():identity(p) for p in FIXTURE.rglob('*') if p.is_file()}
    write_new(DOC/'ARTIFICIAL-002.json',{'status':'PASSED' if result.wasSuccessful() else 'FAILED','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'sources':{p.relative_to(ROOT).as_posix():identity(p) for p in (ROOT/'wm_diag1_saved_v1').glob('*.py')},'fixture_members':files,
        'fixture_bytes':sum(r['bytes'] for r in files.values()),'actual_saved_research_array_reads':0,'model_or_physics_calls':0,'real_saved_data_job_launched':False})
    if not result.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':main()
