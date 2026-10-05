"""Authenticated Ubuntu disk-format conversion only; no research/guest execution."""
import hashlib
import json
import os
import pathlib
import resource
import subprocess
import time

BASE = pathlib.Path('/mnt/c/Users/Chris/thesis-vm/wm-diag0-a2-c0-runtime-v1')
ROOT = BASE / 'os-image-v1'
SOURCE = ROOT / 'ubuntu-22.04-minimal-cloudimg-amd64.img'
PARTIAL = ROOT / 'ubuntu-minimal.vhdx.partial'
FINAL = ROOT / 'ubuntu-minimal.vhdx'
TOOLS = BASE / 'os-tools-v1'
COMMAND = ['/lib64/ld-linux-x86-64.so.2', '--library-path', str(TOOLS / 'lib'), str(TOOLS / 'bin/qemu-img')]
PINS = {
    SOURCE: 'bd27c6f51053dd7e59bcbe6016c6fa853f54b1e423af12273ff46a5176bfbf41',
    TOOLS / 'bin/qemu-img': '634320b91165669917123e8e79cce1c4d00cee0a4aa4d662d7c0a8186479b3fb',
    TOOLS / 'lib/libaio.so.1t64': 'fbc4a5cc34ead525e68c7b4beba25bfa2c5affae0c564a68d684ba299e6c9a19',
    TOOLS / 'lib/liburing.so.2': '51594b92ac35f96595d3fcec9c3ec5d190637d9b426d5f8a8f4207875d2962f6',
}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            result.update(chunk)
    return result.hexdigest()


def limits():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2500000000, 2500000000))


def run(args):
    result = subprocess.run(COMMAND + args, capture_output=True, text=True, timeout=120, preexec_fn=limits, env={'PATH': '/usr/bin:/bin', 'HOME': str(ROOT), 'LANG': 'C'})
    if len(result.stdout) + len(result.stderr) > 65536:
        raise ValueError('OS disk tool response exceeds evidence cap')
    if result.returncode != 0:
        raise ValueError(f'OS-only disk utility error {result.returncode}: {result.stderr[:8192]}')
    return result.stdout


if __name__ == '__main__':
    start = time.monotonic()
    if PARTIAL.exists() or FINAL.exists():
        raise ValueError('Existing OS disk or conversion partial: reconcile, do not repeat')
    for ancestor in [ROOT, *ROOT.parents]:
        if ancestor.is_symlink():
            raise ValueError('Redirected OS disk root')
    for path, expected in PINS.items():
        if path.is_symlink() or digest(path) != expected:
            raise ValueError('OS image/tool/library identity mismatch')
    if SOURCE.stat().st_size != 310607360:
        raise ValueError('OS source byte identity mismatch')
    info = json.loads(run(['info', '-f', 'qcow2', '--output=json', str(SOURCE)]))
    if info.get('format') != 'qcow2' or info.get('virtual-size') != 2361393152 or info.get('encrypted', False) or info.get('backing-filename') or info.get('snapshots'):
        raise ValueError('Unexpected OS image architecture/backing/encryption/snapshot metadata')
    run(['convert', '-m', '4', '-f', 'qcow2', '-O', 'vhdx', '-o', 'subformat=dynamic,block_size=8388608', str(SOURCE), str(PARTIAL)])
    if PARTIAL.stat().st_size > 2500000000:
        raise ValueError('OS export byte cap exceeded')
    output = json.loads(run(['info', '-f', 'vhdx', '--output=json', str(PARTIAL)]))
    if output.get('virtual-size') != 2361393152 or output.get('format') != 'vhdx' or output.get('backing-filename'):
        raise ValueError('OS output format/virtual size mismatch')
    comparison = run(['compare', '-f', 'qcow2', '-F', 'vhdx', str(SOURCE), str(PARTIAL)]).strip()
    identity = digest(PARTIAL)
    PARTIAL.rename(FINAL)
    print(json.dumps({'mode': 'AUTHENTICATED_OS_ONLY_OFFLINE_DISK_CONVERSION', 'OS_source_SHA256': PINS[SOURCE], 'VHDX_SHA256': identity, 'VHDX_bytes': FINAL.stat().st_size, 'virtual_disk_bytes': output['virtual-size'], 'whole_logical_disk_comparison': comparison, 'elapsed_seconds': time.monotonic() - start, 'OS_booted_or_disk_attached': False, 'guest_runtime_installed': False, 'research_checkpoint_conversion_or_loading': False, 'gate_ready': False}, indent=2))
