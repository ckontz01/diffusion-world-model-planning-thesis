"""Whole-root inventory with EXTERNALLY approved inert alias literals only.

Absolute, parent-relative, directory and chained aliases are preserved as plain
metadata, NEVER resolved, followed, restored or executed. No new target access
is granted. This is distinct from declaring those targets safe to execute.
"""
import os,stat
from pathlib import Path
from wm_diag0_rc1_final_v1.inventory import safe_name,MAX_MEMBERS,MAX_PAYLOAD,OVERHEAD

def alias_literal(target):
    if not isinstance(target,str) or not target or len(target.encode('utf8'))>4096 or any(x in target for x in ('\x00','\n','\r')):raise ValueError('bounded inert alias literal')
    return target

def plan(study_base,approved_children,external_roots,approved_aliases):
    base=Path(study_base)
    if base.is_symlink() or not base.is_dir():raise ValueError('physical canonical study root')
    children={p.name for p in base.iterdir()}
    if children!=set(approved_children) or len(approved_children)!=len(set(approved_children)):raise ValueError('every actual lineage/failure/partial required')
    roots={'study/'+safe_name(n):base/n for n in approved_children}
    for label,path in external_roots.items():
        safe_name(label)
        if label in roots or label.startswith('study/'):raise ValueError('unique external root label')
        roots[label]=Path(path)
    labels=sorted(roots)
    if any(a!=b and b.startswith(a+'/') for a in labels for b in labels):raise ValueError('nonoverlapping logical root labels')
    for name,target in approved_aliases.items():safe_name(name);alias_literal(target)
    files={};seen=set();total=0
    def add(name,path,s):
        nonlocal total
        safe_name(name)
        if name=='ARCHIVE-MEMBERS.json' or name in files or len(files)>=MAX_MEMBERS:raise ValueError('unique bounded whole inventory')
        if stat.S_ISLNK(s.st_mode):
            target=alias_literal(os.readlink(str(path)))
            if approved_aliases.get(name)!=target:raise ValueError('alias was not independently approved with exact literal')
            # Deliberately NO join/resolve/stat/open on the alias target.
            files[name]={'path':str(path),'type':'symlink','target':target};seen.add(name)
        elif stat.S_ISREG(s.st_mode):
            total+=s.st_size
            if s.st_size>4000000000 or total>MAX_PAYLOAD:raise ValueError('all logical copies/per-member bytes')
            files[name]={'path':str(path),'type':'file','bytes':s.st_size}
        else:raise ValueError('special file cannot be omitted')
    for label,root in sorted(roots.items()):
        if root.is_symlink():raise ValueError('explicit root cannot redirect')
        if root.is_file():add(label,root,root.lstat());continue
        if not root.is_dir():raise ValueError('missing approved whole root')
        for directory,dirs,names in os.walk(str(root),followlinks=False):
            for n in list(dirs):
                p=Path(directory)/n;s=p.lstat()
                if stat.S_ISLNK(s.st_mode):
                    add(label+'/'+p.relative_to(root).as_posix(),p,s);dirs.remove(n)
            for n in sorted(names):
                p=Path(directory)/n;add(label+'/'+p.relative_to(root).as_posix(),p,p.lstat())
    if seen!=set(approved_aliases):raise ValueError('missing/unused external alias approval')
    if len(files)*4096+20000000>OVERHEAD or total+OVERHEAD>14000000000:raise ValueError('full member/manifest overhead reservation')
    return {'members':files,'logical_payload_bytes_no_discounts':total,'archive_reserved_bytes':total+OVERHEAD,
            'root_labels':labels,'compression_or_hardlink_savings_assumed':False}
