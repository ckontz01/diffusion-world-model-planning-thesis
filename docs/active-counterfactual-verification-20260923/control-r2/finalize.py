"""Separate R2 final acceptance/archive adapter. Never call R1 archive()."""
import r2_core as r
import argparse
import os
from pathlib import Path
import subprocess
import tarfile
import time

def scheduler_snapshot(ctx,result):
    expected={'304189'}|{v['job'] for v in result['jobs']}
    p=subprocess.run(['sacct','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],
                      '--format='+r.FIELDS+',TotalCPU,MaxRSS'],capture_output=True,text=True,timeout=60)
    q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
    r.require(p.returncode==q.returncode==0,'Final scheduler reconciliation unavailable')
    rows=[s.split('|') for s in p.stdout.splitlines() if 'acv0' in s.lower() or s.split('|')[0].split('.')[0] in expected]
    top=[r.parse_row(v[:12]) for v in rows if '.' not in v[0]]
    r.require(len(top)==340 and {v['job'] for v in top}==expected,'All and only340 campaign allocations')
    r.require(not any('acv0' in s.lower() or s.split('|')[0] in expected for s in q.stdout.splitlines()),'Live campaign allocation at finalization')
    return {'unix':time.time(),'allocations':top,'scope_separated_raw_steps':rows,'no_live_campaign_jobs':True}

