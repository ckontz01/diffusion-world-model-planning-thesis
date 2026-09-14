"""Independent saved-array checks and fixed reference-cluster aggregation.

No torch/physics imports. Run only after ALL64 processes are terminal/successful.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import single_anchor_ranking as spec
from single_anchor_ranking_runner import LIFECYCLE, exact, match_saved
from verify_diffusion_branch import seal, independent_decode
from verify_diffusion_extension import verify_source
from diffusion_bottleneck import require, require_sha, sha256


def check_row(v,row,historical,trace,saved):
    h,a,arm=row['horizon'],row['anchor'],row['arm']
    metrics=spec.physical(v('states'),v('flags'),v('goal_state'),2*h-a)
    require(row['metrics']==metrics and row['interventions']==1,'Reported endpoint/intervention')
    require(v('actions').shape==(metrics['delivered'],2) and v('actions').dtype==np.float32 and
            np.isfinite(v('actions')).all() and (np.abs(v('actions'))<=1).all(),'Action shape/range')
    exact(v('prefix_actions'),trace['actions'][:a]);exact(v('goal_state'),trace['goal_state'])
    np.testing.assert_allclose(v('anchor_state'),trace['states'][a],rtol=0,atol=spec.ATOL)
    require(v('first_planner').shape==(1,64,25,2) and v('second_planner').shape==(64,8,25,2), 'Candidate shapes')
    immediate=np.sum((v('predicted_latent')-v('goal_raw')[:1,None])**2,axis=-1)[0]
    cost=np.sum((v('scoring_terminal')-v('goal_raw')[:,None])**2,axis=-1)
    np.testing.assert_allclose(v('immediate'),immediate,rtol=2e-6,atol=1e-5)
    np.testing.assert_allclose(v('costs'),cost,rtol=2e-6,atol=1e-5)
    require(v('costs').shape==(64,8) and np.isfinite(v('costs')).all(),'Costs finite')
    exact(v('continuation'),np.sort(v('costs'),axis=1)[:,:2].mean(axis=1))
    ci,ii=int(v('continuation').argmin()),int(v('immediate').argmin())
    require(int(v('continuation_index'))==ci and int(v('immediate_index'))==ii,'Rank ties')
    chosen=ii if arm=='immediate' else ci
    require(int(v('chosen'))==chosen,'Arm selection')
    match_saved({k:v(k) for k in ('first_raw','first_planner','second_raw','second_planner',
        'predicted_latent','scoring_terminal','current_raw','goal_raw','normalized_current',
        'normalized_goal','normalized_state','supplied_state','supplied_latent','costs','immediate',
        'continuation','proposal_after')},saved,h,a)
    sp=f'h{h}/t{a}/'
    exact(v('decoder_mean'),saved[sp+'decoder_mean']);exact(v('decoder_scale'),saved[sp+'decoder_scale'])
    np.testing.assert_allclose(v('anchor_controller'),saved[sp+'anchor_controller'],rtol=0,atol=spec.ATOL)
    actions=independent_decode(v('first_planner')[0,chosen,:15],v('decoder_scale'),v('decoder_mean'))
    n=min(15,len(v('actions')));exact(v('actions')[:n],actions[:n])
    calls=row['calls'];end=a+metrics['delivered']
    require([c['at'] for c in calls]==list(range(0,end,15)), 'Full planning call grid')
    historical_calls={c['at']:c for c in historical['calls']}
    for i,c in enumerate(calls):
        at=c['at'];diag=c['diagnostics']
        require((diag['delta'],diag['tau'])==spec.schedule(h,at),'Absolute schedule')
        require(diag['call']==i and diag['arm']=='vad_continuation' and diag['family']=='vad','Original tail identity')
        require(diag['first_candidate_count']==64 and
                diag['continuations_per_first']==(8 if diag['delta']>=30 else 0),'Original workload')
        if at==a:
            require(all(diag[k]==historical_calls[at]['diagnostics'][k] for k in LIFECYCLE),'Anchor historical lifecycle')
            for name,key in (('proposal','proposal_after'),('gmm','gmm_after')):
                require(hashlib.sha256(v(key).tobytes()).hexdigest()==diag[name+'_generator_after_sha256'], 'Post-bank RNG digest')
        from diffusion_bottleneck_branch import array_hash
        plan=v(f'plan-{at}')
        require(plan.shape==(1,3,10) and array_hash(plan)==c['plan_hash'],'Saved selected plan')
        decoded=independent_decode(plan.reshape(15,2),v('decoder_scale'),v('decoder_mean'))
        if at>=a: exact(v('actions')[at-a:min(at-a+15,metrics['delivered'])],decoded[:min(15,end-at)])
        else: exact(trace['actions'][at:at+15],decoded)
        if i:
            for name in ('proposal','gmm'):
                require(diag[name+'_generator_before_sha256']==calls[i-1]['diagnostics'][name+'_generator_after_sha256'],'RNG lifecycle')
        if at<a or arm=='continuation':
            require(c['plan_hash']==historical_calls[at]['plan_hash'] and all(diag[k]==historical_calls[at]['diagnostics'][k] for k in LIFECYCLE),'Historical control call')
    if metrics['first_terminal']:
        require(row['handoff'] is None,'Terminal handoff fabricated')
    else:
        require(row['handoff']=={'absolute':a+15,'stage_index':(a+15)//15,'buffer_length':0},'Handoff time/buffer')
    if arm=='continuation':
        exact(v('actions'),trace['actions'][a:])
        np.testing.assert_allclose(v('states'),trace['states'][a+1:],rtol=0,atol=spec.ATOL)
        require(end==historical['delivered'] and metrics['success']==bool(historical['success']) and
                metrics['native_truncated']==historical['native_truncation'],'Historical control outcome')
    return metrics


def analyze(root,src,source_sha,protocol,protocol_sha,combined,completion):
    verify_source(src,source_sha);require_sha(protocol,protocol_sha)
    completed=json.loads(completion.read_text())
    require(completed['all_64_completed'] is True and len(set(completed['jobs']))==64 and
            completed['allocation_seconds']<=14400 and completed['bytes']<=2_000_000_000,'Incomplete dispatch')
    reports={}
    # No scientific arrays opened before all adjacent seals and identities pass.
    for ref in spec.REFS:
        for rep in spec.REPEATS:
            r,_=seal(root/f'ref-{ref}-repeat-{rep}')
            require((r['reference'],r['repeat'])==(ref,rep) and r['model_state_sha256']==spec.MODEL_SHA and
                    r['source_manifest_sha256']==source_sha and r['protocol_sha256']==protocol_sha and
                    r['program_sha256']==sha256(src/'cluster/prometheus/single_anchor_ranking_runner.py'),'Run provenance')
            reports[ref,rep]=r
    science=[];counts=[];repeat_arrays=0
    for ref in spec.REFS:
        _,_,histories,saved,provenance=spec.load_inputs(ref,combined)
        with np.load(root/f'ref-{ref}-repeat-0/BANKS.npz',allow_pickle=False) as x, \
             np.load(root/f'ref-{ref}-repeat-1/BANKS.npz',allow_pickle=False) as y:
            require(set(x.files)==set(y.files),'Repeat array schema')
            for key in x.files:exact(x[key],y[key]);repeat_arrays+=1
            for rep,data in ((0,x),(1,y)):
                r=reports[ref,rep];require(r['provenance']==provenance,'Historical input linkage')
                keys=[(v['horizon'],v['anchor'],v['arm']) for v in r['rows']]
                expected={(h,a,arm) for h in spec.HORIZONS for a in spec.ANCHORS for arm in spec.ARMS}
                require(len(keys)==8 and set(keys)==expected,'Duplicate/missing branch')
                metrics={};steps=0
                for row in r['rows']:
                    h,a,arm=row['horizon'],row['anchor'],row['arm'];prefix=f'h{h}/t{a}/{arm}/'
                    v=lambda key:data[prefix+key]
                    metrics[h,a,arm]=check_row(v,row,*histories[h],saved)
                    steps+=a+len(v('states'))
                require(r['primitive_steps_including_replays']==steps and r['physical_branch_rollouts']==8,'Accounting')
                counts.append({'reference':ref,'repeat':rep,'steps':steps,
                               'planning_calls':sum(len(row['calls']) for row in r['rows'])})
                for h in spec.HORIZONS:
                    for a in spec.ANCHORS:
                        c=f'h{h}/t{a}/continuation/';m=f'h{h}/t{a}/immediate/'
                        shared=['first_raw','first_planner','second_raw','second_planner','costs','immediate','continuation',
                                'proposal_after','gmm_after','global_after','cuda_global_after','anchor_state','anchor_controller','anchor_pixels','anchor_goal']
                        for name in shared:exact(data[c+name],data[m+name])
                        if int(data[c+'chosen'])==int(data[m+'chosen']):
                            for name in ('states','flags','actions'):exact(data[c+name],data[m+name])
                        if rep==0:science.append({'reference':ref,'repeat':0,'horizon':h,'anchor':a,
                            **{arm:metrics[h,a,arm] for arm in spec.ARMS}})
    return {'all_passed':True,'runs':64,'logical_branches':512,'repeat_arrays':repeat_arrays,
            'analysis':spec.reference_effects(science),'anchors':science,'counts':counts,
            'source_manifest_sha256':source_sha,'protocol_sha256':protocol_sha,
            'neural_or_hidden_physics_independently_regenerated':False,
            'protected_payload_reads':0,'historical_decision_changed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','src','protocol','combined','completion','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-sha',required=True);p.add_argument('--protocol-sha',required=True)
    a=p.parse_args()
    require(not a.out.exists(),'Refuse existing analysis')
    r=analyze(a.root,a.src,a.source_sha,a.protocol,a.protocol_sha,a.combined,a.completion)
    a.out.mkdir(parents=True)
    with (a.out/'ANALYSIS.json').open('x') as f:json.dump(r,f,sort_keys=True,indent=2,allow_nan=False)
    with (a.out/'sha256.txt').open('x') as f:f.write(sha256(a.out/'ANALYSIS.json')+'  ANALYSIS.json\n')
