"""Independent original + recovery accounting; no implicit fault resolution."""
import r1 as r
import argparse
import acceptance_r1 as a
import scheduler
from controller import accepted

def reconcile(ctx,rows):
    state=a.ledger(ctx.control,ctx.jobs,False)
    ids={e['job'] for e in state['submitted'].values()}
    r.require(len(rows)==8198 and len({x['job'] for x in rows})==8198,'Every allocation including failed bootstrap')
    old=[x for x in rows if x['job']=='304589']
    r.require(old==[ctx.baseline['failed_row']],'Historical failed attempt/accounting unchanged')
    r.require(ids=={x['job'] for x in rows}-{'304589'} and len(ids)==8197,'Exact finite remaining supplier set')
    result=a.full(ctx.auth,ctx.control,[x for x in rows if x['job'] in ids])
    for j in ctx.jobs:r.require(r.read(ctx.run/j['key']/'TECHNICAL.json')['recovery_approval']==ctx.approval_sha,'Every successful recovery worker binding')
    result.update(attempts=8198,successful_tasks=8197,failed_attempts=old,recovery_manifest=ctx.binding['manifest'],recovery_approval=ctx.approval_sha,prior_stop=ctx.baseline['stop_sha256'],total_gpu_seconds=result['gpu_seconds'],total_cpu_seconds=result['cpu_seconds']+old[0]['seconds'])
    r.require(result['total_gpu_seconds']<=r.c.caps()['gpu_allocation_seconds'] and result['total_cpu_seconds']<=r.c.caps()['cpu_stage_allocation_seconds'],'Combined cumulative charges')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);arg=p.parse_args();ctx=r.Context(arg.approval)
    r.baseline(ctx);r.guard(ctx)
    state=a.ledger(ctx.control,ctx.jobs)
    raw=scheduler.observe(ctx.control,['304589']+[e['job'] for e in state['submitted'].values()],'independent-R1-final-acceptance')
    result=reconcile(ctx,[scheduler.parse(x) for x in raw.splitlines() if x])
    r.write(ctx.control/'FINAL-ACCEPTANCE.json',result)
    print(r.c.json.dumps({k:v for k,v in result.items() if k!='receipts'}))

if __name__=='__main__':main()
