"""Local source-only diagnosis of an unused draft identity-size constant."""
import json
from . import cpu_schedule_v1 as s
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def main():
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    tested=json.loads((doc/'ARTIFICIAL-CPU-SCHEDULE-001.json').read_text())
    if identity(ROOT/'wm_diag0_rc1_final_v2/cpu_schedule_v1.py')!=tested['source']['cpu_schedule_v1.py']:raise ValueError('exact first tested draft source retained')
    actual=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if actual!={'bytes':8269,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}:raise ValueError('original tested V2 cleanup source unchanged')
    if s.CPU_V2['sha256']!=actual['sha256'] or s.CPU_V2['bytes']!=10254:raise ValueError('exact diagnosed unused metadata constant')
    result={'status':'UNUSED_UNFROZEN_CPU_SCHEDULE_V1_SIZE_CONSTANT_INCORRECT_NO_RESEARCH_FAULT',
            'preserved_tested_draft':tested['source']['cpu_schedule_v1.py'],'declared_unused_size':s.CPU_V2['bytes'],
            'actual_original_V2_cleanup_identity':actual,
            'scope':'draft validator tested only correctSHA; unused bytes constant was wrong. No production closure/allocation used it.',
            'required':'new separately versioned strict full-identity adapter; preserve V1 source/test unchanged',
            'research_job_or_controller_changed':False,'GPU_or_CPU_research_allocation_or_scientific_values_read':False,
            'actual_V2_cleanup_source_changed':False,'final_gate_ready':False}
    write_new(doc/'CPU-SCHEDULE-V1-DIAGNOSIS-001.json',result,limit=16000)
    print(json.dumps({'status':result['status'],'actual_source_bytes':8269,'research_calls':0}))


if __name__=='__main__':main()
