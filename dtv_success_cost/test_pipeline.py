"""Artificial weights, native-interface doubles and mocked allocations only."""
import copy
import json
import math
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from dtv_success_cost.common import *
from dtv_success_cost import episode,analysis,campaign,preserve

class Artificial:
    def __init__(self,task='reacher',terminal=50,initial=False,fail=False):
        self.task=task;self.terminal=terminal;self.initial=initial;self.fail=fail;self.steps=0;self.closed=False;self.requests=0
    def reset(self):self.steps=0
    def sync(self):pass
    def evidence(self):
        target={'reacher':[0.,0.],'cube':[0.,0.,0.],'pusht':[100.,100.,100.,100.,0.,0.,0.]}[self.task]
        current=target.copy()
        if not(self.initial or self.steps>=self.terminal) or self.fail:current[0]+=100
        return dict(current=current,target=target)
    def native_success(self):return episode.success(self.task,self.evidence())
    def action(self):
        self.requests+=1
        plan=dict(solve_seconds=.01,populations=30,candidates=9000,return_rule='final_elite_mean',normalized_actions=[[0.,0.] for _ in range(25)]) if self.steps%25==0 else None
        return [[2.,3.]],plan
    def step(self,a):self.steps+=1;return self.steps>=self.terminal,False
    def action_list(self,a):return a[0]
    def decoder(self):return dict(mean=[2.,3.],scale=[1.,1.])
    def resources(self):return dict(rss_process_high_water_bytes=1000000,cuda_peak_allocated_bytes=0,cuda_peak_reserved_bytes=0)

class ClosedLoop(unittest.TestCase):
    def test_complete_trace_all_native_endpoints_and_cadence(self):
        for task in TASKS:
            e=episode.run_episode(Artificial(task), 'dtv30');r=episode.verify_episode(e)
            self.assertEqual(r['actions'],50);self.assertEqual(r['decisions'],2);self.assertTrue(e['success'])
    def test_early_terminal_no_postwork(self):
        a=Artificial(terminal=7);e=episode.run_episode(a,'dtv30');episode.verify_episode(e)
        self.assertEqual(a.steps,7);self.assertEqual(a.requests,7);self.assertEqual(len(e['plans']),1)
    def test_initial_success_zero_work_not_excluded(self):
        a=Artificial(initial=True);e=episode.run_episode(a,'dtv30');episode.verify_episode(e);self.assertEqual(a.steps,0)
    def test_adverse_failure_trace_retained(self):
        e=episode.run_episode(Artificial(terminal=5,fail=True),'dtv30');episode.verify_episode(e)
        self.assertFalse(e['success']);self.assertEqual(e['termination'],'terminated');self.assertGreater(e['planning_seconds'],0)
    def test_mutated_action_endpoint_or_timing_rejected(self):
        e=episode.run_episode(Artificial(),'dtv30')
        for mutate in (lambda x:x['actions'][0]['action'].__setitem__(0,99),lambda x:x.__setitem__('success',False),lambda x:x.__setitem__('planning_seconds',99)):
            c=copy.deepcopy(e);mutate(c)
            with self.assertRaises(RuntimeError):episode.verify_episode(c)
    def test_native_boundary_strict_no_relaxed_endpoints(self):
        self.assertFalse(episode.success('reacher',dict(current=[.05,0],target=[0,0])))
        self.assertTrue(episode.success('cube',dict(current=[.04,0,0],target=[0,0,0])))
        self.assertFalse(episode.success('pusht',dict(current=[20,0,0,0,0,0,0],target=[0]*7)))

def records(n=3):
    out=[]
    for t in TASKS:
        for s in range(n):
            for seed in SEEDS:
                for a in CONFIGS:
                    # Includes deliberate DTV losses with higher costs. Passing
                    # technical tests never depends on a favorable efficacy toy.
                    out.append(dict(task=t,source=s,parent=s,scorer_seed=seed,config=a,success=a!='dtv30',planning_seconds=2 if a=='dtv30' else 1,solve_seconds=1,episode_operational_seconds=3,episode_elapsed_including_audit_seconds=3.5,first_decision_seconds=1,decisions=1,actions=5,audit_seconds=.1,process_cpu_seconds=.2,decision_observation_to_action_seconds=1,later_decision_seconds=0,reset_seconds=.1,environment_construction_seconds=.2))
    return out

