"""One new small source package; native Windows whole/member SSD verification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from wm_diag0_preflight_v1.common import ROOT,DOC,DOCREL,identity,write_new

def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30)
def digest(b): return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def volume():
    v=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        'Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining,HealthStatus | ConvertTo-Json'],text=True,timeout=20))
    if v['FileSystemLabel']!='THESIS_SSD' or '0a2f1ba9-0000-0000-0000-100000000000' not in v['UniqueId'].lower(): raise ValueError('wrong SSD')
    if v['HealthStatus']!='Healthy' or v['SizeRemaining']<40*1024**3: raise ValueError('SSD capacity/health')
    return v

def verify_zip(path,members):
    with zipfile.ZipFile(path) as z:
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(members): raise ValueError('archive member set')
        for n,b in members.items():
            if digest(z.read(n))!=digest(b): raise ValueError('archive member identity')

def main():
    if os.name!='nt': raise RuntimeError('native Windows preservation')
    commit=sys.argv[1]; remote=git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]
    if len(commit)!=40 or git('rev-parse',commit).decode().strip()!=commit or remote!=commit: raise ValueError('published full hash')
    v=volume()
    prefixes=['wm_diag0_preflight_v1',DOCREL,'docs/world-model-diagnostic-a2-native-v2-20261015']
    names=git('ls-tree','-r','--name-only',commit,'--',*prefixes).decode().splitlines()
    if any('/delivery/' in n or n.endswith(('.pth','.ckpt','.vhdx','.sif')) for n in names): raise ValueError('source/metadata only')
    members={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,members.values()))>2_000_000: raise ValueError('new small-package reservation')
    manifest={'source_commit':commit,'remote_full_hash':remote,'members':{n:digest(b) for n,b in members.items()},
              'original_a2_source':'ab50aaab8b01691b88574d35eb71a7ba1477bebb','old_archives_and_weights_not_recopied':True}
    members['PACKAGE-MEMBERS.json']=json.dumps(manifest,sort_keys=True,indent=2).encode()
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-preflight-v1-20261015'); dest.mkdir(exist_ok=True)
    local=DOC/'delivery'; local.mkdir(exist_ok=True)
    filename='preflight-v1-'+commit+'.zip'; src=local/filename; dst=dest/filename
    if any(p.exists() for p in (src,dst,DOC/'SSD-VERIFIED-001.json')): raise FileExistsError('no rearchive/overwrite')
    with src.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in sorted(members.items()): z.writestr(n,b)
        f.flush(); os.fsync(f.fileno())
    verify_zip(src,members)
    with dst.open('xb') as f: f.write(src.read_bytes()); f.flush(); os.fsync(f.fileno())
    if identity(dst)!=identity(src): raise ValueError('whole archive identity')
    verify_zip(dst,members)
    result={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','source_commit':commit,'remote_full_hash':remote,
            'archive':str(dst),'whole':identity(dst),'verified_members':len(members),'volume':v,
            'contract':identity(DOC/'CONTRACT.json'),'model_files_copied':0,'old_packages_rearchived':0}
    write_new(DOC/'SSD-VERIFIED-001.json',result)
    write_new(dest/'SSD-VERIFIED-001.json',result)
    if identity(DOC/'SSD-VERIFIED-001.json')!=identity(dest/'SSD-VERIFIED-001.json'): raise ValueError('receipt copy')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
