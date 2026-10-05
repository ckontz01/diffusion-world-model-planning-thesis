"""Version and tiny artificial disk checks; not a model conversion/isolation test."""
import hashlib
import json
import os
import pathlib
import resource
import subprocess

ROOT = pathlib.Path('/mnt/c/Users/Chris/thesis-vm/wm-diag0-a2-c0-runtime-v1/os-tools-v1')
TEST = ROOT / 'artificial-disk-v1'
COMMAND = ['/lib64/ld-linux-x86-64.so.2', '--library-path', str(ROOT / 'lib'), str(ROOT / 'bin/qemu-img')]


def limit():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16777216, 16777216))


def run(args):
    result = subprocess.run(COMMAND + args, capture_output=True, text=True, timeout=20, preexec_fn=limit, env={'PATH': '/usr/bin:/bin', 'HOME': str(TEST), 'LANG': 'C'}, check=True)
    if len(result.stdout) + len(result.stderr) > 65536:
        raise ValueError('Tool output exceeds test cap')
    return result.stdout.strip()


def main():
    TEST.mkdir()
    version = run(['--version'])
    if '8.2.2' not in version or '0ubuntu1.18' not in version:
        raise ValueError('Unexpected offline tool version')
    run(['create', '-f', 'qcow2', str(TEST / 'artificial.qcow2'), '1048576'])
    run(['convert', '-m', '4', '-f', 'qcow2', '-O', 'vhdx', str(TEST / 'artificial.qcow2'), str(TEST / 'artificial.vhdx')])
    comparison = run(['compare', '-f', 'qcow2', '-F', 'vhdx', str(TEST / 'artificial.qcow2'), str(TEST / 'artificial.vhdx')])
    info = json.loads(run(['info', '--output=json', '-f', 'vhdx', str(TEST / 'artificial.vhdx')]))
    if info['virtual-size'] != 1048576 or info['format'] != 'vhdx':
        raise ValueError('Artificial disk format/size mismatch')
    files = [{'name': p.name, 'bytes': p.stat().st_size, 'SHA256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(TEST.iterdir()) if p.is_file()]
    print(json.dumps({'mode': 'OS_TOOL_ARTIFICIAL_DISK_INTERFACE_ONLY', 'version': version, 'comparison': comparison, 'virtual_bytes': info['virtual-size'], 'files': files, 'VM_started_or_disk_attached': False, 'research_checkpoint_conversion': False, 'gate_ready': False}, indent=2))


if __name__ == '__main__':
    main()