class Analysis(unittest.TestCase):
    def test_complete_maximum_grid_analysis_output_with_setup_and_resources(self):
        c=load(DOC/'BINDINGS.json');rows=records(320)
        for r in rows:
            for k,v in list(r.items()):
                if isinstance(v,float):r[k]=123.45678901234567
            r.update(initial_success=False,resources=dict(rss_process_high_water_bytes=8589934592,cuda_peak_allocated_bytes=4000000000,cuda_peak_reserved_bytes=6000000000))
        result=analysis.analyze(rows,dict(c['analysis'],bootstrap=2))
        result['worker_setup_and_authentication']={j['id']:dict(identity=j['id'],bindings_sha256='a'*64,authentication_seconds=12.345678901234567,setup_model_input_seconds=12.345678901234567,checkpoints={a:'b'*64 for a in ('acid','diffusion','forward')},world_checkpoint='c'*64,source_input_sha256='d'*64,hostname='gpu09.cluster',allocation_id='9999999',gpu='NVIDIA RTX 6000 Ada Generation',wall_seconds=299.123456789012345,automatic_retry=False,warmup_research_episodes=0) for j in c['jobs']}
        byte_count=len(json.dumps(result,separators=(',',':')).encode())
        self.assertEqual(result['episode_count'],23040);self.assertLess(byte_count+1000000,c['analysis_bytes'])
        print('COMPLETE_ANALYSIS_FOOTPRINT '+json.dumps(dict(artificial=True,episodes=len(rows),report_bytes=byte_count,analysis_reserved_bytes=c['analysis_bytes'])))
    def test_adverse_source_clustered_full_axes_no_success_filter(self):
        c=load(DOC/'BINDINGS.json');spec=dict(c['analysis'],bootstrap=20)
        r=analysis.analyze(records(),spec)
        self.assertEqual(r['episode_count'],216);self.assertEqual(len(r['fixed_checkpoint_blocks']),72)
        self.assertEqual(r['contrasts']['equal_task:dtv30-minus-acid30:success']['estimate'],-1)
        self.assertEqual(r['contrasts']['equal_task:dtv30-minus-acid30:planning_seconds']['estimate'],1)
        self.assertEqual(len(r['source_effects']['pusht:acid30']),3)
        self.assertIn('planning_seconds_nominal95',r['points']['equal_task:dtv30'])
    def test_duplicates_and_missing_seeds_rejected(self):
        spec=dict(load(DOC/'BINDINGS.json')['analysis'],bootstrap=1)
        with self.assertRaises(RuntimeError):analysis.analyze(records()+[records()[0]],spec)
        with self.assertRaises(RuntimeError):analysis.analyze(records()[1:],spec)
    def test_precision_small_effects_assumes_losses(self):
        self.assertEqual(len(analysis.precision()),13)
        self.assertTrue(all(r['loss_probability']>0 for r in analysis.precision()))
        for r in analysis.precision():self.assertAlmostEqual(r['gain_probability']+r['loss_probability'],r['discordance'])
        row=next(r for r in analysis.precision() if r['discordance']==.1 and r['difference']==.02)
        self.assertGreater(row['task_nominal_halfwidth'],.03)

