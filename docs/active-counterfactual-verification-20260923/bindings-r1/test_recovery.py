"""R1 artificial/mock controls only; no model, research or scheduler execution."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import common as c
import dispatch
import hardware
import recovery


def fake_torch(name=hardware.EXPECTED_DEVICE, count=1, available=True, error=False):
    cuda=NS(is_available=lambda:available,device_count=lambda:count,
            get_device_name=Mock(return_value=name,side_effect=RuntimeError('query failed') if error else None),
            get_device_properties=lambda _:NS(name=name,major=8,minor=9,total_memory=48*1024**3,uuid='MOCK-UUID'))
    return NS(cuda=cuda)


class Scheduler:
    def __init__(self):self.calls=[]
    def submit(self,j):self.calls.append(j);return str(700000+len(self.calls))
    def wait(self,job,j):return {'state':'COMPLETED','exit_code':'0:0','seconds':j['seconds'],
                               'gpus':j['gpu'],'allocated_cpus':4,'node':'MOCK-HOST'}


class RecoveryTests(unittest.TestCase):
    def test_exact_names_counts_and_query_receipts(self):
        with patch.dict(os.environ,{'SLURM_JOB_ID':'700001'}),patch('socket.gethostname',return_value='MOCK-HOST'):
            saved=[];result=hardware.verify_device(fake_torch(),saved.append)
            self.assertTrue(result['accepted']);self.assertEqual(result['slurm_job_id'],'700001')
            self.assertEqual(result['hostname'],'MOCK-HOST');self.assertEqual(result['properties']['uuid'],'MOCK-UUID')
            for name in ('NVIDIA RTX A6000','NVIDIA A100','NVIDIA RTX 6000','NVIDIA RTX 6000 Ada Generation extra'):
                rows=[]
                with self.assertRaises(ValueError):hardware.verify_device(fake_torch(name),rows.append)
                self.assertEqual(len(rows),1);self.assertEqual(rows[0]['device_name'],name);self.assertFalse(rows[0]['accepted'])
            for torch in (fake_torch(count=2),fake_torch(count=0),fake_torch(available=False)):
                rows=[]
                with self.assertRaises(ValueError):hardware.verify_device(torch,rows.append)
                self.assertEqual(len(rows),1);self.assertFalse(rows[0]['accepted'])
            rows=[]
            with self.assertRaises(RuntimeError):hardware.verify_device(fake_torch(error=True),rows.append)
            self.assertEqual(rows[0]['query_status'],'error');self.assertIsNone(rows[0]['device_name'])
            for method in ('is_available','device_count','get_device_properties'):
                torch=fake_torch();setattr(torch.cuda,method,Mock(side_effect=RuntimeError(method)))
                rows=[]
                with self.assertRaises(RuntimeError):hardware.verify_device(torch,rows.append)
                self.assertEqual(rows[0]['query_status'],'error');self.assertFalse(rows[0]['accepted'])

    def test_executable_worker_order_no_loader_after_rejection(self):
        import worker
        for torch in (fake_torch('NVIDIA RTX A6000'),fake_torch(count=2),fake_torch(available=False),fake_torch(error=True)):
            with tempfile.TemporaryDirectory() as tmp:
                run=Path(tmp);auth=NS(run=run,runtime=Mock(),checkpoint=Mock(),reference=Mock())
                loaders=NS(load_backend=Mock(),source_factory=Mock())
                alarms=[];signals=NS(SIGALRM=14,SIGTERM=15,signal=Mock(),alarm=alarms.append)
                with patch.object(c,'Authorization',return_value=auth),patch.object(dispatch,'storage',return_value={}), \
                     patch.object(worker,'signal',signals),patch.dict(sys.modules,{'torch':torch,'bridge':loaders,'resource':NS()}), \
                     patch.dict(os.environ,{'SLURM_JOB_ID':'700001','SLURM_CPUS_PER_TASK':'4'}), \
                     patch.object(sys,'argv',['worker.py','--approval','mock','--run',str(run),'--task','collect-fit-490']):
                    with self.assertRaises((ValueError,RuntimeError)):worker.main()
                self.assertTrue((run/'collect-fit-490/HARDWARE.json').exists())
                self.assertTrue((run/'collect-fit-490/FAILURE.json').exists())
                loaders.load_backend.assert_not_called();loaders.source_factory.assert_not_called()
                auth.checkpoint.assert_not_called();auth.reference.assert_not_called()
                self.assertEqual(alarms[0],1620)
        calls=[]
        with patch.dict(sys.modules,{'bridge':NS(load_backend=lambda _:calls.append('load') or 'backend')}):
            h,b=hardware.initialize_backend(fake_torch(),lambda _:calls.append('receipt'),'mock')
        self.assertEqual(calls,['receipt','load']);self.assertEqual(b,'backend')

    def test_prior_authentication_and_unknown_namespace(self):
        p=recovery.prior();line='|'.join(p['scheduler_row'])+'\n'
        recovery.validate_scheduler(line,'')
        for wrong in (line+line,line.replace('|23|','|24|'),line+'999|alternate-ACV0-recovery|RUNNING|0:0|1|4|gres/gpu=1|gpu09|a6000|normal-a6000|superworld|\n'):
            with self.assertRaises(ValueError):recovery.validate_scheduler(wrong,'')
        with self.assertRaises(ValueError):recovery.validate_scheduler(line,'999|prefix-acv0-other|PENDING')
        with tempfile.TemporaryDirectory() as tmp:
            p=copy.deepcopy(p);p['paths']={'source':str(Path(tmp)/'source'),'control':str(Path(tmp)/'control'),'run':str(Path(tmp)/'old-run')}
            p['members']={}
            for label,root in p['paths'].items():
                path=Path(root);path.mkdir();c.write(path/'old.json',{'artificial':label})
                p['members'][label+'/old.json']={'bytes':(path/'old.json').stat().st_size,'sha256':c.sha(path/'old.json')}
            recovery.authenticate_prior_files(p)
            with (Path(p['paths']['control'])/'old.json').open('ab') as f:f.write(b'changed')
            with self.assertRaises(ValueError):recovery.authenticate_prior_files(p)

    def test_unchanged_science_and_amended_grid(self):
        old=c.BASE/'bindings-v2'
        for name in ('bridge.py','episodes.py','verify.py','fitting.py','analysis.py','artificial.py','model_seal.py','run_worker.sh','INPUT-BINDINGS.json','controller_runtime.py','CONTROLLER-RUNTIME.json'):
            self.assertEqual(c.sha(old/name),c.sha(c.ROOT/name),name)
        before=c.read(old/'GRID.json');after=c.grid();self.assertEqual(len(after),339)
        self.assertEqual(before[0]['seconds'],1800);before[0]['seconds']=1740
        self.assertEqual(before,after);self.assertEqual(c.read(c.ROOT/'GRID.json'),after)
        self.assertEqual(23+sum(j['seconds'] for j in after if j['gpu']),220763)
        self.assertEqual(c.work_seconds(after[0]),1620);self.assertEqual(c.supervisor_seconds(after[0]),1730)

    def test_actual_scheduler_and_supervisor_envelopes(self):
        import supervise
        with tempfile.TemporaryDirectory() as tmp:
            auth=NS(run=Path(tmp));captured=[]
            def command(args,**kw):captured.append(args);return NS(returncode=0,stdout='700001\n',stderr='')
            with patch.object(subprocess,'run',command):self.assertEqual(dispatch.Slurm(auth,Path('mock')).submit(c.grid()[0]),'700001')
            args=captured[0]
            for value in ('--time=29','--no-requeue','--job-name=acv0r1-collect-fit-490','--gres=gpu:1','--cpus-per-task=4','--mem=24G','--partition=a6000','--qos=normal-a6000'):self.assertIn(value,args)
            import io
            child=NS(stdout=io.BytesIO(),stderr=io.BytesIO(),wait=Mock(return_value=0))
            with patch.object(c,'Authorization',return_value=auth),patch.object(subprocess,'Popen',return_value=child), \
                 patch.object(sys,'argv',['supervise.py','--approval','mock','--run',tmp,'--task','collect-fit-490']):
                self.assertEqual(supervise.main(),0)
            child.wait.assert_called_once_with(timeout=1730)

    def test_attempts_remaining_reservations_and_gates(self):
        s=Scheduler();events=[];gates=[]
        result=dispatch.execute(c.grid(),s,events.append,lambda _:None,lambda n,r:gates.append((n,len(r))),lambda:None)
        self.assertEqual(result['gpu_seconds'],220763);self.assertEqual(result['r1_gpu_seconds'],220740)
        self.assertEqual(result['campaign_attempts'],340);self.assertEqual(result['new_attempts'],339)
        self.assertEqual(gates,[('technical',2),('models',82),('analysis',338)])
        self.assertEqual([r['attempt'] for r in events if r['event']=='submitted'],[2]+[1]*338)
        self.assertEqual([j['reference'] for j in s.calls[:2]],[490,545])
        self.assertEqual(len({j['key'] for j in s.calls}),339)
        self.assertTrue(all(r['campaign_gpu_seconds']+r['remaining_gpu_reservation']<=220800 for r in events if r['event']=='claim'))
        def overcharge(job,j):return {'state':'COMPLETED','exit_code':'0:0','seconds':j['seconds'],'gpus':2}
        s=Scheduler();s.wait=overcharge;rows=[]
        with self.assertRaises(ValueError):dispatch.execute(c.grid(),s,rows.append,lambda _:None,lambda *x:None,lambda:None)
        self.assertEqual(len(s.calls),1);self.assertEqual(rows[-1]['gpu_seconds'],23+3480)
        for gate in ('technical','models'):
            s=Scheduler()
            def stop(name,rows):
                if name==gate:raise ValueError('mock gate rejection')
            with self.assertRaises(ValueError):dispatch.execute(c.grid(),s,lambda _:None,lambda _:None,stop,lambda:None)
            self.assertEqual(len(s.calls),2 if gate=='technical' else 82)

    def test_model_gate_stdlib_and_192_updates(self):
        from model_seal import model_freeze
        from fitting import model_freeze as original
        for updates in (192,191):
            with tempfile.TemporaryDirectory() as tmp:
                roots=[Path(tmp)/'a',Path(tmp)/'b']
                for root in roots:
                    for key in ('fit-joint','fit-ordinary'):
                        p=root/key;p.mkdir(parents=True);c.write(p/'FIT.json',{'updates':updates})
                        c.write(p/'PREPROCESSING.json',{'fit_ids':list(map(str,c.roles()['fit']))});c.seal(p,{'key':key})
                if updates==191:
                    with self.assertRaises(ValueError):model_freeze(roots[0],'mock')
                else:
                    original(roots[0],'mock');model_freeze(roots[1],'mock')
                    self.assertEqual((roots[0]/'MODEL-FREEZE.json').read_bytes(),(roots[1]/'MODEL-FREEZE.json').read_bytes())

    def test_full_archive_340_attempts_provenance_not_data_and_storage(self):
        import preserve
        original_prior=recovery.prior();original_root=c.ROOT
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);source=base/'source';source.mkdir();run=base/'run';run.mkdir();control=base/'control';control.mkdir()
            p=copy.deepcopy(original_prior);p['paths']={k:str(base/('old-'+k)) for k in ('source','run','control')};p['members']={}
            for label,root in p['paths'].items():
                root=Path(root);root.mkdir();c.write(root/'evidence.json',{'artificial':label})
                f=root/'evidence.json';p['members'][label+'/evidence.json']={'bytes':f.stat().st_size,'sha256':c.sha(f)}
            c.write(source/'PRIOR-ATTEMPT.json',p);c.write(source/'SOURCE-MANIFEST.json',{'files':{}});c.write(source/'APPROVAL-TEMPLATE.json',{'authorized':False})
            c.write(control/'launch.json',{'artificial':True});jobs=c.grid()
            auth=NS(run=run,approval={'package_sha256':'mock','recovery':{'control':str(control)}},approval_sha='mock-approval')
            with patch.object(recovery,'prior',return_value=p),patch.object(c,'ROOT',source),patch.object(c,'REPO',base), \
                 patch.object(recovery,'approval_binding',return_value={'control':str(control)}):
                recovery.copy_prior(run);recovery.append(run/'CAMPAIGN-ATTEMPTS.jsonl',recovery.historical_event())
                def record(row):
                    recovery.append(run/'CAMPAIGN-ATTEMPTS.jsonl',row)
                    if row['event']=='scientific_task_accepted':recovery.append(run/'SCIENTIFIC-TASKS.jsonl',dict(row,seal_sha256=c.sha(run/row['key']/'SEAL.json')))
                def check(j):
                    target=run/j['key'];target.mkdir();c.write(target/'TECHNICAL.json',{'artificial':True});c.seal(target,j)
                complete=dispatch.execute(jobs,Scheduler(),record,check,lambda *x:None,lambda:None)
                accepted=recovery.final_acceptance(run,complete)
                self.assertEqual(accepted['campaign_allocations'],340);self.assertFalse(accepted['failed_attempt_in_scientific_denominators'])
                c.write(run/'COMPUTE-COMPLETE.json',complete)
                size=dispatch.storage(source,run,jobs)
                self.assertGreater(size['old_original_bytes'],0);self.assertGreater(size['old_provenance_copy_bytes'],size['old_original_bytes'])
                self.assertEqual(size['inclusive_reservation'],7248000000)
                with patch.object(c,'Authorization',return_value=auth):preserve.archive('mock',str(run))
                request=c.read(run/'final-preservation/BACKUP-REQUEST.json')
                self.assertTrue(request['failed_v2_included_as_provenance_not_data'])
                self.assertTrue(all('run/provenance-failed-v2/'+n in request['members'] for n in p['members']))
                preserve.verify_tar(run/'final-preservation/final.tar',request['members'])
                with self.assertRaises(FileExistsError):
                    with patch.object(c,'Authorization',return_value=auth):preserve.archive('mock',str(run))
                with self.assertRaises(ValueError):recovery.final_acceptance(run,dict(complete,campaign_attempts=339))


if __name__=='__main__':unittest.main(verbosity=2)
