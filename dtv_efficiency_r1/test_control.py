"""Artificial fixtures only: real OS blocking mock, mocked Slurm, no models."""
import ast,json,os,subprocess,sys,tempfile,time,types,unittest
from pathlib import Path
from dtv_efficiency_r1 import profile as p,campaign,accept
from dtv_efficiency_r1.control import DOC,ORIGINAL_DOC,ROOT,load_bindings
from dtv_efficiency_r1.deadline import supervise,EvidenceList

class Clock:
    def __init__(self):self.now=0
    def __call__(self):return self.now
    def sleep(self,seconds):self.now+=seconds

def response(text='',code=0,stderr=''):return types.SimpleNamespace(stdout=text,stderr=stderr,returncode=code)
def allocation_row(state='COMPLETED',allocation='101',task='pusht-6101',elapsed=17):return f'{allocation}|dtveff0-{task}|{state}|0:0|{elapsed}|cpu=4,gres/gpu=1,mem=8G|gpu09|\n'

class Scheduler(unittest.TestCase):
    def run_script(self,script,repeat_last=False,charged=0):
        events=[];calls=[];clock=Clock();values=list(script)
        job=campaign.plan(load_bindings(),ROOT,DOC/'EXECUTION-APPROVAL.json',Path('/artificial/run'))[0]
        def invoke(cmd,timeout):
            calls.append(cmd)
            if cmd[0]=='sbatch':return response('101\n')
            if len(values)>1 or not repeat_last:return values.pop(0)
            return values[0]
        error=None;result=None
        try:result=campaign.dispatch_one(job,events.append,charged,invoke,clock,clock.sleep)
        except campaign.ControlFault as e:error=e
        self.assertEqual(sum(c[0]=='sbatch' for c in calls),1)
        self.assertEqual(len([e for e in events if e['event']=='submitted']),1)
        self.assertEqual({e['allocation_id'] for e in events if e['event'] in ('submitted','scheduler','terminal')},{'101'})
        return events,calls,clock,result,error
    def test_empty_empty_running_completed_same_allocation(self):
        events,_,clock,result,error=self.run_script([response(),response(),response(allocation_row('RUNNING')),response(allocation_row())])
        self.assertIsNone(error);self.assertEqual(result[0],17);self.assertEqual(clock.now,15)
        self.assertEqual(len([e for e in events if e['event']=='scheduler']),4)
        self.assertEqual(len([e for e in events if e['event']=='terminal']),1)
    def test_persistently_empty_is_scoped_unresolved_no_guess_charge(self):
        events,_,clock,result,error=self.run_script([response()],True,charged=37)
        self.assertIsNotNone(error);self.assertEqual(error.charged,37);self.assertEqual(clock.now,60)
        self.assertEqual(len([e for e in events if e['event']=='scheduler']),13)
        self.assertFalse(any(e['event']=='terminal' for e in events))
    def test_wrong_allocation_rejected_no_charge(self):
        _,_,_,_,error=self.run_script([response(allocation_row(allocation='102'))])
        self.assertIn('identity',str(error));self.assertEqual(error.charged,0)
    def test_wrong_task_rejected_no_charge(self):
        _,_,_,_,error=self.run_script([response(allocation_row(task='cube-6101'))])
        self.assertIn('identity',str(error));self.assertEqual(error.charged,0)
    def test_duplicate_matching_rows_rejected(self):
        _,_,_,_,error=self.run_script([response(allocation_row()+allocation_row())])
        self.assertIn('duplicate',str(error));self.assertEqual(error.charged,0)
    def test_terminal_failure_charge_carried_once_no_resubmit(self):
        events,_,_,_,error=self.run_script([response(allocation_row('FAILED',elapsed=23))],charged=37)
        self.assertEqual(error.charged,60)
        terminal=[e for e in events if e['event']=='terminal'];self.assertEqual(len(terminal),1)
        self.assertEqual(terminal[0]['elapsed_seconds'],23);self.assertEqual(terminal[0]['cumulative_gpu_seconds'],60)
    def test_command_error_not_grace_or_guessed_charge(self):
        events,_,clock,_,error=self.run_script([response('',1,'artificial accounting error')],charged=37)
        self.assertEqual(error.charged,37);self.assertEqual(clock.now,0)
        self.assertEqual(events[-1]['stderr'],'artificial accounting error');self.assertEqual(events[-1]['returncode'],1)
    def test_unknown_state_not_terminal(self):
        events,_,_,_,error=self.run_script([response(allocation_row('UNKNOWN'))])
        self.assertIn('nonterminal',str(error));self.assertFalse(any(e['event']=='terminal' for e in events))
    def test_live_suspended_not_terminal(self):
        events,_,_,result,error=self.run_script([response(allocation_row('SUSPENDED')),response(allocation_row())])
        self.assertIsNone(error);self.assertEqual(result[0],17);self.assertEqual(len([e for e in events if e['event']=='terminal']),1)
    def test_terminal_record_fault_does_not_reset_actual_charge(self):
        events=[];calls=[];clock=Clock()
        job=campaign.plan(load_bindings(),ROOT,DOC/'EXECUTION-APPROVAL.json',Path('/artificial/run'))[0]
        def invoke(cmd,timeout):
            calls.append(cmd);return response('101\n' if cmd[0]=='sbatch' else allocation_row('FAILED',elapsed=23))
        def append(event):
            events.append(event)
            if event['event']=='terminal':raise RuntimeError('artificial record cap fault')
        with self.assertRaises(campaign.ControlFault) as raised:campaign.dispatch_one(job,append,37,invoke,clock,clock.sleep)
        self.assertEqual(raised.exception.charged,60);self.assertEqual(sum(c[0]=='sbatch' for c in calls),1)
        self.assertEqual(len([e for e in events if e['event']=='terminal']),1)

