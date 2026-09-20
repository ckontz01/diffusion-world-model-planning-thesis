"""Post-completion new archive plus byte/member-verified LGP1/RB1 union."""
import argparse,json,re,subprocess,tarfile,time
from pathlib import Path
import lgprb2_contract as c
from lgp1_preserve import check_ssd,verify_archive,VOLUME

DEST=Path('D:/THESIS-BACKUPS')/c.NAME
HISTORICAL=[('local-goal-proposals-20260918','run-b54a55b16bcb83a5','24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd'),
 ('local-goal-search-budget-20260919','run-a0bcdb48029909e0','72c2717be4a10b0e103a05c6575710832e5ae4c9e9a21be573c8cb3c4441f175')]

def archive(source,run):
    began=time.monotonic();cpu=time.process_time();a,specs=c.authorize(source,run/'APPROVAL.json')
    done=c.read(run/'COMPUTE-COMPLETE.json');rows=done['completed']
    c.require(done['new_jobs']==len(rows)==1537 and [r['task'] for r in rows]==specs and len({r['job'] for r in rows})==1537,'Complete unique chain')
    c.require(all(r['state']=='COMPLETED' and r['exit_code']=='0:0' and r['seconds']<=r['task']['seconds'] for r in rows),'All bounded successes')
    for gpu,key in ((True,'gpu_seconds'),(False,'cpu_seconds')):
        c.require(sum(r['seconds'] for r in rows if r['task']['gpu']==gpu)==done[key]<=c.CAPS[key],'All charges')
    from lgprb2_analysis import task
    for spec in specs:task(run/spec['name'],spec)
    c.verify_models(source);c.require(c.sha(run/'PRE-EVALUATION-FREEZE.json')==c.FREEZE_SHA,'Original freeze')
    dest=run/'final-preservation';dest.mkdir(exist_ok=False);paths={}
    for prefix,root in [('source',source),('run',run),('control',c.control_path(run))]:
        for p in sorted(root.rglob('*')):
            if not p.is_file() or dest in p.parents:continue
            c.require(not p.is_symlink(),'No archive symlinks');paths[prefix+'/'+p.relative_to(root).as_posix()]=p
    inventory={n:dict(bytes=p.stat().st_size,sha256=c.sha(p)) for n,p in paths.items()}
    c.require(c.storage(source,run)['total_with_history_bytes']+sum(v['bytes'] for v in inventory.values())+2048*len(paths)+10240<c.CAPS['total_with_history_bytes'],'Final archive reservation')
    target=dest/'final.tar'
    with tarfile.open(target,'x',format=tarfile.PAX_FORMAT) as tar:
        for n,p in paths.items():tar.add(p,arcname=n,recursive=False)
    checked=verify_archive(target,inventory)
    c.write(dest/'BACKUP-REQUEST.json',dict(**checked,archive=str(target),members=inventory,source_sha256=c.sha(source/c.MANIFEST),
        backup_destination=DEST.as_posix(),volume_id=VOLUME,historical_archives=HISTORICAL,
        archive_wall_seconds=time.monotonic()-began,archive_cpu_seconds=time.process_time()-cpu))
    c.storage(source,run);return checked

def backup(request):
    check_ssd();began=time.monotonic()
    c.require(re.fullmatch(re.escape((c.ROOT/'experiments'/c.NAME).as_posix())+r'/run-[0-9a-f]{16}/final-preservation/BACKUP-REQUEST\.json',request),'Exact remote request')
    old=[]
    for study,run,digest in HISTORICAL:
        root=DEST.parent/study/run;r=c.read(root/'BACKUP-REQUEST.json');receipt=c.read(root/'BACKUP-VERIFIED.json')
        c.require(r['sha256']==receipt['sha256']==digest,'Historical backup binding')
        actual=verify_archive(root/'final.tar',r['members']);c.require(actual['sha256']==digest,'Historical bytes')
        old.append(dict(path=str(root/'final.tar'),**actual))
    prefix=['wsl','-d','Thesis-Ubuntu','-u','chris','--','ssh','-o','BatchMode=yes','prometheus','cat']
    r=json.loads(subprocess.check_output(prefix+[request],text=True))
    c.require(r['archive']==request.rsplit('/',1)[0]+'/final.tar' and r['volume_id']==VOLUME and
        Path(r['backup_destination'])==DEST and r['historical_archives']==[list(x) for x in HISTORICAL],'Pinned archive/SSD union')
    root=DEST/('run-'+r['source_sha256'][:16]);root.mkdir(parents=True,exist_ok=False);c.write(root/'BACKUP-REQUEST.json',r)
    partial=root/'final.tar.partial'
    try:
        with partial.open('xb') as f:p=subprocess.run(prefix+[r['archive']],stdout=f)
        c.require(p.returncode==0,'Failed transfer preserved; no retry')
        check_ssd();actual=verify_archive(partial,r['members'])
        c.require(actual['sha256']==r['sha256'] and actual['bytes']==r['bytes'],'Copied archive bytes')
        partial.rename(root/'final.tar')
        c.write(root/'BACKUP-VERIFIED.json',dict(**actual,historical=old,seconds=time.monotonic()-began,source_sha256=r['source_sha256'],volume_id=VOLUME))
    except BaseException as e:
        c.write(root/'BACKUP-FAILURE.json',dict(error=str(e),automatic_retry=False));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('archive');a.add_argument('--source',type=Path,required=True);a.add_argument('--run',type=Path,required=True)
    a=s.add_parser('backup');a.add_argument('--request',required=True);a=p.parse_args()
    if a.command=='archive':print(json.dumps(archive(a.source,a.run)))
    else:backup(a.request)
