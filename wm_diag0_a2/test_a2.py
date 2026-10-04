"""Artificial new-origin, routing, phase and adverse-outcome tests. No native imports."""
import copy
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import numpy as np
from wm_diag0.core import Features, native_terminal_score, select_four, array_id
from wm_diag0.test_components import bank, contract, ridge
from wm_diag0.readout import task_margin
from wm_diag0.phase import seal_artificial, join_artificial_outcomes
from wm_diag0.accept import check_branch
from wm_diag0.analysis import estimate
from .design import root_plan, counts, storage, DOC
from .path import *

class ToyOriginWorld:
    def __init__(self,origin=None,stop=1000,success_clock=None,goal_steps=False):
        self.origin=origin or {'clock':0,'hidden':3,'rng_seed':7}
        self.clock=0;self.hidden=3;self.stop=stop;self.success_clock=success_clock
        self.goal_steps=goal_steps;self.goal_installed=False;self.closed=False
    def obs(self): return np.full((2,2,3),self.clock,np.uint8)
    def complete_state(self): return {'clock':self.clock,'hidden':self.hidden,'rng_seed':self.origin['rng_seed']}
    def dynamic_state(self): return self.complete_state()
    def reset(self):
        self.clock=self.origin['clock'];self.hidden=self.origin['hidden']
        return self.current()
    def current(self):
        success=self.goal_installed and self.success_clock is not None and self.clock>=self.success_clock
        return self.obs(),success,self.clock>=self.stop,False
    def step(self,action):
        _,success,terminal,_=self.current()
        if success or terminal: raise AssertionError('post-terminal physics')
        self.clock+=1;self.hidden+=int(np.asarray(action)[0])+1
        return self.current()
    def install_goal(self,goal):
        self.goal_installed=True
        if self.goal_steps: self.clock+=1
    def close(self): self.closed=True

def collector(obs,clock,seed): return np.zeros(2,np.float32)
def record():
    row=root_plan()['roots'][0]
    return collect_artificial(row,lambda seed:ToyOriginWorld({'clock':0,'hidden':3,'rng_seed':seed}),collector,domain='artificial')
def route():
    return ArtifactRoute('pusht','dinowm_noprop','1'*64,'2'*64,'3'*64,'4'*64,'a'*40,(196,384))

