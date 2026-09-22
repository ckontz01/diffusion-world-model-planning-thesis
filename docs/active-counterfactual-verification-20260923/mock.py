"""Artificial vector environments and source-grouped branch collector only."""
import hashlib
import json
import numpy as np
from policy import Observation,context,features
from tree import Node,Tree,finite,identity


def abstract_tree():
    """Prototype's three physical abstract action codes, not source/slot features.

    The action content itself distinguishes robust / two opposite continuations.
    Encoding does not add hidden mode, true probability, outcome, or case name.
    Five/ten repetitions are an interface embedding, not PushT physics evidence.
    """
    prefixes=[np.tile([v,0.],(5,1)) for v in (0.,.5,-.5)]
    suffixes=tuple(np.tile([v,0.],(10,1)) for v in (0.,.5,-.5))
    nodes=tuple(Node(p,suffixes,np.array([p[0,0],0,0,0.]),
                     tuple(np.array([p[0,0],a[0,0],0,0.]) for a in suffixes),
                     ('baseline-or-robust','positive-command','negative-command')) for p in prefixes)
    return Tree(nodes,np.concatenate((prefixes[0],suffixes[0])),0).validate()


def prototype_dataset(case,n,seed,role):
    from prototype.experiment import draw_training
    rng=np.random.default_rng(np.random.SeedSequence([seed,int(hashlib.sha256(case.name.encode()).hexdigest()[:8],16)]))
    # Exact original training generator. On held-out reversal, invert only the
    # relevant observed response, as the original specified test law does.
    observations,outcomes=draw_training(case,n,rng)
    if role!='fit' and case.shift_flip:observations[:,1]=1-observations[:,1]
    tree=abstract_tree();h=context([np.zeros(4)],[],np.zeros(4),0)
    rows=[]
    for source in range(n):
        for p,node in enumerate(tree.nodes):
            x,a=features(h,node)
            r=np.array([2*observations[source,p]-1,0.,0.,0.])
            rows.append(dict(source_id=f'{case.name}/{role}/{seed}/{source}',role=role,x=x[0],a=a[0],r=r,
                             y=outcomes[source,p],terminal=2,mask=np.ones(3,dtype=bool)))
    data=pack(rows)
    data_digest=hashlib.sha256(observations.tobytes()+outcomes.tobytes()).hexdigest()
    return data,tree,h,data_digest


def pack(rows):
    if not rows:raise ValueError('No source records')
    maxk=max(max(len(r['a']),1) for r in rows);adim=rows[0]['a'].shape[-1]
    output=dict(x=[],a=[],r=[],y=[],terminal=[],mask=[],source_ids=[],roles=[])
    seen=set()
    for r in rows:
        key=(r['source_id'],identity(r['x']))
        if key in seen:raise ValueError('Duplicate source/prefix record')
        seen.add(key)
        k=len(r['a']);aa=np.zeros((maxk,adim));yy=np.zeros(maxk);mask=np.zeros(maxk,dtype=bool)
        if k>4 or len({identity(v) for v in r['a']})!=k:raise ValueError('Duplicate/oversized suffix bank')
        if r['terminal']!=2 and k:raise ValueError('Terminal prefix cannot carry unused suffix labels')
        if r['terminal']==2 and not k:raise ValueError('Active prefix requires its own suffix labels')
        aa[:k]=r['a'];yy[:k]=r['y'];mask[:k]=True
        for name,value in [('x',r['x']),('a',aa),('r',r['r']),('y',yy),('terminal',r['terminal']),
                           ('mask',mask),('source_ids',r['source_id']),('roles',r['role'])]:output[name].append(value)
    return {k:np.asarray(v) for k,v in output.items()}


