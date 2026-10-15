"""Native Windows preservation of this one new compact decision record."""
import json,os,sys,zipfile
from pathlib import Path
from wm_diag0_native_v3.common import ROOT,write_new,identity
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify
from .check import DOC,DOCREL

def main():
    commit=sys.argv[1]
    if os.name!='nt' or git('rev-parse','HEAD').decode().strip()!=commit or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('native Windows and exact published commit')
    check=json.loads((DOC/'ARITHMETIC-CHECK-001.json').read_text())
    if check['new_inference_authorized'] or check['document']!=identity(DOC/'NUMERICAL-VALIDATION-AMENDMENT.md'):raise ValueError('disabled exact decision record')
    v=volume();names=git('ls-tree','-r','--name-only',commit,'--',DOCREL,'wm_diag0_numerical_amendment_r2',
        'docs/world-model-diagnostic-a2-parity-r1-20261015/REVIEW-REQUEST-RECOVERED-20261015.json',
        'docs/world-model-diagnostic-a2-native-v3-20261015/LOCAL-NUMERICALAMENDMENTCHECK001.json',
        'docs/world-model-diagnostic-a2-native-v3-20261015/LOCAL-NUMERICALAMENDMENTCHECK001.started.json').decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,blobs.values()))>1000000 or any(n.endswith(('.pth','.ckpt','.sif')) for n in names):raise ValueError('compact new record only')
    blobs['PACKAGE-MEMBERS.json']=json.dumps({'source_commit':commit,'members':{n:digest(b) for n,b in blobs.items()},'research_authorized':False},sort_keys=True).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-numerical-validation-r2-20261015');dest.mkdir(exist_ok=False)
    archive=dest/('disabled-amendment-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    r={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,'archive':str(archive),
       'whole':identity(archive),'members':len(blobs),'document':identity(DOC/'NUMERICAL-VALIDATION-AMENDMENT.md'),
       'volume':v,'old_packages_recopied':0,'new_research_execution_authorized':False}
    write_new(DOC/'SSD-VERIFIED-001.json',r);write_new(dest/'SSD-VERIFIED-001.json',r);print(json.dumps(r,indent=2))

if __name__=='__main__':main()
