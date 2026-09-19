"""Artificial tensors/World protocol only; no pretrained model, physics or fit."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
import lgprb1_contract as c
import lgprb1_evaluate as ev
from lgprb1_analysis import summarize
from lgprb1_dispatch import execute
from lgp1_tensor import cem,project
from lgp1_runtime import Policy
from lgp1_lifecycle_tests import setup,Backend
from lgp1_endpoint import array_sha,verify_file
from e18_fresh_driver import FreshEpisode,computational_info

SOURCE=Path(__file__).resolve().parents[2]

def artificial(family='gmm'):
    w,f=setup(family,truncated_at=300);p=f(75,8301);w.close()
    initial=np.zeros(7);initial[0]=100
    def world():return setup(family,truncated_at=300)[0]
    modules=[p.model]
    def tensor_hash(ms):return '|'.join(array_sha(v.detach().numpy()) for m in ms for v in m.state_dict().values())
    return Backend(),p.model,p.stats,dict(file='/artificial/only',sha256='a'*64),initial,{75:np.zeros(7),150:np.zeros(7)},world,modules,tensor_hash

class BudgetTests(unittest.TestCase):
    def test_total_populations_prefix_rng_and_return(self):
        bank=torch.linspace(-.8,.8,9000).reshape(1,300,3,10)
        histories={}
        for n in (1,5,30):
            seen=[];g=torch.Generator().manual_seed(99)
            def cost(x):seen.append(x.clone());return x.square().sum((2,3))
            result,logs=cem(bank,cost,generator=g,project_fn=lambda x:project(x,[0,0],[1,1]),rounds=n)
            expected_generator=torch.Generator().manual_seed(99)
            for _ in range(n-1):torch.randn(bank.shape,generator=expected_generator)
            self.assertTrue(torch.equal(g.get_state(),expected_generator.get_state()))
            self.assertEqual(len(seen),n);self.assertEqual(len(logs),n)
            ix=torch.argsort(seen[-1].square().sum((2,3)),stable=True)[:,:30]
            mean=seen[-1][torch.arange(1)[:,None],ix].mean(1)
            expected=project(mean[:,None],[0,0],[1,1])[0][:,0]
            self.assertTrue(torch.equal(result,expected))
            if n==1:self.assertFalse(torch.equal(result,seen[-1][:,ix[0,0]]))
            histories[n]=seen
        for n in (1,5):
            for i in range(n):self.assertTrue(torch.equal(histories[n][i],histories[30][i]))

    def test_ties_and_no_best_candidate_return(self):
        bank=torch.arange(300,dtype=torch.float32)[None,:,None,None].expand(1,300,3,10)/300
        result,logs=cem(bank,lambda x:torch.zeros(1,300),generator=torch.Generator(),
            project_fn=lambda x:project(x,[0,0],[1,1]),rounds=1)
        self.assertEqual(logs[0]['elite_indices'],[list(range(30))])
        self.assertTrue(torch.equal(result,bank[:,:30].mean(1)))
        self.assertFalse(torch.equal(result,bank[:,0]))

    def test_budget_rejection(self):
        _,f=setup();p=f(75,8301)
        for n in (0,2,True,1.0,31):
            with self.assertRaisesRegex(RuntimeError,'budget'):
                Policy(p.backend,p.model,p.stats,75,8301,1269,populations=n)

    def test_actual_legacy_and_new_policy_banks_first_and_later_stage(self):
        legacy=ev.legacy_module(SOURCE)
        for family in c.old.FAMILIES:
            b,m,s,ref,initial,goals,world,_,_=artificial(family)
            info=dict(state=initial[None,None],pixels=np.zeros((1,1,2,2,3),np.uint8),goal=np.ones((1,1,2,2,3),np.uint8))
            for stage in (0,1,5):
                actions={};logs={}
                for n in (1,5,30,'legacy30'):
                    klass=legacy.Policy if n=='legacy30' else Policy
                    kw={} if n=='legacy30' else dict(populations=n,record_bank_hashes=True)
                    p=klass(b,m,s,75,8301,1269,**kw);p.elapsed=15*stage;p._stage_index=stage
                    # Common actual information/history, not forced future actions.
                    p.history.extend([np.zeros((2,2,3),np.uint8)]*2)
                    a=p.get_action(info);actions[n]=np.concatenate([a]+list(p._action_buffer),0);logs[n]=p.diagnostic_history[0]
                    self.assertEqual(len(logs[n]['rounds']),30 if n=='legacy30' else n)
                np.testing.assert_array_equal(actions[30],actions['legacy30'])
                self.assertEqual(logs[30]['rounds'],logs['legacy30']['rounds'])
                self.assertEqual(len({logs[n]['initial_unprojected_bank_sha256'] for n in (1,5,30)}),1)
                self.assertEqual(len({logs[n]['initial_projected_bank_sha256'] for n in (1,5,30)}),1)

    def test_default_policy_has_original_log_schema(self):
        _,f=setup();p=f(75,8301)
        p.get_action(dict(state=np.zeros((1,1,7)),pixels=np.zeros((1,1,2,2,3),np.uint8),goal=np.ones((1,1,2,2,3),np.uint8)))
        self.assertNotIn('initial_unprojected_bank_sha256',p.diagnostic_history[0])
        self.assertEqual(p.diagnostic_history[0]['cost_calls'],30)

    def test_complete_technical_compatibility_path_with_artificial_inputs(self):
        for family in c.old.FAMILIES:
            with patch.object(ev,'load',return_value=artificial(family)):
                result=ev.compatibility(SOURCE,Path('/unused'),dict(family=family,seed=8301,reference=1269),lambda:None)
            self.assertTrue(result['passed']);self.assertEqual(result['first_decisions'],8)
            self.assertEqual(result['physical_actions'],0);self.assertEqual(result['episodes'],0)

    def test_full_new_evaluation_path_and_endpoint_with_artificial_physics(self):
        for family in c.old.FAMILIES:
            for n in (1,5):
                with tempfile.TemporaryDirectory() as tmp,patch.object(ev,'load',return_value=artificial(family)),\
                     patch.object(ev,'verify_file',side_effect=lambda root,row,ref:verify_file(root,row,ref,authenticate_reference=False)):
                    result=ev.evaluate(SOURCE,Path(tmp),dict(family=family,seed=8301,reference=1269,populations=n),lambda:None)
                self.assertTrue(result['models_unchanged'])
                self.assertEqual([r['steps'] for r in result['rows']],[150,300])
                self.assertEqual([r['success'] for r in result['rows']],[0,0])
                for row in result['rows']:
                    h=row['horizon'];stages=row['stages']
                    self.assertEqual([s['remaining'] for s in stages],list(range(h,0,-15))*2)
                    self.assertEqual([s['elapsed'] for s in stages],list(range(0,2*h,15)))
                    self.assertTrue(all(s['cost_calls']==n and s['candidate_trajectories']==300*n for s in stages))
                    self.assertGreater(row['episode_execution_seconds'],row['reset_seconds'])

    def test_native_early_terminal_no_post_action_and_new_episode(self):
        for n in (1,5):
            world,f=setup(terminal_at=1);p=f(75,8301)
            e=FreshEpisode(world,lambda h,s:Policy(p.backend,p.model,p.stats,h,s,1269,populations=n))
            actions=[]
            for _ in range(2):
                e.start(dict(state=np.zeros(7),goal_state=np.zeros(7)),horizon=75,budget=150,seed=8301)
                self.assertTrue(e.advance());actions.append(world.infos['action'].copy())
                with self.assertRaises(RuntimeError):e.advance()
                e.policy.finish()
            np.testing.assert_array_equal(*actions);world.close()

class ContractTests(unittest.TestCase):
    def test_exact_grid_and_counts(self):
        refs=c.read(SOURCE/c.DOC/'REUSE.json')['references'];tasks=c.grid(refs)
        self.assertEqual(tasks,c.read(SOURCE/c.DOC/'GRID.json'))
        self.assertEqual(len({s['name'] for s in tasks}),387)
        self.assertEqual(sum(s['kind']=='evaluation' for s in tasks)*2,768)
        self.assertEqual(sum(s['gpu'] for s in tasks),386)
        self.assertEqual(sum(s['seconds'] for s in tasks if s['gpu']),70320)
        self.assertFalse(any(s['kind'] in ('cache','fit') for s in tasks))
        for bad in (refs[:-1],refs[:-1]+[refs[0]],refs[:-1]+[1600]):
            with self.assertRaises(RuntimeError):c.grid(bad)

    def test_serial_gates_and_no_reuse_submission(self):
        tasks=c.grid(list(range(32)));events=[];submitted=[];stages=[]
        class Scheduler:
            def submit(self,s):submitted.append(s);return str(len(submitted))
            def wait(self,j,s):return dict(state='COMPLETED',exit_code='0:0',seconds=1)
        result=execute(tasks,Scheduler(),events.append,lambda s:None,lambda n,r:stages.append((n,len(r))),lambda:None)
        self.assertEqual(len(submitted),387);self.assertEqual(stages,[('compatibility',2),('analysis',386)])
        self.assertEqual(result['gpu_seconds'],386);self.assertEqual(result['cpu_seconds'],1)
        self.assertFalse(any(s.get('populations')==30 for s in submitted))

    def test_failure_charged_before_stop_and_no_retry(self):
        events=[];submitted=[]
        class Scheduler:
            def submit(self,s):submitted.append(s);return '123'
            def wait(self,j,s):return dict(state='FAILED',exit_code='1:0',seconds=13)
        with self.assertRaisesRegex(RuntimeError,'Failure preserved'):
            execute(c.grid(list(range(32))),Scheduler(),events.append,lambda s:None,lambda *a:None,lambda:None)
        self.assertEqual(len(submitted),1);self.assertEqual(events[-1]['gpu_seconds'],13)

    def test_ambiguous_submit_stops_without_second_attempt(self):
        events=[]
        class Scheduler:
            def submit(self,s):raise TimeoutError('Unknown allocation state')
        with self.assertRaises(TimeoutError):execute(c.grid(list(range(32))),Scheduler(),events.append,lambda s:None,lambda *a:None,lambda:None)
        self.assertEqual([r['event'] for r in events],['claim','submission_unresolved'])

    def test_full_remaining_reservation_guard(self):
        bad=c.grid(list(range(32)));bad[0]['seconds']+=1
        with self.assertRaisesRegex(RuntimeError,'remaining reservations'):
            execute(bad,None,None,None,None,lambda:None)

    def test_host_imports_without_site_packages(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import lgprb1_dispatch,lgprb1_analysis,lgprb1_preserve,lgprb1_launch;assert 'numpy' not in sys.modules;assert 'torch' not in sys.modules"
        p=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(SOURCE/'cluster/prometheus')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_disabled_approval_before_execution_and_strict_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/c.DOC).mkdir(parents=True);(root/c.old.DOC).mkdir(parents=True)
            c.write(root/c.old.DOC/'DATA-ROLES.json',dict(development_reference_indices=list(range(32))))
            for p in (root/c.DOC/'PROTOCOL.md',root/c.DOC/'REUSE.json',root/c.DOC/'GRID.json'):p.write_text('synthetic')
            names=sorted(p for p in root.rglob('*') if p.is_file())
            (root/c.MANIFEST).write_text(''.join(c.sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in names))
            template=c.template(root);c.write(root/'APPROVAL-TEMPLATE.json',template)
            with self.assertRaisesRegex(RuntimeError,'disabled'):c.authorize(root,root/'APPROVAL-TEMPLATE.json')
            for key,val in [('source_sha256','f'*64),('new_main_episodes',770),('automatic_retry',True)]:
                bad={**template,'execution_authorized':True,key:val}
                with patch.object(c,'read',side_effect=lambda p:bad if Path(p).name=='APPROVAL-TEMPLATE.json' else json.loads(Path(p).read_text())):
                    with self.assertRaisesRegex(RuntimeError,'Exact separately'):c.authorize(root,root/'APPROVAL-TEMPLATE.json')
            (root/c.DOC/'PROTOCOL.md').write_text('changed')
            with self.assertRaisesRegex(RuntimeError,'Hash mismatch'):c.authorize(root,root/'APPROVAL-TEMPLATE.json')

    def test_real_disabled_template_blocks_all_execution_entrypoints(self):
        # Package-only extension of the same test; checkout has no template.
        if not (SOURCE/'APPROVAL-TEMPLATE.json').exists():return
        for script in ('lgprb1_launch.py','lgprb1_dispatch.py','lgprb1_worker.py'):
            args=[sys.executable,'-B',str(SOURCE/'cluster/prometheus'/script),'--source',str(SOURCE),'--approval',str(SOURCE/'APPROVAL-TEMPLATE.json')]
            if script!='lgprb1_launch.py':args+=['--run','/must-not-create']
            if script=='lgprb1_worker.py':args+=['--task','analysis']
            p=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertIn('Preparation disabled',p.stderr)
        self.assertFalse(Path('/must-not-create').exists())

    def test_legacy_bytes_and_remote_evidence(self):
        reuse=c.read(SOURCE/c.DOC/'REUSE.json')
        self.assertEqual(c.sha(SOURCE/c.DOC/'LEGACY-RUNTIME.py.txt'),reuse['legacy_runtime_sha256'])
        self.assertEqual(len(reuse['main_workers']),192);self.assertEqual(len(reuse['models']),6)
        remote=c.read(SOURCE/c.DOC/'REMOTE-BYTE-COMPATIBILITY.json')
        self.assertEqual(remote['verified_files'],17)
        self.assertTrue(all('\\' not in p for p in remote['hashes']))
        self.assertFalse(reuse['diagnostic_inventory']['saved_proposal_bank_hashes'])

class AnalysisTests(unittest.TestCase):
    def rows(self):
        return [dict(reference=r,populations=b,family=f,horizon=h,seed=s,
                success=int(f=='diffusion' and b==5))
                for r in range(32) for b in (1,5,30) for f in c.old.FAMILIES for h in (75,150) for s in c.old.SEEDS]
    def test_exact_paired_source_contrasts(self):
        result=summarize(self.rows())
        self.assertEqual(result['independent_sources'],32);self.assertEqual(len(result['strata']),36)
        self.assertEqual(result['changes_relative_to_30']['5']['mean'],1.)
        self.assertEqual(result['changes_relative_to_30']['5']['descriptive_interval'],[1.,1.])
        self.assertEqual(result['family_differences']['30']['mean'],0.)
        self.assertEqual(len(result['source_effects']),32)
    def test_incomplete_or_duplicate_reference_grid_rejected(self):
        rows=self.rows()
        for bad in (rows[:-1],rows[:-1]+[rows[0]]):
            with self.assertRaisesRegex(RuntimeError,'Complete 3-budget'):summarize(bad)

if __name__=='__main__':
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);unittest.main()
