"""Amended artificial collection/replay and strict RGB route firewall.

These are executable pure-array components, NOT native runtime adapters.
No source generation with native worlds can be enabled through this module.
"""
from dataclasses import dataclass
import copy
import hashlib
import json
import numpy as np
from wm_diag0.core import array_id, digest, frozen
from wm_diag0.branches import SourceHistory, run_branch

@dataclass(frozen=True)
class ArtifactRoute:
    task: str
    backbone: str
    checkpoint: str
    config: str
    normalization: str
    encoder: str
    source_revision: str
    layout: tuple
    history: int = 1
    grouping: int = 5
    horizon: int = 5

    @property
    def identity(self): return digest(self.__dict__)

def authenticate_route(route, expected):
    if route != expected or route.task not in ('pusht','reacher'):
        raise ValueError('Exact task/checkpoint/config/encoder/normalizer route')
    for value in (route.checkpoint,route.config,route.normalization,route.encoder):
        if len(value)!=64 or any(c not in '0123456789abcdef' for c in value): raise ValueError('Exact hash required')
    if len(route.source_revision)!=40 or any(c not in '0123456789abcdef' for c in route.source_revision):
        raise ValueError('Immutable implementation revision required')
    if route.history!=1 or route.grouping!=5 or route.horizon!=5:
        raise ValueError('Native evaluated T=1 action-clock contract; training history is not eval input')
    wanted = (192,) if route.backbone=='lewm' else (196,384) if route.backbone=='dinowm_noprop' else None
    if route.layout!=wanted: raise ValueError('Own native feature layout')
    return route.identity

@dataclass(frozen=True)
class SelectorInput:
    root: str
    task: str
    role: str
    history: np.ndarray
    goal: np.ndarray

    @property
    def scenario_id(self):
        return digest({'root':self.root,'task':self.task,'role':self.role,
                       'history':array_id(self.history),'goal':array_id(self.goal)})

def selector_input(raw):
    if set(raw)!= {'root','task','role','history','goal'}: raise ValueError('No state/collector future/label privileges')
    if raw['role']!='diagnostic': raise ValueError('Diagnostic selectors only')
    history, goal = frozen(raw['history']), frozen(raw['goal'])
    if history.dtype!=np.uint8 or goal.dtype!=np.uint8 or history.shape[0]!=1 or history.shape[1:]!=goal.shape:
        raise ValueError('One native RGB context and same-sized RGB goal')
    return SelectorInput(raw['root'],raw['task'],raw['role'],history,goal)

def check_root_roles(plan):
    rows = plan['roots']; ids=[r['root_id'] for r in rows]
    if len(ids)!=len(set(ids)): raise ValueError('Whole-root duplicate/cross-role leakage')
    for task in ('pusht','reacher'):
        for role,n in (('diagnostic',32),('readout_fit',16),('readout_validation',12)):
            if sum(r['task']==task and r['role']==role for r in rows)!=n: raise ValueError('Predeclared root count')
    if plan.get('protected_historical_inputs') or plan.get('replacement_attempts')!=0:
        raise ValueError('No historical source/replacement')

def collect_artificial(row, factory, collector, *, domain):
    if domain!='artificial': raise PermissionError('Native generation disabled')
    world = factory(row['seeds']['native_reset'])
    observations=[]; actions=[]; states=[]; events=[]
    try:
        obs,success,terminal,truncated=world.reset()
        observations.append(frozen(obs));states.append(digest(world.complete_state()))
        # Full opaque complete-origin fixture; never a qpos/qvel-only restoration.
        origin=copy.deepcopy(world.complete_state())
        for clock in range(row['collection_actions_cap']):
            if success or terminal or truncated: break
            action=frozen(collector(obs,clock,row['seeds']['collector']))
            obs,success,terminal,truncated=world.step(action)
            actions.append(action);observations.append(frozen(obs));states.append(digest(world.complete_state()))
            events.append((bool(success),bool(terminal),bool(truncated)))
        available=len(actions)>=row['goal_action_index']
        return {'root':row['root_id'],'role':row['role'],'origin':origin,'actions':tuple(actions),
                'observations':tuple(observations),'observation_ids':tuple(array_id(o) for o in observations),
                'complete_state_ids':tuple(states),'events':tuple(events),'available':available,
                'source_index':row['source_action_index'],'goal_index':row['goal_action_index'],
                'reason':'complete' if available else 'unavailable_window_no_replacement',
                'world_model_inputs_generated':False}
    finally: world.close()

class Ownership:
    """Hold strong references: a previously used world can never become a fresh branch."""
    def __init__(self): self.worlds=[]
    def claim(self, world):
        if any(world is used for used in self.worlds): raise ValueError('World reused between branches')
        self.worlds.append(world)

