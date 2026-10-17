"""New controller/publication guards only; no real saved scientific data read."""
import ast,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from .common import ROOT,DOC,PKG,identity,write_new
from . import driver,stage,collect,publish

class Guards(unittest.TestCase):
    def test_no_dispatch_no_child(self):
        with patch.dict(os.environ,{},clear=True),patch.object(driver.subprocess,'check_output') as command:
            with self.assertRaises(PermissionError):driver.allocation({'job_id':'123'})
            command.assert_not_called()
    def test_gpu_refused_before_scheduler(self):
        env={'SLURM_JOB_ID':'123','SLURM_CPUS_PER_TASK':'4','SLURM_MEM_PER_NODE':'8192','SLURM_JOB_GPUS':'0'}
        with patch.dict(os.environ,env,clear=True),patch.object(driver.subprocess,'check_output') as command:
            with self.assertRaises(PermissionError):driver.allocation({'job_id':'123'})
            command.assert_not_called()
    def test_fixed_stage_order_and_cpu_only(self):
        ast.parse(stage.CODE,feature_version=(3,6));text=stage.CODE
        self.assertIn("'--hold'",text);self.assertIn("'--no-requeue'",text)
        self.assertLess(text.index("write('DISPATCH.json'"),text.index("['scontrol','release',job]"))
        self.assertIn("'--cpus-per-task=4'",text);self.assertNotIn('--gres',text)
    def test_exact_new_collection_not_old_archive(self):
        ast.parse(collect.STATUS,feature_version=(3,6))
        self.assertNotIn('--array',collect.STATUS)
        self.assertIn("rows[0][:2]!=[d['job_id'],d['job_id']]",collect.STATUS)
        self.assertNotIn('final-study.tar',(PKG/'collect.py').read_text())
    def test_immutable_small_zip_roundtrip(self):
        # Only artificial two-member opaque byte strings.
        target=DOC/'operational-artificial-001';target.mkdir(exist_ok=False)
        p=target/'tiny.zip';expected={'a.json':b'{"artificial":true}\n','b.txt':b'tiny opaque fixture'}
        result=publish.zip_verified(p,expected);self.assertEqual(result,identity(p))
        with self.assertRaises(FileExistsError):publish.zip_verified(p,expected)
    def test_complete_source_parses_and_lock_excluded(self):
        for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf8'),feature_version=(3,11))
        for p in (PKG/'driver.py',PKG/'common.py'):ast.parse(p.read_text(),feature_version=(3,6))
        self.assertNotIn(DOC/'operation.lock',publish.source_files())

def main():
    result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Guards))
    receipt={'status':'PASSED' if result.wasSuccessful() else 'FAILED','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'scope':'Native new operational guards and one artificial tiny two-member ZIP only; zero Slurm/SSH/model/scientific input calls.',
        'sources':{p.relative_to(ROOT).as_posix():identity(p) for p in PKG.glob('*.py')}}
    write_new(DOC/'ARTIFICIAL-OPERATIONS-001.json',receipt)
    if not result.wasSuccessful():raise ValueError('operational tests failed')
    print(json.dumps({'status':receipt['status'],'tests':result.testsRun}))

if __name__=='__main__':main()
