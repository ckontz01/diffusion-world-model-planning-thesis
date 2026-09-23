"""Synthetic transport and disabled-authority tests; no cluster calls."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import r2_core as r
import transport as t
import finalize
from test_r2 import Fixture

class TransportTests(unittest.TestCase):
    def test_instruction_preserves_original_crlf_bytes(self):
        raw=(r.ROOT/'INSTRUCTION.txt').read_bytes()
        self.assertEqual(t.instruction().encode('utf8'),raw)
        self.assertEqual(r.hashlib.sha256(t.instruction().encode('utf8')).hexdigest(),r.read(r.ROOT/'CONTRACT.json')['instruction_sha256'])

    def test_fixed_bootstrap_binary_and_quoting(self):
        payload=bytes(range(256))*16
        code="import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"
        p=subprocess.run([sys.executable,'-B','-S','-c',t.BOOTSTRAP],input=t.envelope(code,payload,{'quoted':'a\"b\'c\\d'}),capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.decode().strip(),r.hashlib.sha256(payload).hexdigest())
        with self.assertRaises(ValueError):t.envelope(code,b'x'*2000000,{})
        p=subprocess.run([sys.executable,'-B','-S','-c',t.BOOTSTRAP],input=b'x'*2000001,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertIn(b'Transport envelope bound',p.stderr)

    def test_python39_grammar_and_remote_operations(self):
        for path in r.ROOT.glob('*.py'):ast.parse(path.read_text(encoding='utf8'),feature_version=(3,9))
        for script in (t.BOOTSTRAP,t.STAGE,t.LAUNCH,t.OBSERVE):ast.parse(script,feature_version=(3,9));compile(script,'operation','exec')
        self.assertNotIn('dispatch.py',t.LAUNCH)
        self.assertIn('r.reconcile(ctx)',t.LAUNCH)

    def test_false_authority_before_source_or_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'FALSE.json';r.write(path,{'schema':'ACV0-control-only-r2','authorized':False,'instruction':'','binding':{}})
            for command in (['controller.py','--approval',str(path)],['finalize.py','archive','--approval',str(path)]):
                p=subprocess.run([sys.executable,'-B','-S',str(r.ROOT/command[0])]+command[1:],capture_output=True)
                self.assertNotEqual(p.returncode,0);self.assertIn(b'R2 continuation disabled',p.stderr)
                self.assertNotIn(b'No module named',p.stderr)

    def test_r2_extra_bytes_counted(self):
        import dispatch
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp);base={'source_control_models_analysis':499999999,'full_live_reservation':1812000000,'inclusive_reservation':7248000000}
            with patch.object(dispatch,'storage',return_value=base):
                with self.assertRaises(ValueError):r.storage(x)
            base['source_control_models_analysis']=10
            with patch.object(dispatch,'storage',return_value=base):
                result=r.storage(x);self.assertEqual(result['source_control_models_analysis_including_r2'],10+r.total(r.ROOT)+r.total(x.control))

    def test_final_scheduler_rejects_unknown_341st_and_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=Fixture(tmp)
            rows=[r.parse_row(x.baseline['scheduler_rows'][1])]+[x.row(j,str(800000+i)) for i,j in enumerate(x.jobs[1:])]
            result={'jobs':rows};raw='\n'.join('|'.join(v)+'|00:00:00||' for v in [x.baseline['scheduler_rows'][0]]+[x.raw(v) for v in rows])
            with patch.dict('os.environ',{'USER':'synthetic'}):
                for extra,queue,ok in [('', '',True),('\n999999|acv0-unknown|FAILED|1:0|1|4|cpu=4,gres/gpu=1,mem=24G,node=1|gpu09|a6000|normal-a6000|superworld|30|00:00:00||','',False),('','304193|acv0r1-collect-fit-490|RUNNING',False)]:
                    outputs=[NS(returncode=0,stdout=raw+extra),NS(returncode=0,stdout=queue)]
                    with patch.object(subprocess,'run',side_effect=outputs):
                        if ok:self.assertEqual(len(finalize.scheduler_snapshot(x,result)['allocations']),340)
                        else:
                            with self.assertRaises(ValueError):finalize.scheduler_snapshot(x,result)

if __name__=='__main__':unittest.main(verbosity=2)
