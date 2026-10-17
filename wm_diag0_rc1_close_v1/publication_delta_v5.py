"""Preserve exact ignored tiny test archive in SSD; honor Git repository policy."""
import hashlib,json,os,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .publication_delta_v4 import git,reviewed_additions,BRANCH
from wm_diag0_preflight_v1.preserve import volume

def main():
    start=DOC/'PUBLICATION-DELTA-005.started.json'
    if start.exists() or (DOC/'SSD-VERIFIED-002.json').exists():raise FileExistsError('exclusive source delta')
    previous=json.loads((ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/LOCAL-FINALPUBLICATIONDELTA004.json').read_text())
    if previous['status']!='CHILD_NONZERO' or 'following paths are ignored' not in previous['stdout']:raise ValueError('saved precommit Git-ignore failure')
    parent=json.loads((DOC/'SSD-VERIFIED-001.json').read_text());review=json.loads((DOC/'REVIEW-002.json').read_text())
    if identity(parent['archive'])!=parent['whole'] or git('rev-parse','HEAD').decode().strip()!=parent['source_commit']:raise ValueError('unchanged completed predecessor')
    reviewed_additions();names=[]
    for package in ('wm_diag0_rc1_close_v1','wm_diag0_rc1_final_v1','wm_diag0_rc1_final_v2'):
        names.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/package).glob('*.py'))
    names.extend(p.relative_to(ROOT).as_posix() for p in DOC.rglob('*') if p.is_file() and p.suffix!='.stderr')
    members={n:identity(ROOT/n) for n in sorted(set(names))};delta={n:x for n,x in members.items() if parent['members'].get(n)!=x}
    if any(n in parent['members'] for n in delta):raise ValueError('never modify preserved predecessor bytes')
    ignored='docs/world-model-diagnostic-rc1-final-close-v1-20261017/artificial-native-finish-001/tiny.tar'
    fixture=json.loads((DOC/'ARTIFICIAL-NATIVE-FINISH-001.json').read_text())
    if delta.get(ignored)!=fixture['tiny_archive']:raise ValueError('exact tested tiny ignored archive')
    selected=[n for n in delta if n!=ignored];v=volume()
    write_new(start,{'contract':review['contract'],'parent':identity(DOC/'SSD-VERIFIED-001.json'),'delta':delta,'Git_ignored_fixture_still_preserved_in_SSD':ignored})
    git('add','--',*selected);git('diff','--cached','--check','--',*selected)
    git('commit','--only','-m','Complete forecast-correct RC1 preservation and native final SSD release','--',*selected)
    commit=git('rev-parse','HEAD').decode().strip();git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    if remote!=commit:raise ValueError('full remote hash')
    payload={n:((ROOT/n).read_bytes() if n==ignored else git('show',commit+':'+n)) for n in delta}
    for n,raw in payload.items():
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=delta[n]:raise ValueError('published delta bytes')
    payload['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':delta,'contract':review['contract'],'parent_source_commit':parent['source_commit'],
        'parent_source_SSD_whole':parent['whole'],'repository_ignored_test_archive_preserved_in_SSD':ignored},sort_keys=True,separators=(',',':')).encode()
    destination=Path(parent['archive']).parent;path=destination/('finalizer-delta-'+commit+'.zip')
    with path.open('xb') as out:
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as archive:
            for name,raw in sorted(payload.items()):archive.writestr(name,raw)
        out.flush();os.fsync(out.fileno())
    whole=identity(path)
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist())!=len(payload) or set(archive.namelist())!=set(payload):raise ValueError('every source delta member')
        for name,raw in payload.items():
            if hashlib.sha256(archive.read(name)).digest()!=hashlib.sha256(raw).digest():raise ValueError('source SSD member readback')
    if identity(path)!=whole:raise ValueError('source SSD whole readback')
    c=json.loads((DOC/'FINAL-CONTRACT-002.json').read_text())
    result={'status':'FINALIZER_SOURCE_PUBLISHED_FULL_REMOTE_AND_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_VERIFIED',
        'source_commit':commit,'remote_full_hash':remote,'archive':str(path),'whole':whole,'members':members,'volume':v,
        'verified_delta_members':len(payload),'contract':review['contract'],'publication_anchor':c['rc1_final']['publication_anchor'],
        'verified_parent_source_SSD':{'archive':parent['archive'],'whole':parent['whole'],'source_commit':parent['source_commit']},
        'repository_ignored_tiny_fixture_preserved_in_SSD_not_force_added':ignored,'actual_study_SSD_gate':False,'old_source_package_recopied':False}
    write_new(DOC/'SSD-VERIFIED-002.json',result);write_new(destination/'SSD-VERIFIED-002.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='members'}))
if __name__=='__main__':main()
