"""Read-only exact-job technical reconciliation for the retained R2 fit."""
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docs/active-counterfactual-mechanism-replication-20260924/control-r2'))
import r1 as r
from transport import remote

if __name__=='__main__':
    output=Path(__file__).with_name('SUCCESS-RECONCILIATION.json')
    r.require(not output.exists(),'Exclusive reconciliation receipt')
    b=r.binding()
    code='import sys,json,time,subprocess,os\nfrom pathlib import Path\n'
    code+='root=Path('+repr(b['source'])+');control=Path('+repr(b['control'])+')\n'
    code+='sys.path.insert(0,str(root));import r1 as r;import acceptance_r1 as a;import scheduler\n'
    code+='''ctx=r.Context(control/'EXECUTION-APPROVAL.json');r.baseline(ctx)
assert r.sha(control/'STOP.json')=='6404de638c2ea7fcd9fa36f25bd7254be73d3cd97288a5917d0b39d79a205184'
state=a.ledger(control,ctx.jobs,False)
assert set(state['submitted'])==set(state['terminal'])=={'fit-pair1-joint'} and not state['accepted']
assert state['submitted']['fit-pair1-joint']['job']=='304593'
p=subprocess.run(['/usr/bin/sacct','-X','-n','-P','-j','304589,304591,304593','--format='+scheduler.FIELDS],capture_output=True,text=True,timeout=60)
assert p.returncode==0
rows=[scheduler.parse(x) for x in p.stdout.splitlines() if x]
assert [x['job'] for x in rows]==['304589','304591','304593']
assert rows[:2]==ctx.baseline['failed_rows']
row=rows[2];assert row==state['terminal']['fit-pair1-joint']['row'] and row['state']=='COMPLETED' and row['exit']=='0:0' and row['seconds']==11
receipt=a.worker(ctx.run,ctx.jobs[0],row,r.SCIENCE,r.APPROVAL)
technical=r.read(ctx.run/'fit-pair1-joint/TECHNICAL.json')
assert technical['recovery_approval']==ctx.approval_sha and technical['updates']==192 and technical['seed']==94411
claim=r.read(ctx.run/'submissions-r2/fit-pair1-joint.json');assert claim['job']=='304593'
history=r.read(control/'FAILED-OUTPUT-RELOCATION.json')
assert history['sha256']==r.sha(ctx.run/'recovery-history/r1/fit-pair1-joint/FAILURE.json')
q=subprocess.run(['/usr/bin/squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T|%N'],capture_output=True,text=True,timeout=30)
assert q.returncode==0 and not [x for x in q.stdout.splitlines() if 'acvm1-' in x.lower()]
identity=r.read(control/'CONTROLLER-PROCESS.json');proc=Path('/proc')/str(identity['pid'])
assert not proc.exists() or proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=str(identity['start_ticks'])
assert not (ctx.run/'ALL-MODELS-FROZEN.json').exists() and not (ctx.run/'TECHNICAL-TRANCHE-PASSED.json').exists()
roots=dict(science_source=r.c.REPO,r1_source=Path(r.R1_SOURCE),r2_source=root,original_control=ctx.old_control,r1_control=ctx.r1_control,r2_control=control,run=ctx.run)
inventory={label+'/'+name:i for label,path in roots.items() for name,i in r.c.members(path).items()}
print(json.dumps(dict(unix=time.time(),roots={k:str(v) for k,v in roots.items()},inventory=inventory,rows=rows,sacct_raw=p.stdout,squeue_acvm1_matches=[],accepted_existing=receipt,technical_sha256=r.sha(ctx.run/'fit-pair1-joint/TECHNICAL.json'),fit_seal_sha256=r.sha(ctx.run/'fit-pair1-joint/SEAL.json'),fit_members=r.c.members(ctx.run/'fit-pair1-joint'),original_stop_sha256=ctx.baseline['original_stop_sha256'],r1_stop_sha256=ctx.baseline['r1_stop_sha256'],r2_stop_sha256=r.sha(control/'STOP.json'),r2_controller_exited=True,successful_tasks=1,prior_attempts=3,prior_gpu_seconds=0,prior_cpu_seconds=19,scientific_outcomes_decoded=False)))
'''
    response=remote(code)
    record=dict(unix=time.time(),returncode=response.returncode,stdout=response.stdout.decode(errors='replace'),stderr=response.stderr.decode(errors='replace'))
    r.write(output,record)
    r.require(response.returncode==0,'R2 successful fit not authenticated; no continuation')
    value=r.c.json.loads(record['stdout'])
    print(r.c.json.dumps(dict(rows=value['rows'],fit_seal_sha256=value['fit_seal_sha256'],members=len(value['inventory']),cpu_seconds=value['prior_cpu_seconds'])))
