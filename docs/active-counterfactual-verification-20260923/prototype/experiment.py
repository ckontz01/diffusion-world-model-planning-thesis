#!/usr/bin/env python3
"""Two-stage artificial action-verification experiment; NO robot/LeWM use.

Every policy spends exactly one prefix action and one suffix action. A prefix
changes both the observation and the success law; no free/resettable sensing.
The learned model is a table of joint P(observation, terminal success), estimated
from branched artificial training episodes. Hidden modes are NOT supplied to it.
This is a mechanism test; the contingent decision equation is standard Bayesian
experimental design, not a new theorem or a reproduction of any cited paper.
"""
from __future__ import annotations
import argparse, dataclasses, hashlib, json, math, time
from pathlib import Path
import numpy as np

@dataclasses.dataclass(frozen=True)
class Case:
    name: str
    theta_prior: float
    signal_accuracy: float
    probe_survival: float
    safe_success: float
    nuisance_accuracy: float = .98
    effect: float = .35
    shift_flip: bool = False
    theta_changes: float = 0.

CASES = (
    Case('informative_contact', .50,.90,.97,.58),
    Case('mostly_known_context',.95,.90,.97,.58),
    Case('uninformative_prefix',.50,.50,.97,.58),
    Case('expensive_prefix',.50,.90,.65,.58),
    Case('no_decision_relevant_uncertainty',.50,.90,.97,.62,effect=0.),
    Case('unstable_contact_mode',.50,.90,.97,.58,theta_changes=.45),
    Case('unannounced_sensor_reversal',.50,.90,.97,.58,shift_flip=True),
)
METHODS = ('commit','passive_feedback','fixed_relevant_probe','oracle_entropy_probe',
           'active_counterfactual_feedback','active_without_transfer','oracle_contingent')

def canonical(x): return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def tables(case: Case, test: bool=False):
    """Return exact joint J[p,o,a,y], P[o|p], and prefix informativeness.
    Prefix p=0 ordinary approach, p=1 contact test, p=2 highly informative nuisance.
    Suffix a=0 robust alternative, a=1 /2 opposite control directions.
    Two hidden mode bits. They describe episode variability, not learner inputs.
    """
    J=np.zeros((3,2,3,2))
    # All prefixes consume a control slot. Successful survival of a prefix is
    # folded into terminal task success; p=1 is not a cost-free oracle query.
    surv=np.array([1.,case.probe_survival,.98])
    for theta in (0,1):
      for nuisance in (0,1):
        ph=(case.theta_prior if theta else 1-case.theta_prior)*.5
        for theta_final in (0,1):
          pf=(1-case.theta_changes) if theta_final==theta else case.theta_changes
          if not pf: continue
          base=np.array([case.safe_success,
                         .5+case.effect*(2*theta_final-1),
                         .5-case.effect*(2*theta_final-1)])
          for p in range(3):
            if p==0: probs=np.array([.5,.5])
            else:
              bit=theta if p==1 else nuisance
              if p==1 and test and case.shift_flip: bit=1-bit
              accuracy=case.signal_accuracy if p==1 else case.nuisance_accuracy
              probs=np.array([accuracy if bit==0 else 1-accuracy,
                              accuracy if bit==1 else 1-accuracy])
            for o in range(2):
              py=surv[p]*base
              J[p,o,:,1]+=ph*pf*probs[o]*py
              J[p,o,:,0]+=ph*pf*probs[o]*(1-py)
    obs=J.sum(-1)[:,:,0]
    assert np.allclose(J.sum((1,3)),1)
    # Information gain about the hidden state (theta,nuisance), from its full
    # correct observation model, is GIVEN to the entropy comparator. Thus it
    # is a deliberately strong oracle-information heuristic, not a fake paper.
    def hb(p):
      return -sum(v*math.log(v) for v in (p,1-p) if v>0)
    pplus=case.theta_prior*case.signal_accuracy+(1-case.theta_prior)*(1-case.signal_accuracy)
    info=np.array([0,hb(pplus)-hb(case.signal_accuracy),math.log(2)-hb(case.nuisance_accuracy)])
    return J, obs, info

def draw_training(case, n, rng):
    """Complete branches on artificial episodes. One source shared across actions.
    Records contain ONLY prefix observations and binary branch outcomes, not
    hidden modes/true probabilities. Coupled uniforms reduce paired-label noise.
    """
    theta=rng.random(n)<case.theta_prior
    nuisance=rng.random(n)<.5
    final_theta=np.logical_xor(theta,rng.random(n)<case.theta_changes)
    observation=np.empty((n,3),dtype=np.int64)
    observation[:,0]=rng.integers(0,2,n)
    observation[:,1]=np.logical_xor(theta,rng.random(n)>case.signal_accuracy)
    observation[:,2]=np.logical_xor(nuisance,rng.random(n)>case.nuisance_accuracy)
    base=np.column_stack([np.full(n,case.safe_success),.5+case.effect*(2*final_theta.astype(float)-1),
                          .5-case.effect*(2*final_theta.astype(float)-1)])
    survival=np.array([1,case.probe_survival,.98])
    # Shared outcome uniform across prefixes/actions is explicitly the chosen
    # artificial counterfactual coupling, not an independence assertion.
    u=rng.random((n,1,1))
    outcomes=(u<survival[None,:,None]*base[:,None,:]).astype(np.int64)
    return observation,outcomes

