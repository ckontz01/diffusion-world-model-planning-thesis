"""Export committed source/import closure, never data, to an immutable tar."""
import argparse
import ast
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path


def git(*args):return subprocess.check_output(['git',*args])


def package(commit,out):
    commit=git('rev-parse',commit).decode().strip()
    files=set(git('ls-tree','-r','--name-only',commit).decode().splitlines());base='cluster/prometheus/'
    pending=[p for p in files if p.startswith(base) and p.endswith('.py') and
             (Path(p).name.startswith(('candidate_value','test_candidate_value','prepare_candidate_value','package_candidate_value')))]
    pending += [base+n for n in ('independent_pusht_runtime.py','independent_pusht_collect.py',
                                'e18_fresh_driver.py','single_anchor_ranking.py','test_single_anchor_ranking.py',
                                'test_single_anchor_ranking_host.py')]
    payload={}
    while pending:
        p=pending.pop()
        if p in payload:continue
        data=git('show',commit+':'+p);payload[p]=data
        for node in ast.walk(ast.parse(data,filename=p)):
            names=[n.name for n in node.names] if isinstance(node,ast.Import) else (
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for n in names:
                target=base+n.split('.')[0]+'.py'
                if target in files and target not in payload:pending.append(target)
    extras=[base+'INDEPENDENT-PINNED-INPUTS.json',base+'run_candidate_value.sh']
    extras += sorted(p for p in files if p.startswith('docs/candidate-value-learning-20260914/'))
    for p in extras:payload[p]=git('show',commit+':'+p)
    for p,b in payload.items():
        if p.endswith('.sh') and b'\r' in b:raise RuntimeError('CRLF shell in Git object: '+p)
    payload['PACKAGE.json']=(json.dumps(dict(commit=commit,kind='CVL-source-only',files=len(payload),
        real_launch_approved=False),sort_keys=True)+'\n').encode()
    manifest=''.join(hashlib.sha256(v).hexdigest()+'  '+p+'\n' for p,v in sorted(payload.items())).encode()
    payload['SOURCE-MANIFEST.sha256']=manifest
    with Path(out).open('xb') as f:
        with tarfile.open(fileobj=f,mode='w') as tar:
            for p,b in sorted(payload.items()):
                info=tarfile.TarInfo(p);info.size=len(b);info.mtime=0;info.mode=0o444
                tar.addfile(info,io.BytesIO(b))
    return dict(commit=commit,source_sha256=hashlib.sha256(manifest).hexdigest(),members=len(payload))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(package(a.commit,a.out),sort_keys=True))
