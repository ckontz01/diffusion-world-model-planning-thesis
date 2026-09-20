"""New immutable LF export layered on the exact executed RB1 source."""
import argparse,hashlib,json,tarfile
from pathlib import Path
import lgprb2_contract as c
from lgp1_preserve import check_ssd,verify_archive

BASE=Path('D:/THESIS-BACKUPS/local-goal-search-budget-20260919/preparation-v1')
DEST=Path('D:/THESIS-BACKUPS')/c.NAME

def export(repo,destination):
    check_ssd();repo,destination=Path(repo),Path(destination)
    c.require(destination.parent==DEST and not destination.exists(),'Exclusive designated SSD export')
    c.require(c.sha(BASE/c.rb1.MANIFEST)==c.RB1_SOURCE_SHA,'Executed RB1 source manifest');c.old.verify(BASE,c.rb1.MANIFEST)
    payload={}
    for line in (BASE/c.rb1.MANIFEST).read_text().splitlines():
        digest,name=line.split('  ',1);data=(BASE/name).read_bytes();c.require(hashlib.sha256(data).hexdigest()==digest,'Inherited source');payload[name]=data
    paths=list((repo/'cluster/prometheus').glob('lgprb2_*.py'))+[repo/'cluster/prometheus/test_lgprb2.py',repo/'cluster/prometheus/run_lgprb2.sh']
    paths += [p for p in (repo/c.DOC).iterdir() if p.is_file() and p.name not in ('PREPARATION-RECEIPT.md','TEST-RESULTS.json')]
    # Include original metadata records as auditable identifiers, never payloads.
    from lgprb2_prepare import ROLE_FILES
    paths += [repo/v for v in ROLE_FILES.values()]
    for p in paths:
        name=p.relative_to(repo).as_posix();data=p.read_bytes().replace(b'\r\n',b'\n')
        if name in payload:c.require(payload[name]==data,'No replacement of inherited source '+name)
        payload[name]=data
    reuse=c.read(repo/c.DOC/'REUSE.json')
    for name,digest in reuse['unchanged_files'].items():c.require(hashlib.sha256(payload[name]).hexdigest()==digest,'Frozen scientific component')
    c.require(sum(map(len,payload.values()))<20_000_000,'Source allowance')
    destination.mkdir(parents=True,exist_ok=False)
    for name,data in sorted(payload.items()):
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    with (destination/c.MANIFEST).open('x',encoding='utf8',newline='\n') as f:
        for name,data in sorted(payload.items()):f.write(hashlib.sha256(data).hexdigest()+'  '+name+'\n')
    c.write(destination/'APPROVAL-TEMPLATE.json',c.template(destination));c.old.verify(destination,c.MANIFEST)
    inventory={p.relative_to(destination).as_posix():dict(bytes=p.stat().st_size,sha256=c.sha(p)) for p in destination.rglob('*') if p.is_file()}
    target=destination.with_suffix('.tar')
    with tarfile.open(target,'x',format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(inventory):tar.add(destination/name,arcname=name,recursive=False)
    result=dict(**verify_archive(target,inventory),source=str(destination),archive=str(target),source_sha256=c.sha(destination/c.MANIFEST),
        input_sha256=c.sha(destination/c.DOC/'INPUTS.json'),roles_sha256=c.sha(destination/c.DOC/'DATA-ROLES.json'),
        grid_sha256=c.sha(destination/c.DOC/'GRID.json'),protocol_sha256=c.sha(destination/c.DOC/'PROTOCOL.md'),
        execution_authorized=False,inventory=inventory)
    c.write(destination.with_suffix('.package.json'),result);return {k:v for k,v in result.items() if k!='inventory'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    print(json.dumps(export(a.repo,a.destination),indent=2))
