"""Publish the complete fixed result only from the verified SSD archive."""
import hashlib
import json
from pathlib import Path
import statistics
import tarfile
from finalize import HERE, sha, write

request = json.loads((HERE/'BACKUP-REQUEST.json').read_text())
preserved = json.loads((HERE/'BACKUP-VERIFIED.json').read_text())
if preserved['status'] != 'verified' or not preserved['whole_archive_verified'] or not preserved['every_member_verified']:
    raise RuntimeError('preservation gate has not passed')
if preserved['request_sha256'] != sha(HERE/'BACKUP-REQUEST.json'):
    raise RuntimeError('preservation request binding differs')
archive_path = Path(preserved['destination'])
if sha(archive_path) != request['archive_sha256']:
    raise RuntimeError('verified archive changed before publication')
root = HERE.parent/'completion-r1'
if root.exists():
    raise RuntimeError('exclusive completion publication already exists')
root.mkdir()
with tarfile.open(archive_path, 'r:') as archive:
    def read(name):
        data = archive.extractfile(name).read()
        expected = next(row for row in request['files'] if row['path'] == name)
        if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            raise RuntimeError('sealed publication member differs')
        return json.loads(data)
    report = read('final/REPORT.json')
    auth = read('final/AUTHENTICATION.json')
    bindings = read('source/docs/dtv-efficiency-20260930/BINDINGS.json')
    profiles = [read('run/'+job['id']+'/PROFILE.json') for job in bindings['jobs']]
    supervisors = {job['id']: read('run/'+job['id']+'/SUPERVISION.json') for job in bindings['jobs']}

if report['status'] != 'complete_fixed_grid' or report['models_promoted'] or report['next_stage_authorized'] or report['science_outcomes']:
    raise RuntimeError('fixed scientific reporting contract differs')
arms = ('plain', 'acid', 'forward', 'legacy_dtv', 'd1_sigma025')
cells = report['comparisons']
ops = []
offline = []
first = []
for job, profile in zip(bindings['jobs'], profiles):
    records = profile['records']
    calls = [row for row in records if 'cuda_peak_allocated_bytes' in row]
    ops.append(dict(job=job['id'], task=job['task'], scorer_seed=job['scorer_seed'],
                    historical_contexts=job['contexts'], context_indices=job['context_indices'],
                    allocation_id=profile['slurm_allocation_id'], python=profile['python'], torch=profile['torch'],
                    gpu=profile['gpu'], hostname=profile['hostname'], gpu_properties=profile['gpu_properties'],
                    authentication_seconds=profile['authentication_seconds'], setup_seconds=profile['setup_seconds'],
                    child_wall_seconds=profile['wall_seconds'], supervisor=supervisors[job['id']],
                    child_rss_high_water_bytes=profile['rss_high_water_bytes'],
                    torch_peak_allocated_bytes=max(row['cuda_peak_allocated_bytes'] for row in calls),
                    torch_peak_reserved_bytes=max(row['cuda_peak_reserved_bytes'] for row in calls),
                    timed_call_process_cpu_seconds=sum(row['process_cpu_seconds'] for row in calls),
                    timed_call_cpu_scope='Only measured calls, not total worker/setup/audit CPU'))
    offline.extend(dict(job=job['id'], **row) for row in records if row['level'] == 'A_offline_reconciliation')
    first.extend(dict(job=job['id'], **row) for row in records
                 if row.get('phase') != 'warm' and row['level'] != 'A_offline_reconciliation')

complete = dict(fixed_report=report, authentication=auth, operations=ops,
                first_call_audit_and_boundary_records=first, offline_records=offline,
                preservation=preserved, archive_request_metadata={k:v for k,v in request.items() if k != 'files'},
                raw_warm_samples='All exact RECORDS.jsonl and PROFILE.json members in the verified archive',
                interpretations=dict(contexts_are_six_not_eighteen=True,
                    tails_are_descriptive=True, checker_only_offline_is_not_online_latency=True,
                    level_C_excludes_raw_preprocessing_physical_decoding_and_physics=True,
                    audit_scopes_overlap_first_calls=True, no_overlapping_timer_subtraction=True,
                    no_training_energy_whole_device_memory_or_success_claim=True,
                    no_promotion_or_next_stage=True))
with (root/'COMPLETE-RESULTS.json').open('x', encoding='utf-8') as stream:
    json.dump(complete, stream, separators=(',', ':'))
