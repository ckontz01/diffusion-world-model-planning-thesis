"""Separate pure-native controller helpers from scientific NumPy child imports."""
import ast,inspect,json
from .common import ROOT,DOC,identity,write_new

def create(name,header,function):
    raw=(header+'\n'+inspect.getsource(function)).encode();ast.parse(raw.decode(),feature_version=(3,6))
    with (ROOT/'wm_diag0_rc1_close_v1'/name).open('xb') as f:f.write(raw)

def main():
    from wm_diag0_rc1_final_v2.cpu_entry_guard_v1 import source_closure
    from .analysis import authorization
    from wm_diag0_rc1_final_v2.cpu_workflow_v1 import identity as closed_identity
    create('entry_source.py','import os,stat,hashlib\nfrom pathlib import Path\nfrom wm_diag0_rc1_final_v2.archive_v2 import canonical,check_time\nfrom wm_diag0_rc1_final_v2.evidence_auth_v1 import bound_bytes\nfrom wm_diag0_rc1_final_v2.inventory_v3 import safe_name',source_closure)
    create('authorization.py','import json\nfrom pathlib import Path\nfrom wm_diag0_rc1_grid_v1.common import identity\nfrom wm_diag0_rc1_final_v1.usage import HISTORICAL_DINO,HISTORICAL_LEWM',authorization)
    create('closed_identity.py','import hashlib\nfrom pathlib import Path\nfrom wm_diag0_rc1_final_v2.evidence_auth_v1 import ordinary\nfrom wm_diag0_rc1_final_v2.archive_v2 import check_time',closed_identity)
    # These NEW adapters have not been frozen/published/executed. Their pure
    # helper imports must not accidentally load NumPy on login/native Python3.6.
    for name in ('analysis_closure.py','workflow.py'):
        p=ROOT/'wm_diag0_rc1_close_v1'/name;text=p.read_text()
        before='from wm_diag0_rc1_final_v2.cpu_workflow_v1 import identity'
        if text.count(before)!=1:raise ValueError('exact unused new adapter import')
        text=text.replace(before,'from .closed_identity import identity')
        p.write_text(text,encoding='utf8')
    write_new(DOC/'NATIVE-CONTROLLER-IMPORTS-001.json',{'status':'NATIVE_CONTROLLER_HELPERS_SEPARATED_FROM_NUMPY_CHILD','prior_frozen_sources_edited':False,
        'pure_helpers':{name:identity(ROOT/'wm_diag0_rc1_close_v1'/name) for name in ('entry_source.py','authorization.py','closed_identity.py')},
        'actual_analysis_executed':False})
    print(json.dumps({'status':'NATIVE_HELPERS_DERIVED'}))
if __name__=='__main__':main()