class Control(unittest.TestCase):
    def test_canonical_worker_namespace_and_no_child_repeat(self):
        from dtv_success_cost import worker
        c=load(DOC/'BINDINGS.json');job=c['jobs'][0]['id']
        with tempfile.TemporaryDirectory() as d,patch.object(worker,'run_namespace',return_value=Path(d)):
            args=types.SimpleNamespace(job=job,output=Path(d)/job,run=None,child=False);worker.namespace(c,args)
            args.output=Path(d)/'other'
            with self.assertRaises(RuntimeError):worker.namespace(c,args)
            args.output=Path(d)/job;args.output.mkdir();args.child=True
            with patch.dict(worker.os.environ,{'DTVEFF_SUPERVISOR_PID':str(worker.os.getppid())}):
                worker.namespace(c,args);write(args.output/'completed.json',{})
                with self.assertRaises(RuntimeError):worker.namespace(c,args)
    def test_remote_bindings_posix_and_cohort_whole_parent_exclusion(self):
        c=load(DOC/'BINDINGS.json');roles=load(DOC/'ROLE-RECONCILIATION.json')
        paths=[c['container']['path']]+[r['path'] for r in c['runtime']+c['historical_sources']+c['preservation_inputs']]
        for s in c['models'].values():paths+=[s['dataset'],s['world_checkpoint']]+[m['checkpoint'] for m in s['models'].values()]
        self.assertTrue(all(p.startswith('/lustreFS/') and '\\' not in p for p in paths))
        for t in TASKS:
            selected=[r['parent_id'] for r in c['cohort'][t]]
            self.assertEqual(len(set(selected)),320);self.assertTrue(set(selected)<=set(roles[t]['eligible_parents']))
            self.assertFalse(set(selected)&{i for r in roles[t]['evidence'] for i in r['parent_ids']})
    def test_intervening_metadata_assignment_blocks_without_new_payload(self):
        from dtv_success_cost.roles import inventory,verify
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'manifests').mkdir();(p/'manifests/a.tsv').write_text('parent\n3\n')
            c=dict(role_inventory=inventory(p));verify(c,p)
            (p/'manifests/new.tsv').write_text('parent\n7\n')
            with self.assertRaisesRegex(RuntimeError,'intervening'):verify(c,p)
    def test_exact_full_grid_and_integer_minute_resources(self):
        c=load(DOC/'BINDINGS.json');jobs=campaign.commands(c,DOC/'EXECUTION-APPROVAL.json',Path('/unused'))
        self.assertEqual(len(jobs),2882);self.assertEqual(sum(j['gpu'] for j in jobs),2880)
        self.assertEqual(len(set(j['id'] for j in jobs)),2882)
        for j in jobs:
            self.assertIn('--time='+('00:05:00' if j['gpu'] else '02:00:00'),j['command'])
        self.assertEqual(c['gpu_seconds'],864000);self.assertEqual(c['cpu_seconds'],14400)
        self.assertEqual(len({(j['task'],j['source_index'],j['scorer_seed'],a) for j in c['jobs'] for a in j['configs']}),23040)
        self.assertEqual({j['source_index'] for j in c['jobs'][:9]},{0})
        self.assertEqual({j['task'] for j in c['jobs'][:9]},set(TASKS))
    def test_capability_disabled_before_payloads(self):
        with self.assertRaisesRegex(RuntimeError,'disabled'):gate(DOC/'EXECUTION-APPROVAL.json')
    def mock_dispatch(self,outputs):
        calls=[];events=[];charges=dict(gpu=0,cpu=0);now=[0.]
        j=dict(id='fixture',gpu=True,wall_seconds=300,command=['sbatch'])
        def call(command,timeout):calls.append(command);x=outputs.pop(0);return types.SimpleNamespace(returncode=0,stdout=x,stderr='')
        def sleep(s):now[0]+=s
        return j,events,charges,calls,call,lambda:now[0],sleep
    def test_visibility_and_terminal_failure_charged_once(self):
        args=self.mock_dispatch(['9','', '9|dtveff1-fixture|FAILED|1:0|17|gres/gpu=1|gpu09|'])
        j,e,c,calls,call,clock,sleep=args
        with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(c['gpu'],17);self.assertEqual(sum(x[0]=='sbatch' for x in calls),1)
        self.assertEqual(e[-1]['event'],'terminal')
    def test_missing_status_bounded_and_no_charge_fabricated(self):
        j,e,c,calls,call,clock,sleep=self.mock_dispatch(['9']+['']*13)
        with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(c['gpu'],0);self.assertLessEqual(len(calls),14)
    def test_wrong_task_terminal_charge_preserved(self):
        j,e,c,calls,call,clock,sleep=self.mock_dispatch(['9','9|wrong|COMPLETED|0:0|12|gres/gpu=1|gpu09|'])
        with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(c['gpu'],12)
    def test_wrong_node_or_gpu_rejected(self):
        for node,resources in [('gpu10','gres/gpu=1'),('gpu09','cpu=4')]:
            j,e,c,_,call,clock,sleep=self.mock_dispatch(['9',f'9|dtveff1-fixture|COMPLETED|0:0|12|{resources}|{node}|'])
            with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
    def test_ambiguous_submission_never_repeated(self):
        j,e,c,calls,call,clock,sleep=self.mock_dispatch(['not-an-id'])
        with self.assertRaises(campaign.ControlFault):campaign.dispatch(j,e.append,c,call,clock,sleep)
        self.assertEqual(len(calls),1);self.assertEqual(c['gpu'],0)
    def test_full_future_footprint_fits_and_failures_retained(self):
        c=load(DOC/'BINDINGS.json');j=campaign.commands(c,Path('/approval'),Path('/run'))
        with tempfile.TemporaryDirectory() as d:
            campaign.footprint(c,Path(d),j)
            bad=dict(c,live_bytes=1)
            with self.assertRaises(RuntimeError):campaign.footprint(bad,Path(d),j)
        # Complete worker, logs, analysis, metadata, models and archive reservations.
        worst=sum(r['output_bytes']+r['log_bytes'] for r in j)+c['source_bytes']+c['control_bytes']+c['reused_model_bytes']
        self.assertLess(worst,c['live_bytes']);self.assertLess(c['live_bytes']+2*c['archive_bytes'],c['inclusive_bytes'])