write(root/'AUTHENTICATION.json', auth)
write(root/'PRESERVATION.json', preserved)

def num(value):
    return f'{value:.6f}'

# Full, unfiltered comparison matrix: every warmed A/B/C event/wall cell.
lines = ['# DTV-EFF0 complete timing cells', '',
         'All 504 comparison rows are retained. A has no plain checker. Each summary has ten samples from five blocks and two repetitions. Ratios use ACID divided by the listed arm; saved milliseconds and fractions use ACID minus the arm. Quantiles are descriptive.', '',
         '| Worker | Context | Level | Measurement | Arm | n | Median ms | q25 ms | q75 ms | p95 ms | p99 ms | ACID / arm | Saved ms | Saved fraction | Five block fractions | Utility cell |',
         '| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |']
for cell in cells:
    s = cell['summary']
    lines.append('| '+' | '.join([cell['job'], str(cell['context']), cell['level'], cell['metric'], cell['arm'], str(s['n']),
        *[num(s[key]) for key in ('median','q25','q75','p95','p99')], num(cell['acid_over_arm_ratio']),
        num(cell['absolute_ms_saved']), num(cell['fraction_saved']), ', '.join(num(x) for x in cell['block_fractions']),
        str(cell['utility_cell_pass'])])+' |')
with (root/'TIMING-CELLS.md').open('x', encoding='utf-8') as stream:
    stream.write('\n'.join(lines)+'\n')

