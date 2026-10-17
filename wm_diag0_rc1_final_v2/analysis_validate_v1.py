"""Independent COMPLETE analysis reconstruction inside a future CPU allocation.

No public main/partial-results entry. The separately frozen supervisor must run
this under cpu_process_v2 and its allocation-wide CPU/memory/deadline limits.
Every original supplier is independently accepted again BEFORE any aggregate.
Scientific payloads remain private; the returned proof contains identities only.
"""
import json
from pathlib import Path
import numpy as np
from wm_diag0_rc1_grid_v1.common import SETTINGS,identity
from wm_diag0_native_v3.store import authenticate,load_array
from wm_diag0_campaign_v4.analysis import pack,native_distances
from wm_diag0_rc1_final_v1.analysis import LIMITATIONS,authorization
from wm_diag0_rc1_final_v1.suppliers import independently_accept_sources,independently_accept_heads,independently_accept_parents
from wm_diag0_rc1_final_v1.usage import cpu_history,total
from wm_diag0_rc1_final_v1.ledger import reconcile
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity
from .archive_v2 import canonical,check_time
from .evidence_auth_v1 import authenticate_usage,bound_json


def read_json(path):
    return json.loads(Path(path).read_text())


def exact_complete(parents,heads,head_proofs):
    if len(parents)!=128 or {(r[0]['setting'],r[0]['root_index']) for r in parents}!={(s,i) for s in range(4) for i in range(32)}:
        raise ValueError('independent complete128 before any scientific aggregate')
    if set(heads)!=set(range(4)) or len(head_proofs)!=6 or sum(h.get('active') is True for h in head_proofs)!=4:
        raise ValueError('all six retained fits and four active heads, not obsolete four-fit finalizer')
    for proof,out,usage,physical,actual in parents:
        if proof.get('accepted') is not True or (proof['task'],proof['backbone'])!=SETTINGS[proof['setting']]:
            raise ValueError('each exact setting/root independently accepted')
    return [row[0] for row in parents]


def reconstruct(c,expected,final,sources,heads,head_proofs,parents,accounting,cpu,resource,deadline):
    """Second private pass, reusing ONLY the unchanged fixed estimator/math.

    Does not trust the first writer's result objects or accepted parent list.
    Production validate_complete independently builds the inputs from originals.
    """
    accepted=exact_complete(parents,heads,head_proofs);check_time(deadline)
    settings={}
    for s,(task,backbone) in enumerate(SETTINGS):
        check_time(deadline);settings[task+'|'+backbone]=pack([r for r in accepted if r['setting']==s])
    pooled={}
    for backbone in ('lewm','dinowm_noprop'):
        check_time(deadline);pooled[backbone]=pack([r for r in accepted if r['backbone']==backbone])
    result={'study':'WM-DIAG0-A2-RC1','status':'COMPLETE_RESULTS_PENDING_FINAL_SSD_PRESERVATION',
            'settings':settings,'pooled_by_backbone':pooled,'head_quality':{},'head_lineage':head_proofs,
            'independent_parent_count_per_backbone':64,'paired_bootstrap_seed':20261004,'limitations':LIMITATIONS,
            'termination_reasons':{},'local_task_distances':{},'feature_prediction_diagnostics':{},
            'resource_accounting':accounting,'CPU_history':cpu,'all_attempt_numerical_and_physical_usage':resource,
            'source_lineage':sources['exact_source_job_ids'],'source_contract':sources['source_contract'],'grid_contract':final['grid_contract']}
    for s,(task,backbone) in enumerate(SETTINGS):
        check_time(deadline);key=task+'|'+backbone
        result['head_quality'][key]=read_json(heads[s][0]/'READOUT.json')['quality']
        result['termination_reasons'][key]={r['root_id']:r['reasons'] for r in accepted if r['setting']==s}
    for proof,out,usage,physical,actual in parents:
        check_time(deadline);task=proof['task'];n=proof['candidate_count'];key=proof['root_id']+'|'+proof['backbone']
        source=Path(c['source_runs'][task])/'tasks'/(task+'-'+str(proof['root_index']).zfill(3))/'output'
        coords=load_array(source/'evidence/coordinates.npy');goal=coords[44];local=[]
        for candidate in range(n):
            check_time(deadline);ends=[]
            for draw in (0,1):
                branch=read_json(out/'evaluation'/(str(candidate)+'-'+str(draw))/'BRANCH.json')
                ends.append(native_distances(task,branch['events'][-1]['coordinates'],goal))
            local.append(ends)
        result['local_task_distances'][key]={'source':native_distances(task,coords[20],goal),'candidate_final_two_draws':local,
            'definition':'native endpoint threshold-normalized distances; descriptive only, not success replacement'}
        predicted=load_array(out/'predicted.npy').astype(np.float64)
        realized=load_array(out/'realized.npy').astype(np.float64);costs=load_array(out/'costs.npy')
        result['feature_prediction_diagnostics'][key]={
            'MSE_by_retained_sampling_position':np.mean(np.square(predicted-realized),axis=tuple([0]+list(range(2,predicted.ndim)))).tolist(),
            'within_bank_S0_pairwise_rank_agreement':float(np.mean(np.equal(
                np.sign(costs[0,:,None]-costs[0,None,:]),np.sign(costs[2,:,None]-costs[2,None,:])))),
            'within_backbone_only_no_cross_latent_unit_comparison':True}
    acceptance={'status':'ALL120_SOURCES_6_RETAINED_FITS_4_ACTIVE_HEADS_128_PARENTS_INDEPENDENTLY_ACCEPTED',
                'parent_output_seals':{r['root_id']+'|'+r['backbone']:r['output_seal'] for r in accepted},
                'active_head_seals':{str(k):v[1] for k,v in heads.items()},'retained_head_proofs':head_proofs,
                'source_acceptance':c['source_acceptance'],'contract_sha256':expected,
                'GPU_charged_seconds':accounting['GPU_charged_seconds'],'CPU_history':cpu,'all_attempt_usage':resource,
                'publication_requires_final_SSD_whole_and_every_member_verification':True}
    check_time(deadline);return result,acceptance


