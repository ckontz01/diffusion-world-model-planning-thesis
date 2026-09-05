"""One-shot backup of completed, hash-sealed shards without outcome interpretation.

This does not poll, submit jobs, aggregate success, or alter scientific inputs.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
REMOTE_ROOT='/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/'
PROBE = r'''import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lock=json.loads((root/'INPUT-LOCK.json').read_text())
assert sha(root/'CONFIG.json')==lock['config_sha256']
assert sha(root/'REGISTRY.json')==lock['registry_sha256']
registry=json.loads((root/'REGISTRY.json').read_text())
rows=[]
for stage,tasks in enumerate(registry['stages']):
 for task in tasks:
  p=root/('stage-%d'%stage)/('task-%04d'%task['task'])
  if not (p/'DONE.json').exists():continue
  d=json.loads((p/'DONE.json').read_text())
  assert d['task']==task and d['config_sha256']==lock['config_sha256']
  assert d['source_manifest_sha256']==lock['source_manifest_sha256']
  assert sha(p/'results/RESULT.json')==d['result_sha256']
  files=[]
  for line in (p/'results/sha256.txt').read_text().splitlines():
   digest,name=line.split(maxsplit=1)
   assert Path(name).name==name and sha(p/'results'/name)==digest
   files.append({'name':name,'sha256':digest})
  rows.append({'stage':stage,'task':task['task'],'directory':str(p.relative_to(root)),
               'done_sha256':sha(p/'DONE.json'),'files':files})
print(json.dumps({'shards':rows,'outcome_values_parsed':False,'input_lock_sha256':sha(root/'INPUT-LOCK.json')}))
'''

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def archive(study,destination):
 import shlex
 if not study.startswith(REMOTE_ROOT) or not re.fullmatch(r'final-[A-Za-z0-9-]+',study[len(REMOTE_ROOT):]):
  raise ValueError('unsupported study path')
 dest=Path(destination)/Path(study).name;dest.mkdir(parents=True,exist_ok=True)
 remote=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','prometheus',
      'python3 -c '+shlex.quote(PROBE)+' '+shlex.quote(study)],text=True))
 for r in remote['shards']:
  local=dest/r['directory'];local.parent.mkdir(parents=True,exist_ok=True)
  subprocess.run(['rsync','-a','--protect-args','-e','ssh -o BatchMode=yes -o StrictHostKeyChecking=yes',
      'prometheus:'+study+'/'+r['directory'],str(local.parent)+'/'],check=True)
  assert sha(local/'DONE.json')==r['done_sha256']
  for f in r['files']:assert sha(local/'results'/f['name'])==f['sha256']
 report={'completed_shards_backed_up':len(remote['shards']),
   'shards':[{'stage':r['stage'],'task':r['task'],'file_count':len(r['files']),
              'done_sha256':r['done_sha256']} for r in remote['shards']],
   'input_lock_sha256':remote['input_lock_sha256'],'outcome_values_parsed':False,'destination':str(dest)}
 (dest/'SHARD-BACKUP-STATUS.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',required=True)
 p.add_argument('--destination',default='/home/chris/thesis-artifacts/independent-pusht')
 a=p.parse_args();archive(a.study,a.destination)