def accept(ctx,result):
    r.verify_baseline(ctx);r.stop_guard(ctx)
    r.require((ctx.control/'STOP-RESOLUTION.json').exists(),'Explicit R1 fault resolution required')
    existing,receipt=r.accept_existing(ctx)
    accepted=r.read(ctx.control/'ACCEPTED-EXISTING.json')
    r.require(accepted['message']==receipt['message'] and accepted['seal_sha256']==receipt['seal_sha256']
              and accepted['job']=='304193' and accepted['new_submission'] is False and accepted['accepted_unix']>ctx.baseline['unix'],'Currently dated existing acceptance')
    jobs=ctx.jobs;rows=result['jobs']
    r.require(len(rows)==339 and [v['spec'] for v in rows]==jobs,'Combined339 successful logical tasks')
    r.require(rows[0]==existing,'Existing supplier exactly once, not a new allocation')
    ids=[v['job'] for v in rows];r.require(len(set(ids))==339 and '304189' not in ids,'Successful unique allocation IDs')
    for name,value in [('new_r2_allocations',338),('campaign_allocations',340),('successful_unique_tasks',339),('historical_failed_allocations',1),
                       ('previously_authorized_replacements',1),('new_replacements_authorized',0),('automatic_retry_count',0)]:
        r.require(result[name]==value,'Final campaign count: '+name)
    for j,row in zip(jobs,rows):r.verify_worker(ctx,j,row)
    gpu=23+sum(v['seconds']*v['gpus'] for v in rows if v['spec']['gpu']);cpu=sum(v['seconds'] for v in rows if not v['spec']['gpu'])
    r.require(gpu==result['campaign_gpu_seconds'] and cpu==result['campaign_cpu_stage_seconds'] and gpu<=220800 and cpu<=21600,'All charges carried once')
    ledger=r.lines(ctx.control/'CAMPAIGN-R2.jsonl');new_submitted=[v for v in ledger if v['event']=='submitted']
    terminal=[v for v in ledger if v['event']=='terminal'];reused=[v for v in ledger if v['event']=='accepted_existing']
    r.require(len(reused)==1 and reused[0]['job']=='304193' and not reused[0]['new_submission'],'Single reused completion event')
    r.require([v['job'] for v in new_submitted]==ids[1:] and terminal==rows[1:] and len(new_submitted)==338,'Only338 new allocation events')
    r.require([v['spec'] for v in new_submitted]==jobs[1:],'Submitted original specifications')
    r.require(not any('unresolved' in v['event'] for v in ledger),'Unresolved R2 attempt')
    scientific=r.lines(ctx.control/'SCIENTIFIC-TASKS-R2.jsonl')
    r.require([v['key'] for v in scientific]==[j['key'] for j in jobs] and [v['job'] for v in scientific]==ids,'Complete339 supplier view')
    for s,j in zip(scientific,jobs):r.require(s['seal_sha256']==r.sha(ctx.run/j['key']/'SEAL.json'),'Supplier seal identity')
    before=r.read(ctx.run/'PRE-ANALYSIS-ACCOUNTING.json')['jobs']
    r.require(before==rows[:-1] and len(before)==338,'Unchanged analysis full338 inputs')
    gate=r.read(ctx.run/'TECHNICAL-TRANCHE-PASSED.json')
    r.require(gate=={'scientific_selection':False,'seals':{j['key']:r.sha(ctx.run/j['key']/'SEAL.json') for j in jobs[:2]}},'Included490/545 tranche')
    tranche=r.read(ctx.control/'TECHNICAL-TRANCHE-R2.json')
    r.require(tranche['original_run_marker_sha256']==r.sha(ctx.run/'TECHNICAL-TRANCHE-PASSED.json')
              and [v['job'] for v in tranche['suppliers']]==ids[:2] and tranche['failed304189_counted'] is False,'Dated two-supplier gate')
    r.require(rows[1]['unix']<=tranche['unix']<=new_submitted[1]['unix'],'Both technical suppliers before third source')
    freeze=r.read(ctx.run/'MODEL-FREEZE.json');r.require(freeze['package']==r.SCIENCE_MANIFEST and freeze['selection']=='final192 only; before any final source','Original model-freeze identity')
    r.require(set(freeze['models'])=={'fit-joint','fit-ordinary'},'Exactly both unchanged models')
    for key,info in freeze['models'].items():
        r.require(info['seal']==r.sha(ctx.run/key/'SEAL.json') and info['files']==ctx.c.verify_seal(ctx.run/key)['files'],'Final model seal unchanged')
        r.require(r.read(ctx.run/key/'FIT.json')['updates']==192 and set(r.read(ctx.run/key/'PREPROCESSING.json')['fit_ids'])==set(map(str,ctx.c.roles()['fit'])),'Original update/source-fit contract')
    frozen=r.read(ctx.control/'MODEL-FREEZE-R2.json')
    r.require(frozen['original_model_freeze_sha256']==r.sha(ctx.run/'MODEL-FREEZE.json') and rows[81]['unix']<=frozen['unix']<=new_submitted[81]['unix'],'Both model seals before final-source submission')
    snapshot=r.read(ctx.control/'FINAL-SCHEDULER.json');alloc=snapshot['allocations']
    expected_failed=r.parse_row(ctx.baseline['scheduler_rows'][0])
    r.require(len(alloc)==340 and len({v['job'] for v in alloc})==340 and snapshot['no_live_campaign_jobs'] is True,'Final scheduler cardinality')
    by_id={v['job']:v for v in alloc};r.require(by_id.get('304189')==expected_failed,'Authenticated original failed allocation')
    for v in rows:r.require(by_id[v['job']]=={k:v[k] for k in by_id[v['job']]},'Final scheduler identity/charge')
    r.require(ctx.baseline['failed_terminal']['seconds']==23 and ctx.baseline['failed_terminal']['state']=='FAILED','Failed23-second evidence')
    originals={n:r.sha(Path(ctx.baseline['paths']['run'])/n) for n in ('DISPATCH.jsonl','CAMPAIGN-ATTEMPTS.jsonl','STOP.json')}
    return {'allocations':[expected_failed]+rows,'successful_task_keys':[j['key'] for j in jobs],
            'campaign_allocations':340,'successful_unique_tasks':339,'historical_failed_allocations':1,
            'gpu_seconds':gpu,'cpu_stage_seconds':cpu,'new_r2_allocations':338,'new_r2_replacements':0,'automatic_retries':0,
            'original_r1_segments_unchanged':originals,'r2_segment_sha256':r.sha(ctx.control/'CAMPAIGN-R2.jsonl'),
            'existing304193_reused_once':True,'failed_attempts_in_scientific_denominators':False,
            'original_stop_sha256':r.STOP_SHA,'resolution_sha256':r.sha(ctx.control/'STOP-RESOLUTION.json'),
            'original_scientific_manifest':r.SCIENCE_MANIFEST,'original_worker_approval_sha256':r.WORKER_APPROVAL,
            'r2_control_manifest':ctx.binding['control_manifest'],'r2_authorization_sha256':ctx.approval_sha}

