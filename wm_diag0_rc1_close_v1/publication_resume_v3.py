"""Resume exact precommit formatting stop without altering frozen source bytes."""
import hashlib,json,os,subprocess,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .publication_v2 import reviewed_additions
from wm_diag0_preflight_v1.preserve import volume
BRANCH='world-model-diagnostic-preparation-20261004'
def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol,-blank-at-eof',*args],cwd=ROOT,timeout=30)
def main():
    failure=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/LOCAL-FINALPUBLICATION002.json'
    z=json.loads(failure.read_text());start=json.loads((DOC/'PUBLICATION-001.started.json').read_text())
    if z['status']!='CHILD_NONZERO' or "git('diff','--cached','--check'" not in z['stdout']:raise ValueError('exact publication stop before commit')
    if git('rev-parse','HEAD').decode().strip()!='69f73cd15a799fe19abce352f89c6a3e08feada3':raise ValueError('no unknown commit/push phase')
    if set(git('diff','--cached','--name-only').decode().splitlines())!=set(start['members']):raise ValueError('only authenticated failed publication index paths')
    for name,want in start['members'].items():
        if identity(ROOT/name)!=want:raise ValueError('failed source preimage preserved')
        raw=git('show',':'+name)
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=want:raise ValueError('index source bytes changed')
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-final-close-v1-20261017')
    if dest.exists() or (DOC/'PUBLICATION-RESUME-003.started.json').exists() or (DOC/'SSD-VERIFIED-001.json').exists():raise FileExistsError('never duplicate publication or SSD package')
    # Old files intentionally retain their exact tested trailing blank lines.
    # The command-local whitespace policy ignores only that harmless formatting;
    # no persistent config or historical source/contract byte is modified.
    names=sorted(set(start['members'])|{Path(__file__).relative_to(ROOT).as_posix(),'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/CONTINUATION-019.txt'})
    members={n:identity(ROOT/n) for n in names};v=volume()
    write_new(DOC/'PUBLICATION-RESUME-003.started.json',{'old_failure':identity(failure),'old_start':identity(DOC/'PUBLICATION-001.started.json'),
        'members':members,'contract':start['contract'],'source_bytes_edited':False,'persistent_config_changed':False})
    git('add','--',*names);git('diff','--cached','--check','--',*names)
    git('commit','--only','-m','Freeze independently validated recovery-aware RC1 final analysis and preservation','--',*names)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full published remote hash')
    payload={n:git('show',commit+':'+n) for n in names}
    for n,raw in payload.items():
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=members[n]:raise ValueError('published source byte identity')
    payload['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':members,'contract':start['contract'],'no_old_package_or_model_copy':True},sort_keys=True,separators=(',',':')).encode()
    dest.mkdir(exist_ok=False);path=dest/('finalizer-source-'+commit+'.zip')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as archive:
            for n,raw in sorted(payload.items()):archive.writestr(n,raw)
        f.flush();os.fsync(f.fileno())
    whole=identity(path)
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist())!=len(payload) or set(archive.namelist())!=set(payload):raise ValueError('exact all source members')
        for n,raw in payload.items():
            if hashlib.sha256(archive.read(n)).digest()!=hashlib.sha256(raw).digest():raise ValueError('source SSD every-member verification')
    if identity(path)!=whole:raise ValueError('source SSD whole verification')
    c=json.loads((DOC/'FINAL-CONTRACT.json').read_text())
    result={'status':'FINALIZER_SOURCE_PUBLISHED_FULL_REMOTE_AND_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
        'archive':str(path),'whole':whole,'members':members,'verified_members':len(payload),'volume':v,'contract':start['contract'],
        'publication_anchor':c['rc1_final']['publication_anchor'],'actual_study_SSD_gate':False,
        'preserved_original_publication_failure':identity(failure),'frozen_source_bytes_changed':False}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='members'}))
if __name__=='__main__':main()
