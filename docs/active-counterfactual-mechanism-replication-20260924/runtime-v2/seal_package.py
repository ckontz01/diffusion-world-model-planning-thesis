"""Seal only after live metadata reconciliation and successful bounded tests."""
import common as c
import argparse
import tarfile
from pathlib import Path
from preserve import ssd,verify_tar

def closure():
    paths=set(c.ROOT.glob('*.py'))|set(c.ROOT.glob('*.sh'))|set(c.ROOT.glob('*.md'))|set(c.ROOT.glob('*.patch'))
    paths|={p for p in c.ROOT.glob('*.json') if p.name not in ('SOURCE-MANIFEST.json','EXECUTION-APPROVAL.json','PACKAGE-VERIFIED.json')}
    paths|=set(c.BASE.glob('*.py'))
    # Complete imported accepted scientific dependency closure, not historical research outputs.
    paths|={c.OLD/n for n in ('bridge.py','episodes.py','fitting.py','verify.py','hardware.py','artificial.py')}
    paths|={c.PROPOSAL/n for n in ('base.py','planned_analysis.py','GRID.json','PROTOCOL.json','ELIGIBILITY.json','DEPENDENCIES.json')}
    paths|={c.REPO/'cluster/prometheus/pusht_fresh_initialization.py'}
    paths|=set(c.files(c.ROOT/'review-input'))
    return sorted(paths)
def freeze():
    c.require(c.reconciliation()['status']=='LIVE_METADATA_RECONCILED','Cannot freeze: fresh cluster metadata reconciliation blocked')
    test=c.read(c.ROOT/'TEST-CORRECTION.json');c.require(test['passed'],'Focused production-path integration receipt')
    for n,h in test['tested_sources'].items():c.require(c.sha(c.ROOT/n)==h,'Source changed after final integration test')
    rows=c.lines(c.ROOT/'ATTEMPTS.jsonl');c.require({r['label'] for r in rows if r['state']=='started'}=={r['label'] for r in rows if r['state']=='finished'},'Unreconciled local test')
    preservation=c.read(c.ROOT/'TEST-PRESERVATION.json');c.require(preservation['passed'],'Preservation regression')
    for n,h in preservation['source_sha256'].items():c.require(c.sha(c.ROOT/n)==h,'Preservation source changed after test')
    c.require(c.read(c.ROOT/'PROBE-REPRODUCTION.json')['all_expected_probe_checks_passed'],'Review probes reproduced')
    c.require(sum(r.get('wall_seconds',0) for r in rows)<=7200 and c.bytes_in(c.ROOT)<=250_000_000,'Correction preparation envelope')
    c.write(c.ROOT/'PREPARATION-RECEIPT.json',dict(attempts=rows,wall_seconds=sum(r.get('wall_seconds',0) for r in rows),
                peak_job_memory_bytes=max(r.get('peak_job_memory_bytes',0) for r in rows),research_allocations=0,payload_reads=0,
                artifact_bytes=c.bytes_in(c.ROOT),tests_sha256=c.sha(c.ROOT/'TEST-CORRECTION.json')))
    manifest={'files':{p.relative_to(c.REPO).as_posix():c.sha(p) for p in closure()},'schema':'ACVM1-source-v1','execution_enabled':False}
    c.write(c.ROOT/'SOURCE-MANIFEST.json',manifest);h=c.sha(c.ROOT/'SOURCE-MANIFEST.json')
    c.write(c.ROOT/'EXECUTION-APPROVAL.json',dict(schema='ACVM1-execution-v1',authorized=False,instruction='',package_sha256=h,
            bindings=c.bindings(),run=c.RUN_PARENT+'/run-'+h[:16],no_retry=True,caps=c.caps()))
    output=c.ROOT/'SOURCE-PACKAGE.tar'
    with output.open('xb') as f,tarfile.open(fileobj=f,mode='w') as t:
        for p in closure()+[c.ROOT/'SOURCE-MANIFEST.json',c.ROOT/'EXECUTION-APPROVAL.json']:t.add(p,arcname=p.relative_to(c.REPO).as_posix(),recursive=False)
    c.require(output.stat().st_size<=40_000_000,'Small source export cap');return h
def backup_package():
    volume=ssd();h=c.sha(c.ROOT/'SOURCE-MANIFEST.json');c.source_check()
    dest=Path('D:/THESIS-BACKUPS')/c.NAMESPACE/('preparation-runtime-v2-'+h[:16]);dest.mkdir(parents=True,exist_ok=False)
    original=c.ROOT/'SOURCE-PACKAGE.tar';copied=dest/'SOURCE-PACKAGE.tar'
    import shutil
    with original.open('rb') as r,copied.open('xb') as w:shutil.copyfileobj(r,w)
    c.require(c.sha(original)==c.sha(copied) and original.stat().st_size==copied.stat().st_size,'Small package copied bytes')
    expected={}
    for p in closure()+[c.ROOT/'SOURCE-MANIFEST.json',c.ROOT/'EXECUTION-APPROVAL.json']:
        expected[p.relative_to(c.REPO).as_posix()]=dict(bytes=p.stat().st_size,sha256=c.sha(p))
    verified=verify_tar(copied,expected)
    receipt=dict(manifest=h,bundle_sha256=c.sha(copied),ssd_bundle=str(copied),volume=volume,verified=verified)
    c.write(dest/'PACKAGE-VERIFIED.json',receipt);c.write(c.ROOT/'PACKAGE-VERIFIED.json',receipt)
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['freeze','backup-package']);a=p.parse_args()
    print(c.json.dumps(freeze() if a.operation=='freeze' else backup_package()))
