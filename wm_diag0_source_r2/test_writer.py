import ast,json,random,tempfile,unittest
from pathlib import Path
import numpy as np
from .writer import write_audits
from wm_diag0_native_v3.world import plain
from wm_diag0_native_v3.common import canonical

class Writer(unittest.TestCase):
    def test_compact_large_rng_audit_is_lossless_within_existing_limit(self):
        rng=np.random.RandomState(7);py=random.Random(9)
        sample={'python_rng':plain(py.getstate()),'numpy_rng':plain(rng.get_state()),'task_rng':plain(rng.get_state()),
                'variation':{str(i):{'value':plain(np.array([1.,2.,3.])),'rng':plain(np.random.default_rng(i).bit_generator.state)} for i in range(10)},
                'integration':plain(np.linspace(-1,1,32))}
        audits=[dict(sample,clock=i) for i in range(45)]
        self.assertGreater(len(json.dumps(audits,sort_keys=True,indent=2).encode()),2_000_000)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'audits.json';write_audits(p,audits);loaded=json.loads(p.read_text())
            self.assertLess(p.stat().st_size,2_000_000)
            self.assertEqual([canonical(x) for x in loaded],[canonical(x) for x in audits])
    def test_still_rejects_over_limit_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.json'
            with self.assertRaises(ValueError):write_audits(p,[{'x':'x'*2_000_000}])
            write_audits(p,[{'x':1}])
            with self.assertRaises(FileExistsError):write_audits(p,[{'x':1}])
    def test_new_source_compiles(self):
        for p in Path(__file__).parent.glob('*.py'):compile(p.read_bytes(),str(p),'exec')

if __name__=='__main__':unittest.main()
