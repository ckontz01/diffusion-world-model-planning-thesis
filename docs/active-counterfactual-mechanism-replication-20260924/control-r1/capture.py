"""Read-only exact failure/source/input inventory; no worker probe allocation."""
import r1 as r
import time
from transport import remote

if __name__=='__main__':
    r.require(not (r.ROOT/'BASELINE.json').exists(),'Exclusive fresh capture')
    code='import sys,json,subprocess,os,time\nfrom pathlib import Path\n'
    code+='root=Path('+repr(str(r.science_root) if str(r.science_root).startswith('/lustreFS') else r.OLD_SOURCE+'/'+r.REL)+')\n'
    code+='sys.path.insert(0,str(root));import common as c;import scheduler;import acceptance\n'
    code+='control=Path('+repr(r.OLD_CONTROL)+');run=Path('+repr(r.RUN)+')\n'
    code+='''auth=c.Authorization(control/'EXECUTION-APPROVAL.json',str(run))
assert auth.approval_sha=='''+repr(r.APPROVAL)+'''
assert c.sha(control/'STOP.json')=='237cd6138603a1d72a2f04f6c1d623746f03e3a40da5c7b89c1dd667cba9458b'
identity=c.read(control/'CONTROLLER-PROCESS.json');p=Path('/proc')/str(identity['pid'])
assert not p.exists() or p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=str(identity['start_ticks'])
ledger=acceptance.ledger(control,c.grid(),False)
assert [v['job'] for v in ledger['submitted'].values()]==['304589'] and not ledger['accepted']
p=subprocess.run(['/usr/bin/sacct','-X','-n','-P','-j','304589','--format='+scheduler.FIELDS],capture_output=True,text=True,timeout=60)
assert p.returncode==0
row=scheduler.parse(p.stdout.strip());scheduler.allocation(c.grid()[0],row,successful=False)
assert row==ledger['terminal']['fit-pair1-joint']['row'] and row['state']=='FAILED' and row['seconds']==0
q=subprocess.run(['/usr/bin/squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T|%N'],capture_output=True,text=True,timeout=30)
assert q.returncode==0
assert not [s for s in q.stdout.splitlines() if 'acvm1-' in s.lower()]
conflicts=[]
for parent in ('snapshots','staging'):
 conflicts.extend(str(p) for p in (Path(c.RESEARCH)/parent).glob('active-counterfactual-mechanism-replication-control-r1*'))
assert not conflicts
assert not (run/'submissions-r1').exists() and not any((run/j['key']).exists() for j in c.grid())
c.verify_seal(run/'reused')
assert c.sha(auth.inputs['registry_path'])==auth.inputs['registry_sha256']
roots=dict(science_source=c.REPO,original_control=control,run=run)
inventory={label+'/'+n:i for label,root in roots.items() for n,i in c.members(root).items()}
print(json.dumps(dict(unix=time.time(),roots={k:str(v) for k,v in roots.items()},inventory=inventory,failed_row=row,sacct_raw=p.stdout,squeue_acvm1_matches=[],stop_sha256=c.sha(control/'STOP.json'),reused_seal_sha256=c.sha(run/'reused/SEAL.json'),science_manifest=c.sha(root/'SOURCE-MANIFEST.json') if False else c.sha(c.ROOT/'SOURCE-MANIFEST.json'),worker_approval=auth.approval_sha,successful_tasks=0,prior_attempts=1,prior_gpu_seconds=0,prior_cpu_seconds=0,scientific_payloads_decoded=False)))
'''
    response=remote(code)
    r.write(r.ROOT/'CAPTURE-TRANSPORT.json',dict(unix=time.time(),returncode=response.returncode,stdout=response.stdout.decode(errors='replace'),stderr=response.stderr.decode(errors='replace')))
    r.require(response.returncode==0,'Fresh recovery reconciliation failed')
    baseline=r.c.json.loads(response.stdout);r.write(r.ROOT/'BASELINE.json',baseline)
    print(r.c.json.dumps(dict(files=len(baseline['inventory']),failed_row=baseline['failed_row'],successful_tasks=0,live_jobs=0)))
