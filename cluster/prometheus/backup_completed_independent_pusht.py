"""Incremental byte-level backup of completed independent-benchmark shards.

Copies only DONE-sealed tasks. Outcome JSON/NPZ payloads are hashed, never
parsed for scores. No model, job submission, cancellation or inference occurs.
The final verified-result exporter remains a separate process.
"""
import argparse, hashlib, json, os, re, shlex, subprocess, time
from pathlib import Path

PREFIX = '/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/'
PROBE = r"""import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lock=json.loads((root/'INPUT-LOCK.json').read_text())
assert sha(root/'CONFIG.json')==lock['config_sha256']
rows=[]
for stage in range(3):
 for done in sorted((root/('stage-%d'%stage)).glob('task-*/DONE.json')):
  d=json.loads(done.read_text())
  assert d['config_sha256']==lock['config_sha256']
  assert d['source_manifest_sha256']==lock['source_manifest_sha256']
  parent=done.parent
  assert parent.name=='task-%04d'%d['task']['task']
  rows.append({'path':str(parent.relative_to(root)), 'done_sha256':sha(done),
               'result_sha256':d['result_sha256']})
print(json.dumps({'rows':rows,'terminal':(root/'TERMINAL.json').exists(),
                  'config_sha256':lock['config_sha256']}))
"""

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def study_name(study):
 if not study.startswith(PREFIX):raise ValueError('wrong remote study root')
 name=study[len(PREFIX):]
 if not re.fullmatch(r'final-[A-Za-z0-9-]+',name):raise ValueError('unsafe study name')
 return name

def validate_row(row):
 if set(row)!={'path','done_sha256','result_sha256'}:raise ValueError('unexpected metadata keys')
 if not re.fullmatch(r'stage-[0-2]/task-[0-9]{4}',row['path']):raise ValueError('unsafe task path')
 for key in ('done_sha256','result_sha256'):
  if not re.fullmatch(r'[0-9a-f]{64}',row[key]):raise ValueError('invalid digest')

def verify_task(local,row):
 validate_row(row);root=Path(local)/row['path']
 if sha(root/'DONE.json')!=row['done_sha256']:raise RuntimeError('DONE identity mismatch')
 # This file contains task metadata, not per-run outcomes.
 done=json.loads((root/'DONE.json').read_text())
 if done['result_sha256']!=row['result_sha256']:raise RuntimeError('result seal mismatch')
 result=root/'results'
 if sha(result/'RESULT.json')!=row['result_sha256']:raise RuntimeError('result bytes differ')
 lines=(result/'sha256.txt').read_text().splitlines();names=set()
 for line in lines:
  digest,name=line.split(maxsplit=1)
  if not re.fullmatch(r'[0-9a-f]{64}',digest):raise RuntimeError('invalid file seal')
  if not re.fullmatch(r'RESULT.json|episode-[0-9]{5}-h(?:75|150)\.(?:json|npz)',name):raise RuntimeError('unsafe sealed filename')
  if name in names:raise RuntimeError('duplicate filename in seal')
  names.add(name)
  if (result/name).is_symlink() or sha(result/name)!=digest:raise RuntimeError('artifact digest mismatch')
 count=done['task']['end']-done['task']['begin']
 expected={'RESULT.json'}|{f'episode-{i:05d}-h{h}.{ext}' for i in range(done['task']['begin'],done['task']['end']) for h in (75,150) for ext in ('json','npz')}
 if names!=expected or len(names)!=1+4*count:raise RuntimeError('incomplete shard coverage')
 return sum((result/n).stat().st_size for n in names)

def update_index(path,state):
 path=Path(path);temp=path.with_suffix('.tmp')
 with temp.open('w') as f:
  json.dump(state,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(temp,path)

def sync(study,destination):
 local=Path(destination)/study_name(study);local.mkdir(parents=True,exist_ok=True)
 command='python3 -c '+shlex.quote(PROBE)+' '+shlex.quote(study)
 data=json.loads(subprocess.check_output(['ssh','-n','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10','prometheus',command],text=True,timeout=120))
 index=local/'COMPLETED-SHARD-BACKUP.json'
 state=json.loads(index.read_text()) if index.exists() else {'study':study,'shards':{},'payloads_interpreted':False}
 if state['study']!=study:raise RuntimeError('wrong local study identity')
 added=0
 for row in data['rows']:
  validate_row(row)
  old=state['shards'].get(row['path'])
  if old:
   if old['done_sha256']!=row['done_sha256'] or old['result_sha256']!=row['result_sha256']:raise RuntimeError('previously completed shard changed')
   continue
  target=local/Path(row['path']).parent;target.mkdir(parents=True,exist_ok=True)
  subprocess.run(['rsync','-a','--protect-args','-e','ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10',
                  'prometheus:'+study+'/'+row['path'],str(target)+'/'],check=True,stdin=subprocess.DEVNULL,timeout=900)
  byte_count=verify_task(local,row)
  state['shards'][row['path']]={**row,'verified_bytes':byte_count}
  state['updated_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());update_index(index,state);added+=1
 return {'new_shards':added,'sealed_shards_backed_up':len(state['shards']),
         'verified_bytes':sum(r['verified_bytes'] for r in state['shards'].values()),
         'terminal':data['terminal'],'payloads_interpreted':False,'index':str(index)}

def main(study,destination,interval,max_hours):
 end=time.monotonic()+max_hours*3600;errors=0
 while time.monotonic()<end:
  try:
   result=sync(study,destination);errors=0;print(json.dumps(result),flush=True)
   if result['terminal']:return 0
  except Exception as e:
   errors+=1;print(json.dumps({'backup_error':type(e).__name__,'message':str(e),'consecutive_errors':errors}),flush=True)
   if errors>=3:return 2
  time.sleep(interval)
 return 3

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',required=True)
 p.add_argument('--destination',default='/home/chris/thesis-artifacts/independent-pusht')
 p.add_argument('--interval',type=int,default=300);p.add_argument('--max-hours',type=int,default=168);p.add_argument('--once',action='store_true');a=p.parse_args()
 if a.once:print(json.dumps(sync(a.study,a.destination)))
 else:raise SystemExit(main(a.study,a.destination,a.interval,a.max_hours))
