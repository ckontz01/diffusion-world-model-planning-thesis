"""Preparation-only single-decision protocol and pure lifecycle helpers.

No model, environment, scheduler or dataset is constructed by importing this file.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from diffusion_extension_control import REFS
from diffusion_bottleneck import require, require_sha, checked_child, sha256
from verify_diffusion_branch import independent_decode

HORIZONS = (75, 150)
ANCHORS = (0, 30)
ARMS = ('continuation', 'immediate')
REPEATS = (0, 1)
CHUNK = 15
ATOL = 1e-10
COMBINED_SHA = '820f027f7313c4179d95f99e5eda54d2172469eb4a3cd8541883aa5f8a0e0a54'
DECODER_SHA = '334dca60b952d1fb8436e3c9af009f2159dd863e5d402e15f917cb6da55a8a21'
MODEL_SHA = 'f0c666cc011ab057390f7e1571cf3d8bde905d13ff11f1d406f6d3dd8575340d'
STUDY = Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5')
COMBINED_ROOT = STUDY.parents[1] / 'diffusion-bottleneck/combined-20260914-265b618'


def coordinate(ref, h, anchor, arm, repeat):
    require(ref in REFS and h in HORIZONS and anchor in ANCHORS and
            arm in ARMS and repeat in REPEATS, 'Unapproved coordinate')


def schedule(h, absolute):
    require(h in HORIZONS and 0 <= absolute < 2*h and absolute % CHUNK == 0,
            'Invalid absolute planning time')
    return h - absolute % h, CHUNK


def bounds(repeats=2):
    require(repeats in (1, 2), 'Repeat proposal')
    cells = [(h, a) for _ in REFS for h in HORIZONS for a in ANCHORS for _ in ARMS]
    post = sum(2*h-a for h, a in cells)
    prefix = sum(a for h, a in cells)
    post_calls = sum(len(range(a, 2*h, CHUNK)) for h, a in cells)
    prefix_calls = prefix // CHUNK
    # Each branch replays its OWN historical prefix through the actual policy.
    calls = post_calls + prefix_calls
    second = sum(sum(schedule(h, t)[0] >= 30 for t in range(0, 2*h, CHUNK))
                 for h, _ in cells)
    return {k: v*repeats for k, v in dict(
        logical_branches=len(cells), post_anchor_steps=post, prefix_steps=prefix,
        physical_steps=post+prefix, post_anchor_planning_calls=post_calls,
        prefix_planning_calls=prefix_calls, planning_calls=calls,
        continuation_calls=second, first_only_calls=calls-second,
        proposal_batches=calls+second, encoder_calls=2*calls,
        adapter_calls=second, latent_rollout_batches=calls+second,
        predictor_calls=3*(calls+second), action_encoder_calls=3*(calls+second),
        candidate_trajectories=64*calls+512*second,
        diffusion_network_forwards=10*(calls+second),
        model_constructions=len(REFS), environment_constructions=len(cells)).items()}


def execute_branch(policy, info, step, observe, *, horizon, anchor, history):
    """Actual policy owns its buffer/stage; never replace/reset it at hand-off.

    step returns (state, [native terminated, native truncated]); observes poststeps.
    Hook installed by the caller changes solve output ONLY at the absolute anchor.
    """
    delivered = []
    flags = []
    states = []
    for absolute in range(2*horizon):
        if not policy._action_buffer:
            require(policy._stage_index == absolute//CHUNK, 'Stage drift')
            require(tuple(policy.stages[policy._stage_index]) == schedule(horizon, absolute),
                    'Schedule-cycle drift')
        action = np.asarray(policy.get_action(info()))
        require(action.shape == (1, 2) and np.isfinite(action).all() and
                (np.abs(action) <= 1).all(), 'Invalid action; no clipping/fallback')
        if absolute < anchor:
            np.testing.assert_array_equal(action[0], history['actions'][absolute])
        state, terminal = step(action)
        terminal = np.asarray(terminal)
        require(terminal.shape == (2,) and terminal.dtype == np.bool_, 'Native flags')
        if absolute < anchor:
            np.testing.assert_allclose(state, history['states'][absolute+1], rtol=0, atol=ATOL)
            require(not terminal.any(), 'Historical prefix terminated')
        else:
            states.append(np.asarray(state).copy())
            delivered.append(action[0].copy())
            flags.append(terminal.copy())
        observe(absolute+1, policy)
        if terminal.any():
            break
    require(len(states) > 0, 'Anchor unavailable: stop rather than replace')
    return {'states': np.stack(states), 'actions': np.stack(delivered),
            'flags': np.stack(flags)}


def physical(states, flags, goal, cap):
    """Reviewed angle/decoder semantics, now allowing the declared full budget."""
    require(states.dtype == np.float64 and states.ndim == 2 and states.shape[1] == 7,
            'State dtype/shape')
    require(goal.dtype == np.float64 and goal.shape == (7,) and np.isfinite(goal).all(), 'Goal')
    require(np.isfinite(states).all() and np.all((states[:,4] >= 0) & (states[:,4] <= 2*np.pi)), 'State domain')
    require(0 <= goal[4] < 2*np.pi, 'Goal angle')
    require(flags.dtype == np.bool_ and flags.shape == (len(states), 2), 'Flags')
    require(0 < len(states) <= cap and (len(states) == cap or flags[-1].any()), 'Cap/early stop')
    require(not flags[:-1].any(), 'Post-terminal action')
    distance = np.sqrt(np.sum((states[:,:4]-goal[:4])**2, axis=1))
    d = np.abs(states[:,4]-goal[4]); angle = np.minimum(d, 2*np.pi-d)
    success = (distance < 20) & (angle < np.pi/9)
    np.testing.assert_array_equal(success, flags[:,0])
    margins = np.maximum(distance/20, angle/(np.pi/9))
    n = min(CHUNK, len(states))
    first_terminal = bool(flags[:n].any())
    return {'success': bool(success.any()), 'first_success': bool(success[:n].any()),
            'first_margin': float(margins[:n].min()),
            'handoff_margin': None if first_terminal or len(states)<CHUNK else float(margins[CHUNK-1]),
            'first_terminal': first_terminal, 'closest_margin': float(margins.min()),
            'delivered': len(states), 'native_truncated': bool(flags[-1,1]),
            'budget_exhausted': len(states) == cap}


def reference_effects(rows):
    expected = {(ref,h,a) for ref in REFS for h in HORIZONS for a in ANCHORS}
    keys = [(r['reference'],r['horizon'],r['anchor']) for r in rows]
    require(len(keys) == len(expected) and set(keys) == expected, 'Duplicate/missing coordinates')
    require(all(r['repeat'] == 0 for r in rows), 'Scientific aggregation uses repeat0 only')
    result = []
    for ref in REFS:
        per_h = []
        for h in HORIZONS:
            points = [r for r in rows if (r['reference'],r['horizon']) == (ref,h)]
            per_h.append({'horizon':h, 'success_difference_pp':100*float(np.mean([
                int(r['immediate']['success'])-int(r['continuation']['success']) for r in points])),
                'margin_improvement':float(np.mean([r['continuation']['closest_margin']-
                    r['immediate']['closest_margin'] for r in points]))})
        result.append({'reference':ref,'per_horizon':per_h,
                       'success_difference_pp':float(np.mean([r['success_difference_pp'] for r in per_h])),
                       'margin_improvement':float(np.mean([r['margin_improvement'] for r in per_h]))})
    summary = {}
    for metric in ('success_difference_pp','margin_improvement'):
        values = np.array([r[metric] for r in result])
        rng = np.random.default_rng(20260914)
        boot = values[rng.integers(0,len(values),(10000,len(values)))].mean(axis=1)
        summary[metric] = dict(mean=float(values.mean()), wins=int((values>0).sum()),
                              losses=int((values<0).sum()), ties=int((values==0).sum()),
                              exploratory_95=np.quantile(boot,[.025,.975]).tolist())
    anchor_difference = [int(r['immediate']['success'])-int(r['continuation']['success']) for r in rows]
    return {'reference_effects':result,'summary':summary,'anchor_paired_success':{
        'wins':anchor_difference.count(1),'losses':anchor_difference.count(-1),'ties':anchor_difference.count(0)},
        'independent_references':32,'scientific_repeat':0,'confirmation':False}


def load_inputs(ref, combined):
    """Only selected payloads; authenticate against accepted receipts first."""
    require(ref in REFS, 'Unselected reference')
    require_sha(combined, COMBINED_SHA)
    certificate = json.loads(combined.read_text())
    require(certificate['all_combined_checks_passed'] is True, 'Prior acceptance')
    from diffusion_bottleneck import LOCK_SHA
    require_sha(STUDY/'INPUT-LOCK.json', LOCK_SHA)
    lock = json.loads((STUDY/'INPUT-LOCK.json').read_text())
    require_sha(STUDY/'collection/COLLECTION.json', lock['collection_sha256'])
    collection = json.loads((STUDY/'collection/COLLECTION.json').read_text())
    record = collection['records'][ref]
    require(record['index'] == ref, 'Record identity')
    p = checked_child(STUDY/'collection', record['file']); require_sha(p, record['sha256'])
    with np.load(p,allow_pickle=False) as z:
        initial = z['initial_request'].copy()
        goals = {h:z['states'][h].copy() for h in HORIZONS}
    result_path = STUDY/f'stage-0/task-{ref//64:04d}/results/RESULT.json'
    require_sha(result_path, certificate['historical_result_sha256'][str(ref)])
    historical = json.loads(result_path.read_text())
    require(historical['arm'] == 'vad_continuation' and historical['train_seed'] == 7201 and
            historical['model_state_sha256'] == MODEL_SHA, 'Historical model/arm')
    rows = [r for r in historical['rows'] if r['reference_index'] == ref]
    require(len(rows) == 2 and {r['horizon'] for r in rows} == set(HORIZONS), 'Historical grid')
    traces = {}
    for row in rows:
        h = row['horizon']
        require(row['failure'] is None and row['delivered'] > 30, 'Historical availability/failure')
        p = checked_child(result_path.parent,row['trajectory_file']); require_sha(p,row['trajectory_sha256'])
        with np.load(p,allow_pickle=False) as z:
            trace = {k:z[k].copy() for k in ('states','actions','goal_state')}
        np.testing.assert_array_equal(trace['goal_state'],goals[h])
        require(len(trace['actions']) == row['delivered'] and len(trace['states']) == row['delivered']+1, 'History length')
        traces[h] = (row,trace)
    prior = COMBINED_ROOT/f'ref-{ref}-repeat-0'
    expected = certificate['seals'][str(prior)]
    require(set(expected) == {'REPORT.json','BANKS.npz'}, 'Prior seal schema')
    for name,digest in expected.items(): require_sha(prior/name,digest)
    prior_report = json.loads((prior/'REPORT.json').read_text())
    require(prior_report['reference'] == ref and prior_report['repeat'] == 0 and
            prior_report['model_state_sha256'] == MODEL_SHA and
            prior_report['all_technical_checks_passed'] is True, 'Prior identity')
    with np.load(prior/'BANKS.npz',allow_pickle=False) as z:
        banks = {k:z[k].copy() for k in z.files if not any('/'+s+'/' in k for s in ('state','latent','joint'))
                 and '/first-' not in k}
    return initial, goals, traces, banks, {'reference_sha256':record['sha256'],
        'historical_result_sha256':sha256(result_path),'prior_seals':expected,
        'prior_runner_sha256':prior_report['program_sha256'],'combined_sha256':COMBINED_SHA}


def check_approval(path, source_sha, protocol_sha):
    """A real researcher approval file must be supplied AFTER this preparation."""
    approval = json.loads(Path(path).read_text())
    require(approval.get('researcher_approved') is True and
            approval.get('experiment') == 'single-anchor-ranking-20260914' and
            approval.get('source_manifest_sha256') == source_sha and
            approval.get('protocol_sha256') == protocol_sha and
            approval.get('repeats') == 2 and approval.get('gpu_seconds') == 14400 and
            approval.get('job_seconds') == 900 and approval.get('storage_bytes') == 2_000_000_000,
            'Missing/mismatched researcher approval; no execution')
    return approval
