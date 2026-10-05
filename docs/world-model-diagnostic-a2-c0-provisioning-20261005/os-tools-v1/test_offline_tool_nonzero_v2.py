"""Small nonzero disk identity and output-limit checks, never a guest/model test."""
import hashlib
import json
import os
import pathlib
import resource
import subprocess
from test_offline_tool_v1 import ROOT, COMMAND, run

TEST = ROOT / 'artificial-nonzero-v2'


def quota():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))


if __name__ == '__main__':
    TEST.mkdir()
    raw = bytes(range(256)) * 1024
    with (TEST / 'source.raw').open('xb') as stream:
        stream.write(raw)
    run(['convert', '-m', '4', '-f', 'raw', '-O', 'qcow2', str(TEST / 'source.raw'), str(TEST / 'source.qcow2')])
    run(['convert', '-m', '4', '-f', 'qcow2', '-O', 'vhdx', str(TEST / 'source.qcow2'), str(TEST / 'export.vhdx')])
    result = run(['compare', '-f', 'raw', '-F', 'vhdx', str(TEST / 'source.raw'), str(TEST / 'export.vhdx')])
    run(['convert', '-m', '4', '-f', 'vhdx', '-O', 'raw', str(TEST / 'export.vhdx'), str(TEST / 'readback.raw')])
    if (TEST / 'readback.raw').read_bytes() != raw:
        raise ValueError('Independent nonzero raw equality failed')
    rejected = subprocess.run(COMMAND + ['convert', '-f', 'qcow2', '-O', 'vhdx', str(TEST / 'source.qcow2'), str(TEST / 'quota-rejected.vhdx')], capture_output=True, text=True, timeout=20, preexec_fn=quota, env={'PATH': '/usr/bin:/bin', 'HOME': str(TEST), 'LANG': 'C'})
    if rejected.returncode == 0 or len(rejected.stdout) + len(rejected.stderr) > 65536:
        raise ValueError('Output-limit rejection not demonstrated')
    files = [{'name': p.name, 'bytes': p.stat().st_size, 'SHA256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(TEST.iterdir()) if p.is_file()]
    if any(p['bytes'] > 1048576 for p in files if p['name'] == 'quota-rejected.vhdx'):
        raise ValueError('Output-limit fixture exceeded byte cap')
    print(json.dumps({'mode': 'NONZERO_OS_DISK_TOOL_ARTIFICIAL_TEST_ONLY', 'comparison': result, 'raw_bytes_equal': True, 'quota_rejection_returncode': rejected.returncode, 'quota_rejection_stderr': rejected.stderr, 'preserved_files': files, 'guest_or_research_code_executed': False, 'gate_ready': False}, indent=2))
