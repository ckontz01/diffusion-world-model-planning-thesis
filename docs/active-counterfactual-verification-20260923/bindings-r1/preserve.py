"""One-shot final archive and native-Windows SSD verification. No retry path."""
import common as c
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import time

SSD=Path('D:/THESIS-BACKUPS/active-counterfactual-verification-pilot-v1')
VOLUME='\\\\?\\Volume{0a2f1ba9-0000-0000-0000-100000000000}\\'


def archive(approval,run):
    auth=c.Authorization(approval,run);run=auth.run
    complete=c.read(run/'COMPUTE-COMPLETE.json')
    import recovery
    from dispatch import storage
    jobs=c.grid();accounting=recovery.final_acceptance(run,complete)
    recovery.authenticate_prior_files()
    storage(c.ROOT,run,jobs)
    for j in jobs:c.verify_seal(run/j['key'],j)
    c.require(not (run/'STOP.json').exists(),'Unresolved failure')
    output=run/'final-preservation';output.mkdir(exist_ok=False)
    started=time.monotonic();cpu=time.process_time();members={}
    try:
        items=[('source/'+n,c.REPO/n) for n in c.read(c.ROOT/'SOURCE-MANIFEST.json')['files']]
        items += [('source/'+str((c.ROOT/'SOURCE-MANIFEST.json').relative_to(c.REPO)).replace('\\','/'),c.ROOT/'SOURCE-MANIFEST.json')]
        items += [('source/'+str((c.ROOT/'APPROVAL-TEMPLATE.json').relative_to(c.REPO)).replace('\\','/'),c.ROOT/'APPROVAL-TEMPLATE.json')]
        control=Path(auth.approval['recovery']['control'])
        items += [('recovery-control/'+p.relative_to(control).as_posix(),p) for p in sorted(control.rglob('*')) if p.is_file()]
        items += [('run/'+p.relative_to(run).as_posix(),p) for p in sorted(run.rglob('*')) if p.is_file() and output not in p.parents]
        for name,p in items:
            c.require(not p.is_symlink(),'No archive symlink')
            members[name]={'bytes':p.stat().st_size,'sha256':c.sha(p)}
        c.require(sum(v['bytes'] for v in members.values())<2_000_000_000,'Archive input cap')
        dest=output/'final.tar'
        with dest.open('xb') as f:
            with tarfile.open(fileobj=f,mode='w') as tar:
                for name,p in items:tar.add(p,arcname=name,recursive=False)
        verify_tar(dest,members)
        c.require(dest.stat().st_size<2_000_000_000,'Archive cap including headers')
        request={'archive':dest.as_posix(),'bytes':dest.stat().st_size,'sha256':c.sha(dest),'members':members,
                 'package_sha256':auth.approval['package_sha256'],'approval_sha256':auth.approval_sha,
                 'run_name':run.name,'archive_wall_seconds':time.monotonic()-started,'archive_cpu_seconds':time.process_time()-cpu,
                 'ssd_volume':VOLUME,'ssd_free_required':40_000_000_000,'automatic_retry':False,
                 'campaign_accounting':accounting,'failed_v2_included_as_provenance_not_data':True}
        c.write(output/'BACKUP-REQUEST.json',request)
    except BaseException as e:
        c.write(output/'FAILURE.json',{'error':repr(e),'automatic_retry':False});raise


def verify_tar(path,members):
    seen=set()
    with tarfile.open(path,'r:') as tar:
        for member in tar:
            c.require(member.isfile() and member.name in members and member.name not in seen,'Archive member identity')
            seen.add(member.name);h=hashlib.sha256();n=0
            with tar.extractfile(member) as f:
                for b in iter(lambda:f.read(1<<20),b''):n+=len(b);h.update(b)
            c.require({'bytes':n,'sha256':h.hexdigest()}==members[member.name],'Archive member bytes')
    c.require(seen==set(members),'Whole member set')


def ssh(script):
    return subprocess.Popen(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',
        '-o','ServerAliveInterval=15','-o','ServerAliveCountMax=4','prometheus','python3.9','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)


def backup(request_path):
    c.require(os.name=='nt','Native Windows SSD path only')
    expected=c.RUN_PARENT+'/run-'+c.sha(c.ROOT/'SOURCE-MANIFEST.json')[:16]+'/final-preservation/BACKUP-REQUEST.json'
    c.require(request_path==expected,'Exact remote request path')
    command="Get-Volume -DriveLetter D | Select-Object UniqueId,FileSystemLabel,SizeRemaining | ConvertTo-Json -Compress"
    volume=c.json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,timeout=30))
    c.require(volume['UniqueId']==VOLUME and volume['FileSystemLabel']=='THESIS_SSD' and volume['SizeRemaining']>=40_000_000_000,'Designated SSD identity/capacity')
    process=ssh(None)
    request,err=process.communicate(('from pathlib import Path\nimport sys\nsys.stdout.buffer.write(Path('+repr(request_path)+').read_bytes())\n').encode(),timeout=60)
    c.require(process.returncode==0,err.decode(errors='replace'))
    r=c.json.loads(request);c.require(r['package_sha256']==c.sha(c.ROOT/'SOURCE-MANIFEST.json'),'Package identity')
    c.require(r['archive']==request_path.replace('BACKUP-REQUEST.json','final.tar') and 0<r['bytes']<2_000_000_000,'Archive request')
    dest=SSD/r['run_name'];c.require(dest.parent==SSD and r['run_name']=='run-'+r['package_sha256'][:16],'Backup namespace')
    dest.mkdir(parents=True,exist_ok=False);started=time.monotonic();process=None
    c.write(dest/'REQUEST.json',r)
    try:
        process=ssh(None)
        code='from pathlib import Path\nimport sys\nwith Path('+repr(r['archive'])+').open("rb") as f:\n while True:\n  b=f.read(1048576)\n  if not b: break\n  sys.stdout.buffer.write(b)\n'
        process.stdin.write(code.encode());process.stdin.close()
        # A watchdog bounds stalled pipe reads too, not only intervals with bytes.
        import threading
        timer=threading.Timer(7200,process.kill);timer.start()
        try:
            n=0
            with (dest/'final.tar.partial').open('xb') as f:
                while True:
                    b=process.stdout.read(1<<20)
                    if not b:break
                    n+=len(b);c.require(n<=r['bytes'],'Transfer overflow');f.write(b)
            code=process.wait(timeout=60)
        finally:timer.cancel()
        c.require(code==0 and n==r['bytes'],'Transfer failed; preserve partial, no retry')
        part=dest/'final.tar.partial';c.require(c.sha(part)==r['sha256'],'Whole archive hash')
        verify_tar(part,r['members'])
        part.rename(dest/'final.tar')  # target new/exclusive; no overwrite
        c.write(dest/'BACKUP-VERIFIED.json',{'status':'VERIFIED','archive':r['sha256'],'members':len(r['members']),
                'bytes':n,'request_sha256':hashlib.sha256(request).hexdigest(),'volume':volume,
                'wall_seconds':time.monotonic()-started,'historical_archives_transferred':0})
    except BaseException as e:
        if process is not None and process.poll() is None:process.kill();process.wait()
        c.write(dest/'BACKUP-FAILURE.json',{'error':repr(e),'automatic_retry':False,'partial_preserved':True});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('archive');a.add_argument('--approval',required=True);a.add_argument('--run',required=True)
    b=sub.add_parser('backup');b.add_argument('--request',required=True);args=p.parse_args()
    if args.mode=='archive':archive(args.approval,args.run)
    else:backup(args.request)
