"""Bounded final preservation routing; no compute, retry or result inspection."""
import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R4 = HERE.parent / 'recovery-r4'
spec = importlib.util.spec_from_file_location('frozen_r4_transport', R4 / 'transport.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


def exclusive_receipt(label, action):
    path = HERE / (label + '.json')
    if path.exists():
        raise RuntimeError('exclusive receipt exists; no retry')
    start = time.monotonic()
    try:
        result = action()
        value = dict(returncode=result.returncode,
                     stdout=result.stdout.decode(errors='replace'),
                     stderr=result.stderr.decode(errors='replace'),
                     wall_seconds=time.monotonic()-start, automatic_retry=False)
    except subprocess.TimeoutExpired as exc:
        value = dict(returncode=None, stdout=(exc.stdout or b'').decode(errors='replace'),
                     stderr=(exc.stderr or b'').decode(errors='replace'),
                     wall_seconds=time.monotonic()-start, ambiguous_transport=True,
                     automatic_retry=False)
    with path.open('x', encoding='utf-8') as output:
        json.dump(value, output, indent=2)
    print(json.dumps(dict(receipt=str(path), returncode=value['returncode'],
                          wall_seconds=value['wall_seconds'])))
    if value['returncode'] != 0:
        raise RuntimeError('preserved fault; inspect receipt, never retry blindly')
    print(value['stdout'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['archive', 'backup'])
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    identity = json.loads((R4 / 'IDENTITIES.json').read_text())
    command = ['wsl.exe', '-d', 'Thesis-Ubuntu', '-u', 'chris', '--',
               'ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
               'prometheus', 'python3.9 -']
    if args.mode == 'archive':
        inner = '''
import json,sys
sys.dont_write_bytecode=True
from dtv_success_cost_r4.common import recovery_gate
from dtv_success_cost_r4.preserve import archive_bounded
from dtv_success_cost.preserve import validate_request
c,r=recovery_gate(APPROVAL)
from dtv_success_cost.common import run_namespace,load
run=run_namespace(c);location=run/'final-preservation'
if location.exists():
    request=load(location/'BACKUP-REQUEST.json')
    validate_request(request,(location/'BACKUP-REQUEST.json').as_posix(),c)
    if not (location/'final.tar').is_file():raise RuntimeError('existing preservation incomplete; retain, do not recreate')
    status='existing_archive_not_recreated'
else:
    request=archive_bounded(c,run);status='archive_created_verified_once'
print(json.dumps(dict(status=status,archive=request['archive'],
    acceptance={k:v for k,v in request['acceptance'].items() if k not in ('allocations','actual_allocations')},
    archive_wall_seconds=request['archive_wall_seconds'],scientific_results_opened=False)))
'''.replace('APPROVAL', repr(identity['recovery_control'] + '/EXECUTION-APPROVAL.json'))
        base = transport.BASE.replace('IDENTITY_PLACEHOLDER', repr(identity))
        script = base + '\nsetup_imports()\n' + '''
env=dict(os.environ,PYTHONPATH=':'.join(str(x) for x in (source,r3source,r2source,r1source,science)),
    PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
result=subprocess.run([I['control_python'],'-B','-c',INNER],cwd=source,env=env,capture_output=True,timeout=7250)
sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr)
raise SystemExit(result.returncode)
'''.replace('INNER', repr(inner))
        exclusive_receipt(args.label, lambda: subprocess.run(command, input=script.encode(),
                          capture_output=True, timeout=7350))
    else:
        approval = HERE.parent / 'execution-v1/EXECUTION-APPROVAL-WINDOWS.json'
        request = identity['run'] + '/final-preservation/BACKUP-REQUEST.json'
        exclusive_receipt(args.label, lambda: subprocess.run(
            [sys.executable, '-B', '-m', 'dtv_success_cost.preserve', 'backup',
             '--approval', str(approval), '--request', request],
            cwd=ROOT, capture_output=True, timeout=7350))


if __name__ == '__main__':
    main()
