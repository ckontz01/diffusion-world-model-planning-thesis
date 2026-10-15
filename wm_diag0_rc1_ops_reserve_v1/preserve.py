"""Final small operational-bound source/activation only; no original recopy."""
import json,os,sys,zipfile
from pathlib import Path
from .runner import DOC
from wm_diag0_rc1_v1.common import ROOT,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def main():
    commit=sys.argv[1]
    if os.name!='nt' or git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('full remote identity')
    v=volume();rel=str(DOC.relative_to(ROOT)).replace('\\','/')
    names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_rc1_ops_reserve_v1',rel).decode().splitlines();blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>50000:raise ValueError('small source/activation only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()}},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-ops-reserve-v1-20261016');dest.mkdir(exist_ok=False);p=dest/('ops-source-'+commit+'.zip')
    with p.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(p);verify(p,{n:digest(b) for n,b in blobs.items()})
    if identity(p)!=whole:raise ValueError('stable whole')
    r={'status':'FINAL_OPERATIONAL_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED','source_commit':commit,'archive':str(p),'whole':whole,'members':len(blobs),'volume':v,'old_packages_recopied':0}
    write_new(DOC/'SSD-VERIFIED-001.json',r);write_new(dest/'SSD-VERIFIED-001.json',r);print(json.dumps(r))

if __name__=='__main__':main()
