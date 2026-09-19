"""Exclusive LF source export, disabled approval and member-verified tar on SSD."""
import argparse,hashlib,json,tarfile
from pathlib import Path
import lgprb1_contract as c
from lgp1_preserve import check_ssd,verify_archive

BASE=Path('D:/THESIS-BACKUPS/local-goal-proposals-20260918/preparation-policy-recovery-20260919')
DEST=Path('D:/THESIS-BACKUPS')/c.NAME

def export(repo,destination):
    repo,destination=Path(repo),Path(destination)
    check_ssd();c.require(destination.parent==DEST and not destination.exists(),'Exclusive designated SSD source export')
    reuse=c.read(repo/c.DOC/'REUSE.json');payload={}
    c.require(c.sha(BASE/'LGP1-SOURCE-MANIFEST.sha256')==c.OLD_SOURCE_SHA,'Executed base export manifest')
    c.old.verify(BASE,'LGP1-SOURCE-MANIFEST.sha256')
    for name,h in reuse['source_files'].items():
        data=(BASE/name).read_bytes();c.require(hashlib.sha256(data).hexdigest()==h,'Original source closure '+name);payload[name]=data
    for name in ('cluster/prometheus/lgp1_runtime.py','cluster/prometheus/lgp1_preserve.py'):
        payload[name]=(repo/name).read_bytes().replace(b'\r\n',b'\n')
    paths=list((repo/'cluster/prometheus').glob('lgprb1_*.py'))+[repo/'cluster/prometheus/test_lgprb1.py',repo/'cluster/prometheus/run_lgprb1.sh']
    paths += [repo/c.DOC/n for n in ('PROTOCOL.md','RESOURCE-PLAN.md','README.md','HISTORY.md','REUSE.json','GRID.json','MEASURED-COST.json','LEGACY-RUNTIME.py.txt','REMOTE-BYTE-COMPATIBILITY.json')]
    for p in paths:payload[p.relative_to(repo).as_posix()]=p.read_bytes().replace(b'\r\n',b'\n')
    for name,h in reuse['unchanged_scientific_components'].items():
        c.require(hashlib.sha256(payload[name]).hexdigest()==h,'Scientific component drift '+name)
    c.require(hashlib.sha256(payload[c.old.DOC+'/INPUTS.json']).hexdigest()==c.INPUT_SHA,'Unchanged input lock')
    c.require(hashlib.sha256(payload[c.DOC+'/LEGACY-RUNTIME.py.txt']).hexdigest()==reuse['legacy_runtime_sha256'],'Verbatim executed runtime')
    c.require(sum(map(len,payload.values()))<10_000_000,'Small source transport')
    destination.mkdir(parents=True,exist_ok=False)
    for name,data in sorted(payload.items()):
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
    with (destination/c.MANIFEST).open('x',encoding='utf8',newline='\n') as f:
        for name,data in sorted(payload.items()):f.write(hashlib.sha256(data).hexdigest()+'  '+name+'\n')
    c.write(destination/'APPROVAL-TEMPLATE.json',c.template(destination));c.old.verify(destination,c.MANIFEST)
    inventory={p.relative_to(destination).as_posix():dict(sha256=c.sha(p),bytes=p.stat().st_size) for p in destination.rglob('*') if p.is_file()}
    target=destination.with_suffix('.tar')
    with tarfile.open(target,'x',format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(inventory):tar.add(destination/name,arcname=name,recursive=False)
    result=verify_archive(target,inventory)
    result.update(source_sha256=c.sha(destination/c.MANIFEST),input_sha256=c.INPUT_SHA,
        protocol_sha256=c.sha(destination/c.DOC/'PROTOCOL.md'),reuse_sha256=c.sha(destination/c.DOC/'REUSE.json'),
        grid_sha256=c.sha(destination/c.DOC/'GRID.json'),approval_template_sha256=c.sha(destination/'APPROVAL-TEMPLATE.json'),
        source=str(destination),archive=str(target),execution_authorized=False,inventory=inventory)
    c.write(destination.with_suffix('.package.json'),result)
    return {k:v for k,v in result.items() if k!='inventory'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    print(json.dumps(export(a.repo,a.destination),indent=2))
