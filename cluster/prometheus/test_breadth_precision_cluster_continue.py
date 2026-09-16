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
import breadth_precision_cluster_continue as r


class ClusterContinueTests(unittest.TestCase):
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
    def simulated_dispatch(self,fail_at=None,freeze_fail=False):
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
        for spec in p.grid()[:r.PREFIX]:self.report(run/r.name(spec),spec)
        value=dict(researcher_approved=True,caps=p.CAPS,source_sha256=r.SOURCE_SHA,run=str(run),scientific_source=str(source),
            old_approval=str(approval),overlay=str(overlay),overlay_sha256='test',accounting=str(accounting),
            completed_prefix=r.PREFIX,backup_policy='external_after_compute',remaining_tasks=p.grid()[r.PREFIX:],
            max_additional_replacement_attempts=0,automatic_job_retries=False,prior_jobs=prior,
            original_dispatch_sha256=p.sha(run/'DISPATCH.jsonl'),completed_seals={})
        recovery=control/'RECOVERY-APPROVAL.json';self.write(recovery,value);digest=p.sha(recovery)
        self.write(control/'RECOVERY2-APPROVAL.json',{})
        (run/'RECOVERY2-DISPATCH.jsonl').write_text('second ledger\n'.replace('\n','\\n'))
        (run/'RECOVERY2-STOP.json').write_text('second stop')
        submitted=[];order=[];real_write=ct.json_write
        def write(path,data):
            real_write(path,data)
            if Path(path).name.startswith('CLUSTER-STAGE-'):
                order.append(('barrier',data['stage']))
        def command(*args):
            if args[0]=='sbatch':
                spec=p.task(args[-2],int(args[-1]));submitted.append(spec);order.append(('submit',spec['kind'],spec['index']))
                job=str(400000+len(submitted));self.report(run/r.name(spec),spec);return job
            if args[0]=='sacct':
                state='FAILED' if fail_at==len(submitted) else 'COMPLETED'
                return '%s|%s|%s|1|'%(400000+len(submitted),state,'1:0' if state=='FAILED' else '0:0')
            if args[0]=='scancel':return ''
            raise AssertionError(args)
        def frozen(*args):
            order.append(('freeze',))
            if freeze_fail: raise RuntimeError('Model freeze invalid')
        import breadth_precision_freeze as freeze
        with patch.object(r.p,'authorize',return_value=({},{})),patch.object(r,'overlay_check'),\
             patch.object(r,'prior_state',return_value=(prior,dict(directories=[r.name(s) for s in p.grid()[:r.PREFIX]],seals={}))),\
             patch.object(r,'R2_CONTROL',control),patch.object(r,'__file__',str(overlay/'controller.py')),\
             patch.object(r,'OLD_APPROVAL_SHA',p.sha(approval)),patch.object(r,'command',side_effect=command),\
             patch.object(ct,'json_write',side_effect=write),patch.object(r.time,'sleep'),patch.object(freeze,'check_frozen',side_effect=frozen):
            if fail_at or freeze_fail:
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
        self.assertEqual(len(submitted),300)
        self.assertLess(order.index(('barrier','train')),order.index(('submit','fit',0)))
        self.assertLess(order.index(('freeze',)),order.index(('barrier','models')))
        self.assertLess(order.index(('barrier','models')),order.index(('submit','evaluation',0)))
        self.assertLess(order.index(('barrier','evaluation')),order.index(('submit','analyze',0)))
        summary=ct.json_read(run/'CLUSTER-COMPUTE-COMPLETE.json')
        self.assertFalse((run/'DISPATCH-FINAL.json').exists())
        self.assertFalse(summary['external_backup_verified'])
        self.assertTrue((run/'BACKUP-REQUEST-cluster-final.json').exists())
        self.assertEqual(summary['allocation_attempts'],451)
        self.assertEqual(summary['successful_coordinates'],450)
        self.assertEqual(summary['gpu_seconds'],r.PRIOR_GPU+298)
        self.assertEqual(summary['cpu_wall_seconds'],2)
    def test_new_failure_stops_without_retry(self):
        run,submitted,order=self.simulated_dispatch(fail_at=2)
        self.assertEqual(submitted,p.grid()[r.PREFIX:r.PREFIX+2])
        self.assertTrue((run/'CLUSTER-CONTINUE-STOP.json').exists())
        self.assertFalse((run/'DISPATCH-FINAL.json').exists())

    def test_model_freeze_failure_prevents_any_evaluation(self):
        run,submitted,order=self.simulated_dispatch(freeze_fail=True)
        self.assertEqual(len(submitted),235)
        self.assertFalse(any(x['kind']=='evaluation' for x in submitted))
        self.assertTrue((run/'CLUSTER-CONTINUE-STOP.json').exists())
    def test_no_laptop_or_backup_liveness_dependency(self):
        source=(Path(__file__).parent/'breadth_precision_cluster_continue.py').read_text()
        self.assertNotIn('wait_live(',source)
        self.assertNotIn('BACKUP-LIVE',source)
        self.assertNotIn('BACKUP-ACK-'+ 'train',source)
    def test_exact_remainder_and_caps(self):
        rest=p.grid()[r.PREFIX:]
        self.assertEqual(rest[0],p.task('breadth',142))
        self.assertEqual(len(rest),300)
        self.assertEqual(sum(x['gpu'] for x in rest),298)
        self.assertEqual(r.PRIOR_GPU+sum(x['seconds'] for x in rest if x['gpu']),249669)
        self.assertTrue(p.reservation(r.PRIOR_GPU,0,600_000_000,rest))
        self.assertFalse(p.reservation(p.CAPS['gpu_seconds'],0,0,rest))
    def test_prior_evidence_tamper_rejected(self):
        self.write(self.root/'RECOVERY2-APPROVAL.json',{})
        with patch.object(r,'R2_CONTROL',self.root):
            with self.assertRaises(RuntimeError):r.prior_state(self.root)
    def test_original_worker_command(self):
        args=r.arguments(p.task('breadth',142),'/source','/run','/approval')
        self.assertEqual(args[-5:],['/source','/run','/approval','breadth','142'])
        self.assertIn('/source/cluster/prometheus/run_breadth_precision.sh',args)

if __name__=='__main__':unittest.main(verbosity=2)
