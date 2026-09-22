"""Independent primitive/endpoint checks; no policy or model imports."""
import numpy as np


def check_reference(result):
    rows=result['trace']
    assert result['steps']==len(rows)<=150
    for i,row in enumerate(rows):
        assert row['clock']==i+1
        assert np.isfinite(row['action']).all() and np.max(np.abs(row['action']))<=1
        if i:assert not any(rows[i-1][k] for k in ('success','terminated','truncated'))
    assert result['success']==any(r['success'] for r in rows)
    if rows and len(rows)<150:assert any(rows[-1][k] for k in ('success','terminated','truncated'))
    expected=[0]+list(range(5,150,15)) if result['early_replan'] else list(range(0,150,15))
    assert result['planner_clocks']==[t for t in expected if t<len(rows)]
    return True


def check_native_pusht(post_states,goal,success,terminated,truncated,actions):
    """Independent source-inspected native endpoint, on supplied arrays only.

    POST-action states Nx7; initial state deliberately absent. Native PushT
    uses a combined agent/block-position norm and circular block orientation.
    Standard TimeLimit is 300, so budget 150 alone is NOT truncation.
    No payloads, simulator or trained models are loaded by this checker.
    """
    states=np.asarray(post_states,dtype=float);g=np.asarray(goal,dtype=float);a=np.asarray(actions,dtype=float)
    assert states.ndim==2 and states.shape[1]==7 and 1<=len(states)<=150
    assert g.shape==(7,) and a.shape==(len(states),2)
    assert np.isfinite(states).all() and np.isfinite(g).all() and np.isfinite(a).all() and np.max(abs(a))<=1
    theta=np.mod(np.abs(states[:,4]-g[4]),2*np.pi);theta=np.minimum(theta,2*np.pi-theta)
    native=(np.linalg.norm(states[:,:4]-g[:4],axis=1)<20)&(theta<np.pi/9)
    s=np.asarray(success,dtype=bool);t=np.asarray(terminated,dtype=bool);u=np.asarray(truncated,dtype=bool)
    assert s.shape==t.shape==u.shape==(len(states),)
    assert np.array_equal(s,native) and np.array_equal(t,native)
    assert not u.any()  # original native TimeLimit=300, never reached here
    assert not (s|t|u)[:-1].any()
    assert len(states)==150 or bool(t[-1])
    return dict(success=bool(native.any()),steps=len(states),independent=True)


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
