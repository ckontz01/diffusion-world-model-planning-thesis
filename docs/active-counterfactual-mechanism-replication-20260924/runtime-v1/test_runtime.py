"""Artificial interfaces + real state machine; no cluster, checkpoint, physics or efficacy sweep."""
import common as c
import ast
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
import acceptance
import dispatch
import models
import scheduler
import storage
from selector import CommittedFeedbackSelector
from model import JointModel,OrdinaryModel,Preprocessing
from policy import Selector,context,execute_episode
from tree import Ledger
from mock import abstract_tree,VectorEnv

RESULTS={}
def row(j,job='42',state='COMPLETED'):
    return scheduler.parse('|'.join([job,'acvm1-'+j['key'],state,'0:0' if state=='COMPLETED' else '1:0','2','4',
        'cpu=4,mem='+str(j['ram_gib'])+'G,node=1'+(',gres/gpu=1' if j['gpu'] else ''),
        'gpu09' if j['gpu'] else 'cpu01','a6000' if j['gpu'] else 'defq','normal-a6000' if j['gpu'] else 'normal','superworld',str(j['seconds']//60)]))

class Unit(unittest.TestCase):
    def test_01_false_approval_before_inputs_or_commands(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'false.json';c.write(p,{'authorized':False})
            with patch('subprocess.run',side_effect=AssertionError('scheduler accessed')):
                with self.assertRaises(PermissionError):c.Authorization(p,'invalid')
    def test_02_frozen_old_code(self):
        p=c.read(c.PROPOSAL/'DEPENDENCIES.json')
        # Reviewed dependency document may be a list or wrapped map; pins below are explicit.
        for name,h in {'policy.py':'753271dcce8f1e7c21a665e215c4aee2e6a5a8f8098fe6d816a75e2b93a38453',
                       'bindings-r1/fitting.py':'c4fa3ee50cdcbac0267d10bb62d62ab7d8ccd16d8040d1043ebdf80109e060e1',
                       'bindings-r1/episodes.py':'5f09b7c5c23b9c3ec947dec9e32f216a8a83e6422d379bbba5637b7e96712edc'}.items():self.assertEqual(c.sha(c.BASE/name),h)
    def test_03_all_original_decisions_unchanged(self):
        j=JointModel(56,24,4);o=OrdinaryModel(56,24,4);old=Selector(j,o);new=CommittedFeedbackSelector(j,o)
        tree=abstract_tree();h=context([np.zeros(4)],[],np.zeros(4),0)
        for mode in ('static','passive','active','no_update','ordinary'):
            a,b=Ledger(),Ledger();x=old.select(tree,h,a,mode);y=new.select(tree,h,b,mode)
            self.assertEqual(x,y);self.assertEqual(old.after(x,tree,h,np.ones(4),a),new.after(y,tree,h,np.ones(4),b));self.assertEqual(vars(a),vars(b))
    def test_04_new_prefix_static_baseline_feedback_and_terminal(self):
        j=JointModel(56,24,4);new=CommittedFeedbackSelector(j);tree=abstract_tree();h=context([np.zeros(4)],[],np.zeros(4),0)
        for p in j.params:p[:]=0
        static=Selector(j).select(tree,h,Ledger(),'static');d=new.select(tree,h,Ledger())
        self.assertEqual(d.prefix,static.prefix);self.assertEqual(d.prefix,0);self.assertIsNone(d.suffix);self.assertFalse(d.direct_baseline)
        original_conditional=new.conditional
        new.conditional=lambda x,a,r,mode,ledger:np.tile([0.,0.,1.],(len(x),1))
        self.assertEqual(new.after(d,tree,h,np.ones(4),Ledger()),2)
        new.conditional=original_conditional
        new.after=lambda *a:(_ for _ in ()).throw(AssertionError('post-terminal suffix'))
        result=execute_episode(VectorEnv(success_at=3),tree,new,np.zeros(4),lambda *a:np.zeros((15,2)),Ledger(),'committed_feedback')
        self.assertIsNone(result['selected_suffix']);self.assertEqual(result['steps'],3)
    def test_05_grid_exact_axes_and_order(self):
        jobs=c.grid();ev=[j for j in jobs if j['gpu']];refs=c.roles()['mechanism_evaluation']
        self.assertEqual(len(jobs),8197);self.assertEqual(len(ev),8192);self.assertEqual(len({j['key'] for j in jobs}),8197)
        for n,ref in enumerate(refs):
            rows=ev[n*16:(n+1)*16];self.assertEqual({j['reference'] for j in rows},{ref})
            self.assertEqual({(j['pair'],j['control']) for j in rows},{(p,a) for p in range(3) for a in c.CONTROLS[:-1]}|{(None,'early-replan')})
        RESULTS['grid']=dict(tasks=8197,episodes=8192,sources=512,early_replan_actual_executions=512)
    def test_06_scheduler_strict_alias_and_id(self):
        j=next(j for j in c.grid() if j['gpu']);r=row(j)
        scheduler.allocation(j,r)
        h=dict(hostname='gpu09.cluster',slurm_job_id='42',accepted=True,query_status='complete',cuda_available=True,visible_device_count=1,device_name=scheduler.DEVICE)
        scheduler.association(h,r)
        for bad in (dict(h,hostname='gpu09.evil'),dict(h,slurm_job_id='43'),dict(h,device_name='NVIDIA RTX A6000'),dict(h,visible_device_count=2)):
            with self.assertRaises(ValueError):scheduler.association(bad,r)
        self.assertEqual(scheduler.status('42|allocation|PENDING|0:0|0|0||gpu09||Unknown|superworld|','42',j),'INCOMPLETE')
        with self.assertRaises(ValueError):scheduler.status('43|allocation|PENDING|0:0|0|0||gpu09||Unknown|superworld|','42',j)
        with self.assertRaises(ValueError):scheduler.allocation(j,dict(r,node='gpu08'))
    def test_07_full_future_reservation_and_footprint(self):
        jobs=c.grid();x=dispatch.reservation(jobs,{})
        self.assertEqual(x,dict(gpu_seconds=2457600,cpu_stage_seconds=36000))
        f=storage.footprint(jobs);self.assertLess(f['archive'],18500000000);self.assertLess(f['inclusive'],80000000000)
        RESULTS['complete_footprint']=f
    def test_08_model_access_gate(self):
        auth=c.Authorization.__new__(c.Authorization);auth.approval={'package_sha256':'artificial'}
        with tempfile.TemporaryDirectory() as d:
            auth.run=Path(d);auth.inputs={'references':{}}
            with patch.object(c,'sha',side_effect=AssertionError('reference payload read')):
                with self.assertRaises(FileNotFoundError):auth.reference(c.roles()['mechanism_evaluation'][0],'mechanism_evaluation')
        with self.assertRaises(ValueError):auth.reference(c.roles()['fit'][0],'fit')
    def test_09_estimator_exact_axes_single_early(self):
        sys.path.append(str(c.PROPOSAL));from planned_analysis import contrasts,analyze
        y=np.zeros((512,3,5),dtype=np.int8);early=np.zeros(512,dtype=np.int8)
        # Algebraic axes only: not an efficacy scenario or pass/fail based on treatment superiority.
        y[0,:,3]=1;early[0]=1
        d=contrasts(y,early);self.assertEqual(d.shape,(512,3,7));self.assertEqual(d[0,:,6].sum(),0)
        with self.assertRaises(ValueError):contrasts(y,np.zeros((512,3)))
        r=analyze(np.zeros_like(y),np.zeros_like(early));self.assertEqual(r['source_count'],512)
        self.assertEqual(len(r['contrasts']),7);self.assertEqual(r['bootstrap_resamples'],10000)
    def test_10_archive_nested_roots_hidden_corruption(self):
        from preserve import inventory,verify_tar
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);root=d/'nested'/'source';root.mkdir(parents=True);(root/'.hidden').write_bytes(b'artificial')
            expected,paths=inventory({'source':root});self.assertEqual(set(expected),{'source/.hidden'})
            t=d/'test.tar'
            with tarfile.open(t,'w') as z:
                for name,path in paths.items():z.add(path,arcname=name)
            self.assertEqual(verify_tar(t,expected)['members'],1)
            wrong={k:dict(v,sha256='0'*64) for k,v in expected.items()}
            with self.assertRaises(ValueError):verify_tar(t,wrong)
            with self.assertRaises(ValueError):verify_tar(t,{})
    def test_11_syntax_and_no_gpu_preparation_import(self):
        for p in c.ROOT.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
        self.assertNotIn('torch',sys.modules);self.assertNotIn('stable_worldmodel',sys.modules)
    def test_17_pending_grace_is_finite(self):
        j=next(j for j in c.grid() if j['gpu'])
        with tempfile.TemporaryDirectory() as d,patch.object(scheduler,'observe',return_value='42|allocation|PENDING|0:0|0|0||gpu09||Unknown|superworld|') as observed,patch('dispatch.time.sleep'):
            with self.assertRaises(ValueError):dispatch.RealScheduler(Path(d),Path(d)/'a',Path(d)).terminal('42',j)
            self.assertEqual(observed.call_count,9)
    def test_18_disabled_all_production_clis(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'false.json';c.write(a,{'authorized':False})
            for script,extra in [('worker.py',['--task','analysis']),('dispatch.py',['--control',d]),('finalize.py',['--control',d]),
                                 ('transport.py',['launch','--receipt',str(Path(d)/'x')]),('preserve.py',['backup','--request','invalid'])]:
                r=subprocess.run([sys.executable,'-B',str(c.ROOT/script),'--approval',str(a),'--run','invalid',*extra],capture_output=True,text=True,timeout=15)
                self.assertNotEqual(r.returncode,0);self.assertIn('DISABLED',r.stderr)
    def test_19_native_windows_remote_posix_path_and_deadline(self):
        from preserve import remote_archive_path,verify_tar
        self.assertEqual(remote_archive_path('/lustreFS/example/run-preservation/BACKUP-REQUEST.json'),'/lustreFS/example/run-preservation/final.tar')
        for bad in ('C:\\request.json','relative/BACKUP-REQUEST.json','/a/../b/BACKUP-REQUEST.json'):
            with self.assertRaises(ValueError):remote_archive_path(bad)
        with tempfile.TemporaryDirectory() as d:
            t=Path(d)/'empty.tar'
            with tarfile.open(t,'w'):pass
            with self.assertRaises(ValueError):verify_tar(t,{},deadline=0)

class Orchestration(unittest.TestCase):
    def execute(self,jobs,fault=None):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);control=root/'control';run=root/'run';control.mkdir();run.mkdir();(run/'submissions').mkdir()
        auth=types.SimpleNamespace(run=run,approval={'package_sha256':'artificial'})
        flags=dict(reused=False,frozen=False,gate=False);seen=[]
        class MockScheduler:
            def submit(_,j):
                if fault=='ambiguous':raise RuntimeError('artificial ambiguous scheduler response')
                if j['gpu']:
                    if not flags['frozen']:raise AssertionError('access before model freeze')
                    if len([x for x in seen if x['gpu']])>=16 and not flags['gate']:raise AssertionError('source2 before gate')
                seen.append(j);return str(100000+len(seen))
            def terminal(_,job,j):return row(j,job,'FAILED' if fault=='failed' else 'COMPLETED')
        def accept(j,r):scheduler.allocation(j,r);return dict(key=j['key'],job=r['job'],seal='artificial')
        kwargs=dict(jobs=jobs,accept=accept,reuse=lambda:flags.update(reused=True),freeze=lambda:flags.update(frozen=True),gate=lambda:flags.update(gate=True))
        if fault:
            with self.assertRaises((RuntimeError,ValueError)):dispatch.campaign(auth,control,MockScheduler(),**kwargs)
        else:dispatch.campaign(auth,control,MockScheduler(),**kwargs)
        with self.assertRaises(ValueError):dispatch.campaign(auth,control,MockScheduler(),**kwargs)
        return control,run,seen,flags
    def test_12_all8197_actual_state_machine(self):
        control,run,seen,flags=self.execute(c.grid())
        state=acceptance.ledger(control,c.grid());self.assertEqual(len(state['accepted']),8197);self.assertTrue(all(flags.values()))
        self.assertEqual(len({e['job'] for e in state['submitted'].values()}),8197)
        RESULTS['orchestration']=dict(tasks=len(seen),mocked_scheduler=True,production_state_machine=True,restart_rejected=True)
        # Full finalization control-plane check over all identities, using mocked worker
        # seals because8192 full-sized fixture payloads would violate the1GB prep limit.
        auth=types.SimpleNamespace(run=run,approval={'package_sha256':'artificial'},approval_sha='artificial')
        ev=[j for j in c.grid() if j['gpu']];gate_time=(state['claimed'][ev[15]['key']]['unix']+state['claimed'][ev[16]['key']]['unix'])/2
        snapshot=[e['row'] for e in state['terminal'].values()]
        with patch.object(acceptance,'worker',side_effect=lambda *a:dict(key=a[1]['key'])),patch('models.check_freeze',return_value={'unix':0}),patch.object(acceptance,'check_gate',return_value={'unix':gate_time}):
            self.assertEqual(acceptance.full(auth,control,snapshot)['tasks'],8197)
            c.write(control/'STOP.json',dict(error='artificial post-completion control-only fault'))
            with self.assertRaises(ValueError):acceptance.full(auth,control,snapshot)
            resolution=control/'RESOLUTION.json';c.write(resolution,dict(schema='ACVM1-control-resolution',package='artificial',faults={'STOP.json':c.sha(control/'STOP.json')},
                missing_acceptance=[],instruction='RESOLVE ACVM1 CONTROL artificial test only',new_jobs=0))
            answer=acceptance.full(auth,control,snapshot,resolution);self.assertEqual(answer['control_faults'],{'STOP.json':c.sha(control/'STOP.json')})
            self.assertTrue((control/'STOP.json').exists())
    def test_13_ambiguous_retains_claim_no_retry(self):
        control,_,seen,_=self.execute(c.grid()[:1],'ambiguous');s=acceptance.ledger(control,c.grid()[:1],False)
        self.assertEqual(len(s['claimed']),1);self.assertEqual(s['submitted'],{});self.assertTrue((control/'STOP.json').exists())
        self.assertEqual(s['claimed'][c.grid()[0]['key']]['reservation']['cpu_stage_seconds'],7200)
    def test_14_terminal_failure_charged_before_stop(self):
        j=next(j for j in c.grid() if j['gpu']);control,_,seen,_=self.execute([j],'failed');s=acceptance.ledger(control,[j],False)
        self.assertEqual(s['gpu_seconds'],2);self.assertEqual(s['accepted'],{});self.assertTrue((control/'STOP.json').exists())

class ScientificInterfaces(unittest.TestCase):
    def test_15_all_six_artificial_episode_paths_fresh(self):
        from artificial import FakeLeWM,FakeTorch,factory
        from bridge import LeWMBridge
        from episodes import evaluate,save
        from verify import verify_arrays,load_verify
        from worker import arrays_digest
        backend=LeWMBridge(FakeLeWM(),FakeTorch,'artificial-cpu');owned=[]
        selector=CommittedFeedbackSelector(JointModel(996,212,192),OrdinaryModel(996,212,192))
        ref=c.roles()['mechanism_evaluation'][0];trees=[];sizes=[]
        with tempfile.TemporaryDirectory() as d:
            for arm in c.CONTROLS:
                a,m=evaluate(factory(backend,owned=owned),backend.rollout,ref,arm,selector,settings=dict(population=6,elites=2,rounds=1))
                m['role']='mechanism_evaluation';check=verify_arrays(a,m,role_map=c.roles());self.assertTrue(check['passed'])
                self.assertEqual(m['branches'][0]['steps'],150)
                root=Path(d)/arm;root.mkdir();save(root,a,m);_,_,again=load_verify(root,role_map=c.roles());self.assertEqual(check,again)
                c.write(root/'HARDWARE.json',{'artificial':True});c.write(root/'TECHNICAL.json',{'artificial':True,'padding':'x'*20000});c.seal(root,{'artificial':True})
                self.assertLess(c.bytes_in(root),2000000);sizes.append(c.bytes_in(root))
                if arm!='early-replan':trees.append(arrays_digest(a,[k for k in a if k.startswith('tree/')]))
        self.assertEqual(len(set(trees)),1);self.assertEqual(len(owned),6);self.assertTrue(all(w.closed for w in owned))
        RESULTS['physical_interface']=dict(artificial_only=True,arms=6,fresh_worlds=6,full150steps=True,max_saved_worker_with_seal=max(sizes),search_fixture=dict(population=6,elites=2,rounds=1))
        # Exact worst-shape serialization including four prefixes/four suffixes; no
        # additional controller efficacy execution or invented final-source outcome.
        if 'tree/count' not in a:
            a.update({'tree/count':np.full(4,4,dtype=np.int64),'tree/baseline':np.zeros((15,2)),
                      'tree/prefix':np.zeros((4,5,2)),'tree/suffix':np.zeros((4,4,10,2)),
                      'tree/predicted_prefix':np.zeros((4,192)),'tree/predicted_terminal':np.zeros((4,4,192))})
        b=io.BytesIO();np.savez(b,**a)
        worst=b.tell()+100000+len(c.canonical(m));self.assertLess(worst,2000000)
        RESULTS['physical_interface']['max4x4_150step_serialization_bound_including_metadata_seal_reserve']=worst
    def test_16_four_explicit_seed_192_update_synthetic_fits(self):
        from artificial import d192_fixture
        fit=d192_fixture('fit',c.roles()['fit']);val=d192_fixture('validation',c.roles()['validation']);pre=Preprocessing.fit(fit)
        receipts=[]
        with tempfile.TemporaryDirectory() as d:
            for spec in c.grid()[:4]:
                out=Path(d)/spec['key'];out.mkdir();r=models.fit_explicit(spec,fit,val,pre,out,c.roles())
                self.assertEqual(r['seed'],spec['seed']);self.assertEqual(r['updates'],192);self.assertEqual([x['update'] for x in r['trace']],list(range(1,193)))
                c.seal(out,spec);self.assertLess(c.bytes_in(out),spec['byte_cap'])
                with np.load(out/(spec['kind']+'.npz'),allow_pickle=False) as z:metadata=c.json.loads(str(z['metadata']))
                self.assertEqual(metadata['seed'],spec['seed']);receipts.append(dict(key=spec['key'],seed=r['seed'],updates=r['updates'],bytes=c.bytes_in(out)))
            root=Path(d);reused=root/'reused';reused.mkdir()
            oldjoint=JointModel(996,212,192,seed=94011,preprocessing=pre);oldjoint.save(reused/'joint.npz')
            oldordinary=OrdinaryModel(996,212,192,seed=94012,preprocessing=pre)
            with (reused/'ordinary.npz').open('xb') as f:
                np.savez(f,metadata=np.array(c.json.dumps(dict(kind='ACV0-ordinary',preprocessing='joint.npz',dims=oldordinary.net.dims,seed=94012))),**{f'p{i}':p for i,p in enumerate(oldordinary.params)})
            c.write(reused/'PREPROCESSING.json',models.pre_record(pre))
            for kind,seed in zip(('JOINT','ORDINARY'),(94011,94012)):c.write(reused/('ORIGINAL-'+kind+'-FIT.json'),dict(seed=seed,updates=192,artificial_metadata=True))
            bindings={'files':{p.name:dict(bytes=p.stat().st_size,sha256=c.sha(p)) for p in reused.iterdir()}}
            c.seal(reused,dict(artificial=True,reuse_not_refit=True));real_read=c.read
            def fixture_read(path):return bindings if Path(path)==c.ROOT/'MODEL-REUSE.json' else real_read(path)
            with patch.object(c,'read',side_effect=fixture_read):
                models.freeze(root,'artificial');frozen=models.check_freeze(root,'artificial');self.assertEqual(len(frozen['models']),6)
                self.assertEqual(sum(x['reused'] for x in frozen['models'].values()),2)
                for pair,seeds in enumerate(models.PAIRS):
                    j,o=models.load_pair(types.SimpleNamespace(run=root,approval={'package_sha256':'artificial'}),pair)
                    self.assertEqual((j.seed,o.seed),seeds)
                with (reused/'joint.npz').open('ab') as f:f.write(b'corruption')
                with self.assertRaises(ValueError):models.check_freeze(root,'artificial')
        RESULTS['synthetic_optimizer']=receipts

if __name__=='__main__':
    tested={p.name:c.sha(p) for p in list(c.ROOT.glob('*.py'))+list(c.ROOT.glob('*.sh'))}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if result.wasSuccessful():
        name=sys.argv[1] if len(sys.argv)>1 else 'TEST-RECEIPT.json'
        c.require(all(c.sha(c.ROOT/n)==h for n,h in tested.items()),'Test source changed during suite')
        c.write(c.ROOT/name,dict(tests=result.testsRun,passed=True,tested_sources=tested,research_fitting=False,physics=False,lewm_forward=False,new_payload_access=False,**RESULTS))
    sys.exit(0 if result.wasSuccessful() else 1)
