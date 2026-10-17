"""Forecast-driven metadata-only preservation update; science stays byte-exact."""
import json
from .common import ROOT,DOC,write_new
from .build import derive
def main():
    p='wm_diag0_rc1_close_v1/';made={}
    made['preparation']=derive('wm_diag0_rc1_final_v2/preparation_binding_v1.py',p+'preparation_binding_v2.py',[
        ('actual)+80000000','actual)+110000000'),
        ("'remaining_auxiliary_all_copies_reserved':80000000","'remaining_auxiliary_all_copies_reserved':110000000"),
        ("PREPARATION-MEASUREMENT-001.json","PREPARATION-MEASUREMENT-002.json"),
        ("PREPARATION-COPIES-001.json","PREPARATION-COPIES-002.json")])
    made['budget']=derive('wm_diag0_rc1_final_v2/preservation_budget_v1.py',p+'preservation_budget_v2.py',[
        ('from .archive_v2 import','from wm_diag0_rc1_final_v2.archive_v2 import'),
        ('PORTABLE_LIMIT=12000000','PORTABLE_LIMIT=20000000'),
        ('SOURCE_DOC_BUNDLE_LIMIT=4500000','SOURCE_DOC_BUNDLE_LIMIT=6000000'),
        ('SMALL_SOURCE_PACKAGES_ALL_COPIES_LIMIT=2200000','SMALL_SOURCE_PACKAGES_ALL_COPIES_LIMIT=10000000'),
        ("total_aux!=63928640 or total_aux>64000000","total_aux!=93728640 or total_aux+10000000>110000000"),
        ('+64000000+4000000','+110000000+5000000'),
        ("'final_artificial_whole_root_reservation_bytes':4000000,'all_new_auxiliary_logical_copy_reservation_bytes':64000000","'final_artificial_whole_root_reservation_bytes':5000000,'all_new_auxiliary_logical_copy_reservation_bytes':110000000"),
        ("'locked_auxiliary_margin_bytes':71360","'locked_auxiliary_margin_bytes':6271360")])
    made['pipeline']=derive(p+'archive_pipeline.py',p+'archive_pipeline_v2.py',[
        ('from .preservation_budget import','from .preservation_budget_v2 import')])
    made['archive']=derive(p+'archive_operation_v2.py',p+'archive_operation_v3.py',[
        ('from .archive_pipeline import','from .archive_pipeline_v2 import'),
        ("PREPARATION_PRODUCER='wm_diag0_rc1_final_v2/preparation_binding_v1.py'","PREPARATION_PRODUCER='wm_diag0_rc1_close_v1/preparation_binding_v2.py'"),
        ("'wm_diag0_rc1_close_v1.archive_operation_v2'","'wm_diag0_rc1_close_v1.archive_operation_v3'")])
    made['workflow']=derive(p+'workflow_v2.py',p+'workflow_v3.py',[
        ('from .archive_pipeline import','from .archive_pipeline_v2 import'),
        ('from .archive_operation_v2 import','from .archive_operation_v3 import')])
    made['driver']=derive(p+'driver_v2.py',p+'driver_v3.py',[
        ('from .workflow_v2 import','from .workflow_v3 import'),
        ("proof['portable_inventory'],12000000,end","proof['portable_inventory'],20000000,end")])
    write_new(DOC/'MANIFEST-FORECAST-DISPOSITION-003.json',{'status':'COMPLETE_ACTUAL_INVENTORY_FORECAST_REQUIRES_NEW_PRESERVATION_METADATA_ADAPTER',
        'actual_existing_portable_bytes':13320770,'actual_existing_manifest_bytes':15198405,'new_portable_cap':20000000,
        'unchanged_format_manifest_cap':20000000,'complete_copy_auxiliary_reservation':110000000,
        'new_source':made,'scientific_analysis_or_estimator_changed':False,'no_CPU_allocation_started':True})
    print(json.dumps({'status':'FORECAST_DRIVEN_PRESERVATION_V3_DERIVED','science_unchanged':True}))
if __name__=='__main__':main()
