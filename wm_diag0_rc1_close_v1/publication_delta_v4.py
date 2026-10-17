"""Publish and preserve only new source/evidence delta; old source ZIP untouched."""
import hashlib,json,os,subprocess,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .freeze_v2 import EVIDENCE
from wm_diag0_preflight_v1.preserve import volume
BRANCH='world-model-diagnostic-preparation-20261004'
def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.whitespace=cr-at-eol,-blank-at-eof',*args],cwd=ROOT,timeout=30)
def reviewed_additions():
    review=json.loads((DOC/'REVIEW-002.json').read_text());result={}
    for name,want in review['new_members'].items():
        p=EVIDENCE[name[len('final_evidence/'):]] if name.startswith('final_evidence/') else ROOT/name;raw=p.read_bytes()
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=want:raise ValueError('exact newly frozen source '+name)
        result[name]=raw
    return result
def main():
    if (DOC/'PUBLICATION-DELTA-004.started.json').exists():raise FileExistsError('exclusive source delta publication')
    parent=json.loads((DOC/'SSD-VERIFIED-001.json').read_text());review=json.loads((DOC/'REVIEW-002.json').read_text())
    if identity(parent['archive'])!=parent['whole'] or git('rev-parse','HEAD').decode().strip()!=parent['source_commit']:raise ValueError('completed source predecessor unchanged; never recopy')
    reviewed_additions();names=[]
    for package in ('wm_diag0_rc1_close_v1','wm_diag0_rc1_final_v1','wm_diag0_rc1_final_v2'):names.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/package).glob('*.py'))
    names.extend(p.relative_to(ROOT).as_posix() for p in DOC.rglob('*') if p.is_file() and p.suffix not in ('.stderr',))
    names=sorted(set(names));members={n:identity(ROOT/n) for n in names}
    delta={n:x for n,x in members.items() if parent['members'].get(n)!=x}
    if any(n in parent['members'] for n in delta):raise ValueError('predecessor source/evidence bytes may not change')
    v=volume();write_new(DOC/'PUBLICATION-DELTA-004.started.json',{'parent':identity(DOC/'SSD-VERIFIED-001.json'),'contract':review['contract'],'delta_members':delta})
    git('add','--',*delta);git('diff','--cached','--check','--',*delta)
    git('commit','--only','-m','Complete forecast-correct RC1 preservation and native final SSD release','--',*delta)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full remote source delta hash')
    payload={n:git('show',commit+':'+n) for n in delta}
    for n,raw in payload.items():
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=delta[n]:raise ValueError('published raw delta identity')
    payload['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':delta,'parent_source_commit':parent['source_commit'],'parent_source_SSD_whole':parent['whole'],'contract':review['contract']},sort_keys=True,separators=(',',':')).encode()
    dest=Path(parent['archive']).parent;path=dest/('finalizer-delta-'+commit+'.zip')
    with path.open('xb') as out:
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as z:
            for n,raw in sorted(payload.items()):z.writestr(n,raw)
        out.flush();os.fsync(out.fileno())
    whole=identity(path)
    with zipfile.ZipFile(path) as z:
        if len(z.namelist())!=len(payload) or set(z.namelist())!=set(payload):raise ValueError('source delta all members')
        for n,raw in payload.items():
            if hashlib.sha256(z.read(n)).digest()!=hashlib.sha256(raw).digest():raise ValueError('source delta member readback')
    if identity(path)!=whole:raise ValueError('source delta whole readback')
    result={'status':'FINALIZER_SOURCE_PUBLISHED_FULL_REMOTE_AND_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
        'archive':str(path),'whole':whole,'members':members,'verified_delta_members':len(payload),'volume':v,'contract':review['contract'],
        'publication_anchor':json.loads((DOC/'FINAL-CONTRACT-002.json').read_text())['rc1_final']['publication_anchor'],
        'verified_parent_source_SSD':{'archive':parent['archive'],'whole':parent['whole'],'source_commit':parent['source_commit']},'actual_study_SSD_gate':False,'old_source_package_recopied':False}
    write_new(DOC/'SSD-VERIFIED-002.json',result);write_new(dest/'SSD-VERIFIED-002.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='members'}))
if __name__=='__main__':main()
