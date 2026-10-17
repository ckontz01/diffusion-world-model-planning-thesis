"""Artificial fixed-estimator/complete-counter checks; no study data read."""
import json,tempfile
from pathlib import Path
from .analysis import paired,authorization,pack
from .usage import total,cpu_history,CAPS
from wm_diag0_rc1_grid_v1.common import ROOT,SETTINGS,bounds,identity,write_new
from wm_diag0_rc1_technical_v1.common import bounds as technical_bounds


def reject(fn):
    try:fn()
    except (ValueError,PermissionError,FileNotFoundError):return
    raise AssertionError('required rejection missing')


def main():
    proofs=[];parents=[]
    for s,(task,backbone) in enumerate(SETTINGS):
        for i in range(32):
            r={'accepted':True,'setting':s,'root_index':i,'root_id':'artificial:'+task+':'+str(i),'task':task,'backbone':backbone,
               'candidate_count':16,'outcomes':[[int((i+j)%2),int((i+j+1)%2)] for j in range(16)],'choices':[0,1,2,3],
               'initial_success':False,'technical':i==0}
            actual=technical_bounds(s) if i==0 and s else dict(visual_encoder_calls=2002,encoded_frames=2066,proprio_encoder_calls=0,action_encoder_calls=5958,predictor_calls=4965,cost_api_calls=993) if i==0 else bounds(s*31+i-1)
            usage={k:actual[k] for k in ('encoded_frames','predictor_calls','cost_api_calls')}
            worlds=51 if i==0 else 49;steps=3020 if i==0 else 2980
            # Artificial feasible aggregate, not a truncation of any real work.
            if s==0 and i==0:steps-=40
            physical={'world_resets':worlds,'controller_actions':steps,'Reacher_dm_steps':2*steps if task=='reacher' else 0,
                'PushT_controller_actions':steps if task=='pusht' else 0,'PushT_world_resets':worlds if task=='pusht' else 0,'native_CEM_decisions':33}
            proofs.append(r);parents.append((r,Path('artificial-not-opened'),usage,physical,None if s==0 and i==0 else actual))
    groups,pooled=paired(proofs)
    if len(groups)!=4 or any(x['n_independent_parents']!=32 for x in groups.values()) or any(x['n_independent_parents']!=64 for x in pooled.values()):raise AssertionError('parent counts, never candidates/draws')
    if groups['pusht|lewm']!=pack(proofs[:32]):raise AssertionError('same original fixed estimator/bootstrap exactly')
    if any(v['mean']!=0 for g in groups.values() for v in g['contrasts'].values()):raise AssertionError('synthetic two-draw known contrasts')
    reject(lambda:paired(proofs[:-1]));reject(lambda:paired(proofs[:-1]+[proofs[0]]))
    heads=[{'accepted':True,'active':i in (0,2,4,5),'fit_frames':256,'validation_frames':96} for i in range(6)]
    resource=total(parents,heads,10);counts=resource['all_attempt_counts']
    for k in ('DINO_predictor_calls','LeWM_predictor_calls','forecast_cost_API_operations','bank_reforecast_sequences','additional_parity_sequences','native_CEM_decisions','CEM_sequences','predicted_macro_sequence_transitions'):
        if counts[k]!=CAPS[k]:raise AssertionError('failure-inclusive exact maximum '+k)
    if counts['encoded_frames']!=143779 or resource['baseline_encoded_frames_all_six_fits_and_failed_diagnostics']!=2317:raise AssertionError('all six fits/failures/frame arithmetic')
    changed=list(parents);proof,out,u,w,a=changed[32];changed[32]=(proof,out,dict(u,predictor_calls=u['predictor_calls']+1),w,dict(a,predictor_calls=a['predictor_calls']+1))
    reject(lambda:total(changed,heads,10));reject(lambda:total(parents[:-1],heads,10));reject(lambda:total(parents,heads[:-1],10))
    bad=list(parents);p,o,u,w,a=bad[0];bad[0]=(p,o,u,dict(w,world_resets=w['world_resets']+1),a);reject(lambda:total(bad,heads,10))
    old=['|'.join(['317041_'+str(i),str(600000+i),'COMPLETED','0:0',str(16 if i==59 else 11),'4','artificial-cpu']) for i in range(60)]
    old+=['317041_60|317102|FAILED|125:0|13|4|artificial-cpu','317041_[61-119%1]|317041|CANCELLED by 1201|0:0|0|4|None assigned']
    new=['|'.join(['317103_'+str(i+60),str(700000+i),'COMPLETED','0:0',str(33 if i==59 else 12),'4','artificial-cpu']) for i in range(60)]
    sources={'scheduler_original':'\n'.join(old),'scheduler_recovery':'\n'.join(new),'cpu_total_with_preflight':1436,'failed_replacement_attempts':1}
    if cpu_history(sources)['full_future_seconds']!=6836:raise AssertionError('source failure and unused conversion CPU reservation')
    reject(lambda:cpu_history(dict(sources,cpu_total_with_preflight=1423)))
    with tempfile.TemporaryDirectory(prefix='wm-rc1-final-disabled-') as tmp:
        p=Path(tmp)/'contract.json';write_new(p,{'domain':'artificial'})
        reject(lambda:authorization({'gpu_stages_authorized':False},identity(p)['sha256'],p,Path(tmp)/'analysis-0'))
    folder=ROOT/'wm_diag0_rc1_final_v1'
    source={}
    for p in folder.glob('*.py'):compile(p.read_bytes(),str(p),'exec');source[p.name]=identity(p)
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v1-20261016'
    write_new(doc/'ARTIFICIAL-ANALYSIS-002.json',{'status':'PASSED','source':source,'checks':['complete128 exact-parent gate','32per setting/64per backbone fixed estimator identical to original pack','known artificial two-draw contrasts','all-attempt exact maximum model/API/sequence counters','sixfit failures encoded143779 versus cap265360','failed-source CPU1436 plus future reserves6836','overrun/missing/head/physical rejection','grid contract cannot authorize final analysis'],
        'research_artifacts_or_partial_scientific_aggregates_read':False,'model_simulator_or_fit_calls':0,'real_final_analysis_executed':False,'final_gate_ready':False,
        'remaining':'authenticated historical baseline receipt, full runtime/alias binding, archive creation/verification/transfer, CPU supervisor/freeze/publication/SSD'})
    print(json.dumps({'status':'FINAL_ANALYSIS_AND_ALL_ATTEMPT_ACCOUNTING_ARTIFICIAL_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
