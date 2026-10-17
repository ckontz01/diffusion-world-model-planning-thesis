"""New dynamic handoff fixtures; no actual study, archive, scheduler or SSD work."""
import ast,copy,json,os,shutil,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import cpu_workflow_v2 as w
from .analysis_closure_tests_v1 import fixture
from .evidence_auth_v1 import bound_json
from wm_diag0_rc1_final_v1.cpu_process_v2 import run_child as native_child
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new

PHASES={'analysis':1800,'independent_acceptance':600,'archive':1170,'finalize':30}


def reject(fn):
    try:fn()
    except (ValueError,PermissionError,FileExistsError,FileNotFoundError,TimeoutError,RuntimeError):return
    raise AssertionError('required dynamic handoff refusal absent')


def setup(root):
    template,c,contract,accepted,proof=fixture(root/'template')
    task=root/'future-task';ops=root/'external-ops'
    for p in (task/'logs',task/'controls',task/'output',task/'tmp',ops/'cpu/controls',ops/'cpu/tmp-archive',ops/'archive'):
        p.mkdir(parents=True)
    layout={'analysis_task':str(task),'operational_root':str(ops),'cpu_control_root':str(ops/'cpu/controls'),
            'archive_path':str(ops/'archive/final-study.tar')}
    c['rc1_final'].update(allocation_seconds=3600,CPUs=4,RAM_bytes=8589934592,GPU_requested=0,
                          automatic_retry=False,phase_seconds=dict(PHASES))
    c['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']=dict(w.CPU_V2)
    return template,task,layout,c,contract


