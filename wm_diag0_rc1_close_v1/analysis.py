"""Complete-study supplier-aware CPU analysis, disabled until final contract.

The original fixed paired estimator, bootstrap, native distances and diagnostics
are retained. No main/partial-analysis command is authorized by the grid contract.
"""
import json,sys
from pathlib import Path
import numpy as np
from wm_diag0_rc1_grid_v1.common import SETTINGS,identity,write_new
from wm_diag0_campaign_v4.analysis import pack,native_distances
from wm_diag0_native_v3.store import load_array,seal
from .suppliers import independently_accept_sources,independently_accept_heads,independently_accept_parents
from .usage import total,cpu_history,HISTORICAL_DINO,HISTORICAL_LEWM
from .terminal import reconcile

LIMITATIONS=[
 'third-party DINO predictor bundles; training-time encoder checkout unverified',
 'accepted pinned DINOv2 encoder is prospective implementation definition, not historical equivalence',
 'readout coordinate supervision is additional training data; no tuning or historical-origin reconstruction',
 'raw Reacher qpos may be visually winding-ambiguous; no hidden winding correction',
 'descriptive paired bootstrap, not confirmatory/multiplicity-controlled or architectural causal attribution',
 'native success under fixed50-action tail budget is not global solvability; all-bank failure is not unreachability',
 'hindsight maximum is optimistic tested-bank opportunity; deterministic draws add no independent parents',
 'one failed source persistence attempt retained and charged; same-seed four-array identity required on retry',
 'DINO RC1 is pointwise B1/T1 on pinned bytes/runtime/transforms; LeWM retains original acceptance scope and is not equally representation-controlled',
 'original uncached PushT reference FAILED; original uncached Reacher reference UNTESTED; conditional/full RC1 numerical evidence does not rewrite those historical facts',
 'unsaved original role-array audit limitation retained; saved full forecast/goal reference identities and exact checks do not restore unsaved role arrays',
 'old DINO heads are retained inactive; exactly two new fixed pointwise DINO heads are active, without validation tuning',
 'first-call timing screens are not worst-case whole-parent timing guarantees; finite per-allocation work and preservation bounds remain enforced']


def paired(accepted):
    if len(accepted)!=128 or {(r['setting'],r['root_index']) for r in accepted}!={(s,i) for s in range(4) for i in range(32)}:raise ValueError('complete exact128 before any aggregate')
    for r in accepted:
        if not r['accepted'] or (r['task'],r['backbone'])!=SETTINGS[r['setting']]:raise ValueError('independently accepted fixed task/backbone')
    settings={task+'|'+backbone:pack([r for r in accepted if r['setting']==s]) for s,(task,backbone) in enumerate(SETTINGS)}
    pooled={backbone:pack([r for r in accepted if r['backbone']==backbone]) for backbone in ('lewm','dinowm_noprop')}
    return settings,pooled


def authorization(c,expected,contract,taskdir):
    final=c.get('rc1_final',{})
    if identity(contract)['sha256']!=expected or final.get('analysis_authorized') is not True or c['gpu_stages_authorized'] or Path(taskdir)!=Path(final.get('run',''))/'tasks/analysis-0':raise PermissionError('new frozen final CPU-only contract required')
    grid=Path(c['run'])/'source/GRID-CONTRACT.json'
    if identity(grid)!=final['grid_contract'] or c['run']!=final['grid_run']:raise ValueError('actual grid science/supplier contract retained')
    receipt=Path(final['historical_usage_receipt']['path'])
    if identity(receipt)!=final['historical_usage_receipt']['identity']:raise ValueError('historical invocation/source provenance not bound')
    h=json.loads(receipt.read_text())
    if h['DINO_baseline']!=HISTORICAL_DINO or h['LeWM_baseline']!=HISTORICAL_LEWM or h.get('independently_authenticated') is not True:raise ValueError('no invented historical instrumentation')
    return final


