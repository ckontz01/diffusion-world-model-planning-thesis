"""One compact new source/contract package, before any gate submission."""
import json,os,sys,zipfile
from pathlib import Path
from .common import DOC,DOCREL,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def published():
    row=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if identity(row['archive'])!=row['whole'] or identity(DOC/'RC1-CONTRACT.json')!=row['contract']:raise ValueError('preserved exact RC1 package')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=row['remote_full_hash']:raise ValueError('exact published source hash')
    return row

def main():
    if os.name!='nt':raise ValueError('native Windows only')
    commit=sys.argv[1]
    if git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:
        raise ValueError('full remote hash verification')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_rc1_v1',DOCREL).decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>500000 or any(n.endswith(('.pth','.ckpt','.sif','.npy','.png','.jpg','.jpeg')) for n in names):raise ValueError('compact new source/metadata only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()},'old_packages_or_models_recopied':0},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-v1-20261016');dest.mkdir(exist_ok=False)
    archive=dest/('gate-source-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(archive);verify(archive,{n:digest(b) for n,b in blobs.items()})
    if identity(archive)!=whole:raise ValueError('stable whole hash')
    row={'status':'RC1_NEW_SOURCE_WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,
      'archive':str(archive),'whole':whole,'members':len(blobs),'volume':v,'contract':identity(DOC/'RC1-CONTRACT.json'),
      'old_packages_or_models_recopied':0,'research_calls':0,'campaign_ready':False}
    write_new(DOC/'SSD-VERIFIED-001.json',row);write_new(dest/'SSD-VERIFIED-001.json',row);print(json.dumps(row))

if __name__=='__main__':main()
