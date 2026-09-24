"""Exclusive archive and native-Windows transfer; hashes EVERY regular member."""
import r1 as recovery
import common as c
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import threading
import time
import os
import shutil
VOLUME='0a2f1ba9-0000-0000-0000-100000000000'
DEST=Path('D:/THESIS-BACKUPS')/c.NAMESPACE

def deadline_check(deadline):
    if deadline is not None:c.require(time.monotonic()<deadline,'Preservation cumulative wall deadline')
def timed_sha(path,deadline=None):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):deadline_check(deadline);h.update(b)
    return h.hexdigest()
def inventory(roots,deadline=None):
    result={};paths={}
    for label,root in roots.items():
        c.require(label and '/' not in label and label not in ('.','..'),'Flat archive root label')
        for p in c.files(root):
            name=label+'/'+p.relative_to(root).as_posix()
            c.require(name not in result,'Duplicate archive name')
            deadline_check(deadline)
            result[name]=dict(bytes=p.stat().st_size,sha256=timed_sha(p,deadline));paths[name]=p
    return result,paths
def verify_tar(path,expected,deadline=None):
    seen=set()
    with tarfile.open(path,'r|') as tar:
        for member in tar:
            deadline_check(deadline)
            c.require(not PurePosixPath(member.name).is_absolute() and '..' not in PurePosixPath(member.name).parts and '\\' not in member.name,'Unsafe archive member name')
            c.require(member.isfile() and member.name in expected and member.name not in seen,'Archive member type/set/duplicate')
            seen.add(member.name);h=hashlib.sha256();total=0
            with tar.extractfile(member) as f:
                for b in iter(lambda:f.read(1<<20),b''):deadline_check(deadline);h.update(b);total+=len(b)
            c.require(dict(bytes=total,sha256=h.hexdigest())==expected[member.name] and total==member.size,'Archive member bytes')
    c.require(seen==set(expected),'Complete archive member coverage')
    return dict(bytes=Path(path).stat().st_size,sha256=timed_sha(path,deadline),members=len(seen))

def archive(auth,control,acceptance):
    from storage import MAX_MEMBERS,TAR_OVERHEAD
    out=auth.run.parent/(auth.run.name+'-preservation');out.mkdir(exist_ok=False)
    start=time.monotonic()
    accepted=c.read(acceptance)
    c.require(Path(acceptance)==control/'FINAL-ACCEPTANCE.json' and accepted['tasks']==8197 and accepted['episodes']==8192
              and accepted['package']==auth.approval['package_sha256'] and accepted['approval']==auth.approval_sha and accepted['run']==str(auth.run),'Final full-grid acceptance binding')
    for r in accepted['receipts']:
        c.require(c.sha(auth.run/r['key']/'SEAL.json')==r['seal'],'Accepted output seal changed before archive')
        c.verify_seal(auth.run/r['key'])
    c.write(out/'ARCHIVE-INTENT.json',dict(unix=time.time(),acceptance=c.sha(acceptance),attempt=1))
    try:
        ctx=recovery.Context(control/'EXECUTION-APPROVAL.json');recovery.baseline(ctx);roots=dict(science_source=c.REPO,r1_source=Path(recovery.R1_SOURCE),r2_source=recovery.ROOT,original_control=ctx.old_control,r1_control=ctx.r1_control,r2_control=control,run=auth.run)
        items,paths=inventory(roots,start+7200)
        c.require(len(items)<=MAX_MEMBERS and sum(x['bytes'] for x in items.values())+TAR_OVERHEAD<=c.caps()['archive_bytes'],'Complete archive reserve')
        partial=out/'final.tar.partial'
        with partial.open('xb') as stream,tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for n,p in paths.items():
                c.require(time.monotonic()-start<7200,'Archive wall cap')
                tar.add(p,arcname=n,recursive=False)
        verified=verify_tar(partial,items,start+7200)
        c.require(verified['bytes']<=c.caps()['archive_bytes'] and time.monotonic()-start<7200,'Archive final cap')
        final=out/'final.tar';c.require(not final.exists(),'Exclusive final');partial.rename(final)
        request=dict(schema='ACVM1-backup-v1',package=auth.approval['package_sha256'],approval=auth.approval_sha,run=str(auth.run),archive=str(final),
                     archive_identity=verified,members=items,acceptance=c.sha(acceptance),archive_wall_seconds=time.monotonic()-start)
        c.write(out/'BACKUP-REQUEST.json',request);return str(out/'BACKUP-REQUEST.json')
    except BaseException as e:c.write(out/'ARCHIVE-FAILURE.json',dict(error=repr(e),no_retry=True));raise

