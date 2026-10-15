"""New native-gate interface tests with artificial arrays/JSON only."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .accept import accept
from .common import canonical,identity,write_new
from wm_diag0.core import FeatureContract,Features,Selection,array_id,capture_bank,frozen
from wm_diag0.readout import Ridge
from wm_diag0_native_v3.actions import decode
from wm_diag0_native_v3.store import save_array,seal

class Acceptance(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        from PIL import Image
        rng=np.random.default_rng(5);task='reacher';backbone='lewm'
        self.c={'lewm':{task:{'sha256':'a'*64}},'prior_source':str(self.root/'prior')}
        stats=self.root/'prior/configs/reacher';stats.mkdir(parents=True)
        write_new(stats/'swm_h5_norm_stats.json',{'action_mean':[0.,0.],'action_std':[1.,1.]})
        route=FeatureContract(backbone,'a'*64,'b'*64,(192,),(5,10,15,20,25),1,'terminal_sum')
        self.row={'task':task,'root_id':'ARTIFICIAL-ONLY-ROOT','root_index':0,'role':'diagnostic'}
        history=np.zeros((1,224,224,3),dtype=np.uint8);goalrgb=np.ones((224,224,3),dtype=np.uint8)
        self.source=self.root/'source';self.source.mkdir();(self.source/'selector').mkdir();(self.source/'evidence').mkdir()
        save_array(self.source/'selector/history.npy',history);save_array(self.source/'selector/goal.npy',goalrgb)
        coords=np.zeros((45,2),dtype=np.float64);coords[44]=1;save_array(self.source/'evidence/coordinates.npy',coords)
        write_new(self.source/'record.json',{'root':self.row,'available':True,'frames':[{'audit':'artificial-audit'}]*45})
        self.source_seal=seal(self.source,12_000_000)
        self.head=self.root/'readout';self.head.mkdir()
        model=Ridge(route,task,frozen(np.zeros(192)),frozen(np.ones(192)),frozen(np.zeros((192,2))),frozen(np.zeros(2)),('ARTIFICIAL-FIT',))
        for k,a in zip(('mean','scale','weights','intercept'),(model.mean,model.scale,model.weights,model.intercept)):save_array(self.head/(k+'.npy'),a)
        for k,a in (('fit-features',np.zeros((256,192),np.float32)),('fit-labels',np.zeros((256,2))),('validation-features',np.zeros((96,192),np.float32)),('validation-labels',np.zeros((96,2))),('dual',np.zeros((256,2)))):save_array(self.head/(k+'.npy'),a)
        write_new(self.head/'READOUT.json',{'task':task,'backbone':backbone,'fit_parents':model.fit_parent_ids,'identity':model.identity})
        self.head_seal=seal(self.head,5_000_000)
        trace=rng.normal(size=(9000,25,2)).astype(np.float32);tc=np.mean(trace**2,axis=(1,2),dtype=np.float32)
        idx=np.argsort(tc[8700:])[:30].astype(np.int64);elites=trace[8700+idx].reshape(30,5,10);mean=elites.mean(0)
        native=decode(mean,np.zeros(2),np.ones(2));bank=capture_bank(native,trace,tc)
        n=len(bank.candidates);actions=np.stack([x.actions for x in bank.candidates]);pred=rng.normal(size=(n,5,192)).astype(np.float32);real=rng.normal(size=(n,5,192)).astype(np.float32);goal=np.zeros(192,np.float32)
        costs=np.stack([np.sum(pred[:,-1]**2,axis=1),np.zeros(n),np.sum(real[:,-1]**2,axis=1),np.zeros(n)]).astype(np.float64)
        sid=canonical({'root':self.row['root_id'],'source':array_id(history),'goal':array_id(goalrgb),'route':route.identity})
        selection=Selection(bank.identity,sid,route.identity,array_id(goal),model.identity,tuple(np.argmin(costs,axis=1).tolist()),tuple(array_id(x) for x in costs))
        self.out=self.root/'output';self.out.mkdir()
        for k,a in (('trace',trace),('trace-costs',tc),('actions',actions),('native-elites',elites),('native-mean',mean),('native-indices',idx),('predicted',pred),('realized',real),('goal',goal),('costs',costs)):save_array(self.out/(k+'.npy'),a)
        def events():return [{'clock':0,'native_clocks':{'clock':20,'wrapper_elapsed':20,'step_count':40,'physics_time':.4},'coordinates':[0.,0.],'pixels':array_id(history[0]),'audit':'artificial-audit','success':False,'terminated':False,'truncated':False},
                {'clock':1,'native_clocks':{'clock':21,'wrapper_elapsed':21,'step_count':42,'physics_time':.42},'coordinates':[1.,1.],'pixels':array_id(goalrgb),'audit':'artificial-final','success':True,'terminated':True,'truncated':False}]
        (self.out/'oracle').mkdir()
        for i in range(n):
            p=self.out/'oracle'/str(i);p.mkdir();save_array(p/'actions.npy',actions[i,:1])
            for t in (5,10,15,20,25):Image.fromarray(goalrgb).save(p/(str(t)+'.png'))
            write_new(p/'PREFIX.json',{'actions':1,'events':events(),'goal_installation':{'world_serial':1+i*3}})
        selected={'root':self.row,'backbone':backbone,'route':route.__dict__,'source_id':sid,'source_seal':self.source_seal,
            'readout_id':model.identity,'selection':selection.__dict__,'bank_id':bank.identity,'candidate_ids':[x.identity for x in bank.candidates],
            'native_index':0,'trace_digest':bank.trace_digest,'technical':False,'goal_installation':{'world_serial':0},'evaluation_draws':[1,2],
            'members_before_evaluation':{str(p.relative_to(self.out)).replace('\\','/'):identity(p) for p in self.out.rglob('*') if p.is_file()}}
        write_new(self.out/'SELECTION.json',selected);self.external=self.root/'SELECTION-EXTERNAL.json';write_new(self.external,{'seal':identity(self.out/'SELECTION.json')})
        (self.out/'evaluation').mkdir()
        for i in range(n):
            for draw in (0,1):
                p=self.out/'evaluation'/(str(i)+'-'+str(draw));p.mkdir();save_array(p/'actions.npy',actions[i,:1])
                write_new(p/'BRANCH.json',{'elapsed':1,'events':events(),'draw_seed':draw+1,'replay_steps':20,'tail_replans':0,'reason':'success','goal_installation':{'world_serial':2+i*3+draw}})
        write_new(self.out/'USAGE.json',{'candidate_count':n})
        self.output_seal=seal(self.out,10_000_000)
    def tearDown(self):self.tmp.cleanup()
    def call(self):return accept(self.out,self.output_seal,self.external,self.source,self.source_seal,self.head,self.head_seal,self.c,gpu=False)
    def test_complete_artificial_independent_acceptance(self):
        r=self.call();self.assertTrue(r['accepted']);self.assertEqual(r['candidate_count'],16);self.assertEqual(r['worlds'],49)
    def test_selection_tampering_is_rejected_before_outcome_access(self):
        p=self.out/'SELECTION.json';raw=json.loads(p.read_text());raw['selection']['source_id']='forged';p.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):self.call()
    def test_extra_untrusted_file_is_rejected(self):
        (self.out/'unexpected.py').write_text('not executed')
        with self.assertRaisesRegex(ValueError,'extra/missing'):self.call()

if __name__=='__main__':unittest.main()
