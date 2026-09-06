"""Synthetic-only raw backup integrity tests; no SSH or research outcomes."""
import hashlib,json,tempfile,unittest
from pathlib import Path
import backup_completed_independent_pusht as b

class BackupTests(unittest.TestCase):
 def fixture(self,folder):
  task=Path(folder)/'stage-0/task-0000';result=task/'results';result.mkdir(parents=True)
  names=['RESULT.json']+[f'episode-00000-h{h}.{ext}' for h in (75,150) for ext in ('json','npz')]
  for n in names:(result/n).write_bytes(b'opaque outcome bytes; not parsed as JSON')
  (result/'sha256.txt').write_text(''.join(b.sha(result/n)+'  '+n+'\n' for n in names))
  done={'task':{'begin':0,'end':1},'result_sha256':b.sha(result/'RESULT.json')}
  (task/'DONE.json').write_text(json.dumps(done))
  row={'path':'stage-0/task-0000','done_sha256':b.sha(task/'DONE.json'),'result_sha256':done['result_sha256']}
  return result,row
 def test_namespace(self):
  self.assertEqual(b.study_name(b.PREFIX+'final-20260906-abcd'),'final-20260906-abcd')
  for x in ('/etc/passwd',b.PREFIX+'../elsewhere',b.PREFIX+'final-x/../y'):
   with self.assertRaises(ValueError):b.study_name(x)
 def test_opaque_payloads_pass_without_interpretation(self):
  with tempfile.TemporaryDirectory() as d:
   _,r=self.fixture(d);self.assertGreater(b.verify_task(d,r),0)
 def test_corrupt_payload(self):
  with tempfile.TemporaryDirectory() as d:
   p,r=self.fixture(d);(p/'episode-00000-h75.npz').write_bytes(b'corrupt')
   with self.assertRaises(RuntimeError):b.verify_task(d,r)
 def test_unsafe_manifest(self):
  with tempfile.TemporaryDirectory() as d:
   p,r=self.fixture(d)
   with (p/'sha256.txt').open('a') as f:f.write('0'*64+'  ../outside\n')
   with self.assertRaises(RuntimeError):b.verify_task(d,r)
 def test_missing_coverage(self):
  with tempfile.TemporaryDirectory() as d:
   p,r=self.fixture(d);z=(p/'sha256.txt').read_text().splitlines();(p/'sha256.txt').write_text('\n'.join(z[:-1])+'\n')
   with self.assertRaises(RuntimeError):b.verify_task(d,r)
 def test_changed_done(self):
  with tempfile.TemporaryDirectory() as d:
   p,r=self.fixture(d);(p.parent/'DONE.json').write_text('{}')
   with self.assertRaises(RuntimeError):b.verify_task(d,r)
 def test_atomic_index(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'index.json';b.update_index(p,{'shards':{},'payloads_interpreted':False})
   self.assertFalse(json.loads(p.read_text())['payloads_interpreted']);self.assertFalse(p.with_suffix('.tmp').exists())
 def test_invalid_probe_row(self):
  for path in ('stage-3/task-0000','stage-0/../private','stage-0/task-1'):
   with self.assertRaises(ValueError):b.validate_row({'path':path,'done_sha256':'0'*64,'result_sha256':'1'*64})
if __name__=='__main__':unittest.main()
