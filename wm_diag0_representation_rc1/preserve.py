"""One new small proposal/review package; do not recopy accepted studies."""
import json,os,sys,zipfile
from pathlib import Path
from .check import DOC,DOCREL
from wm_diag0_native_v3.common import ROOT,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def main():
    if os.name!='nt':raise ValueError('native Windows preservation')
    commit=sys.argv[1]
    if git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('full published hash')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_representation_rc1',DOCREL).decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>250000 or any(n.endswith(('.pth','.ckpt','.sif','.npy','.jpg','.png')) for n in names):raise ValueError('compact new proposal only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()},'old_packages_or_models_recopied':0},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-representation-control-rc1-20261016');dest.mkdir(exist_ok=False)
    archive=dest/('disabled-amendment-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    row={'status':'NEW_PROPOSAL_WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,
         'archive':str(archive),'whole':identity(archive),'members':len(blobs),'volume':v,
         'old_packages_or_models_recopied':0,'scientific_operations':0,'campaign_resumed':False}
    write_new(DOC/'SSD-VERIFIED-001.json',row);write_new(dest/'SSD-VERIFIED-001.json',row);print(json.dumps(row))

if __name__=='__main__':main()
