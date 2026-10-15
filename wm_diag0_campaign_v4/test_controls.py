import ast,json,tempfile,time,unittest
from pathlib import Path
from .submit import specification
from .final_archive import create,ident
from .verify_archive import verify

class Controls(unittest.TestCase):
    def test_finite_serial_DAG_exact_caps(self):
        rows=specification();self.assertEqual(sum(n*s for _,n,s,_,_,gpu,_ in rows if gpu),468000)
        self.assertEqual([(x[0],x[6]) for x in rows],[('readout',None),('technical','readout'),('grid','technical'),('analysis','grid')])
        self.assertEqual(sum(x[1] for x in rows if x[5]),132)
    def test_every_new_source_and_remote_literal_compiles(self):
        count=0
        for p in Path(__file__).parent.glob('*.py'):
            t=ast.parse(p.read_text());compile(t,str(p),'exec')
            if p.name in ('supervisor.py','final_archive.py'):ast.parse(p.read_text(),feature_version=(3,6))
            for n in ast.walk(t):
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith(('import json','import hashlib','import base64')):ast.parse(n.value,feature_version=(3,6));count+=1
        self.assertGreater(count,5)
    def test_artificial_archive_whole_every_member_and_no_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            for name in ('preflight-v1','preflight-v1-stage-r1','native-v3','native-v3-import-r1','native-v3-source-r3','campaign-v4'):(base/name).mkdir()
            root=base/'campaign-v4';(root/'source').mkdir();(root/'controls').mkdir();(root/'source/CONTRACT.json').write_text('{"domain":"artificial"}')
            task=root/'tasks/analysis-0';(task/'output').mkdir(parents=True);(task/'controls').mkdir()
            (task/'output/MEMBERS.json').write_text('{}');(task/'controls/ACCEPTED.json').write_text(json.dumps({'accepted':True,'diagnostic_parents':128,'source_roots':120,'output_seal':ident(task/'output/MEMBERS.json')}))
            venv=base/'artificial-runtime';venv.mkdir();(venv/'example').write_bytes(b'artificial numeric fixture')
            (root/'controls/RUNTIME-MANIFEST.json').write_text(json.dumps({'members':{'example':ident(venv/'example')}}))
            sif=base/'artificial-sif';sif.write_bytes(b'NOT AN EXECUTABLE IMAGE')
            c={'venv':str(venv),'sif':str(sif),'lewm':{},'renderer':{'aliases':{}}}
            row=create(root,c,time.monotonic()+10);result=verify(row['archive'],row['whole'],ident(root/'source/CONTRACT.json')['sha256'])
            self.assertEqual(result['extracted_or_executed_files'],0)
            with self.assertRaises(FileExistsError):create(root,c,time.monotonic()+10)
            with self.assertRaises(ValueError):verify(row['archive'],{'bytes':1,'sha256':'0'*64},'bad')

if __name__=='__main__':unittest.main()
