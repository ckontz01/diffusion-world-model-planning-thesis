"""One finite metadata-only acceptance, archive and original native SSD transport."""
import argparse
import os
from pathlib import Path
import sys
import tarfile
import time
import r5_core as r

def evidence(ctx,combined):
    return dict(combined,r5_control_manifest=ctx.binding['control_manifest'],r5_authorization_sha256=ctx.approval_sha,
        r4_finalization_stop_retained=True,r4_stop_sha256=ctx.binding['r4_stop_sha256'],
        r5_resolution_sha256=r.sha(ctx.control/'STOP-RESOLUTION.json'),new_r5_allocations=0,
        reanalysis_count=0,r5_baseline_sha256=ctx.binding['baseline_sha256'])

def finalize(ctx):
    r.guard(ctx)
    r.require(not any((ctx.control/n).exists() for n in ('FINALIZE-INTENT.json','COMPUTE-COMPLETE.json','FINAL-SCHEDULER.json'))
              and not (ctx.run/'COMPUTE-COMPLETE.json').exists(),'One finalization only; preserve ambiguity')
    r.write(ctx.control/'FINALIZE-INTENT.json',{'unix':time.time(),'approval_sha256':ctx.approval_sha,'new_jobs':0,'automatic_retry':False})
    try:
        snapshot=r.reconcile(ctx);r.write(ctx.control/'FINAL-SCHEDULER.json',snapshot)
        r.write(ctx.control/'STOP-RESOLUTION.json',{'unix':time.time(),'original_r4_stop_sha256':ctx.binding['r4_stop_sha256'],
            'r5_approval_sha256':ctx.approval_sha,'baseline_sha256':ctx.binding['baseline_sha256'],
            'scientific_jobs_resubmitted':0,'final_scheduler_sha256':r.sha(ctx.control/'FINAL-SCHEDULER.json'),
            'original_fault_queue_stdout_preserved':False,'decision':'Accept all339 unchanged sealed tasks after strict empty-queue reconciliation; do not restart R4'})
        import validation5
        result=r.result_from_ledger(ctx)
        combined=evidence(ctx,validation5.accept(ctx.r4,result));space=r.storage(ctx)
        r.write(ctx.control/'COMBINED-CAMPAIGN.json',combined)
        r.write(ctx.control/'COMPUTE-COMPLETE.json',dict(result,accepted_unix=time.time(),r5_manifest=ctx.binding['control_manifest'],
            approval_sha256=ctx.approval_sha,storage=space))
        r.write(ctx.run/'COMPUTE-COMPLETE.json',{'r5_control':str(ctx.control),
            'completion_sha256':r.sha(ctx.control/'COMPUTE-COMPLETE.json'),
            'combined_campaign_sha256':r.sha(ctx.control/'COMBINED-CAMPAIGN.json'),
            'successful_unique_tasks':339,'campaign_allocations':340,'new_r5_allocations':0})
        return {'successful_tasks':339,'attempts':340,'gpu_seconds':combined['gpu_seconds'],
                'cpu_stage_seconds':combined['cpu_stage_seconds'],'completion_sha256':r.sha(ctx.run/'COMPUTE-COMPLETE.json')}
    except BaseException as e:
        r.write(ctx.control/'STOP-R5.json',{'unix':time.time(),'error':repr(e)[:4096],'automatic_retry':False});raise

def authenticate_complete(ctx):
    r.guard(ctx)
    import validation5
    result=r.read(ctx.control/'COMPUTE-COMPLETE.json')
    r.require(all(result[k]==v for k,v in r.result_from_ledger(ctx).items()),'Completion exact original ledger')
    combined=evidence(ctx,validation5.accept(ctx.r4,result))
    r.require(combined==r.read(ctx.control/'COMBINED-CAMPAIGN.json'),'Combined accounting unchanged')
    pointer={'r5_control':str(ctx.control),'completion_sha256':r.sha(ctx.control/'COMPUTE-COMPLETE.json'),
        'combined_campaign_sha256':r.sha(ctx.control/'COMBINED-CAMPAIGN.json'),
        'successful_unique_tasks':339,'campaign_allocations':340,'new_r5_allocations':0}
    r.require(r.read(ctx.run/'COMPUTE-COMPLETE.json')==pointer,'Exact authenticated R5 run pointer')
    return combined

