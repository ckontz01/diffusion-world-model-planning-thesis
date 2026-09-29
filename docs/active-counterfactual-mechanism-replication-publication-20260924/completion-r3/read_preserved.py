"""Present the sealed ACVM1 analysis only after whole/member SSD verification.

Uses standard-library presentation arithmetic only. Does not invoke a model,
physics, fitting, bootstrap, scheduler or the completed analysis entry point.
"""
import collections
import hashlib
import json
from pathlib import Path
import tarfile
import time

HERE = Path(__file__).resolve().parent
SSD = Path('D:/THESIS-BACKUPS/active-counterfactual-mechanism-replication-v1/run-9f91156fd11a5d54')
SCIENCE = '9f91156fd11a5d54172e8cec79d37ca50199c132780b5aee3636f34b0dd2e916'
APPROVAL = '22cf11af0742c4a17987d783cf984c313dfc45beaff2a7ba32d1b2c6f36f3d27'
RECOVERY = '59e41de0f12c14af9eaba86b74e8699d3151b6e0e45554627864b54bc4466741'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with (HERE / name).open('xb') as stream:
        stream.write(raw)


def main():
    started = time.monotonic()
    request_raw = (SSD / 'REQUEST.json').read_bytes()
    gate_raw = (SSD / 'BACKUP-VERIFIED.json').read_bytes()
    request, gate = json.loads(request_raw), json.loads(gate_raw)
    assert request['schema'] == 'ACVM1-backup-v1'
    assert request['package'] == SCIENCE and request['approval'] == APPROVAL
    assert gate['request'] == sha(request_raw)
    assert gate['archive'] == request['archive_identity']
    assert gate['archive']['members'] == len(request['members'])
    assert gate['archive']['bytes'] == (SSD / 'final.tar').stat().st_size
    assert not (SSD / 'final.tar.partial').exists()
    assert not (SSD / 'BACKUP-FAILURE.json').exists()
    assert gate['volume']['FileSystemLabel'] == 'THESIS_SSD'
    assert '0a2f1ba9-0000-0000-0000-100000000000' in gate['volume']['UniqueId'].lower()
    first_read_unix = time.time()
    with tarfile.open(SSD / 'final.tar', 'r:') as archive:
        def raw(name):
            value = archive.extractfile(name).read()
            assert request['members'][name] == {'bytes': len(value), 'sha256': sha(value)}
            return value

        def get(name):
            return json.loads(raw(name))

        acceptance_raw = raw('r3_control/FINAL-ACCEPTANCE.json')
        accepted = json.loads(acceptance_raw)
        assert sha(acceptance_raw) == request['acceptance']
        assert accepted['tasks'] == accepted['successful_tasks'] == 8197
        assert accepted['episodes'] == 8192 and accepted['sources'] == 512
        assert accepted['attempts'] == 8199 and accepted['recovery_manifest'] == RECOVERY
        report_raw = raw('run/analysis/REPORT.json')
        report = json.loads(report_raw)
        write('REPORT.json', report_raw)
        write('FINAL-ACCEPTANCE.json', acceptance_raw)
        copies = {
            'COMPUTE-COMPLETE.json': 'r3_control/COMPUTE-COMPLETE.json',
            'MODEL-FREEZE.json': 'run/ALL-MODELS-FROZEN.json',
            'TECHNICAL-TRANCHE-PASSED.json': 'run/TECHNICAL-TRANCHE-PASSED.json',
            'ANALYSIS-TECHNICAL.json': 'run/analysis/TECHNICAL.json',
        }
        for target, member in copies.items():
            write(target, raw(member))
        fits, fit_technical = {}, {}
        for name in request['members']:
            if name.startswith('run/fit-') and name.endswith('/FIT.json'):
                fits[name.split('/')[1]] = get(name)
                fit_technical[name.split('/')[1]] = get(name.rsplit('/', 1)[0] + '/TECHNICAL.json')
        assert len(fits) == 4
        assert sorted(v['seed'] for v in fits.values()) == [94411, 94412, 94421, 94422]
        assert all(v['updates'] == 192 and len(v['trace']) == 192 for v in fits.values())
        write('FIT-RECORDS.json', fits)
        write('FIT-TECHNICAL.json', fit_technical)
        write('REUSED-FIT-RECORDS.json', {name: get('run/reused/' + name) for name in
              ('ORIGINAL-JOINT-FIT.json', 'ORIGINAL-ORDINARY-FIT.json', 'PREPROCESSING.json')})
        scheduler_records = raw('r3_control/SCHEDULER.jsonl').splitlines()
        final_scheduler = json.loads(scheduler_records[-1])
        assert final_scheduler['label'] == 'independent-R3-final-acceptance'
        assert final_scheduler['returncode'] == 0
        write('FINAL-SCHEDULER.json', final_scheduler)
        rows = []
        for line in final_scheduler['stdout'].splitlines():
            values = line.split('|')
            if values[-1] == '':
                values.pop()
            assert len(values) == 12
            rows.append(dict(job=values[0], key=values[1].removeprefix('acvm1-'), state=values[2], exit=values[3],
                             allocation_seconds=int(values[4]), cpus=int(values[5]), allocated_resources=values[6],
                             node=values[7], partition=values[8], qos=values[9], account=values[10], minutes=int(values[11])))
        assert len(rows) == len({v['job'] for v in rows}) == 8199
        successful = {v['key']: v for v in rows if v['state'] == 'COMPLETED' and v['exit'] == '0:0'}
        assert len(successful) == 8197
        failed = [v for v in rows if v['key'] not in successful or v['job'] != successful[v['key']]['job']]
        assert [v['job'] for v in failed] == ['304589', '304591']
        assert sum(v['allocation_seconds'] for v in rows if v['key'].startswith('evaluate-')) == accepted['gpu_seconds']
        assert sum(v['allocation_seconds'] for v in rows if not v['key'].startswith('evaluate-')) == accepted['cpu_seconds']
        write('ACCOUNTING.json', dict(allocations=rows, gpu_seconds=accepted['gpu_seconds'], cpu_stage_seconds=accepted['cpu_seconds'],
                                      successful_unique_tasks=8197, attempts=8199, failed_attempts=failed))
        decisions = []
        for evidence in report['evidence']:
            source, pair, arm = evidence['identity']
            key = f'evaluate-{source}-{arm}' + ('' if pair is None else f'-pair{pair}')
            meta = get('run/' + key + '/EVIDENCE.json')
            assert [meta['reference'], meta['pair'], meta['control']] == evidence['identity']
            decisions.append(dict(task=key, identity=evidence['identity'], branches=meta['branches']))
        assert len(decisions) == 8192
        write('ALL-DECISIONS.json', decisions)
    write('BACKUP-VERIFIED.json', gate_raw)
    root_bytes = collections.Counter()
    task_bytes = collections.Counter()
    for name, info in request['members'].items():
        root_bytes[name.split('/')[0]] += info['bytes']
        parts = name.split('/')
        if parts[0] == 'run' and len(parts) > 2:
            task_bytes[parts[1]] += info['bytes']
    eval_bytes = sum(value for key, value in task_bytes.items() if key.startswith('evaluate-'))
    group_bytes = sum(root_bytes.values()) - eval_bytes
    assert group_bytes <= 1_000_000_000 and sum(root_bytes.values()) <= 18_000_000_000
    assert gate['archive']['bytes'] <= 18_500_000_000
    assert all(value <= 2_000_000 for key, value in task_bytes.items() if key.startswith('evaluate-'))
    assert all(value <= 150_000_000 for key, value in root_bytes.items() if key.endswith('_control'))
    ssd_study_bytes = sum(path.stat().st_size for path in SSD.parent.rglob('*') if path.is_file())
    # One GB additionally reserves remote preservation manifests/receipts and local publication.
    inclusive_bound = sum(root_bytes.values()) + gate['archive']['bytes'] + ssd_study_bytes + 1_000_000_000
    assert inclusive_bound <= 80_000_000_000
    write('PRESERVATION.json', dict(first_scientific_read_unix=first_read_unix, opened_after_verified_preservation=True,
                                    ssd=str(SSD), archive=gate['archive'], request_sha256=sha(request_raw),
                                    verification_sha256=sha(gate_raw), acceptance_sha256=request['acceptance'],
                                    archive_wall_seconds=request['archive_wall_seconds'], transfer_and_verification_wall_seconds=gate['wall_seconds'],
                                    root_member_bytes=dict(root_bytes), input_member_bytes=sum(root_bytes.values()), historical_study_transfers=0,
                                    evaluation_worker_bytes=eval_bytes, other_member_bytes=group_bytes,
                                    ssd_entire_study_logical_bytes=ssd_study_bytes, inclusive_bytes_upper_bound=inclusive_bound,
                                    publication_read_wall_seconds=time.monotonic()-started, report_sha256=sha(report_raw)))
    refs, arms, outcomes, early = report['ordered_sources'], report['arms'], report['successes'], report['early_successes']
    assert len(refs) == len(set(refs)) == len(outcomes) == len(early) == 512
    assert arms == ['static', 'committed_feedback', 'no_update', 'active', 'ordinary']
    assert report['seed_pairs'] == [[94011, 94012], [94411, 94412], [94421, 94422]]
    assert all(len(source) == 3 and all(len(seed) == 5 and set(seed) <= {0, 1} for seed in source) for source in outcomes)
    assert set(early) <= {0, 1}
    expected_names = ['active-minus-no_update', 'active-minus-committed_feedback', 'committed_feedback-minus-static',
                      'no_update-minus-static', 'feedback-by-prefix-interaction', 'active-minus-ordinary', 'active-minus-early-replan']
    assert set(report['estimator']['contrasts']) == set(expected_names)
    for i, source in enumerate(outcomes):
        expected = []
        for static, feedback, no_update, active, ordinary in source:
            expected.append([active-no_update, active-feedback, feedback-static, no_update-static,
                             active-no_update-feedback+static, active-ordinary, active-early[i]])
        for k, name in enumerate(expected_names):
            observed = report['estimator']['contrasts'][name]
            assert observed['source_by_seed_effects'][i] == [pair[k] for pair in expected]
            assert abs(observed['source_effects'][i] - sum(pair[k] for pair in expected)/3) < 1e-12
    by_arm = {}
    for index, arm in enumerate(arms):
        totals = [sum(source[pair][index] for source in outcomes) for pair in range(3)]
        by_arm[arm] = dict(successes_by_pair=totals, episodes_by_pair=512, successes_total=sum(totals),
                           episodes_total=1536, fixed_pair_average_success_rate=sum(totals)/1536)
    by_arm['early-replan'] = dict(successes_total=sum(early), episodes_total=512, success_rate=sum(early)/512,
                                 reused_only_algebraically=True)
    source_table = [dict(reference=reference, success_by_pair=outcomes[i], early_success=early[i],
                         effects={name: value['source_effects'][i] for name, value in report['estimator']['contrasts'].items()})
                    for i, reference in enumerate(refs)]
    write('ALL-SOURCE-RESULTS.json', source_table)
    write('ALL-EPISODES.json', report['evidence'])
    technical = dict(report['resources'], **fit_technical)
    technical['analysis'] = json.loads((HERE / 'ANALYSIS-TECHNICAL.json').read_text())
    resources = {}
    for arm in arms + ['early-replan', 'fitting', 'analysis']:
        selected = [value for key, value in technical.items() if key == arm == 'analysis'
                    or value['spec'].get('control') == arm or value['spec']['stage'] == arm == 'fitting']
        counts = collections.Counter()
        for value in selected:
            counts.update(value.get('counts', {}))
        resources[arm] = dict(tasks=len(selected), allocation_seconds=sum(successful[v['spec']['key']]['allocation_seconds'] for v in selected),
                              worker_wall_seconds=sum(v['worker_wall_seconds'] for v in selected),
                              process_cpu_seconds=sum(v['process_cpu_seconds'] for v in selected),
                              max_process_rss_bytes=max(v['peak_process_rss_bytes'] for v in selected),
                              max_torch_allocated_bytes=max(v.get('peak_torch_allocated_bytes', 0) for v in selected),
                              max_torch_reserved_bytes=max(v.get('peak_torch_reserved_bytes', 0) for v in selected),
                              image_encodings=sum(v.get('image_encodings', 0) for v in selected),
                              fingerprinting_seconds=sum(v.get('fingerprinting_seconds', 0) for v in selected),
                              output_bytes=sum(task_bytes[v['spec']['key']] for v in selected), counts=dict(counts))
    summary = dict(arms=by_arm, resources=resources, source_count=512, model_pairs=3, episode_count=8192,
                   report_sha256=sha(report_raw), bootstrap_rerun=False, models_or_physics_invoked=False,
                   certificate=report['hoeffding_positive_additional_certificate'], contrasts=report['estimator']['contrasts'])
    write('SUMMARY.json', summary)
    print(json.dumps(dict(arms=by_arm, certificate=summary['certificate'], contrasts={name: {key: value for key, value in item.items()
                          if key not in ('source_effects', 'source_by_seed_effects')} for name, item in summary['contrasts'].items()},
                          resources=resources, report_bytes=len(report_raw)), indent=2))


if __name__ == '__main__':
    main()
