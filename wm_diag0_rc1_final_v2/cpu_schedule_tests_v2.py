"""Targeted full-identity regression only; no old CPU process suite repeated."""
import ast,copy,json
from pathlib import Path
from . import cpu_schedule_v2 as s
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def main():
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    diagnosis=json.loads((doc/'CPU-SCHEDULE-V1-DIAGNOSIS-001.json').read_text())
    layout=json.loads((doc/'PRESERVATION-LAYOUT-001.json').read_text())['layout']
    grid=json.loads((ROOT/'docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json').read_text());c=copy.deepcopy(grid)
    actual=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if actual!=s.CPU_V2 or actual!=diagnosis['actual_original_V2_cleanup_identity']:raise ValueError('actual unchanged source identity independently matched')
    c['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']=actual
    c['rc1_final']={'run':layout['final_run'],'operational_root':layout['operational_root'],'archive_path':layout['archive_path'],
                    'grid_run':grid['run'],'grid_contract':s.v1.GRID,'analysis_authorized':False,
                    'allocation_seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0,'automatic_retry':False,
                    'phase_seconds':{'analysis':1800,'independent_acceptance':600,'archive':1170,'finalize':30}}
    good=s.validate_draft(grid,c,layout)
    for value in (10254,True,8269.0,8268):
        bad=copy.deepcopy(c);bad['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']['bytes']=value
        try:s.validate_draft(grid,bad,layout)
        except ValueError:pass
        else:raise AssertionError('wrong/coerced V2 cleanup size accepted')
    source={}
    for n in ('cpu_schedule_v1.py','cpu_schedule_tests_v1.py','cpu_schedule_diagnose_v1.py','cpu_schedule_v2.py','cpu_schedule_tests_v2.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    if source['cpu_schedule_v1.py']!=diagnosis['preserved_tested_draft']:raise ValueError('historical tested V1 draft preserved exactly')
    write_new(doc/'ARTIFICIAL-CPU-SCHEDULE-002.json',{'status':'STRICT_V2_CLEANUP_FULL_IDENTITY_ADAPTER_REGRESSION_PASSED',
        'source':source,'actual_cleanup_source':actual,'diagnosis':identity(doc/'CPU-SCHEDULE-V1-DIAGNOSIS-001.json'),
        'checks':['preserved V1/test source unchanged','actual8269B+13f3d73a source identity exact','10254/bool/float/offbyone size rejected before V1 delegation'],
        'future_schedule_adapter':'cpu_schedule_v2.validate_draft','old_draft_unused_wrong_size_consumed':False,
        'old_original_V2_cleanup_or_research_source_changed':False,'process_scheduler_network_or_research_calls':0,
        'real_final_CPU_analysis_archive_or_SSD_run':False,'final_gate_ready':False})
    print(json.dumps({'status':'STRICT_V2_CLEANUP_FULL_IDENTITY_ADAPTER_REGRESSION_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
