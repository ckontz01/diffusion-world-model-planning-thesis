"""Full collect/evaluate executor over a real or artificial episode interface."""
import common as c
import time
import io
import numpy as np
from tree import Ledger, FrozenPort, construct_tree
from policy import context
from runtime_adapter import BaselinePlanner


def tree_arrays(tree):
    tree.validate(); d = len(tree.nodes[0].predicted_prefix)
    arrays = {'tree/baseline': tree.baseline_plan, 'tree/count': np.array([len(n.suffixes) for n in tree.nodes], np.int64),
              'tree/prefix': np.stack([n.prefix for n in tree.nodes]),
              'tree/predicted_prefix': np.stack([n.predicted_prefix for n in tree.nodes]),
              'tree/suffix': np.zeros((len(tree.nodes), 4, 10, 2)),
              'tree/predicted_terminal': np.zeros((len(tree.nodes), 4, d))}
    for p, n in enumerate(tree.nodes):
        arrays['tree/suffix'][p, :len(n.suffixes)] = n.suffixes
        arrays['tree/predicted_terminal'][p, :len(n.suffixes)] = n.predicted_terminals
    return arrays


def build_tree(env, rollout, ledger, reference, settings=None):
    # Deliberately no labels/branch callbacks/source payload supplied to search.
    planner = BaselinePlanner(env.goal, rollout, ledger, [94041, reference], **(settings or {}))
    initial = env.initial()
    solve = planner.solve(initial.latent, 0)
    port = FrozenPort(initial.latent, env.goal, rollout, ledger)
    tree = construct_tree(port, solve, **(settings or {}))
    return tree, planner


def execute(env, tree, selector, mode, planner, ledger, fixed_pair=None):
    obs = env.initial(); history = [obs.latent.copy()]; actions = []; plans = []; plan_indices = []; offsets = []
    ledger.observations += 1; prefix = suffix = None; decision = None
    c.require(obs.clock == 0 and not obs.done, 't0 is initialization, never success')
    h = context(history, actions, env.goal, 0)
    env.inflight = {'mode':mode,'plans':plans,'prefix':None,'suffix':None}

    def do(plan, stage, length=None):
        nonlocal obs
        a = np.asarray(plan)
        c.require(a.ndim == 2 and a.shape[1] == 2 and np.isfinite(a).all() and (abs(a) <= 1).all(), 'Plan coordinates')
        i = len(plans); plans.append({'start': obs.clock, 'stage': stage, 'actions': a.copy()})
        count = min(len(a) if length is None else length, 150 - obs.clock)
        for k in range(count):
            c.require(not obs.done, 'No post-terminal step')
            obs = env.step(a[k]); actions.append(env.records[-1]['action'].copy())
            ledger.physical_steps += 1; ledger.observations += 1
            plan_indices.append(i); offsets.append(k)
            if obs.clock % 5 == 0: history.append(obs.latent.copy())
            if obs.done: break

    if mode in ('vanilla', 'early-replan'):
        first = True
        while not obs.done and obs.clock < 150:
            plan = planner(tuple(history), tuple(actions), obs, 150-obs.clock)
            do(plan, mode, 5 if first and mode == 'early-replan' else 15); first = False
    else:
        c.require(tree is not None, 'Matched tree required')
        if fixed_pair is None:
            decision = selector.select(tree, h, ledger, mode, 94021)
            prefix = decision.prefix
        else:
            prefix, suffix = fixed_pair
        c.require(0 <= prefix < len(tree.nodes), 'Prefix index')
        node = tree.nodes[prefix]
        env.inflight['prefix'] = prefix
        do(node.prefix, 'prefix')
        if not obs.done:
            if fixed_pair is None: suffix = selector.after(decision, tree, h, obs.latent, ledger)
            c.require(type(suffix) in (int, np.int64) and 0 <= suffix < len(node.suffixes), 'Cross-prefix suffix')
            env.inflight['suffix'] = int(suffix)
            do(node.suffixes[suffix], 'suffix')
        else:
            suffix = None
        while not obs.done and obs.clock < 150:
            c.require(obs.clock >= 15, 'Premature tail')
            plan = planner(tuple(history), tuple(actions), obs, 150-obs.clock)
            do(plan, 'baseline-tail')
    c.require(len(env.records) == obs.clock, 'Trace/action clock')
    return {'prefix': prefix, 'suffix': None if suffix is None else int(suffix), 'mode': mode,
            'decision': None if decision is None else decision.__dict__, 'plans': plans,
            'plan_indices': np.array(plan_indices, np.int64), 'offsets': np.array(offsets, np.int64),
            'success': bool(obs.success), 'steps': obs.clock, 'ledger': vars(ledger).copy()}


def capture(env, result, arrays, name, save_prefix_images):
    for key in ('state', 'proprio', 'latent', 'dynamics', 'pixel_hash', 'flags', 'action'):
        arrays[name + '/' + key] = np.stack([r[key] for r in env.records])
        arrays[name + '/initial_' + key] = np.asarray(env.first[key])
    arrays[name + '/clock'] = np.arange(1, result['steps']+1, dtype=np.int64)
    arrays[name + '/remaining'] = 150 - arrays[name + '/clock']
    arrays[name + '/plan_index'] = result.pop('plan_indices'); arrays[name + '/plan_offset'] = result.pop('offsets')
    for i, p in enumerate(result['plans']):
        arrays[f'{name}/plan{i}'] = p.pop('actions')
    if save_prefix_images:
        arrays[name + '/prefix_images'] = np.asarray(env.prefix_images, np.uint8)
    return result


