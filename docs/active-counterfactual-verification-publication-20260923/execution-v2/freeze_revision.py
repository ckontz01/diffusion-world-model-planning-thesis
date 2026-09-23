"""Freeze technical revision exclusively; never launch or regenerate science."""
from pathlib import Path
import sys
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PACKAGE=REPO/'docs/active-counterfactual-verification-20260923/bindings-v2'
sys.path.insert(0,str(PACKAGE))
import common as c

def main():
    old=c.BASE/'bindings-v1'
    original=c.read(old/'SOURCE-MANIFEST.json')
    # Authenticate the entire accepted closure before creating the revision.
    for name,h in original['files'].items():assert c.sha(REPO/name)==h,name
    identical=('common.py','bridge.py','episodes.py','verify.py','fitting.py','worker.py',
               'supervise.py','analysis.py','preserve.py','run_worker.sh','INPUT-BINDINGS.json','GRID.json','artificial.py')
    unchanged={name:c.sha(PACKAGE/name) for name in identical}
    assert all(c.sha(old/name)==h for name,h in unchanged.items())
    assert c.digest(c.grid())=='f9b4986c9f674122c253cff9aaf802e8d4b181180553d0e5643c0c92bb175a2a'
    accepted_ledger=subprocess.check_output(['git','show','b27605ccf7e9097beb02e3d0d638d3e31a175121:'+str((old/'ATTEMPTS.jsonl').relative_to(REPO)).replace('\\','/')],cwd=REPO)
    ledger=(old/'ATTEMPTS.jsonl').read_bytes()
    assert ledger.startswith(accepted_ledger),'Historical ledger was changed rather than appended'
    entries=[c.json.loads(line) for line in ledger.splitlines()]
    tests=[e for e in entries if e['label']=='technical-v2-integration']
    assert len(tests)==2 and tests[-1]['returncode']==0
    c.write(PACKAGE/'TECHNICAL-REVISION-RECEIPT.json',{
      'previous_manifest':c.sha(old/'SOURCE-MANIFEST.json'),'accepted_closure_all_38_members_unchanged':len(original['files'])==38,
      'byte_identical_modules_and_contract':unchanged,'test_attempt':tests,
      'prior_ledger_bytes_preserved':len(accepted_ledger),'append_only_ledger_extension_bytes':len(ledger)-len(accepted_ledger),
      'ledger_note':'The first v2 synthetic test used the prior bounded runner, appending evidence only. Original ledger bytes and all sealed v1 members remain unchanged. Further tests use v2 runner with cumulative v1+v2 accounting.',
      'cumulative_script_wall_seconds_through_integration':sum(e.get('wall_seconds',0) for e in entries),
      'scientific_grid_repeats':0,'research_payload_reads':0,'research_allocations':0,
      'authority':'Original delegated EXECUTE ACV0 direction plus direct user technical-correction instruction: FIX ALL TECHNICAL ISSUES TO ACHIEVE WHAT WAS SAID IN THE INSTRUCTIONS',
      'revision':'stdlib model seal; pin existing host Python and Slurm; unchanged container workers and science'})
    # Carry all parent scientific dependencies from the exact accepted manifest.
    files={name:h for name,h in original['files'].items() if '/bindings-v1/' not in name}
    files[(old/'README.md').relative_to(REPO).as_posix()]=c.sha(old/'README.md')
    for p in sorted(PACKAGE.iterdir()):
        if p.is_file() and p.name not in ('ATTEMPTS.jsonl','DELIVERY.json'):
            files[p.relative_to(REPO).as_posix()]=c.sha(p)
    c.write(PACKAGE/'SOURCE-MANIFEST.json',{'reviewed_base':'1c66038901fe39640add38aa796a816c06ccd1ae',
         'technical_revision_of':'bf3f4558f2cdfbca98715ad684c596d23626d5650e32a72a0e26f46dc3f83554','files':files})
    h=c.sha(PACKAGE/'SOURCE-MANIFEST.json')
    template=c.read(old/'APPROVAL-TEMPLATE.json');assert template['authorized'] is False
    template.update(package_sha256=h,run=c.RUN_PARENT+'/run-'+h[:16])
    c.write(PACKAGE/'APPROVAL-TEMPLATE.json',template)
    for name in ('SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json'):
        files[(PACKAGE/name).relative_to(REPO).as_posix()]=c.sha(PACKAGE/name)
    members={}
    archive=PACKAGE/'source-export.tar'
    with archive.open('xb') as output:
        with tarfile.open(fileobj=output,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for name,h in sorted(files.items()):
                p=REPO/name;assert c.sha(p)==h
                info=tar.gettarinfo(str(p),arcname=name)
                info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
                with p.open('rb') as stream:tar.addfile(info,stream)
                members[name]={'sha256':h,'bytes':p.stat().st_size}
    from preserve import verify_tar
    verify_tar(archive,members)
    c.write(PACKAGE/'SOURCE-TRANSPORT.json',{'sha256':c.sha(archive),'bytes':archive.stat().st_size,
             'members':members,'research_payloads_included':0,'execution_authorized':False})
    print(c.json.dumps({'manifest':c.sha(PACKAGE/'SOURCE-MANIFEST.json'),'archive':c.sha(archive),'bytes':archive.stat().st_size,'members':len(members),'run':template['run']}))

if __name__=='__main__':main()
