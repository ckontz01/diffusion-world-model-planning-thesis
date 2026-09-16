"""Freeze only the second approved host overlay, preserving the scientific snapshot."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile

FILES = (
    'cluster/prometheus/breadth_precision_recovery2.py',
    'cluster/prometheus/breadth_precision_backup_recovery2.py',
    'cluster/prometheus/breadth_precision_volume_lease.ps1',
    'cluster/prometheus/test_breadth_precision_recovery2.py',
    'cluster/prometheus/freeze_breadth_precision_recovery2.py',
    'cluster/prometheus/breadth_precision_recovery.py',
    'cluster/prometheus/breadth_precision_backup_recovery.py',
    'docs/candidate-value-breadth-precision-20260915/RECOVERY2-20260917.md',
)


def freeze(repo, parent):
    repo, parent = Path(repo), Path(parent)
    parent.mkdir(parents=True,exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='recovery2-freeze-',dir=str(parent)))
    lines = []
    for rel in FILES:
        src, dst = repo/rel, staging/Path(rel).name
        with src.open('rb') as inp, dst.open('xb') as out: shutil.copyfileobj(inp,out)
        lines.append(hashlib.sha256(dst.read_bytes()).hexdigest()+'  '+dst.name+'\n')
    manifest = staging/'SOURCE-MANIFEST.sha256'
    with manifest.open('x',newline='\n') as out: out.write(''.join(sorted(lines)))
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    target = parent/('cvl-bp1-recovery2-'+digest[:16])
    if target.exists(): raise RuntimeError('No frozen overlay overwrite')
    staging.rename(target)
    print(str(target)); print(digest)


if __name__ == '__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--repo',required=True);cli.add_argument('--parent',required=True)
    args=cli.parse_args();freeze(args.repo,args.parent)
