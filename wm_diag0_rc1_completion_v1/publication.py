"""One new reviewed source/authority package, never a historical recopy."""
import json,os,subprocess,sys,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from wm_diag0_preflight_v1.preserve import volume,digest
from wm_diag0_native_v3.preserve import verify

BRANCH='world-model-diagnostic-preparation-20261004'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30)

def main():
    if os.name!='nt' or git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('exact native Windows work branch')
    if any((DOC/n).exists() for n in ('PUBLICATION-001.started.json','SSD-VERIFIED-001.json','SOURCE-MANIFEST-001.json')):raise FileExistsError('publication already started/ambiguous; authenticate, no recopy')
    for n in ('ARTIFICIAL-001.json','ARTIFICIAL-002.json','ARTIFICIAL-003.json','REVIEW-001.txt'):
        if not (DOC/n).is_file():raise ValueError('review and targeted tests required')
    names=[str(p.relative_to(ROOT)).replace('\\','/') for p in sorted((ROOT/'wm_diag0_rc1_completion_v1').glob('*.py'))]
    names += [str((DOC/n).relative_to(ROOT)).replace('\\','/') for n in ('AUTHORITY.json','ACTIVATION.json','BASELINE.json','LOCAL-BOOTSTRAP.json','ARTIFICIAL-001.json','ARTIFICIAL-002.json','ARTIFICIAL-003.json','REVIEW-001.txt')]
    members={n:identity(ROOT/n) for n in names}
    if sum(x['bytes'] for x in members.values())>1000000:raise ValueError('new compact reviewed source only')
    write_new(DOC/'SOURCE-MANIFEST-001.json',{'members':members,'old_source_packages_models_private_browser_captures_copied':0,'research_controller_changed':False})
    names.append(str((DOC/'SOURCE-MANIFEST-001.json').relative_to(ROOT)).replace('\\','/'))
    write_new(DOC/'PUBLICATION-001.started.json',{'reviewed_paths':names,'source_manifest':identity(DOC/'SOURCE-MANIFEST-001.json')})
    git('add','--',*names);git('diff','--cached','--check','--',*names)
    git('commit','--only','-m','Bound RC1 completion operations under approved 35700-second cap','--',*names)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full remote commit mismatch; authenticate, no repeated commit')
    blobs={n:git('show',commit+':'+n) for n in names}
    for n,x in members.items():
        if digest(blobs[n])!=x or identity(ROOT/n)!=x:raise ValueError('reviewed/published working bytes changed')
    v=volume();dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-completion-budget-v1-20261016');dest.mkdir(exist_ok=False)
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()},'old_packages_or_models_recopied':0},sort_keys=True).encode()
    path=dest/('completion-source-'+commit+'.zip')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as z:
            for n,b in sorted(blobs.items()):z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(path);verify(path,{n:digest(b) for n,b in blobs.items()})
    if identity(path)!=whole:raise ValueError('source SSD whole changed')
    result={'status':'COMPLETION_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
            'archive':str(path),'whole':whole,'verified_members':len(blobs),'volume':v,'working_source_members':members,
            'old_packages_or_models_recopied':0,'final_study_acceptance_or_SSD_gate_passed':False,'research_controller_changed':False}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(dest/'SSD-VERIFIED-001.json'):raise ValueError('matching source preservation receipts')
    print(json.dumps({k:v for k,v in result.items() if k!='working_source_members'}))

if __name__=='__main__':main()
