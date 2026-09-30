"""Exclusive correction export, including immutable reviewed dependencies."""
import argparse,json,shutil,subprocess,tarfile,time
from pathlib import Path
from dtv_efficiency.package import verify_archive,VOLUME
from dtv_efficiency_r1.control import ROOT,DOC,ORIGINAL_DOC
from dtv_efficiency_r1.profile import sha

DEST=Path('D:/THESIS-BACKUPS/dtv-efficiency-20260930/correction-r1')
REVIEWED_MANIFEST_SHA='a9a3b495e479916dfc64279e2c099a76a8817119c53607770b04e22f693796ae'

def files():
    original=ORIGINAL_DOC/'PACKAGE-MANIFEST.json'
    if sha(original)!=REVIEWED_MANIFEST_SHA:raise RuntimeError('reviewed manifest changed')
    rows=json.loads(original.read_text())['files']
    for row in rows:
        if sha(ROOT/row['path'])!=row['sha256'] or (ROOT/row['path']).stat().st_size!=row['bytes']:raise RuntimeError('reviewed source changed')
    extra=[original]+[p for base in (ROOT/'dtv_efficiency_r1',DOC) for p in sorted(base.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in ('PACKAGE-MANIFEST.json','SSD-BACKUP.json','PUBLICATION.json')]
    rows=rows+[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in extra]
    if len({r['path'] for r in rows})!=len(rows):raise RuntimeError('duplicate export member')
    if sum(r['bytes'] for r in rows)>4000000:raise RuntimeError('complete source package exceeds unchanged 4 MB reservation')
    new_bytes=sum(r['bytes'] for r in rows if r['path'].startswith(('dtv_efficiency_r1/','docs/dtv-efficiency-correction-r1-20260930/')))
    if new_bytes>50000000:raise RuntimeError('new correction artifact envelope')
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('freeze','backup'));args=parser.parse_args()
    manifest=DOC/'PACKAGE-MANIFEST.json'
    if args.mode=='freeze':
        rows=files();content=json.dumps(dict(study='DTV-EFF0',version='control-correction-r1',execute=False,reviewed_commit='712c39041a8242c3f45d43f95b3199bd77ca64ba',reviewed_manifest_sha256=REVIEWED_MANIFEST_SHA,files=rows),indent=2)
        if sum(row['bytes'] for row in rows)+len(content.encode())>4000000:raise RuntimeError('complete frozen source including manifest exceeds 4 MB')
        with manifest.open('x') as f:f.write(content)
        print('package_manifest_sha256',sha(manifest));return
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command','Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress'],text=True)
    volume=json.loads(raw)
    if volume['FileSystemLabel']!='THESIS_SSD' or volume['UniqueId'].lower()!=VOLUME.lower() or volume['SizeRemaining']<40000000000:raise RuntimeError('required designated SSD/40 GB free unavailable')
    entries=json.loads(manifest.read_text())['files']
    if entries!=files():raise RuntimeError('frozen correction changed')
    if sum(row['bytes'] for row in entries)+manifest.stat().st_size>4000000:raise RuntimeError('complete frozen source cap')
    identity=sha(manifest);target=DEST/('package-'+identity[:16])
    if target.exists():raise RuntimeError('exclusive SSD export already exists; no extra cycle')
    target.mkdir(parents=True);started=time.monotonic();path=target/'package.tar'
    with tarfile.open(path,'x:') as archive:
        for row in entries:archive.add(ROOT/row['path'],arcname=row['path'],recursive=False)
    before=sha(path);members=verify_archive(path,entries);after=sha(path)
    if before!=after:raise RuntimeError('whole archive changed during verification')
    shutil.copyfile(manifest,target/'PACKAGE-MANIFEST.json')
    if sha(target/'PACKAGE-MANIFEST.json')!=identity:raise RuntimeError('manifest copied bytes differ')
    receipt=dict(status='verified',archive=str(path),archive_sha256=after,whole_sha256_before_after_match=True,archive_bytes=path.stat().st_size,members=members,all_member_hashes_verified=True,manifest_sha256=identity,volume=volume,wall_seconds=time.monotonic()-started,reviewed_export_unchanged=True,historical_archives_touched=False,research_execution=False)
    if path.stat().st_size+sum(r['bytes'] for r in entries if r['path'].startswith(('dtv_efficiency_r1/','docs/dtv-efficiency-correction-r1-20260930/')))>50000000:raise RuntimeError('new correction export/artifact cap')
    for destination in (target/'VERIFIED.json',DOC/'SSD-BACKUP.json'):
        with destination.open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
