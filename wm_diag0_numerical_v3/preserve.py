"""Only this new source/validation package; native Windows SSD verification."""
import json,os,sys,zipfile
from pathlib import Path
from .common import *
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def published():
    volume();r=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=r['source_commit']:raise ValueError('published full hash')
    if identity(r['archive'])!=r['whole'] or identity(DOC/'VALIDATION-CONTRACT.json')!=r['contract']:raise ValueError('preserved exact package')
    from .prepare import additions
    c=json.loads((DOC/'VALIDATION-CONTRACT.json').read_text())
    for n,b in additions().items():
        if digest(b)!=c['staged_members'][n]:raise ValueError('frozen local additions changed')
    return r

def main():
    if os.name!='nt':raise ValueError('native Windows preservation')
    commit=sys.argv[1]
    if git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('full published source hash')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_numerical_v3',DOCREL).decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>1_000_000 or any(n.endswith(('.pth','.ckpt','.sif')) for n in names):raise ValueError('new small source only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()}},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-numerical-validation-v3-20261016');dest.mkdir(exist_ok=False)
    archive=dest/('validation-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    row={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,'archive':str(archive),'whole':identity(archive),
         'contract':identity(DOC/'VALIDATION-CONTRACT.json'),'members':len(blobs),'volume':v,'old_packages_recopied':0}
    write_new(DOC/'SSD-VERIFIED-001.json',row);write_new(dest/'SSD-VERIFIED-001.json',row);print(json.dumps(row))

if __name__=='__main__':main()