def partial_evidence(env, arrays):
    """Retain in-memory work on a fault; never treated as a completed job."""
    partial = dict(arrays)
    if env is not None:
        for k in ('state','proprio','latent','dynamics','pixel_hash','flags','action'):
            partial['failed_branch/initial_'+k] = np.asarray(env.first[k])
            if env.records:partial['failed_branch/'+k] = np.stack([r[k] for r in env.records])
        pending = dict(getattr(env,'inflight',{})); saved=[]
        for i,p in enumerate(pending.pop('plans',[])):
            p=dict(p); actions=p.pop('actions',None)
            if actions is not None:partial[f'failed_branch/plan{i}']=actions
            saved.append(p)
        pending['plans']=saved
        return partial,pending
    return partial,{}


def collect(factory, rollout, reference, role, *, settings=None, preserve=None):
    c.require(role in ('fit', 'validation'), 'Collection role')
    first = factory(); env=first; arrays = {}; branches = []; start = time.monotonic()
    try:
        ledger = Ledger(); tree, first_planner = build_tree(first, rollout, ledger, reference, settings)
        arrays.update(tree_arrays(tree))
        arrays['requested_initial'] = np.asarray(first.record['state'], np.float64)
        arrays['goal_state'] = np.asarray(first.record['goal_state'], np.float64)
        arrays['initial_image'] = first.initial_image; arrays['goal_image'] = first.goal_image; arrays['goal_latent'] = first.goal
        for p, node in enumerate(tree.nodes):
            common_prefix = None
            for s in range(len(node.suffixes)):
                if p == 0 and s == 0: env, plan, accounting = first, first_planner, ledger
                else:
                    env = factory(); accounting = Ledger()
                    plan = BaselinePlanner(env.goal, rollout, accounting, [94041, reference], **(settings or {}))
                try:
                    np.testing.assert_array_equal(env.initial_image, arrays['initial_image'])
                    np.testing.assert_array_equal(env.goal_image, arrays['goal_image'])
                    result = execute(env, tree, None, 'collection', plan, accounting, (p, s))
                    name = f'b{len(branches)}'
                    branches.append(capture(env, result, arrays, name, s == 0))
                    # Compare ALL physical replay fields, not just latent embeddings.
                    fields = ('state', 'proprio', 'latent', 'dynamics', 'pixel_hash', 'flags', 'action')
                    prefix = {k: arrays[name+'/'+k][:5] for k in fields}
                    if common_prefix is None: common_prefix = prefix
                    else:
                        for k in fields: np.testing.assert_array_equal(prefix[k], common_prefix[k])
                    if result['suffix'] is None: break  # terminal prefix once, zero fictional suffixes
                finally: env.close()
    except BaseException:
        if preserve is not None:
            partial,pending=partial_evidence(env,arrays)
            preserve(partial,{'complete':False,'kind':'partial-collection','reference':reference,'role':role,
                              'completed_branches':branches,'inflight':pending})
        raise
    finally: first.close()
    return arrays, {'reference': reference, 'role': role, 'kind': 'collection', 'branches': branches,
                    'tree_origins': [list(n.origins) for n in tree.nodes], 'duplicates_skipped': tree.duplicates_skipped,
                    'wall_seconds': time.monotonic()-start}


def evaluate(factory, rollout, reference, mode, selector, *, settings=None, preserve=None):
    c.require(mode in c.CONTROLS, 'Fixed control')
    env = factory(); start = time.monotonic();arrays={}
    try:
        ledger = Ledger()
        if mode in ('vanilla', 'early-replan'):
            tree = None; arrays = {}
            planner = BaselinePlanner(env.goal, rollout, ledger, [94041, reference], **(settings or {}))
        else:
            tree, planner = build_tree(env, rollout, ledger, reference, settings)
            arrays = tree_arrays(tree)
        arrays.update(requested_initial=np.asarray(env.record['state'], np.float64),
                      goal_state=np.asarray(env.record['goal_state'], np.float64), goal_latent=env.goal,
                      initial_image=env.initial_image, goal_image=env.goal_image)
        result = execute(env, tree, selector, mode, planner, ledger)
        capture(env, result, arrays, 'b0', True)
        return arrays, {'reference': reference, 'role': 'final_development', 'kind': 'evaluation', 'control': mode,
                        'branches': [result], 'wall_seconds': time.monotonic()-start}
    except BaseException:
        if preserve is not None:
            partial,pending=partial_evidence(env,arrays)
            preserve(partial,{'complete':False,'kind':'partial-evaluation','reference':reference,'control':mode,'inflight':pending})
        raise
    finally: env.close()


def save(directory, arrays, metadata):
    """Uncompressed numeric NPZ, complete evidence; deterministic byte accounting."""
    stream=io.BytesIO();np.savez(stream,**arrays);payload=stream.getvalue()
    cap=10_000_000 if metadata['kind']=='collection' else 2_000_000
    c.require(len(payload)+len(c.canonical(metadata))+100_000<=cap,'Pre-write complete evidence/technical/seal reservation')
    with (directory / 'evidence.npz').open('xb') as f:f.write(payload)
    c.write(directory / 'EVIDENCE.json', metadata)
