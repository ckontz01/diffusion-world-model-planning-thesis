"""Independent SAVED-evidence verifier: no model, physics or executor imports."""
import common as c
import hashlib
import numpy as np


def ah(a):
    a = np.ascontiguousarray(a)
    return hashlib.sha256(str((a.shape, a.dtype.str)).encode() + a.tobytes()).digest()


def verify_arrays(a, m, *, role_map=None):
    rm = c.roles() if role_map is None else role_map
    c.require(m['reference'] in rm[m['role']], 'Whole-source role')
    goal, initial = a['goal_state'], a['requested_initial']
    c.require(goal.shape == initial.shape == (7,), 'Initial/goal shape')
    for x in (goal, initial): c.require(np.isfinite(x).all() and 0 <= x[4] < 2*np.pi, 'Canonical state')
    has_tree = 'tree/count' in a
    if has_tree:
        counts = a['tree/count']; prefixes = a['tree/prefix']; suffixes = a['tree/suffix']
        c.require(1 <= len(counts) <= 4 and all(1 <= n <= 4 for n in counts), 'Tree counts')
        c.require(prefixes.shape == (len(counts), 5, 2) and suffixes.shape == (len(counts), 4, 10, 2), 'Tree axes')
        np.testing.assert_array_equal(a['tree/baseline'], np.concatenate((prefixes[0], suffixes[0, 0])))
        c.require(len({ah(p) for p in prefixes}) == len(counts), 'Unique prefixes')
        for p, n in enumerate(counts):
            c.require(len({ah(s) for s in suffixes[p, :n]}) == n, 'Unique suffixes')
        c.require(a['tree/predicted_prefix'].shape==(len(counts),192) and a['tree/predicted_terminal'].shape==(len(counts),4,192),'Tree feature axes')
        for k in ('tree/predicted_prefix','tree/predicted_terminal'):
            c.require(np.isfinite(a[k]).all(),'Finite frozen predicted features')
        c.require(np.isfinite(prefixes).all() and np.isfinite(suffixes).all() and (abs(prefixes)<=1).all() and (abs(suffixes)<=1).all(), 'Tree action coordinates')
    successes = []; prefix_groups = {}
    for b, meta in enumerate(m['branches']):
        name = f'b{b}/'; n = meta['steps']; states = a[name+'state']; flags = a[name+'flags']; actions = a[name+'action']
        c.require(type(n) is int and 0 < n <= 150, 'No t0 success/budget overflow')
        c.require(states.shape == (n, 7) and states.dtype == np.float64 and np.isfinite(states).all(), 'Post states')
        c.require(actions.shape == (n, 2) and actions.dtype == np.float32 and np.isfinite(actions).all() and (abs(actions)<=1).all(), 'Actual delivered actions')
        c.require(flags.shape == (n, 2) and flags.dtype == bool and not flags[:-1].any(), 'No post-terminal actions')
        c.require(not flags[:, 1].any(), '150 budget is not native truncation')
        c.require(((states[:,4]>=0)&(states[:,4]<=2*np.pi)).all(), 'Observed angle convention')
        delta = abs(goal[4]-states[:, 4]); angle = np.minimum(delta, 2*np.pi-delta)
        native = (np.linalg.norm(states[:, :4]-goal[:4], axis=1)<20) & (angle < np.pi/9)
        np.testing.assert_array_equal(native, flags[:, 0])
        c.require(n == 150 or native[-1], 'Legitimate terminal or full-budget failure')
        c.require(meta['success'] == bool(native.any()), 'Native same-step success')
        np.testing.assert_array_equal(a[name+'clock'], np.arange(1, n+1))
        np.testing.assert_array_equal(a[name+'remaining'], 150-np.arange(1, n+1))
        np.testing.assert_allclose(a[name+'initial_state'], initial, atol=1e-10, rtol=0)
        np.testing.assert_array_equal(a[name+'proprio'], states[:, [0, 1, 5, 6]])
        np.testing.assert_array_equal(a[name+'initial_pixel_hash'], np.frombuffer(ah(a['initial_image']), np.uint8))
        c.require(not a[name+'initial_flags'].any(), 'Initial flags must not certify success')
        c.require(a[name+'latent'].shape == (n,192) and a[name+'dynamics'].shape == (n,25), 'Latent/dynamics layout')
        np.testing.assert_array_equal(states[:,:4],a[name+'dynamics'][:,[0,1,9,10]])
        np.testing.assert_array_equal(states[:,5:7],a[name+'dynamics'][:,[2,3]])
        np.testing.assert_array_equal(a[name+'initial_state'][:4],a[name+'initial_dynamics'][[0,1,9,10]])
        for key in ('latent','dynamics','initial_latent','initial_dynamics'):
            c.require(np.isfinite(a[name+key]).all(), 'Finite saved evidence')
        if name+'prefix_images' in a:
            images = a[name+'prefix_images']
            c.require(images.shape == (min(n,5),224,224,3) and images.dtype==np.uint8, 'Canonical prefix images')
            for t, image in enumerate(images): np.testing.assert_array_equal(a[name+'pixel_hash'][t], np.frombuffer(ah(image),np.uint8))
        plans = meta['plans']; pi = a[name+'plan_index']; offsets = a[name+'plan_offset']
        c.require(len(pi) == len(offsets) == n, 'Tail association length')
        starts = []
        for j, plan in enumerate(plans):
            start = plan['start']; starts.append(start); values = a[name+f'plan{j}']
            stop = plans[j+1]['start'] if j+1 < len(plans) else n
            c.require(0 <= start < stop <= n and values.shape[1:] == (2,), 'Plan start/length')
            np.testing.assert_array_equal(pi[start:stop], np.full(stop-start, j))
            np.testing.assert_array_equal(offsets[start:stop], np.arange(stop-start))
            np.testing.assert_array_equal(actions[start:stop], values[:stop-start].astype(np.float32))
            if plan['stage'] == 'prefix':
                c.require(start == 0 and values.shape == (5,2), 'Prefix starts at zero')
                np.testing.assert_array_equal(values, prefixes[meta['prefix']])
            elif plan['stage'] == 'suffix':
                p, s = meta['prefix'], meta['suffix']
                c.require(start == 5 and type(s) is int and 0<=s<int(counts[p]), 'Illegal cross-prefix suffix')
                np.testing.assert_array_equal(values, suffixes[p,s])
            else:
                c.require(values.shape == (15,2), 'Tail/reference full solve')
                c.require(plan['stage'] in ('baseline-tail','vanilla','early-replan'), 'Unknown execution stage')
        mode = meta['mode']
        if mode in ('vanilla','early-replan'):
            expected = list(range(0,n,15)) if mode=='vanilla' else [0]+list(range(5,n,15))
            c.require(starts == expected, 'Absolute reference solve schedule')
        else:
            c.require(has_tree, 'Matched tree missing')
            p, s = meta['prefix'], meta['suffix']
            c.require(type(p) is int and 0<=p<len(counts), 'Prefix association')
            expected = [0] + ([5] if n>5 else []) + list(range(15,n,15))
            c.require(starts == expected, 'Five+ten+135 absolute schedule')
            c.require((s is None) == (n<=5), 'Terminal prefix has no fictional suffix')
            if m['kind'] == 'collection': prefix_groups.setdefault(p, []).append((b,s))
        successes.append(int(native.any()))
    if m['kind'] == 'collection':
        c.require(set(prefix_groups) == set(range(len(counts))), 'All tree prefixes collected')
        for p, branches in prefix_groups.items():
            expected = [None] if branches[0][1] is None else list(range(int(counts[p])))
            c.require([s for _,s in branches] == expected, 'Complete unique suffixes/terminal prefix once')
            first = f'b{branches[0][0]}/'
            for b,_ in branches[1:]:
                for field in ('state','proprio','dynamics','latent','pixel_hash','flags','action'):
                    np.testing.assert_array_equal(a[f'b{b}/'+field][:5], a[first+field][:5])
                    np.testing.assert_array_equal(a[f'b{b}/initial_'+field], a[first+'initial_'+field])
    else:
        c.require(len(successes)==1 and m['control'] == m['branches'][0]['mode'], 'One outcome/source/control')
    return {'passed': True, 'reference': m['reference'], 'role': m['role'], 'branches': len(successes),
            'actions': sum(b['steps'] for b in m['branches']), 'successes': successes,
            'post_action_only': True, 'physical_replay_checked': m['kind']=='collection'}


