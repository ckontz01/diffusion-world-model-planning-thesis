"""Independent physical endpoint checks, no model or simulator imports."""
import hashlib
from pathlib import Path
import numpy as np
import lgp1_contract as c

def array_sha(value):
    a=np.ascontiguousarray(value)
    h=hashlib.sha256();h.update(str((a.shape,a.dtype.str)).encode());h.update(a.tobytes())
    return h.hexdigest()

def identity(reference,initial,goal,horizon):
    return dict(reference_file=reference['file'],reference_sha256=reference['sha256'],
                initial_key='initial_request',goal_key='states',goal_index=horizon,
                initial_sha256=array_sha(initial),goal_sha256=array_sha(goal))

def physical(evidence,row):
    """All evaluated states are POST action; t0 is only initialization evidence."""
    n=row['steps'];h=row['horizon'];budget=2*h
    c.require(h in (75,150) and isinstance(n,int) and 0<n<=budget,'Physical budget/count')
    required={'requested_initial','initialized_state','goal_state','post_states','actions','flags',
              'absolute_steps','physical_remaining','action_stage'}
    c.require(set(evidence)==required,'Missing or unexpected endpoint evidence')
    initial=evidence['requested_initial'];goal=evidence['goal_state'];states=evidence['post_states']
    flags=evidence['flags'];actions=evidence['actions']
    c.require(initial.shape==goal.shape==evidence['initialized_state'].shape==(7,),'Initial/goal shape')
    c.require(states.shape==(n,7) and states.dtype==np.float64 and np.isfinite(states).all(),'Raw post-action states')
    c.require(np.isfinite(initial).all() and np.isfinite(goal).all(),'Initial/goal values')
    for angles in (initial[4:5],goal[4:5],states[:,4],evidence['initialized_state'][4:5]):
        c.require(((angles>=0)&(angles<2*np.pi)).all(),'Reviewed angle domain [0,2pi)')
    # Exactly the existing FreshEpisode reset check, not a new tolerance.
    np.testing.assert_allclose(evidence['initialized_state'],initial,rtol=0,atol=1e-10)
    c.require(actions.shape==(n,2) and actions.dtype==np.float32 and np.isfinite(actions).all() and
              (abs(actions)<=1).all(),'Delivered action evidence')
    c.require(flags.shape==(n,2) and flags.dtype==np.bool_,'Missing/mistyped native terminal flags')
    steps=np.arange(1,n+1,dtype=np.int64)
    for name,expected in [('absolute_steps',steps),('physical_remaining',budget-steps),('action_stage',(steps-1)//15)]:
        c.require(evidence[name].dtype==np.int64 and np.array_equal(evidence[name],expected),'Absolute schedule evidence: '+name)
    c.require(not flags[:-1].any(),'Post-terminal action')
    # Unchanged PushT.eval_state: one combined agent/block norm and angle at
    # the SAME post-action step. No t0, modulo repair or velocity condition.
    joint=np.linalg.norm(goal[:4]-states[:,:4],axis=1)
    delta=np.abs(goal[4]-states[:,4]);angle=np.minimum(delta,2*np.pi-delta)
    native=(joint<20)&(angle<np.pi/9)
    c.require(np.array_equal(native,flags[:,0]),'Native success/terminal flag inconsistent with physical states')
    # Native PushT returns truncated=False; unchanged World uses TimeLimit300.
    c.require(np.array_equal(flags[:,1],steps>=300),'Mislabeled or missing TimeLimit truncation')
    c.require(n==budget or bool(flags[-1].any()),'Unexplained early nonterminal stopping')
    c.require(row['success']==int(native.any()),'Reported success inconsistent with physical states')
    c.require(type(row.get('terminated')) is bool and row['terminated']==bool(flags[-1,0]),'Reported terminal flag')
    c.require(type(row.get('truncated')) is bool and row['truncated']==bool(flags[-1,1]),'Reported truncation flag')
    stages=row['stages'];starts=list(range(0,n,15))
    c.require(len(stages)==len(starts),'Stage count')
    for i,(s,t) in enumerate(zip(stages,starts)):
        c.require(s['stage']==i and s['elapsed']==t and s['physical_remaining']==budget-t and
                  s['remaining']==h-t%h and s['final_goal']==(h-t%h==15),'Absolute stage/schedule fields')
    return dict(success=int(native.any()),actions=n,post_action_only=True)

def verify_file(root,row,reference,*,authenticate_reference=True):
    with np.load(Path(root)/f"endpoint-h{row['horizon']}.npz",allow_pickle=False) as z:
        evidence={k:z[k].copy() for k in z.files}
    c.require(row['endpoint_identity']==identity(reference,evidence['requested_initial'],evidence['goal_state'],row['horizon']),
              'Endpoint initial/goal identity')
    if authenticate_reference:
        # Only the allowlisted already-exposed reference, during execution.
        c.require(c.sha(reference['file'])==reference['sha256'],'Authenticated reference bytes')
        with np.load(reference['file'],allow_pickle=False) as z:
            np.testing.assert_array_equal(evidence['requested_initial'],z['initial_request'])
            np.testing.assert_array_equal(evidence['goal_state'],z['states'][row['horizon']])
    return physical(evidence,row)
