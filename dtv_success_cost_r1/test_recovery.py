"""Artificial control, complete-ledger and preservation integration regressions."""
import copy
import inspect
import json
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from dtv_success_cost.common import *
from dtv_success_cost import campaign as original, accept as original_accept, preserve as original_preserve
from dtv_success_cost_r1 import campaign,accept,common,analysis_entry,preserve
from dtv_success_cost.test_pipeline import Artificial,Authentication as OriginalAuthentication,Control,ClosedLoop

class Authentication(OriginalAuthentication):
    def test_preservation_deadline_preserves_fault_and_does_not_retry(self):
        # POSIX alarms are host-only. On Windows exercise the identical error
        # preservation path with an artificial signal interface, never edit it.
        import signal
        with patch.object(signal,'SIGALRM',14,create=True),patch.object(signal,'ITIMER_REAL',0,create=True),patch.object(signal,'signal',return_value=None),patch.object(signal,'setitimer',create=True):
            super().test_preservation_deadline_preserves_fault_and_does_not_retry()

class Recovery(unittest.TestCase):
    def mock(self,outputs,gpu=False,identity='analysis'):
        calls=[];events=[];charges=dict(gpu=0,cpu=178);now=[0.]
        job=dict(id=identity,gpu=gpu,wall_seconds=300 if gpu else 7200,command=['sbatch'])
        def call(command,timeout):
            calls.append(command);v=outputs.pop(0)
            if isinstance(v,Exception):raise v
            return types.SimpleNamespace(returncode=0,stdout=v,stderr='')
        return job,events,charges,calls,call,lambda:now[0],lambda s:now.__setitem__(0,now[0]+s)
    def run_mock(self,outputs,gpu=False,identity='analysis'):
        j,e,c,calls,call,clock,sleep=self.mock(outputs,gpu,identity)
        result=campaign.dispatch(j,e.append,c,call,clock,sleep)
        return result,e,c,calls
    def test_exact_cpu_placeholder_preserved_then_success(self):
        _,e,c,calls=self.run_mock(['10','10|allocation|PENDING|0:0|0||gpu03',
                                 '10|dtveff1-analysis|RUNNING|0:0|2|cpu=4,mem=8G,node=1|gpu03',
                                 '10|dtveff1-analysis|COMPLETED|0:0|7|cpu=4,mem=8G,node=1|gpu03'])
        self.assertEqual(c,dict(gpu=0,cpu=185));self.assertEqual(e[3]['stdout'],'10|allocation|PENDING|0:0|0||gpu03')
        self.assertEqual(sum(x[0]=='sbatch' for x in calls),1);self.assertIn('JobName%200',calls[1][-1])
    def test_cpu_placeholder_finite_eight_polls(self):
        j,e,c,calls,call,clock,sleep=self.mock(['10']+['10|allocation|PENDING|0:0|0||gpu03']*9)
        with self.assertRaisesRegex(campaign.ControlFault,'grace exhausted'):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(c['cpu'],178);self.assertEqual(len(calls),10)
    def test_cpu_wrong_placeholder_identity_state_resources_rejected(self):
        for row in ('11|allocation|PENDING|0:0|0||gpu03','10|wrong|PENDING|0:0|0||gpu03',
                    '10|allocation|RUNNING|0:0|0||gpu03','10|allocation|PENDING|0:0|1||gpu03',
                    '10|allocation|PENDING|0:0|0|gres/gpu=1|gpu03','10|allocation|PENDING|0:0|0||bad,node'):
            j,e,c,_,call,clock,sleep=self.mock(['10',row])
            with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
            self.assertEqual(c['cpu'],178)
    def test_cpu_grace_not_generic_task_permission(self):
        j,e,c,_,call,clock,sleep=self.mock(['10','10|allocation|PENDING|0:0|0||gpu03'],identity='unapproved')
        with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
    def test_failed_cpu_terminal_charged_and_retained(self):
        j,e,c,calls,call,clock,sleep=self.mock(['10','10|dtveff1-analysis|FAILED|1:0|8|cpu=4,mem=8G|gpu03'])
        with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(c['cpu'],186);self.assertEqual(e[-1]['event'],'terminal')
        self.assertEqual(sum(x[0]=='sbatch' for x in calls),1)
    def test_cpu_gpu_allocation_rejected_and_charged(self):
        j,e,c,_,call,clock,sleep=self.mock(['10','10|dtveff1-analysis|COMPLETED|0:0|8|cpu=4,gres/gpu=1|gpu09'])
        with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(c['cpu'],186)
    def test_ambiguous_timeout_never_repeated(self):
        j,e,c,calls,call,clock,sleep=self.mock([subprocess.TimeoutExpired('sbatch',30)])
        with self.assertRaisesRegex(campaign.ControlFault,'ambiguous'):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(len(calls),1);self.assertTrue(e[-1]['ambiguous']);self.assertEqual(c['cpu'],178)
    def test_gpu_grace_and_wrong_hardware_preserved(self):
        _,e,c,_=self.run_mock(['10','10|allocation|PENDING|0:0|0||gpu09','10|dtveff1-fixture|COMPLETED|0:0|17|gres/gpu=1|gpu09'],True,'fixture')
        self.assertEqual(c['gpu'],17)
        for node,resources in [('gpu10','gres/gpu=1'),('gpu09','gres/gpu=2'),('gpu09','cpu=4')]:
            j,e,c,_,call,clock,sleep=self.mock(['10',f'10|dtveff1-fixture|COMPLETED|0:0|17|{resources}|{node}'],True,'fixture')
            with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
            self.assertEqual(c['gpu'],17)
    def test_original_cpu_fault_still_reproduces_unmodified(self):
        j,e,c,_,call,clock,sleep=self.mock(['10','10|allocation|PENDING|0:0|0||gpu03'])
        with self.assertRaises(original.ControlFault):original.dispatch(j,e.append,c,call,clock,sleep)
    def test_remaining_exact_grid_and_workers_unchanged(self):
        c=load(DOC/'BINDINGS.json');old=original.commands(c,Path('/old'),Path('/run'))
        new=campaign.commands(c,Path('/old'),Path('/recovery'),Path('/run'))
        self.assertEqual(len(new),2881);self.assertEqual(new[:-1],old[1:-1])
        self.assertEqual(sum(j['gpu'] for j in new),2880);self.assertNotIn('preflight',[j['id'] for j in new])
        self.assertEqual(178+sum(j['wall_seconds'] for j in new if not j['gpu']),7378)
        self.assertEqual(sum(j['wall_seconds'] for j in new if j['gpu']),864000)
        self.assertIn('dtv_success_cost_r1.analysis_entry',new[-1]['command'][-1]);self.assertEqual(new[-1]['wall_seconds'],7200)
    def test_original_acceptance_and_estimator_logic_not_changed(self):
        # Compare the copied independent checks with the frozen originals except
        # for the explicitly dated lineage and event supplier changes.
        a=inspect.getsource(original_accept.accounting);b=inspect.getsource(accept.accounting_events)
        a=a.replace("def accounting(run,c,include_analysis=False):\n    events=[__import__('json').loads(line) for line in (Path(run)/'DISPATCH.jsonl').read_text().splitlines()]",
                    'def accounting_events(events,c,include_analysis=False):')
        self.assertEqual(a.strip(),b.strip())
        self.assertIs(accept.accept_worker,original_accept.accept_worker)
        self.assertIs(analysis_entry.analyze,__import__('dtv_success_cost.analysis',fromlist=['analyze']).analyze)
    def test_restarts_and_existing_success_never_submit(self):
        c=load(DOC/'BINDINGS.json')
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);location=run/'recovery-r1';location.mkdir();resolution=location/'STOP-RESOLUTION.json';write(resolution,{})
            campaign.begin(run,resolution)
            with self.assertRaisesRegex(RuntimeError,'already started'):campaign.begin(run,resolution)
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);(run/'recovery-r1').mkdir();(run/c['jobs'][0]['id']).mkdir()
            with self.assertRaisesRegex(RuntimeError,'existing evidence'):campaign.begin(run,Path('/unused'))
    def fixture_events(self):
        c=load(DOC/'BINDINGS.json');events=[]
        ids=['preflight']+[j['id'] for j in c['jobs']]+['analysis']
        for i,identity in enumerate(ids):
            allocation=str(i+1);cpu=identity in ('preflight','analysis');elapsed=178 if identity=='preflight' else 1
            resources='cpu=4,mem=8G'+('' if cpu else ',gres/gpu=1')
            events += [dict(event='submission_intent',task=identity),dict(event='submitted',task=identity,allocation_id=allocation),
                       dict(event='scheduler',allocation_id=allocation,returncode=0,stdout=f'{allocation}|dtveff1-{identity}|COMPLETED|0:0|{elapsed}|{resources}|gpu09'),
                       dict(event='terminal',task=identity,allocation_id=allocation,state='COMPLETED',exit='0:0',elapsed_seconds=elapsed),
                       dict(event='accepted',task=identity)]
            if i==9:events.append(dict(event='technical_tranche_passed',included_workers=9))
        return c,events
    def test_full_combined_2882_grid_analysis_inflight_and_gate(self):
        c,e=self.fixture_events();r=accept.accounting_events(e,c,True)
        self.assertEqual(r['unique_tasks'],2882);self.assertEqual(r['gpu_allocation_seconds'],2880);self.assertEqual(r['cpu_stage_allocation_seconds'],179)
        cut=next(i for i,r in enumerate(e) if r['event']=='submission_intent' and r['task']=='analysis')
        self.assertEqual(accept.accounting_events(e[:cut+2],c)['unique_tasks'],2881)
        bad=copy.deepcopy(e);g=next(v for v in bad if v['event']=='technical_tranche_passed');bad.remove(g);bad.append(g)
        with self.assertRaises(RuntimeError):accept.accounting_events(bad,c,True)
        for mutation in ('duplicate','charge','raw','allocation'):
            bad=copy.deepcopy(e)
            if mutation=='duplicate':bad.append(dict(event='submission_intent',task=c['jobs'][0]['id']))
            if mutation=='charge':bad[3]['elapsed_seconds']=7201
            if mutation=='raw':bad[2]['stdout']='wrong'
            if mutation=='allocation':bad[6]['allocation_id']='1'
            with self.assertRaises(RuntimeError):accept.accounting_events(bad,c,True)
    def test_dated_resolution_unknown_stop_and_old_evidence_change_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);(run/'preflight').mkdir();location=run/'recovery-r1';location.mkdir()
            write(run/'STOP.json',{});write(run/'DISPATCH.jsonl',{});write(run/'preflight/SEAL.json',{})
            write(run/'preflight/INPUT-AUTHENTICATION.json',{})
            r=dict(recovery_manifest_sha256='a'*64,authorization_sha256='b'*64)
            resolution=dict(original_stop_sha256=common.STOP_SHA,original_dispatch_sha256=common.LEDGER_SHA,preflight_seal_sha256=common.SEAL_SHA,
                            preflight_input_sha256=common.AUTH_SHA,terminal_row=common.ROW,**r,cpu_seconds=178,gpu_seconds=0,
                            successful_preflight_recomputed=False,scientific_changes=False,observed_unix=1.)
            write(location/'STOP-RESOLUTION.json',resolution)
            digests={'STOP.json':common.STOP_SHA,'DISPATCH.jsonl':common.LEDGER_SHA,'SEAL.json':common.SEAL_SHA,'INPUT-AUTHENTICATION.json':common.AUTH_SHA}
            with patch.object(common,'sha',side_effect=lambda p:digests[Path(p).name]),patch.object(common,'read_seal'):
                common.verify_resolution(run,r)
                write(location/'STOP-R1.json',{'error':'new'})
                with self.assertRaisesRegex(RuntimeError,'unresolved'):common.verify_resolution(run,r)
            with self.assertRaises(RuntimeError):common.verify_resolution(run,r)
    def test_combined_projection_is_dated_not_original_rewrite(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);location=run/'recovery-r1';location.mkdir();(run/'preflight').mkdir()
            write(location/'EXECUTION-APPROVAL.json',{});write(location/'STOP-RESOLUTION.json',{});write(run/'preflight/SEAL.json',{})
            old=[dict(event='submission_intent',task='preflight'),dict(event='submission_response',task='preflight'),dict(event='submitted',task='preflight',allocation_id='312920'),dict(event='scheduler',allocation_id='312920')]
            (run/'DISPATCH.jsonl').write_text('\n'.join(json.dumps(e) for e in old))
            carry=dict(event='carried_preflight_accepted',allocation_id='312920',elapsed_seconds=178,
                       seal_sha256=sha(run/'preflight/SEAL.json'),resolution_sha256=sha(location/'STOP-RESOLUTION.json'))
            (location/'DISPATCH-R1.jsonl').write_text(json.dumps(carry))
            before=sha(run/'DISPATCH.jsonl')
            with patch.object(accept,'verify_resolution',return_value={}):
                projected=accept.combined_events(run,{})
            self.assertEqual(sha(run/'DISPATCH.jsonl'),before);self.assertEqual(projected[-1]['supplier'],'R1 dated carry')
    def test_complete_footprint_includes_recovery_and_preserved_failures(self):
        c=load(DOC/'BINDINGS.json');new=campaign.commands(c,Path('/old'),Path('/r1'),Path('/run'))
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);location=run/'recovery-r1';location.mkdir();write(location/'STOP-RESOLUTION.json',dict(failure_preserved=True))
            campaign.footprint(c,run,new)
            with self.assertRaises(RuntimeError):campaign.footprint(dict(c,live_bytes=1),run,new)
        worst=sum(j['output_bytes']+j['log_bytes'] for j in new)+c['source_bytes']+c['control_bytes']+c['reused_model_bytes']+1000000
        self.assertLess(worst,c['live_bytes'])
        self.assertLess(c['live_bytes']+c['source_bytes']+2*c['archive_bytes'],c['inclusive_bytes'])
    def test_archive_preserves_nested_recovery_under_simple_roots(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);run=p/'run';(run/'recovery-r1/source').mkdir(parents=True)
            for x in ('STOP.json','DISPATCH.jsonl','recovery-r1/STOP-RESOLUTION.json','recovery-r1/source/control.py'):write(run/x,dict(original=True))
            rows=original_preserve.inventory({'run':run});archive=p/'final.tar'
            info=preserve.make_archive(archive,rows);self.assertEqual(info['members'],4);self.assertEqual(original_preserve.verify_archive(archive,rows),4)
            self.assertEqual(sha(archive),info['sha256'])
            with self.assertRaises(RuntimeError):preserve.make_archive(archive,rows)
    def test_finalization_uses_current_lineage_and_same_archive_contract(self):
        src=inspect.getsource(preserve.archive)
        self.assertIn('dtv_success_cost_r1.accept',src);self.assertIn('COMPUTE-COMPLETE.json',src)
        old=inspect.getsource(original_preserve.archive).replace('dtv_success_cost.accept','dtv_success_cost_r1.accept')
        self.assertEqual(old.strip(),src.strip())
    def test_r1_archive_deadline_retains_evidence_and_never_retries(self):
        import signal
        with tempfile.TemporaryDirectory() as d,patch.object(signal,'SIGALRM',14,create=True),patch.object(signal,'ITIMER_REAL',0,create=True),patch.object(signal,'signal',return_value=None),patch.object(signal,'setitimer',create=True) as timer,patch.object(preserve,'archive',side_effect=TimeoutError('artificial deadline')) as a:
            with self.assertRaises(TimeoutError):preserve.archive_bounded({},Path(d))
            self.assertEqual(a.call_count,1);self.assertTrue(load(Path(d)/'ARCHIVE-FAILURE.json')['partials_retained'])
            self.assertEqual(timer.call_args_list[0].args,(0,7200));self.assertEqual(timer.call_args_list[-1].args,(0,0))
    def test_analysis_adapter_actual_path_seals_unchanged_analysis_output(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);out=run/'analysis';out.mkdir();c=dict(models={},analysis={},jobs=[],analysis_bytes=40000000)
            with patch.object(analysis_entry,'accept_grid',return_value=([],{'technical':True})),patch.object(analysis_entry,'analyze',return_value={'artificial':True}) as a:
                analysis_entry.analysis(c,run,out);a.assert_called_once_with([],{})
            read_seal(out,'analysis');self.assertTrue(load(out/'REPORT.json')['artificial'])
    def test_false_original_capability_and_false_recovery_stay_disabled(self):
        with self.assertRaises(RuntimeError):gate(DOC/'EXECUTION-APPROVAL.json')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'disabled.json';write(p,{'study':'DTV-EFF1-R1','execute':False})
            with self.assertRaisesRegex(RuntimeError,'disabled'):common.recovery_gate(p)

if __name__=='__main__':unittest.main()
