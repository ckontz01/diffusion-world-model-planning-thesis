"""Complete stdlib-only synthetic continuation/finalization regressions."""
import copy
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch
import r2_core as r
import controller
import finalize

sys.path.insert(0,str(r.ROOT.parent/'bindings-r1'))
import common as c

class Fixture:
    def __init__(self,root):
        self.root=Path(root);self.jobs=c.grid();self.run=self.root/'run';self.control=self.root/'r2-control'
        self.run.mkdir();self.control.mkdir();self.c=c;self.science_root=self.root/'source';self.science_root.mkdir()
        self.r1_control=self.root/'r1-control';self.r1_control.mkdir()
        self.worker_approval=self.r1_control/'APPROVAL.json';r.write(self.worker_approval,{'mock':True})
        self.approval_sha='mock-r2-approval';self.binding={'instruction_sha256':'mock-instruction','control_manifest':'mock-r2-manifest'}
        r.write(self.run/'STOP.json',{'error':'mock original hostname association failure'})
        self.stop_sha=r.sha(self.run/'STOP.json')
        self.old_ledger=self.run/'CAMPAIGN-ATTEMPTS.jsonl'
        r.append(self.old_ledger,{'mock':'failed304189 plus completed304193; unchanged original segment'})
        r.append(self.run/'DISPATCH.jsonl',{'mock':'original dispatch immutable'})
        r.write(self.run/'APPROVAL.json',{'mock':'original worker approval'})
        r.write(self.run/'CONTROLLER.json',{'mock':'original controller'})
        for label,p in [('source',self.science_root/'source.py'),('control',self.r1_control/'controller.err')]:
            with p.open('xb') as f:f.write(label.encode())
        provenance=self.run/'provenance-failed-v2';provenance.mkdir();r.write(provenance/'STOP.json',{'failed_job':'304189'})
        r.write(provenance/'FAILURE.json',{'provenance_not_data':True})
        self.make_worker(self.jobs[0],'304193',existing=True)
        self.expected_hashes={n:r.sha(self.run/'collect-fit-490'/n) for n in r.EXISTING_HASHES}
        failed=self.row(self.jobs[0],'304189',existing=True);failed.update(state='FAILED',exit_code='1:0',seconds=23,time_limit_minutes=30)
        raw_failed=self.raw(failed);old=self.row(self.jobs[0],'304193',existing=True)
        self.baseline={'unix':1,'paths':{'source':str(self.science_root),'control':str(self.r1_control),'run':str(self.run)},
                       'scheduler_rows':[raw_failed,self.raw(old)],'failed_terminal':{'seconds':23,'state':'FAILED'},
                       'original_controller':{'pid':684587,'start_ticks':'893012584'},'inventory':{}}
        for label,root in self.baseline['paths'].items():
            for p in Path(root).rglob('*'):
                if p.is_file():self.baseline['inventory'][label+'/'+p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':r.sha(p)}
        self.original_bytes={p:p.read_bytes() for root in self.baseline['paths'].values() for p in Path(root).rglob('*') if p.is_file()}
    def raw(self,row):
        return [row['job'],row['job_name'],row['state'],row['exit_code'],str(row['seconds']),str(row['allocated_cpus']),
                row['allocated_tres'],row['node'],row['partition'],row['qos'],row['account'],str(row['time_limit_minutes'])]
    def row(self,j,job,existing=False):
        row={'job':job,'job_name':('acv0r1-' if existing else 'acv0r2-')+j['key'],'state':'COMPLETED','exit_code':'0:0',
             'seconds':80 if existing else j['seconds'],'allocated_cpus':4,'allocated_tres':'billing=1,cpu=4,'+('gres/gpu=1,mem=24G' if j['gpu'] else 'mem=8G')+',node=1',
             'gpus':j['gpu'],'node':'gpu09' if j['gpu'] else 'cpu01','partition':'a6000' if j['gpu'] else 'defq',
             'qos':'normal-a6000' if j['gpu'] else 'normal','account':'superworld','time_limit_minutes':j['seconds']//60}
        row['raw_scheduler']=self.raw(row);return row
    def make_worker(self,j,job,existing=False):
        p=self.run/j['key'];p.mkdir()
        tech={'passed':True,'spec':j,'package':r.SCIENCE_MANIFEST,'approval':r.WORKER_APPROVAL,'attempt':2 if existing else 1,
              'hard_seconds':j['seconds'],'work_seconds':c.work_seconds(j),'supervisor_seconds':c.supervisor_seconds(j)}
        if j['gpu']:
            h={'accepted':True,'query_status':'complete','cuda_available':True,'visible_device_count':1,'device_name':r.DEVICE,
               'hostname':'gpu09.cluster','slurm_job_id':job,'properties':{'uuid':'different-uuid-'+job}}
            r.write(p/'HARDWARE.json',h);tech.update(hardware=h,models_unchanged=True,
                checks={'passed':True,'reference':j['reference'],'role':j.get('role','final_development'),'physical_replay_checked':True})
        if j['stage']=='fitting':
            r.write(p/'FIT.json',{'updates':192});r.write(p/'PREPROCESSING.json',{'fit_ids':list(map(str,c.roles()['fit']))})
        r.write(p/'TECHNICAL.json',tech);r.write(p/'artificial-payload.json',{'synthetic_only':True});c.seal(p,j)
    def resolution(self,receipt):
        r.write(self.control/'ACCEPTED-EXISTING.json',receipt)
        r.write(self.control/'STOP-RESOLUTION.json',{'resolved_stop_path':str(self.run/'STOP.json'),'resolved_stop_sha256':self.stop_sha,
                'instruction_sha256':self.binding['instruction_sha256'],'r2_approval_sha256':self.approval_sha,
                'accepted_existing_sha256':r.sha(self.control/'ACCEPTED-EXISTING.json')})
    def run_all(self):
        old,accepted=r.accept_existing(self);self.resolution(accepted);calls=[];gates=[]
        def record(row):
            row['unix']=time.time()
            r.append(self.control/'CAMPAIGN-R2.jsonl',row)
            if row['event'] in ('accepted_existing','accepted_new'):r.append(self.control/'SCIENTIFIC-TASKS-R2.jsonl',row)
        record(accepted)
        def submit(j):
            r.stop_guard(self);calls.append(j);job=str(800000+len(calls));self.make_worker(j,job);return job
        scheduler=NS(submit=submit,wait=lambda job,j:self.row(j,job))
        def gate(name,rows):gates.append((name,len(calls)));controller.gates(self,name,rows)
        result=controller.execute(self.jobs,old,scheduler,record,lambda j,row:r.verify_worker(self,j,row),gate,lambda:r.stop_guard(self))
        snap={'allocations':[r.parse_row(self.baseline['scheduler_rows'][0])]+[{k:v[k] for k in self.row(v['spec'],v['job'],v['job']=='304193')} for v in result['jobs']],
              'no_live_campaign_jobs':True}
        r.write(self.control/'FINAL-SCHEDULER.json',snap)
        return result,calls,gates

class R2Tests(unittest.TestCase):
    def test_actual_receipt_allowed_pairs_and_strict_rejections(self):
        base=r.read(r.ROOT/'BASELINE.json');spec=c.grid()[0];row=r.parse_row(base['scheduler_rows'][1]);h=base['hardware']
        for host in ('gpu09.cluster','gpu09'):
            out=r.association(dict(h,hostname=host),spec,row);self.assertEqual(out['worker_hostname'],host)
        for change in ({'hostname':'gpu09.evil'},{'hostname':'gpu090.cluster'},{'hostname':'prefix-gpu09'},{'slurm_job_id':'304194'},
                       {'device_name':'NVIDIA RTX A6000'},{'device_name':r.DEVICE+' extra'},{'visible_device_count':2},{'cuda_available':False}):
            with self.assertRaises(ValueError):r.association(dict(h,**change),spec,row)
        for change in ({'node':'gpu10'},{'node':'gpu09,gpu10'},{'node':'gpu[09-10]'},{'gpus':2},{'allocated_cpus':8},
                       {'partition':'other'},{'qos':'other'},{'account':'other'},{'allocated_tres':'cpu=4,gres/gpu=1,mem=48G,node=1'}):
            with self.assertRaises(ValueError):r.association(h,spec,dict(row,**change))
        changed=copy.deepcopy(h);changed['properties']['uuid']='new-per-allocation-uuid';r.association(changed,spec,row)

    def test_existing_acceptance_readonly_no_scheduler_model_or_physics(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp)
            with patch.object(r,'EXISTING_HASHES',x.expected_hashes),patch.object(subprocess,'run',side_effect=AssertionError('No scheduler/model calls')), \
                 patch.dict(sys.modules,{'torch':None,'bridge':None,'episodes':None}):
                row,accepted=r.accept_existing(x)
            self.assertEqual(row['job'],'304193');self.assertFalse(accepted['new_submission']);self.assertGreater(accepted['accepted_unix'],x.baseline['unix'])
            for path,data in x.original_bytes.items():self.assertEqual(path.read_bytes(),data)
            with (x.run/'collect-fit-490/artifical-new-member.json').open('xb') as f:f.write(b'{}')
            with patch.object(r,'EXISTING_HASHES',x.expected_hashes):
                with self.assertRaises(ValueError):r.accept_existing(x)
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);wrong=copy.deepcopy(x.jobs);wrong[0]['seconds']=1800;x.jobs=wrong
            with patch.object(r,'EXISTING_HASHES',x.expected_hashes):
                with self.assertRaises(ValueError):r.accept_existing(x)

    def test_490_blocked_in_loop_scheduler_and_generic_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);calls=Mock();s=controller.Slurm(x)
            with patch.object(subprocess,'run',calls):
                with self.assertRaises(ValueError):s.submit(x.jobs[0])
            calls.assert_not_called()
            with self.assertRaises(ValueError):controller.permitted(dict(x.jobs[1],key='collect-fit-490'),x.jobs)
            with patch.object(r,'EXISTING_HASHES',x.expected_hashes):old,_=r.accept_existing(x)
            for wrong in ([x.jobs[0]]+x.jobs, [x.jobs[0],x.jobs[0]]+x.jobs[2:]):
                with self.assertRaises(ValueError):controller.execute(wrong,old,NS(submit=calls),lambda _:None,lambda *a:None,lambda *a:None,lambda:None)
            calls.assert_not_called()

    def test_actual_launch_args_original_source_and_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);s=controller.Slurm(x);commands=[]
            def run(args,**kw):commands.append(args);return NS(returncode=0,stdout='800001',stderr='')
            with patch.object(r,'STOP_SHA',x.stop_sha),patch.object(subprocess,'run',run):
                self.assertEqual(s.submit(x.jobs[1]),'800001')
                with self.assertRaises(ValueError):s.submit(x.jobs[1])
            a=commands[0]
            for value in ('--time=30','--nodelist=gpu09','--no-requeue','--mem=24G','--cpus-per-task=4','--partition=a6000','--qos=normal-a6000'):self.assertIn(value,a)
            self.assertEqual(a[-5:],[str(x.science_root),str(x.worker_approval),str(x.run),'collect-fit-545','1'])

    def test_unknown_attempts_prior_inactive_and_r2_exclusivity(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);accounting='\n'.join('|'.join(v)+'|' for v in x.baseline['scheduler_rows'])
            r.validate_prior_scheduler(x,accounting,'');r.ensure_unstarted(x)
            for wrong in (accounting+'\n999|alternate-ACV0-job|RUNNING',accounting.replace('|80|','|81|')):
                with self.assertRaises(ValueError):r.validate_prior_scheduler(x,wrong,'')
            with self.assertRaises(ValueError):r.validate_prior_scheduler(x,accounting,'999|prefix-acv0-more|RUNNING')
            r.write(x.control/'CONTROLLER-STARTED.json',{})
            with self.assertRaises(ValueError):r.ensure_unstarted(x)

    def test_complete338_continuation_finalization_inventory_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp)
            with patch.object(r,'STOP_SHA',x.stop_sha),patch.object(r,'EXISTING_HASHES',x.expected_hashes):
                result,calls,gates=x.run_all()
                self.assertEqual(len(calls),338);self.assertEqual(calls[0]['key'],'collect-fit-545');self.assertNotIn('collect-fit-490',[j['key'] for j in calls])
                self.assertEqual(gates,[('technical',1),('models',81),('analysis',337)])
                self.assertEqual(result['campaign_gpu_seconds'],219103);self.assertEqual(result['campaign_cpu_stage_seconds'],21600)
                self.assertEqual(len(result['jobs']),339)
                ledger=r.lines(x.control/'CAMPAIGN-R2.jsonl');claims=[v for v in ledger if v['event']=='claim']
                self.assertEqual(claims[0]['campaign_gpu_seconds'],103)
                self.assertTrue(all(v['campaign_gpu_seconds']+v['remaining_gpu_reservation']<=220800 for v in claims))
                combined=finalize.accept(x,result);self.assertEqual(len(combined['allocations']),340);self.assertNotEqual(len(combined['allocations']),341)
                self.assertFalse(combined['failed_attempts_in_scientific_denominators']);self.assertEqual(combined['successful_task_keys'],[j['key'] for j in x.jobs])
                before=r.read(x.run/'PRE-ANALYSIS-ACCOUNTING.json')['jobs'];self.assertEqual(before,result['jobs'][:-1]);self.assertEqual(before[0]['job'],'304193')
                inventory=finalize.inventory(x);names={n for n,_ in inventory}
                for name in ('run/STOP.json','r2-control-records/STOP-RESOLUTION.json','run/provenance-failed-v2/FAILURE.json',
                             'r1-control/controller.err','run/collect-fit-490/SEAL.json','run/analysis/SEAL.json'):
                    self.assertIn(name,names)
                r.write(x.control/'COMPUTE-COMPLETE.json',result);r.write(x.control/'COMBINED-CAMPAIGN.json',combined)
                r.write(x.run/'COMPUTE-COMPLETE.json',{'r2_control':str(x.control),'completion_sha256':r.sha(x.control/'COMPUTE-COMPLETE.json'),
                    'combined_campaign_sha256':r.sha(x.control/'COMBINED-CAMPAIGN.json'),'successful_unique_tasks':339,'campaign_allocations':340})
                r.write(x.control/'CONTROLLER-STARTED.json',{'pid':99999999,'start_ticks':'0'})
                with patch.object(r,'storage',return_value={'synthetic_cap_check':True}):finalize.archive(x)
                req=r.read(x.run/'final-preservation/BACKUP-REQUEST.json');self.assertTrue(req['original_stop_retained_and_resolved'])
                from preserve import verify_tar
                verify_tar(x.run/'final-preservation/final.tar',req['members'])
                with self.assertRaises(ValueError):
                    with patch.object(r,'storage',return_value={}):finalize.archive(x)
                for p,data in x.original_bytes.items():self.assertEqual(p.read_bytes(),data)
                with self.assertRaises(ValueError):finalize.accept(x,dict(result,campaign_allocations=341))
                original_read=r.read
                def incorrect_order(path):
                    value=original_read(path)
                    if Path(path).name=='MODEL-FREEZE-R2.json':value['unix']=0
                    return value
                with patch.object(r,'read',incorrect_order):
                    with self.assertRaises(ValueError):finalize.accept(x,result)
                r.write(x.control/'STOP-R2.json',{'fault':'mock new unresolved fault'})
                with self.assertRaises(ValueError):finalize.accept(x,result)

    def test_stop_resolution_only_exact_original_and_no_new_stops(self):
        for target in ('changed-original','new-run','new-control'):
            with tempfile.TemporaryDirectory() as tmp:
                x=Fixture(tmp)
                with patch.object(r,'STOP_SHA',x.stop_sha),patch.object(r,'EXISTING_HASHES',x.expected_hashes):
                    _,receipt=r.accept_existing(x);x.resolution(receipt);r.stop_guard(x)
                    if target=='changed-original':
                        with (x.run/'STOP.json').open('ab') as f:f.write(b'changed')
                    elif target=='new-run':r.write(x.run/'UNRECOGNIZED-STOP.json',{})
                    else:r.write(x.control/'STOP-NEW.json',{})
                    with self.assertRaises(ValueError):r.stop_guard(x)

    def test_failures_and_gates_stop_without_another_submission(self):
        for fail in ('technical','models','allocation','ambiguous'):
            with tempfile.TemporaryDirectory() as tmp:
                x=Fixture(tmp);calls=[]
                with patch.object(r,'EXISTING_HASHES',x.expected_hashes):existing,_=r.accept_existing(x)
                def submit(j):
                    calls.append(j)
                    if fail=='ambiguous':raise RuntimeError('Unknown submit result')
                    return str(800000+len(calls))
                def wait(job,j):
                    row=x.row(j,job)
                    if fail=='allocation':row.update(state='FAILED',exit_code='1:0',seconds=7)
                    return row
                def gate(name,rows):
                    if name==fail:raise ValueError('Mock gate rejection')
                events=[]
                with self.assertRaises((ValueError,RuntimeError)):
                    controller.execute(x.jobs,existing,NS(submit=submit,wait=wait),events.append,lambda j,row:{'key':j['key'],'job':row['job']},gate,lambda:None)
                self.assertEqual(len(calls),81 if fail=='models' else 1)
                if fail=='allocation':self.assertEqual(events[-1]['campaign_gpu_seconds'],110)

    def test_all_original_files_unchanged_and_preparation_footprint(self):
        old=r.ROOT.parent/'bindings-r1'
        manifest=c.read(old/'SOURCE-MANIFEST.json')
        for name,h in manifest['files'].items():self.assertEqual(c.sha(c.REPO/name),h,name)
        self.assertLess(r.total(r.ROOT),250000000)
        base=r.read(r.ROOT/'BASELINE.json')
        self.assertEqual(base['hardware']['hostname'],'gpu09.cluster');self.assertEqual(r.parse_row(base['scheduler_rows'][1])['node'],'gpu09')
        self.assertLess(sum(v['bytes'] for v in base['inventory'].values())+339*2*65536+300000000+r.total(r.ROOT),500000000)

if __name__=='__main__':unittest.main(verbosity=2)
