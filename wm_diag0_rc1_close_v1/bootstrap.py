"""Once-only new runner derivation; old executed runners are byte-unchanged."""
import ast,json
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
def main():
    old=ROOT/'wm_diag0_rc1_completion_v1/local_v2.py';text=old.read_text()
    before='from .common import ROOT,DOC,CAPS,raw_json,write_new,identity,reserve,owned_bytes,charge\nfrom .job import child_job'
    after='from .budget import ROOT,DOC,CAPS,raw_json,write_new,identity,reserve,owned_bytes,charge,AUTH\nfrom wm_diag0_rc1_completion_v1.job import child_job'
    if text.count(before)!=1:raise ValueError('exact previous runner preimage')
    text=text.replace(before,after)
    before="'authority':identity(DOC/'AUTHORITY.json'),"
    after="'authority':identity(DOC/'AUTHORITY.json'),'current_finalization_authority':identity(AUTH),'shared_component_envelope_not_additive_grants':True,"
    if text.count(before)!=1:raise ValueError('exact historical authority binding')
    text=text.replace(before,after)
    ast.parse(text,feature_version=(3,6));target=ROOT/'wm_diag0_rc1_close_v1/local_v3.py'
    with target.open('xb') as f:f.write(text.encode())
    write_new(DOC/'RUNNER-003.json',{'status':'NEW_SHARED_FINALIZATION_ENGINEERING_RUNNER','old_runner':identity(old),'new_runner':identity(target),
        'authority':identity(DOC/'AUTHORITY-002.json'),'old_runner_edited':False,'old_charges_refunded_or_moved':False})
    print(json.dumps({'status':'NEW_RUNNER_READY','old_runner_unchanged':True}))
if __name__=='__main__':main()