def replay_artificial(record, factory, ownership, *, domain):
    if domain!='artificial': raise PermissionError('Native restoration disabled')
    if not record['available']: raise ValueError('Missing source/goal; no silent replacement')
    world=factory(copy.deepcopy(record['origin']));ownership.claim(world)
    try:
        obs,success,terminal,truncated=world.reset()
        for i in range(record['source_index']+1):
            if array_id(obs)!=record['observation_ids'][i] or digest(world.complete_state())!=record['complete_state_ids'][i]:
                raise ValueError('Full root/replay observation AND hidden-state mismatch')
            if i==record['source_index']: break
            if success or terminal or truncated: raise ValueError('Replay crosses collection stop')
            obs,success,terminal,truncated=world.step(record['actions'][i])
        before=digest(world.dynamic_state());before_image=array_id(obs)
        world.install_goal(record['observations'][record['goal_index']])
        if digest(world.dynamic_state())!=before: raise ValueError('Goal installation advances/modifies physics')
        if array_id(world.current()[0])!=before_image: raise ValueError('Goal installation changes source pixels')
        # Goal installed by declared metadata-only setter; render/evaluate but do not step.
        return world
    except Exception:
        world.close(); raise

def shared_scenario(record, task):
    s,g=record['source_index'],record['goal_index']
    if not record['available']: raise ValueError('Source/goal unavailable')
    return selector_input({'root':record['root'],'task':task,'role':record['role'],
                           'history':np.stack([record['observations'][s]]), 'goal':record['observations'][g]})

def decoded_actions(z, mean, std):
    z,mean,std=np.asarray(z),np.asarray(mean),np.asarray(std)
    if z.shape[-1]!=10 or mean.shape!=(2,) or std.shape!=(2,) or not np.all(std>0): raise ValueError('Native 5x2 grouping')
    result=z.reshape(*z.shape[:-2],z.shape[-2]*5,2)*std+mean
    if not np.isfinite(result).all(): raise ValueError('Action bytes finite')
    return frozen(result)  # no clipping/rescaling convention silently inserted

def sampling_clock(route, actions):
    if route.history!=1 or np.asarray(actions).shape!=(25,2): raise ValueError('Forecast/physical duration mismatch')
    return (5,10,15,20,25)

def source_reference(record):
    n=record['source_index']
    return SourceHistory(record['root'],digest(record['origin']),
                         frozen(np.stack(record['actions'][:n])),record['observation_ids'][:n+1],0)

def run_new_branch(record,factory,ownership,candidate,tail_factory,draw_id,*,domain):
    if domain!='artificial': raise PermissionError('Native branch disabled')
    world=replay_artificial(record,factory,ownership,domain=domain)
    source=source_reference(record)
    actions=[];observations=[];flags=[];terms=[];truncs=[]
    tail=tail_factory(draw_id)  # separately owned state and random stream
    elapsed=prefix=0
    try:
        obs,success,terminal,truncated=world.current()
        observations.append(frozen(obs));flags.append(bool(success));terms.append(bool(terminal));truncs.append(bool(truncated))
        while not(success or terminal or truncated) and elapsed<50:
            if elapsed<len(candidate.actions):
                action=candidate.actions[elapsed];prefix+=1
            else:
                action=tail(frozen(obs),elapsed,50-elapsed)
            obs,success,terminal,truncated=world.step(action)
            actions.append(frozen(action));observations.append(frozen(obs));flags.append(bool(success))
            terms.append(bool(terminal));truncs.append(bool(truncated));elapsed+=1
        a=frozen(np.stack(actions) if actions else np.empty((0,*candidate.actions.shape[1:]),dtype=candidate.actions.dtype))
        o=frozen(np.stack(observations))
        return {'parent':source.parent,'construction':source.construction_id,'candidate_id':candidate.identity,
                'draw_id':draw_id,'replay_id':array_id(source.replay_actions),'replay_steps':len(source.replay_actions),
                'source_elapsed':0,'actions':a,'observations':o,'endpoint_flags':tuple(flags),
                'terminal_flags':tuple(terms),'truncation_flags':tuple(truncs),'elapsed':elapsed,
                'prefix_steps':prefix,'prefix_id':array_id(o[:prefix+1]),'tail_id':array_id(a[prefix:]),
                'success':bool(success),'reason':'success' if success else 'truncated' if truncated else
                'terminal_failure' if terminal else 'budget_failure','domain':domain}
    finally: world.close()

class NativeCampaign:
    def __init__(self,*args,**kwargs):
        raise PermissionError('A2 native collection, loading, fitting, forecasting and scheduling NOT IMPLEMENTED/AUTHORIZED')
