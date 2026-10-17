"""Once-only mechanical derivation; preserve every tested predecessor unchanged."""
import ast,hashlib,json
from pathlib import Path
from .common import ROOT,DOC,identity,write_new

def derive(old,new,edits):
    source=ROOT/old;original=source.read_text(encoding='utf8');text=original
    for before,after in edits:
        if text.count(before)!=1:raise ValueError('exact unique derivation preimage: '+old+' '+before[:70])
        text=text.replace(before,after)
    ast.parse(text,feature_version=(3,6));raw=text.encode('utf8')
    target=ROOT/new
    with target.open('xb') as f:f.write(raw)
    return {'original':identity(source),'derived':identity(target),'edits':len(edits)}

def main():
    result={}
    old='wm_diag0_rc1_final_v1/'
    new='wm_diag0_rc1_close_v1/'
    result['suppliers']=derive(old+'suppliers.py',new+'suppliers.py',[
      ("    return Path(c['run'])/'tasks'/('grid-'+str(setting*31+root_index-1)),None",
       "    from wm_diag0_rc1_final_v2.recovery_suppliers_v1 import parent_location as recovered\n    return recovered(c,setting,root_index)")])
    before="    accounting=reconcile(accounting_input['scheduler'],final['grid_dispatch'],{int(k):v for k,v in accounting_input['technical_raw_ids'].items()},{int(k):v for k,v in accounting_input['grid_raw_ids'].items()})"
    result['analysis']=derive(old+'analysis.py',new+'analysis.py',[
      ('from .ledger import reconcile','from .terminal import reconcile'),
      (before,"    accounting=reconcile(c,accounting_input)"),
      ("    if accounting!=accounting_input['reconciled']:raise ValueError('independent failure-inclusive scheduler charge recomputation')",
       "    if accounting!=accounting_input['reconciled']:raise ValueError('independent failure-inclusive scheduler charge recomputation')\n    from wm_diag0_rc1_final_v2.recovery_suppliers_v1 import authenticate_terminal\n    import time\n    authenticate_terminal(c,taskdir/'controls/ALL-ALLOCATIONS-TERMINAL.json',final['all_allocations_terminal'],time.monotonic()+120)")])
    before="    accounting=reconcile(allocations['scheduler'],final['grid_dispatch'],\n                         {int(k):v for k,v in allocations['technical_raw_ids'].items()},\n                         {int(k):v for k,v in allocations['grid_raw_ids'].items()})"
    result['validator']=derive('wm_diag0_rc1_final_v2/analysis_validate_v1.py',new+'analysis_validate.py',[
      ('from wm_diag0_rc1_final_v1.analysis import','from .analysis import'),
      ('from wm_diag0_rc1_final_v1.suppliers import','from .suppliers import'),
      ('from wm_diag0_rc1_final_v1.usage import','from .usage import'),
      ('from wm_diag0_rc1_final_v1.ledger import reconcile','from .terminal import reconcile'),
      ('from .archive_v2 import','from wm_diag0_rc1_final_v2.archive_v2 import'),
      ('from .evidence_auth_v1 import','from wm_diag0_rc1_final_v2.evidence_auth_v1 import'),
      (before,"    from wm_diag0_rc1_final_v2.recovery_suppliers_v1 import authenticate_terminal\n    authenticate_terminal(c,taskdir/'controls/ALL-ALLOCATIONS-TERMINAL.json',declared,deadline)\n    accounting=reconcile(c,allocations)"),
      ('independent complete138 failure-inclusive allocations','independent complete139 failure-inclusive allocations'),
      ("'allocation_attempts':138","'allocation_attempts':139")])
    result['closure']=derive('wm_diag0_rc1_final_v2/analysis_closure_v1.py',new+'analysis_closure.py',[
      ('from .archive_v2 import','from wm_diag0_rc1_final_v2.archive_v2 import'),
      ('from .evidence_auth_v1 import','from wm_diag0_rc1_final_v2.evidence_auth_v1 import'),
      ('from .cpu_workflow_v1 import','from wm_diag0_rc1_final_v2.cpu_workflow_v1 import'),
      ("VALIDATOR='wm_diag0_rc1_final_v2/analysis_validate_v1.py'","VALIDATOR='wm_diag0_rc1_close_v1/analysis_validate.py'"),
      ("'allocation_attempts':138","'allocation_attempts':139")])
    write_new(DOC/'DERIVATION-001.json',{'status':'NEW_RECOVERY_AWARE_DERIVED_SOURCE_NOT_FROZEN_OR_EXECUTION_AUTHORITY','sources':result})
    print(json.dumps({'status':'DERIVED_FOUR_RECOVERY_AWARE_MODULES','predecessors_edited':False}))

if __name__=='__main__':main()
