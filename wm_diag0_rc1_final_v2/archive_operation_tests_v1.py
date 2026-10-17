"""New closed-analysis-to-once-archive integration on tiny native fixtures only."""
import ast,copy,json,os,tempfile,time
from pathlib import Path
from . import archive_operation_v1 as a
from .analysis_closure_tests_v1 import fixture
from .analysis_closure_v1 import close_after_owned_children
from .inventory_v3 import plan
from .root_binding_v1 import authenticate,OWNED_FINAL
from .archive_verify_v2 import verify,strict_json
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn,kinds=(ValueError,PermissionError,FileExistsError,TimeoutError,FileNotFoundError)):
    try:fn()
    except kinds:return
    raise AssertionError('required archive operation refusal missing')


def main():
    with tempfile.TemporaryDirectory(prefix='wm-rc1-closed-once-archive-') as tmp:
        root=Path(tmp);study=root/'study';old=study/'old';old.mkdir(parents=True);runtime=root/'runtime';runtime.mkdir();ops=root/'external-ops';ops.mkdir()
        for p,b in ((old/'STOP.json',b'retained old stop'),(old/'failure.partial',b'opaque retained failure'),(runtime/'all-runtime',b'synthetic entire runtime')):
            with p.open('xb') as f:f.write(b)
        priorpaths={'study/old':str(old),'runtime':str(runtime)}
        prior=authenticate(plan(study,['old'],{'runtime':runtime},{}),priorpaths,'f'*64,time.monotonic()+10)
        final=study/'campaign-v4-rc1-final-v2';task,c,contract,accepted,proof=fixture(final/'tasks')
        independent=identity(task/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json')
        closed=close_after_owned_children(c,contract,task,independent,time.monotonic()+5)
        paths=dict(priorpaths,**{OWNED_FINAL:str(final)})
        def fresh():return plan(study,['old',final.name],{'runtime':runtime},{})
        args=(c,contract,task,closed,fresh(),{'root_paths':paths,'final_contract_sha256':contract['sha256']},'f'*64,prior,
              ops/'once.tar',ops/'portable.json',ops/'readback.json',fresh,3000000000)
        result=a.preserve_closed_inventory(*args,deadline=time.monotonic()+10)
        portable=strict_json((ops/'portable.json').read_bytes())
        readback=verify(ops/'once.tar',portable,args[5],time.monotonic()+5,check_sources=False,
                        expected_whole=result['whole'],expected_manifest=result['manifest'])
        if result['whole']!=identity(ops/'once.tar') or not result['archive_created_once'] or result['final_gate_ready'] or readback['logical_members']!=len(fresh()['members']):
            raise AssertionError('complete tiny closed analysis/archive/portable/readback binding')
        reject(lambda:a.preserve_closed_inventory(*args,deadline=time.monotonic()+5))
        # A changed CLOSED input must stop before creating a DIFFERENT archive.
        with (task/'logs/analysis.log').open('ab') as f:f.write(b'inert mutation after closure')
        bad=list(args);bad[8]=ops/'must-not-create.tar';bad[9]=ops/'must-not-create-portable';bad[10]=ops/'must-not-create-proof'
        reject(lambda:a.preserve_closed_inventory(*bad,deadline=time.monotonic()+5))
        if bad[8].exists():raise AssertionError('archive created despite changed closed analysis input')
    layout=json.loads((ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/PRESERVATION-LAYOUT-001.json').read_text())['layout']
    grid=json.loads((ROOT/'docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json').read_text())
    command=a.archive_argv(grid,layout,{'bytes':100,'sha256':'a'*64},{'bytes':100,'sha256':'b'*64},time.monotonic()+10)
    binds=[command[i+1] for i,x in enumerate(command[:-1]) if x=='--bind']
    if '--nv' in command or any(x.startswith(layout['analysis_task']+':') and x.endswith(':rw') for x in binds) or layout['operational_root']+'/cpu/tmp-archive:/tmp:rw' not in binds:
        raise AssertionError('no mutable archive-input task/tmp or GPU binding')
    if layout['root_paths']['runtime/container.sif']+':'+layout['root_paths']['runtime/container.sif']+':ro' not in binds:raise AssertionError('complete SIF input must be readable inside archive container')
    if 'wm_diag0_rc1_final_v2.archive_operation_v1' not in command:raise AssertionError('real implemented archive child, not no-op')
    producer=identity(Path(__file__).parent/'archive_operation_v1.py')
    c={'staged_members':{a.PREPARATION_PRODUCER:producer}}
    prep={'schema':'WM-DIAG0-RC1-PREPARATION-COPIES-v1','producer_source':producer,
          'full_future_preparation_bytes':3000000000,'measurement_commitment':{'bytes':10,'sha256':'e'*64}}
    if a.preparation_bytes(c,prep)!=3000000000:raise AssertionError('finite evidence consumer')
    for n in (True,3000000000.,None,5368709121):
        bad=copy.deepcopy(prep);bad['full_future_preparation_bytes']=n;reject(lambda:a.preparation_bytes(c,bad))
    bad=copy.deepcopy(prep);bad['producer_source']['sha256']='0'*64;reject(lambda:a.preparation_bytes(c,bad))
    reject(lambda:a.preparation_bytes({'staged_members':{}},prep))
    reject(lambda:a.cpu_context({}))
    source={}
    for n in ('archive_operation_v1.py','archive_operation_tests_v1.py'):
        p=Path(__file__).parent/n;ast.parse(p.read_text(),feature_version=(3,6));source[n]=identity(p)
    result={'status':'CLOSED_ANALYSIS_TO_REAL_ARCHIVE_OPERATION_TINY_NATIVE_INTEGRATION_PASSED','source':source,
        'checks':['new tiny complete old STOP/failure/runtime+owned final analysis root preserved','closed controls/logs/sealed opaque output before AND after archive readback',
            'real once archive+independent everymember/original/root+portable readback','existing artifact refusal/no retry','changed closed input refused BEFORE new archive',
            'fixed real CPU archive argv/SIF input/RO study and final task/external RW ops+tmp/noGPU','finite bound producer/preparation consumer typing'],
        'native_preparation_measurement_producer_or_full_entry_stage_gate_implemented':False,
        'production_CLI_Linux_supervisor_submission_executed':False,'actual_research_analyses_or_study_archives_created':0,
        'research_WSL_cluster_scheduler_SSD_calls':0,'scientific_payload_values_deserialized':False,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-ARCHIVE-OPERATION-001.json',result,limit=16000)
    print(json.dumps({'status':result['status'],'actual_study_archive_created':False,'final_gate_ready':False}))


if __name__=='__main__':main()
