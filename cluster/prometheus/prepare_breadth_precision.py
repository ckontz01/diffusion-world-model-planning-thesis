"""Source/metadata-only packaging. Never authorizes or launches execution."""
import argparse
import hashlib
from pathlib import Path
import breadth_precision_contract as p
import candidate_value_contract as ct

EXTRA = tuple('cluster/prometheus/'+n for n in (
    'breadth_precision_contract.py','breadth_precision_data.py','breadth_precision_learning.py',
    'breadth_precision_execute.py','breadth_precision_backup.py','breadth_precision_infra.py','prepare_breadth_precision.py',
    'run_breadth_precision.sh','test_breadth_precision.py')) + (
    'analysis/cvl1-objective-capacity-20260915-v1/study.py',
    p.MANIFEST,p.DOC,'docs/'+p.VERSION+'/RESOURCE-PLAN.md',
    'docs/'+p.VERSION+'/IMPLEMENTATION.md')


def source_freeze(repo, upstream, destination):
    repo,upstream,destination=map(Path,(repo,upstream,destination))
    p.require(p.sha(upstream/'SOURCE-MANIFEST.sha256')==p.OLD_SOURCE_SHA,'Pinned original source manifest')
    ct.verify_source(upstream,p.OLD_SOURCE_SHA)
    p.require(not destination.exists(),'New immutable snapshot only')
    destination.mkdir(parents=True,exist_ok=False)
    for line in (upstream/'SOURCE-MANIFEST.sha256').read_text().splitlines():
        digest,name=line.split('  ',1)
        target=ct.child(destination,name);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(ct.child(upstream,name).read_bytes())
        p.require(p.sha(target)==digest,'Byte-identical inherited source')
    (destination/'UPSTREAM-MANIFEST.sha256').write_bytes((upstream/'SOURCE-MANIFEST.sha256').read_bytes())
    for name in EXTRA:
        target=ct.child(destination,name)
        p.require(not target.exists(),'New source may not replace inherited source')
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=ct.child(repo,name).read_bytes().replace(b'\r\n',b'\n')
        p.require(b'\r' not in raw,'Source LF transport')
        target.write_bytes(raw)
    from breadth_precision_learning import METRICS_SHA
    p.require(p.sha(destination/'analysis/cvl1-objective-capacity-20260915-v1/study.py')==METRICS_SHA,
              'Unchanged accepted metrics helper')
    ct.json_write(destination/'EXECUTION-GRID.json',p.costs())
    ct.json_write(destination/'APPROVAL-TEMPLATE.json',dict(experiment=p.VERSION,researcher_approved=False,
        source_sha256='SET_AFTER_FREEZE',protocol_sha256=p.sha(destination/p.DOC),
        role_manifest_sha256=p.sha(destination/p.MANIFEST),caps=p.CAPS,
        old_capsule=str(p.ROOT/'staging/candidate-value-learning-20260914-521a0e6627c570ff/LAUNCH-CAPSULE.json')))
    entries=sorted(x for x in destination.rglob('*') if x.is_file())
    manifest=''.join(p.sha(x)+'  '+x.relative_to(destination).as_posix()+'\n' for x in entries)
    (destination/'SOURCE-MANIFEST.sha256').write_bytes(manifest.encode())
    digest=p.sha(destination/'SOURCE-MANIFEST.sha256');ct.verify_source(destination,digest)
    p.require(2*sum(x.stat().st_size for x in destination.rglob('*') if x.is_file())<p.CAPS['source_bytes'],
              'Extracted source plus transport reservation')
    return dict(source=str(destination),source_sha256=digest,
        protocol_sha256=p.sha(destination/p.DOC),role_manifest_sha256=p.sha(destination/p.MANIFEST),
        execution_authorized=False,source_files=len(entries),
        run=str(p.RUN_PARENT/('run-'+digest[:16])))


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('mode',choices=['plan','freeze'])
    cli.add_argument('--repo');cli.add_argument('--upstream',default=str(p.OLD_SOURCE));cli.add_argument('--out')
    a=cli.parse_args()
    if a.mode=='plan':
        import json
        print(json.dumps(p.costs(),indent=2))
    else:
        p.require(a.repo and a.out,'Explicit repository and new snapshot directory required')
        print(source_freeze(a.repo,a.upstream,a.out))
