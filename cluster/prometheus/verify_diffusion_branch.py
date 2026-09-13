"""Independent, NumPy-only sealed pilot validation and descriptive reduction."""
import argparse
import json
from pathlib import Path
import numpy as np
from diffusion_bottleneck import require,require_sha,sha256,write_report

REFS=(1269,582,525,722)
CONDS=('baseline','state','latent','joint')

def physical(states,flags,goal):
    require(states.ndim==2 and states.shape[1]==7 and 0<len(states)<=30,'Physical shape')
    require(flags.shape==(len(states),2) and np.isfinite(states).all(),'Flags/finite')
    require(not flags[:-1].any(),'Stepped after termination')
    raw=np.abs(states[:,4]-goal[4]);angle=np.minimum(raw,2*np.pi-raw)
    joint=np.sqrt(np.sum((states[:,:4]-goal[:4])**2,axis=1))
    success=(joint<20)&(angle<np.pi/9)
    np.testing.assert_array_equal(success,flags[:,0])
    return {'success':bool(success.any()),'delivered':len(states),
            'closest_margin':float(np.max(np.stack((joint/20,angle/(np.pi/9))),axis=0).min())}

def seal(directory):
    seen={}
    for line in (directory/'sha256.txt').read_text().splitlines():
        digest,name=line.split(maxsplit=1)
        require(name in ('BANKS.npz','REPORT.json') and name not in seen,'Unexpected seal')
        require_sha(directory/name,digest);seen[name]=digest
    require(set(seen)=={'BANKS.npz','REPORT.json'},'Incomplete seal')
    report=json.loads((directory/'REPORT.json').read_text())
    require(report['all_technical_checks_passed'] is True,'Runner failed')
    require(report['banks_sha256']==seen['BANKS.npz'],'Bank identity')
    for name in ('protected_payload_reads','unevaluated_reference_payload_reads','training_runs'):
        require(report[name]==0,'Forbidden execution')
    require(report['historical_decision_changed'] is False,'Historical change')
    return report,seen

