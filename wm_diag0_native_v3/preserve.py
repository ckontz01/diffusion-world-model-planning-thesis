"""Native Windows preservation of this new source and new renderer only."""
import hashlib,json,os,sys,zipfile
from pathlib import Path
from .common import DOC,DOCREL,ROOT,identity,write_new
from wm_diag0_preflight_v1.preserve import git,volume,digest

def verify(path,expected):
    with zipfile.ZipFile(path) as z:
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(expected):raise ValueError('archive member set')
        for name,row in expected.items():
            h=hashlib.sha256();size=0
            with z.open(name) as f:
                for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
            if {'bytes':size,'sha256':h.hexdigest()}!=row:raise ValueError('archive member identity')

def main():
    if os.name!='nt':raise RuntimeError('native Windows transfer')
    commit=sys.argv[1];remote=git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]
    if commit!=remote or git('rev-parse','HEAD').decode().strip()!=commit:raise ValueError('published full source hash')
    v=volume();dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-native-v3-20261015');dest.mkdir(exist_ok=False)
    names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_native_v3',DOCREL).decode().splitlines()
    if any('/delivery/' in n or n.endswith(('.pth','.ckpt','.so','.sif','.vhdx')) for n in names):raise ValueError('source/compact metadata only')
    blobs={n:git('show',commit+':'+n) for n in names}
    members={n:digest(b) for n,b in blobs.items()}
    manifest={'source_commit':commit,'remote_full_hash':remote,'members':members,'old_packages_rearchived':0,'model_files_copied':0}
    blobs['PACKAGE-MEMBERS.json']=json.dumps(manifest,sort_keys=True,indent=2).encode();members['PACKAGE-MEMBERS.json']=digest(blobs['PACKAGE-MEMBERS.json'])
    path=dest/('native-v3-'+commit+'.zip')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in sorted(blobs.items()):z.writestr(n,b)
        f.flush();os.fsync(f.fileno())
    verify(path,members)
    source_result={'archive':str(path),'whole':identity(path),'verified_members':len(members)}
    runtime_members={str(p.relative_to(DOC/'delivery')):identity(p) for p in sorted((DOC/'delivery').rglob('*')) if p.is_file()}
    if sum(r['bytes'] for r in runtime_members.values())>250_000_000:raise ValueError('all-failure-inclusive renderer preparation')
    runtime_archive=dest/'renderer-signed-packages-and-all-preparation-evidence.zip'
    with runtime_archive.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for name in runtime_members:z.write(DOC/'delivery'/name,name)
        f.flush();os.fsync(f.fileno())
    verify(runtime_archive,runtime_members)
    if runtime_archive.stat().st_size>250_000_000:raise ValueError('renderer SSD reservation')
    runtime_result={'archive':str(runtime_archive),'whole':identity(runtime_archive),'verified_members':len(runtime_members),'members':runtime_members}
    result={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
            'source_package':source_result,'renderer_package':runtime_result,'volume':v,'contract':identity(DOC/'CONTRACT.json'),
            'renderer_manifest':identity(DOC/'RENDERER-R5-MANIFEST.json'),'original_A2_and_other_packages_rearchived':0,'model_files_recopied':0}
    write_new(DOC/'SSD-VERIFIED-001.json',result);write_new(dest/'SSD-VERIFIED-001.json',result)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(dest/'SSD-VERIFIED-001.json'):raise ValueError('receipt identity')
    print(json.dumps({k:v for k,v in result.items() if k!='renderer_package'},indent=2))
    print(json.dumps({k:v for k,v in runtime_result.items() if k!='members'},indent=2))

if __name__=='__main__':main()
