"""One new repair delta publication/SSD package; old packages never recopied."""
import json,os,subprocess,zipfile
from .common import *
from wm_diag0_preflight_v1.preserve import volume

BRANCH='world-model-diagnostic-preparation-20261004'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=18)

def main():
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-recovery-r1-20261016')
    if dest.exists() or (DOC/'PUBLICATION-001.started.json').exists():raise FileExistsError('exclusive repair publication, reconcile partials not retry')
    if git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('exact branch')
    review=json.loads((DOC/'REVIEW-001.json').read_text())
    if review['status']!='RECOVERY_FIXED_SCOPE_SOURCE_AND_CONTRACT_REVIEW_PASSED':raise ValueError('review required')
    for n,x in review['sources'].items():
        if identity(ROOT/n)!=x:raise ValueError('reviewed repair source changed')
    if identity(DOC/'GRID-CONTRACT.json')!=review['new_contract']:raise ValueError('reviewed contract')
    selected=['AUTHORITY-001.json','ARTIFICIAL-NATIVE-001.json','BINDING001.started.json','BINDING001.failure.json','BINDING002.json','LINUXTEST001.json','GRID-CONTRACT.json','REVIEW-001.json']
    names=list(review['sources'])+[str((DOC/n).relative_to(ROOT)).replace('\\','/') for n in selected]
    members={n:identity(ROOT/n) for n in names}
    if sum(x['bytes'] for x in members.values())>500000:raise ValueError('bounded new source-only package')
    v=volume()
    for p in (dest,)+tuple(dest.parents):
        if p.exists() and (p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400):raise ValueError('ordinary native SSD destination')
    write_new(DOC/'PUBLICATION-001.started.json',{'members':members,'previous_commit':git('rev-parse','HEAD').decode().strip(),'new_source_only':True})
    git('add','--',*names);git('diff','--cached','--check','--',*names)
    git('commit','--only','-m','Repair RC1 mutable-artifact supervisor and authorize exact failed/unstarted recovery','--',*names)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if commit!=remote:raise ValueError('exact full remote repair commit')
    blobs={n:git('show',commit+':'+n) for n in names}
    for n,x in members.items():
        if digest(blobs[n])!=x or identity(ROOT/n)!=x:raise ValueError('working/published reviewed bytes')
    blobs['PACKAGE-MEMBERS.json']=canonical({'source_commit':commit,'members':members,'old_packages_models_recopied':0})
    dest.mkdir(exist_ok=False);path=dest/('recovery-source-'+commit+'.zip')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as z:
            for n,b in sorted(blobs.items()):z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(path)
    with zipfile.ZipFile(path) as z:
        if set(z.namelist())!=set(blobs) or len(z.namelist())!=len(blobs):raise ValueError('every new member exact')
        for n,b in blobs.items():
            if digest(z.read(n))!=digest(b):raise ValueError('independent SSD member readback')
    if identity(path)!=whole:raise ValueError('whole archive readback changed')
    r={'status':'RECOVERY_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
       'archive':str(path),'whole':whole,'verified_members':len(blobs),'working_source_members':members,
       'contract':identity(DOC/'GRID-CONTRACT.json'),'volume':v,'old_packages_models_recopied':0,'research_dispatched':False}
    write_new(DOC/'SSD-VERIFIED-001.json',r);write_new(dest/'SSD-VERIFIED-001.json',r)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(dest/'SSD-VERIFIED-001.json'):raise ValueError('host/SSD receipt match')
    print(json.dumps({k:v for k,v in r.items() if k!='working_source_members'}))

if __name__=='__main__':main()
