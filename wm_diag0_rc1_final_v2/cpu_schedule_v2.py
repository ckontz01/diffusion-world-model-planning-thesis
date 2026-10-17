"""Strict full-identity draft adapter; V1 source/test retained unchanged.

V1's unused declared CPU_V2 byte count was incorrect; its SHA check was correct.
Future production integration must use this adapter, never consume V1's constant.
No allocation/analysis authority or process/submission entry is provided here.
"""
from . import cpu_schedule_v1 as v1
from .archive_v2 import canonical

CPU_V2={'bytes':8269,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}
PHASES=v1.PHASES
PhaseClock=v1.PhaseClock
prospective_analysis_argv=v1.prospective_analysis_argv
prospective_cpu_environment=v1.prospective_cpu_environment


def validate_draft(grid,proposed,layout):
    actual=proposed.get('staged_members',{}).get('wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if canonical(actual)!=canonical(CPU_V2):raise ValueError('exact tested V2 cleanup bytes AND SHA256; no float/bool/coerced identity')
    result=v1.validate_draft(grid,proposed,layout)
    result['strict_original_V2_cleanup_identity']=CPU_V2
    result['preserved_V1_unused_size_constant_consumed']=False
    return result
