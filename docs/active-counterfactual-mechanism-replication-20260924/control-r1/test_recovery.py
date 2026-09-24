"""Artificial control-plane tests only; no model, reference, GPU or scheduler access."""
import r1 as r
import ast
import io
import sys
import tempfile
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import campaign_r1 as d
import acceptance_r1 as a
import scheduler
import controller
import supervise
import finalize

c=r.c
def row(j,job):
    return scheduler.parse('|'.join([str(job),'acvm1-'+j['key'],'COMPLETED','0:0','1','4','cpu=4,mem='+str(j['ram_gib'])+'G,node=1'+(',gres/gpu=1' if j['gpu'] else ''),'gpu09' if j['gpu'] else 'gpu02','a6000' if j['gpu'] else 'defq','normal-a6000' if j['gpu'] else 'normal','superworld',str(j['seconds']//60)]))

class Tests(unittest.TestCase):
    def test_disabled_before_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'false.json';c.write(p,dict(schema='ACVM1-recovery-r1',authorized=False,instruction='',binding={}))
            with patch.object(r,'binding',side_effect=AssertionError('premature input access')):
                with self.assertRaises(PermissionError):r.Context(p)

    def test_scientific_evaluation_function_identical(self):
        old=ast.parse((r.science_root/'worker.py').read_text());new=ast.parse((r.ROOT/'worker_r1.py').read_text())
        for name in ('evaluation','arrays_digest'):
            f=lambda tree:ast.dump(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name),include_attributes=False)
            self.assertEqual(f(old),f(new))
        c.source_check()

    def test_only_submission_and_recovery_technical_binding_changed(self):
        old=(r.science_root/'worker.py').read_text();new=(r.ROOT/'worker_r1.py').read_text()
        for unchanged in ("from models import fitting","from analysis import analyze","f=fitting(auth,spec,out)","extra=evaluation(auth,spec,out)","auth.runtime()","signal.alarm(spec['work_seconds'])"):
            self.assertIn(unchanged,old);self.assertIn(unchanged,new)
        self.assertIn("'submissions-r1'",new)
        self.assertNotIn("claim=auth.run/'submissions'/",new)

    def test_command_keeps_resources_and_retains_failed_logs(self):
        ctx=types.SimpleNamespace(worker_approval=Path(r.OLD_CONTROL)/'EXECUTION-APPROVAL.json',run=Path(r.RUN),control=Path('/artificial/control'))
        for spec in (c.grid()[0],c.grid()[1],next(j for j in c.grid() if j['gpu'])):
            old=d.command(spec,ctx.worker_approval,ctx.run);new=controller.command(ctx,spec)
            flags=lambda cmd:[x for x in cmd if x.startswith('--') and not x.startswith(('--output=','--error='))]
            self.assertEqual(flags(old),flags(new));self.assertEqual(new[-1],str(spec['gpu']))
            self.assertEqual(new[new.index(str(r.ROOT/'run_worker.sh'))+1:],[str(r.ROOT),str(ctx.control/'EXECUTION-APPROVAL.json'),str(c.ROOT),str(ctx.worker_approval),str(ctx.run),spec['key'],str(spec['gpu'])])
        self.assertTrue(str(r.slurm_log(ctx.run,'fit-pair1-joint','.slurm.err')).endswith('.r1.slurm.err'))
        self.assertTrue(str(r.slurm_log(ctx.run,'fit-pair1-joint','.err')).endswith('joint.err'))

    def test_bootstrap_no_host_python_and_exact_container(self):
        text=(r.ROOT/'run_worker.sh').read_text()
        self.assertNotIn('/usr/bin/python',text)
        self.assertIn('exec apptainer exec --cleanenv',text)
        self.assertIn('589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2',text)
        self.assertIn('SLURM_JOB_NODELIST=',text);self.assertIn('else visible=;',text)
        self.assertIn('"$runtime/bin/python" -B "$recovery/supervise.py"',text)

    def test_watchdog_preserves_failure_overflow_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for label,code,secs,expected in [('ok','print("artificial")',5,0),('fail','raise SystemExit(3)',5,3),('overflow','print("x"*9000)',5,1),('timeout','import time;time.sleep(2)',.1,1)]:
                files=[root/(label+s) for s in ('.out','.err')]
                result,errors=supervise.bounded_child([sys.executable,'-c',code],files,secs)
                self.assertEqual(result,expected);self.assertTrue(all(p.stat().st_size<=4096 for p in files))
                if label in ('overflow','timeout'):self.assertTrue(errors)

    def campaign(self,fault=None):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);run=root/'run';control=root/'control';run.mkdir();control.mkdir();(run/'submissions-r1').mkdir()
        auth=types.SimpleNamespace(run=run,approval={'package_sha256':'artificial'},approval_sha='artificial')
        flags={'reuse':False,'freeze':False,'gate':False};seen=[]
        class Mock:
            def submit(_,j):
                if fault=='ambiguous':raise ValueError('artificial ambiguous submission')
                if j['gpu']:
                    assert flags['freeze']
                    if len(seen)>=20:assert flags['gate']
                seen.append(j);return str(400000+len(seen))
            def terminal(_,job,j):
                rr=row(j,job)
                if fault=='failed':rr.update(state='FAILED',exit='1:0',seconds=3)
                return rr
        jobs=c.grid() if not fault else c.grid()[:1]
        def accept(j,rr):scheduler.allocation(j,rr);return dict(job=rr['job'],seal='artificial')
        args=dict(jobs=jobs,accept=accept,reuse=lambda:flags.update(reuse=True),freeze=lambda:flags.update(freeze=True),gate=lambda:flags.update(gate=True))
        if fault:
            with self.assertRaises(ValueError):d.campaign(auth,control,Mock(),**args)
        else:d.campaign(auth,control,Mock(),**args)
        with self.assertRaises(ValueError):d.campaign(auth,control,Mock(),**args)
        return auth,control,a.ledger(control,jobs,False),flags

    def test_actual8197_campaign_and8198_combined_finalization(self):
        auth,control,state,flags=self.campaign();self.assertTrue(all(flags.values()));self.assertEqual(len(state['accepted']),8197)
        self.assertEqual(len(list((auth.run/'submissions-r1').iterdir())),8197)
        self.assertEqual(sum(j['gpu'] for j in c.grid()),8192)
        ev=[j for j in c.grid() if j['gpu']];gate_time=(state['claimed'][ev[15]['key']]['unix']+state['claimed'][ev[16]['key']]['unix'])/2
        ctx=types.SimpleNamespace(auth=auth,run=auth.run,control=control,jobs=c.grid(),baseline=c.read(r.ROOT/'BASELINE.json'),binding={'manifest':'artificial'},approval_sha='artificial')
        rows=[e['row'] for e in state['terminal'].values()]+[ctx.baseline['failed_row']]
        real_read=c.read
        def read(path):
            if Path(path).name=='TECHNICAL.json':return dict(recovery_approval='artificial')
            return real_read(path)
        with patch.object(a,'worker',side_effect=lambda *args:dict(key=args[1]['key'])),patch('models.check_freeze',return_value={'unix':0}),patch.object(a,'check_gate',return_value={'unix':gate_time}),patch.object(c,'read',side_effect=read),patch.object(r,'read',side_effect=read):
            result=finalize.reconcile(ctx,rows);self.assertEqual(result['attempts'],8198);self.assertEqual(result['successful_tasks'],8197)
            with self.assertRaises(ValueError):finalize.reconcile(ctx,rows[:-1])
            bad=[dict(x,seconds=1) if x['job']=='304589' else x for x in rows]
            with self.assertRaises(ValueError):finalize.reconcile(ctx,bad)
            c.write(control/'STOP.json',dict(error='unresolved artificial new fault'))
            with self.assertRaises(ValueError):finalize.reconcile(ctx,rows)

    def test_failstop_ambiguous_and_charge(self):
        _,control,state,_=self.campaign('ambiguous');self.assertEqual(len(state['claimed']),1);self.assertFalse(state['submitted']);self.assertTrue((control/'STOP.json').exists())
        _,control,state,_=self.campaign('failed');self.assertEqual(state['cpu_seconds'],3);self.assertFalse(state['accepted']);self.assertTrue((control/'STOP.json').exists())

    def test_full_resource_caps_and_all_archive_roots(self):
        import storage
        f=storage.footprint(c.grid());self.assertEqual(d.reservation(c.grid(),{}),dict(gpu_seconds=2457600,cpu_stage_seconds=36000))
        self.assertLess(f['archive'],18500000000);self.assertLess(f['inclusive'],80000000000)
        text=(r.ROOT/'preserve_r1.py').read_text()
        self.assertIn('science_source=c.REPO,recovery_source=recovery.ROOT,original_control=ctx.old_control,recovery_control=control,run=auth.run',text)
        from preserve import inventory,verify_tar
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);roots={}
            for label in ('science_source','recovery_source','original_control','recovery_control','run'):
                p=root/label;p.mkdir();(p/'.hidden').write_bytes(label.encode());roots[label]=p
            items,paths=inventory(roots);tar=root/'all.tar'
            with tarfile.open(tar,'w') as t:
                for n,p in paths.items():t.add(p,arcname=n,recursive=False)
            self.assertEqual(verify_tar(tar,items)['members'],5)
            wrong=dict(items);wrong.pop(next(iter(wrong)))
            with self.assertRaises(ValueError):verify_tar(tar,wrong)

    def test_syntax_and_no_research_imports(self):
        for p in r.ROOT.glob('*.py'):ast.parse(p.read_text())
        self.assertNotIn('torch',sys.modules);self.assertNotIn('stable_worldmodel',sys.modules)

    def test_actual_worker_main_with_artificial_fit_and_claim(self):
        import worker_r1 as w
        import os
        spec=c.grid()[0]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'submissions-r1').mkdir()
            auth=types.SimpleNamespace(run=root,approval={'package_sha256':'artificial'},approval_sha='artificial-old',runtime=lambda:None)
            ctx=types.SimpleNamespace(auth=auth,worker_approval=Path('artificial-approval'),run=root,approval_sha='artificial-recovery')
            c.write(root/'submissions-r1'/(spec['key']+'.json'),dict(job='42',spec=spec,package='artificial'))
            fake_resource=types.SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda _:types.SimpleNamespace(ru_maxrss=1024))
            with patch.object(w.recovery,'Context',return_value=ctx),patch.dict(os.environ,{'ACVM_R1_APPROVAL':'artificial','SLURM_JOB_ID':'42','SLURM_CPUS_PER_TASK':'4','CUDA_VISIBLE_DEVICES':''}),patch.object(sys,'argv',['worker','--approval','artificial-approval','--run',str(root),'--task',spec['key']]),patch.object(w.signal,'SIGALRM',14,create=True),patch.object(w.signal,'alarm',create=True),patch.object(w.signal,'signal'),patch.dict(sys.modules,{'resource':fake_resource}),patch('models.fitting',return_value=dict(seed=94411,updates=192)) as fit:
                w.main();self.assertEqual(fit.call_count,1)
            t=c.read(root/spec['key']/'TECHNICAL.json');self.assertEqual(t['recovery_approval'],'artificial-recovery');self.assertEqual(t['job'],'42')
            c.verify_seal(root/spec['key'],spec)

    def test_actual_archive_builder_all_five_roots(self):
        import preserve_r1 as p
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);roots={}
            for label in ('science_source','recovery_source','original_control','recovery_control','run'):
                root=base/label;root.mkdir();(root/'.hidden').write_bytes(label.encode());roots[label]=root
            ctx=types.SimpleNamespace(old_control=roots['original_control'])
            auth=types.SimpleNamespace(run=roots['run'],approval={'package_sha256':'artificial'},approval_sha='artificial')
            acceptance=roots['recovery_control']/'FINAL-ACCEPTANCE.json'
            c.write(acceptance,dict(tasks=8197,episodes=8192,package='artificial',approval='artificial',run=str(auth.run),receipts=[]))
            with patch.object(p.recovery,'Context',return_value=ctx),patch.object(p.recovery,'baseline'),patch.object(p.recovery,'ROOT',roots['recovery_source']),patch.object(c,'REPO',roots['science_source']):
                request=p.archive(auth,roots['recovery_control'],acceptance)
            record=c.read(request)
            self.assertEqual({k.split('/')[0] for k in record['members']},set(roots))
            self.assertEqual(p.verify_tar(record['archive'],record['members']),record['archive_identity'])

if __name__=='__main__':
    tested={p.name:r.sha(p) for p in r.ROOT.glob('*') if p.suffix in ('.py','.sh')}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    if result.wasSuccessful():r.write(r.ROOT/'TEST-RECEIPT.json',dict(passed=True,tests=result.testsRun,tested_sources=tested,science_unchanged=True,mocked_scheduler=True,original_tasks=8197,total_attempts=8198,research_allocations=0,scientific_outcomes_read=False))
    sys.exit(0 if result.wasSuccessful() else 1)