wall_C = [row for row in cells if row['level'] == 'C' and row['metric'] == 'synchronized_wall_ms']
screen = report['frozen_utility_screen']
summary_lines = ['# DTV-EFF0 fixed saved-input timing results', '',
    'All nine workers completed and passed independent full-grid acceptance. The new study archive was transferred once to the designated SSD and verified as a whole file and member by member before its timing findings were opened. No worker was retried or omitted.', '',
    'The frozen complete-CEM utility screen requires at least 10% synchronized-wall median saving against ACID in every task/seed/context cell and at least 10% saving in four of five blocks in each cell. Legacy DTV: **'+('passes' if screen['legacy_dtv'] else 'does not pass')+'**. D1 sigma 0.25: **'+('passes' if screen['d1_sigma025'] else 'does not pass')+'**. Failure of this demanding screen does not establish exactly zero saving.', '',
    '## Complete CEM comparison', '',
    'Every method remains visible below. Values are warmed synchronized-wall medians in milliseconds. The percentage columns compare the two diffusion controls with ACID, and preserve negative and small differences.', '',
    '| Worker | Context | Plain ms | ACID ms | Forward ms | Legacy DTV ms | D1 sigma025 ms | Legacy saving % | D1 saving % | Legacy blocks >=10% | D1 blocks >=10% |',
    '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
for job in bindings['jobs']:
    for ctx in job['context_indices']:
        by_arm = {row['arm']: row for row in wall_C if row['job'] == job['id'] and row['context'] == ctx}
        summary_lines.append('| '+' | '.join([job['id'], str(ctx),
            *[num(by_arm[arm]['summary']['median']) for arm in arms],
            num(100*by_arm['legacy_dtv']['fraction_saved']), num(100*by_arm['d1_sigma025']['fraction_saved']),
            str(sum(x >= .1 for x in by_arm['legacy_dtv']['block_fractions'])),
            str(sum(x >= .1 for x in by_arm['d1_sigma025']['block_fractions']))])+' |')
summary_lines.extend(['', '## Measurement boundaries and full evidence', '',
    'A measures the checker alone; B measures the complete world-model cost call; C measures the original complete CEM solve from saved preprocessed observations/history/goal to returned planner actions. C excludes raw-image preprocessing, physical action decoding and physics, so it is not episode latency. Event timings and synchronized-wall timings are reported separately in [the complete 504-row matrix](TIMING-CELLS.md) and [the complete machine-readable result](COMPLETE-RESULTS.json).', '',
    'The separate offline lane retains all 54 records: ACID, forward and legacy DTV, two repetitions per worker over 15,000 candidate sequences/75,000 transitions with chunk 8,192. It is not online planning latency and cannot alone advance this line. All setup/first/reset calls, equivalence/warmup audit scopes, empty-boundary controls, offline records and operation scopes are in COMPLETE-RESULTS.json. Exact warmed samples and all journals remain unchanged in the verified archive.', '',
    'The grid uses two fixed historical contexts per task and three existing scorer seeds: six distinct contexts, not 18 independent task situations. Every warmed timing cell has five balanced blocks and two repetitions. The workload is 1,260 CEM solves, including 900 warmed timed solves. Checkpoint weights, normalization, RNG, precision, batch/chunk conventions and original scorer/CEM functions were unchanged.', '',
    'The historical ACID reconstruction remains explicitly disclosed. No new calibration or fastest-seed selection occurred. Empirical p95/p99 estimates from ten repeated calls per warmed cell are descriptive, not deployment-tail guarantees.', '',
    '## Allocation and operation costs', '',
    '| Worker | Allocation | GPU allocation s | Authentication s | Model loading/setup s | Child wall s | Child RSS bytes | Torch peak allocated bytes | Torch peak reserved bytes |',
    '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |'])
for op in ops:
    charge = next(row['elapsed_seconds'] for row in auth['allocations'] if row['task'] == op['job'])
    summary_lines.append('| '+' | '.join([op['job'], op['allocation_id'], str(charge),
        num(op['authentication_seconds']), num(op['setup_seconds']), num(op['child_wall_seconds']),
        str(op['child_rss_high_water_bytes']), str(op['torch_peak_allocated_bytes']), str(op['torch_peak_reserved_bytes'])])+' |')
summary_lines.extend(['',
    f"Actual total GPU allocation charge is {report['allocation_seconds']} seconds ({report['allocation_seconds']/60:.3f} minutes), including every attempt; the ceiling is 7,200 seconds. All nine allocations were COMPLETED 0:0 on gpu09 with one RTX 6000 Ada, four CPUs and 8 GiB. The pinned workers used Python 3.11.10 and torch 2.5.1+cu121. There were no failed allocations, retries, requeues or extra probes.", '',
    'Authentication seconds run from the entry/start boundary through authentication, imports and hardware checks; model loading/setup is reported separately. The context audit/warmup scope overlaps first calls. Output fingerprinting is outside the warmed hot-call timers. No overlapping timers were subtracted. Timed process CPU totals cover measured calls only, not total worker CPU. Child RSS excludes the supervisor; Torch allocated/reserved counters are scoped allocator high-water marks, not whole-device memory.', '',
    '## Authentication and preservation', '',
    'Enabled approval: `'+auth['approval_sha256']+'`. Source manifest: `'+auth['manifest_sha256']+'`. Binding overlay: `'+auth['bindings_sha256']+'`. Full launch authority, exact PID/start identity and source/input hashes remain in the execution records.', '',
    f"Final archive: {request['archive_bytes']:,} bytes / {request['archive_members']} members; SHA256 `{request['archive_sha256']}`. Destination: `{preserved['destination']}`. Whole archive and every expected member verified. Only this new study was transferred; no checkpoint/input copies or historical-study archives were included.", '',
    'All source, authorization, approval, controller/submission/accounting records, profiles, journals, seals, complete fixed report and archive inventory are preserved. The independent validator checked exact grid/allocations, hardware/runtime, seals, journal consistency, equivalence, warmed cells, offline workloads and byte/time limits. All 167 exact input/runtime bindings were reauthenticated in place without inference.', '',
    '## Scope of the conclusion', '',
    'These are fixed saved-input timing comparisons, not training-cost, energy, whole-device-memory or closed-loop-success measurements. Historical success rates are not attached to these timings. Plain and deterministic-forward costs remain comparators. No model is promoted and no next experiment, fitting, physics, new source access or monitor is authorized. ACV0, ACVM1, historical closures, reserved data and E12 remain unchanged.', ''])
with (root/'RESULTS-20260930.md').open('x', encoding='utf-8') as stream:
    stream.write('\n'.join(summary_lines))
print(json.dumps(dict(status='complete_fixed_result_published_after_preservation',
    utility_screen=screen, allocation_seconds=report['allocation_seconds'],
    legacy_C_wall_median_saving_range=[min(r['fraction_saved'] for r in wall_C if r['arm']=='legacy_dtv'),max(r['fraction_saved'] for r in wall_C if r['arm']=='legacy_dtv')],
    d1_C_wall_median_saving_range=[min(r['fraction_saved'] for r in wall_C if r['arm']=='d1_sigma025'),max(r['fraction_saved'] for r in wall_C if r['arm']=='d1_sigma025')],
    publication_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
    output=str(root)), indent=2))
