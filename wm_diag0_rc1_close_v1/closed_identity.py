import hashlib
from pathlib import Path
from wm_diag0_rc1_final_v2.evidence_auth_v1 import ordinary
from wm_diag0_rc1_final_v2.archive_v2 import check_time
def identity(path,limit,deadline):
    p=ordinary(path);n=p.stat().st_size
    if n>limit:raise ValueError('finite closed technical control/log bytes')
    h=hashlib.sha256();count=0
    with p.open('rb') as f:
        while True:
            check_time(deadline);raw=f.read(min(1048576,limit-count+1))
            if not raw:break
            count+=len(raw)
            if count>limit:raise ValueError('closed control/log grew')
            h.update(raw)
    want={'bytes':count,'sha256':h.hexdigest()};bound_bytes(p,want,limit,deadline);return want
