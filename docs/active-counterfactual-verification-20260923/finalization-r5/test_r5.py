"""Synthetic metadata/transport/archive tests; no research execution."""
import ast,copy,hashlib,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import r5_core as r
old=r.load_r4()
from test_r4 import Fixture
import validation5 as v
import finalize5 as f
import transport5 as t

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();x=Fixture(cls.tmp.name)
        cls.stop_patch=patch.object(old,'STOP_SHA',x.stop_sha);cls.stop_patch.start()
        result,_,_=x.run_all()
        r.write(x.control/'STOP-R4.json',{'error':"ValueError('Live campaign allocation at finalization')",'automatic_retry':False})
        paths=dict(x.baseline['paths'],r4_source=str(old.ROOT),r4_control=str(x.control));inventory={}
        for label,root in paths.items():
            for p in Path(root).rglob('*'):
                if p.is_file():inventory[label+'/'+p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':r.sha(p)}
        base={'paths':paths,'inventory':inventory,'r4_controller':{'pid':99999999,'start_ticks':'0'},
            'successful_rows':result['jobs'],'allocations':r.read(x.control/'FINAL-SCHEDULER.json')['allocations']}
        control=Path(cls.tmp.name)/'new-r5';control.mkdir()
        ctx=NS(r4=x,baseline=base,control=control,run=x.run,jobs=x.jobs,approval_sha='synthetic-r5-authority',
            binding={'r4_stop_sha256':r.sha(x.control/'STOP-R4.json'),'baseline_sha256':r.digest(base),
                'control_manifest':'synthetic-r5-manifest','gpu_seconds':result['campaign_gpu_seconds'],'cpu_stage_seconds':result['campaign_cpu_stage_seconds']})
        x.recovery_context=ctx;cls.ctx=ctx;cls.result=result
        cls.raw='\n'.join('|'.join(row['raw_scheduler'])+'|00:00:00|' for row in base['allocations'])
    @classmethod
    def tearDownClass(cls):
        cls.stop_patch.stop();cls.tmp.cleanup()
    def scheduler(self,queue='',extra=''):
        return patch.object(subprocess,'run',side_effect=[NS(returncode=0,stdout=self.raw+extra,stderr=''),NS(returncode=0,stdout=queue,stderr='')])
    def test_01_frozen_old_validation_only_three_explicit_changes(self):
        text=(old.ROOT/'finalize4.py').read_text().split('def inventory(')[0]
        expected=text.replace('import r4_core as r','import r4_core as r\nfrom r5_core import guard').replace('r.verify_baseline(ctx);r.stop_guard(ctx)','r.verify_baseline(ctx);guard(ctx.recovery_context)').replace("snapshot=r.read(ctx.control/'FINAL-SCHEDULER.json')","snapshot=r.read(ctx.recovery_context.control/'FINAL-SCHEDULER.json')")
        self.assertEqual((r.ROOT/'validation5.py').read_text().strip(),expected.strip())
    def test_02_original_sources_and_python39(self):
        for folder in ('bindings-r1','control-r2','control-r3','control-r4'):
            root=r.ROOT.parent/folder
            for n,h in r.read(root/'SOURCE-MANIFEST.json')['files'].items():self.assertEqual(r.sha((r.REPO/n) if folder=='bindings-r1' else root/n),h)
        for p in r.ROOT.glob('*.py'):ast.parse(p.read_text(),feature_version=(3,9))
        for code in (t.BOOTSTRAP,t.STAGE,t.OPERATE):ast.parse(code,feature_version=(3,9))
    def test_03_exact339_340_and_all_charges(self):
        result=r.result_from_ledger(self.ctx)
        self.assertEqual(result,self.result);self.assertEqual(len(result['jobs']),339)
        self.assertEqual(result['campaign_allocations'],340)
        with patch.object(subprocess,'run',side_effect=AssertionError('No research/scheduler execution')):
            rows,checks=r.accept_existing(self.ctx)
        self.assertEqual(len(checks),339);self.assertEqual(rows,self.result['jobs'])
    def test_04_strict_queue_and_unknown_allocation_refusal(self):
        with patch.dict(os.environ,{'USER':'synthetic'}):
            for queue in ('304193|acv0-collect-fit-490|RUNNING','999999|acv0-unknown|COMPLETING'):
                with self.scheduler(queue):
                    with self.assertRaisesRegex(ValueError,'Live campaign'):r.reconcile(self.ctx)
            extra='\n999999|acv0-unknown|FAILED|1:0|1|4|cpu=4,gres/gpu=1,mem=24G,node=1|gpu09|a6000|normal-a6000|superworld|30|00:00:00|'
            with self.scheduler(extra=extra):
                with self.assertRaises(ValueError):r.reconcile(self.ctx)
    def test_05_empty_queue_and_exact_attempts(self):
        with patch.dict(os.environ,{'USER':'synthetic'}),self.scheduler():snap=r.reconcile(self.ctx)
        self.assertEqual(len(snap['allocations']),340);self.assertTrue(snap['no_live_campaign_jobs'])
    def test_06_changed_stop_and_old_bytes_refused(self):
        for p in (self.ctx.r4.control/'STOP-R4.json',self.ctx.run/self.ctx.jobs[-1]['key']/'SEAL.json'):
            raw=p.read_bytes()
            try:
                p.write_bytes(raw+b' ')
                with self.assertRaises(ValueError):r.guard(self.ctx)
            finally:p.write_bytes(raw)
    def test_07_unknown_stop_and_changed_charge_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad=copy.copy(self.ctx);bad.control=Path(tmp);r.write(bad.control/'STOP-R5.json',{'error':'new'})
            with self.assertRaises(ValueError):r.guard(bad)
        bad=copy.copy(self.ctx);bad.binding=dict(bad.binding,gpu_seconds=0)
        with self.assertRaises(ValueError):r.result_from_ledger(bad)
    def test_08_false_authority_and_no_submission_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'false.json';r.write(p,{'schema':'ACV0-finalization-only-r5','authorized':False,'instruction':'','binding':{}})
            with self.assertRaises(PermissionError):r.Context(p)
        for p in ('finalize5.py','r5_core.py'):
            text=(r.ROOT/p).read_text()
            self.assertNotIn('sbatch',text);self.assertNotIn('Popen',text);self.assertNotIn('requeue',text)
        self.assertFalse(hasattr(t,'LAUNCH'))
    def test_09_binary_envelope_and_bound(self):
        raw=bytes(range(256))*4096
        code='import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
        out=subprocess.run([sys.executable,'-B','-S','-c',t.BOOTSTRAP],input=t.envelope(code,raw,{}),capture_output=True)
        self.assertEqual(out.returncode,0,out.stderr);self.assertEqual(out.stdout.decode().strip(),hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):t.envelope(code,b'x'*8000000,{})
    def test_10_complete_accept_archive_verify_no_repeat(self):
        with patch.dict(os.environ,{'USER':'synthetic'}),self.scheduler(),patch.object(r,'storage',return_value={'synthetic':True}):
            result=f.finalize(self.ctx)
        self.assertEqual(result['successful_tasks'],339);self.assertEqual(result['attempts'],340)
        self.assertEqual(r.read(self.ctx.control/'COMBINED-CAMPAIGN.json')['new_r5_allocations'],0)
        self.assertTrue((self.ctx.r4.control/'STOP-R4.json').exists())
        with self.assertRaises(ValueError):f.finalize(self.ctx)
        with patch.object(r,'storage',return_value={'synthetic':True}):out=f.archive(self.ctx)
        request=r.read(self.ctx.run/'final-preservation/BACKUP-REQUEST.json')
        from preserve import verify_tar
        verify_tar(self.ctx.run/'final-preservation/final.tar',request['members'])
        self.assertEqual(out['members'],len(request['members']))
        for n in ('r4-control-records/STOP-R4.json','r5-control-records/STOP-RESOLUTION.json','run/STOP.json','r3-control-records/STOP-R3.json'):
            self.assertIn(n,request['members'])
        with patch.object(r,'storage',return_value={}):
            with self.assertRaises(ValueError):f.archive(self.ctx)
        r.guard(self.ctx)
        bad=dict(request['members']);name=next(iter(bad));bad[name]=dict(bad[name],sha256='0'*64)
        with self.assertRaises((ValueError,AssertionError)):verify_tar(self.ctx.run/'final-preservation/final.tar',bad)
    def test_11_storage_inclusive_r5(self):
        with patch.object(old,'storage',return_value={'source_control_models_analysis_including_r2_r4':1}):
            got=r.storage(self.ctx);self.assertEqual(got['all_source_control_models_analysis'],1+r.total(r.ROOT)+r.total(self.ctx.control))
        with patch.object(old,'storage',return_value={'source_control_models_analysis_including_r2_r4':500000000}):
            with self.assertRaises(ValueError):r.storage(self.ctx)

if __name__=='__main__':unittest.main(verbosity=2)
