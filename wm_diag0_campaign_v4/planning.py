"""Reviewed CEM plus exact physical trace; branch-owned generators and buffers."""
import hashlib
import numpy as np
import torch
from types import SimpleNamespace
from wm_diag0.core import capture_bank, array_id

def substream(base,backbone): return int.from_bytes(hashlib.sha256((str(base)+'|'+backbone).encode()).digest()[:4],'big')&0x7fffffff

class Trace:
    output_key='a2_trace'
    def __init__(self,adapter): self.adapter=adapter; self.history={}; self.actions=[]; self.costs=[]; self.proof=None
    def reset(self): self.actions=[]; self.costs=[]
    def start_batch(self): pass
    def end_solve(self): pass
    def __call__(self,**row):
        self.actions.append(self.adapter.decode(row['candidates'][0].detach().cpu().numpy()))
        self.costs.append(row['costs'][0].detach().float().cpu().numpy())
        if row['step']==29:
            self.proof={'elites':row['topk_candidates'][0].detach().cpu().numpy(),'mean':row['mean'][0].detach().cpu().numpy(),'indices':row['topk_inds'][0].detach().cpu().numpy()}

def solve(adapter,history,goal,seed,capture=False):
    import gymnasium as gym
    from stable_worldmodel.policy import PlanConfig
    from stable_worldmodel.solver.cem import CEMSolver
    recorder=Trace(adapter)
    solver=CEMSolver(adapter,batch_size=1,num_samples=300,var_scale=1,n_steps=30,topk=30,
                     device=str(adapter.device),seed=seed,callbacks=[recorder] if capture else [])
    solver.configure(action_space=gym.spaces.Box(-1.,1.,(1,2),dtype=np.float32),n_envs=1,
                     config=PlanConfig(horizon=5,receding_horizon=5,history_len=1,action_block=5,warm_start=True))
    info=adapter.public_info(history,goal)
    # The reviewed policy's warm-start suffix after a full five-group chunk is
    # empty. A fresh tail solve therefore zero-pads identically. No previous
    # candidate plan, oracle world or collector continuation enters this solve.
    result=solver(info,init_action=None)
    native=adapter.decode(result['actions'][0].numpy())
    if not capture: return native
    trace=np.concatenate(recorder.actions); costs=np.concatenate(recorder.costs)
    if trace.shape!=(9000,25,2) or costs.shape!=(9000,): raise ValueError('exact CEM trace')
    return capture_bank(native,trace,costs),trace,costs,recorder.proof
