import common as c
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TechnicalRevision(unittest.TestCase):
    def fixture(self,root,updates=192):
        for key in ('fit-joint','fit-ordinary'):
            p=root/key;p.mkdir(parents=True)
            c.write(p/'FIT.json',{'updates':updates,'artificial':True})
            c.write(p/'PREPROCESSING.json',{'fit_ids':list(map(str,c.roles()['fit']))})
            c.seal(p,{'key':key})

    def test_stdlib_gate_equal_to_original(self):
        from fitting import model_freeze as original
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'old';b=Path(tmp)/'new'
            self.fixture(a);self.fixture(b);original(a,'artificial-package')
            code="import sys;sys.path.insert(0,"+repr(str(c.ROOT))+");import dispatch,model_seal;from pathlib import Path;model_seal.model_freeze(Path("+repr(str(b))+"),'artificial-package');assert 'numpy' not in sys.modules and 'torch' not in sys.modules"
            p=subprocess.run([sys.executable,'-B','-S','-c',code],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual((a/'MODEL-FREEZE.json').read_bytes(),(b/'MODEL-FREEZE.json').read_bytes())

    def test_gate_rejects_wrong_updates_and_changed_seals(self):
        from model_seal import model_freeze
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p,191)
            with self.assertRaises(ValueError):model_freeze(p,'artificial-package')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p)
            c.write(p/'fit-joint'/'unexpected.json',{})
            with self.assertRaises(ValueError):model_freeze(p,'artificial-package')

    def test_scientific_modules_and_contract_unchanged(self):
        old=c.BASE/'bindings-v1'
        for name in ('common.py','bridge.py','episodes.py','verify.py','fitting.py','worker.py','supervise.py','analysis.py','preserve.py','run_worker.sh','INPUT-BINDINGS.json','GRID.json'):
            self.assertEqual(c.sha(old/name),c.sha(c.ROOT/name),name)
        self.assertEqual(c.digest(c.grid()),'f9b4986c9f674122c253cff9aaf802e8d4b181180553d0e5643c0c92bb175a2a')


if __name__=='__main__':unittest.main(verbosity=2)
