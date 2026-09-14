"""Opt-in bank observation/selection wrapper; frozen solve still runs unchanged.

No environment construction, model loading, I/O or launch capabilities. The
caller binds h/absolute time at the existing fresh driver's decision boundary.
"""
import numpy as np
import torch
from candidate_value_learning import features, clock, require


def capture(solver, original, args, kwargs, *, h, t, selector=None):
    time_features=clock(h,t)
    require(kwargs['delta_value']==h-t%h and kwargs['tau_value']==15, 'Schedule')
    events={k:[] for k in ('_propose','_rollout','_encode','_predict_intermediate_state')}
    old={k:getattr(solver,k) for k in events}
    def hook(name):
        def wrapped(*a,**kw):
            out=old[name](*a,**kw)
            events[name].append((kw,out))
            return out
        return wrapped
    for k in events:setattr(solver,k,hook(k))
    try:
        result=original(*args,**kwargs)
    finally:
        for k,v in old.items():setattr(solver,k,v)
    second=kwargs['delta_value']>=30
    require([len(v) for v in events.values()]==([2,2,1,1] if second else [1,1,1,0]),
            'Batch-one frozen proposal workload')
    first_kw,first=events['_propose'][0]
    current,goal=events['_encode'][0][1]
    terminal=events['_rollout'][0][1]
    require(first[1].shape==(1,64,25,2) and terminal.shape==(1,64,192), 'Bank shape')
    cpu=lambda x:x.detach().cpu().numpy().copy()
    proposal=solver.proposal_generator.get_state().clone()
    gmm=solver.gmm_generator.get_state().clone()
    global_rng=torch.get_rng_state().clone()
    cuda_rng=torch.cuda.get_rng_state_all() if solver.device.type=='cuda' else []
    with torch.inference_mode():
        immediate=(terminal-goal[:,None]).square().sum(-1)[0]
        if second:
            last=events['_rollout'][1][1].reshape(1,64,8,192)
            costs=(last-goal[:,None,None]).square().sum(-1)
            continuation=torch.topk(costs,2,dim=-1,largest=False,sorted=False).values.mean(-1)[0]
        else:
            continuation=immediate
        require(bool(torch.isfinite(immediate).all()) and bool(torch.isfinite(continuation).all()),
                'Finite frozen costs')
        baseline=int(continuation.argmin())
        plans=first[1][:,:,:15].reshape(64,3,10).cpu()
        require(torch.equal(result['actions'],plans[baseline:baseline+1]), 'Frozen selection identity')
        def repeat(x):return cpu(x.expand(64,-1))
        x=features(dict(current=repeat(first_kw['current']),goal=repeat(first_kw['goal']),
            predicted=cpu((terminal[0]-solver.statistics.latent_mean)/solver.statistics.latent_std),
            state=repeat(first_kw['state']),actions=cpu(first[1][0,:,:15]),
            time=np.tile(time_features,(64,1))))
        bank=dict(x=x,immediate=cpu(immediate),continuation=cpu(continuation),
                  planner_actions=cpu(first[1][0,:,:15]),raw_actions=cpu(first[0][0,:,:15]),
                  continuation_index=baseline,immediate_index=int(immediate.argmin()))
        index=baseline if selector is None else selector(bank)
        require(isinstance(index,(int,np.integer)) and 0<=index<64,'Selector index')
        output={**result,'actions':plans[index:index+1].clone()}
    current_cuda=torch.cuda.get_rng_state_all() if cuda_rng else []
    require(torch.equal(proposal,solver.proposal_generator.get_state()) and
            torch.equal(gmm,solver.gmm_generator.get_state()) and
            torch.equal(global_rng,torch.get_rng_state()) and
            len(cuda_rng)==len(current_cuda) and
            all(torch.equal(a,b) for a,b in zip(cuda_rng,current_cuda)), 'Selection changed RNG')
    return output,bank
