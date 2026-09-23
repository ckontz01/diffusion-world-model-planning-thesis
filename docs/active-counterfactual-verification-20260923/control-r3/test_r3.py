"""Stdlib-only synthetic R3 regressions. No research model/data/physics calls."""
import ast,copy,importlib.util,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import r3_core as r
import controller3 as ctl
import finalize3 as final
import transport3 as t
sys.path.insert(0,str(r.ROOT.parent/'control-r2'))
from test_r2 import Fixture as OriginalFixture
import common as c

ACTUAL=r.read(r.ROOT/'BASELINE.json')

class Fixture(OriginalFixture):
    def __init__(self,path):
        super().__init__(path)
        self.binding.update(resolved_r2_stop_sha256='',r2_source_manifest='synthetic-r2')
        self.r2_source=self.root/'r2-source';self.r2_source.mkdir();r.write(self.r2_source/'control.json',{'artificial':True})
        self.r2_control=self.root/'old-r2';self.r2_control.mkdir()
        r.write(self.r2_control/'STOP-R2.json',{'error':"ValueError('Unambiguous scheduler columns')"})
        r.write(self.r2_control/'STOP-RESOLUTION.json',{'old_r1_fault_resolved':True})
        self.binding['resolved_r2_stop_sha256']=r.sha(self.r2_control/'STOP-R2.json')
        for row in ACTUAL['successful_rows'][1:]:self.make_worker(row['spec'],row['job'])
        gate={'scientific_selection':False,'seals':{j['key']:r.sha(self.run/j['key']/'SEAL.json') for j in self.jobs[:2]}}
        r.write(self.run/'TECHNICAL-TRANCHE-PASSED.json',gate)
        tranche=copy.deepcopy(ACTUAL['tranche']);tranche['original_run_marker_sha256']=r.sha(self.run/'TECHNICAL-TRANCHE-PASSED.json')
        for a in tranche['suppliers']:a['seal_sha256']=r.sha(self.run/a['key']/'SEAL.json')
        r.write(self.r2_control/'TECHNICAL-TRANCHE-R2.json',tranche)
        for row in ACTUAL['r2_ledger']:r.append(self.r2_control/'CAMPAIGN-R2.jsonl',row)
        self.baseline=copy.deepcopy(ACTUAL);self.baseline.update(unix=1,gate=gate,tranche=tranche)
        self.baseline['paths']={'source':str(self.science_root),'control':str(self.r1_control),'run':str(self.run),
                                'r2_source':str(self.r2_source),'r2_control':str(self.r2_control)}
        self.baseline['inventory']={};self.original_bytes={}
        for label,root in self.baseline['paths'].items():
            for p in Path(root).rglob('*'):
                if p.is_file():
                    self.baseline['inventory'][label+'/'+p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':r.sha(p)}
                    self.original_bytes[p]=p.read_bytes()
    def row(self,j,job,existing=False):
        row=super().row(j,job,existing)
        row['job_name']=r.read(r.ROOT/'CONTRACT.json')['historical_job_names'].get(job,'acv0r3-'+j['key'])
        row['raw_scheduler']=self.raw(row);return row
    def resolution(self,accepted):
        r.write(self.control/'ACCEPTED-EXISTING.json',accepted)
        r.write(self.control/'STOP-RESOLUTION.json',{'resolved_stop_path':str(self.run/'STOP.json'),'resolved_stop_sha256':self.stop_sha,
            'resolved_r2_stop_sha256':self.binding['resolved_r2_stop_sha256'],'instruction_sha256':self.binding['instruction_sha256'],
            'r3_approval_sha256':self.approval_sha,'accepted_existing_sha256':r.sha(self.control/'ACCEPTED-EXISTING.json')})
    def run_all(self):
        existing,accepted=r.accept_existing(self);self.resolution(accepted);calls=[];gates=[]
        def record(row):
            row['unix']=time.time();r.append(self.control/'CAMPAIGN-R3.jsonl',row)
            if row['event'] in ('accepted_existing','accepted_new'):r.append(self.control/'SCIENTIFIC-TASKS-R3.jsonl',row)
        for a in accepted:record(a)
        def submit(j):
            r.stop_guard(self);calls.append(j);job=str(800000+len(calls));self.make_worker(j,job);return job
        def gate(name,rows):gates.append((name,len(calls)));ctl.gates(self,name,rows)
        result=ctl.execute(self.jobs,existing,NS(submit=submit,wait=lambda job,j:self.row(j,job)),record,
            lambda j,row:r.verify_worker(self,j,row),gate,lambda:r.stop_guard(self))
        allocations=[self.baseline['allocations'][0]]+[r.parse_row(v['raw_scheduler']) for v in result['jobs']]
        r.write(self.control/'FINAL-SCHEDULER.json',{'allocations':allocations,'no_live_campaign_jobs':True})
        return result,calls,gates

class R3Tests(unittest.TestCase):
    def test_blank_final_field_and_optional_delimiter(self):
        raw=ACTUAL['scheduler_raw'][-1];cols=raw.split('|');cols[-1]='';blank='|'.join(cols)
        self.assertEqual(len(blank.rstrip('|').split('|')),11) # exact old parser defect
        self.assertEqual(len(r.columns(blank)),12);self.assertEqual(r.columns(blank)[-1],'')
        self.assertEqual(r.parse_row(raw),r.parse_row(raw+'|'))
        for v in (blank,raw.replace('|160|','||'),raw.replace('|160|','|unknown|')):
            with self.assertRaises(ValueError):r.parse_row(v)

    def test_state_before_nonterminal_numeric_fields(self):
        j=c.grid()[24]
        for state in sorted(ctl.ACTIVE):
            raw='800001|acv0r3-'+j['key']+'|'+state+'|||||||||'
            row,reason=ctl.observation(raw,'800001',j)
            self.assertIsNone(row);self.assertEqual(reason,'active:'+state)
        for raw in ('','800001|','800001|acv0r3-'+j['key']+'|COMPLETED|0:0'):
            self.assertIsNone(ctl.observation(raw,'800001',j)[0])
        for raw in ('999|x|RUNNING','800001|wrong|RUNNING','800001|acv0r3-'+j['key']+'|REQUEUED',
                    '800001|x|RUNNING\n800001|x|RUNNING','800001|'+'x|'*14):
            with self.assertRaises(ValueError):ctl.observation(raw,'800001',j)

    def test_status_only_wait_delayed_terminal_and_single_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);s=ctl.Slurm(x);j=x.jobs[24];good='|'.join(x.raw(x.row(j,'800001')))
            partial=good.rsplit('|',1)[0]+'|';responses=['800001','', '800001|acv0r3-'+j['key']+'|RUNNING|||||||||',partial,good]
            calls=[]
            def run(args,**kw):calls.append(args);return NS(returncode=0,stdout=responses.pop(0),stderr='')
            with patch.object(r,'STOP_SHA',x.stop_sha),patch.object(subprocess,'run',run),patch.object(time,'sleep'):
                job=s.submit(j);row=s.wait(job,j)
                with self.assertRaises(ValueError):s.submit(j)
            self.assertEqual(row['state'],'COMPLETED');self.assertEqual(sum(a[0]=='sbatch' for a in calls),1)
            obs=r.lines(x.control/'SCHEDULER-OBSERVATIONS.jsonl');self.assertIn(partial,[v['stdout'] for v in obs])
            args=calls[0]
            for a in ('--no-requeue','--nodelist=gpu09','--cpus-per-task=4','--mem=24G','--time=30'):self.assertIn(a,args)
            self.assertEqual(args[-5:],[str(x.science_root),str(x.worker_approval),str(x.run),j['key'],'1'])

    def test_status_grace_bounded_and_error_evidence(self):
        for stdout,rc in [('',0),('999|wrong|RUNNING',0),('',1)]:
            with tempfile.TemporaryDirectory() as tmp:
                x=NS(control=Path(tmp));calls=Mock(return_value=NS(returncode=rc,stdout=stdout,stderr='technical only'))
                with patch.object(r,'stop_guard'),patch.object(subprocess,'run',calls),patch.object(time,'sleep'):
                    with self.assertRaises(ValueError):ctl.Slurm(x).wait('800001',c.grid()[24])
                self.assertEqual(calls.call_count,9 if stdout=='' and rc==0 else 1)
                self.assertTrue(r.lines(x.control/'SCHEDULER-OBSERVATIONS.jsonl'))
                self.assertTrue(all(a.args[0][0]=='sacct' for a in calls.call_args_list))

    def test_all24_reused_readonly_no_scheduler_model_or_physics(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp)
            with patch.object(subprocess,'run',side_effect=AssertionError('No scheduler calls')),patch.dict(sys.modules,{'torch':None,'bridge':None,'episodes':None}):
                rows,receipts=r.accept_existing(x)
            self.assertEqual(len(rows),24);self.assertEqual(rows[-1]['job'],'304220')
            self.assertTrue(all(v['accepted_unix']>1 and not v['new_submission'] for v in receipts))
            self.assertFalse(receipts[-1]['originally_accepted_by_r2_controller'])
            for p,data in x.original_bytes.items():self.assertEqual(p.read_bytes(),data)
            (x.run/x.jobs[-1]['key']).mkdir() # never-submitted conflict detected
            with self.assertRaises(ValueError):r.ensure_unstarted(x)
            x.jobs=copy.deepcopy(x.jobs);x.jobs[23]['seconds']=300
            with self.assertRaises(ValueError):r.accept_existing(x)

    def test_corrupt_existing_and_all24_submission_paths_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);s=ctl.Slurm(x);calls=Mock()
            with patch.object(subprocess,'run',calls):
                for j in x.jobs[:24]:
                    with self.assertRaises(ValueError):s.submit(j)
                    with self.assertRaises(ValueError):ctl.permitted(j,x.jobs)
            calls.assert_not_called()
            with (x.run/x.jobs[23]['key']/'SEAL.json').open('ab') as f:f.write(b' ')
            with self.assertRaises(ValueError):r.accept_existing(x)

    def test_exact_association_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);j=x.jobs[23];row=ACTUAL['successful_rows'][23];h=r.read(x.run/j['key']/'HARDWARE.json')
            for host in ('gpu09','gpu09.cluster'):r.association(dict(h,hostname=host),j,row)
            for changes in ({'hostname':'gpu09.evil'},{'hostname':'gpu090.cluster'},{'slurm_job_id':'304219'},
                            {'device_name':'NVIDIA RTX A6000'},{'visible_device_count':2},{'cuda_available':False}):
                with self.assertRaises(ValueError):r.association(dict(h,**changes),j,row)
            for changes in ({'gpus':2},{'node':'gpu10'},{'node':'gpu09,gpu10'},{'allocated_cpus':8},{'seconds':1801}):
                with self.assertRaises(ValueError):r.association(h,j,dict(row,**changes))

    def test_reconciliation_unknown_changed_live_and_started_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);raw='\n'.join(ACTUAL['scheduler_raw']);r.validate_prior_scheduler(x,raw,'');r.ensure_unstarted(x)
            for wrong in (raw+'\n999|acv0-unknown|RUNNING',raw.replace('|160|','|161|')):
                with self.assertRaises(ValueError):r.validate_prior_scheduler(x,wrong,'')
            with self.assertRaises(ValueError):r.validate_prior_scheduler(x,raw,'999|acv0-other|RUNNING')
            r.write(x.control/'CONTROLLER-STARTED.json',{})
            with self.assertRaises(ValueError):r.ensure_unstarted(x)

    def test_complete315_dispatch_finalization_and_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp)
            with patch.object(r,'STOP_SHA',x.stop_sha):
                result,calls,gates=x.run_all()
                self.assertEqual(len(calls),315);self.assertEqual(calls[0]['key'],'collect-fit-505')
                self.assertFalse(set(j['key'] for j in calls)&set(j['key'] for j in x.jobs[:24]))
                self.assertEqual(gates,[('models',58),('analysis',314)])
                self.assertEqual(result['campaign_gpu_seconds'],180615);self.assertEqual(result['campaign_cpu_stage_seconds'],21600)
                claims=[v for v in r.lines(x.control/'CAMPAIGN-R3.jsonl') if v['event']=='claim']
                self.assertEqual(claims[0]['campaign_gpu_seconds'],3015)
                self.assertTrue(all(v['campaign_gpu_seconds']+v['remaining_gpu_reservation']<=220800 for v in claims))
                combined=final.accept(x,result);self.assertEqual(len(combined['allocations']),340)
                self.assertEqual(len(result['jobs']),339);self.assertEqual(r.read(x.run/'PRE-ANALYSIS-ACCOUNTING.json')['jobs'],result['jobs'][:-1])
                for name in ('run/STOP.json','r2-control-records/STOP-R2.json','r2-control-records/STOP-RESOLUTION.json',
                             'r3-control-records/STOP-RESOLUTION.json','run/provenance-failed-v2/FAILURE.json','run/collect-fit-1342/SEAL.json'):
                    self.assertIn(name,{n for n,_ in final.inventory(x)})
                r.write(x.control/'COMPUTE-COMPLETE.json',result);r.write(x.control/'COMBINED-CAMPAIGN.json',combined)
                r.write(x.run/'COMPUTE-COMPLETE.json',{'r3_control':str(x.control),'completion_sha256':r.sha(x.control/'COMPUTE-COMPLETE.json'),
                    'combined_campaign_sha256':r.sha(x.control/'COMBINED-CAMPAIGN.json'),'successful_unique_tasks':339,'campaign_allocations':340})
                r.write(x.control/'CONTROLLER-STARTED.json',{'pid':99999999,'start_ticks':'0'})
                with patch.object(r,'storage',return_value={}):final.archive(x)
                req=r.read(x.run/'final-preservation/BACKUP-REQUEST.json')
                from preserve import verify_tar
                verify_tar(x.run/'final-preservation/final.tar',req['members'])
                with patch.object(r,'storage',return_value={}):
                    with self.assertRaises(ValueError):final.archive(x)
                for p,data in x.original_bytes.items():self.assertEqual(p.read_bytes(),data)
                with self.assertRaises(ValueError):final.accept(x,dict(result,campaign_allocations=341))
                r.write(x.control/'STOP-R3.json',{'error':'new fault'})
                with self.assertRaises(ValueError):final.accept(x,result)

    def test_exact_stops_retained_new_changed_or_unresolved_block(self):
        for change in ('r1','r2','new-run','new-control'):
            with tempfile.TemporaryDirectory() as tmp:
                x=Fixture(tmp)
                with patch.object(r,'STOP_SHA',x.stop_sha):
                    _,a=r.accept_existing(x);x.resolution(a);r.stop_guard(x)
                    if change in ('r1','r2'):
                        path=x.run/'STOP.json' if change=='r1' else x.r2_control/'STOP-R2.json'
                        with path.open('ab') as f:f.write(b'changed')
                    else:r.write((x.run if change=='new-run' else x.control)/'NEW-STOP.json',{})
                    with self.assertRaises(ValueError):r.stop_guard(x)

    def test_new_failure_charged_and_never_retried(self):
        for mode in ('failed','ambiguous'):
            calls=[];events=[];jobs=c.grid()
            def submit(j):
                calls.append(j)
                if mode=='ambiguous':raise RuntimeError('submission ambiguous')
                return str(800000+len(calls))
            def wait(job,j):
                row={'job':job,'seconds':7,'gpus':1,'state':'FAILED','exit_code':'1:0','allocated_tres':'cpu=4,gres/gpu=1,mem=24G,node=1'}
                return row
            with self.assertRaises((ValueError,RuntimeError)):
                ctl.execute(jobs,ACTUAL['successful_rows'],NS(submit=submit,wait=wait),events.append,lambda *a:None,lambda *a:None,lambda:None)
            self.assertEqual(len(calls),1)
            if mode=='failed':self.assertEqual(events[-1]['campaign_gpu_seconds'],3022)

    def test_bad_existing_rows_and_gate_rejection_stop_dispatch(self):
        jobs=c.grid();calls=[]
        existing=copy.deepcopy(ACTUAL['successful_rows']);existing[-1]['seconds']=161
        with self.assertRaises(ValueError):
            ctl.execute(jobs,existing,NS(submit=calls.append),lambda _:None,lambda *a:None,lambda *a:None,lambda:None)
        self.assertFalse(calls)
        def submit(j):calls.append(j);return str(800000+len(calls))
        def wait(job,j):return {'job':job,'seconds':1,'gpus':j['gpu'],'state':'COMPLETED','exit_code':'0:0'}
        def gate(name,rows):raise ValueError('Synthetic rejected model freeze')
        with patch.object(r,'allocation_contract'):
            with self.assertRaisesRegex(ValueError,'rejected model freeze'):
                ctl.execute(jobs,ACTUAL['successful_rows'],NS(submit=submit,wait=wait),lambda _:None,lambda j,row:{},gate,lambda:None)
        self.assertEqual(len(calls),58);self.assertEqual(calls[-1]['key'],'fit-ordinary')

    def test_final_scheduler_exact340_and_no_live_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp)
            rows=ACTUAL['successful_rows']+[x.row(j,str(800000+i)) for i,j in enumerate(x.jobs[24:])]
            raw='\n'.join('|'.join(v['raw_scheduler'])+'|00:00:00|' for v in [ACTUAL['allocations'][0]]+rows)
            with patch.dict(os.environ,{'USER':'synthetic'}):
                for extra,queue,ok in [('', '',True),('\n999999|acv0-unknown|FAILED|1:0|1|4|cpu=4,gres/gpu=1,mem=24G,node=1|gpu09|a6000|normal-a6000|superworld|30|00:00:00|','',False),('','304220|acv0r2-collect-fit-1342|RUNNING',False)]:
                    with patch.object(subprocess,'run',side_effect=[NS(returncode=0,stdout=raw+extra),NS(returncode=0,stdout=queue)]):
                        if ok:self.assertEqual(len(final.scheduler_snapshot(x,{'jobs':rows})['allocations']),340)
                        else:
                            with self.assertRaises(ValueError):final.scheduler_snapshot(x,{'jobs':rows})

    def test_original_sources_storage_and_python39(self):
        for folder in ('bindings-r1','control-r2'):
            base=r.ROOT.parent/folder;manifest=r.read(base/'SOURCE-MANIFEST.json')
            for name,h in manifest['files'].items():self.assertEqual(r.sha((c.REPO/name) if folder=='bindings-r1' else base/name),h)
        for path in r.ROOT.glob('*.py'):ast.parse(path.read_text(encoding='utf8'),feature_version=(3,9))
        for code in (t.BOOTSTRAP,t.STAGE,t.LAUNCH,t.OBSERVE):ast.parse(code,feature_version=(3,9))
        import dispatch
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);base={'source_control_models_analysis':10,'full_live_reservation':1812000000,'inclusive_reservation':7248000000}
            with patch.object(dispatch,'storage',return_value=base):
                got=r.storage(x);self.assertEqual(got['r2_r3_source_and_control_bytes'],r.total(r.ROOT)+r.total(x.control)+r.total(x.r2_source)+r.total(x.r2_control))
                base['source_control_models_analysis']=499999999
                with self.assertRaises(ValueError):r.storage(x)

    def test_disabled_authority_and_binary_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'false.json';r.write(path,{'schema':'ACV0-control-only-r3','authorized':False,'instruction':'','binding':{}})
            for args in (['controller3.py','--approval',str(path)],['finalize3.py','archive','--approval',str(path)]):
                p=subprocess.run([sys.executable,'-B','-S',str(r.ROOT/args[0])]+args[1:],capture_output=True)
                self.assertNotEqual(p.returncode,0);self.assertIn(b'R3 continuation disabled',p.stderr)
        payload=bytes(range(256))*16;code='import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
        p=subprocess.run([sys.executable,'-B','-S','-c',t.BOOTSTRAP],input=t.envelope(code,payload,{'quoted':'a"b\'c\\d'}),capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.decode().strip(),r.hashlib.sha256(payload).hexdigest())
        with self.assertRaises(ValueError):t.envelope(code,b'x'*2000000,{})
        self.assertEqual(t.instruction(),'FIX IT AND RESUME IT')

if __name__=='__main__':unittest.main(verbosity=2)
