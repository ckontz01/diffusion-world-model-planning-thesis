"""Explicitly started WSL external-SSD companion; incremental sealed-stage backup.

No execution/dispatch/model capability. Uses the normally configured prometheus
SSH alias, never credentials. No extraction and no deletion of prior backups.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import shlex
import shutil
import subprocess
import tarfile
import time
import candidate_value_contract as ct


def ssh(command,input=None):
    return subprocess.check_output(['ssh','prometheus',command],input=input)


def remote_json(path,value):
    # Exclusive creation. The payload is a receipt, not executable source.
    code='import sys,pathlib; p=pathlib.Path(sys.argv[1]); f=p.open("xb"); f.write(sys.stdin.buffer.read()); f.close()'
    return ssh('python3 -c '+shlex.quote(code)+' '+shlex.quote(str(path)),json.dumps(value).encode())


def verify_archive(path,request):
    with tarfile.open(path,'r:') as tar:
        regular=[m for m in tar.getmembers() if m.isfile()]
        members={m.name.removeprefix('./'):m for m in regular}
        ct.require(len(members)==len(regular),'Duplicate archive member')
        ct.require(all(not m.issym() and not m.islnk() and not PurePosixPath(m.name).is_absolute()
                       and '..' not in PurePosixPath(m.name).parts for m in tar.getmembers()),'Archive traversal/link')
        expected=set()
        for d,seal_sha in request['seals'].items():
            name=d+'/sha256.txt';raw=tar.extractfile(members[name]).read()
            ct.require(hashlib.sha256(raw).hexdigest()==seal_sha,'Backup seal identity')
            expected.add(name)
            for line in raw.decode().splitlines():
                wanted,rel=line.split('  ',1);key=d+'/'+rel;expected.add(key)
                h=hashlib.sha256();f=tar.extractfile(members[key])
                for block in iter(lambda:f.read(1<<20),b''):h.update(block)
                ct.require(h.hexdigest()==wanted,'Backup member hash')
        ct.require(set(members)==expected,'Unexpected backup members')


def once(run,destination,stage):
    request_path=run/('BACKUP-REQUEST-'+stage+'.json')
    raw=ssh('cat '+shlex.quote(str(request_path)));r=json.loads(raw)
    ct.require(r['run']==str(run) and r['stage']==stage,'Backup scope')
    ct.require(all('/' not in d and d not in ('.','..') for d in r['directories']),'Backup directory scope')
    target=destination/(stage+'.tar');free=shutil.disk_usage(destination).free
    ct.require(free>=ct.CAPS['storage_bytes'],'Backup free-space reserve')
    command='tar -cf - -C '+shlex.quote(str(run))+' '+' '.join(map(shlex.quote,r['directories']))
    with target.open('xb') as f:
        p=subprocess.Popen(['ssh','prometheus',command],stdout=subprocess.PIPE)
        size=0
        try:
            for b in iter(lambda:p.stdout.read(1<<20),b''):
                size+=len(b);ct.require(size<=ct.CAPS['storage_bytes'],'Backup byte cap');f.write(b)
            ct.require(p.wait()==0,'Backup transport failure; preserve partial file')
        except BaseException:
            p.terminate();p.wait();raise
    verify_archive(target,r)
    receipt=dict(verified=True,request_sha256=hashlib.sha256(raw).hexdigest(),
                 archive_sha256=ct.sha(target),archive=str(target),bytes=size)
    ct.json_write(destination/(stage+'-receipt.json'),receipt)
    remote_json(run/('BACKUP-ACK-'+stage+'.json'),receipt)


def watch(run,approval,source_sha):
    run=Path(run)
    ct.require(run.parent==ct.RUN_PARENT and run.name=='run-'+source_sha[:16],'Backup run namespace')
    mount=subprocess.check_output(['findmnt','-n','-o','TARGET','--target','/mnt/d'],text=True).strip()
    ct.require(mount=='/mnt/d','No fallback from mounted external SSD')
    label=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
                                  '(Get-Volume -DriveLetter D).FileSystemLabel'],text=True).strip()
    ct.require(label=='THESIS_SSD','External SSD volume label differs')
    destination=Path('/mnt/d/THESIS-BACKUPS/candidate-value-learning-20260914')/run.name
    destination.mkdir(parents=True,exist_ok=False)
    free=shutil.disk_usage(destination).free
    ct.require(free>=ct.CAPS['backup_free_bytes'],'40GB external headroom required')
    remote_json(Path(approval).with_name('BACKUP-READY.json'),dict(external_mount='/mnt/d',free_bytes=free,
                utc=time.time(),source_sha256=source_sha))
    done=set();deadline=time.monotonic()+7*86400
    while time.monotonic()<deadline:
        for stage in ('train','validation','closed','report','terminal'):
            if stage in done:continue
            exists=ssh('test -f '+shlex.quote(str(run/('BACKUP-REQUEST-'+stage+'.json')))+' && echo yes || echo no')
            if exists.strip()==b'yes':once(run,destination,stage);done.add(stage)
        finished=ssh('test -f '+shlex.quote(str(run/'DISPATCH-FINAL.json'))+' && echo yes || echo no')
        if finished.strip()==b'yes':return
        time.sleep(30)
    raise RuntimeError('Backup companion lifetime exhausted; no automatic restart')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('run','approval','source-sha'):p.add_argument('--'+n,required=True)
    a=p.parse_args();watch(a.run,a.approval,a.source_sha)
