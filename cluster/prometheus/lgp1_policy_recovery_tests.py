"""Synthetic recovery routing/accounting tests; no cluster or research access."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import lgp1_contract as c
import lgp1_policy_recovery as r
from lgp1_dispatch import Controller

class Recovery(unittest.TestCase):
    def test_exact_authority_and_no_cap_increase(self):
        a=dict(policy_recovery=r.contract());r.authorize(a)
        for field,value in (('prior_gpu_seconds',0),('optimizer_updates_to_repeat',1),('automatic_retry',True)):
            bad=dict(policy_recovery={**r.contract(),field:value})
            with self.assertRaises(RuntimeError):r.authorize(bad)
        self.assertEqual(sum(int(v[2]) for v in r.JOBS.values()),5877)
        self.assertEqual(5877+196*1200,241077)
        self.assertLess(241077,c.CAPS['gpu_seconds'])

    def test_all_seven_successes_route_to_original_roots(self):
        approved=dict(policy_recovery=r.contract())
        with patch.object(c,'read',return_value=approved):
            for spec in c.grid(list(range(32)))[:7]:
                expected=(r.CACHE_RUN if spec['kind']=='cache' else r.PRIOR)/spec['name']
                self.assertEqual(c.task_root(Path('/new'),spec),expected)
            spec=c.grid(list(range(32)))[7]
            self.assertEqual(c.task_root(Path('/new'),spec),Path('/new')/spec['name'])
        paths=r.roots(dict(source_sha256='a'*64))
        self.assertEqual(len(paths),len({p for _,p in paths}))
        self.assertIn(('validation-run',r.PRIOR),paths)
        self.assertEqual(len([p for n,p in paths if n.endswith('-run')]),3)

    def test_serial_remaining_chain_and_failed_attempt_accounting(self):
        specs=c.grid(list(range(32)));events=[];submitted=[];checked=[];stages=[]
        class Scheduler:
            def submit(self,s):submitted.append(s);return str(len(submitted))
            def wait(self,j,s):return dict(state='COMPLETED',exit_code='0:0',seconds=1)
        ctl=Controller(specs[7:],Scheduler(),events.append,lambda:0,checked.append,
                       lambda stage,rows:stages.append((stage,len(rows))))
        ctl.completed=[dict(task=s) for s in specs[:7]];ctl.gpu=5877
        final=ctl.run()
        self.assertEqual(len(submitted),197);self.assertEqual(final['jobs'],204)
        self.assertEqual(final['gpu_seconds'],5877+196);self.assertEqual(final['cpu_seconds'],1)
        self.assertEqual(stages,[('models',7),('evaluation',203)])
        self.assertEqual([s['kind'] for s in submitted[:4]],['technical']*4)
        self.assertTrue(all(s['kind'] not in ('cache','fit') for s in submitted))
        self.assertEqual(10+len(submitted),207)

    def test_technical_failure_cannot_release_main_grid(self):
        specs=c.grid(list(range(32)));submitted=[]
        class Scheduler:
            def submit(self,s):submitted.append(s);return '1'
            def wait(self,j,s):return dict(state='FAILED',exit_code='1:0',seconds=22)
        ctl=Controller(specs[7:],Scheduler(),lambda x:None,lambda:0,lambda s:None,lambda *a:None)
        ctl.completed=[dict(task=s) for s in specs[:7]];ctl.gpu=5877
        with self.assertRaisesRegex(RuntimeError,'Technical failure'):ctl.run()
        self.assertEqual(len(submitted),1);self.assertEqual(ctl.gpu,5899)
        with self.assertRaisesRegex(RuntimeError,'No automatic'):ctl.run()

    def test_aggregate_uses_original_fit_reports_and_complete_grid(self):
        import lgp1_aggregate as aggregate
        from lgp1_validation_recovery import MODEL
        specs=c.grid(list(range(32)));models={s['name']:MODEL for s in specs if s['kind']=='fit'}
        frozen=dict(unix=0,models=models,seals={n:MODEL for n in models})
        approval=dict(policy_recovery=r.contract(),input_sha256='inputs',source_sha256='source')
        seen=[]
        with tempfile.TemporaryDirectory() as t:
            run=Path(t)/'new';run.mkdir()
            (run/'DISPATCH.jsonl').write_text('\n'.join(json.dumps(dict(event='submitted',unix=1,task=s))
                for s in specs if s['kind'] in ('technical','evaluation')))
            def read(p):
                p=Path(p);seen.append(p)
                if p.name=='APPROVAL.json':return approval
                if p.name=='PRE-EVALUATION-FREEZE.json':return frozen
                if p.name=='PRE-ANALYSIS-ACCOUNTING.json':return {}
                if p.name=='INPUTS.json':return dict(references={str(i):{} for i in range(32)})
                if p.name=='REPORT.json':
                    self.assertEqual(p.parent.parent,r.PRIOR)
                    reused=p.parent.name=='fit-gmm-8301'
                    return dict(updates=12000,row_presentations=1536000,
                        optimizer_updates_this_allocation=0 if reused else 12000,
                        row_presentations_this_allocation=0 if reused else 1536000)
                raise AssertionError(str(p))
            def root(run,s):return r.reused_root(s) if s['kind'] in ('cache','fit') else run/s['name']
            def episodes(path,s,ref):return [dict(reference=s['reference'],horizon=h,family=s['family'],seed=s['seed'],success=0) for h in (75,150)]
            with patch.object(c,'read',side_effect=read),patch.object(c,'sha',return_value=MODEL),\
                 patch.object(c,'task_root',side_effect=root),patch.object(aggregate.verify,'episodes',side_effect=episodes),\
                 patch.object(aggregate.verify,'task',return_value=dict(source_sha256='source',approval_sha256=MODEL)):
                result=aggregate.aggregate(run,specs,Path('/synthetic'))
            self.assertEqual(len(result['rows']),384);self.assertEqual(len(result['source_effects']),32)
            self.assertEqual(len([p for p in seen if p.name=='REPORT.json']),6)

if __name__=='__main__':unittest.main()
