"""Independent primitive/endpoint checks; no policy or model imports."""
import numpy as np


def check_episode(result,tree):
    trace=result['trace'];decision=result['decision']
    if result['steps']!=len(trace) or len(trace)>150:raise AssertionError('Step budget')
    if not trace:
        if decision is not None:raise AssertionError('Unexpected empty active episode')
        return True
    prefix=tree.nodes[decision['prefix']].prefix
    suffix_index=result['selected_suffix']
    for i,row in enumerate(trace):
        clock=i+1
        if row['clock']!=clock:raise AssertionError('Absolute clock reset/gap')
        if i and any(trace[i-1][key] for key in ('success','terminated','truncated')):
            raise AssertionError('Work after native termination')
        expected_stage='prefix' if clock<=5 else 'suffix' if clock<=15 else 'baseline-tail'
        if row['stage']!=expected_stage:raise AssertionError('5+10+135 association')
        if clock<=5:expected=prefix[i]
        elif clock<=15:
            if suffix_index is None:raise AssertionError('Missing suffix association')
            expected=tree.nodes[decision['prefix']].suffixes[suffix_index][clock-6]
        else:expected=None
        if expected is not None and not np.array_equal(expected,row['action']):raise AssertionError('Wrong prefix/suffix action')
    if bool(result['success'])!=any(row['success'] for row in trace):raise AssertionError('Native endpoint mismatch')
    if len(trace)<150 and not any(trace[-1][key] for key in ('success','terminated','truncated')):
        raise AssertionError('Unexplained early stopping')
    return True
