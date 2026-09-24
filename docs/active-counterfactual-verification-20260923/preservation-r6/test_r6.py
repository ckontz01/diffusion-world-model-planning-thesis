import ast,copy,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import archive6 as a
import transport6 as t
class Tests(unittest.TestCase):
    def fixture(self,root):
        paths={};expected={}
        for label in ('source','control','run','r2_source','r2_control','r3_source','r3_control','r4_source','r4_control','r5_source','r5_control','r6_source','r6_control'):
            p=root/label;p.mkdir();paths[label]=str(p)
            n='docs/study/control-r4/APPROVAL-TEMPLATE.json' if label=='r4_source' else 'evidence.json'
            file=p/n;file.parent.mkdir(parents=True,exist_ok=True);a.write(file,{'artificial':True,'label':label})
            expected[label+'/'+n]={'bytes':file.stat().st_size,'sha256':a.sha(file)}
        return paths,expected
    def test_01_actual_nested_snapshot_root_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,expected=self.fixture(Path(tmp));out=Path(paths['run'])/'final-preservation'
            items=a.inventory_from_roots(list(paths.items()),out,expected)
            self.assertIn('r4_source/docs/study/control-r4/APPROVAL-TEMPLATE.json',dict(items))
            self.assertEqual(set(dict(items)),set(expected))
            wrong=dict(paths,r4_source=str(Path(paths['r4_source'])/'docs/study/control-r4'))
            with self.assertRaisesRegex(ValueError,'missing'):a.inventory_from_roots(list(wrong.items()),out,expected)
    def test_02_changed_and_missing_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,expected=self.fixture(Path(tmp));bad=copy.deepcopy(expected);bad['run/evidence.json']['sha256']='0'*64
            with self.assertRaises(ValueError):a.inventory_from_roots(list(paths.items()),Path(paths['run'])/'final-preservation',bad)
            with self.assertRaises(ValueError):a.inventory_from_roots(list(paths.items())[1:],Path(paths['run'])/'final-preservation',expected)
    def test_03_duplicate_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,expected=self.fixture(Path(tmp))
            with self.assertRaises(ValueError):a.inventory_from_roots(list(paths.items())+[('run',paths['run'])],Path(tmp)/'out',expected)
    def test_04_archive_all13roots_member_checks_and_no_repeat(self):
        r=a.load5();r.load_r4();sys.path.insert(0,str(a.ROOT.parent/'bindings-r1'))
        from preserve import verify_tar
        with tempfile.TemporaryDirectory() as tmp:
            paths,expected=self.fixture(Path(tmp));oldpaths={k:v for k,v in paths.items() if k not in ('r5_source','r5_control','r6_source','r6_control')}
            ctx=NS(run=Path(paths['run']),control=Path(paths['r6_control']),approval_sha='synthetic-authority',
                old=NS(control=Path(paths['r5_control']),baseline={'paths':oldpaths,'inventory':{k:v for k,v in expected.items() if k.split('/')[0] in oldpaths}}),
                binding={'r5_source':paths['r5_source'],'source':paths['r6_source'],'r5_manifest':'synthetic-r5','manifest':'synthetic-r6'})
            with patch.object(a,'guard',return_value={'successful_unique_tasks':339}),patch.object(r,'storage',return_value={'all_source_control_models_analysis':0}):
                result=a.archive(ctx)
                with self.assertRaises(ValueError):a.archive(ctx)
            request=a.read(ctx.run/'final-preservation/BACKUP-REQUEST.json')
            verify_tar(ctx.run/'final-preservation/final.tar',request['members'])
            self.assertEqual(len(request['root_labels']),13);self.assertTrue(set(expected)<=set(request['members']))
            self.assertEqual(result['members'],14) #13artificial files +exclusive archive intent
    def test_05_frozen_history_and_python39(self):
        for folder in ('bindings-r1','control-r2','control-r3','control-r4','finalization-r5'):
            root=a.ROOT.parent/folder
            for n,h in a.read(root/'SOURCE-MANIFEST.json')['files'].items():self.assertEqual(a.sha((a.REPO/n) if folder=='bindings-r1' else root/n),h)
        for p in a.ROOT.glob('*.py'):ast.parse(p.read_text(),feature_version=(3,9))
        for code in (t.STAGE,t.ARCHIVE):ast.parse(code,feature_version=(3,9))
    def test_06_no_science_entrypoint_and_false_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'approval.json';a.write(p,{'authorized':False})
            with self.assertRaisesRegex(ValueError,'disabled'):a.Context(p)
        code=(a.ROOT/'archive6.py').read_text()
        for forbidden in ('sbatch','squeue','sacct','Popen','optimizer','aggregate('):self.assertNotIn(forbidden,code)
if __name__=='__main__':unittest.main(verbosity=2)
