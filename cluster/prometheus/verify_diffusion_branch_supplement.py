"""Versioned saved-artifact supplement; no torch, model or simulator execution.

Closes the independently reviewed semantic omissions without editing either
prior verifier or any pilot output. Acceptance tolerances remain unchanged.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from diffusion_bottleneck import require, require_sha, sha256, write_report, checked_child
from verify_diffusion_branch import REFS, CONDS, seal, physical

CANONICAL_SHA = '0c406ca98e051d0f5aa9d8d701f5bc6bc299d67b38906bb2c6bbc39e6d5362ee'
AGGREGATE_SHA = '58c75c57e87a5736e6a9065334beeef57a682e9193153b6c19f2e08b80ff749a'
LAUNCH_SHA = '897dba9f318c48ae2e0889c8bf78ccf22808ccbe6132af7aee4e7648bfe8163f'
MODEL_SHA = 'f0c666cc011ab057390f7e1571cf3d8bde905d13ff11f1d406f6d3dd8575340d'


def checked_physical(states, flags, goal, cap):
    require(states.dtype == np.float64 and states.ndim == 2 and states.shape[1] == 7,
            'Physical dtype/shape')
    require(goal.dtype == np.float64 and goal.shape == (7,) and np.isfinite(goal).all(),
            'Goal dtype/shape/finite')
    require(np.isfinite(states).all(), 'State finite')
    require(np.all((states[:, 4] >= 0) & (states[:, 4] <= 2*np.pi)), 'State angle domain')
    require(0 <= goal[4] < 2*np.pi, 'Goal angle domain')
    require(flags.dtype == np.bool_ and flags.shape == (len(states), 2), 'Flag type/shape')
    require(0 < len(states) <= cap, 'Trace exceeds cap or empty')
    require(len(states) == cap or bool(flags[-1].any()), 'Unexplained early stopping')
    return physical(states, flags, goal)


def coverage(rows, historical):
    expected = {(h, t) for h in (75, 150) for t in (0, 30)}
    coordinates = [(r['horizon'], r['anchor']) for r in rows]
    require(len(coordinates) == 4 and len(set(coordinates)) == 4 and set(coordinates) == expected,
            'Duplicate/missing anchor')
    for r in rows:
        available = historical[r['horizon']]['delivered'] > r['anchor']
        require(type(r['available']) is bool and r['available'] == available, 'False availability')
        if not available:
            require(r['reason'] == 'historical_episode_finished', 'Unavailable reason')


def immediate_cost(predicted, goal, stored, chosen):
    expected = np.sum((predicted.reshape(64, -1)-goal)**2, axis=-1)
    require(stored.shape == (64,) and np.isfinite(stored).all(), 'Greedy cost shape/finite')
    np.testing.assert_allclose(stored, expected, rtol=2e-6, atol=1e-5)
    # Select from the original stored reduction, not a differently ordered sum.
    require(chosen == int(np.argmin(stored)), 'Greedy original cost/tie rule')


def counters(report, branches, steps):
    require(report['physical_branch_rollouts'] == branches, 'Branch counter mismatch')
    require(report['primitive_steps_including_replays'] == steps, 'Step counter mismatch')


def provenance(report, runner_sha, historical_model):
    require(report['program_sha256'] == runner_sha, 'Runner source mismatch')
    require(report['model_state_sha256'] == historical_model == MODEL_SHA, 'Model identity mismatch')


def check_anchor(v, row, historical_states, historical_actions, historical_goal):
    h, t = row['horizon'], row['anchor']
    np.testing.assert_array_equal(v('prefix_actions'), historical_actions[:t])
    np.testing.assert_allclose(v('anchor_state'), historical_states[t], rtol=0, atol=1e-10)
    np.testing.assert_array_equal(v('goal_state'), historical_goal)
    first_cap, second_cap = min(15, 2*h-t), min(30, 2*h-t)
    first = []
    lengths = 0
    for i in range(64):
        s, f = v(f'first-{i}/states'), v(f'first-{i}/termination_flags')
        first.append(checked_physical(s, f, v('goal_state'), first_cap))
        lengths += len(s)
    active = [x['delivered'] == 15 and not v(f'first-{i}/termination_flags')[-1].any()
              for i, x in enumerate(first)]
    require(row['active_first_branches'] == sum(active), 'Active count')
    require(row['first_chunk_successes'] == sum(x['success'] for x in first), 'First success count')
    np.testing.assert_array_equal(v('active'), active)
    np.testing.assert_array_equal(v('first_success'), [x['success'] for x in first])
    for cond in CONDS:
        i, _ = row['selected'][cond]
        s, f = v(cond+'/states'), v(cond+'/termination_flags')
        m = checked_physical(s, f, v('goal_state'), second_cap)
        n = min(15, len(s))
        np.testing.assert_array_equal(s[:n], v(f'first-{i}/states'))
        np.testing.assert_array_equal(f[:n], v(f'first-{i}/termination_flags'))
        require(row['short_outcomes'][cond] == {
            'short_branch_success': m['success'], 'delivered': len(s),
            'first_chunk_success': bool(f[:15, 0].any()),
            'first_branch_active_for_intervention': bool(active[i])}, 'Reported short outcome mismatch')
        lengths += len(s)
    g = row['greedy64']
    immediate_cost(v('predicted_latent'), v('goal_raw'), v('greedy64/costs'), g)
    gs, gf = v('greedy64/states'), v('greedy64/termination_flags')
    checked_physical(gs, gf, v('goal_state'), first_cap)
    np.testing.assert_array_equal(gs, v(f'first-{g}/states'))
    np.testing.assert_array_equal(gf, v(f'first-{g}/termination_flags'))
    lengths += len(gs)
    return 69, 69*len(v('prefix_actions')) + lengths


def analyze(root, study, canonical, aggregate, launch):
    require_sha(canonical, CANONICAL_SHA); certificate = json.loads(canonical.read_text())
    require_sha(aggregate, AGGREGATE_SHA); prior = json.loads(aggregate.read_text())
    require(certificate['all_passed'] and prior['all_technical_checks_passed'], 'Prior verification failed')
    require(str(study.resolve()) == certificate['canonical_study'], 'Wrong study')
    manifest = launch/'SOURCE-MANIFEST.sha256'; require_sha(manifest, LAUNCH_SHA)
    for line in manifest.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        require_sha(checked_child(launch, name), digest)
    runner_sha = sha256(launch/'cluster/prometheus/diffusion_bottleneck_branch.py')
    reports = {}; seals = {}
    # Authenticate all eight bundles against the prior aggregate before arrays.
    for ref in REFS:
        for rep in (0, 1):
            directory = root/f'ref-{ref}-repeat-{rep}'
            r, s = seal(directory)
            require((r['reference'], r['repeat']) == (ref, rep), 'Run identity')
            require(prior['seals'][str(directory)] == s, 'Pilot changed since prior verification')
            reports[ref, rep] = r; seals[str(directory)] = s
    total_steps = total_branches = available_count = 0
    histories = {}; run_counts = []
    for ref in REFS:
        task = f'stage-0/task-{ref//64:04d}'
        result = study/task/'results/RESULT.json'
        require_sha(result, certificate['shards'][task]['result_sha256'])
        historical = json.loads(result.read_text())
        rows = [r for r in historical['rows'] if r['reference_index'] == ref]
        require(len(rows) == 2 and {r['horizon'] for r in rows} == {75, 150}, 'Historical horizon grid')
        history = {r['horizon']: r for r in rows}; traces = {}
        for h, row in history.items():
            require(row['failure'] is None, 'Historical failure')
            path = checked_child(result.parent, row['trajectory_file']); require_sha(path, row['trajectory_sha256'])
            with np.load(path, allow_pickle=False) as data:
                traces[h] = {k: data[k].copy() for k in ('states', 'actions', 'goal_state')}
            require(len(traces[h]['actions']) == row['delivered'] and len(traces[h]['states']) == row['delivered']+1,
                    'Historical episode length')
        histories[str(ref)] = {'result_sha256': sha256(result), 'delivered': {str(h): r['delivered'] for h,r in history.items()}}
        for rep in (0, 1):
            r = reports[ref, rep]; provenance(r, runner_sha, historical['model_state_sha256'])
            coverage(r['anchors'], history)
            steps = branches = 0
            with np.load(root/f'ref-{ref}-repeat-{rep}/BANKS.npz', allow_pickle=False) as bank:
                for row in r['anchors']:
                    h, t = row['horizon'], row['anchor']; prefix = f'h{h}/t{t}/'
                    if not row['available']:
                        require(not any(k.startswith(prefix) for k in bank.files), 'Unavailable anchor has arrays')
                        continue
                    available_count += 1
                    def v(k): return bank[prefix+k]
                    trace = traces[h]
                    nb, ns = check_anchor(v, row, trace['states'], trace['actions'], trace['goal_state'])
                    branches += nb; steps += ns
                # The main baseline world advances through the last available
                # anchor plus its one delivered action, once per horizon.
                for h in (75, 150):
                    available = [x['anchor'] for x in r['anchors'] if x['horizon'] == h and x['available']]
                    steps += max(available)+1 if available else 0
            counters(r, branches, steps)
            total_steps += steps; total_branches += branches
            run_counts.append({'reference': ref, 'repeat': rep, 'branches': branches, 'primitive_steps': steps})
    require(total_steps == prior['primitive_steps_including_prefixes'] and
            total_branches == prior['physical_branch_rollouts'], 'Aggregate accounting mismatch')
    return {'all_passed': True, 'runs': 8, 'available_anchors_including_repeats': available_count,
            'independently_counted_branches': total_branches, 'independently_counted_primitive_steps': total_steps,
            'run_counts': run_counts, 'historical_evidence': histories, 'seals': seals,
            'launch_manifest_sha256': LAUNCH_SHA, 'runner_sha256': runner_sha, 'model_state_sha256': MODEL_SHA,
            'prior_aggregate_sha256': AGGREGATE_SHA, 'canonical_receipt_sha256': CANONICAL_SHA,
            'scope': 'Independent saved-array arithmetic, trace semantics, counts and provenance linkage; not independent neural-output regeneration or hidden-physics reconstruction',
            'new_model_or_physics_execution': False, 'protected_payload_reads': 0,
            'unevaluated_reference_payload_reads': 0, 'historical_decision_changed': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('root', 'study', 'canonical', 'aggregate', 'launch', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); result = analyze(a.root, a.study, a.canonical, a.aggregate, a.launch)
    result['program_sha256'] = sha256(Path(__file__))
    write_report(a.out, result, (a.root, a.study, a.launch))
