"""Native Windows, exclusive opaque-byte archive; no model/source execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from .audit_package import BASE, dependencies, digest, git
from .design import DOC, ROOT

VOLUME='0a2f1ba9-0000-0000-0000-100000000000'
DEST=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-20261004')
OLD_SSD=Path('D:/THESIS-BACKUPS/world-model-diagnostic-20261004')

def file_digest(path):
    h=hashlib.sha256();total=0
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b);total+=len(b)
    return {'bytes':total,'sha256':h.hexdigest()}

def verify(path,manifest,encoded):
    expected=dict(manifest['members']);expected['PACKAGE-MEMBERS.json']=digest(encoded)
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(expected):raise ValueError('Member set')
        for name,row in expected.items():
            h=hashlib.sha256();total=0
            with z.open(name) as f:
                for b in iter(lambda:f.read(1024*1024),b''):h.update(b);total+=len(b)
            if {'bytes':total,'sha256':h.hexdigest()}!=row:raise ValueError('Member authentication: '+name)
    return len(expected)

def main():
    if os.name!='nt':raise PermissionError('Native Windows only')
    commit=sys.argv[1]
    if len(commit)!=40 or git('rev-parse',commit).decode().strip()!=commit:raise ValueError('Full immutable commit')
    volume=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        'Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining,HealthStatus | ConvertTo-Json'],text=True))
    if volume['FileSystemLabel']!='THESIS_SSD' or VOLUME not in volume['UniqueId'].lower():raise PermissionError('Required SSD identity')
    if volume['HealthStatus']!='Healthy' or volume['SizeRemaining']<40*1024**3:raise RuntimeError('SSD health/free-space gate')
    inheritance=json.loads(git('show',commit+':docs/world-model-diagnostic-a2-20261004/INPUT-AND-INHERITANCE.json'))
    if inheritance['original_git_commit']!=BASE:raise ValueError('Inherited revision')
    names=git('ls-tree','-r','--name-only',commit,'--','wm_diag0_a2','docs/world-model-diagnostic-a2-20261004').decode().splitlines()
    if any('/artifacts/' in n or '/delivery/' in n for n in names):raise ValueError('Binary/delivery tracked unexpectedly')
    names+=dependencies(BASE)
    members={n:git('show',(BASE if n in inheritance['inherited_immutable_dependencies'] else commit)+':'+n) for n in names}
    for n,row in inheritance['inherited_immutable_dependencies'].items():
        if digest(members[n])!=row:raise ValueError('Inherited archive bytes')
    sources=json.loads(members['docs/world-model-diagnostic-a2-20261004/SOURCE-AUDIT-RECEIPTS.json'])
    sources+=json.loads(members['docs/world-model-diagnostic-a2-20261004/ENCODER-PIN.json'])['source_receipts']
    for row in sources:
        n=row['path'].replace('\\','/')
        if digest(members[n])!={'bytes':row['bytes'],'sha256':row['sha256']}:raise ValueError('Git normalization altered source bytes')
    artifacts=json.loads(members['docs/world-model-diagnostic-a2-20261004/ARTIFACT-RECEIPTS.json'])
    rawfiles={}
    for row in artifacts:
        n='docs/world-model-diagnostic-a2-20261004/artifacts/'+row['name']+'.pth'
        p=ROOT/n
        if file_digest(p)!={'bytes':row['bytes'],'sha256':row['sha256']}:raise ValueError('Opaque artifact changed')
        rawfiles[n]=p
    expected={n:digest(b) for n,b in members.items()}
    expected.update({n:file_digest(p) for n,p in rawfiles.items()})
    if sum(len(b) for b in members.values())>1_000_000_000:raise RuntimeError('Code/metadata cap')
    manifest={'study':'WM-DIAG0-A2-v1','git_commit':commit,'original_dependency_commit':BASE,
              'domain':'PREPARATION_ONLY','unsafe_deserialization':False,'members':expected}
    encoded=json.dumps(manifest,sort_keys=True,indent=2).encode()
    payload=sum(r['bytes'] for r in expected.values())+len(encoded)
    archive_reserve=payload+10_000_000
    bases=(ROOT/'wm_diag0',ROOT/'wm_diag0_a2',ROOT/'docs/world-model-diagnostic-20261004',DOC)
    retained=sum(p.stat().st_size for d in bases for p in d.rglob('*') if p.is_file())
    ssd_existing=sum(p.stat().st_size for p in DEST.rglob('*') if p.is_file()) if DEST.exists() else 0
    prior_ssd=sum(p.stat().st_size for p in OLD_SSD.rglob('*') if p.is_file()) if OLD_SSD.exists() else 0
    if retained+ssd_existing+prior_ssd+2*archive_reserve>5*1024**3:raise RuntimeError('All preparation copies full-future cap')
    # A2 copies must also fit the explicit future 1 GB preparation/storage line.
    a2retained=sum(p.stat().st_size for d in (ROOT/'wm_diag0_a2',DOC) for p in d.rglob('*') if p.is_file())
    if retained+ssd_existing+prior_ssd+2*archive_reserve>1_000_000_000:raise RuntimeError('Future preparation/copies reservation')
    local=DOC/'delivery';local.mkdir(exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    filename='amendment-a2-v1-'+commit+'.zip'
    path=local/filename;target=DEST/filename;receiptpath=local/'SSD-VERIFIED-A2-001.json'
    if any(p.exists() for p in (path,target,receiptpath)):raise FileExistsError('Preserve existing archive/partial/receipt')
    with path.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
            for n,b in sorted(members.items()):z.writestr(n,b)
            for n,p in sorted(rawfiles.items()):
                # Opaque model files are stored, not decoded or nested-extracted.
                with p.open('rb') as src,z.open(zipfile.ZipInfo(n),'w',force_zip64=True) as dst:
                    for b in iter(lambda:src.read(1024*1024),b''):dst.write(b)
            z.writestr('PACKAGE-MEMBERS.json',encoded)
        f.flush();os.fsync(f.fileno())
    if path.stat().st_size>archive_reserve:raise RuntimeError('Archive reservation exceeded; preserve partial')
    verify(path,manifest,encoded)
    with path.open('rb') as src,target.open('xb') as dst:
        for b in iter(lambda:src.read(1024*1024),b''):dst.write(b)
        dst.flush();os.fsync(dst.fileno())
    whole=file_digest(path)
    if file_digest(target)!=whole:raise ValueError('Whole SSD archive hash')
    count=verify(target,manifest,encoded)
    receipt={'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED','study':'WM-DIAG0-A2-v1','git_commit':commit,
             'original_dependency_commit':BASE,'archive':str(target),'local_archive':str(path),
             'whole':whole,'verified_members':count,'members_manifest_sha256':digest(encoded)['sha256'],
             'volume':volume,'all_preparation_copies_reserved_bytes':retained+ssd_existing+prior_ssd+2*archive_reserve,
             'existing_original_ssd_preparation_bytes':prior_ssd,
             'a2_preparation_and_copies_reserved_bytes':a2retained+ssd_existing+2*archive_reserve,
             'research_authority':False,'models_loaded':False,'historical_archives_rebacked_up':0}
    with receiptpath.open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
