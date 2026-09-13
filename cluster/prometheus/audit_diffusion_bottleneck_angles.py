"""Bounded diagnostic of a failed canonical-angle guard; never relabel outcomes."""
import argparse
import json
import itertools
from pathlib import Path
import numpy as np
from diffusion_bottleneck import require,require_sha,checked_child,write_report,sha256,ARMS,HORIZONS,SEEDS
from diffusion_bottleneck_traces import sealed_stage

def audit(study):
    files,lock=sealed_stage(study)
    counts={'runs':0,'state_samples':0,'noncanonical_runs':0,'noncanonical_states':0,
            'exact_two_pi_states':0,'negative_states':0,'above_two_pi_states':0,
            'noncanonical_goals':0,'historical_recorded_disagreements':0,
            'modular_historical_step_disagreements':0,'modular_historical_run_disagreements':0}
    examples=[];minimum=None;maximum=None
    seen=set();dtypes={};angle_disagreements=[];max_error_difference=0.0
    counts['unmasked_angular_classification_disagreements']=0
    for path,task in files:
        data=json.loads(path.read_text())
        for row in data['rows']:
            require(0<=row['reference_index']<1600,'Outside exposed scope')
            key=(row['reference_index'],row['horizon'],row['train_seed'],row['arm'])
            require(key not in seen,'Duplicate logical run');seen.add(key)
            require(key[1] in HORIZONS and key[2] in SEEDS and key[3] in ARMS,'Unexpected grid identity')
            p=checked_child(path.parent,row['trajectory_file']);require_sha(p,row['trajectory_sha256'])
            with np.load(p,allow_pickle=False) as trace:
                states=trace['states'];goal=trace['goal_state']
                require(states.ndim==2 and states.shape[1]==7 and goal.shape==(7,),'Schema')
                require(np.isfinite(states).all() and np.isfinite(goal).all(),'Nonfinite input')
                require(states.dtype==np.dtype('float64') and goal.dtype==np.dtype('float64'),'Unexpected saved dtype')
                dtype_key=f'{states.dtype}/{goal.dtype}'
                dtypes[dtype_key]=dtypes.get(dtype_key,0)+1
                angle=states[:,4];bad=(angle<0)|(angle>=2*np.pi)
                counts['runs']+=1;counts['state_samples']+=len(states)
                counts['noncanonical_states']+=int(bad.sum());counts['noncanonical_runs']+=int(bad.any())
                counts['exact_two_pi_states']+=int((angle==2*np.pi).sum())
                counts['negative_states']+=int((angle<0).sum());counts['above_two_pi_states']+=int((angle>2*np.pi).sum())
                counts['noncanonical_goals']+=int(not 0<=goal[4]<2*np.pi)
                minimum=float(angle.min()) if minimum is None else min(minimum,float(angle.min()))
                maximum=float(angle.max()) if maximum is None else max(maximum,float(angle.max()))
                for t in np.flatnonzero(bad):
                    if len(examples)<12:
                        examples.append({'reference':row['reference_index'],'arm':row['arm'],'horizon':row['horizon'],
                            'training_seed':row['train_seed'],'step':int(t),'angle':float(angle[t]),
                            'angle_hex':float(angle[t]).hex(),'trajectory_sha256':row['trajectory_sha256']})
                pos=np.linalg.norm(states[1:,:4]-goal[:4],axis=1)<20
                raw=np.abs(angle[1:]-goal[4]);historic=(np.minimum(raw,2*np.pi-raw)<np.pi/9)&pos
                circular=np.abs((angle[1:]-goal[4]+np.pi)%(2*np.pi)-np.pi)
                historical_error=np.minimum(raw,2*np.pi-raw)
                angular_bad=(historical_error<np.pi/9)!=(circular<np.pi/9)
                counts['unmasked_angular_classification_disagreements']+=int(angular_bad.sum())
                max_error_difference=max(max_error_difference,float(np.max(np.abs(historical_error-circular),initial=0)))
                for t in np.flatnonzero(angular_bad):
                    angle_disagreements.append({'identity':key,'post_action_step':int(t+1),
                        'state_angle_hex':float(angle[t+1]).hex(),'goal_angle_hex':float(goal[4]).hex(),
                        'historical_error':float(historical_error[t]),'modular_error':float(circular[t]),
                        'historical_distance_from_threshold':float(historical_error[t]-np.pi/9),
                        'modular_distance_from_threshold':float(circular[t]-np.pi/9),
                        'trajectory_sha256':row['trajectory_sha256']})
                modular=(circular<np.pi/9)&pos
                counts['historical_recorded_disagreements']+=int(bool(historic.any())!=bool(row['success']))
                counts['modular_historical_step_disagreements']+=int((modular!=historic).sum())
                counts['modular_historical_run_disagreements']+=int(bool(modular.any())!=bool(historic.any()))
    require(counts['runs']==57600,'Incomplete angle inventory')
    require(seen==set(itertools.product(range(1600),HORIZONS,SEEDS,ARMS)),'Incomplete unique grid')
    return {'counts':counts,'minimum_angle':minimum,'maximum_angle':maximum,'examples':examples,
            'unique_grid_verified':True,'saved_state_goal_dtypes':dtypes,
            'angular_classification_disagreements':angle_disagreements,
            'maximum_angular_error_formula_difference':max_error_difference,
            'two_pi':float(2*np.pi),'two_pi_hex':float(2*np.pi).hex(),
            'synthetic_negative_tiny_modulo':float(-1e-20%(2*np.pi)),
            'historical_labels_changed':False,'normalization_applied_to_saved_artifacts':False,
            'scope':'Technical boundary classification only; modular comparison is not a replacement endpoint',
            'protected_payload_reads':0,'unevaluated_reference_payload_reads':0,'model_runs':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();require(not a.out.exists(),'Existing output')
    require(a.study.resolve() not in a.out.resolve().parents,'Historical output boundary')
    r=audit(a.study);r['program_sha256']=sha256(Path(__file__))
    write_report(a.out,r,(a.study,));print(json.dumps({'complete_runs':r['counts']['runs'],'report_sha256':sha256(a.out)}))
