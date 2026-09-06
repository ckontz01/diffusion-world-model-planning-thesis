"""User-owned archival process for the already-submitted independent study.

No experiment submission, cancellation, tuning or statistical decision occurs
here. Only independently verified complete-look artifacts are interpreted and
published. The Slurm controller alone follows the frozen statistical protocol.
No credential is embedded; git uses the user's existing local authentication.
"""
import argparse,hashlib,json,shlex,shutil,subprocess,sys,time
from pathlib import Path
from backup_independent_pusht import sync

REPO=Path('/home/chris/thesis')
BRANCH='independent-pusht-benchmark'
PROBE=r'''import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);lock=json.loads((root/'INPUT-LOCK.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'CONFIG.json')==lock['config_sha256']
rows=[]
for stage in range(3):
 a=root/('analysis-%d'%stage)
 if not (a/'INDEPENDENT-VERIFICATION.json').exists():continue
 v=json.loads((a/'INDEPENDENT-VERIFICATION.json').read_text())
 assert v['all_passed'] and v['summary_sha256']==sha(a/'SUMMARY.json')
 rows.append({'stage':stage,'summary_sha256':v['summary_sha256']})
terminal=(root/'TERMINAL.json').exists()
if terminal:
 z=json.loads((root/'TERMINAL.json').read_text())
 assert z['complete'] and any(r['stage']==z['analysis_stage'] and r['summary_sha256']==z['summary_sha256'] for r in rows)
print(json.dumps({'verified':rows,'terminal_exists':terminal}))
'''

def git(*args):
 return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()

def committed(path):
 try:
  git('cat-file','-e','HEAD:'+str(path.relative_to(REPO)));return True
 except subprocess.CalledProcessError:return False

def export(study,destination):
 branch=git('branch','--show-current')
 if branch!=BRANCH:raise RuntimeError('archiver refuses to write on another branch')
 status=json.loads(subprocess.check_output(['ssh','-n','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',
   'prometheus','python3 -c '+shlex.quote(PROBE)+' '+shlex.quote(study)],text=True,timeout=60))
 evidence=REPO/'cluster/prometheus/independent-pusht-evidence'
 pending=[r for r in status['verified'] if not committed(evidence/('look-%d'%r['stage'])/'INDEPENDENT-VERIFICATION.json')]
 terminal_new=status['terminal_exists'] and not committed(evidence/'TERMINAL.json')
 if not pending and not terminal_new:return {'new_looks':0,'terminal':status['terminal_exists']}
 # Never stage or commit an unrelated user's/agent's already-staged changes.
 staged=git('diff','--cached','--name-only').splitlines()
 allowed=('cluster/prometheus/independent-pusht-evidence/AUTO-ARCHIVE-STATUS.json','cluster/prometheus/independent-pusht-evidence/TERMINAL.json')
 if any(not (q.startswith('cluster/prometheus/independent-pusht-evidence/look-') or q in allowed) for q in staged):raise RuntimeError('unrelated staged changes present')
 backup=sync(study,destination)
 local=Path(backup['local_directory']);paths=[]
 for r in pending:
  src=local/('analysis-%d'%r['stage']);dst=evidence/('look-%d'%r['stage']);dst.mkdir(exist_ok=True)
  assert hashlib.sha256((src/'SUMMARY.json').read_bytes()).hexdigest()==r['summary_sha256']
  for line in (src/'sha256.txt').read_text().splitlines():
   digest,name=line.split(maxsplit=1)
   assert Path(name).name==name and hashlib.sha256((src/name).read_bytes()).hexdigest()==digest
  for name in ('SUMMARY.json','RESULT.md','INDEPENDENT-VERIFICATION.json','ALL-EPISODES.tsv.gz','EPISODE-TENSOR.npz','sha256.txt'):
   shutil.copy2(src/name,dst/name);paths.append(str((dst/name).relative_to(REPO)))
 if terminal_new:
  shutil.copy2(local/'TERMINAL.json',evidence/'TERMINAL.json');paths.append(str((evidence/'TERMINAL.json').relative_to(REPO)))
 state={'verified_stages':[r['stage'] for r in status['verified']],'terminal':status['terminal_exists'],
        'last_backup':backup,'study':study,'updated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'method':'standalone archival exporter; no model/experiment decisions'}
 (evidence/'AUTO-ARCHIVE-STATUS.json').write_text(json.dumps(state,indent=2)+'\n')
 paths.append(str((evidence/'AUTO-ARCHIVE-STATUS.json').relative_to(REPO)))
 git('add','--',*paths)
 git('commit','-m','Archive independently verified PushT evaluation look(s) '+','.join(str(r['stage']+1) for r in pending)+(' and terminal record' if terminal_new else ''))
 git('push','origin',BRANCH)
 return {'new_looks':len(pending),'terminal':status['terminal_exists'],'commit':git('rev-parse','HEAD')}

def main(study,destination,interval,max_hours):
 deadline=time.monotonic()+max_hours*3600
 failures=0
 while time.monotonic()<deadline:
  try:
   # Retry an interrupted git push without creating another scientific result.
   if git('branch','--show-current')!=BRANCH:raise RuntimeError('working branch changed')
   if git('rev-list','--count','origin/'+BRANCH+'..HEAD')!='0':git('push','origin',BRANCH)
   result=export(study,destination);failures=0
   print(json.dumps(result),flush=True)
   if result['terminal']:return 0
  except Exception as exc:
   failures+=1;print(json.dumps({'archival_error':type(exc).__name__,'message':str(exc),'consecutive_errors':failures}),flush=True)
   if failures>=3:return 2
  time.sleep(interval)
 return 3

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',required=True)
 p.add_argument('--destination',default='/home/chris/thesis-artifacts/independent-pusht')
 p.add_argument('--interval',type=int,default=300);p.add_argument('--max-hours',type=int,default=168)
 p.add_argument('--once',action='store_true');a=p.parse_args()
 if a.once:print(json.dumps(export(a.study,a.destination)))
 else:raise SystemExit(main(a.study,a.destination,a.interval,a.max_hours))
