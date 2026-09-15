"""Restore only the idle CVL external backup watcher; never retry a transfer."""
import argparse
from pathlib import Path
import shutil
import subprocess
import time
import candidate_value_contract as ct
import candidate_value_backup as original


STAGES=('train','validation','closed','report','terminal')


def restore(run,control,source_sha):
    run=Path(run);control=Path(control)
    ct.require(run.parent==ct.RUN_PARENT and run.name=='run-'+source_sha[:16], 'Backup run namespace')
    mount=subprocess.check_output(['findmnt','-n','-o','TARGET','--target','/mnt/d'],text=True).strip()
    label=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
                                  '(Get-Volume -DriveLetter D).FileSystemLabel'],text=True).strip()
    ct.require(mount=='/mnt/d' and label=='THESIS_SSD','External SSD required')
    destination=Path('/mnt/d/THESIS-BACKUPS/candidate-value-learning-20260914')/run.name
    ct.require(destination.is_dir() and not list(destination.iterdir()),'Only an untouched backup destination may resume')
    free=shutil.disk_usage(destination).free
    ct.require(free>=ct.CAPS['backup_free_bytes'],'40GB external headroom required')
    for stage in STAGES:
        for kind in ('REQUEST','ACK'):
            path=run/('BACKUP-'+kind+'-'+stage+'.json')
            ct.require(original.ssh('test -e '+original.shlex.quote(str(path))+' && echo yes || echo no').strip()==b'no',
                       'A stage was already requested/transferred; no automatic recovery')
    ct.require(original.ssh('test -e '+original.shlex.quote(str(run/'DISPATCH-FINAL.json'))+' && echo yes || echo no').strip()==b'no',
               'Run already final')
    claim=destination.parent/('BACKUP-WATCH-RESUME-'+run.name+'.json')
    ct.json_write(claim,dict(run=str(run),source_sha256=source_sha,utc=time.time(),
                             helper_sha256=ct.sha(__file__),no_transfer_retry=True))
    original.remote_json(control/'BACKUP-READY.json',dict(external_mount='/mnt/d',free_bytes=free,
                         utc=time.time(),source_sha256=source_sha,restored_idle_watcher=True))
    done=set();deadline=time.monotonic()+7*86400
    while time.monotonic()<deadline:
        for stage in STAGES:
            if stage in done:continue
            path=run/('BACKUP-REQUEST-'+stage+'.json')
            if original.ssh('test -f '+original.shlex.quote(str(path))+' && echo yes || echo no').strip()==b'yes':
                original.once(run,destination,stage);done.add(stage)
        if original.ssh('test -f '+original.shlex.quote(str(run/'DISPATCH-FINAL.json'))+' && echo yes || echo no').strip()==b'yes':return
        time.sleep(30)
    raise RuntimeError('Backup watcher lifetime exhausted; no automatic restart')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('run','control','source-sha'):p.add_argument('--'+name,required=True)
    a=p.parse_args();restore(a.run,a.control,a.source_sha)
