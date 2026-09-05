"""Synthetic statistical and provenance tests; no final outcomes."""
import json
import numpy as np
import pytest
from analyze_independent_pusht import calculate,physical_success,FINAL_ARMS
from independent_pusht_design import LOOKS,ALPHAS

def test_no_effect_never_rejects():
    x=np.zeros((1600,2,3,6))
    r=calculate(x,0)
    assert not r['stop'] and not any(r['ever_rejected'].values())

def test_large_effect_rejects_all():
    x=np.zeros((1600,2,3,6));x[:,:,:,0]=1
    r=calculate(x,0)
    assert r['stop'] and r['all_three_established']
    assert all(c['lower_bound_this_look']==1 for c in r['primary'].values())

def test_episode_clustering_matches_manual():
    rng=np.random.default_rng(96);x=rng.binomial(1,.5,(1600,2,3,6))
    r=calculate(x,0)
    d=(x[:,:,:,0]-x[:,:,:,1]).mean(axis=(1,2))
    assert r['primary']['vad_greedy_300']['difference']==pytest.approx(d.mean())
    assert r['primary']['vad_greedy_300']['se']==pytest.approx(d.std(ddof=1)/40)

def test_earlier_rejection_preserved_not_new_threshold():
    x=np.zeros((3200,2,3,6));prior={'ever_rejected':{a:True for a in ('vad_greedy_300','diagonal_gaussian_continuation','sage')}}
    r=calculate(x,1,prior)
    assert r['stop'] and all(r['ever_rejected'].values())
    assert not any(v['reject_this_look'] for v in r['primary'].values())

def test_maximum_sample_stops_without_claim():
    r=calculate(np.zeros((6000,2,3,6)),2)
    assert r['decision']=='stop_maximum_sample' and not r['all_three_established']

def test_physics_success_angle_wrap_and_agent_inclusion():
    goal=np.array([100,100,200,200,0,0,0.])
    s=np.tile(goal,(4,1));s[1,4]=2*np.pi-.01;s[2,0]+=21;s[3,4]=np.pi
    np.testing.assert_array_equal(physical_success(s,goal),[True,True,False,False])

def test_all_registered_looks_alpha():
    assert sum(ALPHAS)*3==pytest.approx(.05)
    assert LOOKS[0]>=1600 and LOOKS[-1]==6000


def test_strong_adverse_signal_stops_without_superiority():
    x=np.zeros((1600,2,3,6));x[:,:,:,5]=1
    r=calculate(x,0)
    assert r['futility'] and r['stop'] and not r['all_three_established']
    assert r['decision']=='stop_futility_strong_adverse_signal'


def test_complete_synthetic_grid_and_independent_verifier(tmp_path,monkeypatch):
    import analyze_independent_pusht as a
    import verify_independent_pusht_analysis as v
    from independent_pusht_collect import sha,seed_for
    monkeypatch.setattr(a,'LOOKS',(2,4,6))
    source=tmp_path/'source';source.mkdir();(source/'SOURCE-MANIFEST.sha256').write_text('synthetic')
    monkeypatch.setattr(a,'__file__',str(source/'analyzer.py'))
    root=tmp_path/'study';root.mkdir();data=root/'collection';data.mkdir()
    cfg={'arms':list(FINAL_ARMS),'training_seed_blocks':[7201,7202,7203],
         'looks':[2,4,6],'alpha_by_look':list(ALPHAS)}
    refs=[]
    for i in range(2):
        initial=np.array([50.+i,50.,120.,120.,.1,0.,0.])
        states=np.tile(initial,(151,1));states[75,:4]=[350,350,300,300];states[150,:4]=[400,400,350,350]
        file=f'ref-{i}.npz';np.savez_compressed(data/file,initial_request=initial,states=states)
        refs.append({'index':i,'attempt':i,'file':file,'sha256':sha(data/file)})
    manifest={'namespace':'final-20260906-primary-v1','records':refs}
    (data/'COLLECTION.json').write_text(json.dumps(manifest))
    registry={'stages':[[{'task':k,'arm':arm,'seed':seed,'begin':0,'end':2}
       for k,(arm,seed) in enumerate((arm,s) for arm in FINAL_ARMS for s in (7201,7202,7203))]]}
    (root/'CONFIG.json').write_text(json.dumps(cfg));(root/'REGISTRY.json').write_text(json.dumps(registry))
    lock={'config_sha256':sha(root/'CONFIG.json'),'registry_sha256':sha(root/'REGISTRY.json'),
      'collection_sha256':sha(data/'COLLECTION.json'),'source_manifest_sha256':sha(source/'SOURCE-MANIFEST.sha256')}
    (root/'INPUT-LOCK.json').write_text(json.dumps(lock))
    for task in registry['stages'][0]:
        parent=root/'stage-0'/f'task-{task["task"]:04d}';rdir=parent/'results';rdir.mkdir(parents=True)
        arm=task['arm'];rows=[]
        for i in range(2):
            with np.load(data/refs[i]['file']) as f:initial=f['initial_request'];reference=f['states']
            for h in (75,150):
                win=arm=='vad_continuation';failure=arm=='direct_gmm_continuation'
                count=0 if failure else (1 if win else 2*h)
                states=np.tile(initial,(count+1,1));goal=reference[h]
                if win:states[-1]=goal
                actions=np.zeros((count,2),np.float32)
                name=f'trace-{i}-{h}.npz';np.savez_compressed(rdir/name,states=states,actions=actions,raw_actions=actions,goal_state=goal)
                row={'reference_index':i,'reference_attempt':i,'horizon':h,'train_seed':task['seed'],'arm':arm,
                    'budget':2*h,'seed':seed_for(manifest['namespace'],i,f'planner|h={h}|seed={task["seed"]}'),
                    'initial_hash':str((i,h)),'trajectory_file':name,'trajectory_sha256':sha(rdir/name),
                    'delivered':count,'success':int(win),'native_truncation':False,
                    'failure':{'category':'planner','message':'synthetic'} if failure else None,
                    'calls':[{'at':j,'seconds':.01} for j in range(0,count,15)],
                    'wall_seconds':.1,'decoded_outside_box_coordinates':0}
                rows.append(row)
        result={'completed':True,'pilot':False,'models_unchanged':True,'arm':arm,'train_seed':task['seed'],
          'action_rule':'native_finite','collection_sha256':lock['collection_sha256'],
          'model_state_sha256':'synthetic'+arm,'rows':rows}
        (rdir/'RESULT.json').write_text(json.dumps(result))
        (parent/'DONE.json').write_text(json.dumps({'task':task,'config_sha256':lock['config_sha256'],
          'source_manifest_sha256':lock['source_manifest_sha256'],'result_sha256':sha(rdir/'RESULT.json')}))
    report=a.analyze(root,0)
    verified=v.verify(root,0)
    assert verified['all_passed'] and report['all_three_established']
    assert len(report['failures'])==12
