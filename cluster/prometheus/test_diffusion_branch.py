import unittest
import hashlib
import json
import numpy as np
from pathlib import Path
from diffusion_bottleneck_branch import delta_at,decode,score,run

class Decoder:
    def inverse_transform(self,x): return x*np.array([.2,.3],np.float32)+np.array([.01,-.01],np.float32)

class BranchTests(unittest.TestCase):
    def test_full_identifier_selection_manifest(self):
        path=Path(__file__).resolve().parents[2]/'docs/bottleneck/BRANCH-PILOT-SELECTION.json'
        manifest=json.loads(path.read_text())
        ordered=sorted(range(1600),key=lambda i:(hashlib.sha256(f"{manifest['namespace']}|{i}".encode()).hexdigest(),i))
        self.assertEqual(ordered[:32],manifest['development_reference_indices'])
        self.assertEqual(ordered[:4],[1269,582,525,722])
    def test_schedule(self):
        self.assertEqual([delta_at(h,t) for h in (75,150) for t in (0,30)],[75,45,150,120])
    def test_reject_unapproved_anchor(self):
        with self.assertRaises(RuntimeError):delta_at(75,60)
    def test_decode_preserves_batch_axes(self):
        x=np.ones((64,15,2),np.float32)
        y=decode(x,Decoder())
        self.assertEqual(y.shape,x.shape)
        np.testing.assert_array_equal(y[0,0],Decoder().inverse_transform(np.ones((1,2),np.float32))[0])
    def test_decode_does_not_clip(self):
        self.assertTrue((decode(np.full((1,2),10,np.float32),Decoder())>1).all())
    def test_score_lower_two_mean_not_minimum(self):
        x=np.tile([2.,10.,5.,7.,9.,8.,6.,4.],(64,1)).astype(np.float32)
        np.testing.assert_array_equal(score(x),np.full(64,3.,np.float32))
    def test_score_nonfinite_refused(self):
        with self.assertRaises(RuntimeError):score(np.full((64,8),np.nan))
    def test_protected_coordinate_rejected_before_io(self):
        with self.assertRaisesRegex(RuntimeError,'authorized pilot'):
            run(Path('/never'),Path('/never'),1600,0)
    def test_unapproved_study_rejected_before_model_import(self):
        with self.assertRaisesRegex(RuntimeError,'historical study'):
            run(Path('/never'),Path('/never'),1269,0)

if __name__=='__main__':unittest.main()
