"""Fail-closed all-lineage archive inventory; no hardlink/compression discounts.

This is not an archive creator or transfer command. Actual root/member/alias
allowlists must be frozen after technical metadata reconciliation. No roots are
silently inferred from obsolete six-root finalizers.
"""
import os,stat
from pathlib import Path,PurePosixPath

MAX_MEMBERS=100000
MAX_PAYLOAD=13500000000
OVERHEAD=500000000


def safe_name(name):
    if not isinstance(name,str) or not name or len(name.encode('utf8'))>512 or '\\' in name or ':' in name or '\x00' in name or name.startswith('/') or any(x in ('','.','..') for x in name.split('/')):
        raise ValueError('bounded canonical relative archive member')
    return name


def plan(study_base,approved_children,external_roots,approved_aliases):
    """Only explicit whole roots. Unknown canonical-study children stop binding.

    external_roots maps safe archive prefixes to reviewed runtime/model roots.
    approved_aliases maps exact archived symlink names to exact relative targets;
    it is externally bound, not learned from the files being archived.
    """
    base=Path(study_base)
    if base.is_symlink() or not base.is_dir():raise ValueError('actual canonical study directory')
    children={p.name for p in base.iterdir()}
    if children!=set(approved_children):raise ValueError('every actual lineage/root/partial must be accounted for')
    roots={'study/'+safe_name(n):base/n for n in approved_children}
    for label,path in external_roots.items():
        safe_name(label)
        if label in roots or label.startswith('study/'):raise ValueError('unique explicit external archive root')
        roots[label]=Path(path)
    files={};total=0;aliases=set()
    def add(name,p):
        nonlocal total
        safe_name(name)
        if name=='ARCHIVE-MEMBERS.json' or name in files or len(files)>=MAX_MEMBERS:raise ValueError('unique bounded archive inventory')
        mode=p.lstat().st_mode
        if stat.S_ISLNK(mode):
            target=os.readlink(str(p));want=approved_aliases.get(name)
            if target!=want or not target or target.startswith('/') or '\\' in target or ':' in target or any(x in ('','.','..') for x in target.split('/')):raise ValueError('exact reviewed relative alias only')
            resolved=p.parent/target
            if resolved.is_symlink() or not resolved.is_file():raise ValueError('alias must target direct regular file')
            files[name]={'path':str(p),'type':'symlink','target':target};aliases.add(name)
        elif stat.S_ISREG(mode):
            size=p.stat().st_size
            if size>4000000000:raise ValueError('per-member byte bound')
            total+=size
            if total>MAX_PAYLOAD:raise ValueError('all logical copies counted without deduplication')
            files[name]={'path':str(p),'type':'file','bytes':size}
        else:raise ValueError('no device/socket/FIFO or unhandled directory')
    for label,root in sorted(roots.items()):
        if root.is_symlink():raise ValueError('no symlink root')
        if root.is_dir():
            for directory,dirs,names in os.walk(str(root),followlinks=False):
                for n in list(dirs):
                    p=Path(directory)/n
                    if p.is_symlink():raise ValueError('no symlink directories')
                for n in sorted(names):
                    p=Path(directory)/n;add(label+'/'+p.relative_to(root).as_posix(),p)
        elif root.is_file():add(label,root)
        else:raise ValueError('missing explicitly approved root')
    if aliases!=set(approved_aliases):raise ValueError('unused/missing alias allowlist member')
    # A conservative envelope, not reliance on hardlinks or compressibility.
    if len(files)*4096+20000000>OVERHEAD or total+OVERHEAD>14000000000:raise ValueError('member and manifest overhead envelope')
    return {'members':files,'logical_payload_bytes_no_discounts':total,'archive_reserved_bytes':total+OVERHEAD,
        'root_labels':sorted(roots),'compression_or_hardlink_savings_assumed':False}
