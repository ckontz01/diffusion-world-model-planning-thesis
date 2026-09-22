"""One active opportunity, initial decision only, no physical branch callback."""
from dataclasses import dataclass
import numpy as np
from tree import finite, identity, tie_argmax


@dataclass(frozen=True)
class Observation:
    latent: np.ndarray
    clock: int
    success: bool = False
    terminated: bool = False
    truncated: bool = False

    @property
    def done(self):return self.success or self.terminated or self.truncated


def context(history,action_history,goal,elapsed):
    if not 0<=elapsed<=150:raise ValueError('Absolute clock')
    frames=[finite(v) for v in history][-3:]
    while len(frames)<3:frames.insert(0,frames[0].copy())
    actions=np.zeros((10,2))
    if len(action_history):
        tail=np.asarray(action_history)[-10:];actions[-len(tail):]=tail
    return np.concatenate((*frames,finite(goal),actions.ravel(),
                           [elapsed/150,(150-elapsed)/150,75/150,5/150,10/150,1]))


def features(h,node):
    x=np.concatenate((finite(h),node.prefix.ravel(),node.predicted_prefix))
    a=np.stack([np.concatenate((s.ravel(),z)) for s,z in zip(node.suffixes,node.predicted_terminals)])
    return x[None],a[None]


@dataclass(frozen=True)
class Decision:
    prefix: int
    suffix: int | None
    mode: str
    values: tuple
    direct_baseline: bool


class Selector:
    """A/static B/passive C/active D/no-update E/ordinary. F separate Bayes port.

    Explicit injection is limited to outcome predictors, never a world object.
    All comparisons share the same learned response sampler, terminal head and
    128 integration samples per prefix; no-update pays the same computation as C.
    """
    MODES=('static','passive','active','no_update','ordinary','bayesian')

    def __init__(self,joint,ordinary=None,bayesian=None):
        self.joint=joint;self.ordinary=ordinary;self.bayesian=bayesian

    def conditional(self,x,a,r,mode,ledger=None):
        if ledger is not None:ledger.learned_module_forward_calls+=1
        if mode=='ordinary':
            if self.ordinary is None:raise ValueError('Ordinary model required')
            return self.ordinary.forward(x,a,r)[0]
        if mode=='bayesian':
            if self.bayesian is None:raise ValueError('Bayesian predictor required')
            return self.bayesian.predict(x,a,r)
        return self.joint.forward(x,a,r)[0]['q']

    def select(self,tree,h,ledger,mode='active',seed=94021):
        if mode not in self.MODES:raise ValueError('Unknown control')
        tree.validate();d=self.joint.rdim
        # Separate integration RNG; the same normals are used for all prefixes.
        rng=np.random.default_rng(seed);half=rng.normal(size=(16,d));eps=np.concatenate((half,-half))
        values=[];means=[]
        for node in tree.nodes:
            x,a=features(h,node);o,_=self.joint.forward(x,a)
            ledger.learned_module_forward_calls+=1;ledger.prior_candidate_predictions+=len(node.suffixes)
            # Stratified mixture integral: 32 antithetic normals per component.
            rnorm=o['mu'][0,:,None,:]+np.sqrt(o['var'][0,:,None,:])*eps[None]
            samples=rnorm.reshape(128,d)
            r=samples*self.joint.pre.rstd+self.joint.pre.rmean if self.joint.pre else samples
            weights=np.repeat(o['pi'][0]/32,32)
            xx=np.repeat(x,128,0);aa=np.repeat(a,128,0)
            q=self.conditional(xx,aa,r,mode,ledger)
            ledger.integration_responses+=128;ledger.outcome_queries+=128*len(node.suffixes)
            if ledger.integration_responses>512:raise RuntimeError('Single-opportunity integration cap')
            ps,pf,pa=o['terminal'][0]
            values.append(float(ps+pa*np.dot(weights,np.max(q,axis=1))))
            # Integration also gives the ordinary/Bayesian committed marginals.
            marginal=o['q'][0] if mode not in ('ordinary','bayesian') else weights@q
            means.append(ps+pa*marginal)
        baseline=float(means[0][0])
        if mode=='static':
            pairs=[(p,i) for p,n in enumerate(tree.nodes) for i in range(len(n.suffixes))]
            v=[means[p][i] for p,i in pairs]
            keys=[(0 if (p,i)==(0,0) else 1,identity(tree.nodes[p].prefix),identity(tree.nodes[p].suffixes[i])) for p,i in pairs]
            p,i=pairs[tie_argmax(v,keys)]
            return Decision(p,i,mode,tuple(values),(p,i)==(0,0))
        if mode=='passive':return Decision(0,None,mode,tuple(values),False)
        # Baseline commitment wins exact ties. No arbitrary bonus or probe penalty.
        p=tie_argmax(values,[(0 if i==0 else 1,identity(n.prefix)) for i,n in enumerate(tree.nodes)])
        if values[p]<=baseline:return Decision(0,0,mode,tuple(values),True)
        i=None
        if mode=='no_update':
            i=tie_argmax(means[p],[(0 if p==0 and k==0 else 1,identity(s)) for k,s in enumerate(tree.nodes[p].suffixes)])
        return Decision(p,i,mode,tuple(values),False)

    def after(self,decision,tree,h,observed_latent,ledger):
        if decision.suffix is not None:return decision.suffix
        node=tree.nodes[decision.prefix];x,a=features(h,node)
        r=(finite(observed_latent)-node.predicted_prefix)[None]
        q=self.conditional(x,a,r,decision.mode,ledger)[0];ledger.outcome_queries+=len(q)
        return tie_argmax(q,[(0 if decision.prefix==0 and i==0 else 1,identity(s)) for i,s in enumerate(node.suffixes)])


