"""Focused real saved-authentication/acceptance paths; artificial dependencies only."""
import common as c
import contextlib
import copy
import io
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
import acceptance,analysis,dispatch,models,prefix_coupling,worker
import bridge,episodes,hardware,verify
from artificial import FakeLeWM,FakeTorch,factory
from model import JointModel,OrdinaryModel
from test_runtime import row,Unit,Orchestration

RESULTS={}

@contextlib.contextmanager
def fixture(success_at=None):
    with tempfile.TemporaryDirectory() as directory:
        run=Path(directory);(run/'submissions').mkdir();(run/'logs').mkdir()
        c.write(run/'ALL-MODELS-FROZEN.json',dict(artificial=True))
        ref=c.roles()['mechanism_evaluation'][0];initial=np.zeros(7);goal=np.array([100.,100.,100.,100.,0,0,0])
        rp=run/'artificial-reference.npz';np.savez(rp,initial_request=initial,states=np.tile(goal,(76,1)))
        binding=dict(file=str(rp),sha256=c.sha(rp),index=ref,source_key='artificial-only',environment_seed=94031)
        auth=c.Authorization.__new__(c.Authorization)
        auth.run=run;auth.approval={'package_sha256':'artificial'};auth.approval_sha='artificial';auth.inputs={'references':{str(ref):binding}}
        owned=[];backends=[];called=[];real_evaluate=episodes.evaluate;real_reader=verify.load_verify
        def loader(_):
            backend=bridge.LeWMBridge(FakeLeWM(),FakeTorch,'artificial-cpu')
            backend.frozen_hash='artificial';backend.fingerprint=lambda:'artificial';backends.append(backend);return backend
        def source(aa,index,role,backend):
            # REAL capability.reference hashes only the temporary artificial NPZ.
            self_ref=aa.reference(index,role)
            return factory(backend,success_at=success_at,owned=owned),self_ref,dict(state=initial,goal_state=goal)
        def pair(*args):
            joint=JointModel(996,212,192);ordinary=OrdinaryModel(996,212,192)
            for model in (joint,ordinary):
                for param in model.params:param[:]=0
            return joint,ordinary
        def gpu(_,writer):
            value=dict(hostname='gpu09.cluster',slurm_job_id=os.environ['SLURM_JOB_ID'],accepted=True,query_status='complete',cuda_available=True,visible_device_count=1,device_name='NVIDIA RTX 6000 Ada Generation',artificial=True)
            writer(value);return value
        def evaluate(*args,**kwargs):return real_evaluate(*args,**kwargs,settings=dict(population=6,elites=2,rounds=1))
        def reader(path,**kwargs):
            c.require(type(kwargs.get('authorization')) is c.Authorization,'Production reader lost authorization')
            result=real_reader(path,**kwargs);called.append(str(path));return result
        def init(self,*args):self.__dict__.update(auth.__dict__)
        fake_torch=types.SimpleNamespace(set_num_threads=lambda n:None,cuda=types.SimpleNamespace(reset_peak_memory_stats=lambda:None,max_memory_allocated=lambda:0,max_memory_reserved=lambda:0))
        with contextlib.ExitStack() as stack:
            for target,kwargs in [(patch.object(c.Authorization,'__init__',init),{}),(patch.object(c.Authorization,'runtime',lambda self:None),{}),
              (patch.object(models,'check_freeze',return_value={'artificial':True}),{}),(patch.object(models,'load_pair',side_effect=pair),{}),
              (patch.object(bridge,'load_backend',side_effect=loader),{}),(patch.object(bridge,'source_factory',side_effect=source),{}),
              (patch.object(hardware,'verify_device',side_effect=gpu),{}),(patch.object(episodes,'evaluate',side_effect=evaluate),{}),
              (patch.object(verify,'load_verify',side_effect=reader),{}),(patch.object(worker.signal,'SIGALRM',14,create=True),{}),
              (patch.object(worker.signal,'alarm',lambda n:None,create=True),{}),(patch.object(worker.signal,'signal',lambda *a:None),{}),
              (patch.dict(sys.modules,{'torch':fake_torch,'resource':types.SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda n:types.SimpleNamespace(ru_maxrss=65536))}),{}),
              (patch.dict(os.environ,SLURM_CPUS_PER_TASK='4',SLURM_JOB_NODELIST='gpu09'),{})]:stack.enter_context(target)
            yield types.SimpleNamespace(run=run,auth=auth,reference=ref,binding=binding,owned=owned,reader_calls=called,real_reader=real_reader)

