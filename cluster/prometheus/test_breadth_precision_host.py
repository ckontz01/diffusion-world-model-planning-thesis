"""Run with python -I -S: host boundary requires only the standard library."""
import ast
import importlib.abc
import inspect
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))


class NoNumerics(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('numpy','torch','candidate_value_data','candidate_value_learning','breadth_precision_learning'):
            raise AssertionError('Host imported numerical/runtime module: '+fullname)


sys.meta_path.insert(0,NoNumerics())
import breadth_precision_contract as p
import breadth_precision_freeze as boundary
import breadth_precision_execute as controller
import prepare_breadth_precision as packager
import candidate_value_contract as ct


class HostBoundaryTests(unittest.TestCase):
    def fixture(self,root,**overrides):
        directory=Path(root)/'fit-0';directory.mkdir()
        (directory/'synthetic-model.npz').write_bytes(b'synthetic fixture, not model weights')
        freeze=dict(fitted_models=18,configs=list(boundary.CONFIGS),evaluation_outcomes_opened=False,
                    members={'synthetic-model.npz':p.sha(directory/'synthetic-model.npz')})
        freeze.update(overrides)
        ct.json_write(directory/'PRE-EVALUATION-FREEZE.json',freeze)
        ct.json_write(directory/'REPORT.json',dict(models_frozen=True,new_source_sha256='source'))
        ct.seal(directory)
        return directory

    def test_no_numerical_imports(self):
        self.assertFalse({'numpy','torch','candidate_value_data','candidate_value_learning','breadth_precision_learning'} & set(sys.modules))
        self.assertEqual(len(p.grid()),450)
        self.assertEqual(len(boundary.CONFIGS),6)
        tree=ast.parse(inspect.getsource(controller.dispatch))
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertIn('breadth_precision_freeze',imports)
        self.assertNotIn('breadth_precision_learning',imports)

    def test_valid_freeze_and_wrong_source(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixture(root)
            self.assertEqual(boundary.check_frozen(root,'source')['fitted_models'],18)
            with self.assertRaises(RuntimeError):boundary.check_frozen(root,'wrong')

    def test_member_mutation_remains_fatal(self):
        with tempfile.TemporaryDirectory() as root:
            directory=self.fixture(root)
            (directory/'synthetic-model.npz').write_bytes(b'changed')
            with self.assertRaises(RuntimeError):boundary.check_frozen(root,'source')

    def test_incomplete_or_opened_freeze_remains_fatal(self):
        for values in (dict(fitted_models=17),dict(configs=[]),dict(evaluation_outcomes_opened=True)):
            with tempfile.TemporaryDirectory() as root:
                self.fixture(root,**values)
                with self.assertRaises(RuntimeError):boundary.check_frozen(root,'source')


if __name__=='__main__':unittest.main(verbosity=2)
