"""Final-only union backup: new chain plus authenticated unchanged LGP1 archive."""
import argparse,json,os,subprocess,tarfile,time
from pathlib import Path
import lgprb1_contract as c
from lgp1_preserve import verify_archive,check_ssd,VOLUME

DEST=Path('D:/THESIS-BACKUPS')/c.NAME
OLD_BACKUP=Path('D:/THESIS-BACKUPS/local-goal-proposals-20260918/run-b54a55b16bcb83a5')

def archive(source,run):
    began=time.monotonic();cpu=time.process_time();c.old.verify(source,c.MANIFEST)
    a,specs=c.authorize(source,run/'APPROVAL.json');complete=c.read(run/'COMPUTE-COMPLETE.json')
    c.require(complete['new_jobs']==len(complete['completed'])==387,'Complete chain before archive')
    records=complete['completed']
    c.require([r['task'] for r in records]==specs and len({r['job'] for r in records})==387,'Exact unique allocation grid')
    c.require(all(r['state']=='COMPLETED' and r['exit_code']=='0:0' and r['seconds']<=r['task']['seconds'] for r in records),'Successful bounded allocations')
    for gpu,key in ((True,'gpu_seconds'),(False,'cpu_seconds')):
        c.require(sum(r['seconds'] for r in records if r['task']['gpu']==gpu)==complete[key]<=c.CAPS[key],'Reconciled final charges')
    c.require(c.sha(run/'PRE-EVALUATION-FREEZE.json')==c.FREEZE_SHA,'Unchanged copied model freeze')
    from lgprb1_analysis import task
    for spec in specs:task(run/spec['name'],spec)
    c.verify_reuse(source)
    dest=run/'final-preservation';dest.mkdir(exist_ok=False)
    paths={}
    for prefix,root in [('source',source),('run',run),('control',c.control_path(run))]:
        for p in sorted(root.rglob('*')):
            if not p.is_file() or dest in p.parents:continue
            c.require(not p.is_symlink(),'No archive symlinks');paths[prefix+'/'+p.relative_to(root).as_posix()]=p
    inventory={n:dict(bytes=p.stat().st_size,sha256=c.sha(p)) for n,p in paths.items()}
    c.require(c.storage(source,run)['total_with_history_bytes']+sum(v['bytes'] for v in inventory.values())+2048*len(paths)+10240<c.CAPS['total_with_history_bytes'],'Archive storage reservation')
    target=dest/'final.tar'
    with tarfile.open(target,'x',format=tarfile.PAX_FORMAT) as tar:
        for n,p in paths.items():tar.add(p,arcname=n,recursive=False)
    checked=verify_archive(target,inventory)
    c.write(dest/'BACKUP-REQUEST.json',dict(archive=str(target),members=inventory,**checked,
        source_sha256=c.sha(source/c.MANIFEST),volume_id=VOLUME,backup_destination=DEST.as_posix(),
        old_archive_sha256=c.read(source/c.DOC/'REUSE.json')['backup_sha256'],
        archive_wall_seconds=time.monotonic()-began,archive_cpu_seconds=time.process_time()-cpu))
    return checked

def backup(request):
    check_ssd();began=time.monotonic()
    import re
    c.require(re.fullmatch(re.escape((c.ROOT/'experiments'/c.NAME).as_posix())+r'/run-[0-9a-f]{16}/final-preservation/BACKUP-REQUEST\.json',request) is not None,'Remote POSIX request')
    old_request=c.read(OLD_BACKUP/'BACKUP-REQUEST.json');old_verified=c.read(OLD_BACKUP/'BACKUP-VERIFIED.json')
    c.require(old_request['sha256']==old_verified['sha256']=='24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd','Historical backup binding')
    old_actual=verify_archive(OLD_BACKUP/'final.tar',old_request['members'])
    c.require(old_actual['sha256']==old_verified['sha256'],'Historical bytes still present')
    prefix=['wsl','-d','Thesis-Ubuntu','-u','chris','--','ssh','-o','BatchMode=yes','prometheus','cat']
    r=json.loads(subprocess.check_output(prefix+[request],text=True))
    c.require(r['archive']==request.rsplit('/',1)[0]+'/final.tar' and Path(r['backup_destination'])==DEST and
        r['volume_id']==VOLUME and r['old_archive_sha256']==old_verified['sha256'],'Exact source/archive/SSD union')
    root=DEST/('run-'+r['source_sha256'][:16]);root.mkdir(parents=True,exist_ok=False)
    c.write(root/'BACKUP-REQUEST.json',r);partial=root/'final.tar.partial'
    try:
        with partial.open('xb') as f:p=subprocess.run(prefix+[r['archive']],stdout=f)
        c.require(p.returncode==0,'Transfer failed; preserve partial')
        check_ssd();actual=verify_archive(partial,r['members'])
        c.require(actual['sha256']==r['sha256'] and actual['bytes']==r['bytes'],'Copied archive hash/bytes')
        partial.rename(root/'final.tar')
        c.write(root/'BACKUP-VERIFIED.json',dict(**actual,seconds=time.monotonic()-began,volume_id=VOLUME,
            source_sha256=r['source_sha256'],historical_archive_sha256=old_actual['sha256'],
            historical_members=old_actual['files'],scope='All new source/run/control plus separately reverified entire LGP1 historical archive; no relabelled fresh30 outcomes.'))
    except BaseException as e:
        c.write(root/'BACKUP-FAILURE.json',dict(error=str(e),automatic_retry=False));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('archive');a.add_argument('--source',type=Path,required=True);a.add_argument('--run',type=Path,required=True)
    a=s.add_parser('backup');a.add_argument('--request',required=True);a=p.parse_args()
    if a.command=='archive':print(json.dumps(archive(a.source,a.run)))
    else:backup(a.request)