def main():
    contract=Path(sys.argv[1]);expected=sys.argv[2];taskdir=Path(sys.argv[3]);c=json.loads(contract.read_text());final=authorization(c,expected,contract,taskdir)
    accounting_input=json.loads((taskdir/'controls/ALL-ALLOCATIONS-TERMINAL.json').read_text())
    accounting=reconcile(c,accounting_input)
    if accounting!=accounting_input['reconciled']:raise ValueError('independent failure-inclusive scheduler charge recomputation')
    from wm_diag0_rc1_final_v2.recovery_suppliers_v1 import authenticate_terminal
    import time
    authenticate_terminal(c,taskdir/'controls/ALL-ALLOCATIONS-TERMINAL.json',final['all_allocations_terminal'],time.monotonic()+120)
    sources=independently_accept_sources(c);cpu=cpu_history(sources)
    heads,head_proofs=independently_accept_heads(c);parents=independently_accept_parents(c,sources,heads)
    # No aggregate is formed before independent acceptance of every required
    # source, six retained fits, four active heads and128 logical parents.
    accepted=[r[0] for r in parents];settings,pooled=paired(accepted)
    resource=total(parents,head_proofs,c['compiled_physics']['n_sub_steps'])
    result={'study':'WM-DIAG0-A2-RC1','status':'COMPLETE_RESULTS_PENDING_FINAL_SSD_PRESERVATION','settings':settings,'pooled_by_backbone':pooled,
        'head_quality':{},'head_lineage':head_proofs,'independent_parent_count_per_backbone':64,'paired_bootstrap_seed':20261004,
        'limitations':LIMITATIONS,'termination_reasons':{},'local_task_distances':{},'feature_prediction_diagnostics':{},
        'resource_accounting':accounting,'CPU_history':cpu,'all_attempt_numerical_and_physical_usage':resource,
        'source_lineage':sources['exact_source_job_ids'],'source_contract':sources['source_contract'],'grid_contract':final['grid_contract']}
    for s,(task,backbone) in enumerate(SETTINGS):
        key=task+'|'+backbone;rows=[r for r in accepted if r['setting']==s]
        result['head_quality'][key]=json.loads((heads[s][0]/'READOUT.json').read_text())['quality']
        result['termination_reasons'][key]={r['root_id']:r['reasons'] for r in rows}
    for proof,out,usage,physical,actual in parents:
        key=proof['root_id']+'|'+proof['backbone'];task=proof['task'];n=proof['candidate_count']
        source=Path(c['source_runs'][task])/'tasks'/(task+'-'+str(proof['root_index']).zfill(3))/'output'
        coords=load_array(source/'evidence/coordinates.npy');goal=coords[44];local=[]
        for i in range(n):
            ends=[]
            for draw in (0,1):
                b=json.loads((out/'evaluation'/(str(i)+'-'+str(draw))/'BRANCH.json').read_text())
                ends.append(native_distances(task,b['events'][-1]['coordinates'],goal))
            local.append(ends)
        result['local_task_distances'][key]={'source':native_distances(task,coords[20],goal),'candidate_final_two_draws':local,
            'definition':'native endpoint threshold-normalized distances; descriptive only, not success replacement'}
        pred=load_array(out/'predicted.npy').astype(np.float64);real=load_array(out/'realized.npy').astype(np.float64);costs=load_array(out/'costs.npy')
        result['feature_prediction_diagnostics'][key]={'MSE_by_retained_sampling_position':np.mean((pred-real)**2,axis=(0,*range(2,pred.ndim))).tolist(),
            'within_bank_S0_pairwise_rank_agreement':float(np.mean(np.sign(costs[0,:,None]-costs[0,None,:])==np.sign(costs[2,:,None]-costs[2,None,:]))),
            'within_backbone_only_no_cross_latent_unit_comparison':True}
    out=taskdir/'output';out.mkdir(exist_ok=False)
    raw=json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>38000000:raise ValueError('bounded complete fixed-results output')
    with (out/'RESULTS.json').open('xb') as f:f.write(raw)
    write_new(out/'ACCEPTANCE.json',{'status':'ALL120_SOURCES_6_RETAINED_FITS_4_ACTIVE_HEADS_128_PARENTS_INDEPENDENTLY_ACCEPTED',
        'parent_output_seals':{r['root_id']+'|'+r['backbone']:r['output_seal'] for r in accepted},'active_head_seals':{str(k):v[1] for k,v in heads.items()},
        'retained_head_proofs':head_proofs,'source_acceptance':c['source_acceptance'],'contract_sha256':expected,
        'GPU_charged_seconds':accounting['GPU_charged_seconds'],'CPU_history':cpu,'all_attempt_usage':resource,
        'publication_requires_final_SSD_whole_and_every_member_verification':True})
    output_seal=seal(out,39000000)
    write_new(taskdir/'controls/ACCEPTED.json',{'accepted':True,'phase':'analysis','output_seal':output_seal,'source_roots':120,'retained_fits':6,'active_heads':4,'diagnostic_parents':128,'scientific_values_emitted_to_controls':False})
    print(json.dumps({'status':'COMPLETE_STUDY_INDEPENDENTLY_ACCEPTED_PENDING_FINAL_SSD','output_seal':output_seal,'source_roots':120,'retained_fits':6,'active_heads':4,'parents':128}))


if __name__=='__main__':main()
