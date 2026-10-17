"""New finite workflow integration with tiny ordinary-native synthetic children.

No research artifacts, models, simulator, scheduler, WSL, SSD or scientific math.
The three commands below are TEST fixtures, not production archive/analysis argv.
"""
import ast,json,os,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from . import cpu_workflow_v1 as w
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn,kind=(ValueError,FileExistsError,TimeoutError,RuntimeError)):
    try:fn()
    except kind:return
    raise AssertionError('required finite workflow refusal missing')


def fixture(root):
    controls=root/'external-controls';controls.mkdir()
    logs={};artifacts={};commands={}
    for p in w.ROLES:
        logs[p]=str(root/(p+'.log'));a=root/('own-'+p);a.mkdir();artifacts[p]=[str(a)]
        commands[p]=[sys.executable,'-B','-c',"print('synthetic owned phase')"]
    return controls,logs,artifacts,commands


def main():
    phases={'analysis':1800,'independent_acceptance':600,'archive':1170,'finalize':30};events=[]
    with tempfile.TemporaryDirectory(prefix='wm-rc1-cpu-workflow-') as tmp:
        controls,logs,artifacts,commands=fixture(Path(tmp))
        def entry(end):events.append('entry');return {'synthetic':True,'no_actual_stage_authority':True}
        def close(end):
            if not all(Path(logs[p]).is_file() for p in ('analysis','independent_acceptance')):raise AssertionError('logs must be closed first')
            events.append('closed');return {'synthetic_closed_logs':{p:w.identity(logs[p],100000,end) for p in ('analysis','independent_acceptance')}}
        def archive(end):events.append('archive-readback');return {'synthetic':True,'no_actual_archive_created':True}
        result=w.run_sequence(time.monotonic(),phases,commands,dict(os.environ),logs,artifacts,controls,entry,close,archive)
        if events!=['entry','closed','archive-readback'] or set(result['phases'])!=set(w.ROLES) or result['conversion_reserve_used'] or result['final_gate_ready']:
            raise AssertionError('once-only authenticated phase order/no gate promotion')
        reject(lambda:w.run_sequence(time.monotonic(),phases,commands,dict(os.environ),logs,artifacts,controls,entry,close,archive))
    for which in ('missing_archive','entry_failure','child_failure','deadline','order','boolean_time','close_failure'):
        with tempfile.TemporaryDirectory(prefix='wm-rc1-cpu-workflow-negative-') as tmp:
            controls,logs,artifacts,commands=fixture(Path(tmp));attempts=[];began=time.monotonic()
            def entry(end):
                if which=='entry_failure':raise ValueError('synthetic missing entry authority')
                return {'synthetic':True}
            def close(end):
                if which=='close_failure':raise ValueError('synthetic complete validator mismatch')
                return {'synthetic':True}
            def run(argv,*args):
                attempts.append(argv)
                if which=='child_failure':raise RuntimeError('synthetic child error; never retry')
                return {'status':'SYNTHETIC_CHILD_NOT_RUN','returncode':0}
            if which=='missing_archive':commands.pop('archive')
            if which=='deadline':began-=3601
            if which=='boolean_time':began=True
            if which=='order':commands={'analysis':commands['analysis']}
            with patch.object(w,'run_child',run):reject(lambda:w.run_sequence(began,phases,commands,dict(os.environ),logs,artifacts,controls,entry,close,lambda end:{'synthetic':True}))
            if which in ('missing_archive','entry_failure','deadline','order','boolean_time') and attempts:raise AssertionError('failed preflight must launch zero children')
            if which=='child_failure' and len(attempts)!=1:raise AssertionError('failed child automatically retried')
            if which=='close_failure' and len(attempts)!=2:raise AssertionError('archive launched before closed complete analysis gate')
    source={}
    for n in ('cpu_workflow_v1.py','cpu_workflow_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    result={'status':'NEW_FINITE_CPU_CHILD_PHASE_COMPOSITION_NATIVE_ARTIFICIAL_PASSED','source':source,
        'actual_tiny_native_owned_synthetic_children':3,'actual_research_children':0,
        'checks':['real V2 child runner for three tiny ordinary native fixture commands','ordered entry/writer/validator/closed/archive/finalize',
            'each child own cleanup and full future phase reservations','no conversion borrowing','exclusive existing refusal before launch',
            'missing archive/entry/child/deadline/bool/close failure stops without retry'],
        'production_archive_command_real_CPU_supervisor_stage_dispatch_publication_SSD_gates_complete':False,
        'Linux_full_workflow_integration_performed':False,'research_scheduler_WSL_SSD_calls':0,
        'actual_final_CPU_analysis_study_archive_full_SSD_run':False,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-CPU-WORKFLOW-001.json',result,limit=16000)
    print(json.dumps({'status':result['status'],'synthetic_owned_children':3,'research_calls':0,'final_gate_ready':False}))


if __name__=='__main__':main()
