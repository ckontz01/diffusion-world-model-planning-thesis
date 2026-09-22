"""Executable array/vector adapter; research entry point remains hard-disabled.

FrozenPort is a dependency-injected, already-frozen rollout, NOT a loader.
No torch, physics, image, checkpoint or reference payload import occurs here.
The baseline uses the SAME unmodified cem() as the initial tree solve.
"""
import numpy as np
from tree import FrozenPort,cem


class BaselinePlanner:
    def __init__(self,goal,rollout,ledger,source_seed=94041,population=300,elites=30,rounds=30):
        self.goal=np.asarray(goal).copy();self.rollout=rollout;self.ledger=ledger
        self.seed=source_seed;self.settings=dict(population=population,elites=elites,rounds=rounds)
        self.calls=[]

    def solve(self,latent,clock):
        if clock<0 or clock>=150:raise ValueError('Absolute budget')
        self.calls.append(clock)
        port=FrozenPort(latent,self.goal,self.rollout,self.ledger)
        # Common absolute-clock stream across policies, no outcome/arm identifier.
        stream=list(np.atleast_1d(self.seed).astype(np.uint32))+[clock]
        return cem(port,np.random.default_rng(np.random.SeedSequence(stream)),**self.settings)

    def __call__(self,history,actions,obs,remaining):
        if remaining!=150-obs.clock or len(actions)!=obs.clock:raise ValueError('Budget reset')
        return self.solve(obs.latent,obs.clock).baseline


def execute_reference(env,planner,ledger,early_replan=False):
    """Strong vanilla comparator: full fresh search after five, then every 15.

    Early replanning discards the initial suffix and executes its own fresh bank.
    Every solve uses the planner's unchanged N/K/J settings, including at 140.
    Only the remaining 10 primitives of the final 15-action plan are executed.
    Ordinary vanilla replans at 0,15,...135. Neither has a matched-tree claim.
    """
    obs=env.initial();ledger.observations+=1;trace=[];history=[obs.latent.copy()];actions=[]
    if obs.clock!=0:raise ValueError('Fresh episode required')
    first=True
    while not obs.done and obs.clock<150:
        plan=planner(tuple(history),tuple(actions),obs,150-obs.clock)
        count=5 if first and early_replan else 15;first=False
        for action in plan[:min(count,150-obs.clock)]:
            previous=obs.clock;obs=env.step(action.copy())
            if obs.clock!=previous+1:raise ValueError('Absolute clock')
            actions.append(action.copy());ledger.physical_steps+=1;ledger.observations+=1
            trace.append(dict(clock=obs.clock,stage='early-replan' if early_replan else 'vanilla',
                              action=action.tolist(),latent=obs.latent.tolist(),success=bool(obs.success),
                              terminated=bool(obs.terminated),truncated=bool(obs.truncated)))
            if obs.clock%5==0:history.append(obs.latent.copy())
            if obs.done:break
    return dict(trace=trace,steps=len(trace),success=any(r['success'] for r in trace),
                planner_clocks=list(planner.calls),early_replan=early_replan)


def launch_real_pilot(*args,**kwargs):
    raise PermissionError('Review required: no research model loading, physics, collection or launch is enabled')
