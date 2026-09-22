"""Read-only publication from the completed, union-preserved RB2 archive.

Outside the immutable executed source. No model, simulator, optimizer, research
analysis rerun, scheduler calls or raw reference/endpoint payload access.
"""
import hashlib
import json
import tarfile
from pathlib import Path

BASE = Path('D:/THESIS-BACKUPS/local-goal-source-replication-20260920/run-a8fa92772272e11a-recovery-r1')
DOC = Path(__file__).resolve().parent
SOURCE = 'a8fa92772272e11a279aac6c13699fc5b6da9f8160bd3264bab15e3f6bf68cec'
ARCHIVE = 'fa17faef59d068b6a71d0ca40a3178b7f1be0a4e78688282a1bd846eb8a8b2aa'
APPROVAL = '013dfa0c2498a627e84057d7f53a758871cae010c8f51a0db4553717a697e49b'
HISTORY = ['24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd',
           '72c2717be4a10b0e103a05c6575710832e5ae4c9e9a21be573c8cb3c4441f175']
ARMS = [('gmm', 5), ('diffusion', 5), ('gmm', 30), ('diffusion', 30)]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(name, value):
    with (DOC / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def main():
    def sha(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    request = read(BASE / 'BACKUP-REQUEST.json')
    backup = read(BASE / 'RECOVERY-BACKUP-VERIFIED.json')
    complete = read(BASE / 'RECOVERY-SESSION-COMPLETE.json')
    assert complete['complete'] and complete['supervisor']['returncode'] == 0
    assert complete['supervisor']['owned_process_resolved'] and complete['supervisor']['watchdog'] is None
    assert sha(BASE / 'RECOVERY-BACKUP-VERIFIED.json') == complete['receipt_sha256'] == 'f37008725443d44a883f7a3035c67070e2560dacedf2cbad3fccf0c23d688cb6'
    assert sha(BASE / 'RECOVERY-SESSION-COMPLETE.json') == '18f65732f9e2622fd1e4f8bdc89856dc45775ff767daa2712b1d6a09d2167578'
    assert sha(BASE / 'RECOVERY-SEAL.json') == complete['recovery_seal_sha256']
    assert sha(BASE / 'BACKUP-REQUEST.json') == backup['request_sha256'] == 'f980786b598867e12dd9fad0589dbc9afc642bc4441136721abbfb787457af06'
    assert backup['recovery_verified'] and not backup['first_transfer_succeeded'] and not backup['unresolved_remote_operations']
    assert Path(backup['successful_destination']) == BASE / 'final.tar'
    assert not (BASE / 'RECOVERY-FAILURE.json').exists() and not (BASE / 'SUPERVISOR-FAILURE.json').exists()
    assert sha(BASE / 'final.tar') == ARCHIVE
    assert request['sha256'] == backup['sha256'] == ARCHIVE
    assert request['bytes'] == backup['bytes'] == (BASE / 'final.tar').stat().st_size
    assert request['files'] == backup['files'] == 32393
    assert request['source_sha256'] == backup['source_sha256'] == SOURCE
    assert [r['sha256'] for r in backup['historical']] == HISTORY
    accessed = {}
    with tarfile.open(BASE / 'final.tar', 'r:') as archive:
        def member(name):
            payload = archive.extractfile(name).read()
            expected = request['members'][name]
            assert len(payload) == expected['bytes']
            assert hashlib.sha256(payload).hexdigest() == expected['sha256']
            accessed[name] = expected
            return json.loads(payload)
        result = member('run/analysis/REPORT.json')
        done = member('run/COMPUTE-COMPLETE.json')
        analysis = member('run/analysis/TECHNICAL.json')
        approval = member('run/APPROVAL.json')
        gate = member('run/TECHNICAL-TRANCHE-PASSED.json')
        roles = member('source/docs/local-goal-source-replication-20260920/DATA-ROLES.json')
    assert request['members']['run/APPROVAL.json']['sha256'] == APPROVAL
    assert request['members']['run/PRE-EVALUATION-FREEZE.json']['sha256'] == 'a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305'
    refs = roles['ordered_references']
    rows, resources = result['rows'], result['resources']
    expected = {(ref, seed, family, budget, horizon) for ref in refs for seed in (8301, 8302, 8303)
                for family, budget in ARMS for horizon in (75, 150)}
    keys = [(r['reference'], r['seed'], r['family'], r['populations'], r['horizon']) for r in rows]
    assert len(refs) == len(set(refs)) == 512
    assert len(rows) == len(set(keys)) == len(expected) == 12288 and set(keys) == expected
    assert result['independent_sources'] == 512 and result['main_episodes'] == 12288 and result['reused_episodes'] == 0
    assert len(result['source_effects']) == 512 and len(result['strata']) == 24
    assert len(resources) == 1536 and len(done['completed']) == done['new_jobs'] == 1537
    assert len({x['job'] for x in done['completed']}) == 1537
    assert all(x['state'] == 'COMPLETED' and x['exit_code'] == '0:0' and x['seconds'] <= x['task']['seconds'] for x in done['completed'])
    assert sum(x['seconds'] for x in done['completed'] if x['task']['gpu']) == done['gpu_seconds'] <= 460800
    assert sum(x['seconds'] for x in done['completed'] if not x['task']['gpu']) == done['cpu_seconds'] <= 7200
    assert all(r['failure'] is None and not r['reused'] and r['endpoint_check']['actions'] == r['steps']
               and r['endpoint_check']['success'] == r['success'] and r['endpoint_check']['post_action_only'] for r in rows)
    assert all(m['complete'] and m['models_unchanged'] and m['source_sha256'] == SOURCE
               and m['approval_sha256'] == APPROVAL and m['technical_checks'] == {
                   'common_initial_banks': True, 'fresh_episode_ownership': True, 'endpoint_checks_passed': 8} for m in resources)
    assert analysis['complete'] and not analysis['gpu_used'] and analysis['source_sha256'] == SOURCE and analysis['approval_sha256'] == APPROVAL
    configurations = []
    for family, budget in ARMS:
        selected = [r for r in rows if (r['family'], r['populations']) == (family, budget)]
        assert len(selected) == 3072
        planning = {k: sum(r['planning'][k] for r in selected) for k in selected[0]['planning']}
        assert planning['cost_calls'] == planning['stages'] * budget
        assert planning['candidate_trajectories'] == 300 * planning['cost_calls']
        assert planning['predicted_primitive_steps'] == 15 * planning['candidate_trajectories']
        assert all(r['planning']['stages'] == (r['steps'] + 14) // 15 for r in selected)
        generator_calls = sum(sum(1 for stage in range(r['planning']['stages'])
                                  if stage % (r['horizon']//15) != r['horizon']//15-1) for r in selected)
        successes = sum(r['success'] for r in selected)
        assert abs(successes / 3072 - result['absolute'][f'{family}-{budget}']['mean']) < 1e-12
        timing_keys = ['world_creation_seconds', 'reset_seconds', 'physics_delivery_seconds',
                       'evidence_verification_seconds', 'world_close_seconds', 'complete_episode_seconds']
        configurations.append(dict(family=family, populations=budget, episodes=3072,
            successes=successes, delivered_actions=sum(r['steps'] for r in selected),
            terminated=sum(r['terminated'] for r in selected), truncated=sum(r['truncated'] for r in selected),
            planning_totals=planning, episode_timing_totals={k:sum(r[k] for r in selected) for k in timing_keys},
            derived_model_calls=dict(proposal_sampling_calls=planning['stages'],
                proposer_network_forward_calls=planning['stages']*(1 if family == 'gmm' else 5),
                lewm_encode_calls=3*planning['stages'], local_goal_generator_calls=generator_calls,
                lewm_batched_cost_calls=planning['cost_calls'],
                scope='Derived from sealed stage counts and frozen executed code; not a profiler count of internal kernels or model submodules.'),
            planning_seconds_per_stage=planning['seconds']/planning['stages'],
            proposal_seconds_per_stage=planning['proposal_seconds']/planning['stages'],
            refinement_seconds_per_stage=planning['refinement_total_seconds']/planning['stages']))
    for effect in result['source_effects']:
        for family, budget in ARMS:
            selected = [r for r in rows if (r['reference'],r['family'],r['populations']) == (effect['reference'],family,budget)]
            assert len(selected) == 6 and abs(sum(r['success'] for r in selected)/6-effect['means'][f'{family}-{budget}']) < 1e-12
    for stratum in result['strata']:
        selected = [r for r in rows if all(r[k] == stratum[k] for k in ('family','populations','horizon','seed'))]
        assert len(selected) == 512 and sum(r['success'] for r in selected)/512 == stratum['success']
    all_resources = resources + [analysis]
    accounting = dict(compute_complete=done, configurations=configurations, analysis=analysis,
        gpu_worker_process_cpu_seconds=sum(m['process_cpu_seconds'] for m in resources),
        total_worker_process_cpu_seconds=sum(m['process_cpu_seconds'] for m in all_resources),
        gpu_worker_wall_seconds=sum(m['wall_seconds'] for m in resources),
        total_worker_wall_seconds=sum(m['wall_seconds'] for m in all_resources),
        shared_setup_seconds=sum(m['setup_seconds'] for m in resources),
        max_gpu_worker_python_rss_bytes=max(m['peak_rss_bytes'] for m in resources),
        max_worker_python_rss_bytes=max(m['peak_rss_bytes'] for m in all_resources),
        max_torch_allocated_bytes=max(m['peak_gpu_bytes'] for m in resources),
        archive={k:v for k,v in request.items() if k != 'members'}, backup=backup, recovery_session_complete=complete,
        timing_scope='Scoring is inside refinement; bank fingerprint time overlaps planning/refinement. Complete episode includes world creation through close and endpoint verification, but excludes shared job setup. Worker timing ends after report write and before technical/seal writes. Allocation includes setup and preservation; excludes queue wait. Four arms share each allocation: no invented arm-level allocation or worker CPU split.',
        memory_scope='Python ru_maxrss is one worker process, not whole child-process memory. Torch max_memory_allocated excludes allocator reserve, CUDA context/driver and other processes. Slurm top-level TotalCPU zero is not actual worker CPU.')
    projection = {k:v for k,v in result.items() if k not in ('rows','resources','accounting')}
    projection.update(aggregate_sha256=request['members']['run/analysis/REPORT.json']['sha256'], configurations=configurations)
    checks = dict(passed=True, research_execution=False, checks=[
        'Verified full new and historical archive union receipts', 'Accessed archived aggregate/member SHA and bytes',
        '1537 unique bounded successful allocations and all charges', '12288 unique exact allowlisted source/seed/arm/horizon identities',
        'Zero reused rows and endpoint actions/native-success/post-action consistency', '1536 workers: unchanged models and 12288 endpoint checks',
        'Every source equal-weight arm mean and every one of 24 strata matches complete rows',
        'Exact planning scoring/candidate/predicted-step arithmetic', 'Primary and secondary intervals reused unchanged from sealed complete analyzer'])
    authentication = dict(source_sha256=SOURCE, approval_sha256=APPROVAL, archive_sha256=ARCHIVE,
        accessed_members=accessed, analysis_seal=request['members']['run/analysis/sha256.txt'],
        original_freeze=request['members']['run/PRE-EVALUATION-FREEZE.json'], approval=approval,
        technical_gate=gate, backup=backup, publication_method='Read-only completed aggregate from fully verified SSD union; no raw protected reference or endpoint payload opened; no new research execution.')
    write('FINAL-AGGREGATE-PROJECTION.json', projection)
    write('FINAL-ACCOUNTING.json', accounting)
    write('FINAL-AUTHENTICATION.json', authentication)
    write('FINAL-BACKUP-VERIFIED.json', backup)
    write('FINAL-PUBLICATION-CHECKS.json', checks)
    write('FINAL-EPISODES.json', [{k:r[k] for k in ('reference','horizon','seed','family','populations','success','steps','terminated','truncated','reused','endpoint_identity','endpoint_check')} for r in rows])
    lines = ['# All 512 source effects and 24 strata', '',
        'Every source retained. Arm counts are successes out of six (two horizons × three seeds); effects are percentage points. The source, not seed/horizon/episode, is the independent unit.', '',
        '| Source | G5 | D5 | G30 | D30 | D5−G5 | D30−G30 | Interaction | D5−D30 | D5−G30 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    effect_keys = ['delta5','delta30','interaction','diffusion5_minus_diffusion30','diffusion5_minus_gmm30']
    for effect in result['source_effects']:
        values = [str(effect['reference'])] + [str(round(6*effect['means'][f'{f}-{n}'])) for f,n in ARMS]
        values += [f'{100*effect[k]:+.3f}' for k in effect_keys]
        lines.append('| '+' | '.join(values)+' |')
    lines += ['', '## All strata', '', '| Family | Populations | Horizon | Seed | Successes / 512 |', '| --- | ---: | ---: | ---: | ---: |']
    for s in result['strata']:
        lines.append('| '+' | '.join([s['family'],str(s['populations']),str(s['horizon']),str(s['seed']),str(round(512*s['success']))+'/512'])+' |')
    with (DOC/'FINAL-SOURCE-EFFECTS.md').open('x',encoding='utf-8',newline='\n') as stream:
        stream.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(primary=result['primary'],secondary=result['secondary'],absolute=result['absolute'],
        configurations=configurations,accounting={k:v for k,v in accounting.items() if k not in ('compute_complete','configurations','backup','archive')},
        backup=backup, archive={k:v for k,v in request.items() if k != 'members'},
        aggregate_sha256=projection['aggregate_sha256'], checks=checks),indent=2))


if __name__ == '__main__':
    main()
