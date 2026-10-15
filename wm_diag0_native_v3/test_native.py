"""New artificial integration/rejection tests. No torch, model or simulator."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from .common import ROOT,identity,write_new
from .store import save_array,load_array,seal,authenticate,PhaseAccess,unique
from .source_accept import header
from .actions import decode,normalize

class NativePreparation(unittest.TestCase):
    def test_scaler_exact_native_rounding_and_group_clock(self):
        z=np.linspace(-2.,2.,50,dtype=np.float32).reshape(5,10)
        mean=np.array([-.007812564379916172,.006860687229453032]); std=np.array([.20846744284501714,.20674862637362224])
        physical=decode(z,mean,std)
        expected=np.array([np.float32(float(np.float32(float(x)*std[i%2]))+mean[i%2]) for i,x in enumerate(z.ravel())],dtype=np.float32).reshape(25,2)
        self.assertTrue(np.array_equal(physical,expected))
        norm=normalize(physical,mean,std)
        independent=np.array([np.float32(float(np.float32(float(x)-mean[i%2]))/std[i%2]) for i,x in enumerate(physical.ravel())],dtype=np.float32).reshape(1,5,10)
        self.assertTrue(np.array_equal(norm,independent))
        self.assertFalse(np.array_equal(physical,(z.reshape(25,2)*std+mean).astype(np.float32)))

    def test_safe_arrays_and_independent_header(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.npy'; a=np.arange(12,dtype=np.float64).reshape(3,4)
            save_array(p,a)
            self.assertTrue(np.array_equal(load_array(p,(3,4),['<f8']),a))
            self.assertGreater(header(p,(3,4),'<f8'),0)
            with self.assertRaises(ValueError): load_array(p,(4,3),['<f8'])
            with self.assertRaises(ValueError): header(p,(3,4),'<f4')

    def test_objects_nonfinite_and_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.npy'
            with p.open('wb') as f: np.save(f,np.array([{'x':1}],dtype=object),allow_pickle=True)
            with self.assertRaises(ValueError): load_array(p)
            with self.assertRaises(ValueError): save_array(Path(t)/'bad.npy',np.array([np.nan]))
            p.unlink(); save_array(p,np.arange(10))
            with self.assertRaises(ValueError): load_array(p,max_bytes=8)

    def test_external_manifest_extra_missing_and_changed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); save_array(root/'a.npy',np.zeros((2,3)))
            s=seal(root,10000); authenticate(root,s,10000,{'a.npy'})
            save_array(root/'extra.npy',np.zeros(1))
            with self.assertRaises(ValueError): authenticate(root,s,10000)
            (root/'extra.npy').unlink(); (root/'a.npy').write_bytes(b'changed')
            with self.assertRaises(ValueError): authenticate(root,s,10000)

    def test_phase_requires_external_seal_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            phase=PhaseAccess(t)
            with self.assertRaises(PermissionError): phase.authorize_outcomes({'sha256':'0'*64,'bytes':1})
            s=phase.record_selection({'choices':[0,1,2,3]})
            self.assertEqual(phase.authorize_outcomes(s),Path(t)/'evaluation')
            with self.assertRaises(ValueError): phase.record_selection({})
            (Path(t)/'SELECTION.json').write_text('{}')
            with self.assertRaises(PermissionError): phase.authorize_outcomes(s)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError): json.loads('{"a":1,"a":2}',object_pairs_hook=unique)

    def test_frozen_manifest_not_regenerated(self):
        p=ROOT/'docs/world-model-diagnostic-a2-20261004/ROOT-PLAN.json'
        self.assertEqual(identity(p)['sha256'],'e648465420311a69a3df237b9f199ecd070e1c1241481376888ffbffe593630f')
        rows=json.loads(p.read_text())['roots']
        self.assertEqual(len(rows),120)
        self.assertEqual(len({r['root_id'] for r in rows}),120)
        self.assertEqual(sum(r['role']=='readout_fit' for r in rows),32)

    def test_all_new_source_compiles_without_import_execution(self):
        for p in Path(__file__).parent.glob('*.py'): compile(p.read_bytes(),str(p),'exec',dont_inherit=True)
        tree=ast.parse((Path(__file__).parent/'world.py').read_text())
        restore=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='restore')
        calls=[n.func.attr for n in ast.walk(restore) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertNotIn('set_state',calls); self.assertNotIn('_set_state',calls)
        self.assertIn('reset',calls); self.assertIn('step',calls); self.assertIn('install_goal',calls)

if __name__=='__main__': unittest.main()
