"""Derive complete final adapters in NEW files, never edit predecessors."""
import ast,inspect,json
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .build import derive

def main():
    out={};new='wm_diag0_rc1_close_v1/'
    from wm_diag0_rc1_final_v2.preservation_layout_v1 import check_paths
    text='from pathlib import PurePosixPath\nfrom wm_diag0_rc1_final_v2.preservation_layout_v1 import absolute,beneath,FINAL\nfrom wm_diag0_rc1_final_v2.inventory_v3 import safe_name,alias_literal\n'+inspect.getsource(check_paths).replace('len(old)!=19','len(old)!=21').replace('all19 retained','all21 retained')
    with (ROOT/new/'layout.py').open('xb') as f:f.write(text.encode())
    out['layout']=identity(ROOT/new/'layout.py')
    out['pipeline']=derive('wm_diag0_rc1_final_v2/archive_pipeline_v1.py',new+'archive_pipeline.py',[
        ('from .archive_v2 import','from wm_diag0_rc1_final_v2.archive_v2 import'),
        ('from .archive_verify_v2 import','from wm_diag0_rc1_final_v2.archive_verify_v2 import'),
        ('from .root_binding_v1 import','from wm_diag0_rc1_final_v2.root_binding_v1 import'),
        ('from .preservation_budget_v1 import','from .preservation_budget import'),
        ("    original=authenticate(planned,root_paths,source_authority_sha256,deadline)","    from .parallel_binding import parallel_authenticate\n    original,_,_=parallel_authenticate(planned,root_paths,source_authority_sha256,deadline)")])
    out['archive']=derive('wm_diag0_rc1_final_v2/archive_operation_v1.py',new+'archive_operation.py',[
        ('from .archive_v2 import','from wm_diag0_rc1_final_v2.archive_v2 import'),
        ('from .archive_pipeline_v1 import','from .archive_pipeline import'),
        ('from .analysis_closure_v1 import','from .analysis_closure import'),
        ('from .cpu_entry_guard_v1 import','from .entry import'),
        ('from .evidence_auth_v1 import','from wm_diag0_rc1_final_v2.evidence_auth_v1 import'),
        ('from .preservation_layout_v1 import','from .layout import'),
        ('from .inventory_v3 import','from wm_diag0_rc1_final_v2.inventory_v3 import'),
        ('from .cpu_schedule_v2 import v1 as schedule','from . import schedule'),
        ("LAYOUT={'bytes':10618,'sha256':'0f64eb876a3f0007ae0188f4902d4d8a114548d62e0c1cef610af02d5ffc3243'}","# The final contract externally pins the new recovery-inclusive layout identity."),
        ("    if canonical(members.get(LAYOUT_MEMBER))!=canonical(LAYOUT):raise ValueError('exact source-bound complete19+final layout')\n    layout_receipt=bound_json(cp.parent/LAYOUT_MEMBER,LAYOUT,32000,deadline);layout=check_paths(layout_receipt['layout'])",
         "    layout_id=members[LAYOUT_MEMBER];valid_identity(layout_id,32000)\n    layout_receipt=bound_json(cp.parent/LAYOUT_MEMBER,layout_id,32000,deadline);layout=check_paths(layout_receipt['layout'])"),
        ("LAYOUT['sha256'],prior","layout_id['sha256'],prior"),
        ("'wm_diag0_rc1_final_v2.archive_operation_v1'","'wm_diag0_rc1_close_v1.archive_operation'")])
    out['workflow']=derive('wm_diag0_rc1_final_v2/cpu_workflow_v2.py',new+'workflow.py',[
        ('from .archive_v2 import','from wm_diag0_rc1_final_v2.archive_v2 import'),
        ('from .archive_pipeline_v1 import','from .archive_pipeline import'),
        ('from .analysis_closure_v1 import','from .analysis_closure import'),
        ('from .archive_operation_v1 import','from .archive_operation import'),
        ('from .cpu_schedule_v2 import','from .schedule import'),
        ('from .cpu_workflow_v1 import','from wm_diag0_rc1_final_v2.cpu_workflow_v1 import'),
        ('from .evidence_auth_v1 import','from wm_diag0_rc1_final_v2.evidence_auth_v1 import'),
        ('from .preservation_layout_v1 import','from .layout import'),
        ('    for p in outputs:ordinary(p.parent)',"    for p in outputs:\n        ancestor=p.parent\n        while not ancestor.exists():ancestor=ancestor.parent\n        ordinary(ancestor)")])
    write_new(DOC/'WORKFLOW-DERIVATION-001.json',{'status':'NEW_FIXED_REAL_WORKFLOW_SOURCE_DERIVED_NOT_YET_FROZEN','source':out,
       'analysis_and_second_pass_recovery_aware':True,'actual_archive_module_not_noop':True,'owned_final_output_must_be_absent_before_writer':True})
    print(json.dumps({'status':'NEW_COMPLETE_WORKFLOW_ADAPTERS_DERIVED'}))
if __name__=='__main__':main()
