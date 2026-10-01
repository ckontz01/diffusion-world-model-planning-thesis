"""One new-study archive and native Windows whole/member SSD verification."""
import argparse
import hashlib
import json
import subprocess
import tarfile
import time
from dtv_success_cost.common import *

VOLUME=chr(92)*2+'?'+chr(92)+'Volume{0a2f1ba9-0000-0000-0000-100000000000}'+chr(92)
DEST=Path('D:/THESIS-BACKUPS/dtv-success-cost-20261001')

def inventory(roots):
    out=[]
    for label,root in sorted(roots.items()):
        if not label or '/' in label or label in ('.','..'):raise RuntimeError('exclusive simple archive root labels required')
        root=Path(root).resolve()
        paths=[root] if root.is_file() else sorted(root.rglob('*'))
        for p in paths:
            if p.is_symlink():raise RuntimeError('archive symlinks forbidden')
            if not p.is_file():continue
            if not p.resolve().is_relative_to(root) and p!=root:raise RuntimeError('archive path escape')
            name=label+'/'+(p.name if p==root else p.relative_to(root).as_posix())
            out.append(dict(path=name,source=str(p),bytes=p.stat().st_size,sha256=sha(p)))
    if len({r['path'] for r in out})!=len(out):raise RuntimeError('duplicate archive member')
    return out

def verify_archive(path,rows,check=lambda:None):
    expected={r['path']:r for r in rows};seen=set()
    with tarfile.open(path,'r:') as archive:
        for member in archive:
            check()
            if not member.isfile() or member.name not in expected or member.name in seen:raise RuntimeError('unexpected/duplicate archive member')
            r=expected[member.name];f=archive.extractfile(member);h=hashlib.sha256()
            for chunk in iter(lambda:f.read(1048576),b''):check();h.update(chunk)
            if member.size!=r['bytes'] or h.hexdigest()!=r['sha256']:raise RuntimeError('archive member authentication failed')
            seen.add(member.name)
    if seen!=set(expected):raise RuntimeError('missing archive members')
    return len(seen)

def make_archive(path,rows,check=lambda:None):
    path=Path(path)
    if path.exists():raise RuntimeError('archive already exists; no rearchive')
    with tarfile.open(path,'x:',format=tarfile.PAX_FORMAT) as archive:
        for r in rows:
            check()
            if sha(r['source'])!=r['sha256']:raise RuntimeError('inventory source changed')
            archive.add(r['source'],arcname=r['path'],recursive=False)
    check();before=sha(path);check();count=verify_archive(path,rows,check)
    if sha(path)!=before:raise RuntimeError('archive changed during verification')
    return dict(bytes=path.stat().st_size,sha256=before,members=count)

def volume():
    r=subprocess.run(['powershell.exe','-NoProfile','-Command','Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress'],capture_output=True,text=True,timeout=15,check=True)
    v=json.loads(r.stdout)
    if v['FileSystemLabel']!='THESIS_SSD' or v['UniqueId'].lower()!=VOLUME.lower() or v['SizeRemaining']<40000000000:raise RuntimeError('designated SSD / 40 GB free required')
    return v

