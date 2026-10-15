"""Publish/SSD-bind one new compact stage package; no historical rearchive."""
import hashlib,json,os,sys,zipfile
from pathlib import Path
from .common import DOC,DOCREL,ROOT,identity,write_new
from wm_diag0_native_v3.common import DOC as OLD_DOC
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def published(label):
    row=json.loads((DOC/label/'SSD-VERIFIED-001.json').read_text())
    if row['status']!='WHOLE_AND_EVERY_MEMBER_VERIFIED' or identity(DOC/label/'CONTRACT.json')!=row['contract']:raise ValueError('new source preservation')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=row['source_commit']:raise ValueError('full remote tip')
    if identity(row['archive'])!=row['whole']:raise ValueError('new source archive changed')
    base=json.loads((OLD_DOC/'SSD-VERIFIED-001.json').read_text())
    if identity(base['renderer_package']['archive'])!=base['renderer_package']['whole']:raise ValueError('renderer preservation')
    volume();return row

def main():
    label,commit=sys.argv[1:3]
    if label not in ('source-import-r1','campaign'):raise ValueError('versioned stage')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('published full hash')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_campaign_v4',DOCREL).decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    if any('/delivery/' in n or n.endswith(('.pth','.ckpt','.so')) for n in blobs) or sum(map(len,blobs.values()))>3_000_000:raise ValueError('compact source only')
    meta={'source_commit':commit,'remote_full_hash':commit,'members':{n:digest(b) for n,b in blobs.items()},'previous_packages_not_rearchived':True}
    blobs['PACKAGE-MEMBERS.json']=json.dumps(meta,sort_keys=True,indent=2).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-campaign-v4-20261015');dest.mkdir(exist_ok=True)
    archive=dest/(label+'-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    result={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,
            'archive':str(archive),'whole':identity(archive),'verified_members':len(blobs),'volume':v,
            'contract':identity(DOC/label/'CONTRACT.json'),'previous_large_packages_recopied':0}
    write_new(DOC/label/'SSD-VERIFIED-001.json',result);write_new(dest/(label+'-SSD-VERIFIED-001.json'),result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
