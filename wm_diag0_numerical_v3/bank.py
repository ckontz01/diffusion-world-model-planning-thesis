"""Authenticate and independently reconstruct the failed fixed bank; never CEM."""
import json
import numpy as np
from pathlib import Path
from wm_diag0.core import array_id, capture_bank
from wm_diag0_native_v3.store import load_array
from .common import identity

def retained(c):
    p=Path(c['recovery']['old_run'])/'tasks/technical-1/output'
    if {x.name for x in p.iterdir()}!=set(c['recovery']['partial']):raise ValueError('unchanged failed partial members')
    for n,r in c['recovery']['partial'].items():
        if identity(p/n)!=r:raise ValueError('failed partial identity')
    actions=load_array(p/'actions.npy',(16,25,2),['<f4'])
    trace=load_array(p/'trace.npy',(9000,25,2),['<f4'])
    costs=load_array(p/'trace-costs.npy',(9000,),['<f4'])
    elites=load_array(p/'native-elites.npy',(30,5,10),['<f4'])
    mean=load_array(p/'native-mean.npy',(5,10),['<f4'])
    ix=load_array(p/'native-indices.npy',(30,),['<i8'])
    if np.any(ix<0) or np.any(ix>=300) or len(set(ix.tolist()))!=30:raise ValueError('elite slot bounds')
    stats=json.loads((Path(c['prior_source'])/'configs/pusht/swm_h5_norm_stats.json').read_text())
    def decode(x):
        a=x.reshape(*x.shape[:-2],25,2).copy();a*=np.array(stats['action_std']);a+=np.array(stats['action_mean']);return a
    if not np.array_equal(decode(mean),actions[0]) or not np.array_equal(decode(elites),trace[8700+ix]):raise ValueError('native return/physical action binding')
    if not np.array_equal(np.sort(costs[8700+ix]),np.sort(costs[8700:])[:30]):raise ValueError('retained native top30')
    import torch
    if not np.array_equal(torch.from_numpy(elites)[None].cuda().mean(1)[0].cpu().numpy(),mean):raise ValueError('native elite mean bits')
    bank=capture_bank(actions[0],trace,costs)
    if len(bank.candidates)!=16 or [x.identity for x in bank.candidates]!=[array_id(x) for x in actions]:raise ValueError('independent fixed bank reconstruction')
    return bank,actions
