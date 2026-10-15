import json,os,sys,zipfile
from pathlib import Path
from .common import DOC,DOCREL,BASE,SOURCE_COMMIT,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def published():
    volume();r=json.loads((DOC/'SSD-VERIFIED-001.json').read_text());base=json.loads((BASE/'campaign/SSD-VERIFIED-001.json').read_text())
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=r['source_commit']:raise ValueError('full repair remote hash')
    if identity(DOC/'CONTRACT.json')!=r['contract'] or identity(r['archive'])!=r['whole']:raise ValueError('new repair preservation')
    if base['source_commit']!=SOURCE_COMMIT or identity(base['archive'])!=base['whole']:raise ValueError('unchanged preserved scientific source')
    return r

def main():
    commit=sys.argv[1]
    if git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('full published repair commit')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_submit_r1',DOCREL,
        'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/QOS-DIAGNOSIS-001.json',
        'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/SUBMISSION-RECONCILIATION-001.json',
        'docs/world-model-diagnostic-a2-native-v3-20261015/LOCAL-QOSR1TEST001.json').decode().splitlines();blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>1000000:raise ValueError('one compact source package only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'scientific_source_unchanged':SOURCE_COMMIT,'members':{n:digest(b) for n,b in blobs.items()}},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-campaign-submit-r1-20261015');dest.mkdir(exist_ok=True);archive=dest/('submit-r1-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    r={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,'archive':str(archive),'whole':identity(archive),'contract':identity(DOC/'CONTRACT.json'),'members':len(blobs),'volume':v,'previous_packages_recopied':0}
    write_new(DOC/'SSD-VERIFIED-001.json',r);write_new(dest/'SSD-VERIFIED-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
