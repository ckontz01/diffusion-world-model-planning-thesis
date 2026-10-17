"""New complete-validator artificial test; no original study arrays/results."""
import ast,copy,json,time
from pathlib import Path
import numpy as np
from . import analysis_validate_v1 as v
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except (ValueError,PermissionError):return
    raise AssertionError('required complete-analysis validation rejection absent')


def main():
    parents=[];heads={s:(Path('artificial-head-'+str(s)),{'bytes':1,'sha256':str(s)*64}) for s in range(4)}
    head_proofs=[{'accepted':True,'active':i in (0,2,4,5),'fit_frames':256,'validation_frames':96} for i in range(6)]
    for s,(task,backbone) in enumerate(v.SETTINGS):
        for i in range(32):
            proof={'accepted':True,'setting':s,'root_index':i,'root_id':'artificial:'+task+':'+str(i),'task':task,'backbone':backbone,
                   'candidate_count':2,'outcomes':[[0,1],[1,0]],'choices':[0,1,0,1],'initial_success':False,'technical':i==0,
                   'reasons':{'artificial':True},'output_seal':{'bytes':1,'sha256':'a'*64}}
            parents.append((proof,Path('artificial-parent-'+str(s)+'-'+str(i)),{}, {}, {}))
    # New independent decoder/math branch tested with inert in-memory artifact
    # adapters. Only the unchanged real fixed estimator/NumPy math is executed.
    original_json,original_array=v.read_json,v.load_array
    def fixture_json(path):
        if path.name=='READOUT.json':return {'quality':{'synthetic_only':True}}
        if path.name=='BRANCH.json':return {'events':[{'coordinates':[0.0]*5}]}
        raise AssertionError('undeclared artificial JSON access')
    def fixture_array(path):
        if path.name=='coordinates.npy':return np.zeros((45,5),dtype=np.float64)
        if path.name=='predicted.npy':return np.ones((2,3,4),dtype=np.float32)
        if path.name=='realized.npy':return np.zeros((2,3,4),dtype=np.float32)
        if path.name=='costs.npy':return np.asarray([[0,1],[1,0],[0,1],[1,0]],dtype=np.float32)
        raise AssertionError('undeclared artificial array access')
    c={'source_runs':{'pusht':'artificial-source-pusht','reacher':'artificial-source-reacher'},'source_acceptance':{'bytes':1,'sha256':'b'*64}}
    sources={'exact_source_job_ids':['artificial-only'],'source_contract':{'bytes':1,'sha256':'c'*64}}
    final={'grid_contract':{'bytes':1,'sha256':'d'*64}}
    try:
        v.read_json,v.load_array=fixture_json,fixture_array
        result,acceptance=v.reconstruct(c,'e'*64,final,sources,heads,head_proofs,parents,{'GPU_charged_seconds':1},
                                       {'synthetic':True},{'synthetic':True},time.monotonic()+30)
        if set(result['settings'])!={t+'|'+b for t,b in v.SETTINGS} or any(g['n_independent_parents']!=32 for g in result['settings'].values()) or any(g['n_independent_parents']!=64 for g in result['pooled_by_backbone'].values()):
            raise AssertionError('fixed complete setting/pooled parent cardinality')
        if len(result['local_task_distances'])!=128 or len(result['feature_prediction_diagnostics'])!=128 or len(acceptance['parent_output_seals'])!=128:raise AssertionError('every complete parent diagnostic/seal reconstructed')
        for diag in result['feature_prediction_diagnostics'].values():
            if diag['MSE_by_retained_sampling_position']!=[1.0]*3 or diag['within_bank_S0_pairwise_rank_agreement']!=1.0:raise AssertionError('known synthetic independent diagnostics')
        v.compare_payloads(copy.deepcopy(result),copy.deepcopy(acceptance),result,acceptance)
        reject(lambda:v.exact_complete(parents[:-1],heads,head_proofs))
        reject(lambda:v.exact_complete(parents[:-1]+[parents[0]],heads,head_proofs))
        reject(lambda:v.exact_complete(parents,heads,head_proofs[:-1]))
        for name in ('missing','extra','wrong_float','boolean_number','limitations','nonfinite'):
            bad=copy.deepcopy(result)
            if name=='missing':bad['feature_prediction_diagnostics'].pop(next(iter(bad['feature_prediction_diagnostics'])))
            if name=='extra':bad['extra_unchecked_field']=True
            if name=='wrong_float':next(iter(bad['feature_prediction_diagnostics'].values()))['MSE_by_retained_sampling_position'][0]=1.01
            if name=='boolean_number':bad['independent_parent_count_per_backbone']=True
            if name=='limitations':bad['limitations']=[]
            if name=='nonfinite':bad['independent_parent_count_per_backbone']=float('nan')
            reject(lambda:v.compare_payloads(bad,acceptance,result,acceptance))
        bad=copy.deepcopy(acceptance);bad['publication_requires_final_SSD_whole_and_every_member_verification']=False
        reject(lambda:v.compare_payloads(result,bad,result,acceptance))
    finally:v.read_json,v.load_array=original_json,original_array
    source={}
    for n in ('analysis_validate_v1.py','analysis_validate_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    out={'status':'COMPLETE_ANALYSIS_SECOND_PASS_ARTIFICIAL_VALIDATION_PASSED','source':source,
         'synthetic_parents':128,'retained_fits':6,'active_heads':4,'fixed_estimator_seed':20261004,
         'checks':['complete128 before aggregates','all four32parent and two64parent original-estimator groups',
                   'all128 private distance/prediction diagnostics and parent seals','exact full JSON reconstruction, no ignored fields/tolerance',
                   'missing/duplicate/head/field/diagnostic/boolean/limitations/nonfinite/finalSSD downgrade rejection'],
         'artifact_access_scope':'inert in-memory JSON/array fixtures; actual unchanged fixed estimator and NumPy math',
         'original_research_files_values_or_scientific_aggregates_read':False,'real_final_analysis_executed':False,
         'network_calls':0,'scheduler_calls':0,'model_simulator_fit_source_generation_calls':0,
         'actual_final_source_frozen_or_published':False,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-COMPLETE-VALIDATOR-001.json',out,limit=16000)
    print(json.dumps({'status':out['status'],'synthetic_parents':128,'research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
