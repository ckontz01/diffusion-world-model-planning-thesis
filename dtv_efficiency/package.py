"""New-small-package freeze and native designated-SSD whole/member verification."""
import argparse,hashlib,json,shutil,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
from dtv_efficiency.profile import DOC,sha

ROOT=DOC.parents[1]
DEST=Path('D:/THESIS-BACKUPS/dtv-efficiency-20260930')
VOLUME='\\\\?\\Volume{0a2f1ba9-0000-0000-0000-100000000000}\\'

def files():
    result=[]
    for base in (ROOT/'dtv_efficiency',DOC):
        for p in sorted(base.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.name not in ('PACKAGE-MANIFEST.json','SSD-BACKUP.json','PUBLICATION.json'):
                result.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    if sum(x['bytes'] for x in result)>250000000:raise RuntimeError('preparation byte envelope')
    return result

def verify_archive(path,entries):
    expected={x['path']:x for x in entries}
    with tarfile.open(path,'r:') as archive:
        members=archive.getmembers()
        if len(members)!=len(expected) or len({m.name for m in members})!=len(members):raise RuntimeError('archive inventory mismatch')
        for m in members:
            name=PurePosixPath(m.name)
            if not m.isfile() or name.is_absolute() or '..' in name.parts or m.name not in expected:raise RuntimeError('unsafe/unexpected archive member')
            h=hashlib.sha256();stream=archive.extractfile(m)
            for b in iter(lambda:stream.read(1048576),b''):h.update(b)
            if m.size!=expected[m.name]['bytes'] or h.hexdigest()!=expected[m.name]['sha256']:raise RuntimeError('archive member identity mismatch')
    return len(members)

def main():
    a=argparse.ArgumentParser();a.add_argument('mode',choices=('freeze','backup'));args=a.parse_args()
    if args.mode=='freeze':
        with (DOC/'PACKAGE-MANIFEST.json').open('x') as f:json.dump(dict(study='DTV-EFF0',execute=False,files=files()),f,indent=2)
        print('package_manifest_sha256',sha(DOC/'PACKAGE-MANIFEST.json'));return
    # This is native Windows transport only, never through the WSL D: mount.
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command',"Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress"],text=True)
    volume=json.loads(raw)
    if volume['FileSystemLabel']!='THESIS_SSD' or volume['UniqueId'].lower()!=VOLUME.lower() or volume['SizeRemaining']<40000000000:raise RuntimeError('required designated SSD/40 GB free unavailable')
    manifest=DOC/'PACKAGE-MANIFEST.json';entries=json.loads(manifest.read_text())['files']
    for row in entries:
        if sha(ROOT/row['path'])!=row['sha256']:raise RuntimeError('frozen package changed')
    identity=sha(manifest);target=DEST/('package-'+identity[:16])
    if target.exists():raise RuntimeError('exclusive SSD package exists; no extra backup cycle')
    target.mkdir(parents=True);started=time.monotonic()
    path=target/'package.tar'
    with tarfile.open(path,'x:') as archive:
        for row in entries:archive.add(ROOT/row['path'],arcname=row['path'],recursive=False)
    whole_before=sha(path)
    members=verify_archive(path,entries)
    whole_after=sha(path)
    if whole_before!=whole_after:raise RuntimeError('whole archive changed during verification')
    manifest_copy=target/'PACKAGE-MANIFEST.json';shutil.copyfile(manifest,manifest_copy)
    if sha(manifest_copy)!=identity:raise RuntimeError('manifest copy mismatch')
    receipt=dict(status='verified',archive=str(path),archive_sha256=whole_after,whole_sha256_before_after_match=True,archive_bytes=path.stat().st_size,members=members,all_member_hashes_verified=True,manifest_sha256=identity,volume=volume,wall_seconds=time.monotonic()-started,historical_archives_touched=False,research_execution=False)
    with (target/'VERIFIED.json').open('x') as f:json.dump(receipt,f,indent=2)
    with (DOC/'SSD-BACKUP.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
