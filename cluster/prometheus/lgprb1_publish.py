"""Post-preservation publication from sealed completed aggregates; stdlib only.

No model imports, outcome generation, simulator, optimizer or scheduler calls.
This publisher is outside the immutable executed source package.
"""
import hashlib
import json
import tarfile
from pathlib import Path

BASE = Path('D:/THESIS-BACKUPS/local-goal-search-budget-20260919/run-a0bcdb48029909e0')
OLD = Path('D:/THESIS-BACKUPS/local-goal-proposals-20260918/run-b54a55b16bcb83a5')
DOC = Path(__file__).resolve().parents[2] / 'docs/local-goal-search-budget-20260919'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def member_json(archive, request, name):
    data = archive.extractfile(name).read()
    expected = request['members'][name]
    assert len(data) == expected['bytes']
    assert hashlib.sha256(data).hexdigest() == expected['sha256']
    return json.loads(data)


def write_json(name, value):
    with (DOC / name).open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')


def main():
    request = read_json(BASE / 'BACKUP-REQUEST.json')
    verified = read_json(BASE / 'BACKUP-VERIFIED.json')
    old_request = read_json(OLD / 'BACKUP-REQUEST.json')
    assert request['sha256'] == verified['sha256'] == '72c2717be4a10b0e103a05c6575710832e5ae4c9e9a21be573c8cb3c4441f175'
    assert verified['historical_archive_sha256'] == old_request['sha256'] == '24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd'
    with tarfile.open(BASE / 'final.tar', 'r:') as archive:
        result = member_json(archive, request, 'run/analysis/REPORT.json')
        complete = member_json(archive, request, 'run/COMPUTE-COMPLETE.json')
        analysis = member_json(archive, request, 'run/analysis/TECHNICAL.json')
        approval = member_json(archive, request, 'run/APPROVAL.json')
        gate = member_json(archive, request, 'run/COMPATIBILITY-PASSED.json')
    with tarfile.open(OLD / 'final.tar', 'r:') as archive:
        old_complete = member_json(archive, old_request, 'run/COMPUTE-COMPLETE.json')
    rows = result['rows']
    assert len(rows) == 1152 and len({r['reference'] for r in rows}) == 32
    assert len(complete['completed']) == 387
    assert all(r['state'] == 'COMPLETED' and r['exit_code'] == '0:0' for r in complete['completed'])
    assert sum(not r['reused'] for r in rows) == 768
    assert all(r['endpoint_check']['actions'] == r['steps'] and
               r['endpoint_check']['success'] == r['success'] and
               r['endpoint_check']['post_action_only'] and r['failure'] is None for r in rows)
    grouped = []
    for budget in (1, 5, 30):
        for family in ('gmm', 'diffusion'):
            selected = [r for r in rows if (r['populations'], r['family']) == (budget, family)]
            assert len(selected) == 192
            assert len({(r['reference'], r['horizon'], r['seed']) for r in selected}) == 192
            stages = sum(r['planning']['stages'] for r in selected)
            timing = {k: sum(r['planning'][k] for r in selected) for k in selected[0]['planning'] if k != 'stages'}
            assert timing['cost_calls'] == stages * budget
            assert timing['candidate_trajectories'] == 300 * timing['cost_calls']
            assert timing['predicted_primitive_steps'] == 15 * timing['candidate_trajectories']
            assert abs(sum(r['success'] for r in selected) / 192 - result['family_success'][str(budget)][family]['mean']) < 1e-12
            ledger = old_complete['completed'] if budget == 30 else complete['completed']
            allocations = [x for x in ledger if x['task']['kind'] == 'evaluation' and
                           x['task']['family'] == family and (budget == 30 or x['task']['populations'] == budget)]
            assert len(allocations) == 96
            item = dict(populations=budget, family=family, episodes=192,
                        successes=sum(r['success'] for r in selected), delivered_actions=sum(r['steps'] for r in selected),
                        terminated=sum(r['terminated'] for r in selected), truncated=sum(r['truncated'] for r in selected),
                        planning_stages=stages, planning_totals=timing,
                        planning_seconds_per_stage=timing['seconds'] / stages,
                        proposal_seconds_per_stage=timing['proposal_seconds'] / stages,
                        refinement_seconds_per_stage=timing['refinement_total_seconds'] / stages,
                        physical_delivery_seconds=sum(r['physics_delivery_seconds'] for r in selected),
                        allocation_seconds=sum(x['seconds'] for x in allocations),
                        reset_seconds=None if budget == 30 else sum(r['reset_seconds'] for r in selected),
                        episode_execution_seconds=None if budget == 30 else sum(r['episode_execution_seconds'] for r in selected),
                        reused=budget == 30)
            if budget != 30:
                resources = [x for x in result['resources'] if x['task']['kind'] == 'evaluation' and
                             (x['task']['populations'], x['task']['family']) == (budget, family)]
                assert len(resources) == 96
                item.update(worker_process_cpu_seconds=sum(x['process_cpu_seconds'] for x in resources),
                            worker_wall_seconds=sum(x['wall_seconds'] for x in resources),
                            setup_seconds=sum(x['setup_seconds'] for x in resources),
                            max_worker_rss_bytes=max(x['peak_rss_bytes'] for x in resources),
                            max_torch_allocated_gpu_bytes=max(x['peak_gpu_bytes'] for x in resources))
            grouped.append(item)
    new_resources = result['resources'] + [analysis]
    assert len(new_resources) == 387
    tests = dict(checks=['archive receipt binding', 'accessed-member SHA/size', '387 completed allocations',
                        '1152 unique source/horizon/seed/family/budget rows', '768 new / 384 reused',
                        'endpoint result/count/post-action consistency', 'exact scoring-call arithmetic',
                        'success totals match source-weighted aggregate', '96 job allocations per configuration'],
                 passed=True, research_execution=False)
    accounting = dict(new_allocation_count=387, failed_allocations=0,
                      gpu_allocation_seconds=complete['gpu_seconds'], cpu_allocation_seconds=complete['cpu_seconds'],
                      first_job=complete['completed'][0]['job'], last_job=complete['completed'][-1]['job'],
                      compatibility_gate=gate, analysis=analysis,
                      controller_wall_seconds=complete['controller_wall_seconds'],
                      controller_process_cpu_seconds=complete['controller_cpu_seconds'],
                      worker_process_cpu_seconds=sum(x['process_cpu_seconds'] for x in new_resources),
                      worker_wall_seconds_sum=sum(x['wall_seconds'] for x in new_resources),
                      max_worker_rss_bytes=max(x['peak_rss_bytes'] for x in new_resources),
                      max_torch_allocated_gpu_bytes=max(x.get('peak_gpu_bytes', 0) for x in new_resources),
                      compatibility_gpu_seconds=sum(x['seconds'] for x in complete['completed'] if x['task']['kind'] == 'compatibility'),
                      allocation_ledger=complete['completed'], configurations=grouped,
                      storage_at_compute_complete=complete['storage'],
                      archive={k:v for k,v in request.items() if k != 'members'}, backup=verified,
                      memory_scope='Worker Python ru_maxrss; PyTorch allocated GPU peak excludes CUDA driver/context, reserved allocator and simulator child-process memory. Slurm TotalCPU reported zero and is not substituted for recorded process CPU.',
                      timing_scope='Scoring is within refinement. Hash timer overlaps planning/refinement; historical30 did not fingerprint banks. New episode execution/reset are unavailable historically. Allocation includes setup/authentication/sealing; queue waiting excluded.')
    projection = {k:v for k,v in result.items() if k not in ('rows','resources','accounting')}
    projection['aggregate_sha256'] = request['members']['run/analysis/REPORT.json']['sha256']
    projection['aggregate_seal_sha256'] = request['members']['run/analysis/sha256.txt']['sha256']
    projection['configurations'] = grouped
    write_json('FINAL-AGGREGATE-PROJECTION.json', projection)
    write_json('FINAL-ACCOUNTING.json', accounting)
    write_json('FINAL-PUBLICATION-CHECKS.json', tests)
    write_json('FINAL-BACKUP-VERIFIED.json', verified)
    write_json('FINAL-EPISODES.json', [{k:r[k] for k in ('reference','horizon','seed','family','populations','success','steps','terminated','truncated','reused','provenance')} for r in rows])
    lines = ['# All 32 source effects', '', 'Each family/budget count is successes out of six (two horizons × three training seeds). Differences and changes below are percentage points. Every source is retained; seeds/horizons are not independent sources.', '',
             '| Source | GMM1 | Diff1 | GMM5 | Diff5 | GMM30 | Diff30 | D−G1 | D−G5 | D−G30 | Change1−30 | Change5−30 |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for effect in result['source_effects']:
        counts = [str(round(6*effect['means'][str(b)][f])) for b in (1,5,30) for f in ('gmm','diffusion')]
        effects = [f'{100*effect["family_differences"][str(b)]:+.3f}' for b in (1,5,30)]
        changes = [f'{100*effect["changes_relative_to_30"][str(b)]:+.3f}' for b in (1,5)]
        lines.append('| '+ ' | '.join([str(effect['reference'])]+counts+effects+changes)+' |')
    lines += ['', '## All horizon/training-seed strata', '', 'Each cell is successes / 32 sources. No seed selection.', '',
              '| Populations | Family | H75 seed8301 | H75 seed8302 | H75 seed8303 | H150 seed8301 | H150 seed8302 | H150 seed8303 |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for b in (1,5,30):
        for f in ('gmm','diffusion'):
            values = [str(round(32*next(s['success'] for s in result['strata'] if (s['populations'],s['family'],s['horizon'],s['seed'])==(b,f,h,seed))))+'/32' for h in (75,150) for seed in (8301,8302,8303)]
            lines.append('| '+' | '.join([str(b),f]+values)+' |')
    with (DOC/'FINAL-SOURCE-EFFECTS.md').open('x',encoding='utf-8',newline='\n') as handle:
        handle.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(publication_checks=tests,configurations=grouped,worker_cpu=accounting['worker_process_cpu_seconds'],peak_rss=accounting['max_worker_rss_bytes'],peak_gpu=accounting['max_torch_allocated_gpu_bytes'],aggregate_sha256=projection['aggregate_sha256']),indent=2))


if __name__ == '__main__':
    main()
