"""Native no-follow logical-copy measurement; no scientific payload decoding."""
import hashlib,json,os,stat,time
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new
from wm_diag0_rc1_final_v2.archive_v2 import canonical,check_time

def scan(root,deadline):
    root=Path(root);stack=[root];rows=[];count=0;total=0
    for p in (root,)+tuple(root.parents):
        if getattr(p.lstat(),'st_file_attributes',0)&0x400 or p.is_symlink():raise ValueError('physical preparation ancestors')
    while stack:
        check_time(deadline);directory=stack.pop()
        with os.scandir(str(directory)) as stream:entries=sorted(list(stream),key=lambda e:e.name)
        for entry in entries:
            s=entry.stat(follow_symlinks=False);p=Path(entry.path)
            if getattr(s,'st_file_attributes',0)&0x400:raise ValueError('preparation reparse member')
            if stat.S_ISDIR(s.st_mode):stack.append(p)
            elif stat.S_ISREG(s.st_mode):
                count+=1;total+=s.st_size
                rows.append([p.relative_to(root).as_posix(),s.st_size,s.st_mtime_ns,s.st_ino])
                if count>100000 or total>5368709120:raise ValueError('retained preparation member/byte cap')
            else:raise ValueError('preparation alias or special member')
    raw=canonical(sorted(rows));return {'path':str(root),'regular_files':count,'logical_bytes':total,
        'sorted_stat_commitment':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
        'compression_hardlink_dedup_discounts':False}

def main():
    from wm_diag0_preflight_v1.preserve import volume
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-close-v1-20261017';deadline=time.monotonic()+45
    v=volume();backup=Path('D:/THESIS-BACKUPS')
    roots=[ROOT]+sorted(p for p in backup.iterdir() if p.name.startswith('world-model-diagnostic') and p.is_dir())
    rows=[scan(p,deadline) for p in roots]
    # The operation meter is currently writing only after this child exits.
    # This explicit remaining reservation includes future source/log/control,
    # Git and small-source ZIP copies; existing historical charges are retained.
    actual=sum(x['logical_bytes'] for x in rows)
    future=max(2874852312,actual)+80000000
    if future>5368709120:raise ValueError('all actual preparation copies plus full future allowance exceed cap')
    audit={'status':'NATIVE_PREPARATION_ALL_ENUMERATED_LOGICAL_COPIES_MEASURED',
           'roots':rows,'actual_logical_bytes':actual,'historical_retained_floor_not_discounted':2874852312,
           'remaining_auxiliary_all_copies_reserved':80000000,'full_future_preparation_bytes':future,
           'SSD_volume':v,'scientific_payloads_read':False,'source':identity(__file__)}
    write_new(doc/'PREPARATION-MEASUREMENT-001.json',audit)
    commitment=identity(doc/'PREPARATION-MEASUREMENT-001.json')
    write_new(doc/'PREPARATION-COPIES-001.json',{'schema':'WM-DIAG0-RC1-PREPARATION-COPIES-v1',
        'producer_source':identity(__file__),'full_future_preparation_bytes':future,'measurement_commitment':commitment})
    print(json.dumps({'status':audit['status'],'actual_logical_bytes':actual,'full_future_preparation_bytes':future,'roots':len(rows)}))

if __name__=='__main__':main()
