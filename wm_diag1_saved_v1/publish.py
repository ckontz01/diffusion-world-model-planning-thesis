"""Publish frozen new analysis before execution and verify small source SSD ZIP."""
import hashlib,json,os,subprocess,zipfile
from pathlib import Path
from .common import ROOT,DOC,PKG,BRANCH,identity,write_new
from .freeze import payload
from wm_diag0_preflight_v1.preserve import volume

def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol,-blank-at-eof',*args],cwd=ROOT,timeout=40)
def git_paths(args,names):return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol,-blank-at-eof',*args,'--pathspec-from-file=-','--pathspec-file-nul'],input=b''.join(n.encode()+b'\0' for n in names),cwd=ROOT,timeout=40)
def source_files():return sorted(set([p for p in DOC.rglob('*') if p.is_file() and p.name!='operation.lock']+list(PKG.glob('*.py'))))
def zip_verified(path,members):
    with path.open('xb') as stream:
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as z:
            for name,raw in sorted(members.items()):z.writestr(name,raw)
        stream.flush();os.fsync(stream.fileno())
    with zipfile.ZipFile(path) as z:
        if len(z.namelist())!=len(members) or set(z.namelist())!=set(members):raise ValueError('exact small-package membership')
        for name,raw in members.items():
            if z.read(name)!=raw:raise ValueError('small-package every-member readback')
    return identity(path)

def main():
    if (DOC/'SOURCE-PUBLISHED.json').exists() or (DOC/'SOURCE-PUBLICATION.started.json').exists():raise FileExistsError('never duplicate a source publication')
    runtime=payload()
    if sum(map(len,runtime.values()))>8000000:raise ValueError('finite small frozen runtime copy')
    if git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('separate saved-data branch')
    paths=source_files();selected=[];ignored=[];allmembers={p.relative_to(ROOT).as_posix():identity(p) for p in paths}
    if sum(v['bytes'] for v in allmembers.values())>8000000:raise ValueError('small source/spec/test package all logical files')
    for p in paths:
        name=p.relative_to(ROOT).as_posix();check=subprocess.run(['git','check-ignore','-q','--',name],cwd=ROOT)
        if check.returncode==1:selected.append(name)
        elif check.returncode==0:ignored.append(name)
        else:raise ValueError('Git ignore check')
    volume();write_new(DOC/'SOURCE-PUBLICATION.started.json',{'freeze':identity(DOC/'FREEZE.json'),'all_source_test_members':allmembers,'Git_ignored_tiny_numeric_fixtures_preserved_in_SSD':ignored,'new_derived_results_computed':False})
    selected.append((DOC/'SOURCE-PUBLICATION.started.json').relative_to(ROOT).as_posix());git_paths(['add'],selected)
    for i in range(0,len(selected),15):git('diff','--cached','--check','--',*selected[i:i+15])
    git_paths(['commit','--only','-m','Freeze WM-DIAG1 saved-data mechanism analysis before first derived run'],selected)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full pre-run remote commit readback')
    for name in selected:
        if git('show',commit+':'+name)!=(ROOT/name).read_bytes():raise ValueError('exact published raw code/spec/input bytes')
    destination=Path('D:/THESIS-BACKUPS/wm-diag1-saved-20261017');destination.mkdir(parents=True,exist_ok=False)
    members={p.relative_to(ROOT).as_posix():p.read_bytes() for p in paths};members['PACKAGE-MEMBERS.json']=json.dumps({'commit':commit,'freeze':identity(DOC/'FREEZE.json'),'members':allmembers},sort_keys=True).encode()
    archive=destination/('analysis-source-'+commit+'.zip');whole=zip_verified(archive,members)
    receipt={'status':'FROZEN_ANALYSIS_PUBLISHED_FULL_REMOTE_SOURCE_SSD_WHOLE_EVERY_MEMBER_VERIFIED_BEFORE_FIRST_DERIVED_PASS',
        'source_commit':commit,'full_remote_hash':remote,'branch':BRANCH,'freeze':identity(DOC/'FREEZE.json'),'archive':str(archive),'whole':whole,'verified_members':len(members),'source_all_members':allmembers,
        'old_study_archive_recreated_or_copied':False,'new_derived_result_computed':False}
    write_new(DOC/'SOURCE-PUBLISHED.json',receipt);write_new(destination/'SOURCE-PUBLISHED.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_all_members'}))

if __name__=='__main__':main()
