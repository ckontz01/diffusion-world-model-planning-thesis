"""External-SSD backup companion; accepted archive verifier, new study namespace."""
import argparse
from pathlib import Path
import shlex
import shutil
import subprocess
import time
import breadth_precision_contract as p
from candidate_value_backup import once,remote_json,ssh


def watch(run,approval,source_sha):
    run=Path(run)
    p.require(run.parent==p.RUN_PARENT and run.name=='run-'+source_sha[:16],'Exact new backup namespace')
    mount=subprocess.check_output(['findmnt','-n','-o','TARGET','--target','/mnt/d'],text=True).strip()
    p.require(mount=='/mnt/d','External SSD mount; no laptop fallback')
    label=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        '(Get-Volume -DriveLetter D).FileSystemLabel'],text=True).strip()
    p.require(label=='THESIS_SSD','Named external SSD required')
    destination=Path('/mnt/d/THESIS-BACKUPS')/p.VERSION/run.name
    destination.mkdir(parents=True,exist_ok=False)
    free=shutil.disk_usage(destination).free
    p.require(free>=p.CAPS['backup_free_bytes'],'40GB external headroom')
    remote_json(Path(approval).with_name('BACKUP-READY.json'),dict(external_mount='/mnt/d',free_bytes=free,
        utc=time.time(),source_sha256=source_sha))
    done=set();deadline=time.monotonic()+7*86400
    def exists(name):
        return ssh('test -f '+shlex.quote(str(run/name))+' && echo yes || echo no').strip()==b'yes'
    while time.monotonic()<deadline:
        for stage in ('train','models','evaluation','terminal'):
            if stage not in done and exists('BACKUP-REQUEST-'+stage+'.json'):
                once(run,destination,stage);done.add(stage)
        if exists('DISPATCH-FINAL.json'):return
        # A failure is preserved in place; no unsafe archive of a still-live job.
        # Terminal accounting/sealing and failure backup require reconciliation.
        if exists('DISPATCH-STOP.json'):
            raise RuntimeError('Controller stopped; reconcile terminal allocation then seal/back up partials; no restart')
        time.sleep(30)
    raise RuntimeError('Backup deadline; no automatic restart')


if __name__=='__main__':
    cli=argparse.ArgumentParser()
    for name in ('run','approval','source-sha'):cli.add_argument('--'+name,required=True)
    a=cli.parse_args();watch(a.run,a.approval,a.source_sha)
