"""Additional artificial terminal/race/owned-descendant regressions only."""
import ast,copy,ctypes,json,subprocess,sys,tempfile,time
from pathlib import Path
from .common import DOC,identity,write_new
from .compact import compact_payload,program,GRID_HASH
from .job import child_job

def main():
    for source in Path(__file__).parent.glob('*.py'):ast.parse(source.read_text(),feature_version=(3,6))
    rows=[];tasks={}
    for i in range(124):
        raw=str(400000+i);seal={'bytes':1,'sha256':'b'*64};rows.append('317180_'+str(i)+'|'+raw+'|COMPLETED|0:0|100|4|gpu09')
        tasks[str(i)]={'STARTED':{'array_job_id':'317180','index':i,'contract':GRID_HASH,'job_id':raw},
                       'ACCEPTED':{'accepted':True,'contract_sha256':GRID_HASH,'output_seal':seal},
                       'RESULT':{'status':'ACCEPTED','job_id':raw,'output_seal':seal}}
    o={'dispatch':{'array_job_id':'317180','indices':124,'contract_sha256':GRID_HASH,'automatic_retries':0},
       'scheduler':'\n'.join(rows),'queue':'','queue_diagnostic':{'invalid_live_queue_id_authenticated_by_complete_terminal_history':True},
       'tasks':tasks,'accepted_grid_parents':124,'active_process_records':[],'STOP':None,'full_future_GPU_reservation':449783,
       'CPU_before_analysis':1436,'quality_choices_outcomes_or_predictions_read':False}
    z=compact_payload(o);assert z['complete_grid_technical_terminal_candidate'] and z['GPU_terminal_all_attempts_seconds']==15783
    b=copy.deepcopy(o);del b['tasks']['123']['RESULT'];b['accepted_grid_parents']=123
    assert compact_payload(b)['publication_finalization_pending']==[123]
    b=copy.deepcopy(o);b['scheduler']+='\n'+rows[0]
    try:compact_payload(b)
    except ValueError:pass
    else:raise AssertionError('duplicate scheduler row')
    b=copy.deepcopy(o);b['scheduler']=b['scheduler'].replace('|100|4|gpu09','|3601|4|gpu09',1)
    try:compact_payload(b)
    except ValueError:pass
    else:raise AssertionError('allocation overrun')
    b=copy.deepcopy(o);b['active_process_records']=[{'node_verification':{'PID_exists':True,'start_ticks_match':False}}]
    assert compact_payload(b)['status']=='PROCESS_VERIFICATION_UNAVAILABLE'
    # Actual native early-leader case: grandchild holds inherited stdout while
    # the worker/leader finishes. Kill only the newly owned job, then read its
    # accounting process count until empty under the reserved parent deadline.
    class ACC(ctypes.Structure):
        _fields_=[('user',ctypes.c_int64),('kernel',ctypes.c_int64),('period_user',ctypes.c_int64),('period_kernel',ctypes.c_int64),('faults',ctypes.c_ulong),('total',ctypes.c_ulong),('active',ctypes.c_ulong),('terminated',ctypes.c_ulong)]
    with tempfile.TemporaryDirectory(prefix='wmrc1-owned-job-') as tmp:
        marker=Path(tmp)/'descendant.txt'
        grand='from pathlib import Path;import os,time;Path('+repr(str(marker))+').write_text(str(os.getpid()));time.sleep(20)'
        leader='import subprocess,sys;subprocess.Popen([sys.executable,"-B","-c",'+repr(grand)+'])'
        k,h,usage=child_job();p=subprocess.Popen([sys.executable,'-B','-m','wm_diag0_rc1_completion_v1.worker',sys.executable,'-B','-c',leader],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:
            assert k.AssignProcessToJobObject(h,int(p._handle));p.stdin.write(b'GO\n');p.stdin.close()
            end=time.monotonic()+3
            while (not marker.exists() or p.poll() is None) and time.monotonic()<end:time.sleep(.02)
            assert marker.exists() and p.poll()==0
            before=ACC();assert k.QueryInformationJobObject(h,1,ctypes.byref(before),ctypes.sizeof(before),None) and before.active>=1
            descendant=int(marker.read_text());assert k.TerminateJobObject(h,125)
            end=time.monotonic()+2;after=ACC()
            while time.monotonic()<end:
                assert k.QueryInformationJobObject(h,1,ctypes.byref(after),ctypes.sizeof(after),None)
                if not after.active:break
                time.sleep(.02)
            assert after.active==0
        finally:
            k.TerminateJobObject(h,125);k.CloseHandle(h)
            if p.poll() is None:p.kill();p.wait(timeout=1)
    result={'status':'ARTIFICIAL_TERMINAL_RACE_AND_OWNED_DESCENDANT_TESTS_PASSED','scheduler_calls':0,'research_calls':0,'unrelated_processes_signalled':False,
            'owned_synthetic_descendant_PID':descendant,'owned_job_active_after_cleanup':after.active,
            'source':{p.name:identity(p) for p in Path(__file__).parent.glob('*.py')}}
    write_new(DOC/'ARTIFICIAL-002.json',result);print(json.dumps(result))

if __name__=='__main__':main()
