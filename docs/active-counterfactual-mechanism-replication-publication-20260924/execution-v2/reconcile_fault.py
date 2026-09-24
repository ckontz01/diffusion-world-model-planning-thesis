"""One read-only reconciliation of the observed first-allocation failure."""
import sys
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-mechanism-replication-20260924/runtime-v2'
sys.path.insert(0,str(ROOT))
import common as c
from transport import remote

def main():
    dest=HERE/'FAULT-RECONCILIATION.json'
    c.require(not dest.exists(),'Exclusive fault receipt')
    ap=c.read(HERE/'EXECUTION-APPROVAL.json');prefix=c.RESEARCH
    source=prefix+'/snapshots/'+c.NAMESPACE+'-'+ap['package_sha256'][:16]
    control=prefix+'/staging/'+c.NAMESPACE+'-'+ap['package_sha256'][:16]
    code='import sys,os,json,subprocess,time\nfrom pathlib import Path\n'
    code+='root=Path('+repr(source)+')/'+repr(ROOT.relative_to(c.REPO).as_posix())+'\n'
    code+='control=Path('+repr(control)+');run=Path('+repr(ap['run'])+')\n'
    code+='''sys.path.insert(0,str(root));import common as c;import scheduler;import acceptance
a=c.Authorization(control/'EXECUTION-APPROVAL.json',str(run))
state=acceptance.ledger(control,c.grid(),False)
ids=[e['job'] for e in state['submitted'].values()]
assert ids==['304589'], 'Unexpected allocation set: preserve and inspect before proceeding'
r=dict(unix=time.time(),package=a.approval['package_sha256'],approval=a.approval_sha,run=str(run),ledger=state)
r['control_records']={}
for n in ('CONTROLLER-PROCESS.json','CONTROLLER-STARTED.json','LAUNCH-INTENT.json','STAGED.json','STOP.json','CAMPAIGN.jsonl','SCHEDULER.jsonl','fit-pair1-joint.SUBMIT.json','controller.out','controller.err'):
 p=control/n
 r['control_records'][n]=dict(bytes=p.stat().st_size,sha256=c.sha(p),text=p.read_text()) if p.exists() else None
identity=c.read(control/'CONTROLLER-PROCESS.json');p=Path('/proc')/str(identity['pid'])
if p.exists():
 stat=(p/'stat').read_text().rsplit(')',1)[1].split()
 r['process']=dict(pid=identity['pid'],start_ticks=stat[19],state=stat[0],exact_start=stat[19]==str(identity['start_ticks']))
else:r['process']=dict(pid=identity['pid'],exists=False)
cmd=['/usr/bin/sacct','-X','-n','-P','-j',','.join(ids),'--format='+scheduler.FIELDS]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
r['sacct']=dict(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
qcmd=['/usr/bin/squeue','-h','-j',','.join(ids),'-o','%i|%j|%T|%N']
p=subprocess.run(qcmd,capture_output=True,text=True,timeout=30)
r['squeue']=dict(command=qcmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
assert r['sacct']['returncode']==0 and r['squeue']['returncode']==0
rows=[scheduler.parse(x) for x in r['sacct']['stdout'].splitlines() if x.strip()]
assert len(rows)==1 and rows[0]['job']=='304589'
scheduler.allocation(c.grid()[0],rows[0],successful=False)
r['independent_charges']=dict(gpu_seconds=0,cpu_stage_allocation_seconds=rows[0]['seconds'],attempts=1,successful_tasks=0,live_allocations=bool(r['squeue']['stdout'].strip()),ambiguous_submissions=sorted(set(state['claimed'])-set(state['submitted'])))
r['worker_logs']={}
for p in sorted((run/'logs').glob('fit-pair1-joint*')):
 assert p.is_file() and p.stat().st_size<=65536
 r['worker_logs'][p.name]=dict(bytes=p.stat().st_size,sha256=c.sha(p),text=p.read_text(errors='replace'))
failed=run/'fit-pair1-joint'
r['failed_output_inventory']=c.members(failed) if failed.exists() else {}
for n in ('FAILURE.json','TECHNICAL.json'):
 p=failed/n
 if p.exists():r[n]=c.read(p)
r['reused_seal']=c.verify_seal(run/'reused')
r['reused_seal_sha256']=c.sha(run/'reused/SEAL.json')
r['run_top_names']=sorted(p.name for p in run.iterdir())
r['retained_bytes']=dict(source=c.bytes_in(c.REPO),control=c.bytes_in(control),run=c.bytes_in(run))
r['information_barrier']=dict(new_evaluation_payloads_opened=False,scientific_aggregates_read=False,checkpoint_deserialization_by_this_reconciliation=False)
print(json.dumps(r))
'''
    p=remote(code)
    receipt=dict(unix=time.time(),returncode=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace'),read_only=True,automatic_retry=False)
    c.write(dest,receipt)
    c.require(p.returncode==0,'Reconciliation incomplete; no recovery authorized')
    print(receipt['stdout'])

if __name__=='__main__':main()
