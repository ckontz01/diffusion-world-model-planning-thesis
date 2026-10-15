"""Preserve only the new compact result/review delta, never rearchive source."""
import json,os,sys,zipfile
from pathlib import Path
from .common import *
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def main():
    if os.name!='nt':raise ValueError('native Windows only')
    commit=sys.argv[1]
    if git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('exact remote full hash')
    v=volume();prior=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if identity(prior['archive'])!=prior['whole']:raise ValueError('existing source archive identity')
    with zipfile.ZipFile(prior['archive']) as z:
        existing=json.loads(z.read('PACKAGE-MEMBERS.json'))['members']
    names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_numerical_v3',DOCREL).decode().splitlines()
    blobs={}
    for n in names:
        raw=git('show',commit+':'+n)
        if n in existing:
            if digest(raw)!=existing[n]:raise ValueError('executed source changed')
        else:blobs[n]=raw
    if not blobs or sum(map(len,blobs.values()))>250000:raise ValueError('only new compact review delta')
    manifest={'source_commit':commit,'source_package':prior['whole'],'source_package_commit':prior['source_commit'],
              'members':{n:digest(b) for n,b in blobs.items()},'old_archive_members_recopied':0,'scientific_arrays_copied':0}
    blobs['PACKAGE-MEMBERS.json']=json.dumps(manifest,sort_keys=True).encode()
    dest=Path(prior['archive']).parent;archive=dest/('result-review-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    row={'status':'NEW_REVIEW_DELTA_WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,
         'archive':str(archive),'whole':identity(archive),'members':len(blobs),'volume':v,
         'prior_source_package':prior['whole'],'old_archive_members_recopied':0,'scientific_arrays_copied':0}
    write_new(DOC/'RESULT-REVIEW-SSD-001.json',row);write_new(dest/'RESULT-REVIEW-SSD-001.json',row);print(json.dumps(row))

if __name__=='__main__':main()
