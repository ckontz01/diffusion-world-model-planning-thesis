"""CPU stdlib fake-device and call-order regressions; no CUDA/research imports."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import hardware

class DeviceGate(unittest.TestCase):
    def fake(self,name=hardware.EXPECTED_DEVICE,count=1,available=True):
        return SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:available,device_count=lambda:count,get_device_name=lambda index:name))

    def test_exact_known_partition_device_accepted(self):
        records=[]
        out=hardware.verify_device(self.fake(),records.append)
        self.assertEqual(out['device_name'],'NVIDIA RTX 6000 Ada Generation')
        self.assertEqual(records,[out])
        self.assertNotIn('A6000',out['device_name'])

    def test_other_device_and_unavailable_fail_with_receipt(self):
        for name,count,available in [('NVIDIA RTX A6000',1,True),('NVIDIA A100',1,True),(hardware.EXPECTED_DEVICE,2,True),(None,0,False)]:
            records=[]
            with self.assertRaises(ValueError):hardware.verify_device(self.fake(name,count,available),records.append)
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]['no_model_or_reference_loaded_yet'],True)

    def test_gate_precedes_backend_and_reference_load(self):
        path=Path(__file__).with_name('worker.py');tree=ast.parse(path.read_text())
        calls={node.func.id:node.lineno for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('verify_device','load_backend','source_factory')}
        self.assertLess(calls['verify_device'],calls['load_backend'])
        self.assertLess(calls['load_backend'],calls['source_factory'])

if __name__=='__main__':unittest.main(verbosity=2)
