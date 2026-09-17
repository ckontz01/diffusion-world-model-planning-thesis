"""Synthetic arithmetic/forward/guard tests only. Never fit or take optimizer steps."""
import copy
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
import score_information as s


def bank(ref,h=75,t=0):
    return dict(reference=ref,horizon=h,anchor=t,slot=0,x=np.tile(np.arange(619,dtype=np.float32),(8,1))+ref,
        immediate=-np.arange(8,dtype=np.float32),continuation=-np.arange(8,dtype=np.float32)[::-1].copy(),
        y=np.array([[0,1],[1,1]]+[[0,0]]*6),ids=[7,1,2,3,4,5,6,0],base=0,continuation_index=7)


class Tests(unittest.TestCase):
    def test_folds_complete_disjoint(self):
        folds=s.folds();self.assertEqual([len(x) for x in folds],[48]*4)
        self.assertEqual(len(set(sum(folds,[]))),192)
        a=s.bp.allocation();self.assertEqual(set(sum(folds,[])),set(a['original_train']+a['extra_train']))
        self.assertFalse(set(sum(folds,[]))&set(a['evaluation']))
        self.assertEqual(folds,s.folds())

    def test_no_identity_features(self):
        a=bank(1);b=copy.deepcopy(a);b['reference']=1599;b['ids']=list(reversed(b['ids']))
        np.testing.assert_array_equal(s.inputs(a),s.inputs(b))
        self.assertEqual(s.inputs(a).shape,(8,621))
        np.testing.assert_array_equal(s.inputs(a)[:,619],-a['immediate'])

    def test_training_only_preprocessing(self):
        a=[bank(1),bank(2)];mean,scale=s.preprocessing(a,[1,2])
        held=bank(3);held['x'][:]=1e9;held['immediate'][:]=-1e8
        other=s.preprocessing(a,[1,2])
        np.testing.assert_array_equal(mean,other[0]);np.testing.assert_array_equal(scale,other[1])
        with self.assertRaises(AssertionError):s.preprocessing(a+[held],[1,2])

    def test_control_zero_after_standardization(self):
        b=bank(1);mean,scale=s.preprocessing([b],[1]);x=s.inputs(b)
        control=s.transform(x,mean,scale,'control');scores=s.transform(x,mean,scale,'scores')
        np.testing.assert_array_equal(control[:,:619],scores[:,:619])
        np.testing.assert_array_equal(control[:,619:],np.zeros((8,2)))
        self.assertGreater(float(np.std(scores[:,619:])),0)

    def test_degenerate_scalers_and_nonfinite(self):
        b=bank(1);b['immediate'][:]=-5;b['continuation'][:]=-5
        mean,scale=s.preprocessing([b],[1]);self.assertTrue((scale[-2:]==1).all())
        self.assertTrue(np.isfinite(s.transform(s.inputs(b),mean,scale,'scores')).all())
        b['x'][0,0]=np.nan
        with self.assertRaises(AssertionError):s.inputs(b)

    def test_label_draws_and_weighting(self):
        banks=[bank(1,75),bank(1,150),bank(2,75),bank(2,150)]
        x,y,w,keys=s.table(banks)
        self.assertEqual(len(y),64);self.assertEqual(set(y),{0.,1.})
        for ref in (1,2):self.assertAlmostEqual(float(sum(v for k,v in zip(keys,w) if k[0]==ref)),.5)
        self.assertEqual(set(k[-1] for k in keys),{0,1})

    def test_same_initialization_dimensions_and_forward(self):
        with torch.random.fork_rng():torch.manual_seed(8201);a=s.Model()
        with torch.random.fork_rng():torch.manual_seed(8201);b=s.Model()
        self.assertEqual(sum(p.numel() for p in a.parameters()),87937)
        for x,y in zip(a.parameters(),b.parameters()):self.assertTrue(torch.equal(x,y))
        with torch.inference_mode():self.assertEqual(tuple(a(torch.zeros(8,621)).shape),(8,))

    def test_update_budget_and_paired_order(self):
        a=list(s.batches(513,8201));b=list(s.batches(513,8201))
        self.assertEqual(len(a),1800);self.assertTrue(all(torch.equal(x,y) for x,y in zip(a,b)))
        self.assertEqual([len(x) for x in a[:3]],[256,256,1])
        self.assertEqual(2*4*3*1800,43200)

    def test_ties_and_empirical_selection(self):
        m=s.metrics_module();b=bank(1)
        chosen,stats=m.metrics(np.ones(8)*.5,b,True,True)
        self.assertEqual(chosen,b['base']);self.assertEqual(stats['effect'],0)
        q=np.array([0,1,1,0,0,0,0,0]);chosen,stats=m.metrics(q,b,True,True)
        self.assertEqual(b['ids'][chosen],1);self.assertEqual(stats['effect'],.5)
        self.assertAlmostEqual(stats['gain']-stats['loss'],stats['effect'])

    def test_approval_before_saved_reads(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'approval.json';p.write_text('{"execution_authorized":false}')
            with patch.object(s,'saved_banks',side_effect=AssertionError('must not read')) as reader:
                with self.assertRaises(AssertionError):s.run(p,Path(d)/'out')
                reader.assert_not_called();self.assertFalse((Path(d)/'out').exists())

    def test_exclusive_artifacts_and_cap(self):
        with tempfile.TemporaryDirectory() as d:
            a=s.Artifacts(Path(d)/'out');a.json('ok.json',{'value':1})
            with self.assertRaises(FileExistsError):a.json('ok.json',{})
            a.bytes=900000000
            with self.assertRaises(AssertionError):a.put('no',b'x')

    def test_full_synthetic_driver_no_optimizer(self):
        # Exercise all 24 fit slots with a fixed forward-only stand-in; no training.
        refs=sum(s.folds(),[]);data=[bank(r,h) for r in refs for h in (75,150)]
        calls=[]
        def fake_fit(x,y,w,seed,check):
            calls.append((len(y),seed));check()
            return s.Model().eval().requires_grad_(False),dict(updates=1800,seed=seed)
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)/'experiments'/s.VERSION;parent.mkdir(parents=True)
            with patch.object(s,'authorize',return_value={}),patch.object(s,'saved_banks',return_value=data), \
                 patch.object(s,'fit',side_effect=fake_fit),patch.object(s.bp,'ROOT',Path(d)), \
                 patch.object(torch,'set_num_interop_threads'), \
                 patch.dict(os.environ,CUDA_VISIBLE_DEVICES='',SLURM_JOB_ID='synthetic',SLURM_CPUS_PER_TASK='4'), \
                 patch.object(torch.optim,'AdamW',side_effect=AssertionError('optimizer forbidden')):
                s.run('unused',parent/'synthetic')
            result=json.loads((parent/'synthetic/REPORT.json').read_text())
            self.assertEqual(len(calls),24);self.assertEqual({n for n,_ in calls},{144*2*16})
            self.assertEqual(len(result['models']['reference_rows']),192)
            self.assertEqual(len(result['fold_summaries']),4)
            self.assertTrue((parent/'synthetic/sha256.txt').is_file())


if __name__=='__main__':unittest.main()
