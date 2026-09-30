"""One-shot CPU acceptance/archive/SSD transport, outside executed source.

No dispatch, model deserialization, inference, timer changes or retry path.
The accepted independent validator is invoked from the frozen source.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
CPU_LIMIT = 600
ARCHIVE_LIMIT = 62000000
SSD_ROOT = Path('D:/THESIS-BACKUPS/dtv-efficiency-20260930')
SSH = ['wsl.exe', '-d', 'Thesis-Ubuntu', '-u', 'chris', '--', 'ssh',
       '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'prometheus']


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def safe_name(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or path.is_absolute() or '..' in path.parts or str(path) != name:
        raise RuntimeError('unsafe or noncanonical archive member')


def verify_archive(path, request):
    """No extraction: authenticate the whole file, exact set and every member."""
    path = Path(path)
    if path.stat().st_size != request['archive_bytes'] or path.stat().st_size > ARCHIVE_LIMIT:
        raise RuntimeError('archive byte count differs')
    if sha(path) != request['archive_sha256']:
        raise RuntimeError('whole archive hash differs')
    expected = {row['path']: row for row in request['files']}
    if len(expected) != len(request['files']):
        raise RuntimeError('duplicate expected members')
    with tarfile.open(path, 'r:') as archive:
        members = archive.getmembers()
        if len(members) != request['archive_members'] or len({m.name for m in members}) != len(members):
            raise RuntimeError('archive duplicate/count mismatch')
        if {m.name for m in members} != set(expected):
            raise RuntimeError('archive complete member set differs')
        for member in members:
            safe_name(member.name)
            if not member.isfile() or member.size != expected[member.name]['bytes']:
                raise RuntimeError('archive member type/size differs')
            digest = hashlib.sha256()
            with archive.extractfile(member) as stream:
                for block in iter(lambda: stream.read(1048576), b''):
                    digest.update(block)
            if digest.hexdigest() != expected[member.name]['sha256']:
                raise RuntimeError('archive member hash differs')
    return dict(whole_archive_verified=True, every_member_verified=True,
                archive_bytes=path.stat().st_size, archive_sha256=sha(path),
                archive_members=len(expected))


def check_volume():
    command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
               "Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True)
    volume = json.loads(result.stdout)
    normalized = volume['UniqueId'].lower().replace('\\', '')
    if volume['FileSystemLabel'] != 'THESIS_SSD' or normalized != '?volume{0a2f1ba9-0000-0000-0000-100000000000}':
        raise RuntimeError('designated SSD identity differs')
    if volume['SizeRemaining'] < 40000000000:
        raise RuntimeError('designated SSD has less than 40 GB free')
    return volume


def accept_archive():
    identity = json.loads((HERE/'IDENTITIES.json').read_text())
    # Copy only the small operational provenance, never historical inputs.
    files = {}
    for path in sorted(HERE.rglob('*')):
        if path.is_symlink():
            raise RuntimeError('operational symlink not allowed')
        if path.is_file():
            name = path.relative_to(HERE).as_posix()
            safe_name(name)
            files[name] = base64.b64encode(path.read_bytes()).decode()
    helper = (HERE/'finalize_remote.py').read_text()
    code = 'I='+repr(identity)+'\nCLIENT='+repr(files)+'\n'+helper
    result = subprocess.run(SSH+['/usr/bin/python3.9 -'], input=code.encode(),
                            capture_output=True, timeout=180)
    record = dict(returncode=result.returncode, stdout=result.stdout.decode(errors='replace'),
                  stderr=result.stderr.decode(errors='replace'), automatic_retry=False)
    write(HERE/'FINALIZE-01.json', record)
    if result.returncode:
        raise RuntimeError('acceptance/archive fault; preserved; no retry: '+record['stderr'])
    request = json.loads(record['stdout'])
    write(HERE/'BACKUP-REQUEST.json', request)
    print(json.dumps({k: v for k, v in request.items() if k != 'files'}, indent=2))


def backup():
    request = json.loads((HERE/'BACKUP-REQUEST.json').read_text())
    identity = json.loads((HERE/'IDENTITIES.json').read_text())
    remote_expected = identity['run']+'/final-preservation/final.tar'
    if request['remote_archive'] != remote_expected or request['manifest_sha256'] != identity['manifest_sha256']:
        raise RuntimeError('backup request/run/source binding differs')
    if request['approval_sha256'] != identity['enabled_approval_sha256']:
        raise RuntimeError('backup approval binding differs')
    if request['archive_bytes'] > ARCHIVE_LIMIT or request['archive_bytes'] <= 0:
        raise RuntimeError('invalid backup reservation')
    volume = check_volume()
    destination = SSD_ROOT/Path(identity['run']).name
    if destination.exists():
        raise RuntimeError('exclusive final backup destination exists; do not overwrite/resume')
    destination.mkdir()
    partial = destination/'final.tar.partial'
    final = destination/'final.tar'
    began = time.monotonic()
    try:
        # Exactly one stream. Native Windows receives bytes directly on SSD.
        with partial.open('xb') as stream, (HERE/'TRANSFER-STDERR.bin').open('xb') as error:
            result = subprocess.run(SSH+['cat '+remote_expected], stdout=stream, stderr=error, timeout=120)
        if result.returncode:
            raise RuntimeError('SSH archive transfer failed with exit '+str(result.returncode))
        receipt = verify_archive(partial, request)
        if final.exists():
            raise RuntimeError('exclusive final name unexpectedly exists')
        partial.rename(final)  # Windows refuses an existing destination.
        receipt.update(status='verified', destination=str(final), ssd=volume,
                       request_sha256=sha(HERE/'BACKUP-REQUEST.json'),
                       transfer_and_verification_wall_seconds=time.monotonic()-began,
                       automatic_retry=False, historical_archives_transferred=False)
        write(destination/'BACKUP-VERIFIED.json', receipt)
        write(HERE/'BACKUP-VERIFIED.json', receipt)
        print(json.dumps(receipt, indent=2))
    except BaseException as error:
        failure = dict(status='failed', error=repr(error), partial=str(partial),
                       partial_exists=partial.exists(), partial_bytes=partial.stat().st_size if partial.exists() else 0,
                       partial_sha256=sha(partial) if partial.exists() else None,
                       observed_unix=time.time(), automatic_retry=False,
                       request_sha256=sha(HERE/'BACKUP-REQUEST.json'))
        write(HERE/'BACKUP-FAILURE.json', failure)
        write(destination/'BACKUP-FAILURE.json', failure)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('test', 'accept-archive', 'backup', 'publish'))
    args = parser.parse_args()
    ledger = HERE/'CPU-FINALIZATION.jsonl'
    entries = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    if any(e['event'] == 'intent' and e['action'] == args.action for e in entries):
        raise RuntimeError('one-shot action already attempted; reconcile, do not repeat')
    if any(e['event'] == 'finished' and e['status'] != 'passed' for e in entries):
        raise RuntimeError('previous finalization fault; no automatic continuation')
    if sum(e.get('wall_seconds', 0) for e in entries) >= CPU_LIMIT:
        raise RuntimeError('cumulative CPU finalization wall budget exhausted')
    os.environ.update(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', PYTHONDONTWRITEBYTECODE='1')
    began = time.monotonic()
    with ledger.open('a') as stream:
        stream.write(json.dumps(dict(event='intent', action=args.action, observed_unix=time.time()))+'\n')
    status, error = 'passed', None
    try:
        if args.action == 'test':
            result = subprocess.run([sys.executable, '-B', str(HERE/'test_finalize.py')], timeout=30)
            if result.returncode:
                raise RuntimeError('artificial preservation tests failed')
        elif args.action == 'accept-archive':
            accept_archive()
        elif args.action == 'backup':
            backup()
        else:
            result = subprocess.run([sys.executable, '-B', str(HERE/'publish.py')], timeout=30)
            if result.returncode:
                raise RuntimeError('post-preservation publication failed; no measurement repeated')
    except BaseException as caught:
        status, error = 'failed', repr(caught)
        raise
    finally:
        elapsed = time.monotonic()-began
        with ledger.open('a') as stream:
            stream.write(json.dumps(dict(event='finished', action=args.action, status=status,
                         error=error, wall_seconds=elapsed, automatic_retry=False))+'\n')
        if sum(e.get('wall_seconds', 0) for e in entries)+elapsed > CPU_LIMIT:
            raise RuntimeError('cumulative finalization CPU wall ceiling exceeded; retain evidence')


if __name__ == '__main__':
    main()
