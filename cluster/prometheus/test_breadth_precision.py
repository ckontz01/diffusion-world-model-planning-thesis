"""Focused synthetic preparation checks: no learned model, fitting or physics."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
import breadth_precision_contract as p
import breadth_precision_data as d
import breadth_precision_learning as l
import breadth_precision_execute as e
import candidate_value_contract as ct
import candidate_value_learning as c
from candidate_value_data import read_npz
from test_candidate_value_pipeline import SyntheticBackend,synthetic_record

ROOT=Path(__file__).resolve().parents[2]


def bank(ref=1,draws=4,h=75,t=0):
    ids=[7,1,3,4,5,6,8,9]
    y=np.zeros((8,draws),np.int64);y[0,0]=1;y[1,:]=1
    return dict(reference=ref,horizon=h,anchor=t,slot=c.anchors(h).index(t),
        x=np.zeros((8,619),np.float32),y=y,ids=ids,base=0,continuation_index=7,
        continuation=np.arange(8.,0.,-1.),immediate=np.array([0.,9.,1.,2.,3.,4.,5.,6.]))


class FixedScores:
    """Arithmetic fixture, NOT a learned evaluator or a neural forward call."""
    def __init__(self,v):self.v=torch.tensor(v,dtype=torch.float32)
    def __call__(self,x):return self.v


class BreadthPrecisionTests(unittest.TestCase):
    def test_identity_manifest_exact_roles(self):
        m=ct.json_read(ROOT/p.MANIFEST);a=p.allocation()
        self.assertEqual(m['allocation'],a)
        groups=[set(a[n]) for n in ('original_train','extra_train','evaluation')]
        self.assertEqual(list(map(len,groups)),[96,96,32])
        self.assertEqual(len(set.union(*groups)),224)
        self.assertEqual(set(map(int,m['records'])),set.union(*groups))
        self.assertEqual(len({r['source_key'] for r in m['records'].values()}),224)

    def test_all_previous_roles_excluded(self):
        a=p.allocation();excluded=set(sum(a['exclusions'].values(),[]))
        self.assertEqual(len(excluded),192)
        self.assertFalse(excluded & set(a['extra_train']+a['evaluation']))
        self.assertTrue(all(0<=r<1600 for r in a['extra_train']+a['evaluation']))
        self.assertEqual(a['eligible_before_new_allocation'],1408)
        self.assertEqual(a['remaining_after_new_allocation'],1280)
        self.assertEqual(a['extra_train'][:4],[333,894,1125,387])
        self.assertEqual(a['evaluation'][:4],[949,977,800,1206])

    def test_stream_identity_and_cpu_output_distinction(self):
        for ref in p.allocation()['original_train']+p.allocation()['extra_train']+p.allocation()['evaluation']:
            for h in (75,150):
                for t in c.anchors(h):
                    seeds=[p.tail_seed(ref,h,t,d) for d in range(4)]
                    self.assertEqual(tuple(seeds[:2]),ct.tail_seeds(ref,h,t))
                    self.assertEqual(len(set(seeds)),4)
                    samples=[torch.rand(16,generator=torch.Generator().manual_seed(s)).numpy().tobytes() for s in seeds]
                    self.assertEqual(len(set(samples)),4)
        # Candidate not in seed signature: common random draws across indices.
        self.assertEqual(list(__import__('inspect').signature(p.tail_seed).parameters),['ref','h','t','draw'])

    def test_original_sampling_exact_and_nonwinners(self):
        r=p.allocation()['original_train'][0]
        for collision in (False,True):
            im=np.arange(64.);co=np.arange(64.)
            if not collision:im[4]=-1
            self.assertEqual(p.sampling(im,co,r,75,0),c.sample_bank(im,co,reference=r,h=75,t=0))
            q=p.sampling(im,co,r,75,0)
            self.assertEqual(len(set(q['indices'])),8)
            self.assertEqual(q['other_slots'],7 if collision else 6)
        self.assertEqual(len(p.sampling(im,co,p.allocation()['extra_train'][0],150,30)['indices']),8)

    def test_sampling_rejects_reserved_or_unavailable_slot(self):
        z=np.zeros(64)
        for r,h,t in [(ct.allocation()['closed_loop'][0],75,0),(1600,75,0),(333,75,45)]:
            with self.assertRaises(RuntimeError):p.sampling(z,z,r,h,t)

    def test_independent_outcome_count(self):
        actual={kind:sum(4*8*(4 if kind=='evaluation' else 2) for job in p.grid() if job['kind']==kind)
                for kind in ('breadth','precision','evaluation')}
        self.assertEqual(actual,dict(breadth=12288,precision=12288,evaluation=8192))
        self.assertEqual(sum(actual.values()),32768)
        self.assertEqual(p.costs()['known_availability_adjusted_new_ceiling'],31824)
        self.assertEqual(p.costs()['known_C_new_outcomes'],11344)

    def test_physical_steps_and_compute_counts(self):
        maximum=sum((4*8*(4 if j['kind']=='evaluation' else 2)+(j['kind']!='precision'))*2*j['h']
                    for j in p.grid() if j['gpu'])
        costs=p.costs();self.assertEqual(maximum,7430400)
        self.assertEqual(costs['steps_max'],maximum)
        self.assertEqual(costs['proposal_batches_max'],924672)
        self.assertEqual(costs['diffusion_forwards_max'],9246720)
        self.assertEqual(costs['C_extra_final_budget_outcome_records'],2512)
        self.assertEqual(costs['C_final_budget_additional_stochastic_information'],0)

    def test_grid_order_and_caps(self):
        g=p.grid();self.assertEqual(len(g),450)
        self.assertEqual(len({(j['kind'],j['index']) for j in g}),450)
        self.assertEqual([x['kind'] for x in g[:16]],['breadth']*8+['precision']*8)
        self.assertEqual(g[384]['kind'],'fit');self.assertEqual(g[385]['kind'],'evaluation')
        self.assertEqual(g[-1]['kind'],'analyze')
        self.assertEqual(sum(j['seconds'] for j in g if j['gpu']),307200)
        self.assertEqual(sum(j['seconds'] for j in g if not j['gpu']),7200)
        self.assertTrue(p.reservation(0,0,0,g))
        self.assertFalse(p.reservation(2401,0,0,g))
        self.assertFalse(p.reservation(0,1,0,g))
        self.assertFalse(p.reservation(0,0,9500000000,g))

    def test_sbatch_preserves_machine_and_cpu_no_gpu(self):
        gpu=e.arguments(p.task('breadth',0),'s','r','a')
        self.assertIn('--partition=a6000',gpu);self.assertIn('--qos=normal-a6000',gpu)
        self.assertIn('--mem=24G',gpu)
        cpu=e.arguments(p.task('fit',0),'s','r','a')
        self.assertIn('--partition=defq',cpu);self.assertIn('--mem=8G',cpu)
        self.assertFalse(any('gpu' in x or 'gres' in x for x in cpu))

    def test_no_permission_no_model_or_submit(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(e,'command') as command:
            f=Path(tmp)/'approval.json';ct.json_write(f,dict(researcher_approved=False))
            for mode in ('dispatch','worker'):
                with self.assertRaisesRegex(RuntimeError,'approval'):
                    if mode=='dispatch':e.dispatch(tmp,tmp+'/run',f)
                    else:e.worker(tmp,tmp+'/run',f,'breadth',0)
            command.assert_not_called()

    def test_c_same_bank_and_unavailability(self):
        r=p.allocation()['original_train'][0]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);b=root/'b';b.mkdir();x=root/'c';x.mkdir()
            original=d.collect(SyntheticBackend(),synthetic_record(),0,r,75,'breadth',b)
            banks={0:read_npz(b/'bank-0.npz')};prefix=read_npz(b/'prefix.npz')
            precision=d.collect(SyntheticBackend(),synthetic_record(),0,r,75,'precision',x,
                                (original,banks,prefix,{'synthetic':'fixture'}))
            self.assertEqual(precision['new_outcomes'],16)
            self.assertFalse(precision['standalone_prefix_executed'])
            self.assertEqual([z['available'] for z in precision['banks']],[True,False,False,False])
            self.assertFalse((x/'bank-0.npz').exists())
            merged=copy.deepcopy(original);merged['banks'][0]['labels']+=precision['banks'][0]['labels']
            rows=d.unpack(merged,banks,[0,1,2,3]);self.assertEqual(rows[0]['y'].shape,(8,4))
            self.assertTrue(np.isin(rows[0]['y'],[0,1]).all())

    def test_bank_mutation_is_fatal(self):
        z={'x':np.zeros((64,619)),'actions':np.zeros((64,15,2))};bad=copy.deepcopy(z)
        bad['actions'][0,0,0]=1
        with self.assertRaises(AssertionError):d.equal_bank(bad,z)
        with self.assertRaises(RuntimeError):d.equal_bank({'x':z['x']},z)

    def test_binary_fraction_not_majority(self):
        b=bank();_,_,y,w,k=l.table([b],False)
        self.assertEqual(y[:4].tolist(),[1,0,0,0])
        self.assertEqual(float(y[:4].mean()),.25)
        self.assertEqual(len(k),32);self.assertAlmostEqual(float(w.sum()),1.)

    def test_relative_all_pairs_including_zero(self):
        b=bank();_,_,y,w,k=l.table([b],True)
        self.assertEqual(len(y),28);self.assertEqual(y[:4].tolist(),[0,1,1,1])
        self.assertGreater(int((y==0).sum()),0)
        self.assertEqual({q[3] for q in k},set(b['ids'])-{7})
        self.assertAlmostEqual(float(w.sum()),1.,places=6)

    def test_source_horizon_anchor_weights(self):
        banks=[bank(1,2),bank(1,2,t=30),bank(1,2,h=150),bank(2,4),bank(2,4,h=150)]
        _,_,_,w,k=l.table(banks,False)
        self.assertAlmostEqual(float(sum(v for key,v in zip(k,w) if key[0]==1)),.5)
        self.assertAlmostEqual(float(sum(v for key,v in zip(k,w) if key[:3]==(1,75,0))),.125)

    def test_matched_updates_not_matched_epochs(self):
        for objective,updates in p.UPDATES.items():
            for n in (11344,22688,23632):
                batches=list(l.update_batches(n,updates,8201))
                self.assertEqual(len(batches),updates)
                self.assertTrue(all(0<len(b)<=256 for b in batches))
                self.assertLess(len(batches[-1]),257)
        self.assertEqual(40*((11344+255)//256),1800)
        self.assertEqual(40*((9926+255)//256),1560)

    def test_update_permutation_and_short_batch(self):
        a=list(l.update_batches(513,5,8201));b=list(l.update_batches(513,5,8201))
        self.assertEqual([len(x) for x in a],[256,256,1,256,256])
        self.assertTrue(all(torch.equal(x,y) for x,y in zip(a,b)))
        self.assertEqual(len(set(torch.cat(a[:3]).tolist())),513)

    def test_four_draw_probability_error_and_ties(self):
        s=l.helpers();b=bank();q=np.full(8,.25)
        chosen,m=s.metrics(q,b,True,True)
        self.assertEqual(chosen,b['base'])
        self.assertAlmostEqual(m['brier'],float(((q[:,None]-b['y'])**2).mean()))
        self.assertEqual(m['maximum_ties'],8)
        self.assertEqual(s.choose(q,b['ids'],None),1)

    def test_ensemble_definition_arithmetic_only(self):
        s=l.helpers();models=[FixedScores(np.arange(8.)*v) for v in (1,2,3)]
        b=bank();values,ensemble=s.scores(models,'C_relative',b['x'],0,np.zeros(619),np.ones(619))
        np.testing.assert_array_equal(ensemble,np.arange(8.)*2)
        self.assertTrue((values[:,0]==0).all())
        values,ensemble=s.scores(models,'A_bce',b['x'],0,np.zeros(619),np.ones(619))
        np.testing.assert_allclose(ensemble,values.mean(0))
        self.assertEqual(len(l.CONFIGS),6);self.assertEqual(len(p.SEEDS)*len(l.CONFIGS),18)

    def test_all_models_refs_strata_reported(self):
        models={k:[FixedScores(np.arange(8.)) for _ in p.SEEDS] for k in l.CONFIGS}
        result,rows,preds=l.evaluate([bank(1),bank(2,h=150)],models,np.zeros(619),np.ones(619))
        self.assertEqual(len(result['reference_rows']),2)
        self.assertEqual(len(result['models']),27) # six ensembles, 18 seeds, three controls
        self.assertEqual(len(rows),54);self.assertEqual(len(preds),2)
        self.assertEqual(len(result['strata']),8)

    def test_evaluation_missing_freeze_fails_before_data(self):
        with tempfile.TemporaryDirectory() as tmp,patch('breadth_precision_data.datasets') as read:
            with self.assertRaises(FileNotFoundError):l.analyze(tmp,tmp,'source')
            read.assert_not_called()

    def test_full_model_freeze_member_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'fit-0';out.mkdir();f=out/'model.npz';f.write_bytes(b'synthetic bytes')
            ct.json_write(out/'PRE-EVALUATION-FREEZE.json',dict(members={'model.npz':p.sha(f)},
                fitted_models=18,configs=list(l.CONFIGS),evaluation_outcomes_opened=False))
            ct.json_write(out/'REPORT.json',dict(models_frozen=True,new_source_sha256='x'));ct.seal(out)
            l.check_frozen(tmp,'x');f.write_bytes(b'corruption')
            with self.assertRaises(RuntimeError):l.check_frozen(tmp,'x')

    def test_source_wrapper_no_legacy_evaluator(self):
        text=(ROOT/'cluster/prometheus/run_breadth_precision.sh').read_text()
        self.assertIn('CUDA_VISIBLE_DEVICES=',text);self.assertIn('$ROOT:$ROOT:ro',text)
        self.assertIn('breadth_precision_execute.py',text)
        self.assertNotIn('candidate_value_worker.py',text)
        tree=ast.parse((ROOT/'cluster/prometheus/breadth_precision_execute.py').read_text())
        worker=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='worker')
        self.assertIn('authorize',ast.unparse(worker.body[0]))

    def test_packaging_closure_and_negative_approval(self):
        from prepare_breadth_precision import source_freeze
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);up=root/'old';up.mkdir();(up/'legacy.txt').write_bytes(b'frozen\r\n')
            seal=p.sha(up/'legacy.txt')+'  legacy.txt\n';(up/'SOURCE-MANIFEST.sha256').write_text(seal)
            with patch.object(p,'OLD_SOURCE_SHA',p.sha(up/'SOURCE-MANIFEST.sha256')):
                receipt=source_freeze(ROOT,up,root/'new')
            ct.verify_source(root/'new',receipt['source_sha256'])
            self.assertEqual((root/'new/legacy.txt').read_bytes(),b'frozen\r\n')
            self.assertFalse(ct.json_read(root/'new/APPROVAL-TEMPLATE.json')['researcher_approved'])
            self.assertFalse(receipt['execution_authorized'])
            self.assertNotIn(b'\r',(root/'new/cluster/prometheus/run_breadth_precision.sh').read_bytes())

    def test_accepted_infrastructure_function_identity(self):
        import inspect,hashlib
        import breadth_precision_infra as new
        raw=''.join(inspect.getsource(getattr(new,n)) for n in ('file_bytes','bytes_used','technical_report')).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '6ec5e0a643b87c73b5320a9de121b547cbb36040c855fa1cd7e5bca3c06c008b')

    def test_storage_race_and_technical_only_projection(self):
        from breadth_precision_infra import bytes_used,technical_report
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(bytes_used(root/'missing'),0)
            ct.json_write(root/'REPORT.json',dict(technical_valid=True,source_sha256='x',
                protected_payload_reads=0,secret_outcomes=[1,0,1],nested={'scores':[.1,.9]}))
            ct.seal(root);meta=technical_report(root)
            self.assertNotIn('secret_outcomes',meta);self.assertNotIn('nested',meta)
            self.assertEqual(meta['source_sha256'],'x')
            self.assertGreater(bytes_used(root),0)


if __name__=='__main__':unittest.main()
