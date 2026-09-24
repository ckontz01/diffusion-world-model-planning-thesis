"""Independent full-grid acceptance across original, R1, R2 and R3 allocations."""
import r1 as r
import argparse
import acceptance_r1 as a
import scheduler
import models

def reconcile(ctx,rows):
    jobs=ctx.jobs;remaining=jobs[1:]
    state=a.ledger(ctx.control,remaining,True)
    r.require(len(rows)==8199 and len({x['job'] for x in rows})==8199,'Every historical and R3 allocation accounted')
    r.require(rows[:3]==ctx.baseline['rows'],'Three historical allocation rows unchanged')
    expected={x['job'] for x in rows[3:]}
    r.require(len(expected)==8196 and expected=={x['job'] for x in state['submitted'].values()},'Exact R3 allocation supplier set')
    r.require([x['state'] for x in rows[:3]]==['FAILED','FAILED','COMPLETED'] and rows[2]['exit']=='0:0','Two failures and one retained success')
    old=r.read(ctx.control/'ACCEPTED-EXISTING.json')
    r.require(old['key']=='fit-pair1-joint' and old['job']=='304593' and old['seal']==ctx.baseline['fit_seal_sha256'] and old['approval']==ctx.approval_sha and old['recomputed'] is False,'Authenticated no-rerun fit')
    r.c.verify_seal(ctx.run/'fit-pair1-joint',jobs[0])
    r.require(r.sha(ctx.run/'fit-pair1-joint/SEAL.json')==old['seal'] and r.sha(ctx.run/'fit-pair1-joint/TECHNICAL.json')==old['technical'],'Retained fit bytes unchanged')
    r.require(r.read(ctx.run/'fit-pair1-joint/TECHNICAL.json')['recovery_approval']==r.sha(ctx.r2_control/'EXECUTION-APPROVAL.json'),'Retained fit R2 authority')
    raw={x['job']:x for x in rows}
    receipts=[dict(key='fit-pair1-joint',job='304593',seal=old['seal'],accepted_existing=True)]
    for spec in remaining:
        job=state['submitted'][spec['key']]['job'];row=raw[job]
        r.require(row==state['terminal'][spec['key']]['row'],'Independent R3 scheduler equality')
        receipt=a.worker(ctx.run,spec,row,r.SCIENCE,r.APPROVAL)
        r.require(r.read(ctx.run/spec['key']/'TECHNICAL.json')['recovery_approval']==ctx.approval_sha,'Every R3 worker authority')
        receipts.append(receipt)
    frozen=models.check_freeze(ctx.run,r.SCIENCE);gate=a.check_gate(ctx.run)
    evaluations=[j for j in remaining if j['stage']=='evaluation']
    r.require(frozen['unix']<min(state['claimed'][j['key']]['unix'] for j in evaluations),'Six models froze before evaluation')
    r.require(gate['unix']<state['claimed'][evaluations[16]['key']]['unix'],'Source2 after first16 technical gate')
    complete=r.read(ctx.control/'COMPUTE-COMPLETE.json')
    r.require(complete['tasks']==8197 and complete['carried_tasks']==1 and complete['episodes']==8192,'Complete fixed study')
    allowed={j['key'] for j in jobs}|{'reused','submissions','submissions-r1','submissions-r2','submissions-r3','recovery-history','logs','ALL-MODELS-FROZEN.json','TECHNICAL-TRANCHE-PASSED.json'}
    r.require({p.name for p in ctx.run.iterdir()}<=allowed,'No extra run artifact/task')
    gpu=state['gpu_seconds'];cpu=19+state['cpu_seconds']
    r.require(gpu<=r.c.caps()['gpu_allocation_seconds'] and cpu<=36008,'Combined all-attempt compute caps')
    return dict(unix=__import__('time').time(),package=r.SCIENCE,approval=r.APPROVAL,run=str(ctx.run),tasks=8197,episodes=8192,sources=512,attempts=8199,successful_tasks=8197,failed_attempts=rows[:2],carried_success=rows[2],gpu_seconds=gpu,cpu_seconds=cpu,receipts=receipts,recovery_manifest=ctx.binding['manifest'],recovery_approval=ctx.approval_sha,prior_stops=[ctx.baseline['original_stop_sha256'],ctx.baseline['r1_stop_sha256'],ctx.baseline['r2_stop_sha256']],accepted_existing_sha256=r.sha(ctx.control/'ACCEPTED-EXISTING.json'),model_freeze_sha256=r.sha(ctx.run/'ALL-MODELS-FROZEN.json'),technical_gate_sha256=r.sha(ctx.run/'TECHNICAL-TRANCHE-PASSED.json'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);arg=p.parse_args();ctx=r.Context(arg.approval)
    r.baseline(ctx);r.guard(ctx)
    state=a.ledger(ctx.control,ctx.jobs[1:])
    ids=['304589','304591','304593']+[e['job'] for e in state['submitted'].values()]
    raw=scheduler.observe(ctx.control,ids,'independent-R3-final-acceptance')
    result=reconcile(ctx,[scheduler.parse(x) for x in raw.splitlines() if x])
    r.write(ctx.control/'FINAL-ACCEPTANCE.json',result)
    print(r.c.json.dumps({k:v for k,v in result.items() if k!='receipts'}))

if __name__=='__main__':main()
