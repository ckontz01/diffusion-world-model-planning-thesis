"""Copy only sealed independent-study artifacts to a second local disk location.

Run from WSL. No planner is invoked and no partial comparative outcomes are
read. Full stage artifacts are copied only after independent stage verification.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path

REMOTE_ROOT='/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/'
REMOTE_CHECK=r'''import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1])
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
status={'collection_ready':False,'verified_stages':[],'terminal':False}
if (p/'INPUT-LOCK.json').exists():
 lock=json.loads((p/'INPUT-LOCK.json').read_text())
 for name,key in [('CONFIG.json','config_sha256'),('REGISTRY.json','registry_sha256'),('collection/COLLECTION.json','collection_sha256'),('COLLECTION-VALIDATION.json','collection_validation_sha256')]:
  assert sha(p/name)==lock[key]
 status['collection_ready']=True
 for stage in range(3):
  a=p/('analysis-%d'%stage)
  if (a/'INDEPENDENT-VERIFICATION.json').exists():
   v=json.loads((a/'INDEPENDENT-VERIFICATION.json').read_text())
   assert v['all_passed'] and v['summary_sha256']==sha(a/'SUMMARY.json')
   status['verified_stages'].append(stage)
 status['terminal']=(p/'TERMINAL.json').exists()
print(json.dumps(status))
'''

def sync(study,destination):
 import shlex
 if not study.startswith(REMOTE_ROOT) or not re.fullmatch(r'final-[A-Za-z0-9-]+',study[len(REMOTE_ROOT):]):
  raise ValueError('only this independent-study namespace may be backed up')
 status=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','prometheus',
     'python3 -c '+shlex.quote(REMOTE_CHECK)+' '+shlex.quote(study)],text=True))
 if not status['collection_ready']:
  print(json.dumps(status));return status
 destination=Path(destination)/Path(study).name;destination.mkdir(parents=True,exist_ok=True)
 def copy(name):
  subprocess.run(['rsync','-a','--protect-args','-e','ssh -o BatchMode=yes -o StrictHostKeyChecking=yes',
      'prometheus:'+study+'/'+name,str(destination)+'/'],check=True)
 for name in ('CONFIG.json','REGISTRY.json','INPUT-LOCK.json','COLLECTION-VALIDATION.json','collection'):
  copy(name)
 for stage in status['verified_stages']:
  copy('stage-%d'%stage);copy('analysis-%d'%stage)
 if status['terminal']:copy('TERMINAL.json')
 manifest=json.loads((destination/'collection/COLLECTION.json').read_text())
 for r in manifest['records']:
  q=destination/'collection'/r['file']
  assert hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256']
 status.update(local_directory=str(destination),references_hash_verified=len(manifest['records']),
               local_file_bytes=sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()))
 (destination/'BACKUP-STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
 print(json.dumps(status,indent=2));return status

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',required=True)
 p.add_argument('--destination',default='/home/chris/thesis-artifacts/independent-pusht')
 a=p.parse_args();sync(a.study,a.destination)
