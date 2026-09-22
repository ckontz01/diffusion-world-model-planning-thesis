"""Exclusive small-package SSD copy. Never opens historical archives.

This final step has its own receipt, not a post-copy edit to EXECUTION-LOG.
The receipt and manifest are self-excluded where necessary to avoid hash cycles.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from bounded_run import limits

ROOT=Path(__file__).resolve().parent
DEST=Path('D:/THESIS-BACKUPS/local-goal-line-closure-20260922/closure-package-v1')
RECEIPT=ROOT/'BACKUP-RECEIPT.json'
MANIFEST=ROOT/'MANIFEST.json'
CAP=250_000_000


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def main():
    start=time.monotonic()
    entries=json.loads((ROOT/'EXECUTION-LOG.json').read_text())
    remaining=7200-sum(e['wall_seconds'] for e in entries)
    assert remaining>0
    k,job,usage=limits()
    watchdog=threading.Timer(min(remaining,300),lambda:os._exit(124))
    watchdog.daemon=True;watchdog.start()
    for p in [DEST,RECEIPT,MANIFEST]:
        if p.exists(): raise RuntimeError('Exclusive preservation target exists: '+str(p))
    volume=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress'],text=True))
    assert volume['FileSystemLabel']=='THESIS_SSD'
    assert volume['UniqueId'].lower()=='\\\\?\\volume{0a2f1ba9-0000-0000-0000-100000000000}\\'
    assert volume['SizeRemaining']>=40_000_000_000
    assert json.loads((ROOT/'CHECKS.json').read_text())['passed']
    files=sorted(p for p in ROOT.rglob('*') if p.is_file())
    assert all(not p.is_symlink() for p in files)
    total=sum(p.stat().st_size for p in files)
    assert total*2+100_000<CAP
    records=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    manifest=dict(schema='lgp-documentation-package-v1',base_commit='dcf51819b1e0961388856e890b1e3c7f833257fe',
                  accepted_result_commit='0b6507fc7398eb0624d0755035db22e666de74d5',
                  accepted_preservation_commit='28cbcf18ec16bcb496132c7c9bd0204a7cf2eca9',
                  package_files=records,package_bytes_before_manifest=total,
                  exclusions=['MANIFEST.json (self)','BACKUP-RECEIPT.json (written after verification)'],
                  historical_archive_access=False)
    with MANIFEST.open('x',encoding='utf-8') as f: f.write(json.dumps(manifest,indent=2)+'\n')
    records.append(dict(path=MANIFEST.name,bytes=MANIFEST.stat().st_size,sha256=sha(MANIFEST)))
    DEST.mkdir(parents=True,exist_ok=False)
    for r in records:
        source=ROOT/r['path'];target=DEST/r['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as inp,target.open('xb') as out:
            for block in iter(lambda:inp.read(1024*1024),b''): out.write(block)
        if target.stat().st_size!=r['bytes'] or sha(target)!=r['sha256']:
            raise RuntimeError('SSD copy mismatch; retain partial directory; do not retry')
    import ctypes as C
    assert k.QueryInformationJobObject(job,9,C.byref(usage),C.sizeof(usage),None)
    elapsed=time.monotonic()-start
    result=dict(status='verified',destination=str(DEST),volume=volume,
                copied_files=records,verified_files=len(records),bytes_copied=sum(r['bytes'] for r in records),
                manifest_sha256=sha(MANIFEST),backup_wall_seconds_through_verification=elapsed,
                peak_job_memory_bytes=usage.peak_job,affinity_mask=usage.basic.affinity,
                prior_scripted_seconds=sum(e['wall_seconds'] for e in entries),
                cumulative_scripted_seconds_through_verification=elapsed+sum(e['wall_seconds'] for e in entries),
                no_archive_access_or_bulk_transfer=True,no_retry=True,
                receipt_self_hash='Excluded; identical local/SSD receipt bytes checked after writing and hash printed.')
    receipt_text=json.dumps(result,indent=2)+'\n'
    with RECEIPT.open('x',encoding='utf-8') as f:f.write(receipt_text)
    with (DEST/RECEIPT.name).open('x',encoding='utf-8') as f:f.write(receipt_text)
    assert sha(RECEIPT)==sha(DEST/RECEIPT.name)
    assert set(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file())==set(p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file())
    print(json.dumps(dict(status='verified',destination=str(DEST),total_files=len(records)+1,
                         bytes_including_receipt=result['bytes_copied']+RECEIPT.stat().st_size,
                         receipt_sha256=sha(RECEIPT),manifest_sha256=sha(MANIFEST),
                         cumulative_scripted_seconds=result['cumulative_scripted_seconds_through_verification'])))
    watchdog.cancel()


if __name__=='__main__':main()
