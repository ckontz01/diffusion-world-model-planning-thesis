"""Small immutable launch-review export only; never a research-data backup cycle."""
import argparse
import shutil
import time
from dtv_success_cost.common import *
from dtv_success_cost.preserve import inventory,make_archive,volume

SUPPORT=['dtv_efficiency/__init__.py','dtv_efficiency/profile.py','dtv_efficiency/test_profile.py','dtv_efficiency/campaign.py','dtv_efficiency/accept.py','dtv_efficiency/package.py','dtv_efficiency/prepare.py','dtv_efficiency/recover.py',
         'dtv_efficiency_r1/__init__.py','dtv_efficiency_r1/campaign.py','dtv_efficiency_r1/control.py','dtv_efficiency_r1/deadline.py','dtv_efficiency_r1/profile.py','dtv_efficiency_r1/accept.py','dtv_efficiency_r1/test_control.py','dtv_efficiency_r1/package.py',
         'cluster/prometheus/pusht_fresh_initialization.py']

def files():
    paths=set(ROOT/p for p in SUPPORT)
    for base in ('dtv_success_cost','dtv_efficiency','dtv_efficiency_r1','docs/dtv-success-cost-20261001','docs/dtv-efficiency-20260930','docs/dtv-efficiency-correction-r1-20260930'):
        paths.update(p for p in (ROOT/base).rglob('*') if p.is_file())
    excluded={'PACKAGE-MANIFEST.json','SSD-BACKUP.json','PUBLICATION.json'}
    out=[]
    for p in sorted(paths):
        if '__pycache__' in p.parts or (p.parent==DOC and p.name in excluded):continue
        # Historical evidence is included read-only as the reproducible delegated
        # scientific/test dependency, not regenerated or republished as new data.
        out.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','backup']);a=p.parse_args();manifest=DOC/'PACKAGE-MANIFEST.json'
    if a.mode=='freeze':
        rows=files()
        if sum(r['bytes'] for r in rows)>load(DOC/'BINDINGS.json')['source_bytes']-300000:raise RuntimeError('complete source including manifest ceiling')
        write(manifest,dict(study='DTV-EFF1',research_execution=False,files=rows));print(dict(package_sha256=sha(manifest),members=len(rows),bytes=sum(r['bytes'] for r in rows)+manifest.stat().st_size));return
    v=volume();rows=load(manifest)['files']
    if rows!=files():raise RuntimeError('frozen package changed')
    target=Path('D:/THESIS-BACKUPS/dtv-success-cost-20261001/preparation-v1')/('package-'+sha(manifest)[:16])
    if target.exists():raise RuntimeError('new small export already exists; no duplicate cycle')
    target.mkdir(parents=True);start=time.perf_counter()
    entries=[dict(r,source=str(ROOT/r['path'])) for r in rows]+[dict(path='PACKAGE-MANIFEST.json',source=str(manifest),sha256=sha(manifest),bytes=manifest.stat().st_size)]
    archive=make_archive(target/'package.tar',entries);shutil.copyfile(manifest,target/'PACKAGE-MANIFEST.json')
    if sha(target/'PACKAGE-MANIFEST.json')!=sha(manifest):raise RuntimeError('copied manifest bytes differ')
    receipt=dict(status='verified',study='DTV-EFF1',archive=str(target/'package.tar'),**archive,package_sha256=sha(manifest),whole_and_every_member_verified=True,volume=v,wall_seconds=time.perf_counter()-start,
                 only_new_small_package=True,historical_archives_rebuilt=False,research_execution=False)
    write(target/'VERIFIED.json',receipt);write(DOC/'SSD-BACKUP.json',receipt);print(__import__('json').dumps(receipt))
if __name__=='__main__':main()