class VectorEnv:
    """Deterministic mock, not a simulator. New instance owns all state and RNG.

    The only policy-facing methods are initial() and step(). No counterfactual
    outcome API is provided. Collector may read history_digest for clone checks.
    """
    def __init__(self,seed=94031,success_at=None,truncate_at=None):
        self._rng=np.random.default_rng(seed);self._latent=np.zeros(4)
        self._clock=0;self._done=False;self._success_at=success_at;self._truncate_at=truncate_at
        self._history=[];self.calls=0

    def initial(self):
        if self._clock:raise RuntimeError('Episode already started')
        return Observation(self._latent.copy(),0)

    def step(self,action):
        if self._done or self._clock>=150:raise RuntimeError('Post-terminal step')
        a=finite(action)
        if a.shape!=(2,) or np.max(abs(a))>1:raise ValueError('Primitive action')
        self._latent[:2]+=a*.01;self._latent[2:]+=self._rng.normal(0,.001,2)
        self._clock+=1;self.calls+=1
        success=self._clock==self._success_at;truncated=self._clock==self._truncate_at
        self._done=success or truncated
        self._history.append((self._clock,a.tolist(),self._latent.tolist(),success,truncated))
        return Observation(self._latent.copy(),self._clock,success,success,truncated)

    def history_digest(self):
        return hashlib.sha256(json.dumps(self._history,sort_keys=True).encode()).hexdigest()


def mock_rollout(current,normalized):
    from tree import FrozenPort
    physical=normalized.reshape(-1,15,2)*FrozenPort.scale+FrozenPort.mean
    z=np.repeat(np.asarray(current)[None,None,:],len(physical),0)
    path=[z[:,0].copy()]
    for t in range(3):
        nxt=path[-1].copy();nxt[:,:2]+=physical[:,t*5:(t+1)*5].sum(1)*.01;path.append(nxt)
    return np.stack(path,1)


def collect_source(source_id,role,tree,factory,goal,tail_planner):
    """Fresh construction + exact prefix replay, never visible-state assignment.

    One canonical response record per prefix; replay steps charged. A terminated
    prefix is executed ONCE and carries zero suffix branches. Active replays must
    match all actual prefix observations/actions and endpoint status exactly.
    """
    records=[];receipts=[];steps=0;episodes=0;response_observations=0
    for p,node in enumerate(tree.nodes):
        base_hash=None;labels=[];prefix_r=None;terminal=2
        for i,suffix in enumerate(node.suffixes):
            env=factory();episodes+=1;obs=env.initial();history=[obs.latent.copy()];actions=[]
            h=context(history,actions,goal,0)
            for action in node.prefix:
                obs=env.step(action);actions.append(action.copy());steps+=1
                if obs.done:break
            prefix_hash=env.history_digest()
            if i==0:
                base_hash=prefix_hash
                if obs.done:
                    terminal=0 if obs.success else 1
                    receipts.append(dict(prefix=p,terminal=terminal,steps=obs.clock,unused_suffixes_executed=0,
                                         common_history_sha256=prefix_hash))
                    break
                prefix_r=obs.latent-node.predicted_prefix;response_observations+=1
            elif prefix_hash!=base_hash:raise ValueError('Actual common-prefix history mismatch')
            history.append(obs.latent.copy())
            for action in suffix:
                obs=env.step(action);actions.append(action.copy());steps+=1
                if obs.clock%5==0:history.append(obs.latent.copy())
                if obs.done:break
            while not obs.done and obs.clock<150:
                plan=tail_planner(tuple(history),tuple(actions),obs,150-obs.clock)
                for action in plan[:150-obs.clock]:
                    obs=env.step(action);actions.append(action.copy());steps+=1
                    if obs.clock%5==0:history.append(obs.latent.copy())
                    if obs.done:break
            labels.append(int(obs.success))
            receipts.append(dict(prefix=p,suffix=i,steps=obs.clock,success=bool(obs.success),
                                 common_history_sha256=prefix_hash,plan_sha256=identity(np.concatenate((node.prefix,suffix)))))
        x,a=features(h,node)
        records.append(dict(source_id=source_id,role=role,x=x[0],a=a[0] if terminal==2 else np.empty((0,a.shape[-1])),
                            r=prefix_r if terminal==2 else np.zeros(len(node.predicted_prefix)),
                            y=np.array(labels),terminal=terminal))
    return records,dict(source_id=source_id,physical_steps=steps,constructed_episodes=episodes,
                        canonical_response_observations=response_observations,branches=receipts)
