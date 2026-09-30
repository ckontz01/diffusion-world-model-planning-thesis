"""Executed via authenticated stdin only after the complete campaign.

I and CLIENT are injected by the operational one-shot finalizer. No worker or
approved source is edited. Output is a technical backup request, not timings.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tarfile
import time

began = time.monotonic()
P = Path
source, control, run = (P(I[key]) for key in ('source', 'control', 'run'))
sys.dont_write_bytecode = True
sys.path.insert(0, str(source))
os.environ.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1',
                  OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4')
resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
available = sorted(os.sched_getaffinity(0))
os.sched_setaffinity(0, available[:4])


def sha(path):
    h = hashlib.sha256()
    with P(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    with P(path).open('x') as stream:
        json.dump(value, stream, indent=2)


def size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


preserve = run/'final-preservation'
if preserve.exists() or (control/'client').exists():
    raise RuntimeError('exclusive finalization already exists; no repeat/archive retry')
if (run/'STOP.json').exists():
    raise RuntimeError('STOP is unresolved; finalization refused')
events = [json.loads(line) for line in (run/'DISPATCH.jsonl').read_text().splitlines()]
if len([e for e in events if e['event'] == 'all_complete']) != 1:
    raise RuntimeError('complete-grid dispatch gate absent/duplicate')
launch = json.loads((control/'CONTROLLER-PROCESS.json').read_text())
proc = P('/proc')/str(launch['pid'])/'stat'
if proc.exists():
    fields = proc.read_text().rsplit(')', 1)[1].split()
    if int(fields[19]) == launch['process']['start_ticks'] and fields[0] != 'Z':
        raise RuntimeError('exact campaign controller still alive; do not archive changing evidence')
if sha(control/'EXECUTION-APPROVAL.json') != I['enabled_approval_sha256'] or sha(control/'AUTHORIZATION.json') != I['authority_sha256']:
    raise RuntimeError('enabled approval/authority authentication differs')
from dtv_efficiency_r1.profile import gate
from dtv_efficiency_r1.control import load_bindings, DOC, ORIGINAL_DOC
gate(DOC/'BINDINGS.json', json.loads((control/'EXECUTION-APPROVAL.json').read_text()))
c = load_bindings()
if sha(DOC/'BINDINGS.json') != I['bindings_sha256']:
    raise RuntimeError('corrected overlay authentication differs')
terminal = [e for e in events if e['event'] == 'terminal']
submitted = [e for e in events if e['event'] == 'submitted']
if len(submitted) != 9 or len(terminal) != 9:
    raise RuntimeError('full-grid submission/terminal count differs')
result = subprocess.run(['sacct', '-n', '-P', '-X', '-j', ','.join(e['allocation_id'] for e in submitted),
                         '--format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'],
                        capture_output=True, text=True, timeout=30)
if result.returncode:
    raise RuntimeError('final exact-allocation accounting command fault: '+result.stderr)
rows = [line.split('|') for line in result.stdout.splitlines() if line.strip()]
for row in rows:
    if row[-1] == '':
        row.pop()
if len(rows) != 9 or len({row[0] for row in rows}) != 9:
    raise RuntimeError('final exact allocation row count differs')
for row in rows:
    matches = [e for e in terminal if e['allocation_id'] == row[0]]
    if len(matches) != 1:
        raise RuntimeError('unknown final allocation identity')
    e = matches[0]
    if row[1:] != ['dtveff0-'+e['task'], 'COMPLETED', '0:0', str(e['elapsed_seconds']), e['allocated_resources'], e['node']]:
        raise RuntimeError('final scheduler/ledger reconciliation differs')
# Reauthenticate bound files in place, without deserialization/inference.
inputs = {}
for job in c['jobs']:
    for model in job['models'].values():
        inputs[model['checkpoint']] = model['checkpoint_sha256']
    for value in (job['capture'], job['saved_scores'], job['offline_scores']):
        inputs[value['artifact']] = value['artifact_sha256']
    inputs[job['capture']['world_model_checkpoint']] = job['capture']['world_model_checkpoint_sha256']
for value in c['runtime']+json.loads((ORIGINAL_DOC/'FINAL-RECOVERY.json').read_text())['model_runtime_sources']:
    inputs[value['path']] = value['sha256']
for path, digest in inputs.items():
    if sha(path) != digest:
        raise RuntimeError('final bound input/runtime bytes differ: '+path)
preserve.mkdir()
client = control/'client'
client.mkdir()
for name, encoded in CLIENT.items():
    target = client/name
    if target.is_absolute() and not target.resolve().is_relative_to(client.resolve()):
        raise RuntimeError('unsafe operational member')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(base64.b64decode(encoded))
report = preserve/'REPORT.json'
accepted = subprocess.run(['/usr/bin/python3.9', '-m', 'dtv_efficiency_r1.accept',
                           '--run', str(run), '--output', str(report)],
                          capture_output=True, text=True, timeout=60)
if accepted.returncode:
    write(preserve/'ACCEPTANCE-FAILURE.json', dict(returncode=accepted.returncode,
          stdout=accepted.stdout, stderr=accepted.stderr, automatic_retry=False))
    raise RuntimeError('frozen independent acceptance failed; preserve and report: '+accepted.stderr)
from dtv_efficiency_r1.accept import validate
# The original validator has run once. Supplement metadata coverage without
# rerunning measurement or regenerating the report.
worker_names = {'PROFILE.json', 'SEAL.json', 'CONTROL-SEAL.json', 'RECORDS.jsonl',
                'EQUIVALENCE.jsonl', 'SUPERVISOR-STARTED.json', 'SUPERVISION.json'}
for job in c['jobs']:
    root = run/job['id']
    if {p.name for p in root.iterdir()} != worker_names or any(not p.is_file() for p in root.iterdir()):
        raise RuntimeError('unexpected/missing complete worker files')
    if size(root) > 4000000 or sum((run/(job['id']+suffix)).stat().st_size for suffix in ('.out', '.err')) > 2000000:
        raise RuntimeError('worker/log byte cap exceeded')
    value = json.loads((root/'PROFILE.json').read_text())
    expected = {(ctx, arm, level, block, rep) for ctx in job['context_indices']
                for arm in ('plain', 'acid', 'forward', 'legacy_dtv', 'd1_sigma025')
                for level in ('A', 'B', 'C') if not (arm == 'plain' and level == 'A')
                for block in range(5) for rep in range(2)}
    actual = [(r['context'], r['arm'], r['level'], r['block'], r['repetition'])
              for r in value['records'] if r.get('phase') == 'warm']
    if len(actual) != len(expected) or set(actual) != expected:
        raise RuntimeError('exact context and warm timing axes differ')
    phases = [(r.get('context'), r.get('arm'), r.get('phase')) for r in value['records'] if r['level'] == 'C']
    for ctx in job['context_indices']:
        for arm in ('plain', 'acid', 'forward', 'legacy_dtv', 'd1_sigma025'):
            if phases.count((ctx, arm, 'first_solve_before_equivalence_and_solver_warmup')) != 1 or phases.count((ctx, arm, 'post_equivalence_first_reset_call')) != 1:
                raise RuntimeError('first/reset solve evidence differs')
authentication = dict(status='independently_accepted_complete_grid', manifest_sha256=I['manifest_sha256'],
    bindings_sha256=I['bindings_sha256'], approval_sha256=I['enabled_approval_sha256'],
    authority_sha256=I['authority_sha256'], source_files=283, authenticated_bound_files=len(inputs),
    bound_input_deserialization=False, all_worker_seals_verified=True, all_journals_verified=True,
    workers=9, context_seed_cells=18, distinct_historical_contexts=6, methods=5,
    full_cem_solves=1260, warmed_timed_cem_solves=900, timing_interpreted_by_operator=False,
    final_scheduler=dict(command='sacct exact nine submitted IDs', stdout=result.stdout, stderr=result.stderr),
    allocations=terminal, gpu_allocation_seconds=sum(e['elapsed_seconds'] for e in terminal),
    report_sha256=sha(report), automatic_retry=False)
write(preserve/'AUTHENTICATION.json', authentication)
inventory = []
paths = []
for label, root in (('source', source), ('control', control), ('run', run)):
    for path in sorted(root.rglob('*')):
        if label == 'run' and preserve in path.parents:
            continue  # Self archive/request are not their own source inventory.
        if path.is_symlink():
            raise RuntimeError('symlink in final preserved roots')
        if path.is_file():
            paths.append((label+'/'+path.relative_to(root).as_posix(), path))
for path in (report, preserve/'AUTHENTICATION.json'):
    paths.append(('final/'+path.name, path))
for name, path in paths:
    inventory.append(dict(path=name, bytes=path.stat().st_size, sha256=sha(path)))
source_bytes = size(source)
worker_bytes = sum(size(run/j['id']) for j in c['jobs'])
log_bytes = sum((run/(j['id']+suffix)).stat().st_size for j in c['jobs'] for suffix in ('.out', '.err'))
other_bytes = size(control)+size(run)-worker_bytes-log_bytes
if source_bytes > 4000000 or other_bytes+300000 > 2000000 or source_bytes+size(run)+size(control)+300000 > 60000000:
    raise RuntimeError('complete source/control/live reservation exceeded')
manifest = preserve/'INVENTORY.json'
write(manifest, dict(files=inventory, source_manifest_sha256=I['manifest_sha256'],
      included_roots=['source', 'control', 'run', 'final'], bound_input_files_copied=False))
paths.append(('INVENTORY.json', manifest))
inventory.append(dict(path='INVENTORY.json', bytes=manifest.stat().st_size, sha256=sha(manifest)))
archive_path = preserve/'final.tar'
with archive_path.open('xb') as stream:
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for name, path in paths:
            if sha(path) != next(row['sha256'] for row in inventory if row['path'] == name):
                raise RuntimeError('source member changed during preservation')
            archive.add(path, arcname=name, recursive=False)
if archive_path.stat().st_size > 62000000:
    raise RuntimeError('archive byte ceiling exceeded; retain oversized archive')
request = dict(status='complete_grid_archive_ready', remote_archive=str(archive_path),
    manifest_sha256=I['manifest_sha256'], approval_sha256=I['enabled_approval_sha256'],
    archive_bytes=archive_path.stat().st_size, archive_sha256=sha(archive_path),
    archive_members=len(inventory), files=inventory, source_bytes=source_bytes,
    run_nonarchive_bytes=size(run)-archive_path.stat().st_size,
    control_bytes=size(control), other_control_report_bytes=other_bytes,
    report_sha256=sha(report), authentication_sha256=sha(preserve/'AUTHENTICATION.json'),
    finalization_wall_seconds=time.monotonic()-began, rss_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    cpu_threads_cap=4, ram_bytes_cap=8*1024**3, automatic_retry=False)
request_reserve = len(json.dumps(request, indent=2).encode())+256
if size(control)+size(run)-archive_path.stat().st_size-worker_bytes-log_bytes+request_reserve > 2000000:
    raise RuntimeError('complete control/report/request inventory exceeds metadata cap')
# Includes all currently stored roots and reservations for the SSD copy,
# source preparation export, local operational/publication copies and partials.
inclusive_reserved = size(source)+size(control)+size(run)+request_reserve+request['archive_bytes']+10000000+2000000
if inclusive_reserved > 250000000:
    raise RuntimeError('inclusive new artifacts/reservation ceiling exceeded')
request['inclusive_bytes_with_local_copy_reservations'] = inclusive_reserved
write(preserve/'BACKUP-REQUEST.json', request)
print(json.dumps(request))
