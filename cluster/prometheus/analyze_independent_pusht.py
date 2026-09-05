"""Complete-grid sequential analysis with independent physical-success checks."""
import argparse,csv,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.stats import t
from independent_pusht_collect import sha,seed_for
from independent_pusht_design import LOOKS,ALPHAS

PRIMARY=('vad_greedy_300','diagonal_gaussian_continuation','sage')
FINAL_ARMS=('vad_continuation','vad_greedy_300','diagonal_gaussian_continuation',
            'vad_greedy_576','direct_gmm_continuation','sage')
SEEDS=(7201,7202,7203)

def physical_success(states,goal):
    position=np.linalg.norm(states[...,:4]-goal[:4],axis=-1)
    angle=np.abs(states[...,4]-goal[4]);angle=np.minimum(angle,2*np.pi-angle)
    return (position<20)&(angle<np.pi/9)

def calculate(tensor,stage,previous=None):
    # N x H x seed x arm. Horizons and seeds stay paired inside reference.
    n=tensor.shape[0]
    assert tensor.shape==(LOOKS[stage],2,3,len(FINAL_ARMS))
    means=tensor.mean(axis=(1,2));alpha=ALPHAS[stage]
    contrasts={};ever={} if previous is None else dict(previous['ever_rejected'])
    for control in PRIMARY:
        d=means[:,0]-means[:,FINAL_ARMS.index(control)]
        se=float(d.std(ddof=1)/np.sqrt(n));delta=float(d.mean())
        lower=delta-float(t.ppf(1-alpha,n-1))*se
        reject=lower>0;ever[control]=bool(ever.get(control,False) or reject)
        contrasts[control]={'difference':delta,'se':se,'one_sided_alpha':alpha,
          'lower_bound_this_look':lower,'reject_this_look':bool(reject),
          'futility_upper_bound':delta+float(t.ppf(.999,n-1))*se,
          'mean_by_horizon':(tensor[:,:,:,0]-tensor[:,:,:,FINAL_ARMS.index(control)]).mean(axis=(0,2)).tolist()}
    futility=any(r['futility_upper_bound']<0 for r in contrasts.values())
    stop=all(ever.values()) or futility or stage==len(LOOKS)-1
    return {'n':n,'stage':stage,'arm_success':dict(zip(FINAL_ARMS,means.mean(0).tolist())),
      'task':'pusht','horizons':[75,150],'primary':contrasts,'ever_rejected':ever,
      'all_three_established':all(ever.values()),'stop':stop,'futility':futility,
      'decision':'stop_all_three_established' if all(ever.values()) else ('stop_futility_strong_adverse_signal' if futility else ('stop_maximum_sample' if stop else 'continue_next_fixed_stage')),
      'per_horizon':{arm:tensor[:,:,:,a].mean(axis=(0,2)).tolist() for a,arm in enumerate(FINAL_ARMS)},
      'inference':'Prespecified approximate paired Student with Bonferroni across looks and three contrasts; not distribution-free.'}