def compare_payloads(actual_result,actual_acceptance,expected_result,expected_acceptance):
    # Canonical bytes, not Python's True==1/False==0 equality, and no tolerance
    # or best-effort field selection. Missing/extra/changed/nonfinite data stops.
    if canonical(actual_result)!=canonical(expected_result) or canonical(actual_acceptance)!=canonical(expected_acceptance):
        raise ValueError('independent complete fixed-results/acceptance reconstruction disagrees')


def validate_complete(contract,expected,taskdir,deadline):
    """Future controller only: original source reacceptance and full comparison.

    This function supplies no authority, submission, retries or result printing.
    Final source/publication/SSD/runtime/root/allocation gates remain the caller's
    responsibility and cannot be replaced by the receipt returned here.
    """
    check_time(deadline);valid_identity({'bytes':0,'sha256':expected},0)
    contract=Path(contract);taskdir=Path(taskdir)
    c=bound_json(contract,{'bytes':contract.lstat().st_size,'sha256':expected},1000000,deadline)
    final=authorization(c,expected,contract,taskdir)
    historical=authenticate_usage(final['historical_usage_receipt']['path'],final['historical_usage_receipt']['identity'],deadline)
    declared=final['all_allocations_terminal']
    valid_identity(declared,1000000)
    allocations=bound_json(taskdir/'controls/ALL-ALLOCATIONS-TERMINAL.json',declared,1000000,deadline)
    accounting=reconcile(allocations['scheduler'],final['grid_dispatch'],
                         {int(k):v for k,v in allocations['technical_raw_ids'].items()},
                         {int(k):v for k,v in allocations['grid_raw_ids'].items()})
    if canonical(accounting)!=canonical(allocations['reconciled']):raise ValueError('independent complete138 failure-inclusive allocations')
    check_time(deadline);sources=independently_accept_sources(c);cpu=cpu_history(sources)
    check_time(deadline);heads,head_proofs=independently_accept_heads(c)
    check_time(deadline);parents=independently_accept_parents(c,sources,heads)
    resource=total(parents,head_proofs,c['compiled_physics']['n_sub_steps'])
    result,acceptance=reconstruct(c,expected,final,sources,heads,head_proofs,parents,accounting,cpu,resource,deadline)
    ctl_path=taskdir/'controls/ACCEPTED.json';ctl_identity=identity(ctl_path)
    ctl=bound_json(ctl_path,ctl_identity,1000000,deadline)
    if ctl.get('accepted') is not True or ctl.get('phase')!='analysis' or (ctl.get('source_roots'),ctl.get('retained_fits'),ctl.get('active_heads'),ctl.get('diagnostic_parents'))!=(120,6,4,128):
        raise ValueError('first analysis complete-control schema, not an independent proof by itself')
    output=taskdir/'output';authenticate(output,ctl['output_seal'],39000000)
    actual=bound_json(output/'RESULTS.json',identity(output/'RESULTS.json'),38000000,deadline)
    actual_acceptance=bound_json(output/'ACCEPTANCE.json',identity(output/'ACCEPTANCE.json'),1000000,deadline)
    compare_payloads(actual,actual_acceptance,result,acceptance)
    authenticate(output,ctl['output_seal'],39000000)
    if identity(ctl_path)!=ctl_identity:raise ValueError('analysis accepted control changed during independent validation')
    check_time(deadline)
    return {'status':'COMPLETE_ANALYSIS_INDEPENDENTLY_RECONSTRUCTED_PENDING_ARCHIVE_AND_FINAL_SSD',
            'contract_sha256':expected,'analysis_output_seal':ctl['output_seal'],'validator_source':identity(__file__),
            'sources':120,'retained_fits':6,'active_heads':4,'parents':128,'allocation_attempts':138,
            'historical_evidence_reauthentication':historical,'scientific_values_emitted':False,
            'research_model_simulator_fit_source_generation_calls':0,'parent_publication_authorized':False,'final_gate_ready':False}
