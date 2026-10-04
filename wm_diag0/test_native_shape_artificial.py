"""Full proposed patch shape with random arrays, NOT checkpoint inference."""
import unittest
import tempfile
from pathlib import Path
import numpy as np
from .core import Features, select_four, native_terminal_score
from .readout import fit_artificial, realized_quality
from .test_components import bank, contract
from .phase import seal_artificial, authenticate_selection

class NativeShapeArtificialTest(unittest.TestCase):
    def test_full_patch_ridge_and_four_cell_interface(self):
        c=contract('dinowm_noprop',(256,384))
        rng=np.random.default_rng(20261004)
        x=rng.standard_normal((256,256,384),dtype=np.float32)
        y=rng.standard_normal((256,6),dtype=np.float32)
        r=fit_artificial(x,y,['fit-fixture']*256,
            (['fit-fixture'],['validation-fixture'],['diagnostic-fixture']),c,'pusht',domain='artificial')
        b=bank();v=np.zeros((16,5,256,384),np.float32)
        p=Features(v,c,b.identity,'diagnostic-fixture','predicted')
        o=Features(v.copy(),c,b.identity,'diagnostic-fixture','realized')
        s=select_four(b,p,o,np.zeros((256,384),np.float32),native_terminal_score,r)
        self.assertEqual(s.choices,(0,0,0,0))
        self.assertEqual(r.weights.shape,(256*384,6))
        before=r.identity
        q=realized_quality(r,x[:96],y[:96])
        self.assertTrue(np.isfinite(q['coordinate_rmse']).all())
        self.assertEqual(r.identity,before)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'full-patch-phase'
            seal=seal_artificial(path,b,p,o,np.zeros((256,384),np.float32),native_terminal_score,r,
                oracle_prefix_id='artificial-prefix',oracle_draw=9401,evaluation_draws=(9301,9302),domain='artificial')
            self.assertEqual(authenticate_selection(path,seal)['candidate_count'],16)
            # Worst-case full patch+head array bundle plus separately bounded
            # action/endpoint/observation-hash evidence allowance.
            actual=sum(f.stat().st_size for f in path.iterdir())
            self.assertLess(actual+300000,70000000)

if __name__=='__main__':unittest.main(verbosity=2)
