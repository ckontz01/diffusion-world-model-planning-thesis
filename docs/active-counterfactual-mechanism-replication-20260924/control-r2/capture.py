"""Read-only R2 baseline: both terminal failures, all retained bytes, no science decoding."""
import r1 as r
import time
from transport import remote

if __name__=='__main__':
    r.require(not (r.ROOT/'BASELINE.json').exists(),'Exclusive fresh R2 capture')
    code='import sys,json,subprocess,os,time\nfrom pathlib import Path\n'
    code+='root=Path('+repr(r.OLD_SOURCE+'/'+r.REL)+')\n'
    code+='sys.path.insert(0,str(root));import common as c;import scheduler\n'
    code+='''old=Path('''+repr(r.OLD_CONTROL)+''');r1=Path('''+repr(r.R1_CONTROL)+''');run=Path('''+repr(r.RUN)+''')
science=Path('''+repr(r.OLD_SOURCE)+''');r1_source=Path('''+repr(r.R1_SOURCE)+''')
auth=c.Authorization(old/'EXECUTION-APPROVAL.json',str(run))
assert auth.approval_sha=='''+repr(r.APPROVAL)+''' and auth.approval['package_sha256']=='''+repr(r.SCIENCE)+'''
oldstop=c.sha(old/'STOP.json');r1stop=c.sha(r1/'STOP.json')
assert oldstop=='237cd6138603a1d72a2f04f6c1d623746f03e3a40da5c7b89c1dd667cba9458b'
assert r1stop=='70fe437716a441d34d9845a3af90ad09d7f3de988c4ea105a9e454289ef73eac'
for control in (old,r1):
 identity=c.read(control/'CONTROLLER-PROCESS.json');p=Path('/proc')/str(identity['pid'])
 assert not p.exists() or p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=str(identity['start_ticks'])
p=subprocess.run(['/usr/bin/sacct','-X','-n','-P','-j','304589,304591','--format='+scheduler.FIELDS],capture_output=True,text=True,timeout=60)
assert p.returncode==0
rows=[scheduler.parse(x) for x in p.stdout.splitlines() if x]
assert [x['job'] for x in rows]==['304589','304591'] and [x['state'] for x in rows]==['FAILED','FAILED'] and [x['seconds'] for x in rows]==[0,8]
for row in rows:scheduler.allocation(c.grid()[0],row,successful=False)
assert c.read(run/'submissions/fit-pair1-joint.json')['job']=='304589'
assert c.read(run/'submissions-r1/fit-pair1-joint.json')['job']=='304591'
assert {p.name for p in (run/'fit-pair1-joint').iterdir()}=={'FAILURE.json'}
for control,job in ((old,'304589'),(r1,'304591')):
 lines=c.lines(control/'CAMPAIGN.jsonl')
 assert [e['job'] for e in lines if e['event']=='submitted']==[job]
 assert [e['row'] for e in lines if e['event']=='terminal']==[next(x for x in rows if x['job']==job)]
 assert not any(e['event']=='accepted' for e in lines)
q=subprocess.run(['/usr/bin/squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T|%N'],capture_output=True,text=True,timeout=30)
assert q.returncode==0 and not [s for s in q.stdout.splitlines() if 'acvm1-' in s.lower()]
assert not (run/'submissions-r2').exists() and not (run/'recovery-history').exists()
assert not any((run/j['key']).exists() for j in c.grid()[1:])
for parent in ('snapshots','staging'):
 assert not list((Path(c.RESEARCH)/parent).glob('active-counterfactual-mechanism-replication-control-r2*'))
c.verify_seal(run/'reused')
assert c.sha(auth.inputs['registry_path'])==auth.inputs['registry_sha256']
roots=dict(science_source=science,r1_source=r1_source,original_control=old,r1_control=r1,run=run)
inventory={label+'/'+n:i for label,path in roots.items() for n,i in c.members(path).items()}
print(json.dumps(dict(unix=time.time(),roots={k:str(v) for k,v in roots.items()},inventory=inventory,failed_rows=rows,sacct_raw=p.stdout,squeue_acvm1_matches=[],original_stop_sha256=oldstop,r1_stop_sha256=r1stop,reused_seal_sha256=c.sha(run/'reused/SEAL.json'),science_manifest=c.sha(c.ROOT/'SOURCE-MANIFEST.json'),r1_manifest=c.sha(r1_source/'SOURCE-MANIFEST.json'),worker_approval=auth.approval_sha,successful_tasks=0,prior_attempts=2,prior_gpu_seconds=0,prior_cpu_seconds=8,scientific_payloads_decoded=False)))
'''
    response=remote(code)
    r.write(r.ROOT/'CAPTURE-TRANSPORT.json',dict(unix=time.time(),returncode=response.returncode,stdout=response.stdout.decode(errors='replace'),stderr=response.stderr.decode(errors='replace')))
    r.require(response.returncode==0,'Fresh R2 reconciliation failed')
    baseline=r.c.json.loads(response.stdout);r.write(r.ROOT/'BASELINE.json',baseline)
    print(r.c.json.dumps(dict(files=len(baseline['inventory']),failed_rows=baseline['failed_rows'],successful_tasks=0,live_jobs=0)))