def execute_one(f,spec,job='42'):
    c.write(f.run/'submissions'/(spec['key']+'.json'),dict(job=job,spec=spec,package='artificial'))
    for suffix in ('.slurm.out','.slurm.err','.out','.err'):(f.run/'logs'/(spec['key']+suffix)).touch()
    with patch.dict(os.environ,SLURM_JOB_ID=job),patch.object(sys,'argv',['worker.py','--approval','unused-artificial','--run',str(f.run),'--task',spec['key']]):worker.main()
    accepted=acceptance.worker(f.run,spec,row(spec,job),'artificial','artificial')
    a,m,check=f.real_reader(f.run/spec['key'],role_map=c.roles(),authorization=f.auth)
    return a,m,c.read(f.run/spec['key']/'TECHNICAL.json'),accepted

def saved_clone(f,spec,a,m,technical,name=None):
    parent=f.run/name if name else f.run
    if name:parent.mkdir();(parent/'logs').mkdir()
    root=parent/spec['key'];root.mkdir()
    m=copy.deepcopy(m);m.update(control=spec['control'],pair=spec['pair'],task=spec['key']);m['branches'][0]['mode']=spec['control']
    episodes.save(root,a,m)
    _,_,check=f.real_reader(root,role_map=c.roles(),authorization=f.auth)
    t=copy.deepcopy(technical);t.update(spec=spec,episode_identity=[spec['reference'],spec['pair'],spec['control']],checks={k:v for k,v in check.items() if k!='successes'},prefix_coupling=prefix_coupling.technical(a,m))
    c.write(root/'HARDWARE.json',t['hardware']);c.write(root/'TECHNICAL.json',t);c.seal(root,spec)
    for suffix in ('.slurm.out','.slurm.err','.out','.err'):(parent/'logs'/(spec['key']+suffix)).touch()
    acceptance.worker(parent,spec,row(spec),'artificial','artificial')
    return root,t