class A2Tests(unittest.TestCase):
    def test_exact_route_and_no_third_backbone(self):
        r=route();self.assertEqual(authenticate_route(r,r),r.identity)
        for field,value in [('checkpoint','0'*64),('config','0'*64),('normalization','0'*64),('task','reacher'),('encoder','0'*64)]:
            with self.assertRaises(ValueError): authenticate_route(replace(r,**{field:value}),r)
        with self.assertRaises(ValueError): authenticate_route(replace(r,source_revision='main'),replace(r,source_revision='main'))
        with self.assertRaises(ValueError): authenticate_route(replace(r,backbone='point_lewm'),replace(r,backbone='point_lewm'))
    def test_native_patch_and_action_clock(self):
        r=route();self.assertEqual(sampling_clock(r,np.zeros((25,2))),(5,10,15,20,25))
        for changed in (replace(r,history=3),replace(r,layout=(256,384)),replace(r,grouping=4)):
            with self.assertRaises(ValueError): authenticate_route(changed,changed)
        with self.assertRaises(ValueError): sampling_clock(r,np.zeros((24,2)))
    def test_decoding_full_physical_bytes_not_repeated_actions(self):
        z=np.arange(50,dtype=np.float32).reshape(5,10)
        a=decoded_actions(z,np.array([1.,2.]),np.array([.2,.3]))
        np.testing.assert_array_equal(a,z.reshape(25,2)*[.2,.3]+[1.,2.])
        self.assertEqual(a.shape,(25,2));self.assertGreater(a.max(),1)
    def test_deterministic_whole_root_roles(self):
        p=root_plan();check_root_roles(p);self.assertEqual(p,root_plan())
        self.assertEqual(len(p['roots']),120)
        self.assertFalse(any('P2' in r['root_id'] for r in p['roots']))
        bad=copy.deepcopy(p);bad['roots'][-1]['root_id']=bad['roots'][0]['root_id']
        with self.assertRaises(ValueError):check_root_roles(bad)
    def test_readout_rows_owned_by_root_only(self):
        p=root_plan()
        for r in p['roots']:
            self.assertEqual(len(r['readout_frame_indices']),16 if r['role']=='readout_fit' else 8 if r['role']=='readout_validation' else 0)
            self.assertTrue(all(10<=i<=44 for i in r['readout_frame_indices']))
    def test_collection_no_future_model_selector_inputs(self):
        rec=record();self.assertEqual(len(rec['actions']),44);self.assertTrue(rec['available'])
        self.assertNotIn('labels',inspect.signature(collector).parameters)
        s=shared_scenario(rec,'pusht');self.assertEqual(s.scenario_id,shared_scenario(rec,'pusht').scenario_id)
        self.assertEqual(s.history.shape,(1,2,2,3));self.assertEqual(s.history[0,0,0,0],20);self.assertEqual(s.goal[0,0,0],44)
        raw=dict(root=s.root,task=s.task,role=s.role,history=s.history,goal=s.goal)
        for name in ('qpos','winding','future_actions','evaluation_labels','success'):
            with self.assertRaises(ValueError):selector_input(dict(raw,**{name:np.zeros(1)}))
    def test_early_collection_stops_preserved_no_replacement(self):
        r=root_plan()['roots'][0]
        rec=collect_artificial(r,lambda _:ToyOriginWorld(stop=7),collector,domain='artificial')
        self.assertFalse(rec['available']);self.assertEqual(len(rec['actions']),7)
        self.assertEqual(rec['reason'],'unavailable_window_no_replacement')
        with self.assertRaises(ValueError):shared_scenario(rec,'pusht')
    def test_full_replay_not_partial_observable_state(self):
        rec=record();owner=Ownership();w=replay_artificial(rec,ToyOriginWorld,owner,domain='artificial')
        self.assertEqual(w.clock,20);self.assertEqual(w.hidden,23);w.close()
        def wrong(origin):
            origin['hidden']+=1;return ToyOriginWorld(origin)
        with self.assertRaises(ValueError):replay_artificial(rec,wrong,owner,domain='artificial')
    def test_independent_world_and_goal_install_no_physics(self):
        rec=record();owner=Ownership()
        a=replay_artificial(rec,ToyOriginWorld,owner,domain='artificial')
        b=replay_artificial(rec,ToyOriginWorld,owner,domain='artificial')
        self.assertIsNot(a,b);a.hidden+=1;self.assertNotEqual(a.hidden,b.hidden)
        with self.assertRaises(ValueError):replay_artificial(rec,lambda _:b,owner,domain='artificial')
        with self.assertRaises(ValueError):replay_artificial(rec,lambda o:ToyOriginWorld(o,goal_steps=True),Ownership(),domain='artificial')
        class WrongGoalPixels(ToyOriginWorld):
            def obs(self):return super().obs()+(1 if self.goal_installed else 0)
        with self.assertRaises(ValueError):replay_artificial(rec,WrongGoalPixels,Ownership(),domain='artificial')
        a.close();b.close()
    def test_snapshot_restore_matches_replay_hidden_state(self):
        rec=record();replayed=replay_artificial(rec,ToyOriginWorld,Ownership(),domain='artificial')
        snap=copy.deepcopy(replayed.complete_state());restored=ToyOriginWorld(snap);restored.reset()
        self.assertEqual(restored.complete_state(),replayed.complete_state())
        self.assertEqual(array_id(restored.obs()),array_id(replayed.obs()))
        restored.step(np.zeros(2));self.assertNotEqual(restored.complete_state(),replayed.complete_state())
        restored.close();replayed.close()
    def test_branch_budget_tail_ownership_and_independent_acceptance(self):
        rec=record();c=bank().candidates[0];tails=[];owner=Ownership()
        def make_tail(draw):
            state={'draw':draw,'calls':0};tails.append(state)
            def tail(obs,elapsed,remaining):
                self.assertEqual(remaining,50-elapsed);state['calls']+=1
                return np.zeros(2,np.float32)
            return tail
        rr=[run_new_branch(rec,ToyOriginWorld,owner,c,make_tail,d,domain='artificial') for d in (1,2)]
        self.assertIsNot(tails[0],tails[1]);self.assertEqual(tails[0]['calls'],25)
        for r in rr:
            self.assertEqual(r['elapsed'],50);self.assertEqual(r['replay_steps'],20)
            self.assertTrue(check_branch(r,c,source_reference(rec),lambda _:False)['accepted'])
    def test_initial_success_and_early_terminal_unchanged_budget(self):
        rec=record();c=bank().candidates[0]
        for success,stop,expected in ((20,1000,0),(27,1000,7),(None,27,7)):
            factory=lambda o:ToyOriginWorld(o,stop=stop,success_clock=success)
            result=run_new_branch(rec,factory,Ownership(),c,lambda _:lambda *args:self.fail('tail after stop'),1,domain='artificial')
            self.assertEqual(result['elapsed'],expected)
            self.assertEqual(result['success'],success is not None)
    def test_four_cells_native_reference_and_seal_before_join(self):
        b=bank();c=contract();r=ridge(c);values=np.zeros((16,5,6))
        p=Features(values,c,b.identity,record()['root'],'predicted');o=replace(p,kind='realized')
        choices=select_four(b,p,o,np.zeros(6),native_terminal_score,r)
        self.assertEqual(len(choices.choices),4);self.assertEqual(b.native_index,0)
        calls=[]
        def outcome():
            calls.append(True);return {'source_id':p.source_id,'bank_id':b.identity,'draws':[1,2],'success':np.zeros((16,2),int)}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'seal'
            seal=seal_artificial(path,b,p,o,np.zeros(6),native_terminal_score,r,oracle_prefix_id='prefix',oracle_draw=3,evaluation_draws=(1,2),domain='artificial')
            self.assertFalse(calls);join_artificial_outcomes(path,seal,outcome);self.assertEqual(calls,[True])
            with (path/'action-0.npy').open('ab') as f:f.write(b'x')
            calls.clear()
            with self.assertRaises(ValueError):join_artificial_outcomes(path,seal,outcome)
            self.assertFalse(calls)
    def test_negative_zero_all_failure_effects_allowed(self):
        for y in (np.zeros((3,2,2),int),np.array([[[1,1],[0,0]]]*3)):
            result=estimate(['new-a','new-b','new-c'],y,np.array([[0,0,1,1]]*3),[0,0,0])
            self.assertLessEqual(result['contrasts']['O0-P0']['mean'],0)
    def test_raw_reacher_no_hidden_winding_fix(self):
        self.assertAlmostEqual(task_margin('reacher',np.array([[2*np.pi,0.]]),np.zeros(2))[0],2*np.pi/.05)
    def test_recomputed_resources_and_full_future(self):
        c=counts();s=storage();self.assertEqual(c['all_controller_steps_max'],386880)
        self.assertEqual(c['world_resets_max'],6400);self.assertEqual(c['successful_logical_tasks_max'],255)
        self.assertEqual(c['dino_predictor_chunk_calls_max'],950740)
        self.assertEqual(c['cpu_allocation_seconds_proposed_cap'],13800)
        self.assertLess(s['live_reserved_bytes'],s['live_cap_bytes']);self.assertLess(s['inclusive_reserved_bytes'],s['inclusive_cap_bytes'])
    def test_written_manifests_and_exact_native_size_reservations(self):
        self.assertEqual(json.loads((DOC/'ROOT-PLAN.json').read_text()),root_plan())
        self.assertEqual(json.loads((DOC/'RESOURCE-PLAN.json').read_text()),{'counts':counts(),'storage':storage()})
        d=196*384
        self.assertEqual(2*16*5*d*4,48_168_960)
        self.assertEqual((d*6+2*d+6)*8,4_816_944)
        self.assertEqual(352*d*4,105_971_712)
        self.assertEqual(counts()['pusht_integrator_steps_max']+counts()['pusht_reset_internal_integrator_steps_max'],1_940_800)
    def test_all_native_entry_points_refuse_execution(self):
        with self.assertRaises(PermissionError):NativeCampaign()
        for fn,args in ((collect_artificial,(None,None,None)),(replay_artificial,(None,None,None)),
                        (run_new_branch,(None,None,None,None,None,None))):
            with self.assertRaises(PermissionError):fn(*args,domain='research')
    def test_preservation_member_identity_and_corruption_rejection(self):
        from .preserve import verify
        from .audit_package import digest
        raw=b'opaque test bytes, never model execution';encoded=b'{}'
        manifest={'members':{'fixture.bin':digest(raw)}}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.zip'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('fixture.bin',raw);z.writestr('PACKAGE-MEMBERS.json',encoded)
            self.assertEqual(verify(path,manifest,encoded),2)
            with self.assertRaises(ValueError):verify(path,{'members':{'fixture.bin':digest(b'changed')}},encoded)
            with self.assertRaises(ValueError):verify(path,{'members':{}},encoded)
    def test_downloaded_config_blobs_and_checkpoints_authenticated_without_loading(self):
        pins=json.loads((DOC/'PUBLIC-PINS.json').read_text());receipts=json.loads((DOC/'ARTIFACT-RECEIPTS.json').read_text())
        for task,row in pins['huggingface'].items():
            for member in row['dino_members']:
                if member['rfilename'].endswith('.pth'):continue
                raw=(DOC/'source-audit'/task/member['rfilename']).read_bytes()
                self.assertEqual(len(raw),member['size'])
                self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),member['blobId'])
            art=next(r for r in receipts if r['name']==task)
            self.assertEqual(art['sha256'],art['published_sha256']);self.assertIn('data.pkl',[m['name'].split('/')[-1] for m in art['zip_members']])

if __name__=='__main__': unittest.main(verbosity=2)
