"""Artificial numeric/interface/full-grid regression, never favorable outcomes."""
import inspect,tempfile,types,unittest,importlib.util
from pathlib import Path
from unittest.mock import patch
import numpy as np
from dtv_success_cost.common import *
from dtv_success_cost_r3 import native as r3native,worker as r3worker
from dtv_success_cost import analysis as oldanalysis
from dtv_success_cost_r4 import common,campaign,worker,native,accept,analysis_entry,preserve
from dtv_success_cost_r4.initialization import verify_pusht_initialization as check

class Recovery(unittest.TestCase):
    def source(self):return np.array([123.,234.,243.5,255.4,.665,-10.,1.2],dtype=np.float32)
    def test_original_bitwise_guard_rejects_artificial_one_ulp_roundtrip(self):
        s=self.source();a=s.astype(np.float64);a[3]=np.nextafter(a[3],np.inf)
        self.assertFalse(np.array_equal(a,s));self.assertTrue(check(a,s,[0,45])['source_precision_roundtrip'])
    def test_exact_original_initialization_retains_zero_error(self):
        s=self.source();self.assertEqual(check(s,s,[0,45])['max_absolute_error'],0.)
    def test_roundtrip_bound_is_below_independent_one_e_minus_twelve(self):
        s=self.source();a=s.astype(np.float64);a[3]+=2.842170943040401e-14
        c=check(a,s,[0,45]);self.assertLessEqual(max(c['bounds']),1e-12);self.assertEqual(c['block_position_errors'][0],0.)
    def test_genuine_sub_float32_position_change_rejected(self):
        s=self.source();a=s.astype(np.float64);a[2]+=1e-8
        self.assertTrue(np.array_equal(a.astype(np.float32),s))
        with self.assertRaisesRegex(RuntimeError,'bound'):check(a,s,[0,45])
    def test_changed_nonposition_fields_rejected_even_one_ulp(self):
        s=self.source()
        for i in (0,1,4,5,6):
            a=s.astype(np.float64);a[i]=np.nextafter(a[i],np.inf)
            with self.assertRaises(RuntimeError):check(a,s,[0,45])
    def test_geometry_and_nonfinite_and_shapes_rejected(self):
        s=self.source()
        for a,source,cog in [(s,s,[0,30]),(s[:6],s,[0,45]),(s,s.astype(np.int32),[0,45]),(s*np.nan,s,[0,45])]:
            with self.assertRaises(RuntimeError):check(a,source,cog)
    def test_no_state_setter_or_observation_rounding_in_fix(self):
        self.assertEqual(inspect.getsource(native.environment),inspect.getsource(r3native.environment))
        self.assertEqual(inspect.getsource(native.read_source),inspect.getsource(r3native.read_source))
        for name in ('action','step','evidence','native_success','decoder'):
            self.assertEqual(inspect.getsource(getattr(native.Adapter,name)),inspect.getsource(getattr(r3native.Adapter,name)))
        source=inspect.getsource(native.Adapter.reset)
        self.assertNotIn('set_state',source);self.assertNotIn('allclose(n._get_obs',source)
        self.assertIs(analysis_entry.analyze,oldanalysis.analyze)
    def test_exact_finite_remaining_grid_resources_and_namespace(self):
        c=load(DOC/'BINDINGS.json');jobs=campaign.commands(c,Path('/original'),Path('/r4'),Path('/run'),Path('/r1'),Path('/r2'),Path('/r3'))
        self.assertEqual(len(jobs),2854);self.assertEqual(sum(j['gpu'] for j in jobs),2853)
        self.assertEqual(jobs[0]['id'],'pusht-3819-6101');self.assertEqual(jobs[-1]['id'],'analysis')
        self.assertEqual(campaign.reservations(c,dict(gpu=1622,cpu=178),jobs),dict(gpu=857522,cpu=7378))
        self.assertEqual([j['id'] for j in jobs[:-1]],[j['id'] for j in c['jobs'][27:]])
        for j in jobs[:-1]:
            self.assertIn('MUJOCO_GL=egl',j['command'][-1]);self.assertIn('/run/recovery-r4/workers/'+j['id'],j['command'][-1]);self.assertIn('dtv_success_cost_r4.worker',j['command'][-1])
            self.assertEqual(j['wall_seconds'],300);self.assertIn('--no-requeue',j['command'])
    def test_full_future_cap_rejects_reset_or_exhaustion(self):
        c=load(DOC/'BINDINGS.json');jobs=campaign.commands(c,Path('/o'),Path('/r'),Path('/run'),Path('/r1'),Path('/r2'),Path('/r3'))
        with self.assertRaises(RuntimeError):campaign.reservations(c,dict(gpu=864000,cpu=178),jobs)
    def test_carried_success_namespace_is_closed(self):
        c=load(DOC/'BINDINGS.json');a=types.SimpleNamespace(job=c['jobs'][0]['id'],output=Path('/anything'),child=False)
        with self.assertRaises(RuntimeError):worker.namespace(c,a)
    def test_unknown_stop_and_disabled_approval_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);common.location(run).mkdir();write(common.location(run)/'STOP-R4.json',{})
            with self.assertRaisesRegex(RuntimeError,'unresolved'):common.verify_resolution(run,{})
            p=run/'approval.json';write(p,dict(study='DTV-EFF1-R4',execute=False))
            with self.assertRaisesRegex(RuntimeError,'disabled'):common.recovery_gate(p)
    def test_restart_never_repeats_successful_or_ambiguous_work(self):
        c=load(DOC/'BINDINGS.json')
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);common.location(run).mkdir();write(common.location(run)/'STARTED.json',{})
            with self.assertRaisesRegex(RuntimeError,'never repeat'):campaign.begin(run,c)
    def test_supplier_projection_excludes_failed_same_task(self):
        rows=[dict(event='submitted',task='a',allocation_id='1'),dict(event='terminal',task='a',allocation_id='1'),dict(event='submitted',task='b',allocation_id='2')]
        self.assertEqual(accept.supplier_events(rows,[dict(task='a',allocation_id='1')]),rows[:2])
    def test_actual_four_history_full_grid_and_all_three_failed_attempts(self):
        c=load(DOC/'BINDINGS.json');l=load(common.LINEAGE);early=load(common.prior.LINEAGE)['carried'];history=[[],[],[]];future=[]
        def rows(task,allocation,elapsed=1,state='COMPLETED'):
            cpu=task in ('analysis','preflight');res='cpu=4,mem=8G'+('' if cpu else ',gres/gpu=1');code='0:0' if state=='COMPLETED' else '1:0'
            return [dict(event='submission_intent',task=task),dict(event='submitted',task=task,allocation_id=allocation),dict(event='scheduler',allocation_id=allocation,returncode=0,stdout=f'{allocation}|dtveff1-{task}|{state}|{code}|{elapsed}|{res}|gpu09'),dict(event='terminal',task=task,allocation_id=allocation,state=state,exit=code,elapsed_seconds=elapsed),dict(event='accepted',task=task)]
        old=[dict(event='submission_intent',task='preflight'),dict(event='submission_response',task='preflight'),dict(event='submitted',task='preflight',allocation_id='312920'),dict(event='scheduler',allocation_id='312920')]
        for i,j in enumerate(c['jobs']):
            if i<27:
                supplier=early[i] if i<6 else l['carried'][i-6];which=i//3 if i<6 else 2
                history[which]+=rows(j['id'],supplier['allocation_id'],supplier['elapsed_seconds'])
                if i==8:history[2].append(dict(event='technical_tranche_passed',included_workers=9))
            else:future+=rows(j['id'],str(900000+i))
        history[0]+=rows('reacher-4374-6101','312924',19,'FAILED')[:-1];history[1]+=rows('cube-3506-6101','312928',19,'FAILED')[:-1];history[2]+=rows('pusht-3819-6101','312950',21,'FAILED')[:-1]
        future+=rows('analysis','999999')
        with patch.object(accept,'sha',return_value='a'*64),patch.object(campaign,'sha',return_value='a'*64):carry=campaign.carry_record(Path('/fixture'))
        real_load=accept.load
        def loader(p):return {} if str(p).endswith('EXECUTION-APPROVAL.json') else real_load(p)
        with patch.object(accept,'verify_resolution'),patch.object(accept,'authenticate_history',return_value=tuple(history)),patch.object(accept,'sha',return_value='a'*64),patch.object(campaign,'sha',return_value='a'*64),patch.object(accept,'events',side_effect=[old,[carry]+future]),patch.object(accept,'load',side_effect=loader):
            result=accept.accounting(Path('/fixture'),c,True)
        self.assertEqual(result['unique_tasks'],2882);self.assertEqual(result['actual_attempts'],2885);self.assertEqual(result['gpu_allocation_seconds'],1622+2853);self.assertEqual(result['failed_gpu_allocation_seconds'],59)
        self.assertEqual([result['actual_allocations'][i]['allocation_id'] for i in (4,8,30)],common.FAILED_IDS)
        self.assertEqual(sum(x['task']=='pusht-3819-6101' for x in result['allocations']),1)
    def test_actual_transport_compiles_and_current_archive_adapter(self):
        path=common.HERE/'transport.py';spec=importlib.util.spec_from_file_location('r4transport',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for body in (module.STAGE,module.LAUNCH,module.OBSERVE):compile(module.BASE.replace('IDENTITY_PLACEHOLDER','{}')+'\n'+body,str(path),'exec')
        self.assertIn('dtv_success_cost_r4.accept',inspect.getsource(preserve.archive))
        self.assertIn('r3source',module.BASE);self.assertIn('resolution_fields',module.STAGE)
    def test_actual_adapter_reset_records_certificate_without_changing_native_state(self):
        source=self.source();actual=source.astype(np.float64);actual[3]=np.nextafter(actual[3],np.inf)
        n=types.SimpleNamespace(_get_obs=lambda:actual,block=types.SimpleNamespace(center_of_gravity=(0,45)))
        a=native.Adapter.__new__(native.Adapter);a.task='pusht';a.source_data={'state':source};a.np=np;a._reset=lambda:None
        a.world=types.SimpleNamespace(envs=types.SimpleNamespace(unwrapped=types.SimpleNamespace(envs=[types.SimpleNamespace(unwrapped=n)])))
        a.torch=types.SimpleNamespace(cuda=types.SimpleNamespace(reset_peak_memory_stats=lambda:None))
        before=actual.copy();a.reset();self.assertTrue(np.array_equal(actual,before));self.assertGreater(a.initialization_roundtrip['max_absolute_error'],0.)
    def test_independent_acceptance_reconstructs_and_rejects_certificate_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'recovery-r4/workers';job=dict(id='artificial',task='pusht');out=root/job['id'];out.mkdir(parents=True)
            source=self.source();actual=source.astype(np.float64);actual[3]=np.nextafter(actual[3],np.inf)
            np.savez(out/'SOURCE-INPUT.npz',initial_state=source)
            episodes=[dict(config=config,initial=dict(current=actual.tolist())) for config in CONFIGS]
            for e in episodes:write(out/(e['config']+'.initialization.json'),check(actual,source,[0,45]))
            with patch.object(accept,'original_accept_worker',return_value=episodes):self.assertEqual(accept.accept_worker({},job,root),episodes)
            with patch.object(accept,'original_accept_worker',return_value=episodes),patch.object(accept,'load',return_value={}):
                with self.assertRaisesRegex(RuntimeError,'certificate'):accept.accept_worker({},job,root)
    def test_complete_certificate_footprint_and_exclusive_per_config_files(self):
        import json
        certificate=check(self.source(),self.source(),[0,45]);self.assertLess(len(json.dumps(certificate).encode()),512)
        body=inspect.getsource(worker.gpu_job)
        self.assertIn("write(output/(config+'.initialization.json')",body)
        self.assertEqual(len({config+'.initialization.json' for config in CONFIGS}),8)
        self.assertLess(2880*(1000000+100000)+100000000+20000000+428451336+40100000+1100000+5000000,4000000000)
        self.assertLess(4000000000+20000000+2*4200000000,13000000000)
    def test_package_exclusive_r4_namespace_and_all_history_closure_checks(self):
        from dtv_success_cost_r4 import package
        code=inspect.getsource(package.main)
        self.assertIn("suffix='dtv-success-cost-control-r4-",code)
        self.assertIn("('recovery-r1','recovery-r2','recovery-r3')",code)
if __name__=='__main__':unittest.main()
