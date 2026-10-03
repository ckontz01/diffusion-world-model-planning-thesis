"""Native-Windows new-study immutable-Git archive, whole/member verification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PREFIXES=('wm_diag0','docs/world-model-diagnostic-20261004')
VOLUME='0a2f1ba9-0000-0000-0000-100000000000'

def sha_bytes(data):return hashlib.sha256(data).hexdigest()

def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def build_archive(path, commit, members):
    manifest={'git_commit':commit,'domain':'preparation-only','members':
        {n:{'sha256':sha_bytes(b),'bytes':len(b)} for n,b in sorted(members.items())}}
    encoded=json.dumps(manifest,sort_keys=True,indent=2).encode()
    all_members=dict(members);all_members['PACKAGE-MEMBERS.json']=encoded
    with Path(path).open('xb') as handle:
        with zipfile.ZipFile(handle,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,data in sorted(all_members.items()):
                if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe archive member')
                info=zipfile.ZipInfo(name,date_time=(2026,10,4,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,data)
    return all_members

def verify_archive(path, expected):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(expected):raise ValueError('Member set')
        if z.testzip() is not None:raise ValueError('Archive CRC')
        receipts=[]
        for name,data in sorted(expected.items()):
            saved=z.read(name)
            if saved!=data:raise ValueError('Archive member differs from immutable source: '+name)
            receipts.append({'path':name,'bytes':len(saved),'sha256':sha_bytes(saved)})
    return receipts

def main():
    if os.name!='nt':raise PermissionError('Native Windows transfer only')
    if len(sys.argv)!=2 or len(sys.argv[1])!=40:raise ValueError('Exact full Git commit required')
    commit=sys.argv[1]
    if git('rev-parse',commit).decode().strip()!=commit:raise ValueError('Unresolved commit')
    volume=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        'Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining,HealthStatus | ConvertTo-Json'],text=True))
    if volume['FileSystemLabel']!='THESIS_SSD' or VOLUME not in volume['UniqueId'].lower():
        raise PermissionError('Required SSD identity unavailable')
    if volume['SizeRemaining']<40*1024**3:raise RuntimeError('Required SSD free-space gate')
    names=git('ls-tree','-r','--name-only',commit,'--',*PREFIXES).decode().splitlines()
    names=[n for n in names if '/delivery/' not in n]
    if not names or any(not any(n.startswith(p+'/') for p in PREFIXES) for n in names):raise ValueError('New-study scope')
    members={n:git('show',commit+':'+n) for n in names}
    if sum(map(len,members.values()))>1_000_000_000:raise RuntimeError('Preparation output cap')
    destination=Path('D:/THESIS-BACKUPS/world-model-diagnostic-20261004')
    destination.mkdir(parents=True,exist_ok=True)
    local=ROOT/'docs/world-model-diagnostic-20261004/delivery'
    local.mkdir(exist_ok=True)
    name='prepare-v1-'+commit+'.zip'
    local_archive=local/name;ssd_archive=destination/name
    if local_archive.exists() or ssd_archive.exists():raise FileExistsError('Preserve existing archive/partial; no blind repeat')
    expected=build_archive(local_archive,commit,members)
    verify_archive(local_archive,expected)
    with local_archive.open('rb') as src,ssd_archive.open('xb') as dst:
        for block in iter(lambda:src.read(1024*1024),b''):dst.write(block)
        dst.flush();os.fsync(dst.fileno())
    whole=sha_file(local_archive)
    if sha_file(ssd_archive)!=whole:raise ValueError('SSD whole archive hash')
    receipt={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','git_commit':commit,
             'domain':'preparation-only','source':'immutable Git blobs, not mutable working files',
             'volume':volume,'archive':str(ssd_archive),'archive_bytes':ssd_archive.stat().st_size,
             'sha256':whole,'members':verify_archive(ssd_archive,expected),'historical_rebackups':0}
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
