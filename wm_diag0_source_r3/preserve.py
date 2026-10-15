"""Exactly one new compact source/authority/contract package, native SSD."""
import json,os,sys,zipfile
from pathlib import Path
from .common import ROOT,DOC,DOCREL,R2,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def published():
    v=volume();r=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if r['status']!='WHOLE_AND_EVERY_MEMBER_VERIFIED' or identity(DOC/'CONTRACT.json')!=r['contract']:raise ValueError('preserved exact R3 contract')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=r['source_commit']:raise ValueError('full remote hash')
    if identity(r['archive'])!=r['whole']:raise ValueError('preserved R3 source archive')
    return r

def main():
    commit=sys.argv[1]
    if len(commit)!=40 or git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('published full source hash')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_source_r3',DOCREL,'wm_diag0_source_r2/entry.py','wm_diag0_source_r2/writer.py','wm_diag0_source_r2/__init__.py').decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    for n,b in blobs.items():
        if n.endswith('.py'):compile(b,n,'exec',dont_inherit=True)
    if sum(map(len,blobs.values()))>1000000 or any(n.endswith(('.pth','.ckpt','.sif')) for n in blobs):raise ValueError('small source only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()},'old_archives_or_models_recopied':0},sort_keys=True,indent=2).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-source-r3-20261015');dest.mkdir(exist_ok=True)
    archive=dest/('source-r3-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    result={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,'archive':str(archive),
        'whole':identity(archive),'contract':identity(DOC/'CONTRACT.json'),'verified_members':len(blobs),'volume':v,'old_packages_recopied':0}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result);print(json.dumps(result))

if __name__=='__main__':main()