def execute_episode(env,tree,selector,goal,tail_planner,ledger,mode='active',integration_seed=94021):
    """env exposes only initial observation and step(action); no branch interface.

    step returns the actual post-action Observation, including native endpoint.
    No explicit observe-at-five call exists: earlier termination prevents all
    post-prefix model/observation work. Tail first planned at absolute action 15.
    """
    obs=env.initial()
    if obs.clock!=0:raise ValueError('Initial-only execution')
    history=[obs.latent.copy()];actions=[];trace=[];ledger.observations+=1
    if obs.done:return dict(trace=[],success=obs.success,steps=0,termination='initial',decision=None)
    h=context(history,actions,goal,0)
    decision=selector.select(tree,h,ledger,mode,integration_seed)
    node=tree.nodes[decision.prefix]

    def step(action,stage):
        nonlocal obs
        if obs.done or obs.clock>=150:raise RuntimeError('Post-terminal or over-budget work')
        old=obs.clock;obs=env.step(np.asarray(action).copy())
        if obs.clock!=old+1:raise ValueError('Absolute action clock')
        actions.append(np.asarray(action).copy());ledger.physical_steps+=1;ledger.observations+=1
        trace.append(dict(clock=obs.clock,stage=stage,action=np.asarray(action).tolist(),
                          latent=obs.latent.tolist(),success=bool(obs.success),
                          terminated=bool(obs.terminated),truncated=bool(obs.truncated)))
        if obs.clock%5==0:history.append(obs.latent.copy())

    for action in node.prefix:
        step(action,'prefix')
        if obs.done:break
    selected=None
    if not obs.done:
        selected=selector.after(decision,tree,h,obs.latent,ledger)
        for action in node.suffixes[selected]:
            step(action,'suffix')
            if obs.done:break
    while not obs.done and obs.clock<150:
        if obs.clock<15:raise RuntimeError('Premature baseline handoff')
        plan=finite(tail_planner(tuple(v.copy() for v in history),tuple(a.copy() for a in actions),
                                obs,150-obs.clock))
        if plan.shape!=(15,2):raise ValueError('Baseline tail must return fifteen primitives')
        for action in plan[:150-obs.clock]:
            step(action,'baseline-tail')
            if obs.done:break
    return dict(trace=trace,success=any(t['success'] for t in trace),steps=len(trace),
                termination='native' if obs.done else 'budget',decision=decision.__dict__,
                selected_suffix=selected,history_size=len(history),action_buffer_size=len(actions))


def real_runtime(*args,**kwargs):
    raise PermissionError('ACV0 preparation only: research runtime, source payloads and simulator execution remain disabled')