def main():
    with tempfile.TemporaryDirectory(prefix='wm-rc1-dynamic-handoff-') as tmp:
        template,task,layout,c,contract=setup(Path(tmp));events=[];calls=[];closed_file=Path(layout['cpu_control_root'])/'ANALYSIS-CLOSED.json'
        def entry(end):events.append('entry');return {'synthetic':True,'actual_full_stage_gate':False}
        def analysis_argv(cc,ll,sha,role,end):
            if closed_file.exists():raise AssertionError('closed record premature')
            events.append('argv-'+role);return [sys.executable,'-B','-c',"print('new synthetic owned '+"+repr(role)+")"]
        def archive_argv(cc,ll,expected,closed_id,end):
            if len(calls)!=2:raise AssertionError('two owned V2 children/logs must close first')
            closed=bound_json(closed_file,closed_id,8000,end)
            if closed['contract']!=contract:raise AssertionError('dynamic external closed identity')
            for role in w.ROLES[:2]:
                if closed['files'][role]!=identity(task/'logs'/(role+'.log')):raise AssertionError('actual closed tiny child logs')
            events.append('argv-archive-after-closed');return [sys.executable,'-B','-c',"print('synthetic archive role; no archive made')"]
        def child(argv,env,log,roots,cap,logcap,end,cleanup):
            result=native_child(argv,env,log,roots,cap,logcap,end,cleanup);calls.append((str(log),end,cleanup))
            if len(calls)==2:
                # New inert fixture data, installed only after actual tiny child
                # groups/logs closed. This does NOT emulate real scientific work.
                for p in (template/'output').iterdir():shutil.copyfile(str(p),str(task/'output'/p.name))
                for p in (template/'controls').iterdir():shutil.copyfile(str(p),str(task/'controls'/p.name))
            return result
        def readback(end):events.append('readback');return {'synthetic':True,'actual_archive_readback':False}
        with patch.object(w,'check_paths',lambda z:z),patch.object(w,'prospective_analysis_argv',analysis_argv),patch.object(w,'archive_argv',archive_argv),patch.object(w,'run_child',child):
            result=w.run_fixed_sequence(c,layout,contract,time.monotonic(),PHASES,dict(os.environ),entry,readback)
            reject(lambda:w.run_fixed_sequence(c,layout,contract,time.monotonic(),PHASES,dict(os.environ),entry,readback))
        if events!=['entry','argv-analysis','argv-independent_acceptance','argv-archive-after-closed','readback'] or len(calls)!=3 or result['conversion_reserve_used'] or result['final_gate_ready']:
            raise AssertionError('exact once-only fixed role/dynamic handoff order')
        phase=json.loads((Path(layout['cpu_control_root'])/'PHASE-archive.json').read_text())
        for k in ('work_deadline','cleanup_deadline'):
            if phase['bounds'][k]-phase['child_work_and_cleanup_bounds'][k]!=30:raise AssertionError('parent authentication reservation stays inside archive phase')
        if (Path(layout['operational_root'])/'archive/final-study.tar').exists():raise AssertionError('tiny role is not actual archive execution')
    for which in ('draft','bool_resource','wrong_cleanup','wrong_phase','entry','missing_proof','child','parent_readback','boolean_time','existing_archive'):
        with tempfile.TemporaryDirectory(prefix='wm-rc1-dynamic-negative-') as tmp:
            template,task,layout,c,contract=setup(Path(tmp));calls=[];began=time.monotonic()
            def entry(end):
                if which=='entry':raise ValueError('synthetic entry refusal')
                return {'synthetic':True}
            def child(*args):
                calls.append(1)
                if which=='child':raise RuntimeError('synthetic child failure, no retry')
                if len(calls)==2 and which=='parent_readback':
                    for directory in ('output','controls','logs'):
                        for p in (template/directory).iterdir():shutil.copyfile(str(p),str(task/directory/p.name))
                return {'returncode':0}
            def readback(end):raise ValueError('synthetic missing archive readback')
            if which=='draft':c['rc1_final']['analysis_authorized']=False
            if which=='bool_resource':c['rc1_final']['CPUs']=True
            if which=='wrong_cleanup':c['staged_members']['wm_diag0_rc1_final_v1/cpu_process_v2.py']['bytes']=10254
            if which=='wrong_phase':c['rc1_final']['phase_seconds']['archive']-=1
            if which=='boolean_time':began=True
            if which=='existing_archive':
                with Path(layout['archive_path']).open('xb') as f:f.write(b'preserved synthetic partial')
            with patch.object(w,'check_paths',lambda z:z),patch.object(w,'prospective_analysis_argv',lambda *args:['synthetic']),patch.object(w,'archive_argv',lambda *args:['synthetic']),patch.object(w,'run_child',child):
                reject(lambda:w.run_fixed_sequence(c,layout,contract,began,PHASES,dict(os.environ),entry,readback))
            expected=3 if which=='parent_readback' else 2 if which=='missing_proof' else 1 if which=='child' else 0
            if len(calls)!=expected:raise AssertionError('failed gate must not launch/retry later phase: '+which)
    source={}
    for n in ('cpu_workflow_v2.py','cpu_workflow_tests_v2.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    record={'status':'FIXED_DYNAMIC_CLOSED_RECORD_TO_ARCHIVE_ROLE_TINY_NATIVE_COMPOSITION_PASSED','source':source,
        'actual_tiny_native_owned_synthetic_children':3,'actual_study_analysis_archives_or_allocations':0,
        'checks':['actual V2 tiny child cleanup/logs before dynamic closed proof identity',
            'complete synthetic controls and opaque NONJSON output authenticated',
            'fixed role builders receive actual phase deadlines; archive identity only after close',
            'parent authentication30 reserved inside archive phase; no conversion/final borrowing',
            'draft/bool/wrong V2/phase/entry/missing proof/child/readback/time/existing partial refusal; no retry'],
        'canonical_production_paths_and_real_archive_argv_executed':False,
        'actual_stage_runtime_root_storage_sourceCPU_dispatch_publication_SSD_gates_passed':False,
        'research_WSL_cluster_scheduler_SSD_calls':0,'scientific_payload_values_deserialized':False,
        'Linux_full_workflow_or_CPU_submission_executed':False,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-CPU-DYNAMIC-001.json',record,limit=16000)
    print(json.dumps({'status':record['status'],'tiny_owned_children':3,'actual_study_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