class Deadline(unittest.TestCase):
    def test_mock_blocking_operation_killed_partial_evidence_preserved(self):
        with tempfile.TemporaryDirectory(prefix='dtveff-r1-artificial-') as name:
            root=Path(name)
            code="import json,signal,time,sys;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);p=Path(sys.argv[1]);p.joinpath('RECORDS.jsonl').write_text(json.dumps({'completed_artificial_call':1})+'\\n');time.sleep(30)"
            began=time.monotonic()
            result=supervise([sys.executable,'-c',code,name],root,work_seconds=1,termination_grace=.2,kill_wait=.2,started=began)
            self.assertEqual(result['fault'],'work_deadline');self.assertTrue(result['termination_sent']);self.assertFalse(result['unresolved_process'])
            if os.name=='posix':self.assertTrue(result['kill_sent'])
            self.assertLess(time.monotonic()-began,3)
            self.assertEqual(json.loads((root/'RECORDS.jsonl').read_text())['completed_artificial_call'],1)
            self.assertTrue((root/'FAILURE.json').is_file());self.assertTrue((root/'DEADLINE-FAULT.json').is_file())
            self.assertLess(sum(p.stat().st_size for p in root.iterdir()),4000000)
    def test_prior_startup_time_counts_no_deadline_reset(self):
        with tempfile.TemporaryDirectory(prefix='dtveff-r1-artificial-') as name:
            began=time.monotonic();start=began-.7
            result=supervise([sys.executable,'-c','import time;time.sleep(30)'],Path(name),work_seconds=1,started=start,termination_grace=.2,kill_wait=.2)
            self.assertEqual(result['accounting_start_monotonic'],start);self.assertEqual(result['fault'],'work_deadline')
            self.assertLess(time.monotonic()-began,.9)
    def test_expired_before_child_startup_does_not_start_work(self):
        with tempfile.TemporaryDirectory(prefix='dtveff-r1-artificial-') as name:
            result=supervise([sys.executable,'-c','raise RuntimeError("must not run")'],Path(name),work_seconds=.1,started=time.monotonic()-1)
            self.assertIsNone(result['child_pid']);self.assertEqual(result['fault'],'work_deadline')
    def test_normal_completion_and_startup_failure_artifacts(self):
        with tempfile.TemporaryDirectory(prefix='dtveff-r1-artificial-') as name:
            result=supervise([sys.executable,'-c','pass'],Path(name),work_seconds=2)
            self.assertIsNone(result['fault']);self.assertEqual(result['child_exit_code'],0);self.assertFalse((Path(name)/'FAILURE.json').exists())
        with tempfile.TemporaryDirectory(prefix='dtveff-r1-artificial-') as name:
            result=supervise(['/nonexistent/artificial-program'],Path(name),work_seconds=2)
            self.assertEqual(result['fault'],'child_startup');self.assertTrue((Path(name)/'FAILURE.json').is_file())