def archive(c,run):
    from dtv_success_cost.accept import accept_grid,accounting
    if run!=run_namespace(c):raise RuntimeError('wrong study run')
    if not (run/'COMPUTE-COMPLETE.json').exists():raise RuntimeError('compute incomplete')
    read_seal(run/'analysis','analysis');_,accepted=accept_grid(c,run);allocation=accounting(run,c,True)
    location=run/'final-preservation'
    if location.exists():raise RuntimeError('final preservation namespace already exists; retain archive/partials')
    roots=dict(source=ROOT,run=run)
    # Package closure only, not unrelated repository/history or other studies.
    rows=[]
    for r in load(DOC/'PACKAGE-MANIFEST.json')['files']:
        rows.append(dict(path='source/'+r['path'],source=str(ROOT/r['path']),bytes=r['bytes'],sha256=r['sha256']))
    rows.append(dict(path='source/PACKAGE-MANIFEST.json',source=str(DOC/'PACKAGE-MANIFEST.json'),bytes=(DOC/'PACKAGE-MANIFEST.json').stat().st_size,sha256=sha(DOC/'PACKAGE-MANIFEST.json')))
    rows+=inventory(dict(run=run))
    for i,r in enumerate(c['preservation_inputs']):
        if sha(r['path'])!=r['sha256']:raise RuntimeError('reused model preservation binding')
        rows.append(dict(path=f'reused-models/{i:02d}-'+Path(r['path']).name,source=r['path'],bytes=r['bytes'],sha256=r['sha256']))
    if sum(r['bytes'] for r in rows)+2048*len(rows)+10240>c['archive_bytes']:raise RuntimeError('full archive payload/header reservation exhausted')
    location.mkdir();start=time.perf_counter();info=make_archive(location/'final.tar',rows)
    if info['bytes']>c['archive_bytes']:raise RuntimeError('complete archive ceiling; evidence retained')
    request=dict(study='DTV-EFF1',run=str(run),remote_archive=str(location/'final.tar'),archive=info,inventory=rows,
                 acceptance=accepted,allocation=allocation,bindings_sha256=sha(DOC/'BINDINGS.json'),package_sha256=sha(DOC/'PACKAGE-MANIFEST.json'),cohort_sha256=sha(DOC/'COHORT.json'),archive_wall_seconds=time.perf_counter()-start)
    write(location/'BACKUP-REQUEST.json',request);return request

def validate_request(request,request_path,c):
    from pathlib import PurePosixPath
    path=PurePosixPath(request_path);run=run_namespace(c).as_posix()
    if str(path)!=run+'/final-preservation/BACKUP-REQUEST.json' or request.get('study')!='DTV-EFF1' or request.get('run')!=run or request.get('remote_archive')!=run+'/final-preservation/final.tar':raise RuntimeError('wrong new-study preservation request')
    for key,name in [('bindings_sha256','BINDINGS.json'),('package_sha256','PACKAGE-MANIFEST.json'),('cohort_sha256','COHORT.json')]:
        if request.get(key)!=sha(DOC/name):raise RuntimeError('preservation capability binding changed')
    rows=request['inventory'];names=set()
    for r in rows:
        p=PurePosixPath(r['path']);digest=r['sha256']
        if str(p)!=r['path'] or '\\' in r['path'] or p.is_absolute() or '..' in p.parts or p.parts[0] not in ('source','run','reused-models') or r['path'] in names:raise RuntimeError('unsafe/duplicate archive inventory path')
        if not isinstance(r['bytes'],int) or r['bytes']<0 or len(digest)!=64 or any(x not in '0123456789abcdef' for x in digest):raise RuntimeError('invalid archive inventory binding')
        names.add(r['path'])
    a=request['archive'];digest=a['sha256']
    if not 0<a['bytes']<=c['archive_bytes'] or a['members']!=len(rows) or len(digest)!=64 or any(x not in '0123456789abcdef' for x in digest):raise RuntimeError('archive finite envelope/member identity')
    if sum(r['bytes'] for r in rows)>a['bytes']:raise RuntimeError('archive payload length inconsistent')