def ssh(command,**kwargs):
    return subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','prometheus',command],**kwargs)
def ssd():
    p=subprocess.run(['powershell.exe','-NoProfile','-Command',"Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress"],capture_output=True,text=True,timeout=30)
    c.require(p.returncode==0 and p.stdout.strip(),'Designated SSD unavailable')
    v=c.json.loads(p.stdout);c.require(v['FileSystemLabel']=='THESIS_SSD' and VOLUME in v['UniqueId'].lower() and v['SizeRemaining']>=40_000_000_000,'Exact SSD identity/free-space');return v
def backup(auth,request_path):
    start=time.monotonic();volume=ssd()
    remote_run=PurePosixPath(auth.approval['run'])
    expected=str(remote_run.parent/(remote_run.name+'-preservation')/'BACKUP-REQUEST.json')
    c.require(request_path==expected,'Exact remote POSIX request path')
    p=ssh('cat '+request_path,capture_output=True,timeout=60);c.require(p.returncode==0,'Request transport failed')
    request=c.json.loads(p.stdout)
    c.require(request['schema']=='ACVM1-backup-v1' and request['package']==auth.approval['package_sha256'] and request['approval']==auth.approval_sha and request['run']==str(auth.run),'Backup authority')
    c.require(request['archive']==remote_archive_path(request_path) and request['archive_identity']['bytes']<=c.caps()['archive_bytes'],'Archive path/cap')
    dest=DEST/auth.run.name;dest.mkdir(parents=True,exist_ok=False)
    with (dest/'REQUEST.json').open('xb') as f:f.write(p.stdout)
    c.write(dest/'TRANSFER-INTENT.json',dict(unix=time.time(),volume=volume,request_sha256=c.sha(dest/'REQUEST.json'),attempt=1))
    partial=dest/'final.tar.partial';proc=None;errors=[]
    try:
        cmd=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','prometheus','cat '+request['archive']]
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def timeout():
            if proc.poll() is None:proc.kill()
        timer=threading.Timer(max(1,14400-(time.monotonic()-start)),timeout);timer.start()
        def stderr():
            with (dest/'TRANSFER.stderr').open('xb') as f:
                total=0
                for b in iter(lambda:proc.stderr.read(4096),b''):
                    f.write(b[:max(0,65536-total)]);total+=len(b)
                    if total>65536:errors.append('stderr overflow');timeout();break
        thread=threading.Thread(target=stderr);thread.start()
        count=0;h=hashlib.sha256()
        with partial.open('xb') as f:
            for block in iter(lambda:proc.stdout.read(1<<20),b''):
                count+=len(block);c.require(count<=request['archive_identity']['bytes'],'Stream overrun');f.write(block);h.update(block)
        code=proc.wait(timeout=30);thread.join(timeout=10);timer.cancel()
        c.require(code==0 and not errors and not thread.is_alive(),'Transfer failed; partial retained, no retry')
        c.require(count==request['archive_identity']['bytes'] and h.hexdigest()==request['archive_identity']['sha256'],'Whole archive streamed bytes')
        verify=verify_tar(partial,request['members'],start+14400);c.require(verify==request['archive_identity'],'Whole + every member readback')
        c.require(time.monotonic()-start<=14400,'Complete transfer/verification wall cap')
        partial.rename(dest/'final.tar');c.write(dest/'BACKUP-VERIFIED.json',dict(unix=time.time(),archive=verify,request=c.sha(dest/'REQUEST.json'),volume=volume,wall_seconds=time.monotonic()-start))
        return dest
    except BaseException as e:
        if proc and proc.poll() is None:proc.kill()
        c.write(dest/'BACKUP-FAILURE.json',dict(error=repr(e),partial_bytes=partial.stat().st_size if partial.exists() else 0,no_retry=True));raise

def remote_archive_path(request_path):
    p=PurePosixPath(request_path)
    c.require(p.is_absolute() and p.name=='BACKUP-REQUEST.json' and '\\' not in request_path and '..' not in p.parts,'Exact POSIX request, independent of local OS')
    return str(p.parent/'final.tar')

def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['archive','backup']);p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--control');p.add_argument('--acceptance');p.add_argument('--request');a=p.parse_args()
    auth=c.Authorization(a.approval,a.run)
    if a.operation=='archive':print(archive(auth,Path(a.control),Path(a.acceptance)))
    else:print(backup(auth,a.request))
if __name__=='__main__':raise SystemExit('Use preserve_entry.py with separate recovery authority')
