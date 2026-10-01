"""Exclusive small R1 source export and verified authority copy."""
import argparse
import json
import shutil
import time
from pathlib import Path
from dtv_success_cost.common import ROOT,load,write,sha
from dtv_success_cost.preserve import make_archive,volume
HERE=ROOT/'docs/dtv-success-cost-publication-20261001/recovery-r1'
EXCLUDED={'PACKAGE-MANIFEST.json','AUTHORIZATION.json','EXECUTION-APPROVAL.json','IDENTITIES.json','SSD-BACKUP.json','PUBLICATION.json'}
def files():
    paths=list((ROOT/'dtv_success_cost_r1').glob('*.py'))+[p for p in HERE.iterdir() if p.is_file() and p.name not in EXCLUDED and not p.name.startswith(('STAGE-','LAUNCH-','OBSERVATION-'))]
    return [dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(paths)]
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','backup']);a=p.parse_args();manifest=HERE/'PACKAGE-MANIFEST.json'
    if a.mode=='freeze':
        test=load(HERE/'TEST-03.json')
        if test['errors'] or test['failures'] or test['tests']!=47:raise RuntimeError('complete artificial acceptance required')
        rows=files()
        if sum(r['bytes'] for r in rows)>500000:raise RuntimeError('small recovery closure cap')
        write(manifest,dict(study='DTV-EFF1-R1',scientific_changes=False,research_execution=False,files=rows))
        print(json.dumps(dict(manifest_sha256=sha(manifest),files=len(rows),bytes=sum(r['bytes'] for r in rows))));return
    v=volume();m=load(manifest)
    if m['files']!=files():raise RuntimeError('frozen recovery changed')
    destination=Path('D:/THESIS-BACKUPS/dtv-success-cost-20261001/recovery-r1')/('package-'+sha(manifest)[:16])
    if destination.exists():raise RuntimeError('R1 small backup already attempted; no duplicate/overwrite')
    destination.mkdir(parents=True);started=time.perf_counter()
    rows=[dict(r,source=str(ROOT/r['path'])) for r in m['files']]
    rows.append(dict(path='PACKAGE-MANIFEST.json',source=str(manifest),bytes=manifest.stat().st_size,sha256=sha(manifest)))
    info=make_archive(destination/'package.tar',rows)
    copies=[]
    for name in ('PACKAGE-MANIFEST.json','AUTHORIZATION.json','EXECUTION-APPROVAL.json'):
        source=HERE/name;target=destination/name;shutil.copyfile(source,target)
        if sha(source)!=sha(target) or source.stat().st_size!=target.stat().st_size:raise RuntimeError('R1 authority copy differs')
        copies.append(dict(path=name,bytes=target.stat().st_size,sha256=sha(target)))
    receipt=dict(status='verified',study='DTV-EFF1-R1',archive=str(destination/'package.tar'),**info,
                 copies=copies,manifest_sha256=sha(manifest),volume=v,whole_and_every_member_verified=True,
                 wall_seconds=time.perf_counter()-started,new_small_package_only=True,historical_archives_transferred=False)
    write(destination/'VERIFIED.json',receipt);write(HERE/'SSD-BACKUP.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