def analyze(root):
    # All eight adjacent seals pass BEFORE scientific arrays are opened.
    reports={};seals={}
    for ref in REFS:
        for repeat in (0,1):
            directory=root/f'ref-{ref}-repeat-{repeat}'
            r,s=seal(directory);require((r['reference'],r['repeat'])==(ref,repeat),'Wrong run identity')
            reports[ref,repeat]=r;seals[str(directory)]=s
    results=[];array_count=0;total_wall=0;steps=0;branches=0
    for ref in REFS:
        r=reports[ref,0]
        require(reports[ref,1]['model_state_sha256']==r['model_state_sha256'],'Repeat models')
        with np.load(root/f'ref-{ref}-repeat-0/BANKS.npz',allow_pickle=False) as a, \
             np.load(root/f'ref-{ref}-repeat-1/BANKS.npz',allow_pickle=False) as b:
            require(set(a.files)==set(b.files),'Repeat bank schema')
            for key in a.files:
                require(a[key].dtype==b[key].dtype and a[key].shape==b[key].shape,'Repeat array metadata')
                require(a[key].tobytes()==b[key].tobytes(),'Repeat bytes differ: '+key)
                array_count+=1
            require(r['anchors']==reports[ref,1]['anchors'],'Repeat anchor decisions')
            require({(x['horizon'],x['anchor']) for x in r['anchors']}=={(h,t) for h in (75,150) for t in (0,30)},'Anchor grid')
            for row in r['anchors']:
                if not row['available']:
                    results.append({'reference':ref,**row});continue
                prefix=f"h{row['horizon']}/t{row['anchor']}"
                def v(key):return a[prefix+'/'+key]
                require(v('first_planner').shape==(1,64,25,2),'First bank shape')
                require(v('first_noise').shape[:2]==(1,64) and v('second_noise').shape[:2]==(64,8),'Noise bank shape')
                # sklearn inverse_transform uses FP32 in-place multiply then add.
                delivered=v('first_planner')[0,:,:15].copy()
                delivered*=v('decoder_scale');delivered+=v('decoder_mean')
                np.testing.assert_array_equal(delivered,v('physical_first'))
                active=[];metrics=[];first_states=[]
                for i in range(64):
                    states=v(f'first-{i}/states');flags=v(f'first-{i}/termination_flags')
                    require(len(states)<=15,'First chunk overrun')
                    metrics.append(physical(states,flags,v('goal_state')))
                    active.append(len(states)==15 and not flags[-1].any());first_states.append(states[-1])
                np.testing.assert_array_equal(v('actual_states'),first_states)
                np.testing.assert_array_equal(v('active'),active)
                np.testing.assert_array_equal(v('first_success'),[x['success'] for x in metrics])
                sn=(v('actual_states').astype(np.float32)-v('state_mean'))/v('state_std')
                ln=(v('actual_latents')-v('latent_mean'))/v('latent_std')
                predicted=v('predicted_latent').reshape(64,-1)
                np.testing.assert_allclose(v('baseline/supplied_latent'),(predicted-v('latent_mean'))/v('latent_std'),rtol=1e-6,atol=1e-6)
                np.testing.assert_array_equal(v('baseline/supplied_state'),v('predicted_state'))
                selected={};mask=np.asarray(active)[:,None]
                for cond in CONDS:
                    state=np.where(mask,sn,v('predicted_state')) if cond in ('state','joint') else v('predicted_state')
                    latent=np.where(mask,ln,v('baseline/supplied_latent')) if cond in ('latent','joint') else v('baseline/supplied_latent')
                    np.testing.assert_allclose(v(cond+'/supplied_state'),state,rtol=1e-6,atol=1e-6)
                    np.testing.assert_allclose(v(cond+'/supplied_latent'),latent,rtol=1e-6,atol=1e-6)
                    # Inactive inputs and all unchanged components must be bit-identical.
                    np.testing.assert_array_equal(v(cond+'/supplied_state')[~np.asarray(active)],v('predicted_state')[~np.asarray(active)])
                    np.testing.assert_array_equal(v(cond+'/supplied_latent')[~np.asarray(active)],v('baseline/supplied_latent')[~np.asarray(active)])
                    if cond in ('baseline','latent'):np.testing.assert_array_equal(v(cond+'/supplied_state'),v('predicted_state'))
                    if cond in ('baseline','state'):np.testing.assert_array_equal(v(cond+'/supplied_latent'),v('baseline/supplied_latent'))
                    costs=v(cond+'/costs');require(costs.shape==(64,8) and np.isfinite(costs).all(),'Costs')
                    recomputed=np.sum((v(cond+'/scoring_terminal')-v('goal_raw')[:,None])**2,axis=-1)
                    np.testing.assert_allclose(costs,recomputed,rtol=2e-6,atol=1e-5)
                    scores=np.sort(costs,axis=1)[:,:2].mean(axis=1)
                    np.testing.assert_array_equal(v(cond+'/scores'),scores)
                    i=int(np.argmin(scores));j=int(np.argmin(costs[i]))
                    require(row['selected'][cond]==[i,j],'Selector/tie mismatch')
                    states=v(cond+'/states');flags=v(cond+'/termination_flags')
                    second_actions=v(cond+'/second_planner')[i,j,:15].copy()
                    second_actions*=v('decoder_scale');second_actions+=v('decoder_mean')
                    np.testing.assert_array_equal(v(cond+'/delivered_actions'),np.concatenate((delivered[i],second_actions))[:len(states)])
                    length=min(15,len(states))
                    np.testing.assert_array_equal(states[:length],v(f'first-{i}/states'))
                    two=physical(states,flags,v('goal_state'))
                    require(two['success']==row['short_outcomes'][cond]['short_branch_success'],'Short outcome')
                    selected[cond]={'first_index':i,'second_index':j,'first_chunk':metrics[i],
                                    'committed_two_chunk':two,
                                    'first_margin_regret':metrics[i]['closest_margin']-min(x['closest_margin'] for x in metrics)}
                greedy=int(v('greedy64/costs').argmin());require(greedy==row['greedy64'],'Greedy selector')
                np.testing.assert_array_equal(v('greedy64/states'),v(f'first-{greedy}/states'))
                adapter_error=(v('predicted_state')-sn)[np.asarray(active)]
                latent_error=(predicted-v('actual_latents'))[np.asarray(active)]
                results.append({'reference':ref,'horizon':row['horizon'],'anchor':row['anchor'],'available':True,
                    'active_branches':int(sum(active)),'terminated_first':sum(bool(v(f'first-{i}/termination_flags')[-1,0]) for i in range(64)),
                    'truncated_first':sum(bool(v(f'first-{i}/termination_flags')[-1,1]) for i in range(64)),
                    'first_chunk_successes':sum(x['success'] for x in metrics),'selected':selected,
                    'greedy64_first_chunk':metrics[greedy],
                    'active_adapter_normalized_state_rmse':float(np.sqrt(np.mean(adapter_error**2))) if len(adapter_error) else None,
                    'active_latent_raw_rmse':float(np.sqrt(np.mean(latent_error**2))) if len(latent_error) else None})
        for repeat in (0,1):
            q=reports[ref,repeat];total_wall+=q['wall_seconds'];steps+=q['primitive_steps_including_replays'];branches+=q['physical_branch_rollouts']
    return {'all_technical_checks_passed':True,'runs':8,'repeat_arrays_bit_identical':array_count,'anchors':results,
        'sum_runner_wall_seconds':total_wall,'primitive_steps_including_prefixes':steps,'physical_branch_rollouts':branches,
        'maximum_gpu_peak_allocated_bytes':max(x['gpu_peak_allocated_bytes'] for x in reports.values()),
        'linear_32_reference_two_repeat_runner_seconds':8*total_wall,
        'extrapolation_warning':'Linear planning estimate only; different termination patterns and queue/load may change costs',
        'scope':'Four identifier-selected exposed references in outcome-informed development; not efficacy or full second-bank oracle',
        'seals':seals,'protected_payload_reads':0,'unevaluated_reference_payload_reads':0,'historical_decision_changed':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=analyze(a.root);r['program_sha256']=sha256(Path(__file__));write_report(a.out,r,(a.root,))