class Contract(unittest.TestCase):
    def test_generated_exact_minutes_and_full_grid_reservation(self):
        c=load_bindings();jobs=campaign.plan(c,ROOT,DOC/'EXECUTION-APPROVAL.json',Path('/artificial/run'))
        self.assertEqual(sum(j['reservation_seconds'] for j in jobs),7020)
        self.assertEqual(c['gpu_allocation_seconds_cap'],7200)
        self.assertTrue(all(j['reservation_seconds']==780 and '--time=00:13:00' in j['command'] for j in jobs))
        self.assertTrue(all('--no-requeue' in j['command'] and '--mem=8G' in j['command'] for j in jobs))
        self.assertEqual(c['work_deadline_seconds'],720);self.assertEqual(c['preservation_allowance_seconds'],60)
    def test_only_control_bindings_change_all_science_preserved(self):
        original=json.loads((ORIGINAL_DOC/'BINDINGS.json').read_text());corrected=load_bindings()
        for job in corrected['jobs']:job['wall_limit_seconds']=800
        for key in ('work_deadline_seconds','preservation_allowance_seconds','worker_wall_seconds','grid_reservation_seconds'):corrected.pop(key)
        self.assertEqual(corrected,original)
        self.assertEqual(original['blocks']*original['repetitions']*5*2,100)
        self.assertEqual((100+20+10+10)*len(original['jobs']),1260)
    def test_hot_path_helpers_and_entire_workload_unchanged_ast(self):
        old=ast.parse((ROOT/'dtv_efficiency/profile.py').read_text());new=ast.parse((ROOT/'dtv_efficiency_r1/profile.py').read_text())
        functions=lambda tree:{n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
        before,after=functions(old),functions(new)
        for name in ('order','quantile','summary','hardware','world_prefix','measured','output_hash','reset','equivalent','make_wrapper','raw'):
            self.assertEqual(ast.dump(before[name],include_attributes=False),ast.dump(after[name],include_attributes=False),name)
        old_work=next(n for n in ast.walk(before['main']) if isinstance(n,ast.With) and ast.unparse(n.items[0].context_expr)=='torch.inference_mode()')
        new_work=next(n for n in ast.walk(after['worker_main']) if isinstance(n,ast.With) and ast.unparse(n.items[0].context_expr)=='torch.inference_mode()')
        self.assertEqual(ast.dump(old_work,include_attributes=False),ast.dump(new_work,include_attributes=False))
        old_cmp=functions(ast.parse((ROOT/'dtv_efficiency/accept.py').read_text()))['comparisons']
        new_cmp=functions(ast.parse((ROOT/'dtv_efficiency_r1/accept.py').read_text()))['comparisons']
        self.assertEqual(ast.dump(old_cmp,include_attributes=False),ast.dump(new_cmp,include_attributes=False))
    def test_disabled_corrected_worker_gate(self):
        with self.assertRaisesRegex(RuntimeError,'disabled'):p.gate(DOC/'BINDINGS.json',json.loads((DOC/'EXECUTION-APPROVAL.json').read_text()))
    def test_full_grid_complete_outputs_and_independent_acceptance(self):
        c=load_bindings()
        with tempfile.TemporaryDirectory(prefix='dtveff-r1-artificial-') as name:
            run=Path(name);events=[];total=0
            for index,job in enumerate(c['jobs']):
                root=run/job['id'];root.mkdir();records=EvidenceList(root/'RECORDS.jsonl');audit=EvidenceList(root/'EQUIVALENCE.jsonl')
                for context in (0,1):
                    for arm in p.ARMS:
                        audit.append(dict(context=context,arm=arm,index_equivalence=True,rounds=30))
                        for level in ('A','B','C'):
                            if level=='A' and arm=='plain':continue
                            for block in range(5):
                                for repetition in range(2):records.append(dict(context=context,arm=arm,level=level,phase='warm',block=block,repetition=repetition,gpu_event_ms=2,synchronized_wall_ms=3))
                for arm in ('acid','forward','legacy_dtv'):
                    for repetition in range(2):records.append(dict(level='A_offline_reconciliation',arm=arm,repetition=repetition,candidate_sequences=15000,horizon_transitions=75000,transition_chunk=8192,gpu_event_ms=2,synchronized_wall_ms=3))
                allocation=str(1000+index);total+=17
                profile=dict(status='completed',job=job['id'],bindings_sha256=p.sha(DOC/'BINDINGS.json'),science_outcomes_computed=False,gpu='NVIDIA RTX 6000 Ada Generation',hostname='gpu09',python='3.11.10',torch='2.5.1+cu121',rss_high_water_bytes=1000000,wall_seconds=17,records=records,equivalence=audit,slurm_allocation_id=allocation,artificial=True)
                (root/'PROFILE.json').write_text(json.dumps(profile));(root/'SEAL.json').write_text(json.dumps(dict(job=job['id'],profile_sha256=p.sha(root/'PROFILE.json'))))
                (root/'SUPERVISOR-STARTED.json').write_text(json.dumps(dict(artificial=True)))
                (root/'SUPERVISION.json').write_text(json.dumps(dict(fault=None,child_exit_code=0,unresolved_process=False,elapsed_seconds=17,work_deadline_seconds=720,artificial=True)))
                p.seal_output(root,job['id'])
                self.assertLess(sum(f.stat().st_size for f in root.iterdir()),4000000)
                events.extend([dict(event='submitted',task=job['id'],allocation_id=allocation),dict(event='terminal',task=job['id'],allocation_id=allocation,state='COMPLETED',exit='0:0',elapsed_seconds=17,cumulative_gpu_seconds=total,node='gpu09',allocated_resources='gres/gpu=1')])
            (run/'DISPATCH.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
            profiles,terminal=accept.validate(run,c);self.assertEqual(len(profiles),9);self.assertEqual(len(terminal),9)
            # Remove no evidence: append a fault to make authentication reject.
            last=run/c['jobs'][-1]['id']/'SUPERVISION.json';last.write_text(last.read_text()+' ')
            with self.assertRaisesRegex(RuntimeError,'seal'):accept.validate(run,c)

if __name__=='__main__':unittest.main(verbosity=2)