def analyze(study,stage):
    study=Path(study);config=json.loads((study/'CONFIG.json').read_text())
    registry=json.loads((study/'REGISTRY.json').read_text());lock=json.loads((study/'INPUT-LOCK.json').read_text())
    for file,key in [('CONFIG.json','config_sha256'),('REGISTRY.json','registry_sha256'),('collection/COLLECTION.json','collection_sha256')]:
        assert sha(study/file)==lock[key]
    assert config['arms']==list(FINAL_ARMS) and config['training_seed_blocks']==list(SEEDS)
    assert config['looks']==list(LOOKS) and config['alpha_by_look']==list(ALPHAS)
    source_hash=sha(Path(__file__).with_name('SOURCE-MANIFEST.sha256'))
    assert source_hash==lock['source_manifest_sha256']
    manifest=json.loads((study/'collection/COLLECTION.json').read_text())
    files=[]
    # Completeness barrier before reading outcome payloads.
    for k in range(stage+1):
        for task in registry['stages'][k]:
            root=study/f'stage-{k}'/f'task-{task["task"]:04d}'
            done=json.loads((root/'DONE.json').read_text())
            assert done['task']==task and done['config_sha256']==lock['config_sha256']
            assert done['source_manifest_sha256']==source_hash
            path=root/'results/RESULT.json';assert sha(path)==done['result_sha256']
            files.append((path,task))
    n=LOOKS[stage]
    reference_data={}
    for ref in manifest['records'][:n]:
        q=study/'collection'/ref['file'];assert sha(q)==ref['sha256']
        with np.load(q,allow_pickle=False) as f:
            reference_data[ref['index']]=(f['initial_request'].copy(),f['states'][75].copy(),f['states'][150].copy())
    tensor=np.full((n,2,3,len(FINAL_ARMS)),np.nan)
    initial={};model_hashes={};rawrows=[];failures=[];elapsed={a:[] for a in FINAL_ARMS};plans={a:[] for a in FINAL_ARMS};excursions={a:0 for a in FINAL_ARMS}
    for path,task in files:
        result=json.loads(path.read_text());assert result['completed'] and not result['pilot'] and result['models_unchanged']
        assert result['arm']==task['arm'] and result['train_seed']==task['seed']
        assert result['action_rule']=='native_finite' and result['collection_sha256']==lock['collection_sha256']
        assert len(result['rows'])==2*(task['end']-task['begin'])
        group=(task['arm'],task['seed']);m=result['model_state_sha256']
        assert model_hashes.setdefault(group,m)==m
        expected={(i,h) for i in range(task['begin'],task['end']) for h in (75,150)}
        actual={(r['reference_index'],r['horizon']) for r in result['rows']};assert actual==expected
        for row in result['rows']:
            i=row['reference_index'];h=row['horizon'];seed=row['train_seed'];arm=row['arm']
            assert arm==task['arm'] and seed==task['seed']
            coord=(i,(75,150).index(h),SEEDS.index(seed),FINAL_ARMS.index(arm))
            assert np.isnan(tensor[coord]);assert row['budget']==2*h
            ref=manifest['records'][i]
            assert row['reference_attempt']==ref['attempt']
            assert row['seed']==seed_for(manifest['namespace'],ref['attempt'],f'planner|h={h}|seed={seed}')
            key=(i,h);assert initial.setdefault(key,row['initial_hash'])==row['initial_hash']
            p=path.parent/row['trajectory_file'];assert sha(p)==row['trajectory_sha256']
            with np.load(p,allow_pickle=False) as f:
                states=f['states'];actions=f['actions'];raw=f['raw_actions'];goal=f['goal_state']
            np.testing.assert_allclose(states[0],reference_data[i][0],rtol=0,atol=1e-10)
            np.testing.assert_array_equal(goal,reference_data[i][1 if h==75 else 2])
            assert states.shape==(row['delivered']+1,7) and actions.shape==raw.shape==(row['delivered'],2)
            assert np.isfinite(states).all() and np.isfinite(actions).all()
            np.testing.assert_array_equal(actions,raw) # no clipping in main comparison
            y=physical_success(states[1:],goal)
            success=bool(y.any())
            if success:assert np.flatnonzero(y)[0]==len(actions)-1
            assert row['success']==int(success)
            if row['failure'] is not None:
                assert not success;failures.append({k:row[k] for k in ('reference_index','horizon','arm','train_seed','failure')})
            else:
                assert len(actions)>0
                assert [c['at'] for c in row['calls']]==list(range(0,len(actions),15))
            if not success and row['failure'] is None:assert row['native_truncation'] or len(actions)==2*h
            tensor[coord]=int(success)
            elapsed[arm].append(row['wall_seconds']);plans[arm].extend(c['seconds'] for c in row['calls']);excursions[arm]+=row['decoded_outside_box_coordinates']
            rawrows.append({k:row[k] for k in ('reference_index','reference_attempt','horizon','arm','train_seed','success','delivered','wall_seconds')})
    assert np.isfinite(tensor).all() and set(np.unique(tensor))<={0.,1.}
    previous=None if stage==0 else json.loads((study/f'analysis-{stage-1}/SUMMARY.json').read_text())
    report=calculate(tensor,stage,previous)
    report.update(failures=failures,complete_logical_runs=len(rawrows),input_lock_sha256=sha(study/'INPUT-LOCK.json'),
       source_manifest_sha256=source_hash,collection_sha256=lock['collection_sha256'],
       checkpoints_unchanged=True,physics_success_independently_recomputed=True,
       timing={a:{'episode_wall_mean':float(np.mean(elapsed[a])),'planner_mean':float(np.mean(plans[a])) if plans[a] else None,
                  'planner_median':float(np.median(plans[a])) if plans[a] else None,'planner_p90':float(np.quantile(plans[a],.9)) if plans[a] else None,
                  'outside_box_coordinates':excursions[a]} for a in FINAL_ARMS})
    out=study/f'analysis-{stage}';out.mkdir(exist_ok=False)
    np.savez_compressed(out/'EPISODE-TENSOR.npz',success=tensor)
    with gzip.open(out/'ALL-EPISODES.tsv.gz','wt') as f:
        writer=csv.DictWriter(f,fieldnames=list(rawrows[0]),delimiter='\t');writer.writeheader();writer.writerows(rawrows)
    (out/'SUMMARY.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    md=f'# Independent PushT look {stage+1}: N={n}\n\nDecision: **{report["decision"]}**\n\n'
    md+='|Arm|Mean success|H75|H150|\n|---|---:|---:|---:|\n'
    for arm in FINAL_ARMS:md+=f'|{arm}|{100*report["arm_success"][arm]:.2f}%|{100*report["per_horizon"][arm][0]:.2f}%|{100*report["per_horizon"][arm][1]:.2f}%|\n'
    md+='\n|Control|Difference (pp)|Lower bound at this look (pp)|Crossed now|\n|---|---:|---:|---|\n'
    for control,r in report['primary'].items():md+=f'|{control}|{100*r["difference"]:.3f}|{100*r["lower_bound_this_look"]:.3f}|{r["reject_this_look"]}|\n'
    md+='\nNew independent weak-policy reachable-goal distribution; not original SAGE paper reproduction. Fixed checkpoint blocks, episode-level inference. All registered outcomes included.\n'
    (out/'RESULT.md').write_text(md)
    (out/'sha256.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='sha256.txt'))
    print(json.dumps({'decision':report['decision'],'n':n,'all_three_established':report['all_three_established']}))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--stage',type=int,required=True)
    a=p.parse_args();analyze(a.study,a.stage)
