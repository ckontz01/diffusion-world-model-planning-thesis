"""Synthetic second-recovery tests. No real jobs, physics, labels or model imports."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import breadth_precision_contract as p
import candidate_value_contract as ct
import breadth_precision_recovery2 as r
import breadth_precision_backup_recovery2 as b


class Recovery2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);ct.json_write(path,value)
    def report(self,d,spec):
        value=dict(kind=spec['kind'],index=spec['index'],source_sha256=r.SOURCE_SHA,
            capsule_sha256=p.OLD_CAPSULE_SHA,technical_valid=True,protected_payload_reads=0,
            historical_decisions_changed=False,maxrss_bytes=1000)
        if spec['gpu']: value.update(reference=spec['reference'],horizon=spec['h'])
        self.write(d/'REPORT.json',value);ct.seal(d)
    def lease(self):
        return dict(approval_sha256='approval',source_sha256=r.SOURCE_SHA,native_windows=True,
                    volume_id=r.VOLUME_ID,volume_label='THESIS_SSD',free_bytes=50_000_000_000,utc=1000)
    def test_exact_remainder_no_completed_retry_and_caps(self):
        rest=p.grid()[r.PREFIX:]
        self.assertEqual(len(rest),302);self.assertEqual(rest[0],p.task('breadth',140))
        self.assertEqual(sum(s['gpu'] for s in rest),300)
        self.assertEqual(r.PRIOR_GPU+sum(s['seconds'] for s in rest if s['gpu']),250404)
        self.assertTrue(p.reservation(r.PRIOR_GPU,0,500_000_000,rest))
        self.assertFalse(p.reservation(p.CAPS['gpu_seconds'],0,0,rest))
    def test_native_lease_identity_freshness_and_headroom(self):
        self.assertTrue(b.volume_valid(self.lease(),'approval',1090))
        for changes in ({'utc':999},{'utc':1100},{'volume_id':'wrong'},{'volume_label':'wrong'},
                        {'source_sha256':'x'},{'approval_sha256':'x'},{'free_bytes':39_999_999_999},
                        {'native_windows':False}):
            self.assertFalse(b.volume_valid(dict(self.lease(),**changes),'approval',1090))
    def test_no_windows_interop_and_independent_mount_free_checks(self):
        self.write(self.root/'NATIVE-VOLUME-LIVE.json',self.lease())
        destination=Path('/mnt/d/THESIS-BACKUPS')/p.VERSION/('run-'+r.SOURCE_SHA[:16])
        from collections import namedtuple
        disk=namedtuple('disk','free')
        with patch.object(b,'LOCAL_CONTROL',self.root),patch.object(b.time,'time',return_value=1030),\
             patch.object(b.subprocess,'check_output',return_value='/mnt/d') as call,\
             patch.object(b.shutil,'disk_usage',return_value=disk(45_000_000_000)):
            self.assertEqual(b.external_check(destination,'approval'),45_000_000_000)
            self.assertEqual(call.call_args[0][0][0],'findmnt')
            with patch.object(b.subprocess,'check_output',return_value='/'):
                with self.assertRaises(RuntimeError):b.external_check(destination,'approval')
            with patch.object(b.shutil,'disk_usage',return_value=disk(1)):
                with self.assertRaises(RuntimeError):b.external_check(destination,'approval')
            with self.assertRaises(RuntimeError):b.external_check(Path('/tmp/fallback'),'approval')
            self.write(self.root/'NATIVE-VOLUME-STOP.json',{})
            with self.assertRaises(RuntimeError):b.external_check(destination,'approval')
    def test_missing_native_lease_is_not_synthesized(self):
        destination=Path('/mnt/d/THESIS-BACKUPS')/p.VERSION/('run-'+r.SOURCE_SHA[:16])
        with patch.object(b,'LOCAL_CONTROL',self.root):
            with self.assertRaises(FileNotFoundError):b.external_check(destination,'approval')
    def test_old_worker_entrypoint_unchanged(self):
        cmd=r.arguments(p.task('breadth',140),Path('/frozen'),Path('/run'),Path('/approval'))
        self.assertIn('/frozen/cluster/prometheus/run_breadth_precision.sh',cmd)
    def test_closed_accounting_tamper_rejected(self):
        file=self.root/'account.json';self.write(file,{})
        with self.assertRaises(RuntimeError):r.prior_state(self.root,file)
    def test_native_script_has_no_network_execution_or_wsl(self):
        script=(Path(__file__).parent/'breadth_precision_volume_lease.ps1').read_text()
        self.assertIn('Get-Volume -DriveLetter D',script)
        self.assertIn('$volume.UniqueId -ne $expectedVolume',script)
        self.assertIn('[IO.FileMode]::CreateNew',script)
        self.assertIn('[IO.File]::Move',script)
        self.assertNotIn('powershell.exe',script)
        self.assertNotIn('ssh ',script)
        self.assertNotIn('sbatch',script)
        self.assertNotIn('Start-Process',script)

    def simulated_dispatch(self,fail_at=None,stale=False,stop_after=None):
        run=self.root/'run';run.mkdir();control=self.root/'control';control.mkdir()
        overlay=self.root/'overlay';overlay.mkdir();(overlay/'controller.py').write_text('test fixture')
        source=self.root/'source';source.mkdir();approval=self.root/'old.json';self.write(approval,{})
        accounting=self.root/'account.json';self.write(accounting,{})
        (run/'DISPATCH.jsonl').write_text('original immutable ledger\n');(run/'DISPATCH-STOP.json').write_text('original stop\n')
        (run/'RECOVERY-DISPATCH.jsonl').write_text('prior recovery ledger\\n')
        (run/'RECOVERY-STOP.json').write_text('prior recovery stop\\n')
        prior=[dict(job=str(10000+i),task=s,state='COMPLETED',exit_code='0:0',seconds=1)
               for i,s in enumerate(p.grid()[:r.PREFIX])]
        prior.append(dict(job='301578',task=p.task('breadth',94),state='CANCELLED by 1201',exit_code='0:0',seconds=63))
        value=dict(researcher_approved=True,caps=p.CAPS,source_sha256=r.SOURCE_SHA,run=str(run),scientific_source=str(source),
            old_approval=str(approval),overlay=str(overlay),overlay_sha256='test',accounting=str(accounting),
            completed_prefix=r.PREFIX,external_volume_id=r.VOLUME_ID,remaining_tasks=p.grid()[r.PREFIX:],
            max_additional_replacement_attempts=0,automatic_job_retries=False,prior_jobs=prior,
            original_dispatch_sha256=p.sha(run/'DISPATCH.jsonl'),completed_seals={})
        recovery=control/'RECOVERY-APPROVAL.json';self.write(recovery,value);digest=p.sha(recovery)
        self.write(control/'BACKUP-RECOVERY-READY.json',dict(approval_sha256=digest,archives={s:v['archive'] for s,v in r.BACKUPS.items()},
                                                          all_prior_backups_verified=True))
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
            if stale or (stop_after is not None and len(submitted)>=stop_after):
                raise RuntimeError('Backup unavailable')
        import breadth_precision_freeze as freeze
        with patch.object(r.p,'authorize',return_value=({},{})),patch.object(r,'overlay_check'),\
             patch.object(r,'prior_state',return_value=(prior,dict(directories=[r.name(s) for s in p.grid()[:r.PREFIX]],seals={}))),\
             patch.object(r,'wait_live',side_effect=live),patch.object(r,'__file__',str(overlay/'controller.py')),\
             patch.object(r,'OLD_APPROVAL_SHA',p.sha(approval)),patch.object(r,'command',side_effect=command),\
             patch.object(ct,'json_write',side_effect=write),patch.object(r.time,'sleep'),patch.object(freeze,'check_frozen',side_effect=lambda *a:order.append(('freeze',))):
            if fail_at or stale or stop_after is not None:
                with self.assertRaises(RuntimeError):r.dispatch(recovery,digest)
            else:
                r.dispatch(recovery,digest)
                with self.assertRaises((FileExistsError,RuntimeError)):r.dispatch(recovery,digest)
        self.assertEqual((run/'DISPATCH.jsonl').read_text(),'original immutable ledger\n')
        self.assertEqual((run/'DISPATCH-STOP.json').read_text(),'original stop\n')
        self.assertEqual((run/'RECOVERY-DISPATCH.jsonl').read_text(),'prior recovery ledger\\n')
        self.assertEqual((run/'RECOVERY-STOP.json').read_text(),'prior recovery stop\\n')
        return run,submitted,order
    def test_full_mocked_remainder_and_barriers(self):
        run,submitted,order=self.simulated_dispatch()
        self.assertEqual(submitted,p.grid()[r.PREFIX:])
        self.assertEqual(len(submitted),302)
        self.assertLess(order.index(('backup','train')),order.index(('submit','fit',0)))
        self.assertLess(order.index(('freeze',)),order.index(('backup','models')))
        self.assertLess(order.index(('backup','models')),order.index(('submit','evaluation',0)))
        self.assertLess(order.index(('backup','evaluation')),order.index(('submit','analyze',0)))
        summary=ct.json_read(run/'DISPATCH-FINAL.json')
        self.assertEqual(summary['allocation_attempts'],451)
        self.assertEqual(summary['successful_coordinates'],450)
        self.assertEqual(summary['gpu_seconds'],r.PRIOR_GPU+300)
        self.assertEqual(summary['cpu_wall_seconds'],2)
    def test_new_failure_stops_without_retry(self):
        run,submitted,order=self.simulated_dispatch(fail_at=2)
        self.assertEqual(submitted,p.grid()[r.PREFIX:r.PREFIX+2])
        self.assertTrue((run/'RECOVERY2-STOP.json').exists())
        self.assertFalse((run/'DISPATCH-FINAL.json').exists())
    def test_stale_liveness_blocks_before_claim_or_dispatch(self):
        run,submitted,order=self.simulated_dispatch(stale=True)
        self.assertEqual(submitted,[])
        self.assertFalse((run/'RECOVERY2-CLAIM.json').exists())
    def test_backup_loss_after_completed_job_blocks_next_submission(self):
        run,submitted,order=self.simulated_dispatch(stop_after=3)
        self.assertEqual(submitted,p.grid()[r.PREFIX:r.PREFIX+3])
        stop=ct.json_read(run/'RECOVERY2-STOP.json')
        self.assertIsNone(stop['active_job'])
        self.assertEqual(stop['unresolved_reservation_seconds'],0)
        self.assertEqual(stop['gpu_seconds'],r.PRIOR_GPU+3)


if __name__=='__main__':unittest.main(verbosity=2)
