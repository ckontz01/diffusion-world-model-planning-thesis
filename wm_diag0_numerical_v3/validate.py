"""Independent bounded output/decision validation; no checkpoint or forward."""
import json,sys
from pathlib import Path
from wm_diag0_native_v3.store import authenticate,load_array,unique
from wm_diag0.core import array_id
from .common import EXPECTED_USAGE,COMMON,CONTEXT,identity,write_new
from .metrics import decision

def validate(root,expected):
    root=Path(root);cp=root/'source/VALIDATION-CONTRACT.json'
    if identity(cp)['sha256']!=expected:raise ValueError('frozen validation contract')
    c=json.loads(cp.read_text(),object_pairs_hook=unique)
    task=root/'tasks/numerical-validation';seal=json.loads((task/'controls/OUTPUT-SEAL.json').read_text(),object_pairs_hook=unique)
    authenticate(task/'output',seal,26_000_000,{'predicted.npy','goal.npy','VALIDATION.json'})
    report=json.loads((task/'output/VALIDATION.json').read_text(),object_pairs_hook=unique)
    if report['contract_sha256']!=expected or report['actual_usage']!=EXPECTED_USAGE:raise ValueError('exact contract/workload')
    if (report['rtol'],report['atol'])!=(2**-6,2**-8):raise ValueError('unchanged tolerances')
    for key in ('tolerances_changed','production_changed','campaign_resumption_authorized','efficacy_or_readout_outputs_inspected'):
        if report[key] is not False:raise ValueError('scope boundary')
    if (report['old_uncached_PushT'],report['old_uncached_Reacher'])!=('FAILED','UNTESTED'):raise ValueError('preserved historical failures')
    for taskname in ('pusht','reacher'):
        if set(report['roles'][taskname]['input_ids'])!={str(i) for i in CONTEXT}:raise ValueError('fixed common/context identities')
        sa=json.loads((Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json').read_text())
        if report['source_seals'][taskname]!=sa['source_seals'][taskname+'-000']:raise ValueError('source seal binding')
    q=report['conditional']
    p=load_array(task/'output/predicted.npy',(16,5,196,384),['<f4'],25_000_000)
    g=load_array(task/'output/goal.npy',(196,384),['<f4'],400_000)
    if array_id(p)!=q['predicted_id'] or q['forecast']['left_id']!=array_id(p) or array_id(g)!=q['goal_id'] or q['goal']['left_id']!=array_id(g):raise ValueError('saved full feature identities')
    if len(q['candidate_ids'])!=16 or len(set(q['candidate_ids']))!=16 or q['reference_encode_obs_calls']!=1:raise ValueError('fixed reference bank')
    flags=decision(report)
    if any(report[k]!=v for k,v in flags.items()):raise ValueError('independent numerical decision')
    status='NUMERICAL_CHECKS_PASSED_PENDING_PRO' if flags['all_numerical_checks_passed'] else 'NUMERICAL_GATE_FAILED_CAMPAIGN_STOPPED'
    if report['status']!=status:raise ValueError('independent status')
    return {'status':status,'output_seal':seal,'report_identity':identity(task/'output/VALIDATION.json'),
            'actual_usage':EXPECTED_USAGE,'campaign_resumed':False,**flags}

def main():
    root=Path(sys.argv[1]);row=validate(root,sys.argv[2]);write_new(root/'tasks/numerical-validation/controls/VALIDATED.json',row)
    print(json.dumps(row))

if __name__=='__main__':main()
