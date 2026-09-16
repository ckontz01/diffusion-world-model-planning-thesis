"""CVL-BP1 backup recovery: bounded read-only probes and live dispatch lease.

No automatic archive-transfer retry, job execution, model or scientific read.
"""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time
import breadth_precision_contract as p
import candidate_value_contract as ct
from candidate_value_backup import once, verify_archive
import breadth_precision_recovery as r

SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=15',
     '-o','ServerAliveCountMax=2','prometheus']


def probe(command):
    """Three attempts only for transient connection faults on read-only probes."""
    for attempt in range(3):
        try:
            return subprocess.check_output(SSH+[command],stderr=subprocess.PIPE,timeout=60)
        except subprocess.CalledProcessError as exc:
            error=(exc.stderr or b'').lower()
            transient=(exc.returncode==255 and any(x in error for x in
                (b'connection timed out',b'connection reset',b'connection closed',b'broken pipe',b'connection refused')))
            forbidden=any(x in error for x in (b'permission denied',b'host key verification',b'authentication failed'))
            if not transient or forbidden or attempt==2:raise
        except subprocess.TimeoutExpired:
            if attempt==2:raise
        time.sleep((5,15)[attempt])


def write_control(path, value, replace=False):
    """One write attempt; an ambiguous result stops, never silently retries."""
    code=('import sys,pathlib,os,time,json; p=pathlib.Path(sys.argv[1]); v=json.loads(sys.stdin.buffer.read()); '
          'v["utc"]=time.time(); raw=json.dumps(v,sort_keys=True).encode(); ')
    if replace:
        code+='q=p.with_name(p.name+".next"); f=q.open("xb"); f.write(raw); f.close(); os.replace(str(q),str(p))'
    else:
        code+='f=p.open("xb"); f.write(raw); f.close()'
    subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)+' '+shlex.quote(str(path))],
                            input=json.dumps(value).encode(),stderr=subprocess.PIPE,timeout=60)


def external_check(destination):
    mount=subprocess.check_output(['findmnt','-n','-o','TARGET','--target','/mnt/d'],universal_newlines=True).strip()
    label=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        '(Get-Volume -DriveLetter D).FileSystemLabel'],universal_newlines=True).strip()
    p.require(mount=='/mnt/d' and label=='THESIS_SSD','Named external SSD; no laptop fallback')
    free=shutil.disk_usage(destination).free
    p.require(free>=p.CAPS['backup_free_bytes'],'40GB external SSD headroom')
    return free


def watch(recovery, recovery_sha):
    recovery=Path(recovery)
    raw=probe('cat '+shlex.quote(str(recovery)))
    import hashlib
    p.require(hashlib.sha256(raw).hexdigest()==recovery_sha,'Exact recovery approval')
    approval=json.loads(raw);run=Path(approval['run']);control=recovery.parent
    r.overlay_check(Path(__file__).resolve().parent,approval['overlay_sha256'])
    p.require(approval['researcher_approved'] is True and approval['source_sha256']==r.SOURCE_SHA and
              run.parent==p.RUN_PARENT and run.name=='run-'+r.SOURCE_SHA[:16] and approval['caps']==p.CAPS,
              'Exact recovery backup scope')
    destination=Path('/mnt/d/THESIS-BACKUPS')/p.VERSION/run.name
    free=external_check(destination)
    p.require({x.name for x in destination.iterdir()}=={'failure-20260916.tar','failure-20260916-receipt.json'},
              'No pre-existing recovery archives or claim')
    receipt=destination/'failure-20260916-receipt.json';archive=destination/'failure-20260916.tar'
    p.require(p.sha(receipt)==r.FAILURE_RECEIPT_SHA and p.sha(archive)==r.FAILURE_ARCHIVE_SHA,'Existing failure backup unchanged')
    request_raw=probe('cat '+shlex.quote(str(run/'BACKUP-REQUEST-failure-20260916.json')))
    p.require(hashlib.sha256(request_raw).hexdigest()==r.FAILURE_REQUEST_SHA,'Accepted failure coverage')
    verify_archive(archive,json.loads(request_raw))
    ct.json_write(destination/'RECOVERY-BACKUP-CLAIM.json',dict(approval_sha256=recovery_sha,automatic_transfer_retry=False))
    common=dict(approval_sha256=recovery_sha,source_sha256=r.SOURCE_SHA,external_mount='/mnt/d',free_bytes=free)
    write_control(control/'BACKUP-RECOVERY-READY.json',dict(common,failure_archive_sha256=r.FAILURE_ARCHIVE_SHA,
                  failure_backup_verified=True))
    done=set();deadline=time.monotonic()+7*86400
    try:
        while time.monotonic()<deadline:
            free=external_check(destination)
            names=['BACKUP-REQUEST-'+s+'.json' for s in ('train','models','evaluation','terminal')]
            names+=['DISPATCH-FINAL.json','RECOVERY-STOP.json']
            code='import pathlib,json; p=pathlib.Path('+repr(str(run))+'); print(json.dumps({n:(p/n).is_file() for n in '+repr(names)+'}))'
            present=json.loads(probe('python3 -c '+shlex.quote(code)))
            write_control(control/'BACKUP-LIVE.json',dict(common,free_bytes=free),replace=True)
            if present['RECOVERY-STOP.json']:
                raise RuntimeError('Recovery stopped; reconcile and preserve, no automatic restart')
            for stage in ('train','models','evaluation','terminal'):
                if stage not in done and present['BACKUP-REQUEST-'+stage+'.json']:
                    # Accepted streaming/seal verifier, exactly once, never retried.
                    once(run,destination,stage);done.add(stage)
                    write_control(control/'BACKUP-LIVE.json',dict(common,free_bytes=external_check(destination)),replace=True)
            if present['DISPATCH-FINAL.json']:return
            time.sleep(30)
        raise RuntimeError('Backup lifetime exhausted; no restart')
    except BaseException as exc:
        stop=dict(type=type(exc).__name__,reason='Backup recovery stopped; inspect exact technical log',automatic_retry=False)
        ct.json_write(destination/'RECOVERY-BACKUP-STOP.json',stop)
        try:write_control(control/'BACKUP-RECOVERY-STOP.json',stop)
        except Exception:pass
        raise


if __name__=='__main__':
    cli=argparse.ArgumentParser()
    for field in ('recovery','recovery-sha'):cli.add_argument('--'+field,required=True)
    args=cli.parse_args();watch(args.recovery,args.recovery_sha)
