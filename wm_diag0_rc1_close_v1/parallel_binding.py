"""Four-reader opaque binding with stable before/after file identities."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from wm_diag0_rc1_final_v2.archive_v2 import token,check_bindings,check_time,canonical
from wm_diag0_rc1_final_v2.archive_verify_v2 import source_hash
from wm_diag0_rc1_final_v2.root_binding_v1 import accumulator,add,finish

def parallel_authenticate(planned,root_paths,authority_sha256,deadline):
    members,state=accumulator(planned,root_paths,authority_sha256)
    check_bindings(planned,{'root_paths':root_paths,'final_contract_sha256':authority_sha256})
    def read(item):
        name,row=item;check_time(deadline);p=Path(row['path']);before=token(p,row['type']=='symlink')
        if row['type']=='file':digest=source_hash(p,row['bytes'],deadline)
        else:
            if os.readlink(str(p))!=row['target']:raise ValueError('approved inert literal changed')
            digest=None
        if token(p,row['type']=='symlink')!=before:raise ValueError('parallel original changed during hash')
        return name,row,digest,before
    observed={};metadata=[]
    # Four ordinary readers, not extra research/CPU allocations. map preserves
    # sorted logical order, so the root commitment equals the serial verifier.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name,row,digest,before in pool.map(read,sorted(members.items())):
            check_time(deadline)
            if token(Path(row['path']),row['type']=='symlink')!=before:raise ValueError('original changed before root commitment')
            add(state,name,row,digest);metadata.append([name,list(before),row.get('target')])
            if row['type']=='file':observed[row['path']]={'bytes':row['bytes'],'sha256':digest}
    check_time(deadline)
    import hashlib
    raw=canonical(metadata)
    return finish(planned,root_paths,authority_sha256,state),observed,{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
