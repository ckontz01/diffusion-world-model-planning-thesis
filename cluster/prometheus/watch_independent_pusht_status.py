"""Bounded foreground technical-status watch; no scientific outcome reads.

This never submits/cancels jobs or changes a study. Terminate with Ctrl+C.
"""
import argparse,json,shlex,subprocess,time
from pathlib import Path
PROBE = r'''import json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);cfg=json.loads((p/'CONFIG.json').read_text())
rows=[]
for i in range(len(cfg['looks'])):
 sub=p/('SUBMISSION-%d.json'%i)
 if not sub.exists():continue
 d=json.loads(sub.read_text());jid=d.get('array_job')
 s=subprocess.check_output(['sacct','-X','-n','-P','-j',jid,'-o','State'],universal_newlines=True)
 counts={}
 for line in s.splitlines():
  state=line.strip().split('|')[0].split()[0] if line.strip() else ''
  if state:counts[state]=counts.get(state,0)+1
 rows.append({'stage':i,'array':jid,'states':counts,
              'done_shards':sum(1 for q in (p/('stage-%d'%i)).glob('task-*/DONE.json')),
              'analysis_verified':(p/('analysis-%d'%i)/'INDEPENDENT-VERIFICATION.json').exists()})
print(json.dumps({'stages':rows,'terminal_exists':(p/'TERMINAL.json').exists()}))
'''

def watch(study,minutes,interval):
 deadline=time.monotonic()+minutes*60
 while True:
  x=subprocess.run(['ssh','-n','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',
       'prometheus','python3 -c '+shlex.quote(PROBE)+' '+shlex.quote(study)],capture_output=True,text=True,timeout=45)
  if x.returncode:
   print(json.dumps({'transport_error':True,'returncode':x.returncode}),flush=True);return 2
  state=json.loads(x.stdout);state['checked_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
  print(json.dumps(state),flush=True)
  if state['terminal_exists']:return 0
  bad=any(any(k not in ('PENDING','RUNNING','COMPLETED','COMPLETING','CONFIGURING') for k in r['states']) for r in state['stages'])
  if bad:return 3
  if time.monotonic()>=deadline:return 4
  time.sleep(interval)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--minutes',type=int,default=30)
 p.add_argument('--interval',type=int,default=120);a=p.parse_args()
 raise SystemExit(watch(a.study,a.minutes,a.interval))
