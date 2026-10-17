"""Publish only this complete validated study after actual final SSD gate."""
import hashlib,json,os,subprocess,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from wm_diag0_preflight_v1.preserve import volume

BRANCH='world-model-diagnostic-preparation-20261004'
def git(*args):
    return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol,-blank-at-eof',*args],cwd=ROOT,timeout=60)

def git_paths(args,names):
    # Exact NUL-delimited paths over stdin avoid Windows argv limits without
    # broadening the selection or touching unrelated staged/user changes.
    raw=b''.join(name.encode('utf8')+b'\0' for name in names)
    return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol,-blank-at-eof',*args,
        '--pathspec-from-file=-','--pathspec-file-nul'],input=raw,cwd=ROOT,timeout=60)

def main():
    start=DOC/'RESULTS-PUBLICATION-001.started.json'
    if start.exists() or (DOC/'RESULTS-PUBLISHED-001.json').exists():raise FileExistsError('never repeat a publication with ambiguous outcome')
    gate=json.loads((DOC/'FINAL-SSD-VERIFIED.json').read_text());release=json.loads((DOC/'RESULTS-RELEASED.json').read_text())
    ssd=Path(gate['archive']).parent
    if gate['status']!='COMPLETE_STUDY_INDEPENDENT_ACCEPTANCE_AND_FINAL_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_GATE_PASSED' or identity(DOC/'FINAL-SSD-VERIFIED.json')!=identity(ssd/'FINAL-SSD-VERIFIED.json'):raise PermissionError('actual matching whole/every-member final SSD gate')
    if release['final_gate']!=identity(DOC/'FINAL-SSD-VERIFIED.json'):raise PermissionError('scientific release gate binding')
    for name in ('RESULTS','ACCEPTANCE'):
        if identity(DOC/(name+'.json'))!=release[name]:raise ValueError('sealed complete results/acceptance bytes')
    report=DOC/'PRO-RESULTS-HANDOFF.txt'
    if not report.is_file() or report.stat().st_size>200000:raise ValueError('reviewed bounded complete report')
    source=json.loads((DOC/'SSD-VERIFIED-002.json').read_text())
    if git('rev-parse','HEAD').decode().strip()!=source['source_commit'] or git('branch','--show-current').decode().strip()!=BRANCH:raise ValueError('expected unchanged study branch predecessor')
    candidates=[]
    candidates.extend(p for p in DOC.rglob('*') if p.is_file())
    candidates.extend((ROOT/'wm_diag0_rc1_close_v1').glob('*.py'))
    history=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016'
    candidates.extend(p for p in history.iterdir() if p.is_file() and (p.name.startswith('CONTINUATION-') or p.name.startswith('LOCAL-FINAL') or p.name in ('AUTHORITY.json','ACTIVATION.json','BASELINE.json')))
    recovery=ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016'
    candidates.extend(p for p in recovery.iterdir() if p.is_file() and p.suffix in ('.json','.txt'))
    selected=[];ignored=[];native_test_evidence={}
    for p in sorted(set(candidates)):
        name=p.relative_to(ROOT).as_posix()
        limit=38000000 if p==DOC/'RESULTS.json' else 2000000
        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400 or p.stat().st_size>limit:raise ValueError('bounded ordinary final publication evidence '+name)
        test_prefix=DOC.relative_to(ROOT).as_posix()+'/artificial-results-handoff-001/'
        if name.startswith(test_prefix):native_test_evidence[name[len(test_prefix):]]=p
        # Retain this deliberately synthetic nested Git repository as opaque
        # SSD test evidence, not as a submodule or imported project history.
        fixture_prefix=DOC.relative_to(ROOT).as_posix()+'/artificial-results-handoff-001/git-fixture/'
        if name.startswith(fixture_prefix):
            ignored.append({'path':name,'identity':identity(p),'reason':'synthetic nested Git fixture retained whole in separate new SSD test-evidence package'})
            continue
        test=subprocess.run(['git','check-ignore','-q','--',name],cwd=ROOT)
        if test.returncode==0:
            ignored.append({'path':name,'identity':identity(p)});continue
        if test.returncode!=1:raise ValueError('Git ignore check failed')
        selected.append(name)
    members={n:identity(ROOT/n) for n in selected}
    write_new(start,{'status':'FINAL_SSD_GATE_PASSED_EXPLICIT_STUDY_PATH_PUBLICATION_STARTED','final_gate':identity(DOC/'FINAL-SSD-VERIFIED.json'),
        'sealed_results':release['RESULTS'],'report':identity(report),'parent_commit':source['source_commit'],'members':members,
        'repository_ignored_artificial_or_transport_files_retained_not_force_added':ignored},limit=250000)
    selected.append(start.relative_to(ROOT).as_posix());members[selected[-1]]=identity(start)
    git_paths(['add'],selected)
    for offset in range(0,len(selected),20):git('diff','--cached','--check','--',*selected[offset:offset+20])
    git_paths(['commit','--only','-m','Publish complete independently validated WM-DIAG0 RC1 results after final SSD verification'],selected)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full published remote hash')
    essential=['RESULTS.json','ACCEPTANCE.json','PRO-RESULTS-HANDOFF.txt','FINAL-SSD-VERIFIED.json','RESULTS-RELEASED.json','TERMINALCPU001.json']
    payload={}
    for name in essential:
        path=(DOC/name).relative_to(ROOT).as_posix();raw=git('show',commit+':'+path)
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=identity(DOC/name):raise ValueError('actual published complete report bytes')
        payload[name]=raw
    manifest={'source_commit':commit,'remote_full_hash':remote,'final_gate':identity(DOC/'FINAL-SSD-VERIFIED.json'),
        'members':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in payload.items()}}
    payload['PACKAGE-MEMBERS.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    volume();archive=ssd/('pro-results-'+commit+'.zip')
    with archive.open('xb') as out:
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as package:
            for name,raw in sorted(payload.items()):package.writestr(name,raw)
        out.flush();os.fsync(out.fileno())
    with zipfile.ZipFile(archive) as package:
        if len(package.namelist())!=len(payload) or set(package.namelist())!=set(payload):raise ValueError('complete small report package members')
        for name,raw in payload.items():
            if package.read(name)!=raw:raise ValueError('native SSD report every-member readback')
    test_archive=ssd/('postarchive-native-test-evidence-'+commit+'.zip')
    with test_archive.open('xb') as out:
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as package:
            for name,path in sorted(native_test_evidence.items()):package.writestr(name,path.read_bytes())
        out.flush();os.fsync(out.fileno())
    with zipfile.ZipFile(test_archive) as package:
        if len(package.namelist())!=len(native_test_evidence) or set(package.namelist())!=set(native_test_evidence):raise ValueError('all postarchive artificial evidence retained')
        for name,path in native_test_evidence.items():
            if {'bytes':len(package.read(name)),'sha256':hashlib.sha256(package.read(name)).hexdigest()}!=identity(path):raise ValueError('postarchive native test every-member SSD readback')
    result={'status':'COMPLETE_VALIDATED_RESULTS_PUBLISHED_GITHUB_FULL_REMOTE_AND_SMALL_SSD_REPORT_VERIFIED',
        'commit':commit,'remote_full_hash':remote,'branch':BRANCH,'report_path':report.relative_to(ROOT).as_posix(),
        'results_path':(DOC/'RESULTS.json').relative_to(ROOT).as_posix(),'final_study_SSD_gate':identity(DOC/'FINAL-SSD-VERIFIED.json'),
        'small_report_SSD_archive':str(archive),'small_report_SSD_whole':identity(archive),'small_report_verified_members':len(payload),
        'postarchive_native_test_SSD_archive':str(test_archive),'postarchive_native_test_whole':identity(test_archive),'postarchive_native_test_members':len(native_test_evidence),
        'full_study_archive_recopied':False,'unrelated_work_committed':False}
    write_new(DOC/'RESULTS-PUBLISHED-001.json',result);write_new(ssd/'RESULTS-PUBLISHED-001.json',result)
    print(json.dumps(result))

if __name__=='__main__':main()
