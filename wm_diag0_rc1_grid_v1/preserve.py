"""Only the new fixed-grid source/contract delta, native Windows SSD."""
import json,os,sys,zipfile
from pathlib import Path
from .common import DOC,DOCREL,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def published():
    r=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if identity(r['archive'])!=r['whole'] or identity(DOC/'GRID-CONTRACT.json')!=r['contract']:raise ValueError('preserved exact new source')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=r['source_commit']:raise ValueError('exact full remote commit')
    return r

def main():
    commit=sys.argv[1]
    if os.name!='nt' or git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('published native Windows source')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_rc1_grid_v1',DOCREL).decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>500000 or any(n.endswith(('.pth','.ckpt','.sif','.npy','.jpg','.png')) for n in names):raise ValueError('compact source/metadata only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()},'original_packages_or_models_recopied':0},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-grid-v1-20261016');dest.mkdir(exist_ok=False);archive=dest/('grid-source-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(archive);verify(archive,{n:digest(b) for n,b in blobs.items()})
    if identity(archive)!=whole:raise ValueError('stable verified whole')
    r={'status':'FIXED_GRID_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'archive':str(archive),'whole':whole,'members':len(blobs),
        'volume':v,'contract':identity(DOC/'GRID-CONTRACT.json'),'old_packages_or_models_recopied':0,'grid_dispatched':False}
    write_new(DOC/'SSD-VERIFIED-001.json',r);write_new(dest/'SSD-VERIFIED-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()