class Authentication(unittest.TestCase):
    def test_saved_input_to_native_initial_endpoint_all_tasks(self):
        import numpy as np
        from dtv_success_cost.accept import verify_input_endpoints
        for task in TASKS:
            e=episode.run_episode(Artificial(task,fail=True),'dtv30');keys={'pusht':('initial_state','target_state'),'reacher':('initial_qpos','target_qpos'),'cube':('initial_privileged_block_0_pos','target_privileged_block_0_pos')}[task]
            with tempfile.TemporaryDirectory() as d:
                np.savez(Path(d)/'SOURCE-INPUT.npz',goal_pixels=np.zeros((224,224,3),dtype=np.uint8),**{keys[0]:np.array(e['initial']['current']),keys[1]:np.array(e['initial']['target'])})
                verify_input_endpoints(d,task,[e]);bad=copy.deepcopy(e);bad['initial']['target'][0]+=1
                with self.assertRaises(RuntimeError):verify_input_endpoints(d,task,[bad])
    def test_real_worker_seal_trace_readback_and_independent_acceptance(self):
        from dtv_success_cost.accept import accept_worker
        c=load(DOC/'BINDINGS.json');job=c['jobs'][0];spec=c['models'][f'{job["task"]}-{job["scorer_seed"]}']
        with tempfile.TemporaryDirectory() as d:
            import numpy as np
            root=Path(d);out=root/job['id'];out.mkdir()
            initial=Artificial(task=job['task'],terminal=7,fail=True).evidence()
            np.savez(out/'SOURCE-INPUT.npz',goal_pixels=np.zeros((224,224,3),dtype=np.uint8),initial_state=np.array(initial['current']),target_state=np.array(initial['target']))
            for config in CONFIGS:
                journal=[];e=episode.run_episode(Artificial(task=job['task'],terminal=7,fail=True),'dtv30',journal=journal.append)
                e.update(config=config,source=job['source_index'],parent=c['cohort'][job['task']][job['source_index']]['parent_id'],scorer_seed=job['scorer_seed'],planner_seed=job['planner_seed'])
                for p in e['plans']:p.update(populations=int(config[-2:]),candidates=int(config[-2:])*300)
                for r in journal:
                    if r['event']=='action_intent' and r['plan']:r['plan'].update(populations=int(config[-2:]),candidates=int(config[-2:])*300)
                write(out/(config+'.json'),e)
                (out/(config+'.trace.jsonl')).write_text('\n'.join(json.dumps(r) for r in journal)+'\n')
            write(out/'WORKER.json',dict(identity=job['id'],bindings_sha256=sha(DOC/'BINDINGS.json'),allocation_id='9',hostname='gpu09',gpu='NVIDIA RTX 6000 Ada Generation',checkpoints={a:m['checkpoint_sha256'] for a,m in spec['models'].items()},world_checkpoint=spec['world_sha256'],source_input_sha256=sha(out/'SOURCE-INPUT.npz')))
            seal(out,job['id']);accepted=accept_worker(c,job,root,'9');self.assertEqual(len(accepted),8)
            self.assertTrue(all(not e['success'] for e in accepted))
            with self.assertRaises(RuntimeError):accept_worker(c,job,root,'10')
    def test_complete_grid_raw_accounting_gate_and_duplicate_fault(self):
        from dtv_success_cost.accept import accounting
        c=load(DOC/'BINDINGS.json');events=[]
        ids=['preflight']+[j['id'] for j in c['jobs']]+['analysis']
        for i,identity in enumerate(ids):
            allocation=str(i+1);cpu=identity in ('preflight','analysis');resources='cpu=4,mem=8G'+('' if cpu else ',gres/gpu=1')
            events+= [dict(event='submission_intent',task=identity),dict(event='submitted',task=identity,allocation_id=allocation),
                      dict(event='scheduler',allocation_id=allocation,returncode=0,stdout=f'{allocation}|dtveff1-{identity}|COMPLETED|0:0|1|{resources}|gpu09|'),
                      dict(event='terminal',task=identity,allocation_id=allocation,state='COMPLETED',exit='0:0',elapsed_seconds=1),dict(event='accepted',task=identity)]
            if i==9:events.append(dict(event='technical_tranche_passed',included_workers=9))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'DISPATCH.jsonl';p.write_text('\n'.join(json.dumps(e) for e in events))
            receipt=accounting(Path(d),c,True);self.assertEqual(receipt['unique_tasks'],2882);self.assertEqual(receipt['gpu_allocation_seconds'],2880)
            preceding=accounting(Path(d),c,False);self.assertEqual(preceding['unique_tasks'],2881);self.assertEqual(preceding['cpu_stage_allocation_seconds'],1)
            p.write_text(p.read_text()+'\n'+json.dumps(dict(event='submission_intent',task=ids[1])))
            with self.assertRaises(RuntimeError):accounting(Path(d),c,True)
    def test_save_readback_seal_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);write(p/'data.json',dict(x=3));seal(p,'fixture');read_seal(p,'fixture')
            with self.assertRaises(FileExistsError):write(p/'data.json',dict(x=4))
            (p/'data.json').write_text('{}')
            with self.assertRaises(RuntimeError):read_seal(p,'fixture')
    def test_archive_inventory_whole_and_every_member(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);root=p/'source';root.mkdir();write(root/'a.json',dict(x=3))
            rows=preserve.inventory(dict(source=root));a=p/'final.tar';receipt=preserve.make_archive(a,rows)
            self.assertEqual(receipt['sha256'],sha(a));self.assertEqual(preserve.verify_archive(a,rows),1)
            with self.assertRaises(RuntimeError):preserve.make_archive(a,rows)
            bad=copy.deepcopy(rows);bad[0]['sha256']='0'*64
            with self.assertRaises(RuntimeError):preserve.verify_archive(a,bad)
    def test_archive_root_escape_and_missing_members_rejected(self):
        with self.assertRaises(RuntimeError):preserve.inventory({'nested/root':Path('.')})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);write(p/'x',{});rows=preserve.inventory({'x':p/'x'});a=p/'a.tar';preserve.make_archive(a,rows)
            with self.assertRaises(RuntimeError):preserve.verify_archive(a,[])
    def test_preservation_request_paths_caps_and_bindings(self):
        c=load(DOC/'BINDINGS.json');run=run_namespace(c).as_posix();p=run+'/final-preservation/BACKUP-REQUEST.json'
        request=dict(study='DTV-EFF1',run=run,remote_archive=run+'/final-preservation/final.tar',bindings_sha256=sha(DOC/'BINDINGS.json'),package_sha256='a'*64,cohort_sha256=sha(DOC/'COHORT.json'),
                     archive=dict(bytes=10240,sha256='b'*64,members=1),inventory=[dict(path='run/x',bytes=3,sha256='c'*64)])
        original=preserve.sha
        with patch.object(preserve,'sha',side_effect=lambda x:'a'*64 if Path(x).name=='PACKAGE-MANIFEST.json' else original(x)):
            preserve.validate_request(request,p,c)
            for mutate in (lambda r:r.__setitem__('remote_archive','/unrelated/file'),lambda r:r['inventory'][0].__setitem__('path','run/../private'),lambda r:r['archive'].__setitem__('bytes',c['archive_bytes']+1),lambda r:r.__setitem__('bindings_sha256','d'*64)):
                bad=copy.deepcopy(request);mutate(bad)
                with self.assertRaises(RuntimeError):preserve.validate_request(bad,p,c)
    def test_preservation_deadline_preserves_fault_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(preserve,'archive',side_effect=TimeoutError('artificial deadline')) as call:
                with self.assertRaises(TimeoutError):preserve.archive_bounded({},Path(d))
                self.assertEqual(call.call_count,1);self.assertTrue(load(Path(d)/'ARCHIVE-FAILURE.json')['partials_retained'])
    def test_complete_worker_schema_under_output_limit(self):
        # Maximal 50-action trace for every task, expanded to eight configurations.
        for task in TASKS:
            e=episode.run_episode(Artificial(task,fail=True),'dtv30')
            dimension=len(load(DOC/'BINDINGS.json')['models'][task+'-6101']['decoder']['diffusion']['actual_mean'])
            # Long, finite FP32 values at the true task-specific action dimension,
            # 50 endpoint/timing rows, two 25-action plans, report plus journal.
            for r in e['actions']:r['action']=[.12345678901234567]*dimension
            for p in e['plans']:p['normalized_actions']=[[.12345678901234567]*dimension for _ in range(25)]
            self.assertLess(len(json.dumps(e))*8*2+200000+100000,1000000)

if __name__=='__main__':unittest.main()