class Correction(unittest.TestCase):
    def test_01_actual_cpu_gpu_command_vectors(self):
        vectors=[]
        for spec in (c.grid()[0],next(j for j in c.grid() if j['gpu'])):
            run=Path('/artificial/run');approval=Path('/artificial/approval.json')
            cmd=dispatch.command(spec,approval,run);i=next(i for i,x in enumerate(cmd[1:],1) if not x.startswith('-'))
            self.assertEqual(cmd[i],str(c.ROOT/'run_worker.sh'));self.assertNotIn('/bin/bash',cmd)
            self.assertTrue(Path(cmd[i]).read_bytes().startswith(b'#!/bin/bash\n'))
            self.assertEqual(cmd[i+1:],[str(c.ROOT),str(approval),str(run),spec['key'],str(spec['gpu'])])
            # Compare every generated resource/logging option to the actual old function.
            import ast
            src=(c.ROOT.parent/'runtime-v1/dispatch.py').read_text();node=next(x for x in ast.parse(src).body if isinstance(x,ast.FunctionDef) and x.name=='command');ns={'c':c}
            exec(compile(ast.Module(body=[node],type_ignores=[]),'old-command','exec'),ns)
            before=ns['command'](spec,approval,run);self.assertEqual(before[:i],cmd[:i]);self.assertEqual(before[i+1:],cmd[i:])
            vectors.append(dict(gpu=spec['gpu'],argv=cmd,script_sha256=c.sha(cmd[i]),five_arguments=cmd[i+1:],options_unchanged=True))
        RESULTS['command_vectors']=vectors

    def test_02_six_actual_worker_saved_reader_seal_acceptance(self):
        receipts=[];negative=[]
        with fixture() as f:
            for arm in c.CONTROLS:
                spec=next(j for j in c.grid() if j['stage']=='evaluation' and j['reference']==f.reference and j['control']==arm)
                a,m,t,accepted=execute_one(f,spec)
                self.assertEqual(m['initial_sha256'],bridge.array_hash(a['requested_initial']));self.assertEqual(m['goal_sha256'],bridge.array_hash(a['goal_state']))
                size=c.bytes_in(f.run/spec['key']);self.assertLessEqual(size,spec['byte_cap'])
                receipts.append(dict(control=arm,complete_bytes=size,readback_authorization_type='common.Authorization',accepted=True,seal=accepted['seal'],prefix=t['prefix_coupling']))
                mutations={
                    'absent_initial_hash':lambda aa,mm:mm.pop('initial_sha256'),
                    'absent_goal_hash':lambda aa,mm:mm.pop('goal_sha256'),
                    'wrong_initial_hash':lambda aa,mm:mm.update(initial_sha256='0'*64),
                    'wrong_goal_hash':lambda aa,mm:mm.update(goal_sha256='0'*64),
                    'wrong_reference_binding':lambda aa,mm:mm['reference_identity'].update(source_key='wrong'),
                    'changed_initial_array':lambda aa,mm:aa['requested_initial'].__setitem__(0,1.),
                    'changed_goal_array':lambda aa,mm:aa['goal_state'].__setitem__(0,101.)}
                for label,change in mutations.items():
                    bad={k:v.copy() for k,v in a.items()};meta=copy.deepcopy(m);change(bad,meta)
                    root=f.run/(arm+'-'+label);root.mkdir();episodes.save(root,bad,meta)
                    with self.assertRaises((KeyError,ValueError,AssertionError)):f.real_reader(root,role_map=c.roles(),authorization=f.auth)
                    negative.append(dict(control=arm,case=label,rejected=True))
            self.assertEqual(len(f.reader_calls),6);self.assertEqual(len(f.owned),6);self.assertTrue(all(w.closed for w in f.owned))
            # Shape/serialization only, not another episode or efficacy sweep.
            a.update({'tree/count':np.full(4,4,dtype=np.int64),'tree/baseline':np.zeros((15,2)),
                      'tree/prefix':np.zeros((4,5,2)),'tree/suffix':np.zeros((4,4,10,2)),
                      'tree/predicted_prefix':np.zeros((4,192)),'tree/predicted_terminal':np.zeros((4,4,192))})
            stream=io.BytesIO();np.savez(stream,**a);bound=stream.tell()+len(c.canonical(m))+100000
            self.assertLess(bound,2000000)
        RESULTS['authenticated_reader']=dict(controls=receipts,rejections=negative,production_worker_main=True,actual_save_reader_seal_acceptance=True,
          inherited_reader_unmodified=True,authentication_branch_not_mocked=True,fixture_search=dict(population=6,elites=2,rounds=1),max4x4_150step_complete_reservation=bound)

    def test_03_first16_gate_and_individually_valid_mismatch(self):
        checks=[]
        for field in ('b0/latent','b0/dynamics','b0/initial_proprio'):
            with fixture() as f:
                jobs=[j for j in c.grid() if j['stage']=='evaluation'][:16];a,m,t,_=execute_one(f,jobs[0])
                for spec in jobs[1:15]:saved_clone(f,spec,a,m,t)
                # Early path is actually executed, not a relabelled learned episode.
                early=next(j for j in jobs if j['control']=='early-replan');execute_one(f,early)
                acceptance.gate(f.run,c.grid());acceptance.check_gate(f.run)
                spec=jobs[1];bad={k:v.copy() for k,v in a.items()}
                if field=='b0/latent':bad[field][0,0]+=1
                elif field=='b0/dynamics':bad[field][0,4]+=1
                else:bad[field][0]+=1
                # Separate output directory and fresh seal, never edit accepted evidence.
                root,changed=saved_clone(f,spec,bad,m,t,name='individually-valid-'+str(len(checks)))
                f.real_reader(root,role_map=c.roles(),authorization=f.auth);c.verify_seal(root,spec)
                digests=[t['prefix_coupling'],changed['prefix_coupling']]
                with self.assertRaisesRegex(ValueError,'prefix history mismatch'):prefix_coupling.check_technical(digests)
                groups={};prefix_coupling.check_actual(groups,a,m)
                with self.assertRaisesRegex(ValueError,'prefix array mismatch'):prefix_coupling.check_actual(groups,bad,m)
                # Exercise the actual included gate with a separately sealed valid supplier.
                original_read=c.read;original_seal=c.verify_seal
                def read(path):return changed if Path(path)==f.run/spec['key']/'TECHNICAL.json' else original_read(path)
                def seal(path,identity=None):return original_seal(root,identity) if Path(path)==f.run/spec['key'] else original_seal(path,identity)
                with patch.object(c,'read',side_effect=read),patch.object(c,'verify_seal',side_effect=seal):
                    with self.assertRaisesRegex(ValueError,'prefix history mismatch'):acceptance.gate(f.run,c.grid())
                checks.append(dict(field=field,individually_authenticated_and_sealed=True,gate_rejected=True,independent_arrays_rejected=True))
        RESULTS['cross_episode_mismatches']=checks

    def test_04_different_prefix_and_postprefix_permitted(self):
        with fixture() as f:
            spec=next(j for j in c.grid() if j['gpu']);a,m,t,_=execute_one(f,spec)
            after={k:v.copy() for k,v in a.items()};after['b0/latent'][5,0]+=2
            verify.verify_arrays(after,m,role_map=c.roles());groups={};prefix_coupling.check_actual(groups,a,m);prefix_coupling.check_actual(groups,after,m)
            # A different valid prefix index/sequence from the same frozen tree,
            # executed with the existing artificial interface, not a new scenario.
            backend=bridge.load_backend(f.auth);from selector import CommittedFeedbackSelector
            selector=CommittedFeedbackSelector(*models.load_pair(f.auth,0));original=selector.select
            def choose(*args,**kwargs):
                decision=original(*args,**kwargs);return type(decision)(**dict(decision.__dict__,prefix=1))
            selector.select=choose
            other,meta=episodes.evaluate(factory(backend),backend.rollout,f.reference,'static',selector)
            meta.update(role='mechanism_evaluation',reference_identity=f.binding,initial_sha256=bridge.array_hash(other['requested_initial']),goal_sha256=bridge.array_hash(other['goal_state']))
            meta['branches'][0]['prefix_steps']=min(5,meta['branches'][0]['steps'])
            verify.verify_arrays(other,meta,role_map=c.roles());prefix_coupling.check_actual(groups,other,meta);self.assertEqual(len(groups),2)
            # Association uses exact planned actions, not an index label.
            relabel=copy.deepcopy(m);relabel['branches'][0]['prefix']=999
            self.assertEqual(prefix_coupling.technical(a,m),prefix_coupling.technical(a,relabel))
        RESULTS['non_false_rejections']=dict(postprefix_divergence_passed=True,different_selected_actions_passed=True,index_not_identity=True)

    def test_05_terminal_prefix_lengths_and_flags(self):
        samples=[]
        for end in (2,3,5):
            with fixture(success_at=end) as f:
                spec=next(j for j in c.grid() if j['gpu']);a,m,t,_=execute_one(f,spec)
                self.assertIsNone(m['branches'][0]['suffix']);self.assertEqual(m['branches'][0]['prefix_steps'],end)
                groups={};prefix_coupling.check_actual(groups,a,m);prefix_coupling.check_actual(groups,a,m)
                for bad_meta,bad_arrays in ((copy.deepcopy(m),a),(m,{k:v.copy() for k,v in a.items()})):
                    if bad_arrays is a:bad_meta['branches'][0]['prefix_steps']=end-1
                    else:bad_arrays['b0/flags'][-1,0]=False
                    with self.assertRaises(ValueError):prefix_coupling.technical(bad_arrays,bad_meta)
                samples.append((a,m,t['prefix_coupling']))
        with self.assertRaisesRegex(ValueError,'prefix history mismatch'):prefix_coupling.check_technical([x[2] for x in samples])
        groups={};prefix_coupling.check_actual(groups,*samples[0][:2])
        with self.assertRaisesRegex(ValueError,'prefix array mismatch'):prefix_coupling.check_actual(groups,*samples[1][:2])
        RESULTS['terminal_prefix']=dict(actual_lengths=[2,3,5],equal_passed=True,inconsistent_flags_or_lengths_rejected=True,no_missing_steps_fabricated=True)

    def test_06_every_source_analysis_actual_array_hook(self):
        with fixture() as f:
            spec=next(j for j in c.grid() if j['gpu']);a,m,t,_=execute_one(f,spec);visits=[];real_check=prefix_coupling.check_actual
            jobs={j['key']:j for j in c.grid() if j['gpu']};corrupt={'enabled':False}
            def reader(root,**kwargs):
                j=jobs[Path(root).name];meta=copy.deepcopy(m);meta.update(reference=j['reference'],pair=j['pair'],control=j['control']);meta['branches'][0]['mode']=j['control']
                data=a
                if corrupt['enabled'] and j['reference']==c.roles()['mechanism_evaluation'][-1] and j['pair']==1 and j['control']=='active':
                    data=dict(a);data['b0/latent']=a['b0/latent'].copy();data['b0/latent'][0,0]+=1
                return data,meta,{'passed':True}
            def actual(groups,aa,mm):visits.append(mm['reference']);return real_check(groups,aa,mm)
            original_read=c.read
            def read(path):return t if Path(path).name=='TECHNICAL.json' else original_read(path)
            original_sha=c.sha
            def sha(path):return '0'*64 if Path(path).name=='SEAL.json' else original_sha(path)
            sys.path.append(str(c.PROPOSAL));import planned_analysis
            fixed=dict(contrasts={name:dict(simultaneous_hoeffding95=[-1,1],per_seed_means=[0,0,0]) for name in ('active-minus-no_update','active-minus-committed_feedback')},artificial_axes_only=True)
            with patch.object(verify,'load_verify',side_effect=reader),patch.object(c,'verify_seal'),patch.object(c,'sha',side_effect=sha),patch.object(c,'read',side_effect=read),patch.object(acceptance,'check_gate'),patch.object(analysis,'check_actual',side_effect=actual),patch.object(planned_analysis,'analyze',return_value=fixed):
                out=f.run/'analysis-fixture';out.mkdir();result=analysis.analyze(f.auth,out)
                self.assertEqual(result['prefix_coupling_checked_episodes'],8192);self.assertEqual(len(visits),8192);self.assertEqual(set(visits),set(c.roles()['mechanism_evaluation']))
                corrupt['enabled']=True;out=f.run/'analysis-reject-fixture';out.mkdir()
                with self.assertRaisesRegex(ValueError,'prefix array mismatch'):analysis.analyze(f.auth,out)
        RESULTS['final_analysis_hook']=dict(sources=512,records=8192,actual_arrays_checked=True,last_source_mismatch_rejected=True,
            reader_and_seal_fixtures_for_full_grid=True,estimator_not_rerun=True,technical_digests_not_trusted=True)

