"""Authenticate completed SSD archives; fix Windows member-name comparison only."""
import hashlib,json,os,sys,zipfile
from pathlib import Path
from wm_diag0_native_v3.common import ROOT,DOC,DOCREL,identity,write_new
from wm_diag0_native_v3.preserve import verify
from wm_diag0_preflight_v1.preserve import git,volume,digest

SOURCE='98ca0ae0a98cbdeb70a1e4c83c5592ac1b39ec82'

def main():
    commit=sys.argv[1]
    if os.name!='nt' or git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=commit:raise ValueError('native Windows/full remote hash')
    volume();dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-native-v3-20261015')
    names=git('ls-tree','-r','--name-only',SOURCE,'--','wm_diag0_native_v3',DOCREL).decode().splitlines()
    blobs={n:git('show',SOURCE+':'+n) for n in names}
    # The new publication adds only this repair and its receipt contract. Prove
    # every original source/package byte remains identical in the new tip.
    for n,b in blobs.items():
        if git('show',commit+':'+n)!=b:raise ValueError('source/package changed')
    members={n:digest(b) for n,b in blobs.items()}
    with zipfile.ZipFile(dest/('native-v3-'+SOURCE+'.zip')) as z:
        package_manifest=z.read('PACKAGE-MEMBERS.json')
        if json.loads(package_manifest)['members']!=members:raise ValueError('source manifest vs immutable Git bytes')
    members['PACKAGE-MEMBERS.json']=digest(package_manifest)
    source_archive=dest/('native-v3-'+SOURCE+'.zip');verify(source_archive,members)
    runtime_members={str(p.relative_to(DOC/'delivery')).replace('\\','/'):identity(p) for p in sorted((DOC/'delivery').rglob('*')) if p.is_file()}
    runtime_archive=dest/'renderer-signed-packages-and-all-preparation-evidence.zip';verify(runtime_archive,runtime_members)
    repair_names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_campaign_v4','docs/world-model-diagnostic-a2-campaign-v4-20261015').decode().splitlines()
    if len(repair_names)>10:raise ValueError('this receipt-only publication must precede campaign additions')
    repair_blobs={n:git('show',commit+':'+n) for n in repair_names}
    repair_archive=dest/('preservation-receipt-r1-'+commit+'.zip')
    with repair_archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in repair_blobs.items():z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(repair_archive,{n:digest(b) for n,b in repair_blobs.items()})
    result={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':commit,
            'archive_source_commit':SOURCE,'source_closure_byte_equivalence_verified':True,
            'mapping':'archive identifies98ca0ae source; current published tip adds receipt repair only, with every archived source byte unchanged',
            'source_package':{'archive':str(source_archive),'whole':identity(source_archive),'verified_members':len(members)},
            'renderer_package':{'archive':str(runtime_archive),'whole':identity(runtime_archive),'verified_members':len(runtime_members),'members':runtime_members},
            'repair_package':{'archive':str(repair_archive),'whole':identity(repair_archive),'verified_members':len(repair_names)},
            'volume':volume(),'contract':identity(DOC/'CONTRACT.json'),'renderer_manifest':identity(DOC/'RENDERER-R5-MANIFEST.json'),
            'cause':'zipfile normalized Windows backslashes to forward slashes; independent normalized membership+every hash agrees',
            'large_archives_recreated_or_recopied':0,'model_files_recopied':0,
            'failed_receipt_identity':identity(DOC/'LOCAL-PRESERVE001.json')}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(dest/'SSD-VERIFIED-001.json'):raise ValueError('receipt copy')
    print(json.dumps({k:v for k,v in result.items() if k!='renderer_package'},indent=2))
    print(json.dumps({k:v for k,v in result['renderer_package'].items() if k!='members'},indent=2))

if __name__=='__main__':main()
