"""Verify imported Python/binary files against existing full runtime manifest."""
import json
import sys
from pathlib import Path
from .common import identity

def verify_imports(c,source):
    root=Path(c['venv']); site=root/'lib/python3.11/site-packages'
    p=Path(c['run'])/'controls/RUNTIME-MANIFEST.json'
    if identity(p)!=c['runtime_manifest']: raise ValueError('frozen runtime manifest identity')
    members=json.loads(p.read_text())['members']; checked={}
    for name,module in list(sys.modules.items()):
        path=getattr(module,'__file__',None)
        if not path: continue
        path=Path(path)
        if str(path).startswith(str(site)+'/'):
            rel=str(path.relative_to(root))
            if rel not in members or identity(path)!=members[rel]: raise ValueError('imported runtime changed: '+name)
            checked[rel]=members[rel]
        elif str(path).startswith(str(source)+'/'):
            rel=str(path.relative_to(source))
            if rel not in c['staged_members'] or identity(path)!=c['staged_members'][rel]: raise ValueError('staged import changed: '+name)
    return checked
