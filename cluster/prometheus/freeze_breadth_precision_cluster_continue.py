"""Package a separate host controller, never changing frozen scientific bytes."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile

FILES=(
 'cluster/prometheus/breadth_precision_cluster_continue.py',
 'cluster/prometheus/test_breadth_precision_cluster_continue.py',
 'cluster/prometheus/freeze_breadth_precision_cluster_continue.py',
 'cluster/prometheus/breadth_precision_recovery.py',
 'cluster/prometheus/breadth_precision_recovery2.py',
 'docs/candidate-value-breadth-precision-20260915/CLUSTER-CONTINUATION-20260917.md',
)

def freeze(repo,parent):
    repo,parent=Path(repo),Path(parent)
    parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='cluster-continue-freeze-',dir=str(parent)))
    lines=[]
    for rel in FILES:
        src,dst=repo/rel,staging/Path(rel).name
        with src.open('rb') as inp,dst.open('xb') as out:shutil.copyfileobj(inp,out)
        lines.append(hashlib.sha256(dst.read_bytes()).hexdigest()+'  '+dst.name+'\n')
    manifest=staging/'SOURCE-MANIFEST.sha256'
    with manifest.open('x',newline='\n') as out:out.write(''.join(sorted(lines)))
    digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
    target=parent/('cvl-bp1-cluster-continue-'+digest[:16])
    if target.exists():raise RuntimeError('Never overwrite a frozen overlay')
    staging.rename(target)
    print(str(target));print(digest)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);parser.add_argument('--parent',required=True)
    args=parser.parse_args();freeze(args.repo,args.parent)
