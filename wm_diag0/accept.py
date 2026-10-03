"""Independent saved-array/action/endpoint checks. No success-improvement gate."""
import numpy as np
from .core import array_id


def check_branch(record, candidate, source, native_endpoint):
    if record['candidate_id'] != candidate.identity or record['parent'] != source.parent:
        raise ValueError('Candidate/source binding')
    if record['construction'] != source.construction_id or record['replay_id'] != array_id(source.replay_actions):
        raise ValueError('Construction/history binding')
    a, o = np.asarray(record['actions']), np.asarray(record['observations'])
    array_id(a); array_id(o)
    if array_id(o[0]) != source.observation_ids[-1]:
        raise ValueError('Saved diagnostic origin does not match authenticated replay')
    n = record['prefix_steps']
    if not 0 <= n <= len(candidate.actions) or a.shape[1:] != candidate.actions.shape[1:]:
        raise ValueError('Action shape/prefix count')
    # Byte equality, not allclose; native clipping/decoding must be bound before capture.
    if array_id(a[:n]) != array_id(candidate.actions[:n]):
        raise ValueError('Executed chunk bytes changed')
    if record['source_elapsed'] != source.elapsed or record['replay_steps'] != len(source.replay_actions):
        raise ValueError('Replay vs evaluation origin')
    if record['elapsed'] != source.elapsed + len(a) or record['elapsed'] > 50 or len(o) != len(a)+1:
        raise ValueError('Absolute budget/observation length')
    flags = tuple(bool(native_endpoint(x)) for x in o)
    expected_prefix = min(len(candidate.actions),50-source.elapsed)
    if n < expected_prefix and (len(a) != n or not (flags[-1] or record['terminal_flags'][-1] or record['truncation_flags'][-1])):
        raise ValueError('Candidate prefix omitted before tail/budget')
    if flags != record['endpoint_flags'] or bool(flags[-1]) != record['success']:
        raise ValueError('Independent native endpoint mismatch')
    if any(flags[:-1]):
        raise ValueError('Physics after success')
    for key in ('terminal_flags','truncation_flags'):
        stop = record[key]
        if len(stop) != len(o) or any(stop[:-1]): raise ValueError('Post-terminal/truncation work')
    if record['reason'] == 'truncated' and not record['truncation_flags'][-1]:
        raise ValueError('Truncation reason mismatch')
    if record['reason'] == 'terminal_failure' and not record['terminal_flags'][-1]:
        raise ValueError('Terminal reason mismatch')
    if record['success'] != (record['reason'] == 'success'):
        raise ValueError('Endpoint reason')
    if record['reason'] == 'budget_failure' and record['elapsed'] != 50:
        raise ValueError('Premature budget failure')
    if record['reason'] not in ('success','truncated','terminal_failure','budget_failure'):
        raise ValueError('Undeclared stop reason')
    if array_id(o[:n+1]) != record['prefix_id'] or array_id(a[n:]) != record['tail_id']:
        raise ValueError('Prefix/tail identity')
    return {'accepted': True, 'actions_sha256': array_id(a), 'observations_sha256': array_id(o)}


def check_draws(records, deterministic_prefix):
    if len(records) != 2 or len({r['draw_id'] for r in records}) != 2:
        raise ValueError('Two separately owned evaluation draws')
    if len({r['candidate_id'] for r in records}) != 1:
        raise ValueError('Draw candidate binding')
    for key in ('parent','construction','replay_id','source_elapsed'):
        if len({r[key] for r in records}) != 1:raise ValueError('Draw source/history binding')
    if deterministic_prefix and len({r['prefix_id'] for r in records}) != 1:
        raise ValueError('Deterministic prefix divergence')
    return True
