"""Incremental native-Windows preservation of new receipts only; no rearchives."""
import json
import os
from pathlib import Path
import sys
from wm_diag0_preflight_v1.common import ROOT,DOC,DOCREL,identity,write_new
from wm_diag0_preflight_v1.preserve import volume

def main():
    label=sys.argv[1]
    if not label.isalnum(): raise ValueError('exclusive receipt label')
    v=volume(); target=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-preflight-v1-20261015/new-receipts')
    selected=[ROOT/'wm_diag0_preflight_v1'/n for n in ('test_recovery.py','reconcile_stage.py','backup_receipts.py')]
    for pattern in ('LOCAL-RECOVERY*.json','LOCAL-OBSERVE*.json','LOCAL-SUBMIT*.json'):
        selected+=list(DOC.glob(pattern))
    selected+=list((DOC/'stage-recovery-r1').glob('*.json'))
    # Contract and SSD receipt already belong to the completed small archive.
    selected=[p for p in selected if p.name not in ('CONTRACT.json','RECOVERY.json','SSD-VERIFIED-001.json')]
    if sum(p.stat().st_size for p in selected)>2_000_000: raise ValueError('receipt bound')
    copied={}; verified={}
    for p in sorted(set(selected)):
        rel=p.relative_to(ROOT).as_posix(); dest=target/rel; row=identity(p)
        if dest.exists():
            if identity(dest)!=row: raise ValueError('existing receipt differs; preserve evidence')
            verified[rel]=row; continue
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f: f.write(p.read_bytes()); f.flush(); os.fsync(f.fileno())
        if identity(dest)!=row: raise ValueError('receipt whole/member hash')
        copied[rel]=row
    result={'status':'NEW_RECEIPTS_WHOLE_AND_MEMBER_VERIFIED','volume':v,'new_members':copied,
            'existing_members_verified_not_recopied':verified,'old_archives_rebuilt':0,'weights_copied':0}
    write_new(DOC/('RECEIPT-BACKUP-'+label+'.json'),result)
    write_new(target/('RECEIPT-BACKUP-'+label+'.json'),result)
    if identity(DOC/('RECEIPT-BACKUP-'+label+'.json'))!=identity(target/('RECEIPT-BACKUP-'+label+'.json')): raise ValueError('backup receipt')
    print(json.dumps({'status':result['status'],'new_members':len(copied),'existing_verified':len(verified)}))

if __name__=='__main__': main()
