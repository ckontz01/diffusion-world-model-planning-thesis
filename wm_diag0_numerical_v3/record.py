"""Compact preparation/test/accounting receipt, no scientific data access."""
import ast,json
from .common import *
from .operations import STAGE,OBSERVE,TEST,RECONCILE
from .prepare import additions

def main():
    from wm_diag0_native_v3.common import DOC as PREP
    local=json.loads((PREP/'LOCAL-NUMV3LOCAL001.json').read_text())
    artificial=json.loads((DOC/'TEST-ONE.json').read_text())
    if local['returncode'] or artificial['returncode']:raise ValueError('artificial tests must pass')
    for code in (STAGE,OBSERVE,TEST,RECONCILE):ast.parse(code,feature_version=(3,6))
    frozen=json.loads((DOC/'VALIDATION-CONTRACT.json').read_text())
    for n,b in additions().items():
        if __import__('hashlib').sha256(b).hexdigest()!=frozen['staged_members'][n]['sha256']:raise ValueError('freeze')
    rows=[json.loads(p.read_text()) for p in PREP.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    measured=sum(r['elapsed_seconds'] for r in rows)
    write_new(DOC/'PREPARATION-CHECK-001.json',{
        'status':'ARTIFICIAL_TESTS_AND_FROZEN_SOURCE_CHECKED','local_test':local,
        'artificial_cluster_test':identity(DOC/'TEST-ONE.json'),'research_checkpoints_in_tests':0,
        'remote_control_python36_syntax_passed':True,'contract':identity(DOC/'VALIDATION-CONTRACT.json'),
        'nonrefundable_preparation_charge_seconds':14104.10301460012,'preparation_cap_seconds':14400,
        'current_measured_operations_seconds_within_already_charged_continuation':measured,
        'remaining_measured_operation_ceiling_seconds':1700-measured,
        'remaining_unreserved_preparation_seconds':295.89698539988,
        'full_future_GPU_reserved_seconds':457629,'full_future_CPU_reserved_seconds':6836,
        'full_future_live_reserved_bytes':12882899989,'future_scientific_parents':127,
        'canonical_reference_is_not_uncached_equivalence':True,'campaign_dispatch_disabled':True,
        'independent_validator_limit':'schema, exact saved members, tensor identities, workload, decision consistency; unsaved role/reference tensor comparisons execute in worker through separate model-independent numpy checker',
        'no_claim_artificial_tests_validate_research_weights':True})
    print(json.dumps({'status':'PREPARATION_RECEIPT_CREATED','measured_seconds':measured}))

if __name__=='__main__':main()
