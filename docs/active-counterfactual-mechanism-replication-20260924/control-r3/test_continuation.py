"""Artificial R3 orchestration checks; no research model, payload or scheduler call."""
import r1 as r
import ast
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import campaign_r1 as d
import acceptance_r1 as a
import controller
import finalize
import scheduler

c=r.c
def row(spec,job):
    return scheduler.parse('|'.join([str(job),'acvm1-'+spec['key'],'COMPLETED','0:0','1','4','cpu=4,mem='+str(spec['ram_gib'])+'G,node=1'+(',gres/gpu=1' if spec['gpu'] else ''),'gpu09' if spec['gpu'] else 'gpu01','a6000' if spec['gpu'] else 'defq','normal-a6000' if spec['gpu'] else 'normal','superworld',str(spec['seconds']//60)]))

class Tests(unittest.TestCase):
    def test_original_scientific_functions_and_import_guard_retained(self):
        old=ast.parse((r.science_root/'worker.py').read_text());new=ast.parse((r.ROOT/'worker_r1.py').read_text())
        for name in ('evaluation','arrays_digest'):
            find=lambda tree:ast.dump(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name),include_attributes=False)
            self.assertEqual(find(old),find(new))
        self.assertIn('recovery.authenticated_imports()', (r.ROOT/'worker_r1.py').read_text())
        c.source_check()

    def test_disabled_before_input_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'false.json';c.write(p,dict(schema='ACVM1-recovery-r3',authorized=False,instruction='',binding={}))
            with patch.object(r,'binding',side_effect=AssertionError('premature access')):
                with self.assertRaises(PermissionError):r.Context(p)

    def test_full_remaining_grid_acceptance_timestamp_and_no_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'run';control=root/'control';run.mkdir();control.mkdir();(run/'submissions-r3').mkdir()
            auth=types.SimpleNamespace(run=run,approval={'package_sha256':'artificial'})
            jobs=c.grid()[1:];self.assertEqual(len(jobs),8196)
            self.assertEqual(d.reservation(jobs,{}),dict(gpu_seconds=2457600,cpu_stage_seconds=28819,prior_cpu_stage_seconds=19))
            flags={'freeze':False,'gate':False};seen=[]
            class Mock:
                def submit(_,spec):
                    if spec['gpu']:
                        assert flags['freeze']
                        if len(seen)>=19:assert flags['gate']
                    seen.append(spec);return str(500000+len(seen))
                def terminal(_,job,spec):return row(spec,job)
            d.campaign(auth,control,Mock(),jobs=jobs,accept=lambda spec,x:dict(key=spec['key'],job=x['job'],seal='artificial',unix=time.time()),reuse=lambda:None,freeze=lambda:flags.update(freeze=True),gate=lambda:flags.update(gate=True))
            state=a.ledger(control,jobs)
            self.assertEqual(len(state['accepted']),8196)
            self.assertEqual(len(list((run/'submissions-r3').iterdir())),8196)
            self.assertEqual(c.read(control/'COMPUTE-COMPLETE.json')['tasks'],8197)
            self.assertTrue(flags['freeze'] and flags['gate'])
            with self.assertRaises(ValueError):d.campaign(auth,control,Mock(),jobs=jobs)
            # Independent finalizer must account for the two failed historical
            # allocations and the carried R2 success without a second supplier.
            r2=root/'r2';r2.mkdir();c.write(r2/'EXECUTION-APPROVAL.json',dict(authorized=True))
            fit=run/'fit-pair1-joint';fit.mkdir()
            c.write(fit/'SEAL.json',dict(artificial=True))
            c.write(fit/'TECHNICAL.json',dict(recovery_approval=c.sha(r2/'EXECUTION-APPROVAL.json')))
            seal=c.sha(fit/'SEAL.json');technical=c.sha(fit/'TECHNICAL.json')
            c.write(control/'ACCEPTED-EXISTING.json',dict(key='fit-pair1-joint',job='304593',seal=seal,technical=technical,approval='artificial-r3',recomputed=False))
            c.write(run/'ALL-MODELS-FROZEN.json',dict(artificial=True))
            c.write(run/'TECHNICAL-TRANCHE-PASSED.json',dict(artificial=True))
            historical=c.json.loads(c.read(r.ROOT/'BASELINE-TRANSPORT.json')['stdout'])
            ctx=types.SimpleNamespace(run=run,control=control,r2_control=r2,jobs=c.grid(),approval_sha='artificial-r3',binding={'manifest':'artificial'},baseline=dict(historical,fit_seal_sha256=seal))
            rows=historical['rows']+[e['row'] for e in state['terminal'].values()]
            actual_read=r.read
            def synthetic_read(path):
                if Path(path).name=='TECHNICAL.json' and not Path(path).exists():return dict(recovery_approval='artificial-r3')
                return actual_read(path)
            with patch.object(c,'verify_seal'),patch.object(r,'read',side_effect=synthetic_read),patch.object(a,'worker',side_effect=lambda *args:dict(key=args[1]['key'])),patch.object(a,'check_gate',return_value={'unix':0}),patch('models.check_freeze',return_value={'unix':0}):
                result=finalize.reconcile(ctx,rows)
                self.assertEqual(result['attempts'],8199)
                self.assertEqual(result['successful_tasks'],8197)
                self.assertEqual(result['cpu_seconds'],23)
                with self.assertRaises(ValueError):finalize.reconcile(ctx,rows[:-1])

    def test_carry_exact_fit_without_recomputation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'run';fit=run/'fit-pair1-joint';fit.mkdir(parents=True);(run/'submissions-r2').mkdir();control=root/'control';control.mkdir();r2=root/'r2';r2.mkdir()
            spec=c.grid()[0];c.write(r2/'EXECUTION-APPROVAL.json',dict(authorized=True))
            c.write(run/'submissions-r2/fit-pair1-joint.json',dict(job='304593'))
            c.write(fit/'TECHNICAL.json',dict(passed=True,job='304593',seed=94411,updates=192,recovery_approval=c.sha(r2/'EXECUTION-APPROVAL.json')))
            c.write(fit/'FIT.json',dict(seed=94411,updates=192,trace=[0]*192))
            c.seal(fit,spec);seal=c.sha(fit/'SEAL.json')
            ctx=types.SimpleNamespace(run=run,control=control,jobs=c.grid(),r2_control=r2,approval_sha='new-approval',baseline={'fit_seal_sha256':seal})
            with patch.object(r,'ROOT',root):
                c.write(root/'BASELINE-TRANSPORT.json',dict(read_only=True))
                controller.accept_existing(ctx)
            receipt=c.read(control/'ACCEPTED-EXISTING.json')
            self.assertEqual(receipt['job'],'304593');self.assertFalse(receipt['recomputed'])
            self.assertEqual(c.sha(fit/'SEAL.json'),seal)
            with self.assertRaises(FileExistsError):controller.accept_existing(ctx)

    def test_new_worker_claim_and_original_resources(self):
        import worker_r1 as worker
        original=c.grid()[1];gpu=next(x for x in c.grid() if x['gpu'])
        for spec in (original,gpu):
            ctx=types.SimpleNamespace(worker_approval=Path(r.OLD_CONTROL)/'EXECUTION-APPROVAL.json',run=Path(r.RUN),control=Path('/artificial/control'))
            command=controller.command(ctx,spec)
            self.assertIn('--cpus-per-task=4',command)
            self.assertIn('--mem='+str(spec['ram_gib'])+'G',command)
            self.assertEqual(command[-1],str(spec['gpu']))
        self.assertIn("'submissions-r3'",(r.ROOT/'worker_r1.py').read_text())
        self.assertIn('ACVM_R3_APPROVAL', (r.ROOT/'run_worker.sh').read_text())
        self.assertIn('ACVM_R3_APPROVAL', (r.ROOT/'supervise.py').read_text())

    def test_nine_archive_roots_and_member_authentication(self):
        import preserve_r1 as preserve
        import tarfile
        labels=('science_source','r1_source','r2_source','r3_source','original_control','r1_control','r2_control','r3_control','run')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);roots={}
            for label in labels:
                path=base/label;path.mkdir();(path/'.hidden').write_bytes(label.encode());roots[label]=path
            ctx=types.SimpleNamespace(old_control=roots['original_control'],r1_control=roots['r1_control'],r2_control=roots['r2_control'])
            auth=types.SimpleNamespace(run=roots['run'],approval={'package_sha256':'artificial'},approval_sha='artificial')
            receipt=roots['r3_control']/'FINAL-ACCEPTANCE.json'
            c.write(receipt,dict(tasks=8197,episodes=8192,package='artificial',approval='artificial',run=str(auth.run),receipts=[]))
            with patch.object(preserve.recovery,'Context',return_value=ctx),patch.object(preserve.recovery,'baseline'),patch.object(preserve.recovery,'ROOT',roots['r3_source']),patch.object(preserve.recovery,'R1_SOURCE',roots['r1_source']),patch.object(preserve.recovery,'R2_SOURCE',roots['r2_source']),patch.object(c,'REPO',roots['science_source']):
                request=preserve.archive(auth,roots['r3_control'],receipt)
            content=c.read(request)
            self.assertEqual({x.split('/')[0] for x in content['members']},set(labels))
            self.assertEqual(preserve.verify_tar(content['archive'],content['members']),content['archive_identity'])
            missing=dict(content['members']);missing.pop(next(iter(missing)))
            with self.assertRaises(ValueError):preserve.verify_tar(content['archive'],missing)

if __name__=='__main__':
    start=time.monotonic();label='r3-integration-03'
    c.append(r.ROOT/'TEST-ATTEMPTS.jsonl',dict(label=label,state='started',unix=time.time()))
    tested={p.name:r.sha(p) for p in r.ROOT.glob('*') if p.suffix in ('.py','.sh')}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    c.append(r.ROOT/'TEST-ATTEMPTS.jsonl',dict(label=label,state='finished',unix=time.time(),wall_seconds=time.monotonic()-start,passed=result.wasSuccessful(),peak_job_memory_bytes=0))
    if result.wasSuccessful():r.write(r.ROOT/'TEST-RECEIPT.json',dict(passed=True,tests=result.testsRun,tested_sources=tested,science_unchanged=True,mocked_scheduler=True,remaining_tasks=8196,total_attempts=8199,research_allocations=0,scientific_outcomes_read=False))
    sys.exit(0 if result.wasSuccessful() else 1)
