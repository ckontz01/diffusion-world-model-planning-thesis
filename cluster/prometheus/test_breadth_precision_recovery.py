"""Synthetic host-only recovery regressions: no real scheduler or scientific work."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import breadth_precision_contract as p
import candidate_value_contract as ct
import breadth_precision_recovery as r
import breadth_precision_backup_recovery as b


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);ct.json_write(path,value)
    def report(self,d,spec):
        value=dict(kind=spec['kind'],index=spec['index'],source_sha256=r.SOURCE_SHA,
            capsule_sha256=p.OLD_CAPSULE_SHA,technical_valid=True,protected_payload_reads=0,
            historical_decisions_changed=False,maxrss_bytes=1000)
        if spec['gpu']:value.update(reference=spec['reference'],horizon=spec['h'])
        self.write(d/'REPORT.json',value);ct.seal(d)
    def test_exact_remaining_counts_and_cost(self):
        grid=p.grid();remaining=grid[r.PREFIX:]
        self.assertEqual(len(remaining),348);self.assertEqual(remaining[0],p.task('breadth',94))
        self.assertEqual(sum(s['gpu'] for s in remaining),346)
        self.assertEqual(r.PRIOR_GPU+sum(s['seconds'] for s in remaining if s['gpu']),267792)
        self.assertTrue(p.reservation(r.PRIOR_GPU,0,307037221,remaining))
        self.assertFalse(p.reservation(p.CAPS['gpu_seconds'],0,0,remaining))
    def test_metadata_projection_not_outcomes(self):
        spec=p.task('breadth',94);d=self.root/'task';self.report(d,spec)
        meta=r.recovery_meta(d);r.check_meta(meta,spec)
        self.assertEqual(meta['horizon'],75)
        meta['horizon']=150
        with self.assertRaises(RuntimeError):r.check_meta(meta,spec)
    def test_metadata_rejects_protected_and_wrong_identity(self):
        spec=p.task('breadth',94);d=self.root/'task';self.report(d,spec)
        for key,value in [('protected_payload_reads',1),('technical_valid',False),('source_sha256','bad')]:
            meta=r.recovery_meta(d);meta[key]=value
            with self.assertRaises(RuntimeError):r.check_meta(meta,spec)
    def test_relocation_preserves_exact_bytes_and_exclusive_slot(self):
        run=self.root/'run';run.mkdir();expected={}
        for d in ('breadth-94','tmp-breadth-94'):
            (run/d).mkdir();(run/d/'opaque.bin').write_bytes(b'opaque-not-decoded')
            expected[d]=r.tree_inventory(run/d)
        r.relocate_interrupted(run,expected)
        for d in expected:
            self.assertFalse((run/d).exists())
            self.assertEqual(r.tree_inventory(run/'interrupted-attempt-301578'/d),expected[d])
        with self.assertRaises(RuntimeError):r.relocate_interrupted(run,expected)
    def test_relocation_rejects_scope_and_tampering(self):
        run=self.root/'run';run.mkdir()
        with self.assertRaises(RuntimeError):r.relocate_interrupted(run,{'breadth-93':{}})
        expected={}
        for d in ('breadth-94','tmp-breadth-94'):
            (run/d).mkdir();expected[d]={}
        (run/'breadth-94'/'unexpected').write_bytes(b'x')
        with self.assertRaises(RuntimeError):r.relocate_interrupted(run,expected)
        self.assertFalse((run/'interrupted-attempt-301578').exists())
    def test_overlay_rejects_extra_or_changed_files(self):
        (self.root/'a.py').write_text('pass\n')
        seal=self.root/'SOURCE-MANIFEST.sha256';seal.write_text(p.sha(self.root/'a.py')+'  a.py\n')
        digest=p.sha(seal);r.overlay_check(self.root,digest)
        (self.root/'extra').write_text('x')
        with self.assertRaises(RuntimeError):r.overlay_check(self.root,digest)
    def test_lease_is_scoped_fresh_and_headroom_checked(self):
        v=dict(approval_sha256='a',source_sha256=r.SOURCE_SHA,external_mount='/mnt/d',
               free_bytes=p.CAPS['backup_free_bytes'],utc=1000)
        self.assertTrue(r.lease_valid(v,'a',1100))
        for update in ({'utc':0},{'utc':1200},{'external_mount':'/'},{'free_bytes':1},{'source_sha256':'x'}):
            self.assertFalse(r.lease_valid(dict(v,**update),'a',1100))
        self.assertFalse(r.lease_valid(v,'b',1100))
    def test_probe_retries_only_transient_read(self):
        error=subprocess.CalledProcessError(255,['ssh'],stderr=b'Connection timed out')
        with patch.object(b.subprocess,'check_output',side_effect=[error,b'yes']) as call,patch.object(b.time,'sleep') as sleep:
            self.assertEqual(b.probe('test -f harmless'),b'yes');self.assertEqual(call.call_count,2);sleep.assert_called_once_with(5)
    def test_probe_retry_bound(self):
        error=subprocess.CalledProcessError(255,['ssh'],stderr=b'Connection reset')
        with patch.object(b.subprocess,'check_output',side_effect=error) as call,patch.object(b.time,'sleep'):
            with self.assertRaises(subprocess.CalledProcessError):b.probe('test -f harmless')
            self.assertEqual(call.call_count,3)
    def test_probe_permission_and_nonconnection_failures_stop_immediately(self):
        for code,message in [(255,b'Permission denied'),(255,b'Host key verification failed'),(1,b'Connection timed out')]:
            with patch.object(b.subprocess,'check_output',side_effect=subprocess.CalledProcessError(code,[],stderr=message)) as call:
                with self.assertRaises(subprocess.CalledProcessError):b.probe('test -f harmless')
                self.assertEqual(call.call_count,1)
    def test_control_write_is_never_retried(self):
        with patch.object(b.subprocess,'check_output',side_effect=subprocess.TimeoutExpired([],60)) as call:
            with self.assertRaises(subprocess.TimeoutExpired):b.write_control(Path('/x'),{},True)
            self.assertEqual(call.call_count,1)
    def test_old_scientific_worker_is_submission_target(self):
        cmd=r.arguments(p.task('breadth',94),Path('/frozen'),Path('/run'),Path('/approval'))
        self.assertIn('/frozen/cluster/prometheus/run_breadth_precision.sh',cmd)
        self.assertNotIn('breadth_precision_recovery.py',' '.join(cmd))

    def simulated_dispatch(self,fail_at=None,stale=False):
        run=self.root/'run';run.mkdir();control=self.root/'control';control.mkdir()
        overlay=self.root/'overlay';overlay.mkdir();(overlay/'controller.py').write_text('test fixture')
        source=self.root/'source';source.mkdir();approval=self.root/'old.json';self.write(approval,{})
        accounting=self.root/'account.json';self.write(accounting,{})
        (run/'DISPATCH.jsonl').write_text('original immutable ledger\n');(run/'DISPATCH-STOP.json').write_text('original stop\n')
        interrupted={}
        for d in ('breadth-94','tmp-breadth-94'):(run/d).mkdir();interrupted[d]={}
        prior=[dict(job=str(10000+i),task=s,state='COMPLETED',exit_code='0:0',seconds=1)
               for i,s in enumerate(p.grid()[:r.PREFIX])]
        prior.append(dict(job=r.FAILED_JOB,task=p.task('breadth',94),state='CANCELLED by 1201',exit_code='0:0',seconds=63))
        value=dict(researcher_approved=True,caps=p.CAPS,source_sha256=r.SOURCE_SHA,run=str(run),scientific_source=str(source),
            old_approval=str(approval),overlay=str(overlay),overlay_sha256='test',accounting=str(accounting),
            replacement_task=p.task('breadth',94),replacement_job=r.FAILED_JOB,remaining_tasks=p.grid()[r.PREFIX:],
            max_additional_replacement_attempts=1,automatic_job_retries=False,prior_jobs=prior,
            original_dispatch_sha256=p.sha(run/'DISPATCH.jsonl'),interrupted_files=interrupted)
        recovery=control/'RECOVERY-APPROVAL.json';self.write(recovery,value);digest=p.sha(recovery)
        self.write(control/'BACKUP-RECOVERY-READY.json',dict(approval_sha256=digest,failure_archive_sha256=r.FAILURE_ARCHIVE_SHA,
                                                          failure_backup_verified=True))
        submitted=[];order=[];real_write=ct.json_write
        def write(path,data):
            real_write(path,data)
            if Path(path).name.startswith('BACKUP-REQUEST-'):
                stage=data['stage'];order.append(('backup',stage))
                real_write(run/('BACKUP-ACK-'+stage+'.json'),dict(verified=True,request_sha256=p.sha(path),archive_sha256='mock'))
        def command(*args):
            if args[0]=='sbatch':
                spec=p.task(args[-2],int(args[-1]));submitted.append(spec);order.append(('submit',spec['kind'],spec['index']))
                job=str(400000+len(submitted));self.report(run/r.name(spec),spec);return job
            if args[0]=='sacct':
                state='FAILED' if fail_at==len(submitted) else 'COMPLETED'
                return '%s|%s|%s|1|'%(400000+len(submitted),state,'1:0' if state=='FAILED' else '0:0')
            if args[0]=='scancel':return ''
            raise AssertionError(args)
        def live(*args):
            if stale:raise RuntimeError('Backup unavailable')
        import breadth_precision_freeze as freeze
        with patch.object(r.p,'authorize',return_value=({},{})),patch.object(r,'overlay_check'),\
             patch.object(r,'prior_state',return_value=(prior,dict(directories=[r.name(s) for s in p.grid()[:r.PREFIX]]))),\
             patch.object(r,'wait_live',side_effect=live),patch.object(r,'__file__',str(overlay/'controller.py')),\
             patch.object(r,'OLD_APPROVAL_SHA',p.sha(approval)),patch.object(r,'command',side_effect=command),\
             patch.object(ct,'json_write',side_effect=write),patch.object(r.time,'sleep'),patch.object(freeze,'check_frozen',side_effect=lambda *a:order.append(('freeze',))):
            if fail_at or stale:
                with self.assertRaises(RuntimeError):r.dispatch(recovery,digest)
            else:
                r.dispatch(recovery,digest)
                with self.assertRaises((FileExistsError,RuntimeError)):r.dispatch(recovery,digest)
        self.assertEqual((run/'DISPATCH.jsonl').read_text(),'original immutable ledger\n')
        self.assertEqual((run/'DISPATCH-STOP.json').read_text(),'original stop\n')
        return run,submitted,order
    def test_full_mocked_grid_freezes_and_backs_models_before_evaluation(self):
        run,submitted,order=self.simulated_dispatch()
        self.assertEqual(submitted,p.grid()[r.PREFIX:])
        self.assertLess(order.index(('backup','train')),order.index(('submit','fit',0)))
        self.assertLess(order.index(('freeze',)),order.index(('backup','models')))
        self.assertLess(order.index(('backup','models')),order.index(('submit','evaluation',0)))
        self.assertLess(order.index(('backup','evaluation')),order.index(('submit','analyze',0)))
        summary=ct.json_read(run/'DISPATCH-FINAL.json')
        self.assertEqual(summary['allocation_attempts'],451);self.assertEqual(summary['prior_cancelled_seconds'],63)
        self.assertEqual(summary['gpu_seconds'],r.PRIOR_GPU+346);self.assertEqual(summary['cpu_wall_seconds'],2)
    def test_new_failure_stops_without_retry_or_later_submission(self):
        run,submitted,order=self.simulated_dispatch(fail_at=1)
        self.assertEqual(submitted,[p.task('breadth',94)])
        self.assertTrue((run/'RECOVERY-STOP.json').exists());self.assertFalse((run/'DISPATCH-FINAL.json').exists())
    def test_missing_backup_liveness_blocks_any_submission(self):
        run,submitted,order=self.simulated_dispatch(stale=True)
        self.assertEqual(submitted,[]);self.assertFalse((run/'RECOVERY-CLAIM.json').exists())


if __name__=='__main__':unittest.main()