def inventory(ctx):
    import finalize4
    items=finalize4.inventory(ctx.r4)
    for label,root in [('r5-control-source',r.ROOT),('r5-control-records',ctx.control)]:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                r.require(not p.is_symlink(),'Archive symlink rejected');items.append((label+'/'+p.relative_to(root).as_posix(),p))
    names={n for n,p in items};r.require(len(names)==len(items),'Unique archive names')
    mapping={'source':'scientific-source','control':'r1-control','run':'run','r2_source':'r2-control-source',
        'r2_control':'r2-control-records','r3_source':'r3-control-source','r3_control':'r3-control-records',
        'r4_source':'r4-control-source','r4_control':'r4-control-records'}
    for name in ctx.baseline['inventory']:
        label,rel=name.split('/',1);r.require(mapping[label]+'/'+rel in names,'Original R5 baseline member missing: '+name)
    for n in ('r4-control-records/STOP-R4.json','r5-control-records/STOP-RESOLUTION.json','r5-control-records/COMBINED-CAMPAIGN.json'):
        r.require(n in names,'Recovery evidence missing: '+n)
    return items

def archive(ctx):
    combined=authenticate_complete(ctx);space=r.storage(ctx)
    output=ctx.run/'final-preservation';r.require(not output.exists(),'One archive only; no automatic retry')
    items=inventory(ctx);output.mkdir(exist_ok=False);start=time.monotonic();cpu=time.process_time()
    try:
        members={n:{'bytes':p.stat().st_size,'sha256':r.sha(p)} for n,p in items}
        r.require(sum(v['bytes'] for v in members.values())<2000000000,'Archive input cap')
        dest=output/'final.tar'
        with dest.open('xb') as f:
            with tarfile.open(fileobj=f,mode='w') as tar:
                for n,p in items:tar.add(p,arcname=n,recursive=False)
        from preserve import verify_tar,VOLUME
        verify_tar(dest,members);r.require(dest.stat().st_size<2000000000,'Archive including headers cap')
        r.write(output/'BACKUP-REQUEST.json',{'archive':dest.as_posix(),'bytes':dest.stat().st_size,'sha256':r.sha(dest),'members':members,
            'package_sha256':r.SCIENCE_MANIFEST,'approval_sha256':r.WORKER_APPROVAL,'r5_control_manifest':ctx.binding['control_manifest'],
            'r5_approval_sha256':ctx.approval_sha,'run_name':ctx.run.name,'archive_wall_seconds':time.monotonic()-start,
            'archive_cpu_seconds':time.process_time()-cpu,'ssd_volume':VOLUME,'ssd_free_required':40000000000,
            'automatic_retry':False,'campaign_accounting':combined,'all_original_stops_retained_and_resolved':True,'storage_before_archive':space})
        return {'bytes':dest.stat().st_size,'sha256':r.sha(dest),'members':len(members),'request':str(output/'BACKUP-REQUEST.json')}
    except BaseException as e:
        r.write(output/'FAILURE.json',{'error':repr(e)[:4096],'automatic_retry':False});raise

def backup(request):
    old=r.load_r4()
    import finalize4
    finalize4.backup(request)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['finalize','archive','backup']);p.add_argument('--approval');p.add_argument('--request');a=p.parse_args()
    if a.mode=='backup':backup(a.request)
    else:
        ctx=r.Context(a.approval);print(r.json.dumps((finalize if a.mode=='finalize' else archive)(ctx)))
