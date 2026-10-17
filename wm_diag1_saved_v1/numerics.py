"""Fixed terminal algebra and exactly two privileged pure-array selectors."""
from types import SimpleNamespace
import hashlib,json
import numpy as np
from wm_diag0.core import native_terminal_score,array_id

def scalar(x):
    value=float(x)
    if not np.isfinite(value):raise ValueError('nonfinite fixed analysis arithmetic')
    return value
def close_identity(left,right,*scales):
    left=np.asarray(left,dtype=np.float64);right=np.asarray(right,dtype=np.float64)
    scale=np.maximum(1,np.maximum(np.abs(left),np.abs(right)))
    for value in scales:scale=np.maximum(scale,np.abs(value))
    residual=left-right
    if not np.isfinite(residual).all() or np.any(np.abs(residual)>1e-10*scale):raise ValueError('float64 algebra identity failed')
    return residual
def s0(terminal,goal,score_id):
    contract=SimpleNamespace(feature_shape=tuple(goal.shape),native_score_id=score_id)
    features=SimpleNamespace(values=terminal[:,None,...],contract=contract)
    scores=native_terminal_score(features,goal)
    if scores.shape!=(len(terminal),) or not np.isfinite(scores).all():raise ValueError('unchanged pure-array S0 finite scores')
    return scores
def ranks(costs):
    if np.asarray(costs).ndim!=1 or not np.isfinite(costs).all():raise ValueError('finite same-bank ranks')
    order=sorted(range(len(costs)),key=lambda i:(float(costs[i]),i));result=[0]*len(order)
    for rank,index in enumerate(order,1):result[index]=rank
    return result

def decompose(predicted,realized,goal,saved_costs,choices,score_id):
    p0=np.asarray(predicted);r0=np.asarray(realized);g0=np.asarray(goal);n=len(p0)
    if p0.shape!=r0.shape or p0.shape[1:]!=g0.shape or p0.dtype!=r0.dtype or p0.dtype!=g0.dtype or p0.dtype.hasobject or not 1<=n<=16:raise ValueError('same native terminal shape/dtype/ragged bank')
    if score_id not in ('terminal_sum','terminal_mse') or not all(np.isfinite(x).all() for x in (p0,r0,g0)):raise ValueError('authenticated terminal score and finite numeric data')
    costs=np.asarray(saved_costs)
    if costs.shape!=(4,n) or not np.isfinite(costs).all() or len(choices)!=4 or [int(np.argmin(x)) for x in costs]!=list(choices):raise ValueError('authoritative saved costs/lowest-index selections')
    p=p0.astype(np.float64).reshape(n,-1);r=r0.astype(np.float64).reshape(n,-1);g=g0.astype(np.float64).reshape(-1)
    dimension=len(g);gamma=1. if score_id=='terminal_sum' else 1./dimension
    e=p-r;b=e.mean(axis=0);u=e-b
    cp=gamma*np.sum((p-g)**2,axis=1);cr=gamma*np.sum((r-g)**2,axis=1)
    direction=2*gamma*np.sum((r-g)*e,axis=1);squared=gamma*np.sum(e*e,axis=1)
    residual=close_identity(cp-cr,direction+squared,cp,cr,direction,squared)
    energy=scalar(np.mean(np.sum(e*e,axis=1)));common=scalar(np.sum(b*b));specific=scalar(np.mean(np.sum(u*u,axis=1)))
    energy_residual=scalar(close_identity(energy,common+specific,energy,common,specific))
    # Exactly one cast back per correction, then the unchanged stored-dtype S0.
    a=(p-b).reshape(p0.shape).astype(p0.dtype);z=(r+b).reshape(r0.shape).astype(r0.dtype)
    sa=s0(a,g0,score_id);sb=s0(z,g0,score_id);ia=int(np.argmin(sa));ib=int(np.argmin(sb))
    i,j=int(choices[0]),int(choices[2]);rp=ranks(costs[0]);rr=ranks(costs[2])
    delta_saved=float((costs[0,j]-costs[0,i])-(costs[2,j]-costs[2,i]))
    delta64=float((cp[j]-cp[i])-(cr[j]-cr[i]));dirpair=float(direction[j]-direction[i]);sqpair=float(squared[j]-squared[i])
    pair_residual=scalar(close_identity(delta64,dirpair+sqpair,cp[i],cp[j],cr[i],cr[j],dirpair,sqpair))
    rows=[]
    for k in range(n):
        rows.append({'index':k,'saved_predicted_S0':float(costs[0,k]),'saved_realized_S0':float(costs[2,k]),'predicted_rank':rp[k],'realized_rank':rr[k],
            'float64_predicted_S0':float(cp[k]),'float64_realized_S0':float(cr[k]),'signed_goal_direction_term':float(direction[k]),
            'squared_error_term':float(squared[k]),'identity_residual':float(residual[k]),
            'saved_minus_float64_predicted':float(costs[0,k]-cp[k]),'saved_minus_float64_realized':float(costs[2,k]-cr[k]),
            'candidate_specific_error_energy':float(np.sum(u[k]*u[k])),'A_S0':float(sa[k]),'B_S0':float(sb[k])})
    return {'P0_index':i,'O0_index':j,'action_choice_changed':i!=j,'A_index':ia,'B_index':ib,'A_scores':sa.astype(np.float64).tolist(),'B_scores':sb.astype(np.float64).tolist(),
        'A_corrected_array_id':array_id(a),'B_corrected_array_id':array_id(z),'native_dtype':p0.dtype.str,'native_feature_shape':list(g0.shape),'dimension':dimension,'gamma':gamma,
        'energies':{'total_mean_L2_squared':energy,'common_L2_squared':common,'specific_mean_L2_squared':specific,'coordinate_MSE':energy/dimension,
            'common_per_coordinate':common/dimension,'specific_per_coordinate':specific/dimension,'common_energy_fraction_not_failure_attribution':common/energy if energy else None,'identity_residual':energy_residual},
        'common_vector_id':array_id(b),'pair_ordering':{'saved_relative_ordering_error':delta_saved,'float64_relative_ordering_error':delta64,
            'signed_goal_direction_difference':dirpair,'squared_error_difference':sqpair,'identity_residual':pair_residual,'saved_minus_float64_relative_error':delta_saved-delta64},
        'max_absolute_candidate_identity_residual':float(np.max(np.abs(residual))),'candidates':rows}

