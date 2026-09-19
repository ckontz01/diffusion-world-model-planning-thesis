"""Final technical receipt only. No scientific report/array reads or scheduler calls.

Run on Prometheus with the accepted immutable source on sys.path. This is not
an experimental worker, new scientific gate, or replacement aggregate.
"""
import json
import sys
sys.dont_write_bytecode = True
import time
from collections import Counter
from pathlib import Path

BASE = Path('/lustreFS/data/superworld/ckontzias/thesis')
SOURCE = BASE / 'snapshots/local-goal-proposals-20260918-b54a55b16bcb83a5'
RUN = BASE / 'experiments/local-goal-proposals-20260918/run-b54a55b16bcb83a5'
CONTROL = BASE / 'staging/lgp1-policy-recovery-b54a55b16bcb83a5'
sys.path.insert(0, str(SOURCE / 'cluster/prometheus'))
import lgp1_contract as c
import lgp1_policy_recovery as recovery
from lgp1_verify import task


def main():
    began = time.monotonic()
    a = c.authorize(SOURCE, RUN / 'APPROVAL.json')
    c.require(a == c.read(CONTROL / 'EXECUTION-APPROVAL.json'), 'Upload/canonical approval semantics')
    c.require(c.sha(CONTROL / 'EXECUTION-APPROVAL.json') ==
              'b10ba2f2de17efbb177114a94214023bdebad75c4d158b3aaa78a907fbe50df2', 'Uploaded approval hash')
    c.require(a['source_sha256'] == 'b54a55b16bcb83a5092f15703a63fadb81fdbce3fa91f4e6a21b907c934cf361', 'Source pin')
    c.require(a['input_sha256'] == 'b21bac97520696b8bb2008a3cfef3f5188d4c59dd117bc158cc2fe2e86ff5aaa', 'Input pin')
    c.require(not (RUN / 'STOP.json').exists(), 'No current stop')
    lock = c.authenticate_inputs(SOURCE, payload=False)
    specs = c.execution_grid(SOURCE, a)
    frozen = recovery.verify_reuse(specs, a)
    c.require(c.sha(RUN / 'PRE-EVALUATION-FREEZE.json') == recovery.FREEZE, 'Copied original freeze')
    complete = c.read(RUN / 'COMPUTE-COMPLETE.json')
    rows = complete['completed']
    c.require(complete['jobs'] == len(rows) == len(specs) == 204, '204 successful coordinates')
    c.require({r['task']['name'] for r in rows} == {s['name'] for s in specs}, 'Exact full grid')
    c.require(len({r['job'] for r in rows}) == 204, 'Unique successful allocations')
    c.require(all(r['state'] == 'COMPLETED' and r['exit_code'] == '0:0' for r in rows), 'Terminal success')
    by_name = {r['task']['name']: r for r in rows}
    receipts = []
    for spec in specs:
        root = c.task_root(RUN, spec)
        meta = task(root, spec)
        origin = c.read(root.parent / 'APPROVAL.json')
        c.require(meta['source_sha256'] == origin['source_sha256'] and
                  meta['approval_sha256'] == c.sha(root.parent / 'APPROVAL.json') and
                  origin['input_sha256'] == a['input_sha256'], 'Worker source/approval/input lineage')
        allocation = by_name[spec['name']]
        c.require(allocation['task'] == spec and allocation['alloc_cpus'] == 4 and
                  allocation['seconds'] <= spec['seconds'], 'Exact task/resources')
        c.require(('gres/gpu=1' in allocation['alloc_tres']) == spec['gpu'], 'GPU allocation contract')
        c.require(('mem=24G' if spec['gpu'] else 'mem=8G') in allocation['alloc_tres'], 'Memory allocation contract')
        if spec['kind'] in ('technical', 'evaluation'):
            c.require(c.size(root) <= 2 * c.CAPS['episode_bytes'], 'Pair storage bound')
        receipts.append(dict(name=spec['name'], job=allocation['job'], root=str(root),
                             seal=c.sha(root / 'sha256.txt'), metadata=meta,
                             allocation_seconds=allocation['seconds'], bytes=c.size(root)))
    dispatch = [json.loads(s) for s in (RUN / 'DISPATCH.jsonl').read_text().splitlines()]
    submitted = [r for r in dispatch if r['event'] == 'submitted']
    c.require(len(submitted) == 197 and not any(r['task']['kind'] in ('cache', 'fit') for r in submitted), 'No repeated cache/fits')
    c.require(len({r['job'] for r in submitted}) == 197, 'Unique current submissions')
    gate = c.read(RUN / 'TECHNICAL-STAGE-PASSED.json')
    c.require(gate['performance_selection'] is False and len(gate['tasks']) == 4, 'Technical-only gate')
    for name, digest in gate['seals'].items():
        c.require(c.sha(RUN / name / 'sha256.txt') == digest and by_name[name]['unix'] <= gate['unix'], 'Technical seal/order')
    main_sub = [r for r in submitted if r['task']['kind'] == 'evaluation']
    c.require(len(main_sub) == 192 and all(r['unix'] > gate['unix'] > frozen['unix'] for r in main_sub), 'Freeze/gate/main order')
    analysis_sub = next(r for r in submitted if r['task']['kind'] == 'analysis')
    c.require(analysis_sub['unix'] > max(r['unix'] for r in rows if r['task']['kind'] == 'evaluation'), 'Analysis after main completion')
    failures = {job: v for job, v in recovery.JOBS.items() if v[0] == 'FAILED'}
    c.require(set(failures) == {'301977', '301980', '301987'}, 'Three historical failures')
    gpu = sum(r['seconds'] for r in rows if r['task']['gpu']) + sum(int(v[2]) for v in failures.values())
    cpu = sum(r['seconds'] for r in rows if not r['task']['gpu'])
    c.require(gpu == complete['gpu_seconds'] == 15615 and cpu == complete['cpu_seconds'] == 16, 'All charges reconciled')
    c.require(complete['attempts_including_prior'] == 207 and complete['gpu_attempts_including_prior'] == 206, 'Attempt counts')
    c.require(gpu <= c.CAPS['gpu_seconds'] and cpu <= c.CAPS['cpu_seconds'], 'Time caps')
    c.require(sum(r['metadata'].get('updates', 0) for r in receipts) == 72000 and
              sum(r['metadata'].get('row_presentations', 0) for r in receipts) == 9216000, 'Unique training budget')
    c.require(sum(r['metadata'].get('episodes', 0) for r in receipts) == 392, '384 main plus eight technical episodes')
    sources = [('current-source', SOURCE)] + [(n, p) for n, p in c.preserved_paths(RUN) if n.endswith('-source')]
    preserved_seals = {}
    for name, path in sources:
        c.verify(path, 'LGP1-SOURCE-MANIFEST.sha256')
        preserved_seals[name] = c.sha(path / 'LGP1-SOURCE-MANIFEST.sha256')
    for name, path in c.preserved_paths(RUN):
        if name.endswith('-run'):
            for seal in path.rglob('sha256.txt'):
                c.verify(seal.parent)
                preserved_seals[str(seal)] = c.sha(seal)
    c.require(c.sha(recovery.PRIOR / 'DISPATCH.jsonl') == recovery.LEDGER, 'Historical ledger unchanged')
    receipt = dict(verified=True, scientific_reports_opened=False, scientific_arrays_opened=False,
        scheduler_repolled=False, source_sha256=a['source_sha256'], input_sha256=a['input_sha256'],
        canonical_approval_sha256=c.sha(RUN / 'APPROVAL.json'), uploaded_approval_sha256=c.sha(CONTROL / 'EXECUTION-APPROVAL.json'),
        freeze_sha256=recovery.FREEZE, aggregate_seal_sha256=c.sha(RUN / 'analysis/sha256.txt'),
        compute_complete_sha256=c.sha(RUN / 'COMPUTE-COMPLETE.json'), dispatch_sha256=c.sha(RUN / 'DISPATCH.jsonl'),
        successful_coordinates=204, attempts=207, gpu_attempts=206, cpu_attempts=1,
        gpu_allocation_seconds=gpu, cpu_allocation_wall_seconds=cpu, historical_failures=failures,
        counts_by_kind=dict(Counter(s['kind'] for s in specs)), unique_updates=72000,
        unique_training_row_presentations=9216000, optimizer_updates_policy_recovery=0,
        model_freeze_unix=frozen['unix'], technical_gate_unix=gate['unix'], first_main_unix=min(r['unix'] for r in main_sub),
        analysis_submission_unix=analysis_sub['unix'], analysis_recorded_terminal_unix=by_name['analysis']['unix'],
        authenticated_nonpayload_input_files=len(set(lock['files']) - set(lock['payload_files'])),
        preserved_source_and_worker_seals=preserved_seals, workers=receipts, storage=c.storage(SOURCE, RUN),
        verification_wall_seconds=time.monotonic()-began, unix=time.time())
    c.write(CONTROL / 'FINAL-AUTHENTICATION-20260919.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('workers', 'preserved_source_and_worker_seals')}))


if __name__ == '__main__':
    main()
