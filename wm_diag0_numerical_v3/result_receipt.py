"""Publish numerical/control metadata only; no forecast or efficacy decoding."""
import json
from .common import *

def main():
    p=DOC/'OBSERVE-TWO.json';z=json.loads(p.read_text());r=z['report']
    if z['queue'] or z['scheduler'].strip()!='317173|COMPLETED|0:0|19|4|gpu09':raise ValueError('one exact terminal allocation')
    if z['result']['status']!='NUMERICAL_GATE_FAILED_CAMPAIGN_STOPPED' or r['all_numerical_checks_passed']:raise ValueError('preserved numerical STOP')
    if r['actual_usage']!=EXPECTED_USAGE:raise ValueError('exact complete workload')
    from .metrics import decision
    if decision(r)!={k:r[k] for k in decision(r)}:raise ValueError('independent metadata decision')
    # Report-only deterministic encoding binds local metadata to remote report bytes.
    raw=json.dumps(r,sort_keys=True,indent=2,allow_nan=False).encode()
    if {'bytes':len(raw),'sha256':__import__('hashlib').sha256(raw).hexdigest()}!=z['result']['report_identity']:raise ValueError('authenticated report bytes')
    with (DOC/'VALIDATION-REPORT-001.json').open('xb') as f:f.write(raw)
    from wm_diag0_native_v3.common import DOC as PREP
    measured=sum(json.loads(q.read_text())['elapsed_seconds'] for q in PREP.glob('LOCAL-*.json') if not q.name.endswith('.started.json'))
    row={'status':'VALIDATION_COMPLETE_REQUIRED_ROLE_CHECK_FAILED','job_id':'317173','GPU_allocation_seconds':19,
         'GPU_all_attempts_charged_seconds':249+19,'CPU_all_attempts_charged_seconds':1436,
         'full_future_GPU_using_actual_charge_seconds':249+19+127*3600,'approved_full_future_GPU_reservation_seconds':457629,
         'new_attempts':1,'automatic_retries':0,'campaign_resumed':False,'report':identity(DOC/'VALIDATION-REPORT-001.json'),
         'observation':identity(p),'output_seal':z['result']['output_seal'],'actual_usage':EXPECTED_USAGE,
         'source_commit':'7d6ae7ff174d64674f64ec83f294e2a41ccb76f6','contract':identity(DOC/'VALIDATION-CONTRACT.json'),
         'SSD_source_package_receipt':identity(DOC/'SSD-VERIFIED-001.json'),
         'nonrefundable_preparation_charge_seconds':14104.10301460012,'preparation_cap_seconds':14400,
         'measured_operations_within_existing_charge_seconds':measured,
         'remaining_measured_operation_allowance_seconds':1700-measured,
         'original_uncached_PushT':'FAILED','original_uncached_Reacher':'UNTESTED',
         'Pro_review_pending':True,'new_scientific_inference_after_validation':False,
         'efficacy_or_head_outputs_inspected':False}
    write_new(DOC/'RESULT-RECEIPT-001.json',row)
    print(json.dumps(row))

if __name__=='__main__':main()
