import os,stat,hashlib
from pathlib import Path
from wm_diag0_rc1_final_v2.archive_v2 import canonical,check_time
from wm_diag0_rc1_final_v2.evidence_auth_v1 import bound_bytes
from wm_diag0_rc1_final_v2.inventory_v3 import safe_name
def source_closure(source,members,deadline,contract_name=None):
    source=Path(source)
    if not isinstance(members,dict) or not 0<len(members)<=5000:raise ValueError('finite explicit frozen source closure')
    allowed=set(members)
    if contract_name is not None:safe_name(contract_name);allowed.add(contract_name)
    # Source cannot silently acquire extra importable or configuration members.
    # No directory-link classification through os.walk, no following redirects.
    seen=set();pending=[source]
    while pending:
        check_time(deadline);directory=pending.pop()
        with os.scandir(str(directory)) as scan:entries=sorted(list(scan),key=lambda e:e.name)
        for entry in entries:
            p=Path(entry.path);s=entry.stat(follow_symlinks=False)
            if getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no source ancestor/member reparse redirect')
            if stat.S_ISDIR(s.st_mode):pending.append(p)
            elif stat.S_ISREG(s.st_mode):
                seen.add(p.relative_to(source).as_posix())
                if len(seen)>5001:raise ValueError('finite complete source member count')
            else:raise ValueError('no source alias/special member')
    if seen!=allowed:raise ValueError('complete exact source closure, including no extra importable member')
    total=0
    for name,want in sorted(members.items()):
        safe_name(name)
        total+=want.get('bytes',20000001)
        if total>20000000:raise ValueError('finite source byte bound; no artifact-supplied executable')
        bound_bytes(source/name,want,2000000,deadline)
    raw=canonical(members)
    return {'members':len(members),'bytes':total,'source_identity_map_sha256':hashlib.sha256(raw).hexdigest()}
