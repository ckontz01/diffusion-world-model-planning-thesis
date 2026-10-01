"""Artificial EGL/routing, unique-supplier, resource and finalization regression tests."""
import copy,inspect,json,os,tempfile,types,unittest,importlib.util
from pathlib import Path
from unittest.mock import patch
from dtv_success_cost.common import *
from dtv_success_cost import campaign as old,worker as oldworker,analysis as oldanalysis,preserve as oldpreserve
from dtv_success_cost_r1.test_recovery import Recovery as R1Tests
from dtv_success_cost_r2 import campaign,common,render,worker,accept,analysis_entry,preserve

class Recovery(unittest.TestCase):
    def test_actual_transport_scripts_compile_before_any_remote_write(self):
        path=common.HERE/'transport.py'
        spec=importlib.util.spec_from_file_location('r2transport',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for body in (module.STAGE,module.LAUNCH,module.OBSERVE):
            compile(module.BASE.replace('IDENTITY_PLACEHOLDER','{}')+'\n'+body,str(path),'exec')
    def env(self):return dict(render.ENV,__EGL_VENDOR_LIBRARY_FILENAMES=str(render.VENDOR))
    def importer(self,wrong=False):
        class Context:
            def __init__(self,*a):raise AssertionError('no extra context allowed')
        Context.__module__='mujoco.egl'
        class Renderer:
            def __init__(self,*a):raise AssertionError('no extra renderer allowed')
        Renderer.__module__='dm_control._render.pyopengl.egl_renderer'
        class EGL:pass
        EGL.__module__='OpenGL.platform.egl'
        return lambda name:{'mujoco':types.SimpleNamespace(GLContext=Context),
            'dm_control._render':types.SimpleNamespace(BACKEND='glfw' if wrong else 'egl',Renderer=Renderer),
            'OpenGL.platform':types.SimpleNamespace(PLATFORM=EGL())}[name]
    def test_backend_import_guard_no_context_or_episode_and_sealed_evidence(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,self.env()):
            render.validate_backend(Path(d),self.importer());seal(Path(d),'fixture');read_seal(Path(d),'fixture')
            self.assertEqual(render.verify_evidence(d)['extra_contexts'],0)
    def test_bad_or_missing_headless_environment_rejected(self):
        from dtv_success_cost_r2.package import files
        self.assertIn('dtv_success_cost_r2/nvidia-egl.json',[r['path'] for r in files()])
        for key in self.env():
            e=self.env();del e[key]
            with self.assertRaises(RuntimeError):render.validate_environment(e)
        e=self.env();e['MUJOCO_GL']='glfw'
        with self.assertRaises(RuntimeError):render.validate_environment(e)
    def test_wrong_backend_rejected_before_any_output(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,self.env()):
            with self.assertRaises(RuntimeError):render.validate_backend(Path(d),self.importer(True))
            self.assertFalse(any(Path(d).iterdir()))
    def test_render_evidence_wrong_driver_or_platform_rejected(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,self.env()):
            v=render.validate_backend(Path(d),self.importer())
            v['vendor_sha256']='0'*64
            (Path(d)/'RENDER-BACKEND.json').write_text(json.dumps(v))
            with self.assertRaises(RuntimeError):render.verify_evidence(d)
    def test_scientific_gpu_body_byte_identical_except_two_declared_hooks(self):
        expected=inspect.getsource(oldworker.gpu_job).replace('authenticate(c,job,output.parent)','authenticate(c,job,run_namespace(c))')
        expected=expected.replace("    torch.set_num_threads(4);","    validate_backend(output);check()\n    torch.set_num_threads(4);",1)
        self.assertEqual(expected.strip(),inspect.getsource(worker.gpu_job).strip())
    def test_original_grid_site_limits_and_container_preserved(self):
        c=load(DOC/'BINDINGS.json');before=old.commands(c,Path('/old'),Path('/run'))[4:]
        after=campaign.commands(c,Path('/old'),Path('/r2'),Path('/run'),Path('/r1'))
        self.assertEqual(len(after),2878);self.assertEqual([x['id'] for x in after],[x['id'] for x in before])
        for a,b in zip(before,after):
            self.assertEqual({k:v for k,v in a.items() if k!='command'},{k:v for k,v in b.items() if k!='command'})
            self.assertEqual([x for x in a['command'][:-1] if not x.startswith(('--output=','--error='))],
                             [x for x in b['command'][:-1] if not x.startswith(('--output=','--error='))])
            self.assertIn('apptainer exec',b['command'][-1]);self.assertIn('--cleanenv',b['command'][-1])
            if b['gpu']:
                for k,v in self.env().items():self.assertIn(k+'='+v,b['command'][-1])
                self.assertIn('/run/recovery-r2/workers/'+b['id'],b['command'][-1])
                self.assertNotIn('--output /run/'+b['id']+' ',b['command'][-1])
                self.assertIn('dtv_success_cost_r2.worker',b['command'][-1]);self.assertIn('--nv',b['command'][-1])
            else:self.assertIn('dtv_success_cost_r2.analysis_entry',b['command'][-1])
    def test_complete_future_compute_and_storage_reservation(self):
        c=load(DOC/'BINDINGS.json');j=campaign.commands(c,Path('/old'),Path('/r2'),Path('/run'),Path('/r1'))
        self.assertEqual(campaign.reservations(c,dict(gpu=174,cpu=178),j),dict(gpu=863274,cpu=7378))
        with self.assertRaises(RuntimeError):campaign.reservations(c,dict(gpu=901,cpu=178),j)
        self.assertLess(sum(x['output_bytes']+x['log_bytes'] for x in j)+c['source_bytes']+c['control_bytes']+c['reused_model_bytes']+3000000,c['live_bytes'])
        self.assertLess(c['live_bytes']+c['source_bytes']+2*c['archive_bytes'],c['inclusive_bytes'])
    def test_new_workers_cannot_rerun_carried_success_or_use_failed_old_path(self):
        c=load(DOC/'BINDINGS.json');run=run_namespace(c)
        for j in c['jobs'][:4]:
            a=types.SimpleNamespace(job=j['id'],output=run/j['id'],child=False)
            with self.assertRaises(RuntimeError):worker.namespace(c,a)
        a=types.SimpleNamespace(job=c['jobs'][3]['id'],output=common.location(run)/'workers'/c['jobs'][3]['id'],child=False)
        worker.namespace(c,a)
    def test_restart_and_unexplained_evidence_rejected(self):
        c=load(DOC/'BINDINGS.json')
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);common.location(run).mkdir()
            campaign.begin(run,c)
            with self.assertRaises(RuntimeError):campaign.begin(run,c)
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);common.location(run).mkdir();(run/c['jobs'][4]['id']).mkdir()
            with self.assertRaises(RuntimeError):campaign.begin(run,c)
    def test_gate_exact_six_new_plus_three_carried_before_source2(self):
        gates=[campaign.gate_record(i) for i in range(2878)]
        self.assertEqual([i for i,g in enumerate(gates) if g],[5])
        self.assertEqual(gates[5]['included_workers'],9);self.assertFalse(gates[5]['scientific_selection'])
    def test_combined_2883_attempt_accounting_preserves_failed_charge(self):
        c,e=R1Tests().fixture_events()
        # Allocation numbers are synthetic and disjoint from historic failure.
        with patch.object(accept,'combined_events',return_value=e),patch.object(accept,'sha',return_value='a'*64):
            r=accept.accounting(Path('/fixture'),c,True)
        self.assertEqual(r['unique_tasks'],2882);self.assertEqual(r['actual_attempts'],2883)
        self.assertEqual(r['gpu_allocation_seconds'],2899);self.assertEqual(r['failed_gpu_allocation_seconds'],19)
        self.assertIn('312924',[x['allocation_id'] for x in r['actual_allocations']])
    def test_actual_failure_accounted_toward_cap_not_only_successes(self):
        c,e=R1Tests().fixture_events();c=dict(c,gpu_seconds=2898)
        with patch.object(accept,'combined_events',return_value=e),patch.object(accept,'sha',return_value='a'*64):
            with self.assertRaisesRegex(RuntimeError,'cumulative'):accept.accounting(Path('/fixture'),c,True)
    def test_output_mapping_old_success_and_exclusive_replacement(self):
        c=load(DOC/'BINDINGS.json');run=Path('/fixture')
        self.assertEqual(common.output_root(run,c['jobs'][0]),run)
        self.assertEqual(common.output_root(run,c['jobs'][3]),common.location(run)/'workers')
    def test_new_unknown_stop_rejected_without_ignoring_history(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);common.location(run).mkdir();write(common.location(run)/'STOP-R2.json',{})
            with self.assertRaisesRegex(RuntimeError,'unresolved'):common.verify_resolution(run,{})
    def test_actual_analysis_and_archive_use_r2_acceptance_not_obsolete_lineage(self):
        self.assertIs(analysis_entry.analyze,oldanalysis.analyze)
        self.assertIn('output_root(run,j)',inspect.getsource(analysis_entry.analysis))
        self.assertIn('dtv_success_cost_r2.accept',inspect.getsource(preserve.archive))
        expected=inspect.getsource(oldpreserve.archive).replace('dtv_success_cost.accept','dtv_success_cost_r2.accept')
        self.assertEqual(expected.strip(),inspect.getsource(preserve.archive).strip())
    def test_archive_root_coverage_includes_original_failure_and_all_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);run=p/'run'
            for name in ['STOP.json','recovery-r1/STOP-R1.json','reacher-4374-6101/FAILURE.json',
                         'recovery-r2/STOP-RESOLUTION.json','recovery-r2/workers/fixture/RENDER-BACKEND.json','recovery-r2/source/adapter.py']:
                path=run/name;path.parent.mkdir(parents=True,exist_ok=True);write(path,{})
            rows=oldpreserve.inventory({'run':run});info=preserve.make_archive(p/'final.tar',rows)
            self.assertEqual(oldpreserve.verify_archive(p/'final.tar',rows),6);self.assertEqual(info['sha256'],sha(p/'final.tar'))
    def test_false_recovery_approval_cannot_launch(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'disabled.json';write(path,dict(study='DTV-EFF1-R2',execute=False))
            with self.assertRaisesRegex(RuntimeError,'disabled'):common.recovery_gate(path)
if __name__=='__main__':unittest.main()