def archive_bounded(c,run):
    # Host-only POSIX signal interrupts inventory, tar, hashing and readback,
    # not just a per-member estimate. It never retries or deletes a partial.
    import signal
    def expired(*args):raise TimeoutError('7200-second host preservation deadline; retain evidence, no retry')
    previous=signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,7200)
    try:return archive(c,run)
    except Exception as e:
        target=Path(run)/'ARCHIVE-FAILURE.json'
        if not target.exists():write(target,dict(error=repr(e),automatic_retry=False,partials_retained=True))
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def backup(request_path,c):
    v=volume();request_path=str(request_path)
    if not request_path.startswith('/lustreFS/data/superworld/ckontzias/thesis/experiments/dtv-success-cost-20261001/run-') or not request_path.endswith('/final-preservation/BACKUP-REQUEST.json'):raise RuntimeError('unscoped request path')
    command=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus']
    r=subprocess.run(command+['cat '+__import__('shlex').quote(request_path)],capture_output=True,timeout=60,check=True)
    request=json.loads(r.stdout);validate_request(request,request_path,c);folder=DEST/PurePosixPath(request['run']).name
    if folder.exists():raise RuntimeError('SSD preservation already attempted; no retry or overwrite')
    folder.mkdir(parents=True);write(folder/'REQUEST.json',request);path=folder/'final.tar.partial';start=time.monotonic()
    try:
        process=subprocess.Popen(command+['cat '+__import__('shlex').quote(request['remote_archive'])],stdout=subprocess.PIPE,stderr=(folder/'TRANSFER.stderr').open('xb'))
        with path.open('xb') as f:
            # Bounded outer supervisor handles stalled reads without inventing resume.
            import threading
            expired=threading.Event()
            def stop():expired.set();process.kill()
            timer=threading.Timer(7200,stop);timer.start()
            try:
                total=0
                for b in iter(lambda:process.stdout.read(1048576),b''):
                    total+=len(b)
                    if total>request['archive']['bytes']:process.kill();raise RuntimeError('stream exceeds authenticated length')
                    f.write(b)
                process.wait(timeout=30)
                if expired.is_set() or process.returncode:raise RuntimeError('transfer failed/timed out; retain partial, no automatic retry')
            finally:timer.cancel()
        def check():
            if time.monotonic()-start>7200:raise TimeoutError('complete transfer/verification deadline; preserve partial, no retry')
        check()
        if path.stat().st_size!=request['archive']['bytes'] or sha(path)!=request['archive']['sha256']:raise RuntimeError('whole archive transfer mismatch')
        check();verify_archive(path,request['inventory'],check);after=sha(path);check()
        if after!=request['archive']['sha256']:raise RuntimeError('whole readback changed')
        path.rename(folder/'final.tar')
        receipt=dict(status='verified',study='DTV-EFF1',request_sha256=hashlib.sha256(r.stdout).hexdigest(),archive_sha256=after,bytes=request['archive']['bytes'],members=request['archive']['members'],whole_and_members=True,volume=v,wall_seconds=time.monotonic()-start)
        write(folder/'VERIFIED.json',receipt)
        # ACK is supplied to the host only after the actual SSD gate passed.
        ack_path=str(PurePosixPath(request['run'])/'final-preservation/SSD-ACK.json')
        script="import json,pathlib,sys; p=pathlib.Path("+repr(ack_path)+"); f=p.open('x'); json.dump(json.load(sys.stdin),f); f.close()"
        subprocess.run(command+['python3.9 -c '+__import__('shlex').quote(script)],input=json.dumps(receipt).encode(),capture_output=True,timeout=60,check=True)
        return receipt
    except Exception as e:
        write(folder/'FAILURE.json',dict(error=repr(e),retained_partial=str(path),automatic_retry=False));raise

def preserved_report(c):
    run=run_namespace(c);location=run/'final-preservation';request=load(location/'BACKUP-REQUEST.json');ack=load(location/'SSD-ACK.json')
    validate_request(request,(location/'BACKUP-REQUEST.json').as_posix(),c)
    if ack.get('status')!='verified' or ack.get('study')!='DTV-EFF1' or ack.get('whole_and_members') is not True or ack.get('request_sha256')!=sha(location/'BACKUP-REQUEST.json') or ack.get('archive_sha256')!=request['archive']['sha256'] or ack.get('bytes')!=request['archive']['bytes'] or ack.get('members')!=request['archive']['members'] or ack.get('volume',{}).get('UniqueId','').lower()!=VOLUME.lower():raise RuntimeError('actual designated-SSD preservation gate not passed')
    read_seal(run/'analysis','analysis');return load(run/'analysis/REPORT.json')

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['archive','backup','report']);p.add_argument('--approval',type=Path,default=DOC/'EXECUTION-APPROVAL.json');p.add_argument('--request');a=p.parse_args()
    # Archive requires the future execution capability; local backup additionally
    # validates the remote authenticated study request, never a fallback destination.
    c=gate(a.approval)
    result=archive_bounded(c,run_namespace(c)) if a.mode=='archive' else (backup(a.request,c) if a.mode=='backup' else preserved_report(c))
    print(json.dumps(result,default=str))
if __name__=='__main__':main()
