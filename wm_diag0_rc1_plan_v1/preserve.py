"""Preserve only the new compact plan/review delta, once, after publication."""
import json, os, sys, zipfile
from pathlib import Path
from .inventory import DOC, DOCREL
from wm_diag0_native_v3.common import identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify

def main():
    if os.name!='nt':raise ValueError('native Windows only')
    commit=sys.argv[1]
    if git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:
        raise ValueError('exact full published hash')
    v=volume()
    names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_rc1_plan_v1',DOCREL).decode().splitlines()
    names+=git('ls-tree','-r','--name-only',commit,'--','docs/world-model-diagnostic-a2-native-v3-20261015').decode().splitlines()
    names=sorted(n for n in set(names) if n.startswith(('wm_diag0_rc1_plan_v1/',DOCREL+'/')) or '/LOCAL-RC1PLAN' in n)
    if not any(n.endswith('/PRO-REVIEW-20261016.txt') for n in names):raise ValueError('review record required')
    blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>300000 or any(n.endswith(('.pth','.ckpt','.sif','.npy','.png','.jpg','.jpeg')) for n in names):
        raise ValueError('new compact metadata/code only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'remote_full_hash':commit,
        'members':{n:digest(b) for n,b in blobs.items()},'historical_packages_or_models_recopied':0},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-rc1-final-plan-v1-20261016');dest.mkdir(exist_ok=False)
    archive=dest/('disabled-final-plan-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    whole=identity(archive)
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    if identity(archive)!=whole:raise ValueError('whole identity changed during member verification')
    row={'status':'NEW_PLAN_REVIEW_WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,
        'archive':str(archive),'whole':whole,'members':len(blobs),'volume':v,
        'historical_packages_or_models_recopied':0,'research_calls':0,'campaign_resumed':False}
    write_new(DOC/'SSD-VERIFIED-001.json',row);write_new(dest/'SSD-VERIFIED-001.json',row)
    print(json.dumps(row))

if __name__=='__main__':main()
