"""New stdlib artificial tests only; no framework or checkpoint deserialization."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from wm_diag0_preflight_v1.common import relative, reservation, verify, identity, write_new, ROOT
from wm_diag0_preflight_v1.worker import tensor_slots

class Tensor: pass
class FakeModule:
    def __init__(self):
        self._parameters={'weight':Tensor()}; self._buffers={'persistent':Tensor(),'scratch':Tensor()}
        self._non_persistent_buffers_set={'scratch'}; self._modules={}
        self.bias=Tensor(); self.shared=self._parameters['weight']; self.extra={'mask':[Tensor()]}

class GateTests(unittest.TestCase):
    def test_unregistered_mask_is_inventoried(self):
        names={n:k for n,k,t in tensor_slots(FakeModule(),lambda t:isinstance(t,Tensor))}
        self.assertEqual(names['bias'],'unregistered'); self.assertIn('extra.mask.0',names)
    def test_persistent_distinction(self):
        names={n:k for n,k,t in tensor_slots(FakeModule(),lambda t:isinstance(t,Tensor))}
        self.assertEqual(names['scratch'],'nonpersistent_buffer'); self.assertEqual(names['persistent'],'persistent_buffer')
    def test_shared_identity_preserved(self):
        rows={n:t for n,k,t in tensor_slots(FakeModule(),lambda t:isinstance(t,Tensor))}
        self.assertIs(rows['weight'],rows['shared'])
    def test_paths(self):
        for n in ('../bad','/absolute','C:/drive','x\\y','a/../b','a/./b',''):
            with self.assertRaises(ValueError): relative(n)
        self.assertEqual(str(relative('encoder/dinov2/model.py')),'encoder/dinov2/model.py')
    def test_failed_attempts_not_free(self):
        self.assertEqual(reservation(1200),13800)
        with self.assertRaises(ValueError): reservation(1201)
        with self.assertRaises(ValueError): reservation(-1)
    def test_exclusive_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json'; write_new(p,{'a':1})
            with self.assertRaises(FileExistsError): write_new(p,{'a':2})
    def test_bad_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json'; write_new(p,{'a':1}); row=identity(p); verify(p,row)
            with self.assertRaises(ValueError): verify(p,dict(row,sha256='0'*64))
    def test_no_model_forward_or_hub_or_hydra_call(self):
        tree=ast.parse((ROOT/'wm_diag0_preflight_v1/worker.py').read_text())
        forbidden={'forward','get_cost','rollout','hub','instantiate','fit','step','reset','make'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute): self.assertNotIn(node.func.attr,forbidden)
    def test_missing_mask_cannot_silently_pass_source_guard(self):
        s=(ROOT/'wm_diag0_preflight_v1/worker.py').read_text()
        self.assertIn("not hasattr(m,'bias')",s); self.assertIn('len(masks)!=6',s)
    def test_parse_new_sources(self):
        for p in (ROOT/'wm_diag0_preflight_v1').glob('*.py'): ast.parse(p.read_text(),filename=str(p))
    def test_parse_embedded_remote_sources(self):
        for name in ('deploy.py','inventory_r1.py','lewm_source.py'):
            tree=ast.parse((ROOT/'wm_diag0_preflight_v1'/name).read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith('import '):
                    ast.parse(n.value,filename='remote:'+name,feature_version=(3,6))

if __name__=='__main__': unittest.main()
