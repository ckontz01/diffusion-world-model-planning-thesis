"""Independent full saved forecast comparison; no model imports or forwards."""
import json,sys
from pathlib import Path
from wm_diag0_native_v3.store import authenticate,load_array,unique
from wm_diag0_numerical_v3.metrics import compare
from wm_diag0.core import array_id
from .common import EXPECTED_GATE_USAGE,CONTEXT,REPRESENTATION,identity,write_new
from .decision import decision

def validate(root,expected):
    root=Path(root);cp=root/'source/RC1-CONTRACT.json'
    if identity(cp)['sha256']!=expected:raise ValueError('frozen contract')
    c=json.loads(cp.read_text(),object_pairs_hook=unique);task=root/'tasks/rc1-gate'
    seal=json.loads((task/'controls/OUTPUT-SEAL.json').read_text(),object_pairs_hook=unique)
    authenticate(task/'output',seal,26_000_000,{'reference.npy','RC1-GATE.json'})
    r=json.loads((task/'output/RC1-GATE.json').read_text(),object_pairs_hook=unique)
    if r['contract_sha256']!=expected or r['actual_usage']!=EXPECTED_GATE_USAGE or r['representation']!=REPRESENTATION:raise ValueError('scope/workload')
    if (r['rtol'],r['atol'])!=(2**-6,2**-8) or any(r[k] is not False for k in ('tolerances_changed','efficacy_inspected','campaign_resumed')):
        raise ValueError('scope boundary')
    if (r['old_uncached_PushT'],r['old_uncached_Reacher'])!=('FAILED','UNTESTED'):raise ValueError('preserve historical status')
    v3=Path(c['rc1']['V3_run'])/'tasks/numerical-validation/output'
    authenticate(v3,c['rc1']['V3_output_seal'],26_000_000,{'predicted.npy','goal.npy','VALIDATION.json'})
    if identity(v3/'VALIDATION.json')!=c['rc1']['V3_report']:raise ValueError('old report supplier')
    prior=json.loads((v3/'VALIDATION.json').read_text(),object_pairs_hook=unique)['conditional']
    p=load_array(v3/'predicted.npy',(16,5,196,384),['<f4'],25_000_000)
    ref=load_array(task/'output/reference.npy',(16,5,196,384),['<f4'],25_000_000)
    q=r['reference'];metric=compare(p,ref)
    if q['forecast']!=metric or q['production_forecast_supplier_id']!=array_id(p):raise ValueError('independent saved full forecast comparison')
    for k,old in (('bank_id','bank_id'),('candidate_ids','candidate_ids'),('source_RGB_id','source_RGB_id'),('goal_RGB_id','goal_RGB_id'),('goal_id','goal_id')):
        if q[k]!=prior[old]:raise ValueError('retained supplier binding')
    if q['source_binding_exact']!=(q['source_cache_id']==prior['source_cache']['left_id']) or q['goal_binding_exact']!=(q['pointwise_goal_id']==prior['goal_id']) or q['terminal_cost_identity_exact']!=(q['terminal_cost_id']==prior['terminal_cost']['left_id']):
        raise ValueError('original numerical identities')
    if q['reference_boundary_calls']!=1 or q['reused_not_newly_computed'] is not True or q['CEM_repeated'] is not False:raise ValueError('reference independence/reuse')
    sa=json.loads((Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json').read_text())
    for t in ('pusht','reacher'):
        if r['source_seals'][t]!=sa['source_seals'][t+'-000'] or set(r['roles'][t]['input_ids'])!={str(i) for i in CONTEXT}:raise ValueError('source/role bindings')
    flags=decision(r)
    if any(r[k]!=v for k,v in flags.items()):raise ValueError('independent decision')
    status='RC1_GATE_PASSED_PENDING_PRO' if flags['all_RC1_checks_passed'] else 'RC1_GATE_FAILED_CAMPAIGN_STOPPED'
    if r['status']!=status:raise ValueError('status')
    return {'status':status,'output_seal':seal,'report_identity':identity(task/'output/RC1-GATE.json'),
        'actual_usage':EXPECTED_GATE_USAGE,'saved_full_forecast_independently_recomputed':True,
        'unsaved_role_arrays_not_later_recomputed':True,'campaign_resumed':False,**flags}

def main():
    root=Path(sys.argv[1]);row=validate(root,sys.argv[2]);write_new(root/'tasks/rc1-gate/controls/VALIDATED.json',row);print(json.dumps(row))

if __name__=='__main__':main()
