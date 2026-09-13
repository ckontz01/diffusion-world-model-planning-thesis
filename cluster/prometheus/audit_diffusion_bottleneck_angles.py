"""Bounded diagnostic of a failed canonical-angle guard; never relabel outcomes."""
import argparse
import json
from pathlib import Path
import numpy as np
from diffusion_bottleneck import require,require_sha,checked_child,write_report,sha256
from diffusion_bottleneck_traces import sealed_stage

def audit(study):
    files,lock=sealed_stage(study)
    counts={'runs':0,'state_samples':0,'noncanonical_runs':0,'noncanonical_states':0,
            'exact_two_pi_states':0,'negative_states':0,'above_two_pi_states':0,
            'noncanonical_goals':0,'historical_recorded_disagreements':0,
            'modular_historical_step_disagreements':0,'modular_historical_run_disagreements':0}
    examples=[];minimum=None;maximum=None
    for path,task in files:
        data=json.loads(path.read_text())
        for row in data['rows']:
            require(0<=row['reference_index']<1600,'Outside exposed scope')
            p=checked_child(path.parent,row['trajectory_file']);require_sha(p,row['trajectory_sha256'])
            with np.load(p,allow_pickle=False) as trace:
                states=trace['states'];goal=trace['goal_state']
                require(states.ndim==2 and states.shape[1]==7 and goal.shape==(7,),'Schema')
                require(np.isfinite(states).all() and np.isfinite(goal).all(),'Nonfinite input')
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
                modular=(circular<np.pi/9)&pos
                counts['historical_recorded_disagreements']+=int(bool(historic.any())!=bool(row['success']))
                counts['modular_historical_step_disagreements']+=int((modular!=historic).sum())
                counts['modular_historical_run_disagreements']+=int(bool(modular.any())!=bool(historic.any()))
    require(counts['runs']==57600,'Incomplete angle inventory')
    return {'counts':counts,'minimum_angle':minimum,'maximum_angle':maximum,'examples':examples,
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
