"""Final-only exclusive archive and byte/member verification. Never run models."""
import argparse,hashlib,json,os,subprocess,tarfile,time
from pathlib import Path
import lgp1_contract as c

VOLUME='0a2f1ba9-0000-0000-0000-100000000000'
DEST=Path('D:/THESIS-BACKUPS/local-goal-proposals-20260918')

def verify_archive(path,expected):
    seen=set()
    with tarfile.open(path,'r:') as tar:
        for member in tar:
            c.require(member.isfile() and member.name in expected and member.name not in seen,'Unexpected archive member')
            stream=tar.extractfile(member);h=hashlib.sha256()
            for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
            c.require(h.hexdigest()==expected[member.name]['sha256'] and member.size==expected[member.name]['bytes'],'Archive member bytes')
            seen.add(member.name)
    c.require(seen==set(expected),'Archive coverage')
    return dict(files=len(seen),bytes=Path(path).stat().st_size,sha256=c.sha(path))

def archive(source,run):
    began=time.monotonic();cpu=time.process_time()
    c.verify(source,'LGP1-SOURCE-MANIFEST.sha256')
    complete=c.read(run/'COMPUTE-COMPLETE.json')
    c.require(complete['jobs']==204 and len(complete['completed'])==204,'Complete fixed chain required')
    from lgp1_verify import task
    approval=c.read(run/'APPROVAL.json')
    for spec in c.grid(c.read(source/c.DOC/'DATA-ROLES.json')['development_reference_indices'],
                      approval.get('recovery',{}).get('cache_seconds',14400)):task(run/spec['name'],spec)
    destination=run/'final-preservation';destination.mkdir(exist_ok=False)
    paths={}
    for prefix,root in [('source',source),('run',run)]+c.preserved_paths(run):
        for p in sorted(root.rglob('*')):
            if destination in p.parents or not p.is_file():continue
            c.require(not p.is_symlink(),'No preservation symlinks')
            paths[prefix+'/'+p.relative_to(root).as_posix()]=p
    inventory={name:dict(bytes=p.stat().st_size,sha256=c.sha(p)) for name,p in paths.items()}
    raw=sum(v['bytes'] for v in inventory.values());overhead=2048*len(paths)+10240
    c.require(c.storage(source,run)['total_remote_bytes']+raw+overhead<c.CAPS['remote_bytes'],'Archive reservation exceeds remote cap')
    target=destination/'final.tar'
    with tarfile.open(target,'x',format=tarfile.PAX_FORMAT) as tar:
        for name,p in paths.items():tar.add(p,arcname=name,recursive=False)
    checked=verify_archive(target,inventory)
    c.write(destination/'BACKUP-REQUEST.json',dict(archive=str(target),members=inventory,**checked,
        host_archive_seconds=time.monotonic()-began,host_archive_cpu_seconds=time.process_time()-cpu,
        source_sha256=c.sha(source/'LGP1-SOURCE-MANIFEST.sha256'),backup_destination=str(DEST),volume_id=VOLUME))
    c.storage(source,run)
    return checked

def check_ssd():
    c.require(os.name=='nt','Backup must run on Windows, no laptop fallback')
    v=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress'],text=True))
    c.require(v['FileSystemLabel']=='THESIS_SSD' and VOLUME in v['UniqueId'].lower() and v['SizeRemaining']>=40_000_000_000,'Designated SSD / 40GB free required')

def backup(request):
    check_ssd();began=time.monotonic()
    c.require(request.startswith(str(c.ROOT/'experiments/local-goal-proposals-20260918')+'/run-') and
              request.endswith('/final-preservation/BACKUP-REQUEST.json') and '..' not in request,'Request namespace')
    prefix=['wsl','-d','Thesis-Ubuntu','-u','chris','--']
    r=json.loads(subprocess.check_output(prefix+['ssh','prometheus','cat',request],text=True))
    c.require(r['archive']==request.rsplit('/',1)[0]+'/final.tar','Archive path identity')
    c.require(r['volume_id']==VOLUME and Path(r['backup_destination'])==DEST,'Pinned backup destination')
    root=DEST/('run-'+r['source_sha256'][:16]);root.mkdir(parents=True,exist_ok=False)
    c.write(root/'BACKUP-REQUEST.json',r)
    target=root/'final.tar';partial=root/'final.tar.partial'
    try:
        with partial.open('xb') as f:
            proc=subprocess.run(prefix+['ssh','prometheus','cat',r['archive']],stdout=f,check=False)
        c.require(proc.returncode==0,'Transfer failed; preserve partial, no retry')
        check_ssd();checked=verify_archive(partial,r['members'])
        c.require(checked['sha256']==r['sha256'] and checked['bytes']==r['bytes'],'Transfer archive bytes')
        partial.rename(target)
        c.write(root/'BACKUP-VERIFIED.json',dict(**checked,seconds=time.monotonic()-began,volume_id=VOLUME,
            source_sha256=r['source_sha256'],scope='complete request inventory: source, approval, all 204 workers, accounting, control/logs, and any explicitly preserved failed attempt'))
    except BaseException as e:
        c.write(root/'BACKUP-FAILURE.json',dict(error=str(e),automatic_retry=False));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('archive');a.add_argument('--source',type=Path,required=True);a.add_argument('--run',type=Path,required=True)
    a=sub.add_parser('backup');a.add_argument('--request',required=True)
    args=p.parse_args()
    if args.command=='archive':print(json.dumps(archive(args.source,args.run)))
    else:backup(args.request)
