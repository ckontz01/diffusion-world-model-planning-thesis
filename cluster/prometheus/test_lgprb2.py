"""Artificial-only RB2 contracts, actual policy/CEM and pinned World methods."""
import copy,json,subprocess,sys,tempfile,unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
import lgprb2_contract as c
import lgprb2_evaluate as ev
from lgprb2_analysis import summarize
from lgprb2_dispatch import execute
from lgprb2_prepare import role_inventory
from lgp1_endpoint import verify_file,array_sha
from lgp1_lifecycle_tests import setup,Backend
from test_lgprb1 import artificial
import lgprb1_evaluate as rb1ev

SOURCE=Path(__file__).resolve().parents[2]

class ContractTests(unittest.TestCase):
    def test_roles_exact_no_new_payload_read(self):
        roles,pins=role_inventory(SOURCE);a=c.allocate(roles);saved=c.read(SOURCE/c.DOC/'DATA-ROLES.json')
        self.assertEqual((a['eligible_count'],a['excluded_union_count']),(1280,320))
        self.assertEqual(a['ordered_references'],saved['ordered_references']);self.assertEqual(pins,saved['source_record_hashes'])
        self.assertEqual(a['allocation_digest'],'865418138af0f3858f3a677008f717a724bf7ac2bf72881d909c9d0b79bcd000')
        selected=set(a['ordered_references']);excluded=set().union(*(set(v) for v in roles.values()))
        self.assertFalse(selected&excluded);self.assertLess(max(selected),1600)
        for bad in ({'all':list(range(1100))},{'wrong':[1600]}):
            with self.assertRaises(RuntimeError):c.allocate(bad)

    def test_grid_balance_and_exact_identities(self):
        refs=c.read(SOURCE/c.DOC/'DATA-ROLES.json')['ordered_references'];g=c.grid(refs)
        self.assertEqual(g,c.read(SOURCE/c.DOC/'GRID.json'));self.assertEqual(len(g),1537)
        self.assertEqual(sum(t['seconds'] for t in g if t['gpu']),460800)
        cells=[(t['reference'],t['seed'],v['family'],v['populations'],v['horizon']) for t in g[:-1] for v in t['episodes']]
        self.assertEqual(len(cells),len(set(cells)));self.assertEqual(len(cells),12288)
        self.assertEqual(sum(t['technical_tranche'] for t in g[:-1]),4)
        for pos in range(8):self.assertEqual(set(Counter(c.cell_name(t['episodes'][pos]) for t in g[:-1]).values()),{192})
        for bad in (refs[:-1],refs[:-1]+[refs[0]],refs[:-1]+[1600]):
            with self.assertRaises(RuntimeError):c.grid(bad)

    def test_remote_paths_are_posix_and_only_selected_payloads(self):
        lock=c.read(SOURCE/c.DOC/'INPUTS.json');roles=c.read(SOURCE/c.DOC/'DATA-ROLES.json')
        self.assertEqual(set(lock['references']),set(map(str,roles['ordered_references'])))
        for r,v in lock['references'].items():
            self.assertTrue(v['file'].startswith('/lustreFS/'));self.assertNotIn('\\',v['file'])
            self.assertEqual(lock['files'][v['file']],v['sha256']);self.assertIn(v['file'],lock['payload_files'])
        self.assertEqual(c.digest(lock['references']),roles['selected_identity_digest'])

    def test_dispatch_complete_tranche_and_analysis(self):
        events=[];stages=[];calls=[]
        class Scheduler:
            def submit(self,s):calls.append(s);return str(len(calls))
            def wait(self,j,s):return dict(state='COMPLETED',exit_code='0:0',seconds=1)
        result=execute(c.grid(list(range(512))),Scheduler(),events.append,lambda s:None,lambda n,r:stages.append((n,len(r))),lambda:None)
        self.assertEqual(stages,[('technical',4),('analysis',1536)]);self.assertEqual(len(calls),1537)
        self.assertEqual((result['gpu_seconds'],result['cpu_seconds']),(1536,1))

    def test_failed_first_or_fifth_charged_and_no_retry(self):
        for failed in (1,5):
            events=[];calls=[]
            class Scheduler:
                def submit(self,s):calls.append(s);return str(len(calls))
                def wait(self,j,s):return dict(state='FAILED' if int(j)==failed else 'COMPLETED',exit_code='1:0' if int(j)==failed else '0:0',seconds=13)
            with self.assertRaisesRegex(RuntimeError,'Failure preserved'):
                execute(c.grid(list(range(512))),Scheduler(),events.append,lambda s:None,lambda *x:None,lambda:None)
            self.assertEqual(len(calls),failed);self.assertEqual(events[-1]['gpu_seconds'],13*failed)

    def test_reservations_and_ambiguous_submission(self):
        g=c.grid(list(range(512)));g[0]['seconds']+=1
        with self.assertRaisesRegex(RuntimeError,'remaining reservations'):execute(g,None,None,None,None,lambda:None)
        class Scheduler:
            def submit(self,s):raise TimeoutError('Unknown submission')
        events=[]
        with self.assertRaises(TimeoutError):execute(c.grid(list(range(512))),Scheduler(),events.append,None,None,lambda:None)
        self.assertEqual([r['event'] for r in events],['claim','submission_unresolved'])
        self.assertLess(1536*c.CAPS['main_job_bytes']+c.CAPS['analysis_bytes'],c.CAPS['worker_bytes'])

    def test_host_imports_and_disabled_entrypoints(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import lgprb2_dispatch,lgprb2_analysis,lgprb2_preserve,lgprb2_launch;assert 'numpy' not in sys.modules;assert 'torch' not in sys.modules"
        p=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(SOURCE/'cluster/prometheus')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        if not (SOURCE/'APPROVAL-TEMPLATE.json').exists():return
        for script in ('launch','dispatch','worker'):
            args=[sys.executable,'-B',str(SOURCE/f'cluster/prometheus/lgprb2_{script}.py'),'--source',str(SOURCE),'--approval',str(SOURCE/'APPROVAL-TEMPLATE.json')]
            if script!='launch':args+=['--run','/must-not-create-rb2']
            if script=='worker':args+=['--task','analysis']
            p=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(p.returncode,0);self.assertIn('Preparation disabled',p.stderr)

    def test_approval_bound_to_all_frozen_scientific_inputs(self):
        if not (SOURCE/'APPROVAL-TEMPLATE.json').exists():return
        template=c.template(SOURCE)
        for key,value in [('source_sha256','bad'),('roles_sha256','bad'),('grid_sha256','bad'),('input_sha256','bad'),('reuse_sha256','bad'),('main_episodes',8),('automatic_retry',True),('caps',{})]:
            bad={**template,'execution_authorized':True,key:value}
            with patch.object(c,'read',return_value=bad):
                with self.assertRaisesRegex(RuntimeError,'Exact separately frozen'):c.authorize(SOURCE,SOURCE/'APPROVAL-TEMPLATE.json')

class AnalysisTests(unittest.TestCase):
    def rows(self):
        return [dict(reference=r,seed=s,family=f,populations=n,horizon=h,success=int(f=='diffusion' and n==5))
                for r in range(512) for s in c.SEEDS for f,n in c.ARMS for h in (75,150)]
    def test_complete_source_weighted_all_arms(self):
        result=summarize(self.rows(),list(range(512)))
        self.assertEqual(result['primary']['mean'],1);self.assertEqual(result['primary']['interval95'],[1,1])
        self.assertEqual(result['secondary']['interaction']['mean'],1);self.assertEqual(len(result['source_effects']),512)
        self.assertEqual(len(result['strata']),24);self.assertEqual(set(result['absolute']),{'gmm-5','diffusion-5','gmm-30','diffusion-30'})
    def test_missing_duplicate_old_rows_rejected(self):
        rows=self.rows()
        for bad in (rows[:-1],rows[:-1]+[rows[0]],rows+[rows[0]]):
            with self.assertRaisesRegex(RuntimeError,'Complete RB2'):summarize(bad,list(range(512)))

class PackagingTests(unittest.TestCase):
    def bundle(self):
        g=artificial('gmm');d=artificial('diffusion');created=[]
        def world():
            w=setup('gmm',truncated_at=300)[0];created.append(w);return w
        models={'gmm':(g[1],g[2]),'diffusion':(d[1],d[2])}
        return (g[0],models,g[3],g[4],g[5],world,[g[1],d[1]],g[-1]),created

    def test_eight_full_episodes_fresh_ownership_and_order_independence(self):
        bundle,created=self.bundle();spec=c.grid(list(range(512)))[0];outputs=[]
        for cells in (spec['episodes'],list(reversed(spec['episodes']))):
            current={**spec,'episodes':cells}
            with tempfile.TemporaryDirectory() as tmp,patch.object(ev,'load_bundle',return_value=bundle),patch.object(ev,'verify_file',side_effect=lambda root,row,ref:verify_file(root,row,ref,authenticate_reference=False)):
                result=ev.evaluate(SOURCE,Path(tmp),current,lambda:None)
                outputs.append({c.cell_name(r):dict(first=r['stages'][0]['initial_unprojected_bank_sha256'],
                    actions=array_sha(np.load(Path(tmp)/c.cell_name(r)/f"endpoint-h{r['horizon']}.npz")['actions']),
                    rounds=[s['rounds'] for s in r['stages']]) for r in result['rows']})
            self.assertTrue(result['models_unchanged']);self.assertTrue(result['technical_checks']['common_initial_banks'])
            self.assertEqual(sum(r['steps'] for r in result['rows']),1800)
            self.assertEqual({r['success'] for r in result['rows']},{0})
        self.assertEqual(outputs[0],outputs[1]);self.assertEqual(len(created),16);self.assertEqual(len({id(w) for w in created}),16)
        self.assertTrue(all(w.envs.closed and w.envs.resets==[8301] for w in created))

    def test_binding_matches_prior_single_family_driver(self):
        bundle,_=self.bundle();spec=c.grid(list(range(512)))[0]
        for f in c.old.FAMILIES:
            model,stats=bundle[1][f];oldload=(bundle[0],model,stats,*bundle[2:])
            for n in (5,30):
                with tempfile.TemporaryDirectory() as tmp,patch.object(rb1ev,'load',return_value=oldload),patch.object(rb1ev,'verify_file',side_effect=lambda root,row,ref:verify_file(root,row,ref,authenticate_reference=False)):
                    old=rb1ev.evaluate(SOURCE,Path(tmp),dict(reference=spec['reference'],seed=8301,family=f,populations=n),lambda:None)
                    oldactions={h:np.load(Path(tmp)/f'endpoint-h{h}.npz')['actions'].copy() for h in (75,150)}
                for h in (75,150):
                    with tempfile.TemporaryDirectory() as tmp,patch.object(ev,'verify_file',side_effect=lambda root,row,ref:verify_file(root,row,ref,authenticate_reference=False)):
                        row=ev.run_cell(bundle,Path(tmp)/'cell',spec,dict(family=f,populations=n,horizon=h),lambda:None)
                        np.testing.assert_array_equal(np.load(Path(tmp)/'cell'/f'endpoint-h{h}.npz')['actions'],oldactions[h])
                    self.assertEqual([s['rounds'] for s in row['stages']],[s['rounds'] for s in next(r for r in old['rows'] if r['horizon']==h)['stages']])

    def test_changed_initial_bank_rejected(self):
        rows=[dict(family=f,populations=n,horizon=h,stages=[dict(context_sha256='x',initial_unprojected_bank_sha256='x',initial_projected_bank_sha256='x')]) for f,n in c.ARMS for h in (75,150)]
        rows[-1]['stages'][0]['initial_unprojected_bank_sha256']='changed'
        with self.assertRaisesRegex(RuntimeError,'bank differs'):ev.technical_checks(rows)

if __name__=='__main__':
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);unittest.main()
