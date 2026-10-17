"""One finalizer source delta commit/push and native SSD whole/member backup."""
import hashlib,json,os,subprocess,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .freeze import EVIDENCE,additions
from wm_diag0_preflight_v1.preserve import volume
BRANCH='world-model-diagnostic-preparation-20261004'
def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol',*args],cwd=ROOT,timeout=30)

def reviewed_additions():
    review=json.loads((DOC/'REVIEW-001.json').read_text());result={}
    for name,want in review['new_members'].items():
        path=EVIDENCE[name[len('final_evidence/'):]] if name.startswith('final_evidence/') else ROOT/name
        raw=path.read_bytes()
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=want:raise ValueError('frozen reviewed source changed '+name)
        result[name]=raw
    return result

def main():
    started=DOC/'PUBLICATION-001.started.json';dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-final-close-v1-20261017')
    if started.exists() or dest.exists():raise FileExistsError('exclusive publication; reconcile, never recopy')
    review=json.loads((DOC/'REVIEW-001.json').read_text())
    if review['status']!='RECOVERY_FINAL_CPU_SOURCE_AND_CONTRACT_INDEPENDENT_PARENT_REVIEW_PASSED' or identity(DOC/'FINAL-CONTRACT.json')!=review['contract']:raise ValueError('reviewed exact frozen contract')
    for name,want in review['new_members'].items():
        raw=reviewed_additions()[name]
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=want:raise ValueError('reviewed final source changed')
    selected=[]
    for package in ('wm_diag0_rc1_close_v1','wm_diag0_rc1_final_v1','wm_diag0_rc1_final_v2'):
        selected.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/package).glob('*.py'))
    selected.extend(p.relative_to(ROOT).as_posix() for p in DOC.glob('*.json'))
    selected+=['docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/CONTINUATION-018.txt']
    selected=sorted(set(selected));members={n:identity(ROOT/n) for n in selected}
    if git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('exact branch')
    v=volume();write_new(started,{'members':members,'contract':review['contract'],'source_only':True,'actual_final_SSD_gate':False})
    git('add','--',*selected);git('diff','--cached','--check','--',*selected)
    git('commit','--only','-m','Freeze recovery-aware RC1 final analysis, independent validation and preservation workflow','--',*selected)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full remote source hash')
    payload={n:git('show',commit+':'+n) for n in selected}
    for n,raw in payload.items():
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=members[n]:raise ValueError('published source bytes')
    payload['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':members,'contract':review['contract'],'old_packages_or_models_recopied':False},sort_keys=True,separators=(',',':')).encode()
    dest.mkdir(exist_ok=False);path=dest/('finalizer-source-'+commit+'.zip')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as z:
            for name,raw in sorted(payload.items()):z.writestr(name,raw)
        f.flush();os.fsync(f.fileno())
    whole=identity(path)
    with zipfile.ZipFile(path) as z:
        if set(z.namelist())!=set(payload) or len(z.namelist())!=len(payload):raise ValueError('every source member')
        for name,raw in payload.items():
            if hashlib.sha256(z.read(name)).digest()!=hashlib.sha256(raw).digest():raise ValueError('source SSD every-member readback')
    if identity(path)!=whole:raise ValueError('source SSD whole readback')
    result={'status':'FINALIZER_SOURCE_PUBLISHED_FULL_REMOTE_AND_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
        'archive':str(path),'whole':whole,'members':members,'verified_members':len(payload),'volume':v,'contract':review['contract'],
        'publication_anchor':json.loads((DOC/'FINAL-CONTRACT.json').read_text())['rc1_final']['publication_anchor'],'actual_study_SSD_gate':False}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='members'}))
if __name__=='__main__':main()