def fit_joint(observation,outcomes):
    n=observation.shape[0]
    joint=np.empty((3,2,3,2))
    for p in range(3):
      for o in range(2):
        m=observation[:,p]==o
        for a in range(3):
          s=int(outcomes[m,p,a].sum()); count=int(m.sum())
          # Symmetric pseudocount1 for each (observation,outcome) category.
          joint[p,o,a,1]=(s+1)/(n+4)
          joint[p,o,a,0]=(count-s+1)/(n+4)
    return joint

def choose(joint,info,method):
    mean=joint[:,:,:,1].sum(1)
    op=joint.sum(-1)[:,:,0]
    posterior=joint[:,:,:,1]/op[:,:,None]
    flat=int(np.argmax(mean)); p0,a0=np.unravel_index(flat,mean.shape)
    best_after=np.argmax(posterior,axis=-1)
    value=np.max(joint[:,:,:,1],axis=-1).sum(-1)
    pa=int(np.argmax(value))
    if method=='commit': return int(p0),np.full(2,a0,dtype=int)
    if method=='passive_feedback': return int(p0),best_after[p0]
    if method=='fixed_relevant_probe': return 1,best_after[1]
    if method=='oracle_entropy_probe':
      pi=int(np.argmax(info)); return pi,best_after[pi]
    if method in ('active_counterfactual_feedback','oracle_contingent'): return pa,best_after[pa]
    if method=='active_without_transfer': return pa,np.full(2,int(np.argmax(mean[pa])),dtype=int)
    raise ValueError(method)

def evaluate(policy,joint):
    p,aa=policy
    return float(sum(joint[p,o,aa[o],1] for o in range(2)))

def run(out:Path, ntrain=1024, seeds=30):
    out.mkdir(parents=True,exist_ok=False)
    config=dict(type='artificial-two-stage-only',cases=[dataclasses.asdict(c) for c in CASES],
                methods=METHODS,ntrain=ntrain,seeds=list(range(24000,24000+seeds)),
                training_law='full-branch paired binary labels; hidden state absent',
                evaluation='exact expectation under known artificial law, not estimated robot performance',
                no_new_parameter_search=True)
    (out/'CONFIG.json').write_bytes(canonical(config))
    started=time.perf_counter(); rows=[]
    for case in CASES:
      truth,_,info=tables(case,test=True)
      known_train,_,_=tables(case,test=False)
      for seed in config['seeds']:
        seedseq=np.random.SeedSequence([seed,int(hashlib.sha256(case.name.encode()).hexdigest()[:8],16)])
        rng=np.random.default_rng(seedseq)
        obs,ys=draw_training(case,ntrain,rng); model=fit_joint(obs,ys)
        digest=hashlib.sha256(obs.tobytes()+ys.tobytes()).hexdigest()
        for method in METHODS:
          # Oracle knows the TEST law, including the reversal. Learned approaches
          # know only training data. All exact expectations use same test law.
          inp=truth if method=='oracle_contingent' else model
          pol=choose(inp,info,method)
          rows.append(dict(case=case.name,seed=seed,method=method,expected_success=evaluate(pol,truth),
                           prefix=int(pol[0]),suffix_for_observations=pol[1].tolist(),training_digest=digest))
    summary=[]
    for case in CASES:
      for method in METHODS:
        rr=[r for r in rows if r['case']==case.name and r['method']==method]
        vv=np.array([r['expected_success'] for r in rr]);counts=np.bincount([r['prefix'] for r in rr],minlength=3)
        summary.append(dict(case=case.name,method=method,mean=float(vv.mean()),min=float(vv.min()),max=float(vv.max()),
                            between_fit_sd=float(vv.std(ddof=1)),prefix_counts=counts.tolist()))
    result=dict(config_sha256=hashlib.sha256(canonical(config)).hexdigest(),summary=summary,rows=rows,
                seconds=time.perf_counter()-started,fit_count=len(CASES)*seeds,
                training_source_draws=len(CASES)*seeds*ntrain,
                artificial_branch_labels=len(CASES)*seeds*ntrain*3*3,
                statement='Constructed mechanism examples. No Le-WM, ACID, CheckVLA or other robotics method was run.')
    (out/'RESULTS.json').write_bytes(canonical(result))
    lines=['| Case | Static | Passive | Fixed probe | Information-gain probe | Active feedback | No transfer | Oracle |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for case in CASES:
        vals=[next(r['mean'] for r in summary if r['case']==case.name and r['method']==m) for m in METHODS]
        lines.append('| '+case.name+' | '+' | '.join(f'{v*100:.2f}' for v in vals)+' |')
    (out/'TABLE.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines));print(json.dumps({k:v for k,v in result.items() if k not in ('summary','rows')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--ntrain',type=int,default=1024)
    p.add_argument('--seeds',type=int,default=30);a=p.parse_args();run(a.out,a.ntrain,a.seeds)