def load_verify(directory, *, role_map=None, authorization=None):
    with np.load(directory/'evidence.npz', allow_pickle=False) as z: a = {k:z[k] for k in z.files}
    m = c.read(directory/'EVIDENCE.json')
    if authorization is not None:
        c.require(type(authorization) is c.Authorization,'Independent reference check requires execution capability')
        ref=authorization.reference(m['reference'],m['role'])
        c.require(m['reference_identity']==ref,'Saved exact input/source identity')
        # Independent reader, distinct from the world factory. Only this job's
        # explicitly allowlisted initial/H75 pair is decoded, not old endpoints.
        with np.load(ref['file'],allow_pickle=False) as z:
            np.testing.assert_array_equal(a['requested_initial'],z['initial_request'])
            np.testing.assert_array_equal(a['goal_state'],z['states'][75])
        c.require(ah(a['requested_initial']).hex()==m['initial_sha256'] and ah(a['goal_state']).hex()==m['goal_sha256'],'Saved initial/goal digests')
    return a, m, verify_arrays(a,m,role_map=role_map)


def dataset_rows(a,m):
    """Derive labels from already independently checked evidence, canonical r once."""
    from policy import context, features
    from tree import Node
    rows = []
    for p,n in enumerate(a['tree/count']):
        bs = [(i,b) for i,b in enumerate(m['branches']) if b['prefix']==p]; i,b = bs[0]
        node = Node(a['tree/prefix'][p], tuple(a['tree/suffix'][p,:n]), a['tree/predicted_prefix'][p],
                    tuple(a['tree/predicted_terminal'][p,:n]), tuple('saved' for _ in range(n)))
        h = context([a[f'b{i}/initial_latent']], [], a['goal_latent'], 0); x,aa = features(h,node)
        terminal = b['suffix'] is None
        rows.append({'source_id': str(m['reference']), 'role': m['role'], 'x':x[0],
                     'a':np.empty((0,212)) if terminal else aa[0],
                     'r':np.zeros(192) if terminal else a[f'b{i}/latent'][4]-node.predicted_prefix,
                     'terminal':0 if terminal else 2,
                     'y':np.array([]) if terminal else np.array([int(t['success']) for _,t in bs])})
    return rows
