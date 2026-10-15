"""Preserve only this new source/metadata package from a verified Git revision."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCREL = 'docs/world-model-diagnostic-a2-cluster-native-v1-20261015'
DOC = ROOT / DOCREL
DEST = Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-cluster-native-v1-20261015')
PREFIXES = ('wm_diag0_cluster_v1/', DOCREL + '/')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, timeout=30)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def verify(path, expected):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected): raise ValueError('Member set')
        for name, row in expected.items():
            if identity(archive.read(name)) != row: raise ValueError('Member hash: ' + name)


def main():
    if os.name != 'nt': raise PermissionError('Native Windows transfer only')
    commit = sys.argv[1]
    if len(commit) != 40 or git('rev-parse', commit).decode().strip() != commit: raise ValueError('Full commit')
    remote = git('ls-remote', 'origin', 'refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]
    if remote != commit: raise ValueError('Remote tip not exact requested source commit')
    volume = json.loads(subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
        'Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining,HealthStatus | ConvertTo-Json'], text=True, timeout=20))
    if volume['FileSystemLabel'] != 'THESIS_SSD' or '0a2f1ba9-0000-0000-0000-100000000000' not in volume['UniqueId'].lower(): raise ValueError('SSD identity')
    if volume['HealthStatus'] != 'Healthy' or volume['SizeRemaining'] < 40*1024**3: raise ValueError('SSD capacity/health')
    names = git('ls-tree', '-r', '--name-only', commit, '--', *[p.rstrip('/') for p in PREFIXES]).decode().splitlines()
    if not names or any(not n.startswith(PREFIXES) or '/delivery/' in n or n.endswith(('.pth','.pt','.ckpt','.sif','.vhdx')) for n in names): raise ValueError('Source-only allowlist')
    members = {n: git('show', commit+':'+n) for n in names}
    if sum(map(len, members.values())) > 2_000_000: raise ValueError('Small package limit')
    prep = json.loads(members[DOCREL + '/PREPARE-001.json'])
    for row in prep['encoder_source']['members']:
        if identity(members[row['path']]) != {k:row[k] for k in ('bytes','sha256')}: raise ValueError('Source bytes altered')
    manifest = {'source_commit': commit, 'remote_full_hash': remote,
                'original_a2_source_commit': 'ab50aaab8b01691b88574d35eb71a7ba1477bebb',
                'members': {n: identity(b) for n,b in members.items()},
                'old_packages_and_models_not_copied': True}
    members['PACKAGE-MEMBERS.json'] = json.dumps(manifest, sort_keys=True, indent=2).encode()
    expected = {n:identity(b) for n,b in members.items()}
    local = DOC / 'delivery'; local.mkdir(exist_ok=True); DEST.mkdir(exist_ok=True)
    filename = 'cluster-native-v1-' + commit + '.zip'
    src, dst = local / filename, DEST / filename
    receipt = DOC / 'SSD-VERIFIED-001.json'
    if any(p.exists() for p in (src,dst,receipt)): raise FileExistsError('Preserve existing package/partial/receipt')
    with src.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for n,b in sorted(members.items()): archive.writestr(n,b)
        stream.flush(); os.fsync(stream.fileno())
    if src.stat().st_size > 2_000_000: raise ValueError('Archive bound; preserve partial')
    verify(src, expected)
    raw = src.read_bytes()
    with dst.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    if identity(dst.read_bytes()) != identity(raw): raise ValueError('Whole archive identity')
    verify(dst, expected)
    result = {'status':'WHOLE_AND_EVERY_MEMBER_VERIFIED', 'source_commit':commit,
              'remote_full_hash':remote, 'archive':str(dst), 'whole':identity(raw),
              'verified_members':len(expected), 'volume':volume, 'research_launched':False,
              'model_files_copied':0, 'historical_packages_rearchived':0,
              'new_local_and_ssd_archives_bytes':2*len(raw),
              'within_existing_small_package_reservation':True}
    with receipt.open('x', encoding='utf8') as stream: json.dump(result,stream,indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