def inventory(ctx):
    """All original bytes plus new control/run evidence, no historical studies."""
    output=ctx.run/'final-preservation';items=[]
    roots=[('scientific-source',Path(ctx.baseline['paths']['source'])),('r1-control',Path(ctx.baseline['paths']['control'])),
           ('run',ctx.run),('r2-control-source',r.ROOT),('r2-control-records',ctx.control)]
    for label,root in roots:
        for p in sorted(root.rglob('*')):
            if p.is_file() and output not in p.parents:
                r.require(not p.is_symlink(),'Archive symlink rejected');items.append((label+'/'+p.relative_to(root).as_posix(),p))
    names=[n for n,_ in items];r.require(len(names)==len(set(names)),'Exclusive archive members')
    for name in ctx.baseline['inventory']:
        label,rel=name.split('/',1);mapped={'source':'scientific-source','control':'r1-control','run':'run'}[label]+'/'+rel
        r.require(mapped in names,'Original member absent from final inventory: '+name)
    r.require('run/STOP.json' in names and 'r2-control-records/STOP-RESOLUTION.json' in names,'STOP and resolution both archived')
    return items

def archive(ctx):
    result=r.read(ctx.control/'COMPUTE-COMPLETE.json');combined=accept(ctx,result)
    r.require(combined==r.read(ctx.control/'COMBINED-CAMPAIGN.json'),'Combined accounting changed')
    pointer=r.read(ctx.run/'COMPUTE-COMPLETE.json')
    r.require(pointer['r2_control']==str(ctx.control) and pointer['completion_sha256']==r.sha(ctx.control/'COMPUTE-COMPLETE.json')
              and pointer['combined_campaign_sha256']==r.sha(ctx.control/'COMBINED-CAMPAIGN.json')
              and pointer['successful_unique_tasks']==339 and pointer['campaign_allocations']==340,'Original-run completion points to authenticated R2 records')
    r.storage(ctx)
    identity=r.read(ctx.control/'CONTROLLER-STARTED.json');stat=Path('/proc',str(identity['pid']),'stat')
    if stat.exists():
        f=stat.read_text().rsplit(')',1)[1].split();r.require(f[19]!=str(identity['start_ticks']) or f[0]=='Z','Controller still active; preserve after exit')
    output=ctx.run/'final-preservation';r.require(not output.exists(),'One final archive only; no retry')
    items=inventory(ctx);output.mkdir(exist_ok=False);started=time.monotonic();cpu=time.process_time()
    try:
        members={n:{'bytes':p.stat().st_size,'sha256':r.sha(p)} for n,p in items}
        r.require(sum(v['bytes'] for v in members.values())<2000000000,'Archive input byte cap')
        dest=output/'final.tar'
        with dest.open('xb') as f:
            with tarfile.open(fileobj=f,mode='w') as tar:
                for n,p in items:tar.add(p,arcname=n,recursive=False)
        from preserve import verify_tar,VOLUME
        verify_tar(dest,members);r.require(dest.stat().st_size<2000000000,'Archive including headers cap')
        r.write(output/'BACKUP-REQUEST.json',{'archive':dest.as_posix(),'bytes':dest.stat().st_size,'sha256':r.sha(dest),'members':members,
                'package_sha256':r.SCIENCE_MANIFEST,'approval_sha256':r.WORKER_APPROVAL,'r2_control_manifest':ctx.binding['control_manifest'],
                'r2_approval_sha256':ctx.approval_sha,'run_name':ctx.run.name,'archive_wall_seconds':time.monotonic()-started,
                'archive_cpu_seconds':time.process_time()-cpu,'ssd_volume':VOLUME,'ssd_free_required':40000000000,
                'automatic_retry':False,'campaign_accounting':combined,'original_stop_retained_and_resolved':True})
    except BaseException as e:
        r.write(output/'FAILURE.json',{'error':repr(e)[:4096],'automatic_retry':False});raise

def backup(request_path):
    # Original transfer/verifier is unchanged and accepts a request from its
    # original R1 run. Its archive() entry point is NEVER used by this adapter.
    contract=r.read(r.ROOT/'CONTRACT.json')
    r.require(os.name=='nt' and request_path==contract['run']+'/final-preservation/BACKUP-REQUEST.json','Native exact backup request')
    import sys
    local=r.ROOT.parent/'bindings-r1';sys.path.insert(0,str(local))
    import common as c
    r.require(c.ROOT.resolve()==local.resolve() and c.sha(c.ROOT/'SOURCE-MANIFEST.json')==r.SCIENCE_MANIFEST,'Original local transfer source identity')
    for n,h in c.read(c.ROOT/'SOURCE-MANIFEST.json')['files'].items():r.require(c.sha(c.REPO/n)==h,'Original transfer closure')
    from preserve import backup as original_transfer
    original_transfer(request_path)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('archive');a.add_argument('--approval',required=True)
    b=sub.add_parser('backup');b.add_argument('--request',required=True)
    args=p.parse_args()
    if args.mode=='archive':archive(r.Context(args.approval))
    else:backup(args.request)
