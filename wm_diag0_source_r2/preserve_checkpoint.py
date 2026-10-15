"""Preserve one compact NOT-LAUNCH-READY source checkpoint, never old archives."""
import hashlib,json,os,sys,zipfile
from pathlib import Path
from .common import ROOT,DOC,DOCREL,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest
from wm_diag0_native_v3.preserve import verify


def main():
    commit=sys.argv[1]
    if len(commit)!=40 or git('rev-parse','HEAD').decode().strip()!=commit:raise ValueError('exact source commit')
    remote=git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]
    if remote!=commit:raise ValueError('full remote hash')
    blocked=json.loads((DOC/'BLOCKED-001.json').read_text())
    if blocked['status']!='BLOCKED_PHYSICAL_FULL_FUTURE_RESERVATION':raise ValueError('explicit not-ready state')
    v=volume()
    paths=['wm_diag0_source_r2','wm_diag0_campaign_v4',DOCREL,
           'docs/world-model-diagnostic-a2-campaign-v4-20261015',
           'docs/world-model-diagnostic-a2-native-v3-20261015/LOCAL-SOURCER2']
    names=git('ls-tree','-r','--name-only',commit,'--',*paths).decode().splitlines()
    blobs={n:git('show',commit+':'+n) for n in names}
    if not blobs or any('/delivery/' in n or n.endswith(('.pth','.ckpt','.so','.dll')) for n in blobs):raise ValueError('compact source/documentation allowlist')
    if sum(map(len,blobs.values()))>3_000_000:raise ValueError('3MB small checkpoint ceiling')
    for n,b in blobs.items():
        if n.endswith('.py'):compile(b,n,'exec',dont_inherit=True)
    members={n:digest(b) for n,b in blobs.items()}
    manifest={'source_commit':commit,'full_remote_hash':remote,'status':'INCOMPLETE_DRAFT_NOT_LAUNCH_READY',
              'members':members,'original_scientific_protocol_unchanged':True,'new_jobs_submitted_by_R2':0,
              'previous_archives_recopied':0,'includes_model_weights':False}
    blobs['PACKAGE-MEMBERS.json']=json.dumps(manifest,sort_keys=True,indent=2).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-source-r2-20261015');dest.mkdir(exist_ok=True)
    archive=dest/('blocked-preparation-'+commit+'.zip')
    with archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(archive,{n:digest(b) for n,b in blobs.items()})
    result={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
            'archive':str(archive),'whole':identity(archive),'members_verified':len(blobs),'volume':v,
            'readiness':'BLOCKED_PHYSICAL_FULL_FUTURE_RESERVATION','all_prior_packages_recopied':0,
            'research_checkpoint_loads_or_jobs':0}
    write_new(DOC/'SSD-VERIFIED-001.json',result)
    write_new(dest/'SSD-VERIFIED-001.json',result)
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__=='__main__':main()
