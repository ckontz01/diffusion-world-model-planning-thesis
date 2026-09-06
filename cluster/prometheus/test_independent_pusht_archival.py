"""Isolated publication tests; no SSH, model, git or scheduler operations."""
import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import archive_verified_independent_pusht as a

class Tests(unittest.TestCase):
 def test_unverified_outputs_are_not_exported(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);calls=[]
   def git(*args):
    calls.append(args)
    if args==('branch','--show-current'):return a.BRANCH
    return ''
   with patch.object(a,'REPO',root),patch.object(a,'git',git),patch.object(a.subprocess,'check_output',return_value=json.dumps({'verified':[],'terminal_exists':False})),patch.object(a,'sync',side_effect=AssertionError('must not copy partial results')):
    self.assertEqual(a.export('test','unused'),{'new_looks':0,'terminal':False})
    self.assertFalse(list(root.rglob('*')))
 def test_wrong_branch_fails_before_remote_access(self):
  with patch.object(a,'git',return_value='unrelated'),patch.object(a.subprocess,'check_output',side_effect=AssertionError('no remote')):
   with self.assertRaisesRegex(RuntimeError,'another branch'):a.export('test','unused')
 def fixture(self,d):
  repo=Path(d)/'repo';(repo/'cluster/prometheus/independent-pusht-evidence').mkdir(parents=True)
  local=Path(d)/'backup';src=local/'analysis-0';src.mkdir(parents=True)
  names=('SUMMARY.json','RESULT.md','INDEPENDENT-VERIFICATION.json','ALL-EPISODES.tsv.gz','EPISODE-TENSOR.npz')
  for n in names:(src/n).write_text('synthetic fixture '+n)
  (src/'sha256.txt').write_text(''.join(hashlib.sha256((src/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names))
  status={'verified':[{'stage':0,'summary_sha256':hashlib.sha256((src/'SUMMARY.json').read_bytes()).hexdigest()}],'terminal_exists':False}
  return repo,local,src,status
 def test_only_verified_whitelisted_files_are_committed(self):
  with tempfile.TemporaryDirectory() as d:
   repo,local,src,status=self.fixture(d);calls=[]
   def git(*args):
    calls.append(args)
    return a.BRANCH if args==('branch','--show-current') else ('fixturecommit' if args==('rev-parse','HEAD') else '')
   with patch.object(a,'REPO',repo),patch.object(a,'git',git),patch.object(a,'committed',return_value=False),patch.object(a.subprocess,'check_output',return_value=json.dumps(status)),patch.object(a,'sync',return_value={'local_directory':str(local)}):
    r=a.export('test','unused');self.assertEqual(r['new_looks'],1)
   add=next(c for c in calls if c[0]=='add')
   self.assertTrue(all(q.startswith('cluster/prometheus/independent-pusht-evidence/') for q in add[2:]))
   self.assertTrue(any(c[0]=='commit' for c in calls));self.assertTrue(any(c[0]=='push' for c in calls))
 def test_corrupt_backup_is_not_published(self):
  with tempfile.TemporaryDirectory() as d:
   repo,local,src,status=self.fixture(d);(src/'RESULT.md').write_text('corrupt');calls=[]
   def git(*args):
    calls.append(args);return a.BRANCH if args==('branch','--show-current') else ''
   with patch.object(a,'REPO',repo),patch.object(a,'git',git),patch.object(a,'committed',return_value=False),patch.object(a.subprocess,'check_output',return_value=json.dumps(status)),patch.object(a,'sync',return_value={'local_directory':str(local)}):
    with self.assertRaises(AssertionError):a.export('test','unused')
   self.assertFalse(any(c[0]=='commit' for c in calls))
 def test_foreign_staged_files_are_not_committed(self):
  with tempfile.TemporaryDirectory() as d:
   repo,local,src,status=self.fixture(d)
   def git(*args):return a.BRANCH if args==('branch','--show-current') else 'unrelated.txt'
   with patch.object(a,'REPO',repo),patch.object(a,'git',git),patch.object(a,'committed',return_value=False),patch.object(a.subprocess,'check_output',return_value=json.dumps(status)),patch.object(a,'sync',side_effect=AssertionError('no copy')):
    with self.assertRaisesRegex(RuntimeError,'unrelated staged'):a.export('test','unused')

if __name__=='__main__':unittest.main()
