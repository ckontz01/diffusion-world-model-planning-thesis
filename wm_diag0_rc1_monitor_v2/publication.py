"""Once-only new diagnostic source publication, never recopy old packages."""
import json,os,subprocess,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from wm_diag0_rc1_completion_v1.common import DOC as BUDGET
from wm_diag0_preflight_v1.preserve import volume,digest

BRANCH='world-model-diagnostic-preparation-20261004'
OLD='4f48225abf359eae9597488179c1e496f175f940'


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=15)


def verify(path,members):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(members):raise ValueError('exact new source package member set')
        for n,want in members.items():
            info=z.getinfo(n)
            if info.file_size!=want['bytes'] or digest(z.read(n))!=want:raise ValueError('every published source member read back')


def no_redirect(path):
    p=Path(path)
    for q in (p,)+tuple(p.parents):
        if q.exists() and (q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400):raise ValueError('no SSD source destination redirect')


def main():
    if os.name!='nt' or git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('exact native work branch')
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-monitor-v2-20261016')
    if any((DOC/n).exists() for n in ('PUBLICATION-001.started.json','SOURCE-MANIFEST-001.json','SSD-VERIFIED-001.json')) or dest.exists():raise FileExistsError('no repeated/ambiguous publication or source package')
    if git('rev-parse','HEAD').decode().strip()!=OLD:raise ValueError('unexpected local commit; reconcile instead of duplicate')
    t=json.loads((DOC/'ARTIFICIAL-001.json').read_text());p=json.loads((DOC/'ARTIFICIAL-003.json').read_text())
    if t['status']!='ARTIFICIAL_MONITOR_DIAGNOSTIC_WRAPPER_PASSED' or p['status']!='ARTIFICIAL_MONITOR_LOGICAL_COPY_AND_SOURCE_GUARDS_PASSED':raise ValueError('targeted tests required')
    for n,x in p['sources'].items():
        if identity(ROOT/'wm_diag0_rc1_monitor_v2'/n)!=x:raise ValueError('reviewed new source changed after tests')
    names=[str(q.relative_to(ROOT)).replace('\\','/') for q in sorted((ROOT/'wm_diag0_rc1_monitor_v2').glob('*.py'))]
    names += [str((DOC/n).relative_to(ROOT)).replace('\\','/') for n in ('RECOVERY-CONTRACT-001.json','REVIEW-001.txt','ARTIFICIAL-001.json','ARTIFICIAL-002.json','ARTIFICIAL-003.json','source-preimages/compact-before-logical-copy-001.json','source-preimages/publication-before-final-guard-001.json')]
    members={n:identity(ROOT/n) for n in names}
    if sum(x['bytes'] for x in members.values())>500000:raise ValueError('small new source-only reservation')
    old=json.loads((BUDGET/'SSD-VERIFIED-001.json').read_text())
    if old['source_commit']!=OLD or old['whole']!={'bytes':155068,'sha256':'2c6149eb3729182c906ab3c776efe0ba368b2ceca1335e54e7785b08ad43aa83'}:raise ValueError('old preserved dependency reference unchanged, never recopy')
    # Required SSD availability before commit/push as well as before writing.
    v=volume();no_redirect(dest)
    write_new(DOC/'SOURCE-MANIFEST-001.json',{'members':members,'original_completion_package':old['whole'],'old_packages_or_models_recopied':0})
    names.append(str((DOC/'SOURCE-MANIFEST-001.json').relative_to(ROOT)).replace('\\','/'))
    write_new(DOC/'PUBLICATION-001.started.json',{'names':names,'source_manifest':identity(DOC/'SOURCE-MANIFEST-001.json'),'old_HEAD':OLD})
    git('add','--',*names);git('diff','--cached','--check','--',*names)
    git('commit','--only','-m','Preserve bounded RC1 observer transport diagnostics without research changes','--',*names)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('exact full remote commit')
    blobs={n:git('show',commit+':'+n) for n in names}
    for n,want in members.items():
        if digest(blobs[n])!=want or identity(ROOT/n)!=want:raise ValueError('reviewed working/published source bytes changed')
    no_redirect(dest);dest.mkdir(exist_ok=False)
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'original_completion_package':old['whole'],
                    'members':{n:digest(b) for n,b in blobs.items()},'old_packages_or_models_recopied':0},sort_keys=True).encode()
    path=dest/('monitor-v2-source-'+commit+'.zip')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as z:
            for n,b in sorted(blobs.items()):z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(path);verify(path,{n:digest(b) for n,b in blobs.items()})
    if identity(path)!=whole:raise ValueError('whole new source package changed')
    result={'status':'MONITOR_V2_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
            'archive':str(path),'whole':whole,'verified_members':len(blobs),'volume':v,'working_source_members':members,
            'original_completion_package':old['whole'],'old_packages_or_models_recopied':0,
            'R003_retried':False,'research_jobs_or_controllers_changed':False,
            'underlying_transport_cause_diagnosed':False,'final_study_gate_passed':False}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(dest/'SSD-VERIFIED-001.json'):raise ValueError('matching host/SSD source receipt')
    print(json.dumps({k:v for k,v in result.items() if k!='working_source_members'}))


if __name__=='__main__':main()
