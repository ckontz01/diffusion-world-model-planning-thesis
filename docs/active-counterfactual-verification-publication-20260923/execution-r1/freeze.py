"""One exclusive R1 freeze. Original v1/v2 source closures remain untouched."""
from pathlib import Path
import sys
import tarfile
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PACKAGE=REPO/'docs/active-counterfactual-verification-20260923/bindings-r1'
sys.path.insert(0,str(PACKAGE))
import common as c
import recovery

def main():
    old=c.BASE/'bindings-v2';original=c.read(old/'SOURCE-MANIFEST.json')
    for name,h in original['files'].items():assert c.sha(REPO/name)==h,name
    unchanged=('bridge.py','episodes.py','verify.py','fitting.py','analysis.py','artificial.py','model_seal.py',
               'controller_runtime.py','CONTROLLER-RUNTIME.json','run_worker.sh','INPUT-BINDINGS.json')
    assert all(c.sha(old/n)==c.sha(PACKAGE/n) for n in unchanged)
    amended=c.read(old/'GRID.json');assert amended[0]['key']=='collect-fit-490';amended[0]['seconds']=1740
    assert amended==c.grid() and c.read(PACKAGE/'GRID.json')==amended
    attempts=[c.json.loads(s) for s in (PACKAGE/'ATTEMPTS.jsonl').read_text().splitlines()]
    assert attempts[-1]['returncode']==0 and sum(r.get('wall_seconds',0) for r in attempts)<7200
    c.write(PACKAGE/'FREEZE-RECEIPT.json',{'old_source_manifest':c.sha(old/'SOURCE-MANIFEST.json'),
       'unchanged_modules':{n:c.sha(PACKAGE/n) for n in unchanged},'old_grid_sha256':c.digest(c.read(old/'GRID.json')),
       'new_grid_sha256':c.digest(c.grid()),'only_grid_amendment':'collect-fit-490 seconds1800->1740',
       'tests_ledger_sha256':c.sha(PACKAGE/'ATTEMPTS.jsonl'),'test_wall_seconds':sum(r.get('wall_seconds',0) for r in attempts),
       'prior_charge_seconds':23,'initial_maximum_gpu_seconds':220763,'research_allocations_during_preparation':0})
    files={n:h for n,h in original['files'].items() if '/bindings-v2/' not in n}
    for p in sorted(PACKAGE.iterdir()):
        if p.is_file() and p.name not in ('ATTEMPTS.jsonl','DELIVERY.json'):
            files[p.relative_to(REPO).as_posix()]=c.sha(p)
    c.write(PACKAGE/'SOURCE-MANIFEST.json',{'schema':'ACV0-recovery-r1-source','recovery_of':c.sha(old/'SOURCE-MANIFEST.json'),'files':files})
    h=c.sha(PACKAGE/'SOURCE-MANIFEST.json')
    template=c.read(old/'APPROVAL-TEMPLATE.json');assert template['authorized'] is False
    template.update(schema='ACV0-recovery-r1',package_sha256=h,grid_sha256=c.digest(c.grid()),run=c.RUN_PARENT+'/run-'+h[:16],recovery=recovery.approval_binding(h))
    c.write(PACKAGE/'APPROVAL-TEMPLATE.json',template)
    for name in ('SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'):files[(PACKAGE/name).relative_to(REPO).as_posix()]=c.sha(PACKAGE/name)
    archive=PACKAGE/'source-export.tar';members={}
    with archive.open('xb') as output:
        with tarfile.open(fileobj=output,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for name,h in sorted(files.items()):
                p=REPO/name;assert c.sha(p)==h
                info=tar.gettarinfo(str(p),arcname=name);info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
                with p.open('rb') as stream:tar.addfile(info,stream)
                members[name]={'sha256':h,'bytes':p.stat().st_size}
    from preserve import verify_tar
    verify_tar(archive,members)
    c.write(PACKAGE/'SOURCE-TRANSPORT.json',{'sha256':c.sha(archive),'bytes':archive.stat().st_size,'members':members,
           'research_payloads_included':0,'execution_authorized':False})
    print(c.json.dumps({'manifest':c.sha(PACKAGE/'SOURCE-MANIFEST.json'),'archive':c.sha(archive),'bytes':archive.stat().st_size,'members':len(members),'run':template['run']}))

if __name__=='__main__':main()