def clock_summary(record,prefix=False):
    elapsed=record['actions'] if prefix else record['elapsed'];events=record['events'];maximum=25 if prefix else 50
    if type(elapsed) is not int or not 0<=elapsed<=maximum or len(events)!=elapsed+1:raise ValueError('saved actual action-clock schema')
    for index,event in enumerate(events):
        if event['clock']!=index or any(type(event[k]) is not bool for k in ('success','terminated','truncated')):raise ValueError('saved clock/flag typing')
        if index<elapsed and any(event[k] for k in ('success','terminated','truncated')):raise ValueError('saved post-stop event')
    last=events[-1];success=last['success'];first=next((i for i,e in enumerate(events) if e['success']),None)
    result={'actions':elapsed,'success':success,'success_clock':first,'initial_success':events[0]['success'],'terminated':last['terminated'],'truncated':last['truncated']}
    if prefix:
        if record['sampling']!=[5,10,15,20,25] or type(record['absorbed_after_stop']) is not bool:raise ValueError('saved prefix sampling/absorption')
        stopped=any(last[k] for k in ('success','terminated','truncated'))
        if record['absorbed_after_stop']!=stopped or elapsed<25 and not stopped:raise ValueError('actual prefix stop/absorption consistency')
        result.update(absorbed_after_stop=record['absorbed_after_stop'],absorbed_sampling_positions=[t for t in record['sampling'] if t>elapsed] if stopped else [],
            terminal_feature_post_stop_absorbed=bool(stopped and elapsed<25),stopped_exactly_at_horizon=bool(stopped and elapsed==25))
    else:
        reason='success' if success else 'truncated' if last['truncated'] else 'terminal_failure' if last['terminated'] else 'budget_failure'
        if record['reason']!=reason or record['tail_replans']!=int(elapsed>25) or record['replay_steps']!=20:raise ValueError('saved full-budget branch/tail record')
        active=elapsed>=25 and not any(events[25][k] for k in ('success','terminated','truncated'))
        if elapsed>25 and not active:raise ValueError('tail requires active actual state at25')
        result.update(reason=reason,active_at25=active,phase='prefix_success' if success and first<=25 else 'tail_success' if success else 'failure')
    return result

def paired_bootstraps(parent_rows):
    # One fixed task-paired resampling scheme; no independently resampled backbones.
    rng=np.random.default_rng(20261017);matrices={t:rng.integers(0,32,size=(10000,32)) for t in ('pusht','reacher')};result={}
    for task in ('pusht','reacher'):
        ids=None
        for backbone in ('lewm','dinowm_noprop'):
            rows=sorted([r for r in parent_rows if r['task']==task and r['backbone']==backbone],key=lambda r:r['root_index'])
            if len(rows)!=32 or [r['root_index'] for r in rows]!=list(range(32)):raise ValueError('complete fixed source-paired aggregation')
            current=[r['root_id'] for r in rows]
            if ids is not None and ids!=current:raise ValueError('same task physical sources paired across backbones')
            ids=current;group={}
            for selector in ('A','B'):
                values=np.array([r['outcomes'][selector]['mean']-r['outcomes']['P0']['mean'] for r in rows],dtype=np.float64)
                boot=values[matrices[task]].mean(axis=1)
                group[selector]={'difference_vs_P0':float(values.mean()),'ci95_percentile':np.quantile(boot,[.025,.975],method='linear').tolist(),
                    'gains':int(np.sum(values>0)),'losses':int(np.sum(values<0)),'ties':int(np.sum(values==0)),
                    'mean_success':float(np.mean([r['outcomes'][selector]['mean'] for r in rows])),
                    'choice_agreement_with_O0':sum(r['decomposition'][selector+'_index']==r['decomposition']['O0_index'] for r in rows)/32}
            result[task+'|'+backbone]=group
    return result,{t:array_id(m) for t,m in matrices.items()}