def main():
    tested={p.name:c.sha(p) for p in list(c.ROOT.glob('*.py'))+list(c.ROOT.glob('*.sh'))}
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Correction)
    # Relevant unchanged orchestration/identity/resource regressions only. No fitting
    # or original artificial efficacy suite and no saved-data-analysis repetition.
    names=['test_01_false_approval_before_inputs_or_commands','test_02_frozen_old_code','test_03_all_original_decisions_unchanged',
      'test_04_new_prefix_static_baseline_feedback_and_terminal','test_05_grid_exact_axes_and_order','test_06_scheduler_strict_alias_and_id',
      'test_07_full_future_reservation_and_footprint','test_08_model_access_gate','test_10_archive_nested_roots_hidden_corruption',
      'test_11_syntax_and_no_gpu_preparation_import','test_17_pending_grace_is_finite','test_18_disabled_all_production_clis','test_19_native_windows_remote_posix_path_and_deadline']
    suite.addTests(Unit(name) for name in names);suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Orchestration))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        c.require(all(c.sha(c.ROOT/n)==h for n,h in tested.items()),'Tested source changed during focused run')
        import test_runtime
        c.write(c.ROOT/'TEST-CORRECTION.json',dict(passed=True,tests=result.testsRun,tested_sources=tested,reviewed_commit='bb181cc6b6c60770898afacdcca3fb9e604c90c1',
            research_inference=False,research_fitting=False,physics=False,slurm_submissions=0,gpu_allocations=0,new_reference_payload_access=False,
            focused_regressions=test_runtime.RESULTS,**RESULTS))
    sys.exit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':main()
