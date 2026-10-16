"""Diagnosed whitespace-only publication resumption; never rerun old publisher."""
import base64,json,os,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .publication import git,BRANCH,volume,digest,verify

def main():
    original='wm_diag0_rc1_completion_v1/local.py'
    pre=json.loads((DOC/'failures/LOCAL-V1-PREIMAGE.json').read_text())
    if identity(ROOT/original)!={'bytes':pre['bytes'],'sha256':pre['sha256']}:raise ValueError('preserved original V1 source changed')
    fail=json.loads((DOC/'LOCAL-BUDGETPUBLISH001.json').read_text())
    if fail['status']!='CHILD_NONZERO' or fail['returncode']!=1 or "git('diff','--cached','--check'" not in fail['stdout']:raise ValueError('exact diagnosed precommit publication failure')
    if git('rev-parse','HEAD').decode().strip()!='27ca345933fcb4eef3e5a9fc5769a2a8201523f0':raise ValueError('commit state changed; authenticate instead of duplicating')
    if os.name!='nt' or git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('native exact branch')
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-completion-budget-v1-20261016')
    if dest.exists() or (DOC/'SSD-VERIFIED-001.json').exists() or (DOC/'PUBLICATION-RESUME-001.started.json').exists():raise FileExistsError('preserve prior publication/SSD attempt; no repeated package')
    if not (DOC/'ARTIFICIAL-004.json').exists():raise ValueError('mechanical V2 regression required')
    names=[str(p.relative_to(ROOT)).replace('\\','/') for p in sorted((ROOT/'wm_diag0_rc1_completion_v1').glob('*.py')) if p.name!='local.py']
    docs=('AUTHORITY.json','ACTIVATION.json','BASELINE.json','LOCAL-BOOTSTRAP.json','ARTIFICIAL-001.json','ARTIFICIAL-002.json','ARTIFICIAL-003.json','ARTIFICIAL-004.json',
          'REVIEW-001.txt','REVIEW-002.txt','SOURCE-MANIFEST-001.json','failures/LOCAL-V1-PREIMAGE.json')
    names += [str((DOC/n).relative_to(ROOT)).replace('\\','/') for n in docs]
    members={n:identity(ROOT/n) for n in names}
    if sum(x['bytes'] for x in members.values())>1000000:raise ValueError('small reviewed source only')
    write_new(DOC/'SOURCE-MANIFEST-002.json',{'members':members,'supersedes_for_active_source':'SOURCE-MANIFEST-001.json','old_source_and_failed_attempt_retained':True,'old_packages_or_models_recopied':0})
    names.append(str((DOC/'SOURCE-MANIFEST-002.json').relative_to(ROOT)).replace('\\','/'))
    write_new(DOC/'PUBLICATION-RESUME-001.started.json',{'diagnosis':'only old local.py trailing whitespace, before any commit/push/SSD','paths':names,'source_manifest':identity(DOC/'SOURCE-MANIFEST-002.json')})
    # Only unstage our own newly added historical V1 path, after authenticating
    # its exact staged bytes. Its file and inert exact preimage are preserved.
    if digest(git('show',':'+original))!={'bytes':pre['bytes'],'sha256':pre['sha256']}:raise ValueError('staged V1 overlaps another change')
    git('rm','--cached','--',original)
    git('add','--',*names);git('diff','--cached','--check','--',*names)
    git('commit','--only','-m','Activate approved bounded RC1 completion and compact technical monitoring','--',*names)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full remote commit identity')
    blobs={n:git('show',commit+':'+n) for n in names}
    for n,x in members.items():
        if digest(blobs[n])!=x or identity(ROOT/n)!=x:raise ValueError('reviewed working/published bytes changed')
    v=volume();dest.mkdir(exist_ok=False)
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()},'old_packages_or_models_recopied':0},sort_keys=True).encode()
    path=dest/('completion-source-'+commit+'.zip')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as z:
            for n,b in sorted(blobs.items()):z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(path);verify(path,{n:digest(b) for n,b in blobs.items()})
    if identity(path)!=whole:raise ValueError('stable source whole')
    result={'status':'COMPLETION_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,'archive':str(path),
            'whole':whole,'verified_members':len(blobs),'volume':v,'working_source_members':members,'old_packages_or_models_recopied':0,
            'publication_resumed_after_diagnosis_not_retried':True,'active_runner':'wm_diag0_rc1_completion_v1.local_v2',
            'final_study_acceptance_or_SSD_gate_passed':False,'research_controller_changed':False}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(dest/'SSD-VERIFIED-001.json'):raise ValueError('matching host/SSD receipt')
    print(json.dumps({k:v for k,v in result.items() if k!='working_source_members'}))

if __name__=='__main__':main()
