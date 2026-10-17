"""Targeted pure CPU plan/deadline/argv tests, no launched child or scheduler."""
import ast,copy,json
from pathlib import Path
from . import cpu_schedule_v1 as s
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except (ValueError,PermissionError,TimeoutError):return
    raise AssertionError('required CPU draft/deadline/command rejection absent')


def main():
    doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    layout=json.loads((doc/'PRESERVATION-LAYOUT-001.json').read_text())['layout']
    grid=json.loads((ROOT/'docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json').read_text())
    c=copy.deepcopy(grid);c['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    c['rc1_final']={'run':layout['final_run'],'operational_root':layout['operational_root'],'archive_path':layout['archive_path'],
                    'grid_run':grid['run'],'grid_contract':s.GRID,'analysis_authorized':False,
                    'allocation_seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0,'automatic_retry':False,
                    'phase_seconds':{'analysis':1800,'independent_acceptance':600,'archive':1170,'finalize':30}}
    result=s.validate_draft(grid,c,layout)
    for key,value in (('analysis_authorized',True),('GPU_requested',1),('CPUs',True),('RAM_bytes',8589934593),('automatic_retry',True)):
        bad=copy.deepcopy(c);bad['rc1_final'][key]=value;reject(lambda:s.validate_draft(grid,bad,layout))
    bad=copy.deepcopy(c);bad['root_plan_sha256']='0'*64;reject(lambda:s.validate_draft(grid,bad,layout))
    bad=copy.deepcopy(c);bad['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']['sha256']='0'*64;reject(lambda:s.validate_draft(grid,bad,layout))
    phases=c['rc1_final']['phase_seconds'];clock=s.PhaseClock(100,phases)
    first=clock.claim('analysis',101)
    if first['phase_end_including_bookkeeping']!=1900 or first['work_deadline']!=1894 or first['cleanup_deadline']!=1899:raise AssertionError('entry/preflight/cleanup/bookkeeping all included')
    reject(lambda:clock.claim('analysis',102));clock.finish('analysis',1000)
    second=clock.claim('independent_acceptance',1001)
    if second['phase_end_including_bookkeeping']!=1601:raise AssertionError('earlier under-use cannot extend later600s phase')
    clock.finish('independent_acceptance',1100);clock.claim('archive',1101);clock.finish('archive',1200)
    clock.claim('finalize',1201);clock.finish('finalize',1210)
    if s.PhaseClock(100,phases).end!=3700 or clock.complete(1210)['elapsed_seconds']!=1110:raise AssertionError('one finite3600s envelope, not conversion1800')
    late=s.PhaseClock(100,phases);late.claim('analysis',101);reject(lambda:late.finish('analysis',1901))
    nofit=s.PhaseClock(100,phases);nofit.claim('analysis',101);nofit.finish('analysis',1900)
    reject(lambda:nofit.claim('independent_acceptance',1901))
    reject(lambda:s.PhaseClock(True,phases));reject(lambda:s.PhaseClock(float('nan'),phases))
    for phase in ('analysis','independent_acceptance'):
        argv=s.prospective_analysis_argv(c,layout,'a'*64,phase,2000)
        if '--nv' in argv or any(x.startswith('--gres') for x in argv) or c['venv']+'/bin/python' not in argv or '--cleanenv' not in argv:raise AssertionError('noGPU fixed existing runtime container argv')
        if not any(x==layout['study_base']+':'+layout['study_base']+':ro' for x in argv):raise AssertionError('whole research study read-only')
        if phase=='independent_acceptance' and 'INDEPENDENT-ANALYSIS-VERIFIED.json' not in s.VALIDATE_CODE:raise AssertionError('actual fixed validator function invoked, no silent no-op module')
    reject(lambda:s.prospective_analysis_argv(c,layout,'a'*64,'archive',2000))
    parent={'APPTAINERENV_UNAPPROVED':'old','SINGULARITYENV_UNAPPROVED':'old','CUDA_VISIBLE_DEVICES':'0','PATH':'unchanged'}
    env=s.prospective_cpu_environment(parent,layout['final_run']+'/source')
    if env['CUDA_VISIBLE_DEVICES']!='' or env['APPTAINERENV_CUDA_VISIBLE_DEVICES']!='' or 'APPTAINERENV_UNAPPROVED' in env or env['PATH']!='unchanged' or parent['CUDA_VISIBLE_DEVICES']!='0':raise AssertionError('copied CPU-only clean environment, no user environment mutation')
    source={}
    for n in ('cpu_schedule_v1.py','cpu_schedule_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    ast.parse(s.VALIDATE_CODE,feature_version=(3,6))
    write_new(doc/'ARTIFICIAL-CPU-SCHEDULE-001.json',{'status':'V2_CPU_DRAFT_FINITE_PHASE_AND_READONLY_ARGV_ARTIFICIAL_PASSED','source':source,
        'checks':['same executed grid science/source keys','mandatory testedV2cleanup','CPU3600/fourCPU/8GiB/noGPU/noRetry','draft cannot authorize execution',
                  'entry authentication and own5s cleanup+1s bookkeeping inside phase','earlier under-use not transferred to later phase','all future maxima+final30s reserved',
                  'fixed existing analysis and real independent-validator argv','whole study read-only/noGPU/offline/copied environment'],
        'prospective_phase_seconds':phases,'phase_split_frozen_or_whole_study_timing_guarantee':False,
        'real_supervisor_archive_entry_stage_gates_submission_or_terminal_CPU_authentication_complete':False,
        'processes_or_scheduler_calls_or_network_calls':0,'research_files_values_or_aggregates_read':False,
        'actual_final_CPU_or_analysis_run':False,'final_gate_ready':False})
    print(json.dumps({'status':'V2_CPU_DRAFT_FINITE_PHASE_AND_READONLY_ARGV_ARTIFICIAL_PASSED','research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
